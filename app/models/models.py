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

import requests
from flask import current_app
from flask_login import UserMixin
from sqlalchemy import CheckConstraint
from sqlalchemy import literal

from ..extensions import db
from ..utils.crypto import encrypt_token, decrypt_token


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    spotify_id = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=True)
    display_name = db.Column(db.String(255), nullable=True)
    access_token = db.Column(db.String(1024), nullable=False)
    refresh_token = db.Column(db.String(1024), nullable=True)
    token_expiry = db.Column(db.DateTime, nullable=False)
    last_login = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    playlists = db.relationship(
        "Playlist", back_populates="owner", lazy="dynamic", cascade="all, delete-orphan"
    )
    whitelisted_artists = db.relationship(
        "Whitelist",
        backref="user",
        lazy="dynamic",
        foreign_keys="Whitelist.user_id",
        cascade="all, delete-orphan",
    )
    blacklisted_items = db.relationship(
        "Blacklist",
        backref="user_blacklisting",
        lazy="dynamic",
        foreign_keys="Blacklist.user_id",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<User {self.email}>"

    def set_access_token(self, token: str) -> None:
        """Set access token with encryption"""
        self.access_token = encrypt_token(token) if token else None

    def get_access_token(self) -> str:
        """Get decrypted access token"""
        try:
            return decrypt_token(self.access_token) if self.access_token else None
        except Exception as e:
            current_app.logger.error(f"Failed to decrypt access token for user {self.id}: {e}")
            return None

    def set_refresh_token(self, token: str) -> None:
        """Set refresh token with encryption"""
        self.refresh_token = encrypt_token(token) if token else None

    def get_refresh_token(self) -> str:
        """Get decrypted refresh token"""
        try:
            return decrypt_token(self.refresh_token) if self.refresh_token else None
        except Exception as e:
            current_app.logger.error(f"Failed to decrypt refresh token for user {self.id}: {e}")
            return None

    def clear_session(self) -> None:
        self.access_token = None
        self.refresh_token = None
        current_app.logger.debug(f"Session data cleared for user {self.id}")

    @property
    def is_token_expired(self):
        if not self.token_expiry:
            return True
        now = datetime.now(timezone.utc)
        if self.token_expiry.tzinfo is None:
            now = now.replace(tzinfo=None)
        return now >= self.token_expiry

    def ensure_token_valid(self):
        return not self.is_token_expired
    
    def needs_reauth(self, days_threshold=30):
        """Check if user needs to re-authenticate based on last login time"""
        if not self.last_login:
            return True
        
        now = datetime.now(timezone.utc)
        last_login = self.last_login
        
        # Handle timezone-aware vs naive datetimes
        if last_login.tzinfo is None:
            last_login = last_login.replace(tzinfo=timezone.utc)
        
        days_since_login = (now - last_login).days
        return days_since_login >= days_threshold

    def refresh_access_token(self):
        refresh_token = self.get_refresh_token()
        if not refresh_token:
            current_app.logger.warning(f"No refresh token available for user {self.id}")
            return False
        token_url = "https://accounts.spotify.com/api/token"
        client_id = current_app.config.get("SPOTIFY_CLIENT_ID")
        client_secret = current_app.config.get("SPOTIFY_CLIENT_SECRET")
        if not client_id or not client_secret:
            current_app.logger.error("Spotify client credentials not configured")
            return False
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        }
        try:
            response = requests.post(token_url, headers=headers, data=data, timeout=10)
            response.raise_for_status()
            token_info = response.json()
            self.set_access_token(token_info["access_token"])
            self.token_expiry = datetime.now(timezone.utc) + timedelta(
                seconds=token_info["expires_in"]
            )
            if "refresh_token" in token_info:
                self.set_refresh_token(token_info["refresh_token"])
            db.session.commit()
            current_app.logger.info(f"Successfully refreshed token for user {self.id}")
            return True
        except requests.RequestException as e:
            current_app.logger.error(f"Failed to refresh token for user {self.id}: {e}")
            db.session.rollback()
            return False

