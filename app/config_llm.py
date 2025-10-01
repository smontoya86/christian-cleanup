"""
LLM Configuration - OpenAI Only

Note: This config is legacy. The RouterAnalyzer now reads directly from environment variables:
- OPENAI_API_KEY (required)
- OPENAI_MODEL (optional, defaults to fine-tuned GPT-4o-mini)
- LLM_API_BASE_URL (optional, defaults to https://api.openai.com/v1)
"""

llm_config = {
    "default": "openai",
    "providers": {
        "openai": {
            "api_base": "https://api.openai.com/v1",
            "model": "ft:gpt-4o-mini-2024-07-18:personal:christian-discernment-4o-mini-v1:CLxyepav"
        }
    }
}
