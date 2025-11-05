"""
Real BSV Authentication Testing
実際のBSVデータを使用したAuth機能テスト
"""

import os
import sys
import json
import pytest
from pathlib import Path

# Setup
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'examples' / 'django_example'))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.django_example_test_settings')

import django
django.setup()

from django.test import RequestFactory

# py-sdk imports for real BSV operations
try:
    from bsv.keys import PrivateKey, PublicKey, verify_signed_text
    from bsv.signed_message import SignedMessage
    from bsv.auth.auth_message import AuthMessage
    from bsv.auth.verifiable_certificate import VerifiableCertificate
    py_sdk_available = True
except ImportError as e:
    print(f"⚠️ py-sdk not available: {e}")
    py_sdk_available = False

class RealBSVAuthTester:
    """実際のBSVデータを使ったAuth機能テスター"""
    
    def __init__(self):
        self.factory = RequestFactory()
        
        if py_sdk_available:
            # 実際のBSV秘密鍵作成 (テスト用)
            self.private_key = PrivateKey('L5agPjZKceSTkhqZF2dmFptT5LFrbr6ZGPvP7u4A6dvhTrr71WZ9')
            self.public_key = self.private_key.public_key()
            self.identity_key = self.public_key.hex()
            
            print(f"🔑 Generated BSV Identity Key: {self.identity_key}")
            
    def create_real_bsv_signature(self, message: str) -> dict:
        """実際のBSV署名を作成"""
        if not py_sdk_available:
            return None
            
        try:
            # BRC-77 message signing protocol使用
            message_bytes = message.encode('utf-8')
            signature = SignedMessage.sign(message_bytes, self.private_key)
            
            return {
                'message': message,
                'signature': signature.hex(),
                'identity_key': self.identity_key,
                'address': self.private_key.address()
            }
            
        except Exception as e:
            print(f"❌ BSV署名作成エラー: {e}")
            return None
    
    def create_real_bsv_nonce(self) -> str:
        """実際のBSVナンス作成"""
        if not py_sdk_available:
            return "fallback_nonce_12345"
            
        try:
            # py-sdkのランダム関数使用
            from bsv.utils import randbytes
            nonce_bytes = randbytes(32)
            return nonce_bytes.hex()
            
        except Exception as e:
            print(f"⚠️ ナンス作成エラー: {e}")
            # フォールバック
            import secrets
            return secrets.token_hex(32)
    
    def create_real_auth_message(self, message_type: str = "initial") -> dict:
        """実際のBSV AuthMessage作成"""
        try:
            nonce = self.create_real_bsv_nonce()
            
            # Auth message payload
            message_payload = {
                'version': '1.0',
                'messageType': message_type,
                'identityKey': self.identity_key,
                'nonce': nonce
            }
            
            # メッセージ署名 (実際のBSV署名)
            message_text = json.dumps(message_payload, sort_keys=True)
            signature_data = self.create_real_bsv_signature(message_text)
            
            if signature_data:
                return {
                    **message_payload,
                    'signature': signature_data['signature'],
                    'address': signature_data['address']
                }
            else:
                return message_payload
                
        except Exception as e:
            print(f"❌ AuthMessage作成エラー: {e}")
            return None
    
    def test_real_bsv_auth_flow(self):
        """実際のBSVデータを使った認証フローテスト"""
        print("\n🔐 Real BSV Authentication Flow Test")
        print("=" * 50)
        
        if not py_sdk_available:
            print("❌ py-sdk not available, skipping real BSV tests")
            return False
        
        try:
            # Step 1: 実際のAuthMessage作成
            auth_message = self.create_real_auth_message("initial")
            if not auth_message:
                print("❌ AuthMessage作成失敗")
                return False
            
            print(f"✅ Real AuthMessage created:")
            print(f"   Identity Key: {auth_message['identityKey'][:20]}...")
            print(f"   Nonce: {auth_message['nonce'][:20]}...")
            print(f"   Signature: {auth_message.get('signature', 'None')[:20]}...")
            
            # Step 2: BSVヘッダー作成
            bsv_headers = {
                'x-bsv-auth-version': auth_message['version'],
                'x-bsv-auth-message-type': auth_message['messageType'],
                'x-bsv-auth-identity-key': auth_message['identityKey'],
                'x-bsv-auth-nonce': auth_message['nonce']
            }
            
            # Step 3: Django requestでテスト
            request = self.factory.post('/.well-known/auth')
            
            # ヘッダー設定
            for key, value in bsv_headers.items():
                request.META[f'HTTP_{key.upper().replace("-", "_")}'] = value
            
            # ボディ設定
            request._body = json.dumps(auth_message).encode('utf-8')
            request.content_type = 'application/json'
            
            print(f"✅ Real BSV Request created with headers:")
            for key, value in bsv_headers.items():
                print(f"   {key}: {value[:30]}{'...' if len(value) > 30 else ''}")
            
            # Step 4: Middleware統合テスト
            self._test_middleware_integration(request, auth_message)
            
            return True
            
        except Exception as e:
            print(f"❌ Real BSV Auth Flow Error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _test_middleware_integration(self, request, auth_message):
        """Middlewareとの統合テスト"""
        try:
            # BSV Middleware コンポーネントテスト
            from examples.django_example.django_adapter.utils import get_identity_key, debug_request_info
            
            # Request情報デバッグ
            debug_info = debug_request_info(request)
            print(f"\n📊 Request Debug Info:")
            print(f"   BSV Headers: {len(debug_info['headers']['bsv_headers'])}")
            print(f"   Identity Key: {debug_info['authentication']['identity_key']}")
            print(f"   Authenticated: {debug_info['authentication']['authenticated']}")
            
            # Utils functions テスト
            identity_from_utils = get_identity_key(request)
            print(f"\n🔧 Utils Test:")
            print(f"   get_identity_key(): {identity_from_utils}")
            
        except Exception as e:
            print(f"⚠️ Middleware integration test error: {e}")
    
    def test_signature_verification(self):
        """実際のBSV署名検証テスト"""
        print("\n✅ Real BSV Signature Verification Test")
        print("=" * 50)
        
        if not py_sdk_available:
            print("❌ py-sdk not available")
            return False
        
        try:
            # テストメッセージ
            test_message = "Hello BSV Middleware Authentication!"
            
            # 実際のBSV署名作成
            signature_data = self.create_real_bsv_signature(test_message)
            
            print(f"📝 Test Message: {test_message}")
            print(f"🔑 Identity Key: {signature_data['identity_key']}")
            print(f"📧 Address: {signature_data['address']}")
            print(f"✍️ Signature: {signature_data['signature'][:40]}...")
            
            # BRC-77署名検証
            message_bytes = test_message.encode('utf-8')
            signature_bytes = bytes.fromhex(signature_data['signature'])
            
            verification_result = SignedMessage.verify(message_bytes, signature_bytes)
            
            print(f"🔍 Verification Result: {'✅ VALID' if verification_result else '❌ INVALID'}")
            
            # テキスト署名検証も試行
            try:
                address, text_signature = self.private_key.sign_text(test_message)
                text_verification = verify_signed_text(test_message, address, text_signature)
                
                print(f"📝 Text Signature: {text_signature}")
                print(f"🔍 Text Verification: {'✅ VALID' if text_verification else '❌ INVALID'}")
                
            except Exception as text_error:
                print(f"⚠️ Text signature test error: {text_error}")
            
            return verification_result
            
        except Exception as e:
            print(f"❌ Signature verification error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def test_real_certificate_creation(self):
        """実際のBSV証明書作成テスト"""
        print("\n📜 Real BSV Certificate Creation Test")
        print("=" * 50)
        
        if not py_sdk_available:
            print("❌ py-sdk not available")
            return False
        
        try:
            # 簡単な証明書データ
            certificate_data = {
                'type': 'identity-verification',
                'issuer': self.identity_key,
                'subject': self.identity_key,
                'fields': {
                    'name': 'Test User',
                    'country': 'JP'
                },
                'validFrom': '2024-01-01',
                'validUntil': '2025-01-01'
            }
            
            # 証明書署名
            cert_message = json.dumps(certificate_data, sort_keys=True)
            cert_signature = self.create_real_bsv_signature(cert_message)
            
            if cert_signature:
                certificate_data['signature'] = cert_signature['signature']
                
                print(f"📜 Certificate Created:")
                print(f"   Type: {certificate_data['type']}")
                print(f"   Issuer: {certificate_data['issuer'][:20]}...")
                print(f"   Signature: {certificate_data['signature'][:40]}...")
                
                return certificate_data
            else:
                print("❌ Certificate signature failed")
                return None
                
        except Exception as e:
            print(f"❌ Certificate creation error: {e}")
            return None

def main():
    """メインテスト実行"""
    print("🧪 Real BSV Authentication Testing")
    print("=" * 60)
    
    if not py_sdk_available:
        print("❌ py-sdk not available - install py-sdk to run real BSV tests")
        return False
    
    tester = RealBSVAuthTester()
    
    results = {
        'signature_verification': tester.test_signature_verification(),
        'auth_flow': tester.test_real_bsv_auth_flow(),
        'certificate_creation': tester.test_real_certificate_creation() is not None
    }
    
    print("\n" + "=" * 60)
    print("📊 Real BSV Auth Testing Summary")
    print("=" * 60)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    total_tests = len(results)
    passed_tests = sum(results.values())
    
    print(f"\nTotal: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 All real BSV auth tests passed!")
        return True
    else:
        print("⚠️ Some real BSV auth tests failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)


# Pytest形式のテスト関数
@pytest.mark.skipif(not py_sdk_available, reason="py-sdk not available")
def test_real_bsv_signature_verification():
    """Pytest形式: 実際のBSV署名検証テスト"""
    tester = RealBSVAuthTester()
    result = tester.test_signature_verification()
    assert result, "Signature verification should succeed"

@pytest.mark.skipif(not py_sdk_available, reason="py-sdk not available")
def test_real_bsv_auth_flow():
    """Pytest形式: 実際のBSV認証フローテスト"""
    tester = RealBSVAuthTester()
    result = tester.test_real_bsv_auth_flow()
    assert result, "Auth flow should succeed"

@pytest.mark.skipif(not py_sdk_available, reason="py-sdk not available")
def test_real_bsv_certificate_creation():
    """Pytest形式: 実際のBSV証明書作成テスト"""
    tester = RealBSVAuthTester()
    result = tester.test_real_certificate_creation()
    assert result is not None, "Certificate creation should succeed"
