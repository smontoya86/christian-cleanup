"""
Mock Service Factory

Provides a centralized factory for creating and configuring mock services
used in testing. Ensures consistent configuration and easy customization
of mock services across all tests.
"""

from typing import Any, Dict, Optional, Type

from .base import BaseMockService, NetworkConditionSimulator


class MockServiceFactory:
    """
    Factory for creating and configuring mock services.

    Provides a centralized place to instantiate mock services with
    consistent configuration and easy customization for different
    test scenarios.
    """

    # Registry of available mock services
    _service_registry: Dict[str, Type[BaseMockService]] = {}

    @classmethod
    def register_service(cls, name: str, service_class: Type[BaseMockService]) -> None:
        """
        Register a mock service class with the factory.

        Args:
            name: Name to register the service under
            service_class: Mock service class to register
        """
        cls._service_registry[name] = service_class

    @classmethod
    def create_service(
        cls,
        service_name: str,
        test_data: Optional[Dict[str, Any]] = None,
        network_simulator: Optional[NetworkConditionSimulator] = None,
        **kwargs,
    ) -> BaseMockService:
        """
        Create a mock service instance.

        Args:
            service_name: Name of the service to create
            test_data: Custom test data for the service
            network_simulator: Network condition simulator
            **kwargs: Additional arguments to pass to the service constructor

        Returns:
            Configured mock service instance

        Raises:
            ValueError: If the service name is not registered
        """
        if service_name not in cls._service_registry:
            available = ", ".join(cls._service_registry.keys())
            raise ValueError(f"Unknown service '{service_name}'. Available: {available}")

        service_class = cls._service_registry[service_name]
        return service_class(test_data=test_data, network_simulator=network_simulator, **kwargs)

    @classmethod
    def create_spotify_service(
        cls,
        test_data: Optional[Dict[str, Any]] = None,
        network_simulator: Optional[NetworkConditionSimulator] = None,
        **kwargs,
    ) -> "MockSpotifyService":
        """
        Create a mock Spotify service instance.

        Args:
            test_data: Custom test data for Spotify API responses
            network_simulator: Network condition simulator
            **kwargs: Additional arguments

        Returns:
            Configured MockSpotifyService instance
        """
        return cls.create_service("spotify", test_data, network_simulator, **kwargs)

    @classmethod
    def create_genius_service(
        cls,
        test_data: Optional[Dict[str, Any]] = None,
        network_simulator: Optional[NetworkConditionSimulator] = None,
        **kwargs,
    ) -> "MockGeniusService":
        """
        Create a mock Genius service instance.

        Args:
            test_data: Custom test data for Genius API responses
            network_simulator: Network condition simulator
            **kwargs: Additional arguments

        Returns:
            Configured MockGeniusService instance
        """
        return cls.create_service("genius", test_data, network_simulator, **kwargs)

    @classmethod
    def create_analysis_service(
        cls,
        test_data: Optional[Dict[str, Any]] = None,
        network_simulator: Optional[NetworkConditionSimulator] = None,
        **kwargs,
    ) -> "MockAnalysisService":
        """
        Create a mock analysis service instance.

        Args:
            test_data: Custom test data for analysis responses
            network_simulator: Network condition simulator
            **kwargs: Additional arguments

        Returns:
            Configured MockAnalysisService instance
        """
        return cls.create_service("analysis", test_data, network_simulator, **kwargs)

    @classmethod
    def create_test_suite(cls, scenario: str = "default") -> Dict[str, BaseMockService]:
        """
        Create a complete suite of mock services for a test scenario.

        Args:
            scenario: Test scenario name ('default', 'slow_network', 'unreliable', etc.)

        Returns:
            Dictionary of mock services configured for the scenario
        """
        if scenario == "slow_network":
            network_simulator = NetworkConditionSimulator(
                failure_rate=0.0, min_latency_ms=100, max_latency_ms=500
            )
        elif scenario == "unreliable":
            network_simulator = NetworkConditionSimulator(
                failure_rate=0.1, min_latency_ms=50, max_latency_ms=200
            )
        elif scenario == "failing":
            network_simulator = NetworkConditionSimulator(
                failure_rate=0.5, min_latency_ms=0, max_latency_ms=100
            )
        else:  # default
            network_simulator = NetworkConditionSimulator()

        return {
            "spotify": cls.create_spotify_service(network_simulator=network_simulator),
            "genius": cls.create_genius_service(network_simulator=network_simulator),
            "analysis": cls.create_analysis_service(network_simulator=network_simulator),
        }

    @classmethod
    def get_available_services(cls) -> list[str]:
        """Get a list of available service names."""
        return list(cls._service_registry.keys())


# Auto-register services when they're imported
def _auto_register_services():
    """Automatically register mock services when the module is imported."""
    try:
        from .spotify_service import MockSpotifyService

        MockServiceFactory.register_service("spotify", MockSpotifyService)
    except ImportError:
        pass

    try:
        from .genius_service import MockGeniusService

        MockServiceFactory.register_service("genius", MockGeniusService)
    except ImportError:
        pass

    try:
        from .analysis_mocks import MockAnalysisService

        MockServiceFactory.register_service("analysis", MockAnalysisService)
    except ImportError:
        pass


# Register services when module is imported
_auto_register_services()
