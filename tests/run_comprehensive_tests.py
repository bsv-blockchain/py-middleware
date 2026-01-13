"""
Comprehensive Test Runner for BSV Middleware Django Example
Runs all tests and generates detailed reports
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Add current directory to Python path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'examples' / 'django_example'))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.django_example_test_settings')

import django
django.setup()

from django.test import RequestFactory
from django.http import JsonResponse
import importlib

# Import views
try:
    from myapp.views import (
        home, health, public_endpoint, protected_endpoint, 
        premium_endpoint, auth_test
    )
    print("✅ Successfully imported Django views")
except ImportError as e:
    print(f"❌ Failed to import views: {e}")
    sys.exit(1)

class SimpleAPITester:
    """Simplified API tester for comprehensive testing"""
    
    def __init__(self):
        self.factory = RequestFactory()
        self.test_results = []
        
    def test_endpoint(self, endpoint_name: str, view_func, path: str, method: str = 'GET', headers: dict = None):
        """Test a single endpoint"""
        print(f"\n🧪 Testing {endpoint_name}")
        
        try:
            # Create request
            if method == 'GET':
                request = self.factory.get(path)
            else:
                request = self.factory.post(path, content_type='application/json')
            
            # Add headers
            if headers:
                for key, value in headers.items():
                    request.META[f'HTTP_{key.upper().replace("-", "_")}'] = value
            
            # Execute view
            response = view_func(request)
            
            # Parse response
            try:
                response_data = json.loads(response.content.decode())
            except:
                response_data = {'raw_content': response.content.decode()[:200]}
            
            result = {
                'endpoint': endpoint_name,
                'path': path,
                'method': method,
                'status_code': response.status_code,
                'response_data': response_data,
                'success': True,
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"   ✅ Status: {response.status_code}")
            print(f"   📋 Response: {str(response_data)[:150]}...")
            
            self.test_results.append(result)
            return result
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            error_result = {
                'endpoint': endpoint_name,
                'path': path,
                'method': method,
                'error': str(e),
                'success': False,
                'timestamp': datetime.now().isoformat()
            }
            self.test_results.append(error_result)
            return error_result
    
    def run_endpoint_coverage_tests(self):
        """Run comprehensive endpoint coverage tests"""
        print("🚀 Starting Endpoint Coverage Tests")
        print("=" * 50)
        
        # Test all basic endpoints
        test_cases = [
            ("Home Page", home, "/", "GET"),
            ("Health Check", health, "/health/", "GET"),
            ("Public Endpoint", public_endpoint, "/public/", "GET"),
            ("Protected Endpoint (No Auth)", protected_endpoint, "/protected/", "GET"),
            ("Premium Endpoint (No Auth)", premium_endpoint, "/premium/", "GET"),
            ("Auth Test GET", auth_test, "/auth-test/", "GET"),
            ("Auth Test POST", auth_test, "/auth-test/", "POST"),
        ]
        
        for name, view_func, path, method in test_cases:
            self.test_endpoint(name, view_func, path, method)
        
        return self.test_results
    
    def run_bsv_header_tests(self):
        """Test with BSV headers"""
        print("\n🔐 Testing BSV Headers")
        print("=" * 30)
        
        bsv_headers = {
            'x-bsv-auth-version': '1.0',
            'x-bsv-auth-identity-key': '033f5aed5f6cfbafaf94570c8cde0c0a6e2b5fb0e07ca40ce1d6f6bdfde1e5b9b8',
            'x-bsv-auth-nonce': 'test_nonce_12345'
        }
        
        # Test with BSV headers
        self.test_endpoint("Auth Test with BSV Headers", auth_test, "/auth-test/", "GET", bsv_headers)
        
        # Test with payment header
        payment_headers = bsv_headers.copy()
        payment_headers['x-bsv-payment'] = json.dumps({
            "derivationPrefix": "test_prefix",
            "satoshis": 1000,
            "transaction": "test_tx_123"
        })
        
        self.test_endpoint("Auth Test with Payment", auth_test, "/auth-test/", "GET", payment_headers)
    
    def test_middleware_utils(self):
        """Test middleware utility functions"""
        print("\n🛠️ Testing Middleware Utils")
        print("=" * 30)
        
        try:
            from .django_example.adapter.utils import (
                get_identity_key, is_authenticated_request, 
                format_satoshis, create_bsv_response
            )
            
            # Test format_satoshis
            test_amounts = [0, 1, 100, 1000, 1500]
            for amount in test_amounts:
                formatted = format_satoshis(amount)
                print(f"   💰 {amount} satoshis → {formatted}")
            
            # Test with mock request
            request = self.factory.get('/')
            identity = get_identity_key(request)
            authenticated = is_authenticated_request(request)
            
            print(f"   🔑 Identity: {identity}")
            print(f"   🔐 Authenticated: {authenticated}")
            
            # Test BSV response creation
            test_data = {'message': 'test', 'value': 123}
            response = create_bsv_response(test_data, request)
            response_data = json.loads(response.content.decode())
            
            print(f"   📤 BSV Response: {response_data}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Utils test error: {str(e)}")
            return False
    
    def generate_report(self):
        """Generate comprehensive test report"""
        total_tests = len(self.test_results)
        successful_tests = sum(1 for result in self.test_results if result.get('success', False))
        failed_tests = total_tests - successful_tests
        
        report = {
            'test_summary': {
                'total_tests': total_tests,
                'successful_tests': successful_tests,
                'failed_tests': failed_tests,
                'success_rate': round((successful_tests / total_tests) * 100, 2) if total_tests > 0 else 0
            },
            'test_results': self.test_results,
            'timestamp': datetime.now().isoformat()
        }
        
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE TEST REPORT")
        print("=" * 60)
        print(f"Total Tests: {total_tests}")
        print(f"Successful: {successful_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {report['test_summary']['success_rate']}%")
        
        if failed_tests > 0:
            print(f"\n❌ Failed Tests:")
            for result in self.test_results:
                if not result.get('success', False):
                    print(f"   - {result['endpoint']}: {result.get('error', 'Unknown error')}")
        else:
            print(f"\n🎉 All tests passed!")
        
        # Save report to file
        report_file = current_dir / 'comprehensive_test_report.json'
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n📄 Report saved to: {report_file}")
        
        return report

def main():
    """Main test runner"""
    print("🎯 BSV Middleware Comprehensive API Testing")
    print("=" * 60)
    
    try:
        # Initialize tester
        tester = SimpleAPITester()
        
        # Run tests
        tester.run_endpoint_coverage_tests()
        tester.run_bsv_header_tests()
        utils_success = tester.test_middleware_utils()
        
        # Generate report
        report = tester.generate_report()
        
        # Exit with appropriate code
        if report['test_summary']['failed_tests'] == 0 and utils_success:
            print("\n🏆 ALL TESTS PASSED!")
            sys.exit(0)
        else:
            print("\n⚠️ SOME TESTS FAILED")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n💥 Test runner failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
