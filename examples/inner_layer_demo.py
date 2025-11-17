"""
INNER Layer Demo

Demonstrates the orchestration capabilities of the INNER layer including:
- Task decomposition
- Multi-agent coordination
- Context management
- End-to-end task execution
"""
import asyncio
import logging
from datetime import datetime

from insanity_cluster.common.models import ParsedCommand
from insanity_cluster.inner import (
    TaskDecompositionEngine,
    MultiAgentCoordinator,
    ContextManager,
    TaskExecutionPipeline,
    Context,
)
from insanity_cluster.table.database import DatabaseManager
from insanity_cluster.table.redis_manager import RedisManager
from insanity_cluster.table.vector_store import VectorStore

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def demo_task_decomposition():
    """Demonstrate task decomposition"""
    print("\n" + "="*60)
    print("DEMO 1: Task Decomposition")
    print("="*60)
    
    # Create decomposition engine
    engine = TaskDecompositionEngine()
    
    # Create a sample command
    command = ParsedCommand(
        intent="code_generation",
        parameters={
            "raw_command": "Write a Python REST API for user management",
            "language": "python",
            "description": "REST API for user management with CRUD operations"
        },
        confidence=0.95,
        user_id="demo-user",
        timestamp=datetime.utcnow()
    )
    
    print(f"\nCommand: {command.parameters['raw_command']}")
    print(f"Intent: {command.intent}")
    print(f"Confidence: {command.confidence}")
    
    # Decompose the task
    task_graph = await engine.decompose(command)
    
    print(f"\nDecomposed into {len(task_graph.subtasks)} subtasks:")
    for i, subtask in enumerate(task_graph.subtasks, 1):
        print(f"\n{i}. {subtask.description}")
        print(f"   Agent: {subtask.agent_type.value}")
        print(f"   Priority: {subtask.priority}")
        print(f"   Dependencies: {len(subtask.dependencies)}")
        print(f"   Estimated cost: ${subtask.estimated_cost:.2f}")
        print(f"   Estimated duration: {subtask.estimated_duration}")
    
    # Estimate complexity
    complexity = engine.estimate_complexity(task_graph)
    
    print(f"\nComplexity Analysis:")
    print(f"  Time estimate: {complexity.time_estimate}")
    print(f"  Cost estimate: ${complexity.cost_estimate:.2f}")
    print(f"  Agent count: {complexity.agent_count}")
    print(f"  Parallel potential: {complexity.parallel_potential:.1%}")
    print(f"  Complexity score: {complexity.complexity_score:.2f}")


async def demo_multi_agent_coordination():
    """Demonstrate multi-agent coordination"""
    print("\n" + "="*60)
    print("DEMO 2: Multi-Agent Coordination")
    print("="*60)
    
    # Create coordinator
    coordinator = MultiAgentCoordinator(max_concurrent_tasks=5)
    
    # Create a simple task graph
    engine = TaskDecompositionEngine()
    command = ParsedCommand(
        intent="llc_formation",
        parameters={
            "raw_command": "Form an LLC in Delaware",
            "state": "Delaware",
            "company_name": "Demo Tech LLC"
        },
        confidence=0.98,
        user_id="demo-user",
        timestamp=datetime.utcnow()
    )
    
    task_graph = await engine.decompose(command)
    
    print(f"\nExecuting task graph with {len(task_graph.subtasks)} subtasks...")
    
    # Execute the task graph
    result = await coordinator.execute_task_graph(task_graph)
    
    print(f"\nExecution Results:")
    print(f"  Status: {result.status.value}")
    print(f"  Completed: {result.metrics.completed_subtasks}/{result.metrics.total_subtasks}")
    print(f"  Failed: {result.metrics.failed_subtasks}")
    print(f"  Total cost: ${result.metrics.total_cost:.4f}")
    print(f"  Total latency: {result.metrics.total_latency_ms}ms")
    print(f"  Duration: {result.metrics.duration}")
    
    print(f"\nAgent Results:")
    for i, agent_result in enumerate(result.results, 1):
        print(f"\n{i}. Subtask: {agent_result.subtask_id[:8]}...")
        print(f"   Status: {agent_result.status.value}")
        print(f"   Output: {agent_result.output}")
        print(f"   Model: {agent_result.model_used}")
        print(f"   Cost: ${agent_result.cost:.4f}")
        print(f"   Latency: {agent_result.latency_ms}ms")
        print(f"   Validation: {agent_result.validation_score:.2f}")


