"""
Phase 1 Regression Tests: Core Gospel Themes Implementation

These tests ensure that implementing Core Gospel Themes doesn't break
any existing functionality. Run these after Phase 1 implementation.

Critical areas to test:
- Existing analysis pipeline still works
- Database models remain compatible  
- API endpoints function correctly
- Scoring stays within expected ranges
- Performance doesn't degrade significantly
"""

import pytest
from unittest.mock import Mock, patch
from flask import url_for
from app import create_app, db
from app.models.models import Song, AnalysisResult, User, Playlist, PlaylistSong
from app.utils.analysis.huggingface_analyzer import HuggingFaceAnalyzer
from app.services.unified_analysis_service import UnifiedAnalysisService
from app.services.simplified_christian_analysis_service import SimplifiedChristianAnalysisService


class TestPhase1Regression:
    """Regression tests to ensure Phase 1 implementation doesn't break existing functionality."""
    
    @pytest.fixture(autouse=True)
    def setup_test_environment(self, app):
        """Set up test environment for regression testing."""
        with app.app_context():
            db.create_all()
            
            # Create test user with required fields
            from datetime import datetime, timedelta
            self.test_user = User(
                spotify_id='regression_test_user',
                email='regression@test.com',
                display_name='Regression Test User',
                access_token='test_access_token',
                refresh_token='test_refresh_token',
                token_expiry=datetime.utcnow() + timedelta(hours=1)
            )
            db.session.add(self.test_user)
            
            # Create test song with existing analysis
            self.test_song = Song(
                spotify_id='regression_test_song',
                title='Test Song for Regression',
                artist='Test Artist',
                album='Test Album',
                lyrics='Simple test lyrics for regression testing'
            )
            db.session.add(self.test_song)
            db.session.flush()
            
            # Create existing analysis result
            self.existing_analysis = AnalysisResult(
                song_id=self.test_song.id,
                status='completed',
                score=75.0,
                concern_level='low',
                explanation='Existing analysis result for regression testing'
            )
            db.session.add(self.existing_analysis)
            db.session.commit()
            
            yield
            
            db.session.remove()
            db.drop_all()

    def test_existing_analysis_still_works(self, app):
        """Test that existing analysis pipeline continues to function."""
        with app.app_context():
            # Test that we can still create HuggingFace analyzer
            with patch('app.utils.analysis.huggingface_analyzer.pipeline'):
                analyzer = HuggingFaceAnalyzer()
                assert analyzer is not None
                
                # Mock the existing models to ensure they still work
                analyzer._sentiment_analyzer = Mock()
                analyzer._safety_analyzer = Mock() 
                analyzer._emotion_analyzer = Mock()
                
                # Mock responses in existing format
                analyzer._sentiment_analyzer.return_value = [{'label': 'POSITIVE', 'score': 0.8}]
                analyzer._safety_analyzer.return_value = [{'label': 'SAFE', 'score': 0.9}]
                analyzer._emotion_analyzer.return_value = [{'label': 'joy', 'score': 0.7}]
                
                # Test that analyze_song still works
                result = analyzer.analyze_song(
                    "Test Song", 
                    "Test Artist", 
                    "Test lyrics"
                )
                
                assert result is not None, "Analysis should still return results"
                assert hasattr(result, 'scoring_results'), "Result should have scoring_results"
                assert hasattr(result, 'biblical_analysis'), "Result should have biblical_analysis"

    def test_scoring_backwards_compatibility(self, app):
        """Test that scores are still in the expected 0-100 range."""
        with app.app_context():
            with patch('app.utils.analysis.huggingface_analyzer.pipeline'):
                analyzer = HuggingFaceAnalyzer()
                
                # Mock analyzers
                analyzer._sentiment_analyzer = Mock()
                analyzer._safety_analyzer = Mock()
                analyzer._emotion_analyzer = Mock()
                
                # Test various score scenarios
                test_cases = [
                    # Positive case
                    {
                        'sentiment': [{'label': 'POSITIVE', 'score': 0.9}],
                        'safety': [{'label': 'SAFE', 'score': 0.95}],
                        'emotion': [{'label': 'joy', 'score': 0.8}]
                    },
                    # Negative case
                    {
                        'sentiment': [{'label': 'NEGATIVE', 'score': 0.8}],
                        'safety': [{'label': 'TOXIC', 'score': 0.7}],
                        'emotion': [{'label': 'anger', 'score': 0.6}]
                    },
                    # Neutral case
                    {
                        'sentiment': [{'label': 'NEUTRAL', 'score': 0.6}],
                        'safety': [{'label': 'SAFE', 'score': 0.8}],
                        'emotion': [{'label': 'neutral', 'score': 0.5}]
                    }
                ]
                
                for test_case in test_cases:
                    analyzer._sentiment_analyzer.return_value = test_case['sentiment']
                    analyzer._safety_analyzer.return_value = test_case['safety']
                    analyzer._emotion_analyzer.return_value = test_case['emotion']
                    
                    result = analyzer.analyze_song("Test", "Test", "Test lyrics")
                    
                    # Score should always be in valid range
                    score = result.scoring_results['final_score']
                    assert 0 <= score <= 100, f"Score {score} should be between 0-100"

    def test_database_models_unchanged(self, app):
        """Test that database models and relationships remain intact."""
        with app.app_context():
            # Test Song model
            song = Song.query.filter_by(spotify_id='regression_test_song').first()
            assert song is not None, "Should be able to query existing songs"
            assert song.title == 'Test Song for Regression'
            
            # Test AnalysisResult model
            analysis = AnalysisResult.query.filter_by(song_id=song.id).first()
            assert analysis is not None, "Should be able to query existing analysis results"
            assert analysis.score == 75.0
            assert analysis.status == 'completed'
            
            # Test relationships
            assert len(song.analysis_results.all()) >= 1, "Song should have analysis relationships"
            
            # Test that we can create new records (no schema breakage)
            new_song = Song(
                spotify_id='new_regression_song',
                title='New Test Song',
                artist='New Artist',
                lyrics='New test lyrics'
            )
            db.session.add(new_song)
            db.session.flush()
            
            new_analysis = AnalysisResult(
                song_id=new_song.id,
                status='pending',
                score=None
            )
            db.session.add(new_analysis)
            db.session.commit()
            
            assert new_analysis.id is not None, "Should be able to create new analysis results"

    def test_api_endpoints_functional(self, app):
        """Test that key API endpoints still respond correctly."""
        with app.test_client() as client:
            with app.app_context():
                # Test basic endpoints (those that don't require authentication)
                
                # Note: Testing authenticated endpoints would require setting up
                # full authentication, which is complex for regression tests.
                # Instead, we test that the endpoint routing still works.
                
                # Test that API blueprint is registered
                assert 'api' in app.blueprints, "API blueprint should still be registered"
                
                # Test that routes are still registered
                rules = [rule.rule for rule in app.url_map.iter_rules()]
                expected_routes = [
                    '/api/song/<int:song_id>/analysis',
                    '/api/songs/<int:song_id>/analyze',
                    '/api/playlists/<int:playlist_id>/analyze'
                ]
                
                for route in expected_routes:
                    # Convert parameterized routes to check if pattern exists
                    route_pattern = route.replace('<int:song_id>', '<song_id>').replace('<int:playlist_id>', '<playlist_id>')
                    matching_rules = [r for r in rules if route_pattern.replace('<song_id>', '').replace('<playlist_id>', '') in r]
                    assert len(matching_rules) > 0, f"Route pattern {route} should still be registered"

    def test_unified_analysis_service_compatibility(self, app):
        """Test that UnifiedAnalysisService still works with existing interface."""
        with app.app_context():
            service = UnifiedAnalysisService()
            assert service is not None, "UnifiedAnalysisService should still initialize"
            
            # Test that it has expected attributes
            assert hasattr(service, 'analysis_service'), "Should have analysis_service attribute"
            assert hasattr(service, 'analyze_song_complete'), "Should have analyze_song_complete method"
            
            # Test that the analysis service is the expected type
            assert isinstance(service.analysis_service, SimplifiedChristianAnalysisService), \
                "Should use SimplifiedChristianAnalysisService"

    def test_simplified_analysis_service_compatibility(self, app):
        """Test that SimplifiedChristianAnalysisService maintains existing interface."""
        with app.app_context():
            service = SimplifiedChristianAnalysisService()
            assert service is not None, "SimplifiedChristianAnalysisService should initialize"
            
            # Test expected methods exist
            assert hasattr(service, 'analyze_song'), "Should have analyze_song method"
            
            # Test that it still uses HuggingFace analyzer
            assert hasattr(service, 'ai_analyzer'), "Should have ai_analyzer attribute"

    def test_keyword_detection_still_works(self, app):
        """Test that existing keyword-based detection still functions."""
        with app.app_context():
            with patch('app.utils.analysis.huggingface_analyzer.pipeline'):
                analyzer = HuggingFaceAnalyzer()
                
                # Mock the analyzers
                analyzer._sentiment_analyzer = Mock()
                analyzer._safety_analyzer = Mock()
                analyzer._emotion_analyzer = Mock()
                
                analyzer._sentiment_analyzer.return_value = [{'label': 'POSITIVE', 'score': 0.8}]
                analyzer._safety_analyzer.return_value = [{'label': 'SAFE', 'score': 0.9}]
                analyzer._emotion_analyzer.return_value = [{'label': 'joy', 'score': 0.7}]
                
                # Test that existing keyword detection methods still work
                assert hasattr(analyzer, '_detect_christian_themes'), "Should have keyword detection method"
                assert hasattr(analyzer, '_detect_concerns'), "Should have concern detection method"
                
                # Test keyword detection with Christian content
                christian_text = "jesus christ god lord faith praise worship"
                themes = analyzer._detect_christian_themes(christian_text)
                assert len(themes) > 0, "Should detect Christian keywords"
                
                # Test concern detection with problematic content
                concerning_text = "damn hell shit fuck"
                concerns = analyzer._detect_concerns(concerning_text)
                assert len(concerns) > 0, "Should detect concerning keywords"

    def test_analysis_result_structure_preserved(self, app):
        """Test that AnalysisResult structure is preserved for existing code."""
        with app.app_context():
            with patch('app.utils.analysis.huggingface_analyzer.pipeline'):
                analyzer = HuggingFaceAnalyzer()
                
                # Mock analyzers
                analyzer._sentiment_analyzer = Mock()
                analyzer._safety_analyzer = Mock()
                analyzer._emotion_analyzer = Mock()
                
                analyzer._sentiment_analyzer.return_value = [{'label': 'POSITIVE', 'score': 0.8}]
                analyzer._safety_analyzer.return_value = [{'label': 'SAFE', 'score': 0.9}]
                analyzer._emotion_analyzer.return_value = [{'label': 'joy', 'score': 0.7}]
                
                result = analyzer.analyze_song("Test", "Test", "Test lyrics")
                
                # Verify all expected attributes exist
                expected_attributes = [
                    'title', 'artist', 'lyrics_text', 'processed_text',
                    'content_analysis', 'biblical_analysis', 'scoring_results'
                ]
                
                for attr in expected_attributes:
                    assert hasattr(result, attr), f"AnalysisResult should have {attr} attribute"
                
                # Verify nested structure
                assert 'final_score' in result.scoring_results, "Should have final_score"
                assert 'quality_level' in result.scoring_results, "Should have quality_level"
                assert 'themes' in result.biblical_analysis, "Should have themes in biblical_analysis"

    def test_performance_baseline(self, app):
        """Test that analysis performance hasn't degraded significantly."""
        with app.app_context():
            import time
            
            with patch('app.utils.analysis.huggingface_analyzer.pipeline'):
                analyzer = HuggingFaceAnalyzer()
                
                # Mock analyzers for fast execution
                analyzer._sentiment_analyzer = Mock()
                analyzer._safety_analyzer = Mock()
                analyzer._emotion_analyzer = Mock()
                
                analyzer._sentiment_analyzer.return_value = [{'label': 'POSITIVE', 'score': 0.8}]
                analyzer._safety_analyzer.return_value = [{'label': 'SAFE', 'score': 0.9}]
                analyzer._emotion_analyzer.return_value = [{'label': 'joy', 'score': 0.7}]
                
                # Time multiple analyses
                start_time = time.time()
                
                for i in range(10):
                    result = analyzer.analyze_song(
                        f"Test Song {i}",
                        f"Test Artist {i}",
                        f"Test lyrics {i} with some content"
                    )
                    assert result is not None
                
                end_time = time.time()
                total_time = end_time - start_time
                avg_time = total_time / 10
                
                # Analysis should complete in reasonable time (with mocked models)
                assert avg_time < 1.0, f"Average analysis time {avg_time:.3f}s should be under 1 second"

    def test_existing_test_compatibility(self, app):
        """Test that existing test fixtures and patterns still work."""
        with app.app_context():
            # This tests that our changes don't break existing test patterns
            
            # Test creating song and analysis like existing tests do
            song = Song(
                spotify_id='compatibility_test_song',
                title='Compatibility Test',
                artist='Test Artist'
            )
            db.session.add(song)
            db.session.flush()
            
            analysis = AnalysisResult(
                song_id=song.id,
                status='completed',
                score=80.0,
                concern_level='low'
            )
            db.session.add(analysis)
            db.session.commit()
            
            # Verify the objects were created successfully
            assert song.id is not None
            assert analysis.id is not None
            assert analysis.song_id == song.id
            
            # Test querying patterns that existing tests use
            found_song = Song.query.filter_by(spotify_id='compatibility_test_song').first()
            assert found_song is not None
            
            found_analysis = AnalysisResult.query.filter_by(song_id=song.id).first()
            assert found_analysis is not None
            assert found_analysis.score == 80.0 