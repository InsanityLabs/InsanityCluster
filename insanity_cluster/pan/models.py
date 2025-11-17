"""
Data models for PAN layer model integration.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class ModelCapability(str, Enum):
    """Model capabilities."""
    STREAMING = "streaming"
    VISION = "vision"
    LONG_CONTEXT = "long_context"
    FUNCTION_CALLING = "function_calling"
    JSON_MODE = "json_mode"


class ProviderType(str, Enum):
    """AI model provider types."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"
    LM_STUDIO = "lm_studio"


@dataclass
class GenerationParams:
    """Parameters for model generation."""
    max_tokens: int = 1000
    temperature: float = 0.7
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    stop_sequences: Optional[List[str]] = None
    stream: bool = False
    
    # Additional parameters
    system_prompt: Optional[str] = None
    json_mode: bool = False
    timeout: int = 30
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API calls."""
        params = {
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "top_p": self.top_p,
            "stream": self.stream,
        }
        
        if self.frequency_penalty != 0.0:
            params["frequency_penalty"] = self.frequency_penalty
        if self.presence_penalty != 0.0:
            params["presence_penalty"] = self.presence_penalty
        if self.stop_sequences:
            params["stop"] = self.stop_sequences
            
        return params


@dataclass
class PricingInfo:
    """Pricing information for a model."""
    model_name: str
    provider: ProviderType
    input_cost_per_million: float  # Cost per million input tokens
    output_cost_per_million: float  # Cost per million output tokens
    
    # Additional pricing details
    context_window: int = 4096
    supports_streaming: bool = True
    supports_vision: bool = False
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for given token counts."""
        input_cost = (input_tokens / 1_000_000) * self.input_cost_per_million
        output_cost = (output_tokens / 1_000_000) * self.output_cost_per_million
        return input_cost + output_cost


@dataclass
class Response:
    """Response from model generation."""
    content: str
    model: str
    provider: ProviderType
    
    # Token usage
    input_tokens: int
    output_tokens: int
    total_tokens: int
    
    # Metadata
    latency_ms: int
    cost: float
    finish_reason: str = "stop"
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class StreamChunk:
    """A chunk from a streaming response."""
    content: str
    model: str
    provider: ProviderType
    finish_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AdapterError(Exception):
    """Base exception for adapter errors."""
    pass


class APIError(AdapterError):
    """API call failed."""
    def __init__(self, message: str, status_code: Optional[int] = None, provider: Optional[str] = None):
        self.status_code = status_code
        self.provider = provider
        super().__init__(message)


class TimeoutError(AdapterError):
    """Request timed out."""
    pass


class RateLimitError(AdapterError):
    """Rate limit exceeded."""
    def __init__(self, message: str, retry_after: Optional[int] = None):
        self.retry_after = retry_after
        super().__init__(message)


class ModelNotFoundError(AdapterError):
    """Model not found or not available."""
    pass


class AuthenticationError(AdapterError):
    """Authentication failed."""
    pass
