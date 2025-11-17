"""
Main entry point for SURFACE layer API server.

Integrates FastAPI application with WebSocket server and all SURFACE layer components.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, Query
import uvicorn

from insanity_cluster.common.config import settings
from insanity_cluster.surface.api import app as api_app
from insanity_cluster.surface.websocket_server import (
    ConnectionManager,
    WebSocketHandler,
    websocket_endpoint
)
from insanity_cluster.surface.auth import AuthManager
from insanity_cluster.table.database import DatabaseManager
from insanity_cluster.table.redis_manager import RedisManager

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Global instances
db_manager: DatabaseManager = None
redis_manager: RedisManager = None
auth_manager: AuthManager = None
connection_manager: ConnectionManager = None
ws_handler: WebSocketHandler = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown"""
    global db_manager, redis_manager, auth_manager, connection_manager, ws_handler
    
    # Startup
    logger.info("Starting Insanity Cluster SURFACE layer...")
    
    # Run database migrations
    try:
        logger.info("Running database migrations...")
        import subprocess
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            check=False
        )
        if result.returncode == 0:
            logger.info("Database migrations completed successfully")
        else:
            logger.warning(f"Database migrations failed: {result.stderr}")
    except Exception as e:
        logger.error(f"Failed to run migrations: {e}")
    
    # Initialize managers
    db_manager = DatabaseManager()
    redis_manager = RedisManager()
    auth_manager = AuthManager(db_manager, redis_manager)
    connection_manager = ConnectionManager(auth_manager, redis_manager)
    ws_handler = WebSocketHandler(connection_manager)
    
    # Set global instances in API app
    api_app.state.db_manager = db_manager
    api_app.state.redis_manager = redis_manager
    api_app.state.auth_manager = auth_manager
    
    logger.info("SURFACE layer started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down SURFACE layer...")
    
    if redis_manager:
        redis_manager.close()
    
    logger.info("SURFACE layer shutdown complete")


# Create main app with lifespan
app = FastAPI(
    title="Insanity Cluster SURFACE Layer",
    description="Multi-modal AI orchestration system - SURFACE layer",
    version="1.0.0",
    lifespan=lifespan
)

# Mount API routes
app.mount("/api", api_app)


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_route(
    websocket: WebSocket,
    token: str = Query(..., description="Authentication token (JWT or API key)")
):
    """
    WebSocket endpoint for realtime communication.
    
    Requires authentication via token query parameter.
    """
    await websocket_endpoint(
        websocket,
        token,
        connection_manager,
        ws_handler,
        auth_manager
    )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Insanity Cluster SURFACE Layer",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "api": "/api",
            "docs": "/api/docs",
            "websocket": "/ws?token=<your_token>",
            "health": "/api/health"
        }
    }


def main():
    """Run the SURFACE layer server"""
    logger.info(f"Starting server on {settings.api_host}:{settings.api_port}")
    
    uvicorn.run(
        "insanity_cluster.surface.main:app",
        host=settings.api_host,
        port=settings.api_port,
        workers=settings.api_workers if not settings.debug else 1,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )


if __name__ == "__main__":
    main()
