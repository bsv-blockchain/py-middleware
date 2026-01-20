# bsv-middleware
[![build](https://github.com/bitcoin-sv/py-middleware/actions/workflows/build.yml/badge.svg?branch=master)](https://github.com/bitcoin-sv/py-middleware/actions/workflows/build.yml)
[![PyPI version](https://img.shields.io/pypi/v/bsv-middleware)](https://pypi.org/project/bsv-middleware)
[![Python versions](https://img.shields.io/pypi/pyversions/bsv-middleware)](https://pypi.org/project/bsv-middleware)
[![Coverage](https://img.shields.io/badge/coverage-12%25-red)](https://github.com/bitcoin-sv/py-middleware/actions/workflows/build.yml)

> **🔗 Cross-SDK Interoperability**
>
> This release ensures **cross-SDK interoperability** with [TypeScript SDK](https://github.com/bsv-blockchain/ts-sdk) and [Go SDK](https://github.com/bsv-blockchain/go-sdk) (v2.0.0+).
> Compatible with [wallet-toolbox](https://github.com/bsv-blockchain/wallet-toolbox) v2.0.0+.

A **Django** middleware that implements **BRC-103** [Peer-to-Peer Mutual Authentication](https://github.com/bitcoin-sv/BRCs/blob/master/peer-to-peer/0103.md) via **BRC-104** [HTTP Transport](https://github.com/bitcoin-sv/BRCs/blob/master/peer-to-peer/0104.md). This library makes it easy to **mutually authenticate** and exchange **verifiable certificates** between clients and servers in a standardized way.

By layering **BRC-103** on top of Django, you can:

- Perform a **cryptographic handshake** between two peers (your server and an external wallet/user).  
- Request or respond with **certificates** that verify user identity or attributes.  
- Enforce mutual authentication for your APIs, ensuring that each side proves its identity, without passwords or reliance on centralized authentication providers.  
- Optionally enable **selective disclosure** of certificate fields.

---

## Table of Contents

1. [Background](#background)  
2. [Features](#features)  
3. [Installation](#installation)  
4. [Quick Start](#quick-start)  
5. [Detailed Usage](#detailed-usage)  
   - [Creating the Middleware](#creating-the-middleware)  
   - [Injecting the Middleware into Django](#injecting-the-middleware-into-django)  
   - [Handling Certificates](#handling-certificates)  
   - [Interpreting Authenticated Requests](#interpreting-authenticated-requests)  
6. [API Reference](#api-reference)  
7. [Examples](#examples)  
8. [Security Considerations](#security-considerations)  
9. [Resources & References](#resources--references)  
10. [License](#license)

---

## Background

**BRC-103** is a specification for **mutual authentication** and **certificate exchange** over a **peer-to-peer** channel. It uses nonce-based challenges, digital signatures, and an optional selective disclosure mechanism for certificates. **BRC-104** defines how to transport these messages specifically over **HTTP**, describing custom headers and the `.well-known/auth` endpoint.

**`bsv-middleware`** abstracts the complexities of these specs behind a typical **Django** middleware. It verifies BRC-103/104–compliant requests and properly signs responses, all while letting you continue to write normal Django code for your views.

---

## Features

- **Seamless Integration**  
  Plug straight into your existing Django application—no need for rewriting your entire HTTP handling logic.

- **Mutual Authentication**  
  Authenticates **both** the server and the client cryptographically, preventing impersonation or MITM attacks.

- **Certificate Handling**  
  Request, receive, and verify BRC-103 identity certificates. Includes utility methods to request additional certificates from the client.

- **Selective Disclosure**  
  Supports BRC-103's concept of revealing only certain fields in a certificate, helping to preserve privacy for you and your users while verifying necessary information.

- **Extendable**  
  Provide a custom `SessionManager` or plug in advanced logic for verifying user attributes.

---

## Installation

```bash
pip install bsv-middleware
```

This package depends on [Django](https://www.djangoproject.com/) (3.2+ or 4.x) and a BRC-100–capable wallet (e.g., the `bsv-sdk` implementation or your own code).

---

## Quick Start

Below is the minimal setup to enable BRC-103 mutual authentication in your Django server:

```python
# settings.py
from bsv.wallet import ProtoWallet
from bsv.keys import PrivateKey

# Initialize your BSV wallet (manages keys and signs messages)
private_key = PrivateKey.from_wif('your_private_key_wif')
wallet = ProtoWallet(private_key)

# Configure BSV middleware
BSV_MIDDLEWARE = {
    'WALLET': wallet,
    'ALLOW_UNAUTHENTICATED': False,  # Require mutual auth on every route
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # ... other middleware ...
    
    # BSV Auth Middleware (add after Django's built-in middleware)
    'bsv_middleware.django.auth_middleware.BSVAuthMiddleware',
]
```

```python
# views.py
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

@require_http_methods(["GET"])
def home(request):
    if hasattr(request, 'auth') and request.auth and request.auth.get('identity_key') != 'unknown':
        # The request is authenticated
        return JsonResponse({
            'message': f"Hello, authenticated peer with public key: {request.auth['identity_key']}"
        })
    else:
        # Not authenticated
        return JsonResponse({'error': 'Unauthorized'}, status=401)
```

When the server receives a **BRC-103** handshake or "general" message, `bsv-middleware` automatically handles the cryptographic checks. Once verified, `request.auth['identity_key']` will hold the **public key** of the authenticated peer.

---

## Detailed Usage

### Creating the Middleware

The middleware is configured via Django settings. You can also use the factory function for programmatic setup:

```python
from bsv_middleware.django.auth_middleware import create_auth_middleware
from bsv_middleware.types import AuthMiddlewareOptions
from bsv.wallet import ProtoWallet
from bsv.keys import PrivateKey

private_key = PrivateKey.from_wif('your_private_key_wif')
wallet = ProtoWallet(private_key)

options = AuthMiddlewareOptions(
    wallet=wallet,
    allow_unauthenticated=False
)

# This sets up Django settings and returns the middleware class
BSVAuthMiddleware = create_auth_middleware(options)
```

### Injecting the Middleware into Django

Add the middleware to your `MIDDLEWARE` list in `settings.py`:

```python
MIDDLEWARE = [
    # ... other middleware ...
    'bsv_middleware.django.auth_middleware.BSVAuthMiddleware',
]
```

You can also configure it programmatically if needed:

```python
# In your Django app's ready() method or startup code
from bsv_middleware.django.auth_middleware import BSVAuthMiddleware

# The middleware reads configuration from Django settings
```

### Handling Certificates

To request additional certificates from the client, configure `certificates_to_request` in your settings:

```python
# settings.py
BSV_MIDDLEWARE = {
    'WALLET': wallet,
    'ALLOW_UNAUTHENTICATED': False,
    'CERTIFICATE_REQUESTS': {
        'certifiers': ['<33-byte-pubkey-of-certifier-hex>'],
        'types': {
            'age-verification': ['dateOfBirth', 'country']
        }
    },
    'ON_CERTIFICATES_RECEIVED': on_certificates_received_callback,
}
```

Define your callback function:

```python
def on_certificates_received(sender_public_key: str, certs: list, request, response, next_func):
    """
    Callback invoked when certificates are received from the client.
    
    Args:
        sender_public_key: The public key of the peer sending certificates
        certs: List of certificate objects
        request: Django HttpRequest object
        response: Django HttpResponse object
        next_func: Callable to continue to next middleware/handler
    """
    # You can inspect the provided certificates here
    print(f"Received {len(certs)} certificate(s) from {sender_public_key}.")
    
    # Continue to next middleware or route handler
    if callable(next_func):
        next_func()
```

In your server logic, you can then verify or store these certificates as needed. Replace fields like `age-verification` with an actual base64 certificate type.

### Interpreting Authenticated Requests

Once a peer is authenticated, you'll have:

- `request.auth['identity_key']` ⇒ the authenticated user's **33-byte compressed public key** (hex-encoded).  
- `request.body` ⇒ your normal request body (parsed by Django's request handling).  
- Standard `request.headers` ⇒ includes `x-bsv-auth-*` headers with BRC-103 handshake data (for debugging).  

If `allow_unauthenticated` is **False**, any request without a valid handshake or signature is **rejected** with `401` automatically.

---

## API Reference

### `create_auth_middleware(options: AuthMiddlewareOptions)`

Returns a Django middleware class. **Options**:

- **`wallet`**: (required) A BRC-100 object implementing your signing and verification logic (e.g., `ProtoWallet` from `bsv-sdk`).  
- **`session_manager`**: (optional) Manage nonces & state across requests.  
- **`allow_unauthenticated`**: (optional) If `True`, non-authenticated requests are allowed but marked as `identity_key: 'unknown'`.  
- **`certificates_to_request`**: (optional) Automatic certificate request data structure.  
- **`on_certificates_received`**: (optional) A callback triggered when certs arrive from the client.

### Configuration via Django Settings

Alternatively, configure via `settings.py`:

```python
BSV_MIDDLEWARE = {
    'WALLET': wallet,  # or 'WALLET_GETTER': callable that returns wallet
    'ALLOW_UNAUTHENTICATED': False,
    'CERTIFICATE_REQUESTS': {...},
    'ON_CERTIFICATES_RECEIVED': callback_function,
    'SESSION_MANAGER': custom_session_manager,  # optional
    'LOG_LEVEL': 'error',  # 'debug', 'info', 'warning', 'error'
}
```

---

## Examples

### 1. Minimal Setup

```python
# settings.py
from bsv.wallet import ProtoWallet
from bsv.keys import PrivateKey

private_key = PrivateKey.from_wif('your_private_key_wif')
wallet = ProtoWallet(private_key)

BSV_MIDDLEWARE = {
    'WALLET': wallet,
    'ALLOW_UNAUTHENTICATED': False,
}

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'bsv_middleware.django.auth_middleware.BSVAuthMiddleware',
]
```

```python
# views.py
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

@require_http_methods(["GET"])
def protected(request):
    if hasattr(request, 'auth') and request.auth and request.auth.get('identity_key') != 'unknown':
        return JsonResponse({'message': 'You are authenticated via BRC-103!'})
    return JsonResponse({'error': 'Unauthorized'}, status=401)
```

### 2. Requesting Certificates at Handshake

```python
# settings.py
def on_certificates_received(sender_public_key: str, certs: list, request, response, next_func):
    print(f"Received certs from {sender_public_key}", certs)
    if callable(next_func):
        next_func()

BSV_MIDDLEWARE = {
    'WALLET': wallet,
    'ALLOW_UNAUTHENTICATED': False,
    'CERTIFICATE_REQUESTS': {
        'certifiers': ['<certifier-pubkey-hex>'],
        'types': {
            'someCertificateType': ['fieldA', 'fieldB']
        }
    },
    'ON_CERTIFICATES_RECEIVED': on_certificates_received,
}
```

### 3. Complete Django Example

See the [examples/django_example](./examples/django_example) directory for a complete working Django project demonstrating:

- Authentication middleware setup
- Payment middleware integration
- Multiple endpoint types (free, authenticated, paid)
- Certificate handling
- View decorators for authentication and payments

---

## Security Considerations

1. **TLS Encryption**: Although BRC-103 messages are authenticated, the protocol does **not** encrypt the entire payload. It's recommended to serve your Django app over **HTTPS** to maintain confidentiality.  
2. **Nonce Replay Prevention**: This library implements a `SessionManager` that automatically rejects nonces not bound by the server's private key.  
3. **Transport-Only**: BRC-104's HTTP specification focuses on message authenticity, not on anonymizing request metadata.  
4. **Certificate Revocation**: BRC-103 allows for revocation references (`revocationOutpoint`). Ensure your app checks the blockchain or an appropriate certificate revocation overlay service if you require strict revocation handling.
5. **Private Key Security**: Store your wallet's private key securely. Never commit private keys to version control. Consider using environment variables or Django's secret management.

---

## Resources & References

- [BRC-103 Spec](https://github.com/bitcoin-sv/BRCs/blob/master/peer-to-peer/0103.md) – Mutual authentication & certificate exchange.  
- [BRC-104 Spec](https://github.com/bitcoin-sv/BRCs/blob/master/peer-to-peer/0104.md) – HTTP Transport for BRC-103.  
- [bsv-sdk](https://github.com/bsv-blockchain/py-sdk) – BSV Python SDK (used for cryptographic utilities, wallet logic, etc.).  
- [Django](https://www.djangoproject.com/) – Web framework for Python.

---

## License

[Open BSV License](./LICENSE.txt)

---

**Happy hacking!** If you have questions, suggestions, or want to contribute improvements, feel free to open an issue or PR in our [repository](https://github.com/bitcoin-sv/py-middleware).

