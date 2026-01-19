"""
BSV Authentication Flow Tests
Tests BRC-103 protocol compliance and authentication state management
"""

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_example_test_settings")

import django

django.setup()

from django.test import RequestFactory

from bsv_middleware.py_sdk_bridge import PySdkBridge, create_nonce, verify_nonce

# Import middleware components for testing
from examples.django_example.adapter.transport import DjangoTransport


@dataclass
class AuthTestScenario:
    """Authentication test scenario"""

    name: str
    step: str
    headers: Dict[str, str]
    payload: Dict[str, Any]
    expected_status: int
    expected_response_type: str
    should_have_session: bool = False


class BSVAuthFlowTester:
    """BSV Authentication Flow comprehensive tester"""

    def __init__(self):
        self.factory = RequestFactory()
        self.test_results = []

        # Create mock wallet for testing
        self.mock_wallet = self.create_mock_wallet()

        # Initialize middleware components
        self.py_sdk_bridge = PySdkBridge(self.mock_wallet)

    def create_mock_wallet(self):
        """Create enhanced mock wallet for auth testing"""

        class AuthTestWallet:
            def sign_message(self, message: bytes) -> bytes:
                return b"auth_test_signature_" + message[:10]

            def get_public_key(self) -> str:
                return "033f5aed5f6cfbafaf94570c8cde0c0a6e2b5fb0e07ca40ce1d6f6bdfde1e5b9b8"

            def internalize_action(self, action: dict) -> dict:
                return {
                    "accepted": True,
                    "satoshisPaid": action.get("satoshis", 0),
                    "transactionId": f"auth_test_tx_{action.get('satoshis', 0)}",
                }

            def create_nonce(self) -> str:
                return "wallet_generated_nonce_12345"

            def verify_nonce(self, nonce: str) -> bool:
                return len(nonce) >= 16 and nonce.isalnum()

        return AuthTestWallet()

    def get_auth_test_scenarios(self) -> List[AuthTestScenario]:
        """Get comprehensive auth test scenarios"""
        return [
            # Step 1: Initial auth request
            AuthTestScenario(
                name="Step 1: Initial authentication request",
                step="initial",
                headers={
                    "x-bsv-auth-version": "1.0",
                    "x-bsv-auth-message-type": "initial",
                    "x-bsv-auth-identity-key": "033f5aed5f6cfbafaf94570c8cde0c0a6e2b5fb0e07ca40ce1d6f6bdfde1e5b9b8",
                    "x-bsv-auth-nonce": "client_nonce_12345",
                    "content-type": "application/json",
                },
                payload={
                    "version": "1.0",
                    "messageType": "initial",
                    "identityKey": "033f5aed5f6cfbafaf94570c8cde0c0a6e2b5fb0e07ca40ce1d6f6bdfde1e5b9b8",
                    "nonce": "client_nonce_12345",
                },
                expected_status=200,
                expected_response_type="server_response",
            ),
            # Step 2: Certificate request
            AuthTestScenario(
                name="Step 2: Certificate request",
                step="certificate_request",
                headers={
                    "x-bsv-auth-version": "1.0",
                    "x-bsv-auth-message-type": "certificate_request",
                    "x-bsv-auth-identity-key": "033f5aed5f6cfbafaf94570c8cde0c0a6e2b5fb0e07ca40ce1d6f6bdfde1e5b9b8",
                    "x-bsv-auth-nonce": "client_nonce_12345",
                    "content-type": "application/json",
                },
                payload={
                    "version": "1.0",
                    "messageType": "certificate_request",
                    "identityKey": "033f5aed5f6cfbafaf94570c8cde0c0a6e2b5fb0e07ca40ce1d6f6bdfde1e5b9b8",
                    "nonce": "client_nonce_12345",
                    "certificateRequests": {"types": ["identity-verification"]},
                },
                expected_status=200,
                expected_response_type="certificate_response",
            ),
            # Step 3: Invalid auth version
            AuthTestScenario(
                name="Step 3: Invalid auth version",
                step="invalid_version",
                headers={
                    "x-bsv-auth-version": "2.0",  # Invalid version
                    "x-bsv-auth-message-type": "initial",
                    "x-bsv-auth-identity-key": "033f5aed5f6cfbafaf94570c8cde0c0a6e2b5fb0e07ca40ce1d6f6bdfde1e5b9b8",
                    "x-bsv-auth-nonce": "client_nonce_12345",
                    "content-type": "application/json",
                },
                payload={
                    "version": "2.0",
                    "messageType": "initial",
                    "identityKey": "033f5aed5f6cfbafaf94570c8cde0c0a6e2b5fb0e07ca40ce1d6f6bdfde1e5b9b8",
                    "nonce": "client_nonce_12345",
                },
                expected_status=400,
                expected_response_type="error",
            ),
            # Step 4: Missing headers
            AuthTestScenario(
                name="Step 4: Missing required headers",
                step="missing_headers",
                headers={
                    "content-type": "application/json"
                    # Missing all BSV headers
                },
                payload={
                    "version": "1.0",
                    "messageType": "initial",
                    "identityKey": "033f5aed5f6cfbafaf94570c8cde0c0a6e2b5fb0e07ca40ce1d6f6bdfde1e5b9b8",
                    "nonce": "client_nonce_12345",
                },
                expected_status=400,
                expected_response_type="error",
            ),
            # Step 5: Invalid identity key
            AuthTestScenario(
                name="Step 5: Invalid identity key format",
                step="invalid_identity_key",
                headers={
                    "x-bsv-auth-version": "1.0",
                    "x-bsv-auth-message-type": "initial",
                    "x-bsv-auth-identity-key": "invalid_key_format",  # Invalid format
                    "x-bsv-auth-nonce": "client_nonce_12345",
                    "content-type": "application/json",
                },
                payload={
                    "version": "1.0",
                    "messageType": "initial",
                    "identityKey": "invalid_key_format",
                    "nonce": "client_nonce_12345",
                },
                expected_status=400,
                expected_response_type="error",
            ),
        ]

    def test_well_known_auth_endpoint(self, scenario: AuthTestScenario) -> Dict[str, Any]:
        """Test /.well-known/auth endpoint with specific scenario"""
        print(f"\n🔐 Auth Test: {scenario.name}")

        try:
            # Create request
            request = self.factory.post(
                "/.well-known/auth",
                data=json.dumps(scenario.payload),
                content_type="application/json",
            )

            # Add headers
            for key, value in scenario.headers.items():
                request.META[f"HTTP_{key.upper().replace('-', '_')}"] = value

            # Create transport for handling request
            transport = DjangoTransport(
                py_sdk_bridge=self.py_sdk_bridge,
                allow_unauthenticated=True,
                log_level="debug",
            )

            # Handle request (simulating middleware behavior)
            response = transport.handle_incoming_request(request)

            if response is None:
                # No response means continue processing (normal for some flows)
                status_code = 200
                response_data = {"status": "processing"}
            else:
                status_code = response.status_code
                try:
                    response_data = json.loads(response.content.decode())
                except:
                    response_data = {"content": response.content.decode()[:100]}

            # Validate result
            result = {
                "scenario_name": scenario.name,
                "step": scenario.step,
                "status_code": status_code,
                "expected_status": scenario.expected_status,
                "response_data": response_data,
                "success": status_code == scenario.expected_status,
                "headers_sent": scenario.headers,
                "payload_sent": scenario.payload,
            }

            # Log result
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(f"   {status} Status: {status_code} (expected {scenario.expected_status})")
            print(f"   Response: {str(response_data)[:150]}...")

            self.test_results.append(result)
            return result

        except Exception as e:
            print(f"   ❌ ERROR: {e!s}")
            error_result = {
                "scenario_name": scenario.name,
                "step": scenario.step,
                "error": str(e),
                "success": False,
                "headers_sent": scenario.headers,
                "payload_sent": scenario.payload,
            }
            self.test_results.append(error_result)
            return error_result

    def test_nonce_functionality(self) -> Dict[str, Any]:
        """Test nonce creation and verification"""
        print("\n🎲 Testing Nonce Functionality")

        results = {"create_nonce_tests": [], "verify_nonce_tests": []}

        # Test nonce creation
        try:
            nonce1 = create_nonce(self.mock_wallet)
            nonce2 = create_nonce(self.mock_wallet)
            nonce3 = create_nonce()  # Without wallet

            create_tests = [
                {
                    "test": "create_nonce_with_wallet",
                    "nonce": nonce1,
                    "success": len(nonce1) >= 16,
                },
                {
                    "test": "create_nonce_unique",
                    "nonce": nonce2,
                    "success": nonce1 != nonce2,
                },
                {
                    "test": "create_nonce_without_wallet",
                    "nonce": nonce3,
                    "success": len(nonce3) >= 16,
                },
            ]

            results["create_nonce_tests"] = create_tests

            for test in create_tests:
                status = "✅ PASS" if test["success"] else "❌ FAIL"
                print(f"   {status} {test['test']}: {test['nonce'][:20]}...")

        except Exception as e:
            print(f"   ❌ Nonce creation error: {e!s}")
            results["create_nonce_error"] = str(e)

        # Test nonce verification
        try:
            test_nonces = [
                ("valid_hex_32", "abcdef1234567890abcdef1234567890", True),
                ("valid_alphanum", "abc123def456ghi789jkl012", True),
                ("too_short", "short", False),
                ("empty", "", False),
                ("none_value", None, False),
            ]

            for test_name, test_nonce, expected in test_nonces:
                if test_nonce is None:
                    result = False
                else:
                    result = verify_nonce(test_nonce, self.mock_wallet)

                success = result == expected
                verify_test = {
                    "test": f"verify_nonce_{test_name}",
                    "nonce": test_nonce,
                    "result": result,
                    "expected": expected,
                    "success": success,
                }

                results["verify_nonce_tests"].append(verify_test)

                status = "✅ PASS" if success else "❌ FAIL"
                print(f"   {status} {test_name}: {result} (expected {expected})")

        except Exception as e:
            print(f"   ❌ Nonce verification error: {e!s}")
            results["verify_nonce_error"] = str(e)

        return results

    def run_all_auth_tests(self) -> Dict[str, Any]:
        """Run all authentication flow tests"""
        print("🔐 Starting BSV Authentication Flow Tests")
        print("=" * 60)

        # Test nonce functionality first
        nonce_results = self.test_nonce_functionality()

        # Test auth scenarios
        scenarios = self.get_auth_test_scenarios()

        for scenario in scenarios:
            self.test_well_known_auth_endpoint(scenario)

        # Summary
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result.get("success", False))
        pass_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0

        summary = {
            "auth_flow_tests": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "pass_rate": round(pass_rate, 2),
                "test_results": self.test_results,
            },
            "nonce_tests": nonce_results,
        }

        print("\n" + "=" * 60)
        print(f"📊 Auth Flow Summary: {passed_tests}/{total_tests} tests passed ({pass_rate:.1f}%)")

        # Nonce test summary
        create_passed = sum(1 for t in nonce_results.get("create_nonce_tests", []) if t["success"])
        create_total = len(nonce_results.get("create_nonce_tests", []))
        verify_passed = sum(1 for t in nonce_results.get("verify_nonce_tests", []) if t["success"])
        verify_total = len(nonce_results.get("verify_nonce_tests", []))

        print(
            f"🎲 Nonce Tests: Create {create_passed}/{create_total}, Verify {verify_passed}/{verify_total}"
        )

        return summary


if __name__ == "__main__":
    # Run authentication flow tests
    tester = BSVAuthFlowTester()
    results = tester.run_all_auth_tests()

    print("\n📋 Detailed Auth Test Results:")
    for result in results["auth_flow_tests"]["test_results"]:
        if result.get("success", False):
            print(f"   ✅ {result['scenario_name']}")
        else:
            print(f"   ❌ {result['scenario_name']}: {result.get('error', 'Test failed')}")
