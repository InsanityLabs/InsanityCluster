"""
Embedding generation utilities for vector search
"""
from typing import List, Optional
import hashlib

from insanity_cluster.common.config import settings


class EmbeddingGenerator:
    """Generates embeddings for text using various providers"""

    def __init__(self):
        self._openai_client = None
        self._cache: dict = {}

    async def initialize(self):
        """Initialize embedding providers"""
        # Initialize OpenAI client if API key is available
        if settings.openai_api_key:
            try:
                from openai import AsyncOpenAI
                self._openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
            except ImportError:
                pass

    async def generate_embedding(
        self,
        text: str,
        model: str = "text-embedding-ada-002",
        use_cache: bool = True,
    ) -> List[float]:
        """
        Generate embedding for text
        
        Args:
            text: Text to embed
            model: Embedding model to use
            use_cache: Whether to use cached embeddings
        
        Returns:
            Embedding vector
        """
        # Check cache
        if use_cache:
            cache_key = self._get_cache_key(text, model)
            if cache_key in self._cache:
                return self._cache[cache_key]

        # Generate embedding based on available provider
        if self._openai_client:
            embedding = await self._generate_openai_embedding(text, model)
        else:
            # Fallback to simple hash-based embedding (for development/testing)
            embedding = self._generate_simple_embedding(text)

        # Cache the result
        if use_cache:
            cache_key = self._get_cache_key(text, model)
            self._cache[cache_key] = embedding

        return embedding

    async def generate_embeddings_batch(
        self,
        texts: List[str],
        model: str = "text-embedding-ada-002",
    ) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        if self._openai_client:
            return await self._generate_openai_embeddings_batch(texts, model)
        else:
            return [self._generate_simple_embedding(text) for text in texts]

    async def _generate_openai_embedding(self, text: str, model: str) -> List[float]:
        """Generate embedding using OpenAI API"""
        response = await self._openai_client.embeddings.create(
            input=text,
            model=model,
        )
        return response.data[0].embedding

    async def _generate_openai_embeddings_batch(
        self,
        texts: List[str],
        model: str,
    ) -> List[List[float]]:
        """Generate embeddings in batch using OpenAI API"""
        response = await self._openai_client.embeddings.create(
            input=texts,
            model=model,
        )
        return [item.embedding for item in response.data]

    def _generate_simple_embedding(self, text: str, dim: int = 1536) -> List[float]:
        """
        Generate a simple hash-based embedding for development/testing
        This is NOT suitable for production use
        """
        # Create a deterministic hash
        hash_obj = hashlib.sha256(text.encode())
        hash_bytes = hash_obj.digest()

        # Convert to float vector
        embedding = []
        for i in range(dim):
            byte_idx = i % len(hash_bytes)
            value = (hash_bytes[byte_idx] / 255.0) * 2 - 1  # Normalize to [-1, 1]
            embedding.append(value)

        # Normalize to unit vector
        magnitude = sum(x * x for x in embedding) ** 0.5
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]

        return embedding

    def _get_cache_key(self, text: str, model: str) -> str:
        """Generate cache key for text and model"""
        return f"{model}:{hashlib.md5(text.encode()).hexdigest()}"

    def clear_cache(self):
        """Clear embedding cache"""
        self._cache.clear()


# Global embedding generator instance
embedding_generator = EmbeddingGenerator()


# Convenience functions
async def init_embeddings():
    """Initialize embedding generator"""
    await embedding_generator.initialize()


async def generate_embedding(text: str, use_cache: bool = True) -> List[float]:
    """Generate embedding for text"""
    return await embedding_generator.generate_embedding(text, use_cache=use_cache)


async def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for multiple texts"""
    return await embedding_generator.generate_embeddings_batch(texts)
