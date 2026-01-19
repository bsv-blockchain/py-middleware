"""
Django test settings for comprehensive API testing
"""

import sys
from pathlib import Path

# Add paths for imports
BASE_DIR = Path(__file__).resolve().parent.parent
examples_path = BASE_DIR / "examples" / "django_example"
sys.path.insert(0, str(examples_path))

# Basic Django settings
SECRET_KEY = "django-test-secret-key-for-api-testing"
DEBUG = True
ALLOWED_HOSTS = ["*"]

# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

# Applications
INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.messages",
    "myapp",
]

# Middleware
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "bsv_middleware.django.auth_middleware.BSVAuthMiddleware",
]

# URLs
ROOT_URLCONF = "myproject.urls"

# Templates
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Logging - suppress during testing
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "root": {
        "handlers": ["null"],
    },
    "loggers": {
        "bsv_middleware": {
            "handlers": ["null"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}


# BSV Middleware Test Configuration
class TestWallet:
    """Test wallet for API testing"""

    def sign_message(self, message: bytes) -> bytes:
        return b"test_signature_" + message[:10]

    def get_public_key(self) -> str:
        return "033f5aed5f6cfbafaf94570c8cde0c0a6e2b5fb0e07ca40ce1d6f6bdfde1e5b9b8"

    def internalize_action(self, action: dict) -> dict:
        return {
            "accepted": True,
            "satoshisPaid": action.get("satoshis", 0),
            "transactionId": f"test_tx_{action.get('satoshis', 0)}",
        }


def create_test_wallet():
    """Factory function to create a test wallet instance"""
    return TestWallet()


def calculate_test_request_price(request):
    """Test price calculation function"""
    path = request.path
    if path.startswith("/free/") or path in ["/", "/health/", "/public/"]:
        return 0
    elif path.startswith("/protected/"):
        return 500
    elif path.startswith("/premium/"):
        return 1000
    else:
        return 100


def handle_test_certificates_received(
    sender_public_key, certificates, request, response
):
    """Test certificate handler"""


# BSV Middleware Settings
BSV_MIDDLEWARE = {
    "WALLET": TestWallet(),
    "ALLOW_UNAUTHENTICATED": False,
    "CALCULATE_REQUEST_PRICE": calculate_test_request_price,
    "CERTIFICATE_REQUESTS": {
        "certifiers": [
            "033f5aed5f6cfbafaf94570c8cde0c0a6e2b5fb0e07ca40ce1d6f6bdfde1e5b9b8"
        ],
        "types": {"identity-verification": ["name", "address"]},
    },
    "ON_CERTIFICATES_RECEIVED": handle_test_certificates_received,
    "LOG_LEVEL": "error",
}
