from app.config_llm import llm_config

class IntelligentLLMRouter:
    def get_optimal_provider(self):
        provider_name = llm_config.get("default", "ollama")
        return llm_config["providers"].get(provider_name)

def get_intelligent_router():
    return IntelligentLLMRouter()

