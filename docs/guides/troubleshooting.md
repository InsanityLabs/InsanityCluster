# Troubleshooting Guide

## Quick Diagnostics

Run the diagnostic tool to identify common issues:

```bash
insanity-cluster diagnose
```

This will check:
- Service connectivity
- API key validity
- Database connections
- Model endpoint availability
- Configuration validity

## Common Issues

### Installation and Setup

#### Issue: Docker containers won't start

**Symptoms:**
- `docker-compose up` fails
- Containers exit immediately
- Port conflicts

**Solutions:**

1. **Check if ports are already in use:**
```bash
# Windows
netstat -an | findstr "8000 5432 6379 6333"

# Check Docker logs
docker-compose logs
```

2. **Stop conflicting services:**
```bash
# Stop all containers
docker-compose down

# Remove volumes if needed
docker-compose down -v

# Restart
docker-compose up -d
```

3. **Check Docker resources:**
- Ensure Docker has enough memory (4GB minimum)
- Check disk space
- Verify Docker is running

4. **Rebuild containers:**
```bash
docker-compose build --no-cache
docker-compose up -d
```

#### Issue: Database initialization fails

**Symptoms:**
- "Connection refused" errors
- "Database does not exist" errors
- Migration failures

**Solutions:**

1. **Wait for PostgreSQL to be ready:**
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres

# Wait for "database system is ready to accept connections"
```

2. **Initialize database manually:**
```bash
# Run initialization script
docker-compose exec surface python scripts/init_database.py

# Or run migrations
docker-compose exec surface alembic upgrade head
```

3. **Reset database:**
```bash
# Stop services
docker-compose down

# Remove database volume
docker volume rm insanity_cluster_postgres_data

# Restart
docker-compose up -d
```

#### Issue: Python dependencies not installing

**Symptoms:**
- Import errors
- Module not found errors
- Version conflicts

**Solutions:**

1. **Reinstall dependencies:**
```bash
# Activate virtual environment
source venv/bin/activate  # Windows: venv\Scripts\activate

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

2. **Clear pip cache:**
```bash
pip cache purge
pip install -r requirements.txt --no-cache-dir
```

3. **Check Python version:**
```bash
python --version  # Should be 3.11+
```

---

### Authentication and API Keys

#### Issue: "Invalid API key" errors

**Symptoms:**
- 401 Unauthorized responses
- "Authentication required" errors
- API key not recognized

**Solutions:**

1. **Verify API key format:**
```bash
# Should start with ic_test_ or ic_live_
echo $INSANITY_CLUSTER_API_KEY
```

2. **Check environment variables:**
```bash
# View all environment variables
env | grep API_KEY

# Reload .env file
source .env  # Linux/Mac
# Or restart terminal
```

3. **Generate new API key:**
```bash
insanity-cluster auth create-key --name "New Key" --role user
```

4. **Test API key:**
```bash
curl -X GET http://localhost:8000/v1/auth/verify \
  -H "X-API-Key: your-api-key"
```

#### Issue: External model API keys not working

**Symptoms:**
- "Invalid API key" from OpenAI/Anthropic
- Authentication failures with model providers
- Rate limit errors

**Solutions:**

1. **Verify API keys:**
```bash
# Test OpenAI key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"

# Test Anthropic key
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01"
```

2. **Check key permissions:**
- Ensure keys have required permissions
- Verify keys are not expired
- Check usage limits

3. **Update keys in configuration:**
```bash
# Update .env file
nano .env

# Restart services
docker-compose restart
```

---

### Task Execution

#### Issue: Tasks stuck in "queued" status

**Symptoms:**
- Tasks never start executing
- Queue depth increasing
- No agent activity

**Solutions:**

1. **Check agent workers:**
```bash
# View worker logs
docker-compose logs crust

# Check if workers are running
docker-compose ps crust

# Restart workers
docker-compose restart crust
```

2. **Check Redis connection:**
```bash
# Test Redis
docker-compose exec redis redis-cli ping
# Should return "PONG"

# Check queue depth
docker-compose exec redis redis-cli llen task_queue
```

3. **Check for errors:**
```bash
# View all logs
docker-compose logs -f

# Check specific service
docker-compose logs inner
```

