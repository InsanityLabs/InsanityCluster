"""
Configuration models for Model Router.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


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
class AgentModelConfig:
    """
    Model configuration for a specific agent.
    """
    preferred_models: List[str] = field(default_factory=list)
    fallback_to_paid: bool = True
    max_cost: Optional[float] = None
    
    def __post_init__(self):
        """Validate configuration."""
        if self.max_cost is not None and self.max_cost < 0:
            raise ValueError("max_cost must be non-negative")


@dataclass
class TaskModelConfig:
    """
    Model configuration for a specific task type.
    """
    model_override: Optional[str] = None
    strategy_override: Optional[RoutingStrategy] = None
    allow_local: bool = True
    allow_paid: bool = True
    
    def __post_init__(self):
        """Validate configuration."""
        if not self.allow_local and not self.allow_paid:
            raise ValueError("At least one of allow_local or allow_paid must be True")


@dataclass
class ModeConfiguration:
    """
    Complete configuration for an operating mode.
    """
    mode: OperatingMode
    default_strategy: RoutingStrategy = RoutingStrategy.COST_OPTIMIZED
    
    # Cost limits
    max_cost_per_task: Optional[float] = None
    max_cost_per_day: Optional[float] = None
    
    # Mixed mode settings
    local_complexity_threshold: float = 0.5
    paid_model_trigger: str = "complexity"  # "complexity", "failure", "explicit"
    
    # Per-agent overrides
    agent_overrides: Dict[AgentType, AgentModelConfig] = field(default_factory=dict)
    
    # Per-task-type overrides
    task_type_overrides: Dict[str, TaskModelConfig] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate configuration."""
        if self.local_complexity_threshold < 0 or self.local_complexity_threshold > 1:
            raise ValueError("local_complexity_threshold must be between 0 and 1")
        
        if self.max_cost_per_task is not None and self.max_cost_per_task < 0:
            raise ValueError("max_cost_per_task must be non-negative")
        
        if self.max_cost_per_day is not None and self.max_cost_per_day < 0:
            raise ValueError("max_cost_per_day must be non-negative")
        
        if self.paid_model_trigger not in ["complexity", "failure", "explicit"]:
            raise ValueError("paid_model_trigger must be 'complexity', 'failure', or 'explicit'")


# Default configurations for each mode
DEFAULT_CONFIGS = {
    OperatingMode.LOCAL: ModeConfiguration(
        mode=OperatingMode.LOCAL,
        default_strategy=RoutingStrategy.SPEED_FIRST,
        max_cost_per_task=0.0,
        max_cost_per_day=0.0,
        agent_overrides={
            AgentType.DEVELOPER: AgentModelConfig(
                preferred_models=["codellama", "llama3:70b"],
                fallback_to_paid=False,
            ),
            AgentType.COMMUNICATION: AgentModelConfig(
                preferred_models=["mistral", "phi3"],
                fallback_to_paid=False,
            ),
        },
    ),
    
    OperatingMode.OPENROUTER_FREE: ModeConfiguration(
        mode=OperatingMode.OPENROUTER_FREE,
        default_strategy=RoutingStrategy.SPEED_FIRST,
        max_cost_per_task=0.0,
        max_cost_per_day=0.0,
    ),
    
    OperatingMode.MIXED: ModeConfiguration(
        mode=OperatingMode.MIXED,
        default_strategy=RoutingStrategy.COST_OPTIMIZED,
        max_cost_per_day=50.0,
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
        },
    ),
    
    OperatingMode.WEB: ModeConfiguration(
        mode=OperatingMode.WEB,
        default_strategy=RoutingStrategy.QUALITY_FIRST,
        max_cost_per_day=100.0,
        agent_overrides={
            AgentType.DEVELOPER: AgentModelConfig(
                preferred_models=["claude-sonnet-4.5", "gpt-5-codex"],
                max_cost=2.0,
            ),
            AgentType.BUSINESS: AgentModelConfig(
                preferred_models=["claude-opus-4.1", "gpt-5.1"],
                max_cost=5.0,
            ),
        },
    ),
    
    OperatingMode.OPENROUTER_PAID: ModeConfiguration(
        mode=OperatingMode.OPENROUTER_PAID,
        default_strategy=RoutingStrategy.COST_OPTIMIZED,
        max_cost_per_day=75.0,
    ),
}


def get_default_config(mode: OperatingMode) -> ModeConfiguration:
    """
    Get default configuration for an operating mode.
    
    Args:
        mode: Operating mode
        
    Returns:
        Default ModeConfiguration for the mode
    """
    return DEFAULT_CONFIGS.get(mode, DEFAULT_CONFIGS[OperatingMode.MIXED])
