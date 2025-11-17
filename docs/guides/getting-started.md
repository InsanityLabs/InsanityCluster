# Getting Started with Insanity Cluster

Welcome to Insanity Cluster - your autonomous AI team in a box! This guide will help you get up and running in minutes.

## What is Insanity Cluster?

Insanity Cluster is a fully autonomous, real-time multi-modal AI system that functions as a complete team. It can:

- Write and review code
- Handle phone calls and emails
- Form LLCs and manage legal documents
- Conduct research and analysis
- Create content and designs
- Manage finances and projects

All through simple natural language commands.

## Quick Start

### 1. Installation

**Using Docker (Recommended):**

```bash
# Clone the repository
git clone https://github.com/insanity-cluster/insanity-cluster.git
cd insanity-cluster

# Copy environment template
cp .env.template .env

# Edit .env with your API keys (optional for local mode)
nano .env

# Start the system
docker-compose up -d
```

**Using Python:**

```bash
# Clone the repository
git clone https://github.com/insanity-cluster/insanity-cluster.git
cd insanity-cluster

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up database
python scripts/init_database.py

# Start the system
python -m insanity_cluster.surface.main
```

### 2. First Command

Once the system is running, open your browser to `http://localhost:8000` or use the CLI:

**Via Web Dashboard:**
1. Navigate to `http://localhost:8000`
2. Enter your first command: "Write a Python function to calculate fibonacci numbers"
3. Watch as the system decomposes the task and executes it

**Via CLI:**
```bash
insanity-cluster task create "Write a Python function to calculate fibonacci numbers"
```

**Via API:**
```bash
curl -X POST http://localhost:8000/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{"command": "Write a Python function to calculate fibonacci numbers"}'
```

### 3. Monitor Progress

Watch real-time progress in the web dashboard or via WebSocket:

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log(message);
};
```

## Understanding Operating Modes

Insanity Cluster supports five operating modes that determine which AI models are used:

### Local Mode (Free)
- Uses only local models (Ollama, LM Studio)
- Zero cost, maximum privacy
- Best for: Development, privacy-sensitive tasks, offline work

```bash
insanity-cluster config set-mode local
```

### OpenRouter Free Mode
- Uses free models via OpenRouter
- No direct costs (rate-limited)
- Best for: Learning, experimentation, low-budget projects

```bash
insanity-cluster config set-mode openrouter-free
```

### Mixed Mode (Recommended)
- Combines local and paid models intelligently
- Simple tasks use local models, complex tasks use paid models
- Best for: Cost optimization with quality when needed

```bash
insanity-cluster config set-mode mixed
```

### Web Mode
- Uses premium paid models (OpenAI, Anthropic)
- Maximum quality and speed
- Best for: Production, mission-critical tasks

```bash
insanity-cluster config set-mode web
```

### OpenRouter Paid Mode
- All models via OpenRouter (unified billing)
- Access to both free and paid models
- Best for: Simplified billing, model variety

```bash
insanity-cluster config set-mode openrouter-paid
```

## Basic Commands

### Task Management

**Create a task:**
```bash
insanity-cluster task create "Your command here"
```

**Check task status:**
```bash
insanity-cluster task status <task_id>
```

**Get task result:**
```bash
insanity-cluster task result <task_id>
```

**Cancel a task:**
```bash
insanity-cluster task cancel <task_id>
```

**List recent tasks:**
```bash
insanity-cluster task list --limit 10
```

### Configuration

**View current configuration:**
```bash
insanity-cluster config show
```

**Set operating mode:**
```bash
insanity-cluster config set-mode mixed
```

**Set cost limits:**
```bash
insanity-cluster config set-limit --per-task 1.00 --per-day 50.00
```

**Configure model preferences:**
```bash
insanity-cluster config set-agent developer --model claude-sonnet-4.5
```

### Authentication

**Generate API key:**
```bash
insanity-cluster auth create-key --name "My App" --role user
```

**List API keys:**
```bash
insanity-cluster auth list-keys
```

**Revoke API key:**
```bash
insanity-cluster auth revoke-key <key_id>
```

## Example Use Cases

### 1. Code Generation

```bash
insanity-cluster task create "Create a REST API in Python using FastAPI with endpoints for user management"
```

The Developer Agent will:
- Generate the FastAPI application
- Create user models and schemas
- Implement CRUD endpoints
- Add authentication
- Generate tests

### 2. Business Formation

```bash
insanity-cluster task create "Form an LLC in Delaware named TechStartup Inc"
```

The Business Agent will:
- Generate LLC formation documents
- File with Delaware Secretary of State (via LegalZoom API)
- Create operating agreement
- Generate EIN application

### 3. Research and Analysis

```bash
insanity-cluster task create "Research the top 5 project management tools and create a comparison report"
```

The Research Agent will:
- Search for project management tools
- Gather data from multiple sources
- Analyze features and pricing
- Generate structured report with citations

### 4. Communication

```bash
insanity-cluster task create "Send an email to team@example.com with project status update"
```

The Communication Agent will:
- Compose professional email
- Include relevant project details
- Send via configured email service

### 5. Multi-Agent Tasks

```bash
insanity-cluster task create "Create a landing page for my SaaS product, write marketing copy, and set up email automation"
```

Multiple agents will collaborate:
- Developer Agent: Creates landing page
- Creative Agent: Writes marketing copy
- Communication Agent: Sets up email automation

## Configuration Files

### Environment Variables (.env)

```bash
# Operating Mode
OPERATING_MODE=mixed

