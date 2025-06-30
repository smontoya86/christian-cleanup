"""
Database models for the Christian Music Curation application.

This module defines the SQLAlchemy models for the application, including:
- User: Spotify users with authentication tokens
- Playlist: Spotify playlists with sync and analysis data
- Song: Individual tracks with lyrics and analysis
- PlaylistSong: Association table for playlist-song relationships
- AnalysisResult: Christian content analysis results
- Whitelist/Blacklist: User-defined content filters
- LyricsCache: Cached lyrics from external APIs
- BibleVerse: Biblical references for theme analysis
"""

from datetime import datetime, timedelta, timezone
from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.declarative import declarative_base
from ..extensions import db
from sqlalchemy.orm import relationship
from sqlalchemy import CheckConstraint
from flask import current_app, session
from spotipy.oauth2 import SpotifyOAuth
import requests
import os
import json
import secrets
import time

class User(UserMixin, db.Model):
    """
    User model representing authenticated Spotify users in the Christian Cleanup application.
    
    This model stores user authentication information, Spotify tokens, and manages
    token refresh functionality. It integrates with Flask-Login for session management
    and maintains relationships with playlists, whitelists, and blacklists.
    
    Security Features:
    - Encrypted token storage using Fernet encryption
    - Automatic session timeout management
    - Secure token refresh with replay protection
    - Session fingerprinting for additional security
    
    Attributes:
        id (int): Primary key for the user.
        spotify_id (str): Unique Spotify user identifier.
        email (str): User's email address from Spotify (optional).
        display_name (str): User's display name from Spotify (optional).
        access_token (str): Encrypted Spotify API access token.
        refresh_token (str): Encrypted Spotify API refresh token for token renewal.
        token_expiry (datetime): When the current access token expires.
        session_fingerprint (str): Unique fingerprint for session validation.
        last_activity (datetime): When the user was last active.
        session_timeout (int): Session timeout in seconds (default: 8 hours).
        failed_refresh_attempts (int): Counter for failed token refresh attempts.
        created_at (datetime): When the user record was created.
        updated_at (datetime): When the user record was last updated.
        is_admin (bool): Whether the user has administrative privileges.
        
    Relationships:
        playlists: Dynamic relationship to user's playlists.
        whitelisted_artists: Dynamic relationship to user's whitelist entries.
        blacklisted_items: Dynamic relationship to user's blacklist entries.
        
    Examples:
        Creating a new user:
            >>> user = User(
            ...     spotify_id='spotify123',
            ...     email='user@example.com',
            ...     access_token='token123',
            ...     token_expiry=datetime.now(timezone.utc) + timedelta(hours=1)
            ... )
            >>> db.session.add(user)
            >>> db.session.commit()
        
        Checking token validity:
            >>> if user.ensure_token_valid():
            ...     # Token is valid, proceed with API calls
            ...     pass
    """
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    spotify_id = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=True) 
    display_name = db.Column(db.String(255), nullable=True)
    access_token = db.Column(db.String(1024), nullable=False)  # Increased size for encrypted tokens
    refresh_token = db.Column(db.String(1024), nullable=True)  # Increased size for encrypted tokens
    token_expiry = db.Column(db.DateTime, nullable=False)
    
    # Removed enhanced security fields to match simplified database schema
    
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Admin flag
    is_admin = db.Column(db.Boolean, default=False, nullable=False)

    # Relationships
    playlists = db.relationship('Playlist', back_populates='owner', lazy='dynamic', cascade="all, delete-orphan")
    whitelisted_artists = db.relationship('Whitelist', backref='user', lazy='dynamic', foreign_keys='Whitelist.user_id', cascade="all, delete-orphan")
    blacklisted_items = db.relationship('Blacklist', backref='user_blacklisting', lazy='dynamic', foreign_keys='Blacklist.user_id', cascade="all, delete-orphan")

    def __repr__(self):
        """String representation of the User."""
        return f'<User {self.email}>'

    # Simplified token handling (removed encryption for simplified app)

    def set_access_token(self, token: str) -> None:
        """Set the access token (simplified - no encryption)."""
        self.access_token = token

    def get_access_token(self) -> str:
        """Get the access token (simplified - no decryption)."""
        return self.access_token

    def set_refresh_token(self, token: str) -> None:
        """Set the refresh token (simplified - no encryption)."""
        self.refresh_token = token

    def get_refresh_token(self) -> str:
        """Get the refresh token (simplified - no decryption)."""
        return self.refresh_token

    def clear_session(self) -> None:
        """Clear session data for secure logout - simplified version."""
        # Simplified session clearing - just clear tokens
        self.access_token = None
        self.refresh_token = None
        
        # Let Flask-Login handle session clearing
        current_app.logger.debug(f"Session data cleared for user {self.id}")

    @property
    def is_token_expired(self):
        """Check if the access token has expired."""
        if not self.token_expiry:
            return True
        
        now = datetime.now(timezone.utc)
        
        # Handle both timezone-aware and timezone-naive datetime objects
        if self.token_expiry.tzinfo is None:
            # token_expiry is timezone-naive, convert now to naive for comparison
            now = now.replace(tzinfo=None)
        
        return now >= self.token_expiry

    def ensure_token_valid(self):
        """Pure token validation check - no side effects (Manus recommendation)."""
        return not self.is_token_expired

    def refresh_access_token(self):
        """Refresh the access token using the refresh token - simplified version."""
        refresh_token = self.get_refresh_token()
        if not refresh_token:
            current_app.logger.warning(f"No refresh token available for user {self.id}")
            return False

        token_url = "https://accounts.spotify.com/api/token"
        client_id = current_app.config.get('SPOTIFY_CLIENT_ID')
        client_secret = current_app.config.get('SPOTIFY_CLIENT_SECRET')

        if not client_id or not client_secret:
            current_app.logger.error("Spotify client credentials not configured")
            return False

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
        }

        data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': client_id,
            'client_secret': client_secret,
        }

        try:
            response = requests.post(token_url, headers=headers, data=data, timeout=10)
            response.raise_for_status()
            token_info = response.json()

            # Set new encrypted tokens
            self.set_access_token(token_info['access_token'])
            self.token_expiry = datetime.now(timezone.utc) + timedelta(seconds=token_info['expires_in'])

            if 'refresh_token' in token_info:
                self.set_refresh_token(token_info['refresh_token'])

            db.session.commit()
            
            current_app.logger.info(f"Successfully refreshed token for user {self.id}")
            return True

        except requests.RequestException as e:
            current_app.logger.error(f"Failed to refresh token for user {self.id}: {e}")
            
            # Just rollback on failure - don't attempt commit
            db.session.rollback()
            
            return False

