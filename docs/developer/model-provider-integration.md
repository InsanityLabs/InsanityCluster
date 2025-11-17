# Model Provider Integration Guide

## Overview

This guide explains how to integrate new AI model providers into Insanity Cluster's PAN layer.

## Provider Adapter Interface

All model providers must implement the `ProviderAdapter` interface:

```python
from abc import ABC, abstractmethod
from typing import AsyncIterator
from insanity_cluster.pan.models import GenerationParams, Response, PricingInfo

class ProviderAdapter(ABC):
    """Base class for all model provider adapters"""
    
    def __init__(self, api_key: str, config: dict):
        self.api_key = api_key
        self.config = config
        self.provider_name = self.__class__.__name__.replace("Adapter", "")
    
    @abstractmethod
    async def generate(self, prompt: str, params: GenerationParams) -> Response:
        """
        Generate a response from the model.
        
        Args:
            prompt: The input prompt
            params: Generation parameters (temperature, max_tokens, etc.)
        
        Returns:
            Response object with content, cost, latency, and metadata
        """
        pass
    
    @abstractmethod
    async def stream_generate(
        self,
        prompt: str,
        params: GenerationParams
    ) -> AsyncIterator[str]:
        """
        Generate a streaming response from the model.
        
        Args:
            prompt: The input prompt
            params: Generation parameters
        
        Yields:
            String chunks as they are generated
        """
        pass
    
    @abstractmethod
    def get_pricing(self) -> PricingInfo:
        """
        Get pricing information for this provider.
        
        Returns:
            PricingInfo with cost per token for input and output
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the provider is available.
        
        Returns:
            True if provider is healthy, False otherwise
        """
        pass
```

## Creating a New Provider Adapter

### Step 1: Create Adapter Class

Create a new file in `insanity_cluster/pan/`:

```python
# insanity_cluster/pan/custom_provider_adapter.py

import httpx
import time
from typing import AsyncIterator
from insanity_cluster.pan.base_adapter import ProviderAdapter
from insanity_cluster.pan.models import GenerationParams, Response, PricingInfo
import logging

logger = logging.getLogger(__name__)

class CustomProviderAdapter(ProviderAdapter):
    """
    Adapter for Custom AI Provider.
    
    Supports models:
    - custom-model-1
    - custom-model-2
    - custom-model-3
    """
    
    def __init__(self, api_key: str, config: dict):
        super().__init__(api_key, config)
        self.base_url = config.get("base_url", "https://api.customprovider.com/v1")
        self.timeout = config.get("timeout", 60)
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
    
    async def generate(self, prompt: str, params: GenerationParams) -> Response:
        """Generate a non-streaming response"""
        start_time = time.time()
        
        try:
            # Prepare request
            request_data = {
                "model": params.model,
                "prompt": prompt,
                "temperature": params.temperature,
                "max_tokens": params.max_tokens,
                "top_p": params.top_p,
                "stream": False
            }
            
            # Make API call
            response = await self.client.post("/completions", json=request_data)
            response.raise_for_status()
            
            # Parse response
            data = response.json()
            content = data["choices"][0]["text"]
            
            # Calculate cost
            input_tokens = data["usage"]["prompt_tokens"]
            output_tokens = data["usage"]["completion_tokens"]
            pricing = self.get_pricing()
            cost = (
                input_tokens * pricing.input_cost_per_token +
                output_tokens * pricing.output_cost_per_token
            )
            
            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)
            
            return Response(
                content=content,
                model=params.model,
                provider=self.provider_name,
                cost=cost,
                latency_ms=latency_ms,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                metadata={
                    "finish_reason": data["choices"][0]["finish_reason"]
                }
            )
        
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from {self.provider_name}: {e}")
            raise ModelAPIError(f"API error: {e.response.status_code}")
        except httpx.TimeoutException:
            logger.error(f"Timeout from {self.provider_name}")
            raise ModelTimeoutError(f"Request timed out after {self.timeout}s")
        except Exception as e:
            logger.error(f"Unexpected error from {self.provider_name}: {e}")
            raise ModelError(f"Unexpected error: {e}")
    
    async def stream_generate(
        self,
        prompt: str,
        params: GenerationParams
    ) -> AsyncIterator[str]:
        """Generate a streaming response"""
        try:
            # Prepare request
            request_data = {
                "model": params.model,
                "prompt": prompt,
                "temperature": params.temperature,
                "max_tokens": params.max_tokens,
                "top_p": params.top_p,
                "stream": True
            }
            
            # Make streaming API call
            async with self.client.stream("POST", "/completions", json=request_data) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix
                        
                        if data_str == "[DONE]":
                            break
                        
                        try:
                            data = json.loads(data_str)
                            chunk = data["choices"][0]["text"]
                            yield chunk
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse streaming chunk: {data_str}")
                            continue
        
        except Exception as e:
            logger.error(f"Streaming error from {self.provider_name}: {e}")
            raise ModelError(f"Streaming error: {e}")
    
    def get_pricing(self) -> PricingInfo:
        """Get pricing information"""
        # Pricing per million tokens
        pricing_table = {
            "custom-model-1": {"input": 1.00, "output": 3.00},
            "custom-model-2": {"input": 0.50, "output": 1.50},
            "custom-model-3": {"input": 0.10, "output": 0.30},
        }
        
        return PricingInfo(
            provider=self.provider_name,
            pricing_table=pricing_table,
            input_cost_per_token=pricing_table["custom-model-1"]["input"] / 1_000_000,
            output_cost_per_token=pricing_table["custom-model-1"]["output"] / 1_000_000
        )
    
    async def health_check(self) -> bool:
        """Check if provider is available"""
        try:
            response = await self.client.get("/health")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Health check failed for {self.provider_name}: {e}")
            return False
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
```

