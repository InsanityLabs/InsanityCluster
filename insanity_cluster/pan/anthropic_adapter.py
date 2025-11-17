"""
Anthropic adapter for Claude 4 series models.
"""
import logging
import time
from typing import AsyncIterator, Optional

from anthropic import AsyncAnthropic, APIError as AnthropicAPIError, APITimeoutError, RateLimitError as AnthropicRateLimitError

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
    AuthenticationError,
)

logger = logging.getLogger(__name__)


# Pricing information for Claude 4 series (per million tokens)
# Note: These are placeholder prices - update with actual Claude 4 pricing when available
CLAUDE4_PRICING = {
    "claude-sonnet-4.5": PricingInfo(
        model_name="claude-sonnet-4.5",
        provider=ProviderType.ANTHROPIC,
        input_cost_per_million=3.0,
        output_cost_per_million=15.0,
        context_window=200000,
        supports_streaming=True,
        supports_vision=True,
    ),
    "claude-haiku-4.5": PricingInfo(
        model_name="claude-haiku-4.5",
        provider=ProviderType.ANTHROPIC,
        input_cost_per_million=1.0,
        output_cost_per_million=5.0,
        context_window=200000,
        supports_streaming=True,
        supports_vision=False,
    ),
    "claude-opus-4.1": PricingInfo(
        model_name="claude-opus-4.1",
        provider=ProviderType.ANTHROPIC,
        input_cost_per_million=15.0,
        output_cost_per_million=75.0,
        context_window=200000,
        supports_streaming=True,
        supports_vision=True,
    ),
    # Fallback to Claude 3 models for testing
    "claude-3-opus-20240229": PricingInfo(
        model_name="claude-3-opus-20240229",
        provider=ProviderType.ANTHROPIC,
        input_cost_per_million=15.0,
        output_cost_per_million=75.0,
        context_window=200000,
        supports_streaming=True,
        supports_vision=True,
    ),
    "claude-3-sonnet-20240229": PricingInfo(
        model_name="claude-3-sonnet-20240229",
        provider=ProviderType.ANTHROPIC,
        input_cost_per_million=3.0,
        output_cost_per_million=15.0,
        context_window=200000,
        supports_streaming=True,
        supports_vision=True,
    ),
    "claude-3-haiku-20240307": PricingInfo(
        model_name="claude-3-haiku-20240307",
        provider=ProviderType.ANTHROPIC,
        input_cost_per_million=0.25,
        output_cost_per_million=1.25,
        context_window=200000,
        supports_streaming=True,
        supports_vision=True,
    ),
}


