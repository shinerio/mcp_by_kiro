"""
Unit tests for Base64Service

Tests the core functionality of Base64 encoding/decoding service including
validation, error handling, and edge cases.
"""

import pytest
from services.base64_service import Base64Service


class TestBase64Service:
    """Test suite for Base64Service implementation"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.service = Base64Service()
    
    def test_encode_simple_text(self):
        """Test encoding simple ASCII text"""
        text = "Hello, World!"
        expected = "SGVsbG8sIFdvcmxkIQ=="
        result = self.service.encode(text)
        assert result == expected
    
    def test_encode_empty_string(self):
        """Test encoding empty string"""
        text = ""
        expected = ""
        result = self.service.encode(text)
        assert result == expected
    
    def test_encode_unicode_text(self):
        """Test encoding Unicode text"""
        text = "你好世界"
        result = self.service.encode(text)
        # Verify it's valid base64 and can be decoded back
        decoded = self.service.decode(result)
        assert decoded == text
    
    def test_decode_simple_base64(self):
        """Test decoding simple base64 string"""
        base64_string = "SGVsbG8sIFdvcmxkIQ=="
        expected = "Hello, World!"
        result = self.service.decode(base64_string)
        assert result == expected
    
    def test_decode_empty_base64(self):
        """Test decoding empty base64 string should fail"""
        with pytest.raises(ValueError, match="Base64 string cannot be empty"):
            self.service.decode("")
    
    def test_encode_decode_roundtrip(self):
        """Test that encode->decode returns original text"""
        original_texts = [
            "Hello, World!",
            "Python is awesome",
            "Special chars: !@#$%^&*()",
            "Unicode: 你好世界 🌍",
            "Numbers: 12345",
            "Mixed: Hello世界123!@#"
        ]
        
        for text in original_texts:
            encoded = self.service.encode(text)
            decoded = self.service.decode(encoded)
            assert decoded == text
    
    def test_validate_base64_valid_strings(self):
        """Test validation of valid base64 strings"""
        valid_strings = [
            "SGVsbG8=",
            "SGVsbG8sIFdvcmxkIQ==",
            "YWJjZA==",
            "YWJjZGU=",
            "YWJjZGVm"
        ]
        
        for base64_str in valid_strings:
            is_valid, error_msg = self.service.validate_base64(base64_str)
            assert is_valid, f"Should be valid: {base64_str}, error: {error_msg}"
            assert error_msg == ""
    
    def test_validate_base64_invalid_strings(self):
        """Test validation of invalid base64 strings"""
        invalid_strings = [
            "",  # Empty string
            "SGVsbG8",  # Wrong length (not multiple of 4)
            "SGVsbG8===",  # Too many padding chars
            "SGVs=bG8=",  # Padding in wrong position
            "SGVsbG8@",  # Invalid character
            "SGVsbG8 ",  # Space character
        ]
        
        for base64_str in invalid_strings:
            is_valid, error_msg = self.service.validate_base64(base64_str)
            assert not is_valid, f"Should be invalid: {base64_str}"
            assert error_msg != ""
    
    def test_is_valid_text_valid_inputs(self):
        """Test text validation for valid inputs"""
        valid_texts = [
            "",  # Empty string is valid
            "Hello",
            "Unicode: 你好",
            "Numbers: 123",
            "Special: !@#$%"
        ]
        
        for text in valid_texts:
            is_valid, error_msg = self.service.is_valid_text(text)
            assert is_valid, f"Should be valid: {text}, error: {error_msg}"
            assert error_msg == ""
    
    def test_is_valid_text_invalid_inputs(self):
        """Test text validation for invalid inputs"""
        # Test non-string input
        is_valid, error_msg = self.service.is_valid_text(123)
        assert not is_valid
        assert "Input must be a string" in error_msg
        
        # Test very long text
        long_text = "a" * (self.service.MAX_TEXT_LENGTH + 1)
        is_valid, error_msg = self.service.is_valid_text(long_text)
        assert not is_valid
        assert "Text too long" in error_msg
    
    def test_encode_invalid_input(self):
        """Test encoding with invalid input"""
        with pytest.raises(ValueError, match="Invalid text input"):
            self.service.encode(123)  # Non-string input
    
    def test_decode_invalid_base64(self):
        """Test decoding with invalid base64"""
        with pytest.raises(ValueError, match="Invalid base64 input"):
            self.service.decode("invalid@base64")
    
    def test_decode_invalid_utf8(self):
        """Test decoding base64 that doesn't represent valid UTF-8"""
        # This is valid base64 but represents invalid UTF-8 bytes
        invalid_utf8_base64 = "wA=="  # Represents byte 0xC0 which is invalid UTF-8
        with pytest.raises(ValueError, match="Text decoding failed"):
            self.service.decode(invalid_utf8_base64)


if __name__ == "__main__":
    pytest.main([__file__])