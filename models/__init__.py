"""
MCP Base64 Server - Data Models Package

This package contains all data models and structures used throughout the MCP Base64 server.
It includes MCP protocol message structures, tool definitions, and API data models.
"""

from .mcp_models import MCPRequest, MCPResponse, MCPError, ToolDefinition, ToolResult
from .api_models import EncodeRequest, DecodeRequest, APIResponse

__all__ = [
    'MCPRequest',
    'MCPResponse', 
    'MCPError',
    'ToolDefinition',
    'ToolResult',
    'EncodeRequest',
    'DecodeRequest',
    'APIResponse'
]