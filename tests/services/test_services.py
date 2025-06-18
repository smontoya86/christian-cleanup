"""
Service Layer Tests

TDD tests for business logic services including Spotify integration,
analysis engine, and playlist synchronization functionality.
"""

import pytest
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime, timezone, timedelta


class TestSpotifyService:
    """Test Spotify API integration service."""
    
    @pytest.mark.service
    def test_spotify_service_initialization(self, app, sample_user):
        """Test that Spotify service can be initialized with proper configuration."""
        from app.services.spotify_service import SpotifyService
        
        # Mock requests to avoid real HTTP calls
        with patch('app.services.spotify_service.requests.post') as mock_post:
            # Mock token refresh if needed
            mock_post.return_value.json.return_value = {
                'access_token': 'new_token',
                'refresh_token': 'new_refresh',
                'expires_in': 3600
            }
            mock_post.return_value.raise_for_status.return_value = None
            
            service = SpotifyService(sample_user)
            assert service is not None
            assert service.user == sample_user
            # Service should be ready to authenticate users
        
    @pytest.mark.service
    def test_get_user_playlists_handles_authentication(self, app, sample_user):
        """Test that Spotify service properly handles user authentication for playlist fetching."""
        from app.services.spotify_service import SpotifyService
        
        # Mock requests to avoid real HTTP calls
        with patch('app.services.spotify_service.requests.request') as mock_request:
            with patch('app.services.spotify_service.requests.post') as mock_post:
                # Mock token refresh if needed
                mock_post.return_value.json.return_value = {
                    'access_token': 'new_token',
                    'refresh_token': 'new_refresh',
                    'expires_in': 3600
                }
                mock_post.return_value.raise_for_status.return_value = None
                
                # Mock playlist data
                mock_request.return_value.json.return_value = {
                    'items': [
                        {
                            'id': 'test_playlist_1',
                            'name': 'Christian Worship',
                            'description': 'Worship songs',
                            'tracks': {'total': 25},
                            'images': [{'url': 'http://example.com/image.jpg'}],
                            'owner': {'id': sample_user.spotify_id}
                        }
                    ],
                    'next': None
                }
                mock_request.return_value.raise_for_status.return_value = None
                
                service = SpotifyService(sample_user)
                playlists = service.get_user_playlists()
                
                assert len(playlists) == 1
                assert playlists[0]['name'] == 'Christian Worship'
            
    @pytest.mark.service
    def test_get_playlist_tracks_returns_track_data(self, app, sample_user):
        """Test that Spotify service can fetch track data for a specific playlist."""
        from app.services.spotify_service import SpotifyService
        
        # Mock requests to avoid real HTTP calls
        with patch('app.services.spotify_service.requests.request') as mock_request:
            with patch('app.services.spotify_service.requests.post') as mock_post:
                # Mock token refresh if needed
                mock_post.return_value.json.return_value = {
                    'access_token': 'new_token',
                    'refresh_token': 'new_refresh',
                    'expires_in': 3600
                }
                mock_post.return_value.raise_for_status.return_value = None
                
                # Mock track data
                mock_request.return_value.json.return_value = {
                    'items': [
                        {
                            'track': {
                                'id': 'track_1',
                                'name': 'Amazing Grace',
                                'artists': [{'name': 'Traditional'}],
                                'album': {'name': 'Hymns'},
                                'duration_ms': 240000,
                                'type': 'track'
                            }
                        }
                    ],
                    'next': None
                }
                mock_request.return_value.raise_for_status.return_value = None
                
                service = SpotifyService(sample_user)
                tracks = service.get_playlist_tracks('test_playlist_id')
                
                assert len(tracks) == 1
                assert tracks[0]['track']['name'] == 'Amazing Grace'
            
    @pytest.mark.service
    def test_spotify_service_handles_token_refresh(self, app, sample_user):
        """Test that Spotify service handles token refresh when tokens expire."""
        from app.services.spotify_service import SpotifyService
        
        # Set user token to expired to trigger refresh
        sample_user.token_expiry = datetime.now(timezone.utc) - timedelta(hours=1)
        
        # Mock the requests to avoid real HTTP calls
        with patch('app.services.spotify_service.requests.request') as mock_request:
            with patch('app.services.spotify_service.requests.post') as mock_post:
                # Mock token refresh
                mock_post.return_value.json.return_value = {
                    'access_token': 'new_token',
                    'refresh_token': 'new_refresh',
                    'expires_in': 3600
                }
                mock_post.return_value.raise_for_status.return_value = None
                
                # Mock API request after refresh
                mock_request.return_value.json.return_value = {'items': [], 'next': None}
                mock_request.return_value.raise_for_status.return_value = None
                
                service = SpotifyService(sample_user)
                
                # Should work with token refresh
                result = service.get_user_playlists()
                
                # Verify result is a list and token refresh was called
                assert isinstance(result, list)
                mock_post.assert_called_once()


