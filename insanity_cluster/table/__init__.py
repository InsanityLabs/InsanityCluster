"""TABLE Layer - Infrastructure and foundation layer for Insanity Cluster"""

from insanity_cluster.table.database import db_manager, init_db, close_db, get_session
from insanity_cluster.table.redis_manager import redis_manager, init_redis, close_redis
from insanity_cluster.table.vector_store import vector_store, init_vector_store, close_vector_store
from insanity_cluster.table.embeddings import (
    embedding_generator,
    init_embeddings,
    generate_embedding,
    generate_embeddings_batch,
)
from insanity_cluster.table.metrics import metrics_collector, get_metrics, get_metrics_content_type
from insanity_cluster.table.models import Base, User, Task, Context, Metric

__all__ = [
    # Database
    "db_manager",
    "init_db",
    "close_db",
    "get_session",
    # Redis
    "redis_manager",
    "init_redis",
    "close_redis",
    # Vector Store
    "vector_store",
    "init_vector_store",
    "close_vector_store",
    # Embeddings
    "embedding_generator",
    "init_embeddings",
    "generate_embedding",
    "generate_embeddings_batch",
    # Metrics
    "metrics_collector",
    "get_metrics",
    "get_metrics_content_type",
    # Models
    "Base",
    "User",
    "Task",
    "Context",
    "Metric",
]


async def init_table_layer():
    """Initialize all TABLE layer components"""
    await init_db()
    await init_redis()
    await init_vector_store()
    await init_embeddings()


async def close_table_layer():
    """Close all TABLE layer connections"""
    await close_db()
    await close_redis()
    await close_vector_store()
