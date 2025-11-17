# Configuration System Integration Guide

This guide shows how to integrate the Configuration Management System with existing Insanity Cluster layers.

## Quick Start

### 1. Run Database Migration

```bash
alembic upgrade head
```

### 2. Create Default Configurations

```python
from insanity_cluster.common.config_manager import ConfigurationManager
from insanity_cluster.table.database import get_db

db = next(get_db())
config_manager = ConfigurationManager(db)
config_manager.create_default_configurations(user_id=None)  # System-wide defaults
```

### 3. Register API Routes

In `insanity_cluster/surface/main.py`:

```python
from insanity_cluster.surface.config_api import router as config_router
from insanity_cluster.surface.cost_api import router as cost_router
from insanity_cluster.surface.monitoring_api import router as monitoring_router

app.include_router(config_router)
app.include_router(cost_router)
app.include_router(monitoring_router)
```

## Integration with PAN Layer (Model Router)

### Update Model Router to Use Configuration

```python
# insanity_cluster/pan/model_router.py

from insanity_cluster.common.config_manager import ConfigurationManager, config_cache
from insanity_cluster.common.configuration import OperatingMode, RoutingStrategy
from insanity_cluster.common.cost_tracker import CostTracker, CostLimitEnforcer
from insanity_cluster.common.retry_handler import create_retry_handler

class ModelRouter:
    def __init__(self, db_session, user_id=None):
        self.db = db_session
        self.user_id = user_id
        self.config_manager = ConfigurationManager(db_session)
        self.cost_tracker = CostTracker(db_session)
        self.cost_enforcer = CostLimitEnforcer(self.cost_tracker)
        
        # Load active configuration
        self.config = config_cache.get(user_id)
        if not self.config:
            self.config = self.config_manager.get_active_configuration(user_id)
            if self.config:
                config_cache.set(self.config, user_id)
    
    async def route(self, request, agent_type=None, task_type=None):
        """Route request to optimal model based on configuration."""
        
        # Check cost limits before routing
        estimated_cost = self._estimate_request_cost(request)
        cost_check = self.cost_enforcer.check_and_enforce(
            user_id=self.user_id,
            estimated_cost=estimated_cost,
            cost_limits=self.config.cost_limits,
        )
        
        if not cost_check["allowed"]:
            raise CostLimitExceededError(cost_check["reason"])
        
        if cost_check["warning"]:
            # Log warning or notify user
            logger.warning(f"Cost warning: {cost_check['warnings']}")
        
        # Get model based on configuration
        model = self._select_model(request, agent_type, task_type)
        
        # Create retry handler with configuration
        retry_handler = create_retry_handler(
            retry_policy=self.config.default_retry_policy,
            timeout_config=self.config.default_timeout_config,
            circuit_breaker_name=f"{model}_api",
            circuit_breaker_config=self.config.default_circuit_breaker_config,
        )
        
        # Execute with retry
        try:
            result = await retry_handler.execute_with_retry(
                self._call_model,
                model=model,
                request=request,
            )
            
            # Record actual cost
            self.cost_tracker.record_task_cost(
                task_id=request.task_id,
                cost=result.cost,
                model_used=model,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Model routing failed: {e}")
            raise
    
    def _select_model(self, request, agent_type, task_type):
        """Select model based on configuration."""
        
        # Check task-type override
        if task_type and task_type in self.config.task_type_overrides:
            task_config = self.config.task_type_overrides[task_type]
            if task_config.model_override:
                return task_config.model_override
        
        # Check agent override
        if agent_type and agent_type in self.config.agent_overrides:
            agent_config = self.config.agent_overrides[agent_type]
            if agent_config.preferred_models:
                return agent_config.preferred_models[0]
        
        # Use mode-based selection
        return self._select_by_mode(request)
    
    def _select_by_mode(self, request):
        """Select model based on operating mode."""
        
        if self.config.mode == OperatingMode.LOCAL:
            return self._select_local_model(request)
        
        elif self.config.mode == OperatingMode.MIXED:
            complexity = self._estimate_complexity(request)
            if complexity < self.config.local_complexity_threshold:
                return self._select_local_model(request)
            else:
                return self._select_paid_model(request)
        
        elif self.config.mode == OperatingMode.WEB:
            return self._select_paid_model(request)
        
        # Add other modes...
        
    def _estimate_request_cost(self, request):
        """Estimate cost for a request."""
        # Estimate based on prompt length and expected output
        estimated_input_tokens = len(request.prompt.split()) * 1.3
        estimated_output_tokens = request.max_tokens or 500
        
        # Use a default model for estimation
        return self.cost_tracker.estimate_cost(
            model="gpt-5-mini",
            input_tokens=int(estimated_input_tokens),
            output_tokens=estimated_output_tokens,
        )
```