4. **Restart orchestration layer:**
```bash
docker-compose restart inner
```

#### Issue: Tasks failing with "Model API timeout"

**Symptoms:**
- Tasks fail after long wait
- "Timeout" errors in logs
- Slow model responses

**Solutions:**

1. **Increase timeout:**
```bash
# Edit .env
MODEL_TIMEOUT_SECONDS=120

# Restart services
docker-compose restart
```

2. **Check model endpoint:**
```bash
# Test Ollama
curl http://localhost:11434/api/tags

# Test LM Studio
curl http://localhost:1234/v1/models
```

3. **Switch to faster model:**
```bash
insanity-cluster config set-agent developer --model claude-haiku-4.5
```

4. **Check network connectivity:**
```bash
# Test OpenAI
curl -I https://api.openai.com

# Test Anthropic
curl -I https://api.anthropic.com
```

#### Issue: High task failure rate

**Symptoms:**
- Many tasks failing
- Error rates > 10%
- Inconsistent results

**Solutions:**

1. **Check error logs:**
```bash
# View recent errors
docker-compose logs --tail=100 | grep ERROR

# Check specific agent
docker-compose logs crust | grep ERROR
```

2. **Review failed tasks:**
```bash
# List failed tasks
insanity-cluster task list --status failed --limit 10

# View task details
insanity-cluster task status <task_id>
```

3. **Check model availability:**
```bash
# Test model endpoints
insanity-cluster diagnose --check-models
```

4. **Adjust retry policies:**
```yaml
# config.yaml
retry_policies:
  max_attempts: 5
  exponential_backoff: true
```

---

### Performance Issues

#### Issue: Slow response times

**Symptoms:**
- Tasks taking too long
- High latency (> 5 seconds)
- Timeouts

**Solutions:**

1. **Check system resources:**
```bash
# Check Docker stats
docker stats

# Check disk space
df -h

# Check memory
free -h
```

2. **Optimize model selection:**
```bash
# Use faster models
insanity-cluster config set-strategy speed-first

# Use local models for simple tasks
insanity-cluster config set mixed-threshold 0.7
```

3. **Enable caching:**
```yaml
# config.yaml
caching:
  enabled: true
  command_parsing_ttl: 604800
  task_decomposition_ttl: 86400
```

4. **Increase worker count:**
```yaml
# docker-compose.yml
crust:
  deploy:
    replicas: 5
```

5. **Check database performance:**
```bash
# Check slow queries
docker-compose exec postgres psql -U insanity_cluster -c "SELECT * FROM pg_stat_statements ORDER BY total_time DESC LIMIT 10;"
```

#### Issue: High memory usage

**Symptoms:**
- Out of memory errors
- System slowdown
- Container restarts

**Solutions:**

1. **Check memory usage:**
```bash
docker stats --no-stream
```

2. **Reduce concurrent tasks:**
```bash
# Edit .env
MAX_CONCURRENT_TASKS=5

# Restart
docker-compose restart
```

3. **Optimize database connections:**
```bash
# Edit .env
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=5
```

4. **Clear caches:**
```bash
# Clear Redis cache
docker-compose exec redis redis-cli FLUSHDB

# Restart services
docker-compose restart
```

---

### Cost Issues

#### Issue: Unexpected high costs

**Symptoms:**
- Costs exceeding budget
- Expensive model usage
- High daily spending

**Solutions:**

1. **Review cost breakdown:**
```bash
# View costs by model
insanity-cluster metrics costs --by-model

# View costs by agent
insanity-cluster metrics costs --by-agent

# View costs by task
insanity-cluster metrics costs --by-task
```

2. **Set strict cost limits:**
```bash
# Set daily limit
insanity-cluster config set-limit --per-day 10.00

# Set per-task limit
insanity-cluster config set-limit --per-task 0.50
```

3. **Switch to cheaper models:**
```bash
# Use mixed mode with high threshold
insanity-cluster config set-mode mixed
insanity-cluster config set mixed-threshold 0.7

# Or use local mode
insanity-cluster config set-mode local
```

4. **Review expensive tasks:**
```bash
# Find most expensive tasks
insanity-cluster task list --sort-by cost --limit 10
```

