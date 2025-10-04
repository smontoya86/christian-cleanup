"""
Comprehensive regression test suite for recent changes.

Tests all critical functionality to ensure recent updates didn't break existing features.
Covers:
- Prompt optimization
- Database indexes
- Docker configuration  
- Security enhancements
- Admin authentication
- Background job processing
- Frontend integration
"""
import pytest
import json
import os
from unittest.mock import patch, Mock


class TestPromptOptimization:
    """Regression tests for prompt optimization"""
    
    def test_prompt_is_optimized_length(self):
        """Verify production prompt is shorter than training prompt"""
        from app.services.analyzers.router_analyzer import RouterAnalyzer
        
        analyzer = RouterAnalyzer()
        prompt = analyzer._get_comprehensive_system_prompt()
        
        # Optimized prompt should be significantly shorter (< 2500 chars)
        assert len(prompt) < 2500, f"Prompt too long: {len(prompt)} chars"
        
        # Should be at least 100 chars (not empty)
        assert len(prompt) > 100, "Prompt suspiciously short"
    
    def test_prompt_contains_framework_version(self):
        """Verify prompt references Christian Framework v3.1"""
        from app.services.analyzers.router_analyzer import RouterAnalyzer
        
        analyzer = RouterAnalyzer()
        prompt = analyzer._get_comprehensive_system_prompt()
        
        assert 'Christian Framework v3.1' in prompt
        assert 'fine-tuned' in prompt.lower()
    
    def test_prompt_includes_edge_cases(self):
        """Verify prompt includes key edge case reminders"""
        from app.services.analyzers.router_analyzer import RouterAnalyzer
        
        analyzer = RouterAnalyzer()
        prompt = analyzer._get_comprehensive_system_prompt()
        
        # Critical edge cases
        assert 'Common Grace' in prompt
        assert 'Vague Spirituality' in prompt
        assert 'Lament Filter' in prompt
        assert 'Character Voice' in prompt or 'narrative_voice' in prompt
        assert 'Scripture Required' in prompt or 'scripture' in prompt.lower()
    
    def test_prompt_includes_verdict_tiers(self):
        """Verify prompt includes all verdict tiers with scores"""
        from app.services.analyzers.router_analyzer import RouterAnalyzer
        
        analyzer = RouterAnalyzer()
        prompt = analyzer._get_comprehensive_system_prompt()
        
        # All verdict tiers
        assert 'freely_listen' in prompt
        assert 'context_required' in prompt
        assert 'caution_limit' in prompt
        assert 'avoid_formation' in prompt
        
        # Score ranges
        assert '85-100' in prompt or '85' in prompt
        assert '60-84' in prompt or '60' in prompt
        assert '40-59' in prompt or '40' in prompt
        assert '0-39' in prompt or '0' in prompt
    
    def test_prompt_includes_formation_risk_levels(self):
        """Verify prompt includes formation risk levels"""
        from app.services.analyzers.router_analyzer import RouterAnalyzer
        
        analyzer = RouterAnalyzer()
        prompt = analyzer._get_comprehensive_system_prompt()
        
        assert 'very_low' in prompt or 'very low' in prompt.lower()
        assert 'low' in prompt
        assert 'high' in prompt
        assert 'critical' in prompt
    
    def test_prompt_includes_json_schema(self):
        """Verify prompt includes JSON response schema"""
        from app.services.analyzers.router_analyzer import RouterAnalyzer
        
        analyzer = RouterAnalyzer()
        prompt = analyzer._get_comprehensive_system_prompt()
        
        # JSON structure keys
        assert 'score' in prompt.lower()
        assert 'verdict' in prompt.lower()
        assert 'formation_risk' in prompt
        assert 'themes_positive' in prompt or 'positive' in prompt.lower()
        assert 'themes_negative' in prompt or 'negative' in prompt.lower()
        assert 'scripture_references' in prompt or 'scripture' in prompt.lower()
    
    def test_analysis_still_returns_valid_structure(self, app, sample_song):
        """Verify analysis with optimized prompt still returns correct structure"""
        from app.services.unified_analysis_service import UnifiedAnalysisService
        
        with app.app_context():
            service = UnifiedAnalysisService()
            
            with patch.object(service, '_get_or_fetch_lyrics', return_value='Amazing grace how sweet the sound'):
                with patch('app.services.analyzers.router_analyzer.RouterAnalyzer.analyze') as mock_analyze:
                    # Mock response matching expected structure
                    mock_analyze.return_value = {
                        'score': 95,
                        'verdict': 'freely_listen',
                        'formation_risk': 'very_low',
                        'themes_positive': [{'theme': 'Worship', 'points': 15, 'scripture': 'Psalm 95:1'}],
                        'themes_negative': [],
                        'concerns': [],
                        'scripture_references': ['Ephesians 2:8'],
                        'analysis': 'Classic Christian hymn about grace'
                    }
                    
                    result = service.analyze_song(sample_song.id, user_id=1)
                    
                    # Verify result exists and has correct structure
                    assert result is not None
                    assert hasattr(result, 'score')
                    assert hasattr(result, 'verdict')


