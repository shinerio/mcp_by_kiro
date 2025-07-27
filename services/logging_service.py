"""
Logging service for MCP Base64 Server.

This module provides structured logging functionality with different levels,
formatters, and handlers. It supports both development and production logging
configurations with proper log rotation and filtering.
"""

import logging
import logging.handlers
import sys
import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum


class LogLevel(Enum):
    """Log level enumeration."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogEntry:
    """Structured log entry data class."""
    timestamp: str
    level: str
    logger_name: str
    message: str
    module: Optional[str] = None
    function: Optional[str] = None
    line_number: Optional[int] = None
    extra_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert log entry to dictionary."""
        return asdict(self)
    
    def to_json(self) -> str:
        """Convert log entry to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False)


class StructuredFormatter(logging.Formatter):
    """
    Structured log formatter that outputs JSON format.
    
    This formatter creates structured log entries with consistent fields
    for better log analysis and monitoring.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as structured JSON.
        
        Args:
            record: Log record to format
            
        Returns:
            Formatted log entry as JSON string
        """
        # Create structured log entry
        log_entry = LogEntry(
            timestamp=datetime.fromtimestamp(record.created).isoformat(),
            level=record.levelname,
            logger_name=record.name,
            message=record.getMessage(),
            module=record.module if hasattr(record, 'module') else None,
            function=record.funcName if hasattr(record, 'funcName') else None,
            line_number=record.lineno if hasattr(record, 'lineno') else None,
            extra_data=getattr(record, 'extra_data', None)
        )
        
        return log_entry.to_json()


class HumanReadableFormatter(logging.Formatter):
    """
    Human-readable log formatter for development and console output.
    
    This formatter creates easy-to-read log messages with color support
    and clear formatting for development purposes.
    """
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }
    
    def __init__(self, use_colors: bool = True):
        """
        Initialize formatter.
        
        Args:
            use_colors: Whether to use ANSI colors in output
        """
        super().__init__()
        self.use_colors = use_colors and sys.stderr.isatty()
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as human-readable string.
        
        Args:
            record: Log record to format
            
        Returns:
            Formatted log message
        """
        # Format timestamp
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # Format level with color
        level = record.levelname
        if self.use_colors and level in self.COLORS:
            level = f"{self.COLORS[level]}{level}{self.COLORS['RESET']}"
        
        # Format logger name (truncate if too long)
        logger_name = record.name
        if len(logger_name) > 20:
            logger_name = f"...{logger_name[-17:]}"
        
        # Format message
        message = record.getMessage()
        
        # Add extra data if present
        extra_info = ""
        if hasattr(record, 'extra_data') and record.extra_data:
            extra_info = f" | {json.dumps(record.extra_data, ensure_ascii=False)}"
        
        # Format location info for debug level
        location_info = ""
        if record.levelno <= logging.DEBUG:
            location_info = f" [{record.filename}:{record.lineno}]"
        
        return f"{timestamp} | {level:8} | {logger_name:20} | {message}{extra_info}{location_info}"


