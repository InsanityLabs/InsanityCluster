# Agent Capabilities and Use Cases

## Overview

Insanity Cluster includes seven specialized agents, each designed to handle specific types of tasks. This guide explains what each agent can do and provides real-world examples.

## Agent Architecture

All agents share a common architecture:

```
┌─────────────────────────────────────┐
│         BaseAgent (Abstract)        │
├─────────────────────────────────────┤
│ - execute(subtask, context)         │
│ - select_model_strategy()           │
│ - validate_output()                 │
│ - coordinate_with(other_agent)      │
└─────────────────────────────────────┘
                  ▲
                  │
    ┌─────────────┴─────────────┐
    │                           │
┌───┴────┐  ┌──────────┐  ┌────┴─────┐
│Developer│  │Business  │  │Comms     │
│Agent    │  │Agent     │  │Agent     │
└─────────┘  └──────────┘  └──────────┘
```

---

## 1. Developer Agent

### Capabilities

The Developer Agent handles all software development tasks:

#### Code Generation
- Write code in any programming language
- Generate complete applications from specifications
- Create API endpoints and services
- Build database schemas and migrations

#### Code Review
- Analyze existing code for issues
- Suggest refactoring improvements
- Identify security vulnerabilities
- Check code style and best practices

#### Debugging
- Analyze error messages and stack traces
- Identify root causes of bugs
- Suggest fixes and improvements
- Generate test cases to reproduce issues

#### CI/CD Setup
- Create GitHub Actions workflows
- Configure GitLab CI pipelines
- Set up Docker builds
- Configure deployment scripts

#### Documentation
- Generate API documentation
- Create README files
- Write inline code comments
- Generate architecture diagrams

### Model Preferences

- **Primary**: Claude Sonnet 4.5 (excellent for complex code)
- **Alternative**: gpt-5-codex (specialized for code)
- **Fallback**: local:codellama (for simple tasks)

### Example Commands

**Simple Code Generation:**
```bash
insanity-cluster task create "Write a Python function to validate email addresses"
```

**Complete Application:**
```bash
insanity-cluster task create "Create a REST API in FastAPI with user authentication, CRUD operations for blog posts, and PostgreSQL database"
```

**Code Review:**
```bash
insanity-cluster task create "Review the code in src/api/users.py and suggest improvements"
```

**Debugging:**
```bash
insanity-cluster task create "Debug the error: 'TypeError: unsupported operand type(s) for +: 'int' and 'str'' in line 42 of data_processor.py"
```

**CI/CD Setup:**
```bash
insanity-cluster task create "Set up GitHub Actions workflow for Python project with pytest, linting, and Docker build"
```

### Use Cases

1. **Rapid Prototyping**: Generate MVPs quickly
2. **Code Maintenance**: Refactor and improve existing code
3. **Bug Fixing**: Identify and fix issues
4. **Documentation**: Keep docs up to date
5. **DevOps**: Automate deployment pipelines

### Output Validation

The Developer Agent validates outputs by:
- Syntax checking (linting)
- Running tests if available
- Checking for common security issues
- Verifying code style compliance

---

## 2. Communication Agent

### Capabilities

The Communication Agent handles all communication tasks:

#### Phone Calls
- Make and receive phone calls via Twilio
- Convert speech to text in real-time
- Generate appropriate responses
- Convert text to speech for output
- Handle multi-turn conversations

#### Email Management
- Compose professional emails
- Send emails via SendGrid or AWS SES
- Parse and respond to incoming emails
- Manage email templates
- Handle attachments

#### Meeting Scheduling
- Schedule meetings via Google Calendar
- Find available time slots
- Send calendar invitations
- Handle rescheduling requests
- Set up recurring meetings

#### SMS/Text Messaging
- Send SMS messages via Twilio
- Handle incoming messages
- Manage conversation threads
- Support multimedia messages

#### Voice Interactions
- Real-time voice processing (< 1s latency)
- Voice activity detection
- Streaming audio transcription
- Natural conversation flow

### Model Preferences

- **Primary**: Claude Haiku 4.5 (fast, good for real-time)
- **Alternative**: gpt-5-mini (cost-effective)
- **Fallback**: local:mistral (for simple messages)

### Example Commands

**Send Email:**
```bash
insanity-cluster task create "Send an email to team@example.com with subject 'Project Update' and include our progress this week"
```

