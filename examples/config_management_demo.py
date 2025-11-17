"""
Configuration Management System Demo

This example demonstrates:
1. Creating and managing configurations
2. Setting operating modes
3. Configuring agent-specific models
4. Setting up cost limits and tracking
5. Using retry policies and circuit breakers
"""
import asyncio
import uuid
from datetime import datetime

from insanity_cluster.common.configuration import (
    ModeConfiguration,
    OperatingMode,
    RoutingStrategy,
    AgentType,
    AgentModelConfig,
    TaskModelConfig,
    CostLimits,
    RetryPolicy,
    TimeoutConfig,
    CircuitBreakerConfig,
    get_default_config,
)
from insanity_cluster.common.config_manager import ConfigurationManager
from insanity_cluster.common.cost_tracker import CostTracker, CostLimitEnforcer
from insanity_cluster.common.retry_handler import (
    create_retry_handler,
    CircuitBreakerOpenError,
)


def demo_configuration_creation():
    """Demonstrate creating custom configurations."""
    print("=" * 80)
    print("DEMO 1: Configuration Creation")
    print("=" * 80)
    
    # Create a custom mixed mode configuration
    config = ModeConfiguration(
        mode=OperatingMode.MIXED,
        name="Development Configuration",
        description="Optimized for development with cost controls",
        default_strategy=RoutingStrategy.COST_OPTIMIZED,
        cost_limits=CostLimits(
            max_cost_per_task=1.0,
            max_cost_per_day=25.0,
            max_cost_per_month=500.0,
            warning_threshold_percent=80.0,
            block_on_limit=True,
        ),
        local_complexity_threshold=0.6,
        paid_model_trigger="complexity",
    )
    
    # Add agent-specific configurations
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
    
    # Add task-type configurations
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
    
    print(f"\nCreated configuration: {config.name}")
    print(f"Mode: {config.mode.value}")
    print(f"Strategy: {config.default_strategy.value}")
    print(f"Max cost per day: ${config.cost_limits.max_cost_per_day}")
    print(f"Agent overrides: {len(config.agent_overrides)}")
    print(f"Task overrides: {len(config.task_type_overrides)}")
    
    # Validate configuration
    errors = config.validate()
    if errors:
        print(f"\nValidation errors: {errors}")
    else:
        print("\n✓ Configuration is valid")
    
    # Export to JSON
    json_export = config.to_json()
    print(f"\nExported configuration (first 200 chars):")
    print(json_export[:200] + "...")
    
    return config


def demo_default_configurations():
    """Demonstrate default configurations for each mode."""
    print("\n" + "=" * 80)
    print("DEMO 2: Default Configurations")
    print("=" * 80)
    
    for mode in OperatingMode:
        config = get_default_config(mode)
        print(f"\n{mode.value.upper()} Mode:")
        print(f"  Name: {config.name}")
        print(f"  Description: {config.description}")
        print(f"  Strategy: {config.default_strategy.value}")
        print(f"  Max daily cost: ${config.cost_limits.max_cost_per_day or 'unlimited'}")
        print(f"  Agent overrides: {len(config.agent_overrides)}")


def demo_cost_tracking():
    """Demonstrate cost tracking and limits."""
    print("\n" + "=" * 80)
    print("DEMO 3: Cost Tracking and Limits")
    print("=" * 80)
    
    # Note: This would require a database session in real usage
    # For demo purposes, we'll show the API
    
    print("\nCost Estimation:")
    print("-" * 40)
    
    # Simulate cost estimation
    models = [
        ("gpt-5-nano", 1000, 500),
        ("claude-haiku-4.5", 1000, 500),
        ("claude-sonnet-4.5", 1000, 500),
        ("claude-opus-4.1", 1000, 500),
    ]
    
    for model, input_tokens, output_tokens in models:
        # This would use CostTracker.estimate_cost() in real usage
        input_cost = (input_tokens / 1_000_000) * CostTracker.MODEL_PRICING.get(model, {}).get("input", 0)
        output_cost = (output_tokens / 1_000_000) * CostTracker.MODEL_PRICING.get(model, {}).get("output", 0)
        total_cost = input_cost + output_cost
        
        print(f"{model:20s}: ${total_cost:.6f} ({input_tokens} in, {output_tokens} out)")
    
    print("\nCost Limit Checking:")
    print("-" * 40)
    
    cost_limits = CostLimits(
        max_cost_per_task=1.0,
        max_cost_per_day=25.0,
        warning_threshold_percent=80.0,
        block_on_limit=True,
    )
    
    print(f"Max per task: ${cost_limits.max_cost_per_task}")
    print(f"Max per day: ${cost_limits.max_cost_per_day}")
    print(f"Warning threshold: {cost_limits.warning_threshold_percent}%")
    print(f"Block on limit: {cost_limits.block_on_limit}")
    
    # Simulate cost check
    estimated_cost = 0.5
    current_daily = 20.0
    
    print(f"\nEstimated task cost: ${estimated_cost}")
    print(f"Current daily cost: ${current_daily}")
    print(f"Projected daily: ${current_daily + estimated_cost}")
    
    if current_daily + estimated_cost > cost_limits.max_cost_per_day * 0.8:
        print("⚠️  WARNING: Approaching daily limit!")
    else:
        print("✓ Within limits")