# API Keys (optional for local mode)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
OPENROUTER_API_KEY=sk-or-...

# Local Model Endpoints
OLLAMA_ENDPOINT=http://localhost:11434
LMSTUDIO_ENDPOINT=http://localhost:1234

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/insanity_cluster

# Redis
REDIS_URL=redis://localhost:6379

# Qdrant
QDRANT_URL=http://localhost:6333

# Cost Limits
MAX_COST_PER_TASK=1.00
MAX_COST_PER_DAY=50.00

# External Services (optional)
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
SENDGRID_API_KEY=...
```

### User Configuration (~/.insanity-cluster/config.yaml)

```yaml
# Default operating mode
mode: mixed

# Model preferences
agents:
  developer:
    primary_model: claude-sonnet-4.5
    fallback_models:
      - gpt-5-codex
      - local:codellama
  
  communication:
    primary_model: claude-haiku-4.5
    fallback_models:
      - local:mistral-7b

# Cost limits
cost_limits:
  per_task: 1.00
  per_day: 50.00
  warning_threshold: 0.80

# Routing strategy
routing_strategy: cost_optimized

# Mixed mode settings
mixed_mode:
  local_complexity_threshold: 0.5
  paid_model_trigger: complexity
```

## Web Dashboard

Access the web dashboard at `http://localhost:8000`:

### Features

1. **Task Monitor**: View active tasks and their progress
2. **Cost Dashboard**: Track spending and usage
3. **Configuration**: Manage operating mode and settings
4. **Metrics**: View performance metrics and latency
5. **History**: Browse past tasks and results

### Dashboard Sections

**Tasks Tab:**
- Active tasks with real-time progress
- Task queue and status
- Agent activity
- Cancel/retry options

**Metrics Tab:**
- Cost tracking (total, per-task, per-model)
- Latency metrics (p50, p95, p99)
- Success/failure rates
- Model usage statistics

**Config Tab:**
- Operating mode selection
- Agent configuration
- Cost limits
- Model preferences

## Troubleshooting

### Common Issues

**1. "Connection refused" error**
- Ensure all services are running: `docker-compose ps`
- Check logs: `docker-compose logs`
- Verify ports are not in use: `netstat -an | grep 8000`

**2. "API key invalid" error**
- Check your .env file has correct API keys
- Verify keys are not expired
- For local mode, API keys are optional

**3. Tasks stuck in "queued" status**
- Check agent workers are running
- View logs: `docker-compose logs inner`
- Restart services: `docker-compose restart`

**4. High costs**
- Switch to local or mixed mode
- Set cost limits: `insanity-cluster config set-limit --per-day 10.00`
- Review model usage in dashboard

**5. Slow responses**
- Check model endpoint latency
- Consider using faster models (Claude Haiku, gpt-5-mini)
- Enable local models for simple tasks

### Getting Help

- **Documentation**: https://docs.insanitycluster.com
- **GitHub Issues**: https://github.com/insanity-cluster/insanity-cluster/issues
- **Discord**: https://discord.gg/insanity-cluster
- **Email**: support@insanitycluster.com

## Next Steps

Now that you're up and running:

1. **Explore Agents**: Learn about each specialized agent's capabilities
2. **Configure Models**: Optimize model selection for your use case
3. **Set Up Webhooks**: Get notified when tasks complete
4. **Integrate APIs**: Build custom applications on top of Insanity Cluster
5. **Deploy to Production**: Follow the deployment guide for production setup

## Best Practices

1. **Start with Local Mode**: Test and develop without costs
2. **Use Mixed Mode**: Balance cost and quality for production
3. **Set Cost Limits**: Prevent unexpected expenses
4. **Monitor Metrics**: Track performance and costs
5. **Use Webhooks**: Get real-time notifications
6. **Cache Results**: Avoid redundant expensive operations
7. **Batch Similar Tasks**: Process multiple related tasks together

## Quick Reference

```bash
# Start system
docker-compose up -d

# Create task
insanity-cluster task create "Your command"

# Check status
insanity-cluster task status <task_id>

# View logs
docker-compose logs -f

# Stop system
docker-compose down

# Update system
git pull && docker-compose up -d --build
```

Welcome to the future of autonomous AI systems! 🚀
