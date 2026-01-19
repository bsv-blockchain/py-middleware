"""
Comprehensive API tests for Django Example
Tests Express middleware compatibility and BSV protocol compliance
"""

import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_example_test_settings")

import django

django.setup()

from django.test import Client, RequestFactory

# Import all views for testing
from examples.django_example.myapp.views import (
    auth_test,
    decorator_auth_example,
    decorator_payment_example,
    health,
    home,
    premium_endpoint,
    protected_endpoint,
    public_endpoint,
)


@dataclass
class APITestCase:
    """API test case definition"""

    name: str
    endpoint: str
    method: str = "GET"
    headers: Dict[str, str] = None
    data: Dict[str, Any] = None
    expected_status: int = 200
    expected_fields: List[str] = None
    auth_required: bool = False
    payment_required: int = 0


@dataclass
class BSVHeaders:
    """BSV protocol headers"""

    auth_version: str = "1.0"
    auth_message_type: str = "initial"
    identity_key: str = "033f5aed5f6cfbafaf94570c8cde0c0a6e2b5fb0e07ca40ce1d6f6bdfde1e5b9b8"
    nonce: str = "test_nonce_12345"
    payment: Optional[str] = None


class ComprehensiveAPITester:
    """Comprehensive API testing framework"""

    def __init__(self):
        self.factory = RequestFactory()
        self.client = Client()
        self.test_results = []
        self.failed_tests = []

    def create_bsv_headers(self, bsv_headers: BSVHeaders) -> Dict[str, str]:
        """Create BSV protocol headers"""
        headers = {
            "x-bsv-auth-version": bsv_headers.auth_version,
            "x-bsv-auth-message-type": bsv_headers.auth_message_type,
            "x-bsv-auth-identity-key": bsv_headers.identity_key,
            "x-bsv-auth-nonce": bsv_headers.nonce,
        }

        if bsv_headers.payment:
            headers["x-bsv-payment"] = bsv_headers.payment

        return headers

    def create_payment_header(self, satoshis: int, tx_id: str = "test_tx_123") -> str:
        """Create payment header"""
        return json.dumps(
            {
                "derivationPrefix": "test_prefix",
                "satoshis": satoshis,
                "transaction": tx_id,
            }
        )

    def execute_test_case(self, test_case: APITestCase) -> Dict[str, Any]:
        """Execute a single test case"""
        print(f"\n🧪 Testing: {test_case.name}")

        try:
            # Prepare request
            if test_case.method == "GET":
                request = self.factory.get(test_case.endpoint)
            elif test_case.method == "POST":
                request = self.factory.post(
                    test_case.endpoint,
                    data=test_case.data or {},
                    content_type="application/json",
                )

            # Add headers
            if test_case.headers:
                for key, value in test_case.headers.items():
                    request.META[f"HTTP_{key.upper().replace('-', '_')}"] = value

            # Execute view function
            view_map = {
                "/": home,
                "/health/": health,
                "/public/": public_endpoint,
                "/protected/": protected_endpoint,
                "/premium/": premium_endpoint,
                "/auth-test/": auth_test,
                "/decorator-auth/": decorator_auth_example,
                "/decorator-payment/": decorator_payment_example,
            }

            view_func = view_map.get(test_case.endpoint)
            if not view_func:
                raise ValueError(f"No view function for {test_case.endpoint}")

            response = view_func(request)

            # Parse response
            response_data = json.loads(response.content.decode())

            # Validate results
            result = {
                "test_name": test_case.name,
                "endpoint": test_case.endpoint,
                "status_code": response.status_code,
                "expected_status": test_case.expected_status,
                "response_data": response_data,
                "success": response.status_code == test_case.expected_status,
                "timestamp": datetime.now().isoformat(),
            }

            # Check required fields
            if test_case.expected_fields:
                missing_fields = [
                    field for field in test_case.expected_fields if field not in response_data
                ]
                result["missing_fields"] = missing_fields
                if missing_fields:
                    result["success"] = False

            # Log result
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(
                f"   {status} Status: {response.status_code}, Data: {str(response_data)[:100]}..."
            )

            self.test_results.append(result)
            if not result["success"]:
                self.failed_tests.append(result)

            return result

        except Exception as e:
            print(f"   ❌ ERROR: {e!s}")
            error_result = {
                "test_name": test_case.name,
                "endpoint": test_case.endpoint,
                "error": str(e),
                "success": False,
                "timestamp": datetime.now().isoformat(),
            }
            self.test_results.append(error_result)
            self.failed_tests.append(error_result)
            return error_result


