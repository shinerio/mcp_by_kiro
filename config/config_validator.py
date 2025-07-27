"""
Configuration validation module for MCP Base64 Server.

This module provides validation functionality for configuration data,
ensuring that all configuration values are valid and consistent.
"""

from typing import List, Dict, Any
import logging
from .config_models import Config


class ConfigValidationError(Exception):
    """Exception raised when configuration validation fails."""
    
    def __init__(self, message: str, errors: List[str] = None):
        super().__init__(message)
        self.errors = errors or []


class ConfigValidator:
    """Configuration validator class."""
    
    VALID_TRANSPORT_TYPES = ["stdio", "http"]
    VALID_LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    
    @classmethod
    def validate(cls, config: Config) -> None:
        """
        Validate configuration object.
        
        Args:
            config: Configuration object to validate
            
        Raises:
            ConfigValidationError: If validation fails
        """
        errors = []
        
        # Validate server configuration
        errors.extend(cls._validate_server(config.server))
        
        # Validate transport configuration
        errors.extend(cls._validate_transport(config.transport))
        
        # Validate HTTP server configuration
        errors.extend(cls._validate_http_server(config.http_server))
        
        # Validate logging configuration
        errors.extend(cls._validate_logging(config.logging))
        
        # Validate debug configuration
        errors.extend(cls._validate_debug(config.debug))
        
        # Validate cross-section dependencies
        errors.extend(cls._validate_dependencies(config))
        
        if errors:
            raise ConfigValidationError(
                f"Configuration validation failed with {len(errors)} error(s)",
                errors
            )
    
    @classmethod
    def _validate_server(cls, server_config) -> List[str]:
        """Validate server configuration."""
        errors = []
        
        if not server_config.name or not isinstance(server_config.name, str):
            errors.append("Server name must be a non-empty string")
        
        if not server_config.version or not isinstance(server_config.version, str):
            errors.append("Server version must be a non-empty string")
        
        if not server_config.description or not isinstance(server_config.description, str):
            errors.append("Server description must be a non-empty string")
        
        return errors
    
    @classmethod
    def _validate_transport(cls, transport_config) -> List[str]:
        """Validate transport configuration."""
        errors = []
        
        if transport_config.type not in cls.VALID_TRANSPORT_TYPES:
            errors.append(f"Transport type must be one of: {cls.VALID_TRANSPORT_TYPES}")
        
        # Validate HTTP transport settings
        if transport_config.type == "http":
            if not transport_config.http.host or not isinstance(transport_config.http.host, str):
                errors.append("HTTP transport host must be a non-empty string")
            
            if not isinstance(transport_config.http.port, int) or transport_config.http.port <= 0 or transport_config.http.port > 65535:
                errors.append("HTTP transport port must be a valid port number (1-65535)")
        
        return errors
    
    @classmethod
    def _validate_http_server(cls, http_server_config) -> List[str]:
        """Validate HTTP server configuration."""
        errors = []
        
        if not isinstance(http_server_config.enabled, bool):
            errors.append("HTTP server enabled must be a boolean")
        
        if http_server_config.enabled:
            if not http_server_config.host or not isinstance(http_server_config.host, str):
                errors.append("HTTP server host must be a non-empty string")
            
            if not isinstance(http_server_config.port, int) or http_server_config.port <= 0 or http_server_config.port > 65535:
                errors.append("HTTP server port must be a valid port number (1-65535)")
        
        return errors
    
    @classmethod
    def _validate_logging(cls, logging_config) -> List[str]:
        """Validate logging configuration."""
        errors = []
        
        if logging_config.level not in cls.VALID_LOG_LEVELS:
            errors.append(f"Logging level must be one of: {cls.VALID_LOG_LEVELS}")
        
        if not logging_config.format or not isinstance(logging_config.format, str):
            errors.append("Logging format must be a non-empty string")
        
        return errors
    
    @classmethod
    def _validate_debug(cls, debug_config) -> List[str]:
        """Validate debug configuration."""
        errors = []
        
        if not isinstance(debug_config.enabled, bool):
            errors.append("Debug enabled must be a boolean")
        
        if debug_config.enabled:
            if not isinstance(debug_config.inspector_port, int) or debug_config.inspector_port <= 0 or debug_config.inspector_port > 65535:
                errors.append("Debug inspector port must be a valid port number (1-65535)")
        
        return errors
    
    @classmethod
    def _validate_dependencies(cls, config: Config) -> List[str]:
        """Validate cross-section dependencies."""
        errors = []
        
        # Check for port conflicts
        used_ports = []
        
        if config.transport.type == "http":
            used_ports.append(("MCP HTTP transport", config.transport.http.port))
        
        if config.http_server.enabled:
            used_ports.append(("HTTP server", config.http_server.port))
        
        if config.debug.enabled:
            used_ports.append(("Debug inspector", config.debug.inspector_port))
        
        # Check for duplicate ports
        port_numbers = [port for _, port in used_ports]
        if len(port_numbers) != len(set(port_numbers)):
            port_conflicts = {}
            for name, port in used_ports:
                if port_numbers.count(port) > 1:
                    if port not in port_conflicts:
                        port_conflicts[port] = []
                    port_conflicts[port].append(name)
            
            for port, services in port_conflicts.items():
                errors.append(f"Port {port} is used by multiple services: {', '.join(services)}")
        
        return errors