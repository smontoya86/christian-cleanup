import pytest
import json
from flask import url_for
from flask_login import login_user, logout_user
from datetime import datetime, timedelta

from app import db
from app.models import User, Whitelist, Blacklist
from app.services.whitelist_service import ITEM_ADDED, ITEM_ALREADY_EXISTS, ITEM_MOVED_FROM_BLACKLIST, REASON_UPDATED, INVALID_INPUT

# Assuming standard fixtures like 'client', 'app', 'new_user' are available from conftest.py
# 'new_user' fixture should create a user in the db

def test_add_whitelist_item_success(client, app, new_user):
    """Test successfully adding a new song to the whitelist via API."""
    spotify_id = "api_add_song_1"
    item_type = "song"
    name = "API Add Song"
    reason = "Testing API add"

    with app.test_request_context():
        login_user(new_user)
        response = client.post(url_for('api.add_whitelist_item'), json={
            'spotify_id': spotify_id,
            'item_type': item_type,
            'name': name,
            'reason': reason
        })
        logout_user()

    assert response.status_code == 201
    data = response.get_json()
    assert data['message'] == 'Item added to whitelist'
    assert 'item' in data
    assert data['item']['spotify_id'] == spotify_id
    assert data['item']['name'] == name
    assert data['item']['reason'] == reason

    # Verify in DB
    entry = Whitelist.query.filter_by(user_id=new_user.id, spotify_id=spotify_id).first()
    assert entry is not None
    assert entry.name == name
    assert entry.reason == reason

def test_add_whitelist_item_existing(client, app, new_user):
    """Test adding an item that already exists in the whitelist via API."""
    spotify_id = "api_add_existing_song"
    item_type = "song"
    name = "API Existing Song"
    reason_initial = "Initial reason"
    reason_updated = "Updated reason"

    # Add item initially
    initial_entry = Whitelist(user_id=new_user.id, spotify_id=spotify_id, item_type=item_type, name=name, reason=reason_initial)
    db.session.add(initial_entry)
    db.session.commit()

    with app.test_request_context():
        login_user(new_user)
        response = client.post(url_for('api.add_whitelist_item'), json={
            'spotify_id': spotify_id,
            'item_type': item_type,
            'name': name, # Name can be optional if exists
            'reason': reason_updated
        })
        logout_user()

    assert response.status_code == 200
    data = response.get_json()
    assert data['message'] == 'Whitelist item reason updated'
    assert 'item' in data
    assert data['item']['reason'] == reason_updated

    # Verify in DB
    entry = Whitelist.query.filter_by(user_id=new_user.id, spotify_id=spotify_id).first()
    assert entry is not None
    assert entry.reason == reason_updated

def test_add_whitelist_item_move_from_blacklist(client, app, new_user):
    """Test adding an item that exists in the blacklist via API."""
    spotify_id = "api_move_from_blacklist_song"
    item_type = "song"
    name = "API Move Song"
    reason = "Moving from blacklist"

    # Add to blacklist first
    blacklist_entry = Blacklist(user_id=new_user.id, spotify_id=spotify_id, item_type=item_type, name=name, reason="Was bad")
    db.session.add(blacklist_entry)
    db.session.commit()

    assert Blacklist.query.filter_by(user_id=new_user.id, spotify_id=spotify_id).count() == 1

    with app.test_request_context():
        login_user(new_user)
        response = client.post(url_for('api.add_whitelist_item'), json={
            'spotify_id': spotify_id,
            'item_type': item_type,
            'name': name,
            'reason': reason
        })
        logout_user()

    assert response.status_code == 200 # Moved, not created
    data = response.get_json()
    assert data['message'] == 'Item moved from blacklist to whitelist'
    assert 'item' in data
    assert data['item']['reason'] == reason

    # Verify in DB
    assert Whitelist.query.filter_by(user_id=new_user.id, spotify_id=spotify_id).count() == 1
    assert Blacklist.query.filter_by(user_id=new_user.id, spotify_id=spotify_id).count() == 0

def test_add_whitelist_item_invalid_input(client, app, new_user):
    """Test adding an item with missing required fields via API."""
    with app.test_request_context():
        login_user(new_user)
        # Missing item_type
        response = client.post(url_for('api.add_whitelist_item'), json={
            'spotify_id': 'invalid_api_add',
            'name': 'Invalid'
        })
        logout_user()

    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    assert data['error'] == 'Missing required fields: spotify_id and item_type'
    # Check DB state? Should not have added anything
    assert Whitelist.query.filter_by(user_id=new_user.id, spotify_id='invalid_api_add').count() == 0

def test_add_whitelist_item_unauthorized(client, app):
    """Test adding an item without being logged in via API."""
    response = client.post(url_for('api.add_whitelist_item'), json={
        'spotify_id': 'unauth_api_add',
        'item_type': 'song',
        'name': 'Unauthorized Add'
    })

    assert response.status_code == 401 # Unauthorized
    # Optionally check response body if login_required handler returns JSON

def test_add_whitelist_item_invalid_type(client, app, new_user):
    """Test adding an item with an invalid item_type via API."""
    with app.test_request_context():
        login_user(new_user)
        response = client.post(url_for('api.add_whitelist_item'), json={
            'spotify_id': 'invalid_type_api',
            'item_type': 'playlist', # Assuming 'playlist' is not a valid type
            'name': 'Invalid Type Add'
        })
        logout_user()

    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    assert data['error'] == 'Invalid item_type. Must be song, artist, or album.'

