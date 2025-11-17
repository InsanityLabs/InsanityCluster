"""
Demo script for PAN layer functionality.

This script demonstrates:
1. Basic adapter usage
2. Model routing
3. Response streaming
4. Operating modes
"""
import asyncio
import os
from dotenv import load_dotenv

from insanity_cluster.pan import (
    OpenAIAdapter,
    AnthropicAdapter,
    OllamaAdapter,
    ModelRouter,
    RoutingRequest,
    OperatingMode,
    RoutingStrategy,
    ModeConfiguration,
    AgentType,
    ProviderType,
    GenerationParams,
    ResponseStreamer,
    StreamUpdate,
)

# Load environment variables
load_dotenv()


async def demo_basic_generation():
    """Demo basic generation with OpenAI adapter."""
    print("\n=== Demo 1: Basic Generation ===")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  OPENAI_API_KEY not set, skipping OpenAI demo")
        return
    
    adapter = OpenAIAdapter(api_key=api_key)
    
    # Check health
    is_healthy = await adapter.health_check()
    print(f"OpenAI health: {'✓' if is_healthy else '✗'}")
    
    if not is_healthy:
        print("OpenAI is not available")
        return
    
    # Generate response
    params = GenerationParams(
        max_tokens=100,
        temperature=0.7,
        system_prompt="You are a helpful assistant."
    )
    
    print("\nGenerating response...")
    response = await adapter.generate(
        prompt="Explain what a neural network is in one sentence.",
        model="gpt-3.5-turbo",  # Using available model
        params=params
    )
    
    print(f"\nResponse: {response.content}")
    print(f"Cost: ${response.cost:.4f}")
    print(f"Latency: {response.latency_ms}ms")
    print(f"Tokens: {response.input_tokens} in, {response.output_tokens} out")


async def demo_streaming():
    """Demo streaming generation."""
    print("\n=== Demo 2: Streaming Generation ===")
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("⚠️  ANTHROPIC_API_KEY not set, skipping Anthropic demo")
        return
    
    adapter = AnthropicAdapter(api_key=api_key)
    
    # Check health
    is_healthy = await adapter.health_check()
    print(f"Anthropic health: {'✓' if is_healthy else '✗'}")
    
    if not is_healthy:
        print("Anthropic is not available")
        return
    
    params = GenerationParams(stream=True, max_tokens=100)
    
    print("\nStreaming response:")
    print("-" * 50)
    
    async for chunk in adapter.stream_generate(
        prompt="Count from 1 to 5 with descriptions.",
        model="claude-3-haiku-20240307",  # Using available model
        params=params
    ):
        print(chunk.content, end="", flush=True)
    
    print("\n" + "-" * 50)


async def demo_local_models():
    """Demo local model usage with Ollama."""
    print("\n=== Demo 3: Local Models (Ollama) ===")
    
    adapter = OllamaAdapter(auto_pull=False)  # Don't auto-pull for demo
    
    # Check health
    is_healthy = await adapter.health_check()
    print(f"Ollama health: {'✓' if is_healthy else '✗'}")
    
    if not is_healthy:
        print("⚠️  Ollama is not running. Start it with: ollama serve")
        return
    
    # List available models
    models = await adapter.list_models()
    print(f"\nAvailable models: {models}")
    
    if not models:
        print("No models available. Pull a model with: ollama pull mistral")
        return
    
    # Use first available model
    model = models[0]
    print(f"\nUsing model: {model}")
    
    response = await adapter.generate(
        prompt="What is 2+2?",
        model=model,
        params=GenerationParams(max_tokens=50)
    )
    
    print(f"\nResponse: {response.content}")
    print(f"Cost: ${response.cost} (local models are free!)")
    print(f"Latency: {response.latency_ms}ms")


