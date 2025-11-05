"""
ts-go-tests.py

This file combines integration tests from both the TypeScript and Go middleware test suites,
adapted for the Django BSV middleware implementation.

Based on:
- auth-express-middleware/src/__tests/integration.test.ts (TypeScript)
- go-bsv-middleware/pkg/middleware/auth_middleware_test.go (Go)

Usage:
    pytest ts-go-tests.py -v
"""

import pytest
import subprocess
import time
import sys
import os
import json
import requests
from typing import Optional

# Import BSV SDK components
try:
    from bsv.keys import PrivateKey
    from bsv.wallet import WalletImpl
    from bsv.auth.clients.auth_fetch import AuthFetch, SimplifiedFetchRequestOptions
    from bsv.auth.requested_certificate_set import RequestedCertificateSet
    from bsv.auth.master_certificate import MasterCertificate
    # Import the adapter that makes WalletImpl work with AuthFetch
    import sys
    sys.path.insert(0, '/mnt/c/Users/honoh/YenPoint/middleware/py-middleware')
    from bsv_middleware.wallet_adapter import WalletImplAdapter
except ImportError as e:
    pytest.skip(f"BSV SDK not available: {e}", allow_module_level=True)


# Note: We use WalletImpl with WalletImplAdapter to make it compatible with AuthFetch.
# The adapter converts WalletImpl's dict responses to objects that AuthFetch expects.


@pytest.fixture(scope="module")
def django_server(live_server):
    """
    Use pytest-django's live_server fixture for better Django integration.
    Similar to the beforeAll/afterAll in the TypeScript tests.
    """
    print(f'\n[OK] Test Django server is running on {live_server.url}')
    yield live_server.url
    print('\n[OK] Test Django server stopped')


@pytest.fixture
def private_key():
    """Create a random private key for tests"""
    return PrivateKey()  # Creates random key if no arg provided


@pytest.fixture
def wallet_impl(private_key):
    """Create a WalletImpl instance wrapped with adapter for AuthFetch compatibility"""
    wallet = WalletImpl(private_key)
    # Wrap with adapter to convert dict responses to objects
    return WalletImplAdapter(wallet)


@pytest.fixture
def auth_fetch(wallet_impl):
    """Create an AuthFetch instance with adapted WalletImpl"""
    requested_certs = RequestedCertificateSet()
    return AuthFetch(wallet_impl, requested_certs)


# ============================================================================
# Common Tests from TypeScript and Go
# ============================================================================

