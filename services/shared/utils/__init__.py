"""
Shared utilities module containing common functionality for microservices.
"""

from .retry import CircuitBreaker, with_retry

__all__ = ["CircuitBreaker", "with_retry"]