## Integration with CRUST Layer (Agents)

### Update Base Agent to Use Configuration

```python
# insanity_cluster/crust/base_agent.py

from insanity_cluster.common.configuration import AgentType
from insanity_cluster.common.retry_handler import create_retry_handler

class BaseAgent(ABC):
    def __init__(self, db_session, user_id=None):
        self.db = db_session
        self.user_id = user_id
        self.agent_type = self._get_agent_type()
        
        # Load configuration
        from insanity_cluster.common.config_manager import ConfigurationManager, config_cache
        self.config_manager = ConfigurationManager(db_session)
        self.config = config_cache.get(user_id)
        if not self.config:
            self.config = self.config_manager.get_active_configuration(user_id)
            if self.config:
                config_cache.set(self.config, user_id)
        
        # Get agent-specific configuration
        self.agent_config = self.config.agent_overrides.get(self.agent_type)
    
    @abstractmethod
    def _get_agent_type(self) -> AgentType:
        """Return the agent type."""
        pass
    
    async def execute(self, subtask, context):
        """Execute subtask with configuration."""
        
        # Get retry handler with agent-specific config
        retry_policy = self.agent_config.retry_policy if self.agent_config else self.config.default_retry_policy
        timeout_config = self.agent_config.timeout_config if self.agent_config else self.config.default_timeout_config
        
        retry_handler = create_retry_handler(
            retry_policy=retry_policy,
            timeout_config=timeout_config,
            circuit_breaker_name=f"{self.agent_type.value}_agent",
        )
        
        # Execute with retry
        result = await retry_handler.execute_with_retry(
            self._execute_internal,
            subtask=subtask,
            context=context,
        )
        
        return result
    
    @abstractmethod
    async def _execute_internal(self, subtask, context):
        """Internal execution logic."""
        pass
```

### Example: Developer Agent

```python
# insanity_cluster/crust/developer_agent.py

class DeveloperAgent(BaseAgent):
    def _get_agent_type(self) -> AgentType:
        return AgentType.DEVELOPER
    
    async def _execute_internal(self, subtask, context):
        """Execute development task."""
        
        # Get preferred models from configuration
        preferred_models = self.agent_config.preferred_models if self.agent_config else ["claude-sonnet-4.5"]
        
        # Use model router with agent type
        from insanity_cluster.pan.model_router import ModelRouter
        router = ModelRouter(self.db, self.user_id)
        
        result = await router.route(
            request=subtask.to_request(),
            agent_type=self.agent_type,
            task_type="code_generation",
        )
        
        return result
```

## Integration with INNER Layer (Orchestration)

### Update Task Decomposition Engine

```python
# insanity_cluster/inner/task_decomposition.py

from insanity_cluster.common.cost_tracker import CostTracker

class TaskDecompositionEngine:
    def __init__(self, db_session, user_id=None):
        self.db = db_session
        self.user_id = user_id
        self.cost_tracker = CostTracker(db_session)
    
    async def decompose(self, command):
        """Decompose command with cost estimation."""
        
        # Estimate cost for decomposition
        estimated_cost = self.cost_tracker.estimate_cost(
            model="claude-sonnet-4.5",
            input_tokens=len(command.text.split()) * 1.3,
            output_tokens=1000,
        )
        
        # Check if within limits
        from insanity_cluster.common.config_manager import ConfigurationManager
        config_manager = ConfigurationManager(self.db)
        config = config_manager.get_active_configuration(self.user_id)
        
        cost_check = self.cost_tracker.check_cost_limits(
            user_id=self.user_id,
            estimated_cost=estimated_cost,
            cost_limits=config.cost_limits,
        )
        
        if not cost_check["allowed"]:
            raise CostLimitExceededError(cost_check["reason"])
        
        # Proceed with decomposition
        task_graph = await self._decompose_internal(command)
        
        return task_graph
```

