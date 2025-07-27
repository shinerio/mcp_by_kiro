"""
Unit tests for ErrorHandler

Tests the error handling functionality including error creation,
exception handling, and logging integration.
"""

import logging
import unittest
from unittest.mock import Mock, patch
from services.error_handler import ErrorHandler
from models.mcp_models import MCPError, MCPErrorCodes


class TestErrorHandler(unittest.TestCase):
    """Test suite for ErrorHandler implementation"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.mock_logger = Mock(spec=logging.Logger)
        self.error_handler = ErrorHandler(logger=self.mock_logger)
        self.error_handler_default = ErrorHandler()  # Test with default logger
    
    def test_create_error_basic(self):
        """Test basic error creation"""
        code = -32600
        message = "Test error"
        data = {"key": "value"}
        
        error = self.error_handler.create_error(code, message, data)
        
        self.assertIsInstance(error, MCPError)
        self.assertEqual(error.code, code)
        self.assertEqual(error.message, message)
        self.assertEqual(error.data, data)
        
        # Verify logging was called
        self.mock_logger.error.assert_called_once()
    
    def test_create_error_without_data(self):
        """Test error creation without optional data"""
        code = -32600
        message = "Test error"
        
        error = self.error_handler.create_error(code, message)
        
        self.assertEqual(error.code, code)
        self.assertEqual(error.message, message)
        self.assertIsNone(error.data)
    
    def test_create_parse_error(self):
        """Test parse error creation"""
        details = "Invalid JSON syntax"
        error = self.error_handler.create_parse_error(details)
        
        self.assertEqual(error.code, MCPErrorCodes.PARSE_ERROR)
        self.assertEqual(error.message, "Parse error")
        self.assertEqual(error.data["details"], details)
    
    def test_create_parse_error_default(self):
        """Test parse error creation with default details"""
        error = self.error_handler.create_parse_error()
        
        self.assertEqual(error.code, MCPErrorCodes.PARSE_ERROR)
        self.assertEqual(error.message, "Parse error")
        self.assertEqual(error.data["details"], "Invalid JSON format")
    
    def test_create_invalid_request_error(self):
        """Test invalid request error creation"""
        details = "Missing required field"
        error = self.error_handler.create_invalid_request_error(details)
        
        self.assertEqual(error.code, MCPErrorCodes.INVALID_REQUEST)
        self.assertEqual(error.message, "Invalid Request")
        self.assertEqual(error.data["details"], details)
    
    def test_create_method_not_found_error(self):
        """Test method not found error creation"""
        method = "unknown/method"
        error = self.error_handler.create_method_not_found_error(method)
        
        self.assertEqual(error.code, MCPErrorCodes.METHOD_NOT_FOUND)
        self.assertEqual(error.message, "Method not found")
        self.assertEqual(error.data["method"], method)
    
    def test_create_invalid_params_error(self):
        """Test invalid params error creation"""
        details = "Parameter validation failed"
        error = self.error_handler.create_invalid_params_error(details)
        
        self.assertEqual(error.code, MCPErrorCodes.INVALID_PARAMS)
        self.assertEqual(error.message, "Invalid params")
        self.assertEqual(error.data["details"], details)
    
    def test_create_internal_error(self):
        """Test internal error creation"""
        details = "Database connection failed"
        error = self.error_handler.create_internal_error(details)
        
        self.assertEqual(error.code, MCPErrorCodes.INTERNAL_ERROR)
        self.assertEqual(error.message, "Internal error")
        self.assertEqual(error.data["details"], details)
    
    def test_create_invalid_base64_error(self):
        """Test invalid base64 error creation"""
        details = "Contains invalid characters"
        error = self.error_handler.create_invalid_base64_error(details)
        
        self.assertEqual(error.code, MCPErrorCodes.INVALID_BASE64)
        self.assertEqual(error.message, "Invalid base64 string")
        self.assertEqual(error.data["details"], details)
    
    def test_create_encoding_error(self):
        """Test encoding error creation"""
        details = "UTF-8 encoding failed"
        error = self.error_handler.create_encoding_error(details)
        
        self.assertEqual(error.code, MCPErrorCodes.ENCODING_ERROR)
        self.assertEqual(error.message, "Encoding error")
        self.assertEqual(error.data["details"], details)
    
    def test_create_decoding_error(self):
        """Test decoding error creation"""
        details = "Base64 decoding failed"
        error = self.error_handler.create_decoding_error(details)
        
        self.assertEqual(error.code, MCPErrorCodes.DECODING_ERROR)
        self.assertEqual(error.message, "Decoding error")
        self.assertEqual(error.data["details"], details)
    
    def test_create_tool_not_found_error(self):
        """Test tool not found error creation"""
        tool_name = "unknown_tool"
        error = self.error_handler.create_tool_not_found_error(tool_name)
        
        self.assertEqual(error.code, MCPErrorCodes.TOOL_NOT_FOUND)
        self.assertEqual(error.message, "Tool not found")
        self.assertEqual(error.data["tool_name"], tool_name)
    
    def test_handle_value_error(self):
        """Test handling ValueError exception"""
        exception = ValueError("Invalid input value")
        context = "Base64 encoding"
        
        error = self.error_handler.handle_exception(exception, context)
        
        self.assertEqual(error.code, MCPErrorCodes.INVALID_PARAMS)
        self.assertEqual(error.message, "Invalid params")
        self.assertIn("Base64 encoding: Invalid input value", error.data["details"])
        
        # Verify exception logging was called
        self.mock_logger.exception.assert_called_once()
    
    def test_handle_key_error(self):
        """Test handling KeyError exception"""
        exception = KeyError("missing_key")
        context = "Request processing"
        
        error = self.error_handler.handle_exception(exception, context)
        
        self.assertEqual(error.code, MCPErrorCodes.INVALID_REQUEST)
        self.assertEqual(error.message, "Invalid Request")
        self.assertIn("Request processing", error.data["details"])
    
    def test_handle_not_implemented_error(self):
        """Test handling NotImplementedError exception"""
        exception = NotImplementedError("Feature not ready")
        context = "Tool execution"
        
        error = self.error_handler.handle_exception(exception, context)
        
        self.assertEqual(error.code, MCPErrorCodes.INTERNAL_ERROR)
        self.assertEqual(error.message, "Internal error")
        self.assertIn("Feature not implemented", error.data["details"])
    
    def test_handle_generic_exception(self):
        """Test handling generic exception"""
        exception = RuntimeError("Unexpected error")
        context = "Server operation"
        
        error = self.error_handler.handle_exception(exception, context)
        
        self.assertEqual(error.code, MCPErrorCodes.INTERNAL_ERROR)
        self.assertEqual(error.message, "Internal error")
        self.assertIn("Server operation: Unexpected error", error.data["details"])
    
    def test_handle_exception_without_context(self):
        """Test handling exception without context"""
        exception = ValueError("Test error")
        
        error = self.error_handler.handle_exception(exception)
        
        self.assertEqual(error.code, MCPErrorCodes.INVALID_PARAMS)
        self.assertEqual(error.data["details"], "Test error")
    
    def test_default_logger_initialization(self):
        """Test ErrorHandler with default logger"""
        # This should not raise an exception
        handler = ErrorHandler()
        error = handler.create_error(-1000, "Test message")
        
        self.assertIsInstance(error, MCPError)
        self.assertEqual(error.code, -1000)
        self.assertEqual(error.message, "Test message")
    
    def test_error_logging_format(self):
        """Test that error logging includes all relevant information"""
        code = -32600
        message = "Test error"
        data = {"key": "value"}
        
        self.error_handler.create_error(code, message, data)
        
        # Verify the log message format
        expected_log = f"Error created - Code: {code}, Message: {message}, Data: {data}"
        self.mock_logger.error.assert_called_once_with(expected_log)
    
    def test_exception_logging_format(self):
        """Test that exception logging includes context and exception details"""
        exception = ValueError("Test exception")
        context = "Test context"
        
        self.error_handler.handle_exception(exception, context)
        
        # Verify exception logging was called
        self.mock_logger.exception.assert_called_once_with(f"Exception handled: {context}: {str(exception)}")
    
    def test_handle_type_error(self):
        """Test handling TypeError exception"""
        exception = TypeError("Expected string, got int")
        context = "Parameter validation"
        
        error = self.error_handler.handle_exception(exception, context)
        
        self.assertEqual(error.code, MCPErrorCodes.INVALID_PARAMS)
        self.assertEqual(error.message, "Invalid params")
        self.assertIn("Type error", error.data["details"])
    
    def test_handle_attribute_error(self):
        """Test handling AttributeError exception"""
        exception = AttributeError("'NoneType' object has no attribute 'method'")
        
        error = self.error_handler.handle_exception(exception)
        
        self.assertEqual(error.code, MCPErrorCodes.INTERNAL_ERROR)
        self.assertEqual(error.message, "Internal error")
        self.assertIn("Attribute error", error.data["details"])
    
    def test_handle_import_error(self):
        """Test handling ImportError exception"""
        exception = ImportError("No module named 'missing_module'")
        
        error = self.error_handler.handle_exception(exception)
        
        self.assertEqual(error.code, MCPErrorCodes.INTERNAL_ERROR)
        self.assertEqual(error.message, "Internal error")
        self.assertIn("Import error", error.data["details"])
    
    def test_handle_connection_error(self):
        """Test handling ConnectionError exception"""
        exception = ConnectionError("Connection refused")
        
        error = self.error_handler.handle_exception(exception)
        
        self.assertEqual(error.code, MCPErrorCodes.INTERNAL_ERROR)
        self.assertEqual(error.message, "Internal error")
        self.assertIn("Connection error", error.data["details"])
    
    def test_handle_timeout_error(self):
        """Test handling TimeoutError exception"""
        exception = TimeoutError("Operation timed out")
        
        error = self.error_handler.handle_exception(exception)
        
        self.assertEqual(error.code, MCPErrorCodes.INTERNAL_ERROR)
        self.assertEqual(error.message, "Internal error")
        self.assertIn("Timeout error", error.data["details"])
    
    def test_validate_request_format_valid(self):
        """Test validation of valid MCP request format"""
        valid_request = {
            "jsonrpc": "2.0",
            "id": "test-id",
            "method": "tools/list",
            "params": {}
        }
        
        error = self.error_handler.validate_request_format(valid_request)
        
        self.assertIsNone(error)
    
    def test_validate_request_format_not_dict(self):
        """Test validation fails for non-dict request"""
        invalid_request = "not a dict"
        
        error = self.error_handler.validate_request_format(invalid_request)
        
        self.assertIsNotNone(error)
        self.assertEqual(error.code, MCPErrorCodes.INVALID_REQUEST)
        self.assertIn("must be a JSON object", error.data["details"])
    
    def test_validate_request_format_missing_jsonrpc(self):
        """Test validation fails for missing jsonrpc field"""
        invalid_request = {
            "id": "test-id",
            "method": "tools/list"
        }
        
        error = self.error_handler.validate_request_format(invalid_request)
        
        self.assertIsNotNone(error)
        self.assertEqual(error.code, MCPErrorCodes.INVALID_REQUEST)
        self.assertIn("Missing 'jsonrpc' field", error.data["details"])
    
    def test_validate_request_format_invalid_jsonrpc_version(self):
        """Test validation fails for invalid jsonrpc version"""
        invalid_request = {
            "jsonrpc": "1.0",
            "method": "tools/list"
        }
        
        error = self.error_handler.validate_request_format(invalid_request)
        
        self.assertIsNotNone(error)
        self.assertEqual(error.code, MCPErrorCodes.INVALID_REQUEST)
        self.assertIn("Invalid 'jsonrpc' version", error.data["details"])
    
    def test_validate_request_format_missing_method(self):
        """Test validation fails for missing method field"""
        invalid_request = {
            "jsonrpc": "2.0",
            "id": "test-id"
        }
        
        error = self.error_handler.validate_request_format(invalid_request)
        
        self.assertIsNotNone(error)
        self.assertEqual(error.code, MCPErrorCodes.INVALID_REQUEST)
        self.assertIn("Missing 'method' field", error.data["details"])
    
    def test_validate_request_format_invalid_method_type(self):
        """Test validation fails for non-string method"""
        invalid_request = {
            "jsonrpc": "2.0",
            "method": 123
        }
        
        error = self.error_handler.validate_request_format(invalid_request)
        
        self.assertIsNotNone(error)
        self.assertEqual(error.code, MCPErrorCodes.INVALID_REQUEST)
        self.assertIn("'method' field must be a string", error.data["details"])
    
    def test_validate_request_format_invalid_id_type(self):
        """Test validation fails for invalid id type"""
        invalid_request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": []  # Invalid type
        }
        
        error = self.error_handler.validate_request_format(invalid_request)
        
        self.assertIsNotNone(error)
        self.assertEqual(error.code, MCPErrorCodes.INVALID_REQUEST)
        self.assertIn("'id' field must be string, number, or null", error.data["details"])
    
    def test_validate_request_format_invalid_params_type(self):
        """Test validation fails for non-object params"""
        invalid_request = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "params": "not an object"
        }
        
        error = self.error_handler.validate_request_format(invalid_request)
        
        self.assertIsNotNone(error)
        self.assertEqual(error.code, MCPErrorCodes.INVALID_REQUEST)
        self.assertIn("'params' field must be an object", error.data["details"])
    
    def test_validate_base64_format_valid(self):
        """Test validation of valid base64 string"""
        valid_base64 = "SGVsbG8gV29ybGQ="  # "Hello World" in base64
        
        error = self.error_handler.validate_base64_format(valid_base64)
        
        self.assertIsNone(error)
    
    def test_validate_base64_format_not_string(self):
        """Test validation fails for non-string input"""
        invalid_input = 123
        
        error = self.error_handler.validate_base64_format(invalid_input)
        
        self.assertIsNotNone(error)
        self.assertEqual(error.code, MCPErrorCodes.INVALID_BASE64)
        self.assertIn("must be a string", error.data["details"])
    
    def test_validate_base64_format_empty_string(self):
        """Test validation fails for empty string"""
        empty_string = "   "
        
        error = self.error_handler.validate_base64_format(empty_string)
        
        self.assertIsNotNone(error)
        self.assertEqual(error.code, MCPErrorCodes.INVALID_BASE64)
        self.assertIn("cannot be empty", error.data["details"])
    
    def test_validate_base64_format_invalid_characters(self):
        """Test validation fails for invalid characters"""
        invalid_base64 = "Hello@World!"
        
        error = self.error_handler.validate_base64_format(invalid_base64)
        
        self.assertIsNotNone(error)
        self.assertEqual(error.code, MCPErrorCodes.INVALID_BASE64)
        self.assertIn("invalid characters", error.data["details"])
    
    def test_validate_base64_format_invalid_length(self):
        """Test validation fails for invalid length"""
        invalid_base64 = "SGVsbG"  # Invalid length (not multiple of 4)
        
        error = self.error_handler.validate_base64_format(invalid_base64)
        
        self.assertIsNotNone(error)
        self.assertEqual(error.code, MCPErrorCodes.INVALID_BASE64)
        self.assertIn("multiple of 4", error.data["details"])
    
    def test_validate_base64_format_with_whitespace(self):
        """Test validation handles whitespace correctly"""
        base64_with_whitespace = "SGVs\nbG8g\r\nV29y\n bGQ="
        
        error = self.error_handler.validate_base64_format(base64_with_whitespace)
        
        self.assertIsNone(error)  # Should be valid after removing whitespace
    
    def test_create_http_error_response_basic(self):
        """Test creation of basic HTTP error response"""
        status_code = 400
        message = "Bad Request"
        
        response = self.error_handler.create_http_error_response(status_code, message)
        
        self.assertFalse(response["success"])
        self.assertEqual(response["error"]["code"], status_code)
        self.assertEqual(response["error"]["message"], message)
        self.assertNotIn("details", response["error"])
        
        # Verify logging was called
        self.mock_logger.error.assert_called_once()
    
    def test_create_http_error_response_with_details(self):
        """Test creation of HTTP error response with details"""
        status_code = 422
        message = "Validation Error"
        details = "Invalid base64 format"
        
        response = self.error_handler.create_http_error_response(status_code, message, details)
        
        self.assertFalse(response["success"])
        self.assertEqual(response["error"]["code"], status_code)
        self.assertEqual(response["error"]["message"], message)
        self.assertEqual(response["error"]["details"], details)


if __name__ == "__main__":
    unittest.main()