**Make Phone Call:**
```bash
insanity-cluster task create "Call +1-555-0123 and ask about their availability for a meeting next week"
```

**Schedule Meeting:**
```bash
insanity-cluster task create "Schedule a 1-hour meeting with john@example.com next Tuesday at 2pm"
```

**Send SMS:**
```bash
insanity-cluster task create "Send SMS to +1-555-0123: 'Your appointment is confirmed for tomorrow at 10am'"
```

### Use Cases

1. **Customer Support**: Handle customer inquiries
2. **Sales Outreach**: Contact potential customers
3. **Appointment Scheduling**: Manage calendars
4. **Team Communication**: Send updates and notifications
5. **Voice Assistants**: Build voice-enabled applications

### Performance Targets

- Speech-to-text: < 500ms latency
- Text-to-speech: < 300ms latency
- Total round-trip: < 1 second
- Email delivery: < 5 seconds

---

## 3. Business Agent

### Capabilities

The Business Agent handles legal and business operations:

#### LLC Formation
- Generate formation documents
- File with state authorities via LegalZoom API
- Create operating agreements
- Generate EIN applications
- Handle registered agent setup

#### Contract Management
- Analyze contracts for key terms
- Identify risks and obligations
- Generate contract templates
- Review and redline documents
- Track contract deadlines

#### Compliance Monitoring
- Track regulatory requirements
- Monitor compliance deadlines
- Generate compliance reports
- Alert on upcoming obligations
- Maintain audit trails

#### Financial Records
- Maintain bookkeeping records
- Generate financial statements
- Track expenses and revenue
- Prepare tax documents
- Create budget reports

#### Legal Research
- Research legal requirements
- Analyze case law
- Generate legal memos
- Provide compliance guidance

### Model Preferences

- **Primary**: Claude Opus 4.1 (excellent for legal reasoning)
- **Alternative**: gpt-5.1 (strong reasoning capabilities)
- **Fallback**: Claude Sonnet 4.5 (for simpler tasks)

### Example Commands

**Form LLC:**
```bash
insanity-cluster task create "Form an LLC in Delaware named TechStartup Inc with John Doe as registered agent"
```

**Contract Review:**
```bash
insanity-cluster task create "Review the NDA in contracts/nda.pdf and identify any concerning clauses"
```

**Compliance Check:**
```bash
insanity-cluster task create "What are the compliance requirements for a SaaS company operating in California?"
```

**Financial Report:**
```bash
insanity-cluster task create "Generate a profit and loss statement for Q3 2025"
```

### Use Cases

1. **Startup Formation**: Set up new businesses
2. **Contract Management**: Handle legal documents
3. **Compliance**: Stay compliant with regulations
4. **Financial Management**: Track business finances
5. **Legal Research**: Understand legal requirements

### Important Notes

- Legal advice should be reviewed by licensed attorneys
- Agent provides information, not legal counsel
- Always verify critical legal decisions
- Maintain human oversight for important matters

---

## 4. Research Agent

### Capabilities

The Research Agent conducts comprehensive research:

#### Web Search
- Search multiple sources simultaneously
- Gather data from websites, articles, papers
- Extract relevant information
- Verify source credibility
- Track citations

#### Data Synthesis
- Combine information from multiple sources
- Identify patterns and trends
- Generate insights and conclusions
- Create structured summaries
- Highlight key findings

#### Report Generation
- Create comprehensive reports
- Include citations and references
- Generate executive summaries
- Add visualizations and charts
- Format for different audiences

#### Competitive Analysis
- Compare products and services
- Analyze market positioning
- Identify strengths and weaknesses
- Generate comparison matrices
- Provide strategic recommendations

#### Trend Analysis
- Identify emerging trends
- Analyze historical data
- Predict future developments
- Generate trend reports
- Provide actionable insights

### Model Preferences

- **Primary**: Claude Sonnet 4.5 (excellent for synthesis)
- **Alternative**: gpt-5-mini (for web search)
- **Fallback**: local:llama3:70b (for analysis)

### Example Commands

**Market Research:**
```bash
insanity-cluster task create "Research the top 5 project management tools and create a comparison report with pricing, features, and user reviews"
```

**Competitive Analysis:**
```bash
insanity-cluster task create "Analyze our competitors in the CRM space and identify their key differentiators"
```

**Trend Analysis:**
```bash
insanity-cluster task create "What are the emerging trends in AI development for 2025?"
```

