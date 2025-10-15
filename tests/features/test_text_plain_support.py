#!/usr/bin/env python3
"""
Test text/plain content type support for BSV middleware

Tests Express compatibility for text/plain processing
"""

import pytest
from django.test import TestCase, Client
from django.http import HttpRequest
from django.conf import settings
from unittest.mock import Mock, patch
import json

from bsv_middleware.django.utils import (
    is_text_plain_request,
    get_text_content, 
    get_content_by_type
)


class TestTextPlainSupport(TestCase):
    """Test text/plain content type handling"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        
        # Test text content
        self.test_text_utf8 = "Hello, BSV World! 🚀 This is a test message."
        self.test_text_ascii = "Plain ASCII text content"
        self.test_text_multiline = """Line 1
Line 2
Line 3 with unicode: café"""

    def _create_text_request(self, content: str, charset: str = 'utf-8') -> HttpRequest:
        """Helper to create text/plain request"""
        request = HttpRequest()
        request.method = 'POST'
        request.META['CONTENT_TYPE'] = f'text/plain; charset={charset}'
        request._body = content.encode(charset)
        return request

    def test_is_text_plain_request_detection(self):
        """Test text/plain request detection"""
        
        # Test various text/plain content-type variations
        test_cases = [
            ('text/plain', True),
            ('text/plain; charset=utf-8', True),
            ('text/plain; charset=ascii', True),
            ('TEXT/PLAIN', True),  # Case insensitive
            ('application/json', False),
            ('multipart/form-data', False),
            ('application/x-www-form-urlencoded', False),
            ('', False)
        ]
        
        for content_type, expected in test_cases:
            with self.subTest(content_type=content_type):
                request = HttpRequest()
                request.META['CONTENT_TYPE'] = content_type
                
                result = is_text_plain_request(request)
                self.assertEqual(result, expected, f"Failed for content-type: {content_type}")

    def test_get_text_content_utf8(self):
        """Test UTF-8 text content extraction"""
        request = self._create_text_request(self.test_text_utf8, 'utf-8')
        
        result = get_text_content(request)
        
        self.assertEqual(result, self.test_text_utf8)
        self.assertIsInstance(result, str)

    def test_get_text_content_ascii(self):
        """Test ASCII text content extraction"""
        request = self._create_text_request(self.test_text_ascii, 'ascii')
        
        result = get_text_content(request, encoding='ascii')
        
        self.assertEqual(result, self.test_text_ascii)

    def test_get_text_content_multiline(self):
        """Test multiline text content"""
        request = self._create_text_request(self.test_text_multiline)
        
        result = get_text_content(request)
        
        self.assertEqual(result, self.test_text_multiline)
        self.assertIn('\n', result)

    def test_get_text_content_non_text_request(self):
        """Test error handling for non-text/plain request"""
        request = HttpRequest()
        request.META['CONTENT_TYPE'] = 'application/json'
        request._body = b'{"test": true}'
        
        with self.assertRaises(ValueError) as cm:
            get_text_content(request)
        
        self.assertIn('text/plain', str(cm.exception))

    def test_get_text_content_encoding_error(self):
        """Test error handling for encoding issues"""
        # Create request with invalid UTF-8 bytes
        request = HttpRequest()
        request.META['CONTENT_TYPE'] = 'text/plain; charset=utf-8'
        request._body = b'\xff\xfe invalid utf-8'  # Invalid UTF-8 sequence
        
        with self.assertRaises(ValueError) as cm:
            get_text_content(request)
        
        self.assertIn('decode', str(cm.exception))

    def test_get_content_by_type_text_plain(self):
        """Test unified content processing for text/plain (Express compatibility)"""
        request = self._create_text_request(self.test_text_utf8)
        
        result = get_content_by_type(request)
        
        # Verify structure matches Express writeBodyToWriter output
        self.assertEqual(result['content_type'], 'text/plain')
        self.assertEqual(result['data'], self.test_text_utf8)
        self.assertEqual(result['encoding'], 'utf-8')
        
        # Verify processed_body is UTF-8 encoded bytes (Express: Utils.toArray(body, 'utf8'))
        expected_bytes = self.test_text_utf8.encode('utf-8')
        self.assertEqual(result['processed_body'], expected_bytes)

    def test_get_content_by_type_comparison_with_other_types(self):
        """Test text/plain vs other content types"""
        
        # Text/plain
        text_request = self._create_text_request("Hello World")
        text_result = get_content_by_type(text_request)
        
        # JSON 
        json_request = HttpRequest()
        json_request.META['CONTENT_TYPE'] = 'application/json'
        json_request._body = b'{"message": "Hello World"}'
        json_result = get_content_by_type(json_request)
        
        # Form-urlencoded
        form_request = HttpRequest()  
        form_request.META['CONTENT_TYPE'] = 'application/x-www-form-urlencoded'
        form_request._body = b'message=Hello+World'
        form_result = get_content_by_type(form_request)
        
        # Verify different processing for each type
        self.assertEqual(text_result['content_type'], 'text/plain')
        self.assertEqual(json_result['content_type'], 'application/json')
        self.assertEqual(form_result['content_type'], 'application/x-www-form-urlencoded')
        
        # Text should be string, JSON should be dict, form should be dict
        self.assertIsInstance(text_result['data'], str)
        self.assertIsInstance(json_result['data'], dict)
        self.assertIsInstance(form_result['data'], dict)

    def test_express_compatibility_text_processing(self):
        """Test that our processing matches Express writeBodyToWriter for text/plain"""
        
        test_cases = [
            "Simple text",
            "Text with unicode: 日本語 🎌",
            "Multi\nline\ntext",
            "Text with special chars: !@#$%^&*()",
            ""  # Empty string
        ]
        
        for text_content in test_cases:
            with self.subTest(text=text_content[:20]):
                request = self._create_text_request(text_content)
                result = get_content_by_type(request)
                
                # Express equivalent: Utils.toArray(body, 'utf8')
                expected_processed = text_content.encode('utf-8')
                
                self.assertEqual(result['processed_body'], expected_processed)
                self.assertEqual(result['data'], text_content)
                self.assertEqual(result['encoding'], 'utf-8')

    @patch('bsv_middleware.django.utils.logger')
    def test_logging_for_text_plain(self, mock_logger):
        """Test that appropriate logging occurs"""
        request = self._create_text_request(self.test_text_utf8)
        
        result = get_text_content(request)
        
        # Verify debug log was called
        mock_logger.debug.assert_called()
        log_message = mock_logger.debug.call_args[0][0]
        self.assertIn('Decoded text/plain content', log_message)

    def test_empty_text_content(self):
        """Test handling of empty text/plain content"""
        request = self._create_text_request("")
        
        result = get_content_by_type(request)
        
        self.assertEqual(result['data'], "")
        self.assertEqual(result['processed_body'], b"")
        self.assertEqual(result['content_type'], 'text/plain')


class TestExpressCompatibilityTextPlain(TestCase):
    """Test Express middleware compatibility for text/plain"""
    
    def test_text_plain_matches_express_writeBodyToWriter(self):
        """
        Verify our implementation matches Express writeBodyToWriter logic:
        
        Express code:
        if (headers['content-type'] === 'text/plain' && 
            typeof body === 'string' && 
            body.length > 0) {
            const bodyAsArray = Utils.toArray(body, 'utf8')
            writer.writeVarIntNum(bodyAsArray.length)
            writer.write(bodyAsArray)
        }
        """
        
        # Test the exact same logic as Express
        test_text = "BSV Protocol Test Message"
        request = HttpRequest()
        request.META['CONTENT_TYPE'] = 'text/plain'
        request._body = test_text.encode('utf-8')
        
        result = get_content_by_type(request)
        
        # Express: Utils.toArray(body, 'utf8') creates UTF-8 byte array
        expected_bytes = test_text.encode('utf-8')
        
        # Verify our processing matches Express
        self.assertEqual(result['processed_body'], expected_bytes)
        self.assertEqual(len(result['processed_body']), len(expected_bytes))
        
        # Verify data structure matches Express expectations
        self.assertEqual(result['content_type'], 'text/plain')
        self.assertEqual(result['encoding'], 'utf-8')
        self.assertIsInstance(result['data'], str)


if __name__ == '__main__':
    pytest.main([__file__])