async def demo_model_router():
    """Demo intelligent model routing."""
    print("\n=== Demo 4: Model Router ===")
    
    # Create router with Mixed mode
    config = ModeConfiguration(
        mode=OperatingMode.MIXED,
        default_strategy=RoutingStrategy.COST_OPTIMIZED,
        max_cost_per_day=10.0,
        local_complexity_threshold=0.5,
    )
    
    router = ModelRouter(config=config)
    
    # Register available adapters
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        router.register_adapter(ProviderType.OPENAI, OpenAIAdapter(api_key=openai_key))
        print("✓ Registered OpenAI adapter")
    
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        router.register_adapter(ProviderType.ANTHROPIC, AnthropicAdapter(api_key=anthropic_key))
        print("✓ Registered Anthropic adapter")
    
    ollama_adapter = OllamaAdapter()
    if await ollama_adapter.health_check():
        router.register_adapter(ProviderType.OLLAMA, ollama_adapter)
        print("✓ Registered Ollama adapter")
    
    if not router.adapters:
        print("⚠️  No adapters available. Set API keys or start Ollama.")
        return
    
    # Route different types of requests
    requests = [
        RoutingRequest(
            task_description="What is 2+2?",
            complexity=0.1,
            task_type="simple_chat"
        ),
        RoutingRequest(
            task_description="Write a Python function to implement quicksort",
            agent_type=AgentType.DEVELOPER,
            complexity=0.7,
            task_type="code_generation"
        ),
        RoutingRequest(
            task_description="Analyze this legal contract for risks",
            agent_type=AgentType.BUSINESS,
            complexity=0.9,
            task_type="contract_review"
        ),
    ]
    
    print("\n" + "=" * 60)
    for i, request in enumerate(requests, 1):
        print(f"\nRequest {i}: {request.task_description}")
        print(f"Complexity: {request.complexity}")
        
        try:
            result = await router.route(request)
            print(f"→ Selected: {result.model} ({result.provider.value})")
            print(f"→ Estimated cost: ${result.estimated_cost:.4f}")
            print(f"→ Reasoning: {result.reasoning}")
            print(f"→ Fallback chain: {[m for m, _ in result.fallback_chain[:2]]}")
        except Exception as e:
            print(f"→ Error: {e}")
    
    print("=" * 60)


async def demo_response_streamer():
    """Demo response streaming with buffering."""
    print("\n=== Demo 5: Response Streamer ===")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  OPENAI_API_KEY not set, skipping demo")
        return
    
    adapter = OpenAIAdapter(api_key=api_key)
    
    if not await adapter.health_check():
        print("OpenAI is not available")
        return
    
    # Create streamer
    streamer = ResponseStreamer(
        buffer_size=5,
        flush_interval=0.2,
        enable_post_processing=True
    )
    
    # Callback to print updates
    async def print_update(update: StreamUpdate):
        if update.content:
            print(update.content, end="", flush=True)
        if update.is_complete:
            print(f"\n\n[Stream complete: {update.metadata.get('finish_reason')}]")
    
    print("\nStreaming with buffering:")
    print("-" * 50)
    
    # Get model stream
    model_stream = adapter.stream_generate(
        prompt="List 3 benefits of exercise.",
        model="gpt-3.5-turbo",
        params=GenerationParams(stream=True, max_tokens=100)
    )
    
    # Stream to client
    await streamer.stream_to_client(
        task_id="demo-task",
        model_stream=model_stream,
        send_callback=print_update
    )
    
    print("-" * 50)


async def main():
    """Run all demos."""
    print("=" * 60)
    print("PAN Layer Demo")
    print("=" * 60)
    
    demos = [
        ("Basic Generation", demo_basic_generation),
        ("Streaming", demo_streaming),
        ("Local Models", demo_local_models),
        ("Model Router", demo_model_router),
        ("Response Streamer", demo_response_streamer),
    ]
    
    for name, demo_func in demos:
        try:
            await demo_func()
        except Exception as e:
            print(f"\n❌ Error in {name}: {e}")
        
        # Pause between demos
        await asyncio.sleep(1)
    
    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
