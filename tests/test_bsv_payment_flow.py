"""
BSV Payment Flow Tests
Tests BRC-104 protocol compliance and payment processing
"""

import json
import os
from dataclasses import dataclass
from typing import Any, Dict, List

# Django setup
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "django_example_test_settings")

import django

django.setup()

from django.http import HttpRequest, JsonResponse
from django.test import RequestFactory

# Import middleware components for testing
from examples.django_example.adapter.payment_middleware_complete import (
    create_payment_middleware,
)


@dataclass
class PaymentTestScenario:
    """Payment test scenario"""

    name: str
    endpoint: str
    required_payment: int
    headers: Dict[str, str]
    expected_status: int
    should_process_payment: bool = False


class BSVPaymentFlowTester:
    """BSV Payment Flow comprehensive tester"""

    def __init__(self):
        self.factory = RequestFactory()
        self.test_results = []

        # Create mock wallet for testing
        self.mock_wallet = self.create_payment_test_wallet()

        # Create payment middleware
        self.payment_middleware = create_payment_middleware(
            calculate_request_price=self.calculate_test_price, wallet=self.mock_wallet
        )

    def create_payment_test_wallet(self):
        """Create enhanced mock wallet for payment testing"""

        class PaymentTestWallet:
            def __init__(self):
                self.processed_payments = []

            def sign_message(self, message: bytes) -> bytes:
                return b"payment_test_signature_" + message[:10]

            def get_public_key(self) -> str:
                return "033f5aed5f6cfbafaf94570c8cde0c0a6e2b5fb0e07ca40ce1d6f6bdfde1e5b9b8"

            def internalize_action(self, action: dict) -> dict:
                """Process payment action with actual amount validation"""
                self.processed_payments.append(action)

                expected_satoshis = action.get("satoshis", 0)
                beef_data = action.get("beef", "")

                # Extract actual payment amount from beef data (test format: test_beef_data_{amount}_{id})
                actual_satoshis = 0
                if beef_data.startswith("test_beef_data_"):
                    try:
                        parts = beef_data.split("_")
                        if len(parts) >= 4:
                            actual_satoshis = int(parts[3])
                    except (ValueError, IndexError):
                        actual_satoshis = 0

                # Real payment validation: actual amount must meet expected amount
                if actual_satoshis >= expected_satoshis and actual_satoshis >= 100:
                    return {
                        "accepted": True,
                        "satoshisPaid": actual_satoshis,
                        "transactionId": f"payment_tx_{actual_satoshis}_{len(self.processed_payments)}",
                    }
                else:
                    return {
                        "accepted": False,
                        "satoshisPaid": actual_satoshis,
                        "transactionId": None,
                        "error": f"Insufficient payment: {actual_satoshis} < {expected_satoshis}",
                    }

            def get_processed_payments(self) -> List[dict]:
                return self.processed_payments.copy()

        return PaymentTestWallet()

    def calculate_test_price(self, request: HttpRequest) -> int:
        """Calculate price for test requests"""
        path = request.path

        if path.startswith("/free/"):
            return 0
        elif path.startswith("/cheap/"):
            return 100
        elif path.startswith("/premium/"):
            return 1000
        elif path.startswith("/expensive/"):
            return 5000
        else:
            return 500  # Default price

    def create_payment_header(
        self,
        satoshis: int,
        endpoint: str = "/premium/",
        identity_key: str = "033f5aed5f6cfbafaf94570c8cde0c0a6e2b5fb0e07ca40ce1d6f6bdfde1e5b9b8",
    ) -> str:
        """Create payment header JSON in BRC-104 format with correct derivation prefix"""
        import secrets

        # Generate derivation prefix in the same format as middleware expects
        derivation_prefix = (
            f"{endpoint}:{identity_key[:20]}..." if identity_key != "unknown" else endpoint
        )

        return json.dumps(
            {
                "nonce": secrets.token_hex(32),  # Required: Random nonce
                "derivationPrefix": derivation_prefix,  # Required: Correct derivation prefix
                "beef": f"test_beef_data_{satoshis}_{secrets.token_hex(8)}",  # Required: BEEF transaction data
            }
        )

    def get_payment_test_scenarios(self) -> List[PaymentTestScenario]:
        """Get comprehensive payment test scenarios"""
        return [
            # Valid payment scenarios
            PaymentTestScenario(
                name="Valid payment - exact amount",
                endpoint="/premium/",
                required_payment=1000,
                headers={
                    "x-bsv-auth-identity-key": "033f5aed5f6cfbafaf94570c8cde0c0a6e2b5fb0e07ca40ce1d6f6bdfde1e5b9b8",
                    "x-bsv-payment": None,  # Will be set in test
                },
                expected_status=200,
                should_process_payment=True,
            ),
            PaymentTestScenario(
                name="Valid payment - overpayment",
                endpoint="/premium/",
                required_payment=1000,
                headers={
                    "x-bsv-auth-identity-key": "033f5aed5f6cfbafaf94570c8cde0c0a6e2b5fb0e07ca40ce1d6f6bdfde1e5b9b8",
                    "x-bsv-payment": None,  # Will be set to 1500 in test
                },
                expected_status=200,
                should_process_payment=True,
            ),
            # Insufficient payment scenarios
            PaymentTestScenario(
                name="Insufficient payment",
                endpoint="/premium/",
                required_payment=1000,
                headers={
                    "x-bsv-auth-identity-key": "033f5aed5f6cfbafaf94570c8cde0c0a6e2b5fb0e07ca40ce1d6f6bdfde1e5b9b8",
                    "x-bsv-payment": None,  # Will be set to 500 in test
                },
                expected_status=402,
                should_process_payment=False,
            ),
            # No payment scenarios
            PaymentTestScenario(
                name="No payment header",
                endpoint="/premium/",
                required_payment=1000,
                headers={
                    "x-bsv-auth-identity-key": "033f5aed5f6cfbafaf94570c8cde0c0a6e2b5fb0e07ca40ce1d6f6bdfde1e5b9b8"
                    # No x-bsv-payment header
                },
                expected_status=402,
                should_process_payment=False,
            ),
            # Invalid payment scenarios
            PaymentTestScenario(
                name="Invalid payment JSON",
                endpoint="/premium/",
                required_payment=1000,
                headers={
                    "x-bsv-auth-identity-key": "033f5aed5f6cfbafaf94570c8cde0c0a6e2b5fb0e07ca40ce1d6f6bdfde1e5b9b8",
                    "x-bsv-payment": "invalid_json_format",
                },
                expected_status=400,
                should_process_payment=False,
            ),
            # Free endpoint scenarios
            PaymentTestScenario(
                name="Free endpoint - no payment required",
                endpoint="/free/test",
                required_payment=0,
                headers={
                    "x-bsv-auth-identity-key": "033f5aed5f6cfbafaf94570c8cde0c0a6e2b5fb0e07ca40ce1d6f6bdfde1e5b9b8"
                },
                expected_status=200,  # Should pass through
                should_process_payment=False,
            ),
            # Authentication scenarios
            PaymentTestScenario(
                name="Payment without authentication",
                endpoint="/premium/",
                required_payment=1000,
                headers={"x-bsv-payment": None},  # Will be set in test, but no auth
                expected_status=401,  # Should require auth first
                should_process_payment=False,
            ),
        ]

    def test_payment_scenario(self, scenario: PaymentTestScenario) -> Dict[str, Any]:
        """Test a specific payment scenario"""
        print(f"\n💰 Payment Test: {scenario.name}")

        try:
            # Create request
            request = self.factory.get(scenario.endpoint)

            # Set up headers
            headers = scenario.headers.copy()

            # Handle payment header setup
            if "x-bsv-payment" in headers and headers["x-bsv-payment"] is None:
                identity_key = headers.get(
                    "x-bsv-auth-identity-key",
                    "033f5aed5f6cfbafaf94570c8cde0c0a6e2b5fb0e07ca40ce1d6f6bdfde1e5b9b8",
                )
                if scenario.name == "Valid payment - overpayment":
                    headers["x-bsv-payment"] = self.create_payment_header(
                        scenario.required_payment + 500, scenario.endpoint, identity_key
                    )
                elif scenario.name == "Insufficient payment":
                    headers["x-bsv-payment"] = self.create_payment_header(
                        scenario.required_payment - 500, scenario.endpoint, identity_key
                    )
                elif scenario.name == "Payment without authentication":
                    headers["x-bsv-payment"] = self.create_payment_header(
                        scenario.required_payment, scenario.endpoint, identity_key
                    )
                else:
                    headers["x-bsv-payment"] = self.create_payment_header(
                        scenario.required_payment, scenario.endpoint, identity_key
                    )

            # Add headers to request
            for key, value in headers.items():
                if value is not None:
                    request.META[f"HTTP_{key.upper().replace('-', '_')}"] = value

            # Mock authentication (required for payment middleware)
            # Payment middleware expects request.auth to be set by auth middleware
            if scenario.name != "Payment without authentication":
                from bsv_middleware.types import AuthInfo

                request.auth = AuthInfo(
                    identity_key=headers.get(
                        "x-bsv-auth-identity-key",
                        "033f5aed5f6cfbafaf94570c8cde0c0a6e2b5fb0e07ca40ce1d6f6bdfde1e5b9b8",
                    ),
                    certificates=[],
                )

            # Mock response for testing
            def mock_get_response(req):
                return JsonResponse(
                    {
                        "message": f"Success for {scenario.endpoint}",
                        "path": req.path,
                        "payment_processed": (
                            hasattr(req, "bsv_payment") and req.bsv_payment.accepted
                            if hasattr(req, "bsv_payment")
                            else False
                        ),
                    }
                )

            # Apply payment middleware
            middleware_instance = self.payment_middleware(mock_get_response)
            response = middleware_instance(request)

            # Parse response
            status_code = response.status_code
            try:
                response_data = json.loads(response.content.decode())
            except:
                response_data = {"content": response.content.decode()[:100]}

            # Check payment processing
            payment_processed = hasattr(request, "bsv_payment") and getattr(
                request.bsv_payment, "accepted", False
            )

            # Validate result
            result = {
                "scenario_name": scenario.name,
                "endpoint": scenario.endpoint,
                "status_code": status_code,
                "expected_status": scenario.expected_status,
                "response_data": response_data,
                "payment_processed": payment_processed,
                "should_process_payment": scenario.should_process_payment,
                "success": status_code == scenario.expected_status,
                "headers_sent": headers,
            }

            # Additional validation for payment processing
            if scenario.should_process_payment and not payment_processed and status_code == 200:
                result["success"] = False
                result["error"] = "Payment should have been processed but was not"

            # Log result
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            print(f"   {status} Status: {status_code} (expected {scenario.expected_status})")
            print(
                f"   Payment processed: {payment_processed} (expected: {scenario.should_process_payment})"
            )
            print(f"   Response: {str(response_data)[:100]}...")

            self.test_results.append(result)
            return result

        except Exception as e:
            print(f"   ❌ ERROR: {e!s}")
            error_result = {
                "scenario_name": scenario.name,
                "endpoint": scenario.endpoint,
                "error": str(e),
                "success": False,
                "headers_sent": scenario.headers,
            }
            self.test_results.append(error_result)
            return error_result

    def test_payment_calculation(self) -> Dict[str, Any]:
        """Test payment price calculation"""
        print("\n💲 Testing Payment Calculation")

        test_paths = [
            ("/free/test", 0),
            ("/cheap/item", 100),
            ("/premium/service", 1000),
            ("/expensive/luxury", 5000),
            ("/default/path", 500),
        ]

        results = []

        for path, expected_price in test_paths:
            try:
                request = self.factory.get(path)
                calculated_price = self.calculate_test_price(request)

                success = calculated_price == expected_price
                result = {
                    "path": path,
                    "calculated_price": calculated_price,
                    "expected_price": expected_price,
                    "success": success,
                }

                results.append(result)

                status = "✅ PASS" if success else "❌ FAIL"
                print(
                    f"   {status} {path}: {calculated_price} satoshis (expected {expected_price})"
                )

            except Exception as e:
                print(f"   ❌ Error calculating price for {path}: {e!s}")
                results.append({"path": path, "error": str(e), "success": False})

        return {"calculation_tests": results}

    def run_all_payment_tests(self) -> Dict[str, Any]:
        """Run all payment flow tests"""
        print("💰 Starting BSV Payment Flow Tests")
        print("=" * 60)

        # Test payment calculation first
        calculation_results = self.test_payment_calculation()

        # Test payment scenarios
        scenarios = self.get_payment_test_scenarios()

        for scenario in scenarios:
            self.test_payment_scenario(scenario)

        # Summary
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result.get("success", False))
        pass_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0

        # Calculation test summary
        calc_total = len(calculation_results.get("calculation_tests", []))
        calc_passed = sum(
            1 for t in calculation_results.get("calculation_tests", []) if t.get("success", False)
        )

        summary = {
            "payment_flow_tests": {
                "total_tests": total_tests,
                "passed_tests": passed_tests,
                "failed_tests": total_tests - passed_tests,
                "pass_rate": round(pass_rate, 2),
                "test_results": self.test_results,
            },
            "calculation_tests": calculation_results,
            "wallet_state": {"processed_payments": self.mock_wallet.get_processed_payments()},
        }

        print("\n" + "=" * 60)
        print(
            f"📊 Payment Flow Summary: {passed_tests}/{total_tests} tests passed ({pass_rate:.1f}%)"
        )
        print(f"💲 Price Calculation: {calc_passed}/{calc_total} tests passed")
        print(f"🏦 Wallet processed {len(self.mock_wallet.get_processed_payments())} payments")

        return summary


if __name__ == "__main__":
    # Run payment flow tests
    tester = BSVPaymentFlowTester()
    results = tester.run_all_payment_tests()

    print("\n📋 Detailed Payment Test Results:")
    for result in results["payment_flow_tests"]["test_results"]:
        if result.get("success", False):
            print(f"   ✅ {result['scenario_name']}")
        else:
            print(f"   ❌ {result['scenario_name']}: {result.get('error', 'Test failed')}")

    print("\n🏦 Processed Payments:")
    for i, payment in enumerate(results["wallet_state"]["processed_payments"]):
        print(f"   {i + 1}. {payment}")