async def demo_context_management():
    """Demonstrate context management"""
    print("\n" + "="*60)
    print("DEMO 3: Context Management")
    print("="*60)
    
    # Note: This demo uses mock database/redis/vector_store
    # In production, these would be real connections
    
    print("\nContext management requires database connections.")
    print("This demo shows the API usage pattern:")
    
    print("""
    # Create context manager
    context_manager = ContextManager(database, redis_manager, vector_store)
    
    # Create a new context
    context = Context(session_id="session-123", user_id="user-456")
    
    # Add conversation messages
    context.add_message("user", "Write a Python function to calculate fibonacci")
    context.add_message("assistant", "Here's a fibonacci function...")
    context.add_task("task-789")
    
    # Store context
    await context_manager.store_context("session-123", context)
    
    # Retrieve context later
    context = await context_manager.retrieve_context("session-123")
    
    # Search for similar contexts
    similar = await context_manager.search_similar_contexts(
        "fibonacci function",
        limit=5
    )
    
    # Merge contexts from related tasks
    merged = await context_manager.merge_contexts([
        "task-1", "task-2", "task-3"
    ])
    
    # Prune old contexts
    pruned_count = await context_manager.prune_old_context()
    """)


async def demo_task_execution_pipeline():
    """Demonstrate end-to-end task execution"""
    print("\n" + "="*60)
    print("DEMO 4: Task Execution Pipeline")
    print("="*60)
    
    print("\nTask execution pipeline integrates all INNER layer components.")
    print("This demo shows the complete flow:")
    
    print("""
    # Initialize pipeline
    pipeline = TaskExecutionPipeline(
        decomposition_engine=engine,
        coordinator=coordinator,
        context_manager=context_manager,
        database=database
    )
    
    # Execute command end-to-end
    command = ParsedCommand(
        intent="research",
        parameters={"raw_command": "Research AI trends in 2025"},
        confidence=0.92,
        user_id="user-123",
        timestamp=datetime.utcnow()
    )
    
    result = await pipeline.execute_command(command, session_id="session-456")
    
    # Result contains:
    print(f"Task ID: {result.task_id}")
    print(f"Status: {result.status.value}")
    print(f"Output: {result.output}")
    print(f"Cost: ${result.total_cost:.4f}")
    print(f"Latency: {result.total_latency_ms}ms")
    print(f"Validation: {'Passed' if result.validation_passed else 'Failed'}")
    print(f"Agent results: {len(result.agent_results)}")
    
    # Check task status
    status = await pipeline.get_task_status(result.task_id)
    print(f"Current status: {status.value}")
    
    # Cancel task if needed
    cancelled = await pipeline.cancel_task(result.task_id)
    """)


async def demo_circuit_breaker():
    """Demonstrate circuit breaker pattern"""
    print("\n" + "="*60)
    print("DEMO 5: Circuit Breaker Pattern")
    print("="*60)
    
    from insanity_cluster.inner.coordinator import CircuitBreaker, CircuitState
    from insanity_cluster.common.models import AgentType
    
    # Create circuit breaker
    breaker = CircuitBreaker(
        agent_type=AgentType.DEVELOPER,
        failure_threshold=3,
        timeout_seconds=5
    )
    
    print(f"\nInitial state: {breaker.state.value}")
    print(f"Failure threshold: {breaker.failure_threshold}")
    print(f"Timeout: {breaker.timeout_seconds}s")
    
    # Simulate failures
    print("\nSimulating failures...")
    for i in range(5):
        can_execute = breaker.can_execute()
        print(f"\nAttempt {i+1}:")
        print(f"  Can execute: {can_execute}")
        print(f"  State: {breaker.state.value}")
        print(f"  Failure count: {breaker.failure_count}")
        
        if can_execute:
            breaker.record_failure()
    
    print(f"\nFinal state: {breaker.state.value}")
    print("Circuit breaker is now OPEN - rejecting requests")
    
    # Wait for timeout
    print(f"\nWaiting {breaker.timeout_seconds}s for timeout...")
    await asyncio.sleep(breaker.timeout_seconds + 1)
    
    can_execute = breaker.can_execute()
    print(f"\nAfter timeout:")
    print(f"  Can execute: {can_execute}")
    print(f"  State: {breaker.state.value}")
    print("Circuit breaker is now HALF_OPEN - testing recovery")
    
    # Simulate success
    breaker.record_success()
    print(f"\nAfter successful execution:")
    print(f"  State: {breaker.state.value}")
    print("Circuit breaker is now CLOSED - normal operation")


async def main():
    """Run all demos"""
    print("\n" + "="*60)
    print("INNER LAYER DEMONSTRATION")
    print("Orchestration and Task Planning")
    print("="*60)
    
    try:
        # Run demos
        await demo_task_decomposition()
        await demo_multi_agent_coordination()
        await demo_context_management()
        await demo_task_execution_pipeline()
        await demo_circuit_breaker()
        
        print("\n" + "="*60)
        print("DEMO COMPLETED SUCCESSFULLY")
        print("="*60)
        
    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    asyncio.run(main())
