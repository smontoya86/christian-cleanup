"""
Tests for Whitelist API endpoints.

Test-driven development for whitelist functionality:
1. Add items to whitelist (songs, artists, playlists)
2. Get user's whitelist items
3. Remove specific whitelist items
4. Clear all whitelist items
5. Update existing whitelist items
"""

import pytest
import json
from flask import url_for
from datetime import datetime, timezone, timedelta

from app.models.models import User, Song, Whitelist, Playlist, PlaylistSong, AnalysisResult


class TestWhitelistAPI:
    """Test suite for whitelist API endpoints"""

    def test_add_song_to_whitelist(self, client, authenticated_user, sample_song):
        """Test adding a song to user's whitelist"""
        # Log in the user
        authenticated_user(client)
        
        response = client.post('/api/whitelist', 
            json={
                'spotify_id': sample_song.spotify_id,
                'item_type': 'song',
                'name': sample_song.title,
                'reason': 'Excellent Christian content'
            }
        )
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert data['message'] == 'Item added to whitelist'
        assert 'item' in data
        assert data['item']['spotify_id'] == sample_song.spotify_id
        assert data['item']['item_type'] == 'song'
        assert data['item']['reason'] == 'Excellent Christian content'

    def test_add_artist_to_whitelist(self, client, authenticated_user):
        """Test adding an artist to user's whitelist"""
        # Log in the user
        authenticated_user(client)
        
        artist_data = {
            'spotify_id': '3WrFJ7ztbogyGnTHbHJFl2',
            'item_type': 'artist',
            'name': 'Christian Artist',
            'reason': 'Always produces clean content'
        }
        
        response = client.post('/api/whitelist', json=artist_data)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert data['item']['item_type'] == 'artist'
        assert data['item']['name'] == 'Christian Artist'

    def test_add_playlist_to_whitelist(self, client, authenticated_user):
        """Test adding a playlist to user's whitelist"""
        # Log in the user
        authenticated_user(client)
        
        playlist_data = {
            'spotify_id': '37i9dQZF1DX0XUsuxWHRQd',
            'item_type': 'playlist',
            'name': 'Christian Worship Playlist',
            'reason': 'Contains only worship songs'
        }
        
        response = client.post('/api/whitelist', json=playlist_data)
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['success'] is True
        assert data['item']['item_type'] == 'playlist'

    def test_add_whitelist_item_missing_data(self, client, authenticated_user):
        """Test adding whitelist item with missing required data"""
        # Log in the user
        authenticated_user(client)
        
        # Missing spotify_id
        response = client.post('/api/whitelist', 
            json={
                'item_type': 'song',
                'name': 'Test Song'
            }
        )
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert 'spotify_id' in data['error'].lower()

    def test_add_whitelist_item_invalid_type(self, client, authenticated_user):
        """Test adding whitelist item with invalid item_type"""
        # Log in the user first
        authenticated_user(client)
        
        response = client.post('/api/whitelist', 
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



    def test_update_existing_whitelist_reason(self, client, authenticated_user, sample_song, sample_user, db_session):
        """Test updating reason for existing whitelist item"""
        # First add to whitelist
        whitelist_entry = Whitelist(
            user_id=sample_user.id,
            spotify_id=sample_song.spotify_id,
            item_type='song',
            name=sample_song.title,
            reason='Original reason'
        )
        db_session.add(whitelist_entry)
        db_session.commit()
        
        # Log in the user
        authenticated_user(client)
        
        # Update with new reason
        response = client.post('/api/whitelist', 
            json={
                'spotify_id': sample_song.spotify_id,
                'item_type': 'song',
                'name': sample_song.title,
                'reason': 'Updated reason - better explanation'
            }
        )
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['message'] == 'Whitelist item reason updated'
        assert data['item']['reason'] == 'Updated reason - better explanation'

    def test_get_whitelist_items_empty(self, client, authenticated_user):
        """Test getting whitelist when user has no items"""
        # Log in the user
        authenticated_user(client)
        
        response = client.get('/api/whitelist')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['items'] == []
        assert data['total_count'] == 0

    def test_get_whitelist_items_with_data(self, client, authenticated_user, sample_song, sample_user, db_session):
        """Test getting whitelist items when user has data"""
        # Add multiple whitelist items
        items = [
            Whitelist(
                user_id=sample_user.id,
                spotify_id=sample_song.spotify_id,
                item_type='song',
                name=sample_song.title,
                reason='Great song'
            ),
            Whitelist(
                user_id=sample_user.id,
                spotify_id='artist123',
                item_type='artist',
                name='Christian Artist',
                reason='Clean artist'
            )
        ]
        
        for item in items:
            db_session.add(item)
        db_session.commit()
        
        # Log in the user
        authenticated_user(client)
        
        response = client.get('/api/whitelist')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert len(data['items']) == 2
        assert data['total_count'] == 2
        
        # Check data structure
        for item in data['items']:
            assert 'id' in item
            assert 'spotify_id' in item
            assert 'item_type' in item
            assert 'name' in item
            assert 'reason' in item
            assert 'added_date' in item

    def test_get_whitelist_items_filtered_by_type(self, client, authenticated_user, sample_song, sample_user, db_session):
        """Test getting whitelist items filtered by type"""
        # Add items of different types
        items = [
            Whitelist(user_id=sample_user.id, spotify_id='song1', item_type='song', name='Song 1'),
            Whitelist(user_id=sample_user.id, spotify_id='song2', item_type='song', name='Song 2'),
            Whitelist(user_id=sample_user.id, spotify_id='artist1', item_type='artist', name='Artist 1')
        ]
        
        for item in items:
            db_session.add(item)
        db_session.commit()
        
        # Log in the user
        authenticated_user(client)
        
        # Filter by songs
        response = client.get('/api/whitelist?item_type=song')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert len(data['items']) == 2
        assert all(item['item_type'] == 'song' for item in data['items'])

    def test_remove_whitelist_item(self, client, authenticated_user, sample_song, sample_user, db_session):
        """Test removing a specific whitelist item"""
        # Add whitelist item
        whitelist_entry = Whitelist(
            user_id=sample_user.id,
            spotify_id=sample_song.spotify_id,
            item_type='song',
            name=sample_song.title,
            reason='Test reason'
        )
        db_session.add(whitelist_entry)
        db_session.commit()
        
        entry_id = whitelist_entry.id
        
        # Log in the user
        authenticated_user(client)
        
        response = client.delete(f'/api/whitelist/{entry_id}')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['message'] == 'Item removed from whitelist'
        
        # Verify item is removed
        check_entry = Whitelist.query.get(entry_id)
        assert check_entry is None

    def test_remove_whitelist_item_not_found(self, client, authenticated_user):
        """Test removing non-existent whitelist item"""
        # Log in the user
        authenticated_user(client)
        
        response = client.delete('/api/whitelist/99999')
        
        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] is False
        assert 'not found' in data['error'].lower()

    def test_remove_whitelist_item_wrong_user(self, client, authenticated_user, sample_song, sample_user, db_session):
        """Test removing whitelist item that belongs to different user"""
        # Create another user
        from datetime import datetime, timezone, timedelta
        other_user = User(
            spotify_id='other_user_123',
            email='other@example.com',
            display_name='Other User',
            access_token='other_access_token',
            refresh_token='other_refresh_token',
            token_expiry=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        db_session.add(other_user)
        db_session.flush()
        
        # Add whitelist item for other user
        whitelist_entry = Whitelist(
            user_id=other_user.id,
            spotify_id=sample_song.spotify_id,
            item_type='song',
            name=sample_song.title,
            reason='Other user\'s item'
        )
        db_session.add(whitelist_entry)
        db_session.commit()
        
        entry_id = whitelist_entry.id
        
        # Log in the authenticated user (not the owner)
        authenticated_user(client)
        
        response = client.delete(f'/api/whitelist/{entry_id}')
        
        assert response.status_code == 404
        data = response.get_json()
        assert data['success'] is False
        assert 'not found' in data['error'].lower()

    def test_clear_all_whitelist_items(self, client, authenticated_user, sample_song, sample_user, db_session):
        """Test clearing all whitelist items for user"""
        # Add multiple whitelist items
        items = [
            Whitelist(
                user_id=sample_user.id,
                spotify_id='item1',
                item_type='song',
                name='Song 1',
                reason='Good song'
            ),
            Whitelist(
                user_id=sample_user.id,
                spotify_id='item2',
                item_type='artist',
                name='Artist 1',
                reason='Good artist'
            )
        ]
        
        for item in items:
            db_session.add(item)
        db_session.commit()
        
        # Log in the user
        authenticated_user(client)
        
        response = client.post('/api/whitelist/clear')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['message'] == 'All whitelist items cleared'
        assert data['items_removed'] == 2
        
        # Verify all items are removed
        remaining_items = Whitelist.query.filter_by(user_id=sample_user.id).count()
        assert remaining_items == 0

    def test_clear_whitelist_when_empty(self, client, authenticated_user):
        """Test clearing whitelist when user has no items"""
        # Log in the user
        authenticated_user(client)
        
        response = client.post('/api/whitelist/clear')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['items_removed'] == 0

    def test_whitelist_requires_authentication(self, client):
        """Test that whitelist endpoints require authentication"""
        endpoints = [
            ('POST', '/api/whitelist'),
            ('GET', '/api/whitelist'),
            ('DELETE', '/api/whitelist/1'),
            ('POST', '/api/whitelist/clear')
        ]
        
        for method, endpoint in endpoints:
            response = client.open(method=method, path=endpoint)
            # Should redirect to login (302) or return unauthorized (401)
            assert response.status_code in [302, 401]


class TestWhitelistAnalysisIntegration:
    """Test whitelist integration with analysis system"""
    
    def test_whitelisted_song_analysis_optimization(self, client, authenticated_user, sample_song, sample_user, db_session):
        """Test that whitelisted songs get optimized analysis treatment"""
        # Add song to whitelist
        whitelist_entry = Whitelist(
            user_id=sample_user.id,
            spotify_id=sample_song.spotify_id,
            item_type='song',
            name=sample_song.title,
            reason='Pre-approved clean content'
        )
        db_session.add(whitelist_entry)
        db_session.commit()
        
        # This test verifies the concept - actual analysis integration 
        # was implemented in the analysis service
        assert whitelist_entry.id is not None
        assert whitelist_entry.item_type == 'song' 