**Technical Research:**
```bash
insanity-cluster task create "Research best practices for implementing microservices architecture"
```

### Use Cases

1. **Market Research**: Understand markets and competitors
2. **Product Research**: Evaluate products and technologies
3. **Academic Research**: Gather information for papers
4. **Due Diligence**: Research companies and opportunities
5. **Trend Monitoring**: Stay informed about industry trends

### Output Quality

Research Agent outputs include:
- Multiple verified sources
- Citations and references
- Credibility scores for sources
- Structured data and summaries
- Actionable recommendations

---

## 5. Creative Agent

### Capabilities

The Creative Agent handles creative content:

#### Copywriting
- Write marketing copy
- Create ad campaigns
- Generate product descriptions
- Write blog posts and articles
- Create social media content

#### Design
- Generate design concepts
- Create visual mockups
- Suggest color schemes
- Design logos and branding
- Create UI/UX designs

#### Content Creation
- Write long-form content
- Create video scripts
- Generate podcast outlines
- Write press releases
- Create email campaigns

#### Brand Development
- Develop brand voice
- Create brand guidelines
- Generate taglines and slogans
- Design brand identity
- Create style guides

### Model Preferences

- **Primary**: gpt-5.1 (excellent for creative writing)
- **Alternative**: Claude Sonnet 4.5 (strong reasoning)
- **Vision Models**: For design and visual tasks

### Example Commands

**Marketing Copy:**
```bash
insanity-cluster task create "Write compelling marketing copy for our new SaaS product that helps teams collaborate better"
```

**Blog Post:**
```bash
insanity-cluster task create "Write a 1000-word blog post about the benefits of remote work"
```

**Social Media:**
```bash
insanity-cluster task create "Create 5 engaging social media posts for our product launch"
```

**Brand Development:**
```bash
insanity-cluster task create "Develop a brand voice guide for a fintech startup targeting millennials"
```

### Use Cases

1. **Marketing**: Create marketing materials
2. **Content Marketing**: Generate blog content
3. **Social Media**: Manage social presence
4. **Branding**: Develop brand identity
5. **Advertising**: Create ad campaigns

### Validation

Creative Agent validates outputs by:
- Checking brand consistency
- Verifying tone and style
- Ensuring clarity and engagement
- Checking for plagiarism
- Scoring content quality

---

## 6. Finance Agent

### Capabilities

The Finance Agent manages financial operations:

#### Accounting
- Maintain general ledger
- Record transactions
- Reconcile accounts
- Generate journal entries
- Track accounts payable/receivable

#### Budgeting
- Create budget plans
- Track budget vs. actual
- Generate variance reports
- Forecast future expenses
- Provide budget recommendations

#### Invoicing
- Generate invoices
- Track payment status
- Send payment reminders
- Process payments via Stripe/PayPal
- Handle refunds and credits

#### Financial Reporting
- Generate P&L statements
- Create balance sheets
- Generate cash flow statements
- Create financial dashboards
- Prepare tax documents

#### Payment Processing
- Process credit card payments
- Handle ACH transfers
- Manage subscriptions
- Process refunds
- Track payment history

### Model Preferences

- **Primary**: gpt-5-mini (good for calculations)
- **Alternative**: Claude Sonnet 4.5 (for analysis)
- **Validation**: Always verify calculations

### Example Commands

**Generate Invoice:**
```bash
insanity-cluster task create "Create an invoice for Acme Corp for $5,000 for consulting services in October"
```

**Financial Report:**
```bash
insanity-cluster task create "Generate a profit and loss statement for Q3 2025"
```

**Budget Analysis:**
```bash
insanity-cluster task create "Analyze our Q3 spending and compare to budget"
```

**Payment Processing:**
```bash
insanity-cluster task create "Process a $1,000 payment from customer ID 12345"
```

### Use Cases

1. **Bookkeeping**: Maintain financial records
2. **Invoicing**: Bill customers
3. **Budgeting**: Plan and track budgets
4. **Reporting**: Generate financial reports
5. **Payment Processing**: Handle transactions

### Important Notes

- Always verify financial calculations
- Maintain audit trails
- Follow accounting standards
- Ensure data security
- Review critical transactions

---

## 7. Project Manager Agent

### Capabilities

The Project Manager Agent handles project management:

