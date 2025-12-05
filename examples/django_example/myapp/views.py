"""
Views for BSV middleware example.

This module demonstrates different types of endpoints with BSV authentication
and payment requirements.
"""

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

# Simple test view first
def simple_test(request):
    """Simple test view to verify Django is working."""
    return JsonResponse({
        'message': 'Django is working!',
        'path': request.path,
        'method': request.method
    })

# BSV middleware imports - Phase 2.3 Compatible
from examples.django_example.adapter.utils import (
    get_identity_key,
    get_certificates,
    is_authenticated_request,
    is_payment_processed,
    get_request_payment_info,
    format_satoshis,
    bsv_authenticated_required,
    bsv_payment_required,
    debug_request_info,
)


@require_http_methods(["GET"])
def home(request):
    """Home page - free access."""
    return JsonResponse({
        'message': 'Welcome to BSV Middleware Example',
        'endpoints': {
            '/': 'This home page (free)',
            '/health/': 'Health check (free)',
            '/public/': 'Public endpoint (free)',
            '/protected/': 'Protected endpoint (requires auth)',
            '/premium/': 'Premium endpoint (requires payment)',
            '/.well-known/auth': 'BSV auth endpoint'
        },
        'identity_key': get_identity_key(request) or 'unknown',
        'authenticated': is_authenticated_request(request),
        'payment_processed': is_payment_processed(request)
    })


@require_http_methods(["GET"])
def health(request):
    """Health check endpoint - free access."""
    return JsonResponse({
        'status': 'healthy',
        'service': 'BSV Middleware Example',
        'identity_key': 'unknown' # get_identity_key(request) # Temporarily disabled
    })


@require_http_methods(["GET"])
def public_endpoint(request):
    """Public endpoint - free access but shows auth info if available."""
    identity_key = 'unknown' # get_identity_key(request) # Temporarily disabled
    certificates = [] # get_certificates(request) # Temporarily disabled
    
    return JsonResponse({
        'message': 'This is a public endpoint',
        'access': 'free',
        'identity_key': identity_key,
        'authenticated': identity_key != 'unknown',
        'certificates_count': len(certificates),
        'certificates': [str(cert) for cert in certificates] if certificates else []
    })


@require_http_methods(["GET"])
def protected_endpoint(request):
    """Protected endpoint - requires BSV authentication."""
    identity_key = get_identity_key(request) or 'unknown'
    certificates = get_certificates(request)
    
    # Check if authenticated
    if not is_authenticated_request(request):
        return JsonResponse({
            'error': 'Authentication required',
            'message': 'This endpoint requires BSV authentication',
            'identity_key': identity_key
        }, status=401)
    
    return JsonResponse({
        'message': f'Hello, authenticated user!',
        'identity_key': identity_key,
        'access': 'authenticated',
        'certificates_count': len(certificates),
        'endpoint_info': {
            'price': '500 satoshis',
            'requires_auth': True,
            'requires_payment': True
        }
    })


@require_http_methods(["GET"])
def premium_endpoint(request):
    """Premium endpoint - requires BSV authentication and payment."""
    identity_key = get_identity_key(request) or 'unknown'
    payment_info = get_request_payment_info(request)
    
    # Check authentication
    if not is_authenticated_request(request):
        return JsonResponse({
            'error': 'Authentication required',
            'message': 'This premium endpoint requires BSV authentication',
            'identity_key': identity_key
        }, status=401)
    
    # Check payment
    if not is_payment_processed(request) or (payment_info and payment_info.satoshis_paid < 1000):
        return JsonResponse({
            'error': 'Payment required',
            'message': 'This premium endpoint requires payment of 1000 satoshis',
            'required_payment': '1000 satoshis',
            'paid_amount': format_satoshis(payment_info.satoshis_paid if payment_info else 0)
        }, status=402)
    
    return JsonResponse({
        'message': 'Welcome to the premium endpoint!',
        'identity_key': identity_key,
        'access': 'premium',
        'payment_info': {
            'satoshis_paid': payment_info.satoshis_paid if payment_info else 0,
            'accepted': payment_info.accepted if payment_info else False,
            'transaction_id': payment_info.transaction_id if payment_info else None
        },
        'premium_data': {
            'special_content': 'This is premium content only available to paying users',
            'data_quality': 'high',
            'update_frequency': 'real-time'
        }
    })


