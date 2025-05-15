from sqlalchemy.orm import relationship
from sqlalchemy import CheckConstraint
from datetime import datetime, timedelta
from ..extensions import db
from flask_login import UserMixin
from flask import current_app
from spotipy.oauth2 import SpotifyOAuth
import requests

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    spotify_id = db.Column(db.String(255), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=True) 
    display_name = db.Column(db.String(255), nullable=True)
    access_token = db.Column(db.String(512), nullable=False)
    refresh_token = db.Column(db.String(512), nullable=True) 
    token_expiry = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    playlists = db.relationship('Playlist', back_populates='owner', lazy='dynamic', cascade="all, delete-orphan")
    whitelisted_artists = db.relationship('Whitelist', backref='user', lazy='dynamic', foreign_keys='Whitelist.user_id', cascade="all, delete-orphan")
    blacklisted_items = db.relationship('Blacklist', backref='user_blacklisting', lazy='dynamic', foreign_keys='Blacklist.user_id', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<User {self.spotify_id}>'

    @property
    def is_token_expired(self):
        """Checks if the access token is expired or close to expiring."""
        if not self.token_expiry:
            return True 
        return datetime.utcnow() >= (self.token_expiry - timedelta(minutes=5))

    def ensure_token_valid(self):
        """Checks if the access token is valid, refreshing if necessary."""
        self = db.session.merge(self)
        if self.token_expiry and self.token_expiry > datetime.utcnow() + timedelta(seconds=60):
            current_app.logger.debug(f"Token for user {self.id} is valid.")
            return True

        current_app.logger.info(f"Token for user {self.id} has expired or is close to expiring. Attempting refresh.")
        if not self.refresh_token:
            current_app.logger.error(f"User {self.id} has expired token but no refresh token.")
            return False

        # --- Attempt Refresh ---        
        payload = {
            'grant_type': 'refresh_token',
            'refresh_token': self.refresh_token,
        }
        client_id = current_app.config.get('SPOTIFY_CLIENT_ID')
        client_secret = current_app.config.get('SPOTIFY_CLIENT_SECRET')
        
        if not client_id or not client_secret:
             current_app.logger.error("SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET not configured.")
             return False

        try:
            response = requests.post(
                'https://accounts.spotify.com/api/token',
                auth=(client_id, client_secret),
                data=payload
            )
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            token_info = response.json()

            if 'access_token' not in token_info or 'expires_in' not in token_info:
                current_app.logger.error(f"Failed to refresh token for user {self.id}. Invalid response from Spotify: {token_info}")
                return False

            # Update token info
            self.access_token = token_info['access_token']
            expires_in = token_info['expires_in'] # Seconds
            self.token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
            
            # Spotify might return a new refresh token (optional)
            if 'refresh_token' in token_info:
                self.refresh_token = token_info['refresh_token']
                current_app.logger.info(f"Received new refresh token for user {self.id}.")

            db.session.add(self) # Add self to session in case it wasn't already
            db.session.commit()
            try:
                db.session.refresh(self)
            except Exception as e_refresh:
                current_app.logger.error(f"Error refreshing user {self.id} after token commit: {e_refresh}")
                # If refresh fails, the instance might be in an inconsistent state.
                # Depending on the error, it might be safer to treat this as a token validation failure.
                db.session.rollback() # Rollback the previous commit if refresh is critical
                return False
            
            current_app.logger.info(f"Successfully refreshed token for user {self.id}.")
            return True

        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"Error refreshing Spotify token for user {self.id}: {e}")
            # Check if the error indicates invalid refresh token
            if e.response is not None and e.response.status_code == 400:
                 try:
                     error_data = e.response.json()
                     if error_data.get('error') == 'invalid_grant':
                         current_app.logger.error(f"Invalid refresh token for user {self.id}. Requires re-authentication.")
                         # Consider deleting the invalid refresh token?
                         # self.refresh_token = None 
                         # db.session.commit()
                 except ValueError: # JSONDecodeError
                     pass # Ignore if response is not JSON
            db.session.rollback() # Rollback any potential partial changes
            return False
        except Exception as e:
            current_app.logger.exception(f"Unexpected error during token refresh for user {self.id}: {e}")
            db.session.rollback()
            return False

    def ensure_token_valid_original(self):
        """Ensures the user's Spotify access token is valid, refreshing if necessary."""
        if not self.is_token_expired:
            current_app.logger.debug(f"Token for user {self.spotify_id} is still valid.")
            return True

        if not self.refresh_token:
            current_app.logger.warning(f"Token for user {self.spotify_id} is expired, but no refresh token available.")
            return False 

        current_app.logger.info(f"Attempting to refresh token for user {self.spotify_id}.")
        sp_oauth = SpotifyOAuth(
            client_id=current_app.config['SPOTIPY_CLIENT_ID'],
            client_secret=current_app.config['SPOTIPY_CLIENT_SECRET'],
            redirect_uri=current_app.config['SPOTIPY_REDIRECT_URI'], 
            scope=current_app.config.get('SPOTIFY_SCOPES', 'user-read-email'), 
            cache_path=None
        )

        try:
            token_info = sp_oauth.refresh_access_token(self.refresh_token)
        except Exception as e:
            current_app.logger.error(f"Error refreshing token for user {self.spotify_id}: {e}")
            return False

        if not token_info or 'access_token' not in token_info:
            current_app.logger.error(f"Failed to refresh token for user {self.spotify_id}. Invalid token_info received.")
            return False

        self.access_token = token_info['access_token']
        self.token_expiry = datetime.fromtimestamp(token_info['expires_at'])
        if 'refresh_token' in token_info:
            self.refresh_token = token_info['refresh_token']
        self.updated_at = datetime.utcnow()

        try:
            db.session.commit()
            current_app.logger.info(f"Successfully refreshed token for user {self.spotify_id}.")
            return True
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Database error saving refreshed token for user {self.spotify_id}: {e}")
            return False

