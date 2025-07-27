"""
Configuration manager for MCP Base64 Server.

This module provides the main configuration management functionality,
including loading from files, environment variables, and validation.
"""

import os
import yaml
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from .config_models import Config
from .config_validator import ConfigValidator, ConfigValidationError


logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Configuration manager for loading and managing server configuration.
    
    This class handles loading configuration from YAML files, environment
    variables, and provides validation and default configuration management.
    """
    
    DEFAULT_CONFIG_FILE = "config.yaml"
    ENV_PREFIX = "MCP_BASE64_"
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Path to configuration file (optional)
        """
        self.config_file = config_file or self.DEFAULT_CONFIG_FILE
        self._config: Optional[Config] = None
    
    def load_config(self, validate: bool = True) -> Config:
        """
        Load configuration from file and environment variables.
        
        Args:
            validate: Whether to validate the configuration
            
        Returns:
            Loaded and validated configuration
            
        Raises:
            ConfigValidationError: If validation fails
            FileNotFoundError: If config file is not found
            yaml.YAMLError: If YAML parsing fails
        """
        logger.info(f"Loading configuration from {self.config_file}")
        
        # Start with default configuration
        config = Config.get_default()
        
        # Load from file if it exists
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    file_data = yaml.safe_load(f)
                    if file_data:
                        config = Config.from_dict(file_data)
                        logger.info("Configuration loaded from file successfully")
            except yaml.YAMLError as e:
                logger.error(f"Failed to parse YAML configuration: {e}")
                raise
            except Exception as e:
                logger.error(f"Failed to load configuration file: {e}")
                raise
        else:
            logger.warning(f"Configuration file {self.config_file} not found, using defaults")
        
        # Override with environment variables
        config = self._apply_env_overrides(config)
        
        # Validate configuration
        if validate:
            try:
                ConfigValidator.validate(config)
                logger.info("Configuration validation passed")
            except ConfigValidationError as e:
                logger.error(f"Configuration validation failed: {e}")
                for error in e.errors:
                    logger.error(f"  - {error}")
                raise
        
        self._config = config
        return config
    
    def get_config(self) -> Config:
        """
        Get current configuration.
        
        Returns:
            Current configuration object
            
        Raises:
            RuntimeError: If configuration has not been loaded
        """
        if self._config is None:
            raise RuntimeError("Configuration has not been loaded. Call load_config() first.")
        return self._config
    
    def save_config(self, config: Config, file_path: Optional[str] = None) -> None:
        """
        Save configuration to file.
        
        Args:
            config: Configuration object to save
            file_path: Path to save configuration (optional, uses current config file)
        """
        save_path = file_path or self.config_file
        
        try:
            # Validate before saving
            ConfigValidator.validate(config)
            
            # Convert to dictionary and save
            config_dict = config.to_dict()
            
            # Ensure directory exists
            os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else '.', exist_ok=True)
            
            with open(save_path, 'w', encoding='utf-8') as f:
                yaml.dump(config_dict, f, default_flow_style=False, indent=2)
            
            logger.info(f"Configuration saved to {save_path}")
            
        except Exception as e:
            logger.error(f"Failed to save configuration: {e}")
            raise
    
    def _apply_env_overrides(self, config: Config) -> Config:
        """
        Apply environment variable overrides to configuration.
        
        Args:
            config: Base configuration to override
            
        Returns:
            Configuration with environment overrides applied
        """
        logger.debug("Applying environment variable overrides")
        
        # Server configuration
        if env_val := os.getenv(f"{self.ENV_PREFIX}SERVER_NAME"):
            config.server.name = env_val
            logger.debug(f"Override server.name = {env_val}")
        
        if env_val := os.getenv(f"{self.ENV_PREFIX}SERVER_VERSION"):
            config.server.version = env_val
            logger.debug(f"Override server.version = {env_val}")
        
        # Transport configuration
        if env_val := os.getenv(f"{self.ENV_PREFIX}TRANSPORT_TYPE"):
            config.transport.type = env_val
            logger.debug(f"Override transport.type = {env_val}")
        
        if env_val := os.getenv(f"{self.ENV_PREFIX}TRANSPORT_HTTP_HOST"):
            config.transport.http.host = env_val
            logger.debug(f"Override transport.http.host = {env_val}")
        
        if env_val := os.getenv(f"{self.ENV_PREFIX}TRANSPORT_HTTP_PORT"):
            try:
                config.transport.http.port = int(env_val)
                logger.debug(f"Override transport.http.port = {env_val}")
            except ValueError:
                logger.warning(f"Invalid port value in environment: {env_val}")
        
        # HTTP server configuration
        if env_val := os.getenv(f"{self.ENV_PREFIX}HTTP_SERVER_ENABLED"):
            config.http_server.enabled = env_val.lower() in ('true', '1', 'yes', 'on')
            logger.debug(f"Override http_server.enabled = {config.http_server.enabled}")
        
        if env_val := os.getenv(f"{self.ENV_PREFIX}HTTP_SERVER_HOST"):
            config.http_server.host = env_val
            logger.debug(f"Override http_server.host = {env_val}")
        
        if env_val := os.getenv(f"{self.ENV_PREFIX}HTTP_SERVER_PORT"):
            try:
                config.http_server.port = int(env_val)
                logger.debug(f"Override http_server.port = {env_val}")
            except ValueError:
                logger.warning(f"Invalid port value in environment: {env_val}")
        
        # Logging configuration
        if env_val := os.getenv(f"{self.ENV_PREFIX}LOG_LEVEL"):
            config.logging.level = env_val.upper()
            logger.debug(f"Override logging.level = {env_val}")
        
        if env_val := os.getenv(f"{self.ENV_PREFIX}LOG_STRUCTURED"):
            config.logging.use_structured_format = env_val.lower() in ('true', '1', 'yes', 'on')
            logger.debug(f"Override logging.use_structured_format = {config.logging.use_structured_format}")
        
        if env_val := os.getenv(f"{self.ENV_PREFIX}LOG_FILE"):
            config.logging.log_file_path = env_val
            logger.debug(f"Override logging.log_file_path = {env_val}")
        
        if env_val := os.getenv(f"{self.ENV_PREFIX}LOG_COLORS"):
            config.logging.use_colors = env_val.lower() in ('true', '1', 'yes', 'on')
            logger.debug(f"Override logging.use_colors = {config.logging.use_colors}")
        
        # Debug configuration
        if env_val := os.getenv(f"{self.ENV_PREFIX}DEBUG_ENABLED"):
            config.debug.enabled = env_val.lower() in ('true', '1', 'yes', 'on')
            logger.debug(f"Override debug.enabled = {config.debug.enabled}")
        
        if env_val := os.getenv(f"{self.ENV_PREFIX}DEBUG_INSPECTOR_PORT"):
            try:
                config.debug.inspector_port = int(env_val)
                logger.debug(f"Override debug.inspector_port = {env_val}")
            except ValueError:
                logger.warning(f"Invalid port value in environment: {env_val}")
        
        return config
    
    @classmethod
    def create_default_config_file(cls, file_path: str = None) -> None:
        """
        Create a default configuration file.
        
        Args:
            file_path: Path where to create the config file
        """
        file_path = file_path or cls.DEFAULT_CONFIG_FILE
        
        if os.path.exists(file_path):
            logger.warning(f"Configuration file {file_path} already exists")
            return
        
        default_config = Config.get_default()
        manager = cls(file_path)
        manager.save_config(default_config, file_path)
        logger.info(f"Default configuration file created at {file_path}")
    
    def reload_config(self) -> Config:
        """
        Reload configuration from file.
        
        Returns:
            Reloaded configuration
        """
        logger.info("Reloading configuration")
        return self.load_config()
    
    def get_config_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current configuration for logging/debugging.
        
        Returns:
            Configuration summary dictionary
        """
        if self._config is None:
            return {"status": "not_loaded"}
        
        return {
            "status": "loaded",
            "server_name": self._config.server.name,
            "transport_type": self._config.transport.type,
            "http_server_enabled": self._config.http_server.enabled,
            "debug_enabled": self._config.debug.enabled,
            "config_file": self.config_file
        }