"""
Text Tokenizer

Handles tokenization of processed text into words, phrases, and other linguistic units.
Provides utilities for word-level analysis and pattern detection.
"""

import re
import logging
from typing import List, Dict, Set, Optional, Any

logger = logging.getLogger(__name__)


class TextTokenizer:
    """
    Handles text tokenization and word-level analysis operations.
    
    This class provides various tokenization strategies and analysis utilities
    for processed lyrics text.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the tokenizer with optional configuration.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        
        # Load stop words if configured
        self.stop_words = set(self.config.get('stop_words', []))
        self.min_word_length = self.config.get('min_word_length', 1)
        self.max_word_length = self.config.get('max_word_length', 50)
        self.include_numbers = self.config.get('include_numbers', True)
        
        logger.debug(f"TextTokenizer initialized with {len(self.stop_words)} stop words")
    
    def tokenize(self, text: str) -> List[str]:
        """
        Basic word tokenization using whitespace splitting.
        
        Args:
            text: Text to tokenize
            
        Returns:
            List of word tokens
        """
        if not text:
            return []
        
        # Split on whitespace
        tokens = text.split()
        
        # Filter tokens based on configuration
        filtered_tokens = []
        for token in tokens:
            if self._is_valid_token(token):
                filtered_tokens.append(token)
        
        logger.debug(f"Tokenized {len(tokens)} raw tokens -> {len(filtered_tokens)} filtered tokens")
        return filtered_tokens
    
    def tokenize_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences using punctuation patterns.
        
        Args:
            text: Text to split into sentences
            
        Returns:
            List of sentences
        """
        if not text:
            return []
        
        # Split on sentence-ending punctuation
        sentences = re.split(r'[.!?]+', text)
        
        # Clean and filter sentences
        cleaned_sentences = []
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence and len(sentence) > 3:  # Skip very short fragments
                cleaned_sentences.append(sentence)
        
        return cleaned_sentences
    
    def tokenize_phrases(self, text: str, min_phrase_length: int = 2, max_phrase_length: int = 5) -> List[str]:
        """
        Extract phrases (n-grams) of specified lengths.
        
        Args:
            text: Text to extract phrases from
            min_phrase_length: Minimum number of words in a phrase
            max_phrase_length: Maximum number of words in a phrase
            
        Returns:
            List of phrases
        """
        words = self.tokenize(text)
        phrases = []
        
        for length in range(min_phrase_length, max_phrase_length + 1):
            for i in range(len(words) - length + 1):
                phrase = ' '.join(words[i:i + length])
                phrases.append(phrase)
        
        return phrases
    
    def get_word_frequencies(self, text: str) -> Dict[str, int]:
        """
        Calculate word frequency distribution.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary mapping words to their frequencies
        """
        tokens = self.tokenize(text)
        frequencies = {}
        
        for token in tokens:
            frequencies[token] = frequencies.get(token, 0) + 1
        
        return frequencies
    
    def get_unique_words(self, text: str) -> Set[str]:
        """
        Get set of unique words in the text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Set of unique words
        """
        tokens = self.tokenize(text)
        return set(tokens)
    
    def find_repeated_words(self, text: str, min_frequency: int = 2) -> Dict[str, int]:
        """
        Find words that are repeated above a threshold.
        
        Args:
            text: Text to analyze
            min_frequency: Minimum frequency for a word to be considered repeated
            
        Returns:
            Dictionary of repeated words and their frequencies
        """
        frequencies = self.get_word_frequencies(text)
        repeated = {word: freq for word, freq in frequencies.items() if freq >= min_frequency}
        
        return repeated
    
    def extract_capitalized_words(self, original_text: str) -> List[str]:
        """
        Extract words that were originally capitalized (before preprocessing).
        
        This can help identify proper nouns, names, etc.
        
        Args:
            original_text: Original text before lowercase conversion
            
        Returns:
            List of originally capitalized words
        """
        if not original_text:
            return []
        
        # Find words that start with capital letters
        capitalized_pattern = r'\b[A-Z][a-z]+\b'
        capitalized_words = re.findall(capitalized_pattern, original_text)
        
        return capitalized_words
    
    def get_lexical_diversity(self, text: str) -> float:
        """
        Calculate lexical diversity (unique words / total words).
        
        Higher values indicate more diverse vocabulary.
        
        Args:
            text: Text to analyze
            
        Returns:
            Lexical diversity ratio (0.0 to 1.0)
        """
        tokens = self.tokenize(text)
        if not tokens:
            return 0.0
        
        unique_tokens = set(tokens)
        diversity = len(unique_tokens) / len(tokens)
        
        return diversity
    
    def _is_valid_token(self, token: str) -> bool:
        """
        Check if a token meets the validity criteria.
        
        Args:
            token: Token to validate
            
        Returns:
            True if token is valid, False otherwise
        """
        # Check length constraints
        if len(token) < self.min_word_length or len(token) > self.max_word_length:
            return False
        
        # Check if it's a stop word
        if token.lower() in self.stop_words:
            return False
        
        # Check if it contains only numbers (if numbers are excluded)
        if not self.include_numbers and token.isdigit():
            return False
        
        # Check if it's just punctuation or whitespace
        if not re.search(r'[a-zA-Z]', token):
            return False
        
        return True
    
    def get_tokenization_stats(self, text: str) -> Dict[str, Any]:
        """
        Get comprehensive tokenization statistics.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary with tokenization statistics
        """
        tokens = self.tokenize(text)
        unique_tokens = self.get_unique_words(text)
        frequencies = self.get_word_frequencies(text)
        
        stats = {
            'total_tokens': len(tokens),
            'unique_tokens': len(unique_tokens),
            'lexical_diversity': self.get_lexical_diversity(text),
            'avg_word_length': sum(len(token) for token in tokens) / max(len(tokens), 1),
            'most_frequent_words': sorted(frequencies.items(), key=lambda x: x[1], reverse=True)[:10],
            'stop_words_removed': len([t for t in text.split() if t.lower() in self.stop_words])
        }
        
        return stats 