class PlaylistSong(db.Model):
    __tablename__ = "playlist_songs"
    playlist_id = db.Column(
        db.Integer, db.ForeignKey("playlists.id", ondelete="CASCADE"), primary_key=True
    )
    song_id = db.Column(db.Integer, db.ForeignKey("songs.id", ondelete="CASCADE"), primary_key=True)
    track_position = db.Column(db.Integer, nullable=False)
    added_at_spotify = db.Column(db.DateTime, nullable=True)
    added_by_spotify_user_id = db.Column(db.String(255), nullable=True)
    playlist = db.relationship("Playlist", back_populates="song_associations")
    song = db.relationship("Song", back_populates="playlist_associations")
    __table_args__ = (
        db.Index("idx_playlist_songs_playlist_id", "playlist_id"),
        db.Index("idx_playlist_songs_song_id", "song_id"),
        db.Index("idx_playlist_songs_track_position", "playlist_id", "track_position"),
    )

    def __repr__(self):
        return f"<PlaylistSong playlist_id={self.playlist_id} song_id={self.song_id} position={self.track_position}>"

class Playlist(db.Model):
    __tablename__ = "playlists"
    id = db.Column(db.Integer, primary_key=True)
    spotify_id = db.Column(
        db.String(255), nullable=False
    )
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    spotify_snapshot_id = db.Column(
        db.String(255), nullable=True
    )
    image_url = db.Column(db.String(512), nullable=True)
    cover_collage_urls = db.Column(db.JSON, nullable=True)
    track_count = db.Column(db.Integer, nullable=True)
    has_flagged = db.Column(db.Boolean, default=False, nullable=False)
    last_analyzed = db.Column(db.DateTime, nullable=True)
    overall_alignment_score = db.Column(db.Float, nullable=True)
    last_synced_from_spotify = db.Column(
        db.DateTime, nullable=True
    )
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    owner = db.relationship("User", back_populates="playlists")
    song_associations = db.relationship(
        "PlaylistSong", back_populates="playlist", cascade="all, delete-orphan"
    )
    snapshots = db.relationship(
        "PlaylistSnapshot", back_populates="playlist", cascade="all, delete-orphan"
    )
    __table_args__ = (
        db.Index("idx_playlists_owner_id", "owner_id"),
        db.Index("idx_playlists_last_analyzed", "last_analyzed"),
        db.Index("idx_playlists_updated_at", "updated_at"),
        db.UniqueConstraint("owner_id", "spotify_id", name="uq_playlists_owner_spotify"),
    )

    @property
    def songs(self):
        return (
            db.session.query(Song)
            .join(PlaylistSong)
            .filter(PlaylistSong.playlist_id == self.id)
            .order_by(PlaylistSong.track_position)
            .all()
        )

    @property
    def score(self):
        if self.overall_alignment_score is None:
            return None
        return self.overall_alignment_score / 100

    def __repr__(self):
        return f"<Playlist {self.name}>"

