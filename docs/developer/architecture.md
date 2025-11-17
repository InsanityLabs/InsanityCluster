# Architecture Documentation

## System Overview

Insanity Cluster is built on a five-layer architecture designed for scalability, maintainability, and real-time performance.

```
┌─────────────────────────────────────────────────────────────┐
│                      SURFACE LAYER                          │
│              User Interfaces & API Gateway                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                       INNER LAYER                           │
│           Orchestration & Task Management                   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                       CRUST LAYER                           │
│              Specialized Agent Execution                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                        PAN LAYER                            │
│            Model Routing & Inference                        │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                       TABLE LAYER                           │
│         Infrastructure & Data Storage                       │
└─────────────────────────────────────────────────────────────┘
```

## Layer Responsibilities

### SURFACE Layer

**Purpose**: Handle all user interactions and external integrations

**Components**:
- `CommandParser`: Parse natural language commands
- `APIGateway`: REST API endpoints
- `WebSocketServer`: Real-time bidirectional communication
- `CLIInterface`: Command-line interface
- `AuthMiddleware`: Authentication and authorization

**Key Files**:
- `insanity_cluster/surface/main.py`: FastAPI application
- `insanity_cluster/surface/api.py`: REST API endpoints
- `insanity_cluster/surface/websocket_server.py`: WebSocket handling
- `insanity_cluster/surface/command_parser.py`: Command parsing
- `insanity_cluster/surface/auth.py`: Authentication

**Data Flow**:
1. Receive user command (CLI, API, or WebSocket)
2. Authenticate user
3. Parse command into structured format
4. Send to INNER layer for processing
5. Stream updates back to user

### INNER Layer

**Purpose**: Orchestrate task execution and coordinate agents

**Components**:
- `TaskDecompositionEngine`: Break commands into subtasks
- `MultiAgentCoordinator`: Manage agent execution
- `ContextManager`: Maintain conversation state
- `ExecutionPipeline`: End-to-end task flow

**Key Files**:
- `insanity_cluster/inner/task_decomposition.py`: Task decomposition
- `insanity_cluster/inner/coordinator.py`: Agent coordination
- `insanity_cluster/inner/context_manager.py`: Context management
- `insanity_cluster/inner/pipeline.py`: Execution pipeline

**Data Flow**:
1. Receive parsed command from SURFACE
2. Decompose into subtasks with dependencies
3. Assign subtasks to appropriate agents
4. Coordinate parallel/sequential execution
5. Aggregate results and return to SURFACE

### CRUST Layer

**Purpose**: Execute domain-specific tasks using specialized agents

**Components**:
- `BaseAgent`: Abstract base class for all agents
- `DeveloperAgent`: Code generation and review
- `CommunicationAgent`: Phone, email, messaging
- `BusinessAgent`: Legal and business operations
- `ResearchAgent`: Information gathering
- `CreativeAgent`: Content creation
- `FinanceAgent`: Financial operations
- `ProjectManagerAgent`: Project management

**Key Files**:
- `insanity_cluster/crust/base_agent.py`: Base agent class
- `insanity_cluster/crust/developer_agent.py`: Developer agent
- `insanity_cluster/crust/communication_agent.py`: Communication agent
- `insanity_cluster/crust/business_agent.py`: Business agent
- `insanity_cluster/crust/research_agent.py`: Research agent
- `insanity_cluster/crust/creative_agent.py`: Creative agent
- `insanity_cluster/crust/finance_agent.py`: Finance agent
- `insanity_cluster/crust/project_manager_agent.py`: Project manager agent

**Data Flow**:
1. Receive subtask from INNER layer
2. Select optimal model strategy
3. Request inference from PAN layer
4. Validate output
5. Return result to INNER layer

### PAN Layer

**Purpose**: Route requests to optimal AI models and handle inference

**Components**:
- `ModelRouter`: Select optimal model endpoint
- `ProviderAdapters`: Unified interface for model providers
- `ResponseStreamer`: Stream model outputs
- `FallbackHandler`: Handle model failures

**Key Files**:
- `insanity_cluster/pan/model_router.py`: Model routing logic
- `insanity_cluster/pan/base_adapter.py`: Base adapter interface
- `insanity_cluster/pan/openai_adapter.py`: OpenAI integration
- `insanity_cluster/pan/anthropic_adapter.py`: Anthropic integration
- `insanity_cluster/pan/openrouter_adapter.py`: OpenRouter integration
- `insanity_cluster/pan/ollama_adapter.py`: Ollama integration
- `insanity_cluster/pan/lmstudio_adapter.py`: LM Studio integration
- `insanity_cluster/pan/response_streamer.py`: Response streaming

