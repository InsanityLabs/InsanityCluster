"""
SURFACE Layer - User interface and interaction layer

Provides multiple interfaces for user interaction:
- REST API gateway for external integrations
- WebSocket server for realtime communication
- CLI interface for command-line usage
- Command parser for natural language processing
- Authentication and session management
"""

from insanity_cluster.surface.command_parser import CommandParser, ParseError
from insanity_cluster.surface.auth import AuthManager, UserRole
from insanity_cluster.surface.websocket_server import (
    ConnectionManager,
    WebSocketHandler,
    TaskUpdate,
    SystemEvent
)

__all__ = [
    "CommandParser",
    "ParseError",
    "AuthManager",
    "UserRole",
    "ConnectionManager",
    "WebSocketHandler",
    "TaskUpdate",
    "SystemEvent",
]
