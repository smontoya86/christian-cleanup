"""
OpenAI API Rate Limiter

Implements intelligent rate limiting for OpenAI API calls with:
- Exponential backoff with jitter
- Token bucket algorithm
- Concurrent request limiting
- Cost tracking
"""

import logging
import random
import threading
import time
from typing import Optional

logger = logging.getLogger(__name__)


class OpenAIRateLimiter:
    """
    Rate limiter for OpenAI API calls with:
    - 500 RPM limit (Tier 1)
    - Exponential backoff on 429 errors
    - Concurrent request limiting
    - Token bucket for smooth throttling
    """
    
    def __init__(
        self,
        max_rpm: int = 450,  # Leave 50 RPM buffer
        max_concurrent: int = 10,
        max_retries: int = 3
    ):
        self.max_rpm = max_rpm
        self.max_concurrent = max_concurrent
        self.max_retries = max_retries
        
        # Token bucket for smooth rate limiting
        self.tokens = max_rpm
        self.max_tokens = max_rpm
        self.refill_rate = max_rpm / 60.0  # Tokens per second
        self.last_refill = time.time()
        
        # Concurrent request tracking
        self.active_requests = 0
        self.lock = threading.Lock()
        
        # Request history for rate tracking
        self.request_times = []
        
        # Metrics
        self.total_requests = 0
        self.total_retries = 0
        self.total_rate_limit_hits = 0
        
        logger.info(
            f"OpenAIRateLimiter initialized: "
            f"{max_rpm} RPM, {max_concurrent} concurrent"
        )
    
    def acquire(self) -> bool:
        """
        Acquire permission to make an API request.
        Blocks until permission is granted.
        
        Returns:
            True when permission is granted
        """
        with self.lock:
            # Wait for available slot
            while self.active_requests >= self.max_concurrent:
                logger.debug(
                    f"Waiting for concurrent slot "
                    f"({self.active_requests}/{self.max_concurrent})"
                )
                time.sleep(0.1)
            
            # Refill token bucket
            self._refill_tokens()
            
            # Wait for token
            while self.tokens < 1:
                sleep_time = 1 / self.refill_rate
                logger.debug(f"Rate limiting: waiting {sleep_time:.2f}s for token")
                time.sleep(sleep_time)
                self._refill_tokens()
            
            # Consume token
            self.tokens -= 1
            self.active_requests += 1
            self.total_requests += 1
            
            # Track request time
            current_time = time.time()
            self.request_times.append(current_time)
            
            # Clean old request times (older than 1 minute)
            self.request_times = [
                t for t in self.request_times 
                if current_time - t < 60
            ]
            
            logger.debug(
                f"Request acquired: "
                f"{len(self.request_times)}/{self.max_rpm} RPM, "
                f"{self.active_requests}/{self.max_concurrent} concurrent, "
                f"{self.tokens:.1f} tokens"
            )
            
            return True
    
    def release(self):
        """Release a request slot after completion."""
        with self.lock:
            self.active_requests = max(0, self.active_requests - 1)
            logger.debug(f"Request released: {self.active_requests} active")
    
    def _refill_tokens(self):
        """Refill token bucket based on time elapsed."""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Add tokens based on elapsed time
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.max_tokens, self.tokens + tokens_to_add)
        
        self.last_refill = now
    
    def handle_rate_limit_error(self, attempt: int) -> float:
        """
        Calculate backoff time after rate limit error.
        Uses exponential backoff with jitter.
        
        Args:
            attempt: Current retry attempt (0-indexed)
            
        Returns:
            Sleep time in seconds
        """
        self.total_rate_limit_hits += 1
        
        # Exponential backoff: 2^attempt seconds
        base_delay = min(2 ** attempt, 60)  # Cap at 60 seconds
        
        # Add jitter (±20%)
        jitter = base_delay * 0.2 * (random.random() * 2 - 1)
        delay = base_delay + jitter
        
        logger.warning(
            f"Rate limit hit (attempt {attempt + 1}/{self.max_retries}). "
            f"Backing off for {delay:.1f}s"
        )
        
        return delay
    
    def get_metrics(self) -> dict:
        """Get rate limiter metrics."""
        with self.lock:
            current_rpm = len(self.request_times)
            
            return {
                'total_requests': self.total_requests,
                'total_retries': self.total_retries,
                'total_rate_limit_hits': self.total_rate_limit_hits,
                'current_rpm': current_rpm,
                'max_rpm': self.max_rpm,
                'active_requests': self.active_requests,
                'max_concurrent': self.max_concurrent,
                'available_tokens': round(self.tokens, 1),
                'capacity_percent': round((current_rpm / self.max_rpm) * 100, 1)
            }
    
    def reset_metrics(self):
        """Reset metrics counters."""
        with self.lock:
            self.total_requests = 0
            self.total_retries = 0
            self.total_rate_limit_hits = 0
            logger.info("Rate limiter metrics reset")


# Global rate limiter instance
_global_rate_limiter: Optional[OpenAIRateLimiter] = None
_limiter_lock = threading.Lock()


def get_rate_limiter() -> OpenAIRateLimiter:
    """Get the global OpenAI rate limiter instance."""
    global _global_rate_limiter
    
    if _global_rate_limiter is None:
        with _limiter_lock:
            if _global_rate_limiter is None:
                _global_rate_limiter = OpenAIRateLimiter()
    
    return _global_rate_limiter

