"""
Ollama adapter for local model inference.
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


# Local models have zero cost
OLLAMA_PRICING = {
    "llama3": PricingInfo(
        model_name="llama3",
        provider=ProviderType.OLLAMA,
        input_cost_per_million=0.0,
        output_cost_per_million=0.0,
        context_window=8192,
        supports_streaming=True,
        supports_vision=False,
    ),
    "llama3:70b": PricingInfo(
        model_name="llama3:70b",
        provider=ProviderType.OLLAMA,
        input_cost_per_million=0.0,
        output_cost_per_million=0.0,
        context_window=8192,
        supports_streaming=True,
        supports_vision=False,
    ),
    "mistral": PricingInfo(
        model_name="mistral",
        provider=ProviderType.OLLAMA,
        input_cost_per_million=0.0,
        output_cost_per_million=0.0,
        context_window=8192,
        supports_streaming=True,
        supports_vision=False,
    ),
    "phi3": PricingInfo(
        model_name="phi3",
        provider=ProviderType.OLLAMA,
        input_cost_per_million=0.0,
        output_cost_per_million=0.0,
        context_window=4096,
        supports_streaming=True,
        supports_vision=False,
    ),
    "codellama": PricingInfo(
        model_name="codellama",
        provider=ProviderType.OLLAMA,
        input_cost_per_million=0.0,
        output_cost_per_million=0.0,
        context_window=16384,
        supports_streaming=True,
        supports_vision=False,
    ),
    "mixtral": PricingInfo(
        model_name="mixtral",
        provider=ProviderType.OLLAMA,
        input_cost_per_million=0.0,
        output_cost_per_million=0.0,
        context_window=32768,
        supports_streaming=True,
        supports_vision=False,
    ),
}


class OllamaAdapter(ProviderAdapter):
    """
    Adapter for Ollama local model inference.
    
    Supports running models locally with zero cost:
    - LLaMA 3 (various sizes)
    - Mistral
    - Phi-3
    - CodeLLaMA
    - Mixtral
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "http://localhost:11434",
        auto_pull: bool = True
    ):
        """
        Initialize Ollama adapter.
        
        Args:
            api_key: Not used for Ollama (local)
            base_url: Ollama API endpoint
            auto_pull: Automatically pull missing models
        """
        super().__init__(api_key, base_url)
        self.auto_pull = auto_pull
        
    async def generate(
        self,
        prompt: str,
        model: str,
        params: Optional[GenerationParams] = None
    ) -> Response:
        """
        Generate a response from Ollama model.
        
        Args:
            prompt: The input prompt
            model: Model identifier (e.g., "llama3", "mistral")
            params: Generation parameters
            
        Returns:
            Response object with generated content
        """
        if params is None:
            params = GenerationParams()
        
        # Check if model is available, pull if needed
        if self.auto_pull:
            await self._ensure_model_available(model)
        
        start_time = time.time()
        
        try:
            # Build request payload
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": params.temperature,
                    "top_p": params.top_p,
                    "num_predict": params.max_tokens,
                }
            }
            
            if params.system_prompt:
                payload["system"] = params.system_prompt
            
            if params.stop_sequences:
                payload["options"]["stop"] = params.stop_sequences
            
            # Make API call
            async with httpx.AsyncClient(timeout=params.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                )
                
                if response.status_code == 404:
                    raise ModelNotFoundError(f"Model '{model}' not found in Ollama")
                elif response.status_code >= 400:
                    raise APIError(
                        f"Ollama API error: {response.text}",
                        status_code=response.status_code,
                        provider="ollama"
                    )
                
                data = response.json()
            
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Extract response data
            content = data.get("response", "")
            
            # Estimate token usage (Ollama doesn't provide exact counts)
            input_tokens = self._count_tokens(prompt)
            output_tokens = self._count_tokens(content)
            total_tokens = input_tokens + output_tokens
            
            return Response(
                content=content,
                model=model,
                provider=ProviderType.OLLAMA,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                cost=0.0,  # Local models are free
                finish_reason="stop",
                metadata={
                    "eval_count": data.get("eval_count"),
                    "eval_duration": data.get("eval_duration"),
                }
            )
            
        except httpx.TimeoutException as e:
            logger.error(f"Ollama request timed out: {e}")
            raise TimeoutError(str(e))
        except httpx.HTTPError as e:
            logger.error(f"Ollama HTTP error: {e}")
            raise APIError(str(e), provider="ollama")
        except (ModelNotFoundError, APIError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Ollama adapter: {e}")
            raise APIError(f"Unexpected error: {e}", provider="ollama")
    
    async def stream_generate(
        self,
        prompt: str,
        model: str,
        params: Optional[GenerationParams] = None
    ) -> AsyncIterator[StreamChunk]:
        """
        Generate a streaming response from Ollama model.
        
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
        
        # Check if model is available, pull if needed
        if self.auto_pull:
            await self._ensure_model_available(model)
        
        try:
            # Build request payload
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": True,
                "options": {
                    "temperature": params.temperature,
                    "top_p": params.top_p,
                    "num_predict": params.max_tokens,
                }
            }
            
            if params.system_prompt:
                payload["system"] = params.system_prompt
            
            if params.stop_sequences:
                payload["options"]["stop"] = params.stop_sequences
            
            # Make streaming API call
            async with httpx.AsyncClient(timeout=params.timeout) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/generate",
                    json=payload
                ) as response:
                    if response.status_code == 404:
                        raise ModelNotFoundError(f"Model '{model}' not found in Ollama")
                    elif response.status_code >= 400:
                        raise APIError(
                            f"Ollama streaming error: {response.status_code}",
                            status_code=response.status_code,
                            provider="ollama"
                        )
                    
                    # Process NDJSON stream
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        
                        try:
                            import json
                            data = json.loads(line)
                            
                            content = data.get("response", "")
                            done = data.get("done", False)
                            
                            yield StreamChunk(
                                content=content,
                                model=model,
                                provider=ProviderType.OLLAMA,
                                finish_reason="stop" if done else None,
                                metadata={
                                    "eval_count": data.get("eval_count"),
                                    "done": done
                                }
                            )
                            
                            if done:
                                break
                                
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse Ollama response: {line}")
                            continue
                    
        except httpx.TimeoutException as e:
            logger.error(f"Ollama streaming request timed out: {e}")
            raise TimeoutError(str(e))
        except httpx.HTTPError as e:
            logger.error(f"Ollama streaming HTTP error: {e}")
            raise APIError(str(e), provider="ollama")
        except (ModelNotFoundError, APIError):
            raise
        except Exception as e:
            logger.error(f"Unexpected error in Ollama streaming: {e}")
            raise APIError(f"Unexpected error: {e}", provider="ollama")
    
    def get_pricing(self, model: str) -> PricingInfo:
        """
        Get pricing information for an Ollama model.
        
        Args:
            model: Model identifier
            
        Returns:
            PricingInfo object (always zero cost for local models)
        """
        # Return pricing if available, otherwise create default zero-cost pricing
        if model in OLLAMA_PRICING:
            return OLLAMA_PRICING[model]
        
        return PricingInfo(
            model_name=model,
            provider=ProviderType.OLLAMA,
            input_cost_per_million=0.0,
            output_cost_per_million=0.0,
            context_window=4096,
            supports_streaming=True,
            supports_vision=False,
        )
    
    async def health_check(self) -> bool:
        """
        Check if Ollama is available.
        
        Returns:
            True if Ollama is running
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False
    
    async def list_models(self) -> List[str]:
        """
        List available models in Ollama.
        
        Returns:
            List of model names
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                
                if response.status_code == 200:
                    data = response.json()
                    return [model["name"] for model in data.get("models", [])]
                else:
                    logger.error(f"Failed to list Ollama models: {response.status_code}")
                    return []
        except Exception as e:
            logger.error(f"Error listing Ollama models: {e}")
            return []
    
    async def pull_model(self, model: str) -> bool:
        """
        Pull a model from Ollama registry.
        
        Args:
            model: Model name to pull
            
        Returns:
            True if successful
        """
        try:
            logger.info(f"Pulling Ollama model: {model}")
            
            async with httpx.AsyncClient(timeout=300.0) as client:  # Long timeout for downloads
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/pull",
                    json={"name": model}
                ) as response:
                    if response.status_code >= 400:
                        logger.error(f"Failed to pull model {model}: {response.status_code}")
                        return False
                    
                    # Stream progress updates
                    async for line in response.aiter_lines():
                        if line:
                            try:
                                import json
                                data = json.loads(line)
                                status = data.get("status", "")
                                if status:
                                    logger.debug(f"Pull progress: {status}")
                            except json.JSONDecodeError:
                                continue
            
            logger.info(f"Successfully pulled model: {model}")
            return True
            
        except Exception as e:
            logger.error(f"Error pulling Ollama model {model}: {e}")
            return False
    
    async def _ensure_model_available(self, model: str):
        """
        Ensure a model is available, pulling it if necessary.
        
        Args:
            model: Model name
        """
        available_models = await self.list_models()
        
        # Check if model is already available
        if any(model in m for m in available_models):
            return
        
        # Try to pull the model
        logger.info(f"Model {model} not found locally, attempting to pull...")
        success = await self.pull_model(model)
        
        if not success:
            raise ModelNotFoundError(
                f"Model '{model}' not found and could not be pulled"
            )