class TestDatabaseIndexes:
    """Regression tests for database index additions"""
    
    def test_analysis_result_has_required_indexes(self):
        """Verify AnalysisResult model has all required indexes"""
        from app.models import AnalysisResult
        
        index_names = [idx.name for idx in AnalysisResult.__table__.indexes]
        
        # Original indexes
        assert 'idx_analysis_song_id' in index_names
        assert 'idx_analysis_concern_level' in index_names
        assert 'idx_analysis_song_created' in index_names
        
        # New indexes (from quick fixes)
        assert 'idx_analysis_status' in index_names
        assert 'idx_analysis_score' in index_names
    
    def test_indexes_include_correct_columns(self):
        """Verify indexes reference correct columns"""
        from app.models import AnalysisResult
        
        # Find status and score indexes
        status_idx = None
        score_idx = None
        
        for idx in AnalysisResult.__table__.indexes:
            if idx.name == 'idx_analysis_status':
                status_idx = idx
            elif idx.name == 'idx_analysis_score':
                score_idx = idx
        
        assert status_idx is not None, "Status index missing"
        assert score_idx is not None, "Score index missing"
        
        # Verify columns
        assert 'status' in [col.name for col in status_idx.columns]
        assert 'score' in [col.name for col in score_idx.columns]
    
    def test_database_queries_still_work(self, app, db_session, sample_song):
        """Verify common queries still work with new indexes"""
        from app.models import AnalysisResult
        
        with app.app_context():
            # Create test analysis
            analysis = AnalysisResult(
                song_id=sample_song.id,
                score=85,
                verdict='freely_listen',
                status='completed',
                biblical_themes=['worship'],
                concerns=[]
            )
            db_session.add(analysis)
            db_session.commit()
            
            # Query by status (uses new index)
            results = AnalysisResult.query.filter_by(status='completed').all()
            assert len(results) >= 1
            
            # Query by score (uses new index)
            high_scores = AnalysisResult.query.filter(AnalysisResult.score >= 80).all()
            assert len(high_scores) >= 1


class TestDockerConfiguration:
    """Regression tests for Docker Compose configuration"""
    
    def test_docker_compose_file_exists(self):
        """Verify docker-compose.yml exists"""
        assert os.path.exists('docker-compose.yml')
    
    def test_docker_compose_has_multiple_workers(self):
        """Verify Gunicorn is configured with 4 workers"""
        with open('docker-compose.yml', 'r') as f:
            content = f.read()
            
            # Should have 4 workers
            assert '--workers 4' in content or '--workers=4' in content
    
    def test_docker_compose_has_reasonable_timeout(self):
        """Verify Gunicorn timeout is set to 300s (not 1800s)"""
        with open('docker-compose.yml', 'r') as f:
            content = f.read()
            
            # Should have 300s timeout
            assert '--timeout 300' in content or '--timeout=300' in content
            
            # Should NOT have old 1800s timeout
            assert '1800' not in content
    
    def test_docker_compose_has_rq_worker_service(self):
        """Verify RQ worker service is configured"""
        with open('docker-compose.yml', 'r') as f:
            content = f.read()
            
            assert 'worker:' in content
            assert 'rq worker analysis' in content
    
    def test_docker_compose_has_redis_service(self):
        """Verify Redis service is configured"""
        with open('docker-compose.yml', 'r') as f:
            content = f.read()
            
            assert 'redis:' in content
            assert 'redis:7-alpine' in content or 'redis:' in content
            
            # Redis optimization
            assert 'maxmemory' in content
            assert 'maxmemory-policy' in content
    
    def test_docker_compose_services_have_healthchecks(self):
        """Verify critical services have healthchecks"""
        with open('docker-compose.yml', 'r') as f:
            content = f.read()
            
            # Should have healthcheck for web service
            assert 'healthcheck:' in content
            
            # Should check multiple services
            assert content.count('healthcheck:') >= 3  # web, db, redis at minimum


