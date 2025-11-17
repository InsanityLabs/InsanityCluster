# PAN Layer - Model Inference and Integration

The PAN (Provider Adapter Network) layer provides intelligent model routing and unified access to multiple AI model providers.

## Components

### Provider Adapters

Unified interface for different AI model providers:

- **OpenAIAdapter**: GPT-5 series models (gpt-5.1, gpt-5, gpt-5-mini, gpt-5-nano, gpt-5-codex)
- **AnthropicAdapter**: Claude 4 series models (Sonnet 4.5, Haiku 4.5, Opus 4.1)
- **OpenRouterAdapter**: Unified access to multiple providers (free and paid tiers)
- **OllamaAdapter**: Local models (LLaMA 3, Mistral, Phi-3, CodeLLaMA)
- **LMStudioAdapter**: Local models via LM Studio

### Model Router

Intelligent routing based on:
- Operating mode (Local, OpenRouter Free, Mixed, Web, OpenRouter Paid)
- Routing strategy (Speed-First, Quality-First, Cost-Optimized, Task-Specific)
- Task complexity and requirements
- Cost constraints and daily limits

### Response Streamer

Realtime streaming of model responses with:
- Buffering and post-processing
- WebSocket integration
- Error handling and recovery
- Stream multiplexing for concurrent tasks

## Usage Examples

### Basic Generation

```python
from insanity_cluster.pan import OpenAIAdapter, GenerationParams

# Initialize adapter
adapter = OpenAIAdapter(api_key="your-api-key")

# Generate response
params = GenerationParams(
    max_tokens=1000,
    temperature=0.7,
    system_prompt="You are a helpful assistant."
)

response = await adapter.generate(
    prompt="Explain quantum computing",
    model="gpt-5-mini",
    params=params
)

print(response.content)
print(f"Cost: ${response.cost:.4f}")
print(f"Latency: {response.latency_ms}ms")
```

### Streaming Generation

```python
from insanity_cluster.pan import AnthropicAdapter, GenerationParams

adapter = AnthropicAdapter(api_key="your-api-key")

params = GenerationParams(stream=True)

async for chunk in adapter.stream_generate(
    prompt="Write a short story",
    model="claude-sonnet-4.5",
    params=params
):
    print(chunk.content, end="", flush=True)
```

### Model Router

```python
from insanity_cluster.pan import (
    ModelRouter,
    RoutingRequest,
    OperatingMode,
    RoutingStrategy,
    ModeConfiguration,
    OpenAIAdapter,
    AnthropicAdapter,
    OllamaAdapter,
)

# Initialize router with Mixed mode
config = ModeConfiguration(
    mode=OperatingMode.MIXED,
    default_strategy=RoutingStrategy.COST_OPTIMIZED,
    max_cost_per_day=50.0,
    local_complexity_threshold=0.5,
)

router = ModelRouter(config=config)

# Register adapters
router.register_adapter(ProviderType.OPENAI, OpenAIAdapter(api_key="..."))
router.register_adapter(ProviderType.ANTHROPIC, AnthropicAdapter(api_key="..."))
router.register_adapter(ProviderType.OLLAMA, OllamaAdapter())

# Route a request
request = RoutingRequest(
    task_description="Generate a Python function to sort a list",
    agent_type=AgentType.DEVELOPER,
    task_type="code_generation",
    complexity=0.6,
)

result = await router.route(request)

print(f"Selected: {result.model} ({result.provider.value})")
print(f"Estimated cost: ${result.estimated_cost:.4f}")
print(f"Reasoning: {result.reasoning}")

# Use the selected adapter
response = await result.adapter.generate(
    prompt=request.task_description,
    model=result.model
)
```

### Response Streaming to WebSocket

```python
from insanity_cluster.pan import ResponseStreamer, StreamUpdate

streamer = ResponseStreamer(
    buffer_size=10,
    flush_interval=0.1,
    enable_post_processing=True
)

async def send_to_websocket(update: StreamUpdate):
    """Send update to WebSocket client."""
    await websocket.send_json({
        "task_id": update.task_id,
        "content": update.content,
        "is_complete": update.is_complete,
        "metadata": update.metadata,
    })

# Stream model output to client
model_stream = adapter.stream_generate(prompt="...", model="...")

await streamer.stream_to_client(
    task_id="task-123",
    model_stream=model_stream,
    send_callback=send_to_websocket
)
```

### Local Models with Ollama

```python
from insanity_cluster.pan import OllamaAdapter

adapter = OllamaAdapter(
    base_url="http://localhost:11434",
    auto_pull=True  # Automatically pull missing models
)

# Check health
is_healthy = await adapter.health_check()

# List available models
models = await adapter.list_models()
print(f"Available models: {models}")

# Generate with local model (zero cost)
response = await adapter.generate(
    prompt="Explain machine learning",
    model="llama3"
)

print(f"Cost: ${response.cost}")  # Always 0.0 for local models
```

