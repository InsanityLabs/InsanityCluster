"""
Configuration data models for the Insanity Cluster system.

This module provides comprehensive configuration management including:
- Operating modes (Local, OpenRouter Free, Mixed, Web, OpenRouter Paid)
- Routing strategies (Speed-First, Quality-First, Cost-Optimized, Task-Specific)
- Per-agent and per-task-type model configurations
- Cost tracking and limits
- Retry policies and timeout configuration
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
import json


class OperatingMode(str, Enum):
    """Operating modes for model routing."""
    LOCAL = "local"  # Only local models (Ollama, LM Studio)
    OPENROUTER_FREE = "openrouter_free"  # Only free OpenRouter models
    MIXED = "mixed"  # Hybrid: local for simple, paid for complex
    WEB = "web"  # Only premium paid models (OpenAI, Anthropic direct)
    OPENROUTER_PAID = "openrouter_paid"  # All models via OpenRouter


class RoutingStrategy(str, Enum):
    """Routing strategies within each mode."""
    SPEED_FIRST = "speed_first"  # Prioritize fastest models
    QUALITY_FIRST = "quality_first"  # Prioritize most capable models
    COST_OPTIMIZED = "cost_optimized"  # Minimize cost while meeting requirements
    TASK_SPECIFIC = "task_specific"  # Select optimal model per task type


class AgentType(str, Enum):
    """Types of specialized agents."""
    DEVELOPER = "developer"
    COMMUNICATION = "communication"
    BUSINESS = "business"
    RESEARCH = "research"
    CREATIVE = "creative"
    FINANCE = "finance"
    PROJECT_MANAGER = "project_manager"


@dataclass
class RetryPolicy:
    """
    Retry policy configuration for handling failures.
    """
    max_attempts: int = 3
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    
    def __post_init__(self):
        """Validate retry policy configuration."""
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.initial_delay_seconds <= 0:
            raise ValueError("initial_delay_seconds must be positive")
        if self.max_delay_seconds < self.initial_delay_seconds:
            raise ValueError("max_delay_seconds must be >= initial_delay_seconds")
        if self.exponential_base < 1:
            raise ValueError("exponential_base must be >= 1")
    
    def get_delay(self, attempt: int) -> float:
        """
        Calculate delay for a given attempt number.
        
        Args:
            attempt: Attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        import random
        
        delay = min(
            self.initial_delay_seconds * (self.exponential_base ** attempt),
            self.max_delay_seconds
        )
        
        if self.jitter:
            # Add random jitter (±25%)
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)
        
        return max(0, delay)


@dataclass
class TimeoutConfig:
    """
    Timeout configuration for model endpoints.
    """
    connect_timeout_seconds: float = 10.0
    read_timeout_seconds: float = 60.0
    total_timeout_seconds: float = 120.0
    
    def __post_init__(self):
        """Validate timeout configuration."""
        if self.connect_timeout_seconds <= 0:
            raise ValueError("connect_timeout_seconds must be positive")
        if self.read_timeout_seconds <= 0:
            raise ValueError("read_timeout_seconds must be positive")
        if self.total_timeout_seconds <= 0:
            raise ValueError("total_timeout_seconds must be positive")


@dataclass
class CircuitBreakerConfig:
    """
    Circuit breaker configuration for fault tolerance.
    """
    failure_threshold: int = 5
    success_threshold: int = 2
    timeout_seconds: int = 60
    half_open_max_calls: int = 1
    
    def __post_init__(self):
        """Validate circuit breaker configuration."""
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be at least 1")
        if self.success_threshold < 1:
            raise ValueError("success_threshold must be at least 1")
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.half_open_max_calls < 1:
            raise ValueError("half_open_max_calls must be at least 1")


@dataclass
class AgentModelConfig:
    """
    Model configuration for a specific agent.
    """
    preferred_models: List[str] = field(default_factory=list)
    fallback_to_paid: bool = True
    max_cost: Optional[float] = None
    timeout_config: Optional[TimeoutConfig] = None
    retry_policy: Optional[RetryPolicy] = None
    
    def __post_init__(self):
        """Validate configuration."""
        if self.max_cost is not None and self.max_cost < 0:
            raise ValueError("max_cost must be non-negative")
        
        # Set defaults if not provided
        if self.timeout_config is None:
            self.timeout_config = TimeoutConfig()
        if self.retry_policy is None:
            self.retry_policy = RetryPolicy()