## Integration with SURFACE Layer (API)

### Update Task Creation Endpoint

```python
# insanity_cluster/surface/api.py

from insanity_cluster.common.cost_tracker import CostTracker, CostLimitEnforcer
from insanity_cluster.common.config_manager import ConfigurationManager

@router.post("/tasks")
async def create_task(
    request: TaskRequest,
    db: Session = Depends(get_db),
    current_user: Dict = Depends(get_current_user),
):
    """Create a new task with cost checking."""
    
    user_id = UUID(current_user["user_id"])
    
    # Get active configuration
    config_manager = ConfigurationManager(db)
    config = config_manager.get_active_configuration(user_id)
    
    if not config:
        raise HTTPException(
            status_code=400,
            detail="No active configuration found. Please select an operating mode.",
        )
    
    # Estimate task cost
    cost_tracker = CostTracker(db)
    estimated_cost = cost_tracker.estimate_cost(
        model="gpt-5-mini",  # Use default for estimation
        input_tokens=len(request.command.split()) * 1.3,
        output_tokens=1000,
    )
    
    # Check cost limits
    cost_enforcer = CostLimitEnforcer(cost_tracker)
    cost_check = cost_enforcer.check_and_enforce(
        user_id=user_id,
        estimated_cost=estimated_cost,
        cost_limits=config.cost_limits,
    )
    
    if not cost_check["allowed"]:
        raise HTTPException(
            status_code=429,
            detail=cost_check["reason"],
        )
    
    # Create task
    task = Task(
        id=uuid.uuid4(),
        user_id=user_id,
        command=request.command,
        status="pending",
    )
    
    db.add(task)
    db.commit()
    
    # Return with cost warning if applicable
    response = {
        "task_id": str(task.id),
        "status": task.status,
        "estimated_cost": estimated_cost,
    }
    
    if cost_check.get("warning"):
        response["warnings"] = cost_check.get("warnings", [])
    
    return response
```

## Environment Variables

Add to `.env`:

```bash
# Configuration defaults
DEFAULT_OPERATING_MODE=mixed
DEFAULT_ROUTING_STRATEGY=cost_optimized
MAX_COST_PER_DAY=50.0
MAX_COST_PER_TASK=1.0

# Retry configuration
MAX_RETRY_ATTEMPTS=3
RETRY_INITIAL_DELAY=1.0
RETRY_MAX_DELAY=60.0

# Circuit breaker configuration
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_TIMEOUT=60

# Timeout configuration
MODEL_CONNECT_TIMEOUT=10.0
MODEL_READ_TIMEOUT=60.0
MODEL_TOTAL_TIMEOUT=120.0
```

## Monitoring and Observability

### Add Prometheus Metrics

```python
from prometheus_client import Counter, Histogram, Gauge

# Cost metrics
cost_per_task = Histogram(
    'insanity_cluster_cost_per_task',
    'Cost per task in dollars',
    buckets=[0.001, 0.01, 0.1, 1.0, 10.0],
)

daily_cost = Gauge(
    'insanity_cluster_daily_cost',
    'Total cost for the day',
    ['user_id'],
)

# Circuit breaker metrics
circuit_breaker_state = Gauge(
    'insanity_cluster_circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=half_open, 2=open)',
    ['name'],
)

# Retry metrics
retry_attempts = Counter(
    'insanity_cluster_retry_attempts_total',
    'Total number of retry attempts',
    ['service', 'success'],
)
```

### Add Grafana Dashboard

Create a dashboard with panels for:
- Daily cost trend
- Cost by model
- Circuit breaker states
- Retry success rates
- Configuration changes over time

