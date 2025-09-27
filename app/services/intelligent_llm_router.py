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
        """Initialize Llama-based LLM providers (RunPod + Ollama)"""
        providers = []
        
        # 1. RunPod Provider (highest priority) - Llama 3.1:70b
        runpod_endpoint = os.environ.get("RUNPOD_ENDPOINT")
        if runpod_endpoint:
            providers.append(LLMProvider(
                name="runpod",
                endpoint=runpod_endpoint,
                model=os.environ.get("RUNPOD_MODEL", "llama3.1:70b"),
                priority=1,
                timeout=15.0,  # Longer timeout for cloud inference
                max_retries=3
            ))
            self.logger.info(f"🚀 RunPod provider configured: {runpod_endpoint} (Llama 3.1:70b)")
        else:
            # Stub RunPod provider for future use
            self.logger.info("📝 RunPod provider stubbed - set RUNPOD_ENDPOINT to activate")
        
        # 2. Ollama Provider (local fallback) - Llama 3.1:8b
        ollama_endpoints = [
            os.environ.get("OLLAMA_ENDPOINT"),
            "http://ollama:11434",
            "http://localhost:11434", 
            "http://host.docker.internal:11434",
            "http://llm:8000"  # Current working endpoint
        ]
        
        for endpoint in ollama_endpoints:
            if endpoint:
                providers.append(LLMProvider(
                    name="ollama",
                    endpoint=endpoint,
                    model=os.environ.get("OLLAMA_MODEL", "llama3.1:8b"),
                    priority=2,
                    timeout=8.0,  # Reasonable timeout for local/docker
                    max_retries=2
                ))
                self.logger.info(f"🏠 Ollama provider configured: {endpoint} (Llama 3.1:8b)")
                break  # Only add one Ollama provider
        
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
            if provider.name == "runpod":
                return self._check_runpod_health(provider)
            elif provider.name == "ollama":
                return self._check_ollama_health(provider)
            else:
                return self._check_generic_health(provider)
                
        except Exception as e:
            self.logger.debug(f"Health check failed for {provider.name}: {e}")
            return False
    
    def _check_runpod_health(self, provider: LLMProvider) -> bool:
        """Check RunPod endpoint health"""
        try:
            # Get API key - if not set, RunPod is not configured yet
            api_key = os.environ.get('RUNPOD_API_KEY')
            if not api_key:
                self.logger.debug("❌ RunPod API key not configured")
                return False
            
            # Check if RunPod endpoint is reachable
            response = requests.get(
                f"{provider.endpoint}/models",
                timeout=provider.timeout,
                headers={"Authorization": f"Bearer {api_key}"}
            )
            
            if response.status_code == 200:
                self.logger.debug(f"✅ RunPod health check passed: {provider.endpoint}")
                return True
            else:
                self.logger.debug(f"❌ RunPod health check failed: HTTP {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.logger.debug(f"❌ RunPod unreachable: {e}")
            return False
    
    def _check_ollama_health(self, provider: LLMProvider) -> bool:
        """Check Ollama endpoint health"""
        try:
            # Check if Ollama is running and has the model
            response = requests.get(
                f"{provider.endpoint}/models",
                timeout=provider.timeout
            )
            
            if response.status_code == 200:
                models_data = response.json()
                # Check if our model is available
                available_models = [model.get('name', '') for model in models_data.get('data', [])]
                if provider.model in available_models:
                    self.logger.debug(f"✅ Ollama health check passed: {provider.model} available")
                    return True
                else:
                    self.logger.debug(f"❌ Ollama model {provider.model} not available")
                    return False
            else:
                self.logger.debug(f"❌ Ollama health check failed: HTTP {response.status_code}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.logger.debug(f"❌ Ollama unreachable: {e}")
            return False
    
    def _check_generic_health(self, provider: LLMProvider) -> bool:
        """Generic health check for unknown providers"""
        try:
            response = requests.get(
                f"{provider.endpoint}/models",
                timeout=provider.timeout
            )
            return response.status_code == 200
        except:
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
