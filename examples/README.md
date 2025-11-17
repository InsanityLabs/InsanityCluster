# Insanity Cluster Examples

This directory contains example code and configurations to help you get started with Insanity Cluster.

## Examples Overview

### 1. CLI Example (`cli_example.py`)

A command-line application that demonstrates how to interact with Insanity Cluster programmatically.

**Features:**
- Create and execute tasks
- Monitor task progress
- Display results and metrics
- Real-time updates

**Usage:**
```bash
# Install dependencies
pip install httpx rich

# Run example
python cli_example.py "Write a Python function to calculate fibonacci"

# With real-time updates
python cli_example.py --updates "Generate a story about AI"

# Custom API key
python cli_example.py --api-key YOUR_KEY "Your command"
```

### 2. Web Integration Example (`web_integration_example.py`)

A Flask web application that shows how to integrate Insanity Cluster into a web interface with WebSocket support for real-time updates.

**Features:**
- Web-based task submission
- Real-time progress updates via WebSocket
- Visual progress bars
- Result display with metrics
- Responsive UI

**Usage:**
```bash
# Install dependencies
pip install flask flask-socketio python-socketio httpx

# Run example
python web_integration_example.py

# Open browser
# Navigate to http://localhost:5000
```

### 3. Custom Agent Example (`custom_agent_example.py`)

A complete example of creating a custom agent for specialized tasks (Data Analysis Agent).

**Features:**
- Custom agent implementation
- Specialized prompt engineering
- Output validation
- Error handling
- Complexity estimation

**Usage:**
```bash
# Copy to project
cp custom_agent_example.py ../insanity_cluster/crust/data_analysis_agent.py

# Register agent in __init__.py
# Add configuration to config.yaml

# Use the agent
insanity-cluster task create "Analyze sales trends for Q3 2025"
```

### 4. Configuration Examples (`config_examples/`)

Pre-configured YAML files for different use cases:

#### Development Configuration (`development.yaml`)
- Local mode only
- Zero cost
- Fast iteration
- Debug logging

**Use when:**
- Developing and testing
- Learning the system
- No API costs desired

#### Production Configuration (`production.yaml`)
- Mixed mode
- Balanced cost/quality
- High availability
- Comprehensive monitoring
- Auto-scaling

**Use when:**
- Running in production
- Serving real users
- Need reliability and performance

#### Budget-Conscious Configuration (`budget-conscious.yaml`)
- Mixed mode with high local threshold
- Strict cost limits
- Aggressive caching
- Minimal paid API usage

**Use when:**
- Cost is primary concern
- Limited budget
- Can accept slightly lower quality

## Quick Start

### 1. Choose Your Example

Pick the example that matches your use case:
- **CLI**: Building command-line tools
- **Web**: Building web applications
- **Agent**: Creating custom agents
- **Config**: Optimizing for your needs

### 2. Install Dependencies

```bash
# For CLI example
pip install httpx rich

# For web example
pip install flask flask-socketio python-socketio httpx

# For agent example (no additional dependencies)
```

### 3. Configure Insanity Cluster

```bash
# Copy configuration
cp config_examples/development.yaml ~/.insanity-cluster/config.yaml

# Or use environment variables
export INSANITY_CLUSTER_API_KEY=ic_test_demo
export INSANITY_CLUSTER_BASE_URL=http://localhost:8000/v1
```

### 4. Run Example

```bash
# CLI example
python cli_example.py "Your command here"

# Web example
python web_integration_example.py
```

## Example Workflows

### Workflow 1: Code Generation

```bash
# Using CLI
python cli_example.py "Create a REST API in Python with user authentication"

# Using Web Interface
# 1. Open http://localhost:5000
# 2. Enter command: "Create a REST API in Python with user authentication"
# 3. Click "Execute Task"
# 4. Watch real-time progress
```

### Workflow 2: Data Analysis

```bash
# Using custom agent
insanity-cluster task create "Analyze sales data and identify trends"

# Or via CLI example
python cli_example.py "Analyze sales data and identify trends"
```