class AnthropicAdapter(ProviderAdapter):
    """
    Adapter for Anthropic Claude 4 series models.
    
    Supports:
    - claude-sonnet-4.5: Balanced performance and cost
    - claude-haiku-4.5: Fast and efficient
    - claude-opus-4.1: Most capable for complex reasoning
    """
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize Anthropic adapter.
        
        Args:
            api_key: Anthropic API key
            base_url: Custom base URL (optional)
        """
        super().__init__(api_key, base_url)
        
        self.client = AsyncAnthropic(
            api_key=api_key,
            base_url=base_url,
        )
        
    async def generate(
        self,
        prompt: str,
        model: str,
        params: Optional[GenerationParams] = None
    ) -> Response:
        """
        Generate a response from Anthropic model.
        
        Args:
            prompt: The input prompt
            model: Model identifier (e.g., "claude-sonnet-4.5")
            params: Generation parameters
            
        Returns:
            Response object with generated content
        """
        if params is None:
            params = GenerationParams()
        
        async def _generate():
            start_time = time.time()
            
            try:
                # Build request parameters
                request_params = {
                    "model": model,
                    "max_tokens": params.max_tokens,
                    "temperature": params.temperature,
                    "top_p": params.top_p,
                    "messages": [{"role": "user", "content": prompt}],
                }
                
                if params.system_prompt:
                    request_params["system"] = params.system_prompt
                
                if params.stop_sequences:
                    request_params["stop_sequences"] = params.stop_sequences
                
                # Make API call
                response = await self.client.messages.create(**request_params)
                
                latency_ms = int((time.time() - start_time) * 1000)
                
                # Extract response data
                content = ""
                if response.content:
                    for block in response.content:
                        if hasattr(block, 'text'):
                            content += block.text
                
                finish_reason = response.stop_reason or "stop"
                
                # Get token usage
                input_tokens = response.usage.input_tokens if response.usage else self._count_tokens(prompt)
                output_tokens = response.usage.output_tokens if response.usage else self._count_tokens(content)
                total_tokens = input_tokens + output_tokens
                
                # Calculate cost
                pricing = self.get_pricing(model)
                cost = pricing.estimate_cost(input_tokens, output_tokens)
                
                return Response(
                    content=content,
                    model=model,
                    provider=ProviderType.ANTHROPIC,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    latency_ms=latency_ms,
                    cost=cost,
                    finish_reason=finish_reason,
                    metadata={"response_id": response.id, "model": response.model}
                )
                
            except AnthropicRateLimitError as e:
                logger.warning(f"Anthropic rate limit exceeded: {e}")
                raise RateLimitError(str(e))
            except APITimeoutError as e:
                logger.error(f"Anthropic request timed out: {e}")
                raise TimeoutError(str(e))
            except AnthropicAPIError as e:
                if "authentication" in str(e).lower() or "api key" in str(e).lower():
                    raise AuthenticationError(f"Anthropic authentication failed: {e}")
                logger.error(f"Anthropic API error: {e}")
                raise APIError(str(e), provider="anthropic")
            except Exception as e:
                logger.error(f"Unexpected error in Anthropic adapter: {e}")
                raise APIError(f"Unexpected error: {e}", provider="anthropic")
        
        return await self._retry_with_backoff(_generate)
    
    async def stream_generate(
        self,
        prompt: str,
        model: str,
        params: Optional[GenerationParams] = None
    ) -> AsyncIterator[StreamChunk]:
        """
        Generate a streaming response from Anthropic model.
        
        Args:
            prompt: The input prompt
            model: Model identifier
            params: Generation parameters
            
        Yields:
            StreamChunk objects with partial content
        """
        if params is None:
            params = GenerationParams(stream=True)
        else:
            params.stream = True
        
        try:
            # Build request parameters
            request_params = {
                "model": model,
                "max_tokens": params.max_tokens,
                "temperature": params.temperature,
                "top_p": params.top_p,
                "messages": [{"role": "user", "content": prompt}],
                "stream": True,
            }
            
            if params.system_prompt:
                request_params["system"] = params.system_prompt
            
            if params.stop_sequences:
                request_params["stop_sequences"] = params.stop_sequences
            
            # Make streaming API call
            async with self.client.messages.stream(**request_params) as stream:
                async for text in stream.text_stream:
                    yield StreamChunk(
                        content=text,
                        model=model,
                        provider=ProviderType.ANTHROPIC,
                        finish_reason=None,
                        metadata={}
                    )
                
                # Get final message for finish reason
                final_message = await stream.get_final_message()
                if final_message:
                    yield StreamChunk(
                        content="",
                        model=model,
                        provider=ProviderType.ANTHROPIC,
                        finish_reason=final_message.stop_reason or "stop",
                        metadata={"response_id": final_message.id}
                    )
                    
        except AnthropicRateLimitError as e:
            logger.warning(f"Anthropic rate limit exceeded during streaming: {e}")
            raise RateLimitError(str(e))
        except APITimeoutError as e:
            logger.error(f"Anthropic streaming request timed out: {e}")
            raise TimeoutError(str(e))
        except AnthropicAPIError as e:
            logger.error(f"Anthropic streaming API error: {e}")
            raise APIError(str(e), provider="anthropic")
        except Exception as e:
            logger.error(f"Unexpected error in Anthropic streaming: {e}")
            raise APIError(f"Unexpected error: {e}", provider="anthropic")
    
    def get_pricing(self, model: str) -> PricingInfo:
        """
        Get pricing information for an Anthropic model.
        
        Args:
            model: Model identifier
            
        Returns:
            PricingInfo object
        """
        # Return pricing if available, otherwise use claude-3-haiku as fallback
        return CLAUDE4_PRICING.get(model, CLAUDE4_PRICING["claude-3-haiku-20240307"])
    
    async def health_check(self) -> bool:
        """
        Check if Anthropic API is available.
        
        Returns:
            True if API is healthy
        """
        try:
            # Make a minimal API call to check health
            # Anthropic doesn't have a dedicated health endpoint, so we make a small request
            await self.client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=10,
                messages=[{"role": "user", "content": "test"}]
            )
            return True
        except Exception as e:
            logger.error(f"Anthropic health check failed: {e}")
            return False
