# TABLE Layer - Infrastructure and Foundation

The TABLE layer provides the foundational infrastructure for the Insanity Cluster system, including databases, caching, message queues, vector storage, and metrics collection.

## Components

### 1. PostgreSQL Database (`database.py`)

Manages relational data storage with async connection pooling using asyncpg and SQLAlchemy.

**Features:**
- Async connection pooling (20 connections, 10 overflow)
- SQLAlchemy ORM with async support
- Raw asyncpg queries for performance-critical operations
- Health check monitoring
- Automatic connection recycling

**Usage:**
```python
from insanity_cluster.table import db_manager, get_session

# Initialize
await db_manager.initialize()

# Use with SQLAlchemy ORM
async with db_manager.session() as session:
    user = await session.get(User, user_id)

# Use raw queries for performance
result = await db_manager.execute_raw("SELECT * FROM users WHERE email = $1", email)

# Health check
is_healthy = await db_manager.health_check()
```

**Models:**
- `User`: User authentication and authorization
- `Task`: Task tracking and execution history
- `Context`: Session context and conversation history
- `Metric`: Performance and cost metrics

### 2. Redis Cache & Message Queues (`redis_manager.py`)

Provides high-speed caching and message queue functionality using Redis Streams.

**Features:**
- Connection pooling (50 connections)
- Key-value caching with TTL
- Session token management
- Command parsing cache
- Redis Streams for message queues
- Distributed locks

**Usage:**
```python
from insanity_cluster.table import redis_manager

# Initialize
await redis_manager.initialize()

# Cache operations
await redis_manager.cache_set("key", {"data": "value"}, ttl=3600)
value = await redis_manager.cache_get("key")

# Session tokens
await redis_manager.store_session_token(user_id, token, ttl=86400)
is_valid = await redis_manager.validate_session_token(user_id, token)

# Message queues
message_id = await redis_manager.enqueue_task({"task": "data"})
messages = await redis_manager.dequeue_tasks(count=10)

# Distributed locks
lock = await redis_manager.acquire_lock("resource_name", timeout=10)
if lock:
    # Do work
    await redis_manager.release_lock(lock)
```

**Queue Streams:**
- `task_queue`: New tasks for INNER layer
- `agent_queue:{agent_type}`: Agent-specific task queues
- `webhook_queue`: Webhook delivery queue

### 3. Qdrant Vector Database (`vector_store.py`)

Manages vector embeddings for semantic search and pattern matching.

**Features:**
- Three collections: task_patterns, context_embeddings, agent_knowledge
- Cosine similarity search
- Metadata filtering
- Batch operations
- 1536-dimensional vectors (OpenAI ada-002 compatible)

**Usage:**
```python
from insanity_cluster.table import vector_store

# Initialize
await vector_store.initialize()

# Store embeddings
point_id = await vector_store.store_embedding(
    collection_name=vector_store.TASK_PATTERNS,
    vector=embedding_vector,
    payload={"command": "...", "task_graph": {...}}
)

# Search similar
results = await vector_store.search_similar(
    collection_name=vector_store.TASK_PATTERNS,
    query_vector=query_embedding,
    limit=5,
    score_threshold=0.8
)

# Task patterns
await vector_store.store_task_pattern(command, embedding, task_graph)
similar_tasks = await vector_store.search_similar_tasks(query_embedding)

# Context embeddings
await vector_store.store_context_embedding(session_id, user_id, embedding, context_data)
similar_contexts = await vector_store.search_similar_contexts(query_embedding, user_id)
```

**Collections:**
- `task_patterns`: Cached task decomposition patterns
- `context_embeddings`: Session context for semantic retrieval
- `agent_knowledge`: Domain-specific knowledge for agents

### 4. Embedding Generator (`embeddings.py`)

Generates vector embeddings for text using OpenAI or fallback methods.

**Features:**
- OpenAI text-embedding-ada-002 support
- In-memory caching
- Batch generation
- Fallback hash-based embeddings (development only)

**Usage:**
```python
from insanity_cluster.table import generate_embedding, generate_embeddings_batch

# Initialize
await embedding_generator.initialize()

# Single embedding
embedding = await generate_embedding("text to embed")

# Batch embeddings
embeddings = await generate_embeddings_batch(["text1", "text2", "text3"])
```

### 5. Prometheus Metrics (`metrics.py`)

Collects and exports metrics for monitoring and observability.

**Features:**
- Request metrics (count, latency)
- Task metrics (count, duration, active)
- Layer-specific latency tracking
- Model inference metrics (requests, latency, tokens, cost)
- Agent execution metrics
- Queue depth monitoring
- Error tracking
- Cache hit/miss rates
- WebSocket connection tracking
- Database query metrics

**Usage:**
```python
from insanity_cluster.table import metrics_collector

# Record metrics
metrics_collector.record_request("SURFACE", "/tasks", "success", 0.15)
metrics_collector.record_task("success", 5.2)
metrics_collector.record_model_request("openai", "gpt-5-mini", "success", 1.5, 
                                       input_tokens=100, output_tokens=50, cost=0.001)

# Update gauges
metrics_collector.set_active_tasks(10)
metrics_collector.increment_active_agents("developer")

# Context managers for timing
async with metrics_collector.time_request("SURFACE", "/tasks"):
    # Do work
    pass

async with metrics_collector.time_task():
    # Execute task
    pass

# Export metrics (for Prometheus scraping)
metrics_data = metrics_collector.export_metrics()
```

