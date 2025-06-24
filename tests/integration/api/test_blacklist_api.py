"""
Tests for Blacklist API endpoints.

Test-driven development for blacklist functionality:
1. Add items to blacklist (songs, artists, playlists)
2. Get user's blacklist items
3. Remove specific blacklist items
4. Clear all blacklist items
5. Integration with whitelist (mutual exclusivity)
"""

import pytest
import json
from flask import url_for
from datetime import datetime, timezone, timedelta

from app.models.models import User, Song, Blacklist, Whitelist, Playlist, PlaylistSong, AnalysisResult


class TestBlacklistAPI:
    """Test suite for blacklist API endpoints"""

    def test_add_song_to_blacklist(self, client, authenticated_user, sample_song):
        """Test adding a song to user's blacklist"""
        # Log in the user
        authenticated_user(client)
        
        response = client.post('/api/blacklist', 
            json={
                'spotify_id': sample_song.spotify_id,
                'item_type': 'song',
                'name': sample_song.title,
                'reason': 'Inappropriate content'
            }
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert data['message'] == 'Item added to blacklist'
        assert 'item' in data
        assert data['item']['spotify_id'] == sample_song.spotify_id
        assert data['item']['item_type'] == 'song'
        assert data['item']['reason'] == 'Inappropriate content'

    def test_add_artist_to_blacklist(self, client, authenticated_user):
        """Test adding an artist to user's blacklist"""
        # Log in the user
        authenticated_user(client)
        
        artist_data = {
            'spotify_id': '3WrFJ7ztbogyGnTHbHJFl2',
            'item_type': 'artist',
            'name': 'Test Artist',
            'reason': 'Artist contains explicit content'
        }
        
        response = client.post('/api/blacklist', json=artist_data)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert data['item']['item_type'] == 'artist'
        assert data['item']['name'] == 'Test Artist'

    def test_add_playlist_to_blacklist(self, client, authenticated_user):
        """Test adding a playlist to user's blacklist"""
        # Log in the user
        authenticated_user(client)
        
        playlist_data = {
            'spotify_id': '37i9dQZF1DX0XUsuxWHRQd',
            'item_type': 'playlist',
            'name': 'Inappropriate Playlist',
            'reason': 'Contains inappropriate songs'
        }
        
        response = client.post('/api/blacklist', json=playlist_data)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert data['item']['item_type'] == 'playlist'

    def test_add_blacklist_item_missing_data(self, client, authenticated_user):
        """Test adding blacklist item with missing required data"""
        # Log in the user
        authenticated_user(client)
        
        # Missing spotify_id
        response = client.post('/api/blacklist', 
            json={
                'item_type': 'song',
                'name': 'Test Song'
            }
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'spotify_id' in data['error'].lower()

    def test_add_blacklist_item_invalid_type(self, client, authenticated_user):
        """Test adding blacklist item with invalid item_type"""
        response = client.post('/api/blacklist', 
            json={
                'spotify_id': 'test123',
                'item_type': 'invalid_type',
                'name': 'Test Item'
            }
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'item_type' in data['error'].lower()

    def test_move_from_whitelist_to_blacklist(self, client, authenticated_user, sample_song, db_session):
        """Test that adding to blacklist moves item from whitelist"""
        # First add to whitelist
        whitelist_entry = Whitelist(
            user_id=authenticated_user.id,
            spotify_id=sample_song.spotify_id,
            item_type='song',
            name=sample_song.title,
            reason='Good song'
        )
        db_session.add(whitelist_entry)
        db_session.commit()
        
        # Now add to blacklist (should move from whitelist)
        response = client.post('/api/blacklist', 
            json={
                'spotify_id': sample_song.spotify_id,
                'item_type': 'song',
                'name': sample_song.title,
                'reason': 'Changed mind - inappropriate'
            }
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['message'] == 'Item moved from whitelist to blacklist'
        
        # Verify whitelist entry is removed
        whitelist_check = Whitelist.query.filter_by(
            user_id=authenticated_user.id,
            spotify_id=sample_song.spotify_id,
            item_type='song'
        ).first()
        assert whitelist_check is None
        
        # Verify blacklist entry exists
        blacklist_check = Blacklist.query.filter_by(
            user_id=authenticated_user.id,
            spotify_id=sample_song.spotify_id,
            item_type='song'
        ).first()
        assert blacklist_check is not None

    def test_update_existing_blacklist_reason(self, client, authenticated_user, sample_song, db_session):
        """Test updating reason for existing blacklist item"""
        # First add to blacklist
        blacklist_entry = Blacklist(
            user_id=authenticated_user.id,
            spotify_id=sample_song.spotify_id,
            item_type='song',
            name=sample_song.title,
            reason='Original reason'
        )
        db_session.add(blacklist_entry)
        db_session.commit()
        
        # Update with new reason
        response = client.post('/api/blacklist', 
            json={
                'spotify_id': sample_song.spotify_id,
                'item_type': 'song',
                'name': sample_song.title,
                'reason': 'Updated reason'
            }
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['message'] == 'Blacklist item reason updated'
        assert data['item']['reason'] == 'Updated reason'

    def test_get_blacklist_items_empty(self, client, authenticated_user):
        """Test getting blacklist when user has no items"""
        # Log in the user
        authenticated_user(client)
        
        response = client.get('/api/blacklist')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['items'] == []
        assert data['total_count'] == 0

    def test_get_blacklist_items_with_data(self, client, authenticated_user, sample_song, db_session):
        """Test getting blacklist items when user has blacklisted items"""
        # Add multiple blacklist items
        song_entry = Blacklist(
            user_id=authenticated_user.id,
            spotify_id=sample_song.spotify_id,
            item_type='song',
            name=sample_song.title,
            reason='Inappropriate content'
        )
        
        artist_entry = Blacklist(
            user_id=authenticated_user.id,
            spotify_id='artist123',
            item_type='artist',
            name='Bad Artist',
            reason='Explicit artist'
        )
        
        db_session.add_all([song_entry, artist_entry])
        db_session.commit()
        
        response = client.get('/api/blacklist')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['total_count'] == 2
        assert len(data['items']) == 2
        
        # Check song entry
        song_item = next(item for item in data['items'] if item['item_type'] == 'song')
        assert song_item['spotify_id'] == sample_song.spotify_id
        assert song_item['name'] == sample_song.title
        assert song_item['reason'] == 'Inappropriate content'
        
        # Check artist entry
        artist_item = next(item for item in data['items'] if item['item_type'] == 'artist')
        assert artist_item['spotify_id'] == 'artist123'
        assert artist_item['name'] == 'Bad Artist'

    def test_get_blacklist_items_filtered_by_type(self, client, authenticated_user, sample_song, db_session):
        """Test getting blacklist items filtered by item_type"""
        # Add multiple types
        song_entry = Blacklist(
            user_id=authenticated_user.id,
            spotify_id=sample_song.spotify_id,
            item_type='song',
            name=sample_song.title
        )
        
        artist_entry = Blacklist(
            user_id=authenticated_user.id,
            spotify_id='artist123',
            item_type='artist',
            name='Bad Artist'
        )
        
        db_session.add_all([song_entry, artist_entry])
        db_session.commit()
        
        # Filter by song type
        response = client.get('/api/blacklist?item_type=song')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['total_count'] == 1
        assert len(data['items']) == 1
        assert data['items'][0]['item_type'] == 'song'

    def test_remove_blacklist_item(self, client, authenticated_user, sample_song, db_session):
        """Test removing a specific item from blacklist"""
        # Add to blacklist first
        blacklist_entry = Blacklist(
            user_id=authenticated_user.id,
            spotify_id=sample_song.spotify_id,
            item_type='song',
            name=sample_song.title,
            reason='Test reason'
        )
        db_session.add(blacklist_entry)
        db_session.commit()
        
        # Remove from blacklist
        response = client.delete(f'/api/blacklist/{blacklist_entry.id}')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['message'] == f'Removed \'{sample_song.title}\' from blacklist'
        
        # Verify it's removed
        check_entry = Blacklist.query.filter_by(id=blacklist_entry.id).first()
        assert check_entry is None

    def test_remove_blacklist_item_not_found(self, client, authenticated_user):
        """Test removing a blacklist item that doesn't exist"""
        response = client.delete('/api/blacklist/999999')
        
        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] is False
        assert 'not found' in data['error'].lower()

    def test_remove_blacklist_item_wrong_user(self, client, authenticated_user, sample_song, db_session):
        """Test that users can only remove their own blacklist items"""
        # Create another user
        other_user = User(
            spotify_id='other_user_123',
            display_name='Other User',
            email='other@test.com',
            access_token='other_token_123',
            refresh_token='other_refresh_123',
            token_expiry=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        db_session.add(other_user)
        db_session.commit()
        
        # Add to other user's blacklist
        other_blacklist_entry = Blacklist(
            user_id=other_user.id,
            spotify_id=sample_song.spotify_id,
            item_type='song',
            name=sample_song.title
        )
        db_session.add(other_blacklist_entry)
        db_session.commit()
        
        # Try to remove other user's blacklist item
        response = client.delete(f'/api/blacklist/{other_blacklist_entry.id}')
        
        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] is False

    def test_clear_all_blacklist_items(self, client, authenticated_user, sample_song, db_session):
        """Test clearing all blacklist items for user"""
        # Add multiple blacklist items
        entries = [
            Blacklist(
                user_id=authenticated_user.id,
                spotify_id=sample_song.spotify_id,
                item_type='song',
                name=sample_song.title
            ),
            Blacklist(
                user_id=authenticated_user.id,
                spotify_id='artist123',
                item_type='artist',
                name='Bad Artist'
            ),
            Blacklist(
                user_id=authenticated_user.id,
                spotify_id='playlist123',
                item_type='playlist',
                name='Bad Playlist'
            )
        ]
        
        db_session.add_all(entries)
        db_session.commit()
        
        # Clear all blacklist items
        response = client.post('/api/blacklist/clear')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['message'] == 'Cleared 3 items from blacklist'
        assert data['items_removed'] == 3
        
        # Verify all items are removed
        remaining_count = Blacklist.query.filter_by(user_id=authenticated_user.id).count()
        assert remaining_count == 0

    def test_clear_blacklist_when_empty(self, client, authenticated_user):
        """Test clearing blacklist when user has no items"""
        response = client.post('/api/blacklist/clear')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['message'] == 'Cleared 0 items from blacklist'
        assert data['items_removed'] == 0

    def test_blacklist_requires_authentication(self, client):
        """Test that blacklist endpoints require authentication"""
        endpoints = [
            ('POST', '/api/blacklist'),
            ('GET', '/api/blacklist'),
            ('DELETE', '/api/blacklist/1'),
            ('POST', '/api/blacklist/clear')
        ]
        
        for method, endpoint in endpoints:
            response = client.open(endpoint, method=method)
            # Should redirect to login (302) or return unauthorized (401)
            assert response.status_code in [302, 401]


class TestBlacklistAnalysisIntegration:
    """Test blacklist integration with analysis workflow"""

    def test_blacklisted_song_analysis_skipped(self, client, authenticated_user, sample_song, db_session):
        """Test that blacklisted songs skip analysis"""
        # Add song to blacklist
        blacklist_entry = Blacklist(
            user_id=authenticated_user.id,
            spotify_id=sample_song.spotify_id,
            item_type='song',
            name=sample_song.title,
            reason='Inappropriate content'
        )
        db_session.add(blacklist_entry)
        db_session.commit()
        
        # Try to analyze the blacklisted song
        response = client.post(f'/api/songs/{sample_song.id}/analyze')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        # Should indicate blacklisted status
        assert 'blacklisted' in data['message'].lower() or data.get('status') == 'blacklisted'

    def test_blacklisted_artist_songs_skipped(self, client, authenticated_user, sample_song, db_session):
        """Test that songs from blacklisted artists are skipped"""
        # Add artist to blacklist
        artist_blacklist = Blacklist(
            user_id=authenticated_user.id,
            spotify_id='artist_spotify_id_123',  # Different from song's artist
            item_type='artist',
            name=sample_song.artist,  # But same name
            reason='Inappropriate artist'
        )
        db_session.add(artist_blacklist)
        db_session.commit()
        
        # This test assumes the analysis service checks artist blacklist
        # Implementation may vary based on how artist matching is done
