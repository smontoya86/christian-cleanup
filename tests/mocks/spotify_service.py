"""
Mock Spotify Service for Testing

Provides a mock implementation of the SpotifyService that returns
controlled, deterministic responses for testing purposes. This allows
tests to run without making actual API calls to Spotify.
"""

import copy
from typing import Any, Dict, List, Optional, Union
from unittest.mock import MagicMock

from .base import BaseMockService, MockAPIError, MockAuthenticationError, MockRateLimitError
from ..fixtures.spotify_fixtures import (
    SPOTIFY_USER_PROFILE,
    SPOTIFY_PLAYLISTS_RESPONSE,
    SPOTIFY_PLAYLIST_DETAILS,
    SPOTIFY_PLAYLIST_TRACKS,
    SPOTIFY_TRACK_DETAILS,
    SPOTIFY_ERROR_RESPONSES,
    create_spotify_playlist,
    create_spotify_track,
    create_playlist_tracks_response,
    create_tracks_response
)


class MockSpotifyService(BaseMockService):
    """
    Mock implementation of SpotifyService for testing.
    
    Provides realistic responses without making actual HTTP requests
    to the Spotify Web API. Supports error injection and network
    condition simulation for robust testing.
    """
    
    def __init__(self, test_data: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize the mock Spotify service.
        
        Args:
            test_data: Custom test data to override defaults
            **kwargs: Additional arguments for BaseMockService
        """
        super().__init__(test_data, **kwargs)
        self.user = kwargs.get('user')
        self.access_token = kwargs.get('access_token', 'mock_access_token')
        self.sp = MagicMock()  # Mock spotipy client
        
        # Track state for operations that modify data
        self._playlists = copy.deepcopy(self.test_data['playlists'])
        self._playlist_tracks = copy.deepcopy(self.test_data['playlist_tracks'])
        self._should_fail = kwargs.get('should_fail', False)
        self._error_type = kwargs.get('error_type', 'server_error')
    
    def _default_test_data(self) -> Dict[str, Any]:
        """Return default test data for Spotify service."""
        return {
            'user_profile': SPOTIFY_USER_PROFILE,
            'playlists': SPOTIFY_PLAYLISTS_RESPONSE,
            'playlist_details': SPOTIFY_PLAYLIST_DETAILS,
            'playlist_tracks': SPOTIFY_PLAYLIST_TRACKS,
            'track_details': SPOTIFY_TRACK_DETAILS,
            'error_responses': SPOTIFY_ERROR_RESPONSES
        }
    
    def _maybe_raise_error(self, method_name: str) -> None:
        """Raise an error if configured to do so."""
        if self._should_fail:
            error_response = self.test_data['error_responses'].get(self._error_type, 
                                                                  self.test_data['error_responses']['server_error'])
            if self._error_type == 'unauthorized':
                raise MockAuthenticationError(error_response['error']['message'])
            elif self._error_type == 'rate_limit':
                raise MockRateLimitError(error_response['error'].get('retry_after', 60))
            else:
                raise MockAPIError(
                    error_response['error']['message'],
                    status_code=error_response['error']['status']
                )
    
    def get_user_profile(self) -> Optional[Dict[str, Any]]:
        """
        Mock implementation of get_user_profile.
        
        Returns:
            User profile data or None if error configured
        """
        self._simulate_network_call('get_user_profile')
        self._maybe_raise_error('get_user_profile')
        
        return copy.deepcopy(self.test_data['user_profile'])
    
    def get_user_playlists(self, limit: int = 20, offset: int = 0) -> Optional[Dict[str, Any]]:
        """
        Mock implementation of get_user_playlists.
        
        Args:
            limit: Maximum number of playlists to return
            offset: Pagination offset
            
        Returns:
            Playlists response data or None if error configured
        """
        self._simulate_network_call('get_user_playlists', limit=limit, offset=offset)
        self._maybe_raise_error('get_user_playlists')
        
        # Simulate pagination
        all_playlists = self._playlists['items']
        paginated_items = all_playlists[offset:offset + limit]
        
        response = copy.deepcopy(self._playlists)
        response['items'] = paginated_items
        response['limit'] = limit
        response['offset'] = offset
        response['total'] = len(all_playlists)
        
        # Set next/previous URLs
        if offset + limit < len(all_playlists):
            response['next'] = f"https://api.spotify.com/v1/me/playlists?offset={offset + limit}&limit={limit}"
        else:
            response['next'] = None
            
        if offset > 0:
            response['previous'] = f"https://api.spotify.com/v1/me/playlists?offset={max(0, offset - limit)}&limit={limit}"
        else:
            response['previous'] = None
        
        return response
    
    def get_playlist_items(self, playlist_id: str, fields: Optional[str] = None,
                          limit: int = 100, offset: int = 0) -> Optional[Dict[str, Any]]:
        """
        Mock implementation of get_playlist_items.
        
        Args:
            playlist_id: Spotify playlist ID
            fields: Fields to include (ignored in mock)
            limit: Maximum number of items to return
            offset: Pagination offset
            
        Returns:
            Playlist tracks data or None if error configured
        """
        self._simulate_network_call('get_playlist_items', 
                                   playlist_id=playlist_id, fields=fields,
                                   limit=limit, offset=offset)
        self._maybe_raise_error('get_playlist_items')
        
        # Get tracks for this playlist
        playlist_tracks = self._playlist_tracks.get(playlist_id, self.test_data['playlist_tracks'])
        all_items = playlist_tracks['items']
        
        # Simulate pagination
        paginated_items = all_items[offset:offset + limit]
        
        response = copy.deepcopy(playlist_tracks)
        response['items'] = paginated_items
        response['limit'] = limit
        response['offset'] = offset
        response['total'] = len(all_items)
        
        # Set pagination URLs
        if offset + limit < len(all_items):
            response['next'] = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks?offset={offset + limit}&limit={limit}"
        else:
            response['next'] = None
            
        if offset > 0:
            response['previous'] = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks?offset={max(0, offset - limit)}&limit={limit}"
        else:
            response['previous'] = None
        
        return response
    
    def get_playlist_tracks(self, playlist_id: str, fields: Optional[str] = None,
                           limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Mock implementation of get_playlist_tracks (simplified interface).
        
        Args:
            playlist_id: Spotify playlist ID
            fields: Fields to include (ignored in mock)
            limit: Maximum number of items to return per page
            offset: Starting offset
            
        Returns:
            List of track items or empty list if error
        """
        try:
            response = self.get_playlist_items(playlist_id, fields, limit, offset)
            if response:
                return response.get('items', [])
            return []
        except Exception:
            return []
    
    def get_playlist_details(self, user, spotify_playlist_id: str) -> Optional[Dict[str, Any]]:
        """
        Mock implementation of get_playlist_details.
        
        Args:
            user: User object (ignored in mock)
            spotify_playlist_id: Spotify playlist ID
            
        Returns:
            Playlist details or None if error configured
        """
        self._simulate_network_call('get_playlist_details', 
                                   user=user, spotify_playlist_id=spotify_playlist_id)
        self._maybe_raise_error('get_playlist_details')
        
        # Find playlist in our test data
        for playlist in self._playlists['items']:
            if playlist['id'] == spotify_playlist_id:
                return copy.deepcopy(playlist)
        
        # Return default playlist details if not found
        details = copy.deepcopy(self.test_data['playlist_details'])
        details['id'] = spotify_playlist_id
        return details
    
    def get_multiple_track_details(self, user, track_uris: List[str]) -> Optional[List[Dict[str, Any]]]:
        """
        Mock implementation of get_multiple_track_details.
        
        Args:
            user: User object (ignored in mock)
            track_uris: List of Spotify track URIs
            
        Returns:
            List of track details or None if error configured
        """
        self._simulate_network_call('get_multiple_track_details', 
                                   user=user, track_uris=track_uris)
        self._maybe_raise_error('get_multiple_track_details')
        
        tracks = []
        for i, uri in enumerate(track_uris):
            track_id = uri.split(':')[-1] if ':' in uri else uri
            
            # Try to find existing track data
            track_data = None
            for track in self.test_data['track_details']:
                if track['id'] == track_id:
                    track_data = copy.deepcopy(track)
                    break
            
            # Create mock track if not found
            if not track_data:
                track_data = create_spotify_track(
                    track_id=track_id,
                    name=f"Mock Track {i + 1}",
                    artist_name="Mock Artist",
                    album_name="Mock Album"
                )
            
            tracks.append(track_data)
        
        return tracks
    
    def sync_user_playlists_with_db(self, user_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Mock implementation of sync_user_playlists_with_db.
        
        Args:
            user_id: User ID to sync for (ignored in mock)
            
        Returns:
            List of playlist data
        """
        self._simulate_network_call('sync_user_playlists_with_db', user_id=user_id)
        self._maybe_raise_error('sync_user_playlists_with_db')
        
        return copy.deepcopy(self._playlists['items'])
    
    def add_tracks_to_spotify_playlist(self, user, spotify_playlist_id: str, 
                                     track_uris: List[str]) -> bool:
        """
        Mock implementation of add_tracks_to_spotify_playlist.
        
        Args:
            user: User object (ignored in mock)
            spotify_playlist_id: Target playlist ID
            track_uris: List of track URIs to add
            
        Returns:
            True if successful, False if error configured
        """
        self._simulate_network_call('add_tracks_to_spotify_playlist',
                                   user=user, spotify_playlist_id=spotify_playlist_id,
                                   track_uris=track_uris)
        try:
            self._maybe_raise_error('add_tracks_to_spotify_playlist')
        except Exception:
            return False
        
        # Simulate adding tracks (in real implementation this would update the playlist)
        return True
    
    def remove_tracks_from_spotify_playlist(self, user, spotify_playlist_id: str,
                                          track_uris: List[str]) -> bool:
        """
        Mock implementation of remove_tracks_from_spotify_playlist.
        
        Args:
            user: User object (ignored in mock)
            spotify_playlist_id: Target playlist ID
            track_uris: List of track URIs to remove
            
        Returns:
            True if successful, False if error configured
        """
        self._simulate_network_call('remove_tracks_from_spotify_playlist',
                                   user=user, spotify_playlist_id=spotify_playlist_id,
                                   track_uris=track_uris)
        try:
            self._maybe_raise_error('remove_tracks_from_spotify_playlist')
        except Exception:
            return False
        
        # Simulate removing tracks
        return True
    
    def reorder_tracks_in_spotify_playlist(self, user, spotify_playlist_id: str,
                                         range_start: int, insert_before: int,
                                         range_length: int = 1,
                                         snapshot_id: Optional[str] = None) -> Optional[str]:
        """
        Mock implementation of reorder_tracks_in_spotify_playlist.
        
        Args:
            user: User object (ignored in mock)
            spotify_playlist_id: Target playlist ID
            range_start: Start position of tracks to move
            insert_before: Position to insert at
            range_length: Number of tracks to move
            snapshot_id: Playlist snapshot ID
            
        Returns:
            New snapshot ID if successful, None if error configured
        """
        self._simulate_network_call('reorder_tracks_in_spotify_playlist',
                                   user=user, spotify_playlist_id=spotify_playlist_id,
                                   range_start=range_start, insert_before=insert_before,
                                   range_length=range_length, snapshot_id=snapshot_id)
        try:
            self._maybe_raise_error('reorder_tracks_in_spotify_playlist')
        except Exception:
            return None
        
        # Return a new mock snapshot ID
        return f"new_snapshot_{spotify_playlist_id}_{range_start}_{insert_before}"
    
    def replace_playlist_tracks(self, user, spotify_playlist_id: str,
                              track_uris: List[str]) -> Optional[str]:
        """
        Mock implementation of replace_playlist_tracks.
        
        Args:
            user: User object (ignored in mock)
            spotify_playlist_id: Target playlist ID
            track_uris: List of track URIs for new content
            
        Returns:
            New snapshot ID if successful, None if error configured
        """
        self._simulate_network_call('replace_playlist_tracks',
                                   user=user, spotify_playlist_id=spotify_playlist_id,
                                   track_uris=track_uris)
        try:
            self._maybe_raise_error('replace_playlist_tracks')
        except Exception:
            return None
        
        # Return a new mock snapshot ID
        return f"replaced_snapshot_{spotify_playlist_id}_{len(track_uris)}"
    
    def get_spotify_data(self, endpoint: str, access_token: str,
                        params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Mock implementation of get_spotify_data.
        
        Args:
            endpoint: API endpoint URL
            access_token: Access token
            params: Query parameters
            
        Returns:
            Mock response data
        """
        self._simulate_network_call('get_spotify_data',
                                   endpoint=endpoint, access_token=access_token,
                                   params=params)
        self._maybe_raise_error('get_spotify_data')
        
        # Return appropriate mock data based on endpoint
        if 'playlists' in endpoint:
            return copy.deepcopy(self._playlists)
        elif 'tracks' in endpoint:
            return {"tracks": copy.deepcopy(self.test_data['track_details'])}
        else:
            return {"mock_data": True, "endpoint": endpoint}
    
    # Configuration methods for testing
    def set_should_fail(self, should_fail: bool, error_type: str = 'server_error') -> None:
        """Configure the service to fail on the next operation."""
        self._should_fail = should_fail
        self._error_type = error_type
    
    def add_test_playlist(self, playlist_data: Dict[str, Any]) -> None:
        """Add a playlist to the mock data."""
        self._playlists['items'].append(playlist_data)
        self._playlists['total'] = len(self._playlists['items'])
    
    def add_test_tracks_to_playlist(self, playlist_id: str, tracks: List[Dict[str, Any]]) -> None:
        """Add tracks to a playlist in the mock data."""
        if playlist_id not in self._playlist_tracks:
            self._playlist_tracks[playlist_id] = create_playlist_tracks_response(playlist_id, [])
        
        for track in tracks:
            item = {
                "added_at": "2023-12-01T10:30:00Z",
                "added_by": {
                    "id": "test_user_123",
                    "external_urls": {"spotify": "https://open.spotify.com/user/test_user_123"},
                    "href": "https://api.spotify.com/v1/users/test_user_123",
                    "type": "user",
                    "uri": "spotify:user:test_user_123"
                },
                "is_local": False,
                "primary_color": None,
                "track": track,
                "video_thumbnail": {"url": None}
            }
            self._playlist_tracks[playlist_id]['items'].append(item)
        
        self._playlist_tracks[playlist_id]['total'] = len(self._playlist_tracks[playlist_id]['items'])
    
    def reset_mock_data(self) -> None:
        """Reset all mock data to defaults."""
        self._playlists = copy.deepcopy(self.test_data['playlists'])
        self._playlist_tracks = copy.deepcopy(self.test_data['playlist_tracks'])
        self._should_fail = False
        self._error_type = 'server_error'
        self.reset_call_tracking() 