### Workflow 3: Multi-Agent Task

```bash
# Complex task requiring multiple agents
python cli_example.py "Create a landing page, write marketing copy, and set up email automation"

# The system will automatically:
# 1. Decompose into subtasks
# 2. Assign to appropriate agents (Developer, Creative, Communication)
# 3. Execute in parallel where possible
# 4. Aggregate results
```

## Configuration Tips

### For Development

```yaml
mode: local
cost_limits:
  per_day: 0.00
providers:
  ollama:
    enabled: true
logging:
  level: DEBUG
```

### For Production

```yaml
mode: mixed
cost_limits:
  per_day: 100.00
mixed_mode:
  local_complexity_threshold: 0.5
monitoring:
  enabled: true
  alerts:
    - type: cost_limit
      threshold: 0.80
```

### For Budget-Conscious

```yaml
mode: mixed
cost_limits:
  per_day: 10.00
mixed_mode:
  local_complexity_threshold: 0.7
caching:
  enabled: true
  command_parsing_ttl: 2592000  # 30 days
```

## Customization

### Modify CLI Example

```python
# Add custom command-line arguments
parser.add_argument(
    "--model",
    help="Preferred model to use"
)

# Add custom output formatting
def format_result(result):
    # Your custom formatting
    pass
```

### Modify Web Example

```html
<!-- Add custom UI elements -->
<div class="custom-section">
    <!-- Your custom HTML -->
</div>
```

```javascript
// Add custom JavaScript
function customHandler(data) {
    // Your custom logic
}
```

### Modify Agent Example

```python
# Add custom capabilities
class CustomAgent(BaseAgent):
    def __init__(self, model_router, config):
        super().__init__(model_router, config)
        self.capabilities = [
            "custom_capability_1",
            "custom_capability_2"
        ]
    
    # Add custom methods
    def custom_method(self):
        pass
```

## Troubleshooting

### CLI Example Issues

**Problem:** Connection refused
```bash
# Check if Insanity Cluster is running
curl http://localhost:8000/health

# Start Insanity Cluster
docker-compose up -d
```

**Problem:** Authentication failed
```bash
# Check API key
echo $INSANITY_CLUSTER_API_KEY

# Generate new API key
insanity-cluster auth create-key --name "Example"
```

### Web Example Issues

**Problem:** WebSocket not connecting
```bash
# Check CORS settings
# Ensure cors_allowed_origins="*" in SocketIO initialization

# Check firewall
# Ensure port 5000 is open
```

**Problem:** Tasks not updating
```bash
# Check WebSocket connection in browser console
# Verify task_id is correct
# Check server logs
```

### Agent Example Issues

**Problem:** Agent not found
```bash
# Verify agent is registered
# Check insanity_cluster/crust/__init__.py

# Verify configuration
insanity-cluster config show --section agents
```

## Best Practices

1. **Start Simple**: Begin with CLI example before building complex integrations
2. **Use Appropriate Config**: Match configuration to your use case
3. **Monitor Costs**: Always set cost limits and monitor spending
4. **Test Locally**: Use local mode for development and testing
5. **Handle Errors**: Implement proper error handling in your code
6. **Cache Results**: Enable caching to reduce API calls
7. **Validate Inputs**: Always validate user inputs before submission
8. **Log Everything**: Use structured logging for debugging
9. **Secure API Keys**: Never commit API keys to version control
10. **Read Documentation**: Check docs for detailed information

## Additional Resources

- **Documentation**: https://docs.insanitycluster.com
- **API Reference**: https://docs.insanitycluster.com/api
- **GitHub**: https://github.com/insanity-cluster/insanity-cluster
- **Discord**: https://discord.gg/insanity-cluster
- **Email**: support@insanitycluster.com

## Contributing

Have a useful example? Contribute it!

1. Fork the repository
2. Add your example
3. Update this README
4. Submit a pull request

See [CONTRIBUTING.md](../CONTRIBUTING.md) for guidelines.

## License

All examples are provided under the MIT License. Feel free to use and modify them for your projects.
