"""
Basic tests for BSV middleware functionality.
"""

import pytest
from django.test import TestCase, RequestFactory
from django.http import JsonResponse

from bsv_middleware.types import AuthInfo, PaymentInfo, LogLevel
from bsv_middleware.django.auth_middleware import BSVAuthMiddleware
from bsv_middleware.django.payment_middleware import BSVPaymentMiddleware
from bsv_middleware.django.utils import (
    extract_bsv_headers,
    get_identity_key,
    is_authenticated_request
)
from bsv_middleware.py_sdk_bridge import PySdkBridge
from tests.settings import MockTestWallet


class TestBSVMiddleware(TestCase):
    """Test BSV middleware basic functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.wallet = MockTestWallet()
    
    def test_import_middleware(self):
        """Test that middleware classes can be imported."""
        # This test ensures our basic structure is correct
        self.assertIsNotNone(BSVAuthMiddleware)
        self.assertIsNotNone(BSVPaymentMiddleware)
    
    def test_py_sdk_bridge_creation(self):
        """Test creating py-sdk bridge."""
        bridge = PySdkBridge(self.wallet)
        self.assertIsNotNone(bridge)
        self.assertEqual(bridge.wallet, self.wallet)
    
    def test_py_sdk_bridge_nonce_creation(self):
        """Test nonce creation through py-sdk bridge."""
        bridge = PySdkBridge(self.wallet)
        nonce = bridge.create_nonce()
        self.assertIsInstance(nonce, str)
        self.assertGreater(len(nonce), 0)
    
    def test_py_sdk_bridge_nonce_verification(self):
        """Test nonce verification through py-sdk bridge."""
        bridge = PySdkBridge(self.wallet)
        nonce = "test_nonce"
        result = bridge.verify_nonce(nonce)
        self.assertIsInstance(result, bool)
    
    def test_extract_bsv_headers(self):
        """Test BSV header extraction from request."""
        request = self.factory.get('/test/', HTTP_X_BSV_AUTH_VERSION='1.0')
        headers = extract_bsv_headers(request)
        self.assertIn('X-Bsv-Auth-Version', headers)
        self.assertEqual(headers['X-Bsv-Auth-Version'], '1.0')
    
    def test_auth_info_creation(self):
        """Test AuthInfo data class."""
        auth_info = AuthInfo(identity_key='test_key')
        self.assertEqual(auth_info.identity_key, 'test_key')
        self.assertIsNone(auth_info.certificates)
    
    def test_payment_info_creation(self):
        """Test PaymentInfo data class."""
        payment_info = PaymentInfo(satoshis_paid=100, accepted=True)
        self.assertEqual(payment_info.satoshis_paid, 100)
        self.assertTrue(payment_info.accepted)
    
    def test_get_identity_key_unknown(self):
        """Test getting identity key from unauthenticated request."""
        request = self.factory.get('/test/')
        identity_key = get_identity_key(request)
        self.assertEqual(identity_key, 'unknown')
    
    def test_get_identity_key_authenticated(self):
        """Test getting identity key from authenticated request."""
        request = self.factory.get('/test/')
        request.auth = AuthInfo(identity_key='test_key_123')
        identity_key = get_identity_key(request)
        self.assertEqual(identity_key, 'test_key_123')
    
    def test_is_authenticated_request_false(self):
        """Test unauthenticated request detection."""
        request = self.factory.get('/test/')
        self.assertFalse(is_authenticated_request(request))
    
    def test_is_authenticated_request_true(self):
        """Test authenticated request detection."""
        request = self.factory.get('/test/')
        request.auth = AuthInfo(identity_key='test_key_456')
        self.assertTrue(is_authenticated_request(request))
    
    def test_log_level_enum(self):
        """Test LogLevel enum."""
        self.assertEqual(LogLevel.DEBUG, 'debug')
        self.assertEqual(LogLevel.INFO, 'info')
        self.assertEqual(LogLevel.WARN, 'warn')
        self.assertEqual(LogLevel.ERROR, 'error')


class TestBSVMiddlewareIntegration(TestCase):
    """Integration tests for BSV middleware."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
    
    def test_middleware_allows_unauthenticated(self):
        """Test that middleware allows unauthenticated requests when configured."""
        request = self.factory.get('/test/')
        
        # Add session to request (required by Django middleware)
        from django.contrib.sessions.backends.db import SessionStore
        request.session = SessionStore()
        
        # Create middleware with allow unauthenticated
        def dummy_get_response(req):
            return JsonResponse({'message': 'test'})
        
        auth_middleware = BSVAuthMiddleware(dummy_get_response)
        
        # Process request (should not raise exception)
        try:
            response = auth_middleware.process_request(request)
            # None means continue processing
            self.assertIsNone(response)
        except Exception as e:
            self.fail(f"Middleware raised exception for unauthenticated request: {e}")
    
    def test_payment_middleware_zero_price(self):
        """Test payment middleware with zero price."""
        request = self.factory.get('/test/')
        request.auth = AuthInfo(identity_key='test_key')
        
        # Add session to request
        from django.contrib.sessions.backends.db import SessionStore
        request.session = SessionStore()
        
        # Create middleware with dummy get_response
        def dummy_get_response(req):
            return JsonResponse({'message': 'test'})
        
        payment_middleware = BSVPaymentMiddleware(dummy_get_response)
        payment_middleware.calculate_request_price = lambda req: 0
        
        # Process request (should allow free access)
        response = payment_middleware.process_request(request)
        self.assertIsNone(response)  # Continue processing
        
        # Check payment info was set
        self.assertTrue(hasattr(request, 'payment'))
        self.assertEqual(request.payment.satoshis_paid, 0)


@pytest.mark.django_db
class TestBSVMiddlewarePytest:
    """Pytest-style tests for BSV middleware."""
    
    def test_middleware_basic_functionality(self):
        """Test basic middleware functionality with pytest."""
        factory = RequestFactory()
        request = factory.get('/test/')
        
        # Create dummy get_response function
        def dummy_get_response(req):
            from django.http import JsonResponse
            return JsonResponse({'message': 'test'})
        
        # Test that we can create middleware instances
        auth_middleware = BSVAuthMiddleware(dummy_get_response)
        payment_middleware = BSVPaymentMiddleware(dummy_get_response)
        
        assert auth_middleware is not None
        assert payment_middleware is not None
    
    def test_py_sdk_bridge_with_mock_wallet(self):
        """Test py-sdk bridge with mock wallet."""
        wallet = MockTestWallet()
        bridge = PySdkBridge(wallet)
        
        # Test basic operations
        nonce = bridge.create_nonce()
        assert isinstance(nonce, str)
        assert len(nonce) > 0
        
        # Test nonce verification
        is_valid = bridge.verify_nonce(nonce)
        assert isinstance(is_valid, bool)
        
        # Test wallet operations
        pub_key = wallet.get_public_key()
        assert pub_key == 'test_public_key_033f...'
        
        signature = wallet.sign_message(b'test message')
        assert signature == b'test_signature'
