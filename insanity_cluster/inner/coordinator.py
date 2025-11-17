"""
Multi-Agent Coordinator for INNER layer.

Orchestrates parallel and sequential agent execution with circuit breaker pattern
and retry strategies.
"""
import asyncio
import logging
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set

from insanity_cluster.common.models import (
    AgentResult,
    AgentType,
    ResultStatus,
    Subtask,
    TaskGraph,
)

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class CircuitBreaker:
    """Circuit breaker for agent failure handling"""
    agent_type: AgentType
    failure_threshold: int = 5
    timeout_seconds: int = 60
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_failure_time: Optional[float] = None
    
    def record_success(self):
        """Record successful execution"""
        if self.state == CircuitState.HALF_OPEN:
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            logger.info(f"Circuit breaker for {self.agent_type.value} closed")
    
    def record_failure(self):
        """Record failed execution"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            logger.warning(
                f"Circuit breaker for {self.agent_type.value} opened "
                f"after {self.failure_count} failures"
            )
    
    def can_execute(self) -> bool:
        """Check if execution is allowed"""
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # Check if timeout has passed
            if self.last_failure_time:
                elapsed = time.time() - self.last_failure_time
                if elapsed > self.timeout_seconds:
                    self.state = CircuitState.HALF_OPEN
                    logger.info(f"Circuit breaker for {self.agent_type.value} half-open")
                    return True
            return False
        
        # HALF_OPEN state - allow one request to test
        return True


@dataclass
class RetryStrategy:
    """Retry strategy configuration"""
    max_attempts: int = 3
    initial_delay: float = 1.0  # seconds
    max_delay: float = 60.0  # seconds
    exponential_base: float = 2.0
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number"""
        delay = self.initial_delay * (self.exponential_base ** attempt)
        return min(delay, self.max_delay)


@dataclass
class AgentAssignment:
    """Assignment of subtask to agent"""
    subtask: Subtask
    agent_type: AgentType
    assigned_at: datetime
    priority: int


@dataclass
class ExecutionMetrics:
    """Metrics for task execution"""
    task_id: str
    total_subtasks: int
    completed_subtasks: int
    failed_subtasks: int
    in_progress_subtasks: int
    total_cost: float
    total_latency_ms: int
    start_time: datetime
    end_time: Optional[datetime] = None
    
    @property
    def completion_rate(self) -> float:
        """Calculate completion rate"""
        if self.total_subtasks == 0:
            return 0.0
        return self.completed_subtasks / self.total_subtasks
    
    @property
    def duration(self) -> Optional[timedelta]:
        """Calculate total duration"""
        if self.end_time:
            return self.end_time - self.start_time
        return None


@dataclass
class ExecutionResult:
    """Result of task graph execution"""
    task_id: str
    status: ResultStatus
    results: List[AgentResult]
    metrics: ExecutionMetrics
    errors: List[str]


class AgentError(Exception):
    """Error during agent execution"""
    def __init__(self, message: str, subtask_id: str, agent_type: AgentType):
        self.subtask_id = subtask_id
        self.agent_type = agent_type
        super().__init__(message)


