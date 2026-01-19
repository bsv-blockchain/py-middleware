"""
Django utility functions for BSV middleware.

This module provides helper functions for Django views to easily access
BSV authentication and payment information from requests.
"""

from typing import Optional, List, Dict, Any, Callable
from functools import wraps

from django.http import JsonResponse, HttpRequest
from django.core.files.uploadedfile import UploadedFile
from django.http.multipartparser import MultiPartParser
from bsv_middleware.types import AuthInfo, PaymentInfo

import logging
logger = logging.getLogger(__name__)


def get_identity_key(request: HttpRequest) -> Optional[str]:
    """Get the identity key from a BSV authenticated request."""
    # Check both bsv_auth (new) and auth (middleware-set) for compatibility
    if hasattr(request, 'bsv_auth') and request.bsv_auth:
        result: str = request.bsv_auth.identity_key
        return result
    elif hasattr(request, 'auth') and request.auth and hasattr(request.auth, 'identity_key'):
        result_auth: str = request.auth.identity_key
        return result_auth
    return 'unknown'


def get_certificates(request: HttpRequest) -> List[Any]:
    """Get certificates from a BSV authenticated request."""
    if hasattr(request, 'bsv_auth') and request.bsv_auth:
        return request.bsv_auth.certificates or []
    return []


def is_authenticated_request(request: HttpRequest) -> bool:
    """Check if request has valid BSV authentication."""
    # Check both bsv_auth (new) and auth (middleware-set) for compatibility
    if hasattr(request, 'bsv_auth') and request.bsv_auth:
        # Check for is_authenticated property or authenticated attribute
        is_auth = (
            request.bsv_auth.is_authenticated 
            if hasattr(request.bsv_auth, 'is_authenticated') 
            else getattr(request.bsv_auth, 'authenticated', False)
        )
        result: bool = bool(
            is_auth and 
            request.bsv_auth.identity_key is not None and
            request.bsv_auth.identity_key != 'unknown'
        )
        return result
    elif hasattr(request, 'auth') and request.auth and hasattr(request.auth, 'identity_key'):
        key: Any = request.auth.identity_key
        return key is not None and key != 'unknown'
    return False


def is_payment_processed(request: HttpRequest) -> bool:
    """Check if request has valid BSV payment."""
    if hasattr(request, 'bsv_payment') and request.bsv_payment:
        result: bool = bool(
            request.bsv_payment.accepted and 
            request.bsv_payment.satoshis_paid > 0
        )
        return result
    return False


def get_request_payment_info(request: HttpRequest) -> Optional[PaymentInfo]:
    """Get payment information from request."""
    if hasattr(request, 'bsv_payment'):
        result: PaymentInfo = request.bsv_payment
        return result
    return None


def get_request_auth_info(request: HttpRequest) -> Optional[AuthInfo]:
    """Get authentication information from request."""
    # Check both bsv_auth (new) and auth (middleware-set) for compatibility
    if hasattr(request, 'bsv_auth'):
        result: AuthInfo = request.bsv_auth
        return result
    elif hasattr(request, 'auth') and request.auth:
        result2: AuthInfo = request.auth
        return result2
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


def extract_bsv_headers(request: HttpRequest) -> Dict[str, str]:
    """Extract BSV headers from request (alias for get_bsv_headers for compatibility)."""
    return get_bsv_headers(request)


# Decorators for view protection

