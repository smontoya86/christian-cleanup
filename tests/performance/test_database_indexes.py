"""
Performance Benchmark Tests for Database Indexes
Tests written BEFORE implementing optimizations (TDD approach)
"""

import time
import pytest
from datetime import datetime, timedelta, timezone
from flask import url_for
from app import create_app
from app.models import Song, AnalysisResult, Playlist, PlaylistSong, User
from app.extensions import db
from tests.conftest import client, app


class TestDatabaseIndexPerformance:
    """Test suite for database index performance benchmarks"""
    
    def test_progress_api_performance_benchmark(self, client, app):
        """Progress API must respond in < 400ms after optimization"""
        with app.app_context():
            self._ensure_test_data_exists()
            
            # Log in a test user for authentication
            self._login_test_user(client)
            
            # Measure API response time
            start_time = time.time()
            response = client.get('/api/analysis/progress')
            end_time = time.time()
            
            response_time_ms = (end_time - start_time) * 1000
            
            # Assertions
            assert response.status_code == 200
            assert response_time_ms < 400, f"Progress API took {response_time_ms:.1f}ms, target was 400ms"
            
            # Log performance for tracking
            print(f"Progress API response time: {response_time_ms:.1f}ms")
    
    def test_performance_api_benchmark(self, client, app):
        """Performance API must respond in < 500ms after optimization"""
        with app.app_context():
            self._ensure_test_data_exists()
            
            # Log in a test user for authentication
            self._login_test_user(client)
            
            start_time = time.time()
            response = client.get('/api/analysis/performance')
            end_time = time.time()
            
            response_time_ms = (end_time - start_time) * 1000
            
            assert response.status_code == 200
            assert response_time_ms < 500, f"Performance API took {response_time_ms:.1f}ms, target was 500ms"
            
            print(f"Performance API response time: {response_time_ms:.1f}ms")
    
    def test_playlist_query_performance(self, client, app):
        """Playlist queries with 100+ songs must load in < 200ms"""
        with app.app_context():
            # Create large playlist for testing
            large_playlist = self._create_large_playlist(song_count=100)
            
            # Test the database query performance directly instead of the full endpoint
            # This focuses on the actual database performance being tested
            start_time = time.time()
            
            # Test the specific database queries used in playlist detail view
            playlist_with_songs = db.session.query(Playlist).filter_by(id=large_playlist.id).first()
            songs_query = db.session.query(Song, AnalysisResult, PlaylistSong)\
                .join(PlaylistSong, Song.id == PlaylistSong.song_id)\
                .outerjoin(AnalysisResult, Song.id == AnalysisResult.song_id)\
                .filter(PlaylistSong.playlist_id == large_playlist.id)\
                .order_by(PlaylistSong.track_position)\
                .limit(50).all()
            
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000
            
            # Verify we got data
            assert playlist_with_songs is not None
            assert len(songs_query) > 0
            assert response_time_ms < 200, f"Large playlist query took {response_time_ms:.1f}ms, target was 200ms"
            
            print(f"Large playlist query time: {response_time_ms:.1f}ms")
    
    def test_dashboard_performance_with_many_playlists(self, client, app):
        """Dashboard with 25+ playlists must load in < 100ms"""
        with app.app_context():
            # Create multiple playlists for testing
            self._create_multiple_playlists(count=30)
            
            # Log in a test user for authentication
            self._login_test_user(client)
            
            start_time = time.time()
            response = client.get('/dashboard')
            end_time = time.time()
            
            response_time_ms = (end_time - start_time) * 1000
            
            assert response.status_code == 200
            assert response_time_ms < 100, f"Dashboard took {response_time_ms:.1f}ms, target was 100ms"
            
            print(f"Dashboard with many playlists: {response_time_ms:.1f}ms")
    
    def test_analysis_results_query_performance(self, app):
        """Direct database query performance for analysis results"""
        with app.app_context():
            self._ensure_analysis_results_exist()
            
            # Test the specific slow query from Progress API
            start_time = time.time()
            recent_results = db.session.query(AnalysisResult, Song).join(Song).filter(
                AnalysisResult.status == 'completed'
            ).order_by(AnalysisResult.analyzed_at.desc()).limit(5).all()
            end_time = time.time()
            
            query_time_ms = (end_time - start_time) * 1000
            
            assert len(recent_results) <= 5
            assert query_time_ms < 50, f"Analysis results query took {query_time_ms:.1f}ms, target was 50ms"
            
            print(f"Analysis results query time: {query_time_ms:.1f}ms")
    
    def test_playlist_songs_join_performance(self, app):
        """Test playlist-songs join query performance"""
        with app.app_context():
            playlist = self._create_large_playlist(song_count=50)
            
            start_time = time.time()
            songs = db.session.query(Song, AnalysisResult)\
                .join(PlaylistSong)\
                .outerjoin(AnalysisResult)\
                .filter(PlaylistSong.playlist_id == playlist.id)\
                .order_by(PlaylistSong.track_position)\
                .limit(25).all()
            end_time = time.time()
            
            query_time_ms = (end_time - start_time) * 1000
            
            assert len(songs) <= 25
            assert query_time_ms < 30, f"Playlist songs join took {query_time_ms:.1f}ms, target was 30ms"
            
            print(f"Playlist songs join query time: {query_time_ms:.1f}ms")
    
    def test_user_playlists_query_performance(self, app):
        """Test user playlists query performance for dashboard"""
        with app.app_context():
            user = self._get_or_create_test_user()
            self._create_multiple_playlists(count=20, user=user)
            
            start_time = time.time()
            playlists = Playlist.query.filter_by(owner_id=user.id)\
                .order_by(Playlist.updated_at.desc())\
                .limit(25).all()
            end_time = time.time()
            
            query_time_ms = (end_time - start_time) * 1000
            
            assert len(playlists) <= 25
            assert query_time_ms < 20, f"User playlists query took {query_time_ms:.1f}ms, target was 20ms"
            
            print(f"User playlists query time: {query_time_ms:.1f}ms")
    
    # Helper methods for test data creation
    
    def _ensure_test_data_exists(self):
        """Ensure minimum test data exists for API tests"""
        if db.session.query(Song).count() < 10:
            self._create_test_songs(count=20)
        
        if db.session.query(AnalysisResult).filter(AnalysisResult.status == 'completed').count() < 5:
            self._create_test_analysis_results(count=10)
    
    def _ensure_analysis_results_exist(self):
        """Ensure analysis results exist for testing"""
        if db.session.query(AnalysisResult).filter(AnalysisResult.status == 'completed').count() < 10:
            self._create_test_analysis_results(count=20)
    
    def _create_test_songs(self, count=10):
        """Create test songs for performance testing"""
        for i in range(count):
            song = Song(
                spotify_id=f'test_song_{i}',
                title=f'Test Song {i}',
                artist=f'Test Artist {i}',
                album=f'Test Album {i}',
                duration_ms=180000,
                explicit=False
            )
            db.session.add(song)
        db.session.commit()
    
    def _create_test_analysis_results(self, count=10):
        """Create test analysis results"""
        songs = db.session.query(Song).limit(count).all()
        
        for i, song in enumerate(songs):
            if not song.analysis_results:
                analysis = AnalysisResult(
                    song_id=song.id,
                    status='completed',
                    overall_score=85 - (i % 20),  # Vary scores
                    concern_level='low' if i % 3 == 0 else 'medium',
                    explanation=f'Test analysis for song {i}',
                    analyzed_at=db.func.now()
                )
                db.session.add(analysis)
        db.session.commit()
    
    def _create_large_playlist(self, song_count=100):
        """Create a playlist with many songs for testing"""
        user = self._get_or_create_test_user()
        
        playlist = Playlist(
            spotify_id=f'large_playlist_{int(time.time())}',
            name=f'Large Test Playlist ({song_count} songs)',
            owner_id=user.id
        )
        db.session.add(playlist)
        db.session.flush()  # Get playlist ID
        
        # Create songs if needed
        existing_songs = db.session.query(Song).limit(song_count).all()
        if len(existing_songs) < song_count:
            self._create_test_songs(count=song_count - len(existing_songs))
            existing_songs = db.session.query(Song).limit(song_count).all()
        
        # Add songs to playlist
        for i, song in enumerate(existing_songs[:song_count]):
            playlist_song = PlaylistSong(
                playlist_id=playlist.id,
                song_id=song.id,
                track_position=i + 1
            )
            db.session.add(playlist_song)
        
        db.session.commit()
        return playlist
    
    def _create_multiple_playlists(self, count=25, user=None):
        """Create multiple playlists for dashboard testing"""
        if user is None:
            user = self._get_or_create_test_user()
        
        for i in range(count):
            playlist = Playlist(
                spotify_id=f'test_playlist_{i}_{int(time.time())}',
                name=f'Test Playlist {i}',
                owner_id=user.id
            )
            db.session.add(playlist)
        
        db.session.commit()
    
    def _get_or_create_test_user(self):
        """Get or create a test user"""
        user = db.session.query(User).filter_by(spotify_id='test_user_performance').first()
        if not user:
            user = User(
                spotify_id='test_user_performance',
                email='test@performance.com',
                display_name='Performance Test User',
                access_token='test_access_token_performance',
                refresh_token='test_refresh_token_performance',
                token_expiry=datetime.now(timezone.utc) + timedelta(hours=1)
            )
            db.session.add(user)
            db.session.commit()
        return user

    def _login_test_user(self, client):
        """Helper to log in test user for authenticated endpoints."""
        # Get or create the test user
        user = self._get_or_create_test_user()
        
        # Set up Flask-Login session
        with client.session_transaction() as sess:
            sess['_user_id'] = str(user.id)
            sess['_fresh'] = True


