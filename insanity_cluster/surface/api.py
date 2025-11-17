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
from insanity_cluster.table.database import DatabaseManager, get_db
from insanity_cluster.table.redis_manager import RedisManager
from insanity_cluster.table.models import User, Task

# Import API routers
from insanity_cluster.surface.monitoring_api import router as monitoring_router
from insanity_cluster.surface.cost_api import router as cost_router
from insanity_cluster.surface.config_api import router as config_router

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

# Include API routers
app.include_router(monitoring_router)
app.include_router(cost_router)
app.include_router(config_router)


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
    
    # Initialize managers (these are also initialized in main.py but kept here for standalone use)
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
    user: User = Depends(get_current_user_api_key),
    db: Any = Depends(get_db)
):
    """
    Create a new task from natural language command.
    
    The task will be parsed, validated, and queued for execution.
    Returns immediately with task ID for status tracking.
    """
    try:
        # Get command_parser from main.py
        from insanity_cluster.surface import main
        
        if not hasattr(main, 'command_parser') or not main.command_parser:
            # If command parser not available, create a simple parsed command
            from insanity_cluster.common.models import ParsedCommand
            parsed_command = ParsedCommand(
                intent="unknown",
                parameters={},
                user_id=str(user.id),
                timestamp=datetime.utcnow()
            )
        else:
            # Parse command
            parsed_command = main.command_parser.parse(request.command, str(user.id))
        
        # Create task in database
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            user_id=user.id,
            command=request.command,
            status="pending",
            task_graph=None,  # Will be populated by INNER layer
            result=None,
            cost=0.0
        )
        db.add(task)
        db.commit()
        
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
                from insanity_cluster.surface import main
                if hasattr(main, 'redis_manager') and main.redis_manager:
                    progress_key = f"task_progress:{task_id}"
                    progress_data = main.redis_manager.get(progress_key)
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
    offset: int = 0,
    db: Any = Depends(get_db)
):
    """
    List tasks for the current user.
    
    Supports filtering by status and pagination.
    """
    try:
        query = db.query(Task).filter(Task.user_id == user.id)
        
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
        from insanity_cluster.surface import main
        if hasattr(main, 'redis_manager') and main.redis_manager:
            cancel_key = f"task_cancel:{task_id}"
            main.redis_manager.setex(cancel_key, 3600, "cancelled")
        
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
        # Get redis_manager from main.py
        from insanity_cluster.surface import main
        
        if not hasattr(main, 'redis_manager') or not main.redis_manager:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Redis service not available"
            )
        
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
        main.redis_manager.set(webhook_key, json.dumps(webhook_data))
        
        # Add to user's webhooks set
        user_webhooks_key = f"user_webhooks:{user.id}"
        main.redis_manager.sadd(user_webhooks_key, webhook_id)
        
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
        # Get redis_manager from main.py
        from insanity_cluster.surface import main
        
        if not hasattr(main, 'redis_manager') or not main.redis_manager:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Redis service not available"
            )
        
        webhook_key = f"webhook:{webhook_id}"
        webhook_data = main.redis_manager.get(webhook_key)
        
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
        
        main.redis_manager.delete(webhook_key)
        
        user_webhooks_key = f"user_webhooks:{user.id}"
        main.redis_manager.srem(user_webhooks_key, webhook_id)
        
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
        from insanity_cluster.surface import main
        
        if not hasattr(main, 'redis_manager') or not main.redis_manager:
            logger.warning("Redis not available, task not queued")
            return
        
        import json
        task_data = {
            "task_id": task_id,
            "intent": parsed_command.intent,
            "parameters": parsed_command.parameters,
            "user_id": parsed_command.user_id,
            "timestamp": parsed_command.timestamp.isoformat()
        }
        
        main.redis_manager.lpush("task_queue", json.dumps(task_data))
        
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


# Metrics endpoints (simplified versions for dashboard)
@app.get("/metrics/cost", tags=["Metrics"])
async def get_cost_metrics(
    user: User = Depends(get_current_user_api_key),
    db: Any = Depends(get_db)
):
    """Get cost metrics for the current user"""
    try:
        # Get total cost from tasks
        from sqlalchemy import func
        total_cost = db.query(func.sum(Task.cost)).filter(
            Task.user_id == user.id
        ).scalar() or 0.0
        
        # Get task count
        task_count = db.query(func.count(Task.id)).filter(
            Task.user_id == user.id
        ).scalar() or 0
        
        # Get today's cost
        from datetime import datetime, timedelta
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_cost = db.query(func.sum(Task.cost)).filter(
            Task.user_id == user.id,
            Task.created_at >= today_start
        ).scalar() or 0.0
        
        # Calculate cost per task
        cost_per_task = float(total_cost) / task_count if task_count > 0 else 0.0
        
        return {
            "total_spend": float(total_cost),
            "daily_spend": float(today_cost),
            "cost_per_task": cost_per_task,
            "task_count": task_count
        }
    except Exception as e:
        logger.error(f"Failed to get cost metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get cost metrics: {str(e)}"
        )