**Data Flow**:
1. Receive inference request from CRUST layer
2. Select optimal model based on strategy
3. Call model API (with retry logic)
4. Stream response back to CRUST layer
5. Handle failures with fallback models

### TABLE Layer

**Purpose**: Provide infrastructure and data storage

**Components**:
- `PostgreSQL`: Relational data storage
- `Redis`: Caching and message queues
- `Qdrant`: Vector database for embeddings
- `Prometheus`: Metrics collection
- `Object Storage`: File storage

**Key Files**:
- `insanity_cluster/table/database.py`: Database connection
- `insanity_cluster/table/redis_manager.py`: Redis operations
- `insanity_cluster/table/vector_store.py`: Vector database
- `insanity_cluster/table/metrics.py`: Metrics collection
- `insanity_cluster/table/models.py`: Data models

**Data Flow**:
- Persistent storage for all layers
- Caching for performance
- Message queues for async processing
- Metrics collection for monitoring

## Design Patterns

### 1. Adapter Pattern (PAN Layer)

All model providers implement a common interface:

```python
class ProviderAdapter(ABC):
    @abstractmethod
    async def generate(self, prompt: str, params: GenerationParams) -> Response:
        pass
    
    @abstractmethod
    async def stream_generate(self, prompt: str, params: GenerationParams) -> AsyncIterator[str]:
        pass
```

This allows:
- Easy addition of new providers
- Transparent fallback between providers
- Consistent error handling

### 2. Strategy Pattern (Model Routing)

Model selection uses strategy pattern:

```python
class ModelRouter:
    def route(self, request: InferenceRequest, strategy: ModelStrategy) -> ModelEndpoint:
        if strategy == RoutingStrategy.SPEED_FIRST:
            return self._select_fastest_model(request)
        elif strategy == RoutingStrategy.QUALITY_FIRST:
            return self._select_best_model(request)
        # ...
```

### 3. Circuit Breaker Pattern (Error Handling)

Prevents cascading failures:

```python
class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func: Callable):
        if self.state == "OPEN":
            raise CircuitBreakerOpenError()
        # Execute and track failures
```

### 4. Observer Pattern (WebSocket Updates)

Real-time updates use observer pattern:

```python
class WebSocketManager:
    def __init__(self):
        self.connections: Dict[str, Set[WebSocket]] = {}
    
    async def broadcast(self, task_id: str, update: TaskUpdate):
        for ws in self.connections.get(task_id, []):
            await ws.send_json(update.dict())
```

### 5. Factory Pattern (Agent Creation)

Agents are created using factory:

```python
class AgentFactory:
    @staticmethod
    def create_agent(agent_type: AgentType) -> BaseAgent:
        if agent_type == AgentType.DEVELOPER:
            return DeveloperAgent()
        elif agent_type == AgentType.COMMUNICATION:
            return CommunicationAgent()
        # ...
```

## Data Models

### Core Models

```python
@dataclass
class ParsedCommand:
    intent: str
    parameters: Dict[str, Any]
    confidence: float
    user_id: str
    timestamp: datetime

@dataclass
class Subtask:
    id: str
    description: str
    agent_type: AgentType
    dependencies: List[str]
    priority: int
    estimated_cost: float

@dataclass
class TaskGraph:
    root_task_id: str
    subtasks: List[Subtask]
    dependencies: Dict[str, List[str]]

@dataclass
class AgentResult:
    subtask_id: str
    status: ResultStatus
    output: Any
    cost: float
    latency_ms: int
    model_used: str
```

## Communication Patterns

### Synchronous Communication

Used for:
- REST API requests
- Database queries
- Cache operations

```python
# Example: REST API
@app.post("/tasks")
async def create_task(request: TaskRequest) -> TaskResponse:
    parsed = await command_parser.parse(request.command)
    task_id = await task_manager.create_task(parsed)
    return TaskResponse(task_id=task_id)
```

### Asynchronous Communication

Used for:
- Task execution
- Agent coordination
- Model inference

