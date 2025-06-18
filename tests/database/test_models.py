"""
Database Models Tests

TDD tests for database models, relationships, and schema integrity.
These tests define the expected behavior for our simplified database structure.
"""

import pytest
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone
from flask import current_app


class TestUserModel:
    """Test User model functionality and relationships."""
    
    @pytest.mark.database
    def test_user_creation(self, app, db):
        """Test that users can be created with required fields."""
        from app.models.models import User
        
        user = User(
            spotify_id='test_user_123',
            display_name='Test User',
            email='test@example.com',
            access_token='test_token',
            refresh_token='refresh_token',
            token_expiry=datetime(2024, 12, 31, tzinfo=timezone.utc)
        )
        
        db.session.add(user)
        db.session.commit()
        
        assert user.id is not None
        assert user.spotify_id == 'test_user_123'
        assert user.display_name == 'Test User'
        assert user.email == 'test@example.com'
        assert user.created_at is not None
        
    @pytest.mark.database
    def test_user_spotify_id_unique(self, app, db):
        """Test that spotify_id must be unique."""
        from app.models.models import User
        
        # Create first user
        user1 = User(
            spotify_id='duplicate_id',
            display_name='User 1',
            email='user1@example.com',
            access_token='token1',
            refresh_token='refresh1',
            token_expiry=datetime(2024, 12, 31, tzinfo=timezone.utc)
        )
        db.session.add(user1)
        db.session.commit()
        
        # Try to create second user with same spotify_id
        user2 = User(
            spotify_id='duplicate_id',  # Duplicate!
            display_name='User 2',
            email='user2@example.com',
            access_token='token2',
            refresh_token='refresh2',
            token_expiry=datetime(2024, 12, 31, tzinfo=timezone.utc)
        )
        db.session.add(user2)
        
        with pytest.raises(IntegrityError):
            db.session.commit()
            
    @pytest.mark.database
    def test_user_playlists_relationship(self, app, db):
        """Test User -> Playlists relationship."""
        from app.models.models import User, Playlist
        
        user = User(
            spotify_id='test_user',
            display_name='Test User',
            email='test@example.com',
            access_token='token',
            refresh_token='refresh',
            token_expiry=datetime(2024, 12, 31, tzinfo=timezone.utc)
        )
        db.session.add(user)
        db.session.flush()  # Get user.id without committing
        
        playlist = Playlist(
            spotify_id='test_playlist',
            name='Test Playlist',
            owner_id=user.id
        )
        db.session.add(playlist)
        db.session.commit()
        
        assert user.playlists.count() == 1
        assert user.playlists.first().name == 'Test Playlist'
        assert playlist.owner == user


class TestPlaylistModel:
    """Test Playlist model functionality and relationships."""
    
    @pytest.mark.database
    def test_playlist_creation(self, app, db, sample_user):
        """Test that playlists can be created with required fields."""
        from app.models.models import Playlist
        
        playlist = Playlist(
            spotify_id='test_playlist_123',
            name='My Christian Playlist',
            owner_id=sample_user.id,
            description='A collection of Christian music'
        )
        
        db.session.add(playlist)
        db.session.commit()
        
        assert playlist.id is not None
        assert playlist.spotify_id == 'test_playlist_123'
        assert playlist.name == 'My Christian Playlist'
        assert playlist.owner_id == sample_user.id
        assert playlist.description == 'A collection of Christian music'
        assert playlist.created_at is not None
        
    @pytest.mark.database
    def test_playlist_songs_relationship(self, app, db, sample_user):
        """Test Playlist -> Songs many-to-many relationship."""
        from app.models.models import Playlist, Song
        
        playlist = Playlist(
            spotify_id='test_playlist',
            name='Test Playlist',
            owner_id=sample_user.id
        )
        db.session.add(playlist)
        db.session.flush()
        
        song = Song(
            spotify_id='test_song',
            title='Amazing Grace',
            artist='Traditional',
            album='Hymns Collection'
        )
        db.session.add(song)
        db.session.flush()
        
        # Add song to playlist using the association model
        from app.models.models import PlaylistSong
        playlist_song = PlaylistSong(
            playlist_id=playlist.id,
            song_id=song.id,
            track_position=0
        )
        db.session.add(playlist_song)
        db.session.commit()
        
        assert len(playlist.songs) == 1
        assert playlist.songs[0].title == 'Amazing Grace'
        assert song.id in [s.id for s in playlist.songs]


