# CRUST Layer - Specialized Agent Framework

The CRUST layer provides domain-specific agents that execute subtasks assigned by the INNER layer coordinator. Each agent specializes in a particular domain and uses the PAN layer for model inference.

## Architecture

```
INNER Layer (Coordinator)
        ↓
    CRUST Layer (Agents)
        ↓
    PAN Layer (Models)
```

## Agents

### BaseAgent (Abstract)
- **Purpose**: Common interface for all specialized agents
- **Key Methods**:
  - `execute()`: Main execution entry point
  - `select_model_strategy()`: Choose optimal model routing
  - `validate_output()`: Domain-specific validation
  - `coordinate_with()`: Cross-agent collaboration

### DeveloperAgent
- **Domain**: Software development
- **Capabilities**:
  - Code generation (multiple languages)
  - Code review and refactoring
  - Debugging and error analysis
  - CI/CD pipeline setup
  - Documentation generation
- **Model Strategy**: Quality-first (Claude Sonnet 4.5, gpt-5-codex)
- **Validation**: Syntax checking, code structure

### CommunicationAgent
- **Domain**: Communication and outreach
- **Capabilities**:
  - Phone call handling (Twilio)
  - Speech-to-text (500ms target)
  - Text-to-speech (300ms target)
  - Email composition (SendGrid)
  - Meeting scheduling (Google Calendar)
- **Model Strategy**: Speed-first (Claude Haiku 4.5)
- **Validation**: Tone analysis, grammar checking

### BusinessAgent
- **Domain**: Business and legal
- **Capabilities**:
  - LLC formation documents
  - Contract analysis and review
  - Compliance monitoring
  - Financial record keeping
  - LegalZoom/Rocket Lawyer integration
- **Model Strategy**: Quality-first (Claude Opus 4.1, gpt-5.1)
- **Validation**: Legal term verification, completeness

### ResearchAgent
- **Domain**: Research and analysis
- **Capabilities**:
  - Web search and data gathering
  - Multi-source synthesis
  - Report generation with citations
  - Trend analysis
  - Competitive analysis
- **Model Strategy**: Task-specific (Claude Sonnet 4.5)
- **Validation**: Source citations, credibility checking

### CreativeAgent
- **Domain**: Creative content
- **Capabilities**:
  - Copywriting
  - Design concepts (vision models)
  - Content creation
  - Brand consistency validation
- **Model Strategy**: Quality-first (gpt-5.1)
- **Validation**: Creativity, engagement quality

### FinanceAgent
- **Domain**: Financial management
- **Capabilities**:
  - Accounting and budgeting
  - Invoicing
  - Financial reporting
  - Payment processing (Stripe, PayPal)
  - Calculation verification
- **Model Strategy**: Cost-optimized (gpt-5-mini)
- **Validation**: Numerical accuracy, completeness

### ProjectManagerAgent
- **Domain**: Project management
- **Capabilities**:
  - Project planning and scheduling
  - Progress tracking
  - Progress reporting
  - Risk identification
  - Timeline feasibility validation
- **Model Strategy**: Cost-optimized (gpt-5-mini)
- **Validation**: Timeline feasibility, structure

## Usage

### Basic Agent Execution

```python
from insanity_cluster.crust import DeveloperAgent
from insanity_cluster.pan.model_router import ModelRouter
from insanity_cluster.common.models import Subtask, AgentType

# Initialize agent
model_router = ModelRouter()
agent = DeveloperAgent(model_router)

# Create subtask
subtask = Subtask(
    id="task-1",
    description="Generate a Python function to calculate fibonacci numbers",
    agent_type=AgentType.DEVELOPER,
    dependencies=[],
    priority=1,
    estimated_cost=0.1,
    estimated_duration=0
)

# Execute
context = {
    "language": "python",
    "requirements": ["Include docstring", "Handle edge cases"]
}

result = await agent.execute(subtask, context)
print(f"Status: {result.status}")
print(f"Output: {result.output}")
print(f"Cost: ${result.cost:.4f}")
print(f"Validation: {result.validation_score:.2f}")
```

### Cross-Agent Collaboration

