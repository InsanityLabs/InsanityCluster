"""
Redis connection management for caching and message queues
"""
import json
from typing import Any, Optional, List, Dict
from datetime import timedelta

import redis.asyncio as redis
from redis.asyncio import ConnectionPool

from insanity_cluster.common.config import settings


class RedisManager:
    """Manages Redis connections for caching and message queues"""

    def __init__(self):
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[redis.Redis] = None

    async def initialize(self):
        """Initialize Redis connection pool"""
        if self._pool is not None:
            return

        # Create connection pool
        self._pool = ConnectionPool.from_url(
            settings.redis_url,
            max_connections=50,
            decode_responses=True,
            socket_keepalive=True,
            socket_connect_timeout=5,
            retry_on_timeout=True,
        )

        # Create Redis client
        self._client = redis.Redis(connection_pool=self._pool)

    async def close(self):
        """Close Redis connections"""
        if self._client:
            await self._client.close()
            self._client = None

        if self._pool:
            await self._pool.disconnect()
            self._pool = None

    async def health_check(self) -> bool:
        """Check if Redis connection is healthy"""
        try:
            await self._client.ping()
            return True
        except Exception:
            return False

    # ========================================================================
    # Cache Operations
    # ========================================================================

    async def cache_set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Set a value in cache with optional TTL
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds (None = no expiration)
        
        Returns:
            True if successful
        """
        try:
            serialized = json.dumps(value)
            if ttl:
                await self._client.setex(key, ttl, serialized)
            else:
                await self._client.set(key, serialized)
            return True
        except Exception:
            return False

    async def cache_get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache
        
        Args:
            key: Cache key
        
        Returns:
            Cached value or None if not found
        """
        try:
            value = await self._client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception:
            return None

    async def cache_delete(self, key: str) -> bool:
        """
        Delete a key from cache
        
        Args:
            key: Cache key
        
        Returns:
            True if key was deleted
        """
        try:
            result = await self._client.delete(key)
            return result > 0
        except Exception:
            return False

    async def cache_exists(self, key: str) -> bool:
        """Check if a key exists in cache"""
        try:
            return await self._client.exists(key) > 0
        except Exception:
            return False

    async def cache_expire(self, key: str, ttl: int) -> bool:
        """Set expiration time for a key"""
        try:
            return await self._client.expire(key, ttl)
        except Exception:
            return False

    async def cache_get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache"""
        try:
            values = await self._client.mget(keys)
            result = {}
            for key, value in zip(keys, values):
                if value:
                    result[key] = json.loads(value)
            return result
        except Exception:
            return {}

    async def cache_set_many(self, mapping: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set multiple values in cache"""
        try:
            pipe = self._client.pipeline()
            for key, value in mapping.items():
                serialized = json.dumps(value)
                if ttl:
                    pipe.setex(key, ttl, serialized)
                else:
                    pipe.set(key, serialized)
            await pipe.execute()
            return True
        except Exception:
            return False

    # ========================================================================
    # Session Token Cache
    # ========================================================================

    async def store_session_token(
        self,
        user_id: str,
        token: str,
        ttl: int = 86400,  # 24 hours default
    ) -> bool:
        """Store a session token with TTL"""
        key = f"session:{user_id}:{token}"
        return await self.cache_set(key, {"user_id": user_id, "token": token}, ttl=ttl)

    async def validate_session_token(self, user_id: str, token: str) -> bool:
        """Validate a session token"""
        key = f"session:{user_id}:{token}"
        return await self.cache_exists(key)

    async def invalidate_session_token(self, user_id: str, token: str) -> bool:
        """Invalidate a session token"""
        key = f"session:{user_id}:{token}"
        return await self.cache_delete(key)

    # ========================================================================
    # Command Parsing Cache
    # ========================================================================

    async def cache_parsed_command(
        self,
        command: str,
        parsed_result: Dict[str, Any],
        ttl: int = 604800,  # 7 days default
    ) -> bool:
        """Cache a parsed command result"""
        key = f"command:parsed:{hash(command)}"
        return await self.cache_set(key, parsed_result, ttl=ttl)

    async def get_cached_parsed_command(self, command: str) -> Optional[Dict[str, Any]]:
        """Get cached parsed command result"""
        key = f"command:parsed:{hash(command)}"
        return await self.cache_get(key)

    # ========================================================================
    # Redis Streams for Message Queues
    # ========================================================================

    async def stream_add(
        self,
        stream_name: str,
        data: Dict[str, Any],
        max_len: Optional[int] = 10000,
    ) -> str:
        """
        Add a message to a Redis Stream
        
        Args:
            stream_name: Name of the stream
            data: Message data (will be JSON serialized)
            max_len: Maximum stream length (oldest messages trimmed)
        
        Returns:
            Message ID
        """
        # Serialize all values to strings
        serialized_data = {k: json.dumps(v) for k, v in data.items()}
        
        message_id = await self._client.xadd(
            stream_name,
            serialized_data,
            maxlen=max_len,
            approximate=True,
        )
        return message_id

    async def stream_read(
        self,
        stream_name: str,
        count: int = 10,
        block: Optional[int] = None,
        last_id: str = "0",
    ) -> List[Dict[str, Any]]:
        """
        Read messages from a Redis Stream
        
        Args:
            stream_name: Name of the stream
            count: Maximum number of messages to read
            block: Block for N milliseconds if no messages (None = don't block)
            last_id: Read messages after this ID
        
        Returns:
            List of messages with their IDs
        """
        streams = {stream_name: last_id}
        
        if block is not None:
            results = await self._client.xread(streams, count=count, block=block)
        else:
            results = await self._client.xread(streams, count=count)
        
        messages = []
        for stream, stream_messages in results:
            for message_id, data in stream_messages:
                # Deserialize message data
                deserialized = {k: json.loads(v) for k, v in data.items()}
                messages.append({
                    "id": message_id,
                    "stream": stream,
                    "data": deserialized,
                })
        
        return messages

    async def stream_ack(self, stream_name: str, group_name: str, message_id: str) -> int:
        """Acknowledge a message in a consumer group"""
        return await self._client.xack(stream_name, group_name, message_id)

    async def stream_create_group(
        self,
        stream_name: str,
        group_name: str,
        start_id: str = "0",
    ) -> bool:
        """Create a consumer group for a stream"""
        try:
            await self._client.xgroup_create(stream_name, group_name, id=start_id, mkstream=True)
            return True
        except redis.ResponseError as e:
            # Group already exists
            if "BUSYGROUP" in str(e):
                return True
            raise

    async def stream_read_group(
        self,
        stream_name: str,
        group_name: str,
        consumer_name: str,
        count: int = 10,
        block: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Read messages from a stream as part of a consumer group"""
        streams = {stream_name: ">"}
        
        if block is not None:
            results = await self._client.xreadgroup(
                group_name,
                consumer_name,
                streams,
                count=count,
                block=block,
            )
        else:
            results = await self._client.xreadgroup(
                group_name,
                consumer_name,
                streams,
                count=count,
            )
        
        messages = []
        for stream, stream_messages in results:
            for message_id, data in stream_messages:
                deserialized = {k: json.loads(v) for k, v in data.items()}
                messages.append({
                    "id": message_id,
                    "stream": stream,
                    "data": deserialized,
                })
        
        return messages

    # ========================================================================
    # Queue Operations (using Redis Streams)
    # ========================================================================

    async def enqueue_task(self, task_data: Dict[str, Any]) -> str:
        """Add a task to the task queue"""
        return await self.stream_add("task_queue", task_data)

    async def enqueue_agent_task(self, agent_type: str, task_data: Dict[str, Any]) -> str:
        """Add a task to a specific agent queue"""
        stream_name = f"agent_queue:{agent_type}"
        return await self.stream_add(stream_name, task_data)

    async def enqueue_webhook(self, webhook_data: Dict[str, Any]) -> str:
        """Add a webhook delivery to the webhook queue"""
        return await self.stream_add("webhook_queue", webhook_data)

    async def dequeue_tasks(self, count: int = 10, block: Optional[int] = 1000) -> List[Dict[str, Any]]:
        """Read tasks from the task queue"""
        return await self.stream_read("task_queue", count=count, block=block, last_id="$")

    async def dequeue_agent_tasks(
        self,
        agent_type: str,
        count: int = 10,
        block: Optional[int] = 1000,
    ) -> List[Dict[str, Any]]:
        """Read tasks from a specific agent queue"""
        stream_name = f"agent_queue:{agent_type}"
        return await self.stream_read(stream_name, count=count, block=block, last_id="$")

    # ========================================================================
    # Distributed Locks
    # ========================================================================

    async def acquire_lock(
        self,
        lock_name: str,
        timeout: int = 10,
        blocking: bool = True,
        blocking_timeout: Optional[int] = None,
    ) -> Optional[redis.lock.Lock]:
        """Acquire a distributed lock"""
        lock = self._client.lock(
            f"lock:{lock_name}",
            timeout=timeout,
            blocking=blocking,
            blocking_timeout=blocking_timeout,
        )
        
        acquired = await lock.acquire()
        if acquired:
            return lock
        return None

    async def release_lock(self, lock: redis.lock.Lock) -> bool:
        """Release a distributed lock"""
        try:
            await lock.release()
            return True
        except Exception:
            return False


# Global Redis manager instance
redis_manager = RedisManager()


# Convenience functions
async def init_redis():
    """Initialize Redis connection pool"""
    await redis_manager.initialize()


async def close_redis():
    """Close Redis connections"""
    await redis_manager.close()
