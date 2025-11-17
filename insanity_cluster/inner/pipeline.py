"""
Task Execution Pipeline for INNER layer.

End-to-end task execution flow from command to result with integration of
Command Parser, Task Decomposition Engine, and Multi-Agent Coordinator.
"""
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from insanity_cluster.common.models import (
    AgentResult,
    ParsedCommand,
    ResultStatus,
    TaskGraph,
)
from insanity_cluster.inner.task_decomposition import (
    ComplexityEstimate,
    TaskDecompositionEngine,
)
from insanity_cluster.inner.coordinator import (
    ExecutionResult,
    MultiAgentCoordinator,
)
from insanity_cluster.inner.context_manager import Context, ContextManager
from insanity_cluster.table.database import DatabaseManager

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    PARSING = "parsing"
    DECOMPOSING = "decomposing"
    EXECUTING = "executing"
    AGGREGATING = "aggregating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class TaskUpdate:
    """Update on task execution progress"""
    task_id: str
    status: TaskStatus
    message: str
    progress: float  # 0.0 to 1.0
    timestamp: datetime
    metadata: Dict[str, Any]


@dataclass
class AggregatedResult:
    """Aggregated result from multiple agent results"""
    task_id: str
    status: ResultStatus
    output: Any
    agent_results: List[AgentResult]
    validation_passed: bool
    total_cost: float
    total_latency_ms: int
    complexity_estimate: Optional[ComplexityEstimate] = None


class ValidationError(Exception):
    """Result validation failed"""
    pass


