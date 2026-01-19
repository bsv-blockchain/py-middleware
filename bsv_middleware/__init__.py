"""
BSV Middleware Core Library

A framework-agnostic core library for BSV blockchain authentication and payment processing.
Framework-specific adapters are located in examples/<framework>/<framework>_adapter/.

This package provides:
- Core types and interfaces
- py-sdk integration bridge
- Wallet adapters
- Exception definitions

For Django integration, see: examples/django_example/adapter/
For FastAPI integration (future), see: examples/fastapi_example/fastapi_adapter/
"""

__version__ = "0.1.0"
__author__ = "BSV Middleware Team"
__email__ = "team@bsv-middleware.com"

# Core exports (framework-agnostic)
from .exceptions import (
    BSVAuthException,
    BSVPaymentException,
    BSVServerMisconfiguredException,
)
from .interfaces import (
    MiddlewareInterface,
    SessionManagerInterface,
    TransportInterface,
)
from .types import (
    AuthInfo,
    BSVPayment,
    LogLevel,
    PaymentInfo,
    WalletInterface,
)

__all__ = [
    "AuthInfo",
    "BSVAuthException",
    "BSVPayment",
    "BSVPaymentException",
    "BSVServerMisconfiguredException",
    "LogLevel",
    "MiddlewareInterface",
    "PaymentInfo",
    "SessionManagerInterface",
    "TransportInterface",
    "WalletInterface",
]
