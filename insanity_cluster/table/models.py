"""
SQLAlchemy models for the TABLE layer
"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Text,
    DateTime,
    ForeignKey,
    DECIMAL,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    """User model for authentication and authorization"""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    api_key_hash = Column(String(255), nullable=True)
    role = Column(String(50), nullable=False, default="user")
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    tasks = relationship("Task", back_populates="user", cascade="all, delete-orphan")
    contexts = relationship("Context", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, role={self.role})>"


class Task(Base):
    """Task model for tracking user requests and execution"""

    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    command = Column(Text, nullable=False)
    status = Column(String(50), nullable=False, default="pending", index=True)
    task_graph = Column(JSONB, nullable=True)
    result = Column(JSONB, nullable=True)
    cost = Column(DECIMAL(10, 4), default=0.0, nullable=False)
    latency_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    completed_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="tasks")
    metrics = relationship("Metric", back_populates="task", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("idx_tasks_user_status", "user_id", "status"),
        Index("idx_tasks_created_status", "created_at", "status"),
    )

    def __repr__(self):
        return f"<Task(id={self.id}, status={self.status}, command={self.command[:50]}...)>"


class Context(Base):
    """Context model for maintaining conversation and task state"""

    __tablename__ = "context"

    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    context_data = Column(JSONB, nullable=False)
    last_accessed = Column(DateTime, default=func.now(), nullable=False, index=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="contexts")

    # Indexes
    __table_args__ = (Index("idx_context_user_accessed", "user_id", "last_accessed"),)

    def __repr__(self):
        return f"<Context(session_id={self.session_id}, user_id={self.user_id})>"


class Metric(Base):
    """Metric model for tracking performance and cost metrics"""

    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True)
    layer = Column(String(50), nullable=False)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=func.now(), nullable=False, index=True)

    # Relationships
    task = relationship("Task", back_populates="metrics")

    # Indexes
    __table_args__ = (
        Index("idx_metrics_layer_name", "layer", "metric_name"),
        Index("idx_metrics_timestamp_layer", "timestamp", "layer"),
    )

    def __repr__(self):
        return f"<Metric(layer={self.layer}, name={self.metric_name}, value={self.metric_value})>"


class Configuration(Base):
    """Configuration model for storing user and system configurations"""

    __tablename__ = "configurations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    config_data = Column(JSONB, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    is_active = Column(String(50), default=False, nullable=False)
    is_default = Column(String(50), default=False, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Indexes
    __table_args__ = (
        Index("idx_config_user_active", "user_id", "is_active"),
        Index("idx_config_user_name", "user_id", "name"),
    )

    def __repr__(self):
        return f"<Configuration(id={self.id}, name={self.name}, version={self.version})>"


class ConfigurationHistory(Base):
    """Configuration history for tracking changes over time"""

    __tablename__ = "configuration_history"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    config_id = Column(UUID(as_uuid=True), ForeignKey("configurations.id", ondelete="CASCADE"), nullable=False)
    config_data = Column(JSONB, nullable=False)
    version = Column(Integer, nullable=False)
    changed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    change_description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Indexes
    __table_args__ = (
        Index("idx_config_history_config_version", "config_id", "version"),
        Index("idx_config_history_created", "created_at"),
    )

    def __repr__(self):
        return f"<ConfigurationHistory(config_id={self.config_id}, version={self.version})>"
