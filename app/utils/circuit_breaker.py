"""
Circuit Breaker Pattern

Prevents cascading failures by stopping requests to a failing service.

States:
- CLOSED: Normal operation, requests pass through
- OPEN: Service is failing, requests fail fast
- HALF_OPEN: Testing if service has recovered

Flow:
1. CLOSED → OPEN: After threshold failures
2. OPEN → HALF_OPEN: After timeout period
3. HALF_OPEN → CLOSED: After successful test requests
4. HALF_OPEN → OPEN: If test requests fail
"""

import logging
import time
import threading
from enum import Enum
from typing import Callable, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""
    pass


class CircuitBreaker:
    """
    Circuit breaker for external service calls.
    
    Protects against cascading failures by failing fast when a service is down.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        success_threshold: int = 2,
        name: str = "circuit_breaker"
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying half-open
            success_threshold: Successes needed in half-open to close
            name: Name for logging
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        
        self.lock = threading.Lock()
        
        logger.info(
            f"CircuitBreaker '{name}' initialized: "
            f"failure_threshold={failure_threshold}, "
            f"recovery_timeout={recovery_timeout}s"
        )
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker.
        
        Args:
            func: Function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments
            
        Returns:
            Function result
            
        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Original exception from func
        """
        with self.lock:
            # Check if we should transition to half-open
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    logger.info(f"CircuitBreaker '{self.name}': Attempting recovery (OPEN → HALF_OPEN)")
                    self.state = CircuitState.HALF_OPEN
                    self.success_count = 0
                else:
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker '{self.name}' is OPEN. "
                        f"Service unavailable, failing fast."
                    )
        
        # Execute the function
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
    
    def _on_success(self):
        """Handle successful call."""
        with self.lock:
            self.failure_count = 0
            
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                logger.info(
                    f"CircuitBreaker '{self.name}': Success in HALF_OPEN "
                    f"({self.success_count}/{self.success_threshold})"
                )
                
                if self.success_count >= self.success_threshold:
                    logger.info(f"CircuitBreaker '{self.name}': Recovery successful (HALF_OPEN → CLOSED)")
                    self.state = CircuitState.CLOSED
                    self.success_count = 0
    
    def _on_failure(self):
        """Handle failed call."""
        with self.lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.state == CircuitState.HALF_OPEN:
                logger.warning(f"CircuitBreaker '{self.name}': Failed in HALF_OPEN (HALF_OPEN → OPEN)")
                self.state = CircuitState.OPEN
                self.success_count = 0
            
            elif self.state == CircuitState.CLOSED:
                logger.warning(
                    f"CircuitBreaker '{self.name}': Failure "
                    f"({self.failure_count}/{self.failure_threshold})"
                )
                
                if self.failure_count >= self.failure_threshold:
                    logger.error(f"CircuitBreaker '{self.name}': Too many failures (CLOSED → OPEN)")
                    self.state = CircuitState.OPEN
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self.last_failure_time is None:
            return True
        
        elapsed = time.time() - self.last_failure_time
        return elapsed >= self.recovery_timeout
    
    def get_state(self) -> dict:
        """Get current circuit breaker state."""
        with self.lock:
            return {
                'name': self.name,
                'state': self.state.value,
                'failure_count': self.failure_count,
                'success_count': self.success_count,
                'last_failure_time': datetime.fromtimestamp(
                    self.last_failure_time, tz=timezone.utc
                ).isoformat() if self.last_failure_time else None
            }
    
    def reset(self):
        """Manually reset circuit breaker to CLOSED state."""
        with self.lock:
            logger.info(f"CircuitBreaker '{self.name}': Manual reset to CLOSED")
            self.state = CircuitState.CLOSED
            self.failure_count = 0
            self.success_count = 0
            self.last_failure_time = None


# Global circuit breakers
_openai_circuit_breaker: Optional[CircuitBreaker] = None
_circuit_breaker_lock = threading.Lock()


def get_openai_circuit_breaker() -> CircuitBreaker:
    """Get the global OpenAI circuit breaker instance."""
    global _openai_circuit_breaker
    
    if _openai_circuit_breaker is None:
        with _circuit_breaker_lock:
            if _openai_circuit_breaker is None:
                _openai_circuit_breaker = CircuitBreaker(
                    failure_threshold=5,
                    recovery_timeout=60,
                    success_threshold=2,
                    name="openai_api"
                )
    
    return _openai_circuit_breaker

