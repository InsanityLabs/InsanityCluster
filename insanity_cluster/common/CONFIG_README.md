# Configuration Management System

The Configuration Management System provides comprehensive control over the Insanity Cluster's operating modes, model routing, cost limits, and fault tolerance mechanisms.

## Overview

The system consists of several key components:

1. **Configuration Data Models** - Define operating modes, routing strategies, and limits
2. **Configuration Manager** - Store and retrieve configurations from PostgreSQL
3. **Cost Tracker** - Track and enforce cost limits
4. **Retry Handler** - Handle failures with exponential backoff and circuit breakers

## Operating Modes

The system supports five operating modes:

### 1. LOCAL Mode (Privacy-First)
- **Description**: All processing on local models, zero cost, maximum privacy
- **Models**: Ollama, LM Studio (LLaMA, Mistral, Phi-3, CodeLLaMA)
- **Cost**: $0
- **Privacy**: Maximum (no external API calls)
- **Use Case**: Privacy-sensitive applications, offline operation

### 2. OPENROUTER_FREE Mode
- **Description**: Only free models via OpenRouter
- **Models**: Various open-source models via OpenRouter free tier
- **Cost**: $0 (rate-limited)
- **Privacy**: Low (external APIs)
- **Use Case**: Experimentation, learning, low-budget projects

### 3. MIXED Mode (Balanced)
- **Description**: Intelligent hybrid of local and paid models
- **Models**: Local for simple tasks, paid for complex tasks
- **Cost**: Variable (configurable limits)
- **Privacy**: Medium
- **Use Case**: Production with cost optimization

### 4. WEB Mode (Premium)
- **Description**: Only premium paid models for maximum quality
- **Models**: GPT-5 series, Claude 4 series (direct APIs)
- **Cost**: High
- **Privacy**: Low (external APIs)
- **Use Case**: Mission-critical production applications

### 5. OPENROUTER_PAID Mode
- **Description**: All models via OpenRouter unified billing
- **Models**: Both free and paid models via OpenRouter
- **Cost**: Variable
- **Privacy**: Low (external APIs)
- **Use Case**: Simplified billing, model variety

## Routing Strategies

Within each mode, you can select a routing strategy:

- **SPEED_FIRST**: Prioritize fastest models (Claude Haiku, local mini models)
- **QUALITY_FIRST**: Prioritize most capable models (Claude Opus, GPT-5.1)
- **COST_OPTIMIZED**: Minimize cost while meeting requirements
- **TASK_SPECIFIC**: Select optimal model per task type

## Configuration Structure

### Basic Configuration

```python
from insanity_cluster.common.configuration import (
    ModeConfiguration,
    OperatingMode,
    RoutingStrategy,
    CostLimits,
)

config = ModeConfiguration(
    mode=OperatingMode.MIXED,
    name="My Configuration",
    description="Custom configuration for my use case",
    default_strategy=RoutingStrategy.COST_OPTIMIZED,
    cost_limits=CostLimits(
        max_cost_per_task=1.0,
        max_cost_per_day=50.0,
        max_cost_per_month=1000.0,
        warning_threshold_percent=80.0,
        block_on_limit=True,
    ),
    local_complexity_threshold=0.5,
)
```

### Agent-Specific Configuration

```python
from insanity_cluster.common.configuration import AgentType, AgentModelConfig

config.agent_overrides[AgentType.DEVELOPER] = AgentModelConfig(
    preferred_models=["claude-sonnet-4.5", "gpt-5-codex", "codellama"],
    fallback_to_paid=True,
    max_cost=2.0,
)

config.agent_overrides[AgentType.COMMUNICATION] = AgentModelConfig(
    preferred_models=["mistral", "claude-haiku-4.5"],
    fallback_to_paid=True,
    max_cost=0.1,
)
```

### Task-Type Configuration

```python
from insanity_cluster.common.configuration import TaskModelConfig

config.task_type_overrides["code_generation"] = TaskModelConfig(
    strategy_override=RoutingStrategy.QUALITY_FIRST,
    allow_local=False,
    allow_paid=True,
)

config.task_type_overrides["simple_chat"] = TaskModelConfig(
    model_override="phi3",
    allow_local=True,
    allow_paid=False,
)
```

## Configuration Management

### Creating Configurations

```python
from insanity_cluster.common.config_manager import ConfigurationManager

config_manager = ConfigurationManager(db_session)

config_id = config_manager.create_configuration(
    config=config,
    user_id=user_id,
    set_active=True,
)
```

