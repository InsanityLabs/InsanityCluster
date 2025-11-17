"""
Retry handler and circuit breaker implementation.

This module provides:
- Configurable retry policies with exponential backoff
- Circuit breaker pattern for fault tolerance
- Timeout handling for model endpoints
- Retry statistics and monitoring
"""
import asyncio
import time
import random
from typing import Callable, Optional, Any, TypeVar, Dict
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from insanity_cluster.common.configuration import (
    RetryPolicy,
    TimeoutConfig,
    CircuitBreakerConfig,
)


T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RetryStatistics:
    """Statistics for retry operations."""
    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    total_delay_seconds: float = 0.0
    last_attempt_time: Optional[datetime] = None
    last_error: Optional[str] = None


class CircuitBreaker:
    """
    Circuit breaker implementation for fault tolerance.
    """
    
    def __init__(self, config: CircuitBreakerConfig, name: str = "default"):
        """
        Initialize circuit breaker.
        
        Args:
            config: Circuit breaker configuration
            name: Name for this circuit breaker
        """
        self.config = config
        self.name = name
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.half_open_calls = 0
    
    def can_execute(self) -> bool:
        """
        Check if execution is allowed.
        
        Returns:
            True if execution is allowed, False otherwise
        """
        if self.state == CircuitState.CLOSED:
            return True
        
        if self.state == CircuitState.OPEN:
            # Check if timeout has elapsed
            if self.last_failure_time:
                elapsed = (datetime.utcnow() - self.last_failure_time).total_seconds()
                if elapsed >= self.config.timeout_seconds:
                    # Transition to half-open
                    self.state = CircuitState.HALF_OPEN
                    self.half_open_calls = 0
                    return True
            return False
        
        if self.state == CircuitState.HALF_OPEN:
            # Allow limited calls in half-open state
            if self.half_open_calls < self.config.half_open_max_calls:
                self.half_open_calls += 1
                return True
            return False
        
        return False
    
    def record_success(self):
        """Record a successful execution."""
        if self.state == CircuitState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                # Transition back to closed
                self.state = CircuitState.CLOSED
                self.failure_count = 0
                self.success_count = 0
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success
            self.failure_count = 0
    
    def record_failure(self):
        """Record a failed execution."""
        self.last_failure_time = datetime.utcnow()
        
        if self.state == CircuitState.HALF_OPEN:
            # Transition back to open
            self.state = CircuitState.OPEN
            self.success_count = 0
            self.half_open_calls = 0
        elif self.state == CircuitState.CLOSED:
            self.failure_count += 1
            if self.failure_count >= self.config.failure_threshold:
                # Transition to open
                self.state = CircuitState.OPEN
    
    def get_state(self) -> Dict[str, Any]:
        """
        Get current circuit breaker state.
        
        Returns:
            State dictionary
        """
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time.isoformat() if self.last_failure_time else None,
        }


class CircuitBreakerOpenError(Exception):
    """Exception raised when circuit breaker is open."""
    pass


