"""
Spotify API integration service

Handles authentication and API calls to Spotify Web API
"""

import requests
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any

from .. import db
from ..models import User, Playlist, Song, PlaylistSong


class SpotifyService:
    """Service for interacting with Spotify Web API"""
    
    BASE_URL = 'https://api.spotify.com/v1'
    
    def __init__(self, user: User):
        self.user = user
        self._ensure_valid_token()
    
    def _ensure_valid_token(self):
        """Ensure user has a valid access token"""
        if not self.user.access_token:
            raise ValueError("User has no access token")
        
        # Check if token is expired (with 5 minute buffer)
        if self.user.token_expiry:
            # Handle both naive and timezone-aware datetimes
            token_expiry = self.user.token_expiry
            if token_expiry.tzinfo is None:
                # If naive, assume UTC
                token_expiry = token_expiry.replace(tzinfo=timezone.utc)
            
            if token_expiry < datetime.now(timezone.utc) + timedelta(minutes=5):
                self._refresh_token()
    
    def _refresh_token(self):
        """Refresh the user's access token"""
        if not self.user.refresh_token:
            raise ValueError("No refresh token available")
        
        from flask import current_app
        
        token_data = {
            'grant_type': 'refresh_token',
            'refresh_token': self.user.refresh_token,
            'client_id': current_app.config['SPOTIFY_CLIENT_ID'],
            'client_secret': current_app.config['SPOTIFY_CLIENT_SECRET']
        }
        
        response = requests.post('https://accounts.spotify.com/api/token', data=token_data)
        response.raise_for_status()
        token_info = response.json()
        
        # Update user tokens
        self.user.access_token = token_info['access_token']
        if 'refresh_token' in token_info:
            self.user.refresh_token = token_info['refresh_token']
        self.user.token_expiry = datetime.now(timezone.utc) + timedelta(seconds=token_info['expires_in'])
        
        db.session.commit()
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[Any, Any]:
        """Make an authenticated request to Spotify API"""
        url = f"{self.BASE_URL}/{endpoint.lstrip('/')}"
        headers = kwargs.get('headers', {})
        headers.update({'Authorization': f'Bearer {self.user.access_token}'})
        kwargs['headers'] = headers
        
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()
    
    def get_user_playlists(self) -> List[Dict[str, Any]]:
        """Get user's playlists from Spotify with optimized field selection"""
        playlists = []
        url = 'me/playlists'
        
        # Use fields parameter to only fetch what we need
        fields = 'items(id,name,description,images,owner(id),collaborative,tracks(total)),next,total'
        
        while url:
            params = {
                'limit': 50,  # Maximum allowed by Spotify API
                'fields': fields
            }
            
            data = self._make_request('GET', url, params=params)
            playlists.extend(data['items'])
            
            url = data['next']
            if url:
                # Extract just the endpoint from the full URL
                url = url.replace(self.BASE_URL + '/', '')
        
        return playlists
    
    def get_playlist_tracks(self, playlist_id: str) -> List[Dict[str, Any]]:
        """Get tracks from a specific playlist with optimized field selection"""
        tracks = []
        url = f'playlists/{playlist_id}/tracks'
        
        # Use fields parameter to only fetch what we need, following Spotify API best practices
        fields = 'items(track(id,name,artists(name),album(name,images),duration_ms,explicit,type)),next,total'
        
        while url:
            params = {
                'limit': 50,  # Maximum allowed by Spotify API
                'fields': fields
            }
            
            data = self._make_request('GET', url, params=params)
            
            # Filter out null/unavailable tracks immediately
            valid_tracks = [item for item in data['items'] if item['track'] and item['track'].get('id')]
            tracks.extend(valid_tracks)
            
            url = data['next']
            if url:
                # Extract just the endpoint from the full URL
                url = url.replace(self.BASE_URL + '/', '')
        
        return tracks
    
    def sync_user_playlists(self) -> int:
        """Sync user's playlists from Spotify to database"""
        spotify_playlists = self.get_user_playlists()
        synced_count = 0
        
        for spotify_playlist in spotify_playlists:
            # Only sync playlists owned by the user or collaborative
            if (spotify_playlist['owner']['id'] != self.user.spotify_id and 
                not spotify_playlist.get('collaborative', False)):
                continue
            
            # Check if playlist already exists
            playlist = Playlist.query.filter_by(
                owner_id=self.user.id,
                spotify_id=spotify_playlist['id']
            ).first()
            
            if not playlist:
                playlist = Playlist(
                    owner_id=self.user.id,
                    spotify_id=spotify_playlist['id'],
                    name=spotify_playlist['name'],
                    description=spotify_playlist.get('description', ''),
                    image_url=spotify_playlist['images'][0]['url'] if spotify_playlist['images'] else None,
                    created_at=datetime.now(timezone.utc)
                )
                db.session.add(playlist)
                db.session.flush()  # Get the ID
            else:
                # Update existing playlist
                playlist.name = spotify_playlist['name']
                playlist.description = spotify_playlist.get('description', '')
                playlist.image_url = spotify_playlist['images'][0]['url'] if spotify_playlist['images'] else None
            
            # Sync tracks
            self._sync_playlist_tracks(playlist, spotify_playlist['id'])
            synced_count += 1
        
        db.session.commit()
        return synced_count
    
    def _sync_playlist_tracks(self, playlist: Playlist, spotify_playlist_id: str):
        """Sync tracks for a specific playlist"""
        try:
            spotify_tracks = self.get_playlist_tracks(spotify_playlist_id)
            
            # Clear existing tracks in a separate transaction
            PlaylistSong.query.filter_by(playlist_id=playlist.id).delete()
            db.session.flush()  # Ensure deletion is committed before adding new tracks
            
            # Track existing songs to avoid duplicate queries
            existing_songs = {}
            
            for position, track_item in enumerate(spotify_tracks):
                track = track_item['track']
                if not track or track['type'] != 'track':
                    continue
                
                # Skip tracks without valid spotify_id (unavailable tracks)
                spotify_id = track.get('id')
                if not spotify_id:
                    continue
                
                # Check if we've already processed this song in this sync
                if spotify_id in existing_songs:
                    song = existing_songs[spotify_id]
                else:
                    # Check if song already exists in database
                    song = Song.query.filter_by(spotify_id=spotify_id).first()
                    
                    if not song:
                        # Extract album art URL from the album images
                        album_art_url = None
                        if track['album'].get('images'):
                            # Use the first (largest) image
                            album_art_url = track['album']['images'][0]['url']
                        
                        song = Song(
                            spotify_id=spotify_id,
                            title=track['name'],
                            artist=', '.join([artist['name'] for artist in track['artists']]),
                            album=track['album']['name'],
                            album_art_url=album_art_url,
                            duration_ms=track['duration_ms'],
                            explicit=track.get('explicit', False)
                        )
                        db.session.add(song)
                        db.session.flush()  # Get the ID
                    
                    existing_songs[spotify_id] = song
                
                # Check if this playlist-song relationship already exists
                existing_ps = PlaylistSong.query.filter_by(
                    playlist_id=playlist.id,
                    song_id=song.id
                ).first()
                
                if not existing_ps:
                    # Add to playlist
                    playlist_song = PlaylistSong(
                        playlist_id=playlist.id,
                        song_id=song.id,
                        track_position=position
                    )
                    db.session.add(playlist_song)
                    
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f'Error syncing playlist tracks for playlist {playlist.id}: {e}')
            db.session.rollback()
            raise
    
    def remove_song_from_playlist(self, spotify_playlist_id: str, song_id: int) -> bool:
        """Remove a song from a Spotify playlist"""
        try:
            song = Song.query.get(song_id)
            if not song or not song.spotify_id:
                return False
            
            # Remove from Spotify
            data = {
                'tracks': [{'uri': f'spotify:track:{song.spotify_id}'}]
            }
            
            self._make_request(
                'DELETE',
                f'playlists/{spotify_playlist_id}/tracks',
                json=data
            )
            
            return True
        except Exception as e:
            from flask import current_app
            current_app.logger.error(f'Error removing song from Spotify playlist: {e}')
            return False
    
    def get_user_profile(self) -> Dict[str, Any]:
        """Get user's Spotify profile"""
        return self._make_request('GET', 'me')
    
    def search_tracks(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for tracks on Spotify"""
        params = {
            'q': query,
            'type': 'track',
            'limit': limit
        }
        
        data = self._make_request('GET', 'search', params=params)
        return data['tracks']['items'] 