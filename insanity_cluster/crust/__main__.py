"""
CRUST layer agent worker entry point.

This module runs agent workers that consume tasks from agent-specific queues
and execute them using the appropriate specialized agents.
"""
import asyncio
import logging
import os
import signal
from typing import Dict, Type

from insanity_cluster.common.config import settings
from insanity_cluster.table.redis_manager import RedisManager
from insanity_cluster.table.database import DatabaseManager
from insanity_cluster.crust.base_agent import BaseAgent
from insanity_cluster.crust.developer_agent import DeveloperAgent
from insanity_cluster.crust.communication_agent import CommunicationAgent
from insanity_cluster.crust.business_agent import BusinessAgent
from insanity_cluster.crust.research_agent import ResearchAgent
from insanity_cluster.crust.creative_agent import CreativeAgent
from insanity_cluster.crust.finance_agent import FinanceAgent
from insanity_cluster.crust.project_manager_agent import ProjectManagerAgent

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Agent registry
AGENT_REGISTRY: Dict[str, Type[BaseAgent]] = {
    "developer": DeveloperAgent,
    "communication": CommunicationAgent,
    "business": BusinessAgent,
    "research": ResearchAgent,
    "creative": CreativeAgent,
    "finance": FinanceAgent,
    "project_manager": ProjectManagerAgent,
}

# Global shutdown flag
shutdown_event = asyncio.Event()


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_event.set()


async def process_agent_queue(
    agent_type: str,
    agent_class: Type[BaseAgent],
    redis_manager: RedisManager,
    db_manager: DatabaseManager
):
    """
    Process tasks from an agent-specific queue.
    
    Args:
        agent_type: Type of agent (e.g., "developer", "communication")
        agent_class: Agent class to instantiate
        redis_manager: Redis manager instance
        db_manager: Database manager instance
    """
    queue_name = f"agent_queue_{agent_type}"
    logger.info(f"Starting worker for {agent_type} agent (queue: {queue_name})")
    
    # Instantiate agent
    agent = agent_class()
    
    while not shutdown_event.is_set():
        try:
            # Get task from queue (blocking with timeout)
            task_data = await redis_manager.get_from_queue(queue_name, timeout=5)
            
            if task_data is None:
                # No task available, continue loop
                continue
            
            logger.info(f"Processing task {task_data.get('subtask_id')} with {agent_type} agent")
            
            # Execute task
            result = await agent.execute(
                subtask=task_data.get("subtask"),
                context=task_data.get("context")
            )
            
            # Store result
            await redis_manager.publish_result(
                task_id=task_data.get("task_id"),
                subtask_id=task_data.get("subtask_id"),
                result=result
            )
            
            logger.info(f"Completed task {task_data.get('subtask_id')} with status {result.status}")
            
        except asyncio.CancelledError:
            logger.info(f"Worker for {agent_type} agent cancelled")
            break
        except Exception as e:
            logger.error(f"Error processing task in {agent_type} agent: {e}", exc_info=True)
            # Continue processing next task
            await asyncio.sleep(1)
    
    logger.info(f"Worker for {agent_type} agent stopped")


async def main():
    """Main entry point for CRUST layer workers"""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Starting CRUST layer agent workers...")
    
    # Get agent type from environment variable
    agent_type_env = os.getenv("AGENT_TYPE", "all").lower()
    
    # Initialize managers
    redis_manager = RedisManager()
    db_manager = DatabaseManager()
    
    try:
        # Determine which agents to run
        if agent_type_env == "all":
            agents_to_run = AGENT_REGISTRY
            logger.info(f"Running all agent types: {list(agents_to_run.keys())}")
        elif agent_type_env in AGENT_REGISTRY:
            agents_to_run = {agent_type_env: AGENT_REGISTRY[agent_type_env]}
            logger.info(f"Running single agent type: {agent_type_env}")
        else:
            logger.error(f"Invalid AGENT_TYPE: {agent_type_env}")
            return
        
        logger.info(f"CRUST layer initialized with {len(agents_to_run)} agent types")
        logger.info("Waiting for tasks from agent queues...")
        
        # Keep the service running (waiting for tasks from queues)
        while not shutdown_event.is_set():
            await asyncio.sleep(5)
            logger.debug(f"CRUST layer heartbeat - {len(agents_to_run)} agents ready")
        
        logger.info("Shutdown signal received")
        
    finally:
        # Cleanup
        redis_manager.close()
        logger.info("CRUST layer workers stopped")


if __name__ == "__main__":
    asyncio.run(main())
