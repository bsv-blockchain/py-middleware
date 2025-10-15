"""
Django Payment Middleware for BSV Payments

This module provides Django payment middleware for BSV blockchain payments,
directly ported from Express createPaymentMiddleware() function.
"""

import json
import logging
from typing import Optional, Union
from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.deprecation import MiddlewareMixin

from ..types import (
    WalletInterface,
    PaymentMiddlewareOptions,
    CalculateRequestPriceCallback,
    BSV_PAYMENT_HEADER,
    BSV_PAYMENT_VERSION_HEADER,
    BSV_PAYMENT_SATOSHIS_REQUIRED_HEADER,
    BSV_PAYMENT_DERIVATION_PREFIX_HEADER,
    BSV_PAYMENT_SATOSHIS_PAID_HEADER,
    BSVPayment,
    PaymentInfo,
    ERR_PAYMENT_REQUIRED,
    ERR_PAYMENT_INTERNAL,
    ERR_SERVER_MISCONFIGURED
)
from ..exceptions import (
    BSVPaymentException,
    BSVPaymentRequiredException,
    BSVMalformedPaymentException,
    BSVInvalidDerivationPrefixException,
    BSVServerMisconfiguredException
)
from ..py_sdk_bridge import PySdkBridge, create_py_sdk_bridge

logger = logging.getLogger(__name__)

# Payment version constant (from Express middleware)
PAYMENT_VERSION = '1.0'