## Operating Modes

### Local Mode
- Only local models (Ollama, LM Studio)
- Zero cost
- Maximum privacy
- Best for: Development, privacy-sensitive tasks

### OpenRouter Free Mode
- Only free models via OpenRouter
- Zero cost (rate-limited)
- Best for: Experimentation, learning

### Mixed Mode (Recommended)
- Hybrid: local for simple tasks, paid for complex
- Configurable complexity threshold
- Best for: Cost optimization with quality when needed

### Web Mode
- Only premium paid models (OpenAI, Anthropic direct)
- Maximum quality and speed
- Best for: Production, mission-critical tasks

### OpenRouter Paid Mode
- All models via OpenRouter
- Unified billing
- Best for: Simplified billing, model variety

## Routing Strategies

### Speed-First
- Prioritizes fastest models
- Local: Mistral 7B, Phi-3
- Paid: Claude Haiku 4.5

### Quality-First
- Prioritizes most capable models
- Local: LLaMA 3 70B
- Paid: Claude Opus 4.1, GPT-5.1

### Cost-Optimized
- Minimizes cost while meeting requirements
- Escalates based on complexity
- Simple → gpt-5-nano ($0.05/M)
- Complex → Claude Sonnet 4.5 ($3/M)

### Task-Specific
- Selects optimal model per task type
- Code generation → Claude Sonnet 4.5
- Contract review → Claude Opus 4.1
- Simple chat → GPT-5-mini

## Error Handling

All adapters implement automatic retry with exponential backoff:

```python
try:
    response = await adapter.generate(prompt="...", model="...")
except RateLimitError as e:
    print(f"Rate limit hit, retry after: {e.retry_after}s")
except TimeoutError as e:
    print(f"Request timed out: {e}")
except APIError as e:
    print(f"API error: {e}")
except AuthenticationError as e:
    print(f"Authentication failed: {e}")
```

## Fallback Chains

The router automatically provides fallback chains:

```python
result = await router.route(request)

# Try primary model
try:
    response = await result.adapter.generate(...)
except Exception:
    # Try fallback chain
    for fallback_model, fallback_provider in result.fallback_chain:
        fallback_adapter = router.adapters[fallback_provider]
        try:
            response = await fallback_adapter.generate(
                prompt=...,
                model=fallback_model
            )
            break
        except Exception:
            continue
```

## Configuration

### Per-Agent Configuration

```python
config = ModeConfiguration(
    mode=OperatingMode.MIXED,
    agent_overrides={
        AgentType.DEVELOPER: AgentModelConfig(
            preferred_models=["claude-sonnet-4.5", "gpt-5-codex"],
            fallback_to_paid=True,
            max_cost=1.0,
        ),
        AgentType.COMMUNICATION: AgentModelConfig(
            preferred_models=["mistral", "claude-haiku-4.5"],
            max_cost=0.1,
        ),
    }
)
```

### Per-Task-Type Configuration

```python
config = ModeConfiguration(
    mode=OperatingMode.MIXED,
    task_type_overrides={
        "code_generation": TaskModelConfig(
            strategy_override=RoutingStrategy.QUALITY_FIRST,
            allow_local=False,  # Always use paid
        ),
        "simple_chat": TaskModelConfig(
            model_override="phi3",
            allow_paid=False,  # Always use local
        ),
    }
)
```

## Cost Tracking

```python
router = ModelRouter(config=config)

# Track costs
response = await adapter.generate(...)
router.track_cost(response.cost)

# Check daily cost
print(f"Daily cost: ${router._daily_cost:.2f}")

# Reset at midnight
router.reset_daily_cost()
```

## Health Checks

```python
# Check if providers are available
openai_healthy = await openai_adapter.health_check()
anthropic_healthy = await anthropic_adapter.health_check()
ollama_healthy = await ollama_adapter.health_check()

print(f"OpenAI: {'✓' if openai_healthy else '✗'}")
print(f"Anthropic: {'✓' if anthropic_healthy else '✗'}")
print(f"Ollama: {'✓' if ollama_healthy else '✗'}")
```

## Testing

Run tests for the PAN layer:

```bash
pytest tests/test_pan_layer.py -v
```

## Dependencies

- `openai>=1.10.0` - OpenAI SDK
- `anthropic>=0.8.1` - Anthropic SDK
- `httpx>=0.26.0` - HTTP client for OpenRouter and Ollama
- `asyncio` - Async support

## Environment Variables

```bash
# API Keys
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
OPENROUTER_API_KEY=your-openrouter-key

# Local Model Endpoints
OLLAMA_BASE_URL=http://localhost:11434
LMSTUDIO_BASE_URL=http://localhost:1234/v1

# Router Configuration
DEFAULT_OPERATING_MODE=mixed
DEFAULT_ROUTING_STRATEGY=cost_optimized
MAX_COST_PER_DAY=50.0
```
