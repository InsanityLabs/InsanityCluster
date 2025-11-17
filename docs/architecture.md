# Insanity Cluster Architecture

## Overview

The Insanity Cluster is built on a five-layer architecture designed for realtime performance, intelligent routing, and scalability.

## Layer Descriptions

### SURFACE Layer
The user-facing layer that handles all interactions:
- **CLI Interface**: Command-line tool for task submission
- **Web Dashboard**: Real-time monitoring and control interface
- **API Gateway**: REST API for external integrations
- **WebSocket Server**: Bidirectional realtime communication

### INNER Layer
The orchestration layer that manages task execution:
- **Task Decomposition Engine**: Breaks complex commands into subtasks
- **Multi-Agent Coordinator**: Manages parallel and sequential execution
- **Context Manager**: Maintains conversation and task state

### CRUST Layer
The specialized agent layer with domain expertise:
- **Business Agent**: Legal, compliance, and business operations
- **Developer Agent**: Code generation, review, and debugging
- **Communication Agent**: Phone calls, emails, and scheduling
- **Research Agent**: Data gathering and analysis
- **Creative Agent**: Content creation and design
- **Finance Agent**: Accounting and financial management
- **Project Manager Agent**: Planning and tracking

### PAN Layer
The model integration layer:
- **Model Router**: Selects optimal AI models based on strategy
- **Provider Adapters**: Unified interface for different AI providers
- **Response Streamer**: Realtime token-by-token output
- **Fallback Handler**: Automatic retry with alternative models

### TABLE Layer
The infrastructure foundation:
- **PostgreSQL**: Persistent storage for tasks and users
- **Redis**: High-speed caching and message queues
- **Qdrant**: Vector database for semantic search
- **Prometheus**: Metrics collection
- **Grafana**: Visualization and dashboards

## Data Flow

1. User submits command via SURFACE layer
2. Command is parsed and authenticated (< 100ms)
3. INNER layer decomposes into subtasks (< 200ms)
4. CRUST layer agents execute subtasks in parallel
5. PAN layer routes to optimal AI models
6. Results are aggregated and streamed back to user
7. TABLE layer stores metrics and context

## Operating Modes

The system supports five operating modes:

1. **Local Mode**: Free, uses only local models
2. **OpenRouter Free**: Free models via OpenRouter
3. **Mixed Mode**: Hybrid of local and paid models
4. **Web Mode**: Premium paid models only
5. **OpenRouter Paid**: All models via OpenRouter

## Performance Targets

- Command acknowledgment: < 100ms
- Task decomposition: < 200ms
- Voice interaction round-trip: < 1s
- Concurrent tasks: 100+
- WebSocket latency: Sub-second

## Security

- TLS 1.3 for all communications
- AES-256 encryption at rest
- JWT authentication
- Role-based access control
- PII detection and masking
