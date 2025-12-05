# BSV Middleware Django Example

This is a complete Django project demonstrating the use of BSV authentication and payment middleware.

## Features

- **BSV Authentication**: Mutual authentication using BRC-103/104 protocols
- **BSV Payments**: Direct Payment Protocol (DPP) for micro-payments
- **Multiple Endpoint Types**: Free, authenticated, and paid endpoints
- **Certificate Handling**: Support for BSV certificates
- **Django Integration**: Full Django middleware integration with adapter layer
- **Decorator Support**: Authentication and payment decorators for views

## Project Structure

```
django_example/
├── adapter/              # Middleware adapter layer
│   ├── auth_middleware.py
│   ├── payment_middleware_complete.py
│   ├── session_manager.py
│   ├── transport.py
│   ├── utils.py
│   └── settings.py
├── myapp/               # Django application
│   ├── views.py        # Endpoint implementations
│   └── urls.py         # URL routing
├── myproject/          # Django project settings
│   └── settings.py     # BSV middleware configuration
├── manage.py
├── requirements.txt    # Dependencies (local dev versions)
└── README.md
```

## Quick Start

1. **Install Dependencies**:

   ```bash
   cd py-middleware/example/django_example
   pip install -r requirements.txt
   ```

   Note: `requirements.txt` references local development versions:

   - `../../` - py-middleware project
   - `../../../py-sdk` - py-sdk project

2. **Run Migrations**:

   ```bash
   python manage.py migrate
   ```

3. **Start Development Server**:

   ```bash
   python manage.py runserver
   ```

4. **Test Endpoints**:

   ```bash
   # Free endpoints
   curl http://localhost:8000/
   curl http://localhost:8000/health/
   curl http://localhost:8000/public/
   curl http://localhost:8000/test/

   # Auth test endpoint
   curl http://localhost:8000/auth-test/

   # Protected endpoints (require BSV auth/payment)
   curl http://localhost:8000/protected/
   curl http://localhost:8000/premium/
   curl http://localhost:8000/hello-bsv/
   ```

## Endpoint Overview

| Endpoint              | Access         | Price         | Description                                    |
| --------------------- | -------------- | ------------- | ---------------------------------------------- |
| `/`                   | Free           | 0             | Home page with endpoint overview               |
| `/health/`            | Free           | 0             | Health check endpoint                          |
| `/public/`            | Free           | 0             | Public endpoint (shows auth info if available) |
| `/test/`              | Free           | 0             | Simple test endpoint                           |
| `/auth-test/`         | Free           | 0             | Shows current auth/payment status              |
| `/protected/`         | Auth Required  | 500 satoshis  | Protected endpoint requiring authentication    |
| `/premium/`           | Auth + Payment | 1000 satoshis | Premium endpoint requiring payment             |
| `/hello-bsv/`         | Auth + Payment | 500 satoshis  | Returns "Hello BSV" with auth + payment        |
| `/decorator-auth/`    | Auth Required  | 0             | Example using @bsv_authenticated_required      |
| `/decorator-payment/` | Auth + Payment | 500 satoshis  | Example using @bsv_payment_required(500)       |
| `/.well-known/auth`   | BSV Protocol   | -             | BSV authentication endpoint                    |

## Configuration

The BSV middleware is configured in `myproject/settings.py`:

```python
# BSV Middleware Settings
BSV_MIDDLEWARE = {
    # Required: Wallet instance
    'WALLET': bsv_wallet,

    # Optional: Allow unauthenticated requests (useful for development)
    'ALLOW_UNAUTHENTICATED': True,  # Set to False in production

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
```

### Price Calculation

The `calculate_request_price` function determines the price for each endpoint:

```python
def calculate_request_price(request):
    """Calculate the price for a request."""
    # Free endpoints
    if request.path in ['/public/', '/health/', '/']:
        return 0

    # Protected endpoints (auth only)
    if request.path.startswith('/protected/'):
        return 500  # 500 satoshis

    # Premium endpoints (auth + payment)
    if request.path.startswith('/premium/'):
        return 1000  # 1000 satoshis

    # Default price
    return 100  # 100 satoshis
```

## Middleware Order

The BSV middleware is added to Django's MIDDLEWARE list in `myproject/settings.py`:

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    # BSV Middleware (via local adapter layer)
    'adapter.auth_middleware.BSVAuthMiddleware',
]
```

Payment middleware is dynamically added via the adapter:

```python
from adapter.payment_middleware_complete import create_payment_middleware

