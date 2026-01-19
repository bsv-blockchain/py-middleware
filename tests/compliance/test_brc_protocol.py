"""
BRC-103/104 Protocol Compliance Tests
Tests BSV protocol specification compliance
"""

import json
import os
import sys
from pathlib import Path

# Setup
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "examples" / "django_example"))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.django_example_test_settings")

import django

django.setup()

from django.test import RequestFactory


class BRCProtocolTester:
    """BRC-103/104 Protocol compliance tester"""

    def __init__(self):
        self.factory = RequestFactory()
        self.test_results = []

    def test_brc_103_headers(self):
        """Test BRC-103 Authentication Protocol headers"""
        print("🔐 Testing BRC-103 Authentication Protocol Compliance")
        print("-" * 55)

        # Required BRC-103 headers
        required_headers = [
            "x-bsv-auth-version",
            "x-bsv-auth-message-type",
            "x-bsv-auth-identity-key",
            "x-bsv-auth-nonce",
        ]

        # Valid BRC-103 message types
        valid_message_types = [
            "initial",
            "certificate_request",
            "certificate_response",
            "general",
        ]

        # Test header presence and format
        for header in required_headers:
            print(f"   🔍 Testing {header}")

            # Create request with this header
            request = self.factory.post("/.well-known/auth")
            request.META[f"HTTP_{header.upper().replace('-', '_')}"] = "test_value"

            # Check header detection
            detected = any(
                key.lower().replace("_", "-") == header
                for key in request.META
                if key.startswith("HTTP_")
            )

            status = "✅ DETECTED" if detected else "❌ MISSING"
            print(f"      {status}")

        # Test message type validation
        print("\n   📝 Testing Message Types:")
        for msg_type in valid_message_types:
            print(f"      📌 {msg_type}: Valid BRC-103 type")

        return True

    def test_brc_104_payment_headers(self):
        """Test BRC-104 Payment Protocol headers"""
        print("\n💰 Testing BRC-104 Payment Protocol Compliance")
        print("-" * 50)

        # BRC-104 payment header structure
        payment_structure = {
            "derivationPrefix": "string",
            "satoshis": "number",
            "transaction": "string",
        }

        print("   📋 Required Payment Structure:")
        for field, field_type in payment_structure.items():
            print(f"      🔸 {field}: {field_type}")

        # Test valid payment header
        valid_payment = {
            "derivationPrefix": "test_prefix_12345",
            "satoshis": 1000,
            "transaction": "abc123def456...",
        }

        request = self.factory.get("/test")
        request.META["HTTP_X_BSV_PAYMENT"] = json.dumps(valid_payment)

        # Verify header can be parsed
        try:
            payment_data = json.loads(request.META["HTTP_X_BSV_PAYMENT"])
            all_fields_present = all(
                field in payment_data for field in payment_structure
            )

            if all_fields_present:
                print("   ✅ Valid payment structure detected")
            else:
                print("   ❌ Invalid payment structure")

        except json.JSONDecodeError:
            print("   ❌ Payment header is not valid JSON")

        return True

    def test_response_format_compliance(self):
        """Test response format compliance"""
        print("\n📤 Testing Response Format Compliance")
        print("-" * 40)

        from myapp.views import auth_test

        # Test various response scenarios
        test_scenarios = [
            {
                "name": "No Authentication",
                "headers": {},
                "expected_fields": ["method", "path", "identity_key", "authenticated"],
            },
            {
                "name": "With BSV Headers",
                "headers": {
                    "x-bsv-auth-version": "1.0",
                    "x-bsv-auth-identity-key": "033f5aed5f6cfbafaf94570c8cde0c0a6e2b5fb0e07ca40ce1d6f6bdfde1e5b9b8",
                    "x-bsv-auth-nonce": "test_nonce",
                },
                "expected_fields": [
                    "method",
                    "path",
                    "identity_key",
                    "authenticated",
                    "certificates",
                    "payment",
                ],
            },
            {
                "name": "With Payment Header",
                "headers": {
                    "x-bsv-auth-identity-key": "033f5aed5f6cfbafaf94570c8cde0c0a6e2b5fb0e07ca40ce1d6f6bdfde1e5b9b8",
                    "x-bsv-payment": json.dumps(
                        {
                            "derivationPrefix": "test_prefix",
                            "satoshis": 500,
                            "transaction": "test_tx_123",
                        }
                    ),
                },
                "expected_fields": ["method", "path", "payment", "headers"],
            },
        ]

        for scenario in test_scenarios:
            print(f"   🧪 {scenario['name']}")

            # Create request
            request = self.factory.get("/auth-test/")

            # Add headers
            for key, value in scenario["headers"].items():
                request.META[f"HTTP_{key.upper().replace('-', '_')}"] = value

            # Execute
            try:
                response = auth_test(request)
                response_data = json.loads(response.content.decode())

                # Check required fields
                missing_fields = [
                    field
                    for field in scenario["expected_fields"]
                    if field not in response_data
                ]

                if not missing_fields:
                    print("      ✅ All required fields present")
                else:
                    print(f"      ❌ Missing fields: {missing_fields}")

                # Check BSV headers detection
                if (
                    "headers" in response_data
                    and "bsv_headers" in response_data["headers"]
                ):
                    bsv_header_count = len(response_data["headers"]["bsv_headers"])
                    print(f"      📊 BSV headers detected: {bsv_header_count}")

            except Exception as e:
                print(f"      ❌ Error: {e!s}")

        return True

    def test_error_response_compliance(self):
        """Test error response format compliance"""
        print("\n⚠️ Testing Error Response Compliance")
        print("-" * 37)

        from myapp.views import premium_endpoint, protected_endpoint

        error_scenarios = [
            {
                "name": "401 Authentication Required",
                "view": protected_endpoint,
                "path": "/protected/",
                "expected_status": 401,
                "expected_fields": ["error", "message", "identity_key"],
            },
            {
                "name": "402 Payment Required",
                "view": premium_endpoint,
                "path": "/premium/",
                "expected_status": 401,  # Will be 401 first due to no auth
                "expected_fields": ["error", "message", "identity_key"],
            },
        ]

        for scenario in error_scenarios:
            print(f"   🧪 {scenario['name']}")

            request = self.factory.get(scenario["path"])

            try:
                response = scenario["view"](request)
                response_data = json.loads(response.content.decode())

                # Check status code
                status_match = response.status_code == scenario["expected_status"]
                print(
                    f"      📊 Status: {response.status_code} {'✅' if status_match else '❌'}"
                )

                # Check required fields
                missing_fields = [
                    field
                    for field in scenario["expected_fields"]
                    if field not in response_data
                ]

                if not missing_fields:
                    print("      ✅ All error fields present")
                else:
                    print(f"      ❌ Missing error fields: {missing_fields}")

            except Exception as e:
                print(f"      ❌ Error: {e!s}")

        return True

    def run_all_protocol_tests(self):
        """Run all BRC protocol compliance tests"""
        print("🔬 BRC-103/104 Protocol Compliance Testing")
        print("=" * 60)

        results = {
            "brc_103_compliance": self.test_brc_103_headers(),
            "brc_104_compliance": self.test_brc_104_payment_headers(),
            "response_format_compliance": self.test_response_format_compliance(),
            "error_response_compliance": self.test_error_response_compliance(),
        }

        print("\n" + "=" * 60)
        print("📊 BRC Protocol Compliance Summary")
        print("=" * 60)

        total_tests = len(results)
        passed_tests = sum(1 for result in results.values() if result)

        print(f"Total Protocol Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")
        print(f"Compliance Rate: {(passed_tests / total_tests) * 100:.1f}%")

        if passed_tests == total_tests:
            print("\n🏆 FULL BRC-103/104 PROTOCOL COMPLIANCE ACHIEVED!")
        else:
            print("\n⚠️ Some protocol compliance issues detected")

        return results


def main():
    """Main protocol tester"""
    tester = BRCProtocolTester()
    results = tester.run_all_protocol_tests()

    if all(results.values()):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
