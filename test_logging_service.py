"""
Tests for the logging service module.

This module contains comprehensive tests for the logging service functionality,
including structured logging, different formatters, and logging operations.
"""

import unittest
import logging
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO

from services.logging_service import (
    LoggingService, StructuredFormatter, HumanReadableFormatter,
    LogEntry, configure_logging, get_logger, log_operation, log_request, log_error,
    get_logging_service
)


class TestLogEntry(unittest.TestCase):
    """Test LogEntry data class."""
    
    def test_log_entry_creation(self):
        """Test creating a log entry."""
        entry = LogEntry(
            timestamp="2024-01-01T12:00:00",
            level="INFO",
            logger_name="test.logger",
            message="Test message",
            module="test_module",
            function="test_function",
            line_number=42,
            extra_data={"key": "value"}
        )
        
        self.assertEqual(entry.timestamp, "2024-01-01T12:00:00")
        self.assertEqual(entry.level, "INFO")
        self.assertEqual(entry.logger_name, "test.logger")
        self.assertEqual(entry.message, "Test message")
        self.assertEqual(entry.module, "test_module")
        self.assertEqual(entry.function, "test_function")
        self.assertEqual(entry.line_number, 42)
        self.assertEqual(entry.extra_data, {"key": "value"})
    
    def test_log_entry_to_dict(self):
        """Test converting log entry to dictionary."""
        entry = LogEntry(
            timestamp="2024-01-01T12:00:00",
            level="INFO",
            logger_name="test.logger",
            message="Test message"
        )
        
        result = entry.to_dict()
        expected = {
            'timestamp': "2024-01-01T12:00:00",
            'level': "INFO",
            'logger_name': "test.logger",
            'message': "Test message",
            'module': None,
            'function': None,
            'line_number': None,
            'extra_data': None
        }
        
        self.assertEqual(result, expected)
    
    def test_log_entry_to_json(self):
        """Test converting log entry to JSON."""
        entry = LogEntry(
            timestamp="2024-01-01T12:00:00",
            level="INFO",
            logger_name="test.logger",
            message="Test message"
        )
        
        result = entry.to_json()
        parsed = json.loads(result)
        
        self.assertEqual(parsed['timestamp'], "2024-01-01T12:00:00")
        self.assertEqual(parsed['level'], "INFO")
        self.assertEqual(parsed['logger_name'], "test.logger")
        self.assertEqual(parsed['message'], "Test message")