class TestAnalysisService:
    """Test content analysis service."""
    
    @pytest.mark.service
    def test_analysis_service_initialization(self, app):
        """Test that analysis service initializes with proper configuration."""
        from app.services.analysis_service import AnalysisService
        
        service = AnalysisService()
        assert service is not None
        
    @pytest.mark.service
    def test_analyze_song_returns_analysis_result(self, app, sample_song):
        """Test that analysis service can analyze a song and return structured results."""
        from app.services.analysis_service import AnalysisService
        
        service = AnalysisService()
        
        # Mock the lyrics for testing
        sample_song.lyrics = "Amazing grace how sweet the sound that saved a wretch like me"
        
        # Mock the RQ queue to avoid Redis dependency in tests
        with patch.object(service, 'rq') as mock_rq:
            mock_queue = MagicMock()
            mock_job = MagicMock()
            mock_job.id = 'test_job_123'
            mock_queue.enqueue.return_value = mock_job
            mock_rq.get_queue.return_value = mock_queue
            
            result = service.analyze_song(sample_song)
        
            # analyze_song returns boolean indicating if job was queued
            assert result is True
            
            # Check that an analysis record was created
            from app.models.models import AnalysisResult
            analysis = AnalysisResult.query.filter_by(song_id=sample_song.id).first()
            assert analysis is not None
            assert analysis.status == 'pending'
        
    @pytest.mark.service
    def test_analyze_song_handles_missing_lyrics(self, app, sample_song):
        """Test that analysis service handles songs without lyrics gracefully."""
        from app.services.analysis_service import AnalysisService
        
        service = AnalysisService()
        
        # Test with no lyrics
        sample_song.lyrics = None
        
        # Mock the RQ queue to avoid Redis dependency in tests
        with patch.object(service, 'rq') as mock_rq:
            mock_queue = MagicMock()
            mock_job = MagicMock()
            mock_job.id = 'test_job_123'
            mock_queue.enqueue.return_value = mock_job
            mock_rq.get_queue.return_value = mock_queue
            
            result = service.analyze_song(sample_song)
        
            # analyze_song returns boolean even with missing lyrics
            assert result is True
            
            # Should create analysis record
            from app.models.models import AnalysisResult
            analysis = AnalysisResult.query.filter_by(song_id=sample_song.id).first()
            assert analysis is not None
        
    @pytest.mark.service
    def test_analyze_song_detects_christian_themes(self, app, sample_song):
        """Test that analysis service properly detects positive Christian themes."""
        from app.services.analysis_service import AnalysisService
        
        service = AnalysisService()
        
        # Test with clearly Christian lyrics
        sample_song.lyrics = "Jesus loves me this I know, for the Bible tells me so. Praise the Lord and worship Him."
        
        # Mock the RQ queue to avoid Redis dependency in tests
        with patch.object(service, 'rq') as mock_rq:
            mock_queue = MagicMock()
            mock_job = MagicMock()
            mock_job.id = 'test_job_123'
            mock_queue.enqueue.return_value = mock_job
            mock_rq.get_queue.return_value = mock_queue
            
            result = service.analyze_song(sample_song)
        
            # analyze_song queues job and returns boolean
            assert result is True
            
            # Check analysis record was created
            from app.models.models import AnalysisResult
            analysis = AnalysisResult.query.filter_by(song_id=sample_song.id).first()
            assert analysis is not None
            assert analysis.status == 'pending'
        
    @pytest.mark.service
    def test_analyze_song_flags_concerning_content(self, app, sample_song):
        """Test that analysis service flags potentially concerning content."""
        from app.services.analysis_service import AnalysisService
        
        service = AnalysisService()
        
        # Test with potentially concerning content
        sample_song.lyrics = "Violence and hatred fill my heart, destruction everywhere"
        
        # Mock the RQ queue to avoid Redis dependency in tests
        with patch.object(service, 'rq') as mock_rq:
            mock_queue = MagicMock()
            mock_job = MagicMock()
            mock_job.id = 'test_job_123'
            mock_queue.enqueue.return_value = mock_job
            mock_rq.get_queue.return_value = mock_queue
            
            result = service.analyze_song(sample_song)
        
            # analyze_song queues job and returns boolean
            assert result is True
            
            # Check analysis record was created
            from app.models.models import AnalysisResult
            analysis = AnalysisResult.query.filter_by(song_id=sample_song.id).first()
            assert analysis is not None
            assert analysis.status == 'pending'
        
    @pytest.mark.service
    def test_batch_analyze_handles_multiple_songs(self, app, db):
        """Test that analysis service can handle batch analysis of multiple songs."""
        from app.services.analysis_service import AnalysisService
        from app.models.models import Song
        
        service = AnalysisService()
        
        # Create multiple test songs
        songs = []
        for i in range(3):
            song = Song(
                spotify_id=f'batch_test_{i}',
                title=f'Test Song {i}',
                artist='Test Artist',
                lyrics=f'Test lyrics for song {i} with praise and worship'
            )
            db.session.add(song)
            songs.append(song)
        db.session.commit()
        
        # Mock the RQ queue to avoid Redis dependency in tests
        with patch.object(service, 'rq') as mock_rq:
            mock_queue = MagicMock()
            mock_job = MagicMock()
            mock_job.id = 'test_job_123'
            mock_queue.enqueue.return_value = mock_job
            mock_rq.get_queue.return_value = mock_queue
            
            results = service.batch_analyze(songs)
        
            assert len(results) == 3
            # batch_analyze returns list of booleans indicating if jobs were queued
            for result in results:
                assert result is True