PaymentMiddleware = create_payment_middleware(
    calculate_request_price=calculate_request_price,
    wallet=bsv_wallet
)
MIDDLEWARE.append('myproject.settings.PaymentMiddleware')
```

**Note**: Free endpoints (price = 0) do not require authentication. Protected endpoints automatically enforce authentication requirements.

## Adapter Layer

The `adapter/` directory provides Django-specific implementations:

- **`auth_middleware.py`**: BSV authentication middleware adapter
- **`payment_middleware_complete.py`**: BSV payment middleware implementation
- **`session_manager.py`**: Session management for BSV auth
- **`transport.py`**: HTTP transport layer for BSV protocols
- **`utils.py`**: Helper functions for views (decorators, getters)
- **`settings.py`**: Adapter configuration

## Testing with BSV Clients

To test with actual BSV authentication and payments, you'll need:

1. A BSV wallet implementing the py-sdk WalletInterface
2. BSV client software supporting BRC-103/104 protocols
3. Actual BSV transactions for payments

### Testing Free Endpoints

```bash
# These work without authentication
curl http://localhost:8000/
curl http://localhost:8000/health/
curl http://localhost:8000/test/
curl http://localhost:8000/auth-test/
```

### Testing with Authentication

First, authenticate using the BSV protocol endpoint:

```bash
curl -X POST http://localhost:8000/.well-known/auth \
  -H "Content-Type: application/json" \
  -H "x-bsv-auth-version: 1.0" \
  -H "x-bsv-auth-message-type: initial" \
  -H "x-bsv-auth-identity-key: 033f..." \
  -H "x-bsv-auth-nonce: abc123" \
  -d '{
    "version": "1.0",
    "messageType": "initial",
    "identityKey": "033f...",
    "nonce": "abc123"
  }'
```

Then access protected endpoints with the session:

```bash
curl http://localhost:8000/protected/ \
  -H "Cookie: sessionid=..."
```

### Testing with Payment

```bash
curl http://localhost:8000/premium/ \
  -H "x-bsv-auth-identity-key: 033f..." \
  -H "x-bsv-payment: {\"derivationPrefix\":\"abc123\",\"satoshis\":1000,\"transaction\":\"...\"}"
```

### Using View Helpers

In your views, you can use helper functions from `adapter.utils`:

```python
from adapter.utils import (
    get_identity_key,
    get_certificates,
    is_authenticated_request,
    is_payment_processed,
    get_request_payment_info,
    bsv_authenticated_required,
    bsv_payment_required,
)

# Get auth information
identity_key = get_identity_key(request)
certificates = get_certificates(request)

# Check authentication status
if is_authenticated_request(request):
    # User is authenticated
    pass

# Check payment status
if is_payment_processed(request):
    payment_info = get_request_payment_info(request)
    satoshis = payment_info.satoshis_paid

# Use decorators
@bsv_authenticated_required
def my_view(request):
    # Automatically enforces authentication
    pass

@bsv_payment_required(1000)  # Require 1000 satoshis
def premium_view(request):
    # Automatically enforces payment
    pass
```

## Production Deployment

For production deployment:

1. **Replace Example Wallet**: Use actual py-sdk wallet implementation with real keys
2. **Security Settings**:
   - Set `ALLOW_UNAUTHENTICATED = False`
   - Set `DEBUG = False`
   - Update `SECRET_KEY` to a secure value
   - Configure `ALLOWED_HOSTS` properly
3. **Price Calculation**: Implement appropriate pricing logic for your use case
4. **Certificate Validation**: Add proper certificate validation and verification
5. **Logging**: Configure appropriate log levels (set to 'info' or 'warn')
6. **Error Handling**: Add production error handling and monitoring
7. **Database**: Use PostgreSQL or another production database instead of SQLite
8. **HTTPS**: Deploy behind HTTPS proxy (nginx, etc.)

## Debugging

Enable debug logging to see BSV middleware activity:

```python
LOGGING = {
    'loggers': {
        'bsv_middleware': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}
```

## Express Middleware Compatibility

This Django implementation is designed to be compatible with the Express middleware:

- Same HTTP headers and protocols (BRC-103/104)
- Same authentication and payment flows
- Same error codes and responses (401, 402)
- Same configuration options and structure
- Compatible certificate handling

You can use Django and Express BSV applications together in the same ecosystem.

## Development Notes

### Current Configuration

- **ALLOW_UNAUTHENTICATED**: Currently set to `True` in `settings.py`

  - Set to `False` in production
  - When `True`, authentication headers are optional for free endpoints
  - Protected/paid endpoints always require authentication

- **Price-based Authentication**:

  - Endpoints with price = 0 do NOT require authentication
  - Endpoints with price > 0 REQUIRE authentication
  - This allows public/free endpoints while protecting paid ones

- **Wallet**: Example wallet with mock signing

  - Replace with actual py-sdk wallet for production
  - Current implementation uses `WalletAdapter` for compatibility

- **Database**: SQLite (development only)
  - Will be created automatically on first migration
  - Not included in repository (can be regenerated)

### Troubleshooting

1. **Import errors**: Make sure py-middleware and py-sdk are installed

   ```bash
   pip install -r requirements.txt
   ```

2. **Database errors**: Run migrations

   ```bash
   python manage.py migrate
   ```

3. **401 errors on free endpoints**: Set `ALLOW_UNAUTHENTICATED = True` in settings

4. **Module not found errors**: Check that adapter directory is in Python path
