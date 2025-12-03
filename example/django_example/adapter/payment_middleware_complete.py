"""
Django Payment Middleware - Complete Implementation

Complete port of Express createPaymentMiddleware() function
Implements payment processing with BRC-100 compliance
"""

import json
import logging
from typing import Optional, Dict, Any, Callable
from django.http import HttpRequest, HttpResponse, JsonResponse

from bsv_middleware.types import LogLevel, BSVPayment, PaymentInfo
from bsv_middleware.exceptions import BSVAuthException, BSVServerMisconfiguredException
from bsv_middleware.py_sdk_bridge import PySdkBridge

logger = logging.getLogger(__name__)

# Payment version (Express equivalent)
PAYMENT_VERSION = '1.0'

class BSVPaymentMiddleware:
    """
    Django Payment Middleware - Complete port of Express createPaymentMiddleware()
    
    This middleware enforces BSV payment for HTTP requests.
    NOTE: This middleware should run after the authentication middleware 
    so that request.auth is available.
    
    Equivalent to Express: createPaymentMiddleware(options)
    """
    
    def __init__(
        self,
        get_response: Callable[[HttpRequest], HttpResponse],
        calculate_request_price: Optional[Callable[[HttpRequest], int]] = None,
        wallet=None,
        log_level: LogLevel = LogLevel.ERROR
    ):
        """
        Initialize payment middleware.
        
        Args:
            get_response: Django middleware get_response function
            calculate_request_price: Function returning price for request in satoshis
            wallet: Wallet instance capable of submitting direct transactions
            log_level: Logging level
        """
        self.get_response = get_response
        self.calculate_request_price = calculate_request_price or self._default_price_calculator
        self.wallet = wallet
        self.log_level = log_level
        
        # Validate configuration (Express equivalent validation)
        self._validate_configuration()
        
        logger.info(f"BSVPaymentMiddleware initialized (version={PAYMENT_VERSION})")
    
    def _validate_configuration(self) -> None:
        """
        Validate middleware configuration.
        
        Equivalent to Express validation in createPaymentMiddleware()
        """
        if not callable(self.calculate_request_price):
            raise BSVServerMisconfiguredException(
                'The calculateRequestPrice option must be a function.'
            )
        
        if self.wallet is None or not hasattr(self.wallet, 'internalize_action'):
            raise BSVServerMisconfiguredException(
                'A valid wallet instance must be supplied to the payment middleware.'
            )
    
    def _default_price_calculator(self, request: HttpRequest) -> int:
        """
        Default price calculator.
        
        Equivalent to Express: calculateRequestPrice = () => 100
        """
        return 100  # Default to 100 satoshis
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        """
        Process payment middleware.
        
        Equivalent to Express: async (req: Request, res: Response, next: NextFunction)
        """
        try:
            # Express equivalent: calculate request price FIRST
            try:
                request_price = self.calculate_request_price(request)
            except Exception as err:
                logger.error(f"Price calculation error: {err}")
                return JsonResponse({
                    'status': 'error',
                    'code': 'ERR_PAYMENT_INTERNAL',
                    'description': 'An internal error occurred while determining the payment required for this request.'
                }, status=500)
            
            # Express equivalent: if price is 0, continue without payment (no auth required)
            if request_price <= 0:
                self._log('debug', 'Request price is 0, continuing without payment', {
                    'path': request.path,
                    'price': request_price
                })
                return self.get_response(request)
            
            # For paid endpoints, check authentication
            if not hasattr(request, 'auth'):
                # No auth object at all - likely missing auth middleware
                return self._payment_error('ERR_AUTHENTICATION_REQUIRED', 'Authentication required for payment processing.')
            elif not hasattr(request.auth, 'identity_key') or request.auth.identity_key == 'unknown':
                # Auth object exists but not authenticated
                return self._payment_error('ERR_AUTHENTICATION_REQUIRED', 'Valid authentication required for payment processing.')
            
            # Express equivalent: check for payment header
            payment_header = request.headers.get('x-bsv-payment')
            if not payment_header:
                return self._request_payment(request, request_price)
            
            # Express equivalent: verify payment
            return self._verify_payment(request, payment_header, request_price)
            
        except Exception as e:
            logger.error(f"Payment middleware error: {e}")
            return JsonResponse({
                'status': 'error',
                'code': 'ERR_PAYMENT_INTERNAL', 
                'description': 'An internal payment processing error occurred.'
            }, status=500)
    
    def _request_payment(self, request: HttpRequest, price: int) -> JsonResponse:
        """
        Request payment from client.
        
        Equivalent to Express: return res.status(402).json(...)
        """
        try:
            # Express equivalent: generate nonce for payment
            from bsv_middleware.py_sdk_bridge import create_nonce
            nonce = create_nonce()
            
            # Express equivalent: get derivation prefix
            derivation_prefix = self._get_derivation_prefix(request)
            
            self._log('info', 'Requesting payment from client', {
                'path': request.path,
                'price': price,
                'nonce': nonce[:10] + '...' if nonce else 'None',
                'derivationPrefix': derivation_prefix
            })
            
            # Express equivalent: 402 Payment Required response
            response_data = {
                'status': 'error',
                'code': 'ERR_PAYMENT_REQUIRED',
                'description': f'Payment of {price} satoshis is required for this request.',
                'satoshisRequired': price,
                'nonce': nonce,
                'derivationPrefix': derivation_prefix
            }
            
            response = JsonResponse(response_data, status=402)
            
            # Express equivalent: set payment headers
            response['x-bsv-payment-version'] = PAYMENT_VERSION
            response['x-bsv-payment-satoshis-required'] = str(price)
            response['x-bsv-payment-derivation-prefix'] = derivation_prefix
            
            return response
            
        except Exception as e:
            self._log('error', f'Error requesting payment: {e}')
            return JsonResponse({
                'status': 'error',
                'code': 'ERR_PAYMENT_INTERNAL',
                'description': 'Failed to generate payment request.'
            }, status=500)
    
    def _verify_payment(self, request: HttpRequest, payment_header: str, expected_price: int) -> HttpResponse:
        """
        Verify payment from client.
        
        Equivalent to Express payment verification logic.
        """
        try:
            self._log('debug', 'Verifying payment', {
                'path': request.path,
                'paymentHeader': payment_header[:50] + '...' if payment_header else 'None',
                'expectedPrice': expected_price
            })
            
            # Express equivalent: parse payment data
            payment_data = self._parse_payment_data(payment_header)
            if not payment_data:
                return self._payment_error('ERR_MALFORMED_PAYMENT', 'Invalid payment format.')
            
            # Express equivalent: verify nonce
            if not self._verify_nonce(payment_data):
                return self._payment_error('ERR_INVALID_PAYMENT', 'Invalid payment nonce.')
            
            # Express equivalent: verify derivation prefix
            expected_prefix = self._get_derivation_prefix(request)
            if payment_data.get('derivationPrefix') != expected_prefix:
                return self._payment_error('ERR_INVALID_DERIVATION_PREFIX', 'Invalid derivation prefix.')
            
            # Express equivalent: process payment with wallet
            payment_result = self._process_payment_with_wallet(payment_data, expected_price)
            if not payment_result['accepted']:
                return self._payment_error('ERR_PAYMENT_REJECTED', 'Payment was rejected.')
            
            # Express equivalent: add payment info to request
            payment_info = PaymentInfo(
                satoshis_paid=payment_result.get('satoshisPaid', expected_price),
                accepted=True,
                transaction_id=payment_result.get('transactionId', 'unknown'),
                derivation_prefix=payment_data.get('derivationPrefix', expected_prefix)
            )
            request.payment = payment_info
            request.bsv_payment = payment_info  # For compatibility with tests and utils
            
            self._log('info', 'Payment verified successfully', {
                'path': request.path,
                'satoshisPaid': request.payment.satoshis_paid,
                'transactionId': request.payment.transaction_id
            })
            
            # Express equivalent: continue to next middleware
            return self.get_response(request)
            
        except Exception as e:
            self._log('error', f'Payment verification error: {e}')
            return self._payment_error('ERR_PAYMENT_INTERNAL', 'Payment verification failed.')
    
    def _parse_payment_data(self, payment_header: str) -> Optional[Dict[str, Any]]:
        """
        Parse payment data from header.
        
        Equivalent to Express payment parsing logic.
        """
        try:
            # Express equivalent: parse JSON payment data
            payment_data = json.loads(payment_header)
            
            # Validate required fields
            required_fields = ['nonce', 'derivationPrefix', 'beef']
            if not all(field in payment_data for field in required_fields):
                self._log('warn', 'Missing required payment fields', {
                    'provided': list(payment_data.keys()),
                    'required': required_fields
                })
                return None
            
            return payment_data
            
        except json.JSONDecodeError as e:
            self._log('warn', f'Invalid payment JSON: {e}')
            return None
        except Exception as e:
            self._log('error', f'Payment parsing error: {e}')
            return None
    
    def _verify_nonce(self, payment_data: Dict[str, Any]) -> bool:
        """
        Verify payment nonce.
        
        Equivalent to Express: verifyNonce() functionality.
        """
        try:
            nonce = payment_data.get('nonce')
            if not nonce:
                return False
            
            # Express equivalent: verify nonce using py-sdk
            from bsv_middleware.py_sdk_bridge import verify_nonce
            return verify_nonce(nonce)
            
        except Exception as e:
            self._log('error', f'Nonce verification error: {e}')
            return False
    
    def _process_payment_with_wallet(self, payment_data: Dict[str, Any], expected_price: int) -> Dict[str, Any]:
        """
        Process payment using wallet.
        
        Equivalent to Express: wallet.internalizeAction() functionality.
        """
        try:
            # Express equivalent: prepare action for wallet
            action = {
                'type': 'payment',
                'satoshis': expected_price,
                'beef': payment_data.get('beef'),
                'derivationPrefix': payment_data.get('derivationPrefix'),
                'nonce': payment_data.get('nonce')
            }
            
            self._log('debug', 'Processing payment with wallet', {
                'actionType': action['type'],
                'satoshis': action['satoshis']
            })
            
            # Express equivalent: wallet.internalizeAction(action)
            # Handle both py-sdk and simple wallet formats
            try:
                # Try py-sdk format first
                if hasattr(self.wallet, 'internalize_action'):
                    # Check if it's a py-sdk style wallet (requires 3 args)
                    import inspect
                    sig = inspect.signature(self.wallet.internalize_action)
                    if len(sig.parameters) >= 3:
                        # py-sdk format: internalize_action(ctx, args, originator)
                        result = self.wallet.internalize_action(None, {'action': action}, 'payment_middleware')
                    else:
                        # Simple format: internalize_action(action)
                        result = self.wallet.internalize_action(action)
                else:
                    # Fallback: assume simple format
                    result = self.wallet.internalize_action(action)
                    
            except TypeError as sig_error:
                # Signature mismatch - try simple format
                self._log('debug', f'Trying simple wallet format due to signature error: {sig_error}')
                result = self.wallet.internalize_action(action)
            
            self._log('debug', 'Wallet payment result', {'result': result})
            return result
            
        except Exception as e:
            self._log('error', f'Wallet payment processing error: {e}')
            return {
                'accepted': False,
                'error': str(e)
            }
    
    def _get_derivation_prefix(self, request: HttpRequest) -> str:
        """
        Get derivation prefix for payment.
        
        Equivalent to Express derivation prefix logic.
        """
        try:
            # Express equivalent: use request path and identity for derivation
            identity_key = getattr(request.auth, 'identity_key', 'unknown')
            return f"{request.path}:{identity_key[:20]}..." if identity_key != 'unknown' else request.path
            
        except Exception as e:
            self._log('warn', f'Error generating derivation prefix: {e}')
            return request.path
    
    def _payment_error(self, code: str, description: str) -> JsonResponse:
        """
        Return payment error response with appropriate HTTP status code.
        
        Equivalent to Express payment error responses.
        """
        # Map error codes to appropriate HTTP status codes
        status_map = {
            'ERR_PAYMENT_REQUIRED': 402,  # Payment Required
            'ERR_PAYMENT_REJECTED': 402,  # Payment Required (insufficient amount)
            'ERR_INSUFFICIENT_PAYMENT': 402,  # Payment Required
            'ERR_MALFORMED_PAYMENT': 400,  # Bad Request
            'ERR_INVALID_DERIVATION_PREFIX': 400,  # Bad Request
            'ERR_INVALID_PAYMENT': 400,  # Bad Request
            'ERR_SERVER_MISCONFIGURED': 500,  # Internal Server Error
            'ERR_AUTHENTICATION_REQUIRED': 401,  # Unauthorized
        }
        
        status_code = status_map.get(code, 400)  # Default to 400
        
        return JsonResponse({
            'status': 'error',
            'code': code,
            'description': description
        }, status=status_code)
    
    def _log(self, level: str, message: str, data: Optional[Dict[str, Any]] = None) -> None:
        """
        Log message with payment middleware context.
        
        Equivalent to Express logging functionality.
        """
        try:
            log_prefix = f"[BSVPaymentMiddleware] [{level.upper()}]"
            full_message = f"{log_prefix} {message}"
            
            if data:
                full_message += f" {data}"
            
            if level == 'debug':
                logger.debug(full_message)
            elif level == 'info':
                logger.info(full_message)
            elif level == 'warn':
                logger.warning(full_message)
            elif level == 'error':
                logger.error(full_message)
        except Exception:
            # Fallback logging if formatting fails
            logger.error(f"Payment middleware: {message}")


# Factory function for easy instantiation (Express equivalent)
def create_payment_middleware(
    calculate_request_price: Optional[Callable[[HttpRequest], int]] = None,
    wallet=None,
    log_level: LogLevel = LogLevel.ERROR
) -> Callable:
    """
    Create payment middleware instance.
    
    Equivalent to Express: createPaymentMiddleware(options)
    
    Args:
        calculate_request_price: Function returning price for request in satoshis
        wallet: Wallet instance capable of submitting direct transactions
        log_level: Logging level
        
    Returns:
        Middleware class for Django MIDDLEWARE setting
    """
    class PaymentMiddlewareWrapper:
        def __init__(self, get_response):
            self.middleware = BSVPaymentMiddleware(
                get_response=get_response,
                calculate_request_price=calculate_request_price,
                wallet=wallet,
                log_level=log_level
            )
        
        def __call__(self, request):
            return self.middleware(request)
    
    return PaymentMiddlewareWrapper
