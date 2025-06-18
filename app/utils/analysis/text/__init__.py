"""
Text Processing Domain

Handles all text preprocessing, cleaning, tokenization, and normalization operations.
"""

from .preprocessor import LyricsPreprocessor
from .tokenizer import TextTokenizer  
from .cleaner import TextCleaner

# Aliases for compatibility
TextCleaningEngine = TextCleaner

__all__ = [
    'LyricsPreprocessor',
    'TextTokenizer',
    'TextCleaner',
    'TextCleaningEngine'
] 