class TestSongModel:
    """Test Song model functionality and relationships."""
    
    @pytest.mark.database
    def test_song_creation(self, app, db):
        """Test that songs can be created with required fields."""
        from app.models.models import Song
        
        song = Song(
            spotify_id='test_song_123',
            title='How Great Thou Art',
            artist='Various Artists',
            album='Christian Classics',
            duration_ms=240000
        )
        
        db.session.add(song)
        db.session.commit()
        
        assert song.id is not None
        assert song.spotify_id == 'test_song_123'
        assert song.title == 'How Great Thou Art'
        assert song.artist == 'Various Artists'
        assert song.album == 'Christian Classics'
        assert song.duration_ms == 240000
        assert song.created_at is not None
        
    @pytest.mark.database
    def test_song_analysis_relationship(self, app, db):
        """Test Song -> AnalysisResult relationship."""
        from app.models.models import Song, AnalysisResult
        
        song = Song(
            spotify_id='test_song',
            title='Blessed Assurance',
            artist='Fanny Crosby',
            album='Hymns'
        )
        db.session.add(song)
        db.session.flush()
        
        analysis = AnalysisResult(
            song_id=song.id,
            status='completed',
            score=95,
            concern_level='low',
            themes=['worship', 'praise'],
            explanation='Strong Christian themes about assurance and faith.'
        )
        db.session.add(analysis)
        db.session.commit()
        
        assert song.analysis_results.count() == 1
        assert song.analysis_results.first().score == 95
        assert analysis.song_rel == song


class TestAnalysisResultModel:
    """Test AnalysisResult model functionality."""
    
    @pytest.mark.database
    def test_analysis_result_creation(self, app, db, sample_song):
        """Test that analysis results can be created with required fields."""
        from app.models.models import AnalysisResult
        
        analysis = AnalysisResult(
            song_id=sample_song.id,
            status='completed',
            score=85,
            concern_level='medium',
            themes=['faith', 'hope'],
            explanation='Song contains positive Christian themes with minor concerns.'
        )
        
        db.session.add(analysis)
        db.session.commit()
        
        assert analysis.id is not None
        assert analysis.song_id == sample_song.id
        assert analysis.status == 'completed'
        assert analysis.score == 85
        assert analysis.concern_level == 'medium'
        assert analysis.themes == ['faith', 'hope']
        assert analysis.explanation == 'Song contains positive Christian themes with minor concerns.'
        assert analysis.explanation.startswith('Song contains positive')
        assert analysis.created_at is not None
        
    @pytest.mark.database
    def test_analysis_result_latest_for_song(self, app, db, sample_song):
        """Test getting the latest analysis result for a song."""
        from app.models.models import AnalysisResult
        
        # Create older analysis
        old_analysis = AnalysisResult(
            song_id=sample_song.id,
            status='completed',
            score=80,
            concern_level='medium',
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc)
        )
        db.session.add(old_analysis)
        
        # Create newer analysis
        new_analysis = AnalysisResult(
            song_id=sample_song.id,
            status='completed',
            score=90,
            concern_level='low',
            created_at=datetime(2024, 2, 1, tzinfo=timezone.utc)
        )
        db.session.add(new_analysis)
        db.session.commit()
        
        # Test that we can get the latest one
        latest = AnalysisResult.query.filter_by(song_id=sample_song.id)\
                                   .order_by(AnalysisResult.created_at.desc())\
                                   .first()
        
        assert latest.score == 90
        assert latest.concern_level == 'low'


