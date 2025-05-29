"""
Scripture Reference Mapper

Handles mapping of biblical themes to scripture references and 
manages denominational preferences for scripture selection.
"""

import logging
from typing import Dict, List, Any, Optional

from .themes_config import BiblicalThemesConfig

logger = logging.getLogger(__name__)


class ScriptureReferenceMapper:
    """
    Maps biblical themes to appropriate scripture references.
    
    Handles denominational preferences and provides relevant
    scripture support for detected themes.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the scripture reference mapper.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.themes_config = BiblicalThemesConfig()
        
        # Configuration options
        self.denomination = self.config.get('denomination', 'general')
        self.max_refs_per_theme = self.config.get('max_refs_per_theme', 3)
        self.include_book_info = self.config.get('include_book_info', False)
        
        # Load denominational preferences
        self._load_denominational_preferences()
        
        logger.debug(f"ScriptureReferenceMapper initialized for {self.denomination} denomination")
    
    def get_scripture_references(self, theme_name: str) -> List[str]:
        """
        Get scripture references for a specific theme.
        
        Args:
            theme_name: Name of the biblical theme
            
        Returns:
            List of scripture references
        """
        all_references = self.themes_config.get_scripture_references()
        theme_refs = all_references.get(theme_name, [])
        
        # Apply denominational filtering if configured
        if self.denomination != 'general':
            theme_refs = self._filter_by_denomination(theme_refs, theme_name)
        
        # Limit number of references
        if len(theme_refs) > self.max_refs_per_theme:
            theme_refs = theme_refs[:self.max_refs_per_theme]
        
        return theme_refs
    
    def get_all_references_for_themes(self, theme_names: List[str]) -> Dict[str, List[str]]:
        """
        Get scripture references for multiple themes.
        
        Args:
            theme_names: List of theme names
            
        Returns:
            Dictionary mapping themes to scripture references
        """
        references = {}
        
        for theme_name in theme_names:
            refs = self.get_scripture_references(theme_name)
            if refs:
                references[theme_name] = refs
        
        return references
    
    def format_scripture_reference(self, reference: str) -> str:
        """
        Format a scripture reference for display.
        
        Args:
            reference: Raw scripture reference
            
        Returns:
            Formatted reference string
        """
        if not reference:
            return ""
        
        if self.include_book_info:
            return self._add_book_info(reference)
        
        return reference
    
    def get_reference_summary(self, theme_references: Dict[str, List[str]]) -> Dict[str, Any]:
        """
        Generate a summary of scripture references.
        
        Args:
            theme_references: Dictionary of theme references
            
        Returns:
            Summary dictionary
        """
        total_refs = sum(len(refs) for refs in theme_references.values())
        
        # Count books referenced
        book_count = self._count_referenced_books(theme_references)
        
        return {
            'total_themes_with_refs': len(theme_references),
            'total_references': total_refs,
            'books_referenced': len(book_count),
            'most_referenced_book': max(book_count.items(), key=lambda x: x[1])[0] if book_count else None,
            'denomination': self.denomination
        }
    
    def _load_denominational_preferences(self) -> None:
        """Load preferences for different Christian denominations."""
        self.denominational_preferences = {
            'catholic': {
                'preferred_books': ['Matthew', 'Luke', 'John', 'Romans', 'James'],
                'emphasis_themes': ['love_grace', 'service_discipleship'],
                'additional_refs': {
                    'love_grace': ['1 Corinthians 13:13 - And now these three remain: faith, hope and love']
                }
            },
            
            'protestant': {
                'preferred_books': ['Romans', 'Ephesians', 'John', 'Psalms'],
                'emphasis_themes': ['salvation_redemption', 'faith_trust'],
                'additional_refs': {
                    'salvation_redemption': ['Romans 3:23 - For all have sinned and fall short of the glory of God']
                }
            },
            
            'evangelical': {
                'preferred_books': ['John', 'Romans', 'Ephesians', 'Matthew'],
                'emphasis_themes': ['salvation_redemption', 'biblical_references'],
                'additional_refs': {
                    'biblical_references': ['John 1:1 - In the beginning was the Word, and the Word was with God']
                }
            },
            
            'pentecostal': {
                'preferred_books': ['Acts', 'Corinthians', 'Ephesians'],
                'emphasis_themes': ['prayer_communion', 'worship_praise'],
                'additional_refs': {
                    'prayer_communion': ['Acts 2:42 - They devoted themselves to the apostles\' teaching and to fellowship']
                }
            }
        }
    
    def _filter_by_denomination(self, references: List[str], theme_name: str) -> List[str]:
        """
        Filter references based on denominational preferences.
        
        Args:
            references: List of scripture references
            theme_name: Theme name for context
            
        Returns:
            Filtered list of references
        """
        if self.denomination not in self.denominational_preferences:
            return references
        
        prefs = self.denominational_preferences[self.denomination]
        preferred_books = prefs.get('preferred_books', [])
        
        # Prioritize references from preferred books
        prioritized_refs = []
        other_refs = []
        
        for ref in references:
            book_name = self._extract_book_name(ref)
            if book_name in preferred_books:
                prioritized_refs.append(ref)
            else:
                other_refs.append(ref)
        
        # Add denominational-specific references if available
        additional_refs = prefs.get('additional_refs', {}).get(theme_name, [])
        
        # Combine prioritized + additional + others
        result = prioritized_refs + additional_refs + other_refs
        
        return result
    
    def _extract_book_name(self, reference: str) -> str:
        """
        Extract the book name from a scripture reference.
        
        Args:
            reference: Scripture reference string
            
        Returns:
            Book name
        """
        # Extract book name before the first number
        parts = reference.split()
        if parts:
            # Handle books like "1 Corinthians" or "2 Timothy"
            if parts[0].isdigit() and len(parts) > 1:
                return f"{parts[0]} {parts[1]}"
            else:
                return parts[0]
        
        return ""
    
    def _add_book_info(self, reference: str) -> str:
        """
        Add additional book information to a reference.
        
        Args:
            reference: Original reference
            
        Returns:
            Enhanced reference with book info
        """
        book_info = {
            'Genesis': '(First book of the Bible, Creation)',
            'Psalms': '(Book of worship and praise)',
            'Matthew': '(Gospel of Jesus Christ)',
            'John': '(Gospel emphasizing love)',
            'Romans': '(Paul\'s letter on salvation)',
            'Ephesians': '(Paul\'s letter on the church)',
            'Revelation': '(Prophetic book, end times)'
        }
        
        book_name = self._extract_book_name(reference)
        info = book_info.get(book_name, '')
        
        if info:
            return f"{reference} {info}"
        
        return reference
    
    def _count_referenced_books(self, theme_references: Dict[str, List[str]]) -> Dict[str, int]:
        """
        Count how many times each book is referenced.
        
        Args:
            theme_references: Dictionary of theme references
            
        Returns:
            Dictionary mapping book names to reference counts
        """
        book_counts = {}
        
        for refs in theme_references.values():
            for ref in refs:
                book_name = self._extract_book_name(ref)
                if book_name:
                    book_counts[book_name] = book_counts.get(book_name, 0) + 1
        
        return book_counts 