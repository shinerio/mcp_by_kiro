"""
Configuration data models for MCP Base64 Server.

This module defines the data structures used for configuration management,
including validation and default values.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
import os


@dataclass
class ServerConfig:
    """Server basic configuration."""
    name: str = "mcp-base64-server"
    version: str = "1.0.0"
    description: str = "MCP server providing base64 encoding and decoding tools"


@dataclass
class HttpTransportConfig:
    """HTTP transport configuration."""
    host: str = "localhost"
    port: int = 3000


@dataclass
class TransportConfig:
    """Transport layer configuration."""
    type: str = "stdio"  # "stdio" or "http"
    http: HttpTransportConfig = field(default_factory=HttpTransportConfig)


@dataclass
class HttpServerConfig:
    """Standalone HTTP server configuration."""
    enabled: bool = False
    host: str = "0.0.0.0"
    port: int = 8080


@dataclass
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    use_structured_format: bool = False
    log_file_path: Optional[str] = None
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    use_colors: bool = True


@dataclass
class DebugConfig:
    """Debug and development configuration."""
    enabled: bool = False
    inspector_port: int = 9000


@dataclass
class Config:
    """Main configuration class containing all configuration sections."""
    server: ServerConfig = field(default_factory=ServerConfig)
    transport: TransportConfig = field(default_factory=TransportConfig)
    http_server: HttpServerConfig = field(default_factory=HttpServerConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    debug: DebugConfig = field(default_factory=DebugConfig)

    @classmethod
    def get_default(cls) -> 'Config':
        """Get default configuration."""
        return cls()

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        def _dataclass_to_dict(obj):
            if hasattr(obj, '__dataclass_fields__'):
                return {
                    field_name: _dataclass_to_dict(getattr(obj, field_name))
                    for field_name in obj.__dataclass_fields__
                }
            return obj

        return _dataclass_to_dict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Config':
        """Create configuration from dictionary."""
        config = cls()
        
        if 'server' in data:
            server_data = data['server']
            config.server = ServerConfig(
                name=server_data.get('name', config.server.name),
                version=server_data.get('version', config.server.version),
                description=server_data.get('description', config.server.description)
            )
        
        if 'transport' in data:
            transport_data = data['transport']
            http_data = transport_data.get('http', {})
            config.transport = TransportConfig(
                type=transport_data.get('type', config.transport.type),
                http=HttpTransportConfig(
                    host=http_data.get('host', config.transport.http.host),
                    port=http_data.get('port', config.transport.http.port)
                )
            )
        
        if 'http_server' in data:
            http_server_data = data['http_server']
            config.http_server = HttpServerConfig(
                enabled=http_server_data.get('enabled', config.http_server.enabled),
                host=http_server_data.get('host', config.http_server.host),
                port=http_server_data.get('port', config.http_server.port)
            )
        
        if 'logging' in data:
            logging_data = data['logging']
            config.logging = LoggingConfig(
                level=logging_data.get('level', config.logging.level),
                format=logging_data.get('format', config.logging.format),
                use_structured_format=logging_data.get('use_structured_format', config.logging.use_structured_format),
                log_file_path=logging_data.get('log_file_path', config.logging.log_file_path),
                max_file_size=logging_data.get('max_file_size', config.logging.max_file_size),
                backup_count=logging_data.get('backup_count', config.logging.backup_count),
                use_colors=logging_data.get('use_colors', config.logging.use_colors)
            )
        
        if 'debug' in data:
            debug_data = data['debug']
            config.debug = DebugConfig(
                enabled=debug_data.get('enabled', config.debug.enabled),
                inspector_port=debug_data.get('inspector_port', config.debug.inspector_port)
            )
        
        return config