class TestDatabaseConsistency:
    """Test database integrity after index creation"""
    
    def test_database_integrity_after_indexes(self, app):
        """Verify database integrity after index creation"""
        with app.app_context():
            # Check foreign key constraints
            self._verify_foreign_key_constraints()
            
            # Verify data consistency
            self._verify_data_consistency()
            
            # Test all CRUD operations still work
            self._test_crud_operations()
    
    def _verify_foreign_key_constraints(self):
        """Check that all foreign key relationships are intact"""
        # Check playlist-user relationships
        orphaned_playlists = db.session.query(Playlist).filter(
            ~Playlist.owner_id.in_(db.session.query(User.id))
        ).count()
        assert orphaned_playlists == 0, f"Found {orphaned_playlists} orphaned playlists"
        
        # Check playlist-song relationships
        orphaned_playlist_songs = db.session.query(PlaylistSong).filter(
            ~PlaylistSong.playlist_id.in_(db.session.query(Playlist.id))
        ).count()
        assert orphaned_playlist_songs == 0, f"Found {orphaned_playlist_songs} orphaned playlist songs"
        
        # Check analysis-song relationships
        orphaned_analyses = db.session.query(AnalysisResult).filter(
            ~AnalysisResult.song_id.in_(db.session.query(Song.id))
        ).count()
        assert orphaned_analyses == 0, f"Found {orphaned_analyses} orphaned analyses"
    
    def _verify_data_consistency(self):
        """Verify data consistency across tables"""
        # Verify playlist track counts match actual songs
        playlists_with_songs = db.session.query(
            Playlist.id,
            Playlist.track_count,
            db.func.count(PlaylistSong.song_id).label('actual_count')
        ).outerjoin(PlaylistSong).group_by(Playlist.id, Playlist.track_count).all()
        
        for playlist_id, declared_count, actual_count in playlists_with_songs:
            if declared_count is not None and actual_count != declared_count:
                print(f"Warning: Playlist {playlist_id} declares {declared_count} tracks but has {actual_count}")
    
    def _test_crud_operations(self):
        """Test that basic CRUD operations still work after indexing"""
        # Create
        test_song = Song(
            spotify_id='crud_test_song',
            title='CRUD Test Song',
            artist='Test Artist',
            album='Test Album'
        )
        db.session.add(test_song)
        db.session.commit()
        
        # Read
        retrieved_song = db.session.query(Song).filter_by(spotify_id='crud_test_song').first()
        assert retrieved_song is not None
        assert retrieved_song.title == 'CRUD Test Song'
        
        # Update
        retrieved_song.title = 'Updated CRUD Test Song'
        db.session.commit()
        
        updated_song = db.session.query(Song).filter_by(spotify_id='crud_test_song').first()
        assert updated_song.title == 'Updated CRUD Test Song'
        
        # Delete
        db.session.delete(updated_song)
        db.session.commit()
        
        deleted_song = db.session.query(Song).filter_by(spotify_id='crud_test_song').first()
        assert deleted_song is None


