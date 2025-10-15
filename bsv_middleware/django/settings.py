"""
Django Settings Integration for BSV Middleware

This module provides Django settings integration and configuration helpers
for BSV authentication and payment middleware.
"""

from typing import Optional, Dict, Any, Callable
from django.conf import settings as django_settings
from django.core.exceptions import ImproperlyConfigured

from ..types import (
    WalletInterface,
    LogLevel,
    CertificatesReceivedCallback,
    CalculateRequestPriceCallback
)


# ===== BSV Middleware Configuration =====

# Create actual py-sdk wallet for BSV operations
try:
    from bsv.wallet import Wallet
    from bsv.keys import PrivateKey
    
    # Create a test wallet with a private key
    # In production, this would be loaded from secure storage
    test_private_key = PrivateKey.from_wif("L4rK1yDtCWekvXuE6oXD9jCYgFNVsK8osvzUJSEjLHBbiexqjJT")
    actual_wallet = Wallet(test_private_key)
    
    # Create wallet interface that implements WalletInterface
    class PySdkWalletInterface:
        """Wrapper for py-sdk Wallet to implement WalletInterface."""
        
        def __init__(self, wallet: Wallet):
            self.wallet = wallet
        
        def sign_message(self, message: bytes) -> bytes:
            """Sign a message with the wallet."""
            result: bytes = self.wallet.sign_message(message)
            return result
        
        def get_public_key(self) -> str:
            """Get the wallet's public key."""
            result: str = self.wallet.public_key.to_hex()
            return result
        
        def internalize_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
            """Process an action (transaction) with the wallet."""
            # This would use the actual wallet to process the action
            # For now, return a mock result
            return {
                'accepted': True,
                'satoshisPaid': action.get('satoshis', 0),
                'transactionId': 'mock_tx_id'
            }
    
    # Create the wallet interface
    bsv_wallet = PySdkWalletInterface(actual_wallet)
    print(f"✅ Created py-sdk wallet with public key: {bsv_wallet.get_public_key()}")
    
except ImportError as e:
    print(f"⚠️  py-sdk not available, using mock wallet: {e}")
    
    # Fallback to mock wallet
    class MockWallet:
        """Mock wallet for demonstration purposes."""
        
        def sign_message(self, message: bytes) -> bytes:
            """Mock message signing."""
            return b'mock_signature'
        
        def get_public_key(self) -> str:
            """Mock public key."""
            return 'mock_public_key_033f...'
        
        def internalize_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
            """Mock action internalization."""
            return {
                'accepted': True,
                'satoshisPaid': action.get('satoshis', 0),
                'transactionId': 'mock_tx_id_12345'
            }
    
    bsv_wallet: Any = MockWallet()  # type: ignore

# Certificate received callback
def handle_certificates_received(sender_public_key: str, certificates: Any, request: Any, response: Any) -> None:
    """Handle received certificates."""
    print(f"Received {len(certificates)} certificates from {sender_public_key}")
    for cert in certificates:
        print(f"Certificate type: {getattr(cert, 'type', 'unknown')}")

# Price calculation function
def calculate_request_price(request: Any) -> int:
    """Calculate the price for a request."""
    # Free endpoints
    if request.path.startswith('/free/'):
        return 0
    
    # Public endpoints
    if request.path in ['/public/', '/health/', '/']:
        return 0
    
    # Protected endpoints
    if request.path.startswith('/protected/'):
        return 500  # 500 satoshis
    
    # Premium endpoints
    if request.path.startswith('/premium/'):
        return 1000  # 1000 satoshis
    
    # Default price
    return 100  # 100 satoshis

