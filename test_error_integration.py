"""
Integration tests for ErrorHandler

Tests the error handling functionality in realistic scenarios
that demonstrate how the ErrorHandler integrates with other components.
"""

import json
import unittest
from services.error_handler import ErrorHandler
from models.mcp_models import MCPErrorCodes


class TestErrorHandlerIntegration(unittest.TestCase):
    """Integration test suite for ErrorHandler"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.error_handler = ErrorHandler()
    
    def test_mcp_request_validation_workflow(self):
        """Test complete MCP request validation workflow"""
        # Test valid request
        valid_request = {
            "jsonrpc": "2.0",
            "id": "test-123",
            "method": "tools/call",
            "params": {
                "name": "base64_encode",
                "arguments": {"text": "Hello World"}
            }
        }
        
        error = self.error_handler.validate_request_format(valid_request)
        self.assertIsNone(error)
        
        # Test invalid request - missing method
        invalid_request = {
            "jsonrpc": "2.0",
            "id": "test-123",
            "params": {"name": "base64_encode"}
        }
        
        error = self.error_handler.validate_request_format(invalid_request)
        self.assertIsNotNone(error)
        self.assertEqual(error.code, MCPErrorCodes.INVALID_REQUEST)
    
    def test_base64_validation_workflow(self):
        """Test complete base64 validation workflow"""
        # Test valid base64
        valid_base64 = "SGVsbG8gV29ybGQ="  # "Hello World"
        error = self.error_handler.validate_base64_format(valid_base64)
        self.assertIsNone(error)
        
        # Test invalid base64
        invalid_base64 = "Hello World!"  # Not base64
        error = self.error_handler.validate_base64_format(invalid_base64)
        self.assertIsNotNone(error)
        self.assertEqual(error.code, MCPErrorCodes.INVALID_BASE64)
    
    def test_exception_to_mcp_error_workflow(self):
        """Test exception handling to MCP error conversion workflow"""
        # Simulate different types of exceptions that might occur
        exceptions_and_expected_codes = [
            (ValueError("Invalid input"), MCPErrorCodes.INVALID_PARAMS),
            (KeyError("missing_key"), MCPErrorCodes.INVALID_REQUEST),
            (TypeError("Wrong type"), MCPErrorCodes.INVALID_PARAMS),
            (ConnectionError("Network error"), MCPErrorCodes.INTERNAL_ERROR),
            (RuntimeError("Unexpected error"), MCPErrorCodes.INTERNAL_ERROR),
        ]
        
        for exception, expected_code in exceptions_and_expected_codes:
            with self.subTest(exception=type(exception).__name__):
                error = self.error_handler.handle_exception(exception, "Test context")
                self.assertEqual(error.code, expected_code)
                self.assertIn("Test context", error.data["details"])
    
    def test_http_error_response_workflow(self):
        """Test HTTP error response creation workflow"""
        # Test different HTTP error scenarios
        test_cases = [
            (400, "Bad Request", "Invalid JSON format"),
            (422, "Unprocessable Entity", "Invalid base64 string"),
            (500, "Internal Server Error", "Database connection failed"),
        ]
        
        for status_code, message, details in test_cases:
            with self.subTest(status_code=status_code):
                response = self.error_handler.create_http_error_response(
                    status_code, message, details
                )
                
                self.assertFalse(response["success"])
                self.assertEqual(response["error"]["code"], status_code)
                self.assertEqual(response["error"]["message"], message)
                self.assertEqual(response["error"]["details"], details)
    
    def test_error_chain_workflow(self):
        """Test chaining multiple error handling operations"""
        # Simulate a complex error scenario
        try:
            # Simulate parsing invalid JSON
            invalid_json = '{"jsonrpc": "2.0", "method": "tools/call", "params": {'
            json.loads(invalid_json)
        except json.JSONDecodeError as e:
            # Handle JSON parsing error
            mcp_error = self.error_handler.handle_exception(e, "JSON parsing")
            # JSONDecodeError inherits from ValueError, so it maps to INVALID_PARAMS
            self.assertEqual(mcp_error.code, MCPErrorCodes.INVALID_PARAMS)
            
            # Convert to HTTP error response
            http_response = self.error_handler.create_http_error_response(
                400, "Bad Request", mcp_error.data["details"]
            )
            
            self.assertFalse(http_response["success"])
            self.assertEqual(http_response["error"]["code"], 400)
            self.assertIn("JSON parsing", http_response["error"]["details"])
    
    def test_comprehensive_error_scenarios(self):
        """Test comprehensive error scenarios that might occur in production"""
        # Scenario 1: Invalid MCP request format
        invalid_requests = [
            None,  # Not a dict
            {},  # Missing required fields
            {"jsonrpc": "1.0"},  # Wrong version
            {"jsonrpc": "2.0", "method": 123},  # Wrong method type
        ]
        
        for invalid_request in invalid_requests:
            with self.subTest(request=invalid_request):
                error = self.error_handler.validate_request_format(invalid_request)
                self.assertIsNotNone(error)
                self.assertEqual(error.code, MCPErrorCodes.INVALID_REQUEST)
        
        # Scenario 2: Invalid base64 strings
        invalid_base64_strings = [
            "",  # Empty
            "   ",  # Whitespace only
            "Hello@World!",  # Invalid characters
            "SGVsbG",  # Invalid length
            123,  # Not a string
        ]
        
        for invalid_base64 in invalid_base64_strings:
            with self.subTest(base64=invalid_base64):
                error = self.error_handler.validate_base64_format(invalid_base64)
                self.assertIsNotNone(error)
                self.assertEqual(error.code, MCPErrorCodes.INVALID_BASE64)


if __name__ == "__main__":
    unittest.main()