### Retrieving Configurations

```python
# Get active configuration
active_config = config_manager.get_active_configuration(user_id)

# Get specific configuration
config = config_manager.get_configuration(config_id)

# List all configurations
configs = config_manager.list_configurations(user_id)
```

### Updating Configurations

```python
config_manager.update_configuration(
    config_id=config_id,
    config=updated_config,
    user_id=user_id,
    change_description="Updated cost limits",
)
```

### Configuration History

```python
# Get configuration history
history = config_manager.get_configuration_history(config_id, limit=10)

# Restore previous version
config_manager.restore_configuration_version(
    config_id=config_id,
    version=5,
    user_id=user_id,
)
```

### Export/Import

```python
# Export to JSON
json_str = config_manager.export_configuration(config_id, format="json")

# Export to YAML
yaml_str = config_manager.export_configuration(config_id, format="yaml")

# Import from JSON
config_id = config_manager.import_configuration(
    data=json_str,
    format="json",
    user_id=user_id,
    set_active=True,
)
```

## Cost Tracking

### Estimating Costs

```python
from insanity_cluster.common.cost_tracker import CostTracker

cost_tracker = CostTracker(db_session)

estimated_cost = cost_tracker.estimate_cost(
    model="claude-sonnet-4.5",
    input_tokens=1000,
    output_tokens=500,
)
```

### Recording Costs

```python
cost_tracker.record_task_cost(
    task_id=task_id,
    cost=0.015,
    model_used="claude-sonnet-4.5",
    input_tokens=1000,
    output_tokens=500,
)
```

### Checking Cost Limits

```python
from insanity_cluster.common.cost_tracker import CostLimitEnforcer

enforcer = CostLimitEnforcer(cost_tracker)

result = enforcer.check_and_enforce(
    user_id=user_id,
    estimated_cost=0.5,
    cost_limits=config.cost_limits,
)

if not result["allowed"]:
    print(f"Task blocked: {result['reason']}")
elif result["warning"]:
    print(f"Warning: {result['warnings']}")
```

### Cost Reports

```python
# Get daily cost
daily_cost = cost_tracker.get_daily_cost(user_id)

# Get monthly cost
monthly_cost = cost_tracker.get_monthly_cost(user_id)

# Get detailed report
report = cost_tracker.get_cost_report(
    user_id=user_id,
    start_date=start_date,
    end_date=end_date,
)

# Get analytics
analytics = cost_tracker.get_cost_analytics(user_id)
```

## Retry Policies and Circuit Breakers

### Creating Retry Handler

```python
from insanity_cluster.common.retry_handler import create_retry_handler
from insanity_cluster.common.configuration import (
    RetryPolicy,
    TimeoutConfig,
    CircuitBreakerConfig,
)

retry_handler = create_retry_handler(
    retry_policy=RetryPolicy(
        max_attempts=3,
        initial_delay_seconds=1.0,
        max_delay_seconds=60.0,
        exponential_base=2.0,
        jitter=True,
    ),
    timeout_config=TimeoutConfig(
        connect_timeout_seconds=10.0,
        read_timeout_seconds=60.0,
        total_timeout_seconds=120.0,
    ),
    circuit_breaker_name="openai_api",
    circuit_breaker_config=CircuitBreakerConfig(
        failure_threshold=5,
        success_threshold=2,
        timeout_seconds=60,
    ),
)
```

### Using Retry Handler

```python
# Async function
async def call_api():
    # Your API call here
    pass

result = await retry_handler.execute_with_retry(call_api)

# Sync function
def call_api_sync():
    # Your API call here
    pass

result = retry_handler.execute_with_retry_sync(call_api_sync)
```

### Monitoring Circuit Breakers

```python
from insanity_cluster.common.retry_handler import circuit_breaker_manager

# Get all circuit breaker states
states = circuit_breaker_manager.get_all_states()

# Reset a circuit breaker
circuit_breaker_manager.reset("openai_api")

# Reset all circuit breakers
circuit_breaker_manager.reset_all()
```

## API Endpoints

### Configuration Endpoints