# BSV Middleware Settings
BSV_MIDDLEWARE = {
    # Required: Wallet instance (now using actual py-sdk wallet)
    'WALLET': bsv_wallet,
    
    # Optional: Allow unauthenticated requests (useful for development)
    'ALLOW_UNAUTHENTICATED': True,  # Set to False in production
    
    # Optional: Price calculation function
    'CALCULATE_REQUEST_PRICE': calculate_request_price,
    
    # Optional: Certificate requests
    'CERTIFICATE_REQUESTS': {
        'certifiers': ['example_certifier_pubkey_033f...'],
        'types': {
            'age-verification': ['dateOfBirth', 'country'],
            'identity-verification': ['name', 'address']
        }
    },
    
    # Optional: Certificate received callback
    'ON_CERTIFICATES_RECEIVED': handle_certificates_received,
    
    # Optional: Logging level
    'LOG_LEVEL': 'debug',  # 'debug', 'info', 'warn', 'error'
}

# ===== End BSV Middleware Configuration =====


class BSVMiddlewareSettings:
    """
    BSV Middleware settings manager for Django integration.
    
    This class provides a clean interface for accessing BSV middleware
    configuration from Django settings.
    """
    
    def __init__(self) -> None:
        self._settings = self._load_settings()
    
    def _load_settings(self) -> Dict[str, Any]:
        """Load BSV middleware settings from Django configuration."""
        try:
            return getattr(django_settings, 'BSV_MIDDLEWARE', {})
        except AttributeError:
            return {}
    
    @property
    def wallet(self) -> WalletInterface:
        """Get the configured wallet instance."""
        wallet = self._settings.get('WALLET')
        if not wallet:
            raise ImproperlyConfigured(
                "BSV_MIDDLEWARE['WALLET'] is required. "
                "Please configure a wallet instance in your Django settings."
            )
        result: WalletInterface = wallet
        return result
    
    @property
    def allow_unauthenticated(self) -> bool:
        """Whether to allow unauthenticated requests."""
        result: bool = bool(self._settings.get('ALLOW_UNAUTHENTICATED', False))
        return result
    
    @property
    def calculate_request_price(self) -> CalculateRequestPriceCallback:
        """Get the request price calculation function."""
        price_func = self._settings.get('CALCULATE_REQUEST_PRICE')
        if not price_func:
            # Default to 100 satoshis (same as Express middleware)
            return lambda request: 100
        
        if not callable(price_func):
            raise ImproperlyConfigured(
                "BSV_MIDDLEWARE['CALCULATE_REQUEST_PRICE'] must be a callable function."
            )
        
        result: CalculateRequestPriceCallback = price_func
        return result
    
    @property
    def certificate_requests(self) -> Optional[Dict[str, Any]]:
        """Get certificate request configuration."""
        return self._settings.get('CERTIFICATE_REQUESTS')
    
    @property
    def on_certificates_received(self) -> Optional[CertificatesReceivedCallback]:
        """Get the certificate received callback function."""
        return self._settings.get('ON_CERTIFICATES_RECEIVED')
    
    @property
    def session_manager(self) -> Optional[Any]:
        """Get custom session manager if configured."""
        return self._settings.get('SESSION_MANAGER')
    
    @property
    def logger(self) -> Optional[Any]:
        """Get configured logger."""
        return self._settings.get('LOGGER')
    
    @property
    def log_level(self) -> LogLevel:
        """Get configured log level."""
        level_str = self._settings.get('LOG_LEVEL', 'error')
        try:
            return LogLevel(level_str.lower())
        except ValueError:
            return LogLevel.ERROR
    
    def validate_configuration(self) -> None:
        """
        Validate the BSV middleware configuration.
        
        Raises:
            ImproperlyConfigured: If configuration is invalid
        """
        # Check required settings
        if not self.wallet:
            raise ImproperlyConfigured("BSV_MIDDLEWARE['WALLET'] is required.")
        
        # Validate wallet interface
        required_methods = ['sign_message', 'get_public_key', 'internalize_action']
        for method in required_methods:
            if not hasattr(self.wallet, method):
                raise ImproperlyConfigured(
                    f"BSV_MIDDLEWARE['WALLET'] must implement {method} method."
                )
        
        # Validate price calculation function
        try:
            price_func = self.calculate_request_price
            if not callable(price_func):
                raise ImproperlyConfigured(
                    "BSV_MIDDLEWARE['CALCULATE_REQUEST_PRICE'] must be callable."
                )
        except Exception as e:
            raise ImproperlyConfigured(f"Invalid CALCULATE_REQUEST_PRICE: {e}")
        
        # Validate certificate callback if provided
        if self.on_certificates_received and not callable(self.on_certificates_received):
            raise ImproperlyConfigured(
                "BSV_MIDDLEWARE['ON_CERTIFICATES_RECEIVED'] must be callable."
            )