class TestWhitelistModel:
    """Test Whitelist model functionality."""
    
    @pytest.mark.database
    def test_whitelist_creation(self, app, db, sample_user, sample_song):
        """Test that whitelist entries can be created."""
        from app.models.models import Whitelist
        
        entry = Whitelist(
            user_id=sample_user.id,
            spotify_id=sample_song.spotify_id,
            item_type='song',
            reason='Excellent Christian message about salvation',
            name='Amazing Grace Entry'
        )
        
        db.session.add(entry)
        db.session.commit()
        
        assert entry.id is not None
        assert entry.user_id == sample_user.id
        assert entry.spotify_id == sample_song.spotify_id
        assert entry.item_type == 'song'
        assert entry.reason == 'Excellent Christian message about salvation'
        assert entry.name == 'Amazing Grace Entry'
        assert entry.added_date is not None
        
    @pytest.mark.database
    def test_whitelist_unique_constraint(self, app, db, sample_user, sample_song):
        """Test that user can't whitelist the same song twice."""
        from app.models.models import Whitelist
        
        # Create first whitelist entry
        entry1 = Whitelist(
            user_id=sample_user.id,
            spotify_id=sample_song.spotify_id,
            item_type='song',
            reason='First entry'
        )
        db.session.add(entry1)
        db.session.commit()
        
        # Try to create duplicate entry
        entry2 = Whitelist(
            user_id=sample_user.id,
            spotify_id=sample_song.spotify_id,  # Same song!
            item_type='song',
            reason='Duplicate entry'
        )
        db.session.add(entry2)
        
        with pytest.raises(IntegrityError):
            db.session.commit()


class TestDatabaseIntegrity:
    """Test database integrity and constraints."""
    
    @pytest.mark.database
    def test_foreign_key_constraints(self, app, db):
        """Test that foreign key constraints are enforced."""
        from app.models.models import Playlist
        from sqlalchemy import text
        
        # Enable foreign key constraints for SQLite
        db.session.execute(text('PRAGMA foreign_keys=ON'))
        
        # Try to create playlist with invalid user_id
        invalid_playlist = Playlist(
            spotify_id='test_playlist',
            name='Invalid Playlist',
            owner_id=99999  # Non-existent user
        )
        db.session.add(invalid_playlist)
        
        with pytest.raises(IntegrityError):
            db.session.commit()
            
    @pytest.mark.database
    def test_database_tables_exist(self, app, db):
        """Test that all expected tables exist in the database."""
        from sqlalchemy import inspect
        
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        expected_tables = ['users', 'playlists', 'songs', 'playlist_songs', 
                          'analysis_results', 'whitelist', 'blacklist', 
                          'lyrics_cache', 'bible_verses', 'playlist_snapshots']
        
        for table in expected_tables:
            assert table in tables, f"Table '{table}' should exist in database"
            
    @pytest.mark.database
    def test_database_indexes_exist(self, app, db):
        """Test that important indexes exist for performance."""
        from sqlalchemy import inspect
        
        inspector = inspect(db.engine)
        
        # Check users table unique constraints (which create implicit indexes)
        user_unique_constraints = inspector.get_unique_constraints('users')
        user_unique_columns = [constraint['column_names'] for constraint in user_unique_constraints]
        
        # In SQLite, unique constraints create implicit indexes
        # We should have a unique constraint on spotify_id
        spotify_id_unique = any('spotify_id' in columns for columns in user_unique_columns)
        assert spotify_id_unique or any('spotify_id' in idx['column_names'] 
                                       for idx in inspector.get_indexes('users')), \
               "Users should have unique constraint or index on spotify_id"
        
        # Check songs table unique constraints
        song_unique_constraints = inspector.get_unique_constraints('songs')
        song_unique_columns = [constraint['column_names'] for constraint in song_unique_constraints]
        
        spotify_id_unique_songs = any('spotify_id' in columns for columns in song_unique_columns)
        assert spotify_id_unique_songs or any('spotify_id' in idx['column_names'] 
                                             for idx in inspector.get_indexes('songs')), \
               "Songs should have unique constraint or index on spotify_id" 