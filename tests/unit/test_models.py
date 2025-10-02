"""
Unit tests for database models
"""

from datetime import datetime, timezone

import pytest

from app.models.models import AnalysisResult, LyricsCache, Playlist, Song, User


class TestUserModel:
    """Test User model"""
    
    def test_create_user(self, db_session):
        """Test creating a user"""
        from datetime import datetime, timedelta, timezone
        
        user = User(
            spotify_id='user_test_create_123',
            display_name='Test User',
            email='test_create@example.com',
            access_token='test_token',
            refresh_token='test_refresh',
            token_expiry=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        db_session.add(user)
        db_session.commit()
        
        assert user.id is not None
        assert user.spotify_id == 'user_test_create_123'
        assert user.display_name == 'Test User'
        assert user.email == 'test_create@example.com'
    
    def test_user_playlists_relationship(self, sample_user, sample_playlist):
        """Test user playlists relationship"""
        playlists = list(sample_user.playlists)
        assert len(playlists) == 1
        assert playlists[0] == sample_playlist


class TestSongModel:
    """Test Song model"""
    
    def test_create_song(self, db_session):
        """Test creating a song"""
        song = Song(
            spotify_id='song_test_create_456',
            title='Test Song',
            artist='Test Artist',
            album='Test Album',
            duration_ms=180000
        )
        db_session.add(song)
        db_session.commit()
        
        assert song.id is not None
        assert song.spotify_id == 'song_test_create_456'
        assert song.title == 'Test Song'
        assert song.artist == 'Test Artist'
    
    def test_song_analysis_relationship(self, sample_song, sample_analysis):
        """Test song analysis relationship"""
        assert sample_song.analysis_result is not None
        assert sample_song.analysis_result.score == 75


class TestPlaylistModel:
    """Test Playlist model"""
    
    def test_create_playlist(self, db_session, sample_user):
        """Test creating a playlist"""
        playlist = Playlist(
            spotify_id='playlist_123',
            name='Test Playlist',
            owner_id=sample_user.id,
            spotify_snapshot_id='snapshot_123'
        )
        db_session.add(playlist)
        db_session.commit()
        
        assert playlist.id is not None
        assert playlist.spotify_id == 'playlist_123'
        assert playlist.owner_id == sample_user.id


class TestAnalysisResultModel:
    """Test AnalysisResult model"""
    
    def test_create_analysis(self, db_session, sample_song):
        """Test creating an analysis result"""
        analysis = AnalysisResult(
            song_id=sample_song.id,
            score=80,
            verdict='freely_listen',
            biblical_themes=['worship', 'praise'],
            concerns=[],
            explanation='Excellent Christian content'
        )
        db_session.add(analysis)
        db_session.commit()
        
        assert analysis.id is not None
        assert analysis.song_id == sample_song.id
        assert analysis.score == 80
        assert analysis.verdict == 'freely_listen'
        assert 'worship' in analysis.biblical_themes
    
    def test_analysis_timestamp(self, sample_analysis):
        """Test analysis has timestamp"""
        assert sample_analysis.analyzed_at is not None
        assert isinstance(sample_analysis.analyzed_at, datetime)


class TestLyricsCacheModel:
    """Test LyricsCache model"""
    
    def test_create_cache(self, db_session):
        """Test creating a lyrics cache entry"""
        cache = LyricsCache(
            artist='Test Artist',
            title='Test Song',
            lyrics='Test lyrics content',
            source='test'
        )
        db_session.add(cache)
        db_session.commit()
        
        assert cache.id is not None
        assert cache.artist == 'Test Artist'
        assert cache.title == 'Test Song'
    
    def test_find_cached_lyrics(self, sample_lyrics_cache):
        """Test finding cached lyrics"""
        found = LyricsCache.find_cached_lyrics('John Newton', 'Amazing Grace')
        assert found is not None
        assert found.id == sample_lyrics_cache.id
        assert 'Amazing grace' in found.lyrics
    
    def test_find_cached_lyrics_not_found(self, db_session):
        """Test finding non-existent cached lyrics"""
        found = LyricsCache.find_cached_lyrics('Unknown Artist', 'Unknown Song')
        assert found is None
    
    def test_cache_lyrics(self, db_session):
        """Test caching lyrics"""
        cached = LyricsCache.cache_lyrics(
            artist='New Artist',
            title='New Song',
            lyrics='New lyrics',
            source='test'
        )
        
        assert cached is not None
        assert cached.artist == 'New Artist'
        assert cached.title == 'New Song'
        
        # Verify it can be found
        found = LyricsCache.find_cached_lyrics('New Artist', 'New Song')
        assert found is not None
        assert found.id == cached.id

