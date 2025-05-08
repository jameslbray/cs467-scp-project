"""
Retry utility module with exponential backoff and circuit breaker patterns.
"""

import asyncio
import logging
from typing import (
    Callable,
    TypeVar,
    Optional,
    Any,
    Awaitable,
    Union,
    cast
)

logger = logging.getLogger(__name__)

T = TypeVar('T')
AsyncCallable = Callable[..., Awaitable[T]]


class CircuitBreaker:
    """Circuit breaker implementation for handling service dependencies."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        reset_timeout: float = 120.0
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failures = 0
        self.last_failure_time: float = 0.0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF-OPEN

    def record_failure(self) -> None:
        """Record a failure and potentially open the circuit."""
        self.failures += 1
        self.last_failure_time = asyncio.get_event_loop().time()
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(
                f"Circuit breaker for {self.name} opened after "
                f"{self.failures} failures"
            )

    def record_success(self) -> None:
        """Record a success and reset the circuit."""
        self.failures = 0
        self.state = "CLOSED"
        logger.info(f"Circuit breaker for {self.name} closed after success")

    def is_open(self) -> bool:
        """Check if circuit is open."""
        if self.state == "OPEN":
            current_time = asyncio.get_event_loop().time()
            if current_time - self.last_failure_time >= self.reset_timeout:
                self.state = "HALF-OPEN"
                logger.info(
                    f"Circuit breaker for {self.name} entering half-open state"
                )
                return False
            return True
        return False


async def with_retry(
    operation: Union[AsyncCallable[Any], Callable[..., Any]],
    max_attempts: int = 5,
    initial_delay: float = 5.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: float = 0.1,
    circuit_breaker: Optional[CircuitBreaker] = None,
    operation_args: tuple = (),  # Arguments for the operation
    operation_kwargs: dict = None  # Keyword arguments for the operation
) -> Any:
    """
    Execute an operation with exponential backoff retry logic.

    Args:
        operation: Async function to execute
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_base: Base for exponential backoff
        jitter: Random jitter factor to add to delay
        circuit_breaker: Optional circuit breaker instance
        *args: Positional arguments for the operation
        **kwargs: Keyword arguments for the operation

    Returns:
        The result of the operation if successful

    Raises:
        Exception: If all retry attempts fail
    """
    operation_kwargs = operation_kwargs or {}
    delay = initial_delay
    last_exception = None

    for attempt in range(max_attempts):
        try:
            # Check circuit breaker
            if circuit_breaker and circuit_breaker.is_open():
                logger.warning(
                    f"Circuit breaker for {circuit_breaker.name} is open, "
                    "skipping attempt"
                )
                await asyncio.sleep(1)  # Small delay before next check
                continue

            # Cast the operation to an async callable and await its result
            async_op = cast(AsyncCallable[Any], operation)
            result = await async_op(*operation_args, **operation_kwargs)

            # Record success in circuit breaker
            if circuit_breaker:
                circuit_breaker.record_success()

            return result

        except Exception as e:
            last_exception = e

            # Record failure in circuit breaker
            if circuit_breaker:
                circuit_breaker.record_failure()

            if attempt == max_attempts - 1:
                logger.error(
                    f"Operation failed after {max_attempts} attempts: {str(e)}"
                )
                raise

            # Calculate next delay with jitter
            jitter_amount = delay * jitter * \
                (2 * asyncio.get_event_loop().time() % 1 - 1)
            actual_delay = min(delay + jitter_amount, max_delay)

            logger.warning(
                f"Operation failed (attempt {attempt + 1}/{max_attempts}), "
                f"retrying in {actual_delay:.2f}s: {str(e)}"
            )

            await asyncio.sleep(actual_delay)
            delay = min(delay * exponential_base, max_delay)

    if last_exception:
        raise last_exception

    raise RuntimeError("Unreachable code - this should never happen")
