"""
Model Router for intelligent model selection and routing.
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .base_adapter import ProviderAdapter
from .models import PricingInfo, ProviderType
from .router_config import (
    AgentType,
    ModeConfiguration,
    OperatingMode,
    RoutingStrategy,
    get_default_config,
)

logger = logging.getLogger(__name__)


@dataclass
class RoutingRequest:
    """Request for model routing."""
    task_description: str
    agent_type: Optional[AgentType] = None
    task_type: Optional[str] = None
    complexity: float = 0.5  # 0.0 = simple, 1.0 = complex
    required_capabilities: List[str] = field(default_factory=list)
    max_cost: Optional[float] = None
    max_latency_ms: Optional[int] = None


@dataclass
class RoutingResult:
    """Result of model routing."""
    model: str
    provider: ProviderType
    adapter: ProviderAdapter
    estimated_cost: float
    fallback_chain: List[Tuple[str, ProviderType]]
    reasoning: str


class ModelRouter:
    """
    Intelligent model router that selects optimal models based on
    operating mode, routing strategy, and task requirements.
    """
    
    def __init__(
        self,
        config: Optional[ModeConfiguration] = None,
        adapters: Optional[Dict[ProviderType, ProviderAdapter]] = None
    ):
        """
        Initialize Model Router.
        
        Args:
            config: Mode configuration (defaults to MIXED mode)
            adapters: Dictionary of provider adapters
        """
        self.config = config or get_default_config(OperatingMode.MIXED)
        self.adapters = adapters or {}
        
        # Track daily costs
        self._daily_cost = 0.0
        
    def set_config(self, config: ModeConfiguration):
        """Update router configuration."""
        self.config = config
        
    def register_adapter(self, provider: ProviderType, adapter: ProviderAdapter):
        """Register a provider adapter."""
        self.adapters[provider] = adapter
        
    async def route(self, request: RoutingRequest) -> RoutingResult:
        """
        Route a request to the optimal model.
        
        Args:
            request: Routing request with task details
            
        Returns:
            RoutingResult with selected model and fallback chain
        """
        # Check daily cost limit
        if self.config.max_cost_per_day is not None:
            if self._daily_cost >= self.config.max_cost_per_day:
                logger.warning(f"Daily cost limit reached: ${self._daily_cost:.2f}")
                # Fall back to free models
                return await self._route_free_only(request)
        
        # Get strategy (check for overrides)
        strategy = self._get_strategy(request)
        
        # Route based on operating mode
        if self.config.mode == OperatingMode.LOCAL:
            return await self._route_local(request, strategy)
        elif self.config.mode == OperatingMode.OPENROUTER_FREE:
            return await self._route_openrouter_free(request, strategy)
        elif self.config.mode == OperatingMode.MIXED:
            return await self._route_mixed(request, strategy)
        elif self.config.mode == OperatingMode.WEB:
            return await self._route_web(request, strategy)
        elif self.config.mode == OperatingMode.OPENROUTER_PAID:
            return await self._route_openrouter_paid(request, strategy)
        else:
            raise ValueError(f"Unknown operating mode: {self.config.mode}")
    
    def _get_strategy(self, request: RoutingRequest) -> RoutingStrategy:
        """Get routing strategy for request (check for overrides)."""
        # Check task type override
        if request.task_type and request.task_type in self.config.task_type_overrides:
            override = self.config.task_type_overrides[request.task_type]
            if override.strategy_override:
                return override.strategy_override
        
        return self.config.default_strategy
    
    async def _route_local(
        self,
        request: RoutingRequest,
        strategy: RoutingStrategy
    ) -> RoutingResult:
        """Route to local models only."""
        # Get preferred models for agent
        preferred = self._get_preferred_models(request.agent_type, local_only=True)
        
        if strategy == RoutingStrategy.SPEED_FIRST:
            model = preferred[0] if preferred else "mistral"
            fallback = ["phi3", "llama3"]
        elif strategy == RoutingStrategy.QUALITY_FIRST:
            model = "llama3:70b" if "llama3:70b" in preferred else "llama3"
            fallback = ["mixtral", "codellama"]
        elif strategy == RoutingStrategy.TASK_SPECIFIC:
            model = self._select_task_specific_local(request)
            fallback = preferred[:3] if preferred else ["mistral", "llama3"]
        else:  # COST_OPTIMIZED
            model = "phi3" if request.complexity < 0.3 else "mistral"
            fallback = ["llama3", "codellama"]
        
        # Check for model override
        if request.task_type and request.task_type in self.config.task_type_overrides:
            override = self.config.task_type_overrides[request.task_type]
            if override.model_override:
                model = override.model_override
        
        provider = ProviderType.OLLAMA
        adapter = self.adapters.get(provider)
        
        if not adapter:
            raise ValueError(f"No adapter registered for {provider}")
        
        return RoutingResult(
            model=model,
            provider=provider,
            adapter=adapter,
            estimated_cost=0.0,
            fallback_chain=[(m, provider) for m in fallback],
            reasoning=f"Local mode: selected {model} for {strategy.value} strategy"
        )
    
    async def _route_openrouter_free(
        self,
        request: RoutingRequest,
        strategy: RoutingStrategy
    ) -> RoutingResult:
        """Route to free OpenRouter models only."""
        model = "free"  # OpenRouter free tier
        provider = ProviderType.OPENROUTER
        adapter = self.adapters.get(provider)
        
        if not adapter:
            raise ValueError(f"No adapter registered for {provider}")
        
        return RoutingResult(
            model=model,
            provider=provider,
            adapter=adapter,
            estimated_cost=0.0,
            fallback_chain=[],
            reasoning="OpenRouter Free mode: using free tier models"
        )
    
    async def _route_mixed(
        self,
        request: RoutingRequest,
        strategy: RoutingStrategy
    ) -> RoutingResult:
        """Route with hybrid local/paid strategy."""
        # Check if we should use local based on complexity
        use_local = request.complexity < self.config.local_complexity_threshold
        
        # Check task type override
        if request.task_type and request.task_type in self.config.task_type_overrides:
            override = self.config.task_type_overrides[request.task_type]
            if not override.allow_paid:
                use_local = True
            elif not override.allow_local:
                use_local = False
        
        if use_local:
            return await self._route_local(request, strategy)
        else:
            return await self._route_web(request, strategy)
    
    async def _route_web(
        self,
        request: RoutingRequest,
        strategy: RoutingStrategy
    ) -> RoutingResult:
        """Route to premium paid models."""
        # Get preferred models for agent
        preferred = self._get_preferred_models(request.agent_type, local_only=False)
        
        if strategy == RoutingStrategy.SPEED_FIRST:
            model = "claude-haiku-4.5"
            provider = ProviderType.ANTHROPIC
            fallback = [
                ("gpt-5-mini", ProviderType.OPENAI),
                ("claude-sonnet-4.5", ProviderType.ANTHROPIC),
            ]
        elif strategy == RoutingStrategy.QUALITY_FIRST:
            model = "claude-opus-4.1"
            provider = ProviderType.ANTHROPIC
            fallback = [
                ("gpt-5.1", ProviderType.OPENAI),
                ("claude-sonnet-4.5", ProviderType.ANTHROPIC),
            ]
        elif strategy == RoutingStrategy.TASK_SPECIFIC:
            model, provider = self._select_task_specific_paid(request)
            fallback = [
                ("claude-sonnet-4.5", ProviderType.ANTHROPIC),
                ("gpt-5", ProviderType.OPENAI),
            ]
        else:  # COST_OPTIMIZED
            if request.complexity < 0.3:
                model = "gpt-5-nano"
                provider = ProviderType.OPENAI
            elif request.complexity < 0.7:
                model = "claude-haiku-4.5"
                provider = ProviderType.ANTHROPIC
            else:
                model = "claude-sonnet-4.5"
                provider = ProviderType.ANTHROPIC
            
            fallback = [
                ("gpt-5-mini", ProviderType.OPENAI),
                ("claude-haiku-4.5", ProviderType.ANTHROPIC),
            ]
        
        # Use preferred models if specified
        if preferred:
            model = preferred[0]
            provider = self._get_provider_for_model(model)
            fallback = [(m, self._get_provider_for_model(m)) for m in preferred[1:3]]
        
        # Check for model override
        if request.task_type and request.task_type in self.config.task_type_overrides:
            override = self.config.task_type_overrides[request.task_type]
            if override.model_override:
                model = override.model_override
                provider = self._get_provider_for_model(model)
        
        adapter = self.adapters.get(provider)
        if not adapter:
            raise ValueError(f"No adapter registered for {provider}")
        
        # Estimate cost
        estimated_cost = self._estimate_cost(model, provider, request)
        
        return RoutingResult(
            model=model,
            provider=provider,
            adapter=adapter,
            estimated_cost=estimated_cost,
            fallback_chain=fallback,
            reasoning=f"Web mode: selected {model} for {strategy.value} strategy"
        )
    
    async def _route_openrouter_paid(
        self,
        request: RoutingRequest,
        strategy: RoutingStrategy
    ) -> RoutingResult:
        """Route through OpenRouter with paid models."""
        # Similar to web mode but all through OpenRouter
        if strategy == RoutingStrategy.SPEED_FIRST:
            model = "anthropic/claude-haiku-4.5"
        elif strategy == RoutingStrategy.QUALITY_FIRST:
            model = "anthropic/claude-opus-4.1"
        elif strategy == RoutingStrategy.TASK_SPECIFIC:
            model = self._select_task_specific_openrouter(request)
        else:  # COST_OPTIMIZED
            if request.complexity < 0.3:
                model = "openai/gpt-5-nano"
            elif request.complexity < 0.7:
                model = "anthropic/claude-haiku-4.5"
            else:
                model = "anthropic/claude-sonnet-4.5"
        
        provider = ProviderType.OPENROUTER
        adapter = self.adapters.get(provider)
        
        if not adapter:
            raise ValueError(f"No adapter registered for {provider}")
        
        estimated_cost = self._estimate_cost(model, provider, request)
        
        return RoutingResult(
            model=model,
            provider=provider,
            adapter=adapter,
            estimated_cost=estimated_cost,
            fallback_chain=[
                ("anthropic/claude-sonnet-4.5", provider),
                ("openai/gpt-5", provider),
            ],
            reasoning=f"OpenRouter Paid mode: selected {model}"
        )
    
    async def _route_free_only(self, request: RoutingRequest) -> RoutingResult:
        """Fallback to free models when cost limit reached."""
        # Try local first
        if ProviderType.OLLAMA in self.adapters:
            return await self._route_local(request, RoutingStrategy.SPEED_FIRST)
        elif ProviderType.OPENROUTER in self.adapters:
            return await self._route_openrouter_free(request, RoutingStrategy.SPEED_FIRST)
        else:
            raise ValueError("No free model providers available")
    
    def _get_preferred_models(
        self,
        agent_type: Optional[AgentType],
        local_only: bool = False
    ) -> List[str]:
        """Get preferred models for an agent type."""
        if not agent_type or agent_type not in self.config.agent_overrides:
            return []
        
        models = self.config.agent_overrides[agent_type].preferred_models
        
        if local_only:
            # Filter to only local models
            local_models = ["llama3", "mistral", "phi3", "codellama", "mixtral"]
            return [m for m in models if any(lm in m for lm in local_models)]
        
        return models
    
    def _select_task_specific_local(self, request: RoutingRequest) -> str:
        """Select optimal local model for task type."""
        if request.task_type == "code_generation":
            return "codellama"
        elif request.task_type == "simple_chat":
            return "phi3"
        elif request.complexity > 0.7:
            return "llama3:70b"
        else:
            return "mistral"
    
    def _select_task_specific_paid(
        self,
        request: RoutingRequest
    ) -> Tuple[str, ProviderType]:
        """Select optimal paid model for task type."""
        if request.task_type == "code_generation":
            return "claude-sonnet-4.5", ProviderType.ANTHROPIC
        elif request.task_type == "contract_review":
            return "claude-opus-4.1", ProviderType.ANTHROPIC
        elif request.task_type == "simple_chat":
            return "gpt-5-mini", ProviderType.OPENAI
        else:
            return "claude-sonnet-4.5", ProviderType.ANTHROPIC
    
    def _select_task_specific_openrouter(self, request: RoutingRequest) -> str:
        """Select optimal OpenRouter model for task type."""
        if request.task_type == "code_generation":
            return "anthropic/claude-sonnet-4.5"
        elif request.task_type == "contract_review":
            return "anthropic/claude-opus-4.1"
        else:
            return "anthropic/claude-sonnet-4.5"
    
    def _get_provider_for_model(self, model: str) -> ProviderType:
        """Determine provider type from model name."""
        if "claude" in model.lower():
            return ProviderType.ANTHROPIC
        elif "gpt" in model.lower():
            return ProviderType.OPENAI
        elif "/" in model:  # OpenRouter format
            return ProviderType.OPENROUTER
        else:
            return ProviderType.OLLAMA
    
    def _estimate_cost(
        self,
        model: str,
        provider: ProviderType,
        request: RoutingRequest
    ) -> float:
        """Estimate cost for a request."""
        adapter = self.adapters.get(provider)
        if not adapter:
            return 0.0
        
        pricing = adapter.get_pricing(model)
        
        # Estimate token counts (rough approximation)
        input_tokens = len(request.task_description.split()) * 1.3
        output_tokens = 500  # Assume average response
        
        return pricing.estimate_cost(int(input_tokens), int(output_tokens))
    
    def track_cost(self, cost: float):
        """Track cost for daily limit enforcement."""
        self._daily_cost += cost
        logger.info(f"Daily cost: ${self._daily_cost:.4f}")
    
    def reset_daily_cost(self):
        """Reset daily cost counter (call at midnight)."""
        self._daily_cost = 0.0
        logger.info("Daily cost counter reset")
    
    def get_fallback_chain(
        self,
        primary_model: str,
        primary_provider: ProviderType
    ) -> List[Tuple[str, ProviderType]]:
        """
        Get fallback chain for a model.
        
        Args:
            primary_model: Primary model that failed
            primary_provider: Primary provider
            
        Returns:
            List of (model, provider) tuples for fallback
        """
        # Build fallback chain based on mode
        if self.config.mode == OperatingMode.LOCAL:
            return [
                ("mistral", ProviderType.OLLAMA),
                ("llama3", ProviderType.OLLAMA),
                ("phi3", ProviderType.OLLAMA),
            ]
        elif self.config.mode == OperatingMode.WEB:
            if primary_provider == ProviderType.ANTHROPIC:
                return [
                    ("gpt-5", ProviderType.OPENAI),
                    ("claude-sonnet-4.5", ProviderType.ANTHROPIC),
                ]
            else:
                return [
                    ("claude-sonnet-4.5", ProviderType.ANTHROPIC),
                    ("gpt-5", ProviderType.OPENAI),
                ]
        else:
            # Mixed or other modes
            return [
                ("claude-haiku-4.5", ProviderType.ANTHROPIC),
                ("gpt-5-mini", ProviderType.OPENAI),
                ("mistral", ProviderType.OLLAMA),
            ]
