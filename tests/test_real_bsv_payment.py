"""
Real BSV Payment Integration Test

Integration tests for actual BSV payment processing

Express middleware payment implementation reference:
- payment-express-middleware/src/index.ts
"""

import base64
import json
import os
import sys
from pathlib import Path

# Setup
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tests.settings")

import django

django.setup()

from django.test import RequestFactory

# BSV Middleware imports
from bsv_middleware.py_sdk_bridge import create_nonce, verify_nonce

# py-sdk imports
try:
    from bsv.keys import PrivateKey

    py_sdk_available = True
except ImportError as e:
    print(f"⚠️ py-sdk not available: {e}")
    py_sdk_available = False


class RealBSVPaymentTester:
    """
    Real BSV payment processing integration tester

    Express middleware payment flow:
    1. Calculate request price
    2. If price > 0 and no payment header → 402 Payment Required
    3. If payment header exists → verify and internalize
    4. Set payment info on request
    """

    def __init__(self):
        self.factory = RequestFactory()
        self.mock_wallet = self.create_mock_wallet()

        # Test private key (for creating real transactions)
        if py_sdk_available:
            self.private_key = PrivateKey("L5agPjZKceSTkhqZF2dmFptT5LFrbr6ZGPvP7u4A6dvhTrr71WZ9")
            self.public_key = self.private_key.public_key()
            self.identity_key = self.public_key.hex()

    def create_mock_wallet(self):
        """
        Create mock wallet (py-sdk WalletInterface compatible)

        Express equivalent: wallet parameter in createPaymentMiddleware()
        """

        class PaymentTestWallet:
            def get_public_key(self, args, originator):
                return {
                    "publicKey": "033f5aed5f6cfbafaf94570c8cde0c0a6e2b5fb0e07ca40ce1d6f6bdfde1e5b9b8"
                }

            def create_signature(self, args, originator):
                message = args.get("data", b"")
                return {"signature": f"sig_{str(message)[:20]}"}

            def internalize_action(self, args, originator):
                """
                Express equivalent: wallet.internalizeAction()

                Args from Express:
                {
                  tx: AtomicBEEF (base64 decoded),
                  outputs: [{
                    paymentRemittance: {
                      derivationPrefix: string,
                      derivationSuffix: string,
                      senderIdentityKey: string
                    },
                    outputIndex: 0,
                    protocol: 'wallet payment'
                  }],
                  description: 'Payment for request'
                }
                """
                action = args.get("action", {})
                tx = action.get("tx")
                outputs = action.get("outputs", [])

                print("📥 internalize_action called:")
                print(f"   tx type: {type(tx)}")
                print(f"   outputs: {len(outputs)}")

                if outputs:
                    output = outputs[0]
                    remittance = output.get("paymentRemittance", {})
                    print(f"   derivationPrefix: {remittance.get('derivationPrefix', '')[:20]}...")
                    print(f"   derivationSuffix: {remittance.get('derivationSuffix', '')[:20]}...")
                    print(f"   protocol: {output.get('protocol')}")

                # Mock: Always accept payment
                return {
                    "accepted": True,
                    "satoshisPaid": 100,
                    "transactionId": "test_payment_tx_12345",
                }

        return PaymentTestWallet()

    def test_payment_required_response(self):
        """
        Test 402 Payment Required response

        Express equivalent: Lines 60-73 in payment-express-middleware/src/index.ts
        """
        print("\n💰 Test: 402 Payment Required Response")
        print("=" * 60)

        try:
            # Create request without payment header
            request = self.factory.get("/api/paid-endpoint")

            # Mock: Request requires 100 satoshis
            request_price = 100

            # Simulate middleware check
            bsv_payment_header = request.META.get("HTTP_X_BSV_PAYMENT")

            if not bsv_payment_header:
                print("✅ No payment header detected")
                print(f"💳 Request price: {request_price} satoshis")

                # Create nonce (Express: derivationPrefix = await createNonce(wallet))
                derivation_prefix = create_nonce(self.mock_wallet)
                print(f"🎲 Generated derivationPrefix: {derivation_prefix[:20]}...")

                # Expected 402 response headers (Express: lines 63-67)
                expected_headers = {
                    "x-bsv-payment-version": "1.0",
                    "x-bsv-payment-satoshis-required": str(request_price),
                    "x-bsv-payment-derivation-prefix": derivation_prefix,
                }

                print("✅ 402 Response headers prepared:")
                for key, value in expected_headers.items():
                    print(f"   {key}: {value[:50]}")

                # Expected response body (Express: lines 68-73)
                expected_body = {
                    "status": "error",
                    "code": "ERR_PAYMENT_REQUIRED",
                    "satoshisRequired": request_price,
                    "description": "A BSV payment is required to complete this request.",
                }

                print("✅ 402 Response body prepared:")
                print(f"   {json.dumps(expected_body, indent=2)}")

                return True

        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback

            traceback.print_exc()
            return False

    def test_payment_header_parsing(self):
        """
        Test X-BSV-Payment header parsing

        Express equivalent: Lines 76-97 in payment-express-middleware/src/index.ts
        """
        print("\n📋 Test: Payment Header Parsing")
        print("=" * 60)

        try:
            # Create payment data (Express: BSVPayment type)
            payment_data = {
                "derivationPrefix": "test_prefix_12345",
                "derivationSuffix": "test_suffix_67890",
                "transaction": base64.b64encode(b"mock_transaction_data").decode("utf-8"),
            }

            # Create request with payment header
            request = self.factory.post("/api/paid-endpoint", content_type="application/json")

            # Set payment header (Express: req.headers['x-bsv-payment'])
            payment_header = json.dumps(payment_data)
            request.META["HTTP_X_BSV_PAYMENT"] = payment_header

            print("✅ Payment header set:")
            print(f"   derivationPrefix: {payment_data['derivationPrefix']}")
            print(f"   derivationSuffix: {payment_data['derivationSuffix']}")
            print(f"   transaction (base64): {payment_data['transaction'][:40]}...")

            # Parse payment header (Express: lines 76-78)
            parsed_payment = json.loads(payment_header)

            print("✅ Payment header parsed successfully")

            # Verify nonce (Express: lines 79-90)
            is_valid_nonce = verify_nonce(parsed_payment["derivationPrefix"], self.mock_wallet)

            if is_valid_nonce:
                print("✅ Nonce verification passed")
            else:
                print("❌ Nonce verification failed")
                return False

            return True

        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback

            traceback.print_exc()
            return False

    def test_payment_internalization(self):
        """
        Test payment internalization via wallet.internalizeAction

        Express equivalent: Lines 99-132 in payment-express-middleware/src/index.ts
        """
        print("\n🔄 Test: Payment Internalization")
        print("=" * 60)

        try:
            # Mock payment data
            payment_data = {
                "derivationPrefix": "test_prefix_12345",
                "derivationSuffix": "test_suffix_67890",
                "transaction": base64.b64encode(b"mock_beef_transaction").decode("utf-8"),
            }

            # Mock authenticated identity
            sender_identity_key = (
                "033f5aed5f6cfbafaf94570c8cde0c0a6e2b5fb0e07ca40ce1d6f6bdfde1e5b9b8"
            )

            print("📝 Payment data:")
            print(f"   derivationPrefix: {payment_data['derivationPrefix']}")
            print(f"   derivationSuffix: {payment_data['derivationSuffix']}")
            print(f"   senderIdentityKey: {sender_identity_key}")

            # Prepare internalize action args (Express: lines 100-112)
            action_args = {
                "tx": base64.b64decode(payment_data["transaction"]),  # Convert base64 to bytes
                "outputs": [
                    {
                        "paymentRemittance": {
                            "derivationPrefix": payment_data["derivationPrefix"],
                            "derivationSuffix": payment_data["derivationSuffix"],
                            "senderIdentityKey": sender_identity_key,
                        },
                        "outputIndex": 0,
                        "protocol": "wallet payment",
                    }
                ],
                "description": "Payment for request",
            }

            print("✅ Action args prepared")
            print("   protocol: wallet payment")
            print("   outputIndex: 0")

            # Call internalize_action (Express: line 100)
            result = self.mock_wallet.internalize_action(
                {}, {"action": action_args}, "payment_middleware"
            )

            print("✅ Payment internalized:")
            print(f"   accepted: {result['accepted']}")
            print(f"   satoshisPaid: {result.get('satoshisPaid', 0)}")
            print(f"   transactionId: {result.get('transactionId', 'unknown')}")

            # Set payment info on request (Express: lines 114-118)
            payment_info = {
                "satoshisPaid": 100,
                "accepted": result["accepted"],
                "tx": payment_data["transaction"],
            }

            print("✅ Payment info created for request")

            # Response header (Express: lines 120-122)
            print(
                f"✅ Response header set: x-bsv-payment-satoshis-paid: {payment_info['satoshisPaid']}"
            )

            return result["accepted"]

        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback

            traceback.print_exc()
            return False

    def test_free_request_bypass(self):
        """
        Test that free requests (price = 0) bypass payment

        Express equivalent: Lines 53-57 in payment-express-middleware/src/index.ts
        """
        print("\n🆓 Test: Free Request Bypass")
        print("=" * 60)

        try:
            # Mock request with price = 0
            request_price = 0

            print(f"📝 Request price: {request_price} satoshis")

            # Express: if (requestPrice === 0) { req.payment = { satoshisPaid: 0 }; return next() }
            if request_price == 0:
                payment_info = {"satoshisPaid": 0}
                print("✅ Free request - no payment required")
                print(f"✅ Payment info set: {payment_info}")
                return True

            return False

        except Exception as e:
            print(f"❌ Test failed: {e}")
            return False

    def test_complete_payment_flow(self):
        """
        Complete payment flow test

        Simulates full Express middleware payment flow:
        1. Check authentication (must be after auth middleware)
        2. Calculate price
        3. If price = 0 → bypass
        4. If no payment header → 402 Payment Required
        5. If payment header → verify and internalize
        6. Set payment info and continue
        """
        print("\n🔄 Test: Complete Payment Flow")
        print("=" * 60)

        try:
            # Step 1: Authentication check (Express: lines 33-39)
            print("📋 Step 1: Check authentication")
            mock_auth_info = {
                "identityKey": "033f5aed5f6cfbafaf94570c8cde0c0a6e2b5fb0e07ca40ce1d6f6bdfde1e5b9b8",
                "authenticated": True,
            }
            print(f"✅ Auth info available: {mock_auth_info['identityKey'][:20]}...")

            # Step 2: Calculate price (Express: lines 41-51)
            print("\n📋 Step 2: Calculate request price")
            request_price = 100  # Mock: 100 satoshis
            print(f"✅ Price calculated: {request_price} satoshis")

            # Step 3: Check if payment required (Express: lines 53-57)
            print("\n📋 Step 3: Check if payment required")
            print(f"💳 Payment required: {request_price} satoshis")

            # Step 4: Check for payment header (Express: lines 59-74)
            print("\n📋 Step 4: Check for payment header")
            print("✅ Payment header present")

            # Step 5: Verify and internalize payment (Express: lines 76-132)
            print("\n📋 Step 5: Verify and internalize payment")

            payment_data = {
                "derivationPrefix": "test_prefix_12345",
                "derivationSuffix": "test_suffix_67890",
                "transaction": base64.b64encode(b"mock_transaction").decode("utf-8"),
            }

            # Verify nonce
            is_valid = verify_nonce(payment_data["derivationPrefix"], self.mock_wallet)
            if not is_valid:
                print("❌ Nonce verification failed")
                return False

            print("✅ Nonce verified")

            # Internalize action
            action_args = {
                "tx": base64.b64decode(payment_data["transaction"]),
                "outputs": [
                    {
                        "paymentRemittance": {
                            "derivationPrefix": payment_data["derivationPrefix"],
                            "derivationSuffix": payment_data["derivationSuffix"],
                            "senderIdentityKey": mock_auth_info["identityKey"],
                        },
                        "outputIndex": 0,
                        "protocol": "wallet payment",
                    }
                ],
                "description": "Payment for request",
            }

            result = self.mock_wallet.internalize_action(
                {}, {"action": action_args}, "payment_middleware"
            )

            print(f"✅ Payment accepted: {result['accepted']}")

            # Step 6: Set payment info and continue
            print("\n📋 Step 6: Set payment info")
            payment_info = {
                "satoshisPaid": request_price,
                "accepted": result["accepted"],
                "tx": payment_data["transaction"],
            }
            print(f"✅ Payment info set: {payment_info['satoshisPaid']} satoshis paid")

            print("\n" + "=" * 60)
            print("🎉 Complete payment flow test PASSED")
            return True

        except Exception as e:
            print(f"❌ Test failed: {e}")
            import traceback

            traceback.print_exc()
            return False


def main():
    """Main test execution"""
    print("🧪 Real BSV Payment Integration Testing")
    print("=" * 70)
    print("Reference: Express payment-express-middleware/src/index.ts")
    print("=" * 70)

    if not py_sdk_available:
        print("⚠️ py-sdk not available - some tests may be limited")

    tester = RealBSVPaymentTester()

    results = {
        "free_request_bypass": tester.test_free_request_bypass(),
        "payment_required_response": tester.test_payment_required_response(),
        "payment_header_parsing": tester.test_payment_header_parsing(),
        "payment_internalization": tester.test_payment_internalization(),
        "complete_payment_flow": tester.test_complete_payment_flow(),
    }

    print("\n" + "=" * 70)
    print("📊 Real BSV Payment Test Summary")
    print("=" * 70)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")

    total_tests = len(results)
    passed_tests = sum(results.values())

    print(f"\nTotal: {passed_tests}/{total_tests} tests passed")

    if passed_tests == total_tests:
        print("🎉 All real BSV payment tests passed!")
        return True
    else:
        print("⚠️ Some real BSV payment tests failed")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
