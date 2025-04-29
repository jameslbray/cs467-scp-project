"""
Shared utilities package for microservices.

This package contains shared code, utilities, and common functionality
that can be used across different microservices.
"""

from .utils.retry import CircuitBreaker, with_retry

__all__ = ["CircuitBreaker", "with_retry"]