class TestSecurityEnhancements:
    """Regression tests for security improvements"""
    
    def test_encryption_key_validation_in_production(self):
        """Verify ENCRYPTION_KEY is required in production"""
        import os
        
        # Read app/__init__.py to verify validation exists
        with open('app/__init__.py', 'r') as f:
            content = f.read()
            
            # Should check for ENCRYPTION_KEY in production
            assert 'ENCRYPTION_KEY' in content
            assert "FLASK_ENV" in content or "production" in content.lower()
            assert 'RuntimeError' in content or 'raise' in content.lower()
    
    def test_encryption_key_not_required_in_testing(self, app):
        """Verify ENCRYPTION_KEY not required in test environment"""
        # Test app should load without ENCRYPTION_KEY
        assert app is not None
        assert app.config['TESTING'] is True
    
    def test_app_fails_without_encryption_key_in_production(self):
        """Verify app raises error without ENCRYPTION_KEY in production"""
        from app import create_app
        
        with patch.dict(os.environ, {
            'FLASK_ENV': 'production',
            'ENCRYPTION_KEY': '',
            'DATABASE_URL': 'sqlite:///:memory:'
        }, clear=False):
            with pytest.raises(RuntimeError, match='ENCRYPTION_KEY'):
                create_app()


class TestAdminAuthentication:
    """Regression tests for admin authentication improvements"""
    
    def test_admin_required_decorator_exists(self):
        """Verify admin_required decorator still exists"""
        from app.routes.admin import admin_required
        
        assert callable(admin_required)
    
    def test_admin_required_checks_is_admin_attribute(self):
        """Verify admin_required uses is_admin attribute (not hardcoded ID)"""
        # Read admin.py to verify no hardcoded ID check
        with open('app/routes/admin.py', 'r') as f:
            content = f.read()
            
            # Should use is_admin attribute
            assert 'is_admin' in content
            
            # Should NOT have hardcoded user ID check
            assert 'current_user.id != 1' not in content
            assert 'current_user.id == 1' not in content
    
    def test_admin_routes_reject_non_admin(self, client, auth):
        """Verify admin routes reject non-admin users"""
        # Login as non-admin
        auth.login(is_admin=False)
        
        # Try to access admin dashboard
        response = client.get('/admin/dashboard')
        assert response.status_code == 403
    
    def test_admin_routes_accept_admin_users(self, client, auth):
        """Verify admin routes accept admin users"""
        # Login as admin
        auth.login(is_admin=True)
        
        # Should be able to access admin dashboard
        response = client.get('/admin/dashboard')
        assert response.status_code == 200