@dataclass
class TaskModelConfig:
    """
    Model configuration for a specific task type.
    """
    model_override: Optional[str] = None
    strategy_override: Optional[RoutingStrategy] = None
    allow_local: bool = True
    allow_paid: bool = True
    max_cost: Optional[float] = None
    timeout_config: Optional[TimeoutConfig] = None
    
    def __post_init__(self):
        """Validate configuration."""
        if not self.allow_local and not self.allow_paid:
            raise ValueError("At least one of allow_local or allow_paid must be True")
        if self.max_cost is not None and self.max_cost < 0:
            raise ValueError("max_cost must be non-negative")
        
        # Set defaults if not provided
        if self.timeout_config is None:
            self.timeout_config = TimeoutConfig()


@dataclass
class CostLimits:
    """
    Cost limits and tracking configuration.
    """
    max_cost_per_task: Optional[float] = None
    max_cost_per_day: Optional[float] = None
    max_cost_per_month: Optional[float] = None
    warning_threshold_percent: float = 80.0
    block_on_limit: bool = True
    
    def __post_init__(self):
        """Validate cost limits."""
        if self.max_cost_per_task is not None and self.max_cost_per_task < 0:
            raise ValueError("max_cost_per_task must be non-negative")
        if self.max_cost_per_day is not None and self.max_cost_per_day < 0:
            raise ValueError("max_cost_per_day must be non-negative")
        if self.max_cost_per_month is not None and self.max_cost_per_month < 0:
            raise ValueError("max_cost_per_month must be non-negative")
        if not 0 <= self.warning_threshold_percent <= 100:
            raise ValueError("warning_threshold_percent must be between 0 and 100")


@dataclass
class ModelProviderConfig:
    """
    Configuration for a model provider.
    """
    provider_name: str
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    enabled: bool = True
    enabled_models: List[str] = field(default_factory=list)
    rate_limit_rpm: Optional[int] = None
    timeout_config: TimeoutConfig = field(default_factory=TimeoutConfig)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    circuit_breaker_config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    
    def __post_init__(self):
        """Validate provider configuration."""
        if not self.provider_name:
            raise ValueError("provider_name cannot be empty")
        if self.rate_limit_rpm is not None and self.rate_limit_rpm <= 0:
            raise ValueError("rate_limit_rpm must be positive")