class PlaylistSong(db.Model):
    __tablename__ = 'playlist_songs'
    playlist_id = db.Column(db.Integer, db.ForeignKey('playlists.id'), primary_key=True)
    song_id = db.Column(db.Integer, db.ForeignKey('songs.id'), primary_key=True)
    track_position = db.Column(db.Integer, nullable=False) # Spotify's 0-indexed position
    added_at_spotify = db.Column(db.DateTime, nullable=True) # Timestamp from Spotify
    added_by_spotify_user_id = db.Column(db.String(255), nullable=True) # Spotify user ID of adder

    playlist = db.relationship('Playlist', back_populates='song_associations')
    song = db.relationship('Song', back_populates='playlist_associations')

    def __repr__(self):
        return f'<PlaylistSong playlist_id={self.playlist_id} song_id={self.song_id} position={self.track_position}>'

class Playlist(db.Model):
    __tablename__ = 'playlists'
    id = db.Column(db.Integer, primary_key=True)
    spotify_id = db.Column(db.String(255), unique=True, nullable=False) # This is the correct field for Spotify Playlist ID
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    spotify_snapshot_id = db.Column(db.String(255), nullable=True) # Can be null if playlist not yet synced
    image_url = db.Column(db.String(512), nullable=True) # For storing the playlist cover image URL
    last_analyzed = db.Column(db.DateTime, nullable=True)
    overall_alignment_score = db.Column(db.Float, nullable=True)
    last_synced_from_spotify = db.Column(db.DateTime, nullable=True) # Tracks when the playlist was last synced from Spotify changes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = db.relationship('User', back_populates='playlists')
    song_associations = db.relationship('PlaylistSong', back_populates='playlist', cascade='all, delete-orphan')

    # Helper to easily get songs through the association
    @property
    def songs(self):
        return [association.song for association in sorted(self.song_associations, key=lambda x: x.track_position)]

    def __repr__(self):
        return f'<Playlist {self.name}>'

