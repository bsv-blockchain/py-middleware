"""
Django Auth Middleware for BSV Authentication

This module provides Django authentication middleware for BSV blockchain,
directly ported from Express createAuthMiddleware() function.
"""

import logging
from typing import Optional, Dict, Any
from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.deprecation import MiddlewareMixin

from bsv_middleware.types import (
    WalletInterface,
    AuthMiddlewareOptions,
    LogLevel,
    CertificatesReceivedCallback,
    AuthInfo,
    BSVErrorCodes
)
from bsv_middleware.exceptions import (
    BSVAuthException,
    BSVServerMisconfiguredException
)
from bsv_middleware.py_sdk_bridge import PySdkBridge, create_py_sdk_bridge
from .transport import DjangoTransport, create_django_transport
from .session_manager import DjangoSessionManager, create_django_session_manager

logger = logging.getLogger(__name__)


class BSVAuthMiddleware(MiddlewareMixin):
    """
    Django BSV Authentication Middleware
    
    Direct port of Express createAuthMiddleware() function to Django.
    Handles BSV blockchain authentication using BRC-103/104 protocols.
    """
    
    def __init__(self, get_response=None):
        """
        Initialize BSV Auth Middleware.
        
        Equivalent to Express: createAuthMiddleware(options)
        """
        super().__init__(get_response)
        self.get_response = get_response
        
        # Load configuration from Django settings
        self._load_configuration()
        
        # Initialize components (equivalent to Express middleware setup)
        self._initialize_components()
        
        logger.info(f"BSVAuthMiddleware initialized with wallet: {type(self.wallet).__name__}")
    
    def _load_configuration(self) -> None:
        """
        Load BSV middleware configuration from Django settings.
        
        Equivalent to Express options destructuring.
        """
        try:
            bsv_config = getattr(settings, 'BSV_MIDDLEWARE', {})
            
            # Required configuration
            self.wallet = bsv_config.get('WALLET')
            if not self.wallet:
                raise BSVServerMisconfiguredException(
                    'You must configure BSV_MIDDLEWARE with a WALLET in Django settings.'
                )
            
            # Optional configuration with defaults (equivalent to Express options)
            self.allow_unauthenticated = bsv_config.get('ALLOW_UNAUTHENTICATED', False)
            self.certificates_to_request = bsv_config.get('CERTIFICATE_REQUESTS')
            self.on_certificates_received = bsv_config.get('ON_CERTIFICATES_RECEIVED')
            self.custom_session_manager = bsv_config.get('SESSION_MANAGER')
            self.logger_config = bsv_config.get('LOGGER')
            self.log_level = LogLevel(bsv_config.get('LOG_LEVEL', 'error'))
            
        except Exception as e:
            logger.error(f"Failed to load BSV middleware configuration: {e}")
            raise BSVServerMisconfiguredException(
                f"Invalid BSV_MIDDLEWARE configuration: {str(e)}"
            )
    
    def _initialize_components(self) -> None:
        """
        Initialize middleware components.
        
        Equivalent to Express: transport, sessionMgr, peer setup
        """
        try:
            # Create py-sdk bridge (equivalent to Express wallet usage)
            self.py_sdk_bridge = create_py_sdk_bridge(self.wallet)
            
            # Create transport (equivalent to Express ExpressTransport)
            self.transport = create_django_transport(
                self.py_sdk_bridge,
                self.allow_unauthenticated,
                self.log_level
            )
            
            # Session manager will be created per request (Django sessions are request-based)
            
            # 🎯 実際の Peer インスタンス作成 (Express 同等)
            try:
                # wallet を py-sdk 互換形式にアダプト
                from bsv_middleware.wallet_adapter import create_wallet_adapter
                adapted_wallet = create_wallet_adapter(self.wallet)
                
                # session manager を作成 (DefaultSessionManager使用)
                from bsv.auth.session_manager import DefaultSessionManager
                session_mgr = DefaultSessionManager()
                
                # Peer インスタンス作成 (Express new Peer() 同等)
                from bsv.auth.peer import Peer, PeerOptions
                
                # Debug: Verify adapter type before passing to Peer
                logger.info(f"[AUTH MIDDLEWARE DEBUG] adapted_wallet type: {type(adapted_wallet)}")
                logger.info(f"[AUTH MIDDLEWARE DEBUG] adapted_wallet methods: {[m for m in dir(adapted_wallet) if 'verify' in m]}")
                
                peer_options = PeerOptions(
                    wallet=adapted_wallet,
                    transport=self.transport,
                    certificates_to_request=self.certificates_to_request,
                    session_manager=session_mgr,
                    auto_persist_last_session=True,
                    logger=logger
                )
                
                self.peer = Peer(peer_options)
                self.transport.set_peer(self.peer)
                
                # CRITICAL: Start the peer to register message handlers
                self.peer.start()
                logger.info("✅ py-sdk Peer started and integration successful")
                
            except Exception as e:
                logger.error(f"❌ py-sdk Peer integration failed: {e}")
                # エラーの詳細を記録
                self._log_integration_error(e)
                raise BSVServerMisconfiguredException(
                    f"py-sdk Peer integration failed: {str(e)}"
                )
            
            logger.debug("BSV middleware components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize BSV middleware components: {e}")
            raise BSVServerMisconfiguredException(
                f"Component initialization failed: {str(e)}"
            )
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        print(f"[AUTH MIDDLEWARE] Processing request: {request.path}")
        """
        Main middleware entry point.
        
        Equivalent to Express: return (req, res, next) => { ... }
        """
        try:
            logger.debug(f"BSV Auth Middleware processing request: {request.path}")
            
            # Create session manager for this request
            session_manager = self._get_session_manager(request)
            
            # Handle the request through transport (equivalent to Express transport.handleIncomingRequest)
            response = self.transport.handle_incoming_request(
                request,
                self.on_certificates_received
            )
            
            # If transport returned a response, use it (auth endpoint case)
            if response:
                return response
            
            # Continue to next middleware/view (equivalent to Express next())
            if self.get_response:
                return self.get_response(request)
            
            # If no get_response (shouldn't happen in normal Django), return empty response
            return HttpResponse()
            
        except BSVAuthException as e:
            logger.warning(f"BSV authentication failed: {e.message}")
            return self._build_error_response(e)
        except Exception as e:
            logger.error(f"Unexpected error in BSV auth middleware: {e}")
            return self._build_error_response(
                BSVServerMisconfiguredException("Internal server error")
            )
    
    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """
        Django middleware process_request hook.
        
        This is called before the view is executed.
        """
        try:
            # Create session manager for this request
            session_manager = self._get_session_manager(request)
            
            # Handle authentication through transport
            response = self.transport.handle_incoming_request(
                request,
                self.on_certificates_received
            )
            
            # If transport returned a response, return it to short-circuit the request
            if response:
                return response
            
            # Ensure request.auth is set for payment middleware
            if not hasattr(request, 'auth') or request.auth is None:
                from bsv_middleware.types import AuthInfo
                request.auth = AuthInfo(identity_key='unknown')
            
            # Continue processing (return None to continue to view)
            return None
            
        except BSVAuthException as e:
            logger.warning(f"BSV authentication failed in process_request: {e.message}")
            return self._build_error_response(e)
        except Exception as e:
            logger.error(f"Unexpected error in process_request: {e}")
            import traceback
            traceback.print_exc()
            return self._build_error_response(
                BSVServerMisconfiguredException(f"Authentication processing failed: {str(e)}")
            )
    
    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """
        Django middleware process_response hook.
        
        This is called after the view is executed.
        """
        try:
            # Add BSV-specific headers if needed
            if hasattr(request, 'auth') and request.auth.identity_key != 'unknown':
                response['X-BSV-Identity-Key'] = request.auth.identity_key
            
            return response
            
        except Exception as e:
            logger.error(f"Error in process_response: {e}")
            return response  # Return original response on error
    
    def _log_integration_error(self, error: Exception) -> None:
        """統合エラーの詳細をログ記録"""
        import traceback
        from datetime import datetime
        
        error_details = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'component': 'BSVAuthMiddleware._initialize_components',
            'phase': 'Phase 2.1 Day 2',
            'traceback': traceback.format_exc(),
            'timestamp': datetime.now().isoformat()
        }
        
        logger.error(f"py-sdk integration error details: {error_details}")
        
        # ファイルにも記録 (デバッグ用)
        try:
            import json
            from pathlib import Path
            log_file = Path(__file__).parent.parent.parent / 'integration_errors.log'
            
            with open(log_file, 'a') as f:
                f.write(json.dumps(error_details, indent=2) + '\n\n')
        except Exception as log_error:
            logger.warning(f"Failed to write integration error log: {log_error}")

    def _get_session_manager(self, request: HttpRequest):
        """
        Get or create session manager for the request.
        
        Returns py-sdk compatible SessionManager (with adapter).
        Equivalent to Express: sessionManager || new SessionManager()
        """
        if self.custom_session_manager:
            return self.custom_session_manager
        
        # Create Django session manager with py-sdk adapter
        from .session_manager import DjangoSessionManagerAdapter, create_django_session_manager
        django_sm = create_django_session_manager(request.session)
        return DjangoSessionManagerAdapter(django_sm)
    
    def _build_error_response(self, exception: BSVAuthException) -> JsonResponse:
        """
        Build error response from BSV exception.
        
        Equivalent to Express error responses.
        """
        return JsonResponse(
            {
                'status': 'error',
                'code': exception.code,
                'description': exception.message,
                **exception.details
            },
            status=exception.status_code
        )


