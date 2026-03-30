"""Reliability patterns: retry, circuit breaker, backoff.

Provides resilient execution with automatic recovery.
"""

import asyncio
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, TypeVar


T = TypeVar("T")


class BackoffStrategy(Enum):
    """Backoff strategy types."""
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIBONACCI = "fibonacci"


class RetryExhausted(Exception):
    """Raised when all retry attempts are exhausted."""
    
    def __init__(self, attempts: int, last_error: Exception):
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(f"Retry exhausted after {attempts} attempts: {last_error}")


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    jitter: bool = True
    backoff_multiplier: float = 2.0


def calculate_delay(
    attempt: int,
    config: RetryConfig,
) -> float:
    """Calculate delay for given attempt."""
    if config.strategy == BackoffStrategy.FIXED:
        delay = config.initial_delay
    elif config.strategy == BackoffStrategy.LINEAR:
        delay = config.initial_delay + (attempt - 1) * config.backoff_multiplier
    elif config.strategy == BackoffStrategy.EXPONENTIAL:
        delay = config.initial_delay * (config.backoff_multiplier ** (attempt - 1))
    elif config.strategy == BackoffStrategy.FIBONACCI:
        delay = config.initial_delay * fibonacci(attempt)
    else:
        delay = config.initial_delay
        
    delay = min(delay, config.max_delay)
    
    if config.jitter:
        delay = delay * (0.5 + random.random())
        
    return delay


def fibonacci(n: int) -> int:
    """Calculate nth Fibonacci number."""
    if n <= 1:
        return 1
    a, b = 1, 1
    for _ in range(n - 1):
        a, b = b, a + b
    return b


async def retry_async(
    func: Callable[..., T],
    *args,
    config: RetryConfig | None = None,
    should_retry: Callable[[Exception], bool] | None = None,
    **kwargs,
) -> T:
    """Retry an async function with exponential backoff.
    
    Args:
        func: Async function to retry.
        *args: Positional arguments for func.
        config: Retry configuration.
        should_retry: Function to determine if exception should retry.
        **kwargs: Keyword arguments for func.
        
    Returns:
        Result of successful function call.
        
    Raises:
        RetryExhausted: If all attempts fail.
    """
    config = config or RetryConfig()
    should_retry = should_retry or (lambda e: True)
    
    last_error = None
    
    for attempt in range(1, config.max_attempts + 1):
        try:
            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            return func(*args, **kwargs)
        except Exception as e:
            last_error = e
            
            if attempt == config.max_attempts or not should_retry(e):
                raise RetryExhausted(attempt, e) from e
                
            delay = calculate_delay(attempt, config)
            await asyncio.sleep(delay)
            
    raise RetryExhausted(config.max_attempts, last_error)


def retry_sync(
    func: Callable[..., T],
    *args,
    config: RetryConfig | None = None,
    should_retry: Callable[[Exception], bool] | None = None,
    **kwargs,
) -> T:
    """Retry a sync function with exponential backoff."""
    config = config or RetryConfig()
    should_retry = should_retry or (lambda e: True)
    
    last_error = None
    
    for attempt in range(1, config.max_attempts + 1):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_error = e
            
            if attempt == config.max_attempts or not should_retry(e):
                raise RetryExhausted(attempt, e) from e
                
            delay = calculate_delay(attempt, config)
            time.sleep(delay)
            
    raise RetryExhausted(config.max_attempts, last_error)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5
    success_threshold: int = 2
    timeout: float = 30.0
    excluded_exceptions: tuple = ()


class CircuitBreakerOpen(Exception):
    """Raised when circuit is open."""
    pass


class CircuitBreaker:
    """Circuit breaker pattern implementation.
    
    Prevents cascading failures by failing fast when service is down.
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig | None = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0
        
    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time >= self.config.timeout:
                self._state = CircuitState.HALF_OPEN
        return self._state
    
    def is_available(self) -> bool:
        """Check if circuit allows requests."""
        return self.state != CircuitState.OPEN
    
    async def call(self, func: Callable[..., T], *args, **kwargs) -> T:
        """Execute function with circuit breaker protection."""
        if not self.is_available():
            raise CircuitBreakerOpen(f"Circuit {self.name} is open")
            
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            if isinstance(e, self.config.excluded_exceptions):
                raise
            self._on_failure()
            raise
    
    def _on_success(self) -> None:
        """Handle successful call."""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            if self._success_count >= self.config.success_threshold:
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count = 0
        else:
            self._failure_count = 0
            
    def _on_failure(self) -> None:
        """Handle failed call."""
        self._failure_count += 1
        self._last_failure_time = time.time()
        
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            self._success_count = 0
        elif self._failure_count >= self.config.failure_threshold:
            self._state = CircuitState.OPEN
            
    def reset(self) -> None:
        """Manually reset circuit breaker."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0
        
    def get_state(self) -> dict[str, Any]:
        """Get circuit breaker state for monitoring."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "last_failure": self._last_failure_time,
        }


class CircuitBreakerManager:
    """Manages multiple circuit breakers."""
    
    def __init__(self):
        self._breakers: dict[str, CircuitBreaker] = {}
        
    def get_or_create(self, name: str, config: CircuitBreakerConfig | None = None) -> CircuitBreaker:
        """Get or create a circuit breaker."""
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name, config)
        return self._breakers[name]
    
    def get_all_states(self) -> list[dict[str, Any]]:
        """Get state of all circuit breakers."""
        return [cb.get_state() for cb in self._breakers.values()]
