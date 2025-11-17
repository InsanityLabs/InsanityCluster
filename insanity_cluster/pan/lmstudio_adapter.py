"""
LM Studio adapter for local model inference.
"""
import logging
import time
from typing import AsyncIterator, Dict, List, Optional

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
    ModelNotFoundError,
)

logger = logging.getLogger(__name__)


class LMStudioAdapter(ProviderAdapter):
    """
    Adapter for LM Studio local model inference.
    
    LM Studio provides an OpenAI-compatible API for running
    local models with a user-friendly interface.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "http://localhost:1234/v1"
    ):
        """
        Initialize LM Studio adapter.
        
        Args:
            api_key: Not used for LM Studio (local)
            base_url: LM Studio API endpoint
        """
        super().__init__(api_key, base_url)
        
    async def generate(
        self,
        prompt: str,
        model: str,
        params: Optional[GenerationParams] = None
    ) -> Response:
        """
        Generate a response from LM Studio model.
        
        Args:
            prompt: The input prompt
            model: Model identifier (or "local-model" for default)
            params: Generation parameters
            
        Returns:
            Response object with generated content
        """
        if params is None:
            params = GenerationParams()
        
        start_time = time.time()
        
        try:
            messages = []
            if params.system_prompt:
                messages.append({"role": "system", "content": params.system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            # Build request payload (OpenAI-compatible)
            payload = {
                "model": model,
                "messages": messages,
                "max_tokens": params.max_tokens,
                "temperature": params.temperature,
                "top_p": params.top_p,
                "stream": False,
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
                    json=payload
                )
                
                if response.status_code == 404:
                    raise ModelNotFoundError(f"Model '{model}' not found in LM Studio")
                elif response.status_code >= 400:
                    raise APIError(
                        f"LM Studio API error: {response.text}",
                        status_code=response.status_code,
                        provider="lm_studio"
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
            
            return Response(
                content=content,
                model=model,
                provider=ProviderType.LM_STUDIO,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                cost=0.0,  # Local models are free
                finish_reason=finish_reason,
                metadata={"response_id": data.get("id")}
            )
            
        except httpx.TimeoutException as e:
            logger.error(f"LM Studio request timed out: {e}")
            raise TimeoutError(str(e))
        except httpx.HTTPError as e:
            logger.error(f"LM Studio HTTP error: {e}")
            raise APIError(str(e), provider="lm_studio")
        except (ModelNotFoundError, APIError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error in LM Studio adapter: {e}")
            raise APIError(f"Unexpected error: {e}", provider="lm_studio")
    
    async def stream_generate(
        self,
        prompt: str,
        model: str,
        params: Optional[GenerationParams] = None
    ) -> AsyncIterator[StreamChunk]:
        """
        Generate a streaming response from LM Studio model.
        
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
                    json=payload
                ) as response:
                    if response.status_code == 404:
                        raise ModelNotFoundError(f"Model '{model}' not found in LM Studio")
                    elif response.status_code >= 400:
                        raise APIError(
                            f"LM Studio streaming error: {response.status_code}",
                            status_code=response.status_code,
                            provider="lm_studio"
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
                                        provider=ProviderType.LM_STUDIO,
                                        finish_reason=finish_reason,
                                        metadata={"chunk_id": data.get("id")}
                                    )
                            except json.JSONDecodeError:
                                logger.warning(f"Failed to parse SSE data: {data_str}")
                                continue
                    
        except httpx.TimeoutException as e:
            logger.error(f"LM Studio streaming request timed out: {e}")
            raise TimeoutError(str(e))
        except httpx.HTTPError as e:
            logger.error(f"LM Studio streaming HTTP error: {e}")
            raise APIError(str(e), provider="lm_studio")
        except (ModelNotFoundError, APIError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error in LM Studio streaming: {e}")
            raise APIError(f"Unexpected error: {e}", provider="lm_studio")
    
    def get_pricing(self, model: str) -> PricingInfo:
        """
        Get pricing information for an LM Studio model.
        
        Args:
            model: Model identifier
            
        Returns:
            PricingInfo object (always zero cost for local models)
        """
        return PricingInfo(
            model_name=model,
            provider=ProviderType.LM_STUDIO,
            input_cost_per_million=0.0,
            output_cost_per_million=0.0,
            context_window=4096,
            supports_streaming=True,
            supports_vision=False,
        )
    
    async def health_check(self) -> bool:
        """
        Check if LM Studio is available.
        
        Returns:
            True if LM Studio is running
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/models")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"LM Studio health check failed: {e}")
            return False
    
    async def list_models(self) -> List[Dict[str, str]]:
        """
        List available models in LM Studio.
        
        Returns:
            List of model information dictionaries
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/models")
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("data", [])
                else:
                    logger.error(f"Failed to list LM Studio models: {response.status_code}")
                    return []
        except Exception as e:
            logger.error(f"Error listing LM Studio models: {e}")
            return []
    
    async def get_loaded_model(self) -> Optional[str]:
        """
        Get the currently loaded model in LM Studio.
        
        Returns:
            Model identifier or None if no model is loaded
        """
        try:
            models = await self.list_models()
            if models:
                # LM Studio typically has one model loaded at a time
                return models[0].get("id")
            return None
        except Exception as e:
            logger.error(f"Error getting loaded model: {e}")
            return None
