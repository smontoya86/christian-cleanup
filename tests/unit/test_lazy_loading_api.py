"""
Tests for lazy loading API endpoints.
"""
import pytest
import json
from unittest.mock import patch, MagicMock
from app import create_app
from app.models.models import User, Playlist, Song, AnalysisResult
from app.extensions import db


class TestLazyLoadingAPI:
    """Test lazy loading API endpoints."""
    
    @pytest.fixture(autouse=True)
    def setup_app(self):
        """Set up test application and database."""
        self.app = create_app('testing')
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        with self.app.app_context():
            db.drop_all()  # Clean slate
            db.create_all()
            
            # Create test user with unique ID
            from datetime import datetime, timedelta, timezone
            import uuid
            unique_suffix = str(uuid.uuid4())[:8]
            
            self.test_user = User(
                spotify_id=f'test_user_{unique_suffix}',
                display_name='Test User',
                email=f'test_{unique_suffix}@example.com',
                access_token='test_access_token',
                token_expiry=datetime.now(timezone.utc) + timedelta(hours=1)
            )
            db.session.add(self.test_user)
            db.session.flush()  # Get the ID
            
            # Create test playlist
            self.test_playlist = Playlist(
                spotify_id=f'test_playlist_{unique_suffix}',
                name='Test Playlist',
                owner_id=self.test_user.id,
                image_url='http://example.com/image.jpg'
            )
            db.session.add(self.test_playlist)
            db.session.flush()  # Get the ID
            
            # Create test songs
            self.test_songs = [
                Song(
                    spotify_id=f'song_1_{unique_suffix}',
                    title='Test Song 1',
                    artist='Test Artist 1',
                    album='Test Album 1'
                ),
                Song(
                    spotify_id=f'song_2_{unique_suffix}',
                    title='Test Song 2',
                    artist='Test Artist 2',
                    album='Test Album 2'
                ),
                Song(
                    spotify_id=f'song_3_{unique_suffix}',
                    title='Test Song 3',
                    artist='Test Artist 3',
                    album='Test Album 3'
                )
            ]
            for song in self.test_songs:
                db.session.add(song)
            db.session.flush()  # Get the IDs
            
            # Create playlist-song associations
            from app.models.models import PlaylistSong
            for i, song in enumerate(self.test_songs):
                playlist_song = PlaylistSong(
                    playlist_id=self.test_playlist.id,
                    song_id=song.id,
                    track_position=i
                )
                db.session.add(playlist_song)
            
            # Create analysis results for some songs
            self.test_analysis_results = [
                AnalysisResult(
                    song_id=self.test_songs[0].id,
                    score=8.5,
                    concern_level='low',
                    explanation='This is a good Christian song',
                    status='completed'
                ),
                AnalysisResult(
                    song_id=self.test_songs[1].id,
                    score=6.0,
                    concern_level='medium',
                    explanation='Some concerns about lyrics',
                    status='completed'
                )
                # Note: Song 3 has no analysis result (pending)
            ]
            for result in self.test_analysis_results:
                db.session.add(result)
            
            db.session.commit()
            
            # Store IDs for use in tests (to avoid detached instance issues)
            self.test_user_id = self.test_user.id
            self.test_playlist_spotify_id = self.test_playlist.spotify_id
            self.test_song_ids = [song.id for song in self.test_songs]
        
        self.client = self.app.test_client()
        
        yield
        
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        
        self.app_context.pop()
    
    def login_user(self):
        """Helper method to log in test user."""
        with self.client.session_transaction() as sess:
            sess['user_id'] = self.test_user_id
            sess['_user_id'] = str(self.test_user_id)  # Flask-Login uses _user_id
            sess['_fresh'] = True
            sess['spotify_token'] = 'test_token'
    
    def test_playlist_analysis_data_endpoint_success(self):
        """Test successful playlist analysis data retrieval."""
        self.login_user()
        
        response = self.client.get(f'/api/analysis/playlist/{self.test_playlist_spotify_id}')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Verify response structure
        assert 'songs' in data
        assert 'summary' in data
        assert len(data['songs']) == 3
        
        # Verify summary data
        summary = data['summary']
        assert summary['total_songs'] == 3
        assert summary['analyzed_songs'] == 2
        assert summary['pending_analysis'] == 1
        assert summary['average_score'] == 7.25  # (8.5 + 6.0) / 2
        
        # Verify song data
        songs = data['songs']
        
        # First song (analyzed)
        assert songs[0]['id'] == self.test_song_ids[0]
        assert songs[0]['title'] == 'Test Song 1'
        assert songs[0]['status'] == 'analyzed'
        assert songs[0]['score'] == 8.5
        
        # Second song (analyzed)
        assert songs[1]['id'] == self.test_song_ids[1]
        assert songs[1]['title'] == 'Test Song 2'
        assert songs[1]['status'] == 'analyzed'
        assert songs[1]['score'] == 6.0
        
        # Third song (pending)
        assert songs[2]['id'] == self.test_song_ids[2]
        assert songs[2]['title'] == 'Test Song 3'
        assert songs[2]['status'] == 'pending'
        assert 'score' not in songs[2]
    
    def test_playlist_analysis_data_endpoint_unauthorized(self):
        """Test playlist analysis data endpoint without authentication."""
        response = self.client.get(f'/api/analysis/playlist/{self.test_playlist_spotify_id}')
        
        # Flask-Login redirects to login page when not authenticated
        assert response.status_code == 302
        assert 'login' in response.location or response.location == '/'
    
    def test_playlist_analysis_data_endpoint_not_found(self):
        """Test playlist analysis data endpoint with non-existent playlist."""
        self.login_user()
        
        response = self.client.get('/api/analysis/playlist/non_existent_playlist')
        
        assert response.status_code == 404
    
    def test_playlist_analysis_data_endpoint_wrong_user(self):
        """Test playlist analysis data endpoint with wrong user."""
        # Login as different user
        with self.client.session_transaction() as sess:
            sess['user_id'] = 999
            sess['spotify_token'] = 'test_token'
        
        response = self.client.get('/api/analysis/playlist/test_playlist_123')
        
        assert response.status_code == 404
    
    @patch('app.utils.cache.cache.get')
    @patch('app.utils.cache.cache.set')
    def test_playlist_analysis_data_caching(self, mock_cache_set, mock_cache_get):
        """Test that playlist analysis data is cached correctly."""
        self.login_user()
        
        # First request - cache miss
        mock_cache_get.return_value = None
        
        response = self.client.get('/api/analysis/playlist/test_playlist_123')
        
        assert response.status_code == 200
        
        # Verify cache was checked
        expected_cache_key = f'playlist_analysis:{self.test_user.id}:{self.test_playlist.spotify_id}'
        mock_cache_get.assert_called_with(expected_cache_key)
        
        # Verify cache was set
        mock_cache_set.assert_called_once()
        call_args = mock_cache_set.call_args
        assert call_args[0][0] == expected_cache_key
        assert call_args[1]['timeout'] == 300  # 5 minutes
    
    @patch('app.utils.cache.cache.get')
    def test_playlist_analysis_data_cache_hit(self, mock_cache_get):
        """Test that cached playlist analysis data is returned."""
        self.login_user()
        
        # Mock cached data
        cached_data = {
            'songs': [{'id': 1, 'title': 'Cached Song'}],
            'summary': {'total_songs': 1, 'analyzed_songs': 1}
        }
        mock_cache_get.return_value = cached_data
        
        response = self.client.get(f'/api/analysis/playlist/{self.test_playlist.spotify_id}')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Should return cached data
        assert data == cached_data
        
        # Verify cache was checked
        expected_cache_key = f'playlist_analysis:{self.test_user.id}:{self.test_playlist.spotify_id}'
        mock_cache_get.assert_called_with(expected_cache_key)
    
    def test_song_analysis_data_endpoint_success_analyzed(self):
        """Test successful song analysis data retrieval for analyzed song."""
        self.login_user()
        
        response = self.client.get(f'/api/analysis/song/{self.test_songs[0].id}')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Verify response structure
        assert data['id'] == self.test_songs[0].id
        assert data['title'] == 'Test Song 1'
        assert data['artist'] == 'Test Artist 1'
        assert data['album'] == 'Test Album 1'
        assert data['status'] == 'analyzed'
        assert data['score'] == 8.5
        assert 'details' in data
    
    def test_song_analysis_data_endpoint_success_pending(self):
        """Test successful song analysis data retrieval for pending song."""
        self.login_user()
        
        response = self.client.get(f'/api/analysis/song/{self.test_songs[2].id}')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Verify response structure
        assert data['id'] == self.test_songs[2].id
        assert data['title'] == 'Test Song 3'
        assert data['artist'] == 'Test Artist 3'
        assert data['album'] == 'Test Album 3'
        assert data['status'] == 'pending'
        assert 'score' not in data
        assert 'details' not in data
    
    def test_song_analysis_data_endpoint_unauthorized(self):
        """Test song analysis data endpoint without authentication."""
        response = self.client.get(f'/api/analysis/song/{self.test_songs[0].id}')
        
        # Flask-Login redirects to login page when not authenticated
        assert response.status_code == 302
        assert 'login' in response.location or response.location == '/'
    
    def test_song_analysis_data_endpoint_not_found(self):
        """Test song analysis data endpoint with non-existent song."""
        self.login_user()
        
        response = self.client.get('/api/analysis/song/999')
        
        assert response.status_code == 404
    
    def test_song_analysis_data_endpoint_wrong_user(self):
        """Test song analysis data endpoint with wrong user access."""
        # Create song for different user
        with self.app.app_context():
            other_user = User(
                id=2,
                spotify_id='other_user_123',
                display_name='Other User',
                email='other@example.com'
            )
            db.session.add(other_user)
            
            other_playlist = Playlist(
                id=2,
                spotify_id='other_playlist_123',
                name='Other Playlist',
                owner_id=2,
                total_tracks=1
            )
            db.session.add(other_playlist)
            
            other_song = Song(
                id=4,
                spotify_id='other_song',
                title='Other Song',
                artist='Other Artist',
                album='Other Album',
                playlist_id=2
            )
            db.session.add(other_song)
            db.session.commit()
        
        self.login_user()  # Login as original user
        
        response = self.client.get('/api/analysis/song/4')
        
        assert response.status_code == 403
        data = json.loads(response.data)
        assert data['error'] == 'Unauthorized'
    
    @patch('app.utils.cache.cache.get')
    @patch('app.utils.cache.cache.set')
    def test_song_analysis_data_caching(self, mock_cache_set, mock_cache_get):
        """Test that song analysis data is cached correctly."""
        self.login_user()
        
        # First request - cache miss
        mock_cache_get.return_value = None
        
        response = self.client.get(f'/api/analysis/song/{self.test_songs[0].id}')
        
        assert response.status_code == 200
        
        # Verify cache was checked
        expected_cache_key = f'song_analysis:{self.test_user.id}:{self.test_songs[0].id}'
        mock_cache_get.assert_called_with(expected_cache_key)
        
        # Verify cache was set
        mock_cache_set.assert_called_once()
        call_args = mock_cache_set.call_args
        assert call_args[0][0] == expected_cache_key
        assert call_args[1]['timeout'] == 300  # 5 minutes
    
    @patch('app.utils.cache.cache.get')
    def test_song_analysis_data_cache_hit(self, mock_cache_get):
        """Test that cached song analysis data is returned."""
        self.login_user()
        
        # Mock cached data
        cached_data = {
            'id': 1,
            'title': 'Cached Song',
            'status': 'analyzed',
            'score': 9.0
        }
        mock_cache_get.return_value = cached_data
        
        response = self.client.get(f'/api/analysis/song/{self.test_songs[0].id}')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Should return cached data
        assert data == cached_data
        
        # Verify cache was checked
        expected_cache_key = f'song_analysis:{self.test_user.id}:{self.test_songs[0].id}'
        mock_cache_get.assert_called_with(expected_cache_key)
    
    def test_playlist_analysis_data_empty_playlist(self):
        """Test playlist analysis data for empty playlist."""
        self.login_user()
        
        # Create empty playlist
        with self.app.app_context():
            empty_playlist = Playlist(
                id=3,
                spotify_id='empty_playlist_123',
                name='Empty Playlist',
                owner_id=1,
                total_tracks=0
            )
            db.session.add(empty_playlist)
            db.session.commit()
        
        response = self.client.get('/api/analysis/playlist/empty_playlist_123')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Verify response structure
        assert data['songs'] == []
        assert data['summary']['total_songs'] == 0
        assert data['summary']['analyzed_songs'] == 0
        assert data['summary']['pending_analysis'] == 0
        assert data['summary']['average_score'] == 0
    
    def test_playlist_analysis_data_all_pending(self):
        """Test playlist analysis data for playlist with all pending songs."""
        self.login_user()
        
        # Create playlist with pending songs only
        with self.app.app_context():
            pending_playlist = Playlist(
                id=4,
                spotify_id='pending_playlist_123',
                name='Pending Playlist',
                owner_id=1,
                total_tracks=2
            )
            db.session.add(pending_playlist)
            
            pending_songs = [
                Song(
                    id=5,
                    spotify_id='pending_song_1',
                    title='Pending Song 1',
                    artist='Pending Artist 1',
                    album='Pending Album 1',
                    playlist_id=4
                ),
                Song(
                    id=6,
                    spotify_id='pending_song_2',
                    title='Pending Song 2',
                    artist='Pending Artist 2',
                    album='Pending Album 2',
                    playlist_id=4
                )
            ]
            for song in pending_songs:
                db.session.add(song)
            
            db.session.commit()
        
        response = self.client.get('/api/analysis/playlist/pending_playlist_123')
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        # Verify response structure
        assert len(data['songs']) == 2
        assert data['summary']['total_songs'] == 2
        assert data['summary']['analyzed_songs'] == 0
        assert data['summary']['pending_analysis'] == 2
        assert data['summary']['average_score'] == 0
        
        # All songs should be pending
        for song in data['songs']:
            assert song['status'] == 'pending'
            assert 'score' not in song 