### Step 2: Register Provider

Add your provider to the provider registry:

```python
# insanity_cluster/pan/__init__.py

from insanity_cluster.pan.custom_provider_adapter import CustomProviderAdapter

PROVIDER_REGISTRY = {
    "openai": OpenAIAdapter,
    "anthropic": AnthropicAdapter,
    "openrouter": OpenRouterAdapter,
    "ollama": OllamaAdapter,
    "lmstudio": LMStudioAdapter,
    "custom": CustomProviderAdapter,  # Add your provider
}
```

### Step 3: Configure Provider

Add configuration for your provider:

```yaml
# config.yaml
providers:
  custom:
    enabled: true
    api_key: ${CUSTOM_PROVIDER_API_KEY}
    base_url: https://api.customprovider.com/v1
    timeout: 60
    rate_limit: 100
    retry_attempts: 3
    retry_delay: 1
    models:
      - custom-model-1
      - custom-model-2
      - custom-model-3
```

### Step 4: Add Environment Variable

```bash
# .env
CUSTOM_PROVIDER_API_KEY=your-api-key-here
```

### Step 5: Test Provider

Create tests for your provider:

```python
# tests/test_custom_provider_adapter.py

import pytest
from insanity_cluster.pan.custom_provider_adapter import CustomProviderAdapter
from insanity_cluster.pan.models import GenerationParams

@pytest.mark.asyncio
async def test_generate():
    adapter = CustomProviderAdapter(
        api_key="test-key",
        config={"base_url": "https://api.customprovider.com/v1"}
    )
    
    params = GenerationParams(
        model="custom-model-1",
        temperature=0.7,
        max_tokens=100
    )
    
    response = await adapter.generate("Hello, world!", params)
    
    assert response.content is not None
    assert response.cost > 0
    assert response.latency_ms > 0
    assert response.provider == "CustomProvider"

@pytest.mark.asyncio
async def test_stream_generate():
    adapter = CustomProviderAdapter(
        api_key="test-key",
        config={"base_url": "https://api.customprovider.com/v1"}
    )
    
    params = GenerationParams(
        model="custom-model-1",
        temperature=0.7,
        max_tokens=100
    )
    
    chunks = []
    async for chunk in adapter.stream_generate("Hello, world!", params):
        chunks.append(chunk)
    
    assert len(chunks) > 0
    assert "".join(chunks) != ""

@pytest.mark.asyncio
async def test_health_check():
    adapter = CustomProviderAdapter(
        api_key="test-key",
        config={"base_url": "https://api.customprovider.com/v1"}
    )
    
    is_healthy = await adapter.health_check()
    assert isinstance(is_healthy, bool)

def test_pricing():
    adapter = CustomProviderAdapter(
        api_key="test-key",
        config={}
    )
    
    pricing = adapter.get_pricing()
    assert pricing.provider == "CustomProvider"
    assert pricing.input_cost_per_token > 0
    assert pricing.output_cost_per_token > 0
```