class RetryHandler:
    """
    Handler for retry logic with exponential backoff.
    """
    
    def __init__(
        self,
        retry_policy: RetryPolicy,
        timeout_config: Optional[TimeoutConfig] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
    ):
        """
        Initialize retry handler.
        
        Args:
            retry_policy: Retry policy configuration
            timeout_config: Optional timeout configuration
            circuit_breaker: Optional circuit breaker
        """
        self.retry_policy = retry_policy
        self.timeout_config = timeout_config or TimeoutConfig()
        self.circuit_breaker = circuit_breaker
        self.statistics = RetryStatistics()
    
    async def execute_with_retry(
        self,
        func: Callable[..., Any],
        *args,
        **kwargs
    ) -> Any:
        """
        Execute function with retry logic.
        
        Args:
            func: Async function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            Function result
            
        Raises:
            Exception: If all retries fail
            CircuitBreakerOpenError: If circuit breaker is open
        """
        last_exception = None
        
        for attempt in range(self.retry_policy.max_attempts):
            # Check circuit breaker
            if self.circuit_breaker and not self.circuit_breaker.can_execute():
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.circuit_breaker.name}' is open"
                )
            
            try:
                self.statistics.total_attempts += 1
                self.statistics.last_attempt_time = datetime.utcnow()
                
                # Execute with timeout
                result = await asyncio.wait_for(
                    func(*args, **kwargs),
                    timeout=self.timeout_config.total_timeout_seconds,
                )
                
                # Success
                self.statistics.successful_attempts += 1
                if self.circuit_breaker:
                    self.circuit_breaker.record_success()
                
                return result
                
            except asyncio.TimeoutError as e:
                last_exception = e
                self.statistics.failed_attempts += 1
                self.statistics.last_error = f"Timeout after {self.timeout_config.total_timeout_seconds}s"
                
                if self.circuit_breaker:
                    self.circuit_breaker.record_failure()
                
                # Don't retry on timeout if it's the last attempt
                if attempt == self.retry_policy.max_attempts - 1:
                    raise
                
            except Exception as e:
                last_exception = e
                self.statistics.failed_attempts += 1
                self.statistics.last_error = str(e)
                
                if self.circuit_breaker:
                    self.circuit_breaker.record_failure()
                
                # Check if exception is retryable
                if not self._is_retryable_error(e):
                    raise
                
                # Don't retry if it's the last attempt
                if attempt == self.retry_policy.max_attempts - 1:
                    raise
            
            # Calculate delay before next retry
            if attempt < self.retry_policy.max_attempts - 1:
                delay = self.retry_policy.get_delay(attempt)
                self.statistics.total_delay_seconds += delay
                await asyncio.sleep(delay)
        
        # All retries failed
        if last_exception:
            raise last_exception
    
    def execute_with_retry_sync(
        self,
        func: Callable[..., Any],
        *args,
        **kwargs
    ) -> Any:
        """
        Execute synchronous function with retry logic.
        
        Args:
            func: Synchronous function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            Function result
            
        Raises:
            Exception: If all retries fail
            CircuitBreakerOpenError: If circuit breaker is open
        """
        last_exception = None
        
        for attempt in range(self.retry_policy.max_attempts):
            # Check circuit breaker
            if self.circuit_breaker and not self.circuit_breaker.can_execute():
                raise CircuitBreakerOpenError(
                    f"Circuit breaker '{self.circuit_breaker.name}' is open"
                )
            
            try:
                self.statistics.total_attempts += 1
                self.statistics.last_attempt_time = datetime.utcnow()
                
                # Execute function
                result = func(*args, **kwargs)
                
                # Success
                self.statistics.successful_attempts += 1
                if self.circuit_breaker:
                    self.circuit_breaker.record_success()
                
                return result
                
            except Exception as e:
                last_exception = e
                self.statistics.failed_attempts += 1
                self.statistics.last_error = str(e)
                
                if self.circuit_breaker:
                    self.circuit_breaker.record_failure()
                
                # Check if exception is retryable
                if not self._is_retryable_error(e):
                    raise
                
                # Don't retry if it's the last attempt
                if attempt == self.retry_policy.max_attempts - 1:
                    raise
            
            # Calculate delay before next retry
            if attempt < self.retry_policy.max_attempts - 1:
                delay = self.retry_policy.get_delay(attempt)
                self.statistics.total_delay_seconds += delay
                time.sleep(delay)
        
        # All retries failed
        if last_exception:
            raise last_exception
    
    def _is_retryable_error(self, error: Exception) -> bool:
        """
        Check if an error is retryable.
        
        Args:
            error: Exception to check
            
        Returns:
            True if error is retryable, False otherwise
        """
        # Common retryable errors
        retryable_error_types = (
            ConnectionError,
            TimeoutError,
            asyncio.TimeoutError,
        )
        
        if isinstance(error, retryable_error_types):
            return True
        
        # Check error message for common retryable patterns
        error_msg = str(error).lower()
        retryable_patterns = [
            "timeout",
            "connection",
            "rate limit",
            "too many requests",
            "service unavailable",
            "internal server error",
        ]
        
        return any(pattern in error_msg for pattern in retryable_patterns)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get retry statistics.
        
        Returns:
            Statistics dictionary
        """
        success_rate = (
            self.statistics.successful_attempts / self.statistics.total_attempts * 100
            if self.statistics.total_attempts > 0
            else 0.0
        )
        
        return {
            "total_attempts": self.statistics.total_attempts,
            "successful_attempts": self.statistics.successful_attempts,
            "failed_attempts": self.statistics.failed_attempts,
            "success_rate_percent": success_rate,
            "total_delay_seconds": self.statistics.total_delay_seconds,
            "last_attempt_time": self.statistics.last_attempt_time.isoformat() if self.statistics.last_attempt_time else None,
            "last_error": self.statistics.last_error,
        }
    
    def reset_statistics(self):
        """Reset retry statistics."""
        self.statistics = RetryStatistics()


class CircuitBreakerManager:
    """
    Manager for multiple circuit breakers.
    """
    
    def __init__(self):
        """Initialize circuit breaker manager."""
        self._breakers: Dict[str, CircuitBreaker] = {}
    
    def get_or_create(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
    ) -> CircuitBreaker:
        """
        Get or create a circuit breaker.
        
        Args:
            name: Circuit breaker name
            config: Optional configuration (uses default if not provided)
            
        Returns:
            CircuitBreaker instance
        """
        if name not in self._breakers:
            config = config or CircuitBreakerConfig()
            self._breakers[name] = CircuitBreaker(config, name)
        
        return self._breakers[name]
    
    def get(self, name: str) -> Optional[CircuitBreaker]:
        """
        Get a circuit breaker by name.
        
        Args:
            name: Circuit breaker name
            
        Returns:
            CircuitBreaker instance or None if not found
        """
        return self._breakers.get(name)
    
    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """
        Get states of all circuit breakers.
        
        Returns:
            Dictionary mapping names to states
        """
        return {
            name: breaker.get_state()
            for name, breaker in self._breakers.items()
        }
    
    def reset(self, name: str) -> bool:
        """
        Reset a circuit breaker to closed state.
        
        Args:
            name: Circuit breaker name
            
        Returns:
            True if reset successfully, False if not found
        """
        breaker = self._breakers.get(name)
        if breaker:
            breaker.state = CircuitState.CLOSED
            breaker.failure_count = 0
            breaker.success_count = 0
            breaker.last_failure_time = None
            return True
        return False
    
    def reset_all(self):
        """Reset all circuit breakers."""
        for breaker in self._breakers.values():
            breaker.state = CircuitState.CLOSED
            breaker.failure_count = 0
            breaker.success_count = 0
            breaker.last_failure_time = None


# Global circuit breaker manager
circuit_breaker_manager = CircuitBreakerManager()


def create_retry_handler(
    retry_policy: Optional[RetryPolicy] = None,
    timeout_config: Optional[TimeoutConfig] = None,
    circuit_breaker_name: Optional[str] = None,
    circuit_breaker_config: Optional[CircuitBreakerConfig] = None,
) -> RetryHandler:
    """
    Create a retry handler with optional circuit breaker.
    
    Args:
        retry_policy: Retry policy (uses default if not provided)
        timeout_config: Timeout configuration (uses default if not provided)
        circuit_breaker_name: Optional circuit breaker name
        circuit_breaker_config: Optional circuit breaker configuration
        
    Returns:
        RetryHandler instance
    """
    retry_policy = retry_policy or RetryPolicy()
    timeout_config = timeout_config or TimeoutConfig()
    
    circuit_breaker = None
    if circuit_breaker_name:
        circuit_breaker = circuit_breaker_manager.get_or_create(
            circuit_breaker_name,
            circuit_breaker_config,
        )
    
    return RetryHandler(
        retry_policy=retry_policy,
        timeout_config=timeout_config,
        circuit_breaker=circuit_breaker,
    )
