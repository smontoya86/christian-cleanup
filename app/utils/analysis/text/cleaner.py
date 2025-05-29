"""
Text Cleaner

Provides advanced text cleaning operations beyond basic preprocessing.
Handles encoding issues, special characters, and text normalization.
"""

import re
import unicodedata
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class TextCleaner:
    """
    Handles advanced text cleaning operations for improved analysis accuracy.
    
    This class provides utilities for cleaning text issues that can interfere
    with pattern detection and analysis.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the text cleaner with optional configuration.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        
        # Configuration options
        self.normalize_unicode = self.config.get('normalize_unicode', True)
        self.remove_repeated_chars = self.config.get('remove_repeated_chars', True)
        self.max_repeated_chars = self.config.get('max_repeated_chars', 3)
        self.fix_common_typos = self.config.get('fix_common_typos', True)
        
        # Common typo mappings
        self.typo_mappings = self.config.get('typo_mappings', {
            'ur': 'your',
            'u': 'you',
            '2': 'to',
            '4': 'for',
            'b4': 'before',
            'luv': 'love',
            'cuz': 'because',
            'wat': 'what',
            'da': 'the',
            'dis': 'this',
            'dat': 'that'
        })
        
        logger.debug(f"TextCleaner initialized with {len(self.typo_mappings)} typo mappings")
    
    def clean_advanced(self, text: str) -> str:
        """
        Apply all advanced cleaning operations.
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        try:
            cleaned_text = text
            
            if self.normalize_unicode:
                cleaned_text = self._normalize_unicode(cleaned_text)
            
            if self.remove_repeated_chars:
                cleaned_text = self._remove_repeated_characters(cleaned_text)
            
            if self.fix_common_typos:
                cleaned_text = self._fix_common_typos(cleaned_text)
            
            # Remove any remaining problematic characters
            cleaned_text = self._remove_problematic_chars(cleaned_text)
            
            logger.debug(f"Advanced cleaning: {len(text)} -> {len(cleaned_text)} chars")
            return cleaned_text
            
        except Exception as e:
            logger.error(f"Error in advanced text cleaning: {e}", exc_info=True)
            return text
    
    def _normalize_unicode(self, text: str) -> str:
        """
        Normalize unicode characters to standard forms.
        
        Args:
            text: Text to normalize
            
        Returns:
            Normalized text
        """
        # Normalize to NFD (decomposed) form and then to NFC (composed) form
        text = unicodedata.normalize('NFD', text)
        text = unicodedata.normalize('NFC', text)
        
        # Convert to ASCII if possible, removing accents
        try:
            text = text.encode('ascii', 'ignore').decode('ascii')
        except UnicodeError:
            # If ASCII conversion fails, keep the original
            pass
        
        return text
    
    def _remove_repeated_characters(self, text: str) -> str:
        """
        Remove excessive repeated characters (e.g., "hellooooo" -> "hello").
        
        Args:
            text: Text to process
            
        Returns:
            Text with repeated characters reduced
        """
        # Pattern to match 3 or more consecutive identical characters
        pattern = r'(.)\1{' + str(self.max_repeated_chars - 1) + ',}'
        
        def replace_repeated(match):
            char = match.group(1)
            # Keep maximum allowed repetitions
            return char * self.max_repeated_chars
        
        cleaned_text = re.sub(pattern, replace_repeated, text)
        return cleaned_text
    
    def _fix_common_typos(self, text: str) -> str:
        """
        Fix common typos and text speak abbreviations.
        
        Args:
            text: Text to fix
            
        Returns:
            Text with typos corrected
        """
        words = text.split()
        corrected_words = []
        
        for word in words:
            # Check for exact matches in typo mappings
            word_lower = word.lower()
            if word_lower in self.typo_mappings:
                corrected_words.append(self.typo_mappings[word_lower])
            else:
                corrected_words.append(word)
        
        return ' '.join(corrected_words)
    
    def _remove_problematic_chars(self, text: str) -> str:
        """
        Remove characters that can cause issues in pattern matching.
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text
        """
        # Remove zero-width characters and other invisible unicode
        text = re.sub(r'[\u200b-\u200d\u2060\ufeff]', '', text)
        
        # Remove excessive punctuation (more than 3 consecutive)
        text = re.sub(r'[.!?]{4,}', '...', text)
        
        # Remove unusual quotation marks and replace with standard ones
        text = re.sub(r'[""''`´]', '"', text)
        
        return text
    
    def remove_urls(self, text: str) -> str:
        """
        Remove URLs from text.
        
        Args:
            text: Text to process
            
        Returns:
            Text with URLs removed
        """
        # Pattern to match HTTP(S) URLs
        url_pattern = r'https?://[^\s]+'
        text = re.sub(url_pattern, '', text)
        
        # Pattern to match www URLs
        www_pattern = r'www\.[^\s]+'
        text = re.sub(www_pattern, '', text)
        
        return text
    
    def remove_mentions_hashtags(self, text: str) -> str:
        """
        Remove social media mentions and hashtags.
        
        Args:
            text: Text to process
            
        Returns:
            Text with mentions and hashtags removed
        """
        # Remove @ mentions
        text = re.sub(r'@\w+', '', text)
        
        # Remove # hashtags
        text = re.sub(r'#\w+', '', text)
        
        return text
    
    def normalize_contractions(self, text: str) -> str:
        """
        Expand common contractions to full forms.
        
        Args:
            text: Text to process
            
        Returns:
            Text with contractions expanded
        """
        contractions = {
            "can't": "cannot",
            "won't": "will not",
            "n't": " not",
            "'re": " are",
            "'ve": " have",
            "'ll": " will",
            "'d": " would",
            "'m": " am"
        }
        
        for contraction, expansion in contractions.items():
            text = re.sub(re.escape(contraction), expansion, text, flags=re.IGNORECASE)
        
        return text
    
    def get_cleaning_stats(self, original: str, cleaned: str) -> Dict[str, Any]:
        """
        Get statistics about the cleaning operation.
        
        Args:
            original: Original text
            cleaned: Cleaned text
            
        Returns:
            Dictionary with cleaning statistics
        """
        return {
            'original_length': len(original),
            'cleaned_length': len(cleaned),
            'characters_removed': len(original) - len(cleaned),
            'reduction_ratio': 1 - (len(cleaned) / max(len(original), 1)),
            'unicode_normalized': self.normalize_unicode,
            'typos_fixed': self.fix_common_typos,
            'repeated_chars_removed': self.remove_repeated_chars
        } 