class Song(db.Model):
    __tablename__ = "songs"
    id = db.Column(db.Integer, primary_key=True)
    spotify_id = db.Column(db.String(255), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    artist = db.Column(db.String(255), nullable=False)
    album = db.Column(db.String(255), nullable=True)
    duration_ms = db.Column(db.Integer, nullable=True)
    lyrics = db.Column(db.Text, nullable=True)
    album_art_url = db.Column(db.String(512), nullable=True)
    explicit = db.Column(db.Boolean, default=False)
    last_analyzed = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    playlist_associations = db.relationship("PlaylistSong", back_populates="song")
    analysis_result = db.relationship(
        "AnalysisResult",
        back_populates="song_rel",
        uselist=False,
        cascade="all, delete-orphan",
    )
    analysis_results = db.relationship(
        "AnalysisResult",
        back_populates="song_rel",
        lazy="dynamic",
        cascade="all, delete-orphan",
        overlaps="analysis_result",
    )
    __table_args__ = (
        db.Index("idx_songs_explicit", "explicit"),
        db.Index("idx_songs_last_analyzed", "last_analyzed"),
    )

    @property
    def analysis_status(self):
        return "completed" if self.analysis_result else "pending"

    @analysis_status.setter
    def analysis_status(self, value):
        pass

    @property
    def score(self):
        return self.analysis_result.score if self.analysis_result else None

    @score.setter
    def score(self, value):
        pass

    @property
    def concern_level(self):
        result = (
            self.analysis_result
        )
        return result.concern_level if result else None

    @concern_level.setter
    def concern_level(self, value):
        pass

    @property
    def analysis_concerns(self):
        result = (
            self.analysis_result
        )
        return result.concerns if result and hasattr(result, "concerns") else []

    @analysis_concerns.setter
    def analysis_concerns(self, value):
        pass

    @property
    def biblical_themes(self):
        result = (
            self.analysis_result
        )
        if result and result.biblical_themes:
            try:
                import json

                return (
                    json.loads(result.biblical_themes)
                    if isinstance(result.biblical_themes, str)
                    else result.biblical_themes
                )
            except (json.JSONDecodeError, TypeError):
                return []
        return []

    @property
    def supporting_scripture(self):
        result = (
            self.analysis_result
        )
        if result and result.supporting_scripture:
            try:
                import json

                return (
                    json.loads(result.supporting_scripture)
                    if isinstance(result.supporting_scripture, str)
                    else result.supporting_scripture
                )
            except (json.JSONDecodeError, TypeError):
                return []
        return []

    @property
    def positive_themes_identified(self):
        result = (
            self.analysis_result
        )
        if result and result.positive_themes_identified:
            try:
                import json

                return (
                    json.loads(result.positive_themes_identified)
                    if isinstance(result.positive_themes_identified, str)
                    else result.positive_themes_identified
                )
            except (json.JSONDecodeError, TypeError):
                return []
        return []

    @property
    def purity_flags_details(self):
        result = (
            self.analysis_result
        )
        if result and result.purity_flags_details:
            try:
                import json

                return (
                    json.loads(result.purity_flags_details)
                    if isinstance(result.purity_flags_details, str)
                    else result.purity_flags_details
                )
            except (json.JSONDecodeError, TypeError):
                return []
        return []

    def __repr__(self):
        return f"<Song {self.title} - {self.artist}>"

class AnalysisResult(db.Model):
    __tablename__ = "analysis_results"
    id = db.Column(db.Integer, primary_key=True)
    song_id = db.Column(db.Integer, db.ForeignKey("songs.id", ondelete="CASCADE"), nullable=False)
    themes = db.Column(db.JSON, nullable=True)
    problematic_content = db.Column(db.JSON, nullable=True)
    concerns = db.Column(db.JSON, nullable=True)
    alignment_score = db.Column(db.Float, nullable=True)
    score = db.Column(db.Float, nullable=True)
    concern_level = db.Column(db.String(50), nullable=True)
    explanation = db.Column(db.Text, nullable=False, default='Analysis completed')
    analyzed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    purity_flags_details = db.Column(db.JSON, nullable=True)
    positive_themes_identified = db.Column(
        db.JSON, nullable=True
    )
    biblical_themes = db.Column(db.JSON, nullable=True)
    supporting_scripture = db.Column(
        db.JSON, nullable=True
    )
    verdict = db.Column(
        db.String(50), nullable=True
    )
    purity_score = db.Column(db.Float, nullable=True)
    formation_risk = db.Column(db.String(20), nullable=True)
    doctrinal_clarity = db.Column(db.String(20), nullable=True)
    confidence = db.Column(db.String(20), nullable=True)
    analysis_quality = db.Column(db.String(20), default='full', nullable=False)  # 'full', 'degraded', 'cached'
    needs_review = db.Column(db.Boolean, default=False)
    narrative_voice = db.Column(db.String(20), nullable=True)
    lament_filter_applied = db.Column(db.Boolean, default=False)
    framework_data = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    song_rel = db.relationship("Song", back_populates="analysis_results", foreign_keys=[song_id])
    __table_args__ = (
        db.Index("idx_analysis_song_id", "song_id"),
        db.Index("idx_analysis_concern_level", "concern_level"),
        db.Index("idx_analysis_song_created", "song_id", "created_at"),
    )
    status = db.Column(db.String(50), default='pending', nullable=False)
    error = db.Column(db.Text, nullable=True)

    @property
    def is_complete(self):
      return self.status in ['completed', 'failed', 'error', 'skipped']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if getattr(self, "explanation", None) is None:
            self.explanation = "Analysis completed"

    def mark_completed(
        self,
        score=None,
        concern_level=None,
        explanation=None,
        themes=None,
        problematic_content=None,
        concerns=None,
        purity_flags_details=None,
        positive_themes_identified=None,
        biblical_themes=None,
        supporting_scripture=None,
        verdict=None,
        purity_score=None,
        formation_risk=None,
        doctrinal_clarity=None,
        confidence=None,
        analysis_quality=None,
        needs_review=None,
        narrative_voice=None,
        lament_filter_applied=None,
        framework_data=None,
    ):
        self.score = score
        self.concern_level = concern_level
        self.explanation = explanation
        self.themes = themes
        self.problematic_content = problematic_content
        self.concerns = concerns
        self.purity_flags_details = purity_flags_details
        self.positive_themes_identified = positive_themes_identified
        self.biblical_themes = biblical_themes
        self.supporting_scripture = supporting_scripture
        self.verdict = verdict
        self.purity_score = purity_score
        self.formation_risk = formation_risk
        self.doctrinal_clarity = doctrinal_clarity
        self.confidence = confidence
        if analysis_quality is not None:
            self.analysis_quality = analysis_quality
        self.needs_review = needs_review
        self.narrative_voice = narrative_voice
        self.lament_filter_applied = lament_filter_applied
        self.framework_data = framework_data

class Whitelist(db.Model):
    __tablename__ = "whitelist"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    spotify_id = db.Column(db.String(255), nullable=False)
    item_type = db.Column(db.String(50), nullable=False)  # 'artist' or 'song'
    item_name = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    __table_args__ = (
        db.UniqueConstraint(
            "user_id", "spotify_id", "item_type", name="uq_whitelist_user_item"
        ),
        {'extend_existing': True}
    )

class Blacklist(db.Model):
    __tablename__ = "blacklist"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    spotify_id = db.Column(db.String(255), nullable=False)
    item_type = db.Column(db.String(50), nullable=False)  # 'artist' or 'song'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    __table_args__ = (
        db.UniqueConstraint(
            "user_id", "spotify_id", "item_type", name="uq_blacklist_user_item"
        ),
    )

