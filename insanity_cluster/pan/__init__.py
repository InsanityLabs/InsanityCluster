"""
PAN Layer - Model inference and integration layer.

This layer provides:
- Provider adapters for different AI model services
- Intelligent model routing based on cost, speed, and quality
- Response streaming for realtime output
- Fallback mechanisms for reliability
"""

from .base_adapter import ProviderAdapter
from .models import (
    GenerationParams,
    PricingInfo,
    ProviderType,
    Response,
    StreamChunk,
    APIError,
    TimeoutError,
    RateLimitError,
    ModelNotFoundError,
    AuthenticationError,
)
from .openai_adapter import OpenAIAdapter
from .anthropic_adapter import AnthropicAdapter
from .openrouter_adapter import OpenRouterAdapter
from .ollama_adapter import OllamaAdapter
from .lmstudio_adapter import LMStudioAdapter
from .model_router import ModelRouter, RoutingRequest, RoutingResult
from .router_config import (
    OperatingMode,
    RoutingStrategy,
    AgentType,
    ModeConfiguration,
    AgentModelConfig,
    TaskModelConfig,
    get_default_config,
)
from .response_streamer import ResponseStreamer, StreamUpdate, StreamMultiplexer

__all__ = [
    # Base classes
    "ProviderAdapter",
    
    # Models
    "GenerationParams",
    "PricingInfo",
    "ProviderType",
    "Response",
    "StreamChunk",
    
    # Exceptions
    "APIError",
    "TimeoutError",
    "RateLimitError",
    "ModelNotFoundError",
    "AuthenticationError",
    
    # Adapters
    "OpenAIAdapter",
    "AnthropicAdapter",
    "OpenRouterAdapter",
    "OllamaAdapter",
    "LMStudioAdapter",
    
    # Router
    "ModelRouter",
    "RoutingRequest",
    "RoutingResult",
    
    # Router Configuration
    "OperatingMode",
    "RoutingStrategy",
    "AgentType",
    "ModeConfiguration",
    "AgentModelConfig",
    "TaskModelConfig",
    "get_default_config",
    
    # Streaming
    "ResponseStreamer",
    "StreamUpdate",
    "StreamMultiplexer",
]
