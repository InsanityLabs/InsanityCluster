# INNER Layer - Orchestration and Task Planning

The INNER layer is the orchestration brain of the Insanity Cluster. It receives parsed commands from the SURFACE layer, decomposes them into executable subtasks, coordinates specialized agents, and manages execution state.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       INNER LAYER                           │
│                                                             │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │      Task        │  │   Multi-Agent    │               │
│  │  Decomposition   │→ │   Coordinator    │               │
│  │     Engine       │  │                  │               │
│  └──────────────────┘  └──────────────────┘               │
│           ↓                      ↓                         │
│  ┌──────────────────┐  ┌──────────────────┐               │
│  │    Context       │  │      Task        │               │
│  │    Manager       │  │   Execution      │               │
│  │                  │  │    Pipeline      │               │
│  └──────────────────┘  └──────────────────┘               │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. Task Decomposition Engine (`task_decomposition.py`)

Breaks complex commands into executable subtasks with dependency analysis.

**Key Features:**
- Claude Sonnet 4.5 integration for complex decomposition
- Vector search caching for similar commands
- DAG construction with dependency validation
- Complexity estimation (time, cost, resources)
- Rule-based decomposition for common intents

**Usage:**
```python
from insanity_cluster.inner import TaskDecompositionEngine
from insanity_cluster.common.models import ParsedCommand

engine = TaskDecompositionEngine(vector_store, redis_manager)

# Decompose command
task_graph = await engine.decompose(parsed_command)

# Estimate complexity
complexity = engine.estimate_complexity(task_graph)
print(f"Estimated cost: ${complexity.cost_estimate:.2f}")
print(f"Estimated time: {complexity.time_estimate}")
print(f"Complexity score: {complexity.complexity_score:.2f}")
```

### 2. Multi-Agent Coordinator (`coordinator.py`)

Orchestrates parallel and sequential agent execution with fault tolerance.

**Key Features:**
- Parallel execution using asyncio for independent subtasks
- Sequential execution for dependent subtasks
- Circuit breaker pattern for failing agents
- Retry strategy with exponential backoff
- Priority queue for subtask scheduling
- Agent assignment with fallback routing

**Usage:**
```python
from insanity_cluster.inner import MultiAgentCoordinator, RetryStrategy

coordinator = MultiAgentCoordinator(
    retry_strategy=RetryStrategy(max_attempts=3),
    max_concurrent_tasks=10
)

# Execute task graph
result = await coordinator.execute_task_graph(task_graph)

print(f"Completed: {result.metrics.completed_subtasks}/{result.metrics.total_subtasks}")
print(f"Total cost: ${result.metrics.total_cost:.4f}")
print(f"Status: {result.status.value}")
```

### 3. Context Manager (`context_manager.py`)

Maintains conversation and task state across sessions.

**Key Features:**
- PostgreSQL storage for conversation history (JSONB)
- Redis caching for recent contexts (TTL: 1 hour)
- Vector embeddings for semantic context retrieval
- Context merging for related tasks
- Data retention policies with automatic pruning

**Usage:**
```python
from insanity_cluster.inner import ContextManager, Context

context_manager = ContextManager(database, redis_manager, vector_store)

# Create and store context
context = Context(session_id="session-123", user_id="user-456")
context.add_message("user", "Write a Python function")
context.add_task("task-789")
await context_manager.store_context("session-123", context)

# Retrieve context
context = await context_manager.retrieve_context("session-123")

# Search similar contexts
similar = await context_manager.search_similar_contexts("Python function", limit=5)

# Merge contexts from related tasks
merged = await context_manager.merge_contexts(["task-1", "task-2", "task-3"])
```

### 4. Task Execution Pipeline (`pipeline.py`)

End-to-end task execution flow from command to result.

**Key Features:**
- Integration of all INNER layer components
- Task status tracking and updates
- Result aggregation and validation
- Error handling and recovery mechanisms
- Database persistence for task results

**Usage:**
```python
from insanity_cluster.inner import TaskExecutionPipeline

pipeline = TaskExecutionPipeline(
    decomposition_engine=engine,
    coordinator=coordinator,
    context_manager=context_manager,
    database=database
)

# Execute command end-to-end
result = await pipeline.execute_command(parsed_command, session_id="session-123")

print(f"Task ID: {result.task_id}")
print(f"Status: {result.status.value}")
print(f"Output: {result.output}")
print(f"Cost: ${result.total_cost:.4f}")
print(f"Validation: {'Passed' if result.validation_passed else 'Failed'}")

# Check task status
status = await pipeline.get_task_status(result.task_id)

# Cancel task
cancelled = await pipeline.cancel_task(result.task_id)
```

## Data Flow

