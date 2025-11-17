"""
OpenAI adapter for GPT-5 series models.
"""
import logging
import time
from typing import AsyncIterator, Optional

from openai import AsyncOpenAI, OpenAIError, APITimeoutError, RateLimitError as OpenAIRateLimitError

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


# Pricing information for GPT-5 series (per million tokens)
# Note: These are placeholder prices - update with actual GPT-5 pricing when available
GPT5_PRICING = {
    "gpt-5.1": PricingInfo(
        model_name="gpt-5.1",
        provider=ProviderType.OPENAI,
        input_cost_per_million=1.25,
        output_cost_per_million=5.0,
        context_window=128000,
        supports_streaming=True,
        supports_vision=True,
    ),
    "gpt-5": PricingInfo(
        model_name="gpt-5",
        provider=ProviderType.OPENAI,
        input_cost_per_million=1.0,
        output_cost_per_million=4.0,
        context_window=128000,
        supports_streaming=True,
        supports_vision=True,
    ),
    "gpt-5-mini": PricingInfo(
        model_name="gpt-5-mini",
        provider=ProviderType.OPENAI,
        input_cost_per_million=0.15,
        output_cost_per_million=0.60,
        context_window=128000,
        supports_streaming=True,
        supports_vision=False,
    ),
    "gpt-5-nano": PricingInfo(
        model_name="gpt-5-nano",
        provider=ProviderType.OPENAI,
        input_cost_per_million=0.05,
        output_cost_per_million=0.20,
        context_window=16000,
        supports_streaming=True,
        supports_vision=False,
    ),
    "gpt-5-codex": PricingInfo(
        model_name="gpt-5-codex",
        provider=ProviderType.OPENAI,
        input_cost_per_million=1.0,
        output_cost_per_million=4.0,
        context_window=128000,
        supports_streaming=True,
        supports_vision=False,
    ),
    # Fallback to GPT-4 models for testing
    "gpt-4-turbo-preview": PricingInfo(
        model_name="gpt-4-turbo-preview",
        provider=ProviderType.OPENAI,
        input_cost_per_million=10.0,
        output_cost_per_million=30.0,
        context_window=128000,
        supports_streaming=True,
        supports_vision=True,
    ),
    "gpt-4": PricingInfo(
        model_name="gpt-4",
        provider=ProviderType.OPENAI,
        input_cost_per_million=30.0,
        output_cost_per_million=60.0,
        context_window=8192,
        supports_streaming=True,
        supports_vision=False,
    ),
    "gpt-3.5-turbo": PricingInfo(
        model_name="gpt-3.5-turbo",
        provider=ProviderType.OPENAI,
        input_cost_per_million=0.50,
        output_cost_per_million=1.50,
        context_window=16385,
        supports_streaming=True,
        supports_vision=False,
    ),
}


