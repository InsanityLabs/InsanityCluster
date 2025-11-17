"""
OpenRouter adapter for unified access to multiple model providers.
"""
import logging
import time
from typing import AsyncIterator, Dict, Optional

import httpx

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


# Common OpenRouter model pricing (per million tokens)
# OpenRouter provides access to many models with unified API
OPENROUTER_PRICING = {
    # Free tier models
    "free": PricingInfo(
        model_name="openrouter/free",
        provider=ProviderType.OPENROUTER,
        input_cost_per_million=0.0,
        output_cost_per_million=0.0,
        context_window=4096,
        supports_streaming=True,
        supports_vision=False,
    ),
    # Paid tier - examples (actual pricing varies by model)
    "anthropic/claude-3-opus": PricingInfo(
        model_name="anthropic/claude-3-opus",
        provider=ProviderType.OPENROUTER,
        input_cost_per_million=15.0,
        output_cost_per_million=75.0,
        context_window=200000,
        supports_streaming=True,
        supports_vision=True,
    ),
    "anthropic/claude-3-sonnet": PricingInfo(
        model_name="anthropic/claude-3-sonnet",
        provider=ProviderType.OPENROUTER,
        input_cost_per_million=3.0,
        output_cost_per_million=15.0,
        context_window=200000,
        supports_streaming=True,
        supports_vision=True,
    ),
    "openai/gpt-4-turbo": PricingInfo(
        model_name="openai/gpt-4-turbo",
        provider=ProviderType.OPENROUTER,
        input_cost_per_million=10.0,
        output_cost_per_million=30.0,
        context_window=128000,
        supports_streaming=True,
        supports_vision=True,
    ),
    "openai/gpt-3.5-turbo": PricingInfo(
        model_name="openai/gpt-3.5-turbo",
        provider=ProviderType.OPENROUTER,
        input_cost_per_million=0.5,
        output_cost_per_million=1.5,
        context_window=16385,
        supports_streaming=True,
        supports_vision=False,
    ),
}