def bsv_authenticated_required(view_func: Callable[..., Any]) -> Callable[..., Any]:
    """
    Decorator that requires BSV authentication for a view.
    
    Returns 401 if request is not authenticated.
    """
    @wraps(view_func)
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
        if not is_authenticated_request(request):
            return JsonResponse({
                'error': 'Authentication required',
                'message': 'This endpoint requires BSV authentication',
                'identity_key': None
            }, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper


def bsv_payment_required(required_satoshis: int) -> Callable[..., Any]:
    """
    Decorator that requires BSV payment for a view.
    
    Args:
        required_satoshis: Minimum satoshis required
        
    Returns 402 if payment is insufficient.
    """
    def decorator(view_func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(view_func)
        def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
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


def bsv_certificates_required(certificate_types: List[str]) -> Callable[..., Any]:
    """
    Decorator that requires specific certificate types.
    
    Args:
        certificate_types: List of required certificate types
        
    Returns 403 if certificates are missing.
    """
    def decorator(view_func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(view_func)
        def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
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
                'authenticated': auth_info.is_authenticated if auth_info else False,
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


# ==================== multipart/form-data Support Functions ====================

def get_multipart_data(request: HttpRequest) -> Dict[str, Any]:
    """
    Safely parse multipart/form-data after BSV authentication

    Args:
        request: Django HTTP request (BSV authentication already processed)

    Returns:
        dict: {
            'fields': {...},  # Form fields
            'files': {...}    # Uploaded files
        }
    """
    if not request.META.get('CONTENT_TYPE', '').startswith('multipart/form-data'):
        return {'fields': {}, 'files': {}}
    
    try:
        # Use Django's standard parser after BSV processing
        # Note: BSV signature verification is already complete, so parsing is safe here
        parser = MultiPartParser(
            request.META, 
            request, 
            request.upload_handlers
        )
        
        post_data, files_data = parser.parse()
        
        logger.debug(f"Parsed multipart data: {len(post_data)} fields, {len(files_data)} files")
        
        return {
            'fields': dict(post_data),
            'files': dict(files_data)
        }
        
    except Exception as e:
        logger.warning(f"Failed to parse multipart data: {e}")
        return {'fields': {}, 'files': {}}


def is_multipart_request(request: HttpRequest) -> bool:
    """Check if multipart/form-data request"""
    result: bool = request.META.get('CONTENT_TYPE', '').startswith('multipart/form-data')
    return result


def is_text_plain_request(request: HttpRequest) -> bool:
    """Check if text/plain request"""
    content_type = request.META.get('CONTENT_TYPE', '').lower().strip()
    return content_type == 'text/plain' or content_type.startswith('text/plain;')


def get_text_content(request: HttpRequest, encoding: str = 'utf-8') -> str:
    """
    Get text content from text/plain request

    Args:
        request: Django HTTP request (text/plain content-type)
        encoding: Text encoding (default: utf-8)

    Returns:
        str: Decoded text content

    Raises:
        ValueError: If not text/plain or decoding fails
    """
    if not is_text_plain_request(request):
        raise ValueError('Request is not text/plain content type')
    
    try:
        # Decode raw body as text
        text_content = request.body.decode(encoding)
        
        logger.debug(f"Decoded text/plain content: {len(text_content)} characters")
        return text_content
        
    except UnicodeDecodeError as e:
        logger.warning(f"Failed to decode text/plain content as {encoding}: {e}")
        raise ValueError(f'Failed to decode text content as {encoding}')


def get_content_by_type(request: HttpRequest) -> Dict[str, Any]:
    """
    Parse request content based on Content-Type (Express writeBodyToWriter equivalent)

    Args:
        request: Django HTTP request

    Returns:
        dict: {
            'content_type': str,
            'data': Any,  # Parsed data
            'encoding': str,
            'processed_body': bytes  # Processed body for BSV protocol
        }
    """
    content_type = request.META.get('CONTENT_TYPE', '').lower().strip()
    
    try:
        if is_multipart_request(request):
            # multipart/form-data
            multipart_data = get_multipart_data(request)
            return {
                'content_type': 'multipart/form-data',
                'data': multipart_data,
                'encoding': 'multipart',
                'processed_body': request.body  # Preserve raw data
            }
            
        elif content_type == 'application/json' or content_type.startswith('application/json;'):
            # JSON - Express equivalent: JSON.stringify(body)
            import json
            data = json.loads(request.body.decode('utf-8'))
            # Stringify JSON then UTF-8 encode (Express compatible)
            processed_json = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
            return {
                'content_type': 'application/json',
                'data': data,
                'encoding': 'utf-8',
                'processed_body': processed_json.encode('utf-8')
            }
            
        elif is_text_plain_request(request):
            # text/plain - Express equivalent: Utils.toArray(body, 'utf8')
            text_content = get_text_content(request)
            return {
                'content_type': 'text/plain',
                'data': text_content,
                'encoding': 'utf-8',
                'processed_body': text_content.encode('utf-8')  # Express compatible: UTF-8 bytes
            }
            
        elif content_type == 'application/x-www-form-urlencoded' or content_type.startswith('application/x-www-form-urlencoded;'):
            # URL-encoded form - Express equivalent: new URLSearchParams(body).toString()
            from urllib.parse import parse_qs, urlencode
            form_data = parse_qs(request.body.decode('utf-8'))
            # Re-encode form data (Express compatible)
            processed_form = urlencode(form_data, doseq=True)
            return {
                'content_type': 'application/x-www-form-urlencoded',
                'data': form_data,
                'encoding': 'utf-8',
                'processed_body': processed_form.encode('utf-8')
            }
            
        else:
            # Binary/unknown - raw bytes (Express: no processing)
            return {
                'content_type': content_type or 'application/octet-stream',
                'data': request.body,
                'encoding': 'binary',
                'processed_body': request.body
            }
            
    except Exception as e:
        logger.warning(f"Failed to parse content for type '{content_type}': {e}")
        # Fallback to raw bytes
        return {
            'content_type': content_type or 'application/octet-stream',
            'data': request.body,
            'encoding': 'binary',
            'processed_body': request.body
        }


def get_uploaded_files(request: HttpRequest) -> Dict[str, UploadedFile]:
    """
    Get uploaded files from BSV authenticated request

    Args:
        request: Django HTTP request (BSV authenticated)

    Returns:
        dict: filename -> UploadedFile mapping
    """
    # Check if multipart_files was already parsed by decorator
    if hasattr(request, 'multipart_files'):
        return request.multipart_files  # type: ignore
    
    if is_multipart_request(request):
        multipart_data = get_multipart_data(request)
        result: Dict[str, Any] = multipart_data.get('files', {})
        return result
    return {}


def get_multipart_fields(request: HttpRequest) -> Dict[str, Any]:
    """
    Get form fields from BSV authenticated request

    Args:
        request: Django HTTP request (BSV authenticated)

    Returns:
        dict: field_name -> field_value mapping
    """
    # Check if multipart_fields was already parsed by decorator
    if hasattr(request, 'multipart_fields'):
        return request.multipart_fields  # type: ignore
    
    if is_multipart_request(request):
        multipart_data = get_multipart_data(request)
        result: Dict[str, Any] = multipart_data.get('fields', {})
        return result
    return {}


# ==================== BSV Authentication + File Upload Decorators ====================

def handle_file_upload(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    File upload handling decorator
    BSV authentication + multipart/form-data processing

    Usage:
        @handle_file_upload
        def upload_view(request):
            files = get_uploaded_files(request)
            # ... handle files
    """
    @wraps(func)
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
        # BSV authentication is already processed by middleware

        if is_multipart_request(request):
            # Parse multipart data and add to request
            multipart_data = get_multipart_data(request)
            request.multipart_fields = multipart_data['fields']
            request.multipart_files = multipart_data['files']
            
            logger.debug(f"Added multipart data to request: {len(multipart_data['fields'])} fields, {len(multipart_data['files'])} files")
        
        return func(request, *args, **kwargs)
    
    return wrapper


def bsv_file_upload_required(func: Callable[..., Any]) -> Callable[..., Any]:
    """
    BSV authentication + file upload required decorator

    Usage:
        @bsv_file_upload_required
        def secure_upload_view(request):
            identity_key = get_identity_key(request)
            files = get_uploaded_files(request)
            # ... secure file processing
    """
    @wraps(func)
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
        # BSV authentication check
        if not is_authenticated_request(request):
            return JsonResponse({'error': 'BSV authentication required'}, status=401)

        # File upload check
        if not is_multipart_request(request):
            return JsonResponse({'error': 'File upload required (multipart/form-data)'}, status=400)

        # Process multipart data
        multipart_data = get_multipart_data(request)
        if not multipart_data['files']:
            return JsonResponse({'error': 'No files uploaded'}, status=400)
        
        request.multipart_fields = multipart_data['fields']
        request.multipart_files = multipart_data['files']
        
        logger.info(f"BSV authenticated file upload: {len(multipart_data['files'])} files from {get_identity_key(request)}")
        
        return func(request, *args, **kwargs)
    
    return wrapper