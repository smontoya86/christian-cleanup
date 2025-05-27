"""
Advanced job retry mechanisms for RQ with intelligent error handling and recovery.
"""

import os
import time
import logging
from typing import Optional, Dict, Any, Callable, List, Type
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum

from rq import get_current_job
from rq.job import Job
from redis.exceptions import ConnectionError, TimeoutError, RedisError

# Try to import RQ exceptions - API may vary between versions
try:
    from rq.exceptions import WorkerLostError
except ImportError:
    # Define a placeholder if not available
    class WorkerLostError(Exception):
        pass

try:
    from rq.exceptions import RetryableException
except ImportError:
    # Define a placeholder if not available
    class RetryableException(Exception):
        pass

from .redis_manager import redis_manager, RetryConfig

logger = logging.getLogger(__name__)


class ErrorCategory(Enum):
    """Categories of errors for retry classification."""
    NETWORK = "network"           # Network connectivity issues
    RESOURCE = "resource"         # Resource exhaustion (memory, disk, etc.)
    EXTERNAL_API = "external_api" # External API failures
    DATABASE = "database"         # Database connectivity/transaction issues
    BUSINESS_LOGIC = "business"   # Business logic errors (usually not retryable)
    UNKNOWN = "unknown"           # Unclassified errors


@dataclass
class RetryPolicyConfig:
    """Configuration for retry policies based on error categories."""
    max_retries: int = 3
    base_delay: int = 60  # seconds
    max_delay: int = 1800  # 30 minutes
    exponential_base: float = 2.0
    jitter: bool = True  # Add random jitter to prevent thundering herd
    retry_on_categories: List[ErrorCategory] = field(default_factory=lambda: [
        ErrorCategory.NETWORK,
        ErrorCategory.RESOURCE,
        ErrorCategory.EXTERNAL_API,
        ErrorCategory.DATABASE
    ])


class ErrorClassifier:
    """Classifies errors into categories for appropriate retry handling."""
    
    # Error patterns for classification
    ERROR_PATTERNS = {
        ErrorCategory.NETWORK: [
            'connection refused',
            'network unreachable',
            'timeout',
            'connection reset',
            'connection timeout',
            'connection error',
            'redis connection',
            'socket timeout'
        ],
        ErrorCategory.RESOURCE: [
            'memory error',
            'out of memory',
            'disk space',
            'too many open files',
            'resource temporarily unavailable'
        ],
        ErrorCategory.EXTERNAL_API: [
            'api error',
            'http error 5',  # 5xx errors
            'service unavailable',
            'gateway timeout',
            'bad gateway',
            'spotify api',
            'genius api',
            'rate limit'
        ],
        ErrorCategory.DATABASE: [
            'database error',
            'sqlalchemy',
            'postgresql',
            'connection pool',
            'transaction',
            'deadlock'
        ],
        ErrorCategory.BUSINESS_LOGIC: [
            'validation error',
            'invalid input',
            'permission denied',
            'not found',
            'unauthorized'
        ]
    }
    
    @classmethod
    def classify_error(cls, error: Exception) -> ErrorCategory:
        """
        Classify an error into a category for retry decisions.
        
        Args:
            error: The exception to classify.
            
        Returns:
            ErrorCategory enum value.
        """
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()
        
        # Check exception type first
        if isinstance(error, (ConnectionError, TimeoutError, RedisError)):
            return ErrorCategory.NETWORK
        
        if isinstance(error, WorkerLostError):
            return ErrorCategory.RESOURCE
        
        # Check error message patterns
        for category, patterns in cls.ERROR_PATTERNS.items():
            for pattern in patterns:
                if pattern in error_str or pattern in error_type:
                    return category
        
        return ErrorCategory.UNKNOWN
    
    @classmethod
    def is_retryable(cls, error: Exception, retry_policy: RetryPolicyConfig) -> bool:
        """
        Determine if an error should be retried based on the retry policy.
        
        Args:
            error: The exception to evaluate.
            retry_policy: Retry policy configuration.
            
        Returns:
            True if the error should be retried, False otherwise.
        """
        category = cls.classify_error(error)
        return category in retry_policy.retry_on_categories