class TestExistingFunctionalityIntact:
    """Regression tests to verify existing features still work"""
    
    def test_user_can_login(self, client, sample_user):
        """Verify user login still works"""
        # Login flow should still work
        with client.session_transaction() as sess:
            sess['_user_id'] = str(sample_user.id)
        
        response = client.get('/dashboard')
        assert response.status_code == 200
    
    def test_playlist_sync_still_works(self, client, auth, sample_user):
        """Verify playlist sync endpoint still works"""
        auth.login(user=sample_user)
        
        with patch('app.routes.api.SpotifyService') as MockSpotify:
            mock_service = Mock()
            mock_service.get_user_playlists.return_value = []
            MockSpotify.return_value = mock_service
            
            response = client.post('/api/sync_playlists')
            
            # Should not error (200 or 302)
            assert response.status_code in [200, 302]
    
    def test_song_detail_page_loads(self, client, auth, sample_song):
        """Verify song detail page still loads"""
        auth.login()
        
        response = client.get(f'/song/{sample_song.id}')
        assert response.status_code == 200
    
    def test_playlist_detail_page_loads(self, client, auth, sample_playlist):
        """Verify playlist detail page still loads"""
        auth.login(user=sample_playlist.owner)
        
        response = client.get(f'/playlist/{sample_playlist.id}')
        assert response.status_code == 200
    
    def test_analysis_service_still_creates_results(self, app, sample_song):
        """Verify analysis service still creates AnalysisResult records"""
        from app.services.unified_analysis_service import UnifiedAnalysisService
        from app.models import AnalysisResult
        
        with app.app_context():
            service = UnifiedAnalysisService()
            
            with patch.object(service, '_get_or_fetch_lyrics', return_value='Test lyrics'):
                with patch('app.services.analyzers.router_analyzer.RouterAnalyzer.analyze') as mock_analyze:
                    mock_analyze.return_value = {
                        'score': 75,
                        'verdict': 'context_required',
                        'formation_risk': 'low',
                        'themes_positive': [],
                        'themes_negative': [],
                        'concerns': [],
                        'scripture_references': ['Romans 12:1'],
                        'analysis': 'Test analysis'
                    }
                    
                    result = service.analyze_song(sample_song.id, user_id=1)
                    
                    assert result is not None
                    assert isinstance(result, AnalysisResult)
                    assert result.score == 75
    
    def test_lyrics_fetching_still_works(self, app, sample_song):
        """Verify lyrics fetching still works"""
        from app.services.unified_analysis_service import UnifiedAnalysisService
        
        with app.app_context():
            service = UnifiedAnalysisService()
            
            with patch('app.services.unified_analysis_service.LyricsCache') as MockCache:
                # Mock cache miss then successful fetch
                MockCache.query.filter_by.return_value.first.return_value = None
                
                with patch.object(service, '_fetch_lyrics_from_providers', return_value=('Test lyrics', 'test_provider')):
                    lyrics = service._get_or_fetch_lyrics(sample_song)
                    
                    assert lyrics == 'Test lyrics'


class TestFrontendIntegration:
    """Regression tests for frontend integration"""
    
    def test_progress_modal_js_exists(self):
        """Verify progress-modal.js file exists"""
        assert os.path.exists('app/static/js/progress-modal.js')
    
    def test_progress_modal_has_required_methods(self):
        """Verify progress modal has required methods"""
        with open('app/static/js/progress-modal.js', 'r') as f:
            content = f.read()
            
            assert 'class ProgressModal' in content
            assert 'show(' in content
            assert '_pollStatus' in content
            assert '_updateModal' in content
    
    def test_playlist_analysis_module_updated(self):
        """Verify playlist-analysis.js was updated for RQ"""
        with open('app/static/js/modules/playlist-analysis.js', 'r') as f:
            content = f.read()
            
            # Should reference new progress modal
            assert 'ProgressModal' in content
            
            # Should call new API endpoint
            assert '/api/analyze_playlist/' in content or 'analyze_playlist' in content
    
    def test_playlist_detail_template_includes_progress_modal(self):
        """Verify playlist_detail.html includes progress-modal.js"""
        with open('app/templates/playlist_detail.html', 'r') as f:
            content = f.read()
            
            assert 'progress-modal.js' in content


class TestRequirementsTxt:
    """Regression tests for requirements.txt"""
    
    def test_rq_is_in_requirements(self):
        """Verify rq package is in requirements.txt"""
        with open('requirements.txt', 'r') as f:
            content = f.read()
            
            assert 'rq' in content.lower()
            assert 'redis' in content.lower()
    
    def test_existing_packages_still_present(self):
        """Verify critical existing packages still in requirements"""
        with open('requirements.txt', 'r') as f:
            content = f.read()
            
            # Critical packages
            assert 'flask' in content.lower()
            assert 'sqlalchemy' in content.lower()
            assert 'openai' in content.lower()
            assert 'gunicorn' in content.lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

