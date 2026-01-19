"""
Framework-agnostic interfaces for BSV middleware.

This module defines Protocol interfaces that all framework-specific adapters
(Django, FastAPI, Flask, etc.) should implement. This ensures consistency
across different framework implementations and enables type checking.

All framework adapters must implement these interfaces to be compatible
with the BSV middleware core functionality.
"""

from typing import Any, Callable, Dict, List, Optional, Protocol, runtime_checkable


@runtime_checkable
class TransportInterface(Protocol):
    """
    Framework-agnostic Transport interface.

    All framework-specific transports (DjangoTransport, FastAPITransport, etc.)
    must implement this interface to be compatible with py-sdk Peer.

    This interface defines the contract for handling BSV authentication
    protocol messages over HTTP.
    """

    def handle_incoming_request(
        self,
        request: Any,
        on_certificates_received: Optional[Callable[..., Any]] = None,
        response: Optional[Any] = None,
    ) -> Optional[Any]:
        """
        Handle incoming HTTP request for BSV authentication.

        Args:
            request: Framework-specific request object (e.g., Django HttpRequest)
            on_certificates_received: Optional callback for certificate processing
            response: Optional framework-specific response object

        Returns:
            Framework-specific response object if request should be handled immediately,
            None to continue to next middleware/view
        """
        ...

    def send(self, message: Any) -> Optional[Exception]:
        """
        Send an AuthMessage to the connected Peer.

        This is the core method for py-sdk Transport interface compatibility.

        Args:
            message: AuthMessage to send

        Returns:
            None on success, Exception on failure
        """
        ...

    def on_data(self, callback: Callable[[Any], Optional[Exception]]) -> Optional[Exception]:
        """
        Register callback for incoming data.

        Required by py-sdk Transport interface.

        Args:
            callback: Function to call when data is received,
                     signature: (message) -> Optional[Exception]

        Returns:
            None on success, Exception on failure
        """
        ...

    def set_peer(self, peer: Any) -> None:
        """
        Set the peer instance.

        Args:
            peer: py-sdk Peer instance
        """
        ...


@runtime_checkable
class SessionManagerInterface(Protocol):
    """
    Framework-agnostic Session Manager interface.

    All framework-specific session managers must implement this interface
    for BSV authentication session management.
    """

    def has_session(self, identity_key: str) -> bool:
        """
        Check if a BSV session exists for the given identity key.

        Args:
            identity_key: The BSV identity key (public key hex)

        Returns:
            True if a session exists, False otherwise
        """
        ...

    def create_session(self, identity_key: str, auth_data: Optional[Any] = None) -> None:
        """
        Create a new BSV session for the given identity key.

        Args:
            identity_key: The BSV identity key
            auth_data: Optional additional authentication data
        """
        ...

    def get_session(self, identity_key: str) -> Optional[Any]:
        """
        Get the BSV session data for the given identity key.

        Args:
            identity_key: The BSV identity key

        Returns:
            Session data if exists, None otherwise
        """
        ...

    def update_session(self, identity_key: str, auth_data: Any) -> None:
        """
        Update the BSV session data for the given identity key.

        Args:
            identity_key: The BSV identity key
            auth_data: Updated authentication data
        """
        ...

    def delete_session(self, identity_key: str) -> None:
        """
        Delete the BSV session for the given identity key.

        Args:
            identity_key: The BSV identity key
        """
        ...


@runtime_checkable
class MiddlewareInterface(Protocol):
    """
    Framework-agnostic Middleware interface.

    All framework-specific middleware implementations should follow
    this interface pattern for consistency.
    """

    def process_request(self, request: Any) -> Optional[Any]:
        """
        Process incoming request before view execution.

        Args:
            request: Framework-specific request object

        Returns:
            Framework-specific response object to short-circuit the request,
            or None to continue processing
        """
        ...

    def process_response(self, request: Any, response: Any) -> Any:
        """
        Process response after view execution.

        Args:
            request: Framework-specific request object
            response: Framework-specific response object

        Returns:
            Modified or original response object
        """
        ...


@runtime_checkable
class RequestInterface(Protocol):
    """
    Framework-agnostic Request interface.

    Defines minimum required attributes/methods for HTTP requests
    across different frameworks.
    """

    @property
    def method(self) -> str:
        """HTTP method (GET, POST, etc.)"""
        ...

    @property
    def path(self) -> str:
        """Request path"""
        ...

    @property
    def headers(self) -> Dict[str, str]:
        """Request headers"""
        ...

    @property
    def body(self) -> bytes:
        """Request body as bytes"""
        ...


@runtime_checkable
class ResponseInterface(Protocol):
    """
    Framework-agnostic Response interface.

    Defines minimum required attributes/methods for HTTP responses
    across different frameworks.
    """

    @property
    def status_code(self) -> int:
        """HTTP status code"""
        ...

    @status_code.setter
    def status_code(self, value: int) -> None:
        """Set HTTP status code"""
        ...

    @property
    def content(self) -> bytes:
        """Response content as bytes"""
        ...

    @content.setter
    def content(self, value: bytes) -> None:
        """Set response content"""
        ...


# Type aliases for convenience
CertificateCallback = Callable[[str, List[Any], Any, Any], None]
PriceCalculationCallback = Callable[[Any], int]
AuthCallback = Callable[[Any, Any], Optional[Exception]]


def validate_transport_implementation(transport: Any) -> bool:
    """
    Validate that a transport implementation conforms to TransportInterface.

    Args:
        transport: Transport implementation to validate

    Returns:
        True if valid, False otherwise

    Example:
        >>> from examples.django_example.adapter import DjangoTransport
        >>> transport = DjangoTransport(bridge)
        >>> assert validate_transport_implementation(transport)
    """
    return isinstance(transport, TransportInterface)


def validate_session_manager_implementation(session_manager: Any) -> bool:
    """
    Validate that a session manager implementation conforms to SessionManagerInterface.

    Args:
        session_manager: Session manager implementation to validate

    Returns:
        True if valid, False otherwise

    Example:
    >>> from examples.django_example.adapter import DjangoSessionManager
        >>> session_mgr = DjangoSessionManager(request.session)
        >>> assert validate_session_manager_implementation(session_mgr)
    """
    return isinstance(session_manager, SessionManagerInterface)


def validate_middleware_implementation(middleware: Any) -> bool:
    """
    Validate that a middleware implementation conforms to MiddlewareInterface.

    Args:
        middleware: Middleware implementation to validate

    Returns:
        True if valid, False otherwise
    """
    return isinstance(middleware, MiddlewareInterface)


__all__ = [
    "AuthCallback",
    "CertificateCallback",
    "MiddlewareInterface",
    "PriceCalculationCallback",
    "RequestInterface",
    "ResponseInterface",
    "SessionManagerInterface",
    "TransportInterface",
    "validate_middleware_implementation",
    "validate_session_manager_implementation",
    "validate_transport_implementation",
]
