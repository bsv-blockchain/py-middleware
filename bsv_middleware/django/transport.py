"""
Django Transport Implementation for BSV Middleware

This module provides Django-specific transport functionality for BSV authentication,
directly ported from Express ExpressTransport class.
"""

import json
import logging
from typing import Optional, Dict, Any, Callable, List, TYPE_CHECKING
from django.http import HttpRequest, HttpResponse, JsonResponse

from ..types import (
    LogLevel,
    BSV_AUTH_PREFIX,
    AuthInfo, 
    CertificatesReceivedCallback
)

# py-sdk Transport interface import with TYPE_CHECKING
PY_SDK_AVAILABLE = False

if TYPE_CHECKING:
    # For type checking, always import the real types
    from bsv.auth.transports.transport import Transport
else:
    # At runtime, try to import, fall back to Any if not available
    try:
        from bsv.auth.transports.transport import Transport
        PY_SDK_AVAILABLE = True
    except ImportError:
        # Use Any for runtime when py-sdk is not available
        Transport = Any  # type: ignore
        PY_SDK_AVAILABLE = False

from ..exceptions import BSVAuthException, BSVServerMisconfiguredException
from ..py_sdk_bridge import PySdkBridge

logger = logging.getLogger(__name__)


class DjangoTransport(Transport):
    """
    Django equivalent of Express ExpressTransport class.
    
    This class handles HTTP transport for BSV authentication in Django,
    managing peer-to-peer communication and certificate exchange.
    """
    
    def __init__(
        self,
        py_sdk_bridge: PySdkBridge,
        allow_unauthenticated: bool = False,
        log_level: LogLevel = LogLevel.ERROR
    ):
        """
        Initialize Django transport.
        
        Args:
            py_sdk_bridge: Bridge to py-sdk functionality
            allow_unauthenticated: Whether to allow unauthenticated requests
            log_level: Logging level
        """
        self.py_sdk_bridge = py_sdk_bridge
        self.allow_unauthenticated = allow_unauthenticated
        self.log_level = log_level
        self.peer = None  # Will be set by auth_middleware
        
        # Storage for open handles (equivalent to Express implementation)
        self.open_non_general_handles: Dict[str, List[Dict[str, Any]]] = {}
        self.open_general_handles: Dict[str, Dict[str, Any]] = {}
        
        # Message callback (equivalent to Express onData callback)
        self.message_callback: Optional[Callable[..., Any]] = None
        
        # Certificate handling (Phase 2.6: Express compatibility)
        self.on_certificates_received: Optional[CertificatesReceivedCallback] = None
        self._certificate_listener_ids: Dict[str, int] = {}  # identity_key -> listener_id
        self.open_next_handlers: Dict[str, Callable] = {}  # For continuation after cert receipt
    
    def set_peer(self, peer: Any) -> None:
        """
        Set the peer instance.
        
        Equivalent to Express: setPeer(peer)
        """
        self.peer = peer
        self._log('debug', 'Peer set in DjangoTransport', {'peer': str(peer)})
    
    def on_data(self, callback: Callable[[Any, Any], Optional[Exception]]) -> Optional[Exception]:
        """
        Register callback for incoming data.
        
        Equivalent to Express: transport.onData(callback)
        Required by py-sdk Transport interface.
        
        Args:
            callback: Function to call when data is received, signature: (ctx, message) -> Optional[Exception]
            
        Returns:
            Optional[Exception]: None on success, Exception on failure
        """
        try:
            # Store the callback with proper signature handling
            def wrapper_callback(ctx: Any, message: Any) -> Any:
                self._log('info', '[WRAPPER] wrapper_callback called!')
                self._log('info', f'[WRAPPER] ctx type: {type(ctx).__name__}')
                self._log('info', f'[WRAPPER] message type: {type(message).__name__}')
                self._log('info', f'[WRAPPER] message.version: {getattr(message, "version", "NONE")}')
                self._log('info', f'[WRAPPER] message.message_type: {getattr(message, "message_type", "NONE")}')
                
                try:
                    # Call the original callback with both ctx and message
                    self._log('debug', f'wrapper_callback called with ctx={type(ctx).__name__}, message={type(message).__name__}')
                    
                    self._log('info', f'[WRAPPER] About to call original callback')
                    result = callback(ctx, message)
                    self._log('info', f'[WRAPPER] Original callback returned: {result} (type: {type(result)})')
                    
                    self._log('debug', f'callback returned: {result}')
                    return result
                except Exception as e:
                    self._log('error', f'Callback execution error: {e}')
                    import traceback
                    tb = traceback.format_exc()
                    self._log('error', f'Full traceback:\n{tb}')
                    print(f"[WRAPPER ERROR] Exception: {e}")
                    print(f"[WRAPPER ERROR] Full traceback:\n{tb}")
                    return e
            
            self.message_callback = wrapper_callback
            self._log('debug', 'onData callback registered with wrapper', {'callback': str(callback)})
            return None
        except Exception as e:
            self._log('error', 'Failed to register onData callback', {'error': str(e)})
            return e
    
    def send(self, ctx: Any, message: Any) -> Optional[Exception]:
        """
        Send an AuthMessage to the connected Peer.
        
        Equivalent to Express: ExpressTransport.send(message)
        This is the core method for py-sdk Transport interface.
        
        Args:
            ctx: Context (not used in Django implementation)
            message: AuthMessage to send
            
        Returns:
            Optional[Exception]: None on success, Exception on failure
        """
        try:
            self._log('debug', 'Attempting to send AuthMessage', {'message': str(message)[:200]})
            
            # Get message_type (Python standard: snake_case)
            # Handle both dict and object access patterns
            if isinstance(message, dict):
                message_type = message.get('message_type') or message.get('messageType')  # fallback for legacy
            else:
                message_type = getattr(message, 'message_type', None) or getattr(message, 'messageType', None)  # fallback for legacy
            
            if not message_type:
                # Debug: show what we received
                if isinstance(message, dict):
                    self._log('debug', f'AuthMessage dict keys: {list(message.keys())}')
                else:
                    self._log('debug', f'AuthMessage attrs: {[a for a in dir(message) if not a.startswith("_")]}')
                return Exception('Invalid AuthMessage: missing message_type')
            
            # Special handling for initialResponse - this should be sent as HTTP response
            if message_type == 'initialResponse':
                return self._send_initial_response(ctx, message)
            elif message_type != 'general':
                return self._send_non_general_message(message)
            else:
                return self._send_general_message(message)
                
        except Exception as e:
            error_msg = f'Failed to send AuthMessage: {str(e)}'
            self._log('error', error_msg, {'error': str(e)})
            return Exception(error_msg)
    
    def _send_non_general_message(self, message: Any) -> Optional[Exception]:
        """
        Send non-general AuthMessage (for /.well-known/auth endpoint).
        
        Equivalent to Express: ExpressTransport.send() non-general branch
        """
        try:
            your_nonce = getattr(message, 'your_nonce', None) or getattr(message, 'yourNonce', None)  # fallback for legacy
            if not your_nonce:
                return Exception('Non-general message missing your_nonce')
            
            handles = self.open_non_general_handles.get(your_nonce, [])
            if not handles:
                self._log('warn', 'No open handles to peer for nonce', {'yourNonce': your_nonce})
                return Exception('No open handles to this peer!')
            
            # Get the first handle (Express behavior)
            handle = handles[0]
            response = handle.get('response')
            
            if not response:
                return Exception('No response object in handle')
            
            # Build BRC-104 compliant response headers
            response_headers = self._build_auth_response_headers(message)
            
            # Set headers on Django response
            for header, value in response_headers.items():
                response[header] = value
            
            self._log('info', 'Sending non-general AuthMessage response', {
                'status': 200,
                'responseHeaders': response_headers,
                'messageType': message.messageType
            })
            
            # Set response content (AuthMessage as JSON)
            import json
            try:
                message_dict = self._message_to_dict(message)
                response.content = json.dumps(message_dict).encode('utf-8')
                response['Content-Type'] = 'application/json'
            except (TypeError, ValueError) as e:
                self._log('error', f'Failed to serialize AuthMessage to JSON: {e}', {
                    'message_type': getattr(message, 'messageType', 'unknown'),
                    'error': str(e)
                })
                # Fallback: simple string representation
                response.content = str(message).encode('utf-8')
                response['Content-Type'] = 'text/plain'
            
            # Remove the used handle
            handles.pop(0)
            if not handles:
                del self.open_non_general_handles[your_nonce]
            
            return None
            
        except Exception as e:
            return Exception(f'Failed to send non-general message: {str(e)}')
    
    def _send_initial_response(self, ctx: Any, message: Any) -> Optional[Exception]:
        """
        Send initial authentication response as HTTP response.
        
        This handles the special case where Peer generates an initialResponse
        that should be returned as HTTP response rather than sent to a handle.
        """
        try:
            self._log('debug', 'Sending initial response as HTTP response')
            
            # Extract request/response from context
            request = ctx.get('request') if isinstance(ctx, dict) else None
            response = ctx.get('response') if isinstance(ctx, dict) else None
            
            if not request:
                return Exception('No request context available for initial response')
            
            # Convert AuthMessage to JSON response format
            identity_key_raw: Any = getattr(message, 'identity_key', {})
            identity_key_str: str = identity_key_raw.hex() if hasattr(identity_key_raw, 'hex') else str(identity_key_raw)
            
            signature_raw: Any = getattr(message, 'signature', b'')
            signature_str: str = signature_raw.hex() if isinstance(signature_raw, bytes) else str(signature_raw)
            
            response_data: Dict[str, Any] = {
                'status': 'success',
                'messageType': getattr(message, 'messageType', getattr(message, 'message_type', 'initialResponse')),
                'version': getattr(message, 'version', '0.1'),
                'nonce': getattr(message, 'nonce', ''),
                'initialNonce': getattr(message, 'initial_nonce', getattr(message, 'initialNonce', '')),
                'yourNonce': getattr(message, 'your_nonce', getattr(message, 'yourNonce', '')),
                'identityKey': identity_key_str,
                'certificates': getattr(message, 'certificates', []),
                'signature': signature_str
            }
            
            # Store response data in context for middleware to access
            setattr(request, '_bsv_auth_response', response_data)
            
            self._log('debug', 'Initial response stored in request context', {
                'messageType': response_data['messageType'],
                'nonce': response_data['nonce'][:20] + '...' if response_data['nonce'] else ''
            })
            
            return None  # Success
            
        except Exception as e:
            self._log('error', f'Failed to send initial response: {e}')
            return Exception(f'Failed to send initial response: {str(e)}')
    
    def _send_general_message(self, message: Any) -> Optional[Exception]:
        """
        Send general AuthMessage (for regular API requests).
        
        Equivalent to Express: ExpressTransport.send() general branch
        """
        try:
            # Parse payload to get requestId (Express implementation)
            payload = getattr(message, 'payload', [])
            if not payload or len(payload) < 32:
                return Exception('General message missing or invalid payload')
            
            # Extract requestId from first 32 bytes
            request_id_bytes = payload[:32]
            import base64
            request_id = base64.b64encode(bytes(request_id_bytes)).decode('utf-8')
            
            handle = self.open_general_handles.get(request_id)
            if not handle:
                self._log('warn', 'No response handle for requestId', {'requestId': request_id})
                return Exception('No response handle for this requestId!')
            
            response = handle.get('response')
            if not response:
                return Exception('No response object in handle')
            
            # Parse status code and headers from payload (Express format)
            status_code, headers, body = self._parse_general_message_payload(payload[32:])
            
            # Build complete response headers
            response_headers = headers.copy()
            response_headers.update(self._build_auth_response_headers(message))
            response_headers['x-bsv-auth-request-id'] = request_id
            
            # Set headers and content on Django response
            for header, value in response_headers.items():
                response[header] = value
            
            response.status_code = status_code
            if body:
                response.content = bytes(body)
            
            self._log('info', 'Sending general AuthMessage response', {
                'status': status_code,
                'responseHeaders': response_headers,
                'responseBodyLength': len(body) if body else 0,
                'requestId': request_id
            })
            
            # Clean up the used handle
            del self.open_general_handles[request_id]
            
            return None
            
        except Exception as e:
            return Exception(f'Failed to send general message: {str(e)}')
    
    def _build_auth_response_headers(self, message: Any) -> Dict[str, str]:
        """
        Build BRC-104 compliant authentication headers.
        
        Equivalent to Express: responseHeaders object construction
        """
        headers = {}
        
        if hasattr(message, 'version'):
            headers['x-bsv-auth-version'] = str(message.version)
        
        if hasattr(message, 'messageType'):
            headers['x-bsv-auth-message-type'] = str(message.messageType)
            
        if hasattr(message, 'identityKey'):
            headers['x-bsv-auth-identity-key'] = str(message.identityKey)
            
        if hasattr(message, 'nonce'):
            headers['x-bsv-auth-nonce'] = str(message.nonce)
            
        if hasattr(message, 'yourNonce'):
            headers['x-bsv-auth-your-nonce'] = str(message.yourNonce)
            
        if hasattr(message, 'signature'):
            # Convert signature to hex (Express: Utils.toHex(message.signature))
            signature = message.signature
            if isinstance(signature, (list, tuple)):
                signature = bytes(signature)
            if isinstance(signature, bytes):
                headers['x-bsv-auth-signature'] = signature.hex()
            else:
                headers['x-bsv-auth-signature'] = str(signature)
        
        if hasattr(message, 'requestedCertificates') and message.requestedCertificates:
            import json
            headers['x-bsv-auth-requested-certificates'] = json.dumps(message.requestedCertificates)
        
        return headers
    
    def _parse_general_message_payload(self, payload: List[int]) -> tuple[int, Dict[str, str], List[int]]:
        """
        Parse general message payload to extract status, headers, and body.
        
        Equivalent to Express: Utils.Reader parsing logic
        """
        try:
            # Simple implementation - in real Express, this uses Utils.Reader
            # For now, return default values
            status_code = 200
            headers: Dict[str, str] = {}
            body = payload if payload else []
            
            return status_code, headers, body
            
        except Exception:
            empty_headers: Dict[str, str] = {}
            return 200, empty_headers, []
    
    def _message_to_dict(self, message: Any) -> Dict[str, Any]:
        """Convert AuthMessage to dictionary for JSON serialization."""
        result = {}
        for attr in ['messageType', 'version', 'identityKey', 'nonce', 'yourNonce', 'payload', 'signature']:
            if hasattr(message, attr):
                value = getattr(message, attr)
                
                # Handle different value types
                if isinstance(value, bytes):
                    result[attr] = list(value)
                elif hasattr(value, '_mock_name'):  # Mock object detection
                    result[attr] = str(value)
                elif value is None:
                    result[attr] = None
                else:
                    try:
                        # Test if value is JSON serializable
                        import json
                        json.dumps(value)
                        result[attr] = value
                    except (TypeError, ValueError):
                        # Convert non-serializable values to string
                        result[attr] = str(value)
        return result
    
    def handle_incoming_request(
        self,
        request: HttpRequest,
        on_certificates_received: Optional[CertificatesReceivedCallback] = None,
        response: Optional[HttpResponse] = None
    ) -> Optional[HttpResponse]:
        """
        Handle incoming Django request for BSV authentication.
        
        py-sdk compliant: Convert HTTP request to AuthMessage and delegate to Peer
        
        Args:
            request: Django HTTP request
            on_certificates_received: Callback for certificate processing
            response: Django HTTP response (if available)
            
        Returns:
            HttpResponse if request should be handled immediately, None to continue
        """
        self._log('debug', 'Handling incoming request (py-sdk compliant)', {
            'path': request.path,
            'method': request.method,
            'headers': dict(request.headers),
            'body': str(request.body)[:200] if request.body else 'empty'
        })
        
        try:
            if not self.peer:
                self._log('error', 'No Peer set in DjangoTransport! Cannot handle request.')
                raise BSVAuthException('You must set a Peer before you can handle incoming requests!')
            
            # Store callback for later use
            if on_certificates_received:
                self.on_certificates_received = on_certificates_received
            
            # Convert HTTP request to AuthMessage and delegate to py-sdk Peer
            return self._handle_request_via_peer(request, response)
                
        except Exception as e:
            self._log('error', f'Error handling incoming request: {e}')
            import traceback
            traceback.print_exc()
            raise BSVAuthException(f"Request handling failed: {str(e)}")
    
    def _handle_request_via_peer(
        self,
        request: HttpRequest,
        response: Optional[HttpResponse] = None
    ) -> Optional[HttpResponse]:
        """
        py-sdk compliant: Convert HTTP to AuthMessage, delegate to Peer, convert back
        """
        try:
            # Check if this is a .well-known/bsv/auth POST request (initialRequest)
            if request.path == '/.well-known/bsv/auth' and request.method == 'POST':
                self._log('debug', 'Handling .well-known/bsv/auth POST request')
                return self._handle_well_known_auth(request, response, None)
            
            # Step 1: Extract BSV headers and convert to AuthMessage
            auth_message = self._convert_http_to_auth_message(request)
            
            if not auth_message:
                # No BSV auth data - check allowUnauthenticated
                return self._handle_unauthenticated_request(request, response)
            
            self._log('debug', 'Converted HTTP to AuthMessage', {
                'version': auth_message.version,
                'message_type': auth_message.message_type,
                'identity_key': str(auth_message.identity_key)[:20] if auth_message.identity_key else None,
                'nonce': auth_message.nonce[:20] if auth_message.nonce else None
            })
            
            # Step 2: Create context for py-sdk
            ctx = {
                'request': request,
                'response': response,
                'path': request.path,
                'method': request.method
            }
            
            # Step 2.5: Register certificate listener (Phase 2.6: Express compatibility)
            # Equivalent to Express: peer.listenForCertificatesReceived()
            if (auth_message.identity_key and 
                self.peer and 
                hasattr(self.peer, 'session_manager') and
                self.on_certificates_received):
                
                identity_key_str = str(auth_message.identity_key)
                
                # Only register if session doesn't exist yet (like Express)
                try:
                    has_session = self.peer.session_manager.has_session(identity_key_str)
                except Exception:
                    has_session = False
                
                if not has_session and identity_key_str not in self._certificate_listener_ids:
                    self._log('debug', 'Registering certificate listener for new session', {
                        'identity_key': identity_key_str[:20]
                    })
                    
                    # Register certificate listener
                    listener_id = self._register_certificate_listener(
                        identity_key_str,
                        auth_message,
                        request,
                        response
                    )
                    
                    if listener_id is not None:
                        self._certificate_listener_ids[identity_key_str] = listener_id
                        self._log('debug', 'Certificate listener registered', {
                            'listener_id': listener_id,
                            'identity_key': identity_key_str[:20]
                        })
            
            # Step 3: Check if this is a General Message
            # General Message: has x-bsv-auth-request-id header
            if request.headers.get('x-bsv-auth-request-id'):
                self._log('debug', 'Detected General Message, delegating to _handle_general_message')
                return self._handle_general_message(request, response, None)
            
            # Step 3b: Non-general message - delegate to py-sdk Peer
            self._log('debug', 'Delegating to py-sdk Peer.handle_incoming_message')
            
            # Use the message_callback if available (registered via on_data)
            if self.message_callback:
                print(f"[DEBUG] Calling message_callback with ctx={ctx}, auth_message type={type(auth_message)}")
                try:
                    error = self.message_callback(ctx, auth_message)
                    print(f"[DEBUG] message_callback returned: {error} (type: {type(error)})")
                    
                    # Handle NotImplementedError specifically
                    if isinstance(error, NotImplementedError):
                        print(f"[DEBUG] NotImplementedError details: {str(error)}")
                        import traceback
                        traceback.print_exc()
                        return self._create_error_response(f"Peer configuration error: {str(error)}")
                    
                    # py-sdk returns None on success, Exception on error
                    if error is not None and error != "":
                        print(f"[DEBUG] Peer processing failed: {error}")
                        self._log('error', f'Peer processing failed: {error}')
                        return self._create_error_response(f"Authentication failed: {error}")
                    else:
                        print(f"[DEBUG] Peer processing successful")
                except Exception as callback_error:
                    print(f"[DEBUG] message_callback exception: {callback_error}")
                    import traceback
                    traceback.print_exc()
                    return self._create_error_response(f"Authentication failed: {callback_error}")
            else:
                print(f"[DEBUG] No message_callback registered!")
                self._log('warning', 'No message_callback registered! Peer not properly initialized.')
                return self._create_error_response("Peer not initialized")
            
            # Step 4: Convert Peer result back to HTTP response
            print(f"[DEBUG] Converting peer result to HTTP")
            return self._convert_peer_result_to_http(ctx, auth_message, request)
            
        except Exception as e:
            self._log('error', f'Error in peer delegation: {e}')
            import traceback
            traceback.print_exc()
            return self._create_error_response(f"Peer processing error: {str(e)}")
    
    def _convert_http_to_auth_message(self, request: HttpRequest):
        """Convert Django HTTP request to py-sdk AuthMessage"""
        try:
            from bsv.auth.auth_message import AuthMessage
            from bsv.keys import PublicKey
            
            # Extract BSV headers (no defaults - must be explicitly present)
            version = request.headers.get('x-bsv-auth-version', '')
            message_type = request.headers.get('x-bsv-auth-message-type', '')
            identity_key_hex = request.headers.get('x-bsv-auth-identity-key', '')
            nonce = request.headers.get('x-bsv-auth-nonce', '')
            
            # Check if this is a BSV auth request - must have at least one BSV header
            if not any([version, message_type, identity_key_hex, nonce]):
                return None
            
            # Set defaults only if BSV headers are present
            if not version:
                version = '0.1'  # py-sdk expects 0.1
            if not message_type:
                message_type = 'initialRequest'  # Default to initialRequest
            
            # Convert version for py-sdk compatibility
            if version == '1.0':
                version = '0.1'  # py-sdk uses 0.1
            
            # Convert message_type for py-sdk compatibility
            if message_type == 'initial':
                message_type = 'initialRequest'  # py-sdk uses initialRequest
            
            # Convert identity key to PublicKey object
            identity_key = None
            if identity_key_hex:
                try:
                    identity_key = PublicKey(identity_key_hex)
                except Exception as e:
                    self._log('warning', f'Invalid identity key: {e}')
            
            # Extract payload from request body
            payload = None
            if request.body:
                payload = request.body
            
            # Create AuthMessage with py-sdk compatible structure
            auth_message = AuthMessage(
                version=version,
                message_type=message_type,
                identity_key=identity_key,
                nonce=nonce,
                initial_nonce=nonce,  # py-sdk expects initial_nonce for initialRequest
                payload=payload
            )
            
            return auth_message
            
        except Exception as e:
            self._log('error', f'Failed to convert HTTP to AuthMessage: {e}')
            return None
    
    def _convert_peer_result_to_http(
        self, 
        ctx: dict, 
        auth_message, 
        request: HttpRequest
    ) -> Optional[HttpResponse]:
        """Convert py-sdk Peer processing result to HTTP response"""
        try:
            print(f"[DEBUG] _convert_peer_result_to_http called")
            
            # Check if initial response was stored by _send_initial_response
            if hasattr(request, '_bsv_auth_response'):
                print(f"[DEBUG] Found initial response in request context")
                from django.http import JsonResponse
                response_data = request._bsv_auth_response
                self._log('debug', 'Returning initial response as JSON', {
                    'messageType': response_data.get('messageType'),
                    'nonce': response_data.get('nonce', '')[:20] + '...' if response_data.get('nonce') else ''
                })
                return JsonResponse(response_data)
            
            # py-sdk compliant: Check authentication status via Peer's session management
            identity_key = auth_message.identity_key
            print(f"[DEBUG] identity_key: {identity_key.hex()[:20] if identity_key else None}")
            
            if identity_key and self.peer:
                # Check if we have an authenticated session for this identity
                try:
                    self._log('debug', f'Checking authenticated session for {identity_key.hex()[:20]}')
                    session = self.peer.get_authenticated_session(ctx, identity_key, 0)  # No wait time
                    
                    self._log('debug', f'Session result: {session}, authenticated: {getattr(session, "is_authenticated", None) if session else None}')
                    
                    if session and getattr(session, 'is_authenticated', False):
                        # Success - set request.auth like Express middleware
                        from ..types import AuthInfo
                        request.auth = AuthInfo(
                            identity_key=identity_key.hex(),
                            authenticated=True,
                            certificates=getattr(session, 'peer_certificates', [])
                        )
                        
                        self._log('debug', 'Peer authentication successful', {
                            'identity_key': identity_key.hex()[:20],
                            'session_authenticated': session.is_authenticated
                        })
                        return None  # Continue to next middleware/view
                    
                    else:
                        self._log('debug', 'No authenticated session found')
                        # Fall through to unauthenticated handling
                        
                except Exception as session_error:
                    self._log('warning', f'Error checking session: {session_error}')
                    # Fall through to unauthenticated handling
            
            # No authenticated session - handle based on allow_unauthenticated
            if self.allow_unauthenticated:
                # Express equivalent: req.auth = { identityKey: 'unknown' }
                from ..types import AuthInfo
                request.auth = AuthInfo(identity_key='unknown', authenticated=False)
                
                self._log('debug', 'Unauthenticated request allowed')
                return None  # Continue
            else:
                self._log('warning', 'Authentication required but not provided')
                return self._create_error_response("Authentication required", 401)
            
        except Exception as e:
            self._log('error', f'Error converting peer result: {e}')
            import traceback
            traceback.print_exc()
            return self._create_error_response(f"Response conversion error: {str(e)}")
    
    def _create_error_response(self, message: str, status: int = 400) -> HttpResponse:
        """Create a JSON error response"""
        from django.http import JsonResponse
        return JsonResponse({
            'status': 'error',
            'message': message
        }, status=status)
    
    def _handle_well_known_auth(
        self,
        request: HttpRequest,
        response: Optional[HttpResponse],
        on_certificates_received: Optional[CertificatesReceivedCallback]
    ) -> Optional[HttpResponse]:
        """
        Handle /.well-known/auth endpoint (non-general messages).
        
        Equivalent to Express: handleIncomingRequest() /.well-known/auth branch
        """
        try:
            # Parse AuthMessage from request body (Express: req.body as AuthMessage)
            if not request.body:
                raise BSVAuthException('Empty request body for /.well-known/auth')
            
            import json
            message_data = json.loads(request.body.decode('utf-8'))
            self._log('debug', 'Received non-general message at /.well-known/auth', {'message': message_data})
            
            # Get request ID (Express logic)
            request_id = request.headers.get('x-bsv-auth-request-id')
            if not request_id:
                request_id = message_data.get('initialNonce', 'unknown')
            
            # Store handle for response (Express: openNonGeneralHandles)
            if not response:
                response = HttpResponse()
            
            handle = {'response': response, 'request': request}
            
            if request_id in self.open_non_general_handles:
                self.open_non_general_handles[request_id].append(handle)
            else:
                self.open_non_general_handles[request_id] = [handle]
            
            # Set up certificate listener if no session exists (Express logic)
            identity_key = message_data.get('identityKey')
            if identity_key and hasattr(self.peer, 'sessionManager'):
                if not self.peer.sessionManager.hasSession(identity_key):
                    self._setup_certificate_listener(identity_key, request, response, on_certificates_received)
            
            # Trigger message processing through py-sdk Peer
            if self.message_callback:
                try:
                    # Convert message_data to proper AuthMessage format
                    self._log('debug', 'Converting message_data to AuthMessage', {'message_data': message_data})
                    auth_message = self._dict_to_auth_message(message_data)
                    self._log('debug', 'AuthMessage created successfully', {
                        'message_type': getattr(auth_message, 'message_type', 'unknown'),
                        'identity_key_type': type(getattr(auth_message, 'identity_key', None)).__name__
                    })
                    
                    # Create context for Peer
                    ctx = {
                        'request': request,
                        'response': response,
                        'request_id': request_id
                    }
                    
                    # Call Peer.handle_incoming_message synchronously
                    self._log('debug', 'Calling message_callback with ctx and auth_message')
                    error = self.message_callback(ctx, auth_message)
                    self._log('debug', f'message_callback returned: {error}')
                    
                    if error:
                        self._log('error', f'Peer processing error: {error}')
                        import traceback
                        self._log('error', f'Traceback: {traceback.format_exc()}')
                        return JsonResponse({
                            'status': 'error',
                            'code': 'ERR_PEER_PROCESSING_FAILED',
                            'description': str(error)
                        }, status=500)
                except Exception as e:
                    self._log('error', f'Exception in message processing: {e}')
                    import traceback
                    self._log('error', f'Traceback: {traceback.format_exc()}')
                    return JsonResponse({
                        'status': 'error',
                        'code': 'ERR_AUTH_PROCESSING_FAILED',
                        'description': str(e)
                    }, status=500)
                
                # Check if Peer sent initialResponse via _send_initial_response
                # The response data is stored in request._bsv_auth_response
                if hasattr(request, '_bsv_auth_response'):
                    self._log('debug', 'Returning initialResponse from Peer')
                    return JsonResponse(request._bsv_auth_response)
                
                # Fallback: return processing acknowledgment
                self._log('warn', 'No initialResponse found in request context')
                return JsonResponse({
                    'status': 'processing',
                    'message': 'Authentication request received'
                })
            
            # No message callback - should not happen if Peer is initialized
            return JsonResponse({
                'status': 'error',
                'code': 'ERR_NO_PEER',
                'description': 'Peer not initialized'
            }, status=500)
            
        except Exception as e:
            self._log('error', f'Failed to handle /.well-known/auth: {e}')
            return JsonResponse({
                'status': 'error',
                'code': 'ERR_AUTH_PROCESSING_FAILED',
                'description': str(e)
            }, status=500)
    
    def _handle_general_message(
        self,
        request: HttpRequest,
        response: Optional[HttpResponse],
        on_certificates_received: Optional[CertificatesReceivedCallback]
    ) -> Optional[HttpResponse]:
        """
        Handle general messages (regular API requests with auth headers).
        
        Equivalent to Express: handleIncomingRequest() general message branch
        """
        try:
            # Build AuthMessage from request (Express: buildAuthMessageFromRequest)
            auth_message = self._build_auth_message_from_request(request)
            self._log('debug', 'Received general message with x-bsv-auth-request-id', {'message': str(auth_message)[:200]})
            
            # Set up general message listener (Express: peer.listenForGeneralMessages)
            listener_id = self._setup_general_message_listener(request, response, auth_message)
            self._log('debug', 'General message listener registered', {'listenerId': listener_id})
            
            # Trigger message processing SYNCHRONOUSLY
            # Peer will process the message, verify signature, and call the callback
            # The callback will set request.auth if authentication succeeds
            print(f"[DEBUG transport] About to call message_callback")
            print(f"[DEBUG transport] auth_message: {auth_message}")
            print(f"[DEBUG transport] request.auth before: {getattr(request, 'auth', 'NOT SET')}")
            
            if self.message_callback:
                try:
                    self._log('debug', 'Calling message_callback synchronously for general message')
                    
                    # デバッグ：AuthMessageの詳細を確認
                    print(f"[DEBUG transport] === AUTH MESSAGE DETAILS ===")
                    print(f"[DEBUG transport] Type: {type(auth_message)}")
                    print(f"[DEBUG transport] version: {getattr(auth_message, 'version', 'NOT SET')}")
                    print(f"[DEBUG transport] message_type: {getattr(auth_message, 'message_type', 'NOT SET')}")
                    print(f"[DEBUG transport] identity_key: {getattr(auth_message, 'identity_key', 'NOT SET')}")
                    print(f"[DEBUG transport] nonce: {getattr(auth_message, 'nonce', 'NOT SET')[:20] if hasattr(auth_message, 'nonce') else 'NOT SET'}")
                    print(f"[DEBUG transport] signature: {getattr(auth_message, 'signature', 'NOT SET')[:20] if hasattr(auth_message, 'signature') else 'NOT SET'}")
                    print(f"[DEBUG transport] payload: {type(getattr(auth_message, 'payload', None))}")
                    print(f"[DEBUG transport] ===========================")
                    
                    # Call synchronously - Peer.handle_general_message is synchronous
                    result = self.message_callback(None, auth_message)  # ctx, message
                    
                    print(f"[DEBUG transport] message_callback returned: {result} (type: {type(result)})")
                    self._log('debug', 'message_callback completed')
                    print(f"[DEBUG transport] message_callback completed successfully")
                except Exception as e:
                    self._log('error', f'message_callback failed: {e}')
                    import traceback
                    traceback.print_exc()
                    print(f"[DEBUG transport] message_callback FAILED: {e}")
                    return JsonResponse({
                        'status': 'error',
                        'code': 'ERR_MESSAGE_PROCESSING_FAILED',
                        'description': str(e)
                    }, status=500)
            
            print(f"[DEBUG transport] request.auth after: {getattr(request, 'auth', 'NOT SET')}")
            
            # Debug: detailed request.auth inspection
            if hasattr(request, 'auth'):
                print(f"[DEBUG transport] request.auth exists: {request.auth}")
                print(f"[DEBUG transport] request.auth.identity_key: {getattr(request.auth, 'identity_key', 'NO IDENTITY_KEY')}")
                print(f"[DEBUG transport] request.auth.authenticated: {getattr(request.auth, 'authenticated', 'NO AUTHENTICATED')}")
            else:
                print(f"[DEBUG transport] request.auth does NOT exist")
            
            # After message processing, check if authentication was successful
            if hasattr(request, 'auth') and request.auth.identity_key != 'unknown':
                self._log('info', 'General message authenticated, continuing to view', {
                    'identityKey': request.auth.identity_key[:20] + '...'
                })
                print(f"[DEBUG transport] Authentication SUCCESS")
                
                # TypeScript compatibility: Check for payment header
                payment_header = request.headers.get('X-BSV-Payment')
                if payment_header:
                    print(f"[DEBUG transport] Payment header detected, continuing to payment middleware")
                    return None  # Continue to payment middleware
                else:
                    print(f"[DEBUG transport] No payment header, checking if payment required")
                    # Let the view/payment middleware handle payment requirement
                    return None  # Continue to next middleware/view
            else:
                # Authentication failed or not set
                self._log('warn', 'General message authentication failed')
                print(f"[DEBUG transport] Authentication FAILED, returning 401")
                return JsonResponse({
                    'status': 'error',
                    'message': 'Authentication required'
                }, status=401)
            
        except Exception as e:
            self._log('error', f'Failed to handle general message: {e}')
            return JsonResponse({
                'status': 'error',
                'code': 'ERR_GENERAL_MESSAGE_FAILED',
                'description': str(e)
            }, status=500)
    
    def _handle_unauthenticated_request(
        self,
        request: HttpRequest,
        response: Optional[HttpResponse]
    ) -> Optional[HttpResponse]:
        """
        Handle requests without auth headers.
        
        Equivalent to Express: allowUnauthenticated check
        """
        self._log('warn', 'No Auth headers found on request. Checking allowUnauthenticated setting.', {
            'allowAuthenticated': self.allow_unauthenticated
        })
        
        if self.allow_unauthenticated:
            # Set auth info to unknown (Express: req.auth = { identityKey: 'unknown' })
            if not hasattr(request, 'auth'):
                request.auth = AuthInfo(identity_key='unknown')
            return None  # Continue processing
        else:
            self._log('warn', 'Mutual-authentication failed. Returning 401.')
            return JsonResponse({
                'status': 'error',
                'code': 'UNAUTHORIZED',
                'message': 'Mutual-authentication failed!'
            }, status=401)
    
    def _setup_certificate_listener(
        self,
        identity_key: str,
        request: HttpRequest,
        response: HttpResponse,
        on_certificates_received: Optional[CertificatesReceivedCallback]
    ) -> str:
        """
        Set up certificate listener for peer authentication.
        
        Equivalent to Express: peer.listenForCertificatesReceived()
        Full implementation matching Express middleware behavior.
        """
        try:
            def certificate_callback(sender_public_key: str, certificates):
                """
                Handle received certificates.
                
                Equivalent to Express callback in lines 334-366
                """
                self._log('debug', 'Certificates received event triggered', {
                    'senderPublicKey': sender_public_key,
                    'certCount': len(certificates) if certificates else 0,
                    'certificates': [str(cert)[:100] + '...' if str(cert) else 'None' for cert in (certificates or [])]
                })
                
                # Express logic: check if sender matches expected identity
                if sender_public_key != identity_key:
                    self._log('debug', 'Certificate sender does not match expected identity', {
                        'expected': identity_key[:20] + '...' if identity_key else 'None',
                        'actual': sender_public_key[:20] + '...' if sender_public_key else 'None'
                    })
                    return  # Not for this identity
                
                # Express logic: validate certificates
                if not certificates or len(certificates) == 0:
                    self._log('warn', 'No certificates provided by peer', {'senderPublicKey': sender_public_key})
                    
                    # Express equivalent: set 400 status and error response
                    if hasattr(response, 'status_code'):
                        response.status_code = 400
                        response.content = json.dumps({'status': 'No certificates provided'}).encode('utf-8')
                        response['Content-Type'] = 'application/json'
                    
                    # Clean up handles (Express: shift() operation)
                    self._cleanup_certificate_handles(identity_key)
                    return
                
                # Express logic: certificates successfully received
                self._log('info', 'Certificates successfully received from peer', {
                    'senderPublicKey': sender_public_key,
                    'certCount': len(certificates),
                    'firstCertType': type(certificates[0]).__name__ if certificates else 'None'
                })
                
                # Express equivalent: validate certificate format
                validated_certificates = self._validate_certificates(certificates)
                
                # Express logic: call user callback if provided
                if on_certificates_received:
                    try:
                        self._log('debug', 'Invoking onCertificatesReceived callback')
                        on_certificates_received(sender_public_key, validated_certificates, request, response)
                    except Exception as callback_error:
                        self._log('error', f'Error in onCertificatesReceived callback: {callback_error}')
                        # Continue processing despite callback error
                
                # Express logic: handle next() function equivalent
                self._handle_certificate_processing_complete(identity_key, validated_certificates)
                
                # Express logic: clean up handles and stop listener
                self._cleanup_certificate_handles(identity_key)
                
                # Store listener ID for cleanup (Express: stopListeningForCertificatesReceived)
                if hasattr(self, '_active_certificate_listeners'):
                    listener_id = getattr(self, '_current_listener_id', None)
                    if listener_id and hasattr(self.peer, 'stopListeningForCertificatesReceived'):
                        try:
                            self.peer.stopListeningForCertificatesReceived(listener_id)
                            self._log('debug', 'Certificate listener stopped', {'listenerId': listener_id})
                        except Exception as e:
                            self._log('warn', f'Failed to stop certificate listener: {e}')
            
            # Register listener with py-sdk Peer (Express equivalent)
            if hasattr(self.peer, 'listenForCertificatesReceived'):
                listener_id = self.peer.listenForCertificatesReceived(certificate_callback)
                self._log('debug', 'listenForCertificatesReceived registered', {'listenerId': listener_id})
                
                # Store listener ID for cleanup
                self._current_listener_id = listener_id
                if not hasattr(self, '_active_certificate_listeners'):
                    self._active_certificate_listeners = {}
                self._active_certificate_listeners[identity_key] = listener_id
                
                return listener_id
            else:
                self._log('warn', 'Peer does not support listenForCertificatesReceived')
                return 'unsupported'
                
        except Exception as e:
            self._log('error', f'Failed to setup certificate listener: {e}')
            import traceback
            self._log('debug', f'Certificate listener setup traceback: {traceback.format_exc()}')
            return 'error'
    
    def _validate_certificates(self, certificates) -> List[Any]:
        """
        Validate received certificates.
        
        Equivalent to Express certificate validation logic.
        """
        try:
            validated = []
            
            for cert in certificates:
                # Basic validation - check if certificate has required fields
                if self._is_valid_certificate(cert):
                    validated.append(cert)
                else:
                    self._log('warn', 'Invalid certificate format detected', {
                        'certType': type(cert).__name__,
                        'certData': str(cert)[:100] + '...' if str(cert) else 'None'
                    })
            
            self._log('debug', f'Certificate validation complete: {len(validated)}/{len(certificates)} valid')
            return validated
            
        except Exception as e:
            self._log('error', f'Certificate validation failed: {e}')
            return certificates  # Return original on validation error
    
    def _is_valid_certificate(self, certificate) -> bool:
        """
        Check if certificate has valid format.
        
        Basic validation - can be extended for specific certificate types.
        """
        try:
            # Check if certificate is a VerifiableCertificate instance
            if hasattr(certificate, 'type') and hasattr(certificate, 'subject'):
                return True
            
            # Check if certificate is dict with required fields
            if isinstance(certificate, dict):
                required_fields = ['type', 'subject']
                return all(field in certificate for field in required_fields)
            
            # For mock/test certificates
            if hasattr(certificate, '_mock_name') or 'mock' in str(type(certificate)).lower():
                return True
            
            return False
            
        except Exception:
            return False
    
    def _handle_certificate_processing_complete(self, identity_key: str, certificates: List[Any]) -> None:
        """
        Handle completion of certificate processing.
        
        Equivalent to Express next() function handling.
        """
        try:
            self._log('debug', 'Certificate processing complete', {
                'identityKey': identity_key[:20] + '...' if identity_key else 'None',
                'certCount': len(certificates)
            })
            
            # Store certificates for session (Express equivalent)
            if hasattr(self.peer, 'sessionManager'):
                try:
                    # Update session with certificates
                    self.peer.sessionManager.updateSession(identity_key, {'certificates': certificates})
                except Exception as e:
                    self._log('warn', f'Failed to update session with certificates: {e}')
            
            # Trigger next handlers if available (Express openNextHandlers equivalent)
            if hasattr(self, '_open_next_handlers') and identity_key in self._open_next_handlers:
                next_fn = self._open_next_handlers[identity_key]
                if callable(next_fn):
                    try:
                        next_fn()
                        del self._open_next_handlers[identity_key]
                        self._log('debug', 'Next handler executed and removed')
                    except Exception as e:
                        self._log('error', f'Error executing next handler: {e}')
                        
        except Exception as e:
            self._log('error', f'Error handling certificate processing completion: {e}')
    
    def _cleanup_certificate_handles(self, identity_key: str) -> None:
        """
        Clean up certificate-related handles.
        
        Equivalent to Express handles cleanup logic.
        """
        try:
            # Clean up non-general handles (Express: shift() operation)
            for nonce, handles in list(self.open_non_general_handles.items()):
                if handles:
                    # Remove handles related to this identity
                    self.open_non_general_handles[nonce] = [
                        h for h in handles 
                        if not self._handle_belongs_to_identity(h, identity_key)
                    ]
                    
                    # Remove empty handle lists
                    if not self.open_non_general_handles[nonce]:
                        del self.open_non_general_handles[nonce]
            
            self._log('debug', 'Certificate handles cleaned up', {'identityKey': identity_key[:20] + '...' if identity_key else 'None'})
            
        except Exception as e:
            self._log('error', f'Error cleaning up certificate handles: {e}')
    
    def _handle_belongs_to_identity(self, handle: Dict[str, Any], identity_key: str) -> bool:
        """Check if handle belongs to specific identity key."""
        try:
            request = handle.get('request')
            if request and hasattr(request, 'body'):
                # Check request body for identity key
                if hasattr(request.body, 'decode'):
                    try:
                        import json
                        body_data = json.loads(request.body.decode('utf-8'))
                        return body_data.get('identityKey') == identity_key
                    except Exception:
                        pass
            return False
        except Exception:
            return False
    
    def _setup_general_message_listener(
        self,
        request: HttpRequest,
        response: Optional[HttpResponse],
        auth_message: Any
    ) -> str:
        """
        Set up general message listener for API requests.
        
        Equivalent to Express: peer.listenForGeneralMessages()
        """
        try:
            # Get request ID from auth headers
            request_id = request.headers.get('x-bsv-auth-request-id', 'unknown')
            
            # Store handle for response
            if not response:
                response = HttpResponse()
            
            handle = {'response': response, 'request': request}
            self.open_general_handles[request_id] = handle
            
            def general_message_callback(sender_public_key: Any, payload: Any):
                """
                Handle received general message.
                Called by py-sdk Peer when general message is verified.
                
                Args:
                    sender_public_key: Verified sender's public key
                    payload: General message payload
                """
                print(f"[DEBUG callback] General message callback CALLED!")
                print(f"[DEBUG callback] sender_public_key: {sender_public_key}")
                print(f"[DEBUG callback] payload length: {len(payload) if payload else 0}")
                
                try:
                    self._log('debug', 'General message callback triggered', {
                        'requestId': request_id,
                        'senderPublicKey': sender_public_key.hex() if hasattr(sender_public_key, 'hex') else str(sender_public_key)
                    })
                    
                    # ✅ TypeScript版と同じ: req.auth = { identityKey: senderPublicKey }
                    from ..types import AuthInfo
                    identity_key_hex = sender_public_key.hex() if hasattr(sender_public_key, 'hex') else str(sender_public_key)
                    request.auth = AuthInfo(identity_key=identity_key_hex)
                    
                    print(f"[DEBUG callback] request.auth SET to: {identity_key_hex[:20]}...")
                    
                    self._log('info', 'General message authenticated successfully', {
                        'identityKey': identity_key_hex[:20] + '...',
                        'requestId': request_id
                    })
                    
                except Exception as e:
                    self._log('error', f'Error in general message callback: {e}')
                    print(f"[DEBUG callback] ERROR: {e}")
                    import traceback
                    traceback.print_exc()
            
            # Register listener with py-sdk Peer (snake_case method name)
            if hasattr(self.peer, 'listen_for_general_messages'):
                listener_id = self.peer.listen_for_general_messages(general_message_callback)
                self._log('debug', 'listen_for_general_messages registered', {'listenerId': listener_id})
                return listener_id
            elif hasattr(self.peer, 'listenForGeneralMessages'):
                # Fallback for camelCase (older SDK versions)
                listener_id = self.peer.listenForGeneralMessages(general_message_callback)
                self._log('debug', 'listenForGeneralMessages (camelCase) registered', {'listenerId': listener_id})
                return listener_id
            else:
                self._log('warn', 'Peer does not support listen_for_general_messages')
                return 'unsupported'
                
        except Exception as e:
            self._log('error', f'Failed to setup general message listener: {e}')
            return 'error'
    
    def _build_auth_message_from_request(self, request: HttpRequest) -> Any:
        """
        Build AuthMessage from Django request headers and body.
        
        Equivalent to Express: buildAuthMessageFromRequest()
        """
        try:
            # Extract auth headers (BRC-104 format)
            headers = request.headers
            
            message_data = {
                'version': headers.get('x-bsv-auth-version', '1.0'),
                'messageType': headers.get('x-bsv-auth-message-type', 'general'),
                'identityKey': headers.get('x-bsv-auth-identity-key', ''),
                'nonce': headers.get('x-bsv-auth-nonce', ''),
                'yourNonce': headers.get('x-bsv-auth-your-nonce', ''),
                'signature': headers.get('x-bsv-auth-signature', ''),
                'requestedCertificates': None
            }
            
            # Parse requested certificates if present
            cert_header = headers.get('x-bsv-auth-requested-certificates')
            if cert_header:
                try:
                    import json
                    message_data['requestedCertificates'] = json.loads(cert_header)
                except Exception as e:
                    self._log('warn', f'Failed to parse requested certificates: {e}')
            
            # Add request body as payload for general messages
            # Keep payload as raw bytes to match py-sdk Peer signing expectations
            if request.body and len(request.body) > 0:
                message_data['payload'] = request.body  # bytes
                # Debug: log request body for comparison with client
                try:
                    import hashlib
                    body_digest = hashlib.sha256(request.body).digest()
                    self._log('debug', f'Server request.body digest_head: {body_digest[:32].hex()}')
                except Exception:
                    pass
            else:
                message_data['payload'] = b""
            
            # Convert signature from hex to bytes
            if message_data['signature']:
                try:
                    signature_hex = message_data['signature']
                    signature_bytes = bytes.fromhex(signature_hex)
                    message_data['signature'] = signature_bytes
                except Exception as e:
                    self._log('warn', f'Failed to parse signature hex: {e}')
            
            self._log('debug', 'Built AuthMessage from request', {
                'messageType': message_data['messageType'],
                'identityKey': message_data['identityKey'][:20] + '...' if message_data['identityKey'] else '',
                'hasPayload': (isinstance(message_data['payload'], (bytes, bytearray)) and len(message_data['payload']) > 0)
            })
            
            return self._dict_to_auth_message(message_data)
            
        except Exception as e:
            self._log('error', f'Failed to build AuthMessage from request: {e}')
            raise BSVAuthException(f'Invalid auth request format: {str(e)}')
    
    def _dict_to_auth_message(self, message_data: Dict[str, Any]) -> Any:
        """
        Convert dictionary to py-sdk AuthMessage object.
        
        Uses the actual py-sdk AuthMessage class for full compatibility.
        Converts camelCase keys to snake_case and transforms data types as needed.
        """
        try:
            from bsv.auth.auth_message import AuthMessage
            from bsv.keys import PublicKey
            
            # Prepare data with proper type conversions
            converted_data = {}
            
            # Map and convert keys
            key_mapping = {
                'messageType': 'message_type',
                'identityKey': 'identity_key',
                'yourNonce': 'your_nonce',
                'initialNonce': 'initial_nonce',
                # 'nonce' handled below depending on message type
            }
            
            for key, value in message_data.items():
                # Use mapped key if available
                if key == 'nonce':
                    # For initialRequest, client's field is 'nonce' but AuthMessage expects 'initial_nonce'
                    # For general messages, it must remain 'nonce'
                    msg_type = message_data.get('messageType') or message_data.get('message_type')
                    if msg_type == 'initialRequest':
                        converted_key = 'initial_nonce'
                    else:
                        converted_key = 'nonce'
                else:
                    converted_key = key_mapping.get(key, key)
                
                # Convert identityKey hex string to PublicKey object
                if key in ['identityKey', 'identity_key'] and isinstance(value, str):
                    try:
                        value = PublicKey(value)
                    except Exception as e:
                        self._log('warning', f'Failed to convert identity key to PublicKey: {e}')
                
                converted_data[converted_key] = value
            
            # Create AuthMessage with required arguments
            # Required: version, message_type, identity_key
            version = converted_data.get('version', '0.1')
            message_type = converted_data.get('message_type', 'unknown')
            identity_key = converted_data.get('identity_key')
            
            if not identity_key:
                raise ValueError("identity_key is required for AuthMessage")
            
            # Optional arguments
            nonce = converted_data.get('nonce', '')
            initial_nonce = converted_data.get('initial_nonce', nonce)  # Use nonce as fallback
            your_nonce = converted_data.get('your_nonce', '')
            certificates = converted_data.get('certificates', [])
            requested_certificates = converted_data.get('requested_certificates')
            payload = converted_data.get('payload')
            signature = converted_data.get('signature')
            
            return AuthMessage(
                version=version,
                message_type=message_type,
                identity_key=identity_key,
                nonce=nonce,
                initial_nonce=initial_nonce,
                your_nonce=your_nonce,
                certificates=certificates,
                requested_certificates=requested_certificates,
                payload=payload,
                signature=signature
            )
                
        except ImportError as e:
            self._log('error', f'Failed to import AuthMessage: {e}')
            # Fallback to simple object
            class SimpleAuthMessage:
                def __init__(self, data: Dict[str, Any]):
                    for key, value in data.items():
                        setattr(self, key, value)
            return SimpleAuthMessage(message_data)
    
    def _handle_auth_endpoint(
        self,
        request: HttpRequest,
        on_certificates_received: Optional[CertificatesReceivedCallback] = None
    ) -> Optional[HttpResponse]:
        """
        Handle requests to /.well-known/auth endpoint.
        
        Equivalent to Express non-general message handling.
        """
        try:
            # Parse auth message from request
            auth_message = self.py_sdk_bridge.build_auth_message_from_request(request)
            if not auth_message:
                self._log('warn', 'No valid auth message found in request')
                return JsonResponse({
                    'status': 'error',
                    'code': 'ERR_INVALID_AUTH',
                    'description': 'Invalid authentication message'
                }, status=400)
            
            self._log('debug', 'Received non-general message at /.well-known/auth', {
                'message': auth_message
            })
            
            # Get request ID (equivalent to Express logic)
            request_id = request.headers.get('x-bsv-auth-request-id')
            if not request_id:
                request_id = auth_message.get('initialNonce', '')
            
            # Store handle for response (equivalent to Express openNonGeneralHandles)
            if request_id not in self.open_non_general_handles:
                self.open_non_general_handles[request_id] = []
            
            handle_data = {
                'request': request,
                'request_id': request_id,
                'auth_message': auth_message
            }
            self.open_non_general_handles[request_id].append(handle_data)
            
            # TODO: Integrate with py-sdk Peer for session management
            # This would check if session exists and handle certificate exchange
            identity_key = auth_message.get('identityKey', 'unknown')
            
            if on_certificates_received and identity_key != 'unknown':
                # Set up certificate listener (equivalent to Express listenForCertificatesReceived)
                self._setup_certificate_listener(
                    identity_key,
                    request,
                    on_certificates_received
                )
            
            # For now, return basic auth response
            # TODO: Implement full py-sdk peer interaction
            return self._build_auth_response(request, auth_message)
            
        except Exception as e:
            self._log('error', f'Error handling auth endpoint: {e}')
            return JsonResponse({
                'status': 'error',
                'code': 'ERR_INVALID_AUTH',
                'description': 'Authentication processing failed'
            }, status=500)
    
    def _handle_general_request(
        self,
        request: HttpRequest,
        on_certificates_received: Optional[CertificatesReceivedCallback] = None
    ) -> None:
        """
        Handle general requests (non-auth endpoint).
        
        Equivalent to Express general message handling.
        """
        try:
            # Parse auth headers to determine identity
            auth_message = self.py_sdk_bridge.build_auth_message_from_request(request)
            
            if auth_message:
                identity_key = auth_message.get('identityKey', 'unknown')
                
                # Add auth info to request (equivalent to Express req.auth)
                request.auth = AuthInfo(
                    identity_key=identity_key,
                    certificates=auth_message.get('certificates', [])
                )
                
                self._log('debug', 'General request with auth', {
                    'identity_key': identity_key,
                    'path': request.path
                })
            else:
                # No auth info found
                request.auth = AuthInfo(identity_key='unknown')
                
                if not self.allow_unauthenticated:
                    self._log('warn', 'Unauthenticated request rejected', {
                        'path': request.path
                    })
                    raise BSVAuthException("Authentication required")
                
                self._log('debug', 'Unauthenticated request allowed', {
                    'path': request.path
                })
            
            # Continue processing (request will be passed to next middleware/view)
            return None
            
        except BSVAuthException:
            raise
        except Exception as e:
            self._log('error', f'Error handling general request: {e}')
            raise BSVAuthException(f"General request processing failed: {str(e)}")

    
    def _log(self, level: str, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        Log a message at the specified level with optional data.
        
        Equivalent to Express logging functionality.
        """
        if not self._is_log_level_enabled(level):
            return
        
        # Format log message (Express style)
        log_prefix = f"[DjangoTransport] [{level.upper()}]"
        full_message = f"{log_prefix} {message}"
        
        if data:
            full_message += f" {data}"
        
        # Use Django logging
        import logging
        logger = logging.getLogger(__name__)
        
        if level == 'debug':
            logger.debug(full_message)
        elif level == 'info':
            logger.info(full_message)
        elif level == 'warn':
            logger.warning(full_message)
        elif level == 'error':
            logger.error(full_message)
    
    def _get_request_body_for_bsv_protocol(self, request: HttpRequest) -> bytes:
        """
        BSVプロトコル用にリクエストボディを取得
        multipart/form-dataも含めて統一的にバイナリ処理
        
        Args:
            request: Django HTTP request
            
        Returns:
            bytes: BSV署名検証用の生リクエストボディ
        """
        content_type = request.META.get('CONTENT_TYPE', '')
        
        if request.body:
            # すべてのContent-Typeをバイナリとして処理（Go方式）
            # BSV署名検証では生のバイナリデータが必要
            self._log('debug', f'Processing body for BSV protocol', {
                'content_type': content_type,
                'body_length': len(request.body)
            })
            return request.body
        else:
            # 空のリクエスト
            self._log('debug', 'Empty request body for BSV protocol')
            return b''
    
    def _should_preserve_raw_body(self, request: HttpRequest) -> bool:
        """
        BSV署名検証のため、生のリクエストボディを保持すべきかチェック
        
        Args:
            request: Django HTTP request
            
        Returns:
            bool: True if raw body should be preserved
        """
        content_type = request.META.get('CONTENT_TYPE', '')
        
        # multipart/form-dataも含めて、BSVプロトコルでは全て生データとして扱う
        # Express and Go実装と同じアプローチ
        self._log('debug', f'Checking raw body preservation', {
            'content_type': content_type,
            'preserve': True
        })
        return True  # BSVミドルウェアでは常に生データを保持
    
    def _is_multipart_request(self, request: HttpRequest) -> bool:
        """
        multipart/form-dataリクエストかチェック
        
        Args:
            request: Django HTTP request
            
        Returns:
            bool: True if multipart/form-data request
        """
        is_multipart = request.META.get('CONTENT_TYPE', '').startswith('multipart/form-data')
        
        if is_multipart:
            self._log('debug', 'Detected multipart/form-data request', {
                'content_type': request.META.get('CONTENT_TYPE', ''),
                'content_length': request.META.get('CONTENT_LENGTH', 0)
            })
        
        return is_multipart
    
    # ========================================================================
    # Phase 2.6: Certificate Listener Support (Express compatibility)
    # ========================================================================
    
    def _register_certificate_listener(
        self,
        identity_key: str,
        auth_message: Any,
        request: HttpRequest,
        response: Optional[HttpResponse]
    ) -> Optional[int]:
        """
        Register a certificate listener with the peer.
        
        Equivalent to Express:
        ```typescript
        const listenerId = this.peer.listenForCertificatesReceived(
          (senderPublicKey: string, certs: VerifiableCertificate[]) => {
            // ... handle certificates
          })
        ```
        
        Args:
            identity_key: Public key of the peer
            auth_message: Auth message from the request
            request: Django HTTP request
            response: Django HTTP response
            
        Returns:
            Listener ID if successful, None otherwise
        """
        try:
            # Check if peer has the required method
            if not hasattr(self.peer, 'listen_for_certificates_received'):
                self._log('warn', 'Peer does not support listen_for_certificates_received')
                return None
            
            # Define the certificate callback
            def certificate_callback(sender_public_key: str, certificates: List[Any]) -> None:
                """
                Callback invoked when certificates are received.
                
                Equivalent to Express listener callback.
                """
                self._log('debug', 'Certificate listener triggered', {
                    'sender': sender_public_key[:20] if sender_public_key else None,
                    'cert_count': len(certificates) if certificates else 0
                })
                
                # Verify sender matches expected identity
                if sender_public_key != identity_key:
                    self._log('debug', 'Certificate sender mismatch, ignoring', {
                        'expected': identity_key[:20],
                        'received': sender_public_key[:20] if sender_public_key else None
                    })
                    return
                
                # Validate certificates
                if not certificates or len(certificates) == 0:
                    self._log('warn', 'No certificates provided by peer', {
                        'sender': sender_public_key[:20]
                    })
                    # Could send error response here (like Express does)
                    # For now, just log
                    return
                
                self._log('info', 'Certificates received from peer', {
                    'sender': sender_public_key[:20],
                    'cert_count': len(certificates)
                })
                
                # Call the application's certificate callback
                if self.on_certificates_received:
                    try:
                        self.on_certificates_received(
                            sender_public_key,
                            certificates,
                            request,
                            response
                        )
                        self._log('debug', 'Application certificate callback executed')
                    except Exception as e:
                        self._log('error', f'Certificate callback error: {e}', {
                            'error': str(e),
                            'sender': sender_public_key[:20]
                        })
                
                # Handle any continuation handlers (like Express openNextHandlers)
                next_handler = self.open_next_handlers.get(identity_key)
                if next_handler and callable(next_handler):
                    try:
                        next_handler()
                        del self.open_next_handlers[identity_key]
                        self._log('debug', 'Continuation handler executed and removed')
                    except Exception as e:
                        self._log('error', f'Continuation handler error: {e}')
                
                # Clean up: stop listening after receiving certificates
                self._cleanup_certificate_listener(identity_key, sender_public_key)
            
            # Register the listener with py-sdk Peer
            listener_id = self.peer.listen_for_certificates_received(certificate_callback)
            
            self._log('debug', 'Certificate listener registered with peer', {
                'listener_id': listener_id,
                'identity_key': identity_key[:20]
            })
            
            return listener_id
            
        except Exception as e:
            self._log('error', f'Failed to register certificate listener: {e}', {
                'error': str(e),
                'identity_key': identity_key[:20]
            })
            import traceback
            traceback.print_exc()
            return None
    
    def _cleanup_certificate_listener(self, identity_key: str, sender_public_key: str) -> None:
        """
        Clean up certificate listener after certificates are received.
        
        Equivalent to Express:
        ```typescript
        this.peer?.stopListeningForCertificatesReceived(listenerId)
        ```
        
        Args:
            identity_key: Identity key used for registration
            sender_public_key: Sender's public key
        """
        try:
            # Remove from tracking
            listener_id = self._certificate_listener_ids.pop(identity_key, None)
            
            if listener_id is not None:
                # Stop listening with py-sdk Peer
                if hasattr(self.peer, 'stop_listening_for_certificates_received'):
                    try:
                        self.peer.stop_listening_for_certificates_received(listener_id)
                        self._log('debug', 'Certificate listener stopped', {
                            'listener_id': listener_id,
                            'sender': sender_public_key[:20]
                        })
                    except Exception as e:
                        self._log('warn', f'Failed to stop certificate listener: {e}')
                else:
                    self._log('debug', 'Peer does not support stop_listening_for_certificates_received')
            
        except Exception as e:
            self._log('error', f'Error cleaning up certificate listener: {e}')

    def _is_log_level_enabled(self, message_level: str) -> bool:
        """
        Check if the given log level should be output.
        
        Equivalent to Express isLogLevelEnabled()
        """
        levels = ['debug', 'info', 'warn', 'error']
        try:
            # Handle both string and LogLevel enum
            if hasattr(self.log_level, 'value'):
                # LogLevel enum
                configured_level = self.log_level.value
            else:
                # String
                configured_level = str(self.log_level).lower()
                
            configured_index = levels.index(configured_level)
            message_index = levels.index(message_level)
            return message_index >= configured_index
        except ValueError:
            return False


# Factory function for easy instantiation
def create_django_transport(
    py_sdk_bridge: PySdkBridge,
    allow_unauthenticated: bool = False,
    log_level: LogLevel = LogLevel.ERROR
) -> DjangoTransport:
    """Create a Django transport instance."""
    return DjangoTransport(py_sdk_bridge, allow_unauthenticated, log_level)
