"""
FastAPI application with REST API gateway for SURFACE layer.

Implements task creation, status retrieval, and webhook registration endpoints.
"""
import logging
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, HttpUrl
import httpx

from insanity_cluster.common.config import settings
from insanity_cluster.common.models import ParsedCommand
from insanity_cluster.surface.auth import (
    AuthManager,
    get_current_user_api_key,
    UserRole,
    require_role_dependency
)
from insanity_cluster.surface.command_parser import CommandParser
from insanity_cluster.table.database import DatabaseManager
from insanity_cluster.table.redis_manager import RedisManager
from insanity_cluster.table.models import User, Task

logger = logging.getLogger(__name__)


# Request/Response Models
class TaskRequest(BaseModel):
    """Request to create a new task"""
    command: str = Field(..., description="Natural language command")
    context: Optional[Dict[str, Any]] = Field(None, description="Optional context")
    priority: int = Field(1, ge=1, le=5, description="Task priority (1-5)")


class TaskResponse(BaseModel):
    """Response for task creation"""
    task_id: str = Field(..., description="Unique task ID")
    status: str = Field(..., description="Task status")
    message: str = Field(..., description="Status message")
    estimated_duration: Optional[int] = Field(None, description="Estimated duration in seconds")


class TaskStatus(BaseModel):
    """Task status response"""
    task_id: str
    status: str
    command: str
    result: Optional[Dict[str, Any]] = None
    cost: float
    latency_ms: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    progress: Optional[Dict[str, Any]] = None


class WebhookConfig(BaseModel):
    """Webhook configuration"""
    url: HttpUrl = Field(..., description="Webhook URL")
    events: List[str] = Field(..., description="Events to subscribe to")
    secret: Optional[str] = Field(None, description="Webhook secret for verification")


class WebhookResponse(BaseModel):
    """Webhook registration response"""
    webhook_id: str
    url: str
    events: List[str]
    active: bool


class ErrorResponse(BaseModel):
    """Error response"""
    error: str
    detail: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Create FastAPI app
app = FastAPI(
    title="Insanity Cluster API",
    description="Multi-modal AI orchestration system",
    version="1.0.0",
    docs_url="/docs" if settings.enable_api_docs else None,
    redoc_url="/redoc" if settings.enable_api_docs else None
)

# Add CORS middleware
if settings.enable_cors:
    origins = settings.cors_origins.split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Global instances (will be initialized on startup)
db_manager: Optional[DatabaseManager] = None
redis_manager: Optional[RedisManager] = None
auth_manager: Optional[AuthManager] = None
command_parser: Optional[CommandParser] = None


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global db_manager, redis_manager, auth_manager, command_parser
    
    logger.info("Starting Insanity Cluster API...")
    
    # Initialize managers
    db_manager = DatabaseManager()
    redis_manager = RedisManager()
    auth_manager = AuthManager(db_manager, redis_manager)
    command_parser = CommandParser(redis_manager)
    
    logger.info("API startup complete")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("Shutting down Insanity Cluster API...")
    
    if redis_manager:
        redis_manager.close()
    
    logger.info("API shutdown complete")


# Health check endpoint
@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


# Task endpoints
@app.post(
    "/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Tasks"]
)
async def create_task(
    request: TaskRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user_api_key)
):
    """
    Create a new task from natural language command.
    
    The task will be parsed, validated, and queued for execution.
    Returns immediately with task ID for status tracking.
    """
    try:
        # Parse command
        parsed_command = command_parser.parse(request.command, str(user.id))
        
        # Create task in database
        task_id = str(uuid.uuid4())
        with db_manager.get_session() as session:
            task = Task(
                id=task_id,
                user_id=user.id,
                command=request.command,
                status="pending",
                task_graph=None,  # Will be populated by INNER layer
                result=None,
                cost=0.0
            )
            session.add(task)
            session.commit()
        
        # Queue task for processing (background)
        background_tasks.add_task(queue_task_for_processing, task_id, parsed_command)
        
        logger.info(f"Created task {task_id} for user {user.id}")
        
        return TaskResponse(
            task_id=task_id,
            status="pending",
            message="Task created and queued for processing",
            estimated_duration=None  # Will be estimated by INNER layer
        )
        
    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create task: {str(e)}"
        )


