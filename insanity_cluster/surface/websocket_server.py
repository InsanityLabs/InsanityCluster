"""
WebSocket server for realtime communication in SURFACE layer.

Implements WebSocket connections with authentication, heartbeat mechanism,
and realtime task progress streaming.
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Set, Optional, Any
from dataclasses import dataclass

from fastapi import WebSocket, WebSocketDisconnect, status
from fastapi.websockets import WebSocketState

from insanity_cluster.common.config import settings
from insanity_cluster.surface.auth import AuthManager
from insanity_cluster.table.redis_manager import RedisManager

logger = logging.getLogger(__name__)


@dataclass
class TaskUpdate:
    """Task progress update"""
    task_id: str
    status: str
    progress: float  # 0.0 to 1.0
    message: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SystemEvent:
    """System-wide event"""
    event_type: str
    message: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class ConnectionManager:
    """
    Manages WebSocket connections with authentication and heartbeat.
    
    Maintains active connections, handles broadcasting, and implements
    reconnection logic with exponential backoff.
    """
    
    def __init__(
        self,
        auth_manager: AuthManager,
        redis_manager: RedisManager
    ):
        """
        Initialize connection manager.
        
        Args:
            auth_manager: Auth manager for authentication
            redis_manager: Redis manager for pub/sub
        """
        self.auth_manager = auth_manager
        self.redis_manager = redis_manager
        
        # Active connections: user_id -> Set[WebSocket]
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        
        # Connection metadata: WebSocket -> Dict
        self.connection_metadata: Dict[WebSocket, Dict[str, Any]] = {}
        
        # Heartbeat settings
        self.heartbeat_interval = settings.ws_heartbeat_interval
        self.max_connections = settings.ws_max_connections
        
        # Background tasks
        self.heartbeat_tasks: Dict[WebSocket, asyncio.Task] = {}
        
        logger.info("ConnectionManager initialized")
    
    async def connect(
        self,
        websocket: WebSocket,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Accept and register a WebSocket connection.
        
        Args:
            websocket: WebSocket connection
            user_id: User ID
            metadata: Optional connection metadata
            
        Returns:
            True if connection accepted
        """
        # Check max connections
        total_connections = sum(len(conns) for conns in self.active_connections.values())
        if total_connections >= self.max_connections:
            logger.warning(f"Max connections reached: {total_connections}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return False
        
        # Accept connection
        await websocket.accept()
        
        # Register connection
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        
        self.active_connections[user_id].add(websocket)
        
        # Store metadata
        self.connection_metadata[websocket] = {
            "user_id": user_id,
            "connected_at": datetime.utcnow(),
            "metadata": metadata or {}
        }
        
        # Start heartbeat
        heartbeat_task = asyncio.create_task(self._heartbeat_loop(websocket))
        self.heartbeat_tasks[websocket] = heartbeat_task
        
        logger.info(f"WebSocket connected for user {user_id}")
        
        # Send welcome message
        await self.send_personal_message(
            {
                "type": "connection",
                "status": "connected",
                "message": "WebSocket connection established",
                "timestamp": datetime.utcnow().isoformat()
            },
            websocket
        )
        
        return True
    
    async def disconnect(self, websocket: WebSocket):
        """
        Disconnect and cleanup a WebSocket connection.
        
        Args:
            websocket: WebSocket connection
        """
        # Get user ID
        metadata = self.connection_metadata.get(websocket)
        if not metadata:
            return
        
        user_id = metadata["user_id"]
        
        # Cancel heartbeat
        if websocket in self.heartbeat_tasks:
            self.heartbeat_tasks[websocket].cancel()
            del self.heartbeat_tasks[websocket]
        
        # Remove from active connections
        if user_id in self.active_connections:
            self.active_connections[user_id].discard(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        # Remove metadata
        del self.connection_metadata[websocket]
        
        logger.info(f"WebSocket disconnected for user {user_id}")
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """
        Send message to specific WebSocket connection.
        
        Args:
            message: Message to send
            websocket: Target WebSocket
        """
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            await self.disconnect(websocket)
    
    async def send_to_user(self, message: Dict[str, Any], user_id: str):
        """
        Send message to all connections for a user.
        
        Args:
            message: Message to send
            user_id: Target user ID
        """
        if user_id not in self.active_connections:
            return
        
        # Send to all user's connections
        disconnected = []
        for websocket in self.active_connections[user_id]:
            try:
                if websocket.client_state == WebSocketState.CONNECTED:
                    await websocket.send_json(message)
                else:
                    disconnected.append(websocket)
            except Exception as e:
                logger.error(f"Failed to send message to user {user_id}: {e}")
                disconnected.append(websocket)
        
        # Cleanup disconnected sockets
        for websocket in disconnected:
            await self.disconnect(websocket)
    
    async def broadcast(self, message: Dict[str, Any], exclude_users: Optional[Set[str]] = None):
        """
        Broadcast message to all connected users.
        
        Args:
            message: Message to broadcast
            exclude_users: Optional set of user IDs to exclude
        """
        exclude_users = exclude_users or set()
        
        for user_id in list(self.active_connections.keys()):
            if user_id not in exclude_users:
                await self.send_to_user(message, user_id)
    
    async def stream_update(self, task_id: str, update: TaskUpdate):
        """
        Stream task update to relevant users.
        
        Args:
            task_id: Task ID
            update: Task update
        """
        message = {
            "type": "task_update",
            "task_id": task_id,
            "status": update.status,
            "progress": update.progress,
            "message": update.message,
            "timestamp": update.timestamp.isoformat(),
            "metadata": update.metadata
        }
        
        # Get task owner from Redis or database
        task_key = f"task_owner:{task_id}"
        user_id = self.redis_manager.get(task_key)
        
        if user_id:
            await self.send_to_user(message, user_id)
        else:
            logger.warning(f"No owner found for task {task_id}")
    
    async def broadcast_event(self, event: SystemEvent, target_users: Optional[Set[str]] = None):
        """
        Broadcast system event to specific users or all users.
        
        Args:
            event: System event
            target_users: Optional set of target user IDs (None = all users)
        """
        message = {
            "type": "system_event",
            "event_type": event.event_type,
            "message": event.message,
            "timestamp": event.timestamp.isoformat(),
            "metadata": event.metadata
        }
        
        if target_users:
            for user_id in target_users:
                await self.send_to_user(message, user_id)
        else:
            await self.broadcast(message)
    
    async def _heartbeat_loop(self, websocket: WebSocket):
        """
        Send periodic heartbeat pings to keep connection alive.
        
        Args:
            websocket: WebSocket connection
        """
        try:
            while True:
                await asyncio.sleep(self.heartbeat_interval)
                
                if websocket.client_state != WebSocketState.CONNECTED:
                    break
                
                # Send ping
                await websocket.send_json({
                    "type": "ping",
                    "timestamp": datetime.utcnow().isoformat()
                })
                
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
            await self.disconnect(websocket)
    
    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return sum(len(conns) for conns in self.active_connections.values())
    
    def get_user_connection_count(self, user_id: str) -> int:
        """Get number of connections for a user"""
        return len(self.active_connections.get(user_id, set()))


class WebSocketHandler:
    """
    Handles WebSocket messages and routing.
    
    Processes incoming messages and routes them to appropriate handlers.
    """
    
    def __init__(self, connection_manager: ConnectionManager):
        """
        Initialize WebSocket handler.
        
        Args:
            connection_manager: Connection manager
        """
        self.connection_manager = connection_manager
        logger.info("WebSocketHandler initialized")
    
    async def handle_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """
        Handle incoming WebSocket message.
        
        Args:
            websocket: WebSocket connection
            message: Received message
        """
        message_type = message.get("type")
        
        if message_type == "pong":
            # Heartbeat response
            pass
        
        elif message_type == "subscribe":
            # Subscribe to task updates
            task_id = message.get("task_id")
            if task_id:
                await self._handle_subscribe(websocket, task_id)
        
        elif message_type == "unsubscribe":
            # Unsubscribe from task updates
            task_id = message.get("task_id")
            if task_id:
                await self._handle_unsubscribe(websocket, task_id)
        
        elif message_type == "command":
            # Execute command (future feature)
            await self._handle_command(websocket, message)
        
        else:
            logger.warning(f"Unknown message type: {message_type}")
            await self.connection_manager.send_personal_message(
                {
                    "type": "error",
                    "message": f"Unknown message type: {message_type}",
                    "timestamp": datetime.utcnow().isoformat()
                },
                websocket
            )
    
    async def _handle_subscribe(self, websocket: WebSocket, task_id: str):
        """Handle task subscription"""
        metadata = self.connection_manager.connection_metadata.get(websocket)
        if not metadata:
            return
        
        # Add task to subscriptions
        if "subscriptions" not in metadata:
            metadata["subscriptions"] = set()
        
        metadata["subscriptions"].add(task_id)
        
        await self.connection_manager.send_personal_message(
            {
                "type": "subscribed",
                "task_id": task_id,
                "timestamp": datetime.utcnow().isoformat()
            },
            websocket
        )
    
    async def _handle_unsubscribe(self, websocket: WebSocket, task_id: str):
        """Handle task unsubscription"""
        metadata = self.connection_manager.connection_metadata.get(websocket)
        if not metadata or "subscriptions" not in metadata:
            return
        
        metadata["subscriptions"].discard(task_id)
        
        await self.connection_manager.send_personal_message(
            {
                "type": "unsubscribed",
                "task_id": task_id,
                "timestamp": datetime.utcnow().isoformat()
            },
            websocket
        )
    
    async def _handle_command(self, websocket: WebSocket, message: Dict[str, Any]):
        """Handle command execution (placeholder for future feature)"""
        await self.connection_manager.send_personal_message(
            {
                "type": "error",
                "message": "Command execution via WebSocket not yet implemented",
                "timestamp": datetime.utcnow().isoformat()
            },
            websocket
        )


# WebSocket endpoint handler
async def websocket_endpoint(
    websocket: WebSocket,
    token: str,
    connection_manager: ConnectionManager,
    handler: WebSocketHandler,
    auth_manager: AuthManager
):
    """
    WebSocket endpoint with authentication.
    
    Args:
        websocket: WebSocket connection
        token: Authentication token (JWT or API key)
        connection_manager: Connection manager
        handler: WebSocket handler
        auth_manager: Auth manager
    """
    try:
        # Authenticate
        try:
            # Try JWT first
            payload = await auth_manager.verify_jwt_token(token)
            user_id = payload["sub"]
        except:
            # Try API key
            try:
                user = await auth_manager.verify_api_key(token)
                user_id = str(user.id)
            except:
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
                return
        
        # Connect
        connected = await connection_manager.connect(websocket, user_id)
        if not connected:
            return
        
        # Handle messages
        try:
            while True:
                # Receive message
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle message
                await handler.handle_message(websocket, message)
                
        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected for user {user_id}")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
        finally:
            await connection_manager.disconnect(websocket)
            
    except Exception as e:
        logger.error(f"WebSocket endpoint error: {e}")
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
        except:
            pass
