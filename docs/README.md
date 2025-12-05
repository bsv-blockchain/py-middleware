# BSV Python Middleware Documentation

Welcome to the BSV Python Middleware documentation!

## 📚 Documentation Index

### Core Documentation

- **[API Reference](./API.md)** - Complete API documentation with all classes, protocols, and type definitions
- **[Specification](../BSV_MIDDLEWARE_SPECIFICATION.md)** - Technical specification with architecture diagrams and security analysis

### Getting Started

1. **Installation**
   #todo create pip repo and add the URL

```bash
pip install git+https://github.com/bsv-blockchain/py-sdk.git@feature/auth/certificates-port
pip install -e .
```

2. **Quick Start** - See [README.md](../README.md) for a minimal setup example
3. **Examples**

   - [Django Example](../examples/django_example/) - Complete Django application with BSV auth and payment
   - [Testnet Setup](../examples/testnet_setup/) - Guide for testing on BSV testnet

## 🔍 Quick Reference

### Basic Setup

```python
# settings.py
from bsv.wallet import Wallet

wallet = Wallet(private_key='your-key')

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'examples.django_example.django_adapter.auth_middleware.BSVAuthMiddleware',
    'examples.django_example.django_adapter.payment_middleware.BSVPaymentMiddleware',
]

BSV_MIDDLEWARE = {
    'WALLET': wallet,
    'ALLOW_UNAUTHENTICATED': False,
    'CALCULATE_REQUEST_PRICE': lambda req: 100,
}
```

### Using in Views

```python
# views.py
from django.http import JsonResponse

def protected_view(request):
    if hasattr(request, 'auth') and request.auth.is_authenticated:
        return JsonResponse({
            'user': request.auth.identity_key,
            'message': 'Authenticated!'
        })
    return JsonResponse({'error': 'Unauthorized'}, status=401)

def premium_view(request):
    if hasattr(request, 'payment') and request.payment.is_paid:
        return JsonResponse({
            'content': 'Premium data',
            'paid': request.payment.satoshis_paid
        })
    return JsonResponse({'error': 'Payment required'}, status=402)
```

## 📖 Additional Resources

### Specifications

- [BRC-103: Mutual Authentication](https://github.com/bitcoin-sv/BRCs/blob/master/peer-to-peer/0103.md)
- [BRC-104: HTTP Transport](https://github.com/bitcoin-sv/BRCs/blob/master/peer-to-peer/0104.md)

### Related Projects

- [py-sdk](https://github.com/bsv-blockchain/py-sdk) - Python BSV SDK
- [auth-express-middleware](https://github.com/bitcoin-sv/auth-express-middleware) - TypeScript reference implementation
- [payment-express-middleware](https://github.com/bitcoin-sv/payment-express-middleware) - TypeScript payment middleware

### Test Documentation

- [Test Architecture](../tests/TEST_ARCHITECTURE.md) - Testing strategy and structure
- [Testnet Guide](../tests/testnet/README.md) - Running tests on testnet

## 🆚 Comparison with TypeScript

| Feature             | TypeScript (Express)     | Python (Django)           |
| :------------------ | :----------------------- | :------------------------ |
| Middleware Creation | `createAuthMiddleware()` | `BSVAuthMiddleware` class |
| Transport           | `ExpressTransport`       | `DjangoTransport`         |
| Configuration       | Function options         | Django settings dict      |
| Request Attribute   | `req.auth`               | `request.auth`            |
| Payment Attribute   | `req.payment`            | `request.payment`         |
| API Documentation   | ✅ API.md                | ✅ API.md                 |

See [API Reference](./API.md) for detailed Python-specific documentation.

## 💡 Common Use Cases

### 1. Protected API Endpoints

```python
@require_http_methods(["GET"])
def api_endpoint(request):
    if not hasattr(request, 'auth') or not request.auth.is_authenticated:
        return JsonResponse({'error': 'Unauthorized'}, status=401)
    return JsonResponse({'data': 'protected content'})
```

### 2. Paid Content

```python
def premium_content(request):
    if not hasattr(request, 'payment') or request.payment.satoshis_paid < 500:
        return JsonResponse({'error': 'Payment required'}, status=402)
    return JsonResponse({'content': 'Premium data'})
```

### 3. Certificate-Based Access Control

```python
def age_restricted_content(request):
    if not hasattr(request, 'auth') or not request.auth.certificates:
        return JsonResponse({'error': 'Age verification required'}, status=401)

    for cert in request.auth.certificates:
        if cert.type == 'age-verification' and int(cert.fields.get('age', 0)) >= 18:
            return JsonResponse({'content': 'Age-restricted content'})

    return JsonResponse({'error': 'Age verification failed'}, status=403)
```

## 📝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

## 📄 License

[Open BSV License](../LICENSE.txt)

---

**Documentation Status:** ✅ API Reference Complete | 🚧 Additional guides in development

Last updated: 2025-11-19




