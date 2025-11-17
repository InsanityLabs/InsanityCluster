"""
Qdrant vector database client for semantic search and embeddings
"""
from typing import List, Dict, Any, Optional
from uuid import uuid4

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    SearchRequest,
)

from insanity_cluster.common.config import settings


class VectorStore:
    """Manages Qdrant vector database for embeddings and semantic search"""

    # Collection names
    TASK_PATTERNS = "task_patterns"
    CONTEXT_EMBEDDINGS = "context_embeddings"
    AGENT_KNOWLEDGE = "agent_knowledge"

    def __init__(self):
        self._client: Optional[QdrantClient] = None
        self._embedding_dim = 1536  # OpenAI ada-002 dimension

    async def initialize(self):
        """Initialize Qdrant client and create collections"""
        if self._client is not None:
            return

        # Create Qdrant client
        self._client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
            api_key=settings.qdrant_api_key,
            timeout=60,
        )

        # Create collections if they don't exist
        await self._create_collections()

    async def close(self):
        """Close Qdrant client"""
        if self._client:
            self._client.close()
            self._client = None

    async def _create_collections(self):
        """Create vector collections if they don't exist"""
        collections = [
            (self.TASK_PATTERNS, "Task decomposition patterns for caching"),
            (self.CONTEXT_EMBEDDINGS, "Session context for semantic retrieval"),
            (self.AGENT_KNOWLEDGE, "Domain-specific knowledge for agents"),
        ]

        for collection_name, description in collections:
            # Check if collection exists
            try:
                self._client.get_collection(collection_name)
            except Exception:
                # Collection doesn't exist, create it
                self._client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=self._embedding_dim,
                        distance=Distance.COSINE,
                    ),
                )

    async def health_check(self) -> bool:
        """Check if Qdrant connection is healthy"""
        try:
            collections = self._client.get_collections()
            return True
        except Exception:
            return False

    # ========================================================================
    # Generic Vector Operations
    # ========================================================================

    async def store_embedding(
        self,
        collection_name: str,
        vector: List[float],
        payload: Dict[str, Any],
        point_id: Optional[str] = None,
    ) -> str:
        """
        Store an embedding vector with metadata
        
        Args:
            collection_name: Name of the collection
            vector: Embedding vector
            payload: Metadata to store with the vector
            point_id: Optional ID for the point (generated if not provided)
        
        Returns:
            Point ID
        """
        if point_id is None:
            point_id = str(uuid4())

        point = PointStruct(
            id=point_id,
            vector=vector,
            payload=payload,
        )

        self._client.upsert(
            collection_name=collection_name,
            points=[point],
        )

        return point_id

    async def store_embeddings_batch(
        self,
        collection_name: str,
        vectors: List[List[float]],
        payloads: List[Dict[str, Any]],
        point_ids: Optional[List[str]] = None,
    ) -> List[str]:
        """Store multiple embeddings in batch"""
        if point_ids is None:
            point_ids = [str(uuid4()) for _ in vectors]

        points = [
            PointStruct(id=pid, vector=vec, payload=pay)
            for pid, vec, pay in zip(point_ids, vectors, payloads)
        ]

        self._client.upsert(
            collection_name=collection_name,
            points=points,
        )

        return point_ids

    async def search_similar(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: Optional[float] = None,
        filter_conditions: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar vectors
        
        Args:
            collection_name: Name of the collection
            query_vector: Query embedding vector
            limit: Maximum number of results
            score_threshold: Minimum similarity score (0-1)
            filter_conditions: Optional metadata filters
        
        Returns:
            List of search results with scores and payloads
        """
        search_filter = None
        if filter_conditions:
            # Build filter from conditions
            conditions = []
            for key, value in filter_conditions.items():
                conditions.append(
                    FieldCondition(
                        key=key,
                        match=MatchValue(value=value),
                    )
                )
            search_filter = Filter(must=conditions)

        results = self._client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=search_filter,
        )

        return [
            {
                "id": result.id,
                "score": result.score,
                "payload": result.payload,
            }
            for result in results
        ]

    async def delete_points(
        self,
        collection_name: str,
        point_ids: List[str],
    ) -> bool:
        """Delete points from a collection"""
        try:
            self._client.delete(
                collection_name=collection_name,
                points_selector=point_ids,
            )
            return True
        except Exception:
            return False

    async def get_point(
        self,
        collection_name: str,
        point_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get a specific point by ID"""
        try:
            points = self._client.retrieve(
                collection_name=collection_name,
                ids=[point_id],
            )
            if points:
                point = points[0]
                return {
                    "id": point.id,
                    "vector": point.vector,
                    "payload": point.payload,
                }
            return None
        except Exception:
            return None

    # ========================================================================
    # Task Pattern Operations
    # ========================================================================

    async def store_task_pattern(
        self,
        command: str,
        embedding: List[float],
        task_graph: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store a task decomposition pattern"""
        payload = {
            "command": command,
            "task_graph": task_graph,
            "type": "task_pattern",
            **(metadata or {}),
        }

        return await self.store_embedding(
            collection_name=self.TASK_PATTERNS,
            vector=embedding,
            payload=payload,
        )

    async def search_similar_tasks(
        self,
        query_embedding: List[float],
        limit: int = 5,
        score_threshold: float = 0.8,
    ) -> List[Dict[str, Any]]:
        """Search for similar task patterns"""
        return await self.search_similar(
            collection_name=self.TASK_PATTERNS,
            query_vector=query_embedding,
            limit=limit,
            score_threshold=score_threshold,
        )

    # ========================================================================
    # Context Embedding Operations
    # ========================================================================

    async def store_context_embedding(
        self,
        session_id: str,
        user_id: str,
        embedding: List[float],
        context_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store a context embedding for semantic retrieval"""
        payload = {
            "session_id": session_id,
            "user_id": user_id,
            "context_data": context_data,
            "type": "context",
            **(metadata or {}),
        }

        return await self.store_embedding(
            collection_name=self.CONTEXT_EMBEDDINGS,
            vector=embedding,
            payload=payload,
            point_id=session_id,
        )

    async def search_similar_contexts(
        self,
        query_embedding: List[float],
        user_id: Optional[str] = None,
        limit: int = 10,
        score_threshold: float = 0.7,
    ) -> List[Dict[str, Any]]:
        """Search for similar contexts"""
        filter_conditions = {}
        if user_id:
            filter_conditions["user_id"] = user_id

        return await self.search_similar(
            collection_name=self.CONTEXT_EMBEDDINGS,
            query_vector=query_embedding,
            limit=limit,
            score_threshold=score_threshold,
            filter_conditions=filter_conditions if filter_conditions else None,
        )

    async def delete_context_embeddings(self, session_ids: List[str]) -> bool:
        """Delete context embeddings by session IDs"""
        return await self.delete_points(
            collection_name=self.CONTEXT_EMBEDDINGS,
            point_ids=session_ids,
        )

    # ========================================================================
    # Agent Knowledge Operations
    # ========================================================================

    async def store_agent_knowledge(
        self,
        agent_type: str,
        knowledge_id: str,
        embedding: List[float],
        knowledge_data: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Store domain-specific knowledge for an agent"""
        payload = {
            "agent_type": agent_type,
            "knowledge_id": knowledge_id,
            "knowledge_data": knowledge_data,
            "type": "agent_knowledge",
            **(metadata or {}),
        }

        return await self.store_embedding(
            collection_name=self.AGENT_KNOWLEDGE,
            vector=embedding,
            payload=payload,
            point_id=knowledge_id,
        )

    async def search_agent_knowledge(
        self,
        query_embedding: List[float],
        agent_type: Optional[str] = None,
        limit: int = 10,
        score_threshold: float = 0.75,
    ) -> List[Dict[str, Any]]:
        """Search for relevant agent knowledge"""
        filter_conditions = {}
        if agent_type:
            filter_conditions["agent_type"] = agent_type

        return await self.search_similar(
            collection_name=self.AGENT_KNOWLEDGE,
            query_vector=query_embedding,
            limit=limit,
            score_threshold=score_threshold,
            filter_conditions=filter_conditions if filter_conditions else None,
        )

    async def delete_agent_knowledge(self, knowledge_ids: List[str]) -> bool:
        """Delete agent knowledge by IDs"""
        return await self.delete_points(
            collection_name=self.AGENT_KNOWLEDGE,
            point_ids=knowledge_ids,
        )

    # ========================================================================
    # Collection Management
    # ========================================================================

    async def get_collection_info(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """Get information about a collection"""
        try:
            info = self._client.get_collection(collection_name)
            return {
                "name": collection_name,
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status,
            }
        except Exception:
            return None

    async def count_points(self, collection_name: str) -> int:
        """Count points in a collection"""
        try:
            info = self._client.get_collection(collection_name)
            return info.points_count
        except Exception:
            return 0


# Global vector store instance
vector_store = VectorStore()


# Convenience functions
async def init_vector_store():
    """Initialize Qdrant vector store"""
    await vector_store.initialize()


async def close_vector_store():
    """Close Qdrant vector store"""
    await vector_store.close()