# Global settings instance
bsv_settings = BSVMiddlewareSettings()


def get_bsv_settings() -> BSVMiddlewareSettings:
    """Get the global BSV middleware settings instance."""
    return bsv_settings


def validate_bsv_configuration() -> None:
    """
    Validate BSV middleware configuration.
    
    This function can be called during Django startup to ensure
    configuration is valid.
    """
    bsv_settings.validate_configuration()


# Django settings template for documentation
BSV_MIDDLEWARE_TEMPLATE = {
    # Required: BSV wallet instance
    'WALLET': None,  # Must be set to a WalletInterface implementation
    
    # Optional: Allow unauthenticated requests (default: False)
    'ALLOW_UNAUTHENTICATED': False,
    
    # Optional: Function to calculate request price in satoshis (default: lambda request: 100)
    'CALCULATE_REQUEST_PRICE': lambda request: 100,
    
    # Optional: Certificate requests configuration
    'CERTIFICATE_REQUESTS': {
        'certifiers': ['<33-byte-pubkey-of-certifier>'],
        'types': {
            'age-verification': ['dateOfBirth', 'country']
        }
    },
    
    # Optional: Callback for when certificates are received
    'ON_CERTIFICATES_RECEIVED': None,  # Function(sender_key, certs, request, response)
    
    # Optional: Custom session manager
    'SESSION_MANAGER': None,
    
    # Optional: Custom logger
    'LOGGER': None,
    
    # Optional: Log level (default: 'error')
    'LOG_LEVEL': 'error',  # 'debug', 'info', 'warn', 'error'
}


def get_settings_template() -> Dict[str, Any]:
    """
    Get a template for BSV middleware settings.
    
    This can be used as a reference for configuring the middleware.
    """
    result: Dict[str, Any] = dict(BSV_MIDDLEWARE_TEMPLATE)
    return result


# Example settings configurations
EXAMPLE_SETTINGS = {
    'minimal': {
        'WALLET': 'YourWalletInstance',  # Replace with actual wallet
    },
    
    'development': {
        'WALLET': 'YourWalletInstance',  # Replace with actual wallet
        'ALLOW_UNAUTHENTICATED': True,
        'CALCULATE_REQUEST_PRICE': lambda request: 0 if request.path.startswith('/free/') else 100,
        'LOG_LEVEL': 'debug',
    },
    
    'production': {
        'WALLET': 'YourWalletInstance',  # Replace with actual wallet
        'ALLOW_UNAUTHENTICATED': False,
        'CALCULATE_REQUEST_PRICE': lambda request: 500,  # Higher price for production
        'CERTIFICATE_REQUESTS': {
            'certifiers': ['production-certifier-pubkey'],
            'types': {
                'age-verification': ['age'],
                'identity-verification': ['name', 'address']
            }
        },
        'LOG_LEVEL': 'warn',
    }
}


def get_example_settings(environment: str = 'minimal') -> Dict[str, Any]:
    """
    Get example settings for different environments.
    
    Args:
        environment: 'minimal', 'development', or 'production'
        
    Returns:
        Example settings dictionary
    """
    if environment not in EXAMPLE_SETTINGS:
        raise ValueError(f"Unknown environment: {environment}")
    
    env_settings: Dict[str, Any] = EXAMPLE_SETTINGS[environment]  # type: ignore
    result: Dict[str, Any] = dict(env_settings)
    return result