1. **Command Reception**: Receive `ParsedCommand` from SURFACE layer
2. **Task Decomposition**: Break into subtasks with dependencies
3. **Complexity Estimation**: Estimate time, cost, and resources
4. **Agent Coordination**: Execute subtasks in parallel/sequential order
5. **Result Aggregation**: Combine outputs from all agents
6. **Validation**: Validate results for quality and correctness
7. **Persistence**: Store results in database
8. **Context Update**: Update conversation context

## Performance Targets

- **Task Decomposition**: < 200ms for simple commands
- **Parallel Execution**: Up to 10 concurrent subtasks
- **Context Retrieval**: < 50ms from cache, < 200ms from database
- **End-to-End Latency**: < 5 seconds for typical multi-step tasks

## Error Handling

### Circuit Breaker Pattern

Protects against cascading failures when agents are unavailable:

- **CLOSED**: Normal operation, all requests allowed
- **OPEN**: Agent failing, reject requests for timeout period
- **HALF_OPEN**: Testing recovery, allow one request

Configuration:
- Failure threshold: 5 failures
- Timeout: 60 seconds
- Automatic recovery testing

### Retry Strategy

Exponential backoff for transient failures:

- Max attempts: 3
- Initial delay: 1 second
- Max delay: 60 seconds
- Exponential base: 2.0

### Fallback Routing

When primary agent is unavailable:
- Developer → Project Manager
- Business → Project Manager
- Communication → Project Manager
- Research → Project Manager
- Finance → Business → Project Manager

## Context Management

### Storage Strategy

**PostgreSQL (Persistent)**:
- Full conversation history
- Task associations
- Metadata and timestamps
- JSONB for flexible schema

**Redis (Cache)**:
- Recent contexts (TTL: 1 hour)
- Fast retrieval for active sessions
- Automatic expiration

**Vector Store (Semantic)**:
- Context embeddings
- Semantic similarity search
- Related context discovery

### Retention Policy

Default policy:
- Max age: 30 days
- Max messages per session: 1000
- Max sessions per user: 100
- Prune inactive: 7 days

## Integration with Other Layers

### SURFACE Layer
- Receives: `ParsedCommand` from Command Parser
- Returns: `AggregatedResult` with task output
- Streams: `TaskUpdate` for realtime progress

### CRUST Layer
- Sends: `Subtask` assignments to specialized agents
- Receives: `AgentResult` from agent execution
- Coordinates: Multi-agent collaboration

### PAN Layer
- Uses: Model Router for decomposition (Claude Sonnet 4.5)
- Delegates: Model selection to agents via CRUST layer

### TABLE Layer
- Stores: Task results in PostgreSQL
- Caches: Contexts and decompositions in Redis
- Searches: Similar patterns in Vector Store

## Testing

Run tests for INNER layer:

```bash
# Unit tests
pytest tests/inner/test_task_decomposition.py
pytest tests/inner/test_coordinator.py
pytest tests/inner/test_context_manager.py
pytest tests/inner/test_pipeline.py

# Integration tests
pytest tests/inner/test_integration.py

# Performance tests
pytest tests/inner/test_performance.py
```

## Configuration

Environment variables:

```bash
# Task Decomposition
TASK_DECOMPOSITION_CACHE_TTL_DAYS=7
TASK_DECOMPOSITION_SIMILARITY_THRESHOLD=0.85

# Coordinator
MAX_CONCURRENT_TASKS=10
RETRY_MAX_ATTEMPTS=3
RETRY_INITIAL_DELAY=1.0
RETRY_MAX_DELAY=60.0
CIRCUIT_BREAKER_THRESHOLD=5
CIRCUIT_BREAKER_TIMEOUT=60

# Context Manager
CONTEXT_CACHE_TTL_SECONDS=3600
CONTEXT_MAX_AGE_DAYS=30
CONTEXT_MAX_MESSAGES=1000
CONTEXT_PRUNE_INACTIVE_DAYS=7
```

## Future Enhancements

1. **Advanced Decomposition**: ML-based task decomposition learning from history
2. **Dynamic Scaling**: Auto-scale concurrent task limit based on load
3. **Smart Caching**: Predictive caching of likely next commands
4. **Context Compression**: Summarize long conversations for efficiency
5. **Multi-User Coordination**: Coordinate tasks across multiple users
6. **Real-time Streaming**: Stream partial results as they become available
7. **Cost Optimization**: Dynamic routing based on budget constraints
8. **Quality Feedback**: Learn from validation scores to improve decomposition

## Dependencies

- `asyncio`: Async execution
- `asyncpg`: PostgreSQL async driver
- `redis`: Redis client
- `qdrant-client`: Vector database client
- Common models from `insanity_cluster.common`
- TABLE layer components

## License

Part of the Insanity Cluster project.
