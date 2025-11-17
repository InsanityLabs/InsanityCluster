# Configuration Management Guide

## Overview

This guide covers all aspects of configuring Insanity Cluster, from basic setup to advanced customization.

## Configuration Files

### 1. Environment Variables (.env)

Located in the project root, this file contains system-wide settings:

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

# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/insanity_cluster
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Redis Configuration
REDIS_URL=redis://localhost:6379
REDIS_MAX_CONNECTIONS=50

# Qdrant Vector Database
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=

# Cost Limits
MAX_COST_PER_TASK=1.00
MAX_COST_PER_DAY=50.00
COST_WARNING_THRESHOLD=0.80

# Performance Settings
MAX_CONCURRENT_TASKS=10
TASK_TIMEOUT_SECONDS=300
MODEL_TIMEOUT_SECONDS=60

# External Services (optional)
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
SENDGRID_API_KEY=
GOOGLE_CALENDAR_CREDENTIALS=
LEGALZOOM_API_KEY=

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=logs/insanity_cluster.log

# Security
JWT_SECRET_KEY=your-secret-key-here
API_KEY_SALT=your-salt-here
SESSION_TIMEOUT_HOURS=24

# Monitoring
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
ENABLE_METRICS=true
ENABLE_TRACING=true
```

### 2. User Configuration (~/.insanity-cluster/config.yaml)

User-specific settings that override system defaults:

```yaml
# Operating Mode
mode: mixed

# Default Routing Strategy
default_strategy: cost_optimized

# Cost Limits
cost_limits:
  per_task: 1.00
  per_day: 50.00
  per_month: 1000.00
  warning_threshold: 0.80

# Mixed Mode Settings
mixed_mode:
  local_complexity_threshold: 0.5
  paid_model_trigger: complexity  # complexity, failure, explicit
  fallback_enabled: true

# Agent Configuration
agents:
  developer:
    primary_model: claude-sonnet-4.5
    fallback_models:
      - gpt-5-codex
      - local:codellama
    max_cost: 1.00
    fallback_to_paid: true
  
  communication:
    primary_model: claude-haiku-4.5
    fallback_models:
      - local:mistral
      - gpt-5-mini
    max_cost: 0.10
    fallback_to_paid: true
  
  business:
    primary_model: claude-opus-4.1
    fallback_models:
      - gpt-5.1
      - claude-sonnet-4.5
    max_cost: 2.00
    fallback_to_paid: true
  
  research:
    primary_model: claude-sonnet-4.5
    fallback_models:
      - gpt-5-mini
      - local:llama3:70b
    max_cost: 0.50
    fallback_to_paid: true
  
  creative:
    primary_model: gpt-5.1
    fallback_models:
      - claude-sonnet-4.5
      - local:llama3:70b
    max_cost: 0.50
    fallback_to_paid: true
  
  finance:
    primary_model: gpt-5-mini
    fallback_models:
      - claude-haiku-4.5
      - local:mistral
    max_cost: 0.20
    fallback_to_paid: true
  
  project_manager:
    primary_model: gpt-5-mini
    fallback_models:
      - claude-haiku-4.5
      - local:mistral
    max_cost: 0.10
    fallback_to_paid: true

# Task Type Overrides
task_type_overrides:
  code_generation:
    model_override: claude-sonnet-4.5
    strategy_override: quality_first
    allow_local: false
    allow_paid: true
  
  code_review:
    model_override: gpt-5-codex
    strategy_override: quality_first
    allow_local: false
    allow_paid: true
  
  simple_chat:
    model_override: local:phi3
    strategy_override: speed_first
    allow_local: true
    allow_paid: false
  
  legal_analysis:
    model_override: claude-opus-4.1
    strategy_override: quality_first
    allow_local: false
    allow_paid: true
  
  financial_calculations:
    model_override: gpt-5-mini
    strategy_override: cost_optimized
    allow_local: true
    allow_paid: true

# Model Provider Configuration
providers:
  openai:
    enabled: true
    rate_limit: 100  # requests per minute
    timeout: 30  # seconds
    retry_attempts: 3
    retry_delay: 1  # seconds
  
  anthropic:
    enabled: true
    rate_limit: 50
    timeout: 60
    retry_attempts: 3
    retry_delay: 1
  
  openrouter:
    enabled: true
    use_free_tier: true
    use_paid_tier: true
    rate_limit: 100
    timeout: 30
    retry_attempts: 3
    retry_delay: 1
  
  ollama:
    enabled: true
    auto_pull: true  # Automatically pull missing models
    timeout: 120
  
  lmstudio:
    enabled: true
    timeout: 120

# Retry Policies
retry_policies:
  max_attempts: 3
  exponential_backoff: true
  initial_delay: 1  # seconds
  max_delay: 60  # seconds
  backoff_multiplier: 2