@app.get(
    "/tasks/{task_id}",
    response_model=TaskStatus,
    tags=["Tasks"]
)
async def get_task_status(
    task_id: str,
    user: User = Depends(get_current_user_api_key)
):
    """
    Get status of a specific task.
    
    Returns current status, progress, and results if completed.
    """
    try:
        with db_manager.get_session() as session:
            task = session.query(Task).filter(
                Task.id == task_id,
                Task.user_id == user.id
            ).first()
            
            if not task:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Task {task_id} not found"
                )
            
            # Get progress from Redis if task is running
            progress = None
            if task.status in ["pending", "running"]:
                progress_key = f"task_progress:{task_id}"
                progress_data = redis_manager.get(progress_key)
                if progress_data:
                    import json
                    progress = json.loads(progress_data)
            
            return TaskStatus(
                task_id=str(task.id),
                status=task.status,
                command=task.command,
                result=task.result,
                cost=float(task.cost),
                latency_ms=task.latency_ms,
                created_at=task.created_at,
                completed_at=task.completed_at,
                progress=progress
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task status: {str(e)}"
        )


@app.get(
    "/tasks",
    response_model=List[TaskStatus],
    tags=["Tasks"]
)
async def list_tasks(
    user: User = Depends(get_current_user_api_key),
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """
    List tasks for the current user.
    
    Supports filtering by status and pagination.
    """
    try:
        with db_manager.get_session() as session:
            query = session.query(Task).filter(Task.user_id == user.id)
            
            if status_filter:
                query = query.filter(Task.status == status_filter)
            
            query = query.order_by(Task.created_at.desc())
            query = query.limit(limit).offset(offset)
            
            tasks = query.all()
            
            return [
                TaskStatus(
                    task_id=str(task.id),
                    status=task.status,
                    command=task.command,
                    result=task.result,
                    cost=float(task.cost),
                    latency_ms=task.latency_ms,
                    created_at=task.created_at,
                    completed_at=task.completed_at,
                    progress=None
                )
                for task in tasks
            ]
            
    except Exception as e:
        logger.error(f"Failed to list tasks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list tasks: {str(e)}"
        )


@app.delete(
    "/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Tasks"]
)
async def cancel_task(
    task_id: str,
    user: User = Depends(get_current_user_api_key)
):
    """
    Cancel a running task.
    
    Only pending or running tasks can be cancelled.
    """
    try:
        with db_manager.get_session() as session:
            task = session.query(Task).filter(
                Task.id == task_id,
                Task.user_id == user.id
            ).first()
            
            if not task:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Task {task_id} not found"
                )
            
            if task.status not in ["pending", "running"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot cancel task with status: {task.status}"
                )
            
            task.status = "cancelled"
            task.completed_at = datetime.utcnow()
            session.commit()
        
        # Send cancellation signal to INNER layer
        cancel_key = f"task_cancel:{task_id}"
        redis_manager.setex(cancel_key, 3600, "cancelled")
        
        logger.info(f"Cancelled task {task_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel task: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel task: {str(e)}"
        )


# Webhook endpoints
@app.post(
    "/webhooks",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Webhooks"]
)
async def register_webhook(
    config: WebhookConfig,
    user: User = Depends(get_current_user_api_key)
):
    """
    Register a webhook for task completion notifications.
    
    Supported events: task.completed, task.failed, task.cancelled
    """
    try:
        webhook_id = str(uuid.uuid4())
        
        # Store webhook configuration in Redis
        webhook_key = f"webhook:{webhook_id}"
        webhook_data = {
            "id": webhook_id,
            "user_id": str(user.id),
            "url": str(config.url),
            "events": config.events,
            "secret": config.secret,
            "active": True,
            "created_at": datetime.utcnow().isoformat()
        }
        
        import json
        redis_manager.set(webhook_key, json.dumps(webhook_data))
        
        # Add to user's webhooks set
        user_webhooks_key = f"user_webhooks:{user.id}"
        redis_manager.sadd(user_webhooks_key, webhook_id)
        
        logger.info(f"Registered webhook {webhook_id} for user {user.id}")
        
        return WebhookResponse(
            webhook_id=webhook_id,
            url=str(config.url),
            events=config.events,
            active=True
        )
        
    except Exception as e:
        logger.error(f"Failed to register webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register webhook: {str(e)}"
        )


