"""
Base Agent abstract class for CRUST layer.

Provides common interface and functionality for all specialized agents.
"""
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from insanity_cluster.common.models import (
    AgentResult,
    AgentType,
    ModelStrategy,
    ResultStatus,
    Subtask,
)
from insanity_cluster.pan.model_router import ModelRouter
from insanity_cluster.pan.models import GenerationParams, Response

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Abstract base class for all specialized agents.
    
    Provides common functionality for:
    - Model strategy selection
    - Output validation
    - Cross-agent collaboration
    - Error reporting
    """
    
    def __init__(
        self,
        agent_type: AgentType,
        model_router: ModelRouter,
        default_model_strategy: Optional[ModelStrategy] = None
    ):
        """
        Initialize base agent.
        
        Args:
            agent_type: Type of agent
            model_router: Model router for inference
            default_model_strategy: Default model selection strategy
        """
        self.agent_type = agent_type
        self.model_router = model_router
        self.default_model_strategy = default_model_strategy
        
        logger.info(f"Initialized {agent_type.value} agent")
    
    @abstractmethod
    async def execute(self, subtask: Subtask, context: Dict[str, Any]) -> AgentResult:
        """
        Execute subtask and return result.
        
        This is the main entry point for agent execution. Each specialized agent
        must implement this method with their domain-specific logic.
        
        Args:
            subtask: Subtask to execute
            context: Execution context (conversation history, user data, etc.)
            
        Returns:
            AgentResult with execution outcome
            
        Raises:
            AgentExecutionError: If execution fails
        """
        pass
    
    @abstractmethod
    def select_model_strategy(self, subtask: Subtask) -> ModelStrategy:
        """
        Determine optimal model routing strategy for subtask.
        
        Each agent can customize model selection based on:
        - Task complexity
        - Required capabilities (streaming, vision, etc.)
        - Cost constraints
        - Latency requirements
        
        Args:
            subtask: Subtask to analyze
            
        Returns:
            ModelStrategy for this subtask
        """
        pass
    
    @abstractmethod
    def validate_output(self, output: Any, subtask: Subtask) -> float:
        """
        Validate output quality and accuracy.
        
        Each agent implements domain-specific validation:
        - Developer: Syntax checking, linting
        - Business: Legal term verification
        - Communication: Tone analysis, grammar
        - Research: Source credibility
        - etc.
        
        Args:
            output: Output to validate
            subtask: Original subtask for context
            
        Returns:
            Validation score between 0.0 and 1.0
        """
        pass
    
    async def coordinate_with(
        self,
        other_agent: 'BaseAgent',
        data: Any,
        request: str
    ) -> Any:
        """
        Coordinate with another agent for cross-domain tasks.
        
        Enables agents to collaborate when a subtask requires expertise
        from multiple domains. For example:
        - Developer agent asks Business agent to review legal implications
        - Communication agent asks Creative agent for email copy
        - Finance agent asks Business agent for compliance check
        
        Args:
            other_agent: Agent to coordinate with
            data: Data to share with other agent
            request: Description of what is needed
            
        Returns:
            Response from other agent
            
        Raises:
            CoordinationError: If coordination fails
        """
        logger.info(
            f"{self.agent_type.value} coordinating with "
            f"{other_agent.agent_type.value}: {request}"
        )
        
        try:
            # Create a coordination subtask
            coordination_subtask = Subtask(
                id=f"coord_{self.agent_type.value}_{other_agent.agent_type.value}",
                description=request,
                agent_type=other_agent.agent_type,
                dependencies=[],
                priority=1,
                estimated_cost=0.0,
                estimated_duration=0
            )
            
            # Execute coordination subtask
            context = {"coordination_data": data, "requesting_agent": self.agent_type.value}
            result = await other_agent.execute(coordination_subtask, context)
            
            if result.status != ResultStatus.SUCCESS:
                raise CoordinationError(
                    f"Coordination failed: {result.output}",
                    self.agent_type,
                    other_agent.agent_type
                )
            
            return result.output
            
        except Exception as e:
            logger.error(f"Coordination error: {e}")
            raise CoordinationError(
                str(e),
                self.agent_type,
                other_agent.agent_type
            )
    
    async def _generate_with_model(
        self,
        prompt: str,
        model_strategy: ModelStrategy,
        generation_params: Optional[GenerationParams] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Response:
        """
        Generate response using model router.
        
        Helper method for agents to interact with PAN layer.
        
        Args:
            prompt: Prompt for model
            model_strategy: Model selection strategy
            generation_params: Generation parameters
            context: Additional context
            
        Returns:
            Response from model
        """
        if generation_params is None:
            generation_params = GenerationParams()
        
        # Route to appropriate model
        endpoint = self.model_router.route_request(
            prompt=prompt,
            strategy=model_strategy,
            context=context or {}
        )
        
        # Get adapter for endpoint
        adapter = self.model_router.get_adapter(endpoint)
        
        # Generate response
        response = await adapter.generate(prompt, generation_params)
        
        logger.debug(
            f"Generated response using {response.model} "
            f"(cost: ${response.cost:.4f}, latency: {response.latency_ms}ms)"
        )
        
        return response
    
    def _report_error(
        self,
        subtask: Subtask,
        error: Exception,
        context: Dict[str, Any]
    ) -> AgentResult:
        """
        Report error to INNER layer.
        
        Creates a standardized error result that the coordinator can handle.
        
        Args:
            subtask: Failed subtask
            error: Error that occurred
            context: Execution context
            
        Returns:
            AgentResult with failure status
        """
        error_message = f"{type(error).__name__}: {str(error)}"
        
        logger.error(
            f"Agent {self.agent_type.value} failed on subtask {subtask.id}: "
            f"{error_message}"
        )
        
        return AgentResult(
            subtask_id=subtask.id,
            status=ResultStatus.FAILURE,
            output=error_message,
            cost=0.0,
            latency_ms=0,
            model_used="none",
            validation_score=0.0
        )
    
    def _create_success_result(
        self,
        subtask: Subtask,
        output: Any,
        cost: float,
        latency_ms: int,
        model_used: str,
        validation_score: float
    ) -> AgentResult:
        """
        Create success result.
        
        Helper method to create standardized success results.
        
        Args:
            subtask: Completed subtask
            output: Output from execution
            cost: Total cost in USD
            latency_ms: Total latency in milliseconds
            model_used: Model identifier
            validation_score: Validation score (0.0 to 1.0)
            
        Returns:
            AgentResult with success status
        """
        return AgentResult(
            subtask_id=subtask.id,
            status=ResultStatus.SUCCESS,
            output=output,
            cost=cost,
            latency_ms=latency_ms,
            model_used=model_used,
            validation_score=validation_score
        )


class AgentExecutionError(Exception):
    """Error during agent execution"""
    def __init__(self, message: str, agent_type: AgentType, subtask_id: str):
        self.agent_type = agent_type
        self.subtask_id = subtask_id
        super().__init__(message)


class CoordinationError(Exception):
    """Error during cross-agent coordination"""
    def __init__(
        self,
        message: str,
        requesting_agent: AgentType,
        target_agent: AgentType
    ):
        self.requesting_agent = requesting_agent
        self.target_agent = target_agent
        super().__init__(message)


class ValidationError(Exception):
    """Error during output validation"""
    def __init__(self, message: str, validation_score: float):
        self.validation_score = validation_score
        super().__init__(message)