5. **Enable cost warnings:**
```yaml
# config.yaml
cost_limits:
  warning_threshold: 0.80
notifications:
  email:
    enabled: true
```

#### Issue: Cost limits not enforced

**Symptoms:**
- Spending exceeds configured limits
- No warnings received
- Tasks not blocked

**Solutions:**

1. **Verify cost tracking is enabled:**
```bash
# Check configuration
insanity-cluster config show --section cost_limits

# Enable cost tracking
export ENABLE_COST_TRACKING=true
```

2. **Check cost calculation:**
```bash
# View cost metrics
insanity-cluster metrics costs --period day

# Verify model pricing
insanity-cluster config show --section providers
```

3. **Restart services:**
```bash
docker-compose restart
```

---

### Model and Provider Issues

#### Issue: Local models not working

**Symptoms:**
- "Model not found" errors
- Ollama/LM Studio connection failures
- Slow local inference

**Solutions:**

1. **Check Ollama is running:**
```bash
# Test Ollama
curl http://localhost:11434/api/tags

# Start Ollama
ollama serve
```

2. **Pull required models:**
```bash
# Pull models
ollama pull mistral
ollama pull llama3:70b
ollama pull codellama
ollama pull phi3
```

3. **Check LM Studio:**
- Ensure LM Studio is running
- Verify server is started
- Check port (default: 1234)

4. **Test model inference:**
```bash
# Test Ollama
curl http://localhost:11434/api/generate -d '{
  "model": "mistral",
  "prompt": "Hello"
}'
```

#### Issue: OpenAI/Anthropic API errors

**Symptoms:**
- Rate limit errors
- API errors
- Connection timeouts

**Solutions:**

1. **Check API status:**
- OpenAI: https://status.openai.com
- Anthropic: https://status.anthropic.com

2. **Verify rate limits:**
```bash
# Check current usage
curl https://api.openai.com/v1/usage \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

3. **Implement backoff:**
```yaml
# config.yaml
retry_policies:
  max_attempts: 5
  exponential_backoff: true
  initial_delay: 2
  max_delay: 120
```

4. **Use fallback models:**
```yaml
# config.yaml
agents:
  developer:
    fallback_models:
      - gpt-5-codex
      - claude-sonnet-4.5
      - local:codellama
```

---

### WebSocket Issues

#### Issue: WebSocket connection fails

**Symptoms:**
- "Connection refused" errors
- No real-time updates
- Frequent disconnections

**Solutions:**

1. **Check WebSocket endpoint:**
```bash
# Test connection
wscat -c ws://localhost:8000/ws?token=your-token
```

2. **Verify authentication:**
```bash
# Generate valid token
insanity-cluster auth create-token
```

3. **Check firewall:**
- Ensure port 8000 is open
- Check proxy settings
- Verify CORS configuration

4. **Implement reconnection:**
```javascript
// Add reconnection logic
let reconnectDelay = 1000;
function connect() {
  const ws = new WebSocket('ws://localhost:8000/ws');
  ws.onclose = () => {
    setTimeout(connect, reconnectDelay);
    reconnectDelay *= 2;
  };
}
```

---

### Dashboard Issues

#### Issue: Dashboard not loading

**Symptoms:**
- Blank page
- 404 errors
- Assets not loading

**Solutions:**

1. **Check dashboard service:**
```bash
# View dashboard logs
docker-compose logs dashboard

# Restart dashboard
docker-compose restart dashboard
```

2. **Rebuild dashboard:**
```bash
# Rebuild frontend
cd dashboard
npm install
npm run build

# Or rebuild container
docker-compose build dashboard
docker-compose up -d dashboard
```

3. **Check API connectivity:**
```bash
# Test API from dashboard
curl http://localhost:8000/v1/tasks
```

4. **Clear browser cache:**
- Hard refresh (Ctrl+Shift+R)
- Clear browser cache
- Try incognito mode

#### Issue: Dashboard shows incorrect data

**Symptoms:**
- Stale data
- Incorrect metrics
- Missing tasks

**Solutions:**

1. **Refresh data:**
- Click refresh button
- Reload page
- Check WebSocket connection

2. **Check API responses:**
```bash
# Test API endpoints
curl http://localhost:8000/v1/tasks
curl http://localhost:8000/v1/metrics/tasks
```

3. **Clear cache:**
```bash
# Clear Redis cache
docker-compose exec redis redis-cli FLUSHDB
```

---

## Diagnostic Commands

### System Health Check

```bash
# Full diagnostic
insanity-cluster diagnose