```python
# Example: Task execution
async def execute_task(task_id: str):
    task_graph = await decompose_task(task_id)
    results = await asyncio.gather(*[
        execute_subtask(subtask)
        for subtask in task_graph.get_executable_subtasks()
    ])
```

### Event-Driven Communication

Used for:
- Real-time updates
- Webhooks
- Notifications

```python
# Example: WebSocket updates
async def stream_task_updates(task_id: str, websocket: WebSocket):
    async for update in task_updates_stream(task_id):
        await websocket.send_json(update.dict())
```

## Scalability Considerations

### Horizontal Scaling

All layers support horizontal scaling:

**SURFACE Layer**:
- Stateless API servers
- Load balancer (NGINX)
- Session state in Redis

**INNER Layer**:
- Multiple orchestrator instances
- Task queue in Redis
- Distributed locking

**CRUST Layer**:
- Agent worker pool
- Dynamic scaling based on queue depth
- Independent agent processes

**PAN Layer**:
- Connection pooling
- Rate limiting per provider
- Fallback chains

**TABLE Layer**:
- PostgreSQL read replicas
- Redis cluster
- Qdrant sharding

### Vertical Scaling

Resource allocation per layer:

```yaml
# docker-compose.yml
surface:
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 2G

inner:
  deploy:
    resources:
      limits:
        cpus: '4'
        memory: 4G

crust:
  deploy:
    resources:
      limits:
        cpus: '8'
        memory: 8G
```

## Performance Optimization

### Caching Strategy

**Command Parsing** (7 days):
```python
cache_key = f"command_cache:{hash(command)}"
cached = await redis.get(cache_key)
if cached:
    return ParsedCommand.parse_raw(cached)
```

**Task Decomposition** (1 day):
```python
cache_key = f"decomposition_cache:{hash(command)}"
cached = await redis.get(cache_key)
if cached:
    return TaskGraph.parse_raw(cached)
```

**Context** (1 hour):
```python
cache_key = f"context:{session_id}"
cached = await redis.get(cache_key)
if cached:
    return Context.parse_raw(cached)
```

### Database Optimization

**Indexes**:
```sql
CREATE INDEX idx_tasks_user_id ON tasks(user_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_created_at ON tasks(created_at DESC);
CREATE INDEX idx_metrics_task_id ON metrics(task_id);
```

**Connection Pooling**:
```python
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True
)
```

### Async Processing

All I/O operations are async:

```python
# Database
async with async_session() as session:
    result = await session.execute(query)

# Redis
await redis.set(key, value)

# HTTP requests
async with httpx.AsyncClient() as client:
    response = await client.post(url, json=data)

# Model inference
async for chunk in model.stream_generate(prompt):
    yield chunk
```

## Security Architecture

### Authentication Flow

```
User → API Key/JWT → AuthMiddleware → Verify → Allow/Deny
```

### Authorization

Role-based access control (RBAC):

```python
@require_role("admin")
async def admin_endpoint():
    pass

@require_role("user")
async def user_endpoint():
    pass
```

### Data Encryption

- TLS 1.3 for all external communication
- AES-256 for data at rest
- API keys hashed with bcrypt
- Secrets in environment variables

### API Key Management

```python
def generate_api_key() -> str:
    prefix = "ic_live_" if PRODUCTION else "ic_test_"
    random_part = secrets.token_urlsafe(32)
    return f"{prefix}{random_part}"

def hash_api_key(api_key: str) -> str:
    return bcrypt.hashpw(api_key.encode(), bcrypt.gensalt()).decode()
```

## Monitoring and Observability

### Metrics Collection

```python
# Prometheus metrics
task_duration = Histogram('task_duration_seconds', 'Task execution time')
task_cost = Histogram('task_cost_dollars', 'Task cost')
model_latency = Histogram('model_latency_seconds', 'Model inference latency', ['model', 'provider'])
error_rate = Counter('errors_total', 'Total errors', ['layer', 'type'])
```

### Structured Logging

```python
logger.info(
    "task_completed",
    extra={
        "task_id": task_id,
        "user_id": user_id,
        "cost": cost,
        "latency_ms": latency_ms,
        "models_used": models_used
    }
)
```

### Distributed Tracing

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("execute_task") as span:
    span.set_attribute("task_id", task_id)
    result = await execute_task(task_id)
    span.set_attribute("cost", result.cost)
```

## Error Handling

### Error Hierarchy

```python
class InsanityClusterError(Exception):
    """Base exception"""

