"""
Retry utility with exponential backoff for handling transient failures.

This module provides decorators and utilities for implementing retry logic
with configurable backoff strategies, particularly useful for external API calls
that may experience temporary failures.
"""

import logging
import random
import time
from functools import wraps
from typing import Any, Callable, Tuple, Type

import requests
from flask import current_app

logger = logging.getLogger(__name__)

# Default retryable exceptions for external API calls
DEFAULT_RETRYABLE_EXCEPTIONS = (
    requests.exceptions.ConnectionError,
    requests.exceptions.Timeout,
    requests.exceptions.HTTPError,
    requests.exceptions.RequestException,
)


def retry_with_backoff(
    max_retries: int = 3,
    initial_backoff: float = 1.0,
    backoff_multiplier: float = 2.0,
    jitter: float = 0.1,
    retryable_exceptions: Tuple[Type[Exception], ...] = DEFAULT_RETRYABLE_EXCEPTIONS,
    logger_name: str = None,
) -> Callable:
    """
    Decorator that retries the wrapped function with exponential backoff on specified exceptions.

    Args:
        max_retries: Maximum number of retry attempts
        initial_backoff: Initial backoff time in seconds
        backoff_multiplier: Multiplier for backoff time after each retry
        jitter: Random jitter factor to add to backoff time (0-1)
        retryable_exceptions: Tuple of exception types to retry on
        logger_name: Optional logger name for custom logging

    Returns:
        Decorated function with retry logic

    Example:
        @retry_with_backoff(max_retries=3, initial_backoff=2)
        def fetch_from_api():
            response = requests.get("https://api.example.com/data")
            response.raise_for_status()
            return response.json()
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Use custom logger if specified, otherwise use module logger
            retry_logger = logging.getLogger(logger_name) if logger_name else logger

            retries = 0
            backoff = initial_backoff

            while True:
                try:
                    return func(*args, **kwargs)
                except retryable_exceptions as e:
                    retries += 1
                    if retries > max_retries:
                        retry_logger.error(
                            f"Maximum retries ({max_retries}) exceeded for {func.__name__}: {str(e)}",
                            extra={
                                "function": func.__name__,
                                "max_retries": max_retries,
                                "error": str(e),
                                "error_type": type(e).__name__,
                            },
                        )
                        raise

                    # Calculate backoff with jitter
                    jitter_value = backoff * jitter * random.uniform(-1, 1)
                    sleep_time = max(0, backoff + jitter_value)

                    retry_logger.warning(
                        f"Retry {retries}/{max_retries} for {func.__name__} after {sleep_time:.2f}s. Error: {str(e)}",
                        extra={
                            "function": func.__name__,
                            "retry_attempt": retries,
                            "max_retries": max_retries,
                            "sleep_time": sleep_time,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        },
                    )

                    time.sleep(sleep_time)

                    # Increase backoff for next retry
                    backoff *= backoff_multiplier

        return wrapper

    return decorator


def retry_with_config(func: Callable = None, config_prefix: str = "RETRY") -> Callable:
    """
    Decorator that uses application configuration for retry parameters.

    Args:
        func: Function to decorate (when used without parameters)
        config_prefix: Prefix for configuration keys

    Configuration keys (with default values):
        {PREFIX}_MAX_ATTEMPTS = 3
        {PREFIX}_INITIAL_BACKOFF = 1.0
        {PREFIX}_BACKOFF_MULTIPLIER = 2.0
        {PREFIX}_JITTER = 0.1

    Example:
        @retry_with_config
        def api_call():
            pass

        @retry_with_config(config_prefix='SPOTIFY_RETRY')
        def spotify_api_call():
            pass
    """

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args, **kwargs) -> Any:
            # Get configuration from Flask app
            try:
                config = current_app.config
                max_retries = config.get(f"{config_prefix}_MAX_ATTEMPTS", 3)
                initial_backoff = config.get(f"{config_prefix}_INITIAL_BACKOFF", 1.0)
                backoff_multiplier = config.get(f"{config_prefix}_BACKOFF_MULTIPLIER", 2.0)
                jitter = config.get(f"{config_prefix}_JITTER", 0.1)
            except RuntimeError:
                # No application context, use defaults
                max_retries = 3
                initial_backoff = 1.0
                backoff_multiplier = 2.0
                jitter = 0.1

            # Apply retry logic with configuration
            retry_decorator = retry_with_backoff(
                max_retries=max_retries,
                initial_backoff=initial_backoff,
                backoff_multiplier=backoff_multiplier,
                jitter=jitter,
            )

            return retry_decorator(f)(*args, **kwargs)

        return wrapper

    if func is None:
        return decorator
    else:
        return decorator(func)


def should_retry_http_error(response: requests.Response) -> bool:
    """
    Determine if an HTTP error should be retried based on status code.

    Args:
        response: HTTP response object

    Returns:
        True if the error should be retried, False otherwise
    """
    # Retry on server errors (5xx) and some client errors
    retryable_status_codes = {
        429,  # Too Many Requests (rate limiting)
        500,  # Internal Server Error
        502,  # Bad Gateway
        503,  # Service Unavailable
        504,  # Gateway Timeout
        507,  # Insufficient Storage
        508,  # Loop Detected
        510,  # Not Extended
        511,  # Network Authentication Required
    }

    return response.status_code in retryable_status_codes


class RetryableHTTPError(requests.exceptions.HTTPError):
    """Custom exception for HTTP errors that should be retried."""

    pass


def raise_retryable_http_error(response: requests.Response) -> None:
    """
    Raise appropriate exception based on HTTP response.

    Args:
        response: HTTP response object

    Raises:
        RetryableHTTPError: For retryable HTTP errors
        requests.exceptions.HTTPError: For non-retryable HTTP errors
    """
    if should_retry_http_error(response):
        raise RetryableHTTPError(
            f"Retryable HTTP {response.status_code} error: {response.reason}", response=response
        )
    else:
        response.raise_for_status()


def requests_with_retry(
    max_retries: int = 3,
    initial_backoff: float = 1.0,
    backoff_multiplier: float = 2.0,
    jitter: float = 0.1,
) -> Callable:
    """
    Decorator specifically for requests-based functions with intelligent HTTP error handling.

    Args:
        max_retries: Maximum number of retry attempts
        initial_backoff: Initial backoff time in seconds
        backoff_multiplier: Multiplier for backoff time after each retry
        jitter: Random jitter factor to add to backoff time

    Returns:
        Decorated function with retry logic for HTTP requests

    Example:
        @requests_with_retry(max_retries=3, initial_backoff=2)
        def fetch_spotify_data():
            response = requests.get("https://api.spotify.com/v1/me")
            raise_retryable_http_error(response)
            return response.json()
    """
    # Include RetryableHTTPError in retryable exceptions
    retryable_exceptions = DEFAULT_RETRYABLE_EXCEPTIONS + (RetryableHTTPError,)

    return retry_with_backoff(
        max_retries=max_retries,
        initial_backoff=initial_backoff,
        backoff_multiplier=backoff_multiplier,
        jitter=jitter,
        retryable_exceptions=retryable_exceptions,
    )


def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 1.0) -> Callable:
    """
    Decorator that retries a function on failure with configurable delay and backoff.

    Designed primarily for RQ worker tasks that may experience transient failures.

    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry attempt

    Returns:
        Decorated function with retry logic

    Example:
        @retry_on_failure(max_retries=3, delay=2, backoff=2)
        def worker_task():
            # Task that might fail transiently
            pass
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            attempts = 0
            current_delay = delay

            while attempts <= max_retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1

                    # If we've exhausted retries, re-raise the exception
                    if attempts > max_retries:
                        logger.error(
                            f"Function {func.__name__} failed after {max_retries} retries: {str(e)}",
                            extra={
                                "function": func.__name__,
                                "attempts": attempts,
                                "max_retries": max_retries,
                                "error": str(e),
                                "error_type": type(e).__name__,
                            },
                        )
                        raise

                    # Log the retry attempt
                    logger.warning(
                        f"Function {func.__name__} failed (attempt {attempts}/{max_retries + 1}), retrying in {current_delay}s: {str(e)}",
                        extra={
                            "function": func.__name__,
                            "attempt": attempts,
                            "max_retries": max_retries,
                            "delay": current_delay,
                            "error": str(e),
                            "error_type": type(e).__name__,
                        },
                    )

                    # Sleep before retrying
                    time.sleep(current_delay)

                    # Apply backoff for next retry
                    current_delay *= backoff

        return wrapper

    return decorator
