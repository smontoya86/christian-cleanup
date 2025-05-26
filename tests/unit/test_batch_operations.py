"""
Tests for batch database operations optimization.
"""
import time
import pytest
from unittest.mock import patch, MagicMock
from app import create_app, db
from app.models.models import User, Playlist, Song, AnalysisResult, PlaylistSong
from app.services.batch_operations import BatchOperationService
from datetime import datetime, timedelta


class TestBatchOperations:
    """Test batch database operations for performance optimization."""
    
    @pytest.fixture(autouse=True)
    def setup_app(self):
        """Set up test application and database."""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_batch_song_creation(self):
        """Test that songs can be created in batches efficiently."""
        # Create test data
        song_data = [
            {
                'spotify_id': f'test_song_{i}',
                'title': f'Test Song {i}',
                'artist': 'Test Artist',
                'album': 'Test Album'
            }
            for i in range(10)
        ]
        
        # Test batch creation
        start_time = time.time()
        batch_service = BatchOperationService()
        created_songs = batch_service.create_songs_batch(song_data)
        batch_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Verify results
        assert len(created_songs) == 10
        assert all(song.id is not None for song in created_songs)
        assert batch_time < 200, f"Batch song creation took {batch_time:.1f}ms, should be < 200ms"
        
        # Verify songs are in database
        db_songs = Song.query.all()
        assert len(db_songs) == 10
    
    def test_batch_playlist_song_associations(self):
        """Test that playlist-song associations can be created in batches."""
        # Create test user, playlist, and songs
        user = User(
            spotify_id='test_user', 
            email='test@example.com',
            access_token='test_token',
            refresh_token='test_refresh',
            token_expiry=datetime.utcnow() + timedelta(hours=1)
        )
        db.session.add(user)
        db.session.commit()
        
        playlist = Playlist(
            spotify_id='test_playlist',
            name='Test Playlist',
            owner_id=user.id
        )
        db.session.add(playlist)
        db.session.commit()
        
        songs = []
        for i in range(5):
            song = Song(
                spotify_id=f'test_song_{i}',
                title=f'Test Song {i}',
                artist='Test Artist'
            )
            songs.append(song)
            db.session.add(song)
        db.session.commit()
        
        # Test batch association creation
        association_data = [
            {
                'playlist_id': playlist.id,
                'song_id': song.id,
                'track_position': idx
            }
            for idx, song in enumerate(songs)
        ]
        
        start_time = time.time()
        batch_service = BatchOperationService()
        created_associations = batch_service.create_playlist_song_associations_batch(association_data)
        batch_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Verify results
        assert len(created_associations) == 5
        assert batch_time < 100, f"Batch association creation took {batch_time:.1f}ms, should be < 100ms"
        
        # Verify associations are in database
        db_associations = PlaylistSong.query.all()
        assert len(db_associations) == 5
    
    def test_batch_analysis_updates(self):
        """Test that analysis results can be updated in batches."""
        # Create test songs and analysis results
        songs = []
        analyses = []
        for i in range(5):
            song = Song(
                spotify_id=f'test_song_{i}',
                title=f'Test Song {i}',
                artist='Test Artist'
            )
            songs.append(song)
            db.session.add(song)
        db.session.commit()
        
        for song in songs:
            analysis = AnalysisResult(
                song_id=song.id,
                status='pending'
            )
            analyses.append(analysis)
            db.session.add(analysis)
        db.session.commit()
        
        # Test batch update
        update_data = [
            {
                'id': analysis.id,
                'status': 'completed',
                'score': 85.0 + analysis.id
            }
            for analysis in analyses
        ]
        
        start_time = time.time()
        batch_service = BatchOperationService()
        batch_service.update_analysis_results_batch(update_data)
        batch_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Verify updates
        completed_count = AnalysisResult.query.filter_by(status='completed').count()
        assert completed_count == 5
        assert batch_time < 150, f"Batch update took {batch_time:.1f}ms, should be < 150ms"
    
    def test_batch_vs_individual_performance(self):
        """Compare performance of batch operations vs individual operations."""
        # Test individual operations
        start_time = time.time()
        for i in range(10):
            song = Song(
                spotify_id=f'individual_song_{i}',
                title=f'Individual Song {i}',
                artist='Test Artist'
            )
            db.session.add(song)
            db.session.commit()
        individual_time = (time.time() - start_time) * 1000
        
        # Clear database
        Song.query.delete()
        db.session.commit()
        
        # Test batch operations
        song_data = [
            {
                'spotify_id': f'batch_song_{i}',
                'title': f'Batch Song {i}',
                'artist': 'Test Artist'
            }
            for i in range(10)
        ]
        
        start_time = time.time()
        batch_service = BatchOperationService()
        batch_service.create_songs_batch(song_data)
        batch_time = (time.time() - start_time) * 1000
        
        # Batch should be significantly faster
        improvement_ratio = individual_time / batch_time
        assert improvement_ratio > 2, f"Batch operations should be at least 2x faster. Individual: {individual_time:.1f}ms, Batch: {batch_time:.1f}ms" 