@pytest.fixture
def performance_baseline():
    """Fixture to capture performance baseline before optimizations"""
    return {
        'progress_api_target': 400,  # ms
        'performance_api_target': 500,  # ms
        'large_playlist_target': 200,  # ms
        'dashboard_target': 100,  # ms
        'db_query_target': 50,  # ms
    }


class TestPerformanceRegression:
    """Ensure existing functionality maintains performance"""
    
    def test_all_existing_endpoints_maintain_performance(self, client, app, performance_baseline):
        """Test that all existing API endpoints maintain current performance"""
        endpoints_to_test = [
            ('/', 'GET'),
            ('/health', 'GET'),
            ('/dashboard', 'GET'),
            ('/api/analysis/status', 'GET'),
        ]
        
        with app.app_context():
            for endpoint, method in endpoints_to_test:
                start_time = time.time()
                
                if method == 'GET':
                    response = client.get(endpoint)
                
                end_time = time.time()
                response_time_ms = (end_time - start_time) * 1000
                
                # Existing endpoints should maintain reasonable performance
                assert response_time_ms < 2000, f"{endpoint} took {response_time_ms:.1f}ms (too slow)"
                print(f"{endpoint}: {response_time_ms:.1f}ms")
    
    def test_memory_usage_acceptable(self, app):
        """Verify memory usage doesn't increase significantly"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        
        with app.app_context():
            # Perform some database operations
            songs = db.session.query(Song).limit(100).all()
            analyses = db.session.query(AnalysisResult).limit(100).all()
            playlists = db.session.query(Playlist).limit(50).all()
        
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = memory_after - memory_before
        
        # Memory increase should be reasonable (less than 50MB for these operations)
        assert memory_increase < 50, f"Memory increased by {memory_increase:.1f}MB (too much)"
        print(f"Memory usage: {memory_before:.1f}MB -> {memory_after:.1f}MB (+{memory_increase:.1f}MB)") 