@require_http_methods(["GET", "POST"])
@csrf_exempt
def auth_test(request):
    """Test endpoint to show current auth status."""
    identity_key = get_identity_key(request) or 'unknown'
    certificates = get_certificates(request)
    payment_info = get_request_payment_info(request)
    
    response_data = {
        'method': request.method,
        'path': request.path,
        'identity_key': identity_key,
        'authenticated': is_authenticated_request(request),
        'certificates': {
            'count': len(certificates),
            'certificates': [str(cert) for cert in certificates] if certificates else []
        },
        'payment': {
            'processed': is_payment_processed(request),
            'satoshis_paid': payment_info.satoshis_paid if payment_info else 0,
            'accepted': payment_info.accepted if payment_info else False,
            'transaction_id': payment_info.transaction_id if payment_info else None
        } if payment_info else None,
        'headers': {
            'bsv_headers': {
                key: value for key, value in request.headers.items() 
                if key.lower().startswith('x-bsv-')
            }
        }
    }
    
    return JsonResponse(response_data)


# Example using decorators
@require_http_methods(["GET"])
@bsv_authenticated_required
def decorator_auth_example(request):
    """Example endpoint using authentication decorator."""
    return JsonResponse({
        'message': 'This endpoint uses the @bsv_authenticated_required decorator',
        'identity_key': get_identity_key(request) or 'unknown'
    })


@require_http_methods(["GET"])
@bsv_payment_required(500)
def decorator_payment_example(request):
    """Example endpoint using payment decorator."""
    payment_info = get_request_payment_info(request)
    
    return JsonResponse({
        'message': 'This endpoint uses the @bsv_payment_required(500) decorator',
        'identity_key': get_identity_key(request) or 'unknown',
        'payment_info': {
            'satoshis_paid': payment_info.satoshis_paid if payment_info else 0,
            'required': 500
        }
    })


@require_http_methods(["GET", "POST"])
@csrf_exempt
def bsv_auth_wellknown(request):
    """
    /.well-known/auth endpoint
    
    Endpoint for BSV authentication protocol.
    This view is normally not reached as AuthMiddleware handles it.
    
    Note: Bypasses CSRF checks (not needed for BSV auth protocol)
    """
    return JsonResponse({
        'service': 'BSV Authentication',
        'version': '0.1',
        'message': 'This endpoint is handled by BSVAuthMiddleware'
    })


@require_http_methods(["GET"])
def hello_bsv_endpoint(request):
    """
    Hello BSV endpoint
    
    Returns "Hello BSV" when both authentication and payment succeed.
    Simple endpoint for testing purposes.
    """
    identity_key = get_identity_key(request) or 'unknown'
    payment_info = get_request_payment_info(request)
    
    # Check authentication
    if not is_authenticated_request(request):
        return JsonResponse({
            'error': 'Authentication required',
            'message': 'Please authenticate first',
            'identity_key': identity_key
        }, status=401)
    
    # Check payment (500 satoshis)
    required_payment = 500
    if not is_payment_processed(request) or (payment_info and payment_info.satoshis_paid < required_payment):
        return JsonResponse({
            'error': 'Payment required',
            'message': f'Please pay {required_payment} satoshis',
            'required_payment': required_payment,
            'paid_amount': payment_info.satoshis_paid if payment_info else 0
        }, status=402)
    
    # Success! (TypeScript equivalent response)
    return JsonResponse({
        'message': 'Hello BSV',
        'success': True,
        'authenticated': True,
        'payment_received': True,
        'identity_key': identity_key,
        'satoshis_paid': payment_info.satoshis_paid if payment_info else 0,
        'tx': payment_info.transaction_id if payment_info else None  # TypeScript: tx field (transaction data)
    })
