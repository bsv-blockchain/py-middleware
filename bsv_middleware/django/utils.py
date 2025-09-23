"""
Django utility functions for BSV middleware.

This module provides helper functions for Django views to easily access
BSV authentication and payment information from requests.
"""

from typing import Optional, List, Dict, Any, Callable
from functools import wraps

from django.http import JsonResponse, HttpRequest
from ..types import AuthInfo, PaymentInfo


def get_identity_key(request: HttpRequest) -> Optional[str]:
    """Get the identity key from a BSV authenticated request."""
    # Check both bsv_auth (new) and auth (middleware-set) for compatibility
    if hasattr(request, 'bsv_auth') and request.bsv_auth:
        return request.bsv_auth.identity_key
    elif hasattr(request, 'auth') and request.auth and hasattr(request.auth, 'identity_key'):
        return request.auth.identity_key if request.auth.identity_key != 'unknown' else None
    return None


def get_certificates(request: HttpRequest) -> List[Any]:
    """Get certificates from a BSV authenticated request."""
    if hasattr(request, 'bsv_auth') and request.bsv_auth:
        return request.bsv_auth.certificates or []
    return []


def is_authenticated_request(request: HttpRequest) -> bool:
    """Check if request has valid BSV authentication."""
    # Check both bsv_auth (new) and auth (middleware-set) for compatibility
    if hasattr(request, 'bsv_auth') and request.bsv_auth:
        return (
            request.bsv_auth.authenticated and 
            request.bsv_auth.identity_key is not None
        )
    elif hasattr(request, 'auth') and request.auth and hasattr(request.auth, 'identity_key'):
        return request.auth.identity_key is not None and request.auth.identity_key != 'unknown'
    return False


def is_payment_processed(request: HttpRequest) -> bool:
    """Check if request has valid BSV payment."""
    if hasattr(request, 'bsv_payment') and request.bsv_payment:
        return (
            request.bsv_payment.accepted and 
            request.bsv_payment.satoshis_paid > 0
        )
    return False


def get_request_payment_info(request: HttpRequest) -> Optional[PaymentInfo]:
    """Get payment information from request."""
    if hasattr(request, 'bsv_payment'):
        return request.bsv_payment
    return None


def get_request_auth_info(request: HttpRequest) -> Optional[AuthInfo]:
    """Get authentication information from request."""
    # Check both bsv_auth (new) and auth (middleware-set) for compatibility
    if hasattr(request, 'bsv_auth'):
        return request.bsv_auth
    elif hasattr(request, 'auth') and request.auth:
        return request.auth
    return None


def format_satoshis(satoshis: int) -> str:
    """Format satoshis amount for display."""
    if satoshis == 0:
        return "0 satoshis"
    elif satoshis == 1:
        return "1 satoshi"
    else:
        return f"{satoshis:,} satoshis"


def get_bsv_headers(request: HttpRequest) -> Dict[str, str]:
    """Extract all BSV-related headers from request."""
    return {
        key: value for key, value in request.headers.items()
        if key.lower().startswith('x-bsv-')
    }


# Decorators for view protection