class TestAuthMiddlewareIntegration:
    """
    Integration tests covering common test cases from both TypeScript and Go.
    Based on TestAuthMiddlewareAndAuthFetchIntegration from Go tests.
    """

    def test_get_request_on_server_root(self, django_server, auth_fetch):
        """GET request on server root"""
        result = auth_fetch.fetch(None, f'{django_server}/')
        assert result.status_code == 200
        assert result.text is not None

    def test_get_request_on_path(self, django_server, auth_fetch):
        """GET request on path"""
        result = auth_fetch.fetch(None, f'{django_server}/public/')
        assert result.status_code == 200
        assert result.text is not None

    def test_get_with_query_params(self, django_server, auth_fetch):
        """GET with query params"""
        result = auth_fetch.fetch(
            None,
            f'{django_server}/?test=123&other=abc'
        )
        assert result.status_code == 200
        assert result.text is not None

    def test_get_request_on_path_with_query_params(self, django_server, auth_fetch):
        """GET request on path with query params"""
        result = auth_fetch.fetch(
            None,
            f'{django_server}/public/?test=123&other=abc'
        )
        assert result.status_code == 200
        assert result.text is not None

    def test_get_with_authorization_headers(self, django_server, auth_fetch):
        """GET with authorization headers"""
        config = SimplifiedFetchRequestOptions(
            method='GET',
            headers={'Authorization': '123'}
        )
        result = auth_fetch.fetch(None, f'{django_server}/', config)
        assert result.status_code == 200
        assert result.text is not None

    def test_get_with_custom_x_bsv_headers(self, django_server, auth_fetch):
        """GET with custom x-bsv headers"""
        config = SimplifiedFetchRequestOptions(
            method='GET',
            headers={'X-Bsv-Test': 'true'}
        )
        result = auth_fetch.fetch(None, f'{django_server}/', config)
        assert result.status_code == 200
        assert result.text is not None

    def test_get_with_path_and_headers(self, django_server, auth_fetch):
        """GET with path and headers"""
        config = SimplifiedFetchRequestOptions(
            method='GET',
            headers={'Authorization': '123'}
        )
        result = auth_fetch.fetch(None, f'{django_server}/public/', config)
        assert result.status_code == 200
        assert result.text is not None

    def test_post_request_without_body(self, django_server, auth_fetch):
        """POST request without body"""
        config = SimplifiedFetchRequestOptions(
            method='POST'
        )
        result = auth_fetch.fetch(None, f'{django_server}/', config)
        # May return 200 or 405 depending on endpoint configuration
        assert result.status_code in [200, 405]

    def test_post_request_on_path_without_body(self, django_server, auth_fetch):
        """POST request on path without body"""
        config = SimplifiedFetchRequestOptions(
            method='POST'
        )
        result = auth_fetch.fetch(None, f'{django_server}/auth-test/', config)
        assert result.status_code == 200

    def test_post_request_with_content_type_but_no_body(self, django_server, auth_fetch):
        """POST request with content-type but no body"""
        config = SimplifiedFetchRequestOptions(
            method='POST',
            headers={'Content-Type': 'application/json'}
        )
        result = auth_fetch.fetch(None, f'{django_server}/auth-test/', config)
        assert result.status_code == 200

    def test_post_request_on_path_with_json_empty_body(self, django_server, auth_fetch):
        """POST request on path with json empty body"""
        config = SimplifiedFetchRequestOptions(
            method='POST',
            headers={'Content-Type': 'application/json'},
            body=json.dumps({}).encode('utf-8')
        )
        result = auth_fetch.fetch(None, f'{django_server}/auth-test/', config)
        assert result.status_code == 200

    def test_post_request_with_body(self, django_server, auth_fetch):
        """POST request with body"""
        config = SimplifiedFetchRequestOptions(
            method='POST',
            body=b'Ping'
        )
        result = auth_fetch.fetch(None, f'{django_server}/auth-test/', config)
        assert result.status_code == 200

    def test_post_request_on_path_with_body(self, django_server, auth_fetch):
        """POST request on path with body"""
        config = SimplifiedFetchRequestOptions(
            method='POST',
            body=b'Ping'
        )
        result = auth_fetch.fetch(None, f'{django_server}/auth-test/', config)
        assert result.status_code == 200

    def test_post_request_with_body_and_content_type(self, django_server, auth_fetch):
        """POST request with body and content-type"""
        config = SimplifiedFetchRequestOptions(
            method='POST',
            headers={'Content-Type': 'application/json'},
            body=json.dumps({'ping': True}).encode('utf-8')
        )
        result = auth_fetch.fetch(None, f'{django_server}/auth-test/', config)
        assert result.status_code == 200

    def test_post_request_with_body_and_content_type_and_authorization_header(
        self, django_server, auth_fetch
    ):
        """POST request with body and content-type and authorization header"""
        config = SimplifiedFetchRequestOptions(
            method='POST',
            headers={
                'Content-Type': 'application/json',
                'Authorization': '123'
            },
            body=json.dumps({'ping': True}).encode('utf-8')
        )
        result = auth_fetch.fetch(None, f'{django_server}/auth-test/', config)
        assert result.status_code == 200

    def test_post_request_with_body_and_content_type_and_authorization_and_bsv_header(
        self, django_server, auth_fetch
    ):
        """POST request with body and content-type and authorization and bsv header"""
        config = SimplifiedFetchRequestOptions(
            method='POST',
            headers={
                'Content-Type': 'application/json',
                'Authorization': '123',
                'X-Bsv-Test': 'true'
            },
            body=json.dumps({'ping': True}).encode('utf-8')
        )
        result = auth_fetch.fetch(None, f'{django_server}/auth-test/', config)
        assert result.status_code == 200

    def test_post_request_with_query_params_and_body_and_headers(
        self, django_server, auth_fetch
    ):
        """POST request with query params and body and headers"""
        config = SimplifiedFetchRequestOptions(
            method='POST',
            headers={
                'Content-Type': 'application/json',
                'Authorization': '123',
                'X-Bsv-Test': 'true'
            },
            body=json.dumps({'ping': True}).encode('utf-8')
        )
        result = auth_fetch.fetch(
            None,
            f'{django_server}/auth-test/?test=123&other=abc',
            config
        )
        assert result.status_code == 200

    def test_post_request_on_path_with_query_params_and_body_and_headers(
        self, django_server, auth_fetch
    ):
        """POST request on path with query params and body and headers"""
        config = SimplifiedFetchRequestOptions(
            method='POST',
            headers={
                'Content-Type': 'application/json',
                'Authorization': '123',
                'X-Bsv-Test': 'true'
            },
            body=json.dumps({'ping': True}).encode('utf-8')
        )
        result = auth_fetch.fetch(
            None,
            f'{django_server}/auth-test/?test=123&other=abc',
            config
        )
        assert result.status_code == 200

    def test_options_request(self, django_server, auth_fetch):
        """OPTIONS request (from Go tests)"""
        config = SimplifiedFetchRequestOptions(
            method='OPTIONS'
        )
        result = auth_fetch.fetch(None, f'{django_server}/', config)
        # OPTIONS may return 200 or 204
        assert result.status_code in [200, 204]

    def test_options_request_on_path(self, django_server, auth_fetch):
        """OPTIONS request on path (from Go tests)"""
        config = SimplifiedFetchRequestOptions(
            method='OPTIONS'
        )
        result = auth_fetch.fetch(None, f'{django_server}/auth-test/', config)
        assert result.status_code in [200, 204]

    def test_options_request_with_query_params(self, django_server, auth_fetch):
        """OPTIONS request with query params (from Go tests)"""
        config = SimplifiedFetchRequestOptions(
            method='OPTIONS'
        )
        result = auth_fetch.fetch(
            None,
            f'{django_server}/?test=123&other=abc',
            config
        )
        assert result.status_code in [200, 204]

    def test_options_request_on_path_with_query_params(self, django_server, auth_fetch):
        """OPTIONS request on path with query params (from Go tests)"""
        config = SimplifiedFetchRequestOptions(
            method='OPTIONS'
        )
        result = auth_fetch.fetch(
            None,
            f'{django_server}/auth-test/?test=123&other=abc',
            config
        )
        assert result.status_code in [200, 204]


