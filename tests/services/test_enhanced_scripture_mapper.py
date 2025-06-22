#!/usr/bin/env python3
"""
TDD Tests for Enhanced Scripture Mapping
Testing the enhanced scripture mapping functionality
"""
import pytest
import sys
import os

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app.services.enhanced_scripture_mapper import EnhancedScriptureMapper


class TestEnhancedScriptureMapper:
    """Test suite for enhanced scripture mapping functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.mapper = EnhancedScriptureMapper()
    
    def test_get_scripture_references_valid_themes(self):
        """Test getting scripture references for valid themes"""
        themes = ['God', 'love', 'grace']
        result = self.mapper.find_relevant_passages(themes)
        
        # Should return 3 passages (one per theme)
        assert len(result) == 3
        
        # Each passage should have required fields
        for passage in result:
            assert 'reference' in passage
            assert 'text' in passage
            assert 'relevance' in passage
            assert 'application' in passage
            assert 'educational_value' in passage
    
    def test_get_scripture_references_case_insensitive(self):
        """Test that theme matching is case insensitive"""
        themes_lower = ['god', 'jesus']
        themes_mixed = ['God', 'Jesus']
        themes_upper = ['GOD', 'JESUS']
        
        result_lower = self.mapper.find_relevant_passages(themes_lower)
        result_mixed = self.mapper.find_relevant_passages(themes_mixed)
        result_upper = self.mapper.find_relevant_passages(themes_upper)
        
        # All should return same number of results
        assert len(result_lower) == len(result_mixed) == len(result_upper) == 2
        
        # Results should be equivalent (same references)
        refs_lower = [p['reference'] for p in result_lower]
        refs_mixed = [p['reference'] for p in result_mixed]
        refs_upper = [p['reference'] for p in result_upper]
        
        assert set(refs_lower) == set(refs_mixed) == set(refs_upper)
    
    def test_get_scripture_references_unknown_themes(self):
        """Test handling of unknown/invalid themes"""
        themes = ['unknown_theme', 'invalid_theme', 'not_a_theme']
        result = self.mapper.find_relevant_passages(themes)
        
        # Should return empty list for unknown themes
        assert result == []
    
    def test_get_scripture_references_mixed_valid_invalid(self):
        """Test handling of mixed valid and invalid themes"""
        themes = ['God', 'unknown_theme', 'love', 'invalid_theme']
        result = self.mapper.find_relevant_passages(themes)
        
        # Should return only passages for valid themes (God, love)
        assert len(result) == 2
        
        # Check that returned passages are for valid themes
        refs = [p['reference'] for p in result]
        # Should contain references from God and love themes
        assert len(refs) == 2
    
    def test_get_scripture_references_empty_input(self):
        """Test handling of empty input"""
        result = self.mapper.find_relevant_passages([])
        assert result == []
        
        result_none = self.mapper.find_relevant_passages(None)
        assert result_none == []
    
    def test_all_core_themes_supported(self):
        """Test that all 10 core biblical themes are supported"""
        core_themes = [
            'God', 'Jesus', 'grace', 'love', 'worship', 
            'faith', 'hope', 'peace', 'joy', 'forgiveness'
        ]
        
        for theme in core_themes:
            result = self.mapper.find_relevant_passages([theme])
            assert len(result) >= 1, f"Theme '{theme}' should return at least one scripture passage"
            
            # Verify the passage has all required fields
            passage = result[0]
            assert passage['reference'], f"Theme '{theme}' missing reference"
            assert passage['text'], f"Theme '{theme}' missing text"
            assert passage['relevance'], f"Theme '{theme}' missing explanation"
    
    def test_scripture_passage_quality(self):
        """Test the quality and completeness of scripture passages"""
        themes = ['God', 'Jesus', 'grace']
        result = self.mapper.find_relevant_passages(themes)
        
        for passage in result:
            # Reference should be properly formatted (e.g., "John 3:16")
            assert len(passage['reference']) > 5
            assert ':' in passage['reference']
            
            # Text should be substantial (not just a few words)
            assert len(passage['text']) > 20
            
            # Explanations should be educational
            assert len(passage['relevance']) > 30
            assert len(passage['application']) > 20
            assert len(passage['educational_value']) > 20
    
    def test_no_duplicate_passages(self):
        """Test that duplicate themes don't return duplicate passages"""
        themes = ['God', 'God', 'love', 'love']
        result = self.mapper.find_relevant_passages(themes)
        
        # Should not return duplicates (God and love each appear once)
        refs = [p['reference'] for p in result]
        assert len(refs) == len(set(refs)), "Should not return duplicate scripture references"
    
    def test_scripture_text_content(self):
        """Test that scripture text contains actual verse content"""
        themes = ['God']
        result = self.mapper.find_relevant_passages(themes)
        
        passage = result[0]
        text = passage['text']
        
        # Should contain actual verse content, not just reference
        assert len(text) > 50  # Substantial text
        assert not text.startswith(passage['reference'])  # Not just the reference
        
        # Should contain meaningful words related to the theme
        text_lower = text.lower()
        god_related_words = ['god', 'lord', 'father', 'creator', 'almighty']
        assert any(word in text_lower for word in god_related_words)


if __name__ == '__main__':
    pytest.main([__file__, '-v']) 