# Circuit Breaker
circuit_breaker:
  enabled: true
  failure_threshold: 5
  timeout: 60  # seconds
  half_open_attempts: 1

# Caching
caching:
  enabled: true
  command_parsing_ttl: 604800  # 7 days
  context_ttl: 3600  # 1 hour
  task_decomposition_ttl: 86400  # 1 day

# Webhooks
webhooks:
  enabled: true
  retry_attempts: 5
  retry_schedule: [60, 300, 900, 3600, 21600]  # seconds
  timeout: 5  # seconds

# Notifications
notifications:
  email:
    enabled: false
    smtp_host: smtp.gmail.com
    smtp_port: 587
    from_address: notifications@insanitycluster.com
  
  slack:
    enabled: false
    webhook_url: https://hooks.slack.com/services/...
  
  discord:
    enabled: false
    webhook_url: https://discord.com/api/webhooks/...

# Data Retention
data_retention:
  task_history_days: 90
  context_history_days: 30
  metrics_history_days: 365
  logs_history_days: 30
```

### 3. Project Configuration (.insanity-cluster.yaml)

Project-specific settings (optional):

```yaml
# Project name
name: my-project

# Project-specific mode
mode: mixed

# Project-specific cost limits
cost_limits:
  per_task: 0.50
  per_day: 10.00

# Project-specific agent configuration
agents:
  developer:
    primary_model: local:codellama
```

## Configuration via CLI

### View Configuration

```bash
# View all configuration
insanity-cluster config show

# View specific section
insanity-cluster config show --section agents
insanity-cluster config show --section cost_limits
```

### Set Operating Mode

```bash
# Set mode
insanity-cluster config set-mode local
insanity-cluster config set-mode mixed
insanity-cluster config set-mode web

# Set mode with strategy
insanity-cluster config set-mode mixed --strategy cost-optimized
```

### Configure Cost Limits

```bash
# Set per-task limit
insanity-cluster config set-limit --per-task 1.00

# Set daily limit
insanity-cluster config set-limit --per-day 50.00

# Set monthly limit
insanity-cluster config set-limit --per-month 1000.00

# Set warning threshold
insanity-cluster config set-limit --warning-threshold 0.80
```

### Configure Agents

```bash
# Set agent primary model
insanity-cluster config set-agent developer --model claude-sonnet-4.5

# Set agent fallback models
insanity-cluster config set-agent developer --fallback gpt-5-codex,local:codellama

# Set agent cost limit
insanity-cluster config set-agent developer --max-cost 1.00

# Enable/disable fallback to paid
insanity-cluster config set-agent developer --fallback-to-paid true
```

### Configure Task Types

```bash
# Set task type model
insanity-cluster config set-task-type code_generation --model claude-sonnet-4.5

# Set task type strategy
insanity-cluster config set-task-type code_generation --strategy quality-first

# Allow/disallow local models
insanity-cluster config set-task-type code_generation --allow-local false

# Allow/disallow paid models
insanity-cluster config set-task-type simple_chat --allow-paid false
```

### Configure Providers

```bash
# Enable/disable provider
insanity-cluster config set-provider openai --enabled true

# Set rate limit
insanity-cluster config set-provider openai --rate-limit 100

# Set timeout
insanity-cluster config set-provider openai --timeout 30
```

### Import/Export Configuration

```bash
# Export configuration
insanity-cluster config export --output config.yaml

# Import configuration
insanity-cluster config import --input config.yaml

# Reset to defaults
insanity-cluster config reset
```

## Configuration via API

### Get Configuration

```bash
curl -X GET http://localhost:8000/v1/config/mode \
  -H "X-API-Key: your-api-key"
```

### Update Configuration

```bash
curl -X PUT http://localhost:8000/v1/config/mode \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "mode": "MIXED",
    "default_strategy": "COST_OPTIMIZED",
    "local_complexity_threshold": 0.5,
    "max_cost_per_day": 50.00
  }'
```

## Configuration via Dashboard

### Accessing Configuration

1. Navigate to `http://localhost:8000`
2. Click on "Configuration" tab
3. Select configuration section

### Mode Selection

1. Click on "Mode" dropdown
2. Select desired mode
3. Configure mode-specific settings
4. Click "Save"

### Agent Configuration

1. Navigate to "Agents" section
2. Select agent from list
3. Configure primary and fallback models
4. Set cost limits
5. Click "Save"

### Task Type Configuration

1. Navigate to "Task Types" section
2. Click "Add Task Type" or select existing
3. Configure model and strategy
4. Set local/paid permissions
5. Click "Save"

## Advanced Configuration

### Custom Routing Strategies

Create custom routing strategies:

```yaml
# ~/.insanity-cluster/strategies/custom.yaml
name: custom_development
description: Optimized for development tasks

rules:
  - condition:
      task_complexity: < 0.3
    action:
      model: local:phi3
  
  - condition:
      task_type: code_generation
    action:
      model: claude-sonnet-4.5
  
  - condition:
      cost_so_far_today: > 40.00
    action:
      model: local:mistral
  
  - condition:
      requires_long_context: true
    action:
      model: claude-sonnet-4.5
  
  - default:
      model: gpt-5-mini
```

Load custom strategy:

```bash
insanity-cluster config load-strategy custom_development
```

### Environment-Specific Configuration

Use different configurations for different environments:

```bash
# Development
export INSANITY_CLUSTER_ENV=development
insanity-cluster config load development.yaml

# Staging
export INSANITY_CLUSTER_ENV=staging
insanity-cluster config load staging.yaml

# Production
export INSANITY_CLUSTER_ENV=production
insanity-cluster config load production.yaml
```

### Configuration Validation

Validate configuration before applying:

```bash
# Validate configuration file
insanity-cluster config validate config.yaml

# Test configuration
insanity-cluster config test --mode mixed --dry-run
```

## Configuration Best Practices

### 1. Start Simple

Begin with default configuration and adjust based on usage:

```yaml
mode: mixed
default_strategy: cost_optimized
cost_limits:
  per_day: 50.00
```

### 2. Monitor and Adjust

Track costs and performance for first week:

```bash
# Daily cost check
insanity-cluster metrics costs --period day

# Adjust threshold if needed
insanity-cluster config set mixed-threshold 0.6
```

### 3. Use Task Type Overrides

Configure critical tasks explicitly:

```yaml
task_type_overrides:
  legal_analysis:
    model_override: claude-opus-4.1
    strategy_override: quality_first
  
  simple_chat:
    model_override: local:phi3
```

### 4. Set Cost Limits

Always set cost limits to prevent surprises:

```yaml
cost_limits:
  per_task: 1.00
  per_day: 50.00
  warning_threshold: 0.80
```

### 5. Version Control

Keep configuration in version control:

```bash
# Add to git
git add .insanity-cluster.yaml
git commit -m "Update configuration"
```

### 6. Environment Variables for Secrets

Never commit secrets to version control:

```bash
# Use environment variables
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...

# Or use .env file (add to .gitignore)
echo ".env" >> .gitignore
```

### 7. Test Configuration Changes

Test changes before applying to production:

```bash
# Test in development
insanity-cluster config test --env development

# Apply to production
insanity-cluster config apply --env production
```

## Configuration Presets

### Development Preset

```yaml
mode: local
default_strategy: speed_first
cost_limits:
  per_task: 0.00
  per_day: 0.00
caching:
  enabled: true
```

### Production Preset

```yaml
mode: mixed
default_strategy: cost_optimized
local_complexity_threshold: 0.5
cost_limits:
  per_task: 1.00
  per_day: 100.00
  warning_threshold: 0.80
retry_policies:
  max_attempts: 3
circuit_breaker:
  enabled: true
```

### High-Quality Preset

```yaml
mode: web
default_strategy: quality_first
cost_limits:
  per_task: 5.00
  per_day: 200.00
agents:
  developer:
    primary_model: claude-sonnet-4.5
  business:
    primary_model: claude-opus-4.1
```

### Budget-Conscious Preset

```yaml
mode: mixed
default_strategy: cost_optimized
local_complexity_threshold: 0.7
cost_limits:
  per_task: 0.50
  per_day: 10.00
task_type_overrides:
  simple_chat:
    model_override: local:phi3
    allow_paid: false
```

## Troubleshooting Configuration

### Configuration Not Loading

**Problem**: Changes not taking effect

**Solutions**:
1. Restart services: `docker-compose restart`
2. Check file permissions: `ls -la ~/.insanity-cluster/`
3. Validate syntax: `insanity-cluster config validate`
4. Check logs: `docker-compose logs surface`

### Invalid Configuration

**Problem**: Configuration validation fails

**Solutions**:
1. Check YAML syntax
2. Verify required fields
3. Check value types and ranges
4. Review error messages

### API Keys Not Working

**Problem**: Authentication failures

**Solutions**:
1. Verify API keys are correct
2. Check environment variables: `env | grep API_KEY`
3. Ensure keys are not expired
4. Test keys directly with provider

### Cost Limits Not Enforced

**Problem**: Spending exceeds limits

**Solutions**:
1. Verify limits are set: `insanity-cluster config show --section cost_limits`
2. Check warning threshold
3. Review task costs in dashboard
4. Enable cost tracking: `ENABLE_COST_TRACKING=true`

## Support

For configuration help:
- Documentation: https://docs.insanitycluster.com/configuration
- Discord: https://discord.gg/insanity-cluster
- Email: support@insanitycluster.com