@app.get("/metrics/latency", tags=["Metrics"])
async def get_latency_metrics(
    user: User = Depends(get_current_user_api_key),
    db: Any = Depends(get_db)
):
    """Get latency metrics for the current user"""
    try:
        from sqlalchemy import func
        
        # Get all latencies for percentile calculation
        latencies = db.query(Task.latency_ms).filter(
            Task.user_id == user.id,
            Task.latency_ms.isnot(None)
        ).order_by(Task.latency_ms).all()
        
        latency_values = [l[0] for l in latencies if l[0] is not None]
        
        if not latency_values:
            # No data, return zeros
            return {
                "avg": 0.0,
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0
            }
        
        # Calculate percentiles
        import statistics
        avg = statistics.mean(latency_values)
        
        def percentile(data, p):
            n = len(data)
            if n == 0:
                return 0
            k = (n - 1) * p
            f = int(k)
            c = k - f
            if f + 1 < n:
                return data[f] + c * (data[f + 1] - data[f])
            return data[f]
        
        return {
            "avg": float(avg),
            "p50": float(percentile(latency_values, 0.50)),
            "p95": float(percentile(latency_values, 0.95)),
            "p99": float(percentile(latency_values, 0.99))
        }
    except Exception as e:
        logger.error(f"Failed to get latency metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get latency metrics: {str(e)}"
        )


@app.get("/metrics/system", tags=["Metrics"])
async def get_system_metrics(
    user: User = Depends(get_current_user_api_key),
    db: Any = Depends(get_db)
):
    """Get system metrics"""
    try:
        from sqlalchemy import func
        
        # Get task counts by status
        task_counts = db.query(
            Task.status,
            func.count(Task.id)
        ).filter(
            Task.user_id == user.id
        ).group_by(Task.status).all()
        
        status_counts = {status: count for status, count in task_counts}
        
        total_tasks = sum(status_counts.values())
        completed = status_counts.get("completed", 0)
        failed = status_counts.get("failed", 0)
        pending = status_counts.get("pending", 0)
        running = status_counts.get("running", 0)
        
        # Calculate rates
        completion_rate = completed / total_tasks if total_tasks > 0 else 0.0
        error_rate = failed / total_tasks if total_tasks > 0 else 0.0
        
        return {
            "task_completion_rate": completion_rate,
            "error_rate": error_rate,
            "active_tasks": running,
            "queue_depth": pending
        }
    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system metrics: {str(e)}"
        )


@app.get("/config", tags=["Configuration"])
async def get_config(
    user: User = Depends(get_current_user_api_key)
):
    """Get current configuration"""
    try:
        # Return basic config info
        return {
            "api_version": "1.0.0",
            "features": {
                "websocket": True,
                "webhooks": True,
                "metrics": True
            },
            "limits": {
                "max_tasks_per_day": 1000,
                "max_concurrent_tasks": 10
            }
        }
    except Exception as e:
        logger.error(f"Failed to get config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get config: {str(e)}"
        )


@app.put("/config", tags=["Configuration"])
async def update_config(
    config: Dict[str, Any],
    user: User = Depends(get_current_user_api_key)
):
    """Update configuration (placeholder for future implementation)"""
    try:
        # For now, just acknowledge the update
        # In the future, this would update actual configuration
        logger.info(f"Configuration update requested by user {user.id}: {config}")
        
        return {
            "message": "Configuration update received",
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Failed to update config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update config: {str(e)}"
        )


# Admin endpoints
@app.post(
    "/admin/users",
    status_code=status.HTTP_201_CREATED,
    tags=["Admin"],
    dependencies=[Depends(require_role_dependency(UserRole.ADMIN))]
)
async def create_user(
    email: str,
    role: UserRole = UserRole.USER,
    db: Any = Depends(get_db)
):
    """Create a new user (admin only)"""
    try:
        # Get auth_manager from main.py
        from insanity_cluster.surface import main
        
        if not hasattr(main, 'auth_manager') or not main.auth_manager:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service not available"
            )
        
        # Generate API key
        api_key, api_key_hash = main.auth_manager.generate_api_key()
        
        # Create user
        user = User(
            email=email,
            api_key_hash=api_key_hash,
            role=role.value
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
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
