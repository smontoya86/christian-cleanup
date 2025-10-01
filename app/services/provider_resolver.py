"""
Analyzer provider resolver - OpenAI-only

Returns the RouterAnalyzer which uses the fine-tuned GPT-4o-mini model
via OpenAI API for theological music analysis.
"""

from app.services.analyzers import RouterAnalyzer


def get_analyzer() -> RouterAnalyzer:
    """
    Get the OpenAI-powered RouterAnalyzer instance.
    
    Returns:
        RouterAnalyzer: The fine-tuned GPT-4o-mini analyzer
    """
    return RouterAnalyzer()