## Testing

### Unit Tests

```python
# tests/test_configuration.py

import pytest
from insanity_cluster.common.configuration import ModeConfiguration, OperatingMode

def test_configuration_validation():
    config = ModeConfiguration(
        mode=OperatingMode.LOCAL,
        max_cost_per_day=10.0,  # Should fail validation
    )
    
    errors = config.validate()
    assert len(errors) > 0
    assert "LOCAL mode should have zero cost limits" in errors[0]

def test_cost_estimation():
    from insanity_cluster.common.cost_tracker import CostTracker
    
    tracker = CostTracker(db_session)
    cost = tracker.estimate_cost("gpt-5-nano", 1000, 500)
    
    assert cost > 0
    assert cost < 0.001  # Should be very cheap

def test_retry_handler():
    from insanity_cluster.common.retry_handler import create_retry_handler
    
    retry_handler = create_retry_handler()
    
    attempt_count = 0
    def failing_func():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count < 3:
            raise ConnectionError("Failed")
        return "Success"
    
    result = retry_handler.execute_with_retry_sync(failing_func)
    assert result == "Success"
    assert attempt_count == 3
```

### Integration Tests

```python
# tests/test_config_integration.py

import pytest
from fastapi.testclient import TestClient

def test_create_and_activate_configuration(client: TestClient):
    # Create configuration
    response = client.post(
        "/api/v1/config/configurations",
        json={
            "name": "Test Config",
            "mode": "mixed",
            "max_cost_per_day": 25.0,
        },
    )
    assert response.status_code == 200
    config_id = response.json()["id"]
    
    # Activate configuration
    response = client.put(f"/api/v1/config/configurations/{config_id}/activate")
    assert response.status_code == 200
    
    # Verify active
    response = client.get("/api/v1/config/configurations/active")
    assert response.status_code == 200
    assert response.json()["id"] == config_id
```

## Best Practices

1. **Always Check Cost Limits**: Before executing expensive operations
2. **Use Circuit Breakers**: For all external API calls
3. **Cache Configurations**: Use the built-in cache for active configs
4. **Monitor Metrics**: Track costs, retries, and circuit breaker states
5. **Version Configurations**: Use history tracking for audit trails
6. **Validate Before Save**: Always validate configurations before storage
7. **Set Reasonable Limits**: Start with conservative cost limits
8. **Test Retry Logic**: Ensure retry handlers work with your services
9. **Document Changes**: Use change descriptions when updating configs
10. **Regular Backups**: Export configurations regularly

## Troubleshooting

### Configuration Not Loading

```python
# Check if configuration exists
config = config_manager.get_active_configuration(user_id)
if not config:
    # Create default configurations
    config_manager.create_default_configurations(user_id)
    config = config_manager.get_active_configuration(user_id)
```

### Cost Limits Blocking Tasks

```python
# Check current costs
daily_cost = cost_tracker.get_daily_cost(user_id)
print(f"Current daily cost: ${daily_cost}")

# Adjust limits if needed
config.cost_limits.max_cost_per_day = 100.0
config_manager.update_configuration(config_id, config, user_id)
```

### Circuit Breaker Stuck Open

```python
# Reset circuit breaker
from insanity_cluster.common.retry_handler import circuit_breaker_manager

circuit_breaker_manager.reset("openai_api")
```

## Next Steps

1. **Implement UI**: Build web dashboard for configuration management
2. **Add Metrics**: Integrate with Prometheus and Grafana
3. **Optimize Caching**: Tune cache TTLs based on usage patterns
4. **Add Webhooks**: Notify on cost limits and circuit breaker events
5. **ML-Based Routing**: Use ML to optimize model selection
6. **Cost Forecasting**: Predict future costs based on usage patterns
7. **A/B Testing**: Support configuration experiments
8. **Multi-Tenancy**: Add organization-level configurations

## Support

For questions or issues:
- Check the main README: `insanity_cluster/common/CONFIG_README.md`
- Run the demo: `python examples/config_management_demo.py`
- Review this guide: `insanity_cluster/common/INTEGRATION_GUIDE.md`