class JobRetryHandler:
    """Handles job retry logic with sophisticated error handling and backoff strategies."""
    
    def __init__(self, retry_policy: Optional[RetryPolicyConfig] = None):
        self.retry_policy = retry_policy or RetryPolicyConfig()
        self.redis_manager = redis_manager
    
    def calculate_delay(self, attempt: int, base_delay: int = None, jitter: bool = None) -> int:
        """
        Calculate delay for next retry attempt with exponential backoff and optional jitter.
        
        Args:
            attempt: Current attempt number (0-based).
            base_delay: Base delay in seconds. If None, uses policy default.
            jitter: Whether to add jitter. If None, uses policy default.
            
        Returns:
            Delay in seconds for the next retry.
        """
        if base_delay is None:
            base_delay = self.retry_policy.base_delay
        if jitter is None:
            jitter = self.retry_policy.jitter
        
        # Exponential backoff
        delay = base_delay * (self.retry_policy.exponential_base ** attempt)
        
        # Cap at max delay
        delay = min(delay, self.retry_policy.max_delay)
        
        # Add jitter to prevent thundering herd
        if jitter:
            import random
            jitter_amount = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_amount, jitter_amount)
        
        return max(int(delay), 1)  # Ensure minimum 1 second delay
    
    def should_retry(self, job: Job, error: Exception) -> bool:
        """
        Determine if a job should be retried based on error type and retry count.
        
        Args:
            job: RQ Job instance.
            error: Exception that caused the job to fail.
            
        Returns:
            True if the job should be retried, False otherwise.
        """
        # Get retry count from job metadata
        retry_count = job.meta.get('retry_count', 0)
        
        # Check if we've exceeded max retries
        if retry_count >= self.retry_policy.max_retries:
            logger.info(f"Job {job.id} has exceeded max retries ({self.retry_policy.max_retries})")
            return False
        
        # Check if error is retryable
        if not ErrorClassifier.is_retryable(error, self.retry_policy):
            error_category = ErrorClassifier.classify_error(error)
            logger.info(f"Job {job.id} failed with non-retryable error category: {error_category.value}")
            return False
        
        return True
    
    def handle_job_failure(self, job: Job, exc_type: Type[Exception], 
                          exc_value: Exception, traceback) -> bool:
        """
        Handle job failure with retry logic.
        
        Args:
            job: RQ Job instance.
            exc_type: Exception type.
            exc_value: Exception instance.
            traceback: Exception traceback.
            
        Returns:
            True if job was requeued for retry, False if permanently failed.
        """
        error_category = ErrorClassifier.classify_error(exc_value)
        retry_count = job.meta.get('retry_count', 0)
        
        logger.error(f"Job {job.id} failed (attempt {retry_count + 1}): {exc_value}")
        logger.error(f"Error category: {error_category.value}")
        
        # Record failure in job metadata
        if 'failure_history' not in job.meta:
            job.meta['failure_history'] = []
        
        job.meta['failure_history'].append({
            'attempt': retry_count + 1,
            'timestamp': datetime.now().isoformat(),
            'error': str(exc_value),
            'error_type': exc_type.__name__,
            'error_category': error_category.value
        })
        
        # Check if we should retry
        if not self.should_retry(job, exc_value):
            logger.error(f"Job {job.id} permanently failed after {retry_count + 1} attempts")
            # Update job metadata with final failure info
            job.meta.update({
                'final_failure': True,
                'final_error': str(exc_value),
                'final_error_category': error_category.value,
                'total_attempts': retry_count + 1
            })
            job.save_meta()
            return False
        
        # Calculate delay for retry
        delay = self.calculate_delay(retry_count)
        
        # Update retry count and metadata
        job.meta['retry_count'] = retry_count + 1
        job.meta['last_retry_delay'] = delay
        job.meta['next_retry_time'] = (datetime.now() + timedelta(seconds=delay)).isoformat()
        job.save_meta()
        
        logger.info(f"Retrying job {job.id} in {delay} seconds (attempt {retry_count + 2}/{self.retry_policy.max_retries + 1})")
        
        # Requeue the job with delay
        try:
            job.requeue(delay=delay)
            return True
        except Exception as requeue_error:
            logger.error(f"Failed to requeue job {job.id}: {requeue_error}")
            return False
    
    def get_retry_stats(self, job: Job) -> Dict[str, Any]:
        """
        Get retry statistics for a job.
        
        Args:
            job: RQ Job instance.
            
        Returns:
            Dictionary with retry statistics.
        """
        retry_count = job.meta.get('retry_count', 0)
        failure_history = job.meta.get('failure_history', [])
        
        stats = {
            'job_id': job.id,
            'retry_count': retry_count,
            'max_retries': self.retry_policy.max_retries,
            'is_final_failure': job.meta.get('final_failure', False),
            'failure_count': len(failure_history),
            'next_retry_time': job.meta.get('next_retry_time'),
            'last_retry_delay': job.meta.get('last_retry_delay'),
            'failure_categories': []
        }
        
        # Analyze failure patterns
        if failure_history:
            categories = [f['error_category'] for f in failure_history]
            stats['failure_categories'] = list(set(categories))
            stats['most_common_failure'] = max(set(categories), key=categories.count)
        
        return stats