async def demo_retry_handler():
    """Demonstrate retry handler with circuit breaker."""
    print("\n" + "=" * 80)
    print("DEMO 4: Retry Handler and Circuit Breaker")
    print("=" * 80)
    
    # Create retry policy
    retry_policy = RetryPolicy(
        max_attempts=3,
        initial_delay_seconds=1.0,
        max_delay_seconds=10.0,
        exponential_base=2.0,
        jitter=True,
    )
    
    # Create timeout config
    timeout_config = TimeoutConfig(
        connect_timeout_seconds=5.0,
        read_timeout_seconds=30.0,
        total_timeout_seconds=60.0,
    )
    
    # Create circuit breaker config
    circuit_breaker_config = CircuitBreakerConfig(
        failure_threshold=3,
        success_threshold=2,
        timeout_seconds=30,
        half_open_max_calls=1,
    )
    
    print("\nRetry Policy:")
    print(f"  Max attempts: {retry_policy.max_attempts}")
    print(f"  Initial delay: {retry_policy.initial_delay_seconds}s")
    print(f"  Max delay: {retry_policy.max_delay_seconds}s")
    print(f"  Exponential base: {retry_policy.exponential_base}")
    
    print("\nTimeout Configuration:")
    print(f"  Connect timeout: {timeout_config.connect_timeout_seconds}s")
    print(f"  Read timeout: {timeout_config.read_timeout_seconds}s")
    print(f"  Total timeout: {timeout_config.total_timeout_seconds}s")
    
    print("\nCircuit Breaker Configuration:")
    print(f"  Failure threshold: {circuit_breaker_config.failure_threshold}")
    print(f"  Success threshold: {circuit_breaker_config.success_threshold}")
    print(f"  Timeout: {circuit_breaker_config.timeout_seconds}s")
    
    # Create retry handler
    retry_handler = create_retry_handler(
        retry_policy=retry_policy,
        timeout_config=timeout_config,
        circuit_breaker_name="demo_service",
        circuit_breaker_config=circuit_breaker_config,
    )
    
    # Simulate successful execution
    print("\n\nSimulating successful execution:")
    print("-" * 40)
    
    async def successful_operation():
        await asyncio.sleep(0.1)
        return "Success!"
    
    try:
        result = await retry_handler.execute_with_retry(successful_operation)
        print(f"Result: {result}")
        stats = retry_handler.get_statistics()
        print(f"Attempts: {stats['total_attempts']}")
        print(f"Success rate: {stats['success_rate_percent']:.1f}%")
    except Exception as e:
        print(f"Error: {e}")
    
    # Simulate failing operation
    print("\n\nSimulating failing operation (will retry):")
    print("-" * 40)
    
    attempt_count = 0
    
    async def failing_operation():
        nonlocal attempt_count
        attempt_count += 1
        print(f"  Attempt {attempt_count}...")
        if attempt_count < 3:
            raise ConnectionError("Service unavailable")
        return "Success after retries!"
    
    retry_handler.reset_statistics()
    attempt_count = 0
    
    try:
        result = await retry_handler.execute_with_retry(failing_operation)
        print(f"Result: {result}")
        stats = retry_handler.get_statistics()
        print(f"Total attempts: {stats['total_attempts']}")
        print(f"Failed attempts: {stats['failed_attempts']}")
        print(f"Total delay: {stats['total_delay_seconds']:.2f}s")
    except Exception as e:
        print(f"Error: {e}")


def demo_configuration_export_import():
    """Demonstrate configuration export and import."""
    print("\n" + "=" * 80)
    print("DEMO 5: Configuration Export/Import")
    print("=" * 80)
    
    # Create a configuration
    original_config = ModeConfiguration(
        mode=OperatingMode.WEB,
        name="Production Configuration",
        description="High-quality models for production",
        default_strategy=RoutingStrategy.QUALITY_FIRST,
        cost_limits=CostLimits(
            max_cost_per_day=100.0,
            warning_threshold_percent=85.0,
        ),
    )
    
    print("\nOriginal Configuration:")
    print(f"  Name: {original_config.name}")
    print(f"  Mode: {original_config.mode.value}")
    print(f"  Strategy: {original_config.default_strategy.value}")
    
    # Export to JSON
    json_str = original_config.to_json()
    print(f"\nExported to JSON ({len(json_str)} bytes)")
    
    # Import from JSON
    imported_config = ModeConfiguration.from_json(json_str)
    
    print("\nImported Configuration:")
    print(f"  Name: {imported_config.name}")
    print(f"  Mode: {imported_config.mode.value}")
    print(f"  Strategy: {imported_config.default_strategy.value}")
    
    # Verify they match
    if original_config.to_dict() == imported_config.to_dict():
        print("\n✓ Export/Import successful - configurations match!")
    else:
        print("\n✗ Export/Import failed - configurations differ")


async def main():
    """Run all demos."""
    print("\n")
    print("╔" + "=" * 78 + "╗")
    print("║" + " " * 20 + "CONFIGURATION MANAGEMENT DEMO" + " " * 29 + "║")
    print("╚" + "=" * 78 + "╝")
    
    # Run demos
    demo_configuration_creation()
    demo_default_configurations()
    demo_cost_tracking()
    await demo_retry_handler()
    demo_configuration_export_import()
    
    print("\n" + "=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)
    print("\nKey Features Demonstrated:")
    print("  ✓ Configuration creation and validation")
    print("  ✓ Default configurations for all modes")
    print("  ✓ Cost tracking and limit enforcement")
    print("  ✓ Retry policies with exponential backoff")
    print("  ✓ Circuit breaker pattern")
    print("  ✓ Configuration export/import")
    print("\nNext Steps:")
    print("  - Integrate with database for persistence")
    print("  - Use in SURFACE layer API endpoints")
    print("  - Apply to PAN layer model routing")
    print("  - Monitor via Grafana dashboards")
    print()


if __name__ == "__main__":
    asyncio.run(main())
