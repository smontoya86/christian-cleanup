"""
Lyrics Preprocessor

Handles text preprocessing operations including cleaning, normalization,
and preparation of lyrics text for analysis.

Extracted and refactored from original analysis.py _preprocess_lyrics method.
"""

import re
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class LyricsPreprocessor:
    """
    Handles lyrics text preprocessing with configurable cleaning options.
    
    This class consolidates all text preprocessing logic that was previously
    scattered across multiple analyzer classes.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the preprocessor with optional configuration.
        
        Args:
            config: Optional configuration dictionary with preprocessing options
        """
        self.config = config or {}
        
        # Configuration options with defaults
        self.remove_timestamps = self.config.get('remove_timestamps', True)
        self.remove_section_headers = self.config.get('remove_section_headers', True)
        self.convert_to_lowercase = self.config.get('convert_to_lowercase', True)
        self.normalize_whitespace = self.config.get('normalize_whitespace', True)
        self.preserve_contractions = self.config.get('preserve_contractions', True)
        self.preserve_hyphens = self.config.get('preserve_hyphens', True)
        
        logger.debug(f"LyricsPreprocessor initialized with config: {self.config}")
    
    def preprocess(self, lyrics: str) -> str:
        """
        Main preprocessing method that applies all configured cleaning operations.
        
        Args:
            lyrics: Raw lyrics text to preprocess
            
        Returns:
            Cleaned and normalized lyrics text
        """
        if not lyrics:
            logger.debug("Received empty lyrics text")
            return ""
        
        try:
            processed_text = lyrics
            
            # Apply preprocessing steps in order
            if self.remove_section_headers:
                processed_text = self._remove_section_headers(processed_text)
            
            if self.remove_timestamps:
                processed_text = self._remove_timestamps(processed_text)
            
            if self.convert_to_lowercase:
                processed_text = processed_text.lower()
            
            # Remove unwanted punctuation while preserving contractions and hyphens
            processed_text = self._clean_punctuation(processed_text)
            
            if self.normalize_whitespace:
                processed_text = self._normalize_whitespace(processed_text)
            
            logger.debug(f"Preprocessed lyrics: {len(lyrics)} -> {len(processed_text)} chars")
            return processed_text
            
        except Exception as e:
            logger.error(f"Error preprocessing lyrics: {e}", exc_info=True)
            # Return original text if preprocessing fails
            return lyrics
    
    def _remove_section_headers(self, text: str) -> str:
        """
        Remove section headers like [Verse 1], [Chorus], [Bridge], etc.
        
        Args:
            text: Text to clean
            
        Returns:
            Text with section headers removed
        """
        # Remove content within square brackets (section headers)
        text = re.sub(r'\[[^\]]+\]', '', text)
        return text
    
    def _remove_timestamps(self, text: str) -> str:
        """
        Remove timestamps in various formats.
        
        Handles formats like:
        - [00:12.345] or [00:01:12.345] 
        - [MM:SS] or [HH:MM:SS]
        - [MM:SS.mmm] or [HH:MM:SS.mmm]
        
        Args:
            text: Text to clean
            
        Returns:
            Text with timestamps removed
        """
        # Remove timestamps: [MM:SS.mmm] and [MM:SS]
        text = re.sub(r'\[\d{2}:\d{2}(?:\.\d{1,3})?\]', '', text)
        
        # Remove timestamps with hours: [HH:MM:SS.mmm] and [HH:MM:SS]
        text = re.sub(r'\[\d{2}:\d{2}:\d{2}(?:\.\d{1,3})?\]', '', text)
        
        return text
    
    def _clean_punctuation(self, text: str) -> str:
        """
        Remove unwanted punctuation while preserving contractions and hyphens.
        
        This method keeps:
        - Letters and numbers
        - Spaces
        - Apostrophes (for contractions like "don't", "I'll")
        - Hyphens (for compound words like "twenty-one")
        
        Args:
            text: Text to clean
            
        Returns:
            Text with unwanted punctuation removed
        """
        if self.preserve_contractions and self.preserve_hyphens:
            # Keep letters, numbers, spaces, apostrophes, and hyphens
            text = re.sub(r"[^a-z0-9\s'-]", '', text)
        elif self.preserve_contractions:
            # Keep letters, numbers, spaces, and apostrophes only
            text = re.sub(r"[^a-z0-9\s']", '', text)
        elif self.preserve_hyphens:
            # Keep letters, numbers, spaces, and hyphens only
            text = re.sub(r"[^a-z0-9\s-]", '', text)
        else:
            # Keep only letters, numbers, and spaces
            text = re.sub(r"[^a-z0-9\s]", '', text)
        
        return text
    
    def _normalize_whitespace(self, text: str) -> str:
        """
        Normalize whitespace by replacing multiple spaces/newlines with single spaces.
        
        Args:
            text: Text to normalize
            
        Returns:
            Text with normalized whitespace
        """
        # Replace multiple whitespace characters with single spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Strip leading and trailing whitespace
        text = text.strip()
        
        return text
    
    def get_word_count(self, text: str) -> int:
        """
        Get the word count of processed text.
        
        Args:
            text: Text to count words in
            
        Returns:
            Number of words in the text
        """
        if not text:
            return 0
        
        words = text.split()
        return len(words)
    
    def get_processing_stats(self, original: str, processed: str) -> Dict[str, Any]:
        """
        Get statistics about the preprocessing operation.
        
        Args:
            original: Original text before processing
            processed: Text after processing
            
        Returns:
            Dictionary with processing statistics
        """
        return {
            'original_length': len(original),
            'processed_length': len(processed),
            'original_word_count': self.get_word_count(original),
            'processed_word_count': self.get_word_count(processed),
            'reduction_ratio': 1 - (len(processed) / max(len(original), 1)),
            'config_used': self.config
        } 