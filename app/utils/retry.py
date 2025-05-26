"""
Retry utility for RQ background jobs with exponential backoff.
"""
import time
import logging
from functools import wraps
from rq import get_current_job

logger = logging.getLogger(__name__)


def retry_on_failure(max_retries=3, delay=5, backoff=2, exceptions=(Exception,)):
    """
    Retry decorator for RQ jobs with exponential backoff.
    
    Args:
        max_retries (int): Maximum number of retry attempts
        delay (int): Initial delay between retries in seconds
        backoff (int): Backoff multiplier for exponential delay
        exceptions (tuple): Tuple of exception types to catch and retry
    
    Returns:
        Decorated function that will retry on failure
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            job = get_current_job()
            job_id = job.id if job else 'unknown'
            retries = 0
            current_delay = delay
            
            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    retries += 1
                    if retries > max_retries:
                        logger.error(f"Job {job_id} failed after {max_retries} retries: {str(e)}")
                        raise
                    
                    logger.warning(f"Job {job_id} failed (attempt {retries}/{max_retries}), "
                                 f"retrying in {current_delay}s: {str(e)}")
                    time.sleep(current_delay)
                    current_delay *= backoff
        return wrapper
    return decorator 