def create_auth_middleware(options: AuthMiddlewareOptions) -> BSVAuthMiddleware:
    """
    Factory function to create BSV auth middleware with options.
    
    This function is equivalent to Express createAuthMiddleware() but returns
    a Django middleware class instead of a function.
    
    Args:
        options: Authentication middleware options
        
    Returns:
        Configured BSVAuthMiddleware instance
    """
    # Set Django settings based on options
    if not hasattr(settings, 'BSV_MIDDLEWARE'):
        settings.BSV_MIDDLEWARE = {}
    
    settings.BSV_MIDDLEWARE.update({
        'WALLET': options.wallet,
        'ALLOW_UNAUTHENTICATED': options.allow_unauthenticated,
        'CERTIFICATE_REQUESTS': options.certificates_to_request,
        'ON_CERTIFICATES_RECEIVED': options.on_certificates_received,
        'SESSION_MANAGER': options.session_manager,
        'LOGGER': options.logger,
        'LOG_LEVEL': options.log_level.value
    })
    
    return BSVAuthMiddleware()


# Helper function for certificate handling (equivalent to Express onCertificatesReceived)
def default_certificates_received_handler(
    sender_public_key: str,
    certificates: list,
    request: HttpRequest,
    response: HttpResponse
) -> None:
    """
    Default certificate received handler.
    
    Equivalent to Express default onCertificatesReceived behavior.
    """
    logger.info(f"Received {len(certificates)} certificates from {sender_public_key}")
    
    for cert in certificates:
        logger.debug(f"Processing certificate: {cert}")
        # Add certificate processing logic here
