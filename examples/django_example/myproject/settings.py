"""
Django settings for BSV middleware example project.

This example demonstrates how to configure BSV authentication and payment
middleware in a Django application.
"""

import os
from pathlib import Path
from typing import Dict, Any

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-example-key-do-not-use-in-production'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'myapp',  # Our example app
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # BSV Middleware (add after Django's built-in middleware)
    'bsv_middleware.django.auth_middleware.BSVAuthMiddleware',
]

ROOT_URLCONF = 'myproject.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'myproject.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Logging configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'bsv_middleware': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}


# ===== BSV Middleware Configuration =====

# Create BSV wallet for operations
try:
    # Try to use actual py-sdk components
    print("[INFO] Attempting to create py-sdk wallet...")
    
    # Use WalletAdapter to make any wallet compatible
    from bsv_middleware.wallet_adapter import create_wallet_adapter
    
    # Simple wallet for examples - in production use actual py-sdk wallet
    class ExampleWallet:
        """Example wallet for demonstration."""
        
        def sign_message(self, message: bytes) -> bytes:
            return b'example_signature_' + message[:10]
        
        def get_public_key(self) -> str:
            return '033f5aed5f6cfbafaf94570c8cde0c0a6e2b5fb0e07ca40ce1d6f6bdfde1e5b9b8'
        
        def internalize_action(self, action: dict) -> dict:
            """Process payment action."""
            return {
                'accepted': True,
                'satoshisPaid': action.get('satoshis', 0),
                'transactionId': f"example_tx_{action.get('satoshis', 0)}"
            }
    
    # Create adapted wallet that works with py-sdk interfaces
    base_wallet = ExampleWallet()
    bsv_wallet = create_wallet_adapter(base_wallet)
    print(f"[OK] Created adapted wallet with public key: {base_wallet.get_public_key()}")
    
except Exception as e:
    print(f"[WARN] Using fallback mock wallet: {e}")
    
    # Fallback mock wallet
    class MockWallet:
        """Mock wallet for demonstration purposes."""
        
        def sign_message(self, message: bytes) -> bytes:
            return b'mock_signature'
        
        def get_public_key(self) -> str:
            return 'mock_public_key_033f5aed5f6cfbafaf94570c8cde0c0a6e2b5fb0e07ca40ce1d6f6bdfde1e5b9b8'
        
        def internalize_action(self, action: dict) -> dict:
            return {
                'accepted': True,
                'satoshisPaid': action.get('satoshis', 0),
                'transactionId': 'mock_tx_id'
            }
    
    bsv_wallet = MockWallet()

# Certificate received callback
def handle_certificates_received(sender_public_key, certificates, request, response):
    """Handle received certificates."""
    print(f"Received {len(certificates)} certificates from {sender_public_key}")
    for cert in certificates:
        print(f"Certificate type: {getattr(cert, 'type', 'unknown')}")

# Price calculation function
def calculate_request_price(request):
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

# BSV Middleware Settings (Phase 2.3 Compatible)
BSV_MIDDLEWARE = {
    # Required: Wallet instance
    'WALLET': bsv_wallet,
    
    # Optional: Allow unauthenticated requests (useful for development)
    'ALLOW_UNAUTHENTICATED': False,  # Set to False in production
    
    # Optional: Price calculation function
    'CALCULATE_REQUEST_PRICE': calculate_request_price,
    
    # Optional: Certificate requests
    'CERTIFICATE_REQUESTS': {
        'certifiers': ['033f5aed5f6cfbafaf94570c8cde0c0a6e2b5fb0e07ca40ce1d6f6bdfde1e5b9b8'],
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

# Create Payment Middleware using Phase 2.3 implementation
try:
    from django_adapter.payment_middleware_complete import create_payment_middleware
    
    # Create payment middleware with our settings
    PaymentMiddleware = create_payment_middleware(
        calculate_request_price=calculate_request_price,
        wallet=bsv_wallet
    )
    
    # Add payment middleware to MIDDLEWARE list
    MIDDLEWARE.append('myproject.settings.PaymentMiddleware')
    print("[OK] Payment middleware configured successfully")
    
except Exception as e:
    print(f"[WARN] Payment middleware configuration failed: {e}")
    print("   Authentication-only mode will be used")

# ===== End BSV Middleware Configuration =====