# Global retry handler instance
default_retry_handler = JobRetryHandler()


def handle_job_exception(job: Job, exc_type: Type[Exception], 
                        exc_value: Exception, traceback) -> bool:
    """
    Global exception handler for RQ jobs with retry logic.
    
    This function can be used as an exception handler in RQ worker configuration.
    
    Args:
        job: RQ Job instance.
        exc_type: Exception type.
        exc_value: Exception instance.
        traceback: Exception traceback.
        
    Returns:
        True if job was requeued for retry, False if permanently failed.
    """
    return default_retry_handler.handle_job_failure(job, exc_type, exc_value, traceback)


def configure_retry_policy(max_retries: int = 3, base_delay: int = 60, 
                          max_delay: int = 1800, exponential_base: float = 2.0,
                          jitter: bool = True, 
                          retry_categories: Optional[List[ErrorCategory]] = None) -> RetryPolicyConfig:
    """
    Configure a custom retry policy.
    
    Args:
        max_retries: Maximum number of retry attempts.
        base_delay: Base delay in seconds.
        max_delay: Maximum delay in seconds.
        exponential_base: Base for exponential backoff.
        jitter: Whether to add random jitter.
        retry_categories: List of error categories to retry on.
        
    Returns:
        RetryPolicyConfig instance.
    """
    if retry_categories is None:
        retry_categories = [
            ErrorCategory.NETWORK,
            ErrorCategory.RESOURCE,
            ErrorCategory.EXTERNAL_API,
            ErrorCategory.DATABASE
        ]
    
    return RetryPolicyConfig(
        max_retries=max_retries,
        base_delay=base_delay,
        max_delay=max_delay,
        exponential_base=exponential_base,
        jitter=jitter,
        retry_on_categories=retry_categories
    )


def get_job_retry_stats(job_id: str) -> Optional[Dict[str, Any]]:
    """
    Get retry statistics for a job by ID.
    
    Args:
        job_id: Job ID to get stats for.
        
    Returns:
        Dictionary with retry statistics or None if job not found.
    """
    try:
        connection = redis_manager.get_connection()
        job = Job.fetch(job_id, connection=connection)
        return default_retry_handler.get_retry_stats(job)
    except Exception as e:
        logger.error(f"Error getting retry stats for job {job_id}: {e}")
        return None


def create_resilient_job(queue_name: str, func: Callable, *args, 
                        retry_policy: Optional[RetryPolicyConfig] = None, 
                        job_timeout: Optional[int] = None, **kwargs) -> Job:
    """
    Create a job with enhanced retry capabilities.
    
    Args:
        queue_name: Name of the queue to enqueue the job.
        func: Function to execute.
        *args: Positional arguments for the function.
        retry_policy: Custom retry policy. If None, uses default.
        job_timeout: Job timeout in seconds.
        **kwargs: Keyword arguments for the function.
        
    Returns:
        RQ Job instance with retry metadata.
    """
    queue = redis_manager.get_queue(queue_name)
    
    # Create job with retry metadata
    job = queue.enqueue(
        func, 
        *args, 
        timeout=job_timeout,
        **kwargs
    )
    
    # Initialize retry metadata
    if retry_policy:
        job.meta.update({
            'retry_policy': {
                'max_retries': retry_policy.max_retries,
                'base_delay': retry_policy.base_delay,
                'max_delay': retry_policy.max_delay,
                'exponential_base': retry_policy.exponential_base,
                'jitter': retry_policy.jitter,
                'retry_categories': [cat.value for cat in retry_policy.retry_on_categories]
            }
        })
    
    job.meta.update({
        'retry_count': 0,
        'created_at': datetime.now().isoformat(),
        'failure_history': []
    })
    
    job.save_meta()
    
    logger.info(f"Created resilient job {job.id} in queue {queue_name}")
    return job 