def bsv_authenticated_required(view_func: Callable) -> Callable:
    """
    Decorator that requires BSV authentication for a view.
    
    Returns 401 if request is not authenticated.
    """
    @wraps(view_func)
    def wrapper(request: HttpRequest, *args, **kwargs):
        if not is_authenticated_request(request):
            return JsonResponse({
                'error': 'Authentication required',
                'message': 'This endpoint requires BSV authentication',
                'identity_key': None
            }, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper


def bsv_payment_required(required_satoshis: int) -> Callable:
    """
    Decorator that requires BSV payment for a view.
    
    Args:
        required_satoshis: Minimum satoshis required
        
    Returns 402 if payment is insufficient.
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def wrapper(request: HttpRequest, *args, **kwargs):
            # Check authentication first
            if not is_authenticated_request(request):
                return JsonResponse({
                    'error': 'Authentication required',
                    'message': 'This endpoint requires BSV authentication',
                    'identity_key': None
                }, status=401)
            
            # Check payment
            payment_info = get_request_payment_info(request)
            if not is_payment_processed(request) or (
                payment_info and payment_info.satoshis_paid < required_satoshis
            ):
                return JsonResponse({
                    'error': 'Payment required',
                    'message': f'This endpoint requires payment of {format_satoshis(required_satoshis)}',
                    'required_payment': format_satoshis(required_satoshis),
                    'paid_amount': format_satoshis(
                        payment_info.satoshis_paid if payment_info else 0
                    )
                }, status=402)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


def bsv_certificates_required(certificate_types: List[str]) -> Callable:
    """
    Decorator that requires specific certificate types.
    
    Args:
        certificate_types: List of required certificate types
        
    Returns 403 if certificates are missing.
    """
    def decorator(view_func: Callable) -> Callable:
        @wraps(view_func)
        def wrapper(request: HttpRequest, *args, **kwargs):
            # Check authentication first
            if not is_authenticated_request(request):
                return JsonResponse({
                    'error': 'Authentication required',
                    'message': 'This endpoint requires BSV authentication',
                    'identity_key': None
                }, status=401)
            
            # Check certificates
            certificates = get_certificates(request)
            available_types = [
                getattr(cert, 'type', 'unknown') for cert in certificates
            ]
            
            missing_types = [
                cert_type for cert_type in certificate_types
                if cert_type not in available_types
            ]
            
            if missing_types:
                return JsonResponse({
                    'error': 'Certificates required',
                    'message': f'This endpoint requires certificates: {", ".join(certificate_types)}',
                    'required_certificates': certificate_types,
                    'missing_certificates': missing_types,
                    'available_certificates': available_types
                }, status=403)
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


# Development utilities

def debug_request_info(request: HttpRequest) -> Dict[str, Any]:
    """
    Get comprehensive debug information about a request.
    Useful for development and troubleshooting.
    """
    auth_info = get_request_auth_info(request)
    payment_info = get_request_payment_info(request)
    
    return {
        'request': {
            'path': request.path,
            'method': request.method,
            'content_type': request.content_type,
        },
        'authentication': {
            'authenticated': is_authenticated_request(request),
            'identity_key': get_identity_key(request),
            'certificates_count': len(get_certificates(request)),
            'auth_info': {
                'authenticated': auth_info.authenticated if auth_info else False,
                'identity_key': auth_info.identity_key if auth_info else None,
                'certificates': len(auth_info.certificates) if auth_info and auth_info.certificates else 0
            } if auth_info else None
        },
        'payment': {
            'processed': is_payment_processed(request),
            'satoshis_paid': payment_info.satoshis_paid if payment_info else 0,
            'accepted': payment_info.accepted if payment_info else False,
            'transaction_id': payment_info.transaction_id if payment_info else None,
            'payment_info': {
                'satoshis_paid': payment_info.satoshis_paid,
                'accepted': payment_info.accepted,
                'transaction_id': payment_info.transaction_id,
                'derivation_prefix': payment_info.derivation_prefix
            } if payment_info else None
        },
        'headers': {
            'bsv_headers': get_bsv_headers(request),
            'all_headers': dict(request.headers)
        }
    }


def create_bsv_response(data: Dict[str, Any], request: HttpRequest) -> JsonResponse:
    """
    Create a JSON response with BSV information included.
    
    Args:
        data: Response data
        request: Django request object
        
    Returns:
        JsonResponse with BSV info included
    """
    response_data = {
        **data,
        'bsv_info': {
            'identity_key': get_identity_key(request),
            'authenticated': is_authenticated_request(request),
            'payment_processed': is_payment_processed(request),
            'certificates_count': len(get_certificates(request))
        }
    }
    
    return JsonResponse(response_data)