"""
Pytest configuration and shared fixtures
"""
import pytest
from typing import AsyncGenerator


@pytest.fixture
def sample_parsed_command():
    """Sample parsed command for testing"""
    from datetime import datetime
    from insanity_cluster.common.models import ParsedCommand
    
    return ParsedCommand(
        intent="create_llc",
        parameters={"state": "Delaware", "name": "Test LLC"},
        confidence=0.95,
        user_id="test-user-123",
        timestamp=datetime.now()
    )


@pytest.fixture
def sample_task_graph():
    """Sample task graph for testing"""
    from datetime import timedelta
    from insanity_cluster.common.models import TaskGraph, Subtask, AgentType
    
    subtasks = [
        Subtask(
            id="task-1",
            description="Research LLC requirements",
            agent_type=AgentType.RESEARCH,
            dependencies=[],
            priority=1,
            estimated_cost=0.05,
            estimated_duration=timedelta(seconds=30)
        ),
        Subtask(
            id="task-2",
            description="Generate formation documents",
            agent_type=AgentType.BUSINESS,
            dependencies=["task-1"],
            priority=2,
            estimated_cost=0.15,
            estimated_duration=timedelta(seconds=60)
        )
    ]
    
    return TaskGraph(
        root_task_id="root-task-123",
        subtasks=subtasks,
        dependencies={"task-2": ["task-1"]}
    )


@pytest.fixture
async def mock_redis():
    """Mock Redis client for testing"""
    from unittest.mock import AsyncMock
    return AsyncMock()


@pytest.fixture
async def mock_postgres():
    """Mock PostgreSQL connection for testing"""
    from unittest.mock import AsyncMock
    return AsyncMock()