def test_get_whitelist_success(client, app, new_user):
    """Test successfully retrieving all whitelist items via API."""
    # Add some items for the user
    item1 = Whitelist(user_id=new_user.id, spotify_id="get_song_1", item_type="song", name="Get Song 1")
    item2 = Whitelist(user_id=new_user.id, spotify_id="get_artist_1", item_type="artist", name="Get Artist 1")
    db.session.add_all([item1, item2])
    db.session.commit()

    with app.test_request_context():
        login_user(new_user)
        response = client.get(url_for('api.get_whitelist'))
        logout_user()

    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert any(item['spotify_id'] == 'get_song_1' for item in data)
    assert any(item['spotify_id'] == 'get_artist_1' for item in data)

def test_get_whitelist_filtered_by_type(client, app, new_user):
    """Test retrieving whitelist items filtered by type via API."""
    # Add items
    item1 = Whitelist(user_id=new_user.id, spotify_id="filter_song_1", item_type="song", name="Filter Song 1")
    item2 = Whitelist(user_id=new_user.id, spotify_id="filter_artist_1", item_type="artist", name="Filter Artist 1")
    db.session.add_all([item1, item2])
    db.session.commit()

    with app.test_request_context():
        login_user(new_user)
        # Filter for 'song'
        response = client.get(url_for('api.get_whitelist', type='song'))
        logout_user()

    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]['spotify_id'] == 'filter_song_1'
    assert data[0]['item_type'] == 'song'

def test_get_whitelist_empty(client, app, new_user):
    """Test retrieving an empty whitelist via API."""
    # Ensure user has no items
    Whitelist.query.filter_by(user_id=new_user.id).delete()
    db.session.commit()

    with app.test_request_context():
        login_user(new_user)
        response = client.get(url_for('api.get_whitelist'))
        logout_user()

    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
    assert len(data) == 0

def test_get_whitelist_unauthorized(client, app):
    """Test retrieving whitelist without authentication via API."""
    response = client.get(url_for('api.get_whitelist'))

    assert response.status_code == 401
    data = response.get_json()
    assert data['error'] == 'Unauthorized'

def test_delete_whitelist_item_success(client, app, new_user):
    """Test successfully deleting a whitelist item by ID via API."""
    # Add an item to delete
    item_to_delete = Whitelist(user_id=new_user.id, spotify_id="delete_song_1", item_type="song", name="Delete Song 1")
    db.session.add(item_to_delete)
    db.session.commit()
    entry_id = item_to_delete.id

    # Verify it exists before delete
    assert db.session.get(Whitelist, entry_id) is not None

    with app.test_request_context():
        login_user(new_user)
        response = client.delete(url_for('api.remove_whitelist_item', entry_id=entry_id))
        logout_user()

    assert response.status_code == 200
    data = response.get_json()
    assert data['message'] == 'Item successfully removed from whitelist.'

    # Verify it's gone from DB
    assert db.session.get(Whitelist, entry_id) is None

def test_delete_whitelist_item_not_found(client, app, new_user):
    """Test deleting a whitelist item that does not exist via API."""
    non_existent_id = 99999

    with app.test_request_context():
        login_user(new_user)
        response = client.delete(url_for('api.remove_whitelist_item', entry_id=non_existent_id))
        logout_user()

    assert response.status_code == 404
    data = response.get_json()
    assert data['error'] == 'Whitelist entry not found.'

def test_delete_whitelist_item_wrong_user(client, app, new_user):
    """Test deleting a whitelist item belonging to another user via API."""
    # Create another user and their item
    other_user = User(spotify_id='other_user_spotify', display_name='Other User')
    other_user.access_token = "dummy_access_token"
    other_user.token_expiry = datetime.utcnow() + timedelta(hours=1)
    db.session.add(other_user)
    db.session.commit() # Commit to get other_user.id

    other_item = Whitelist(user_id=other_user.id, spotify_id="other_user_song", item_type="song", name="Other Song")
    db.session.add(other_item)
    db.session.commit()
    other_entry_id = other_item.id

    # Verify item exists
    assert db.session.get(Whitelist, other_entry_id) is not None

    # Log in as 'new_user' and try to delete 'other_user's item
    with app.test_request_context():
        login_user(new_user)
        response = client.delete(url_for('api.remove_whitelist_item', entry_id=other_entry_id))
        logout_user()

    assert response.status_code == 404 # Should be treated as not found for the logged-in user
    data = response.get_json()
    assert data['error'] == 'Whitelist entry not found.'

    # Verify item still exists in DB (belonging to other_user)
    assert db.session.get(Whitelist, other_entry_id) is not None

def test_delete_whitelist_item_unauthorized(client, app):
    """Test deleting a whitelist item without authentication via API."""
    # No need to create an item, just need an ID
    entry_id = 123
    response = client.delete(url_for('api.remove_whitelist_item', entry_id=entry_id))

    assert response.status_code == 401
    data = response.get_json()
    assert data['error'] == 'Unauthorized'