## Advanced Features

### Retry Logic

Implement automatic retries:

```python
from tenacity import retry, stop_after_attempt, wait_exponential

class CustomProviderAdapter(ProviderAdapter):
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True
    )
    async def generate(self, prompt: str, params: GenerationParams) -> Response:
        # Implementation with automatic retry
        pass
```

### Rate Limiting

Implement rate limiting:

```python
import asyncio
from collections import deque

class CustomProviderAdapter(ProviderAdapter):
    def __init__(self, api_key: str, config: dict):
        super().__init__(api_key, config)
        self.rate_limit = config.get("rate_limit", 100)  # requests per minute
        self.request_times = deque(maxlen=self.rate_limit)
    
    async def _wait_for_rate_limit(self):
        """Wait if rate limit is exceeded"""
        now = time.time()
        
        if len(self.request_times) >= self.rate_limit:
            oldest = self.request_times[0]
            time_since_oldest = now - oldest
            
            if time_since_oldest < 60:
                wait_time = 60 - time_since_oldest
                logger.info(f"Rate limit reached, waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
        
        self.request_times.append(now)
    
    async def generate(self, prompt: str, params: GenerationParams) -> Response:
        await self._wait_for_rate_limit()
        # Continue with generation
        pass
```

### Connection Pooling

Use connection pooling for better performance:

```python
class CustomProviderAdapter(ProviderAdapter):
    def __init__(self, api_key: str, config: dict):
        super().__init__(api_key, config)
        
        # Configure connection pool
        limits = httpx.Limits(
            max_keepalive_connections=20,
            max_connections=100,
            keepalive_expiry=30
        )
        
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            limits=limits,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
```

### Custom Error Handling

Implement provider-specific error handling:

```python
class CustomProviderError(Exception):
    """Base exception for custom provider"""

class CustomProviderRateLimitError(CustomProviderError):
    """Rate limit exceeded"""

class CustomProviderAuthError(CustomProviderError):
    """Authentication failed"""

class CustomProviderAdapter(ProviderAdapter):
    async def generate(self, prompt: str, params: GenerationParams) -> Response:
        try:
            response = await self.client.post("/completions", json=request_data)
            response.raise_for_status()
            return self._parse_response(response)
        
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise CustomProviderRateLimitError("Rate limit exceeded")
            elif e.response.status_code == 401:
                raise CustomProviderAuthError("Invalid API key")
            else:
                raise CustomProviderError(f"HTTP {e.response.status_code}")
```

### Metrics Collection

Track provider metrics:

```python
from prometheus_client import Histogram, Counter

provider_latency = Histogram(
    'provider_latency_seconds',
    'Provider API latency',
    ['provider', 'model']
)

provider_errors = Counter(
    'provider_errors_total',
    'Provider API errors',
    ['provider', 'error_type']
)

class CustomProviderAdapter(ProviderAdapter):
    async def generate(self, prompt: str, params: GenerationParams) -> Response:
        with provider_latency.labels(
            provider=self.provider_name,
            model=params.model
        ).time():
            try:
                response = await self._generate_internal(prompt, params)
                return response
            except Exception as e:
                provider_errors.labels(
                    provider=self.provider_name,
                    error_type=type(e).__name__
                ).inc()
                raise
```

## Provider-Specific Considerations

### OpenAI-Compatible APIs

Many providers offer OpenAI-compatible APIs:

```python
class OpenAICompatibleAdapter(ProviderAdapter):
    """Adapter for OpenAI-compatible APIs"""
    
    async def generate(self, prompt: str, params: GenerationParams) -> Response:
        # Use OpenAI SDK with custom base URL
        from openai import AsyncOpenAI
        
        client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )
        
        response = await client.completions.create(
            model=params.model,
            prompt=prompt,
            temperature=params.temperature,
            max_tokens=params.max_tokens
        )
        
        return self._parse_openai_response(response)
```

### Local Model Providers

For local models (Ollama, LM Studio):

```python
class LocalProviderAdapter(ProviderAdapter):
    """Adapter for local model providers"""
    
    def __init__(self, api_key: str, config: dict):
        super().__init__(api_key, config)
        # No API key needed for local
        self.endpoint = config.get("endpoint", "http://localhost:11434")
    
    async def generate(self, prompt: str, params: GenerationParams) -> Response:
        # Local models typically have zero cost
        response = await self._call_local_api(prompt, params)
        
        return Response(
            content=response["content"],
            model=params.model,
            provider=self.provider_name,
            cost=0.0,  # Local models are free
            latency_ms=response["latency_ms"],
            input_tokens=0,
            output_tokens=0
        )
```

### Vision Models

For models that support images:

```python
class VisionProviderAdapter(ProviderAdapter):
    """Adapter for vision-capable models"""
    
    async def generate_with_image(
        self,
        prompt: str,
        image_url: str,
        params: GenerationParams
    ) -> Response:
        request_data = {
            "model": params.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": image_url}}
                    ]
                }
            ]
        }
        
        response = await self.client.post("/chat/completions", json=request_data)
        return self._parse_response(response)
```

## Testing Providers

### Unit Tests

Test adapter logic in isolation:

```python
@pytest.fixture
def mock_http_client(monkeypatch):
    """Mock HTTP client for testing"""
    class MockResponse:
        def __init__(self, json_data, status_code=200):
            self.json_data = json_data
            self.status_code = status_code
        
        def json(self):
            return self.json_data
        
        def raise_for_status(self):
            if self.status_code >= 400:
                raise httpx.HTTPStatusError("Error", request=None, response=self)
    
    async def mock_post(*args, **kwargs):
        return MockResponse({
            "choices": [{"text": "Test response"}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20}
        })
    
    monkeypatch.setattr("httpx.AsyncClient.post", mock_post)
    return mock_post

def test_generate_with_mock(mock_http_client):
    adapter = CustomProviderAdapter("test-key", {})
    response = await adapter.generate("Test", GenerationParams(model="test"))
    assert response.content == "Test response"
```

### Integration Tests

Test with real API (use test accounts):

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_real_api():
    adapter = CustomProviderAdapter(
        api_key=os.getenv("CUSTOM_PROVIDER_API_KEY"),
        config={"base_url": "https://api.customprovider.com/v1"}
    )
    
    response = await adapter.generate(
        "Say hello",
        GenerationParams(model="custom-model-1", max_tokens=10)
    )
    
    assert response.content is not None
    assert response.cost > 0
```

## Deployment

### Register in Production

1. Add provider to registry
2. Update configuration
3. Set environment variables
4. Deploy new version
5. Monitor provider health

### Monitoring

Track provider metrics:
- API latency
- Error rates
- Cost per request
- Rate limit usage

### Health Checks

Implement health checks:

```python
# Health check endpoint
@app.get("/health/providers")
async def check_providers():
    results = {}
    for name, adapter_class in PROVIDER_REGISTRY.items():
        adapter = adapter_class(api_key=config.get_api_key(name), config={})
        results[name] = await adapter.health_check()
    return results
```

## Best Practices

1. **Always implement retry logic** for transient failures
2. **Use connection pooling** for better performance
3. **Implement rate limiting** to avoid API limits
4. **Track metrics** for monitoring and debugging
5. **Handle errors gracefully** with specific error types
6. **Test thoroughly** with both mocks and real APIs
7. **Document pricing** accurately for cost tracking
8. **Support streaming** for real-time responses
9. **Implement health checks** for monitoring
10. **Use async/await** for non-blocking I/O

## Support

For provider integration help:
- Documentation: https://docs.insanitycluster.com/providers
- Discord: https://discord.gg/insanity-cluster
- Email: developers@insanitycluster.com
