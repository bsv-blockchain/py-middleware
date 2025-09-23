"""
DjangoTransport 完全実装テスト

Phase 2.2: Transport + Peer統合実装の完全テスト
Express ExpressTransport同等機能の動作確認
"""

import pytest
import json
import logging
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock
from django.http import HttpRequest, HttpResponse
from django.test import RequestFactory

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logger = logging.getLogger(__name__)

class TestDjangoTransportComplete:
    """DjangoTransport の完全機能テスト"""

    def setup_method(self):
        """各テストの前に実行される初期化"""
        from bsv_middleware.django.transport import DjangoTransport
        from bsv_middleware.py_sdk_bridge import create_py_sdk_bridge
        from bsv_middleware.wallet_adapter import create_wallet_adapter
        from tests.settings import MockTestWallet
        
        # 基本コンポーネント作成
        self.mock_wallet = MockTestWallet()
        self.adapted_wallet = create_wallet_adapter(self.mock_wallet)
        self.py_sdk_bridge = create_py_sdk_bridge(self.mock_wallet)
        
        # DjangoTransport 作成
        from bsv_middleware.types import LogLevel
        self.transport = DjangoTransport(
            py_sdk_bridge=self.py_sdk_bridge,
            allow_unauthenticated=True,
            log_level=LogLevel.DEBUG
        )
        
        # Mock Peer 作成
        self.mock_peer = Mock()
        self.mock_peer.sessionManager = Mock()
        self.mock_peer.sessionManager.hasSession = Mock(return_value=False)
        self.mock_peer.listenForCertificatesReceived = Mock(return_value='listener_001')
        self.mock_peer.listenForGeneralMessages = Mock(return_value='listener_002')
        
        # Peer を Transport に設定
        self.transport.set_peer(self.mock_peer)
        
        # Request factory
        self.factory = RequestFactory()
    
    def test_transport_interface_compliance(self):
        """py-sdk Transport interface 準拠テスト"""
        print("\n=== Transport Interface Compliance Test ===")
        
        try:
            # on_data method test
            callback = Mock()
            result = self.transport.on_data(callback)
            assert result is None, "on_data should return None on success"
            assert self.transport.message_callback == callback
            print("✅ on_data method compliant")
            
            # send method signature test  
            from inspect import signature
            send_sig = signature(self.transport.send)
            params = list(send_sig.parameters.keys())
            assert 'ctx' in params and 'message' in params
            print("✅ send method signature compliant")
            
            # Transport inheritance test
            from bsv.auth.transports.transport import Transport
            assert isinstance(self.transport, Transport)
            print("✅ Transport inheritance confirmed")
            
        except Exception as e:
            print(f"❌ Transport interface compliance failed: {e}")
            pytest.fail(f"Interface compliance error: {e}")

    def test_send_non_general_message(self):
        """Non-general message 送信テスト"""
        print("\n=== Send Non-General Message Test ===")
        
        try:
            # Mock AuthMessage 作成
            mock_message = Mock()
            mock_message.messageType = 'initial'
            mock_message.yourNonce = 'test_nonce_123'
            mock_message.version = '1.0'
            mock_message.identityKey = 'test_identity_key'
            mock_message.nonce = 'my_nonce_456'
            mock_message.signature = b'test_signature_bytes'
            mock_message.requestedCertificates = None
            
            # Handle を事前に設定
            mock_response = HttpResponse()
            handle = {'response': mock_response, 'request': Mock()}
            self.transport.open_non_general_handles['test_nonce_123'] = [handle]
            
            # send メソッド実行
            result = self.transport.send(None, mock_message)
            
            assert result is None, "send should return None on success"
            print("✅ Non-general message sent successfully")
            
            # Response headers 確認
            assert 'x-bsv-auth-version' in mock_response
            assert 'x-bsv-auth-message-type' in mock_response
            assert 'x-bsv-auth-identity-key' in mock_response
            print("✅ BRC-104 compliant headers set")
            
            # Handle が消費されたことを確認
            assert len(self.transport.open_non_general_handles.get('test_nonce_123', [])) == 0
            print("✅ Handle correctly consumed")
            
        except Exception as e:
            print(f"❌ Non-general message send failed: {e}")
            pytest.fail(f"Non-general send error: {e}")

    def test_handle_well_known_auth_endpoint(self):
        """/.well-known/auth エンドポイント処理テスト"""
        print("\n=== Well-Known Auth Endpoint Test ===")
        
        try:
            # Mock AuthMessage データ
            auth_message_data = {
                'messageType': 'initial',
                'version': '1.0',
                'identityKey': 'test_peer_identity',
                'nonce': 'peer_nonce_789',
                'initialNonce': 'init_nonce_101'
            }
            
            # HTTP request 作成
            request = self.factory.post(
                '/.well-known/auth',
                data=json.dumps(auth_message_data),
                content_type='application/json'
            )
            request.META['HTTP_X_BSV_AUTH_REQUEST_ID'] = 'request_123'
            
            # Response 作成
            response = HttpResponse()
            
            # handle_incoming_request 実行
            result = self.transport.handle_incoming_request(
                request=request,
                response=response
            )
            
            # 処理が継続されることを確認 (None return)
            assert result is None, "Well-known auth should return None to continue processing"
            print("✅ Well-known auth endpoint handled")
            
            # Handle が保存されたことを確認
            assert 'request_123' in self.transport.open_non_general_handles
            print("✅ Handle stored for response")
            
            # Certificate listener が設定されたことを確認
            assert self.mock_peer.listenForCertificatesReceived.called
            print("✅ Certificate listener registered")
            
        except Exception as e:
            print(f"❌ Well-known auth handling failed: {e}")
            pytest.fail(f"Well-known auth error: {e}")

    def test_handle_general_message(self):
        """General message 処理テスト"""
        print("\n=== General Message Handling Test ===")
        
        try:
            # General message headers 付きリクエスト作成
            request = self.factory.post(
                '/api/test',
                data=b'test_payload_data',
                content_type='application/octet-stream'
            )
            
            # BRC-104 auth headers 設定
            request.META.update({
                'HTTP_X_BSV_AUTH_VERSION': '1.0',
                'HTTP_X_BSV_AUTH_MESSAGE_TYPE': 'general',
                'HTTP_X_BSV_AUTH_IDENTITY_KEY': 'general_identity_key',
                'HTTP_X_BSV_AUTH_NONCE': 'general_nonce',
                'HTTP_X_BSV_AUTH_REQUEST_ID': 'general_request_456'
            })
            
            response = HttpResponse()
            
            # handle_incoming_request 実行
            result = self.transport.handle_incoming_request(
                request=request,
                response=response
            )
            
            assert result is None, "General message should return None to continue"
            print("✅ General message handled")
            
            # General message listener が設定されたことを確認
            assert self.mock_peer.listenForGeneralMessages.called
            print("✅ General message listener registered")
            
            # Handle が保存されたことを確認
            assert 'general_request_456' in self.transport.open_general_handles
            print("✅ General handle stored")
            
        except Exception as e:
            print(f"❌ General message handling failed: {e}")
            pytest.fail(f"General message error: {e}")

    def test_unauthenticated_request_handling(self):
        """認証されていないリクエストの処理テスト"""
        print("\n=== Unauthenticated Request Handling Test ===")
        
        try:
            # 認証ヘッダーなしのリクエスト
            request = self.factory.get('/api/public')
            
            # allowUnauthenticated = True の場合
            self.transport.allow_unauthenticated = True
            result = self.transport.handle_incoming_request(request)
            
            assert result is None, "Should continue processing when allowUnauthenticated=True"
            assert hasattr(request, 'auth'), "Auth info should be set"
            assert request.auth.identity_key == 'unknown'
            print("✅ Unauthenticated allowed when permitted")
            
            # allowUnauthenticated = False の場合
            self.transport.allow_unauthenticated = False
            result = self.transport.handle_incoming_request(request)
            
            assert result is not None, "Should return response when auth required"
            assert result.status_code == 401, "Should return 401 Unauthorized"
            print("✅ Unauthenticated rejected when required")
            
        except Exception as e:
            print(f"❌ Unauthenticated handling failed: {e}")
            pytest.fail(f"Unauthenticated handling error: {e}")

    def test_brc_protocol_compliance(self):
        """BRC-103/104 プロトコル準拠テスト"""
        print("\n=== BRC Protocol Compliance Test ===")
        
        try:
            # BRC-104 compliant headers のテスト
            mock_message = Mock()
            mock_message.version = '1.0'
            mock_message.messageType = 'response'
            mock_message.identityKey = 'brc_identity_key'
            mock_message.nonce = 'brc_nonce'
            mock_message.yourNonce = 'brc_your_nonce'
            mock_message.signature = b'\x01\x02\x03\x04'
            mock_message.requestedCertificates = {'type': 'test'}
            
            headers = self.transport._build_auth_response_headers(mock_message)
            
            # 必須ヘッダーの確認
            expected_headers = [
                'x-bsv-auth-version',
                'x-bsv-auth-message-type', 
                'x-bsv-auth-identity-key',
                'x-bsv-auth-nonce',
                'x-bsv-auth-your-nonce',
                'x-bsv-auth-signature',
                'x-bsv-auth-requested-certificates'
            ]
            
            for header in expected_headers:
                assert header in headers, f"Missing required header: {header}"
            
            print("✅ All BRC-104 headers present")
            
            # Signature が正しく hex エンコードされているか確認
            assert headers['x-bsv-auth-signature'] == '01020304'
            print("✅ Signature correctly hex encoded")
            
            # Certificates が正しく JSON エンコードされているか確認
            cert_data = json.loads(headers['x-bsv-auth-requested-certificates'])
            assert cert_data['type'] == 'test'
            print("✅ Certificates correctly JSON encoded")
            
        except Exception as e:
            print(f"❌ BRC protocol compliance failed: {e}")
            pytest.fail(f"BRC compliance error: {e}")

    def test_express_equivalence(self):
        """Express ExpressTransport 同等機能確認"""
        print("\n=== Express Equivalence Test ===")
        
        try:
            # Express の主要機能が実装されているか確認
            express_methods = [
                'send',
                'on_data', 
                'handle_incoming_request',
                'set_peer'
            ]
            
            for method in express_methods:
                assert hasattr(self.transport, method), f"Missing Express method: {method}"
            
            print("✅ All Express methods implemented")
            
            # Express の handle 管理システム
            assert hasattr(self.transport, 'open_non_general_handles')
            assert hasattr(self.transport, 'open_general_handles')
            assert isinstance(self.transport.open_non_general_handles, dict)
            assert isinstance(self.transport.open_general_handles, dict)
            print("✅ Express handle management system present")
            
            # Express のログシステム
            assert hasattr(self.transport, '_log')
            print("✅ Express logging system equivalent")
            
        except Exception as e:
            print(f"❌ Express equivalence failed: {e}")
            pytest.fail(f"Express equivalence error: {e}")

if __name__ == "__main__":
    """直接実行時のテスト"""
    print("🚀 Starting DjangoTransport Complete Implementation Tests...")
    
    test_instance = TestDjangoTransportComplete()
    
    tests = [
        test_instance.test_transport_interface_compliance,
        test_instance.test_send_non_general_message,
        test_instance.test_handle_well_known_auth_endpoint,
        test_instance.test_handle_general_message,
        test_instance.test_unauthenticated_request_handling,
        test_instance.test_brc_protocol_compliance,
        test_instance.test_express_equivalence
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
    
    print(f"\n📊 Complete Implementation Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 DjangoTransport Express equivalence confirmed! Phase 2.2 SUCCESS!")
    else:
        print("⚠️ Some tests failed. Express equivalence needs refinement.")
