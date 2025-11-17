# Insanity Cluster

⚠️ **<span style="color:red">SECURITY WARNING</span>**
>
> **THIS PROJECT HAS BARELY ANY SECURITY AND IS ENTIRELY A LOCAL NETWORK PROJECT. IT WAS NEVER DESIGNED FOR PUBLIC ACCESS.** This project will be updated with all of the fancy hosted security features every Kubernetes cluster should have, but currently it is NOT suitable for production or internet-facing deployment. Please as well with any of our public facing projects that we do not optimize them (unless explicity stated) for production.

⚠️ **<span style="color:red">PSA</span>**

> **We are not liable for ANYTHING.** This project does NOT replace your employess this is for helping them not harming them. If this takes out a product or database we are not liable, if everyone hates it we are not liable and if you regret everything after installing we are certainaly not liable. you cloned this repo on your own time with your own internet connection. this is not prodction software this is well in progress. we use it internally to support our team and this is a recent change. so there are bugs errors and issues. you need TO BE AWARE WE ARE NOT LIABLE!!!!!!!

## YOU HAVE BEEN WARNED OF THE RISKS

## Insanity Cluster

Is a fully autonomous, real-time multi-modal AI system designed to function as a "team in a box."

## Architecture

The system operates across five architectural layers:

- **SURFACE Layer**: User interface and interaction (CLI, Web Dashboard, API Gateway, WebSocket)
- **INNER Layer**: Orchestration and task planning (Task Decomposition, Multi-Agent Coordination, Context Management)
- **CRUST Layer**: Specialized agent execution (Business, Developer, Communication, Research, Creative, Finance, Project Manager)
- **PAN Layer**: Model inference and integration (Model Router, Provider Adapters, Response Streamer)
- **TABLE Layer**: Infrastructure and foundation (Vector DB, PostgreSQL, Redis, Message Queue, Metrics)

## Quick Start

### Prerequisites

- Python 3.11 or higher
- Docker and Docker Compose
- Git

### Installation

1. Clone the repository:
```bash
git clone https://github.com/InsanityLabs/InsanityCluster.git
cd InsanityCluster
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.template .env
# Edit .env with your configuration
```

5. Start infrastructure services:
```bash
docker-compose up -d
```

6. Initialize the database:
```bash
# Run database migrations
alembic upgrade head

# Verify TABLE layer setup
python scripts/test_table_layer.py
```

### Development

Run the development server:
```bash
uvicorn insanity_cluster.surface.api:app --reload --host 0.0.0.0 --port 8000
```

Access the services:
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Grafana: http://localhost:3000 (admin/admin)
- Prometheus: http://localhost:9090

### Testing

Run tests:
```bash
pytest
```

Run tests with coverage:
```bash
pytest --cov=insanity_cluster --cov-report=html
```

## Configuration

The system supports multiple operating modes:

- **Local Mode**: Fully free, uses only local models
- **OpenRouter Free Mode**: Uses free models via OpenRouter
- **Mixed Mode**: Intelligent hybrid of local and paid models
- **Web Mode**: Premium paid models only
- **OpenRouter Paid Mode**: All models via OpenRouter

Configure the mode in `.env`:
```bash
OPERATING_MODE=mixed
DEFAULT_ROUTING_STRATEGY=cost_optimized
```

## Project Structure

```
insanity_cluster/
├── surface/          # SURFACE layer components
├── inner/            # INNER layer components
├── crust/            # CRUST layer agents
├── pan/              # PAN layer model integration
├── table/            # TABLE layer infrastructure
└── common/           # Shared utilities and models

config/               # Configuration files
scripts/              # Utility scripts
tests/                # Test suite
docs/                 # Documentation
```

## Documentation

- [Architecture Overview](docs/architecture.md)
- [TABLE Layer Documentation](insanity_cluster/table/README.md)
- [API Reference](docs/api.md)
- [Agent Development Guide](docs/agents.md)
- [Deployment Guide](docs/deployment.md)

## TABLE Layer Components

The TABLE layer provides the foundational infrastructure:

### PostgreSQL Database
- Async connection pooling with asyncpg
- SQLAlchemy ORM models
- Alembic migrations
- Health monitoring

### Redis Cache & Message Queues
- High-speed caching with TTL
- Session token management
- Redis Streams for message queues
- Distributed locks

### Qdrant Vector Database
- Semantic search for task patterns
- Context embeddings
- Agent knowledge storage
- 1536-dimensional vectors

### Prometheus Metrics
- Request and task metrics
- Layer-specific latency tracking
- Model inference metrics
- Cost tracking
- Queue depth monitoring

### Grafana Dashboards
- Real-time system overview
- Performance metrics visualization
- Cost tracking
- Error rate monitoring

For detailed TABLE layer documentation, see [insanity_cluster/table/README.md](insanity_cluster/table/README.md)

## License

GNU GENERAL PUBLIC LICENSE v3 (This might get changed to a custom licence we use for our open sourced projects)

## Contributing

For Contributing documentation, see [CONTRIBUTING.md](CONTRIBUTING.md)