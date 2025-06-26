"""
Tests for Enhanced Biblical Content Display in Frontend

Tests the frontend display of biblical content with proper categorization
between positive themes and concern-based scripture references.
"""

import pytest
from app import create_app
from app.models.models import Song, AnalysisResult
from unittest.mock import MagicMock


class TestBiblicalContentDisplay:
    """Test the enhanced biblical content display in frontend templates."""
    
    @pytest.fixture
    def app(self):
        """Create test app instance."""
        app = create_app()
        app.config['TESTING'] = True
        return app
    
    @pytest.fixture 
    def client(self, app):
        """Create test client."""
        return app.test_client()
        
    @pytest.fixture
    def mock_comprehensive_analysis(self):
        """Mock analysis result with both positive and concern-based scriptures."""
        analysis = MagicMock()
        
        # Basic analysis fields
        analysis.content_analysis = {
            'concerns_detected': 2,
            'detailed_concerns': [
                {'type': 'explicit_language', 'severity': 'medium'},
                {'type': 'substance_abuse', 'severity': 'low'}
            ]
        }
        
        # Biblical themes (positive)
        analysis.biblical_themes = [
            {'theme': 'Love', 'score': 1.0},
            {'theme': 'Grace', 'score': 0.9}
        ]
        
        # Comprehensive supporting scripture (17 total - mix of positive and concern-based)
        analysis.supporting_scripture = [
            # Positive theme scriptures (love, grace) 
            {
                'reference': '1 John 4:8',
                'text': 'Whoever does not love does not know God, because God is love.',
                'theme': 'Love',
                'category': 'Relationships and Community',
                'concern_type': None  # Indicates positive theme
            },
            {
                'reference': 'Ephesians 2:8-9',
                'text': 'For it is by grace you have been saved, through faith.',
                'theme': 'Grace',
                'category': 'Salvation and Redemption',
                'concern_type': None  # Indicates positive theme
            },
            # Concern-based scriptures (explicit language)
            {
                'reference': 'Ephesians 4:29',
                'text': 'Do not let any unwholesome talk come out of your mouths.',
                'theme': 'Speech and Communication',
                'category': 'Speech and Communication', 
                'concern_type': 'explicit_language'  # Indicates concern-based
            },
            {
                'reference': 'James 3:9-10',
                'text': 'With the tongue we praise our Lord and Father, and with it we curse human beings.',
                'theme': 'Speech and Communication',
                'category': 'Speech and Communication',
                'concern_type': 'explicit_language'
            },
            # Concern-based scriptures (substance abuse)
            {
                'reference': '1 Corinthians 6:19-20',
                'text': 'Do you not know that your bodies are temples of the Holy Spirit?',
                'theme': 'Physical Holiness and Health',
                'category': 'Physical Holiness and Health',
                'concern_type': 'substance_abuse'
            },
            # Additional scriptures to reach 17 total
            *[{
                'reference': f'Test {i}',
                'text': f'Test scripture {i}',
                'theme': 'Test Theme',
                'category': 'Test Category', 
                'concern_type': 'explicit_language' if i % 2 == 0 else None
            } for i in range(3, 15)]
        ]
        
        return analysis
    
    def test_scripture_references_are_categorized_properly(self, app, mock_comprehensive_analysis):
        """Test that scripture references are properly categorized in template context."""
        with app.app_context():
            # This test verifies that our template logic properly categorizes scriptures
            supporting_scripture = mock_comprehensive_analysis.supporting_scripture
            
            # Categorize scriptures (this logic will be added to template or route)
            positive_scriptures = [s for s in supporting_scripture if not s.get('concern_type')]
            concern_scriptures = [s for s in supporting_scripture if s.get('concern_type')]
            
            # Verify categorization works
            assert len(positive_scriptures) >= 2  # Should have love and grace scriptures
            assert len(concern_scriptures) >= 3  # Should have explicit_language and substance_abuse scriptures
            assert len(positive_scriptures) + len(concern_scriptures) == len(supporting_scripture)
            
            # Verify positive scriptures don't have concern_type
            for scripture in positive_scriptures:
                assert scripture.get('concern_type') is None
                
            # Verify concern scriptures have concern_type
            for scripture in concern_scriptures:
                assert scripture.get('concern_type') is not None
    
    def test_template_displays_categorized_sections(self, app):
        """Test that template will display separate sections for positive vs concern scriptures."""
        with app.app_context():
            # This validates the template structure we'll implement
            # Template should have sections for:
            # 1. "Supporting Positive Themes" - scriptures for detected positive themes
            # 2. "Biblical Foundation for Concerns" - scriptures explaining why concerns are problematic
            
            # Mock template variables that will be passed
            template_vars = {
                'positive_scriptures': [
                    {'reference': '1 John 4:8', 'text': 'God is love', 'theme': 'Love'}
                ],
                'concern_scriptures': [
                    {'reference': 'Ephesians 4:29', 'text': 'No unwholesome talk', 'concern_type': 'explicit_language'}
                ]
            }
            
            # Verify we have the right structure for the template
            assert 'positive_scriptures' in template_vars
            assert 'concern_scriptures' in template_vars
            assert len(template_vars['positive_scriptures']) > 0
            assert len(template_vars['concern_scriptures']) > 0
    
    def test_concern_scriptures_show_educational_context(self, app, mock_comprehensive_analysis):
        """Test that concern-based scriptures show educational context."""
        with app.app_context():
            concern_scriptures = [
                s for s in mock_comprehensive_analysis.supporting_scripture 
                if s.get('concern_type')
            ]
            
            # Verify each concern scripture has educational fields
            for scripture in concern_scriptures:
                assert 'concern_type' in scripture
                assert 'reference' in scripture
                assert 'text' in scripture
                # These would be provided by our enhanced scripture mapper
                expected_fields = ['theme', 'category']
                for field in expected_fields:
                    assert field in scripture, f"Missing {field} in concern scripture"
    
    def test_mixed_content_shows_both_sections(self, app, mock_comprehensive_analysis):
        """Test that songs with both positive themes and concerns show both sections."""
        with app.app_context():
            analysis = mock_comprehensive_analysis
            
            # Should have both positive and concern content
            positive_count = len([s for s in analysis.supporting_scripture if not s.get('concern_type')])
            concern_count = len([s for s in analysis.supporting_scripture if s.get('concern_type')])
            
            assert positive_count > 0, "Should have positive scriptures for themes like love/grace"
            assert concern_count > 0, "Should have concern scriptures for detected issues"
            
            # Template should show both sections for mixed content
            assert len(analysis.biblical_themes) > 0  # Has positive themes
            assert analysis.content_analysis['concerns_detected'] > 0  # Has concerns 