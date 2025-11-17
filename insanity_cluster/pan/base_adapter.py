"""
Base adapter class for AI model providers.
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional

from .models import (
    GenerationParams,
    PricingInfo,
    Response,
    StreamChunk,
    APIError,
    TimeoutError,
    RateLimitError,
)

logger = logging.getLogger(__name__)


class ProviderAdapter(ABC):
    """
    Abstract base class for AI model provider adapters.
    
    All provider adapters must implement this interface to ensure
    consistent behavior across different AI model providers.
    """
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        Initialize the provider adapter.
        
        Args:
            api_key: API key for authentication (if required)
            base_url: Base URL for API endpoint (if custom)
        """
        self.api_key = api_key
        self.base_url = base_url
        self._retry_attempts = 3
        self._retry_delay = 1.0  # Initial delay in seconds
        
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        model: str,
        params: Optional[GenerationParams] = None
    ) -> Response:
        """
        Generate a response from the model.
        
        Args:
            prompt: The input prompt
            model: Model identifier
            params: Generation parameters
            
        Returns:
            Response object with generated content and metadata
            
        Raises:
            APIError: If the API call fails
            TimeoutError: If the request times out
            RateLimitError: If rate limit is exceeded
        """
        pass
    
    @abstractmethod
    async def stream_generate(
        self,
        prompt: str,
        model: str,
        params: Optional[GenerationParams] = None
    ) -> AsyncIterator[StreamChunk]:
        """
        Generate a streaming response from the model.
        
        Args:
            prompt: The input prompt
            model: Model identifier
            params: Generation parameters
            
        Yields:
            StreamChunk objects with partial content
            
        Raises:
            APIError: If the API call fails
            TimeoutError: If the request times out
            RateLimitError: If rate limit is exceeded
        """
        pass
    
    @abstractmethod
    def get_pricing(self, model: str) -> PricingInfo:
        """
        Get pricing information for a model.
        
        Args:
            model: Model identifier
            
        Returns:
            PricingInfo object with cost details
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the provider is available and healthy.
        
        Returns:
            True if provider is healthy, False otherwise
        """
        pass
    
    async def _retry_with_backoff(self, func, *args, **kwargs):
        """
        Retry a function with exponential backoff.
        
        Args:
            func: Async function to retry
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func
            
        Returns:
            Result from func
            
        Raises:
            Exception: Last exception if all retries fail
        """
        last_exception = None
        delay = self._retry_delay
        
        for attempt in range(self._retry_attempts):
            try:
                return await func(*args, **kwargs)
            except RateLimitError as e:
                last_exception = e
                # Use retry_after if provided, otherwise exponential backoff
                wait_time = e.retry_after if e.retry_after else delay
                logger.warning(
                    f"Rate limit hit on attempt {attempt + 1}/{self._retry_attempts}. "
                    f"Retrying in {wait_time}s..."
                )
                await asyncio.sleep(wait_time)
                delay *= 2  # Exponential backoff
            except (APIError, TimeoutError) as e:
                last_exception = e
                if attempt < self._retry_attempts - 1:
                    logger.warning(
                        f"Request failed on attempt {attempt + 1}/{self._retry_attempts}: {e}. "
                        f"Retrying in {delay}s..."
                    )
                    await asyncio.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    logger.error(f"Request failed after {self._retry_attempts} attempts: {e}")
            except Exception as e:
                # Don't retry on unexpected errors
                logger.error(f"Unexpected error: {e}")
                raise
        
        # All retries exhausted
        if last_exception:
            raise last_exception
        
    def _count_tokens(self, text: str) -> int:
        """
        Estimate token count for text.
        
        This is a simple approximation. For accurate counts,
        use provider-specific tokenizers.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Estimated token count
        """
        # Rough approximation: 1 token ≈ 4 characters
        return len(text) // 4
