"""Reliability patterns: retry, circuit breaker, backoff.

Provides resilient execution with automatic recovery.
"""

from __future__ import annotations

import asyncio
import inspect
import random
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any, TypeVar, cast

T = TypeVar("T")


class BackoffStrategy(str, Enum):
    """Backoff strategy types."""

    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    FIBONACCI = "fibonacci"


class RetryExhaustedError(Exception):
    """Raised when all retry attempts are exhausted."""

    def __init__(self, attempts: int, last_error: Exception):
        self.attempts = attempts
        self.last_error = last_error
        super().__init__(f"Retry exhausted after {attempts} attempts: {last_error}")


@dataclass(slots=True)
class RetryConfig:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL
    jitter: bool = True
    backoff_multiplier: float = 2.0

    def __post_init__(self) -> None:
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if self.initial_delay < 0:
            raise ValueError("initial_delay must be >= 0")
        if self.max_delay < 0:
            raise ValueError("max_delay must be >= 0")
        if self.max_delay and self.initial_delay > self.max_delay:
            raise ValueError("initial_delay cannot be greater than max_delay")
        if self.backoff_multiplier <= 0:
            raise ValueError("backoff_multiplier must be > 0")


def fibonacci(n: int) -> int:
    """Calculate nth Fibonacci number."""
    if n <= 1:
        return 1
    a, b = 1, 1
    for _ in range(n - 1):
        a, b = b, a + b
    return b


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """Calculate delay for given attempt."""
    if attempt < 1:
        raise ValueError("attempt must be >= 1")

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

    delay = min(delay, config.max_delay) if config.max_delay > 0 else delay

    if config.jitter and delay > 0:
        # Full jitter-ish scaling. Humans love randomness right up until production.
        delay *= 0.5 + random.random()

    return max(0.0, delay)


async def _maybe_await(result: T | Awaitable[T]) -> T:
    """Await result if needed."""
    if inspect.isawaitable(result):
        return cast(T, await result)
    return cast(T, result)


async def retry_async(
    func: Callable[..., T] | Callable[..., Awaitable[T]],
    *args: Any,
    config: RetryConfig | None = None,
    should_retry: Callable[[Exception], bool] | None = None,
    **kwargs: Any,
) -> T:
    """Retry a function with backoff in async contexts.

    Supports both async and sync callables.
    """
    retry_config = config or RetryConfig()
    retry_predicate = should_retry or (lambda exc: True)

    last_error: Exception | None = None

    for attempt in range(1, retry_config.max_attempts + 1):
        try:
            result = func(*args, **kwargs)
            return await _maybe_await(result)
        except Exception as exc:
            last_error = exc

            if attempt == retry_config.max_attempts or not retry_predicate(exc):
                raise RetryExhaustedError(attempt, exc) from exc

            delay = calculate_delay(attempt, retry_config)
            await asyncio.sleep(delay)

    assert last_error is not None
    raise RetryExhaustedError(retry_config.max_attempts, last_error)


def retry_sync(
    func: Callable[..., T],
    *args: Any,
    config: RetryConfig | None = None,
    should_retry: Callable[[Exception], bool] | None = None,
    **kwargs: Any,
) -> T:
    """Retry a sync function with backoff."""
    retry_config = config or RetryConfig()
    retry_predicate = should_retry or (lambda exc: True)

    last_error: Exception | None = None

    for attempt in range(1, retry_config.max_attempts + 1):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            last_error = exc

            if attempt == retry_config.max_attempts or not retry_predicate(exc):
                raise RetryExhaustedError(attempt, exc) from exc

            delay = calculate_delay(attempt, retry_config)
            time.sleep(delay)

    assert last_error is not None
    raise RetryExhaustedError(retry_config.max_attempts, last_error)


class CircuitState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass(slots=True)
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""

    failure_threshold: int = 5
    success_threshold: int = 2
    timeout: float = 30.0
    excluded_exceptions: tuple[type[BaseException], ...] = ()

    def __post_init__(self) -> None:
        if self.failure_threshold < 1:
            raise ValueError("failure_threshold must be >= 1")
        if self.success_threshold < 1:
            raise ValueError("success_threshold must be >= 1")
        if self.timeout < 0:
            raise ValueError("timeout must be >= 0")


class CircuitBreakerOpenError(Exception):
    """Raised when circuit is open."""


class CircuitBreaker:
    """Circuit breaker pattern implementation.

    Prevents cascading failures by failing fast when service is down.
    """

    def __init__(self, name: str, config: CircuitBreakerConfig | None = None):
        if not name.strip():
            raise ValueError("Circuit breaker name cannot be empty")

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
            elapsed = time.monotonic() - self._last_failure_time
            if elapsed >= self.config.timeout:
                self._state = CircuitState.HALF_OPEN
                self._success_count = 0
        return self._state

    def is_available(self) -> bool:
        """Check if circuit allows requests."""
        return self.state != CircuitState.OPEN

    async def call(
        self,
        func: Callable[..., T] | Callable[..., Awaitable[T]],
        *args: Any,
        **kwargs: Any,
    ) -> T:
        """Execute function with circuit breaker protection."""
        if not self.is_available():
            raise CircuitBreakerOpenError(f"Circuit {self.name} is open")

        try:
            result = func(*args, **kwargs)
            value = await _maybe_await(result)
            self._on_success()
            return value
        except Exception as exc:
            if isinstance(exc, self.config.excluded_exceptions):
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
        self._last_failure_time = time.monotonic()

        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.OPEN
            self._success_count = 0
            return

        if self._failure_count >= self.config.failure_threshold:
            self._state = CircuitState.OPEN

    def reset(self) -> None:
        """Manually reset circuit breaker."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0

    def force_open(self) -> None:
        """Manually open circuit breaker."""
        self._state = CircuitState.OPEN
        self._success_count = 0
        self._last_failure_time = time.monotonic()

    def get_state(self) -> dict[str, Any]:
        """Get circuit breaker state for monitoring."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "last_failure_monotonic": self._last_failure_time,
            "timeout": self.config.timeout,
        }


class CircuitBreakerManager:
    """Manages multiple circuit breakers."""

    def __init__(self) -> None:
        self._breakers: dict[str, CircuitBreaker] = {}

    def get_or_create(
        self,
        name: str,
        config: CircuitBreakerConfig | None = None,
    ) -> CircuitBreaker:
        """Get or create a circuit breaker."""
        if name not in self._breakers:
            self._breakers[name] = CircuitBreaker(name, config)
        return self._breakers[name]

    def get(self, name: str) -> CircuitBreaker | None:
        """Get an existing circuit breaker."""
        return self._breakers.get(name)

    def reset(self, name: str) -> bool:
        """Reset an existing circuit breaker."""
        breaker = self._breakers.get(name)
        if breaker is None:
            return False
        breaker.reset()
        return True

    def get_all_states(self) -> list[dict[str, Any]]:
        """Get state of all circuit breakers."""
        return [
            self._breakers[name].get_state()
            for name in sorted(self._breakers)
        ]