```python
# Developer agent coordinating with Business agent
developer_agent = DeveloperAgent(model_router)
business_agent = BusinessAgent(model_router)

# Developer asks Business agent to review legal implications
legal_review = await developer_agent.coordinate_with(
    other_agent=business_agent,
    data={"code": generated_code},
    request="Review this code for any legal or compliance issues"
)
```

### Integration with INNER Layer

The INNER layer coordinator automatically routes subtasks to appropriate agents:

```python
from insanity_cluster.inner.coordinator import MultiAgentCoordinator

coordinator = MultiAgentCoordinator()

# Coordinator handles agent selection and execution
result = await coordinator.execute_task_graph(task_graph)
```

## Agent Lifecycle

1. **Initialization**: Agent created with model router
2. **Task Assignment**: INNER layer assigns subtask
3. **Model Selection**: Agent selects optimal model strategy
4. **Execution**: Agent performs domain-specific work
5. **Validation**: Output validated against quality criteria
6. **Result Return**: AgentResult returned to coordinator

## Error Handling

Agents implement robust error handling:

```python
try:
    result = await agent.execute(subtask, context)
except AgentExecutionError as e:
    print(f"Agent {e.agent_type} failed on {e.subtask_id}")
except CoordinationError as e:
    print(f"Coordination failed between {e.requesting_agent} and {e.target_agent}")
```

## Model Strategy Selection

Each agent can customize model selection:

```python
def select_model_strategy(self, subtask: Subtask) -> ModelStrategy:
    if "complex" in subtask.description.lower():
        return ModelStrategy(
            routing_mode=RoutingMode.QUALITY_FIRST,
            max_cost=1.0,
            required_capabilities=["long_context"]
        )
    else:
        return ModelStrategy(
            routing_mode=RoutingMode.COST_OPTIMIZED,
            max_cost=0.3
        )
```

## Validation

Each agent implements domain-specific validation:

```python
def validate_output(self, output: Any, subtask: Subtask) -> float:
    """
    Returns validation score between 0.0 and 1.0
    
    Checks:
    - Output completeness
    - Domain-specific quality
    - Error indicators
    - Format correctness
    """
    score = 0.0
    # ... validation logic
    return score
```

## External Service Integration

Agents support optional external service integration:

```python
# Communication agent with Twilio
communication_agent = CommunicationAgent(
    model_router=model_router,
    twilio_client=twilio_client,
    sendgrid_client=sendgrid_client
)

# Business agent with legal services
business_agent = BusinessAgent(
    model_router=model_router,
    legalzoom_client=legalzoom_client
)

# Finance agent with payment processors
finance_agent = FinanceAgent(
    model_router=model_router,
    stripe_client=stripe_client,
    paypal_client=paypal_client
)
```

## Performance Considerations

- **Latency Targets**:
  - Communication Agent: < 1s for voice interactions
  - Developer Agent: < 5s for code generation
  - Other agents: < 3s typical
  
- **Cost Optimization**:
  - Agents select appropriate models based on task complexity
  - Simple tasks use cost-optimized models (gpt-5-nano, gpt-5-mini)
  - Complex tasks use quality models (Claude Opus, gpt-5.1)
  
- **Validation**:
  - All outputs validated before returning
  - Low validation scores trigger retries or alternative routing

## Testing

```python
# Test agent execution
async def test_developer_agent():
    agent = DeveloperAgent(model_router)
    
    subtask = Subtask(
        id="test-1",
        description="Write a hello world function",
        agent_type=AgentType.DEVELOPER,
        dependencies=[],
        priority=1,
        estimated_cost=0.05,
        estimated_duration=0
    )
    
    result = await agent.execute(subtask, {"language": "python"})
    
    assert result.status == ResultStatus.SUCCESS
    assert result.validation_score > 0.7
    assert "def" in result.output
```

## Future Enhancements

- [ ] Add more specialized agents (Legal, Medical, etc.)
- [ ] Implement agent learning from past executions
- [ ] Add agent performance metrics and optimization
- [ ] Support for custom agent plugins
- [ ] Enhanced cross-agent collaboration patterns
- [ ] Agent-specific caching strategies

## Related Documentation

- [PAN Layer](../pan/README.md) - Model routing and inference
- [INNER Layer](../inner/README.md) - Task orchestration
- [Design Document](../../docs/architecture.md) - System architecture