class PlaylistSnapshot(db.Model):
    __tablename__ = "playlist_snapshots"
    id = db.Column(db.Integer, primary_key=True)
    playlist_id = db.Column(db.Integer, db.ForeignKey("playlists.id"), nullable=False)
    spotify_snapshot_id = db.Column(db.String(255), nullable=False)
    track_count = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    playlist = db.relationship("Playlist", back_populates="snapshots")

class BibleVerse(db.Model):
    __tablename__ = "bible_verses"
    id = db.Column(db.Integer, primary_key=True)
    book = db.Column(db.String(50), nullable=False)
    chapter = db.Column(db.Integer, nullable=False)
    verse = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)
    __table_args__ = (db.UniqueConstraint("book", "chapter", "verse", name="uq_bible_verse"),)


class AnalysisCache(db.Model):
    """
    Permanent cache for song analysis results.
    Prevents re-analyzing the same song multiple times.
    """
    __tablename__ = "analysis_cache"
    __table_args__ = (
        db.UniqueConstraint('artist', 'title', 'lyrics_hash', name='uq_analysis_cache_song'),
        db.Index('idx_analysis_cache_artist_title', 'artist', 'title'),
        db.Index('idx_analysis_cache_model_version', 'model_version'),
        db.Index('idx_analysis_cache_created_at', 'created_at'),
    )
    
    id = db.Column(db.Integer, primary_key=True)
    artist = db.Column(db.String(500), nullable=False)
    title = db.Column(db.String(500), nullable=False)
    lyrics_hash = db.Column(db.String(64), nullable=False)  # SHA256 hash of lyrics
    analysis_result = db.Column(db.JSON, nullable=False)  # Full analysis JSON
    model_version = db.Column(db.String(100), nullable=False)  # Track which model version
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), 
                          onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    
    @classmethod
    def find_cached_analysis(cls, artist: str, title: str, lyrics_hash: str):
        """Find cached analysis by artist, title, and lyrics hash."""
        return cls.query.filter_by(
            artist=artist.strip(),
            title=title.strip(),
            lyrics_hash=lyrics_hash
        ).first()
    
    @classmethod
    def cache_analysis(cls, artist: str, title: str, lyrics_hash: str, 
                      analysis_result: dict, model_version: str):
        """Cache analysis result for a song."""
        from app.extensions import db
        
        artist = artist.strip()
        title = title.strip()
        
        # Check if already cached
        cached = cls.find_cached_analysis(artist, title, lyrics_hash)
        if cached:
            # Update existing cache
            cached.analysis_result = analysis_result
            cached.model_version = model_version
            cached.updated_at = datetime.now(timezone.utc)
        else:
            # Create new cache entry
            cached = cls(
                artist=artist,
                title=title,
                lyrics_hash=lyrics_hash,
                analysis_result=analysis_result,
                model_version=model_version
            )
            db.session.add(cached)
        
        db.session.commit()
        return cached
    
    @classmethod
    def get_cache_stats(cls):
        """Get cache statistics."""
        from sqlalchemy import func
        
        total = cls.query.count()
        by_model = db.session.query(
            cls.model_version, 
            func.count(cls.id)
        ).group_by(cls.model_version).all()
        
        return {
            'total_cached': total,
            'by_model_version': dict(by_model)
        }


