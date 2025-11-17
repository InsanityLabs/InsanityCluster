# Agent Development Guide

## Overview

This guide explains how to create custom agents for Insanity Cluster. Agents are specialized components that handle specific types of tasks.

## Agent Architecture

All agents inherit from `BaseAgent` and implement a common interface:

```python
from abc import ABC, abstractmethod
from insanity_cluster.common.models import Subtask, Context, AgentResult, ModelStrategy

class BaseAgent(ABC):
    def __init__(self, model_router, config):
        self.model_router = model_router
        self.config = config
        self.name = self.__class__.__name__
    
    @abstractmethod
    async def execute(self, subtask: Subtask, context: Context) -> AgentResult:
        """Execute a subtask and return result"""
        pass
    
    @abstractmethod
    def select_model_strategy(self, subtask: Subtask) -> ModelStrategy:
        """Determine optimal model routing strategy"""
        pass
    
    @abstractmethod
    def validate_output(self, output: Any) -> ValidationResult:
        """Validate output quality and accuracy"""
        pass
    
    async def coordinate_with(self, other_agent: 'BaseAgent', data: Any) -> Any:
        """Coordinate with another agent for cross-domain tasks"""
        pass
```

## Creating a Custom Agent

### Step 1: Define Agent Class

Create a new file in `insanity_cluster/crust/`:

```python
# insanity_cluster/crust/custom_agent.py

from insanity_cluster.crust.base_agent import BaseAgent
from insanity_cluster.common.models import (
    Subtask, Context, AgentResult, ModelStrategy,
    ResultStatus, ValidationResult
)
from typing import Any
import logging

logger = logging.getLogger(__name__)

class CustomAgent(BaseAgent):
    """
    Custom agent for handling specific tasks.
    
    Capabilities:
    - Task type 1
    - Task type 2
    - Task type 3
    """
    
    def __init__(self, model_router, config):
        super().__init__(model_router, config)
        self.capabilities = ["task_type_1", "task_type_2", "task_type_3"]
    
    async def execute(self, subtask: Subtask, context: Context) -> AgentResult:
        """
        Execute a subtask.
        
        Args:
            subtask: The subtask to execute
            context: Conversation and task context
        
        Returns:
            AgentResult with status, output, cost, and metrics
        """
        logger.info(f"CustomAgent executing subtask: {subtask.id}")
        
        try:
            # 1. Select model strategy
            strategy = self.select_model_strategy(subtask)
            
            # 2. Prepare prompt
            prompt = self._prepare_prompt(subtask, context)
            
            # 3. Call model via router
            response = await self.model_router.route_and_generate(
                prompt=prompt,
                strategy=strategy
            )
            
            # 4. Process response
            output = self._process_response(response.content)
            
            # 5. Validate output
            validation = self.validate_output(output)
            
            if not validation.is_valid:
                logger.warning(f"Output validation failed: {validation.errors}")
                return AgentResult(
                    subtask_id=subtask.id,
                    status=ResultStatus.FAILURE,
                    output=None,
                    cost=response.cost,
                    latency_ms=response.latency_ms,
                    model_used=response.model,
                    validation_score=validation.score,
                    error=f"Validation failed: {validation.errors}"
                )
            
            # 6. Return result
            return AgentResult(
                subtask_id=subtask.id,
                status=ResultStatus.SUCCESS,
                output=output,
                cost=response.cost,
                latency_ms=response.latency_ms,
                model_used=response.model,
                validation_score=validation.score
            )
        
        except Exception as e:
            logger.error(f"CustomAgent execution failed: {e}", exc_info=True)
            return AgentResult(
                subtask_id=subtask.id,
                status=ResultStatus.FAILURE,
                output=None,
                cost=0.0,
                latency_ms=0,
                model_used="",
                validation_score=0.0,
                error=str(e)
            )
    
    def select_model_strategy(self, subtask: Subtask) -> ModelStrategy:
        """
        Select optimal model strategy based on subtask requirements.
        
        Args:
            subtask: The subtask to analyze
        
        Returns:
            ModelStrategy with routing preferences
        """
        # Analyze subtask complexity
        complexity = self._estimate_complexity(subtask)
        
        # Select strategy based on complexity
        if complexity < 0.3:
            # Simple task - use fast, cheap model
            return ModelStrategy(
                routing_mode="SPEED_FIRST",
                max_cost=0.10,
                max_latency_ms=2000,
                required_capabilities=[],
                privacy_level="EXTERNAL_OK"
            )
        elif complexity < 0.7:
            # Moderate task - balance cost and quality
            return ModelStrategy(
                routing_mode="COST_OPTIMIZED",
                max_cost=0.50,
                max_latency_ms=5000,
                required_capabilities=[],
                privacy_level="EXTERNAL_OK"
            )
        else:
            # Complex task - prioritize quality
            return ModelStrategy(
                routing_mode="QUALITY_FIRST",
                max_cost=2.00,
                max_latency_ms=10000,
                required_capabilities=["long_context"],
                privacy_level="EXTERNAL_OK"
            )
    
    def validate_output(self, output: Any) -> ValidationResult:
        """
        Validate output quality and accuracy.
        
        Args:
            output: The output to validate
        
        Returns:
            ValidationResult with score and errors
        """
        errors = []
        score = 1.0
        
        # Check output is not None
        if output is None:
            errors.append("Output is None")
            score = 0.0
        
        # Add custom validation logic
        # Example: Check output format
        if not isinstance(output, dict):
            errors.append("Output must be a dictionary")
            score *= 0.5
        
        # Example: Check required fields
        required_fields = ["result", "metadata"]
        for field in required_fields:
            if field not in output:
                errors.append(f"Missing required field: {field}")
                score *= 0.8
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            score=score,
            errors=errors
        )
    
    def _prepare_prompt(self, subtask: Subtask, context: Context) -> str:
        """Prepare prompt for model"""
        prompt = f"""You are a specialized agent handling the following task:

Task: {subtask.description}

Context:
{context.get_relevant_context()}

Please provide a detailed response following these guidelines:
1. Be specific and actionable
2. Include all necessary details
3. Format output as JSON with 'result' and 'metadata' fields

Response:"""
        return prompt
    
    def _process_response(self, content: str) -> dict:
        """Process model response into structured output"""
        import json
        
        try:
            # Try to parse as JSON
            output = json.loads(content)
            return output
        except json.JSONDecodeError:
            # Fallback: wrap in dict
            return {
                "result": content,
                "metadata": {}
            }
    
    def _estimate_complexity(self, subtask: Subtask) -> float:
        """Estimate task complexity (0.0 - 1.0)"""
        complexity = 0.5  # Default
        
        # Adjust based on description length
        if len(subtask.description) > 500:
            complexity += 0.2
        
        # Adjust based on dependencies
        if len(subtask.dependencies) > 3:
            complexity += 0.1
        
        # Adjust based on priority
        if subtask.priority > 7:
            complexity += 0.1
        
        return min(complexity, 1.0)
```

