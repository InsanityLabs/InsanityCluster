# Layer Integration Guide

This document describes how the five layers of the Insanity Cluster integrate with each other.

## Integration Points

### SURFACE → INNER Integration

**Command Parser → Task Decomposition**
- `CommandParser.parse()` produces `ParsedCommand`
- `TaskDecompositionEngine.decompose()` consumes `ParsedCommand`
- Integration: Direct method call with data model passing

**WebSocket Server → Task Pipeline**
- `TaskExecutionPipeline` accepts optional `websocket_manager`
- Pipeline broadcasts updates via `websocket_manager.stream_update()`
- Integration: Dependency injection during pipeline initialization

```python
# Example initialization
from insanity_cluster.surface.websocket_server import ConnectionManager
from insanity_cluster.inner.pipeline import TaskExecutionPipeline

websocket_manager = ConnectionManager(auth_manager, redis_manager)
pipeline = TaskExecutionPipeline(
    decomposition_engine,
    coordinator,
    context_manager,
    database,
    websocket_manager=websocket_manager  # Optional injection
)
```

### INNER → CRUST Integration

**Multi-Agent Coordinator → Agents**
- `MultiAgentCoordinator` accepts optional `agent_registry`
- Coordinator delegates subtasks to registered agents
- Integration: Dependency injection with agent registry

```python
# Example initialization
from insanity_cluster.crust.developer_agent import DeveloperAgent
from insanity_cluster.crust.business_agent import BusinessAgent
from insanity_cluster.common.models import AgentType

agent_registry = {
    AgentType.DEVELOPER: DeveloperAgent(model_router),
    AgentType.BUSINESS: BusinessAgent(model_router),
    # ... other agents
}

coordinator = MultiAgentCoordinator(
    retry_strategy=retry_strategy,
    max_concurrent_tasks=10,
    agent_registry=agent_registry  # Optional injection
)
```

### INNER → PAN Integration

**Task Decomposition → Model Router**
- `TaskDecompositionEngine` can use model router for AI-powered decomposition
- Currently uses rule-based decomposition as reliable baseline
- Integration: Future enhancement when model router is available

**Command Parser → Model Router**
- `CommandParser` can use lightweight models (gpt-5-nano) for parsing
- Currently uses pattern matching as reliable baseline
- Integration: Future enhancement when model router is available

### CRUST → PAN Integration

**Agents → Model Router**
- All agents extend `BaseAgent` which uses `ModelRouter`
- Agents call `_generate_with_model()` for inference
- Integration: Model router passed during agent initialization

```python
# Example from BaseAgent
async def _generate_with_model(
    self,
    prompt: str,
    model_strategy: ModelStrategy,
    generation_params: Optional[GenerationParams] = None,
    context: Optional[Dict[str, Any]] = None
) -> Response:
    # Route to appropriate model
    endpoint = self.model_router.route_request(
        prompt=prompt,
        strategy=model_strategy,
        context=context or {}
    )
    
    # Get adapter and generate
    adapter = self.model_router.get_adapter(endpoint)
    response = await adapter.generate(prompt, generation_params)
    
    return response
```

### All Layers → TABLE Integration

**Database Access**
- All layers can access PostgreSQL via `DatabaseManager`
- Connection pooling managed by TABLE layer
- Integration: Shared database manager instance

**Redis Caching**
- Command Parser caches parsed commands
- Task Decomposition caches task graphs
- Context Manager caches recent contexts
- Integration: Shared Redis manager instance

**Vector Store**
- Task Decomposition stores/retrieves similar patterns
- Context Manager stores embeddings for semantic search
- Integration: Shared vector store instance

## Integration Patterns

### 1. Dependency Injection

Components accept dependencies through constructor parameters:
- Required dependencies: Passed as regular parameters
- Optional dependencies: Passed with `Optional[Type] = None`

Benefits:
- Testability: Easy to mock dependencies
- Flexibility: Can run without optional components
- Loose coupling: Components don't create their own dependencies

### 2. Data Model Passing

Layers communicate via well-defined data models:
- `ParsedCommand`: SURFACE → INNER
- `TaskGraph`: INNER decomposition → coordination
- `Subtask`: INNER → CRUST
- `AgentResult`: CRUST → INNER

Benefits:
- Type safety: Clear contracts between layers
- Validation: Data models enforce structure
- Documentation: Models serve as API documentation

### 3. Graceful Degradation

Components work with or without optional integrations:
- Pipeline works without WebSocket manager (no realtime updates)
- Coordinator works without agent registry (uses simulation)
- Parser works without model router (uses pattern matching)
- Decomposition works without model router (uses rules)

Benefits:
- Reliability: System works even if components fail
- Development: Can test layers independently
- Deployment: Can deploy incrementally