- `GET /api/v1/config/modes` - List operating modes
- `POST /api/v1/config/modes/select` - Select operating mode
- `GET /api/v1/config/configurations` - List configurations
- `GET /api/v1/config/configurations/active` - Get active configuration
- `POST /api/v1/config/configurations` - Create configuration
- `PUT /api/v1/config/configurations/{id}/activate` - Activate configuration
- `DELETE /api/v1/config/configurations/{id}` - Delete configuration
- `POST /api/v1/config/configurations/{id}/agents` - Configure agent models
- `POST /api/v1/config/configurations/{id}/tasks` - Configure task models
- `POST /api/v1/config/configurations/{id}/providers` - Configure providers
- `POST /api/v1/config/configurations/{id}/validate` - Validate configuration
- `GET /api/v1/config/configurations/{id}/export` - Export configuration
- `POST /api/v1/config/configurations/import` - Import configuration

### Cost Tracking Endpoints

- `POST /api/v1/costs/estimate` - Estimate cost
- `GET /api/v1/costs/daily` - Get daily cost
- `GET /api/v1/costs/monthly` - Get monthly cost
- `GET /api/v1/costs/report` - Get cost report
- `GET /api/v1/costs/analytics` - Get cost analytics

### Monitoring Endpoints

- `GET /api/v1/monitoring/circuit-breakers` - Get all circuit breaker states
- `GET /api/v1/monitoring/circuit-breakers/{name}` - Get circuit breaker state
- `POST /api/v1/monitoring/circuit-breakers/reset` - Reset circuit breaker
- `POST /api/v1/monitoring/circuit-breakers/reset-all` - Reset all
- `GET /api/v1/monitoring/health` - Health check

## Model Pricing

The system includes pricing information for common models:

| Model | Input (per 1M tokens) | Output (per 1M tokens) |
|-------|----------------------|------------------------|
| gpt-5.1 | $1.25 | $5.00 |
| gpt-5 | $1.00 | $4.00 |
| gpt-5-mini | $0.15 | $0.60 |
| gpt-5-nano | $0.05 | $0.20 |
| gpt-5-codex | $1.50 | $6.00 |
| claude-opus-4.1 | $15.00 | $75.00 |
| claude-sonnet-4.5 | $3.00 | $15.00 |
| claude-haiku-4.5 | $1.00 | $5.00 |
| Local models | $0.00 | $0.00 |

## Best Practices

### 1. Start with Default Configurations

Use the default configurations as a starting point:

```python
from insanity_cluster.common.configuration import get_default_config

config = get_default_config(OperatingMode.MIXED)
```

### 2. Set Appropriate Cost Limits

Always set cost limits to prevent unexpected charges:

```python
config.cost_limits = CostLimits(
    max_cost_per_day=50.0,
    warning_threshold_percent=80.0,
    block_on_limit=True,
)
```

### 3. Use Task-Specific Overrides

Configure specific models for critical tasks:

```python
config.task_type_overrides["contract_review"] = TaskModelConfig(
    strategy_override=RoutingStrategy.QUALITY_FIRST,
    allow_local=False,
)
```

### 4. Monitor Circuit Breakers

Regularly check circuit breaker states to identify failing services:

```python
states = circuit_breaker_manager.get_all_states()
open_breakers = [name for name, state in states.items() if state["state"] == "open"]
```

### 5. Version Your Configurations

Use configuration history to track changes:

```python
config_manager.update_configuration(
    config_id=config_id,
    config=config,
    user_id=user_id,
    change_description="Increased cost limits for production deployment",
)
```

## Examples

See `examples/config_management_demo.py` for comprehensive examples of:
- Creating custom configurations
- Using default configurations
- Cost tracking and limits
- Retry handlers and circuit breakers
- Configuration export/import

## Database Schema

The system uses two tables:

### configurations
- `id` (UUID) - Primary key
- `user_id` (UUID) - Foreign key to users
- `name` (VARCHAR) - Configuration name
- `description` (TEXT) - Configuration description
- `config_data` (JSONB) - Configuration data
- `version` (INTEGER) - Version number
- `is_active` (BOOLEAN) - Whether configuration is active
- `is_default` (BOOLEAN) - Whether configuration is default
- `created_at` (TIMESTAMP) - Creation timestamp
- `updated_at` (TIMESTAMP) - Update timestamp

### configuration_history
- `id` (UUID) - Primary key
- `config_id` (UUID) - Foreign key to configurations
- `config_data` (JSONB) - Historical configuration data
- `version` (INTEGER) - Version number
- `changed_by` (UUID) - User who made the change
- `change_description` (TEXT) - Description of changes
- `created_at` (TIMESTAMP) - Creation timestamp

## Migration

Run the database migration to create the configuration tables:

```bash
alembic upgrade head
```

## Testing

Run the demo to test the configuration system:

```bash
python examples/config_management_demo.py
```