### Step 2: Register Agent

Add your agent to the agent registry:

```python
# insanity_cluster/crust/__init__.py

from insanity_cluster.crust.custom_agent import CustomAgent

AGENT_REGISTRY = {
    "developer": DeveloperAgent,
    "communication": CommunicationAgent,
    "business": BusinessAgent,
    "research": ResearchAgent,
    "creative": CreativeAgent,
    "finance": FinanceAgent,
    "project_manager": ProjectManagerAgent,
    "custom": CustomAgent,  # Add your agent
}
```

### Step 3: Configure Agent

Add configuration for your agent:

```yaml
# config.yaml
agents:
  custom:
    primary_model: claude-sonnet-4.5
    fallback_models:
      - gpt-5-mini
      - local:mistral
    max_cost: 1.00
    fallback_to_paid: true
```

### Step 4: Test Agent

Create tests for your agent:

```python
# tests/test_custom_agent.py

import pytest
from insanity_cluster.crust.custom_agent import CustomAgent
from insanity_cluster.common.models import Subtask, Context

@pytest.mark.asyncio
async def test_custom_agent_execution(mock_model_router, mock_config):
    agent = CustomAgent(mock_model_router, mock_config)
    
    subtask = Subtask(
        id="test-001",
        description="Test task",
        agent_type="custom",
        dependencies=[],
        priority=5,
        estimated_cost=0.10
    )
    
    context = Context(session_id="test-session")
    
    result = await agent.execute(subtask, context)
    
    assert result.status == "SUCCESS"
    assert result.output is not None
    assert result.cost > 0

def test_model_strategy_selection(mock_model_router, mock_config):
    agent = CustomAgent(mock_model_router, mock_config)
    
    # Simple task
    simple_subtask = Subtask(
        id="simple",
        description="Simple task",
        agent_type="custom",
        dependencies=[],
        priority=1,
        estimated_cost=0.01
    )
    
    strategy = agent.select_model_strategy(simple_subtask)
    assert strategy.routing_mode == "SPEED_FIRST"
    assert strategy.max_cost < 0.20
    
    # Complex task
    complex_subtask = Subtask(
        id="complex",
        description="Very complex task " * 50,
        agent_type="custom",
        dependencies=["dep1", "dep2", "dep3", "dep4"],
        priority=10,
        estimated_cost=1.00
    )
    
    strategy = agent.select_model_strategy(complex_subtask)
    assert strategy.routing_mode == "QUALITY_FIRST"
    assert strategy.max_cost > 1.00

def test_output_validation(mock_model_router, mock_config):
    agent = CustomAgent(mock_model_router, mock_config)
    
    # Valid output
    valid_output = {
        "result": "Success",
        "metadata": {"key": "value"}
    }
    validation = agent.validate_output(valid_output)
    assert validation.is_valid
    assert validation.score == 1.0
    
    # Invalid output
    invalid_output = None
    validation = agent.validate_output(invalid_output)
    assert not validation.is_valid
    assert validation.score == 0.0
```