@dataclass
class ModeConfiguration:
    """
    Complete configuration for an operating mode.
    """
    mode: OperatingMode
    default_strategy: RoutingStrategy = RoutingStrategy.COST_OPTIMIZED
    
    # Cost limits
    cost_limits: CostLimits = field(default_factory=CostLimits)
    
    # Mixed mode settings
    local_complexity_threshold: float = 0.5
    paid_model_trigger: str = "complexity"  # "complexity", "failure", "explicit"
    
    # Per-agent overrides
    agent_overrides: Dict[AgentType, AgentModelConfig] = field(default_factory=dict)
    
    # Per-task-type overrides
    task_type_overrides: Dict[str, TaskModelConfig] = field(default_factory=dict)
    
    # Model provider configurations
    provider_configs: Dict[str, ModelProviderConfig] = field(default_factory=dict)
    
    # Global retry and timeout settings
    default_retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    default_timeout_config: TimeoutConfig = field(default_factory=TimeoutConfig)
    default_circuit_breaker_config: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    
    # Metadata
    name: Optional[str] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    version: int = 1
    
    def __post_init__(self):
        """Validate configuration."""
        if self.local_complexity_threshold < 0 or self.local_complexity_threshold > 1:
            raise ValueError("local_complexity_threshold must be between 0 and 1")
        
        if self.paid_model_trigger not in ["complexity", "failure", "explicit"]:
            raise ValueError("paid_model_trigger must be 'complexity', 'failure', or 'explicit'")
        
        # Set timestamps if not provided
        if self.created_at is None:
            self.created_at = datetime.utcnow()
        if self.updated_at is None:
            self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        def convert_value(obj):
            if isinstance(obj, Enum):
                return obj.value
            elif isinstance(obj, datetime):
                return obj.isoformat()
            elif hasattr(obj, '__dict__'):
                return asdict(obj)
            return obj
        
        result = {}
        for key, value in asdict(self).items():
            if isinstance(value, dict):
                result[key] = {k: convert_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                result[key] = [convert_value(v) for v in value]
            else:
                result[key] = convert_value(value)
        
        return result
    
    def to_json(self) -> str:
        """Convert configuration to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModeConfiguration':
        """Create configuration from dictionary."""
        # Convert string enums back to enum types
        if 'mode' in data and isinstance(data['mode'], str):
            data['mode'] = OperatingMode(data['mode'])
        if 'default_strategy' in data and isinstance(data['default_strategy'], str):
            data['default_strategy'] = RoutingStrategy(data['default_strategy'])
        
        # Convert datetime strings back to datetime objects
        if 'created_at' in data and isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if 'updated_at' in data and isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        
        # Convert nested dictionaries to dataclass instances
        if 'cost_limits' in data and isinstance(data['cost_limits'], dict):
            data['cost_limits'] = CostLimits(**data['cost_limits'])
        
        if 'agent_overrides' in data:
            agent_overrides = {}
            for agent_type_str, config_dict in data['agent_overrides'].items():
                agent_type = AgentType(agent_type_str)
                agent_overrides[agent_type] = AgentModelConfig(**config_dict)
            data['agent_overrides'] = agent_overrides
        
        if 'task_type_overrides' in data:
            task_overrides = {}
            for task_type, config_dict in data['task_type_overrides'].items():
                if 'strategy_override' in config_dict and config_dict['strategy_override']:
                    config_dict['strategy_override'] = RoutingStrategy(config_dict['strategy_override'])
                task_overrides[task_type] = TaskModelConfig(**config_dict)
            data['task_type_overrides'] = task_overrides
        
        if 'provider_configs' in data:
            provider_configs = {}
            for provider_name, config_dict in data['provider_configs'].items():
                provider_configs[provider_name] = ModelProviderConfig(**config_dict)
            data['provider_configs'] = provider_configs
        
        # Convert nested retry/timeout/circuit breaker configs
        for key in ['default_retry_policy', 'default_timeout_config', 'default_circuit_breaker_config']:
            if key in data and isinstance(data[key], dict):
                class_map = {
                    'default_retry_policy': RetryPolicy,
                    'default_timeout_config': TimeoutConfig,
                    'default_circuit_breaker_config': CircuitBreakerConfig,
                }
                data[key] = class_map[key](**data[key])
        
        return cls(**data)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'ModeConfiguration':
        """Create configuration from JSON string."""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def validate(self) -> List[str]:
        """
        Validate configuration and return list of validation errors.
        
        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []
        
        # Validate mode-specific constraints
        if self.mode == OperatingMode.LOCAL:
            if self.cost_limits.max_cost_per_task and self.cost_limits.max_cost_per_task > 0:
                errors.append("LOCAL mode should have zero cost limits")
        
        # Validate agent overrides
        for agent_type, config in self.agent_overrides.items():
            if not config.preferred_models:
                errors.append(f"Agent {agent_type.value} has no preferred models")
            
            if self.mode == OperatingMode.LOCAL and config.fallback_to_paid:
                errors.append(f"Agent {agent_type.value} cannot fallback to paid in LOCAL mode")
        
        # Validate task type overrides
        for task_type, config in self.task_type_overrides.items():
            if self.mode == OperatingMode.LOCAL and config.allow_paid:
                errors.append(f"Task type '{task_type}' cannot allow paid models in LOCAL mode")
            
            if not config.allow_local and not config.allow_paid:
                errors.append(f"Task type '{task_type}' must allow at least one model type")
        
        # Validate provider configs
        for provider_name, config in self.provider_configs.items():
            if config.enabled and not config.api_key and provider_name not in ['ollama', 'lmstudio']:
                errors.append(f"Provider '{provider_name}' is enabled but has no API key")
        
        return errors


# Default configurations for each operating mode
def get_default_local_config() -> ModeConfiguration:
    """Get default configuration for LOCAL mode."""
    return ModeConfiguration(
        mode=OperatingMode.LOCAL,
        name="Local Mode (Privacy-First)",
        description="All processing on local models, zero cost, maximum privacy",
        default_strategy=RoutingStrategy.SPEED_FIRST,
        cost_limits=CostLimits(
            max_cost_per_task=0.0,
            max_cost_per_day=0.0,
        ),
        agent_overrides={
            AgentType.DEVELOPER: AgentModelConfig(
                preferred_models=["codellama", "llama3:70b"],
                fallback_to_paid=False,
            ),
            AgentType.COMMUNICATION: AgentModelConfig(
                preferred_models=["mistral", "phi3"],
                fallback_to_paid=False,
            ),
            AgentType.BUSINESS: AgentModelConfig(
                preferred_models=["llama3:70b", "mixtral:8x7b"],
                fallback_to_paid=False,
            ),
            AgentType.RESEARCH: AgentModelConfig(
                preferred_models=["llama3:70b", "mistral"],
                fallback_to_paid=False,
            ),
        },
        provider_configs={
            "ollama": ModelProviderConfig(
                provider_name="ollama",
                base_url="http://localhost:11434",
                enabled=True,
            ),
            "lmstudio": ModelProviderConfig(
                provider_name="lmstudio",
                base_url="http://localhost:1234",
                enabled=True,
            ),
        },
    )


def get_default_openrouter_free_config() -> ModeConfiguration:
    """Get default configuration for OPENROUTER_FREE mode."""
    return ModeConfiguration(
        mode=OperatingMode.OPENROUTER_FREE,
        name="OpenRouter Free",
        description="Only free models via OpenRouter, no direct costs",
        default_strategy=RoutingStrategy.SPEED_FIRST,
        cost_limits=CostLimits(
            max_cost_per_task=0.0,
            max_cost_per_day=0.0,
        ),
    )


def get_default_mixed_config() -> ModeConfiguration:
    """Get default configuration for MIXED mode."""
    return ModeConfiguration(
        mode=OperatingMode.MIXED,
        name="Mixed Mode (Balanced)",
        description="Intelligent hybrid of local and paid models based on complexity",
        default_strategy=RoutingStrategy.COST_OPTIMIZED,
        cost_limits=CostLimits(
            max_cost_per_day=50.0,
            warning_threshold_percent=80.0,
        ),
        local_complexity_threshold=0.5,
        paid_model_trigger="complexity",
        agent_overrides={
            AgentType.DEVELOPER: AgentModelConfig(
                preferred_models=["claude-sonnet-4.5", "gpt-5-codex", "codellama"],
                fallback_to_paid=True,
                max_cost=1.0,
            ),
            AgentType.COMMUNICATION: AgentModelConfig(
                preferred_models=["mistral", "claude-haiku-4.5"],
                fallback_to_paid=True,
                max_cost=0.1,
            ),
            AgentType.BUSINESS: AgentModelConfig(
                preferred_models=["claude-opus-4.1", "llama3:70b"],
                fallback_to_paid=True,
                max_cost=2.0,
            ),
        },
        task_type_overrides={
            "code_generation": TaskModelConfig(
                strategy_override=RoutingStrategy.QUALITY_FIRST,
                allow_local=False,
            ),
            "simple_chat": TaskModelConfig(
                model_override="phi3",
                allow_paid=False,
            ),
            "contract_review": TaskModelConfig(
                strategy_override=RoutingStrategy.QUALITY_FIRST,
                allow_local=False,
            ),
        },
    )


def get_default_web_config() -> ModeConfiguration:
    """Get default configuration for WEB mode."""
    return ModeConfiguration(
        mode=OperatingMode.WEB,
        name="Web Mode (Premium)",
        description="Only premium paid models for maximum quality and speed",
        default_strategy=RoutingStrategy.QUALITY_FIRST,
        cost_limits=CostLimits(
            max_cost_per_day=100.0,
            warning_threshold_percent=80.0,
        ),
        agent_overrides={
            AgentType.DEVELOPER: AgentModelConfig(
                preferred_models=["claude-sonnet-4.5", "gpt-5-codex"],
                max_cost=2.0,
            ),
            AgentType.BUSINESS: AgentModelConfig(
                preferred_models=["claude-opus-4.1", "gpt-5.1"],
                max_cost=5.0,
            ),
            AgentType.COMMUNICATION: AgentModelConfig(
                preferred_models=["claude-haiku-4.5", "gpt-5-mini"],
                max_cost=0.5,
            ),
        },
    )


def get_default_openrouter_paid_config() -> ModeConfiguration:
    """Get default configuration for OPENROUTER_PAID mode."""
    return ModeConfiguration(
        mode=OperatingMode.OPENROUTER_PAID,
        name="OpenRouter Paid",
        description="All models via OpenRouter unified billing",
        default_strategy=RoutingStrategy.COST_OPTIMIZED,
        cost_limits=CostLimits(
            max_cost_per_day=75.0,
            warning_threshold_percent=80.0,
        ),
    )


DEFAULT_CONFIGS = {
    OperatingMode.LOCAL: get_default_local_config(),
    OperatingMode.OPENROUTER_FREE: get_default_openrouter_free_config(),
    OperatingMode.MIXED: get_default_mixed_config(),
    OperatingMode.WEB: get_default_web_config(),
    OperatingMode.OPENROUTER_PAID: get_default_openrouter_paid_config(),
}


def get_default_config(mode: OperatingMode) -> ModeConfiguration:
    """
    Get default configuration for an operating mode.
    
    Args:
        mode: Operating mode
        
    Returns:
        Default ModeConfiguration for the mode
    """
    return DEFAULT_CONFIGS.get(mode, get_default_mixed_config())
