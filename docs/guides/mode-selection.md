# Operating Mode Selection Guide

## Overview

Insanity Cluster supports five operating modes that determine which AI models are used for task execution. Each mode offers different trade-offs between cost, quality, speed, and privacy.

## Operating Modes

### 1. Local Mode (Fully Free)

**Description**: Uses only local models running on your hardware via Ollama or LM Studio.

**Characteristics:**
- 💰 **Cost**: $0 (completely free)
- 🔒 **Privacy**: Maximum (no external API calls)
- ⚡ **Speed**: Fast for simple tasks, slower for complex ones
- 🎯 **Quality**: Good for most tasks, excellent for code

**Best For:**
- Development and testing
- Privacy-sensitive data
- Offline operation
- Zero-budget projects
- Learning and experimentation

**Models Used:**
- Simple tasks: Phi-3 Mini, Mistral 7B
- Complex tasks: LLaMA 3 70B, Mixtral 8x7B
- Code tasks: CodeLLaMA, DeepSeek Coder
- Fast responses: Mistral 7B

**Setup:**

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull recommended models
ollama pull mistral
ollama pull llama3:70b
ollama pull codellama
ollama pull phi3

# Set mode
insanity-cluster config set-mode local
```

**Example Configuration:**

```yaml
mode: LOCAL
default_strategy: SPEED_FIRST
agents:
  developer:
    preferred_models:
      - local:codellama
      - local:llama3:70b
  communication:
    preferred_models:
      - local:mistral
      - local:phi3
```

---

### 2. OpenRouter Free Mode

**Description**: Uses free models available through OpenRouter's free tier.

**Characteristics:**
- 💰 **Cost**: $0 (rate-limited)
- 🔒 **Privacy**: Low (external API calls)
- ⚡ **Speed**: Variable (depends on availability)
- 🎯 **Quality**: Good (varies by model)

**Best For:**
- Learning and experimentation
- Low-budget projects
- Testing different models
- Non-critical tasks

**Models Available:**
- Various open-source models via OpenRouter
- Availability varies based on OpenRouter's free tier
- Rate limits apply

**Setup:**

```bash
# Get OpenRouter API key (free tier)
# Visit: https://openrouter.ai/keys

# Set API key
export OPENROUTER_API_KEY=sk-or-...

# Set mode
insanity-cluster config set-mode openrouter-free
```

**Limitations:**
- Rate limits (varies by model)
- Model availability not guaranteed
- Queue times during high demand
- No SLA or guarantees

---

### 3. Mixed Mode (Recommended)

**Description**: Intelligently combines local and paid models based on task complexity.

**Characteristics:**
- 💰 **Cost**: Low to moderate (optimized)
- 🔒 **Privacy**: Medium (local for simple, external for complex)
- ⚡ **Speed**: Fast (local) to moderate (paid)
- 🎯 **Quality**: Excellent (best model for each task)

**Best For:**
- Production applications
- Cost-conscious deployments
- Balanced performance
- Most use cases

**How It Works:**

1. **Task Analysis**: System estimates task complexity (0.0 - 1.0)
2. **Threshold Check**: Compares complexity to configured threshold
3. **Model Selection**:
   - Complexity < threshold → Local models
   - Complexity ≥ threshold → Paid models
4. **Fallback**: If local fails, escalates to paid models

**Complexity Thresholds:**

```
0.0 - 0.3: Very simple (greetings, basic questions)
0.3 - 0.5: Simple (data formatting, simple code)
0.5 - 0.7: Moderate (API integration, analysis)
0.7 - 0.9: Complex (architecture design, research)
0.9 - 1.0: Very complex (multi-step reasoning, legal)
```

**Setup:**

```bash
# Set mode
insanity-cluster config set-mode mixed

# Configure threshold (default: 0.5)
insanity-cluster config set mixed-threshold 0.6

# Set cost limits
insanity-cluster config set-limit --per-task 1.00 --per-day 50.00
```

**Example Configuration:**

```yaml
mode: MIXED
default_strategy: COST_OPTIMIZED
local_complexity_threshold: 0.5
max_cost_per_task: 1.00
max_cost_per_day: 50.00

agents:
  developer:
    preferred_models:
      - claude-sonnet-4.5  # For complex code
      - local:codellama    # For simple code
    fallback_to_paid: true
    max_cost: 1.00
  
  communication:
    preferred_models:
      - local:mistral      # For most tasks
      - claude-haiku-4.5   # For complex emails
    fallback_to_paid: true
    max_cost: 0.10

task_type_overrides:
  code_generation:
    strategy_override: QUALITY_FIRST
    allow_local: false  # Always use paid for code
  
  simple_chat:
    model_override: local:phi3
    allow_paid: false  # Always use local for chat
