"""
INNER layer orchestrator entry point.

This module runs the orchestrator that consumes tasks from the task queue,
decomposes them into subtasks, and coordinates agent execution.
"""
import asyncio
import logging
import signal

from insanity_cluster.common.config import settings
from insanity_cluster.table.redis_manager import RedisManager
from insanity_cluster.table.database import DatabaseManager
from insanity_cluster.inner.pipeline import TaskExecutionPipeline

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Global shutdown flag
shutdown_event = asyncio.Event()


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_event.set()


async def process_task_queue(pipeline: TaskExecutionPipeline, redis_manager: RedisManager):
    """
    Process tasks from the main task queue.
    
    Args:
        pipeline: Task execution pipeline instance
        redis_manager: Redis manager instance
    """
    queue_name = "task_queue"
    logger.info(f"Starting orchestrator worker (queue: {queue_name})")
    
    while not shutdown_event.is_set():
        try:
            # Get task from queue (blocking with timeout)
            task_data = await redis_manager.get_from_queue(queue_name, timeout=5)
            
            if task_data is None:
                # No task available, continue loop
                continue
            
            task_id = task_data.get("task_id")
            command = task_data.get("command")
            user_id = task_data.get("user_id")
            
            logger.info(f"Processing task {task_id}: {command}")
            
            # Execute task through pipeline
            result = await pipeline.execute_task(
                task_id=task_id,
                command=command,
                user_id=user_id
            )
            
            logger.info(f"Completed task {task_id} with status {result.get('status')}")
            
        except asyncio.CancelledError:
            logger.info("Orchestrator worker cancelled")
            break
        except Exception as e:
            logger.error(f"Error processing task: {e}", exc_info=True)
            # Continue processing next task
            await asyncio.sleep(1)
    
    logger.info("Orchestrator worker stopped")


async def main():
    """Main entry point for INNER layer orchestrator"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Starting INNER layer orchestrator...")
    
    # Initialize managers
    redis_manager = RedisManager()
    db_manager = DatabaseManager()
    
    try:
        # Initialize components (minimal setup for now)
        from insanity_cluster.inner.task_decomposition import TaskDecompositionEngine
        from insanity_cluster.inner.coordinator import MultiAgentCoordinator
        from insanity_cluster.inner.context_manager import ContextManager
        
        decomposition_engine = TaskDecompositionEngine()
        coordinator = MultiAgentCoordinator()
        context_manager = ContextManager(redis_manager)
        
        # Initialize pipeline
        pipeline = TaskExecutionPipeline(
            decomposition_engine=decomposition_engine,
            coordinator=coordinator,
            context_manager=context_manager,
            database=db_manager,
            websocket_manager=None
        )
        
        logger.info("Orchestrator initialized, waiting for tasks...")
        
        # Keep the service running (waiting for tasks from queue)
        while not shutdown_event.is_set():
            await asyncio.sleep(5)
            logger.debug("Orchestrator heartbeat - waiting for tasks...")
        
        logger.info("Shutdown signal received")
        
    finally:
        # Cleanup
        redis_manager.close()
        logger.info("INNER layer orchestrator stopped")


if __name__ == "__main__":
    asyncio.run(main())