@app.delete(
    "/webhooks/{webhook_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Webhooks"]
)
async def delete_webhook(
    webhook_id: str,
    user: User = Depends(get_current_user_api_key)
):
    """Delete a webhook"""
    try:
        webhook_key = f"webhook:{webhook_id}"
        webhook_data = redis_manager.get(webhook_key)
        
        if not webhook_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Webhook {webhook_id} not found"
            )
        
        import json
        webhook = json.loads(webhook_data)
        
        if webhook["user_id"] != str(user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this webhook"
            )
        
        redis_manager.delete(webhook_key)
        
        user_webhooks_key = f"user_webhooks:{user.id}"
        redis_manager.srem(user_webhooks_key, webhook_id)
        
        logger.info(f"Deleted webhook {webhook_id}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete webhook: {str(e)}"
        )


# Helper functions
async def queue_task_for_processing(task_id: str, parsed_command: ParsedCommand):
    """
    Queue task for processing by INNER layer.
    
    This is a placeholder - actual implementation will integrate with INNER layer.
    """
    try:
        # Add task to Redis queue for INNER layer
        import json
        task_data = {
            "task_id": task_id,
            "intent": parsed_command.intent,
            "parameters": parsed_command.parameters,
            "user_id": parsed_command.user_id,
            "timestamp": parsed_command.timestamp.isoformat()
        }
        
        redis_manager.lpush("task_queue", json.dumps(task_data))
        
        logger.info(f"Queued task {task_id} for processing")
        
    except Exception as e:
        logger.error(f"Failed to queue task: {e}")


async def deliver_webhook(webhook_url: str, event: str, payload: Dict[str, Any], secret: Optional[str] = None):
    """
    Deliver webhook notification.
    
    Args:
        webhook_url: Webhook URL
        event: Event type
        payload: Event payload
        secret: Optional webhook secret for HMAC signature
    """
    try:
        headers = {
            "Content-Type": "application/json",
            "X-Event-Type": event,
            "X-Timestamp": datetime.utcnow().isoformat()
        }
        
        # Add HMAC signature if secret provided
        if secret:
            import hmac
            import hashlib
            import json
            
            payload_bytes = json.dumps(payload).encode()
            signature = hmac.new(
                secret.encode(),
                payload_bytes,
                hashlib.sha256
            ).hexdigest()
            headers["X-Signature"] = f"sha256={signature}"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                json=payload,
                headers=headers,
                timeout=10.0
            )
            response.raise_for_status()
            
        logger.info(f"Delivered webhook to {webhook_url}")
        
    except Exception as e:
        logger.error(f"Failed to deliver webhook: {e}")


# Admin endpoints
@app.post(
    "/admin/users",
    status_code=status.HTTP_201_CREATED,
    tags=["Admin"],
    dependencies=[Depends(require_role_dependency(UserRole.ADMIN))]
)
async def create_user(
    email: str,
    role: UserRole = UserRole.USER
):
    """Create a new user (admin only)"""
    try:
        # Generate API key
        api_key, api_key_hash = auth_manager.generate_api_key()
        
        # Create user
        with db_manager.get_session() as session:
            user = User(
                email=email,
                api_key_hash=api_key_hash,
                role=role.value
            )
            session.add(user)
            session.commit()
            
            user_id = str(user.id)
        
        logger.info(f"Created user {user_id}")
        
        return {
            "user_id": user_id,
            "email": email,
            "role": role.value,
            "api_key": api_key  # Only returned once
        }
        
    except Exception as e:
        logger.error(f"Failed to create user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )
