"""
Test settings for BSV middleware tests.
"""

import os
from pathlib import Path

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Basic Django settings for testing
SECRET_KEY = 'test-key-not-for-production'
DEBUG = True
ALLOWED_HOSTS = ['testserver', 'localhost', '127.0.0.1']

# Minimal installed apps for testing
INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'bsv_middleware',
]

# Test middleware configuration
MIDDLEWARE = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'bsv_middleware.django.auth_middleware.BSVAuthMiddleware',
    'bsv_middleware.django.payment_middleware.BSVPaymentMiddleware',
]

# Test database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    }
}

# Other required settings
USE_TZ = True
ROOT_URLCONF = 'tests.urls'

# Mock wallet for testing
class MockTestWallet:
    """Mock wallet for testing purposes."""
    
    def sign_message(self, message: bytes) -> bytes:
        return b'test_signature'
    
    def get_public_key(self) -> str:
        # Valid 33-byte compressed public key in hex format
        return '02e46dcd7991e5a4bd642739249b0158312e1aee56a60fd1bf622172ffe65bd789'
    
    def internalize_action(self, action: dict) -> dict:
        return {
            'accepted': True,
            'satoshisPaid': action.get('satoshis', 0),
            'transactionId': 'test_tx_id'
        }

# BSV Middleware test configuration
BSV_MIDDLEWARE = {
    'WALLET': MockTestWallet(),
    'ALLOW_UNAUTHENTICATED': True,
    'CALCULATE_REQUEST_PRICE': lambda request: 100,
    'LOG_LEVEL': 'debug',
}
