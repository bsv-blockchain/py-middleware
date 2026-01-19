"""
Exception definitions for BSV Middleware

Django-specific exceptions for BSV authentication and payment processing.
"""

from typing import Any, Dict, Optional

from .types import (
    ERR_INVALID_AUTH,
    ERR_INVALID_DERIVATION_PREFIX,
    ERR_MALFORMED_PAYMENT,
    ERR_PAYMENT_REQUIRED,
    ERR_SERVER_MISCONFIGURED,
)


class BSVMiddlewareException(Exception):
    """Base exception for BSV middleware"""

    def __init__(
        self,
        message: str,
        code: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class BSVAuthException(BSVMiddlewareException):
    """Authentication-related exceptions"""

    def __init__(
        self,
        message: str = "Authentication failed",
        code: str = ERR_INVALID_AUTH,
        status_code: int = 401,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, code, status_code, details)


class BSVPaymentException(BSVMiddlewareException):
    """Payment-related exceptions"""

    def __init__(
        self,
        message: str = "Payment required",
        code: str = ERR_PAYMENT_REQUIRED,
        status_code: int = 402,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message, code, status_code, details)


class BSVPaymentRequiredException(BSVPaymentException):
    """Payment required exception (402)"""

    def __init__(
        self,
        satoshis_required: int,
        derivation_prefix: str,
        message: str = "A BSV payment is required to complete this request",
        details: Optional[Dict[str, Any]] = None,
    ):
        payment_details = {
            "satoshisRequired": satoshis_required,
            "derivationPrefix": derivation_prefix,
            **(details or {}),
        }
        super().__init__(
            message=message,
            code=ERR_PAYMENT_REQUIRED,
            status_code=402,
            details=payment_details,
        )
        self.satoshis_required = satoshis_required
        self.derivation_prefix = derivation_prefix


class BSVMalformedPaymentException(BSVPaymentException):
    """Malformed payment data exception"""

    def __init__(
        self,
        message: str = "The X-BSV-Payment header is not valid JSON",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code=ERR_MALFORMED_PAYMENT,
            status_code=400,
            details=details,
        )


class BSVInvalidDerivationPrefixException(BSVPaymentException):
    """Invalid derivation prefix exception"""

    def __init__(
        self,
        message: str = "The X-BSV-Payment-Derivation-Prefix header is not valid",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code=ERR_INVALID_DERIVATION_PREFIX,
            status_code=400,
            details=details,
        )


class BSVServerMisconfiguredException(BSVMiddlewareException):
    """Server misconfiguration exception"""

    def __init__(
        self,
        message: str = "The server is misconfigured",
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code=ERR_SERVER_MISCONFIGURED,
            status_code=500,
            details=details,
        )
