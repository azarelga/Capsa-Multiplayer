"""
HTTP Implementation
==================

HTTP-based client and server implementations for the Capsa multiplayer game.

Components:
- client_http: HTTP client with pygame UI and requests library
- custom_http: Custom HTTP server implementation
- server_http: Basic HTTP server wrapper
- server_threading_http: Threading-based HTTP server
- http_server: Advanced HTTP server with game API

Usage:
    # Run HTTP server
    python -m fp_progjar.http.server_threading_http
    
    # Run HTTP client
    python -m fp_progjar.http.client_http
"""

# Import HTTP-specific components
try:
    from .client import CapsaClient as HTTPCapsaClient
except ImportError:
    HTTPCapsaClient = None

try:
    from .http_protocol import HttpServer as CustomHttpServer, GameSession as HTTPGameSession
except ImportError:
    CustomHttpServer = None
    HTTPGameSession = None