class OpenRouterAdapter(ProviderAdapter):
    """
    Adapter for OpenRouter unified API.
    
    OpenRouter provides access to multiple model providers through
    a single API, supporting both free and paid tiers.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://openrouter.ai/api/v1",
        app_name: Optional[str] = None,
        site_url: Optional[str] = None
    ):
        """
        Initialize OpenRouter adapter.
        
        Args:
            api_key: OpenRouter API key
            base_url: OpenRouter API base URL
            app_name: Application name for OpenRouter headers
            site_url: Site URL for OpenRouter headers
        """
        super().__init__(api_key, base_url)
        
        self.app_name = app_name or "Insanity Cluster"
        self.site_url = site_url or "https://github.com/insanity-cluster"
        
        # Rate limiting state
        self._rate_limit_remaining: Optional[int] = None
        self._rate_limit_reset: Optional[int] = None
        
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for OpenRouter API requests."""
        headers = {
            "Content-Type": "application/json",
            "HTTP-Referer": self.site_url,
            "X-Title": self.app_name,
        }
        
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        return headers
    
    def _update_rate_limits(self, response_headers: httpx.Headers):
        """Update rate limit state from response headers."""
        if "x-ratelimit-remaining" in response_headers:
            self._rate_limit_remaining = int(response_headers["x-ratelimit-remaining"])
        if "x-ratelimit-reset" in response_headers:
            self._rate_limit_reset = int(response_headers["x-ratelimit-reset"])
    
    async def generate(
        self,
        prompt: str,
        model: str,
        params: Optional[GenerationParams] = None
    ) -> Response:
        """
        Generate a response from OpenRouter model.
        
        Args:
            prompt: The input prompt
            model: Model identifier (e.g., "anthropic/claude-3-sonnet")
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
                
                # Build request payload
                payload = {
                    "model": model,
                    "messages": messages,
                    "max_tokens": params.max_tokens,
                    "temperature": params.temperature,
                    "top_p": params.top_p,
                }
                
                if params.frequency_penalty != 0.0:
                    payload["frequency_penalty"] = params.frequency_penalty
                if params.presence_penalty != 0.0:
                    payload["presence_penalty"] = params.presence_penalty
                if params.stop_sequences:
                    payload["stop"] = params.stop_sequences
                
                # Make API call
                async with httpx.AsyncClient(timeout=params.timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=self._get_headers(),
                        json=payload
                    )
                    
                    # Update rate limits
                    self._update_rate_limits(response.headers)
                    
                    # Handle errors
                    if response.status_code == 429:
                        retry_after = response.headers.get("retry-after")
                        raise RateLimitError(
                            "OpenRouter rate limit exceeded",
                            retry_after=int(retry_after) if retry_after else None
                        )
                    elif response.status_code == 401:
                        raise AuthenticationError("OpenRouter authentication failed")
                    elif response.status_code >= 400:
                        error_data = response.json() if response.content else {}
                        error_msg = error_data.get("error", {}).get("message", response.text)
                        raise APIError(
                            f"OpenRouter API error: {error_msg}",
                            status_code=response.status_code,
                            provider="openrouter"
                        )
                    
                    data = response.json()
                
                latency_ms = int((time.time() - start_time) * 1000)
                
                # Extract response data
                content = data["choices"][0]["message"]["content"]
                finish_reason = data["choices"][0].get("finish_reason", "stop")
                
                # Get token usage
                usage = data.get("usage", {})
                input_tokens = usage.get("prompt_tokens", self._count_tokens(prompt))
                output_tokens = usage.get("completion_tokens", self._count_tokens(content))
                total_tokens = usage.get("total_tokens", input_tokens + output_tokens)
                
                # Calculate cost
                pricing = self.get_pricing(model)
                cost = pricing.estimate_cost(input_tokens, output_tokens)
                
                return Response(
                    content=content,
                    model=model,
                    provider=ProviderType.OPENROUTER,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    latency_ms=latency_ms,
                    cost=cost,
                    finish_reason=finish_reason,
                    metadata={
                        "response_id": data.get("id"),
                        "rate_limit_remaining": self._rate_limit_remaining
                    }
                )
                
            except httpx.TimeoutException as e:
                logger.error(f"OpenRouter request timed out: {e}")
                raise TimeoutError(str(e))
            except httpx.HTTPError as e:
                logger.error(f"OpenRouter HTTP error: {e}")
                raise APIError(str(e), provider="openrouter")
            except (RateLimitError, AuthenticationError, APIError):
                raise
            except Exception as e:
                logger.error(f"Unexpected error in OpenRouter adapter: {e}")
                raise APIError(f"Unexpected error: {e}", provider="openrouter")
        
        return await self._retry_with_backoff(_generate)
    
    async def stream_generate(
        self,
        prompt: str,
        model: str,
        params: Optional[GenerationParams] = None
    ) -> AsyncIterator[StreamChunk]:
        """
        Generate a streaming response from OpenRouter model.
        
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
            
            # Build request payload
            payload = {
                "model": model,
                "messages": messages,
                "max_tokens": params.max_tokens,
                "temperature": params.temperature,
                "top_p": params.top_p,
                "stream": True,
            }
            
            if params.frequency_penalty != 0.0:
                payload["frequency_penalty"] = params.frequency_penalty
            if params.presence_penalty != 0.0:
                payload["presence_penalty"] = params.presence_penalty
            if params.stop_sequences:
                payload["stop"] = params.stop_sequences
            
            # Make streaming API call
            async with httpx.AsyncClient(timeout=params.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    headers=self._get_headers(),
                    json=payload
                ) as response:
                    # Handle errors
                    if response.status_code == 429:
                        raise RateLimitError("OpenRouter rate limit exceeded")
                    elif response.status_code == 401:
                        raise AuthenticationError("OpenRouter authentication failed")
                    elif response.status_code >= 400:
                        raise APIError(
                            f"OpenRouter streaming error: {response.status_code}",
                            status_code=response.status_code,
                            provider="openrouter"
                        )
                    
                    # Process SSE stream
                    async for line in response.aiter_lines():
                        if not line or line.startswith(":"):
                            continue
                        
                        if line.startswith("data: "):
                            data_str = line[6:]  # Remove "data: " prefix
                            
                            if data_str == "[DONE]":
                                break
                            
                            try:
                                import json
                                data = json.loads(data_str)
                                
                                if "choices" in data and len(data["choices"]) > 0:
                                    choice = data["choices"][0]
                                    delta = choice.get("delta", {})
                                    content = delta.get("content", "")
                                    finish_reason = choice.get("finish_reason")
                                    
                                    yield StreamChunk(
                                        content=content,
                                        model=model,
                                        provider=ProviderType.OPENROUTER,
                                        finish_reason=finish_reason,
                                        metadata={"chunk_id": data.get("id")}
                                    )
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse SSE data: {data_str}")
                                continue
                    
        except httpx.TimeoutException as e:
            logger.error(f"OpenRouter streaming request timed out: {e}")
            raise TimeoutError(str(e))
        except httpx.HTTPError as e:
            logger.error(f"OpenRouter streaming HTTP error: {e}")
            raise APIError(str(e), provider="openrouter")
        except (RateLimitError, AuthenticationError, APIError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error in OpenRouter streaming: {e}")
            raise APIError(f"Unexpected error: {e}", provider="openrouter")
    
    def get_pricing(self, model: str) -> PricingInfo:
        """
        Get pricing information for an OpenRouter model.
        
        Args:
            model: Model identifier
            
        Returns:
            PricingInfo object
        """
        # Return pricing if available, otherwise use free tier as fallback
        return OPENROUTER_PRICING.get(model, OPENROUTER_PRICING["free"])
    
    async def health_check(self) -> bool:
        """
        Check if OpenRouter API is available.
        
        Returns:
            True if API is healthy
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers=self._get_headers()
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"OpenRouter health check failed: {e}")
            return False
    
    async def list_models(self) -> list:
        """
        List available models on OpenRouter.
        
        Returns:
            List of available model identifiers
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.base_url}/models",
                    headers=self._get_headers()
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return [model["id"] for model in data.get("data", [])]
                else:
                    logger.error(f"Failed to list models: {response.status_code}")
                    return []
        except Exception as e:
            logger.error(f"Error listing OpenRouter models: {e}")
            return []
