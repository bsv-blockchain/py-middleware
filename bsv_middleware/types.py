"""
Type definitions for BSV Middleware

Pythonic implementation with Express middleware compatibility.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol, Union

from django.http import HttpRequest, HttpResponse


class LogLevel(str, Enum):
    """Log levels for BSV middleware"""

    DEBUG = "debug"
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


# Type aliases
PubKeyHex = str

# HTTP Headers (module-level constants - more Pythonic)
BSV_AUTH_PREFIX = "x-bsv-auth-"
BSV_PAYMENT_HEADER = "x-bsv-payment"
BSV_PAYMENT_VERSION_HEADER = "x-bsv-payment-version"
BSV_PAYMENT_SATOSHIS_REQUIRED_HEADER = "x-bsv-payment-satoshis-required"
BSV_PAYMENT_DERIVATION_PREFIX_HEADER = "x-bsv-payment-derivation-prefix"
BSV_PAYMENT_SATOSHIS_PAID_HEADER = "x-bsv-payment-satoshis-paid"

# Error codes (module-level constants - more Pythonic)
ERR_INVALID_AUTH = "ERR_INVALID_AUTH"
ERR_MISSING_CERTIFICATES = "ERR_MISSING_CERTIFICATES"
ERR_PAYMENT_REQUIRED = "ERR_PAYMENT_REQUIRED"
ERR_PAYMENT_INTERNAL = "ERR_PAYMENT_INTERNAL"
ERR_MALFORMED_PAYMENT = "ERR_MALFORMED_PAYMENT"
ERR_INVALID_DERIVATION_PREFIX = "ERR_INVALID_DERIVATION_PREFIX"
ERR_SERVER_MISCONFIGURED = "ERR_SERVER_MISCONFIGURED"


@dataclass
class AuthInfo:
    """Authentication information for BSV requests"""

    identity_key: str = "unknown"
    certificates: Optional[List[Any]] = None

    @property
    def is_authenticated(self) -> bool:
        """Check if request is authenticated"""
        return self.identity_key != "unknown"

    @property
    def has_certificates(self) -> bool:
        """Check if certificates are available"""
        return bool(self.certificates)


@dataclass
class PaymentInfo:
    """Payment information for BSV requests"""

    satoshis_paid: int = 0
    accepted: bool = False
    transaction_id: Optional[str] = None
    derivation_prefix: Optional[str] = None

    @property
    def is_paid(self) -> bool:
        """Check if payment was successfully processed"""
        return self.satoshis_paid > 0 and self.accepted

    @property
    def is_free(self) -> bool:
        """Check if this is a free request"""
        return self.satoshis_paid == 0


@dataclass
class BSVPayment:
    """BSV payment data structure

    Compatible with Express/Go BSVPayment interface:
    - derivationPrefix: string
    - derivationSuffix: string
    - transaction: base64 encoded transaction
    """

    derivation_prefix: str
    derivation_suffix: str = ""
    satoshis: int = 0
    transaction: Optional[str] = None  # base64 encoded transaction
    sender_identity_key: Optional[str] = None  # For internalize_action

    def __post_init__(self) -> None:
        """Validate payment data after initialization"""
        if self.satoshis < 0:
            raise ValueError("satoshis cannot be negative")
        if not self.derivation_prefix:
            raise ValueError("derivation_prefix is required")


class WalletInterface(Protocol):
    """Protocol for BSV wallet implementations"""

    def sign_message(self, message: bytes) -> bytes:
        """Sign a message with the wallet"""
        ...

    def get_public_key(self) -> str:
        """Get the wallet's public key"""
        ...

    def internalize_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Process an action (transaction) with the wallet"""
        ...


class SessionManagerInterface(Protocol):
    """Protocol for session managers"""

    def has_session(self, identity_key: str) -> bool:
        """Check if a session exists for the identity key"""
        ...


# Type aliases for callbacks
CertificatesReceivedCallback = Callable[[str, List[Any], HttpRequest, HttpResponse], None]

CalculateRequestPriceCallback = Callable[[HttpRequest], Union[int, float]]


@dataclass
class AuthMiddlewareOptions:
    """Configuration options for authentication middleware"""

    wallet: WalletInterface
    session_manager: Optional[SessionManagerInterface] = None
    allow_unauthenticated: bool = False
    certificates_to_request: Optional[Dict[str, Any]] = None
    on_certificates_received: Optional[CertificatesReceivedCallback] = None
    logger: Optional[Any] = None
    log_level: LogLevel = LogLevel.INFO

    def __post_init__(self) -> None:
        """Validate configuration after initialization"""
        if not hasattr(self.wallet, "sign_message"):
            raise ValueError("wallet must implement WalletInterface")


@dataclass
class PaymentMiddlewareOptions:
    """Configuration options for payment middleware"""

    wallet: WalletInterface
    calculate_request_price: CalculateRequestPriceCallback

    def __post_init__(self) -> None:
        """Validate configuration after initialization"""
        if not callable(self.calculate_request_price):
            raise ValueError("calculate_request_price must be callable")


# Legacy compatibility - keeping old class names for backwards compatibility
class BSVHeaders:
    """BSV-specific HTTP headers (legacy compatibility)"""

    AUTH_PREFIX = BSV_AUTH_PREFIX
    PAYMENT = BSV_PAYMENT_HEADER
    PAYMENT_VERSION = BSV_PAYMENT_VERSION_HEADER
    PAYMENT_SATOSHIS_REQUIRED = BSV_PAYMENT_SATOSHIS_REQUIRED_HEADER
    PAYMENT_DERIVATION_PREFIX = BSV_PAYMENT_DERIVATION_PREFIX_HEADER
    PAYMENT_SATOSHIS_PAID = BSV_PAYMENT_SATOSHIS_PAID_HEADER


class BSVErrorCodes:
    """BSV middleware error codes (legacy compatibility)"""

    ERR_INVALID_AUTH = ERR_INVALID_AUTH
    ERR_MISSING_CERTIFICATES = ERR_MISSING_CERTIFICATES
    ERR_PAYMENT_REQUIRED = ERR_PAYMENT_REQUIRED
    ERR_PAYMENT_INTERNAL = ERR_PAYMENT_INTERNAL
    ERR_MALFORMED_PAYMENT = ERR_MALFORMED_PAYMENT
    ERR_INVALID_DERIVATION_PREFIX = ERR_INVALID_DERIVATION_PREFIX
    ERR_SERVER_MISCONFIGURED = ERR_SERVER_MISCONFIGURED