# Check specific component
insanity-cluster diagnose --component database
insanity-cluster diagnose --component redis
insanity-cluster diagnose --component models
```

### View Logs

```bash
# All logs
docker-compose logs -f

# Specific service
docker-compose logs -f surface
docker-compose logs -f inner
docker-compose logs -f crust

# Last 100 lines
docker-compose logs --tail=100

# Follow errors only
docker-compose logs -f | grep ERROR
```

### Check Service Status

```bash
# All services
docker-compose ps

# Specific service
docker-compose ps surface

# Restart service
docker-compose restart surface
```

### Database Queries

```bash
# Connect to database
docker-compose exec postgres psql -U insanity_cluster

# Check task status
SELECT status, COUNT(*) FROM tasks GROUP BY status;

# Check recent errors
SELECT * FROM tasks WHERE status = 'failed' ORDER BY created_at DESC LIMIT 10;

# Check metrics
SELECT * FROM metrics ORDER BY timestamp DESC LIMIT 100;
```

### Redis Inspection

```bash
# Connect to Redis
docker-compose exec redis redis-cli

# Check queue depth
LLEN task_queue

# View keys
KEYS *

# Check cache
GET command_cache:*
```

---

## Getting Help

### Before Asking for Help

1. **Run diagnostics:**
```bash
insanity-cluster diagnose > diagnostics.txt
```

2. **Collect logs:**
```bash
docker-compose logs > logs.txt
```

3. **Check configuration:**
```bash
insanity-cluster config show > config.txt
```

4. **Document the issue:**
- What were you trying to do?
- What happened instead?
- Error messages
- Steps to reproduce

### Support Channels

- **Documentation**: https://docs.insanitycluster.com
- **GitHub Issues**: https://github.com/insanity-cluster/insanity-cluster/issues
- **Discord**: https://discord.gg/insanity-cluster
- **Email**: support@insanitycluster.com
- **Status Page**: https://status.insanitycluster.com

### Emergency Support

For critical production issues:
- Email: emergency@insanitycluster.com
- Include: "URGENT" in subject line
- Provide: diagnostics, logs, and impact description

---

## Preventive Maintenance

### Regular Checks

1. **Daily:**
   - Check cost metrics
   - Review error rates
   - Monitor queue depths

2. **Weekly:**
   - Review failed tasks
   - Check disk space
   - Update dependencies

3. **Monthly:**
   - Rotate API keys
   - Review configuration
   - Update system
   - Clean old data

### Monitoring Setup

```yaml
# config.yaml
monitoring:
  enabled: true
  alerts:
    - type: cost_limit
      threshold: 0.80
      action: email
    
    - type: error_rate
      threshold: 0.10
      action: slack
    
    - type: queue_depth
      threshold: 100
      action: email
```

### Backup Strategy

```bash
# Backup database
docker-compose exec postgres pg_dump -U insanity_cluster > backup.sql

# Backup configuration
cp -r ~/.insanity-cluster backup/

# Backup .env
cp .env backup/
```

---

## Performance Tuning

### Optimize for Speed

```yaml
mode: mixed
default_strategy: speed_first
local_complexity_threshold: 0.7
caching:
  enabled: true
agents:
  developer:
    primary_model: claude-haiku-4.5
```

### Optimize for Cost

```yaml
mode: mixed
default_strategy: cost_optimized
local_complexity_threshold: 0.3
cost_limits:
  per_task: 0.50
  per_day: 10.00
```

### Optimize for Quality

```yaml
mode: web
default_strategy: quality_first
agents:
  developer:
    primary_model: claude-sonnet-4.5
  business:
    primary_model: claude-opus-4.1
```

---

This troubleshooting guide covers the most common issues. For additional help, consult the documentation or contact support.