```

**Cost Optimization Tips:**

1. **Increase threshold** (0.6-0.7) to use local models more often
2. **Set per-task limits** to prevent expensive operations
3. **Use task-type overrides** for predictable costs
4. **Monitor daily spending** and adjust thresholds

---

### 4. Web Mode (Fully Paid)

**Description**: Uses only premium paid models from OpenAI and Anthropic.

**Characteristics:**
- 💰 **Cost**: High (premium models)
- 🔒 **Privacy**: Low (external API calls)
- ⚡ **Speed**: Very fast (optimized endpoints)
- 🎯 **Quality**: Excellent (best available models)

**Best For:**
- Production applications
- Mission-critical tasks
- Maximum quality requirements
- When cost is not a constraint

**Models Used:**
- Simple tasks: gpt-5-mini ($0.10/M)
- Standard tasks: Claude Haiku 4.5 ($1/M)
- Complex tasks: Claude Sonnet 4.5 ($3/M)
- Specialized reasoning: Claude Opus 4.1 ($15/M), gpt-5.1 ($1.25/M)

**Setup:**

```bash
# Set API keys
export OPENAI_API_KEY=sk-...
export ANTHROPIC_API_KEY=sk-ant-...

# Set mode
insanity-cluster config set-mode web

# Set cost limits (recommended)
insanity-cluster config set-limit --per-day 100.00
```

**Example Configuration:**

```yaml
mode: WEB
default_strategy: QUALITY_FIRST
max_cost_per_day: 100.00

agents:
  developer:
    preferred_models:
      - claude-sonnet-4.5
      - gpt-5-codex
  
  business:
    preferred_models:
      - claude-opus-4.1
      - gpt-5.1
  
  communication:
    preferred_models:
      - claude-haiku-4.5
      - gpt-5-mini
```

**Cost Estimates:**

| Task Type | Model | Cost per Task |
|-----------|-------|---------------|
| Simple chat | gpt-5-mini | $0.001 - $0.01 |
| Code generation | Claude Sonnet 4.5 | $0.05 - $0.50 |
| Research report | Claude Sonnet 4.5 | $0.10 - $1.00 |
| Legal analysis | Claude Opus 4.1 | $0.50 - $5.00 |
| Complex reasoning | gpt-5.1 | $0.10 - $1.00 |

---

### 5. OpenRouter Paid Mode

**Description**: All models accessed through OpenRouter with unified billing.

**Characteristics:**
- 💰 **Cost**: Moderate to high (slight markup)
- 🔒 **Privacy**: Low (external API calls)
- ⚡ **Speed**: Fast (varies by model)
- 🎯 **Quality**: Excellent (access to all models)

**Best For:**
- Simplified billing
- Access to many models
- Unified API interface
- Model experimentation

**Advantages:**
- Single API key for all models
- Unified billing and usage tracking
- Access to both free and paid models
- Fallback to alternative models

**Setup:**

```bash
# Get OpenRouter API key
# Visit: https://openrouter.ai/keys

# Set API key
export OPENROUTER_API_KEY=sk-or-...

# Set mode
insanity-cluster config set-mode openrouter-paid
```

**Example Configuration:**

```yaml
mode: OPENROUTER_PAID
default_strategy: TASK_SPECIFIC
max_cost_per_day: 75.00

agents:
  developer:
    preferred_models:
      - anthropic/claude-sonnet-4.5
      - openai/gpt-5-codex
  
  communication:
    preferred_models:
      - anthropic/claude-haiku-4.5
      - openai/gpt-5-mini
```

---

## Routing Strategies

Within each mode, you can select a routing strategy:

### Speed-First

Prioritizes fastest response times.

**Model Selection:**
- Local Mode: Mistral 7B, Phi-3 Mini
- Mixed Mode: Local models first, Claude Haiku 4.5 if needed
- Web Mode: Claude Haiku 4.5, gpt-5-mini

**Best For:**
- Real-time interactions
- Voice communication
- Quick responses
- High-volume tasks

```bash
insanity-cluster config set-strategy speed-first
```

### Quality-First

Prioritizes best possible output quality.

**Model Selection:**
- Local Mode: LLaMA 3 70B, Mixtral 8x7B
- Mixed Mode: Always use paid models
- Web Mode: Claude Opus 4.1, gpt-5.1

**Best For:**
- Critical decisions
- Legal documents
- Complex reasoning
- High-stakes tasks

```bash
insanity-cluster config set-strategy quality-first
```

### Cost-Optimized

Minimizes costs while maintaining quality.

**Model Selection:**
- Local Mode: Always use local (zero cost)
- Mixed Mode: Escalate only when necessary
- Web Mode: gpt-5-nano → Claude Haiku → Claude Sonnet → Claude Opus

**Best For:**
- Budget-conscious deployments
- High-volume operations
- Development/testing
- Non-critical tasks

```bash
insanity-cluster config set-strategy cost-optimized
```

### Task-Specific

Selects optimal model based on task type.

**Model Selection:**
- Code: Claude Sonnet 4.5, gpt-5-codex
- Chat: gpt-5-mini, local:mistral
- Legal: Claude Opus 4.1
- Research: Claude Sonnet 4.5

**Best For:**
- Diverse workloads
- Specialized tasks
- Optimal performance
- Most use cases

```bash
insanity-cluster config set-strategy task-specific
```

---

## Mode Comparison

| Feature | Local | OpenRouter Free | Mixed | Web | OpenRouter Paid |
|---------|-------|----------------|-------|-----|-----------------|
| **Cost** | $0 | $0 | $5-50/day | $50-200/day | $40-150/day |
| **Privacy** | ⭐⭐⭐⭐⭐ | ⭐ | ⭐⭐⭐ | ⭐ | ⭐ |
| **Speed** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Quality** | ⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Setup** | Complex | Easy | Moderate | Easy | Easy |
| **Offline** | ✅ | ❌ | Partial | ❌ | ❌ |

---

## Switching Modes

### Via CLI

```bash
# Switch to mixed mode
insanity-cluster config set-mode mixed