class TestAuthMiddlewareSubsequentRequests:
    """
    Test subsequent requests and multiple clients (from Go tests).
    Based on TestAuthMiddlewareHandleSubsequentRequests.
    """

    def test_multiple_requests_with_same_client(
        self, django_server, wallet_impl
    ):
        """Multiple requests with the same client (from Go tests)"""
        requested_certs = RequestedCertificateSet()
        auth_fetch = AuthFetch(wallet_impl, requested_certs)

        # First request
        result1 = auth_fetch.fetch(None, f'{django_server}/')
        assert result1.status_code == 200
        print(f"[OK] First request succeeded")

        # Second request with same client
        result2 = auth_fetch.fetch(None, f'{django_server}/')
        assert result2.status_code == 200
        print(f"[OK] Second request with same client succeeded")

    def test_multiple_requests_with_different_clients_for_same_user(
        self, django_server, private_key
    ):
        """Multiple requests with different clients for the same user (from Go tests)"""
        # Create first client with adapter
        wallet1 = WalletImplAdapter(WalletImpl(private_key))
        requested_certs1 = RequestedCertificateSet()
        auth_fetch1 = AuthFetch(wallet1, requested_certs1)

        # First request
        result1 = auth_fetch1.fetch(None, f'{django_server}/')
        assert result1.status_code == 200
        print(f"[OK] First request with first client succeeded")

        # Create second client with same identity key (also with adapter)
        wallet2 = WalletImplAdapter(WalletImpl(private_key))
        requested_certs2 = RequestedCertificateSet()
        auth_fetch2 = AuthFetch(wallet2, requested_certs2)

        # Second request with different client
        result2 = auth_fetch2.fetch(None, f'{django_server}/')
        assert result2.status_code == 200
        print(f"[OK] Second request with different client (same user) succeeded")


class TestUnauthenticatedRequests:
    """
    Test handling of unauthenticated requests (from Go tests).
    Based on TestHandlingUnauthenticatedRequests.
    """

    def test_unauthenticated_request_to_public_endpoint(self, django_server):
        """Unauthenticated requests should succeed on public endpoints"""
        # Use plain requests (no BSV auth)
        response = requests.get(f'{django_server}/public/')
        assert response.status_code == 200
        data = response.json()
        assert data['access'] == 'free'
        print(f"[OK] Unauthenticated request to public endpoint succeeded")

    def test_unauthenticated_request_to_protected_endpoint(self, django_server):
        """Unauthenticated requests should fail on protected endpoints"""
        # Use plain requests (no BSV auth)
        response = requests.get(f'{django_server}/protected/')
        # Should return 401 (Unauthorized)
        assert response.status_code == 401
        print(f"[OK] Unauthenticated request to protected endpoint failed as expected")