class LoggingService:
    """
    Central logging service for MCP Base64 Server.
    
    This service provides structured logging with multiple handlers,
    formatters, and configuration options. It supports both development
    and production logging scenarios.
    """
    
    def __init__(self):
        """Initialize logging service."""
        self._loggers: Dict[str, logging.Logger] = {}
        self._handlers: List[logging.Handler] = []
        self._configured = False
        self._log_level = logging.INFO
        self._use_structured_format = False
        self._log_file_path: Optional[Path] = None
        
    def configure(
        self,
        level: str = "INFO",
        use_structured_format: bool = False,
        log_file_path: Optional[str] = None,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5,
        use_colors: bool = True
    ) -> None:
        """
        Configure logging service.
        
        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            use_structured_format: Whether to use structured JSON format
            log_file_path: Path to log file (optional)
            max_file_size: Maximum log file size in bytes
            backup_count: Number of backup log files to keep
            use_colors: Whether to use colors in console output
        """
        if self._configured:
            self.get_logger(__name__).warning("Logging service already configured")
            return
        
        # Set configuration
        self._log_level = getattr(logging, level.upper())
        self._use_structured_format = use_structured_format
        self._log_file_path = Path(log_file_path) if log_file_path else None
        
        # Clear existing handlers
        self._clear_handlers()
        
        # Configure console handler
        self._configure_console_handler(use_colors)
        
        # Configure file handler if specified
        if self._log_file_path:
            self._configure_file_handler(max_file_size, backup_count)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(self._log_level)
        
        # Add handlers to root logger
        for handler in self._handlers:
            root_logger.addHandler(handler)
        
        self._configured = True
        
        # Log configuration info
        logger = self.get_logger(__name__)
        logger.info("Logging service configured", extra={
            'extra_data': {
                'level': level,
                'structured_format': use_structured_format,
                'log_file': str(self._log_file_path) if self._log_file_path else None,
                'handlers_count': len(self._handlers)
            }
        })
    
    def _configure_console_handler(self, use_colors: bool) -> None:
        """
        Configure console logging handler.
        
        Args:
            use_colors: Whether to use colors in console output
        """
        # Create console handler (use stderr to avoid conflicts with stdio transport)
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(self._log_level)
        
        # Set formatter
        if self._use_structured_format:
            formatter = StructuredFormatter()
        else:
            formatter = HumanReadableFormatter(use_colors=use_colors)
        
        console_handler.setFormatter(formatter)
        self._handlers.append(console_handler)
    
    def _configure_file_handler(self, max_file_size: int, backup_count: int) -> None:
        """
        Configure file logging handler with rotation.
        
        Args:
            max_file_size: Maximum file size in bytes
            backup_count: Number of backup files to keep
        """
        # Ensure log directory exists
        self._log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Create rotating file handler
        file_handler = logging.handlers.RotatingFileHandler(
            filename=str(self._log_file_path),
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(self._log_level)
        
        # Always use structured format for file logs
        formatter = StructuredFormatter()
        file_handler.setFormatter(formatter)
        
        self._handlers.append(file_handler)
    
    def _clear_handlers(self) -> None:
        """Clear all existing handlers."""
        for handler in self._handlers:
            handler.close()
        self._handlers.clear()
    
    def get_logger(self, name: str) -> logging.Logger:
        """
        Get or create logger with specified name.
        
        Args:
            name: Logger name
            
        Returns:
            Logger instance
        """
        if name not in self._loggers:
            logger = logging.getLogger(name)
            self._loggers[name] = logger
        
        return self._loggers[name]
    
    def log_operation(
        self,
        logger_name: str,
        operation: str,
        level: str = "INFO",
        duration_ms: Optional[float] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log an operation with structured data.
        
        Args:
            logger_name: Name of the logger
            operation: Operation name/description
            level: Log level
            duration_ms: Operation duration in milliseconds
            success: Whether operation was successful
            error_message: Error message if operation failed
            extra_data: Additional data to include
        """
        logger = self.get_logger(logger_name)
        
        # Prepare log data
        log_data = {
            'operation': operation,
            'success': success,
            'duration_ms': duration_ms
        }
        
        if error_message:
            log_data['error'] = error_message
        
        if extra_data:
            log_data.update(extra_data)
        
        # Format message
        status = "SUCCESS" if success else "FAILED"
        message = f"Operation {operation} {status}"
        if duration_ms is not None:
            message += f" ({duration_ms:.2f}ms)"
        
        # Log with appropriate level
        log_level = getattr(logging, level.upper())
        logger.log(log_level, message, extra={'extra_data': log_data})
    
    def log_request(
        self,
        logger_name: str,
        method: str,
        path: Optional[str] = None,
        status_code: Optional[int] = None,
        duration_ms: Optional[float] = None,
        client_info: Optional[Dict[str, Any]] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log a request with structured data.
        
        Args:
            logger_name: Name of the logger
            method: Request method (e.g., 'POST', 'call_tool')
            path: Request path (for HTTP requests)
            status_code: Response status code
            duration_ms: Request duration in milliseconds
            client_info: Client information
            extra_data: Additional data to include
        """
        logger = self.get_logger(logger_name)
        
        # Prepare log data
        log_data = {
            'request_method': method,
            'request_path': path,
            'status_code': status_code,
            'duration_ms': duration_ms,
            'client_info': client_info
        }
        
        if extra_data:
            log_data.update(extra_data)
        
        # Format message
        message = f"Request {method}"
        if path:
            message += f" {path}"
        if status_code:
            message += f" -> {status_code}"
        if duration_ms is not None:
            message += f" ({duration_ms:.2f}ms)"
        
        # Determine log level based on status
        if status_code and status_code >= 400:
            level = logging.WARNING if status_code < 500 else logging.ERROR
        else:
            level = logging.INFO
        
        logger.log(level, message, extra={'extra_data': log_data})
    
    def log_error(
        self,
        logger_name: str,
        error: Exception,
        context: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log an error with structured data.
        
        Args:
            logger_name: Name of the logger
            error: Exception object
            context: Additional context about the error
            extra_data: Additional data to include
        """
        logger = self.get_logger(logger_name)
        
        # Prepare log data
        log_data = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context
        }
        
        if extra_data:
            log_data.update(extra_data)
        
        # Format message
        message = f"Error: {type(error).__name__}: {str(error)}"
        if context:
            message = f"{context} - {message}"
        
        logger.error(message, extra={'extra_data': log_data}, exc_info=True)
    
    def get_log_stats(self) -> Dict[str, Any]:
        """
        Get logging statistics.
        
        Returns:
            Dictionary with logging statistics
        """
        return {
            'configured': self._configured,
            'log_level': logging.getLevelName(self._log_level),
            'structured_format': self._use_structured_format,
            'log_file': str(self._log_file_path) if self._log_file_path else None,
            'handlers_count': len(self._handlers),
            'loggers_count': len(self._loggers)
        }
    
    def shutdown(self) -> None:
        """Shutdown logging service and close all handlers."""
        logger = self.get_logger(__name__)
        logger.info("Shutting down logging service")
        
        self._clear_handlers()
        self._loggers.clear()
        self._configured = False


# Global logging service instance
_logging_service: Optional[LoggingService] = None


def get_logging_service() -> LoggingService:
    """
    Get global logging service instance.
    
    Returns:
        LoggingService instance
    """
    global _logging_service
    if _logging_service is None:
        _logging_service = LoggingService()
    return _logging_service


def configure_logging(
    level: str = "INFO",
    use_structured_format: bool = False,
    log_file_path: Optional[str] = None,
    max_file_size: int = 10 * 1024 * 1024,
    backup_count: int = 5,
    use_colors: bool = True
) -> None:
    """
    Configure global logging service.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_structured_format: Whether to use structured JSON format
        log_file_path: Path to log file (optional)
        max_file_size: Maximum log file size in bytes
        backup_count: Number of backup log files to keep
        use_colors: Whether to use colors in console output
    """
    service = get_logging_service()
    service.configure(
        level=level,
        use_structured_format=use_structured_format,
        log_file_path=log_file_path,
        max_file_size=max_file_size,
        backup_count=backup_count,
        use_colors=use_colors
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get logger with specified name.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    service = get_logging_service()
    return service.get_logger(name)


def log_operation(
    logger_name: str,
    operation: str,
    level: str = "INFO",
    duration_ms: Optional[float] = None,
    success: bool = True,
    error_message: Optional[str] = None,
    extra_data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log an operation with structured data.
    
    Args:
        logger_name: Name of the logger
        operation: Operation name/description
        level: Log level
        duration_ms: Operation duration in milliseconds
        success: Whether operation was successful
        error_message: Error message if operation failed
        extra_data: Additional data to include
    """
    service = get_logging_service()
    service.log_operation(
        logger_name=logger_name,
        operation=operation,
        level=level,
        duration_ms=duration_ms,
        success=success,
        error_message=error_message,
        extra_data=extra_data
    )


def log_request(
    logger_name: str,
    method: str,
    path: Optional[str] = None,
    status_code: Optional[int] = None,
    duration_ms: Optional[float] = None,
    client_info: Optional[Dict[str, Any]] = None,
    extra_data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log a request with structured data.
    
    Args:
        logger_name: Name of the logger
        method: Request method (e.g., 'POST', 'call_tool')
        path: Request path (for HTTP requests)
        status_code: Response status code
        duration_ms: Request duration in milliseconds
        client_info: Client information
        extra_data: Additional data to include
    """
    service = get_logging_service()
    service.log_request(
        logger_name=logger_name,
        method=method,
        path=path,
        status_code=status_code,
        duration_ms=duration_ms,
        client_info=client_info,
        extra_data=extra_data
    )


def log_error(
    logger_name: str,
    error: Exception,
    context: Optional[str] = None,
    extra_data: Optional[Dict[str, Any]] = None
) -> None:
    """
    Log an error with structured data.
    
    Args:
        logger_name: Name of the logger
        error: Exception object
        context: Additional context about the error
        extra_data: Additional data to include
    """
    service = get_logging_service()
    service.log_error(
        logger_name=logger_name,
        error=error,
        context=context,
        extra_data=extra_data
    )