"""
INNER Layer - Orchestration and Task Planning

The INNER layer is responsible for:
- Task decomposition: Breaking complex commands into subtasks
- Multi-agent coordination: Orchestrating parallel and sequential execution
- Context management: Maintaining conversation and task state
- Task execution pipeline: End-to-end flow from command to result
"""
from insanity_cluster.inner.task_decomposition import (
    ComplexityEstimate,
    TaskDecompositionEngine,
)
from insanity_cluster.inner.coordinator import (
    AgentAssignment,
    CircuitBreaker,
    CircuitState,
    ExecutionMetrics,
    ExecutionResult,
    MultiAgentCoordinator,
    RetryStrategy,
)
from insanity_cluster.inner.context_manager import (
    Context,
    ContextManager,
    MergedContext,
    RetentionPolicy,
)
from insanity_cluster.inner.pipeline import (
    AggregatedResult,
    TaskExecutionPipeline,
    TaskStatus,
    TaskUpdate,
)

__all__ = [
    # Task Decomposition
    "ComplexityEstimate",
    "TaskDecompositionEngine",
    # Coordinator
    "AgentAssignment",
    "CircuitBreaker",
    "CircuitState",
    "ExecutionMetrics",
    "ExecutionResult",
    "MultiAgentCoordinator",
    "RetryStrategy",
    # Context Manager
    "Context",
    "ContextManager",
    "MergedContext",
    "RetentionPolicy",
    # Pipeline
    "AggregatedResult",
    "TaskExecutionPipeline",
    "TaskStatus",
    "TaskUpdate",
]
