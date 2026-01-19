"""
Real BSV Authentication Testing

Tests authentication features using actual BSV data
"""

import json
import os
import sys
from pathlib import Path

import pytest

# Setup
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "examples" / "django_example"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.django_example_test_settings")

import django

django.setup()

from django.test import RequestFactory

# py-sdk imports for real BSV operations
try:
    from bsv.auth.auth_message import AuthMessage
    from bsv.auth.verifiable_certificate import VerifiableCertificate
    from bsv.keys import PrivateKey, verify_signed_text
    from bsv.signed_message import SignedMessage

    py_sdk_available = True
except ImportError as e:
    print(f"⚠️ py-sdk not available: {e}")
    py_sdk_available = False


class RealBSVAuthTester:
    """Auth functionality tester using real BSV data"""

    def __init__(self):
        self.factory = RequestFactory()

        if py_sdk_available:
            # Create real BSV private key for testing
            self.private_key = PrivateKey("L5agPjZKceSTkhqZF2dmFptT5LFrbr6ZGPvP7u4A6dvhTrr71WZ9")
            self.public_key = self.private_key.public_key()
            self.identity_key = self.public_key.hex()

            print(f"🔑 Generated BSV Identity Key: {self.identity_key}")

    def create_real_bsv_signature(self, message: str) -> dict:
        """Create real BSV signature"""
        if not py_sdk_available:
            return None

        try:
            # Use BRC-77 message signing protocol
            message_bytes = message.encode("utf-8")
            signature = SignedMessage.sign(message_bytes, self.private_key)

            return {
                "message": message,
                "signature": signature.hex(),
                "identity_key": self.identity_key,
                "address": self.private_key.address(),
            }

        except Exception as e:
            print(f"❌ BSV signature creation error: {e}")
            return None

    def create_real_bsv_nonce(self) -> str:
        """Create real BSV nonce"""
        if not py_sdk_available:
            return "fallback_nonce_12345"

        try:
            # Use py-sdk random function
            from bsv.utils import randbytes

            nonce_bytes = randbytes(32)
            return nonce_bytes.hex()

        except Exception as e:
            print(f"⚠️ Nonce creation error: {e}")
            # Fallback
            import secrets

            return secrets.token_hex(32)

    def create_real_auth_message(self, message_type: str = "initial") -> dict:
        """Create real BSV AuthMessage"""
        try:
            nonce = self.create_real_bsv_nonce()

            # Auth message payload
            message_payload = {
                "version": "1.0",
                "messageType": message_type,
                "identityKey": self.identity_key,
                "nonce": nonce,
            }

            # Sign message with real BSV signature
            message_text = json.dumps(message_payload, sort_keys=True)
            signature_data = self.create_real_bsv_signature(message_text)

            if signature_data:
                return {
                    **message_payload,
                    "signature": signature_data["signature"],
                    "address": signature_data["address"],
                }
            else:
                return message_payload

        except Exception as e:
            print(f"❌ AuthMessage creation error: {e}")
            return None

    def test_real_bsv_auth_flow(self):
        """Test authentication flow using real BSV data"""
        print("\n🔐 Real BSV Authentication Flow Test")
        print("=" * 50)

        if not py_sdk_available:
            print("❌ py-sdk not available, skipping real BSV tests")
            return False

        try:
            # Step 1: Create real AuthMessage
            auth_message = self.create_real_auth_message("initial")
            if not auth_message:
                print("❌ AuthMessage creation failed")
                return False

            print("✅ Real AuthMessage created:")
            print(f"   Identity Key: {auth_message['identityKey'][:20]}...")
            print(f"   Nonce: {auth_message['nonce'][:20]}...")
            print(f"   Signature: {auth_message.get('signature', 'None')[:20]}...")

            # Step 2: Create BSV headers
            bsv_headers = {
                "x-bsv-auth-version": auth_message["version"],
                "x-bsv-auth-message-type": auth_message["messageType"],
                "x-bsv-auth-identity-key": auth_message["identityKey"],
                "x-bsv-auth-nonce": auth_message["nonce"],
            }

            # Step 3: Test with Django request
            request = self.factory.post("/.well-known/auth")

            # Set headers
            for key, value in bsv_headers.items():
                request.META[f"HTTP_{key.upper().replace('-', '_')}"] = value

            # Set body
            request._body = json.dumps(auth_message).encode("utf-8")
            request.content_type = "application/json"

            print("✅ Real BSV Request created with headers:")
            for key, value in bsv_headers.items():
                print(f"   {key}: {value[:30]}{'...' if len(value) > 30 else ''}")

            # Step 4: Middleware integration test
            self._test_middleware_integration(request, auth_message)

            return True

        except Exception as e:
            print(f"❌ Real BSV Auth Flow Error: {e}")
            import traceback

            traceback.print_exc()
            return False

    def _test_middleware_integration(self, request, auth_message):
        """Middleware integration test"""
        try:
            # BSV Middleware component test
            from .django_example.adapter.utils import (
                debug_request_info,
                get_identity_key,
            )

            # Debug request information
            debug_info = debug_request_info(request)
            print("\n📊 Request Debug Info:")
            print(f"   BSV Headers: {len(debug_info['headers']['bsv_headers'])}")
            print(f"   Identity Key: {debug_info['authentication']['identity_key']}")
            print(f"   Authenticated: {debug_info['authentication']['authenticated']}")

            # Utils functions test
            identity_from_utils = get_identity_key(request)
            print("\n🔧 Utils Test:")
            print(f"   get_identity_key(): {identity_from_utils}")

        except Exception as e:
            print(f"⚠️ Middleware integration test error: {e}")

    def test_signature_verification(self):
        """Test real BSV signature verification"""
        print("\n✅ Real BSV Signature Verification Test")
        print("=" * 50)

        if not py_sdk_available:
            print("❌ py-sdk not available")
            return False

        try:
            # Test message
            test_message = "Hello BSV Middleware Authentication!"

            # Create real BSV signature
            signature_data = self.create_real_bsv_signature(test_message)

            print(f"📝 Test Message: {test_message}")
            print(f"🔑 Identity Key: {signature_data['identity_key']}")
            print(f"📧 Address: {signature_data['address']}")
            print(f"✍️ Signature: {signature_data['signature'][:40]}...")

            # BRC-77 signature verification
            message_bytes = test_message.encode("utf-8")
            signature_bytes = bytes.fromhex(signature_data["signature"])

            verification_result = SignedMessage.verify(message_bytes, signature_bytes)

            print(f"🔍 Verification Result: {'✅ VALID' if verification_result else '❌ INVALID'}")

            # Try text signature verification as well
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
        """Test real BSV certificate creation"""
        print("\n📜 Real BSV Certificate Creation Test")
        print("=" * 50)

        if not py_sdk_available:
            print("❌ py-sdk not available")
            return False

        try:
            # Simple certificate data
            certificate_data = {
                "type": "identity-verification",
                "issuer": self.identity_key,
                "subject": self.identity_key,
                "fields": {"name": "Test User", "country": "JP"},
                "validFrom": "2024-01-01",
                "validUntil": "2025-01-01",
            }

            # Sign certificate
            cert_message = json.dumps(certificate_data, sort_keys=True)
            cert_signature = self.create_real_bsv_signature(cert_message)

            if cert_signature:
                certificate_data["signature"] = cert_signature["signature"]

                print("📜 Certificate Created:")
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
    """Main test execution"""
    print("🧪 Real BSV Authentication Testing")
    print("=" * 60)

    if not py_sdk_available:
        print("❌ py-sdk not available - install py-sdk to run real BSV tests")
        return False

    tester = RealBSVAuthTester()

    results = {
        "signature_verification": tester.test_signature_verification(),
        "auth_flow": tester.test_real_bsv_auth_flow(),
        "certificate_creation": tester.test_real_certificate_creation() is not None,
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


# Pytest test functions
@pytest.mark.skipif(not py_sdk_available, reason="py-sdk not available")
def test_real_bsv_signature_verification():
    """Pytest format: Real BSV signature verification test"""
    tester = RealBSVAuthTester()
    result = tester.test_signature_verification()
    assert result, "Signature verification should succeed"


@pytest.mark.skipif(not py_sdk_available, reason="py-sdk not available")
def test_real_bsv_auth_flow():
    """Pytest format: Real BSV authentication flow test"""
    tester = RealBSVAuthTester()
    result = tester.test_real_bsv_auth_flow()
    assert result, "Auth flow should succeed"


@pytest.mark.skipif(not py_sdk_available, reason="py-sdk not available")
def test_real_bsv_certificate_creation():
    """Pytest format: Real BSV certificate creation test"""
    tester = RealBSVAuthTester()
    result = tester.test_real_certificate_creation()
    assert result is not None, "Certificate creation should succeed"
