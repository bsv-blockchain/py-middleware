"""
BSV Middleware Core Library

A framework-agnostic core library for BSV blockchain authentication and payment processing.
Framework-specific adapters are located in examples/<framework>/<framework>_adapter/.

This package provides:
- Core types and interfaces
- py-sdk integration bridge
- Wallet adapters
- Exception definitions

For Django integration, see: examples/django_example/django_adapter/
For FastAPI integration (future), see: examples/fastapi_example/fastapi_adapter/
"""

__version__ = "0.1.0"
__author__ = "BSV Middleware Team"
__email__ = "team@bsv-middleware.com"

# Core exports (framework-agnostic)
from .types import (
    WalletInterface,
    AuthInfo,
    PaymentInfo,
    LogLevel,
    BSVPayment,
)
from .exceptions import (
    BSVAuthException,
    BSVPaymentException,
    BSVServerMisconfiguredException,
)
from .interfaces import (
    TransportInterface,
    SessionManagerInterface,
    MiddlewareInterface,
)

__all__ = [
    # Core types
    "WalletInterface",
    "AuthInfo",
    "PaymentInfo",
    "LogLevel",
    "BSVPayment",
    # Exceptions
    "BSVAuthException",
    "BSVPaymentException",
    "BSVServerMisconfiguredException",
    # Interfaces
    "TransportInterface",
    "SessionManagerInterface",
    "MiddlewareInterface",
]