class TestStructuredFormatter(unittest.TestCase):
    """Test StructuredFormatter class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.formatter = StructuredFormatter()
    
    def test_format_basic_record(self):
        """Test formatting a basic log record."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        result = self.formatter.format(record)
        parsed = json.loads(result)
        
        self.assertEqual(parsed['level'], "INFO")
        self.assertEqual(parsed['logger_name'], "test.logger")
        self.assertEqual(parsed['message'], "Test message")
        self.assertIn('timestamp', parsed)
    
    def test_format_record_with_extra_data(self):
        """Test formatting a log record with extra data."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.extra_data = {"key": "value", "number": 123}
        
        result = self.formatter.format(record)
        parsed = json.loads(result)
        
        self.assertEqual(parsed['extra_data'], {"key": "value", "number": 123})


class TestHumanReadableFormatter(unittest.TestCase):
    """Test HumanReadableFormatter class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.formatter = HumanReadableFormatter(use_colors=False)
    
    def test_format_basic_record(self):
        """Test formatting a basic log record."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        result = self.formatter.format(record)
        
        self.assertIn("INFO", result)
        self.assertIn("test.logger", result)
        self.assertIn("Test message", result)
        self.assertIn("2025", result)  # Should contain timestamp
    
    def test_format_record_with_extra_data(self):
        """Test formatting a log record with extra data."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.extra_data = {"key": "value"}
        
        result = self.formatter.format(record)
        
        self.assertIn("Test message", result)
        self.assertIn('"key": "value"', result)
    
    def test_format_debug_record_includes_location(self):
        """Test that DEBUG level records include location info."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=42,
            msg="Debug message",
            args=(),
            exc_info=None
        )
        record.filename = "test.py"
        
        result = self.formatter.format(record)
        
        self.assertIn("Debug message", result)
        self.assertIn("[test.py:42]", result)


class TestLoggingService(unittest.TestCase):
    """Test LoggingService class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.service = LoggingService()
    
    def tearDown(self):
        """Clean up after tests."""
        self.service.shutdown()
    
    def test_configure_basic(self):
        """Test basic configuration."""
        self.service.configure(level="DEBUG")
        
        self.assertTrue(self.service._configured)
        self.assertEqual(self.service._log_level, logging.DEBUG)
        self.assertFalse(self.service._use_structured_format)
        self.assertIsNone(self.service._log_file_path)
    
    def test_configure_with_file(self):
        """Test configuration with log file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            log_file = os.path.join(temp_dir, "test.log")
            
            self.service.configure(
                level="INFO",
                log_file_path=log_file,
                use_structured_format=True
            )
            
            self.assertTrue(self.service._configured)
            self.assertEqual(self.service._log_level, logging.INFO)
            self.assertTrue(self.service._use_structured_format)
            self.assertEqual(str(self.service._log_file_path), log_file)
            
            # Properly shutdown to release file handles
            self.service.shutdown()
    
    def test_get_logger(self):
        """Test getting a logger."""
        self.service.configure()
        
        logger1 = self.service.get_logger("test.logger1")
        logger2 = self.service.get_logger("test.logger2")
        logger1_again = self.service.get_logger("test.logger1")
        
        self.assertIsInstance(logger1, logging.Logger)
        self.assertIsInstance(logger2, logging.Logger)
        self.assertIs(logger1, logger1_again)  # Should return same instance
        self.assertIsNot(logger1, logger2)     # Should be different instances
    
    def test_log_operation(self):
        """Test logging an operation."""
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            self.service.configure(level="INFO")
            
            self.service.log_operation(
                logger_name="test.logger",
                operation="test_operation",
                duration_ms=123.45,
                success=True,
                extra_data={"key": "value"}
            )
            
            output = mock_stderr.getvalue()
            self.assertIn("test_operation", output)
            self.assertIn("SUCCESS", output)
            self.assertIn("123.45ms", output)
    
    def test_log_request(self):
        """Test logging a request."""
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            self.service.configure(level="INFO")
            
            self.service.log_request(
                logger_name="test.logger",
                method="POST",
                path="/api/test",
                status_code=200,
                duration_ms=50.0,
                client_info={"ip": "127.0.0.1"}
            )
            
            output = mock_stderr.getvalue()
            self.assertIn("POST", output)
            self.assertIn("/api/test", output)
            self.assertIn("200", output)
            self.assertIn("50.00ms", output)
    
    def test_log_error(self):
        """Test logging an error."""
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            self.service.configure(level="ERROR")
            
            try:
                raise ValueError("Test error")
            except ValueError as e:
                self.service.log_error(
                    logger_name="test.logger",
                    error=e,
                    context="Test context",
                    extra_data={"key": "value"}
                )
            
            output = mock_stderr.getvalue()
            self.assertIn("ValueError", output)
            self.assertIn("Test error", output)
            self.assertIn("Test context", output)
    
    def test_get_log_stats(self):
        """Test getting log statistics."""
        self.service.configure(level="DEBUG", use_structured_format=True)
        self.service.get_logger("test.logger1")
        self.service.get_logger("test.logger2")
        
        stats = self.service.get_log_stats()
        
        self.assertTrue(stats['configured'])
        self.assertEqual(stats['log_level'], "DEBUG")
        self.assertTrue(stats['structured_format'])
        self.assertIsNone(stats['log_file'])
        self.assertGreaterEqual(stats['loggers_count'], 2)  # May include service's own logger
    
    def test_shutdown(self):
        """Test shutting down the service."""
        self.service.configure()
        self.service.get_logger("test.logger")
        
        self.assertTrue(self.service._configured)
        self.assertGreater(len(self.service._loggers), 0)
        
        self.service.shutdown()
        
        self.assertFalse(self.service._configured)
        self.assertEqual(len(self.service._loggers), 0)


class TestGlobalFunctions(unittest.TestCase):
    """Test global logging functions."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Reset global service
        import services.logging_service
        services.logging_service._logging_service = None
    
    def test_configure_logging(self):
        """Test global configure_logging function."""
        configure_logging(level="DEBUG", use_structured_format=True)
        
        service = get_logging_service()
        self.assertTrue(service._configured)
        self.assertEqual(service._log_level, logging.DEBUG)
        self.assertTrue(service._use_structured_format)
    
    def test_get_logger(self):
        """Test global get_logger function."""
        configure_logging()
        
        logger = get_logger("test.logger")
        self.assertIsInstance(logger, logging.Logger)
        self.assertEqual(logger.name, "test.logger")
    
    def test_log_operation_global(self):
        """Test global log_operation function."""
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            configure_logging(level="INFO")
            
            log_operation(
                logger_name="test.logger",
                operation="global_test",
                success=True
            )
            
            output = mock_stderr.getvalue()
            self.assertIn("global_test", output)
            self.assertIn("SUCCESS", output)
    
    def test_log_request_global(self):
        """Test global log_request function."""
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            configure_logging(level="INFO")
            
            log_request(
                logger_name="test.logger",
                method="GET",
                path="/test",
                status_code=200
            )
            
            output = mock_stderr.getvalue()
            self.assertIn("GET", output)
            self.assertIn("/test", output)
            self.assertIn("200", output)
    
    def test_log_error_global(self):
        """Test global log_error function."""
        with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
            configure_logging(level="ERROR")
            
            try:
                raise RuntimeError("Global test error")
            except RuntimeError as e:
                log_error(
                    logger_name="test.logger",
                    error=e,
                    context="Global test context"
                )
            
            output = mock_stderr.getvalue()
            self.assertIn("RuntimeError", output)
            self.assertIn("Global test error", output)
            self.assertIn("Global test context", output)


if __name__ == '__main__':
    unittest.main()