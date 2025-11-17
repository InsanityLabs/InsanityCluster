"""
CRUST Layer - Specialized Agent Framework

Provides domain-specific agents for executing subtasks:
- BaseAgent: Abstract base class for all agents
- DeveloperAgent: Code generation, review, debugging
- CommunicationAgent: Phone calls, emails, scheduling
- BusinessAgent: LLC formation, contracts, compliance
- ResearchAgent: Web search, data synthesis, reports
- CreativeAgent: Copywriting, design, content
- FinanceAgent: Accounting, invoicing, reporting
- ProjectManagerAgent: Planning, tracking, risk management
"""
from insanity_cluster.crust.base_agent import (
    AgentExecutionError,
    BaseAgent,
    CoordinationError,
    ValidationError,
)
from insanity_cluster.crust.business_agent import BusinessAgent
from insanity_cluster.crust.communication_agent import CommunicationAgent
from insanity_cluster.crust.creative_agent import CreativeAgent
from insanity_cluster.crust.developer_agent import DeveloperAgent
from insanity_cluster.crust.finance_agent import FinanceAgent
from insanity_cluster.crust.project_manager_agent import ProjectManagerAgent
from insanity_cluster.crust.research_agent import ResearchAgent

__all__ = [
    "BaseAgent",
    "AgentExecutionError",
    "CoordinationError",
    "ValidationError",
    "BusinessAgent",
    "CommunicationAgent",
    "CreativeAgent",
    "DeveloperAgent",
    "FinanceAgent",
    "ProjectManagerAgent",
    "ResearchAgent",
]
