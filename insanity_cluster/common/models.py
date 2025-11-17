"""
Shared data models used across all layers
"""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class AgentType(Enum):
    """Types of specialized agents"""
    BUSINESS = "business"
    DEVELOPER = "developer"
    COMMUNICATION = "communication"
    RESEARCH = "research"
    CREATIVE = "creative"
    FINANCE = "finance"
    PROJECT_MANAGER = "project_manager"


class ResultStatus(Enum):
    """Status of agent execution results"""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


class RoutingMode(Enum):
    """Model routing strategies"""
    SPEED_FIRST = "speed_first"
    QUALITY_FIRST = "quality_first"
    COST_OPTIMIZED = "cost_optimized"
    TASK_SPECIFIC = "task_specific"


class PrivacyLevel(Enum):
    """Privacy levels for model selection"""
    LOCAL_ONLY = "local_only"
    EXTERNAL_OK = "external_ok"


class OperatingMode(Enum):
    """System operating modes"""
    LOCAL = "local"
    OPENROUTER_FREE = "openrouter_free"
    MIXED = "mixed"
    WEB = "web"
    OPENROUTER_PAID = "openrouter_paid"


@dataclass
class ParsedCommand:
    """Parsed natural language command"""
    intent: str
    parameters: Dict[str, Any]
    confidence: float
    user_id: str
    timestamp: datetime


@dataclass
class Subtask:
    """Individual subtask in a task graph"""
    id: str
    description: str
    agent_type: AgentType
    dependencies: List[str]
    priority: int
    estimated_cost: float
    estimated_duration: timedelta


@dataclass
class TaskGraph:
    """Directed acyclic graph of subtasks"""
    root_task_id: str
    subtasks: List[Subtask]
    dependencies: Dict[str, List[str]]
    
    def get_executable_subtasks(self, completed: Set[str]) -> List[Subtask]:
        """Get subtasks ready for execution"""
        executable = []
        for subtask in self.subtasks:
            if subtask.id not in completed:
                deps_met = all(dep in completed for dep in subtask.dependencies)
                if deps_met:
                    executable.append(subtask)
        return executable


@dataclass
class AgentResult:
    """Result from agent execution"""
    subtask_id: str
    status: ResultStatus
    output: Any
    cost: float
    latency_ms: int
    model_used: str
    validation_score: float


@dataclass
class ModelStrategy:
    """Strategy for model selection"""
    routing_mode: RoutingMode
    max_cost: Optional[float] = None
    max_latency_ms: Optional[int] = None
    required_capabilities: List[str] = field(default_factory=list)
    privacy_level: PrivacyLevel = PrivacyLevel.EXTERNAL_OK


@dataclass
class InferenceRequest:
    """Request for model inference"""
    prompt: str
    model_strategy: ModelStrategy
    streaming: bool
    max_tokens: int
    temperature: float
    context: Optional[Dict[str, Any]] = None