class EndpointCoverageTester(ComprehensiveAPITester):
    """Test all endpoints comprehensively"""

    def get_test_cases(self) -> List[APITestCase]:
        """Define all endpoint test cases"""
        return [
            # Free endpoints
            APITestCase(
                name="Home endpoint - free access",
                endpoint="/",
                expected_fields=[
                    "message",
                    "endpoints",
                    "identity_key",
                    "authenticated",
                ],
            ),
            APITestCase(
                name="Health endpoint - free access",
                endpoint="/health/",
                expected_fields=["status", "service", "identity_key"],
            ),
            APITestCase(
                name="Public endpoint - free access",
                endpoint="/public/",
                expected_fields=["message", "access", "identity_key", "authenticated"],
            ),
            # Protected endpoints (no auth)
            APITestCase(
                name="Protected endpoint - no auth (should fail)",
                endpoint="/protected/",
                expected_status=401,
                expected_fields=["error", "message", "identity_key"],
            ),
            APITestCase(
                name="Premium endpoint - no auth (should fail)",
                endpoint="/premium/",
                expected_status=401,
                expected_fields=["error", "message", "identity_key"],
            ),
            # Auth test endpoint
            APITestCase(
                name="Auth test endpoint - GET",
                endpoint="/auth-test/",
                method="GET",
                expected_fields=[
                    "method",
                    "path",
                    "identity_key",
                    "authenticated",
                    "certificates",
                    "payment",
                ],
            ),
            APITestCase(
                name="Auth test endpoint - POST",
                endpoint="/auth-test/",
                method="POST",
                expected_fields=[
                    "method",
                    "path",
                    "identity_key",
                    "authenticated",
                    "certificates",
                    "payment",
                ],
            ),
            # Decorator endpoints (no auth)
            APITestCase(
                name="Decorator auth example - no auth (should fail)",
                endpoint="/decorator-auth/",
                expected_status=401,
                expected_fields=["error", "message"],
            ),
            APITestCase(
                name="Decorator payment example - no auth (should fail)",
                endpoint="/decorator-payment/",
                expected_status=401,
                expected_fields=["error", "message"],
            ),
        ]

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all endpoint coverage tests"""
        print("🚀 Starting Endpoint Coverage Tests")
        print("=" * 50)

        test_cases = self.get_test_cases()

        for test_case in test_cases:
            self.execute_test_case(test_case)

        # Summary
        total_tests = len(self.test_results)
        passed_tests = total_tests - len(self.failed_tests)
        pass_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0

        summary = {
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_test_count": len(self.failed_tests),
            "pass_rate": round(pass_rate, 2),
            "test_results": self.test_results,
            "failed_tests": self.failed_tests,
        }

        print("\n" + "=" * 50)
        print(f"📊 Test Summary: {passed_tests}/{total_tests} tests passed ({pass_rate:.1f}%)")

        if self.failed_tests:
            print(f"\n❌ Failed Tests ({len(self.failed_tests)}):")
            for failed in self.failed_tests:
                print(f"   - {failed['test_name']}")
        else:
            print("\n🎉 All tests passed!")

        return summary


# Create test settings for Django
def create_test_settings():
    """Create Django test settings"""
    settings_content = """
import sys
import os
from pathlib import Path

# Add examples to Python path
examples_path = os.path.join(os.path.dirname(__file__), '..', 'examples', 'django_example')
sys.path.insert(0, examples_path)

# Import original settings
from myproject.settings import *

# Test-specific settings
DATABASE_NAME = ':memory:'
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': DATABASE_NAME,
    }
}

# Suppress logs during testing
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['null'],
    }
}
"""

    settings_file = os.path.join(os.path.dirname(__file__), "django_example_test_settings.py")
    with open(settings_file, "w") as f:
        f.write(settings_content)


if __name__ == "__main__":
    # Create test settings
    create_test_settings()

    # Run endpoint coverage tests
    tester = EndpointCoverageTester()
    results = tester.run_all_tests()

    # Print detailed results
    print("\n📋 Detailed Results:")
    for result in results["test_results"]:
        if result["success"]:
            print(f"   ✅ {result['test_name']}")
        else:
            print(f"   ❌ {result['test_name']}: {result.get('error', 'Status mismatch')}")
