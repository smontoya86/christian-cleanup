"""
Intelligent LLM Router Service

This service automatically detects the best available LLM provider and routes
requests accordingly. It supports RunPod, Ollama (local), and OpenAI with
automatic failover and provider-specific optimizations.
"""

import logging
import os
import time
from typing import Dict, List, Optional, Tuple
import requests
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class LLMProvider:
    """Configuration for an LLM provider"""
    name: str
    endpoint: str
    model: str
    priority: int  # Lower number = higher priority
    timeout: float = 5.0
    max_retries: int = 2
    api_key_env: Optional[str] = None  # Environment variable name for API key
    
    def __post_init__(self):
        """Ensure endpoint has proper format"""
        if self.endpoint and not self.endpoint.endswith('/v1'):
            if not self.endpoint.endswith('/'):
                self.endpoint += '/'
            self.endpoint += 'v1'


class IntelligentLLMRouter:
    """
    Intelligent router that automatically selects the best available LLM provider.
    
    Priority order:
    1. RunPod (high-performance cloud)
    2. Ollama (local development)
    3. OpenAI (reliable fallback)
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.providers = self._initialize_providers()
        self.current_provider = None
        self.last_health_check = 0
        self.health_check_interval = 300  # 5 minutes
        
    def _initialize_providers(self) -> List[LLMProvider]:
        """Initialize LLM providers from configuration"""
        from ..config_llm import LLM_PROVIDERS, OLLAMA_FALLBACK_ENDPOINTS
        
        providers = []
        
        for config in LLM_PROVIDERS:
            if config["name"] == "runpod" and config["endpoint"]:
                # RunPod provider configured
                providers.append(LLMProvider(**config))
                self.logger.info(f"🚀 RunPod provider configured: {config['endpoint']} ({config['model']})")
            elif config["name"] == "runpod":
                # RunPod stubbed
                self.logger.info("📝 RunPod provider stubbed - set RUNPOD_ENDPOINT to activate")
            elif config["name"] == "ollama":
                # Try Ollama endpoints in order
                endpoint_found = False
                for endpoint in [config["endpoint"]] + OLLAMA_FALLBACK_ENDPOINTS:
                    if endpoint and not endpoint_found:
                        provider_config = config.copy()
                        provider_config["endpoint"] = endpoint
                        providers.append(LLMProvider(**provider_config))
                        self.logger.info(f"🏠 Ollama provider configured: {endpoint} ({config['model']})")
                        endpoint_found = True
                        break
        
        if not providers:
            self.logger.warning("⚠️ No LLM providers configured! Set RUNPOD_ENDPOINT or ensure Ollama is running")
        
        # Sort by priority
        providers.sort(key=lambda p: p.priority)
        
        self.logger.info(f"📋 Initialized {len(providers)} Llama-based LLM providers")
        return providers
    
    def get_optimal_provider(self) -> Optional[LLMProvider]:
        """
        Get the best available LLM provider with automatic health checking.
        
        Returns:
            LLMProvider: The best available provider, or None if none are available
        """
        current_time = time.time()
        
        # Check if we need to refresh health status
        if (current_time - self.last_health_check) > self.health_check_interval:
            self.current_provider = None  # Force re-check
            self.last_health_check = current_time
        
        # If we have a current provider and it's still healthy, use it
        if self.current_provider and self._is_provider_healthy(self.current_provider):
            return self.current_provider
        
        # Find the best available provider
        for provider in self.providers:
            if self._is_provider_healthy(provider):
                self.current_provider = provider
                self.logger.info(f"✅ Selected LLM provider: {provider.name} ({provider.endpoint})")
                return provider
        
        self.logger.error("❌ No healthy LLM providers available")
        return None
    
    def _is_provider_healthy(self, provider: LLMProvider) -> bool:
        """
        Check if a provider is healthy and available.
        
        Args:
            provider: The LLM provider to check
            
        Returns:
            bool: True if provider is healthy, False otherwise
        """
        try:
            # Get API key if required
            headers = {}
            if provider.name == "runpod":
                api_key = os.environ.get('RUNPOD_API_KEY')
                if not api_key:
                    self.logger.debug("❌ RunPod API key not configured")
                    return False
                headers["Authorization"] = f"Bearer {api_key}"
            
            # Check if endpoint is reachable
            response = requests.get(
                f"{provider.endpoint}/models",
                timeout=provider.timeout,
                headers=headers
            )
            
            if response.status_code == 200:
                self.logger.debug(f"✅ {provider.name} health check passed: {provider.endpoint}")
                return True
            else:
                self.logger.debug(f"❌ {provider.name} health check failed: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.logger.debug(f"❌ {provider.name} unreachable: {e}")
            return False
    

    
    def get_provider_info(self) -> Dict:
        """
        Get information about the current provider and all available providers.
        
        Returns:
            dict: Provider information and status
        """
        current = self.get_optimal_provider()
        
        provider_status = []
        for provider in self.providers:
            is_healthy = self._is_provider_healthy(provider)
            provider_status.append({
                "name": provider.name,
                "endpoint": provider.endpoint,
                "model": provider.model,
                "priority": provider.priority,
                "healthy": is_healthy,
                "current": current and current.name == provider.name
            })
        
        return {
            "current_provider": current.name if current else None,
            "current_endpoint": current.endpoint if current else None,
            "current_model": current.model if current else None,
            "providers": provider_status,
            "total_providers": len(self.providers),
            "healthy_providers": sum(1 for p in provider_status if p["healthy"])
        }
    
    def force_provider(self, provider_name: str) -> bool:
        """
        Force the router to use a specific provider (for testing/debugging).
        
        Args:
            provider_name: Name of the provider to force
            
        Returns:
            bool: True if provider was found and set, False otherwise
        """
        for provider in self.providers:
            if provider.name == provider_name:
                if self._is_provider_healthy(provider):
                    self.current_provider = provider
                    self.logger.info(f"🔧 Forced provider: {provider_name}")
                    return True
                else:
                    self.logger.warning(f"⚠️ Cannot force unhealthy provider: {provider_name}")
                    return False
        
        self.logger.error(f"❌ Provider not found: {provider_name}")
        return False
    
    def reset_provider_cache(self):
        """Reset the current provider cache to force re-detection"""
        self.current_provider = None
        self.last_health_check = 0
        self.logger.info("🔄 Provider cache reset")


# Global router instance
_router_instance = None

def get_intelligent_router() -> IntelligentLLMRouter:
    """Get the global intelligent router instance (singleton)"""
    global _router_instance
    if _router_instance is None:
        _router_instance = IntelligentLLMRouter()
    return _router_instance
