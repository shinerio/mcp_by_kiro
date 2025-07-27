"""
Tests for configuration management system.
"""

import os
import tempfile
import pytest
import yaml
from unittest.mock import patch

from config import ConfigManager, Config, ConfigValidator, ConfigValidationError
from config.config_models import ServerConfig, TransportConfig, HttpServerConfig


class TestConfigModels:
    """Test configuration data models."""
    
    def test_default_config(self):
        """Test default configuration creation."""
        config = Config.get_default()
        
        assert config.server.name == "mcp-base64-server"
        assert config.server.version == "1.0.0"
        assert config.transport.type == "stdio"
        assert config.transport.http.host == "localhost"
        assert config.transport.http.port == 3000
        assert config.http_server.enabled is False
        assert config.http_server.port == 8080
        assert config.logging.level == "INFO"
        assert config.debug.enabled is False
    
    def test_config_to_dict(self):
        """Test configuration to dictionary conversion."""
        config = Config.get_default()
        config_dict = config.to_dict()
        
        assert isinstance(config_dict, dict)
        assert config_dict['server']['name'] == "mcp-base64-server"
        assert config_dict['transport']['type'] == "stdio"
        assert config_dict['transport']['http']['port'] == 3000
    
    def test_config_from_dict(self):
        """Test configuration creation from dictionary."""
        data = {
            'server': {
                'name': 'test-server',
                'version': '2.0.0'
            },
            'transport': {
                'type': 'http',
                'http': {
                    'host': '0.0.0.0',
                    'port': 4000
                }
            },
            'http_server': {
                'enabled': True,
                'port': 9000
            }
        }
        
        config = Config.from_dict(data)
        
        assert config.server.name == 'test-server'
        assert config.server.version == '2.0.0'
        assert config.transport.type == 'http'
        assert config.transport.http.host == '0.0.0.0'
        assert config.transport.http.port == 4000
        assert config.http_server.enabled is True
        assert config.http_server.port == 9000


class TestConfigValidator:
    """Test configuration validator."""
    
    def test_valid_config(self):
        """Test validation of valid configuration."""
        config = Config.get_default()
        # Should not raise any exception
        ConfigValidator.validate(config)
    
    def test_invalid_transport_type(self):
        """Test validation with invalid transport type."""
        config = Config.get_default()
        config.transport.type = "invalid"
        
        with pytest.raises(ConfigValidationError) as exc_info:
            ConfigValidator.validate(config)
        
        assert any("Transport type must be one of" in error for error in exc_info.value.errors)
    
    def test_invalid_port_numbers(self):
        """Test validation with invalid port numbers."""
        config = Config.get_default()
        config.transport.type = "http"
        config.transport.http.port = 0  # Invalid port
        
        with pytest.raises(ConfigValidationError) as exc_info:
            ConfigValidator.validate(config)
        
        assert any("valid port number" in error for error in exc_info.value.errors)
    
    def test_port_conflicts(self):
        """Test validation with port conflicts."""
        config = Config.get_default()
        config.transport.type = "http"
        config.transport.http.port = 8080
        config.http_server.enabled = True
        config.http_server.port = 8080  # Same port as transport
        
        with pytest.raises(ConfigValidationError) as exc_info:
            ConfigValidator.validate(config)
        
        assert any("Port 8080 is used by multiple services" in error for error in exc_info.value.errors)
    
    def test_invalid_log_level(self):
        """Test validation with invalid log level."""
        config = Config.get_default()
        config.logging.level = "INVALID"
        
        with pytest.raises(ConfigValidationError) as exc_info:
            ConfigValidator.validate(config)
        
        assert any("Logging level must be one of" in error for error in exc_info.value.errors)


class TestConfigManager:
    """Test configuration manager."""
    
    def test_load_default_config(self):
        """Test loading default configuration when no file exists."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = os.path.join(temp_dir, "nonexistent.yaml")
            manager = ConfigManager(config_file)
            
            config = manager.load_config()
            
            assert config.server.name == "mcp-base64-server"
            assert config.transport.type == "stdio"
    
    def test_load_config_from_file(self):
        """Test loading configuration from YAML file."""
        config_data = {
            'server': {
                'name': 'test-server',
                'version': '2.0.0'
            },
            'transport': {
                'type': 'http',
                'http': {
                    'port': 4000
                }
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_file = f.name
        
        try:
            manager = ConfigManager(config_file)
            config = manager.load_config()
            
            assert config.server.name == 'test-server'
            assert config.server.version == '2.0.0'
            assert config.transport.type == 'http'
            assert config.transport.http.port == 4000
        finally:
            os.unlink(config_file)
    
    def test_env_overrides(self):
        """Test environment variable overrides."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = os.path.join(temp_dir, "test.yaml")
            manager = ConfigManager(config_file)
            
            with patch.dict(os.environ, {
                'MCP_BASE64_SERVER_NAME': 'env-server',
                'MCP_BASE64_TRANSPORT_TYPE': 'http',
                'MCP_BASE64_TRANSPORT_HTTP_PORT': '5000',
                'MCP_BASE64_HTTP_SERVER_ENABLED': 'true',
                'MCP_BASE64_LOG_LEVEL': 'DEBUG'
            }):
                config = manager.load_config()
                
                assert config.server.name == 'env-server'
                assert config.transport.type == 'http'
                assert config.transport.http.port == 5000
                assert config.http_server.enabled is True
                assert config.logging.level == 'DEBUG'
    
    def test_save_config(self):
        """Test saving configuration to file."""
        config = Config.get_default()
        config.server.name = 'saved-server'
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_file = f.name
        
        try:
            manager = ConfigManager(config_file)
            manager.save_config(config)
            
            # Load and verify
            with open(config_file, 'r') as f:
                saved_data = yaml.safe_load(f)
            
            assert saved_data['server']['name'] == 'saved-server'
        finally:
            os.unlink(config_file)
    
    def test_get_config_before_load(self):
        """Test getting configuration before loading."""
        manager = ConfigManager()
        
        with pytest.raises(RuntimeError, match="Configuration has not been loaded"):
            manager.get_config()
    
    def test_config_summary(self):
        """Test configuration summary."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = os.path.join(temp_dir, "test.yaml")
            manager = ConfigManager(config_file)
            
            # Before loading
            summary = manager.get_config_summary()
            assert summary['status'] == 'not_loaded'
            
            # After loading
            manager.load_config()
            summary = manager.get_config_summary()
            assert summary['status'] == 'loaded'
            assert summary['server_name'] == 'mcp-base64-server'
            assert summary['transport_type'] == 'stdio'
    
    def test_create_default_config_file(self):
        """Test creating default configuration file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = os.path.join(temp_dir, "default.yaml")
            
            ConfigManager.create_default_config_file(config_file)
            
            assert os.path.exists(config_file)
            
            # Verify content
            with open(config_file, 'r') as f:
                data = yaml.safe_load(f)
            
            assert data['server']['name'] == 'mcp-base64-server'
            assert data['transport']['type'] == 'stdio'


if __name__ == "__main__":
    pytest.main([__file__])