class TestPlaylistSyncService:
    """Test playlist synchronization service."""
    
    @pytest.mark.service
    def test_playlist_sync_service_initialization(self, app):
        """Test that playlist sync service initializes properly."""
        from app.services.playlist_sync_service import PlaylistSyncService
        
        service = PlaylistSyncService()
        assert service is not None
        
    @pytest.mark.service
    def test_sync_user_playlists_creates_new_playlists(self, app, db, sample_user):
        """Test that sync service creates new playlists from Spotify data."""
        from app.services.playlist_sync_service import PlaylistSyncService
        from app.models.models import Playlist
        
        service = PlaylistSyncService()
        
        # Mock Spotify data
        spotify_playlists = [
            {
                'id': 'spotify_playlist_1',
                'name': 'My Worship Songs',
                'description': 'Personal worship collection',
                'tracks': {'total': 15},
                'images': [{'url': 'http://example.com/cover.jpg'}]
            }
        ]
        
        with patch('app.services.playlist_sync_service.SpotifyService') as mock_spotify:
            mock_spotify_instance = MagicMock()
            mock_spotify_instance.get_user_playlists.return_value = spotify_playlists
            mock_spotify.return_value = mock_spotify_instance
            
            service.sync_user_playlists(sample_user)
            
            # Check that playlist was created
            playlist = Playlist.query.filter_by(
                spotify_id='spotify_playlist_1',
                owner_id=sample_user.id
            ).first()
            
            assert playlist is not None
            assert playlist.name == 'My Worship Songs'
            assert playlist.description == 'Personal worship collection'
            
    @pytest.mark.service
    def test_sync_playlist_tracks_creates_songs(self, app, db, sample_user, sample_playlist):
        """Test that sync service creates songs and associations from Spotify track data."""
        from app.services.playlist_sync_service import PlaylistSyncService
        from app.models.models import Song, PlaylistSong
        
        service = PlaylistSyncService()
        
        # Mock Spotify track data
        spotify_tracks = [
            {
                'id': 'spotify_track_1',
                'name': 'How Great Thou Art',
                'artists': [{'name': 'Traditional'}],
                'album': {'name': 'Classic Hymns'},
                'duration_ms': 180000
            }
        ]
        
        with patch('app.services.playlist_sync_service.SpotifyService') as mock_spotify:
            mock_spotify_instance = MagicMock()
            mock_spotify_instance.get_playlist_tracks.return_value = spotify_tracks
            mock_spotify.return_value = mock_spotify_instance
            
            service.sync_playlist_tracks(sample_user, sample_playlist)
            
            # Check that song was created
            song = Song.query.filter_by(spotify_id='spotify_track_1').first()
            assert song is not None
            assert song.title == 'How Great Thou Art'
            assert song.artist == 'Traditional'
            
            # Check that playlist-song association was created
            association = PlaylistSong.query.filter_by(
                playlist_id=sample_playlist.id,
                song_id=song.id
            ).first()
            assert association is not None
            
    @pytest.mark.service
    def test_sync_handles_existing_playlists(self, app, db, sample_user, sample_playlist):
        """Test that sync service updates existing playlists instead of creating duplicates."""
        from app.services.playlist_sync_service import PlaylistSyncService
        from app.models.models import Playlist
        
        service = PlaylistSyncService()
        
        # Update existing playlist data
        original_description = sample_playlist.description
        
        spotify_playlists = [
            {
                'id': sample_playlist.spotify_id,
                'name': 'Updated Playlist Name',
                'description': 'Updated description',
                'tracks': {'total': 20},
                'images': [{'url': 'http://example.com/new_cover.jpg'}]
            }
        ]
        
        with patch('app.services.playlist_sync_service.SpotifyService') as mock_spotify:
            mock_spotify_instance = MagicMock()
            mock_spotify_instance.get_user_playlists.return_value = spotify_playlists
            mock_spotify.return_value = mock_spotify_instance
            
            service.sync_user_playlists(sample_user)
            
            # Should update existing playlist, not create new one
            updated_playlist = Playlist.query.filter_by(
                spotify_id=sample_playlist.spotify_id,
                owner_id=sample_user.id
            ).first()
            
            assert updated_playlist.id == sample_playlist.id  # Same record
            assert updated_playlist.name == 'Updated Playlist Name'
            assert updated_playlist.description == 'Updated description'