class ParseError(InsanityClusterError):
    """Command parsing failed"""

class AgentError(InsanityClusterError):
    """Agent execution failed"""

class ModelError(InsanityClusterError):
    """Model inference failed"""

class InfrastructureError(InsanityClusterError):
    """Infrastructure failure"""
```

### Retry Logic

```python
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=60),
    retry=retry_if_exception_type(ModelError)
)
async def call_model(prompt: str) -> Response:
    return await model.generate(prompt)
```

### Graceful Degradation

```python
async def execute_with_fallback(subtask: Subtask) -> AgentResult:
    try:
        return await primary_agent.execute(subtask)
    except AgentError:
        logger.warning("Primary agent failed, trying fallback")
        return await fallback_agent.execute(subtask)
```

## Testing Strategy

### Unit Tests

Test individual components in isolation:

```python
def test_command_parser():
    parser = CommandParser()
    result = parser.parse("Write a Python function")
    assert result.intent == "code_generation"
    assert result.confidence > 0.8
```

### Integration Tests

Test layer interactions:

```python
async def test_task_execution():
    # Create task
    task_id = await create_task("Write a function")
    
    # Wait for completion
    result = await wait_for_completion(task_id)
    
    # Verify result
    assert result.status == "completed"
    assert result.output is not None
```

### Performance Tests

Test under load:

```python
async def test_concurrent_tasks():
    tasks = [create_task(f"Task {i}") for i in range(100)]
    results = await asyncio.gather(*tasks)
    assert all(r.status == "completed" for r in results)
```

## Deployment Architecture

### Development

```yaml
services:
  - surface: Single instance
  - inner: Single instance
  - crust: 2 workers
  - postgres: Single instance
  - redis: Single instance
  - qdrant: Single instance
```

### Production

```yaml
services:
  - surface: 3+ instances (load balanced)
  - inner: 3+ instances
  - crust: 10+ workers (auto-scaled)
  - postgres: Primary + 2 replicas
  - redis: Cluster (3 masters, 3 replicas)
  - qdrant: Cluster (3 nodes)
```

## Technology Stack

### Core
- Python 3.11+
- FastAPI (async web framework)
- asyncio + uvloop (async runtime)
- Pydantic (data validation)

### Data Storage
- PostgreSQL 15+ (relational data)
- Redis 7+ (cache and queues)
- Qdrant (vector database)

### AI/ML
- OpenAI SDK
- Anthropic SDK
- httpx (HTTP client)
- sentence-transformers (embeddings)

### Monitoring
- Prometheus (metrics)
- Grafana (visualization)
- OpenTelemetry (tracing)
- structlog (logging)

### Infrastructure
- Docker (containerization)
- Docker Compose (orchestration)
- NGINX (load balancing)
- GitHub Actions (CI/CD)

## Design Decisions

### Why Five Layers?

**Separation of Concerns**: Each layer has a single responsibility
**Scalability**: Layers can scale independently
**Maintainability**: Changes isolated to specific layers
**Testability**: Layers can be tested in isolation

### Why Async/Await?

**Performance**: Handle many concurrent tasks
**Efficiency**: Non-blocking I/O operations
**Scalability**: Better resource utilization
**Real-time**: Support streaming responses

### Why Multiple Model Providers?

**Reliability**: Fallback if one provider fails
**Cost Optimization**: Choose cheapest appropriate model
**Quality**: Use best model for each task
**Privacy**: Support local models for sensitive data

### Why Agent-Based Architecture?

**Specialization**: Each agent optimized for specific tasks
**Extensibility**: Easy to add new agents
**Coordination**: Agents can collaborate on complex tasks
**Isolation**: Agent failures don't affect others

## Future Enhancements

### Planned Features

1. **Multi-tenancy**: Support multiple organizations
2. **Agent Marketplace**: Community-contributed agents
3. **Custom Models**: Fine-tuned models per user
4. **Advanced Routing**: ML-based model selection
5. **Federated Learning**: Privacy-preserving model training

### Scalability Improvements

1. **Kubernetes**: Production orchestration
2. **Service Mesh**: Advanced networking
3. **Distributed Tracing**: Better observability
4. **Auto-scaling**: Dynamic resource allocation
5. **Global Distribution**: Multi-region deployment

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines on:
- Code style
- Testing requirements
- Pull request process
- Development workflow