#### Project Planning
- Create project plans
- Define milestones and deliverables
- Estimate timelines and resources
- Identify dependencies
- Create Gantt charts

#### Progress Tracking
- Monitor task completion
- Track project status
- Identify blockers
- Generate status reports
- Update stakeholders

#### Risk Management
- Identify project risks
- Assess risk impact
- Create mitigation plans
- Monitor risk indicators
- Generate risk reports

#### Resource Management
- Allocate team members
- Track resource utilization
- Identify resource conflicts
- Optimize resource allocation
- Generate capacity reports

#### Reporting
- Create status reports
- Generate executive summaries
- Track KPIs and metrics
- Create dashboards
- Provide recommendations

### Model Preferences

- **Primary**: gpt-5-mini (for tracking)
- **Alternative**: Claude Haiku 4.5 (for reporting)
- **Fallback**: local:mistral (for simple updates)

### Example Commands

**Create Project Plan:**
```bash
insanity-cluster task create "Create a project plan for building a mobile app with 3 developers over 3 months"
```

**Status Report:**
```bash
insanity-cluster task create "Generate a weekly status report for the website redesign project"
```

**Risk Assessment:**
```bash
insanity-cluster task create "Identify risks for our Q4 product launch"
```

**Resource Planning:**
```bash
insanity-cluster task create "Analyze team capacity for next quarter and identify resource needs"
```

### Use Cases

1. **Project Planning**: Plan new projects
2. **Status Tracking**: Monitor progress
3. **Risk Management**: Identify and mitigate risks
4. **Resource Planning**: Optimize team allocation
5. **Stakeholder Communication**: Keep everyone informed

### Validation

Project Manager Agent validates by:
- Checking timeline feasibility
- Verifying resource availability
- Assessing risk likelihood
- Ensuring plan completeness
- Validating dependencies

---

## Multi-Agent Collaboration

Agents can work together on complex tasks:

### Example: Launch a SaaS Product

```bash
insanity-cluster task create "Launch a SaaS product: build the application, create marketing materials, set up payment processing, and form an LLC"
```

**Agent Collaboration:**

1. **Business Agent**: Forms LLC, handles legal setup
2. **Developer Agent**: Builds the application
3. **Creative Agent**: Creates marketing materials
4. **Finance Agent**: Sets up payment processing
5. **Project Manager Agent**: Coordinates everything
6. **Communication Agent**: Sends launch announcements

### Example: Customer Onboarding

```bash
insanity-cluster task create "Onboard new customer: send welcome email, schedule kickoff call, create project plan, and set up billing"
```

**Agent Collaboration:**

1. **Communication Agent**: Sends welcome email, schedules call
2. **Project Manager Agent**: Creates project plan
3. **Finance Agent**: Sets up billing
4. **Developer Agent**: Provisions customer account

---

## Best Practices

### 1. Choose the Right Agent

Match tasks to agent capabilities:
- Code → Developer Agent
- Legal → Business Agent
- Research → Research Agent
- Communication → Communication Agent

### 2. Provide Context

Include relevant context in commands:
```bash
# Good
insanity-cluster task create "Write a Python function to validate email addresses using regex"

# Better
insanity-cluster task create "Write a Python function to validate email addresses using regex. Should handle international domains and return True/False. Include docstring and type hints."
```

### 3. Break Down Complex Tasks

For very complex tasks, break them into steps:
```bash
# Instead of one huge task
insanity-cluster task create "Build a complete e-commerce platform"

# Break it down
insanity-cluster task create "Design database schema for e-commerce platform"
insanity-cluster task create "Build user authentication system"
insanity-cluster task create "Create product catalog API"
```

### 4. Review Agent Outputs

Always review agent outputs, especially for:
- Legal documents (Business Agent)
- Financial calculations (Finance Agent)
- Critical code (Developer Agent)
- Important communications (Communication Agent)

### 5. Use Task-Type Overrides

Configure specific models for critical tasks:
```yaml
task_type_overrides:
  legal_analysis:
    model_override: claude-opus-4.1
    strategy_override: QUALITY_FIRST
  
  code_generation:
    model_override: claude-sonnet-4.5
    strategy_override: QUALITY_FIRST
```

---

## Support

For agent-specific questions:
- Documentation: https://docs.insanitycluster.com/agents
- Discord: https://discord.gg/insanity-cluster
- Email: support@insanitycluster.com