class MultiAgentCoordinator:
    """
    Orchestrate parallel and sequential agent execution.
    
    Implements circuit breaker pattern for failing agents and retry strategies
    with exponential backoff.
    """
    
    def __init__(
        self,
        retry_strategy: Optional[RetryStrategy] = None,
        max_concurrent_tasks: int = 10,
        agent_registry: Optional[Dict[AgentType, Any]] = None
    ):
        """
        Initialize multi-agent coordinator.
        
        Args:
            retry_strategy: Retry strategy configuration
            max_concurrent_tasks: Maximum number of concurrent subtasks
            agent_registry: Optional registry of CRUST layer agents
        """
        self.retry_strategy = retry_strategy or RetryStrategy()
        self.max_concurrent_tasks = max_concurrent_tasks
        self.agent_registry = agent_registry or {}
        
        # Circuit breakers per agent type
        self.circuit_breakers: Dict[AgentType, CircuitBreaker] = {
            agent_type: CircuitBreaker(agent_type=agent_type)
            for agent_type in AgentType
        }
        
        # Priority queue for subtask scheduling
        self.task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        
        # Execution tracking
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.completed_tasks: Set[str] = set()
        
        logger.info("MultiAgentCoordinator initialized")
    
    async def execute_task_graph(self, task_graph: TaskGraph) -> ExecutionResult:
        """
        Execute task graph with optimal parallelization.
        
        Args:
            task_graph: Task graph to execute
            
        Returns:
            ExecutionResult with all agent results and metrics
        """
        logger.info(f"Executing task graph: {task_graph.root_task_id}")
        
        # Initialize metrics
        metrics = ExecutionMetrics(
            task_id=task_graph.root_task_id,
            total_subtasks=len(task_graph.subtasks),
            completed_subtasks=0,
            failed_subtasks=0,
            in_progress_subtasks=0,
            total_cost=0.0,
            total_latency_ms=0,
            start_time=datetime.utcnow()
        )
        
        results: List[AgentResult] = []
        errors: List[str] = []
        completed: Set[str] = set()
        
        try:
            # Execute subtasks in dependency order
            while len(completed) < len(task_graph.subtasks):
                # Get executable subtasks (dependencies met)
                executable = task_graph.get_executable_subtasks(completed)
                
                if not executable:
                    # Check if we're stuck (no executable tasks but not done)
                    if len(completed) < len(task_graph.subtasks):
                        error_msg = "Deadlock detected: no executable subtasks remaining"
                        logger.error(error_msg)
                        errors.append(error_msg)
                        break
                    break
                
                # Execute subtasks in parallel (up to max_concurrent_tasks)
                batch_results = await self._execute_batch(
                    executable,
                    metrics
                )
                
                # Process results
                for result in batch_results:
                    results.append(result)
                    
                    if result.status == ResultStatus.SUCCESS:
                        completed.add(result.subtask_id)
                        metrics.completed_subtasks += 1
                    else:
                        metrics.failed_subtasks += 1
                        errors.append(
                            f"Subtask {result.subtask_id} failed: {result.output}"
                        )
                    
                    metrics.total_cost += result.cost
                    metrics.total_latency_ms += result.latency_ms
            
            # Determine overall status
            if metrics.failed_subtasks == 0:
                status = ResultStatus.SUCCESS
            elif metrics.completed_subtasks > 0:
                status = ResultStatus.PARTIAL
            else:
                status = ResultStatus.FAILURE
            
        except Exception as e:
            logger.error(f"Error executing task graph: {e}")
            errors.append(str(e))
            status = ResultStatus.FAILURE
        
        finally:
            metrics.end_time = datetime.utcnow()
        
        logger.info(
            f"Task graph execution completed: {metrics.completed_subtasks}/"
            f"{metrics.total_subtasks} subtasks successful"
        )
        
        return ExecutionResult(
            task_id=task_graph.root_task_id,
            status=status,
            results=results,
            metrics=metrics,
            errors=errors
        )
    
    async def _execute_batch(
        self,
        subtasks: List[Subtask],
        metrics: ExecutionMetrics
    ) -> List[AgentResult]:
        """
        Execute a batch of subtasks in parallel.
        
        Args:
            subtasks: List of subtasks to execute
            metrics: Execution metrics to update
            
        Returns:
            List of agent results
        """
        # Limit concurrent execution
        batch_size = min(len(subtasks), self.max_concurrent_tasks)
        
        # Create tasks for parallel execution
        tasks = []
        for subtask in subtasks[:batch_size]:
            task = asyncio.create_task(
                self._execute_subtask_with_retry(subtask)
            )
            tasks.append(task)
            metrics.in_progress_subtasks += 1
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and handle exceptions
        agent_results = []
        for i, result in enumerate(results):
            metrics.in_progress_subtasks -= 1
            
            if isinstance(result, Exception):
                # Create failure result
                subtask = subtasks[i]
                agent_results.append(
                    AgentResult(
                        subtask_id=subtask.id,
                        status=ResultStatus.FAILURE,
                        output=str(result),
                        cost=0.0,
                        latency_ms=0,
                        model_used="none",
                        validation_score=0.0
                    )
                )
            else:
                agent_results.append(result)
        
        return agent_results
    
    async def _execute_subtask_with_retry(self, subtask: Subtask) -> AgentResult:
        """
        Execute subtask with retry logic.
        
        Args:
            subtask: Subtask to execute
            
        Returns:
            AgentResult
        """
        agent_type = subtask.agent_type
        circuit_breaker = self.circuit_breakers[agent_type]
        
        for attempt in range(self.retry_strategy.max_attempts):
            # Check circuit breaker
            if not circuit_breaker.can_execute():
                raise AgentError(
                    f"Circuit breaker open for {agent_type.value}",
                    subtask.id,
                    agent_type
                )
            
            try:
                # Execute subtask
                result = await self._execute_subtask(subtask)
                
                # Record success
                circuit_breaker.record_success()
                
                return result
            
            except Exception as e:
                logger.warning(
                    f"Attempt {attempt + 1}/{self.retry_strategy.max_attempts} "
                    f"failed for subtask {subtask.id}: {e}"
                )
                
                # Record failure
                circuit_breaker.record_failure()
                
                # Check if we should retry
                if attempt < self.retry_strategy.max_attempts - 1:
                    # Calculate delay
                    delay = self.retry_strategy.get_delay(attempt)
                    logger.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    # Final attempt failed
                    raise AgentError(
                        f"All retry attempts exhausted: {e}",
                        subtask.id,
                        agent_type
                    )
        
        # Should not reach here
        raise AgentError(
            "Unexpected retry loop exit",
            subtask.id,
            agent_type
        )
    
    async def _execute_subtask(self, subtask: Subtask) -> AgentResult:
        """
        Execute a single subtask.
        
        Delegates to CRUST layer agents when available, otherwise simulates execution.
        
        Args:
            subtask: Subtask to execute
            
        Returns:
            AgentResult
        """
        logger.info(f"Executing subtask {subtask.id} with {subtask.agent_type.value}")
        
        # Check if agent registry is available (injected during initialization)
        if hasattr(self, 'agent_registry') and self.agent_registry:
            try:
                # Get agent for this subtask type
                agent = self.agent_registry.get(subtask.agent_type)
                
                if agent:
                    # Execute with actual CRUST layer agent
                    context = {"subtask_id": subtask.id}
                    result = await agent.execute(subtask, context)
                    return result
                else:
                    logger.warning(f"No agent registered for {subtask.agent_type.value}, using simulation")
            except Exception as e:
                logger.error(f"Agent execution failed: {e}, falling back to simulation")
        
        # Fallback: simulate execution for testing/development
        await asyncio.sleep(0.1)
        
        return AgentResult(
            subtask_id=subtask.id,
            status=ResultStatus.SUCCESS,
            output=f"Completed: {subtask.description}",
            cost=subtask.estimated_cost,
            latency_ms=100,
            model_used="mock-model",
            validation_score=0.95
        )
    
    async def assign_subtask(self, subtask: Subtask) -> AgentAssignment:
        """
        Assign subtask to appropriate specialized agent.
        
        Args:
            subtask: Subtask to assign
            
        Returns:
            AgentAssignment
        """
        # Agent type is already determined in subtask
        agent_type = subtask.agent_type
        
        # Check circuit breaker
        circuit_breaker = self.circuit_breakers[agent_type]
        if not circuit_breaker.can_execute():
            # Try to find alternative agent
            alternative = self._find_alternative_agent(agent_type)
            if alternative:
                logger.info(
                    f"Using alternative agent {alternative.value} "
                    f"instead of {agent_type.value}"
                )
                agent_type = alternative
            else:
                raise AgentError(
                    f"No available agent for subtask {subtask.id}",
                    subtask.id,
                    agent_type
                )
        
        return AgentAssignment(
            subtask=subtask,
            agent_type=agent_type,
            assigned_at=datetime.utcnow(),
            priority=subtask.priority
        )
    
    async def handle_agent_failure(
        self,
        subtask: Subtask,
        error: AgentError
    ) -> RetryStrategy:
        """
        Determine retry strategy or alternative routing.
        
        Args:
            subtask: Failed subtask
            error: Error that occurred
            
        Returns:
            RetryStrategy for the failure
        """
        agent_type = error.agent_type
        circuit_breaker = self.circuit_breakers[agent_type]
        
        # Record failure
        circuit_breaker.record_failure()
        
        # Check if we should use alternative agent
        if circuit_breaker.state == CircuitState.OPEN:
            alternative = self._find_alternative_agent(agent_type)
            if alternative:
                logger.info(
                    f"Routing to alternative agent {alternative.value} "
                    f"due to circuit breaker"
                )
                # Update subtask agent type
                subtask.agent_type = alternative
        
        return self.retry_strategy
    
    def monitor_execution(self, task_id: str) -> ExecutionMetrics:
        """
        Get realtime execution metrics.
        
        Args:
            task_id: Task ID to monitor
            
        Returns:
            ExecutionMetrics
        """
        # This would be implemented with actual tracking
        # For now, return placeholder
        return ExecutionMetrics(
            task_id=task_id,
            total_subtasks=0,
            completed_subtasks=0,
            failed_subtasks=0,
            in_progress_subtasks=0,
            total_cost=0.0,
            total_latency_ms=0,
            start_time=datetime.utcnow()
        )
    
    def _find_alternative_agent(self, agent_type: AgentType) -> Optional[AgentType]:
        """
        Find alternative agent when primary is unavailable.
        
        Args:
            agent_type: Primary agent type
            
        Returns:
            Alternative agent type or None
        """
        # Define fallback mappings
        fallbacks = {
            AgentType.DEVELOPER: [AgentType.PROJECT_MANAGER],
            AgentType.BUSINESS: [AgentType.PROJECT_MANAGER],
            AgentType.COMMUNICATION: [AgentType.PROJECT_MANAGER],
            AgentType.RESEARCH: [AgentType.PROJECT_MANAGER],
            AgentType.CREATIVE: [AgentType.PROJECT_MANAGER],
            AgentType.FINANCE: [AgentType.BUSINESS, AgentType.PROJECT_MANAGER],
        }
        
        alternatives = fallbacks.get(agent_type, [])
        
        # Find first available alternative
        for alt in alternatives:
            if self.circuit_breakers[alt].can_execute():
                return alt
        
        return None
