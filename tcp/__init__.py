"""
TCP Implementation
=================

TCP-based client and server implementations for the Capsa multiplayer game.

Components:
- tcp_client: TCP client with pygame UI
- tcp_server: Basic TCP server
- server_process_tcp: Process-based TCP server
- server_threading_tcp: Threading-based TCP server (if exists)
- tcp_server_redis: Redis-enhanced TCP server

Usage:
    # Run TCP server
    python -m fp_progjar.tcp.server_process_tcp
    
    # Run TCP client
    python -m fp_progjar.tcp.tcp_client
"""

# Import TCP-specific components
try:
    from .client import CapsaClient as TCPCapsaClient
except ImportError:
    TCPCapsaClient = None

try:
    from .server_redis import CapsaGameServerProd
except ImportError:
    CapsaGameServerProd = None

# Make common imports available
from ..common import *

__all__ = [
    'TCPCapsaClient',
    'CapsaGameServerProd',
]