class PlaylistSong(db.Model):
    """
    Association model for the many-to-many relationship between Playlists and Songs.
    
    This model represents the junction table that connects playlists and songs,
    storing additional metadata about the relationship such as track position,
    when the song was added to Spotify, and who added it. This enables detailed
    playlist synchronization and track ordering capabilities.
    
    Attributes:
        playlist_id (int): Foreign key referencing the playlist.
        song_id (int): Foreign key referencing the song.
        track_position (int): Zero-indexed position of the track in the playlist (Spotify convention).
        added_at_spotify (datetime, optional): When the song was added to the playlist on Spotify.
        added_by_spotify_user_id (str, optional): Spotify user ID of who added the track.
        
    Relationships:
        playlist: Back reference to the associated Playlist object.
        song: Back reference to the associated Song object.
        
    Examples:
        Adding a song to a playlist:
            >>> playlist_song = PlaylistSong(
            ...     playlist_id=1,
            ...     song_id=5,
            ...     track_position=0,
            ...     added_at_spotify=datetime.now(timezone.utc),
            ...     added_by_spotify_user_id='spotify123'
            ... )
            >>> db.session.add(playlist_song)
            >>> db.session.commit()
            
        Querying songs in a playlist by position:
            >>> track = PlaylistSong.query.filter_by(
            ...     playlist_id=1,
            ...     track_position=0
            ... ).first()
    """
    __tablename__ = 'playlist_songs'
    playlist_id = db.Column(db.Integer, db.ForeignKey('playlists.id'), primary_key=True)
    song_id = db.Column(db.Integer, db.ForeignKey('songs.id'), primary_key=True)
    track_position = db.Column(db.Integer, nullable=False) # Spotify's 0-indexed position
    added_at_spotify = db.Column(db.DateTime, nullable=True) # Timestamp from Spotify
    added_by_spotify_user_id = db.Column(db.String(255), nullable=True) # Spotify user ID of adder

    playlist = db.relationship('Playlist', back_populates='song_associations')
    song = db.relationship('Song', back_populates='playlist_associations')
    
    # Performance indexes
    __table_args__ = (
        db.Index('idx_playlist_songs_playlist_id', 'playlist_id'),
        db.Index('idx_playlist_songs_song_id', 'song_id'),
        db.Index('idx_playlist_songs_track_position', 'playlist_id', 'track_position'),
    )

    def __repr__(self):
        """
        Return a string representation of the PlaylistSong association.
        
        Returns:
            str: String representation showing playlist ID, song ID, and track position.
            
        Examples:
            >>> ps = PlaylistSong(playlist_id=1, song_id=5, track_position=0)
            >>> # Expected output: <PlaylistSong playlist_id=1 song_id=5 position=0>
            >>> repr(ps)
        """
        return f'<PlaylistSong playlist_id={self.playlist_id} song_id={self.song_id} position={self.track_position}>'

class Playlist(db.Model):
    """
    Model representing a Spotify playlist in the Christian Music Curation application.
    
    This model stores playlist metadata, tracks synchronization status with Spotify,
    and maintains analysis results. Each playlist belongs to a user and contains
    multiple songs through the PlaylistSong association table. The model supports
    bi-directional synchronization with Spotify using snapshot IDs for change detection.
    
    Attributes:
        id (int): Primary key for the playlist.
        spotify_id (str): Unique Spotify playlist identifier.
        name (str): Display name of the playlist.
        description (str, optional): Playlist description from Spotify.
        owner_id (int): Foreign key referencing the owning user.
        spotify_snapshot_id (str, optional): Spotify snapshot ID for change detection.
        image_url (str, optional): URL to the playlist cover image.
        track_count (int, optional): Total number of tracks in the playlist.
        total_tracks (int, optional): Alternative field name for total tracks (used in some routes/tests)
        last_analyzed (datetime, optional): When the playlist was last analyzed for content.
        overall_alignment_score (float, optional): Aggregated Christian alignment score (0-100).
        last_synced_from_spotify (datetime, optional): When playlist was last synced from Spotify.
        created_at (datetime): When the playlist record was created.
        updated_at (datetime): When the playlist record was last updated.
        
    Relationships:
        owner: Back reference to the User who owns this playlist.
        song_associations: Collection of PlaylistSong associations for track management.
        snapshots: Collection of PlaylistSnapshot associations for snapshot management.
        
    Examples:
        Creating a new playlist:
            >>> playlist = Playlist(
            ...     spotify_id='37i9dQZF1DX0XUsuxWHRQd',
            ...     name='Christian Worship',
            ...     owner_id=1,
            ...     spotify_snapshot_id='abc123'
            ... )
            >>> db.session.add(playlist)
            >>> db.session.commit()
            
        Getting songs in order:
            >>> songs = playlist.songs  # Returns songs ordered by track_position
            
        Checking analysis score:
            >>> score = playlist.score  # Returns normalized score (0-1)
    """
    __tablename__ = 'playlists'
    id = db.Column(db.Integer, primary_key=True)
    spotify_id = db.Column(db.String(255), unique=True, nullable=False) # This is the correct field for Spotify Playlist ID
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    spotify_snapshot_id = db.Column(db.String(255), nullable=True) # Can be null if playlist not yet synced
    image_url = db.Column(db.String(512), nullable=True) # For storing the playlist cover image URL
    track_count = db.Column(db.Integer, nullable=True)  # Total number of tracks in the playlist
    total_tracks = db.Column(db.Integer, nullable=True)  # Alternative field name for total tracks (used in some routes/tests)
    last_analyzed = db.Column(db.DateTime, nullable=True)
    overall_alignment_score = db.Column(db.Float, nullable=True)
    last_synced_from_spotify = db.Column(db.DateTime, nullable=True) # Tracks when the playlist was last synced from Spotify changes
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    owner = db.relationship('User', back_populates='playlists')
    song_associations = db.relationship('PlaylistSong', back_populates='playlist', cascade='all, delete-orphan')
    snapshots = db.relationship('PlaylistSnapshot', back_populates='playlist', cascade='all, delete-orphan')
    
    # Performance indexes
    __table_args__ = (
        db.Index('idx_playlists_owner_id', 'owner_id'),
        db.Index('idx_playlists_last_analyzed', 'last_analyzed'),
        db.Index('idx_playlists_updated_at', 'updated_at'),
    )

    # Helper to easily get songs through the association
    @property
    def songs(self):
        """
        Get all songs in this playlist ordered by their track position.
        
        This property provides convenient access to the playlist's songs in the
        correct order as they appear on Spotify, using the track_position field
        from the PlaylistSong association table.
        
        Returns:
            list[Song]: List of Song objects ordered by track_position.
            
        Examples:
            >>> for song in playlist.songs:
            ...     # Expected output: 0: Song Title by Artist Name
            ...     pass
        """
        return [association.song for association in sorted(self.song_associations, key=lambda x: x.track_position)]
        
    @property
    def score(self):
        """
        Get the normalized Christian alignment score for template compatibility.
        
        This property converts the internal 0-100 scale overall_alignment_score
        to a normalized 0-1 scale for consistent usage in templates and UI components.
        
        Returns:
            float or None: Normalized score between 0.0 and 1.0, or None if not analyzed.
            
        Examples:
            >>> playlist.overall_alignment_score = 85.0
            >>> # Returns 0.85
            >>> playlist.score
            >>> 
            >>> if playlist.score and playlist.score > 0.8:
            ...     # Expected output: "High alignment playlist"
            ...     pass
        """
        if self.overall_alignment_score is not None:
            # overall_alignment_score is 0-100, return as 0-1 scale
            return self.overall_alignment_score / 100.0
        return None

    def __repr__(self):
        """
        Return a string representation of the Playlist instance.
        
        Returns:
            str: String representation showing the playlist name.
            
        Examples:
            >>> playlist = Playlist(name='Christian Worship')
            >>> # Expected output: <Playlist Christian Worship>
            >>> repr(playlist)
        """
        return f'<Playlist {self.name}>'

