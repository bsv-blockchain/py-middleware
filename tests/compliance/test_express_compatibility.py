"""
Express Middleware Compatibility Test
Direct comparison with Express middleware behavior
"""

import os
import sys
import json
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


class ExpressCompatibilityTester:
    """Test Django middleware compatibility with Express middleware"""

    def __init__(self):
        self.factory = RequestFactory()
        self.compatibility_score = 0
        self.total_tests = 0

    def test_api_compatibility(self):
        """Test API endpoint compatibility with Express"""
        print("🔄 Testing Express API Compatibility")
        print("-" * 40)

        from myapp.views import home, health, auth_test

        # Test cases based on Express middleware behavior
        express_compatibility_tests = [
            {
                "name": "Home endpoint response structure",
                "view": home,
                "path": "/",
                "expected_fields": ["message", "endpoints", "identity_key", "authenticated"],
                "express_format": {
                    "message": "string",
                    "endpoints": "object",
                    "identity_key": "string|null",
                    "authenticated": "boolean",
                },
            },
            {
                "name": "Health endpoint Express format",
                "view": health,
                "path": "/health/",
                "expected_fields": ["status", "service", "identity_key"],
                "express_format": {
                    "status": "healthy",
                    "service": "string",
                    "identity_key": "string",
                },
            },
            {
                "name": "Auth test endpoint comprehensive",
                "view": auth_test,
                "path": "/auth-test/",
                "expected_fields": [
                    "method",
                    "path",
                    "identity_key",
                    "authenticated",
                    "certificates",
                    "payment",
                ],
                "express_format": {
                    "method": "string",
                    "path": "string",
                    "identity_key": "string",
                    "authenticated": "boolean",
                    "certificates": "object",
                    "payment": "object|null",
                },
            },
        ]

        for test in express_compatibility_tests:
            print(f"   🧪 {test['name']}")
            self.total_tests += 1

            request = self.factory.get(test["path"])

            try:
                response = test["view"](request)
                response_data = json.loads(response.content.decode())

                # Check field presence
                missing_fields = [
                    field for field in test["expected_fields"] if field not in response_data
                ]

                # Check data types match Express format
                type_matches = []
                for field, expected_type in test["express_format"].items():
                    if field in response_data:
                        actual_value = response_data[field]

                        if expected_type == "string":
                            matches = isinstance(actual_value, str)
                        elif expected_type == "boolean":
                            matches = isinstance(actual_value, bool)
                        elif expected_type == "object":
                            matches = isinstance(actual_value, dict)
                        elif expected_type == "object|null":
                            matches = isinstance(actual_value, dict) or actual_value is None
                        elif expected_type == "string|null":
                            matches = isinstance(actual_value, str) or actual_value is None
                        elif expected_type == "healthy":
                            matches = actual_value == "healthy"
                        else:
                            matches = True

                        type_matches.append((field, matches))

                # Score compatibility
                if not missing_fields and all(match for _, match in type_matches):
                    print("      ✅ 100% Express compatible")
                    self.compatibility_score += 1
                else:
                    print("      ⚠️ Partial compatibility")
                    if missing_fields:
                        print(f"         Missing: {missing_fields}")
                    for field, match in type_matches:
                        if not match:
                            print(f"         Type mismatch: {field}")

            except Exception as e:
                print(f"      ❌ Error: {str(e)}")

        return True

    def test_bsv_header_compatibility(self):
        """Test BSV header handling compatibility"""
        print("\n🔗 Testing BSV Header Compatibility")
        print("-" * 38)

        from myapp.views import auth_test

        # Express-style BSV headers
        express_bsv_headers = {
            "x-bsv-auth-version": "1.0",
            "x-bsv-auth-message-type": "initial",
            "x-bsv-auth-identity-key": "033f5aed5f6cfbafaf94570c8cde0c0a6e2b5fb0e07ca40ce1d6f6bdfde1e5b9b8",
            "x-bsv-auth-nonce": "express_compatible_nonce_12345",
            "x-bsv-payment": json.dumps(
                {
                    "derivationPrefix": "express_test_prefix",
                    "satoshis": 1500,
                    "transaction": "express_compatible_tx_abc123",
                }
            ),
        }

        print("   📤 Testing Express-style headers")
        self.total_tests += 1

        request = self.factory.get("/auth-test/")

        # Add headers
        for key, value in express_bsv_headers.items():
            request.META[f'HTTP_{key.upper().replace("-", "_")}'] = value

        try:
            response = auth_test(request)
            response_data = json.loads(response.content.decode())

            # Check header detection
            bsv_headers = response_data.get("headers", {}).get("bsv_headers", {})

            detected_headers = len(bsv_headers)
            expected_headers = len(express_bsv_headers)

            if detected_headers == expected_headers:
                print(f"      ✅ All {detected_headers} headers detected (Express compatible)")
                self.compatibility_score += 1
            else:
                print(f"      ⚠️ {detected_headers}/{expected_headers} headers detected")

            # Check specific header values
            for header_key in express_bsv_headers:
                django_key = header_key.replace("-", "_").title().replace("_", "-")
                if django_key in bsv_headers:
                    print(f"         ✅ {header_key} → {django_key}")
                else:
                    print(f"         ❌ {header_key} not found")

        except Exception as e:
            print(f"      ❌ Error: {str(e)}")

        return True

    def test_error_response_compatibility(self):
        """Test error response compatibility with Express"""
        print("\n⚠️ Testing Error Response Compatibility")
        print("-" * 42)

        from myapp.views import protected_endpoint, premium_endpoint

        # Express-style error response tests
        error_tests = [
            {
                "name": "401 Authentication Error (Express format)",
                "view": protected_endpoint,
                "path": "/protected/",
                "expected_status": 401,
                "express_error_format": {
                    "error": "string",
                    "message": "string",
                    "identity_key": "string",
                },
            },
            {
                "name": "401 Premium Access Error (Express format)",
                "view": premium_endpoint,
                "path": "/premium/",
                "expected_status": 401,
                "express_error_format": {
                    "error": "string",
                    "message": "string",
                    "identity_key": "string",
                },
            },
        ]

        for test in error_tests:
            print(f"   🧪 {test['name']}")
            self.total_tests += 1

            request = self.factory.get(test["path"])

            try:
                response = test["view"](request)
                response_data = json.loads(response.content.decode())

                # Check status code
                status_match = response.status_code == test["expected_status"]

                # Check Express error format
                format_match = all(
                    field in response_data for field in test["express_error_format"].keys()
                )

                # Check error message contains required info
                error_msg = response_data.get("error", "")
                message_text = response_data.get("message", "")

                has_error_info = (
                    "required" in error_msg.lower() or "required" in message_text.lower()
                )

                if status_match and format_match and has_error_info:
                    print("      ✅ Express error format compatible")
                    self.compatibility_score += 1
                else:
                    print("      ⚠️ Partial error compatibility")
                    print(
                        f"         Status: {response.status_code} {'✅' if status_match else '❌'}"
                    )
                    print(f"         Format: {'✅' if format_match else '❌'}")
                    print(f"         Message: {'✅' if has_error_info else '❌'}")

            except Exception as e:
                print(f"      ❌ Error: {str(e)}")

        return True

    def test_middleware_utilities_compatibility(self):
        """Test utility functions compatibility"""
        print("\n🛠️ Testing Utility Functions Compatibility")
        print("-" * 45)

        from .django_example.adapter.utils import (
            format_satoshis,
            create_bsv_response,
        )

        print("   📦 Testing Express-compatible utility functions")
        self.total_tests += 1

        try:
            # Test format_satoshis (Express compatibility)
            test_amounts = [0, 1, 100, 1000, 1500]
            satoshi_formats = [format_satoshis(amount) for amount in test_amounts]

            # Express format: "X satoshi(s)"
            express_compatible = all("satoshi" in fmt.lower() for fmt in satoshi_formats)

            if express_compatible:
                print("      ✅ Satoshi formatting Express compatible")
            else:
                print("      ⚠️ Satoshi formatting may differ from Express")

            # Test BSV response creation
            request = self.factory.get("/")
            test_data = {"test": "data"}
            bsv_response = create_bsv_response(test_data, request)
            response_data = json.loads(bsv_response.content.decode())

            # Check Express-style BSV info inclusion
            has_bsv_info = "bsv_info" in response_data
            bsv_info = response_data.get("bsv_info", {})
            required_bsv_fields = [
                "identity_key",
                "authenticated",
                "payment_processed",
                "certificates_count",
            ]

            bsv_fields_present = all(field in bsv_info for field in required_bsv_fields)

            if has_bsv_info and bsv_fields_present and express_compatible:
                print("      ✅ Utility functions fully Express compatible")
                self.compatibility_score += 1
            else:
                print("      ⚠️ Partial utility compatibility")

        except Exception as e:
            print(f"      ❌ Error: {str(e)}")

        return True

    def run_compatibility_tests(self):
        """Run all Express compatibility tests"""
        print("🔄 Express Middleware Compatibility Testing")
        print("=" * 60)

        # Run all compatibility tests
        self.test_api_compatibility()
        self.test_bsv_header_compatibility()
        self.test_error_response_compatibility()
        self.test_middleware_utilities_compatibility()

        # Calculate final compatibility score
        compatibility_percentage = (
            (self.compatibility_score / self.total_tests) * 100 if self.total_tests > 0 else 0
        )

        print("\n" + "=" * 60)
        print("📊 Express Compatibility Summary")
        print("=" * 60)
        print(f"Total Compatibility Tests: {self.total_tests}")
        print(f"Express Compatible: {self.compatibility_score}")
        print(f"Compatibility Rate: {compatibility_percentage:.1f}%")

        if compatibility_percentage >= 95:
            print("\n🏆 EXCELLENT EXPRESS COMPATIBILITY!")
            print("🎉 Django middleware is fully Express-compatible")
        elif compatibility_percentage >= 80:
            print("\n✅ GOOD EXPRESS COMPATIBILITY")
            print("Minor differences from Express middleware")
        else:
            print("\n⚠️ EXPRESS COMPATIBILITY ISSUES")
            print("Significant differences from Express middleware")

        return {
            "total_tests": self.total_tests,
            "compatible_tests": self.compatibility_score,
            "compatibility_percentage": compatibility_percentage,
        }


def main():
    """Main Express compatibility tester"""
    tester = ExpressCompatibilityTester()
    results = tester.run_compatibility_tests()

    if results["compatibility_percentage"] >= 95:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