## Testing Integration

### Unit Testing

Test each component in isolation with mocked dependencies:

```python
# Example: Test coordinator without real agents
async def test_coordinator():
    coordinator = MultiAgentCoordinator()  # No agent_registry
    task_graph = create_test_task_graph()
    result = await coordinator.execute_task_graph(task_graph)
    assert result.status == ResultStatus.SUCCESS
```

### Integration Testing

Test components together with real dependencies:

```python
# Example: Test full pipeline
async def test_full_pipeline():
    # Create real components
    decomposition_engine = TaskDecompositionEngine(vector_store, redis)
    coordinator = MultiAgentCoordinator(agent_registry=agents)
    pipeline = TaskExecutionPipeline(
        decomposition_engine,
        coordinator,
        context_manager,
        database,
        websocket_manager=ws_manager
    )
    
    # Execute command
    command = ParsedCommand(...)
    result = await pipeline.execute_command(command)
    assert result.status == ResultStatus.SUCCESS
```

## Production Deployment

### Full Integration

In production, initialize all components with full integration:

```python
# Initialize TABLE layer
database = DatabaseManager(settings.database_url)
redis = RedisManager(settings.redis_url)
vector_store = VectorStore(settings.qdrant_url)

# Initialize PAN layer
model_router = ModelRouter(config, adapters)

# Initialize CRUST layer
agent_registry = {
    AgentType.DEVELOPER: DeveloperAgent(model_router),
    AgentType.BUSINESS: BusinessAgent(model_router),
    AgentType.COMMUNICATION: CommunicationAgent(model_router),
    AgentType.RESEARCH: ResearchAgent(model_router),
    AgentType.CREATIVE: CreativeAgent(model_router),
    AgentType.FINANCE: FinanceAgent(model_router),
    AgentType.PROJECT_MANAGER: ProjectManagerAgent(model_router),
}

# Initialize INNER layer
decomposition_engine = TaskDecompositionEngine(vector_store, redis)
coordinator = MultiAgentCoordinator(
    retry_strategy=RetryStrategy(),
    max_concurrent_tasks=10,
    agent_registry=agent_registry
)
context_manager = ContextManager(database, redis, vector_store)

# Initialize SURFACE layer
websocket_manager = ConnectionManager(auth_manager, redis)
pipeline = TaskExecutionPipeline(
    decomposition_engine,
    coordinator,
    context_manager,
    database,
    websocket_manager=websocket_manager
)
```

### Minimal Integration

For development or testing, use minimal integration:

```python
# Initialize only required components
database = DatabaseManager(settings.database_url)
redis = RedisManager(settings.redis_url)

decomposition_engine = TaskDecompositionEngine()  # No vector store
coordinator = MultiAgentCoordinator()  # No agents
context_manager = ContextManager(database, redis, None)  # No vector store
pipeline = TaskExecutionPipeline(
    decomposition_engine,
    coordinator,
    context_manager,
    database
    # No websocket_manager
)
```

## Error Handling Across Layers

### Error Propagation

Errors propagate up through layers:
1. PAN layer: Model/API errors
2. CRUST layer: Agent execution errors
3. INNER layer: Coordination/decomposition errors
4. SURFACE layer: User-facing errors

### Error Recovery

Each layer implements recovery strategies:
- **PAN**: Fallback to alternative models
- **CRUST**: Retry with exponential backoff
- **INNER**: Circuit breaker, alternative agents
- **SURFACE**: User clarification requests

### Error Reporting

Errors are logged at each layer with context:
```python
logger.error(
    f"Layer: {layer_name}, "
    f"Component: {component_name}, "
    f"Error: {error}, "
    f"Context: {context}"
)
```

## Performance Considerations

### Async/Await

All layer integrations use async/await for non-blocking I/O:
- Database queries
- Redis operations
- Model inference
- WebSocket communication

### Connection Pooling

Shared connection pools across layers:
- PostgreSQL: asyncpg connection pool
- Redis: redis-py connection pool
- HTTP: aiohttp client session

### Caching Strategy

Multi-level caching reduces latency:
1. In-memory: Hot data (< 1s TTL)
2. Redis: Recent data (1h - 7d TTL)
3. PostgreSQL: Persistent data
4. Vector DB: Semantic search

## Monitoring Integration

### Metrics Collection

Each layer reports metrics to TABLE layer:
- Latency per operation
- Cost per request
- Error rates
- Queue depths

### Distributed Tracing

Trace IDs flow through all layers:
```python
context = {
    "trace_id": trace_id,
    "span_id": span_id,
    "parent_span_id": parent_span_id
}
```

### Health Checks

Each layer exposes health check:
```python
async def health_check() -> bool:
    # Check dependencies
    # Return True if healthy
    pass
```