# Verify current mode
insanity-cluster config show
```

### Via API

```bash
curl -X PUT http://localhost:8000/v1/config/mode \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"mode": "MIXED", "default_strategy": "COST_OPTIMIZED"}'
```

### Via Dashboard

1. Navigate to Configuration tab
2. Select desired mode from dropdown
3. Configure mode-specific settings
4. Click "Save Configuration"

---

## Decision Tree

Use this decision tree to select the right mode:

```
Do you need maximum privacy?
├─ Yes → Local Mode
└─ No
   └─ Is cost a major concern?
      ├─ Yes
      │  └─ Can you run local models?
      │     ├─ Yes → Mixed Mode (high threshold)
      │     └─ No → OpenRouter Free Mode
      └─ No
         └─ Need maximum quality?
            ├─ Yes → Web Mode (Quality-First)
            └─ No → Mixed Mode (Cost-Optimized)
```

---

## Recommendations by Use Case

### Development & Testing
**Recommended**: Local Mode
- Zero cost
- Fast iteration
- No API dependencies

### Personal Projects
**Recommended**: Mixed Mode (threshold: 0.6)
- Low cost ($5-20/month)
- Good quality
- Flexible

### Small Business
**Recommended**: Mixed Mode (threshold: 0.5)
- Moderate cost ($50-200/month)
- Excellent quality
- Cost-effective

### Enterprise
**Recommended**: Web Mode or OpenRouter Paid
- Maximum quality
- Predictable performance
- SLA support

### Privacy-Sensitive
**Recommended**: Local Mode
- No external API calls
- Complete data control
- GDPR/CCPA compliant

---

## Monitoring and Optimization

### Track Costs

```bash
# View daily costs
insanity-cluster metrics costs --period day

# View cost by model
insanity-cluster metrics costs --by-model

# View cost by agent
insanity-cluster metrics costs --by-agent
```

### Analyze Performance

```bash
# View latency metrics
insanity-cluster metrics latency

# View success rates
insanity-cluster metrics success-rate

# View model usage
insanity-cluster metrics model-usage
```

### Optimize Configuration

1. **Review cost reports** to identify expensive operations
2. **Adjust thresholds** to use local models more often
3. **Set task-type overrides** for predictable costs
4. **Monitor quality** to ensure acceptable results
5. **Iterate** based on actual usage patterns

---

## Best Practices

1. **Start with Local Mode** for development
2. **Use Mixed Mode** for production (most cost-effective)
3. **Set cost limits** to prevent surprises
4. **Monitor daily** for the first week
5. **Adjust thresholds** based on actual costs
6. **Use task-type overrides** for critical tasks
7. **Review monthly** and optimize configuration

---

## Troubleshooting

### High Costs

**Problem**: Daily costs exceeding budget

**Solutions**:
1. Switch to Mixed Mode with higher threshold (0.7)
2. Set strict per-task limits
3. Use task-type overrides to force local models
4. Review expensive tasks in dashboard
5. Consider Local Mode for non-critical tasks

### Poor Quality

**Problem**: Results not meeting expectations

**Solutions**:
1. Lower complexity threshold (0.3-0.4)
2. Switch to Quality-First strategy
3. Use task-type overrides for critical tasks
4. Consider Web Mode for important work
5. Review model selection in logs

### Slow Responses

**Problem**: Tasks taking too long

**Solutions**:
1. Use Speed-First strategy
2. Ensure local models are properly configured
3. Check model endpoint latency
4. Consider faster models (Claude Haiku, gpt-5-mini)
5. Review task decomposition complexity

---

## Support

For mode selection help:
- Documentation: https://docs.insanitycluster.com/modes
- Discord: https://discord.gg/insanity-cluster
- Email: support@insanitycluster.com