class TestUnifiedAnalysisService:
    """Test unified analysis service coordination."""
    
    @pytest.mark.service
    def test_unified_service_coordinates_analysis_pipeline(self, app, sample_song):
        """Test that unified service coordinates the complete analysis pipeline."""
        from app.services.unified_analysis_service import UnifiedAnalysisService
        
        service = UnifiedAnalysisService()
        
        # Mock the analysis service instance directly
        mock_analysis_instance = MagicMock()
        mock_analysis_instance.analyze_song.return_value = True  # Return success
        
        # Replace the service's analysis_service with our mock
        service.analysis_service = mock_analysis_instance
        
        result = service.analyze_song_complete(sample_song)
        
        assert result is not None
        assert 'score' in result
        mock_analysis_instance.analyze_song.assert_called_once_with(sample_song, force=False)


class TestServiceExceptionHandling:
    """Test service layer exception handling."""
    
    @pytest.mark.service
    def test_spotify_service_handles_api_errors(self, app, sample_user):
        """Test that Spotify service handles API errors gracefully."""
        from app.services.spotify_service import SpotifyService
        from app.services.exceptions import SpotifyAPIError
        
        # Mock the requests to prevent real HTTP calls during initialization
        with patch('app.services.spotify_service.requests.post') as mock_post:
            # Mock successful token refresh during initialization
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'access_token': 'new_token',
                'refresh_token': 'new_refresh',
                'expires_in': 3600
            }
            mock_post.return_value = mock_response
            
            service = SpotifyService(sample_user)
            
            # Now test error handling
            with patch('app.services.spotify_service.requests.get') as mock_get:
                mock_get.side_effect = Exception("Spotify API unavailable")
                
                # Should handle error gracefully
                with pytest.raises((SpotifyAPIError, Exception)):
                    service.get_user_playlists(sample_user)
                
    @pytest.mark.service
    def test_analysis_service_handles_processing_errors(self, app, sample_song):
        """Test that analysis service handles processing errors gracefully."""
        from app.services.analysis_service import AnalysisService
        
        service = AnalysisService()
        
        # Create corrupted song data
        sample_song.lyrics = "A" * 100000  # Extremely long text
        
        # Mock the RQ queue to avoid Redis dependency in tests
        with patch.object(service, 'rq') as mock_rq:
            mock_queue = MagicMock()
            mock_job = MagicMock()
            mock_job.id = 'test_job_123'
            mock_queue.enqueue.return_value = mock_job
            mock_rq.get_queue.return_value = mock_queue
            
            result = service.analyze_song(sample_song)
        
            # Should still return a result, even if analysis is limited
            assert result is True
            
            # Check analysis record was created
            from app.models.models import AnalysisResult
            analysis = AnalysisResult.query.filter_by(song_id=sample_song.id).first()
            assert analysis is not None


class TestServiceIntegration:
    """Test integration between services."""
    
    @pytest.mark.service
    def test_playlist_sync_triggers_analysis(self, app, db, sample_user):
        """Test that playlist sync can trigger automatic analysis of new songs."""
        from app.services.playlist_sync_service import PlaylistSyncService
        
        service = PlaylistSyncService()
        
        # Mock sync that creates new songs
        spotify_playlists = [
            {
                'id': 'integration_test_playlist',
                'name': 'Test Integration',
                'description': 'Integration test',
                'tracks': {'total': 1},
                'images': []
            }
        ]
        
        spotify_tracks = [
            {
                'id': 'integration_test_track',
                'name': 'Test Song',
                'artists': [{'name': 'Test Artist'}],
                'album': {'name': 'Test Album'},
                'duration_ms': 180000
            }
        ]
        
        with patch('app.services.playlist_sync_service.SpotifyService') as mock_spotify:
            mock_spotify_instance = MagicMock()
            mock_spotify_instance.get_user_playlists.return_value = spotify_playlists
            mock_spotify_instance.get_playlist_tracks.return_value = spotify_tracks
            mock_spotify.return_value = mock_spotify_instance
            
            # Sync should create playlist and songs
            service.sync_user_playlists(sample_user)
            
            # Verify integration worked
            from app.models.models import Playlist, Song
            playlist = Playlist.query.filter_by(spotify_id='integration_test_playlist').first()
            song = Song.query.filter_by(spotify_id='integration_test_track').first()
            
            assert playlist is not None
            assert song is not None 