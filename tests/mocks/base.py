"""
Base Mock Service Architecture

Provides the foundation for all mock services used in testing.
Defines common interfaces and behaviors that all mock services should implement.
"""

import abc
import time
import random
from typing import Any, Dict, List, Optional, Union
from unittest.mock import MagicMock


class NetworkConditionSimulator:
    """
    Simulates various network conditions for realistic testing.
    
    Can introduce latency, failures, and other network-related issues
    to test application resilience.
    """
    
    def __init__(self, failure_rate: float = 0.0, min_latency_ms: float = 0, max_latency_ms: float = 0):
        """
        Initialize the network condition simulator.
        
        Args:
            failure_rate: Probability of network failure (0.0 to 1.0)
            min_latency_ms: Minimum latency to add in milliseconds
            max_latency_ms: Maximum latency to add in milliseconds
        """
        self.failure_rate = failure_rate
        self.min_latency_ms = min_latency_ms
        self.max_latency_ms = max_latency_ms
    
    def maybe_fail(self) -> None:
        """Raise a network error based on the failure rate."""
        if random.random() < self.failure_rate:
            raise ConnectionError("Simulated network failure")
    
    def simulate_latency(self) -> None:
        """Add simulated network latency."""
        if self.max_latency_ms > 0:
            latency = random.uniform(self.min_latency_ms, self.max_latency_ms)
            time.sleep(latency / 1000)


class BaseMockService(abc.ABC):
    """
    Base class for all mock services.
    
    Provides common functionality like network simulation, error injection,
    and consistent interfaces across all mock services.
    """
    
    def __init__(self, test_data: Optional[Dict[str, Any]] = None, 
                 network_simulator: Optional[NetworkConditionSimulator] = None):
        """
        Initialize the mock service.
        
        Args:
            test_data: Custom test data to use instead of defaults
            network_simulator: Network condition simulator for testing robustness
        """
        self.test_data = test_data or self._default_test_data()
        self.network_simulator = network_simulator or NetworkConditionSimulator()
        self._call_count = {}
        self._last_call_args = {}
    
    @abc.abstractmethod
    def _default_test_data(self) -> Dict[str, Any]:
        """Return default test data for this service."""
        pass
    
    def _simulate_network_call(self, method_name: str, *args, **kwargs) -> None:
        """
        Simulate a network call with potential failures and latency.
        
        Args:
            method_name: Name of the method being called
            *args: Method arguments
            **kwargs: Method keyword arguments
        """
        # Track call statistics
        self._call_count[method_name] = self._call_count.get(method_name, 0) + 1
        self._last_call_args[method_name] = {'args': args, 'kwargs': kwargs}
        
        # Simulate network conditions
        self.network_simulator.maybe_fail()
        self.network_simulator.simulate_latency()
    
    def get_call_count(self, method_name: str) -> int:
        """Get the number of times a method was called."""
        return self._call_count.get(method_name, 0)
    
    def get_last_call_args(self, method_name: str) -> Optional[Dict[str, Any]]:
        """Get the arguments from the last call to a method."""
        return self._last_call_args.get(method_name)
    
    def reset_call_tracking(self) -> None:
        """Reset call tracking statistics."""
        self._call_count.clear()
        self._last_call_args.clear()


class MockServiceError(Exception):
    """Base exception for mock service errors."""
    pass


class MockNetworkError(MockServiceError):
    """Exception raised for simulated network errors."""
    pass


class MockAPIError(MockServiceError):
    """Exception raised for simulated API errors."""
    
    def __init__(self, message: str, status_code: int = 500, error_type: str = "api_error"):
        super().__init__(message)
        self.status_code = status_code
        self.error_type = error_type


class MockRateLimitError(MockAPIError):
    """Exception raised for simulated rate limiting."""
    
    def __init__(self, retry_after: int = 60):
        super().__init__("Rate limit exceeded", status_code=429, error_type="rate_limit")
        self.retry_after = retry_after


class MockAuthenticationError(MockAPIError):
    """Exception raised for simulated authentication errors."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401, error_type="auth_error") 