"""
Django Auth Middleware for BSV Authentication

This module provides Django authentication middleware for BSV blockchain,
directly ported from Express createAuthMiddleware() function.
"""

import logging
from typing import Optional

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.deprecation import MiddlewareMixin

from bsv_middleware.exceptions import BSVAuthException, BSVServerMisconfiguredException
from bsv_middleware.py_sdk_bridge import create_py_sdk_bridge
from bsv_middleware.types import (
    AuthMiddlewareOptions,
    LogLevel,
)

from .session_manager import create_django_session_manager
from .transport import create_django_transport

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
            bsv_config = getattr(settings, "BSV_MIDDLEWARE", {})

            # Required configuration - support both direct wallet and lazy getter
            self.wallet = bsv_config.get("WALLET")
            if not self.wallet:
                # Try WALLET_GETTER for lazy initialization
                wallet_getter = bsv_config.get("WALLET_GETTER")
                if callable(wallet_getter):
                    self.wallet = wallet_getter()
                    # Cache it back to settings for future use
                    bsv_config["WALLET"] = self.wallet

            if not self.wallet:
                raise BSVServerMisconfiguredException(
                    "You must configure BSV_MIDDLEWARE with a WALLET or WALLET_GETTER in Django settings."
                )

            # Optional configuration with defaults (equivalent to Express options)
            self.allow_unauthenticated = bsv_config.get("ALLOW_UNAUTHENTICATED", False)
            self.certificates_to_request = bsv_config.get("CERTIFICATE_REQUESTS")
            self.on_certificates_received = bsv_config.get("ON_CERTIFICATES_RECEIVED")
            self.custom_session_manager = bsv_config.get("SESSION_MANAGER")
            self.logger_config = bsv_config.get("LOGGER")
            self.log_level = LogLevel(bsv_config.get("LOG_LEVEL", "error"))

        except Exception as e:
            logger.error(f"Failed to load BSV middleware configuration: {e}")
            raise BSVServerMisconfiguredException(f"Invalid BSV_MIDDLEWARE configuration: {e!s}")

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
                self.py_sdk_bridge, self.allow_unauthenticated, self.log_level
            )

            # Session manager will be created per request (Django sessions are request-based)

            # 🎯 Actual Peer instance creation (Express equivalent)
            try:
                # Adapt wallet to py-sdk compatible format
                from bsv_middleware.wallet_adapter import create_wallet_adapter

                adapted_wallet = create_wallet_adapter(self.wallet)

                # Create session manager (using DefaultSessionManager)
                from bsv.auth.session_manager import DefaultSessionManager

                session_mgr = DefaultSessionManager()

                # Peer instance creation (Express new Peer() equivalent)
                from bsv.auth.peer import Peer, PeerOptions

                peer_options = PeerOptions(
                    wallet=adapted_wallet,
                    transport=self.transport,
                    certificates_to_request=self.certificates_to_request,
                    session_manager=session_mgr,
                    auto_persist_last_session=True,
                    logger=logger,
                )

                self.peer = Peer(peer_options)
                self.transport.set_peer(self.peer)

                # CRITICAL: Start the peer to register message handlers
                self.peer.start()
                logger.info("✅ py-sdk Peer started and integration successful")

            except Exception as e:
                logger.error(f"❌ py-sdk Peer integration failed: {e}")
                # Record error details
                self._log_integration_error(e)
                raise BSVServerMisconfiguredException(f"py-sdk Peer integration failed: {e!s}")

            logger.debug("BSV middleware components initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize BSV middleware components: {e}")
            raise BSVServerMisconfiguredException(f"Component initialization failed: {e!s}")

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """
        Main middleware entry point.

        Equivalent to Express: return (req, res, next) => { ... }
        """
        try:
            logger.debug(f"BSV Auth Middleware processing request: {request.path}")

            # Handle OPTIONS requests (CORS preflight) - bypass authentication
            if request.method == "OPTIONS":
                logger.debug("OPTIONS request detected, returning 204 No Content")
                response = HttpResponse()
                response.status_code = 204
                # Add common CORS headers
                response["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
                # Explicitly list all BSV headers (auth + payment)
                response["Access-Control-Allow-Headers"] = (
                    "Content-Type, Authorization, "
                    "X-Bsv-Auth-Version, X-Bsv-Auth-Message-Type, X-Bsv-Identity, "
                    "X-Bsv-Payment, X-Bsv-Payment-Version, X-Bsv-Payment-Satoshis-Required, "
                    "X-Bsv-Payment-Satoshis-Paid, X-Bsv-Payment-Derivation-Prefix"
                )
                response["Access-Control-Max-Age"] = "86400"  # 24 hours
                return response

            # Handle the request through transport (equivalent to Express transport.handleIncomingRequest)
            response = self.transport.handle_incoming_request(
                request, self.on_certificates_received
            )

            # If transport returned a response, use it (auth endpoint case)
            if response:
                return response

            # Continue to next middleware/view (equivalent to Express next())
            if self.get_response:
                response = self.get_response(request)
                # Call process_response to add auth headers
                return self.process_response(request, response)

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
            # Handle OPTIONS requests (CORS preflight) - bypass authentication
            if request.method == "OPTIONS":
                logger.debug(
                    "OPTIONS request detected in process_request, returning 204 No Content"
                )
                response = HttpResponse()
                response.status_code = 204
                # Add common CORS headers
                response["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
                # Explicitly list all BSV headers (auth + payment)
                response["Access-Control-Allow-Headers"] = (
                    "Content-Type, Authorization, "
                    "X-Bsv-Auth-Version, X-Bsv-Auth-Message-Type, X-Bsv-Identity, "
                    "X-Bsv-Payment, X-Bsv-Payment-Version, X-Bsv-Payment-Satoshis-Required, "
                    "X-Bsv-Payment-Satoshis-Paid, X-Bsv-Payment-Derivation-Prefix"
                )
                response["Access-Control-Max-Age"] = "86400"  # 24 hours
                return response

            # Handle authentication through transport
            response = self.transport.handle_incoming_request(
                request, self.on_certificates_received
            )

            # If transport returned a response, return it to short-circuit the request
            if response:
                return response

            # Ensure request.auth is set for payment middleware
            if not hasattr(request, "auth") or request.auth is None:
                from bsv_middleware.types import AuthInfo

                request.auth = AuthInfo(identity_key="unknown")

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
                BSVServerMisconfiguredException(f"Authentication processing failed: {e!s}")
            )

    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """
        Django middleware process_response hook.

        This is called after the view is executed.
        Adds BRC-104 authentication headers to the response.

        Equivalent to Express: res.set() for auth headers
        """
        try:
            # Debug logging - write to file for visibility
            has_auth = hasattr(request, "auth")
            identity_key = (
                getattr(request.auth, "identity_key", "NO_AUTH") if has_auth else "NO_AUTH_ATTR"
            )
            has_version = request.headers.get("x-bsv-auth-version")

            debug_msg = f"[AUTH MIDDLEWARE process_response] has_auth={has_auth}, identity_key={identity_key[:20] if identity_key else None}..., has_version={has_version}, status={response.status_code}"
            logger.debug(debug_msg)

            # Check if this request has x-bsv-auth headers (general message)
            if not request.headers.get("x-bsv-auth-version"):
                logger.debug(
                    "[AUTH MIDDLEWARE process_response] No x-bsv-auth-version header, skipping"
                )
                return response

            # Check if this is an authenticated request with general message
            if not hasattr(request, "auth") or request.auth.identity_key == "unknown":
                logger.debug(
                    f"[AUTH MIDDLEWARE process_response] Not authenticated (has_auth={has_auth}, identity_key={identity_key}), skipping"
                )
                return response

            # Add auth headers to ALL authenticated responses
            # The client ALWAYS expects auth headers on responses, even for authenticated sessions
            logger.debug(
                "[AUTH MIDDLEWARE process_response] Adding auth headers to authenticated response"
            )
            response = self._add_auth_response_headers(request, response)

            return response

        except Exception as e:
            logger.error(f"Error in process_response: {e}")
            import traceback

            traceback.print_exc()
            return response  # Return original response on error

    def _add_auth_response_headers(
        self, request: HttpRequest, response: HttpResponse
    ) -> HttpResponse:
        """
        Add BRC-104 authentication headers to response.

        This creates a signed response that the client can verify.
        Equivalent to Express transport.send() for general messages.

        Key insight: For signature verification to work, the key_id must be:
        - Server signs with: {server_nonce} {client_session_nonce}
        - Client verifies with: {message.nonce} {session.session_nonce}

        Where:
        - server_nonce = new nonce generated for this response
        - client_session_nonce = client's session nonce (stored as peer_nonce in server's session)
        """
        import base64
        import os

        logger.debug("[_add_auth_response_headers] START - adding auth headers to response")

        try:
            # Get request ID and nonces from incoming request
            request_id = request.headers.get("x-bsv-auth-request-id", "")
            client_request_nonce = request.headers.get(
                "x-bsv-auth-nonce", ""
            )  # Client's fresh request nonce
            client_identity_key = request.headers.get("x-bsv-auth-identity-key", "")

            logger.debug(
                f"[_add_auth_response_headers] client_request_nonce: {client_request_nonce[:20]}..."
            )

            # Generate server nonce for this response
            # CRITICAL: TypeScript Peer.processGeneralMessage (line 822) only verifies message.yourNonce (the echoed client nonce)
            # The server's own nonce (message.nonce) is NOT verified by the client!
            # TypeScript client creates nonces with just Random(32), no HMAC! (Peer.ts line 131)
            # So the server can also use a simple random nonce without HMAC
            import base64
            import os

            server_nonce = base64.b64encode(os.urandom(32)).decode("utf-8")
            logger.debug(
                f"[_add_auth_response_headers] Generated random nonce (no HMAC): {server_nonce[:40]}..."
            )

            # Get server's identity key
            from bsv_middleware.wallet_adapter import create_wallet_adapter

            adapted_wallet = create_wallet_adapter(self.wallet)
            identity_result = adapted_wallet.get_public_key({"identityKey": True}, "auth-response")
            server_identity_key = (
                identity_result.publicKey
                if hasattr(identity_result, "publicKey")
                else str(identity_result)
            )

            # Get client's session nonce from the session
            # This is stored as peer_nonce in the server's session with this client
            client_session_nonce = ""
            try:
                if hasattr(self.transport, "peer") and self.transport.peer:
                    session = self.transport.peer.session_manager.get_session(client_identity_key)
                    if session:
                        # peer_nonce is the client's session nonce
                        client_session_nonce = session.peer_nonce or ""
                        logger.debug(f"Got client session nonce: {client_session_nonce[:20]}...")
            except Exception as e:
                logger.warning(f"Failed to get client session nonce: {e}")

            # Build payload for signing (request_id + status + headers + body)
            response_payload = self._build_response_payload(request_id, response)

            # Sign the response with correct key_id: {server_nonce} {client_session_nonce}
            # This matches what the client expects when verifying
            signature = self._sign_response(
                adapted_wallet,
                response_payload,
                server_nonce,  # First part of key_id
                client_session_nonce,  # Second part of key_id (client's session nonce)
                client_identity_key,
            )

            # Add auth headers to response
            logger.debug("[_add_auth_response_headers] Setting response headers...")
            response["x-bsv-auth-version"] = "0.1"
            response["x-bsv-auth-message-type"] = "general"
            response["x-bsv-auth-identity-key"] = server_identity_key
            response["x-bsv-auth-nonce"] = server_nonce
            # CRITICAL: Echo back the CLIENT's session nonce (from initial handshake)!
            # The client will verify this with verifyNonce(yourNonce, wallet, 'self'),
            # so it MUST be the client's own nonce that they created with counterparty='self'!
            response["x-bsv-auth-your-nonce"] = (
                client_session_nonce  # CLIENT's session nonce from handshake!
            )
            response["x-bsv-auth-signature"] = signature
            response["x-bsv-auth-request-id"] = request_id

            logger.debug(
                f"[_add_auth_response_headers] Setting x-bsv-auth-your-nonce to CLIENT's session nonce: {client_session_nonce[:40] if client_session_nonce else 'NONE'}..."
            )
            logger.debug(
                f"[_add_auth_response_headers] response['x-bsv-auth-your-nonce'] = {response.get('x-bsv-auth-your-nonce', 'NOT SET')[:40] if response.get('x-bsv-auth-your-nonce') else 'NOT SET'}..."
            )
            logger.debug("[_add_auth_response_headers] Headers set! Checking response object...")
            logger.debug(
                f"[_add_auth_response_headers] response['x-bsv-auth-version'] = {response.get('x-bsv-auth-version')}"
            )
            logger.debug(
                f"[_add_auth_response_headers] response['x-bsv-auth-signature'] = {response.get('x-bsv-auth-signature', 'MISSING')[:40]}..."
            )

            logger.debug(
                f"[_add_auth_response_headers] SUCCESS - Added auth headers: nonce={server_nonce[:20]}..., identity={server_identity_key[:20]}..., signature={signature[:40]}..."
            )

            return response

        except Exception as e:
            logger.error(f"[_add_auth_response_headers] EXCEPTION: {e}")
            import traceback

            logger.error(f"[_add_auth_response_headers] Traceback:\n{traceback.format_exc()}")
            traceback.print_exc()
            # Return response without auth headers on error
            return response

    def _build_response_payload(self, request_id: str, response: HttpResponse) -> bytes:
        """Build response payload for signing."""
        import struct

        buf = bytearray()

        # Request ID (32 bytes from base64)
        import base64

        try:
            request_id_bytes = base64.b64decode(request_id)
        except Exception:
            request_id_bytes = b"\x00" * 32
        buf.extend(request_id_bytes[:32].ljust(32, b"\x00"))

        # Status code (varint)
        self._write_varint(buf, response.status_code)

        # Headers count (varint) - we only include x-bsv-* non-auth headers
        included_headers = []
        for key, value in response.items():
            key_lower = key.lower()
            if key_lower.startswith("x-bsv-") and not key_lower.startswith("x-bsv-auth"):
                included_headers.append((key_lower, value))

        self._write_varint(buf, len(included_headers))
        for key, value in sorted(included_headers):
            self._write_string(buf, key)
            self._write_string(buf, value)

        # Body
        content = response.content if hasattr(response, "content") else b""
        if content:
            self._write_varint(buf, len(content))
            buf.extend(content)
        else:
            # -1 for no body
            buf.append(0xFF)
            buf.extend(struct.pack("<Q", 0xFFFFFFFFFFFFFFFF))

        return bytes(buf)

    def _write_varint(self, buf: bytearray, value: int) -> None:
        """Write Bitcoin-style varint."""
        import struct

        if value < 0xFD:
            buf.append(value)
        elif value <= 0xFFFF:
            buf.append(0xFD)
            buf.extend(struct.pack("<H", value))
        elif value <= 0xFFFFFFFF:
            buf.append(0xFE)
            buf.extend(struct.pack("<I", value))
        else:
            buf.append(0xFF)
            buf.extend(struct.pack("<Q", value))

    def _write_string(self, buf: bytearray, s: str) -> None:
        """Write length-prefixed string."""
        b = s.encode("utf-8")
        self._write_varint(buf, len(b))
        buf.extend(b)

    def _sign_response(
        self,
        wallet,
        payload: bytes,
        client_nonce: str,
        server_nonce: str,
        client_identity_key: str,
    ) -> str:
        """Sign the response payload."""
        try:
            # Create signature using wallet
            # Note: Protocol name must only contain letters, numbers and spaces
            sig_result = wallet.create_signature(
                {
                    "protocolID": [2, "auth message signature"],
                    "keyID": f"{client_nonce} {server_nonce}",
                    "counterparty": client_identity_key,
                    "data": list(payload),
                },
                "auth-response",
            )

            if sig_result and hasattr(sig_result, "signature"):
                sig = sig_result.signature
                if isinstance(sig, bytes):
                    return sig.hex()
                elif isinstance(sig, list):
                    return bytes(sig).hex()
                return str(sig)

            return ""

        except Exception as e:
            logger.error(f"Failed to sign response: {e}")
            return ""

    def _log_integration_error(self, error: Exception) -> None:
        """Log integration error details"""
        import traceback
        from datetime import datetime

        error_details = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "component": "BSVAuthMiddleware._initialize_components",
            "phase": "Phase 2.1 Day 2",
            "traceback": traceback.format_exc(),
            "timestamp": datetime.now().isoformat(),
        }

        logger.error(f"py-sdk integration error details: {error_details}")

        # Also record to file (for debugging)
        try:
            import json
            from pathlib import Path

            log_file = Path(__file__).parent.parent.parent / "integration_errors.log"

            with open(log_file, "a") as f:
                f.write(json.dumps(error_details, indent=2) + "\n\n")
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
        from .session_manager import DjangoSessionManagerAdapter

        django_sm = create_django_session_manager(request.session)
        return DjangoSessionManagerAdapter(django_sm)

    def _build_error_response(self, exception: BSVAuthException) -> JsonResponse:
        """
        Build error response from BSV exception.

        Equivalent to Express error responses.
        """
        return JsonResponse(
            {
                "status": "error",
                "code": exception.code,
                "description": exception.message,
                **exception.details,
            },
            status=exception.status_code,
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
    if not hasattr(settings, "BSV_MIDDLEWARE"):
        settings.BSV_MIDDLEWARE = {}

    settings.BSV_MIDDLEWARE.update(
        {
            "WALLET": options.wallet,
            "ALLOW_UNAUTHENTICATED": options.allow_unauthenticated,
            "CERTIFICATE_REQUESTS": options.certificates_to_request,
            "ON_CERTIFICATES_RECEIVED": options.on_certificates_received,
            "SESSION_MANAGER": options.session_manager,
            "LOGGER": options.logger,
            "LOG_LEVEL": options.log_level.value,
        }
    )

    return BSVAuthMiddleware()


# Helper function for certificate handling (equivalent to Express onCertificatesReceived)
def default_certificates_received_handler(
    sender_public_key: str,
    certificates: list,
    request: HttpRequest,
    response: HttpResponse,
) -> None:
    """
    Default certificate received handler.

    Equivalent to Express default onCertificatesReceived behavior.
    """
    logger.info(f"Received {len(certificates)} certificates from {sender_public_key}")

    for cert in certificates:
        logger.debug(f"Processing certificate: {cert}")
        # Add certificate processing logic here
