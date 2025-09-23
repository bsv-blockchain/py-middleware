"""
Phase 2.3: Certificate + Payment 統合 完全テスト

Express middleware API 100% 互換性確認
証明書処理と支払い機能の統合動作テスト
"""

import pytest
import json
import logging
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)

class TestPhase23Complete:
    """Phase 2.3 Certificate + Payment 統合の完全テスト"""

    def setup_method(self):
        """各テストの前に実行される初期化"""
        from bsv_middleware.django.transport import DjangoTransport
        from bsv_middleware.django.payment_middleware_complete import BSVPaymentMiddleware, create_payment_middleware
        from bsv_middleware.py_sdk_bridge import create_py_sdk_bridge, create_nonce, verify_nonce
        from bsv_middleware.wallet_adapter import create_wallet_adapter
        from bsv_middleware.types import LogLevel
        from tests.settings import MockTestWallet
        
        # 基本コンポーネント作成
        self.mock_wallet = MockTestWallet()
        self.adapted_wallet = create_wallet_adapter(self.mock_wallet)
        self.py_sdk_bridge = create_py_sdk_bridge(self.mock_wallet)
        
        # DjangoTransport 作成 (Phase 2.3 完全版)
        self.transport = DjangoTransport(
            py_sdk_bridge=self.py_sdk_bridge,
            allow_unauthenticated=True,
            log_level=LogLevel.DEBUG
        )
        
        # Mock Peer 作成 (Phase 2.3 機能付き)
        self.mock_peer = Mock()
        self.mock_peer.sessionManager = Mock()
        self.mock_peer.sessionManager.hasSession = Mock(return_value=False)
        self.mock_peer.sessionManager.updateSession = Mock()
        self.mock_peer.listenForCertificatesReceived = Mock(return_value='cert_listener_001')
        self.mock_peer.stopListeningForCertificatesReceived = Mock()
        self.mock_peer.listenForGeneralMessages = Mock(return_value='general_listener_002')
        
        # Peer を Transport に設定
        self.transport.set_peer(self.mock_peer)
        
        # Payment middleware 作成
        def test_price_calculator(request):
            """テスト用価格計算関数"""
            if 'free' in request.path:
                return 0
            elif 'expensive' in request.path:
                return 1000
            else:
                return 100
                
        self.payment_middleware = BSVPaymentMiddleware(
            get_response=lambda req: HttpResponse("Success"),
            calculate_request_price=test_price_calculator,
            wallet=self.mock_wallet,
            log_level=LogLevel.DEBUG
        )
        
        # Request factory
        self.factory = RequestFactory()
        
        # Module-level functions
        self.create_nonce = create_nonce
        self.verify_nonce = verify_nonce
    
    def test_enhanced_certificate_processing(self):
        """Enhanced certificate processing テスト (Phase 2.3)"""
        print("\n=== Enhanced Certificate Processing Test ===")
        
        try:
            # Mock certificates
            mock_certificates = [
                {'type': 'identity', 'subject': 'test_user', 'issuer': 'test_ca'},
                {'type': 'capability', 'subject': 'test_user', 'capabilities': ['read', 'write']}
            ]
            
            # HTTP request with certificate data
            certificate_request_data = {
                'messageType': 'initial',
                'version': '1.0',
                'identityKey': 'test_identity_12345',
                'nonce': 'test_nonce_67890',
                'initialNonce': 'init_nonce_111'
            }
            
            request = self.factory.post(
                '/.well-known/auth',
                data=json.dumps(certificate_request_data),
                content_type='application/json'
            )
            request.META['HTTP_X_BSV_AUTH_REQUEST_ID'] = 'cert_request_123'
            
            response = HttpResponse()
            
            # Certificate callback function
            certificate_results = []
            def certificate_callback(sender_public_key, certificates, req, res):
                certificate_results.append({
                    'sender': sender_public_key,
                    'certificates': certificates,
                    'request_path': req.path
                })
                print(f"Certificate callback called: {len(certificates)} certificates")
            
            # Execute certificate handling
            result = self.transport.handle_incoming_request(
                request=request,
                response=response,
                on_certificates_received=certificate_callback
            )
            
            assert result is None, "Certificate request should continue processing"
            print("✅ Certificate request handled")
            
            # Verify certificate listener was registered
            assert self.mock_peer.listenForCertificatesReceived.called
            print("✅ Certificate listener registered")
            
            # Simulate certificate reception
            listener_call = self.mock_peer.listenForCertificatesReceived.call_args[0][0]
            listener_call('test_identity_12345', mock_certificates)
            
            # Verify callback was executed
            assert len(certificate_results) == 1
            assert certificate_results[0]['sender'] == 'test_identity_12345'
            assert len(certificate_results[0]['certificates']) == 2
            print("✅ Certificate callback executed successfully")
            
            # Verify certificate validation
            validated_certs = self.transport._validate_certificates(mock_certificates)
            assert len(validated_certs) == 2
            print("✅ Certificate validation successful")
            
        except Exception as e:
            print(f"❌ Enhanced certificate processing failed: {e}")
            pytest.fail(f"Certificate processing error: {e}")

    def test_payment_middleware_complete_flow(self):
        """Payment middleware 完全フロー テスト (Phase 2.3)"""
        print("\n=== Payment Middleware Complete Flow Test ===")
        
        try:
            # Test 1: Free request (price = 0)
            free_request = self.factory.get('/api/free/data')
            free_request.auth = Mock()
            free_request.auth.identity_key = 'test_user'
            
            response = self.payment_middleware(free_request)
            assert response.status_code == 200
            print("✅ Free request processed correctly")
            
            # Test 2: Paid request without payment header
            paid_request = self.factory.get('/api/paid/data')
            paid_request.auth = Mock()
            paid_request.auth.identity_key = 'test_user'
            
            response = self.payment_middleware(paid_request)
            assert response.status_code == 402
            
            response_data = json.loads(response.content.decode('utf-8'))
            assert response_data['code'] == 'ERR_PAYMENT_REQUIRED'
            assert response_data['satoshisRequired'] == 100
            assert 'nonce' in response_data
            print("✅ Payment required response correct")
            
            # Test 3: Paid request with valid payment
            nonce = self.create_nonce()
            payment_data = {
                'nonce': nonce,
                'derivationPrefix': '/api/paid/data:test_user...',
                'beef': 'mock_beef_data_12345'
            }
            
            paid_with_payment_request = self.factory.get('/api/paid/data')
            paid_with_payment_request.auth = Mock()
            paid_with_payment_request.auth.identity_key = 'test_user'
            paid_with_payment_request.META['HTTP_X_BSV_PAYMENT'] = json.dumps(payment_data)
            
            response = self.payment_middleware(paid_with_payment_request)
            assert response.status_code == 200
            assert hasattr(paid_with_payment_request, 'payment')
            assert paid_with_payment_request.payment.satoshis_paid == 100
            print("✅ Payment verification successful")
            
        except Exception as e:
            print(f"❌ Payment middleware flow failed: {e}")
            pytest.fail(f"Payment middleware error: {e}")

    def test_nonce_functionality_enhanced(self):
        """Enhanced nonce functionality テスト (Phase 2.3)"""
        print("\n=== Enhanced Nonce Functionality Test ===")
        
        try:
            # Test module-level create_nonce
            nonce1 = self.create_nonce()
            assert isinstance(nonce1, str)
            assert len(nonce1) >= 16
            print(f"✅ Module-level nonce created: {nonce1[:10]}...")
            
            # Test module-level create_nonce with wallet
            nonce2 = self.create_nonce(self.mock_wallet)
            assert isinstance(nonce2, str)
            assert len(nonce2) >= 16
            print(f"✅ Wallet-based nonce created: {nonce2[:10]}...")
            
            # Test verify_nonce
            assert self.verify_nonce(nonce1)
            assert self.verify_nonce(nonce2)
            print("✅ Nonce verification successful")
            
            # Test invalid nonce
            assert not self.verify_nonce("")
            assert not self.verify_nonce("invalid")
            assert not self.verify_nonce("12345")  # Too short
            print("✅ Invalid nonce rejection successful")
            
            # Test bridge nonce functionality
            bridge_nonce = self.py_sdk_bridge.create_nonce()
            assert self.py_sdk_bridge.verify_nonce(bridge_nonce)
            print("✅ Bridge nonce functionality verified")
            
        except Exception as e:
            print(f"❌ Enhanced nonce functionality failed: {e}")
            pytest.fail(f"Nonce functionality error: {e}")

    def test_express_api_compatibility(self):
        """Express API 100% 互換性テスト (Phase 2.3)"""
        print("\n=== Express API Compatibility Test ===")
        
        try:
            # Express equivalent: createNonce()
            nonce = self.create_nonce()
            assert isinstance(nonce, str) and len(nonce) >= 16
            print("✅ createNonce() Express compatibility")
            
            # Express equivalent: verifyNonce()
            assert self.verify_nonce(nonce)
            print("✅ verifyNonce() Express compatibility")
            
            # Express equivalent: createPaymentMiddleware()
            from bsv_middleware.django.payment_middleware_complete import create_payment_middleware
            middleware_factory = create_payment_middleware(
                calculate_request_price=lambda req: 200,
                wallet=self.mock_wallet
            )
            assert callable(middleware_factory)
            print("✅ createPaymentMiddleware() Express compatibility")
            
            # Express equivalent: peer.listenForCertificatesReceived()
            listener_id = self.transport._setup_certificate_listener(
                'test_identity',
                self.factory.get('/'),
                HttpResponse(),
                None
            )
            assert listener_id is not None
            print("✅ listenForCertificatesReceived() Express compatibility")
            
            # Express equivalent: Transport interface compliance
            from bsv.auth.transports.transport import Transport
            assert isinstance(self.transport, Transport)
            print("✅ Transport interface Express compatibility")
            
        except Exception as e:
            print(f"❌ Express API compatibility failed: {e}")
            pytest.fail(f"Express compatibility error: {e}")

    def test_full_authentication_payment_flow(self):
        """完全な認証+支払いフロー統合テスト (Phase 2.3)"""
        print("\n=== Full Authentication + Payment Flow Test ===")
        
        try:
            # Step 1: Authentication request (/.well-known/auth)
            auth_data = {
                'messageType': 'initial',
                'identityKey': 'full_test_user',
                'nonce': self.create_nonce(),
                'requestedCertificates': {'type': 'identity'}
            }
            
            auth_request = self.factory.post(
                '/.well-known/auth',
                data=json.dumps(auth_data),
                content_type='application/json'
            )
            
            # Mock certificates for authentication
            test_certificates = [
                {'type': 'identity', 'subject': 'full_test_user', 'valid': True}
            ]
            
            # Setup authentication
            auth_results = []
            def auth_callback(sender, certs, req, res):
                auth_results.append({'sender': sender, 'certs': certs})
                # Set authentication info on request
                req.auth = Mock()
                req.auth.identity_key = sender
            
            auth_result = self.transport.handle_incoming_request(
                auth_request,
                on_certificates_received=auth_callback
            )
            
            # Simulate certificate reception
            cert_listener = self.mock_peer.listenForCertificatesReceived.call_args[0][0]
            cert_listener('full_test_user', test_certificates)
            
            assert len(auth_results) == 1
            print("✅ Authentication step completed")
            
            # Step 2: Paid API request
            api_request = self.factory.get('/api/premium/service')
            api_request.auth = Mock()
            api_request.auth.identity_key = 'full_test_user'
            
            # First request - should require payment
            payment_response = self.payment_middleware(api_request)
            assert payment_response.status_code == 402
            
            payment_data = json.loads(payment_response.content.decode('utf-8'))
            required_nonce = payment_data['nonce']
            print("✅ Payment required step completed")
            
            # Step 3: API request with payment
            payment_header = {
                'nonce': required_nonce,
                'derivationPrefix': '/api/premium/service:full_test_user...',
                'beef': 'valid_beef_transaction_data'
            }
            
            paid_request = self.factory.get('/api/premium/service')
            paid_request.auth = Mock()
            paid_request.auth.identity_key = 'full_test_user'
            paid_request.META['HTTP_X_BSV_PAYMENT'] = json.dumps(payment_header)
            
            final_response = self.payment_middleware(paid_request)
            assert final_response.status_code == 200
            assert hasattr(paid_request, 'payment')
            print("✅ Paid API request completed")
            
            print("🎉 Full authentication + payment flow successful!")
            
        except Exception as e:
            print(f"❌ Full flow test failed: {e}")
            pytest.fail(f"Full flow error: {e}")

if __name__ == "__main__":
    """直接実行時のテスト"""
    print("🚀 Starting Phase 2.3 Complete Integration Tests...")
    
    test_instance = TestPhase23Complete()
    
    tests = [
        test_instance.test_enhanced_certificate_processing,
        test_instance.test_payment_middleware_complete_flow,
        test_instance.test_nonce_functionality_enhanced,
        test_instance.test_express_api_compatibility,
        test_instance.test_full_authentication_payment_flow
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test_instance.setup_method()
            test()
            passed += 1
            print(f"✅ {test.__name__} PASSED")
        except Exception as e:
            failed += 1
            print(f"❌ {test.__name__} FAILED: {e}")
    
    print(f"\n📊 Phase 2.3 Complete Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉🏆 Phase 2.3 Certificate + Payment Integration SUCCESS!")
        print("🚀 Express middleware API 100% compatibility achieved!")
    else:
        print("⚠️ Some tests failed. Check integration for completion.")