class BSVPaymentMiddleware(MiddlewareMixin):
    """
    Django BSV Payment Middleware
    
    Direct port of Express createPaymentMiddleware() function to Django.
    Handles BSV blockchain payments using Direct Payment Protocol (DPP).
    """
    
    def __init__(self, get_response=None):
        """
        Initialize BSV Payment Middleware.
        
        Equivalent to Express: createPaymentMiddleware(options)
        """
        super().__init__(get_response)
        self.get_response = get_response
        
        # Load configuration from Django settings
        self._load_configuration()
        
        # Initialize components
        self._initialize_components()
        
        logger.info(f"BSVPaymentMiddleware initialized with wallet: {type(self.wallet).__name__}")
    
    def _load_configuration(self) -> None:
        """
        Load BSV payment configuration from Django settings.
        
        Equivalent to Express options destructuring.
        """
        try:
            bsv_config = getattr(settings, 'BSV_MIDDLEWARE', {})
            
            # Required configuration
            self.wallet = bsv_config.get('WALLET')
            if not self.wallet:
                raise BSVServerMisconfiguredException(
                    'You must configure BSV_MIDDLEWARE with a WALLET in Django settings.'
                )
            
            # Required: price calculation function
            self.calculate_request_price = bsv_config.get('CALCULATE_REQUEST_PRICE')
            if not self.calculate_request_price:
                # Default to 100 satoshis (same as Express default)
                self.calculate_request_price = lambda request: 100
            
            if not callable(self.calculate_request_price):
                raise BSVServerMisconfiguredException(
                    'The CALCULATE_REQUEST_PRICE option must be a callable function.'
                )
            
            # Optional: whether auth middleware is required
            self.require_auth = bsv_config.get('REQUIRE_AUTH', True)
                
        except Exception as e:
            logger.error(f"Failed to load BSV payment configuration: {e}")
            raise BSVServerMisconfiguredException(
                f"Invalid BSV_MIDDLEWARE payment configuration: {str(e)}"
            )
    
    def _initialize_components(self) -> None:
        """
        Initialize payment middleware components.
        
        Equivalent to Express wallet validation and setup.
        """
        try:
            if not hasattr(self.wallet, 'internalize_action'):
                raise BSVServerMisconfiguredException(
                    'A valid wallet instance must be supplied to the payment middleware.'
                )
            
            # Create py-sdk bridge
            self.py_sdk_bridge = create_py_sdk_bridge(self.wallet)
            
            logger.debug("BSV payment middleware components initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize BSV payment components: {e}")
            raise BSVServerMisconfiguredException(
                f"Payment component initialization failed: {str(e)}"
            )
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        """
        Main payment middleware entry point.
        
        Equivalent to Express: return async (req, res, next) => { ... }
        """
        try:
            # Process payment logic
            response = self._process_payment(request)
            
            # If response is returned, payment failed or required
            if response:
                return response
            
            # Continue to next middleware/view
            if self.get_response:
                return self.get_response(request)
            
            return HttpResponse()
            
        except BSVPaymentException as e:
            logger.warning(f"BSV payment failed: {e.message}")
            return self._build_error_response(e)
        except Exception as e:
            logger.error(f"Unexpected error in BSV payment middleware: {e}")
            return self._build_error_response(
                BSVPaymentException("Payment processing failed", ERR_PAYMENT_INTERNAL, 500)
            )
    
    def process_request(self, request: HttpRequest) -> Optional[HttpResponse]:
        """
        Django middleware process_request hook.
        """
        try:
            return self._process_payment(request)
        except BSVPaymentException as e:
            return self._build_error_response(e)
        except Exception as e:
            logger.error(f"Unexpected error in payment process_request: {e}")
            return self._build_error_response(
                BSVPaymentException("Payment processing failed", ERR_PAYMENT_INTERNAL, 500)
            )
    
    def _process_payment(self, request: HttpRequest) -> Optional[HttpResponse]:
        """
        Process payment logic.
        
        Direct port of Express payment middleware logic.
        """
        # Check if auth middleware has run (equivalent to Express auth check)
        # Skip this check if REQUIRE_AUTH is False (for payment-only scenarios)
        
        # Debug: Check auth state
        print(f"[PAYMENT DEBUG] require_auth: {self.require_auth}")
        print(f"[PAYMENT DEBUG] has request.auth: {hasattr(request, 'auth')}")
        if hasattr(request, 'auth'):
            print(f"[PAYMENT DEBUG] request.auth.identity_key: {getattr(request.auth, 'identity_key', 'NO IDENTITY_KEY')}")
        
        if self.require_auth and (not hasattr(request, 'auth') or not hasattr(request.auth, 'identity_key')):
            logger.error("Payment middleware executed before Auth middleware")
            return JsonResponse({
                'status': 'error',
                'code': ERR_SERVER_MISCONFIGURED,
                'description': 'The payment middleware must be executed after the Auth middleware.'
            }, status=500)
        
        # If auth middleware is not required, create a minimal auth object
        if not self.require_auth and not hasattr(request, 'auth'):
            from types import SimpleNamespace
            request.auth = SimpleNamespace(identity_key=None)
        
        # Calculate request price (equivalent to Express calculateRequestPrice)
        try:
            request_price = self.calculate_request_price(request)
            if isinstance(request_price, float):
                request_price = int(request_price)  # Convert to satoshis
        except Exception as e:
            logger.error(f"Error calculating request price: {e}")
            return JsonResponse({
                'status': 'error',
                'code': ERR_PAYMENT_INTERNAL,
                'description': 'An internal error occurred while determining the payment required for this request.'
            }, status=500)
        
        # If no payment required, proceed (equivalent to Express requestPrice === 0)
        if request_price == 0:
            request.payment = PaymentInfo(satoshis_paid=0)
            return None  # Continue processing
        
        # Check for payment header (equivalent to Express bsvPaymentHeader check)
        bsv_payment_header = request.headers.get(BSV_PAYMENT_HEADER)
        
        print(f"[PAYMENT DEBUG] BSV_PAYMENT_HEADER: {BSV_PAYMENT_HEADER}")
        print(f"[PAYMENT DEBUG] bsv_payment_header exists: {bool(bsv_payment_header)}")
        if bsv_payment_header:
            print(f"[PAYMENT DEBUG] payment header length: {len(bsv_payment_header)}")
            print(f"[PAYMENT DEBUG] payment header preview: {bsv_payment_header[:100]}...")
        
        if not bsv_payment_header:
            # Request payment (equivalent to Express 402 response)
            print(f"[PAYMENT DEBUG] No payment header, requesting payment: {request_price} satoshis")
            return self._request_payment(request, request_price)
        
        # Verify and process payment
        return self._verify_payment(request, bsv_payment_header, request_price)
    
    def _request_payment(self, request: HttpRequest, required_satoshis: int) -> JsonResponse:
        """
        Request payment with 402 status.
        
        Equivalent to Express 402 Payment Required response.
        """
        try:
            # Create derivation prefix (equivalent to Express createNonce)
            derivation_prefix = self.py_sdk_bridge.create_nonce()
            
            response = JsonResponse({
                'status': 'error',
                'code': ERR_PAYMENT_REQUIRED,
                'satoshisRequired': required_satoshis,
                'description': 'A BSV payment is required to complete this request. Provide the X-BSV-Payment header.'
            }, status=402)
            
            # Set payment headers (equivalent to Express res.set())
            response[BSV_PAYMENT_VERSION_HEADER] = PAYMENT_VERSION
            response[BSV_PAYMENT_SATOSHIS_REQUIRED_HEADER] = str(required_satoshis)
            response[BSV_PAYMENT_DERIVATION_PREFIX_HEADER] = derivation_prefix
            
            logger.info(f"Requesting payment: {required_satoshis} satoshis")
            return response
            
        except Exception as e:
            logger.error(f"Error requesting payment: {e}")
            return JsonResponse({
                'status': 'error',
                'code': ERR_PAYMENT_INTERNAL,
                'description': 'Failed to generate payment request.'
            }, status=500)
    
    def _verify_payment(
        self,
        request: HttpRequest,
        payment_header: str,
        request_price: int
    ) -> Optional[HttpResponse]:
        """
        Verify and process the payment.
        
        Equivalent to Express payment verification and wallet.internalizeAction.
        """
        try:
            # Parse payment data (equivalent to Express JSON.parse)
            payment_data = self.py_sdk_bridge.parse_payment_header(payment_header)
            
            # Verify nonce (equivalent to Express verifyNonce)
            if not self.py_sdk_bridge.verify_nonce(payment_data.derivation_prefix):
                raise BSVInvalidDerivationPrefixException()
            
            # Process payment through wallet (equivalent to Express wallet.internalizeAction)
            result = self.py_sdk_bridge.internalize_action(payment_data)
            
            accepted = result.get('accepted', False)
            
            # Set payment info on request (TypeScript equivalent: req.payment)
            # TypeScript: { satoshisPaid, accepted, tx: paymentData.transaction }
            payment_info = PaymentInfo(
                satoshis_paid=request_price,
                accepted=accepted,
                transaction_id=payment_data.transaction  # TypeScript: tx field (transaction data, not TXID)
            )
            
            print(f"[PAYMENT DEBUG] Payment processed - TypeScript equivalent")
            print(f"[PAYMENT DEBUG] satoshis_paid: {request_price}")
            print(f"[PAYMENT DEBUG] accepted: {accepted}")
            print(f"[PAYMENT DEBUG] transaction_data: {payment_data.transaction[:40] if payment_data.transaction else 'None'}...")
            
            # Set both attributes for compatibility
            request.payment = payment_info
            request.bsv_payment = payment_info  # For utils.py compatibility
            
            # Add success header (equivalent to Express res.set)
            # This will be added in process_response if needed
            request._bsv_payment_success = str(request_price)
            
            logger.info(f"Payment processed successfully: {request_price} satoshis, accepted: {accepted}")
            return None  # Continue processing
            
        except BSVMalformedPaymentException:
            raise
        except BSVInvalidDerivationPrefixException:
            raise
        except Exception as e:
            logger.error(f"Payment verification failed: {e}")
            error_code = getattr(e, 'code', ERR_PAYMENT_INTERNAL)
            error_message = getattr(e, 'message', str(e)) or 'Payment failed.'
            
            return JsonResponse({
                'status': 'error',
                'code': error_code,
                'description': error_message
            }, status=400)
    
    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """
        Django middleware process_response hook.
        
        Add payment success headers if payment was processed.
        """
        try:
            # Add payment success header if payment was processed
            if hasattr(request, '_bsv_payment_success'):
                response[BSV_PAYMENT_SATOSHIS_PAID_HEADER] = request._bsv_payment_success
            
            return response
            
        except Exception as e:
            logger.error(f"Error in payment process_response: {e}")
            return response  # Return original response on error
    
    def _build_error_response(self, exception: BSVPaymentException) -> JsonResponse:
        """
        Build error response from BSV payment exception.
        
        Equivalent to Express error responses.
        """
        return JsonResponse(
            {
                'status': 'error',
                'code': exception.code,
                'description': exception.message,
                **exception.details
            },
            status=exception.status_code
        )


def create_payment_middleware(options: PaymentMiddlewareOptions) -> BSVPaymentMiddleware:
    """
    Factory function to create BSV payment middleware with options.
    
    This function is equivalent to Express createPaymentMiddleware() but returns
    a Django middleware class instead of a function.
    
    Args:
        options: Payment middleware options
        
    Returns:
        Configured BSVPaymentMiddleware instance
    """
    # Set Django settings based on options
    if not hasattr(settings, 'BSV_MIDDLEWARE'):
        settings.BSV_MIDDLEWARE = {}
    
    settings.BSV_MIDDLEWARE.update({
        'WALLET': options.wallet,
        'CALCULATE_REQUEST_PRICE': options.calculate_request_price
    })
    
    return BSVPaymentMiddleware()