class Song(db.Model):
    __tablename__ = 'songs'
    id = db.Column(db.Integer, primary_key=True)
    spotify_id = db.Column(db.String(255), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    artist = db.Column(db.String(255), nullable=False)
    album = db.Column(db.String(255), nullable=True)
    lyrics = db.Column(db.Text, nullable=True)
    album_art_url = db.Column(db.String(512), nullable=True) # Add album art URL field
    explicit = db.Column(db.Boolean, default=False)
    last_analyzed = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    playlist_associations = db.relationship('PlaylistSong', back_populates='song')
    analysis_results = db.relationship('AnalysisResult', backref='song', lazy='dynamic', cascade="all, delete-orphan")

    def __repr__(self):
        return f'<Song {self.title} - {self.artist}>'

class AnalysisResult(db.Model):
    __tablename__ = 'analysis_results'
    id = db.Column(db.Integer, primary_key=True)
    song_id = db.Column(db.Integer, db.ForeignKey('songs.id'), nullable=False)
    themes = db.Column(db.JSON, nullable=True)  
    problematic_content = db.Column(db.JSON, nullable=True) 
    alignment_score = db.Column(db.Float, nullable=True) # Existing field, might be legacy or repurposed later
    raw_score = db.Column(db.Integer, nullable=True)  # New field for Christian framework score (0-100)
    concern_level = db.Column(db.String(50), nullable=True) # New field for High/Medium/Low concern
    explanation = db.Column(db.Text, nullable=True)
    analyzed_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Foreign key to bible_verses if we link themes directly to specific verses
    # bible_verse_id = db.Column(db.Integer, db.ForeignKey('bible_verses.id'), nullable=True)

    def __repr__(self):
        return f'<AnalysisResult for Song ID {self.song_id}>'

class Whitelist(db.Model):
    __tablename__ = 'whitelist'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    spotify_id = db.Column(db.String(255), nullable=False)  # For song, playlist, or artist Spotify ID
    item_type = db.Column(db.String(50), nullable=False)  # e.g., 'song', 'playlist', 'artist'
    name = db.Column(db.String(255), nullable=True) # Human-readable name of the item
    reason = db.Column(db.Text, nullable=True) # Optional reason for whitelisting
    added_date = db.Column(db.DateTime, default=datetime.utcnow)

    # Ensures a user cannot whitelist the same item of the same type multiple times.
    __table_args__ = (db.UniqueConstraint('user_id', 'spotify_id', 'item_type', name='_user_spotify_item_uc'),)

    def to_dict(self):
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
        return f'<Whitelist {self.item_type.capitalize()}: {self.spotify_id} for User ID {self.user_id}>'

class Blacklist(db.Model):
    __tablename__ = 'blacklist'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    spotify_id = db.Column(db.String(255), nullable=False)  # For song, playlist, or artist Spotify ID
    item_type = db.Column(db.String(50), nullable=False)  # e.g., 'song', 'playlist', 'artist'
    name = db.Column(db.String(255), nullable=True) # Human-readable name of the item
    reason = db.Column(db.Text, nullable=True) # Optional reason for blacklisting
    added_date = db.Column(db.DateTime, default=datetime.utcnow)

    # Ensures a user cannot blacklist the same item of the same type multiple times.
    __table_args__ = (db.UniqueConstraint('user_id', 'spotify_id', 'item_type', name='_user_spotify_item_blacklist_uc'),)

    def to_dict(self):
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
        return f'<Blacklist {self.item_type.capitalize()}: {self.spotify_id} for User ID {self.user_id}>'

class BibleVerse(db.Model):
    __tablename__ = 'bible_verses'
    id = db.Column(db.Integer, primary_key=True)
    book = db.Column(db.String(50), nullable=False)
    chapter = db.Column(db.Integer, nullable=False)
    verse_start = db.Column(db.Integer, nullable=False)
    verse_end = db.Column(db.Integer, nullable=True)
    text = db.Column(db.Text, nullable=False)
    theme_keywords = db.Column(db.JSON, nullable=True) 

    def __repr__(self):
        if self.verse_end:
            return f'<BibleVerse {self.book} {self.chapter}:{self.verse_start}-{self.verse_end}>'
        return f'<BibleVerse {self.book} {self.chapter}:{self.verse_start}>'