class Song(db.Model):
    """
    Model representing a song track in the Christian Music Curation application.
    
    This model stores song metadata from Spotify, lyrics content, and maintains
    relationships with analysis results. Songs can appear in multiple playlists
    through the PlaylistSong association table. The model includes dynamic
    properties for accessing the latest analysis results and supports various
    content filtering and analysis features.
    
    Attributes:
        id (int): Primary key for the song.
        spotify_id (str): Unique Spotify track identifier.
        title (str): Song title.
        artist (str): Primary artist name.
        album (str, optional): Album name.
        duration_ms (int, optional): Track duration in milliseconds.
        lyrics (str, optional): Song lyrics text.
        album_art_url (str, optional): URL to album artwork.
        explicit (bool): Whether the track is marked as explicit on Spotify.
        last_analyzed (datetime, optional): When the song was last analyzed.
        created_at (datetime): When the song record was created.
        updated_at (datetime): When the song record was last updated.
        
    Relationships:
        playlist_associations: Collection of PlaylistSong associations.
        analysis_results: Dynamic collection of AnalysisResult records.
        
    Dynamic Properties:
        analysis_status: Status of the latest analysis ('pending', 'processing', 'completed', 'failed').
        score: Christian alignment score from the latest analysis (0-100).
        concern_level: Concern level from analysis ('Low', 'Medium', 'High').
        analysis_concerns: List of specific concerns identified in analysis.
        
    Examples:
        Creating a new song:
            >>> song = Song(
            ...     spotify_id='4iV5W9uYEdYUVa79Axb7Rh',
            ...     title='Amazing Grace',
            ...     artist='Various Artists',
            ...     album='Christian Classics'
            ... )
            >>> db.session.add(song)
            >>> db.session.commit()
            
        Checking analysis status:
            >>> if song.analysis_status == 'completed':
            ...     # Expected output: Analysis is complete, can access results
            ...     pass
            
        Finding songs by explicit content:
            >>> explicit_songs = Song.query.filter_by(explicit=True).all()
    """
    __tablename__ = 'songs'
    id = db.Column(db.Integer, primary_key=True)
    spotify_id = db.Column(db.String(255), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    artist = db.Column(db.String(255), nullable=False)
    album = db.Column(db.String(255), nullable=True)
    duration_ms = db.Column(db.Integer, nullable=True) # Added duration_ms
    lyrics = db.Column(db.Text, nullable=True)
    album_art_url = db.Column(db.String(512), nullable=True) # Add album art URL field
    explicit = db.Column(db.Boolean, default=False)
    last_analyzed = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    playlist_associations = db.relationship('PlaylistSong', back_populates='song')
    analysis_results = db.relationship('AnalysisResult', back_populates='song_rel', lazy='dynamic', cascade="all, delete-orphan")
    
    # Performance indexes
    __table_args__ = (
        db.Index('idx_songs_explicit', 'explicit'),
        db.Index('idx_songs_last_analyzed', 'last_analyzed'),
    )

    # Analysis properties (not stored in DB, used for template rendering)
    @property
    def analysis_status(self):
        """
        Get the status of the most recent analysis for this song.
        
        Returns:
            str: Analysis status ('pending', 'processing', 'completed', 'failed').
                Returns 'pending' if no analysis results exist.
                
        Examples:
            >>> if song.analysis_status == 'completed':
            ...     # Expected output: Analysis is complete, can access results
            ...     pass
        """
        result = self.analysis_results.first()
        return result.status if result else 'pending'
        
    @analysis_status.setter
    def analysis_status(self, value):
        """
        No-op setter to allow setting the analysis_status property.
        
        Args:
            value: The status value (not actually stored).
            
        Note:
            This setter exists for template compatibility but doesn't
            modify the database. Use AnalysisResult methods instead.
        """
        # This is a no-op setter to allow setting the property
        pass
        
    @property
    def score(self):
        """
        Get the Christian alignment score from the most recent analysis.
        
        Returns:
            float or None: Score between 0-100, or None if not analyzed.
            
        Examples:
            >>> if song.score and song.score > 80:
            ...     # Expected output: "High alignment song"
            ...     pass
        """
        result = self.analysis_results.filter_by(status='completed').order_by(AnalysisResult.analyzed_at.desc()).first()
        return result.score if result else None
        
    @score.setter
    def score(self, value):
        """
        No-op setter to allow setting the score property.
        
        Args:
            value: The score value (not actually stored).
            
        Note:
            This setter exists for template compatibility but doesn't
            modify the database. Use AnalysisResult methods instead.
        """
        # This is a no-op setter to allow setting the property
        pass
        
    @property
    def concern_level(self):
        """
        Get the concern level from the most recent analysis.
        
        Returns:
            str or None: Concern level ('Low', 'Medium', 'High'), or None if not analyzed.
            
        Examples:
            >>> if song.concern_level == 'High':
            ...     # Expected output: "This song requires review"
            ...     pass
        """
        result = self.analysis_results.filter_by(status='completed').order_by(AnalysisResult.analyzed_at.desc()).first()
        return result.concern_level if result else None
        
    @concern_level.setter
    def concern_level(self, value):
        """
        No-op setter to allow setting the concern_level property.
        
        Args:
            value: The concern level value (not actually stored).
            
        Note:
            This setter exists for template compatibility but doesn't
            modify the database. Use AnalysisResult methods instead.
        """
        # This is a no-op setter to allow setting the property
        pass
        
    @property
    def analysis_concerns(self):
        """
        Get the list of specific concerns from the most recent analysis.
        
        Returns:
            list: List of concern strings, empty list if no concerns or not analyzed.
            
        Examples:
            >>> concerns = song.analysis_concerns
            >>> if 'profanity' in concerns:
            ...     # Expected output: "Song contains profanity"
            ...     pass
        """
        result = self.analysis_results.filter_by(status='completed').order_by(AnalysisResult.analyzed_at.desc()).first()
        return result.concerns if result and hasattr(result, 'concerns') else []
        
    @analysis_concerns.setter
    def analysis_concerns(self, value):
        """
        No-op setter to allow setting the analysis_concerns property.
        
        Args:
            value: The concerns value (not actually stored).
            
        Note:
            This setter exists for template compatibility but doesn't
            modify the database. Use AnalysisResult methods instead.
        """
        # This is a no-op setter to allow setting the property
        pass
    
    @property
    def biblical_themes(self):
        """
        Get the biblical themes from the most recent analysis.
        
        Returns:
            list: List of biblical theme dictionaries, empty list if not analyzed.
        """
        result = self.analysis_results.filter_by(status='completed').order_by(AnalysisResult.analyzed_at.desc()).first()
        if result and result.biblical_themes:
            try:
                import json
                return json.loads(result.biblical_themes) if isinstance(result.biblical_themes, str) else result.biblical_themes
            except (json.JSONDecodeError, TypeError):
                return []
        return []
    
    @property
    def supporting_scripture(self):
        """
        Get the supporting scripture from the most recent analysis.
        
        Returns:
            list: List of scripture references, empty list if not analyzed.
        """
        result = self.analysis_results.filter_by(status='completed').order_by(AnalysisResult.analyzed_at.desc()).first()
        if result and result.supporting_scripture:
            try:
                import json
                return json.loads(result.supporting_scripture) if isinstance(result.supporting_scripture, str) else result.supporting_scripture
            except (json.JSONDecodeError, TypeError):
                return []
        return []
    
    @property
    def positive_themes_identified(self):
        """
        Get the positive themes from the most recent analysis.
        
        Returns:
            list: List of positive theme dictionaries, empty list if not analyzed.
        """
        result = self.analysis_results.filter_by(status='completed').order_by(AnalysisResult.analyzed_at.desc()).first()
        if result and result.positive_themes_identified:
            try:
                import json
                return json.loads(result.positive_themes_identified) if isinstance(result.positive_themes_identified, str) else result.positive_themes_identified
            except (json.JSONDecodeError, TypeError):
                return []
        return []
    
    @property
    def purity_flags_details(self):
        """
        Get the purity flags details from the most recent analysis.
        
        Returns:
            list: List of purity flag dictionaries, empty list if not analyzed.
        """
        result = self.analysis_results.filter_by(status='completed').order_by(AnalysisResult.analyzed_at.desc()).first()
        if result and result.purity_flags_details:
            try:
                import json
                return json.loads(result.purity_flags_details) if isinstance(result.purity_flags_details, str) else result.purity_flags_details
            except (json.JSONDecodeError, TypeError):
                return []
        return []
    
    def __repr__(self):
        """
        Return a string representation of the Song instance.
        
        Returns:
            str: String representation showing the song title and artist.
            
        Examples:
            >>> song = Song(title='Amazing Grace', artist='Various Artists')
            >>> # Expected output: <Song Amazing Grace - Various Artists>
            >>> repr(song)
        """
        return f'<Song {self.title} - {self.artist}>'

class AnalysisResult(db.Model):
    """
    Model representing the results of Christian content analysis for a song.
    
    This model stores comprehensive analysis results including content scores,
    identified themes, concerns, biblical references, and detailed explanations.
    Each song can have multiple analysis results over time, with the most recent
    being used for display and decision-making. The model supports different
    analysis states and error handling for failed analyses.
    
    Attributes:
        id (int): Primary key for the analysis result.
        song_id (int): Foreign key referencing the analyzed song.
        status (str): Analysis status using class constants (STATUS_*).
        themes (dict, optional): JSON object containing identified themes.
        problematic_content (dict, optional): JSON object with problematic content details.
        concerns (list, optional): JSON array of specific concern strings.
        alignment_score (float, optional): Legacy alignment score field.
        score (float, optional): Christian alignment score (0-100).
        concern_level (str, optional): Overall concern level ('Low', 'Medium', 'High').
        explanation (str, optional): Detailed analysis explanation.
        analyzed_at (datetime): When the analysis was performed.
        error_message (str, optional): Error message if analysis failed.
        purity_flags_details (dict, optional): JSON object with detailed purity flag information.
        positive_themes_identified (dict, optional): JSON object with positive Christian themes.
        biblical_themes (dict, optional): JSON object with biblical themes and verses.
        supporting_scripture (dict, optional): JSON object with scripture references and text.
        created_at (datetime): When the analysis record was created.
        updated_at (datetime): When the analysis record was last updated.
        
    Relationships:
        song_rel: Back reference to the Song being analyzed.
        
    Class Constants:
        STATUS_PENDING (str): Analysis is queued but not yet started.
        STATUS_PROCESSING (str): Analysis is currently in progress.
        STATUS_COMPLETED (str): Analysis completed successfully.
        STATUS_FAILED (str): Analysis failed with an error.
        
    Examples:
        Creating a new analysis result:
            >>> result = AnalysisResult(
            ...     song_id=1,
            ...     status=AnalysisResult.STATUS_PENDING
            ... )
            >>> db.session.add(result)
            >>> db.session.commit()
            
        Marking analysis as processing:
            >>> result.mark_processing()
            >>> db.session.commit()
            
        Completing analysis with results:
            >>> result.mark_completed(
            ...     score=85.5,
            ...     concern_level='Low',
            ...     themes={'worship': True, 'praise': True},
            ...     explanation='Song contains positive Christian themes'
            ... )
            >>> db.session.commit()
    """
    __tablename__ = 'analysis_results'
    
    # Status constants
    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    
    id = db.Column(db.Integer, primary_key=True)
    song_id = db.Column(db.Integer, db.ForeignKey('songs.id'), nullable=False)
    status = db.Column(db.String(20), default=STATUS_PENDING, nullable=False)
    themes = db.Column(db.JSON, nullable=True)  
    problematic_content = db.Column(db.JSON, nullable=True)
    concerns = db.Column(db.JSON, nullable=True)  # List of concern strings
    alignment_score = db.Column(db.Float, nullable=True)  # Legacy field, might be repurposed
    score = db.Column(db.Float, nullable=True)  # 0-100 score
    concern_level = db.Column(db.String(50), nullable=True)  # High/Medium/Low concern
    explanation = db.Column(db.Text, nullable=True)
    analyzed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    error_message = db.Column(db.Text, nullable=True)  # Store error message if analysis fails
    
    # New detailed analysis fields
    purity_flags_details = db.Column(db.JSON, nullable=True)  # Detailed purity flags information
    positive_themes_identified = db.Column(db.JSON, nullable=True)  # Positive Christian themes detected
    biblical_themes = db.Column(db.JSON, nullable=True)  # Biblical themes and relevant verses
    supporting_scripture = db.Column(db.JSON, nullable=True)  # Supporting scripture references and text
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    song_rel = db.relationship('Song', back_populates='analysis_results')
    
    # Indexes
    __table_args__ = (
        db.Index('idx_analysis_song_id', 'song_id'),
        db.Index('idx_analysis_status', 'status'),
        db.Index('idx_analysis_concern_level', 'concern_level'),
    )
    
    def mark_processing(self):
        """
        Mark this analysis as currently being processed.
        
        Updates the status to STATUS_PROCESSING and sets the updated timestamp.
        This should be called when analysis begins to prevent duplicate processing.
        
        Examples:
            >>> result = AnalysisResult(song_id=1)
            >>> result.mark_processing()
            >>> db.session.commit()
        """
        self.status = self.STATUS_PROCESSING
        self.updated_at = datetime.now(timezone.utc)
        
    def mark_completed(self, score=None, concern_level=None, themes=None, concerns=None, explanation=None, 
                      purity_flags_details=None, positive_themes_identified=None, biblical_themes=None, 
                      supporting_scripture=None):
        """
        Mark this analysis as completed with the given results.
        
        Updates the status to STATUS_COMPLETED and populates all the analysis
        result fields with the provided data. Sets the analyzed_at timestamp.
        
        Args:
            score (float, optional): Christian alignment score (0-100).
            concern_level (str, optional): Overall concern level ('Low', 'Medium', 'High').
            themes (dict, optional): Dictionary of identified themes.
            concerns (list, optional): List of specific concern strings.
            explanation (str, optional): Detailed analysis explanation.
            purity_flags_details (dict, optional): Detailed purity flag information.
            positive_themes_identified (dict, optional): Positive Christian themes detected.
            biblical_themes (dict, optional): Biblical themes and relevant verses.
            supporting_scripture (dict, optional): Scripture references and text.
            
        Examples:
            >>> result.mark_completed(
            ...     score=85.5,
            ...     concern_level='Low',
            ...     themes={'worship': True, 'praise': True},
            ...     concerns=[],
            ...     explanation='Song contains positive Christian themes'
            ... )
            >>> db.session.commit()
        """
        self.status = self.STATUS_COMPLETED
        self.score = score
        self.concern_level = concern_level
        self.themes = themes
        self.concerns = concerns or []
        self.explanation = explanation
        self.purity_flags_details = purity_flags_details
        self.positive_themes_identified = positive_themes_identified
        self.biblical_themes = biblical_themes
        self.supporting_scripture = supporting_scripture
        self.analyzed_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    @property
    def biblical_themes_parsed(self):
        """
        Get the biblical themes as parsed Python objects.
        
        Returns:
            list: List of biblical theme dictionaries, empty list if not analyzed.
        """
        if self.biblical_themes:
            # Already parsed since it's a JSON column
            return self.biblical_themes if isinstance(self.biblical_themes, list) else []
        return []
    
    @property
    def supporting_scripture_parsed(self):
        """
        Get the supporting scripture as parsed Python objects.
        
        Returns:
            list: List of scripture reference dictionaries, empty list if not analyzed.
        """
        if self.supporting_scripture:
            # Already parsed since it's a JSON column
            return self.supporting_scripture if isinstance(self.supporting_scripture, list) else []
        return []
    
    @property
    def positive_themes_identified_parsed(self):
        """
        Get the positive themes as parsed Python objects.
        
        Returns:
            list: List of positive theme dictionaries, empty list if not analyzed.
        """
        if self.positive_themes_identified:
            # Already parsed since it's a JSON column
            return self.positive_themes_identified if isinstance(self.positive_themes_identified, list) else []
        return []
    
    @property
    def purity_flags_details_parsed(self):
        """
        Get the purity flags as parsed Python objects.
        
        Returns:
            list: List of purity flag dictionaries, empty list if not analyzed.
        """
        if self.purity_flags_details:
            # Already parsed since it's a JSON column
            return self.purity_flags_details if isinstance(self.purity_flags_details, list) else []
        return []
        
    def mark_failed(self, error_message):
        """
        Mark this analysis as failed with an error message.
        
        Updates the status to STATUS_FAILED and stores the error message
        for debugging purposes. Sets the updated timestamp.
        
        Args:
            error_message (str): Description of the error that occurred.
            
        Examples:
            >>> result.mark_failed("API rate limit exceeded")
            >>> db.session.commit()
        """
        self.status = self.STATUS_FAILED
        self.error_message = error_message
        self.updated_at = datetime.now(timezone.utc)
        
    def to_dict(self):
        """
        Convert the analysis result to a dictionary representation.
        
        Returns:
            dict: Dictionary containing all analysis result fields,
                 suitable for JSON serialization and API responses.
                 
        Examples:
            >>> result_dict = result.to_dict()
            >>> # Access the score
            >>> result_dict['score']
            >>> json.dumps(result_dict)  # Serialize to JSON
        """
        return {
            'id': self.id,
            'song_id': self.song_id,
            'status': self.status,
            'score': self.score,
            'concern_level': self.concern_level,
            'themes': self.themes,
            'concerns': self.concerns,
            'explanation': self.explanation,
            'purity_flags_details': self.purity_flags_details,
            'positive_themes_identified': self.positive_themes_identified,
            'biblical_themes': self.biblical_themes,
            'supporting_scripture': self.supporting_scripture,
            'analyzed_at': self.analyzed_at.isoformat() if self.analyzed_at else None,
            'error_message': self.error_message
        }
        
    def __repr__(self):
        """
        Return a string representation of the AnalysisResult instance.
        
        Returns:
            str: String representation showing song ID, status, and score.
            
        Examples:
            >>> result = AnalysisResult(song_id=1, status='completed', score=85.5)
            >>> # Expected output: <AnalysisResult song_id=1 status=completed score=85.5>
            >>> repr(result)
        """
        return f'<AnalysisResult song_id={self.song_id} status={self.status} score={self.score}>'

class Whitelist(db.Model):
    """
    Model representing user-approved items that bypass content analysis.
    
    The whitelist allows users to mark specific songs, artists, or playlists as
    always acceptable, bypassing the normal Christian content analysis process.
    This is useful for known Christian content or items the user has personally
    vetted. Each whitelist entry is user-specific and includes metadata about
    when and why the item was whitelisted.
    
    Attributes:
        id (int): Primary key for the whitelist entry.
        user_id (int): Foreign key referencing the user who created the entry.
        spotify_id (str): Spotify ID of the whitelisted item (song, artist, or playlist).
        item_type (str): Type of item ('song', 'artist', 'playlist').
        name (str, optional): Human-readable name of the item for display.
        reason (str, optional): User-provided reason for whitelisting.
        added_date (datetime): When the item was added to the whitelist.
        
    Relationships:
        user: Back reference to the User who owns this whitelist entry.
        
    Constraints:
        - Unique constraint on (user_id, spotify_id, item_type) prevents duplicate entries.
        
    Examples:
        Whitelisting a Christian artist:
            >>> whitelist_entry = Whitelist(
            ...     user_id=1,
            ...     spotify_id='3Nrfpe0tUJi4K4DXYWgMUX',
            ...     item_type='artist',
            ...     name='Chris Tomlin',
            ...     reason='Known Christian worship leader'
            ... )
            >>> db.session.add(whitelist_entry)
            >>> db.session.commit()
            
        Checking if an item is whitelisted:
            >>> entry = Whitelist.query.filter_by(
            ...     user_id=user.id,
            ...     spotify_id='track_id',
            ...     item_type='song'
            ... ).first()
            >>> if entry:
            ...     # Expected output: "Song is whitelisted"
            ...     pass
    """
    __tablename__ = 'whitelist'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    spotify_id = db.Column(db.String(255), nullable=False)  # For song, playlist, or artist Spotify ID
    item_type = db.Column(db.String(50), nullable=False)  # e.g., 'song', 'playlist', 'artist'
    name = db.Column(db.String(255), nullable=True) # Human-readable name of the item
    reason = db.Column(db.Text, nullable=True) # Optional reason for whitelisting
    added_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Ensures a user cannot whitelist the same item of the same type multiple times.
    __table_args__ = (db.UniqueConstraint('user_id', 'spotify_id', 'item_type', name='_user_spotify_item_uc'),)

    def to_dict(self):
        """
        Convert the whitelist entry to a dictionary representation.
        
        Returns:
            dict: Dictionary containing all whitelist entry fields,
                 suitable for JSON serialization and API responses.
                 
        Examples:
            >>> entry_dict = whitelist_entry.to_dict()
            >>> # Access the item type
            >>> entry_dict['item_type']
            >>> json.dumps(entry_dict)  # Serialize to JSON
        """
        return {
            'id': self.id,
            'user_id': self.user_id,
            'spotify_id': self.spotify_id,
            'item_type': self.item_type,
            'name': self.name,
            'reason': self.reason,
            'added_date': self.added_date.isoformat() if self.added_date else None
        }

    def __repr__(self):
        """
        Return a string representation of the Whitelist instance.
        
        Returns:
            str: String representation showing item type, name, and user ID.
            
        Examples:
            >>> entry = Whitelist(item_type='artist', name='Chris Tomlin', user_id=1)
            >>> # Expected output: <Whitelist artist: Chris Tomlin (User 1)>
            >>> repr(entry)
        """
        return f'<Whitelist {self.item_type}: {self.name} (User {self.user_id})>'

class Blacklist(db.Model):
    """
    Model representing user-rejected items that are always flagged as inappropriate.
    
    The blacklist allows users to mark specific songs, artists, or playlists as
    always unacceptable, regardless of analysis results. This is useful for content
    the user has determined is inappropriate for their Christian values. Each
    blacklist entry is user-specific and includes metadata about when and why
    the item was blacklisted.
    
    Attributes:
        id (int): Primary key for the blacklist entry.
        user_id (int): Foreign key referencing the user who created the entry.
        spotify_id (str): Spotify ID of the blacklisted item (song, artist, or playlist).
        item_type (str): Type of item ('song', 'artist', 'playlist').
        name (str, optional): Human-readable name of the item for display.
        reason (str, optional): User-provided reason for blacklisting.
        added_date (datetime): When the item was added to the blacklist.
        
    Relationships:
        user_blacklisting: Back reference to the User who owns this blacklist entry.
        
    Constraints:
        - Unique constraint on (user_id, spotify_id, item_type) prevents duplicate entries.
        
    Examples:
        Blacklisting an inappropriate artist:
            >>> blacklist_entry = Blacklist(
            ...     user_id=1,
            ...     spotify_id='1XtDw4l2zx8XcHX7T7cNzn',
            ...     item_type='artist',
            ...     name='Explicit Artist',
            ...     reason='Contains inappropriate content'
            ... )
            >>> db.session.add(blacklist_entry)
            >>> db.session.commit()
            
        Checking if an item is blacklisted:
            >>> entry = Blacklist.query.filter_by(
            ...     user_id=user.id,
            ...     spotify_id='track_id',
            ...     item_type='song'
            ... ).first()
            >>> if entry:
            ...     # Expected output: "Song is blacklisted"
            ...     pass
    """
    __tablename__ = 'blacklist'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    spotify_id = db.Column(db.String(255), nullable=False)  # For song, playlist, or artist Spotify ID
    item_type = db.Column(db.String(50), nullable=False)  # e.g., 'song', 'playlist', 'artist'
    name = db.Column(db.String(255), nullable=True) # Human-readable name of the item
    reason = db.Column(db.Text, nullable=True) # Optional reason for blacklisting
    added_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Ensures a user cannot blacklist the same item of the same type multiple times.
    __table_args__ = (db.UniqueConstraint('user_id', 'spotify_id', 'item_type', name='_user_spotify_item_blacklist_uc'),)

    def to_dict(self):
        """
        Convert the blacklist entry to a dictionary representation.
        
        Returns:
            dict: Dictionary containing all blacklist entry fields,
                 suitable for JSON serialization and API responses.
                 
        Examples:
            >>> entry_dict = blacklist_entry.to_dict()
            >>> # Access the reason
            >>> entry_dict['reason']
            >>> json.dumps(entry_dict)  # Serialize to JSON
        """
        return {
            'id': self.id,
            'user_id': self.user_id,
            'spotify_id': self.spotify_id,
            'item_type': self.item_type,
            'name': self.name,
            'reason': self.reason,
            'added_date': self.added_date.isoformat() if self.added_date else None
        }

    def __repr__(self):
        """
        Return a string representation of the Blacklist instance.
        
        Returns:
            str: String representation showing item type, name, and user ID.
            
        Examples:
            >>> entry = Blacklist(item_type='artist', name='Explicit Artist', user_id=1)
            >>> # Expected output: <Blacklist artist: Explicit Artist (User 1)>
            >>> repr(entry)
        """
        return f'<Blacklist {self.item_type}: {self.name} (User {self.user_id})>'

class LyricsCache(db.Model):
    """
    Cache model for storing fetched lyrics to reduce API calls and improve performance.
    
    This model implements a persistent cache for song lyrics fetched from various
    external APIs (Genius, LRCLib, Lyrics.ovh, etc.). By caching lyrics locally,
    the application reduces API calls, improves response times, and provides
    fallback access when external services are unavailable. The cache includes
    metadata about the source and supports efficient lookup by artist and title.
    
    Attributes:
        id (int): Primary key for the cache entry.
        artist (str): Artist name (indexed for fast lookup).
        title (str): Song title (indexed for fast lookup).
        lyrics (str): Cached lyrics content.
        source (str): Source API/service that provided the lyrics ('lrclib', 'lyrics_ovh', 'genius', etc.).
        created_at (datetime): When the cache entry was created.
        updated_at (datetime): When the cache entry was last updated.
        
    Constraints:
        - Unique constraint on (artist, title) prevents duplicate cache entries.
        
    Examples:
        Caching lyrics from an API:
            >>> lyrics_cache = LyricsCache.cache_lyrics(
            ...     artist='Chris Tomlin',
            ...     title='Amazing Grace',
            ...     lyrics='Amazing grace, how sweet the sound...',
            ...     source='genius'
            ... )
            
        Finding cached lyrics:
            >>> cached = LyricsCache.find_cached_lyrics('Chris Tomlin', 'Amazing Grace')
            >>> if cached:
            ...     # Expected output: Found lyrics from genius: Amazing grace, how sweet...
            ...     pass
            ... else:
            ...     # Expected output: "No cached lyrics found"
            ...     pass
    """
    __tablename__ = 'lyrics_cache'
    
    id = db.Column(db.Integer, primary_key=True)
    artist = db.Column(db.String(255), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False, index=True)
    lyrics = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(50), nullable=False)  # 'lrclib', 'lyrics_ovh', 'genius', etc.
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Ensure unique combination of artist and title
    __table_args__ = (
        db.UniqueConstraint('artist', 'title', name='uix_artist_title'),
        db.Index('idx_lyrics_cache_artist_title', 'artist', 'title'),
        db.Index('idx_lyrics_cache_source', 'source'),
        db.Index('idx_lyrics_cache_updated_at', 'updated_at'),
    )
    
    def to_dict(self):
        """
        Convert the lyrics cache entry to a dictionary representation.
        
        Returns:
            dict: Dictionary containing all cache entry fields,
                 suitable for JSON serialization and API responses.
                 
        Examples:
            >>> cache_dict = lyrics_cache.to_dict()
            >>> # Access the source
            >>> cache_dict['source']
            >>> json.dumps(cache_dict)  # Serialize to JSON
        """
        return {
            'id': self.id,
            'artist': self.artist,
            'title': self.title,
            'lyrics': self.lyrics,
            'source': self.source,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    @classmethod
    def find_cached_lyrics(cls, artist, title):
        """
        Find cached lyrics for a specific artist and title.
        
        Performs a case-insensitive search for cached lyrics matching the
        provided artist and title. This method helps avoid duplicate API
        calls by checking if lyrics have already been fetched and cached.
        
        Args:
            artist (str): The artist name to search for.
            title (str): The song title to search for.
            
        Returns:
            LyricsCache or None: The cached lyrics entry if found, None otherwise.
            
        Examples:
            >>> cached = LyricsCache.find_cached_lyrics('Chris Tomlin', 'Amazing Grace')
            >>> if cached:
            ...     # Expected output: Found lyrics from genius: Amazing grace, how sweet...
            ...     pass
            ... else:
            ...     # Expected output: "No cached lyrics found"
            ...     pass
        """
        # Normalize for search
        artist_lower = artist.lower().strip()
        title_lower = title.lower().strip()
        
        return cls.query.filter(
            db.func.lower(cls.artist) == artist_lower,
            db.func.lower(cls.title) == title_lower
        ).first()
    
    @classmethod
    def cache_lyrics(cls, artist, title, lyrics, source):
        """
        Cache lyrics for a specific artist and title.
        
        Creates or updates a cache entry for the provided lyrics. If an entry
        already exists for the artist and title combination, it updates the
        existing entry with new lyrics and source information.
        
        Args:
            artist (str): The artist name.
            title (str): The song title.
            lyrics (str): The lyrics content to cache.
            source (str): The source API/service that provided the lyrics.
            
        Returns:
            LyricsCache: The created or updated cache entry.
            
        Raises:
            ValueError: If any required parameters are empty or None.
            SQLAlchemyError: If database operations fail.
            
        Examples:
            >>> cache_entry = LyricsCache.cache_lyrics(
            ...     artist='Chris Tomlin',
            ...     title='How Great Is Our God',
            ...     lyrics='The splendor of the King...',
            ...     source='genius'
            ... )
            >>> # Expected output: Cached lyrics from genius
            >>> cache_entry.source
        """
        if not all([artist, title, lyrics, source]):
            raise ValueError("Artist, title, lyrics, and source are all required")
            
        # Clean up the inputs
        artist = artist.strip()
        title = title.strip()
        lyrics = lyrics.strip()
        source = source.strip()
        
        # Check if already exists
        existing = cls.find_cached_lyrics(artist, title)
        
        if existing:
            # Update existing entry
            existing.lyrics = lyrics
            existing.source = source
            existing.updated_at = datetime.now(timezone.utc)
            db.session.add(existing)
            return existing
        else:
            # Create new entry
            cache_entry = cls(
                artist=artist,
                title=title,
                lyrics=lyrics,
                source=source
            )
            db.session.add(cache_entry)
            return cache_entry

    def __repr__(self):
        """
        Return a string representation of the LyricsCache instance.
        
        Returns:
            str: String representation showing artist, title, and source.
            
        Examples:
            >>> cache = LyricsCache(artist='Chris Tomlin', title='Amazing Grace', source='genius')
            >>> # Expected output: <LyricsCache Chris Tomlin - Amazing Grace (genius)>
            >>> repr(cache)
        """
        return f'<LyricsCache {self.artist} - {self.title} ({self.source})>'

class BibleVerse(db.Model):
    """
    Model representing biblical verses used for theme analysis and scripture references.
    
    This model stores biblical verses with their references and thematic keywords,
    supporting the Christian content analysis features. Verses are used to identify
    biblical themes in songs and provide supporting scripture references in analysis
    results. The model supports both single verses and verse ranges for comprehensive
    scripture coverage.
    
    Attributes:
        id (int): Primary key for the bible verse entry.
        book (str): Name of the biblical book (e.g., 'Genesis', 'John', 'Psalms').
        chapter (int): Chapter number within the book.
        verse_start (int): Starting verse number for the reference.
        verse_end (int, optional): Ending verse number for verse ranges, None for single verses.
        text (str): The actual text content of the verse(s).
        theme_keywords (dict, optional): JSON object containing thematic keywords and categories
                                        associated with this verse for analysis matching.
        
    Examples:
        Creating a single verse:
            >>> verse = BibleVerse(
            ...     book='John',
            ...     chapter=3,
            ...     verse_start=16,
            ...     text='For God so loved the world that he gave his one and only Son...',
            ...     theme_keywords={'love': True, 'salvation': True, 'sacrifice': True}
            ... )
            >>> db.session.add(verse)
            >>> db.session.commit()
            
        Creating a verse range:
            >>> verse_range = BibleVerse(
            ...     book='Psalms',
            ...     chapter=23,
            ...     verse_start=1,
            ...     verse_end=3,
            ...     text='The Lord is my shepherd, I lack nothing. He makes me lie down...',
            ...     theme_keywords={'comfort': True, 'guidance': True, 'trust': True}
            ... )
            
        Finding verses by theme:
            >>> comfort_verses = BibleVerse.query.filter(
            ...     BibleVerse.theme_keywords.contains({'comfort': True})
            ... ).all()
    """
    __tablename__ = 'bible_verses'
    id = db.Column(db.Integer, primary_key=True)
    book = db.Column(db.String(50), nullable=False)
    chapter = db.Column(db.Integer, nullable=False)
    verse_start = db.Column(db.Integer, nullable=False)
    verse_end = db.Column(db.Integer, nullable=True)
    text = db.Column(db.Text, nullable=False)
    theme_keywords = db.Column(db.JSON, nullable=True) 

    def __repr__(self):
        """
        Return a string representation of the BibleVerse instance.
        
        Formats the verse reference according to standard biblical citation format,
        showing either a single verse or verse range as appropriate.
        
        Returns:
            str: String representation in the format 'Book Chapter:Verse' or 
                 'Book Chapter:StartVerse-EndVerse' for ranges.
                 
        Examples:
            >>> verse = BibleVerse(book='John', chapter=3, verse_start=16)
            >>> print(repr(verse))
            <BibleVerse John 3:16>
            
            >>> verse_range = BibleVerse(book='Psalms', chapter=23, verse_start=1, verse_end=3)
            >>> print(repr(verse_range))
            <BibleVerse Psalms 23:1-3>
        """
        if self.verse_end:
            return f'<BibleVerse {self.book} {self.chapter}:{self.verse_start}-{self.verse_end}>'
        return f'<BibleVerse {self.book} {self.chapter}:{self.verse_start}>'

class PlaylistSnapshot(db.Model):
    """
    Model representing a snapshot of a playlist's state at a specific point in time.
    
    This model stores metadata about a playlist's state at a given point in time,
    including the playlist's ID, name, and a reference to the snapshot's content.
    The snapshot is linked to the playlist through a foreign key relationship.
    
    Attributes:
        id (int): Primary key for the playlist snapshot.
        playlist_id (int): Foreign key referencing the playlist.
        snapshot_id (str): Unique identifier for the snapshot.
        name (str): Display name of the snapshot.
        created_at (datetime): When the snapshot was created.
        updated_at (datetime): When the snapshot was last updated.
        
    Relationships:
        playlist: Back reference to the associated Playlist object.
        
    Examples:
        Creating a new playlist snapshot:
            >>> snapshot = PlaylistSnapshot(
            ...     playlist_id=1,
            ...     snapshot_id='abc123',
            ...     name='Initial Snapshot'
            ... )
            >>> db.session.add(snapshot)
            >>> db.session.commit()
    """
    __tablename__ = 'playlist_snapshots'
    id = db.Column(db.Integer, primary_key=True)
    playlist_id = db.Column(db.Integer, db.ForeignKey('playlists.id'), nullable=False)
    snapshot_id = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    playlist = db.relationship('Playlist', back_populates='snapshots')

    def __repr__(self):
        """String representation of the PlaylistSnapshot."""
        return f'<PlaylistSnapshot {self.snapshot_id}>'
