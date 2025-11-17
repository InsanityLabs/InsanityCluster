"""
Context Manager for INNER layer.

Maintains conversation and task state across sessions with PostgreSQL storage,
Redis caching, and vector embeddings for semantic retrieval.
"""
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from insanity_cluster.table.database import DatabaseManager
from insanity_cluster.table.redis_manager import RedisManager
from insanity_cluster.table.vector_store import VectorStore

logger = logging.getLogger(__name__)


@dataclass
class Context:
    """Context data for a session"""
    session_id: str
    user_id: str
    conversation_history: List[Dict[str, Any]] = field(default_factory=list)
    task_history: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None):
        """Add message to conversation history"""
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        self.conversation_history.append(message)
        self.last_accessed = datetime.utcnow()
    
    def add_task(self, task_id: str):
        """Add task to task history"""
        self.task_history.append(task_id)
        self.last_accessed = datetime.utcnow()
    
    def get_recent_messages(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent messages from conversation history"""
        return self.conversation_history[-count:]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "conversation_history": self.conversation_history,
            "task_history": self.task_history,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Context":
        """Create from dictionary"""
        return cls(
            session_id=data["session_id"],
            user_id=data["user_id"],
            conversation_history=data.get("conversation_history", []),
            task_history=data.get("task_history", []),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_accessed=datetime.fromisoformat(data["last_accessed"])
        )


@dataclass
class MergedContext:
    """Merged context from multiple related tasks"""
    contexts: List[Context]
    merged_conversation: List[Dict[str, Any]]
    merged_tasks: List[str]
    common_metadata: Dict[str, Any]
    
    @property
    def total_messages(self) -> int:
        """Total number of messages across all contexts"""
        return len(self.merged_conversation)
    
    @property
    def total_tasks(self) -> int:
        """Total number of tasks across all contexts"""
        return len(self.merged_tasks)


@dataclass
class RetentionPolicy:
    """Data retention policy configuration"""
    max_age_days: int = 30
    max_messages_per_session: int = 1000
    max_sessions_per_user: int = 100
    prune_inactive_days: int = 7
    
    def should_prune(self, context: Context) -> bool:
        """Check if context should be pruned"""
        age = datetime.utcnow() - context.created_at
        inactive = datetime.utcnow() - context.last_accessed
        
        return (
            age.days > self.max_age_days or
            inactive.days > self.prune_inactive_days or
            len(context.conversation_history) > self.max_messages_per_session
        )


class ContextManager:
    """
    Maintain conversation and task state across sessions.
    
    Uses PostgreSQL for persistent storage, Redis for caching recent contexts,
    and vector embeddings for semantic context retrieval.
    """
    
    def __init__(
        self,
        database: DatabaseManager,
        redis_manager: Optional[RedisManager] = None,
        vector_store: Optional[VectorStore] = None,
        retention_policy: Optional[RetentionPolicy] = None
    ):
        """
        Initialize context manager.
        
        Args:
            database: Database manager
            redis_manager: Redis manager for caching
            vector_store: Vector store for semantic search
            retention_policy: Data retention policy
        """
        self.database = database
        self.redis_manager = redis_manager
        self.vector_store = vector_store
        self.retention_policy = retention_policy or RetentionPolicy()
        
        # Cache TTL: 1 hour
        self.cache_ttl = 3600
        
        logger.info("ContextManager initialized")
    
    async def store_context(self, session_id: str, context: Context) -> None:
        """
        Store context for session.
        
        Args:
            session_id: Session ID
            context: Context to store
        """
        logger.info(f"Storing context for session {session_id}")
        
        try:
            # Store in PostgreSQL
            await self._store_in_database(context)
            
            # Cache in Redis
            if self.redis_manager:
                await self._cache_context(context)
            
            # Store embeddings for semantic search
            if self.vector_store:
                await self._store_embeddings(context)
            
            logger.info(f"Context stored successfully for session {session_id}")
        
        except Exception as e:
            logger.error(f"Failed to store context: {e}")
            raise
    
    async def retrieve_context(self, session_id: str) -> Optional[Context]:
        """
        Retrieve context for session.
        
        Args:
            session_id: Session ID
            
        Returns:
            Context or None if not found
        """
        logger.info(f"Retrieving context for session {session_id}")
        
        # Try cache first
        if self.redis_manager:
            cached = await self._get_cached_context(session_id)
            if cached:
                logger.info("Using cached context")
                return cached
        
        # Retrieve from database
        context = await self._retrieve_from_database(session_id)
        
        if context:
            # Update cache
            if self.redis_manager:
                await self._cache_context(context)
            
            logger.info(f"Context retrieved for session {session_id}")
        else:
            logger.info(f"No context found for session {session_id}")
        
        return context
    
    async def merge_contexts(self, task_ids: List[str]) -> MergedContext:
        """
        Merge contexts from related tasks.
        
        Args:
            task_ids: List of task IDs to merge
            
        Returns:
            MergedContext with combined data
        """
        logger.info(f"Merging contexts for {len(task_ids)} tasks")
        
        # Retrieve contexts for all tasks
        contexts = []
        for task_id in task_ids:
            # Get session_id from task
            session_id = await self._get_session_for_task(task_id)
            if session_id:
                context = await self.retrieve_context(session_id)
                if context:
                    contexts.append(context)
        
        if not contexts:
            logger.warning("No contexts found to merge")
            return MergedContext(
                contexts=[],
                merged_conversation=[],
                merged_tasks=[],
                common_metadata={}
            )
        
        # Merge conversation histories
        merged_conversation = []
        for context in contexts:
            merged_conversation.extend(context.conversation_history)
        
        # Sort by timestamp
        merged_conversation.sort(
            key=lambda m: m.get("timestamp", "")
        )
        
        # Merge task histories
        merged_tasks = []
        for context in contexts:
            merged_tasks.extend(context.task_history)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_tasks = []
        for task in merged_tasks:
            if task not in seen:
                seen.add(task)
                unique_tasks.append(task)
        
        # Merge metadata (find common keys)
        common_metadata = {}
        if contexts:
            first_metadata = contexts[0].metadata
            for key, value in first_metadata.items():
                if all(c.metadata.get(key) == value for c in contexts):
                    common_metadata[key] = value
        
        logger.info(
            f"Merged {len(contexts)} contexts: "
            f"{len(merged_conversation)} messages, {len(unique_tasks)} tasks"
        )
        
        return MergedContext(
            contexts=contexts,
            merged_conversation=merged_conversation,
            merged_tasks=unique_tasks,
            common_metadata=common_metadata
        )
    
    async def prune_old_context(self, retention_policy: Optional[RetentionPolicy] = None) -> int:
        """
        Remove context based on retention policy.
        
        Args:
            retention_policy: Retention policy to use (defaults to instance policy)
            
        Returns:
            Number of contexts pruned
        """
        policy = retention_policy or self.retention_policy
        logger.info("Pruning old contexts")
        
        try:
            # Get all contexts that should be pruned
            query = """
                SELECT session_id, context_data
                FROM context
                WHERE last_accessed < $1
                   OR created_at < $2
            """
            
            cutoff_inactive = datetime.utcnow() - timedelta(days=policy.prune_inactive_days)
            cutoff_age = datetime.utcnow() - timedelta(days=policy.max_age_days)
            
            async with self.database.connection() as conn:
                rows = await conn.fetch(query, cutoff_inactive, cutoff_age)
                
                pruned_count = 0
                for row in rows:
                    session_id = row["session_id"]
                    
                    # Delete from database
                    await conn.execute(
                        "DELETE FROM context WHERE session_id = $1",
                        session_id
                    )
                    
                    # Remove from cache
                    if self.redis_manager:
                        cache_key = self._get_cache_key(session_id)
                        self.redis_manager.delete(cache_key)
                    
                    pruned_count += 1
                
                logger.info(f"Pruned {pruned_count} old contexts")
                return pruned_count
        
        except Exception as e:
            logger.error(f"Failed to prune contexts: {e}")
            raise
    
    async def search_similar_contexts(
        self,
        query: str,
        limit: int = 5
    ) -> List[Context]:
        """
        Search for similar contexts using semantic search.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of similar contexts
        """
        if not self.vector_store:
            logger.warning("Vector store not available for semantic search")
            return []
        
        try:
            # Search for similar context embeddings
            results = await self.vector_store.search_similar(
                collection="context_embeddings",
                query_text=query,
                limit=limit
            )
            
            # Retrieve full contexts
            contexts = []
            for result in results:
                session_id = result.metadata.get("session_id")
                if session_id:
                    context = await self.retrieve_context(session_id)
                    if context:
                        contexts.append(context)
            
            logger.info(f"Found {len(contexts)} similar contexts")
            return contexts
        
        except Exception as e:
            logger.error(f"Failed to search similar contexts: {e}")
            return []
    
    async def _store_in_database(self, context: Context) -> None:
        """Store context in PostgreSQL"""
        query = """
            INSERT INTO context (session_id, user_id, context_data, last_accessed)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (session_id)
            DO UPDATE SET
                context_data = EXCLUDED.context_data,
                last_accessed = EXCLUDED.last_accessed
        """
        
        context_data = json.dumps(context.to_dict())
        
        async with self.database.connection() as conn:
            await conn.execute(
                query,
                context.session_id,
                context.user_id,
                context_data,
                context.last_accessed
            )
    
    async def _retrieve_from_database(self, session_id: str) -> Optional[Context]:
        """Retrieve context from PostgreSQL"""
        query = """
            SELECT context_data
            FROM context
            WHERE session_id = $1
        """
        
        async with self.database.connection() as conn:
            row = await conn.fetchrow(query, session_id)
            
            if row:
                context_data = json.loads(row["context_data"])
                return Context.from_dict(context_data)
        
        return None
    
    async def _cache_context(self, context: Context) -> None:
        """Cache context in Redis"""
        if not self.redis_manager:
            return
        
        cache_key = self._get_cache_key(context.session_id)
        try:
            context_json = json.dumps(context.to_dict())
            self.redis_manager.setex(
                cache_key,
                self.cache_ttl,
                context_json
            )
        except Exception as e:
            logger.warning(f"Failed to cache context: {e}")
    
    async def _get_cached_context(self, session_id: str) -> Optional[Context]:
        """Get cached context from Redis"""
        if not self.redis_manager:
            return None
        
        cache_key = self._get_cache_key(session_id)
        try:
            cached_data = self.redis_manager.get(cache_key)
            if cached_data:
                context_data = json.loads(cached_data)
                return Context.from_dict(context_data)
        except Exception as e:
            logger.warning(f"Failed to get cached context: {e}")
        
        return None
    
    async def _store_embeddings(self, context: Context) -> None:
        """Store context embeddings for semantic search"""
        if not self.vector_store:
            return
        
        try:
            # Create text representation of context
            messages = context.get_recent_messages(count=10)
            text_parts = []
            for msg in messages:
                text_parts.append(f"{msg['role']}: {msg['content']}")
            
            text = "\n".join(text_parts)
            
            # Store embedding
            metadata = {
                "session_id": context.session_id,
                "user_id": context.user_id,
                "message_count": len(context.conversation_history),
                "task_count": len(context.task_history),
                "last_accessed": context.last_accessed.isoformat()
            }
            
            await self.vector_store.store_embedding(
                collection="context_embeddings",
                text=text,
                metadata=metadata
            )
        
        except Exception as e:
            logger.warning(f"Failed to store embeddings: {e}")
    
    async def _get_session_for_task(self, task_id: str) -> Optional[str]:
        """Get session ID for a task"""
        query = """
            SELECT session_id
            FROM context
            WHERE context_data::jsonb @> $1::jsonb
        """
        
        search_json = json.dumps({"task_history": [task_id]})
        
        try:
            async with self.database.connection() as conn:
                row = await conn.fetchrow(query, search_json)
                if row:
                    return row["session_id"]
        except Exception as e:
            logger.warning(f"Failed to get session for task: {e}")
        
        return None
    
    def _get_cache_key(self, session_id: str) -> str:
        """Generate cache key for session"""
        return f"context:{session_id}"
