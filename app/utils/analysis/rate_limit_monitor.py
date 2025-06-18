import logging
import time
from typing import Dict, Optional
from datetime import datetime, timedelta
import threading
from collections import defaultdict, deque

logger = logging.getLogger(__name__)

class RateLimitMonitor:
    """
    Monitor and manage rate limits for analysis operations.
    Even though we use local models, this helps track resource usage and prevent abuse.
    """
    
    def __init__(self):
        self._request_history = defaultdict(deque)  # IP/user -> request timestamps
        self._daily_counts = defaultdict(int)       # IP/user -> daily request count
        self._last_reset = datetime.now().date()
        self._lock = threading.Lock()
        
        # Conservative limits to prevent resource abuse
        self.limits = {
            'requests_per_minute': 30,      # Reasonable for local processing
            'requests_per_hour': 200,       # Allow for reasonable testing
            'requests_per_day': 1000,       # Match HF free tier for consistency
            'concurrent_requests': 5        # Prevent CPU/GPU overload
        }
        
        self._active_requests = 0
        logger.info("Rate limit monitor initialized with local model limits")
    
    def check_rate_limit(self, identifier: str = "default") -> Dict[str, any]:
        """
        Check if the request is within rate limits.
        Returns status and remaining quota information.
        """
        with self._lock:
            now = datetime.now()
            current_time = time.time()
            
            # Reset daily counters if needed
            if now.date() > self._last_reset:
                self._daily_counts.clear()
                self._last_reset = now.date()
            
            # Clean old entries (keep last hour)
            cutoff_time = current_time - 3600
            self._request_history[identifier] = deque(
                [ts for ts in self._request_history[identifier] if ts > cutoff_time]
            )
            
            # Check various limits
            minute_requests = sum(1 for ts in self._request_history[identifier] 
                                if ts > current_time - 60)
            hour_requests = len(self._request_history[identifier])
            daily_requests = self._daily_counts[identifier]
            
            # Determine if request should be allowed
            limits_status = {
                'allowed': True,
                'reason': None,
                'retry_after': 0,
                'quotas': {
                    'minute': {'used': minute_requests, 'limit': self.limits['requests_per_minute']},
                    'hour': {'used': hour_requests, 'limit': self.limits['requests_per_hour']},
                    'day': {'used': daily_requests, 'limit': self.limits['requests_per_day']},
                    'concurrent': {'used': self._active_requests, 'limit': self.limits['concurrent_requests']}
                }
            }
            
            # Check concurrent requests
            if self._active_requests >= self.limits['concurrent_requests']:
                limits_status.update({
                    'allowed': False,
                    'reason': 'Too many concurrent requests',
                    'retry_after': 5
                })
                return limits_status
            
            # Check per-minute limit
            if minute_requests >= self.limits['requests_per_minute']:
                limits_status.update({
                    'allowed': False,
                    'reason': 'Rate limit exceeded (per minute)',
                    'retry_after': 60
                })
                return limits_status
            
            # Check per-hour limit
            if hour_requests >= self.limits['requests_per_hour']:
                limits_status.update({
                    'allowed': False,
                    'reason': 'Rate limit exceeded (per hour)',
                    'retry_after': 3600
                })
                return limits_status
            
            # Check daily limit
            if daily_requests >= self.limits['requests_per_day']:
                limits_status.update({
                    'allowed': False,
                    'reason': 'Daily quota exceeded',
                    'retry_after': 86400
                })
                return limits_status
            
            return limits_status
    
    def record_request(self, identifier: str = "default") -> None:
        """Record a new request for rate limiting purposes."""
        with self._lock:
            current_time = time.time()
            self._request_history[identifier].append(current_time)
            self._daily_counts[identifier] += 1
            self._active_requests += 1
            
            logger.debug(f"Request recorded for {identifier}. "
                        f"Active: {self._active_requests}, "
                        f"Daily: {self._daily_counts[identifier]}")
    
    def complete_request(self, identifier: str = "default") -> None:
        """Mark a request as completed to free up concurrent slots."""
        with self._lock:
            if self._active_requests > 0:
                self._active_requests -= 1
            
            logger.debug(f"Request completed for {identifier}. "
                        f"Active: {self._active_requests}")
    
    def get_usage_stats(self, identifier: str = "default") -> Dict[str, any]:
        """Get current usage statistics for monitoring."""
        with self._lock:
            now = time.time()
            
            # Clean old entries
            cutoff_time = now - 3600
            self._request_history[identifier] = deque(
                [ts for ts in self._request_history[identifier] if ts > cutoff_time]
            )
            
            minute_requests = sum(1 for ts in self._request_history[identifier] 
                                if ts > now - 60)
            hour_requests = len(self._request_history[identifier])
            daily_requests = self._daily_counts[identifier]
            
            return {
                'current_usage': {
                    'minute': minute_requests,
                    'hour': hour_requests,
                    'day': daily_requests,
                    'concurrent': self._active_requests
                },
                'limits': self.limits.copy(),
                'percentages': {
                    'minute': (minute_requests / self.limits['requests_per_minute']) * 100,
                    'hour': (hour_requests / self.limits['requests_per_hour']) * 100,
                    'day': (daily_requests / self.limits['requests_per_day']) * 100,
                    'concurrent': (self._active_requests / self.limits['concurrent_requests']) * 100
                }
            }

# Global instance
rate_monitor = RateLimitMonitor() 