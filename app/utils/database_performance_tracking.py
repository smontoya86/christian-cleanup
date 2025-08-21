"""
Simple database performance tracking.
Provides minimal interface for performance tracking without complex monitoring.
"""

import functools
from typing import Callable


def track_lyrics_call(operation_name=None):
    """
    Simple decorator for tracking database calls related to lyrics.
    In the simplified version, this just passes through the function.
    Can be used with or without arguments.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    # Handle being used as @track_lyrics_call or @track_lyrics_call("name")
    if callable(operation_name):
        # Used as @track_lyrics_call (without parentheses)
        func = operation_name
        return decorator(func)
    else:
        # Used as @track_lyrics_call("name") (with parentheses)
        return decorator


def track_database_operation(operation_name: str):
    """
    Decorator factory for tracking database operations.
    In the simplified version, this just passes through the function.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    return decorator


def record_query_performance(query_type: str, duration: float, row_count: int = 0):
    """Record query performance metrics."""
    pass  # Simplified - no actual tracking


def get_performance_stats():
    """Get basic performance statistics."""
    return {"total_queries": 0, "avg_duration": 0.0, "slow_queries": 0}