class LyricsCache(db.Model):
    __table_args__ = (
        db.UniqueConstraint('artist', 'title', name='uq_lyrics_artist_title'),
        {'extend_existing': True}
    )
    __tablename__ = "lyrics_cache"
    id = db.Column(db.Integer, primary_key=True)
    artist = db.Column(db.String(500), nullable=False, index=True)
    title = db.Column(db.String(500), nullable=False, index=True)
    song_id = db.Column(db.Integer, db.ForeignKey("songs.id"), nullable=True)
    lyrics = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(100), nullable=False)
    retrieved_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    song = db.relationship("Song", backref=db.backref("lyrics_cache", uselist=False))

    @classmethod
    def find_cached_lyrics(cls, artist, title):
        """Find cached lyrics by artist and title."""
        return cls.query.filter_by(
            artist=artist.strip(),
            title=title.strip()
        ).first()

    @classmethod
    def cache_lyrics(cls, artist, title, lyrics, source):
        """Cache lyrics for an artist/title pair."""
        from app.extensions import db
        from datetime import datetime, timezone

        artist = artist.strip()
        title = title.strip()
        
        cached = cls.find_cached_lyrics(artist, title)
        if not cached:
            cached = cls(artist=artist, title=title)
        cached.lyrics = lyrics
        cached.source = source
        cached.retrieved_at = datetime.now(timezone.utc)
        cached.updated_at = datetime.now(timezone.utc)
        db.session.add(cached)
        db.session.commit()
        return cached

