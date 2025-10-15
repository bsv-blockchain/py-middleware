"""
Tests for BSV middleware multipart/form-data support

This test suite validates the BSV middleware's ability to handle file uploads
and multipart data while maintaining BSV authentication and payment functionality.
"""

import pytest
import json
import tempfile
from io import BytesIO
from django.test import TestCase, RequestFactory
from django.http import HttpRequest
from django.core.files.uploadedfile import SimpleUploadedFile

from bsv_middleware.django.utils import (
    get_multipart_data,
    is_multipart_request,
    get_uploaded_files,
    get_multipart_fields,
    handle_file_upload,
    bsv_file_upload_required,
    bsv_authenticated_required
)

from bsv_middleware.django.transport import DjangoTransport
from bsv_middleware.py_sdk_bridge import PySdkBridge


class TestMultipartFormDataSupport(TestCase):
    """Test multipart/form-data handling in BSV middleware"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.factory = RequestFactory()
        
        # Create mock BSV authentication data
        self.mock_auth_data = {
            'authenticated': True,
            'identity_key': 'test_identity_key_12345',
            'certificates': []
        }
        
        # Create test file
        self.test_file_content = b"Test file content for BSV upload"
        self.test_file = SimpleUploadedFile(
            "test_document.txt",
            self.test_file_content,
            content_type="text/plain"
        )
        
        # Create test image file
        self.test_image_content = b"FAKE_PNG_DATA"
        self.test_image = SimpleUploadedFile(
            "test_image.png",
            self.test_image_content,
            content_type="image/png"
        )
    
    def _create_multipart_request(self, files=None, fields=None):
        """Helper to create multipart/form-data request"""
        from django.test import Client
        from io import BytesIO
        
        if files is None:
            files = {}
        if fields is None:
            fields = {}
            
        # Use Django's encode_multipart to properly format the request
        from django.test.client import encode_multipart, FakePayload
        from django.utils.http import urlencode
        import uuid
        
        # Create boundary
        boundary = f"----WebKitFormBoundary{uuid.uuid4().hex[:16]}"
        
        # Prepare data for encoding
        data = {}
        data.update(fields)
        data.update(files)
        
        # Encode as multipart
        content = encode_multipart(boundary, data)
        content_type = f'multipart/form-data; boundary={boundary}'
        
        # Create request with proper multipart encoding
        request = self.factory.post(
            '/upload/',
            data=content,
            content_type=content_type
        )
        
        # Add mock BSV authentication
        request.bsv_auth = type('MockAuth', (), self.mock_auth_data)()
        
        return request
    
    def test_is_multipart_request_detection(self):
        """Test multipart request detection"""
        # Test multipart request
        multipart_request = self._create_multipart_request()
        self.assertTrue(is_multipart_request(multipart_request))
        
        # Test non-multipart request
        json_request = self.factory.post(
            '/api/data/',
            {'key': 'value'},
            content_type='application/json'
        )
        self.assertFalse(is_multipart_request(json_request))
        
        # Test plain request
        plain_request = self.factory.get('/test/')
        self.assertFalse(is_multipart_request(plain_request))
    
    def test_get_multipart_data_parsing(self):
        """Test multipart data parsing after BSV authentication"""
        request = self._create_multipart_request(
            files={'document': self.test_file, 'image': self.test_image},
            fields={'title': 'Test Document', 'version': '1.0'}
        )
        
        multipart_data = get_multipart_data(request)
        
        # Check structure
        self.assertIn('fields', multipart_data)
        self.assertIn('files', multipart_data)
        
        # Check fields
        self.assertIn('title', multipart_data['fields'])
        self.assertIn('version', multipart_data['fields'])
        self.assertEqual(multipart_data['fields']['title'], ['Test Document'])
        
        # Check files
        self.assertIn('document', multipart_data['files'])
        self.assertIn('image', multipart_data['files'])
    
    def test_get_uploaded_files(self):
        """Test file extraction from multipart request"""
        request = self._create_multipart_request(
            files={'document': self.test_file, 'image': self.test_image}
        )
        
        files = get_uploaded_files(request)
        
        self.assertIn('document', files)
        self.assertIn('image', files)
        self.assertEqual(files['document'][0].name, 'test_document.txt')
        self.assertEqual(files['image'][0].name, 'test_image.png')
    
    def test_get_multipart_fields(self):
        """Test field extraction from multipart request"""
        request = self._create_multipart_request(
            fields={'title': 'My Document', 'category': 'work', 'priority': 'high'}
        )
        
        fields = get_multipart_fields(request)
        
        self.assertIn('title', fields)
        self.assertIn('category', fields)
        self.assertIn('priority', fields)
        self.assertEqual(fields['title'], ['My Document'])
        self.assertEqual(fields['category'], ['work'])
    
    def test_handle_file_upload_decorator(self):
        """Test @handle_file_upload decorator functionality"""
        
        @handle_file_upload
        def test_view(request):
            # Check if multipart data was added to request
            self.assertTrue(hasattr(request, 'multipart_fields'))
            self.assertTrue(hasattr(request, 'multipart_files'))
            
            return {'status': 'success', 'files_count': len(request.multipart_files)}
        
        request = self._create_multipart_request(
            files={'doc1': self.test_file, 'doc2': self.test_image},
            fields={'title': 'Test Upload'}
        )
        
        result = test_view(request)
        
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['files_count'], 2)
        self.assertIn('title', request.multipart_fields)
        self.assertIn('doc1', request.multipart_files)
        self.assertIn('doc2', request.multipart_files)
    
    def test_bsv_authenticated_required_decorator(self):
        """Test BSV authentication requirement"""
        
        @bsv_authenticated_required
        def protected_view(request):
            return {'message': 'Access granted'}
        
        # Test with authenticated request
        auth_request = self._create_multipart_request()
        result = protected_view(auth_request)
        self.assertEqual(result['message'], 'Access granted')
        
        # Test with unauthenticated request
        unauth_request = self.factory.post('/upload/')
        response = protected_view(unauth_request)
        self.assertEqual(response.status_code, 401)
    
    def test_bsv_file_upload_required_decorator(self):
        """Test BSV authenticated file upload requirement"""
        
        @bsv_file_upload_required
        def secure_upload_view(request):
            files = get_uploaded_files(request)
            return {
                'identity': request.bsv_auth.identity_key,
                'files_received': len(files)
            }
        
        # Test successful authenticated file upload
        request = self._create_multipart_request(files={'file': self.test_file})
        result = secure_upload_view(request)
        
        self.assertEqual(result['identity'], 'test_identity_key_12345')
        self.assertEqual(result['files_received'], 1)
        
        # Test without authentication
        unauth_request = self.factory.post(
            '/upload/',
            {'file': self.test_file},
            content_type='multipart/form-data'
        )
        response = secure_upload_view(unauth_request)
        self.assertEqual(response.status_code, 401)
        
        # Test without file upload
        no_file_request = self.factory.post('/upload/')
        no_file_request.bsv_auth = type('MockAuth', (), self.mock_auth_data)()
        response = secure_upload_view(no_file_request)
        self.assertEqual(response.status_code, 400)
    
    def test_non_multipart_request_handling(self):
        """Test that non-multipart requests are handled gracefully"""
        json_request = self.factory.post(
            '/api/data/',
            json.dumps({'key': 'value'}),
            content_type='application/json'
        )
        json_request.bsv_auth = type('MockAuth', (), self.mock_auth_data)()
        
        # These should return empty results for non-multipart requests
        self.assertEqual(get_multipart_data(json_request), {'fields': {}, 'files': {}})
        self.assertEqual(get_uploaded_files(json_request), {})
        self.assertEqual(get_multipart_fields(json_request), {})
        
        # Decorator should work but not add multipart attributes
        @handle_file_upload
        def json_view(request):
            has_multipart = hasattr(request, 'multipart_fields')
            return {'has_multipart_data': has_multipart}
        
        result = json_view(json_request)
        self.assertFalse(result['has_multipart_data'])


class TestBSVTransportMultipartIntegration(TestCase):
    """Test multipart integration with BSV Transport layer"""
    
    def setUp(self):
        """Set up transport layer tests"""
        self.factory = RequestFactory()
        
        # Mock py-sdk bridge
        self.mock_bridge = type('MockBridge', (), {
            'create_peer': lambda *args: None,
            'get_wallet': lambda: None
        })()
        
        self.transport = DjangoTransport(
            py_sdk_bridge=self.mock_bridge,
            allow_unauthenticated=False
        )
    
    def test_bsv_protocol_body_preservation(self):
        """Test that BSV protocol preserves raw body for signature verification"""
        # Create multipart request with test file  
        test_file = SimpleUploadedFile("test.txt", b"test content", content_type="text/plain")
        
        request = self.factory.post(
            '/upload/',
            {'file': test_file, 'description': 'test upload'},
            content_type='multipart/form-data'
        )
        
        # Test BSV protocol body extraction
        raw_body = self.transport._get_request_body_for_bsv_protocol(request)
        
        # Should preserve raw binary data
        self.assertIsInstance(raw_body, bytes)
        self.assertTrue(len(raw_body) > 0)
        
        # Test preservation check
        should_preserve = self.transport._should_preserve_raw_body(request)
        self.assertTrue(should_preserve)
        
        # Test multipart detection
        is_multipart = self.transport._is_multipart_request(request)
        self.assertTrue(is_multipart)
    
    def test_empty_body_handling(self):
        """Test handling of requests with empty bodies"""
        request = self.factory.get('/test/')
        
        raw_body = self.transport._get_request_body_for_bsv_protocol(request)
        self.assertEqual(raw_body, b'')
        
        # Should still preserve (return True for consistency)
        should_preserve = self.transport._should_preserve_raw_body(request)
        self.assertTrue(should_preserve)


class TestMultipartErrorHandling(TestCase):
    """Test error handling in multipart processing"""
    
    def setUp(self):
        self.factory = RequestFactory()
    
    def test_malformed_multipart_handling(self):
        """Test handling of malformed multipart data"""
        # Create request with invalid multipart content-type but no proper boundary
        request = self.factory.post(
            '/upload/',
            'invalid multipart data',
            content_type='multipart/form-data'
        )
        
        # Should handle gracefully and return empty data
        multipart_data = get_multipart_data(request)
        self.assertEqual(multipart_data, {'fields': {}, 'files': {}})
        
        files = get_uploaded_files(request)
        self.assertEqual(files, {})
        
        fields = get_multipart_fields(request)
        self.assertEqual(fields, {})
    
    def test_decorator_with_invalid_multipart(self):
        """Test decorators with invalid multipart requests"""
        
        @bsv_file_upload_required
        def upload_view(request):
            return {'status': 'success'}
        
        # Create authenticated request with invalid multipart
        request = self.factory.post(
            '/upload/',
            'invalid data',
            content_type='multipart/form-data'
        )
        request.bsv_auth = type('MockAuth', (), {
            'authenticated': True,
            'identity_key': 'test_key'
        })()
        
        # Should return 400 due to no files uploaded
        response = upload_view(request)
        self.assertEqual(response.status_code, 400)


if __name__ == '__main__':
    pytest.main([__file__])