class OpenAIAdapter(ProviderAdapter):
    """
    Adapter for OpenAI GPT-5 series models.
    
    Supports:
    - gpt-5.1: Most capable model
    - gpt-5: Standard model
    - gpt-5-mini: Fast and efficient
    - gpt-5-nano: Ultra-fast for simple tasks
    - gpt-5-codex: Specialized for code
    """
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize OpenAI adapter.
        
        Args:
            api_key: OpenAI API key
            base_url: Custom base URL (optional)
        """
        super().__init__(api_key, base_url)
        
        self.client = AsyncOpenAI(
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
        Generate a response from OpenAI model.
        
        Args:
            prompt: The input prompt
            model: Model identifier (e.g., "gpt-5-mini")
            params: Generation parameters
            
        Returns:
            Response object with generated content
        """
        if params is None:
            params = GenerationParams()
        
        async def _generate():
            start_time = time.time()
            
            try:
                messages = []
                if params.system_prompt:
                    messages.append({"role": "system", "content": params.system_prompt})
                messages.append({"role": "user", "content": prompt})
                
                # Build request parameters
                request_params = {
                    "model": model,
                    "messages": messages,
                    "max_tokens": params.max_tokens,
                    "temperature": params.temperature,
                    "top_p": params.top_p,
                }
                
                if params.frequency_penalty != 0.0:
                    request_params["frequency_penalty"] = params.frequency_penalty
                if params.presence_penalty != 0.0:
                    request_params["presence_penalty"] = params.presence_penalty
                if params.stop_sequences:
                    request_params["stop"] = params.stop_sequences
                if params.json_mode:
                    request_params["response_format"] = {"type": "json_object"}
                
                # Make API call
                response = await self.client.chat.completions.create(**request_params)
                
                latency_ms = int((time.time() - start_time) * 1000)
                
                # Extract response data
                content = response.choices[0].message.content or ""
                finish_reason = response.choices[0].finish_reason
                
                # Get token usage
                usage = response.usage
                input_tokens = usage.prompt_tokens if usage else self._count_tokens(prompt)
                output_tokens = usage.completion_tokens if usage else self._count_tokens(content)
                total_tokens = usage.total_tokens if usage else input_tokens + output_tokens
                
                # Calculate cost
                pricing = self.get_pricing(model)
                cost = pricing.estimate_cost(input_tokens, output_tokens)
                
                return Response(
                    content=content,
                    model=model,
                    provider=ProviderType.OPENAI,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    latency_ms=latency_ms,
                    cost=cost,
                    finish_reason=finish_reason,
                    metadata={"response_id": response.id}
                )
                
            except OpenAIRateLimitError as e:
                logger.warning(f"OpenAI rate limit exceeded: {e}")
                raise RateLimitError(str(e))
            except APITimeoutError as e:
                logger.error(f"OpenAI request timed out: {e}")
                raise TimeoutError(str(e))
            except OpenAIError as e:
                if "authentication" in str(e).lower() or "api key" in str(e).lower():
                    raise AuthenticationError(f"OpenAI authentication failed: {e}")
                logger.error(f"OpenAI API error: {e}")
                raise APIError(str(e), provider="openai")
            except Exception as e:
                logger.error(f"Unexpected error in OpenAI adapter: {e}")
                raise APIError(f"Unexpected error: {e}", provider="openai")
        
        return await self._retry_with_backoff(_generate)
    
    async def stream_generate(
        self,
        prompt: str,
        model: str,
        params: Optional[GenerationParams] = None
    ) -> AsyncIterator[StreamChunk]:
        """
        Generate a streaming response from OpenAI model.
        
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
            messages = []
            if params.system_prompt:
                messages.append({"role": "system", "content": params.system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # Build request parameters
            request_params = {
                "model": model,
                "messages": messages,
                "max_tokens": params.max_tokens,
                "temperature": params.temperature,
                "top_p": params.top_p,
                "stream": True,
            }
            
            if params.frequency_penalty != 0.0:
                request_params["frequency_penalty"] = params.frequency_penalty
            if params.presence_penalty != 0.0:
                request_params["presence_penalty"] = params.presence_penalty
            if params.stop_sequences:
                request_params["stop"] = params.stop_sequences
            
            # Make streaming API call
            stream = await self.client.chat.completions.create(**request_params)
            
            async for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    choice = chunk.choices[0]
                    content = choice.delta.content or ""
                    finish_reason = choice.finish_reason
                    
                    yield StreamChunk(
                        content=content,
                        model=model,
                        provider=ProviderType.OPENAI,
                        finish_reason=finish_reason,
                        metadata={"chunk_id": chunk.id}
                    )
                    
        except OpenAIRateLimitError as e:
            logger.warning(f"OpenAI rate limit exceeded during streaming: {e}")
            raise RateLimitError(str(e))
        except APITimeoutError as e:
            logger.error(f"OpenAI streaming request timed out: {e}")
            raise TimeoutError(str(e))
        except OpenAIError as e:
            logger.error(f"OpenAI streaming API error: {e}")
            raise APIError(str(e), provider="openai")
        except Exception as e:
            logger.error(f"Unexpected error in OpenAI streaming: {e}")
            raise APIError(f"Unexpected error: {e}", provider="openai")
    
    def get_pricing(self, model: str) -> PricingInfo:
        """
        Get pricing information for an OpenAI model.
        
        Args:
            model: Model identifier
            
        Returns:
            PricingInfo object
        """
        # Return pricing if available, otherwise use gpt-3.5-turbo as fallback
        return GPT5_PRICING.get(model, GPT5_PRICING["gpt-3.5-turbo"])
    
    async def health_check(self) -> bool:
        """
        Check if OpenAI API is available.
        
        Returns:
            True if API is healthy
        """
        try:
            # Make a minimal API call to check health
            await self.client.models.list()
            return True
        except Exception as e:
            logger.error(f"OpenAI health check failed: {e}")
            return False