# ============================================================================
# TypeScript-Specific Tests
# ============================================================================

class TestTypeScriptSpecificCases:
    """Tests from TypeScript that are not in Go"""

    def test_post_with_url_encoded(self, django_server, auth_fetch):
        """Test 2: POST request with URL-encoded data (from TS)"""
        config = SimplifiedFetchRequestOptions(
            method='POST',
            headers={
                'content-type': 'application/x-www-form-urlencoded',
                'x-bsv-test': 'this is a test header'
            },
            body=b'message=hello&type=form-data'
        )

        result = auth_fetch.fetch(None, f'{django_server}/auth-test/', config)
        assert result.status_code == 200
        assert result.text is not None
        print(f"[OK] URL encoded data sent successfully")

    def test_post_with_plain_text(self, django_server, auth_fetch):
        """Test 3: POST request with plain text (from TS)"""
        config = SimplifiedFetchRequestOptions(
            method='POST',
            headers={
                'content-type': 'text/plain',
                'x-bsv-test': 'this is a test header'
            },
            body=b'Hello, this is a plain text message!'
        )

        result = auth_fetch.fetch(None, f'{django_server}/auth-test/', config)
        assert result.status_code == 200
        assert result.text is not None

    def test_post_with_binary_data(self, django_server, auth_fetch):
        """Test 4: POST request with binary data (from TS)"""
        config = SimplifiedFetchRequestOptions(
            method='POST',
            headers={
                'content-type': 'application/octet-stream',
                'x-bsv-test': 'this is a test header'
            },
            body=b'Hello from binary!'
        )

        result = auth_fetch.fetch(None, f'{django_server}/auth-test/', config)
        assert result.status_code == 200
        assert result.text is not None

    def test_large_binary_upload(self, django_server, auth_fetch):
        """Test 9: Large binary upload (from TS)"""
        large_buffer = b'Hello from a large upload test' * 100

        config = SimplifiedFetchRequestOptions(
            method='POST',
            headers={'content-type': 'application/octet-stream'},
            body=large_buffer
        )

        result = auth_fetch.fetch(None, f'{django_server}/auth-test/', config)
        assert result.status_code == 200
        assert result.text is not None

    def test_charset_injection(self, django_server, auth_fetch):
        """Test 13: POST with JSON header containing charset (from TS)"""
        config = SimplifiedFetchRequestOptions(
            method='POST',
            headers={'content-type': 'application/json; charset=utf-8'},
            body=json.dumps({'message': 'Testing charset injection normalization!'}).encode('utf-8')
        )

        result = auth_fetch.fetch(None, f'{django_server}/auth-test/', config)
        assert result.status_code == 200
        json_response = result.json()
        print(f"Charset test response: {json_response}")
        assert json_response is not None


# ============================================================================
# Edge Case Tests
# ============================================================================

class TestEdgeCases:
    """Edge case tests from TypeScript"""

    def test_edge_case_undefined_body(self, django_server, auth_fetch):
        """Edge Case B: application/json content with undefined/empty body"""
        config = SimplifiedFetchRequestOptions(
            method='POST',
            headers={'content-type': 'application/json'},
            body=None
        )

        result = auth_fetch.fetch(None, f'{django_server}/auth-test/', config)
        assert result.status_code == 200
        json_response = result.json()
        print(f"Undefined body response: {json_response}")
        assert json_response is not None

    def test_edge_case_empty_json_object(self, django_server, auth_fetch):
        """Edge Case C: application/json content with empty object body"""
        config = SimplifiedFetchRequestOptions(
            method='POST',
            headers={'content-type': 'application/json'},
            body=json.dumps({}).encode('utf-8')
        )

        result = auth_fetch.fetch(None, f'{django_server}/auth-test/', config)
        assert result.status_code == 200
        json_response = result.json()
        print(f"Empty object response: {json_response}")
        assert json_response is not None


if __name__ == '__main__':
    # Allow running directly with: python ts-go-tests.py
    pytest.main([__file__, '-v', '-s'])
