"""
MCP Base64 Server - Main Entry Point

This is the main entry point for the MCP Base64 server. It handles configuration
loading, service initialization, and server startup with support for both stdio
and HTTP transport methods.
"""

import sys
import logging
import argparse
import signal
import threading
import os
from typing import Optional
from pathlib import Path

# Set UTF-8 encoding for Windows compatibility
if sys.platform.startswith('win'):
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Import core components
from config import ConfigManager, Config
from services.base64_service import Base64Service
from services.mcp_protocol_handler import MCPProtocolHandler
from services.logging_service import configure_logging, get_logger
from services.performance_monitor import start_system_monitoring, stop_system_monitoring
from transports.stdio_transport import StdioTransport
from transports.http_transport import HTTPTransport
from servers.http_server import HTTPServer


def setup_logging_from_config(config: Config) -> logging.Logger:
    """
    从配置文件配置日志系统
    
    Args:
        config: 服务器配置对象
        
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    configure_logging(
        level=config.logging.level,
        use_structured_format=config.logging.use_structured_format,
        log_file_path=config.logging.log_file_path,
        max_file_size=config.logging.max_file_size,
        backup_count=config.logging.backup_count,
        use_colors=config.logging.use_colors
    )
    return get_logger(__name__)


def parse_arguments() -> argparse.Namespace:
    """
    解析命令行参数
    
    Returns:
        argparse.Namespace: 解析后的命令行参数
    """
    parser = argparse.ArgumentParser(
        description="MCP Base64 Server - Provides base64 encoding/decoding via MCP protocol"
    )
    
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport method for MCP communication (default: stdio)"
    )
    
    parser.add_argument(
        "--http-host",
        default="localhost",
        help="HTTP transport host (default: localhost)"
    )
    
    parser.add_argument(
        "--http-port",
        type=int,
        default=3000,
        help="HTTP transport port (default: 3000)"
    )
    
    parser.add_argument(
        "--enable-http-server",
        action="store_true",
        help="Enable standalone HTTP API server"
    )
    
    parser.add_argument(
        "--http-server-port",
        type=int,
        default=8080,
        help="HTTP API server port (default: 8080)"
    )
    
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    
    parser.add_argument(
        "--config",
        type=Path,
        help="Configuration file path (YAML format)"
    )
    
    return parser.parse_args()


def load_config(config_path: Optional[Path] = None, args: argparse.Namespace = None) -> Config:
    """
    加载配置文件并应用命令行参数覆盖
    
    Args:
        config_path: 配置文件路径
        args: 命令行参数
        
    Returns:
        Config: 配置对象
    """
    # 创建配置管理器
    config_manager = ConfigManager(str(config_path) if config_path else None)
    
    # 加载配置
    config = config_manager.load_config()
    
    # 应用命令行参数覆盖
    if args:
        if args.transport:
            config.transport.type = args.transport
        if args.http_host:
            config.transport.http.host = args.http_host
        if args.http_port:
            config.transport.http.port = args.http_port
        if args.enable_http_server:
            config.http_server.enabled = True
        if args.http_server_port:
            config.http_server.port = args.http_server_port
        if args.log_level:
            config.logging.level = args.log_level
    
    return config


class MCPBase64Server:
    """
    MCP Base64服务器主类
    
    负责协调所有组件的初始化、启动和关闭。
    支持stdio和HTTP两种MCP传输方式，以及独立的HTTP API服务器。
    """
    
    def __init__(self, config: Config):
        """
        初始化服务器
        
        Args:
            config: 服务器配置
        """
        self.config = config
        self.logger = get_logger(__name__)
        
        # 核心服务组件
        self.base64_service: Optional[Base64Service] = None
        self.mcp_handler: Optional[MCPProtocolHandler] = None
        self.transport: Optional[StdioTransport | HTTPTransport] = None
        self.http_server: Optional[HTTPServer] = None
        
        # 运行状态
        self._running = False
        self._shutdown_event = threading.Event()
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """
        信号处理器，用于优雅关闭
        
        Args:
            signum: 信号编号
            frame: 当前栈帧
        """
        self.logger.info(f"Received signal {signum}, initiating shutdown...")
        self._shutdown_event.set()
    
    def initialize(self) -> None:
        """
        初始化所有服务组件
        
        按照依赖关系顺序初始化各个组件：
        1. Base64Service - 核心业务逻辑
        2. MCPProtocolHandler - MCP协议处理
        3. Transport - 传输层
        4. HTTPServer - HTTP API服务器（可选）
        """
        self.logger.info("Initializing MCP Base64 Server components...")
        
        # 1. 初始化Base64Service
        self.logger.debug("Initializing Base64Service...")
        self.base64_service = Base64Service()
        
        # 2. 初始化MCP协议处理器
        self.logger.debug("Initializing MCP Protocol Handler...")
        self.mcp_handler = MCPProtocolHandler(self.base64_service)
        
        # 3. 初始化传输层
        self.logger.debug(f"Initializing {self.config.transport.type} transport...")
        if self.config.transport.type == "stdio":
            self.transport = StdioTransport()
        elif self.config.transport.type == "http":
            self.transport = HTTPTransport(
                host=self.config.transport.http.host,
                port=self.config.transport.http.port
            )
        else:
            raise ValueError(f"Unsupported transport type: {self.config.transport.type}")
        
        # 设置传输层的请求处理器
        self.transport.set_request_handler(self.mcp_handler.handle_request)
        
        # 4. 初始化HTTP API服务器（如果启用）
        if self.config.http_server.enabled:
            self.logger.debug("Initializing HTTP API Server...")
            self.http_server = HTTPServer(
                host=self.config.http_server.host,
                port=self.config.http_server.port
            )
        
        self.logger.info("All components initialized successfully")
        
        # 启动性能监控
        start_system_monitoring(interval=5.0)
        self.logger.info("Performance monitoring started")
    
    def start(self) -> None:
        """
        启动服务器
        
        按照正确的顺序启动所有组件，并处理启动失败的情况。
        """
        if self._running:
            self.logger.warning("Server is already running")
            return
        
        try:
            self.logger.info("Starting MCP Base64 Server...")
            
            # 启动HTTP API服务器（如果启用）
            if self.http_server:
                self.logger.info(f"Starting HTTP API server on {self.config.http_server.host}:{self.config.http_server.port}")
                self.http_server.start()
            
            # 启动MCP传输层
            transport_info = self.transport.get_connection_info()
            self.logger.info(f"Starting MCP transport: {transport_info}")
            self.transport.start()
            
            self._running = True
            
            # 输出启动信息
            self._print_startup_info()
            
            self.logger.info("MCP Base64 Server started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start server: {e}")
            self.stop()
            raise
    
    def stop(self) -> None:
        """
        停止服务器
        
        优雅地关闭所有组件，确保资源正确释放。
        """
        if not self._running:
            return
        
        self.logger.info("Stopping MCP Base64 Server...")
        self._running = False
        
        # 停止传输层
        if self.transport:
            try:
                self.transport.stop()
                self.logger.debug("MCP transport stopped")
            except Exception as e:
                self.logger.error(f"Error stopping transport: {e}")
        
        # 停止HTTP API服务器
        if self.http_server:
            try:
                self.http_server.stop()
                self.logger.debug("HTTP API server stopped")
            except Exception as e:
                self.logger.error(f"Error stopping HTTP server: {e}")
        
        # 停止性能监控
        stop_system_monitoring()
        
        self.logger.info("MCP Base64 Server stopped")
    
    def run(self) -> None:
        """
        运行服务器
        
        启动服务器并等待关闭信号。这是主要的运行循环。
        """
        try:
            # 初始化组件
            self.initialize()
            
            # 启动服务器
            self.start()
            
            # 等待关闭信号
            if self.config.transport.type == "stdio":
                # stdio模式：等待关闭事件或stdin关闭
                self._wait_for_shutdown_stdio()
            else:
                # HTTP模式：等待关闭信号
                self._wait_for_shutdown_signal()
                
        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        except Exception as e:
            self.logger.error(f"Server error: {e}", exc_info=True)
            raise
        finally:
            self.stop()
    
    def _wait_for_shutdown_stdio(self) -> None:
        """
        等待stdio模式下的关闭信号
        
        在stdio模式下，服务器通过stdin接收消息，当stdin关闭时服务器应该退出。
        """
        try:
            # 等待关闭事件或传输层停止
            while self._running and not self._shutdown_event.is_set():
                if not self.transport._running:
                    self.logger.info("Transport stopped, shutting down server")
                    break
                self._shutdown_event.wait(timeout=1.0)
        except Exception as e:
            self.logger.error(f"Error in shutdown wait: {e}")
    
    def _wait_for_shutdown_signal(self) -> None:
        """
        等待HTTP模式下的关闭信号
        
        在HTTP模式下，服务器持续运行直到收到关闭信号。
        """
        try:
            self.logger.info("Server running, press Ctrl+C to stop...")
            self._shutdown_event.wait()
        except Exception as e:
            self.logger.error(f"Error in shutdown wait: {e}")
    
    def _print_startup_info(self) -> None:
        """
        打印启动信息
        
        向用户显示服务器的配置和访问信息。
        """
        try:
            print("\n" + "="*60)
            print("MCP Base64 Server Started Successfully!")
            print("="*60)
            
            # 服务器基本信息
            print(f"Server Name: {self.config.server.name}")
            print(f"Version: {self.config.server.version}")
            print(f"Transport: {self.config.transport.type}")
            
            # MCP传输信息
            if self.config.transport.type == "stdio":
                print("\nMCP Transport (stdio):")
                print("  - Listening on standard input/output")
                print("  - Ready for AI agent connections")
            else:
                print(f"\nMCP Transport (HTTP):")
                print(f"  - URL: http://{self.config.transport.http.host}:{self.config.transport.http.port}")
                print(f"  - Endpoint: http://{self.config.transport.http.host}:{self.config.transport.http.port}/mcp")
            
            # HTTP API服务器信息
            if self.config.http_server.enabled:
                print(f"\nHTTP API Server:")
                print(f"  - URL: http://{self.config.http_server.host}:{self.config.http_server.port}")
                print(f"  - Web Interface: http://{self.config.http_server.host}:{self.config.http_server.port}/")
                print(f"  - Encode API: http://{self.config.http_server.host}:{self.config.http_server.port}/encode")
                print(f"  - Decode API: http://{self.config.http_server.host}:{self.config.http_server.port}/decode")
                print(f"  - Health Check: http://{self.config.http_server.host}:{self.config.http_server.port}/health")
            
            # 可用工具
            if self.mcp_handler:
                tools = self.mcp_handler.get_available_tools()
                print(f"\nAvailable MCP Tools ({len(tools)}):")
                for tool in tools:
                    print(f"  - {tool.name}: {tool.description}")
            
            print("\n" + "="*60)
            
            if self.config.transport.type == "stdio":
                print("Ready to receive MCP messages via stdin...")
            else:
                print("Press Ctrl+C to stop the server")
            print()
            
        except UnicodeEncodeError:
            # Fallback for systems with encoding issues
            self.logger.info("Server started successfully")
            self.logger.info(f"Server Name: {self.config.server.name}")
            self.logger.info(f"Version: {self.config.server.version}")
            self.logger.info(f"Transport: {self.config.transport.type}")
            if self.config.http_server.enabled:
                self.logger.info(f"HTTP API Server: http://{self.config.http_server.host}:{self.config.http_server.port}")
        except Exception as e:
            self.logger.error(f"Error printing startup info: {e}")
            self.logger.info("Server started successfully")


def main() -> None:
    """
    主函数 - 服务器启动入口点
    
    解析命令行参数，加载配置，初始化并启动MCP服务器。
    支持stdio和HTTP两种传输方式，以及可选的HTTP API服务器。
    """
    try:
        # 解析命令行参数
        args = parse_arguments()
        
        # 加载配置
        config = load_config(args.config, args)
        
        # 设置日志（使用配置文件中的设置）
        logger = setup_logging_from_config(config)
        logger.info("Starting MCP Base64 Server...")
        logger.info("Configuration loaded successfully")
        logger.debug(f"Configuration summary: {ConfigManager().get_config_summary() if hasattr(ConfigManager(), 'get_config_summary') else 'N/A'}")
        
        # 创建并运行服务器
        server = MCPBase64Server(config)
        server.run()
        
    except KeyboardInterrupt:
        logger.info("Server shutdown requested by user")
    except Exception as e:
        logger.error(f"Server startup failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()