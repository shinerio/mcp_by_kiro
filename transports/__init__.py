"""
MCP Base64 Server - Transport Layer Package

This package contains transport layer implementations for the MCP Base64 server.
It provides abstractions for different communication methods (stdio, HTTP) and
ensures consistent message handling across transport types.
"""

from .transport_interface import Transport, TransportInterface
from .stdio_transport import StdioTransport
from .http_transport import HTTPTransport

__all__ = [
    'Transport',
    'TransportInterface', 
    'StdioTransport',
    'HTTPTransport'
]