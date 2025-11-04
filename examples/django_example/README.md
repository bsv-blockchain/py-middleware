# BSV Middleware Django Example

This is a complete Django project demonstrating the use of BSV authentication and payment middleware.

## Features

- **BSV Authentication**: Mutual authentication using BRC-103/104 protocols
- **BSV Payments**: Direct Payment Protocol (DPP) for micro-payments
- **Multiple Endpoint Types**: Free, authenticated, and paid endpoints
- **Certificate Handling**: Support for BSV certificates
- **Django Integration**: Full Django middleware integration

## Quick Start

1. **Install Dependencies**:

   ```bash
   cd py-middleware/examples/django_example
   pip install -r requirements.txt
   ```

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

   # Protected endpoints (require BSV auth/payment)
   curl http://localhost:8000/protected/
   curl http://localhost:8000/premium/
   ```

## Endpoint Overview

| Endpoint            | Access         | Price         | Description                                    |
| ------------------- | -------------- | ------------- | ---------------------------------------------- |
| `/`                 | Free           | 0             | Home page with endpoint overview               |
| `/health/`          | Free           | 0             | Health check endpoint                          |
| `/public/`          | Free           | 0             | Public endpoint (shows auth info if available) |
| `/protected/`       | Auth Required  | 500 satoshis  | Protected endpoint requiring authentication    |
| `/premium/`         | Auth + Payment | 1000 satoshis | Premium endpoint requiring payment             |
| `/.well-known/bsv/auth` | BSV Protocol   | -             | BSV authentication endpoint                    |

## Configuration

The BSV middleware is configured in `myproject/settings.py`:

```python
BSV_MIDDLEWARE = {
    'WALLET': mock_wallet,  # Replace with actual py-sdk wallet
    'ALLOW_UNAUTHENTICATED': True,  # Set to False in production
    'CALCULATE_REQUEST_PRICE': calculate_request_price,
    'CERTIFICATE_REQUESTS': {
        'certifiers': ['example_certifier_pubkey_033f...'],
        'types': {
            'age-verification': ['dateOfBirth', 'country'],
            'identity-verification': ['name', 'address']
        }
    },
    'ON_CERTIFICATES_RECEIVED': handle_certificates_received,
    'LOG_LEVEL': 'debug',
}
```

You can also use the compatibility alias:

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

## Middleware Order

The BSV middleware should be placed after Django's built-in middleware:

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    # BSV Middleware
    'bsv_middleware.django.auth_middleware.BSVAuthMiddleware',
    'bsv_middleware.django.payment_middleware.BSVPaymentMiddleware',
]
```

## Testing with BSV Clients

To test with actual BSV authentication and payments, you'll need:

1. A BSV wallet implementing the py-sdk WalletInterface
2. BSV client software supporting BRC-103/104 protocols
3. Actual BSV transactions for payments

### Example Client Request (with authentication):

```bash
curl -X POST http://localhost:8000/.well-known/bsv/auth \
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

### Example Client Request (with payment):

```bash
curl http://localhost:8000/premium/ \
  -H "x-bsv-auth-identity-key: 033f..." \
  -H "x-bsv-payment: {\"derivationPrefix\":\"abc123\",\"satoshis\":1000,\"transaction\":\"...\"}"
```

## Production Deployment

For production deployment:

1. **Replace Mock Wallet**: Use actual py-sdk wallet implementation
2. **Security Settings**: Set `ALLOW_UNAUTHENTICATED = False`
3. **Price Calculation**: Implement appropriate pricing logic
4. **Certificate Validation**: Add proper certificate validation
5. **Logging**: Configure appropriate log levels
6. **Error Handling**: Add production error handling

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

- Same HTTP headers and protocols
- Same authentication and payment flows
- Same error codes and responses
- Same configuration options

You can use Django and Express BSV applications together in the same ecosystem.

## Mainnet Testing Guide (Django Example)

⚠️ Important: Mainnet uses real BSV and incurs fees. Protect your private keys and follow best practices.

### Prerequisites

- Python virtual environment recommended
- Local editable installs for this repository and `py-sdk` (handled by `requirements.txt`)

### 1) Environment Setup

```bash
cd py-middleware/examples/django_example
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

`requirements.txt` references the local middleware (two levels up) and `py-sdk` (three levels up) in editable mode.

### 2) Create a Mainnet Wallet (first time only)

Create `examples/testnet_setup/mainnet_wallet_config.json` using one of the scripts below:

- Interactive (safer):

```bash
python examples/testnet_setup/create_mainnet_wallet.py
```

- Non-interactive (quick):

```bash
python examples/testnet_setup/quick_create_mainnet_wallet.py
```

The Django mainnet settings will fail to load if this file is missing.

### 3) Run Migrations with Mainnet Settings

```bash
python manage.py migrate --settings=mainnet_settings
```

### 4) Start the Development Server on Mainnet

Either pass the settings module flag:

```bash
python manage.py runserver 0.0.0.0:8000 --settings=mainnet_settings
```

Or set an environment variable:

```bash
export DJANGO_SETTINGS_MODULE=mainnet_settings
python manage.py runserver 0.0.0.0:8000
```

On startup, you'll see logs indicating MAINNET configuration has loaded. Debug is disabled and WhatsOnChain support is enabled.

### 5) Verify Endpoints

- Free endpoints (if `ALLOW_UNAUTHENTICATED=False`, these may return 401; for a quick smoke test, temporarily set `ALLOW_UNAUTHENTICATED=True` in `mainnet_settings.py`):

```bash
curl http://localhost:8000/health/
curl http://localhost:8000/public/
```

- Auth/payment-protected endpoints (will return 401/402 without proper BRC-103/104 auth and payment):

```bash
curl -i http://localhost:8000/protected/
curl -i http://localhost:8000/premium/
```

- BSV auth well-known endpoint (use a BRC-103/104-capable client):

```bash
curl -X POST http://localhost:8000/.well-known/bsv/auth \
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

### Notes and Security

- Mainnet settings live in `examples/django_example/mainnet_settings.py` and the Django settings module name is `mainnet_settings`. They load the wallet from `examples/testnet_setup/mainnet_wallet_config.json`, require authentication, and enable the payment middleware.
- Never commit private keys. The wallet config file should be protected (e.g., file permissions 600).
- Start with small amounts of BSV for testing.