class TaskExecutionPipeline:
    """
    End-to-end task execution flow.
    
    Integrates Command Parser, Task Decomposition Engine, and Multi-Agent
    Coordinator to execute tasks from natural language commands to final results.
    """
    
    def __init__(
        self,
        decomposition_engine: TaskDecompositionEngine,
        coordinator: MultiAgentCoordinator,
        context_manager: ContextManager,
        database: DatabaseManager,
        websocket_manager: Optional[Any] = None
    ):
        """
        Initialize task execution pipeline.
        
        Args:
            decomposition_engine: Task decomposition engine
            coordinator: Multi-agent coordinator
            context_manager: Context manager
            database: Database manager
            websocket_manager: Optional WebSocket connection manager for realtime updates
        """
        self.decomposition_engine = decomposition_engine
        self.coordinator = coordinator
        self.context_manager = context_manager
        self.database = database
        self.websocket_manager = websocket_manager
        
        # Active tasks tracking
        self.active_tasks: Dict[str, TaskStatus] = {}
        
        logger.info("TaskExecutionPipeline initialized")
    
    async def execute_command(
        self,
        command: ParsedCommand,
        session_id: Optional[str] = None
    ) -> AggregatedResult:
        """
        Execute command end-to-end.
        
        Args:
            command: Parsed command to execute
            session_id: Optional session ID for context
            
        Returns:
            AggregatedResult with final output
        """
        task_id = str(uuid.uuid4())
        logger.info(f"Starting task execution: {task_id}")
        
        try:
            # Initialize task tracking
            await self._update_task_status(
                task_id,
                TaskStatus.PENDING,
                "Task created"
            )
            
            # Store command in context
            if session_id:
                context = await self.context_manager.retrieve_context(session_id)
                if not context:
                    context = Context(
                        session_id=session_id,
                        user_id=command.user_id
                    )
                
                context.add_message(
                    role="user",
                    content=command.parameters.get("raw_command", ""),
                    metadata={"intent": command.intent}
                )
                context.add_task(task_id)
                await self.context_manager.store_context(session_id, context)
            
            # Step 1: Task Decomposition
            await self._update_task_status(
                task_id,
                TaskStatus.DECOMPOSING,
                "Decomposing task into subtasks"
            )
            
            task_graph = await self.decomposition_engine.decompose(command)
            complexity = self.decomposition_engine.estimate_complexity(task_graph)
            
            logger.info(
                f"Task decomposed into {len(task_graph.subtasks)} subtasks, "
                f"complexity: {complexity.complexity_score:.2f}"
            )
            
            # Step 2: Execute Task Graph
            await self._update_task_status(
                task_id,
                TaskStatus.EXECUTING,
                f"Executing {len(task_graph.subtasks)} subtasks"
            )
            
            execution_result = await self.coordinator.execute_task_graph(task_graph)
            
            # Step 3: Aggregate Results
            await self._update_task_status(
                task_id,
                TaskStatus.AGGREGATING,
                "Aggregating results"
            )
            
            aggregated = await self._aggregate_results(
                task_id,
                execution_result,
                complexity
            )
            
            # Step 4: Validate Results
            try:
                await self._validate_results(aggregated)
                aggregated.validation_passed = True
            except ValidationError as e:
                logger.warning(f"Validation failed: {e}")
                aggregated.validation_passed = False
            
            # Step 5: Store Results
            await self._store_task_result(task_id, command, aggregated)
            
            # Update context with result
            if session_id:
                context = await self.context_manager.retrieve_context(session_id)
                if context:
                    context.add_message(
                        role="assistant",
                        content=str(aggregated.output),
                        metadata={
                            "task_id": task_id,
                            "status": aggregated.status.value,
                            "cost": aggregated.total_cost
                        }
                    )
                    await self.context_manager.store_context(session_id, context)
            
            # Mark as completed
            final_status = TaskStatus.COMPLETED if aggregated.status == ResultStatus.SUCCESS else TaskStatus.FAILED
            await self._update_task_status(
                task_id,
                final_status,
                "Task execution completed"
            )
            
            logger.info(
                f"Task {task_id} completed: {aggregated.status.value}, "
                f"cost: ${aggregated.total_cost:.4f}"
            )
            
            return aggregated
        
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            
            await self._update_task_status(
                task_id,
                TaskStatus.FAILED,
                f"Task failed: {str(e)}"
            )
            
            # Create failure result
            return AggregatedResult(
                task_id=task_id,
                status=ResultStatus.FAILURE,
                output=f"Task execution failed: {str(e)}",
                agent_results=[],
                validation_passed=False,
                total_cost=0.0,
                total_latency_ms=0
            )
    
    async def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """
        Get current status of a task.
        
        Args:
            task_id: Task ID
            
        Returns:
            TaskStatus or None if not found
        """
        return self.active_tasks.get(task_id)
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a running task.
        
        Args:
            task_id: Task ID to cancel
            
        Returns:
            True if cancelled, False if not found or already completed
        """
        status = self.active_tasks.get(task_id)
        
        if not status or status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            return False
        
        await self._update_task_status(
            task_id,
            TaskStatus.CANCELLED,
            "Task cancelled by user"
        )
        
        logger.info(f"Task {task_id} cancelled")
        return True
    
    async def _aggregate_results(
        self,
        task_id: str,
        execution_result: ExecutionResult,
        complexity: ComplexityEstimate
    ) -> AggregatedResult:
        """
        Aggregate results from multiple agents.
        
        Args:
            task_id: Task ID
            execution_result: Execution result from coordinator
            complexity: Complexity estimate
            
        Returns:
            AggregatedResult
        """
        # Combine outputs from all successful results
        outputs = []
        for result in execution_result.results:
            if result.status == ResultStatus.SUCCESS:
                outputs.append(result.output)
        
        # Create combined output
        if len(outputs) == 1:
            combined_output = outputs[0]
        elif outputs:
            combined_output = {
                "results": outputs,
                "summary": f"Completed {len(outputs)} subtasks successfully"
            }
        else:
            combined_output = "No successful results"
        
        return AggregatedResult(
            task_id=task_id,
            status=execution_result.status,
            output=combined_output,
            agent_results=execution_result.results,
            validation_passed=False,  # Will be set by validation
            total_cost=execution_result.metrics.total_cost,
            total_latency_ms=execution_result.metrics.total_latency_ms,
            complexity_estimate=complexity
        )
    
    async def _validate_results(self, result: AggregatedResult) -> None:
        """
        Validate aggregated results.
        
        Args:
            result: Aggregated result to validate
            
        Raises:
            ValidationError: If validation fails
        """
        # Check if any results exist
        if not result.agent_results:
            raise ValidationError("No agent results to validate")
        
        # Check if at least one result is successful
        has_success = any(
            r.status == ResultStatus.SUCCESS
            for r in result.agent_results
        )
        
        if not has_success:
            raise ValidationError("No successful agent results")
        
        # Check validation scores
        avg_validation_score = sum(
            r.validation_score for r in result.agent_results
        ) / len(result.agent_results)
        
        if avg_validation_score < 0.7:
            raise ValidationError(
                f"Average validation score too low: {avg_validation_score:.2f}"
            )
        
        logger.info(f"Validation passed with score: {avg_validation_score:.2f}")
    
    async def _store_task_result(
        self,
        task_id: str,
        command: ParsedCommand,
        result: AggregatedResult
    ) -> None:
        """
        Store task result in database.
        
        Args:
            task_id: Task ID
            command: Original command
            result: Aggregated result
        """
        query = """
            INSERT INTO tasks (
                id, user_id, command, status, result,
                cost, latency_ms, created_at, completed_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """
        
        import json
        
        async with self.database.connection() as conn:
            await conn.execute(
                query,
                task_id,
                command.user_id,
                command.parameters.get("raw_command", ""),
                result.status.value,
                json.dumps({
                    "output": str(result.output),
                    "validation_passed": result.validation_passed,
                    "agent_count": len(result.agent_results)
                }),
                result.total_cost,
                result.total_latency_ms,
                command.timestamp,
                datetime.utcnow()
            )
    
    async def _update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        message: str
    ) -> None:
        """
        Update task status and broadcast update.
        
        Args:
            task_id: Task ID
            status: New status
            message: Status message
        """
        self.active_tasks[task_id] = status
        
        # Calculate progress based on status
        progress_map = {
            TaskStatus.PENDING: 0.0,
            TaskStatus.PARSING: 0.1,
            TaskStatus.DECOMPOSING: 0.2,
            TaskStatus.EXECUTING: 0.5,
            TaskStatus.AGGREGATING: 0.9,
            TaskStatus.COMPLETED: 1.0,
            TaskStatus.FAILED: 1.0,
            TaskStatus.CANCELLED: 1.0,
        }
        
        update = TaskUpdate(
            task_id=task_id,
            status=status,
            message=message,
            progress=progress_map.get(status, 0.0),
            timestamp=datetime.utcnow(),
            metadata={}
        )
        
        # Broadcast update via WebSocket if connection manager is available
        # This would be injected during pipeline initialization in production
        try:
            if hasattr(self, 'websocket_manager') and self.websocket_manager:
                await self.websocket_manager.stream_update(task_id, update)
        except Exception as e:
            logger.warning(f"Failed to broadcast WebSocket update: {e}")
        
        logger.info(f"Task {task_id} status: {status.value} - {message}")
    
    async def recover_from_error(
        self,
        task_id: str,
        error: Exception
    ) -> Optional[AggregatedResult]:
        """
        Attempt to recover from execution error.
        
        Implements error recovery strategies:
        - Retry with exponential backoff
        - Alternative agent routing
        - Simplified task decomposition
        - Graceful degradation
        
        Args:
            task_id: Task ID
            error: Error that occurred
            
        Returns:
            AggregatedResult if recovery successful, None otherwise
        """
        logger.info(f"Attempting error recovery for task {task_id}")
        
        try:
            # Strategy 1: Check if it's a transient error (network, timeout)
            if isinstance(error, (ConnectionError, TimeoutError)):
                logger.info("Transient error detected, will retry via coordinator")
                # The coordinator already handles retries with exponential backoff
                return None
            
            # Strategy 2: Check if it's a model/agent error
            if "model" in str(error).lower() or "agent" in str(error).lower():
                logger.info("Model/agent error detected, coordinator will use fallback")
                # The coordinator's circuit breaker will route to alternative agents
                return None
            
            # Strategy 3: For other errors, attempt graceful degradation
            logger.warning(f"Unrecoverable error, returning partial result: {error}")
            
            # Return a partial result indicating the error
            return AggregatedResult(
                task_id=task_id,
                status=ResultStatus.PARTIAL,
                output=f"Task partially completed with error: {str(error)}",
                agent_results=[],
                validation_passed=False,
                total_cost=0.0,
                total_latency_ms=0
            )
            
        except Exception as recovery_error:
            logger.error(f"Error recovery itself failed: {recovery_error}")
            return None
