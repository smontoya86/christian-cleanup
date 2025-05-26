"""
Integration tests for Redis cache with Flask views and database operations.
"""
import pytest
import time
from unittest.mock import patch
from app import create_app, db
from app.models.models import User, Playlist, Song, AnalysisResult, PlaylistSong
from app.utils.cache import cache, invalidate_playlist_cache, invalidate_analysis_cache
from datetime import datetime, timedelta


class TestCacheIntegration:
    """Test cache integration with Flask views and database."""
    
    @pytest.fixture(autouse=True)
    def setup_app(self):
        """Set up test application and database with sample data."""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        self.client = self.app.test_client()
        
        db.create_all()
        
        # Create test data
        self._create_test_data()
        
        yield
        
        # Clear Redis cache
        try:
            if cache._redis_client:
                cache._redis_client.flushall()
        except:
            pass  # Redis might not be available in test environment
            
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def _create_test_data(self):
        """Create comprehensive test data."""
        import uuid
        unique_id = str(uuid.uuid4())[:8]
        
        # Create test user
        self.test_user = User(
            spotify_id=f'test_user_{unique_id}',
            display_name='Test User',
            email=f'test_{unique_id}@example.com',
            access_token='test_token',
            refresh_token='test_refresh',
            token_expiry=datetime.now() + timedelta(hours=1)
        )
        db.session.add(self.test_user)
        db.session.commit()
        
        # Create test playlist
        self.test_playlist = Playlist(
            spotify_id=f'test_playlist_{unique_id}',
            name='Test Playlist',
            owner_id=self.test_user.id
        )
        db.session.add(self.test_playlist)
        db.session.commit()
        
        # Create test songs
        self.test_songs = []
        for i in range(3):
            song = Song(
                spotify_id=f'test_song_{unique_id}_{i}',
                title=f'Test Song {i}',
                artist=f'Test Artist {i}',
                album=f'Test Album {i}'
            )
            self.test_songs.append(song)
            db.session.add(song)
        
        db.session.commit()
        
        # Create playlist-song associations
        for i, song in enumerate(self.test_songs):
            playlist_song = PlaylistSong(
                playlist_id=self.test_playlist.id,
                song_id=song.id,
                track_position=i
            )
            db.session.add(playlist_song)
        
        # Create analysis results
        for song in self.test_songs:
            analysis = AnalysisResult(
                song_id=song.id,
                score=85.0,
                concern_level='Low',
                explanation='Test analysis summary',
                status=AnalysisResult.STATUS_COMPLETED
            )
            db.session.add(analysis)
        
        db.session.commit()
    
    def test_cache_basic_functionality(self):
        """Test basic cache get/set functionality."""
        # Test cache set and get
        test_data = {'test': 'value', 'number': 42}
        cache.set('test_key', test_data, 60)
        
        retrieved_data = cache.get('test_key')
        assert retrieved_data == test_data
        
        # Test cache miss
        missing_data = cache.get('nonexistent_key')
        assert missing_data is None
        
        # Test cache delete
        cache.delete('test_key')
        deleted_data = cache.get('test_key')
        assert deleted_data is None
    
    def test_cache_metrics_tracking(self):
        """Test that cache metrics are properly tracked."""
        # Reset metrics
        cache.cache_hits = 0
        cache.cache_misses = 0
        
        # Test cache miss
        cache.get('nonexistent_key')
        
        # Test cache set and hit
        cache.set('test_key', 'test_value')
        cache.get('test_key')
        
        # Check metrics
        metrics = cache.get_metrics()
        assert metrics['hits'] == 1
        assert metrics['misses'] == 1
        assert metrics['total'] == 2
        assert metrics['hit_rate'] == 50.0
    
    def test_cache_pattern_deletion(self):
        """Test cache pattern deletion functionality."""
        # Set multiple keys with patterns
        cache.set('view:dashboard:user:1', 'dashboard_data')
        cache.set('view:dashboard:user:2', 'dashboard_data_2')
        cache.set('view:playlist:123', 'playlist_data')
        cache.set('other:key', 'other_data')
        
        # Delete dashboard pattern
        deleted_count = cache.delete_pattern('view:dashboard*')
        
        # Check that dashboard keys are deleted but others remain
        assert cache.get('view:dashboard:user:1') is None
        assert cache.get('view:dashboard:user:2') is None
        assert cache.get('view:playlist:123') == 'playlist_data'
        assert cache.get('other:key') == 'other_data'
        
        # Should have deleted 2 keys
        assert deleted_count == 2
    
    def test_cache_invalidation_helpers(self):
        """Test cache invalidation helper functions."""
        # Set up cache entries
        cache.set('view:dashboard:test', 'dashboard_data')
        cache.set('view:playlist_detail:playlist_id:123:test', 'playlist_data')
        cache.set('view:playlist_detail:playlist_id:456:test', 'other_playlist_data')
        
        # Test specific playlist invalidation
        invalidate_playlist_cache(playlist_id=123)
        
        # Check that specific playlist cache is invalidated
        assert cache.get('view:playlist_detail:playlist_id:123:test') is None
        # Dashboard should also be invalidated
        assert cache.get('view:dashboard:test') is None
        # Other playlist should remain
        assert cache.get('view:playlist_detail:playlist_id:456:test') == 'other_playlist_data'
    
    def test_cache_with_json_serialization(self):
        """Test cache with complex data structures."""
        complex_data = {
            'user': {
                'id': 123,
                'name': 'Test User',
                'playlists': [
                    {'id': 1, 'name': 'Playlist 1'},
                    {'id': 2, 'name': 'Playlist 2'}
                ]
            },
            'metadata': {
                'timestamp': '2025-01-25T10:00:00Z',
                'version': '1.0'
            }
        }
        
        cache.set('complex_data', complex_data)
        retrieved_data = cache.get('complex_data')
        
        assert retrieved_data == complex_data
        assert retrieved_data['user']['name'] == 'Test User'
        assert len(retrieved_data['user']['playlists']) == 2
    
    def test_cache_expiration(self):
        """Test cache expiration functionality."""
        # Set a key with short expiration
        cache.set('short_lived_key', 'test_value', 1)  # 1 second
        
        # Should be available immediately
        assert cache.get('short_lived_key') == 'test_value'
        
        # Wait for expiration (this test might be flaky in CI)
        time.sleep(1.1)
        
        # Should be expired now
        expired_value = cache.get('short_lived_key')
        assert expired_value is None
    
    def test_cache_error_handling(self):
        """Test cache error handling when Redis is unavailable."""
        # Test when Redis client is None (unavailable)
        original_client = cache._redis_client
        cache._redis_client = None
        
        try:
            # Operations should not crash and should return appropriate defaults
            assert cache.get('test_key') is None
            assert cache.set('test_key', 'value') is False
            assert cache.delete('test_key') is False
        finally:
            # Restore original client
            cache._redis_client = original_client
    
    def test_cache_key_generation_consistency(self):
        """Test that cache key generation is consistent."""
        from app.utils.cache import cached
        
        @cached(expiry=300, key_prefix='test')
        def test_function(arg1, arg2=None, arg3='default'):
            return f"result_{arg1}_{arg2}_{arg3}"
        
        # Mock cache to capture the key
        with patch.object(cache, 'get') as mock_get, \
             patch.object(cache, 'set') as mock_set:
            
            mock_get.return_value = None  # Cache miss
            
            # Call function with same arguments
            test_function('value1', arg2='value2', arg3='value3')
            test_function('value1', arg2='value2', arg3='value3')
            
            # Should generate the same key both times
            assert mock_get.call_count == 2
            key1 = mock_get.call_args_list[0][0][0]
            key2 = mock_get.call_args_list[1][0][0]
            assert key1 == key2
            
            # Key should contain function name and arguments
            assert 'test:test_function' in key1
            assert 'arg2:value2' in key1
            assert 'arg3:value3' in key1
    
    def test_analysis_cache_invalidation_with_database(self):
        """Test analysis cache invalidation with actual database operations."""
        # Set up cache entries for playlists containing our test songs
        cache.set(f'view:playlist_detail:playlist_id:{self.test_playlist.id}:test', 'playlist_data')
        cache.set('view:dashboard:test', 'dashboard_data')
        
        # Invalidate cache for one of our test songs
        invalidate_analysis_cache(song_id=self.test_songs[0].id)
        
        # Cache should be invalidated because the song is in the playlist
        assert cache.get(f'view:playlist_detail:playlist_id:{self.test_playlist.id}:test') is None
        assert cache.get('view:dashboard:test') is None
    
    def test_cache_with_unicode_and_special_characters(self):
        """Test cache with unicode and special characters."""
        unicode_data = {
            'title': 'Test Song with émojis 🎵🎶',
            'artist': 'Artíst Ñame',
            'description': 'Special chars: @#$%^&*()[]{}|\\:";\'<>?,./',
            'unicode': '测试中文字符'
        }
        
        cache.set('unicode_test', unicode_data)
        retrieved_data = cache.get('unicode_test')
        
        assert retrieved_data == unicode_data
        assert retrieved_data['title'] == 'Test Song with émojis 🎵🎶'
        assert retrieved_data['unicode'] == '测试中文字符'
    
    def test_cache_performance_improvement(self):
        """Test that cache actually improves performance."""
        from app.utils.cache import cached
        
        # This is a basic performance test - in real scenarios the improvement would be more significant
        
        def expensive_operation():
            """Simulate an expensive database operation."""
            time.sleep(0.01)  # 10ms delay
            return {'result': 'expensive_data', 'timestamp': time.time()}
        
        @cached(expiry=60, key_prefix='perf_test')
        def cached_expensive_operation():
            return expensive_operation()
        
        # First call should be slow (cache miss)
        start_time = time.time()
        result1 = cached_expensive_operation()
        first_call_time = time.time() - start_time
        
        # Second call should be faster (cache hit)
        start_time = time.time()
        result2 = cached_expensive_operation()
        second_call_time = time.time() - start_time
        
        # Results should be the same
        assert result1 == result2
        
        # Second call should be faster (cache hit)
        # Note: This might be flaky in CI environments, so we use a generous threshold
        assert second_call_time < first_call_time or second_call_time < 0.005  # Either faster or very fast (< 5ms) 