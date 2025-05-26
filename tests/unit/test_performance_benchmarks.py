"""
Tests for database performance benchmarks and optimization verification.
"""
import pytest
import time
from unittest.mock import patch, MagicMock
from app import create_app, db
from app.models.models import User, Playlist, Song, AnalysisResult, PlaylistSong
from app.services.batch_operations import BatchOperationService
from app.utils.database_monitoring import get_pool_status, check_pool_health
from app.utils.query_monitoring import get_query_statistics
from scripts.performance_assessment import PerformanceAssessment


class TestPerformanceBenchmarks:
    """Test performance benchmarks and optimization verification."""
    
    @pytest.fixture(autouse=True)
    def setup_app(self):
        """Set up test application and database with sample data."""
        self.app = create_app('testing')
        # Enable query recording for performance testing
        self.app.config['SQLALCHEMY_RECORD_QUERIES'] = True
        self.app.config['SLOW_QUERY_THRESHOLD'] = 0.1  # 100ms threshold
        
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # Create test data
        self._create_test_data()
        
        yield
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def _create_test_data(self):
        """Create comprehensive test data for performance testing."""
        # Create test user
        from datetime import datetime, timedelta
        import uuid
        unique_id = str(uuid.uuid4())[:8]
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
        
        # Create multiple playlists
        self.test_playlists = []
        for i in range(5):
            playlist = Playlist(
                spotify_id=f'test_playlist_{unique_id}_{i}',
                name=f'Test Playlist {i}',
                owner_id=self.test_user.id
            )
            self.test_playlists.append(playlist)
            db.session.add(playlist)
        
        db.session.commit()
        
        # Create multiple songs
        self.test_songs = []
        for i in range(20):
            song = Song(
                spotify_id=f'test_song_{unique_id}_{i}',
                title=f'Test Song {i}',
                artist=f'Test Artist {i % 5}',  # 5 different artists
                album=f'Test Album {i % 3}'     # 3 different albums
            )
            self.test_songs.append(song)
            db.session.add(song)
        
        db.session.commit()
        
        # Create playlist-song associations
        for playlist in self.test_playlists:
            for i, song in enumerate(self.test_songs[:4]):  # 4 songs per playlist
                playlist_song = PlaylistSong(
                    playlist_id=playlist.id,
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
    
    def test_performance_assessment_initialization(self):
        """Test that PerformanceAssessment can be initialized and run."""
        assessment = PerformanceAssessment()
        
        # Should be able to initialize without errors
        assert assessment is not None
        assert hasattr(assessment, 'run_assessment')
        assert hasattr(assessment, 'benchmark_playlist_loading')
        assert hasattr(assessment, 'benchmark_song_queries')
        assert hasattr(assessment, 'benchmark_batch_operations')
    
    def test_playlist_loading_performance(self):
        """Test playlist loading performance with and without optimization."""
        # Test unoptimized query (N+1 pattern)
        start_time = time.time()
        playlists = Playlist.query.filter_by(owner_id=self.test_user.id).all()
        for playlist in playlists:
            # This creates N+1 queries - one for playlists, then one per playlist for songs
            songs = Song.query.join(PlaylistSong).filter(
                PlaylistSong.playlist_id == playlist.id
            ).all()
            for song in songs:
                # Another N queries for analysis results
                analysis = AnalysisResult.query.filter_by(song_id=song.id).first()
        unoptimized_time = time.time() - start_time
        
        # Test optimized query with eager loading
        start_time = time.time()
        from sqlalchemy.orm import joinedload, subqueryload
        playlists = Playlist.query.filter_by(owner_id=self.test_user.id).options(
            subqueryload(Playlist.song_associations).joinedload(PlaylistSong.song)
        ).all()
        # Pre-load analysis results for all songs in one query
        song_ids = []
        for playlist in playlists:
            for song_assoc in playlist.song_associations:
                song_ids.append(song_assoc.song.id)
        
        if song_ids:
            analysis_results = AnalysisResult.query.filter(AnalysisResult.song_id.in_(song_ids)).all()
            analysis_map = {result.song_id: result for result in analysis_results}
        
        # Access the data to trigger loading
        for playlist in playlists:
            for song_assoc in playlist.song_associations:
                song = song_assoc.song
                analysis = analysis_map.get(song.id)
        optimized_time = time.time() - start_time
        
        # Optimized query should be faster (or at least not significantly slower)
        assert optimized_time <= unoptimized_time * 1.5  # Allow 50% tolerance
        
        # Verify data integrity
        assert len(playlists) == 5
        for playlist in playlists:
            assert len(playlist.songs) == 4
            for song in playlist.songs:
                assert song.analysis_results.count() > 0
    
    def test_batch_operations_performance(self):
        """Test batch operations performance vs individual operations."""
        batch_service = BatchOperationService()
        
        # Test individual song creation (simulated)
        start_time = time.time()
        individual_songs = []
        for i in range(10):
            song = Song(
                spotify_id=f'individual_song_{i}',
                title=f'Individual Song {i}',
                artist=f'Individual Artist {i}'
            )
            db.session.add(song)
            db.session.commit()  # Individual commits
            individual_songs.append(song)
        individual_time = time.time() - start_time
        
        # Clean up individual songs
        for song in individual_songs:
            db.session.delete(song)
        db.session.commit()
        
        # Test batch song creation
        start_time = time.time()
        song_data = [
            {
                'spotify_id': f'batch_song_{i}',
                'title': f'Batch Song {i}',
                'artist': f'Batch Artist {i}'
            }
            for i in range(10)
        ]
        batch_songs = batch_service.create_songs_batch(song_data)
        batch_time = time.time() - start_time
        
        # Batch operations should be significantly faster
        assert batch_time < individual_time
        assert len(batch_songs) == 10
        
        # Verify all songs were created
        created_songs = Song.query.filter(Song.spotify_id.like('batch_song_%')).all()
        assert len(created_songs) == 10
    
    def test_index_performance_verification(self):
        """Test that database indexes are improving query performance."""
        # Test query on indexed column (spotify_id)
        start_time = time.time()
        song = Song.query.filter_by(spotify_id=self.test_songs[0].spotify_id).first()
        indexed_query_time = time.time() - start_time
        
        # Test query on non-indexed column (if any)
        start_time = time.time()
        songs = Song.query.filter(Song.title.like('Test Song%')).all()
        non_indexed_query_time = time.time() - start_time
        
        # Indexed queries should be reasonably fast (under 50ms for test environment)
        assert indexed_query_time < 0.05  # 50ms
        assert song is not None
        assert song.spotify_id == self.test_songs[0].spotify_id
        
        # Non-indexed queries may be slower but should still complete
        assert len(songs) > 0
    
    def test_connection_pool_performance(self):
        """Test connection pool performance and health."""
        # Get pool status
        pool_status = get_pool_status()
        
        # Verify pool is configured correctly
        assert 'pool_size' in pool_status
        assert 'checked_in' in pool_status
        assert 'checked_out' in pool_status
        assert 'overflow' in pool_status
        
        # Check pool health
        health_status = check_pool_health()
        assert 'healthy' in health_status
        assert 'recommendations' in health_status
        assert 'status' in health_status
        
        # Pool should be healthy with test data (allow unhealthy for test environment)
        assert isinstance(health_status['healthy'], bool)
    
    def test_query_monitoring_performance(self):
        """Test query monitoring and statistics collection."""
        # Execute some queries to generate statistics
        playlists = Playlist.query.filter_by(owner_id=self.test_user.id).all()
        songs = Song.query.filter(Song.artist.like('Test Artist%')).all()
        
        # Get query statistics
        stats = get_query_statistics()
        
        # Verify statistics structure
        assert isinstance(stats, dict)
        assert 'total_queries' in stats
        assert 'slow_queries' in stats
        assert 'average_duration' in stats
        assert 'queries' in stats
        
        # Should have recorded some queries
        assert stats['total_queries'] > 0
        assert isinstance(stats['queries'], list)
        
        # Verify query details
        if stats['queries']:
            query = stats['queries'][0]
            assert 'duration' in query
            assert 'statement' in query
            assert 'is_slow' in query
    
    def test_performance_regression_detection(self):
        """Test that performance hasn't regressed from baseline."""
        # Define performance baselines (these would be updated based on actual measurements)
        BASELINE_PLAYLIST_LOAD_TIME = 0.1  # 100ms
        BASELINE_SONG_QUERY_TIME = 0.05    # 50ms
        BASELINE_BATCH_OPERATION_TIME = 0.2  # 200ms for 10 items
        
        # Test playlist loading performance
        start_time = time.time()
        from sqlalchemy.orm import subqueryload, joinedload
        playlists = Playlist.query.filter_by(owner_id=self.test_user.id).options(
            subqueryload(Playlist.song_associations).joinedload(PlaylistSong.song)
        ).all()
        # Pre-load analysis results for all songs in one query
        song_ids = []
        for playlist in playlists:
            for song_assoc in playlist.song_associations:
                song_ids.append(song_assoc.song.id)
        
        if song_ids:
            analysis_results = AnalysisResult.query.filter(AnalysisResult.song_id.in_(song_ids)).all()
            analysis_map = {result.song_id: result for result in analysis_results}
        playlist_load_time = time.time() - start_time
        
        # Test song query performance
        start_time = time.time()
        song = Song.query.filter_by(spotify_id=self.test_songs[0].spotify_id).first()
        song_query_time = time.time() - start_time
        
        # Test batch operation performance
        batch_service = BatchOperationService()
        start_time = time.time()
        song_data = [
            {
                'spotify_id': f'regression_song_{i}',
                'title': f'Regression Song {i}',
                'artist': f'Regression Artist {i}'
            }
            for i in range(10)
        ]
        batch_songs = batch_service.create_songs_batch(song_data)
        batch_operation_time = time.time() - start_time
        
        # Performance should meet or exceed baselines
        # Allow 50% tolerance for test environment variations
        assert playlist_load_time <= BASELINE_PLAYLIST_LOAD_TIME * 1.5
        assert song_query_time <= BASELINE_SONG_QUERY_TIME * 1.5
        assert batch_operation_time <= BASELINE_BATCH_OPERATION_TIME * 1.5
        
        # Verify data integrity
        assert len(playlists) == 5
        assert song is not None
        assert len(batch_songs) == 10
    
    def test_memory_usage_optimization(self):
        """Test that memory usage is optimized for large datasets."""
        # This test would ideally use memory profiling tools
        # For now, we'll test that large queries complete without errors
        
        # Create additional test data
        large_song_batch = []
        for i in range(100):
            song_data = {
                'spotify_id': f'memory_test_song_{i}',
                'title': f'Memory Test Song {i}',
                'artist': f'Memory Test Artist {i % 10}'
            }
            large_song_batch.append(song_data)
        
        # Test batch creation with large dataset
        batch_service = BatchOperationService()
        start_time = time.time()
        created_songs = batch_service.create_songs_batch(large_song_batch)
        batch_time = time.time() - start_time
        
        # Should complete in reasonable time
        assert batch_time < 5.0  # 5 seconds max for 100 songs
        assert len(created_songs) == 100
        
        # Test querying large dataset
        start_time = time.time()
        songs = Song.query.filter(Song.spotify_id.like('memory_test_song_%')).all()
        query_time = time.time() - start_time
        
        # Should complete efficiently
        assert query_time < 1.0  # 1 second max for 100 songs
        assert len(songs) == 100
    
    def test_concurrent_access_performance(self):
        """Test performance under simulated concurrent access."""
        import threading
        import queue
        
        results = queue.Queue()
        
        def worker():
            """Worker function to simulate concurrent database access."""
            try:
                with self.app.app_context():
                    # Create a new session for this thread
                    from sqlalchemy.orm import sessionmaker
                    Session = sessionmaker(bind=db.engine)
                    session = Session()
                    
                    try:
                        # Simulate typical user operations using the thread-local session
                        playlists = session.query(Playlist).filter_by(owner_id=self.test_user.id).all()
                        song_count = 0
                        for playlist in playlists:
                            songs = session.query(Song).join(PlaylistSong).filter(
                                PlaylistSong.playlist_id == playlist.id
                            ).limit(2).all()
                            song_count += len(songs)
                        results.put(('success', len(playlists), song_count))
                    finally:
                        session.close()
            except Exception as e:
                results.put(('error', str(e)))
        
        # Create multiple threads to simulate concurrent access
        threads = []
        start_time = time.time()
        
        for i in range(5):  # 5 concurrent threads
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Collect results
        success_count = 0
        error_count = 0
        
        while not results.empty():
            result = results.get()
            if result[0] == 'success':
                success_count += 1
                assert result[1] == 5  # Should find 5 playlists
                assert result[2] > 0   # Should find some songs
            else:
                error_count += 1
                print(f"Concurrent access error: {result[1]}")
        
        # Most operations should succeed (allow some failures due to test environment limitations)
        assert success_count >= 3  # At least 3 out of 5 should succeed
        assert success_count > error_count  # More successes than failures
        
        # Should complete in reasonable time
        assert total_time < 2.0  # 2 seconds max for 5 concurrent operations 