**Key Metrics:**
- `insanity_requests_total`: Total requests by layer/endpoint/status
- `insanity_request_latency_seconds`: Request latency histogram
- `insanity_tasks_total`: Total tasks by status
- `insanity_task_duration_seconds`: Task duration histogram
- `insanity_active_tasks`: Current active tasks
- `insanity_layer_latency_milliseconds`: Per-layer latency
- `insanity_model_requests_total`: Model inference requests
- `insanity_model_latency_seconds`: Model inference latency
- `insanity_cost_dollars_total`: Total cost by provider/model
- `insanity_agent_executions_total`: Agent executions
- `insanity_queue_depth`: Queue depths
- `insanity_errors_total`: Errors by layer/type
- `insanity_cache_hits_total`: Cache hits
- `insanity_websocket_connections`: Active WebSocket connections

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    api_key_hash VARCHAR(255),
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Tasks Table
```sql
CREATE TABLE tasks (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    command TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    task_graph JSONB,
    result JSONB,
    cost DECIMAL(10, 4) DEFAULT 0.0,
    latency_ms INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Context Table
```sql
CREATE TABLE context (
    session_id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    context_data JSONB NOT NULL,
    last_accessed TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### Metrics Table
```sql
CREATE TABLE metrics (
    id SERIAL PRIMARY KEY,
    task_id UUID REFERENCES tasks(id),
    layer VARCHAR(50) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    metric_value FLOAT NOT NULL,
    timestamp TIMESTAMP DEFAULT NOW()
);
```

## Initialization

### Full Initialization
```python
from insanity_cluster.table import init_table_layer, close_table_layer

# Initialize all components
await init_table_layer()

# ... use components ...

# Clean shutdown
await close_table_layer()
```

### Individual Components
```python
from insanity_cluster.table import (
    init_db, init_redis, init_vector_store, init_embeddings
)

await init_db()
await init_redis()
await init_vector_store()
await init_embeddings()
```

## Database Migrations

### Using Alembic

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Show current version
alembic current

# Show migration history
alembic history
```

## Docker Services

All TABLE layer services are configured in `docker-compose.yml`:

```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f postgres
docker-compose logs -f redis
docker-compose logs -f qdrant
docker-compose logs -f prometheus
docker-compose logs -f grafana

# Stop services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

## Monitoring

### Prometheus
- URL: http://localhost:9090
- Scrapes metrics from application endpoint
- Configuration: `config/prometheus.yml`

### Grafana
- URL: http://localhost:3000
- Default credentials: admin/admin
- Dashboards: `config/grafana/dashboards/`
- Pre-configured dashboard: "Insanity Cluster - Overview"

### Key Dashboards

1. **Overview Dashboard**: System-wide metrics
   - Request rate and latency
   - Active tasks and completion rate
   - Cost tracking
   - Layer latency (p50, p95, p99)
   - Error rates
   - Queue depths

2. **Model Performance**: AI model metrics
   - Inference latency by provider/model
   - Token usage
   - Cost per model
   - Request success/failure rates

3. **Agent Activity**: Agent execution metrics
   - Active agents by type
   - Execution latency
   - Success/failure rates

## Testing

Run the TABLE layer test suite:

```bash
# Ensure services are running
docker-compose up -d

# Run tests
python scripts/test_table_layer.py
```

The test script verifies:
- PostgreSQL connection and queries
- Redis cache operations
- Qdrant vector database
- Metrics collection

## Configuration

All configuration is managed through environment variables (see `.env.template`):

```bash
# Database
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=insanity_cluster
POSTGRES_USER=insanity
POSTGRES_PASSWORD=insanity_dev_password

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Qdrant
QDRANT_HOST=localhost
QDRANT_PORT=6333

# Monitoring
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
```

## Performance Considerations

### Database
- Connection pool: 20 connections + 10 overflow
- Use raw asyncpg for performance-critical queries
- JSONB columns for flexible schema
- Indexes on frequently queried columns

### Redis
- Connection pool: 50 connections
- Use TTL for automatic cleanup
- Redis Streams for reliable message queues
- Distributed locks for coordination

### Vector Store
- Batch operations for bulk inserts
- Score thresholds to limit results
- Metadata filtering for targeted searches
- Regular collection maintenance

### Metrics
- Histogram buckets tuned for expected latencies
- Minimal overhead on hot paths
- Async context managers for timing
- Efficient label cardinality

## Troubleshooting

### Database Connection Issues
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# View logs
docker-compose logs postgres

# Test connection
psql -h localhost -U insanity -d insanity_cluster
```

### Redis Connection Issues
```bash
# Check if Redis is running
docker-compose ps redis

# Test connection
redis-cli ping

# View logs
docker-compose logs redis
```

### Qdrant Connection Issues
```bash
# Check if Qdrant is running
docker-compose ps qdrant

# Test connection
curl http://localhost:6333/health

# View logs
docker-compose logs qdrant
```

### Metrics Not Appearing
```bash
# Check Prometheus targets
# Visit: http://localhost:9090/targets

# Verify metrics endpoint
curl http://localhost:8000/metrics

# Check Prometheus configuration
cat config/prometheus.yml
```