## Advanced Features

### Agent Coordination

Agents can coordinate with each other:

```python
class CustomAgent(BaseAgent):
    async def execute(self, subtask: Subtask, context: Context) -> AgentResult:
        # Check if we need help from another agent
        if self._needs_developer_help(subtask):
            # Get developer agent
            developer_agent = self.agent_registry.get("developer")
            
            # Coordinate with developer agent
            code_result = await self.coordinate_with(
                developer_agent,
                data={"task": "Generate helper function"}
            )
            
            # Use code result in our execution
            output = self._process_with_code(code_result)
        else:
            output = self._process_normally(subtask)
        
        return AgentResult(...)
```

### Streaming Responses

Support real-time streaming:

```python
class CustomAgent(BaseAgent):
    async def execute_streaming(
        self,
        subtask: Subtask,
        context: Context
    ) -> AsyncIterator[str]:
        """Execute with streaming output"""
        strategy = self.select_model_strategy(subtask)
        prompt = self._prepare_prompt(subtask, context)
        
        async for chunk in self.model_router.route_and_stream(prompt, strategy):
            # Process chunk
            processed = self._process_chunk(chunk)
            yield processed
```

### External Tool Integration

Integrate external tools and APIs:

```python
class CustomAgent(BaseAgent):
    def __init__(self, model_router, config):
        super().__init__(model_router, config)
        self.external_api = ExternalAPIClient(config.api_key)
    
    async def execute(self, subtask: Subtask, context: Context) -> AgentResult:
        # Call external API
        api_result = await self.external_api.call(subtask.parameters)
        
        # Use API result in prompt
        prompt = f"""
        Based on this API result:
        {api_result}
        
        Please {subtask.description}
        """
        
        response = await self.model_router.route_and_generate(prompt, strategy)
        
        return AgentResult(...)
```

### Caching

Implement caching for expensive operations:

```python
class CustomAgent(BaseAgent):
    def __init__(self, model_router, config):
        super().__init__(model_router, config)
        self.cache = RedisCache(config.redis_url)
    
    async def execute(self, subtask: Subtask, context: Context) -> AgentResult:
        # Check cache
        cache_key = f"agent:{self.name}:{hash(subtask.description)}"
        cached_result = await self.cache.get(cache_key)
        
        if cached_result:
            logger.info(f"Cache hit for {cache_key}")
            return AgentResult.parse_raw(cached_result)
        
        # Execute normally
        result = await self._execute_uncached(subtask, context)
        
        # Cache result
        await self.cache.set(cache_key, result.json(), ttl=3600)
        
        return result
```

## Best Practices

### 1. Error Handling

Always handle errors gracefully:

```python
async def execute(self, subtask: Subtask, context: Context) -> AgentResult:
    try:
        # Execution logic
        pass
    except ModelError as e:
        logger.error(f"Model error: {e}")
        return AgentResult(status=ResultStatus.FAILURE, error=str(e))
    except ValidationError as e:
        logger.error(f"Validation error: {e}")
        return AgentResult(status=ResultStatus.FAILURE, error=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return AgentResult(status=ResultStatus.FAILURE, error="Internal error")
```

### 2. Logging

Use structured logging:

```python
logger.info(
    "agent_execution_started",
    extra={
        "agent": self.name,
        "subtask_id": subtask.id,
        "complexity": complexity
    }
)
```

### 3. Metrics

Track agent performance:

```python
from prometheus_client import Histogram, Counter

agent_duration = Histogram('agent_duration_seconds', 'Agent execution time', ['agent'])
agent_errors = Counter('agent_errors_total', 'Agent errors', ['agent', 'error_type'])

async def execute(self, subtask: Subtask, context: Context) -> AgentResult:
    with agent_duration.labels(agent=self.name).time():
        try:
            result = await self._execute_internal(subtask, context)
            return result
        except Exception as e:
            agent_errors.labels(agent=self.name, error_type=type(e).__name__).inc()
            raise
```

### 4. Testing

Write comprehensive tests:

```python
# Unit tests
def test_prompt_preparation()
def test_response_processing()
def test_output_validation()
def test_complexity_estimation()

# Integration tests
@pytest.mark.asyncio
async def test_full_execution()
async def test_error_handling()
async def test_coordination()

# Performance tests
@pytest.mark.asyncio
async def test_concurrent_execution()
async def test_caching()
```

### 5. Documentation

Document your agent:

```python
class CustomAgent(BaseAgent):
    """
    Custom agent for handling specific tasks.
    
    Capabilities:
    - Task type 1: Description
    - Task type 2: Description
    - Task type 3: Description
    
    Model Preferences:
    - Primary: claude-sonnet-4.5 (best for reasoning)
    - Fallback: gpt-5-mini (cost-effective)
    - Local: local:mistral (for simple tasks)
    
    Validation:
    - Checks output format
    - Verifies required fields
    - Validates data types
    
    Example Usage:
        agent = CustomAgent(model_router, config)
        result = await agent.execute(subtask, context)
    """
```

## Agent Examples

### Simple Agent

```python
class SimpleAgent(BaseAgent):
    """Minimal agent implementation"""
    
    async def execute(self, subtask: Subtask, context: Context) -> AgentResult:
        prompt = f"Please {subtask.description}"
        response = await self.model_router.route_and_generate(
            prompt,
            ModelStrategy(routing_mode="SPEED_FIRST")
        )
        return AgentResult(
            subtask_id=subtask.id,
            status=ResultStatus.SUCCESS,
            output=response.content,
            cost=response.cost,
            latency_ms=response.latency_ms,
            model_used=response.model,
            validation_score=1.0
        )
    
    def select_model_strategy(self, subtask: Subtask) -> ModelStrategy:
        return ModelStrategy(routing_mode="SPEED_FIRST")
    
    def validate_output(self, output: Any) -> ValidationResult:
        return ValidationResult(is_valid=True, score=1.0, errors=[])
```

### Advanced Agent

```python
class AdvancedAgent(BaseAgent):
    """Advanced agent with all features"""
    
    def __init__(self, model_router, config):
        super().__init__(model_router, config)
        self.cache = RedisCache(config.redis_url)
        self.external_api = ExternalAPI(config.api_key)
        self.metrics = MetricsCollector()
    
    async def execute(self, subtask: Subtask, context: Context) -> AgentResult:
        # Check cache
        cached = await self._check_cache(subtask)
        if cached:
            return cached
        
        # Call external API if needed
        api_data = await self._call_external_api(subtask)
        
        # Select strategy
        strategy = self.select_model_strategy(subtask)
        
        # Prepare prompt with API data
        prompt = self._prepare_prompt(subtask, context, api_data)
        
        # Execute with retry
        response = await self._execute_with_retry(prompt, strategy)
        
        # Process and validate
        output = self._process_response(response.content)
        validation = self.validate_output(output)
        
        if not validation.is_valid:
            # Try to fix output
            output = await self._fix_output(output, validation.errors)
            validation = self.validate_output(output)
        
        # Create result
        result = AgentResult(
            subtask_id=subtask.id,
            status=ResultStatus.SUCCESS if validation.is_valid else ResultStatus.FAILURE,
            output=output,
            cost=response.cost,
            latency_ms=response.latency_ms,
            model_used=response.model,
            validation_score=validation.score
        )
        
        # Cache result
        await self._cache_result(subtask, result)
        
        # Track metrics
        self.metrics.track(result)
        
        return result
```

## Deployment

### Register in Production

1. Add agent to registry
2. Update configuration
3. Deploy new version
4. Monitor agent performance

### Monitoring

Track agent metrics:
- Execution time
- Success rate
- Cost per execution
- Validation scores

### Scaling

Agents scale automatically with worker pool:

```yaml
# docker-compose.yml
crust:
  deploy:
    replicas: 10
    resources:
      limits:
        cpus: '1'
        memory: 1G
```

## Support

For agent development help:
- Documentation: https://docs.insanitycluster.com/agents
- Discord: https://discord.gg/insanity-cluster
- Email: developers@insanitycluster.com
