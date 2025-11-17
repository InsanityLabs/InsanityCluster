"""
Prometheus metrics collection for monitoring and observability
"""
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
import time

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Summary,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

from insanity_cluster.common.config import settings


class MetricsCollector:
    """Collects and exposes Prometheus metrics"""

    def __init__(self):
        self.registry = CollectorRegistry()
        self._initialize_metrics()

    def _initialize_metrics(self):
        """Initialize all Prometheus metrics"""

        # ====================================================================
        # Request Metrics
        # ====================================================================

        self.request_count = Counter(
            "insanity_requests_total",
            "Total number of requests",
            ["layer", "endpoint", "status"],
            registry=self.registry,
        )

        self.request_latency = Histogram(
            "insanity_request_latency_seconds",
            "Request latency in seconds",
            ["layer", "endpoint"],
            buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
            registry=self.registry,
        )

        # ====================================================================
        # Task Metrics
        # ====================================================================

        self.task_count = Counter(
            "insanity_tasks_total",
            "Total number of tasks",
            ["status"],
            registry=self.registry,
        )

        self.task_duration = Histogram(
            "insanity_task_duration_seconds",
            "Task execution duration in seconds",
            ["status"],
            buckets=(1, 5, 10, 30, 60, 120, 300, 600, 1800),
            registry=self.registry,
        )

        self.active_tasks = Gauge(
            "insanity_active_tasks",
            "Number of currently active tasks",
            registry=self.registry,
        )

        # ====================================================================
        # Layer-Specific Latency Metrics
        # ====================================================================

        self.layer_latency = Histogram(
            "insanity_layer_latency_milliseconds",
            "Processing latency per layer in milliseconds",
            ["layer"],
            buckets=(10, 25, 50, 100, 200, 500, 1000, 2000, 5000),
            registry=self.registry,
        )

        # ====================================================================
        # Model Inference Metrics
        # ====================================================================

        self.model_requests = Counter(
            "insanity_model_requests_total",
            "Total number of model inference requests",
            ["provider", "model", "status"],
            registry=self.registry,
        )

        self.model_latency = Histogram(
            "insanity_model_latency_seconds",
            "Model inference latency in seconds",
            ["provider", "model"],
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0),
            registry=self.registry,
        )

        self.model_tokens = Counter(
            "insanity_model_tokens_total",
            "Total number of tokens processed",
            ["provider", "model", "type"],  # type: input/output
            registry=self.registry,
        )

        # ====================================================================
        # Cost Metrics
        # ====================================================================

        self.cost_total = Counter(
            "insanity_cost_dollars_total",
            "Total cost in dollars",
            ["provider", "model"],
            registry=self.registry,
        )

        self.cost_per_task = Histogram(
            "insanity_cost_per_task_dollars",
            "Cost per task in dollars",
            buckets=(0.001, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0),
            registry=self.registry,
        )

        # ====================================================================
        # Agent Metrics
        # ====================================================================

        self.agent_executions = Counter(
            "insanity_agent_executions_total",
            "Total number of agent executions",
            ["agent_type", "status"],
            registry=self.registry,
        )

        self.agent_latency = Histogram(
            "insanity_agent_latency_seconds",
            "Agent execution latency in seconds",
            ["agent_type"],
            buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0),
            registry=self.registry,
        )

        self.active_agents = Gauge(
            "insanity_active_agents",
            "Number of currently active agents",
            ["agent_type"],
            registry=self.registry,
        )

        # ====================================================================
        # Queue Metrics
        # ====================================================================

        self.queue_depth = Gauge(
            "insanity_queue_depth",
            "Number of items in queue",
            ["queue_name"],
            registry=self.registry,
        )

        self.queue_processing_time = Histogram(
            "insanity_queue_processing_seconds",
            "Time spent processing queue items",
            ["queue_name"],
            buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
            registry=self.registry,
        )

        # ====================================================================
        # Error Metrics
        # ====================================================================

        self.errors = Counter(
            "insanity_errors_total",
            "Total number of errors",
            ["layer", "error_type"],
            registry=self.registry,
        )

        self.error_rate = Gauge(
            "insanity_error_rate",
            "Error rate per layer",
            ["layer"],
            registry=self.registry,
        )

        # ====================================================================
        # Cache Metrics
        # ====================================================================

        self.cache_hits = Counter(
            "insanity_cache_hits_total",
            "Total number of cache hits",
            ["cache_type"],
            registry=self.registry,
        )

        self.cache_misses = Counter(
            "insanity_cache_misses_total",
            "Total number of cache misses",
            ["cache_type"],
            registry=self.registry,
        )

        # ====================================================================
        # WebSocket Metrics
        # ====================================================================

        self.websocket_connections = Gauge(
            "insanity_websocket_connections",
            "Number of active WebSocket connections",
            registry=self.registry,
        )

        self.websocket_messages = Counter(
            "insanity_websocket_messages_total",
            "Total number of WebSocket messages",
            ["direction"],  # sent/received
            registry=self.registry,
        )

        # ====================================================================
        # Database Metrics
        # ====================================================================

        self.db_queries = Counter(
            "insanity_db_queries_total",
            "Total number of database queries",
            ["operation"],
            registry=self.registry,
        )

        self.db_query_latency = Histogram(
            "insanity_db_query_latency_seconds",
            "Database query latency in seconds",
            ["operation"],
            buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0),
            registry=self.registry,
        )

    # ========================================================================
    # Recording Methods
    # ========================================================================

    def record_request(self, layer: str, endpoint: str, status: str, latency: float):
        """Record a request with latency"""
        self.request_count.labels(layer=layer, endpoint=endpoint, status=status).inc()
        self.request_latency.labels(layer=layer, endpoint=endpoint).observe(latency)

    def record_task(self, status: str, duration: float):
        """Record a task execution"""
        self.task_count.labels(status=status).inc()
        self.task_duration.labels(status=status).observe(duration)

    def record_layer_latency(self, layer: str, latency_ms: float):
        """Record layer processing latency in milliseconds"""
        self.layer_latency.labels(layer=layer).observe(latency_ms)

    def record_model_request(
        self,
        provider: str,
        model: str,
        status: str,
        latency: float,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost: float = 0.0,
    ):
        """Record a model inference request"""
        self.model_requests.labels(provider=provider, model=model, status=status).inc()
        self.model_latency.labels(provider=provider, model=model).observe(latency)

        if input_tokens > 0:
            self.model_tokens.labels(provider=provider, model=model, type="input").inc(
                input_tokens
            )
        if output_tokens > 0:
            self.model_tokens.labels(provider=provider, model=model, type="output").inc(
                output_tokens
            )
        if cost > 0:
            self.cost_total.labels(provider=provider, model=model).inc(cost)

    def record_task_cost(self, cost: float):
        """Record cost for a task"""
        self.cost_per_task.observe(cost)

    def record_agent_execution(self, agent_type: str, status: str, latency: float):
        """Record an agent execution"""
        self.agent_executions.labels(agent_type=agent_type, status=status).inc()
        self.agent_latency.labels(agent_type=agent_type).observe(latency)

    def record_error(self, layer: str, error_type: str):
        """Record an error"""
        self.errors.labels(layer=layer, error_type=error_type).inc()

    def record_cache_hit(self, cache_type: str):
        """Record a cache hit"""
        self.cache_hits.labels(cache_type=cache_type).inc()

    def record_cache_miss(self, cache_type: str):
        """Record a cache miss"""
        self.cache_misses.labels(cache_type=cache_type).inc()

    def record_db_query(self, operation: str, latency: float):
        """Record a database query"""
        self.db_queries.labels(operation=operation).inc()
        self.db_query_latency.labels(operation=operation).observe(latency)

    # ========================================================================
    # Gauge Updates
    # ========================================================================

    def set_active_tasks(self, count: int):
        """Set the number of active tasks"""
        self.active_tasks.set(count)

    def increment_active_tasks(self):
        """Increment active tasks counter"""
        self.active_tasks.inc()

    def decrement_active_tasks(self):
        """Decrement active tasks counter"""
        self.active_tasks.dec()

    def set_active_agents(self, agent_type: str, count: int):
        """Set the number of active agents"""
        self.active_agents.labels(agent_type=agent_type).set(count)

    def increment_active_agents(self, agent_type: str):
        """Increment active agents counter"""
        self.active_agents.labels(agent_type=agent_type).inc()

    def decrement_active_agents(self, agent_type: str):
        """Decrement active agents counter"""
        self.active_agents.labels(agent_type=agent_type).dec()

    def set_queue_depth(self, queue_name: str, depth: int):
        """Set queue depth"""
        self.queue_depth.labels(queue_name=queue_name).set(depth)

    def set_websocket_connections(self, count: int):
        """Set number of WebSocket connections"""
        self.websocket_connections.set(count)

    def increment_websocket_connections(self):
        """Increment WebSocket connections"""
        self.websocket_connections.inc()

    def decrement_websocket_connections(self):
        """Decrement WebSocket connections"""
        self.websocket_connections.dec()

    def record_websocket_message(self, direction: str):
        """Record a WebSocket message"""
        self.websocket_messages.labels(direction=direction).inc()

    # ========================================================================
    # Context Managers for Timing
    # ========================================================================

    @asynccontextmanager
    async def time_request(self, layer: str, endpoint: str):
        """Context manager to time a request"""
        start_time = time.time()
        status = "success"
        try:
            yield
        except Exception as e:
            status = "error"
            raise
        finally:
            latency = time.time() - start_time
            self.record_request(layer, endpoint, status, latency)

    @asynccontextmanager
    async def time_task(self):
        """Context manager to time a task"""
        start_time = time.time()
        status = "success"
        self.increment_active_tasks()
        try:
            yield
        except Exception:
            status = "error"
            raise
        finally:
            duration = time.time() - start_time
            self.record_task(status, duration)
            self.decrement_active_tasks()

    @asynccontextmanager
    async def time_agent(self, agent_type: str):
        """Context manager to time an agent execution"""
        start_time = time.time()
        status = "success"
        self.increment_active_agents(agent_type)
        try:
            yield
        except Exception:
            status = "error"
            raise
        finally:
            latency = time.time() - start_time
            self.record_agent_execution(agent_type, status, latency)
            self.decrement_active_agents(agent_type)

    @asynccontextmanager
    async def time_db_query(self, operation: str):
        """Context manager to time a database query"""
        start_time = time.time()
        try:
            yield
        finally:
            latency = time.time() - start_time
            self.record_db_query(operation, latency)

    # ========================================================================
    # Export Metrics
    # ========================================================================

    def export_metrics(self) -> bytes:
        """Export metrics in Prometheus format"""
        return generate_latest(self.registry)

    def get_content_type(self) -> str:
        """Get content type for metrics endpoint"""
        return CONTENT_TYPE_LATEST


# Global metrics collector instance
metrics_collector = MetricsCollector()


# Convenience functions
def get_metrics() -> bytes:
    """Get metrics in Prometheus format"""
    return metrics_collector.export_metrics()


def get_metrics_content_type() -> str:
    """Get content type for metrics"""
    return metrics_collector.get_content_type()
