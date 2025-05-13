import pytest
from app import db
from app.models import User, Whitelist, Blacklist
from app.services.whitelist_service import (
    add_to_whitelist,
    ITEM_ADDED, ITEM_ALREADY_EXISTS, ITEM_MOVED_FROM_BLACKLIST, REASON_UPDATED, ERROR_OCCURRED,
    remove_from_whitelist, ITEM_REMOVED, ITEM_NOT_FOUND, INVALID_INPUT,
    is_whitelisted, get_user_whitelist, get_whitelist_entry_by_id
)

def test_add_new_item_to_whitelist(db_session, new_user):
    """Test adding a completely new item to the whitelist."""
    user_id = new_user.id
    spotify_id = "new_song_123"
    item_type = "song"
    name = "Test Song"
    reason = "Testing add"

    status, result = add_to_whitelist(user_id, spotify_id, item_type, name, reason)

    assert status == ITEM_ADDED
    assert isinstance(result, Whitelist)
    assert result.spotify_id == spotify_id
    assert result.item_type == item_type
    assert result.user_id == user_id
    assert result.name == name
    assert result.reason == reason

    # Verify in DB
    entry_in_db = Whitelist.query.filter_by(user_id=user_id, spotify_id=spotify_id, item_type=item_type).first()
    assert entry_in_db is not None
    assert entry_in_db.id == result.id

def test_add_existing_item_to_whitelist(db_session, new_user):
    """Test adding an item that already exists in the whitelist."""
    user_id = new_user.id
    spotify_id = "existing_song_456"
    item_type = "song"

    # Add the item first
    initial_status, initial_result = add_to_whitelist(user_id, spotify_id, item_type, name="Initial Name")
    assert initial_status == ITEM_ADDED
    initial_entry_id = initial_result.id

    # Attempt to add it again, potentially with a new reason
    new_reason = "Updated reason"
    status, result = add_to_whitelist(user_id, spotify_id, item_type, name="Does name update?", reason=new_reason)

    assert status == REASON_UPDATED
    assert isinstance(result, Whitelist)
    assert result.id == initial_entry_id # Should be the same DB entry
    assert result.reason == new_reason # Reason should update
    assert result.name == "Initial Name" # Name should NOT update on existing add

    # Verify count in DB (should still be 1)
    count = Whitelist.query.filter_by(user_id=user_id, spotify_id=spotify_id, item_type=item_type).count()
    assert count == 1

def test_add_blacklisted_item_to_whitelist(db_session, new_user):
    """Test adding an item to the whitelist that is currently blacklisted."""
    user_id = new_user.id
    spotify_id = "blacklisted_song_789"
    item_type = "song"

    # 1. Add to blacklist first
    blacklist_entry = Blacklist(user_id=user_id, spotify_id=spotify_id, item_type=item_type, name="Blacklisted Song")
    db.session.add(blacklist_entry)
    db.session.commit()
    assert Blacklist.query.filter_by(user_id=user_id, spotify_id=spotify_id).count() == 1
    assert Whitelist.query.filter_by(user_id=user_id, spotify_id=spotify_id).count() == 0

    # 2. Attempt to add to whitelist
    whitelist_reason = "Moving from blacklist"
    status, result = add_to_whitelist(user_id, spotify_id, item_type, name="Whitelisted Name", reason=whitelist_reason)

    assert status == ITEM_MOVED_FROM_BLACKLIST
    assert isinstance(result, Whitelist)
    assert result.spotify_id == spotify_id
    assert result.reason == whitelist_reason
    assert result.name == "Whitelisted Name"

    # 3. Verify it's removed from blacklist and added to whitelist in DB
    assert Blacklist.query.filter_by(user_id=user_id, spotify_id=spotify_id).count() == 0
    assert Whitelist.query.filter_by(user_id=user_id, spotify_id=spotify_id).count() == 1
    assert Whitelist.query.first().id == result.id

# --- Tests for remove_from_whitelist --- #

def test_remove_item_by_id(db_session, new_user):
    """Test removing a whitelist item by its database ID."""
    user_id = new_user.id
    spotify_id = "song_to_remove_by_id"
    item_type = "song"

    # 1. Add item first
    status, added_item = add_to_whitelist(user_id, spotify_id, item_type, "Remove Me")
    assert status in [ITEM_ADDED, ITEM_ALREADY_EXISTS, REASON_UPDATED, ITEM_MOVED_FROM_BLACKLIST]
    assert Whitelist.query.filter_by(id=added_item.id).count() == 1
    entry_id_to_remove = added_item.id

    # 2. Remove by ID
    remove_status, result = remove_from_whitelist(user_id, whitelist_entry_id=entry_id_to_remove)

    assert remove_status == ITEM_REMOVED
    assert result == "Item successfully removed from whitelist."

    # 3. Verify removed from DB
    assert Whitelist.query.filter_by(id=entry_id_to_remove).count() == 0

def test_remove_item_by_spotify_id_and_type(db_session, new_user):
    """Test removing a whitelist item by its spotify_id and item_type."""
    user_id = new_user.id
    spotify_id = "song_to_remove_by_spotify"
    item_type = "artist" # Use a different type for variety

    # 1. Add item first
    status, added_item = add_to_whitelist(user_id, spotify_id, item_type, "Remove Artist")
    assert status in [ITEM_ADDED, ITEM_ALREADY_EXISTS, REASON_UPDATED, ITEM_MOVED_FROM_BLACKLIST]
    assert Whitelist.query.filter_by(user_id=user_id, spotify_id=spotify_id, item_type=item_type).count() == 1

    # 2. Remove by spotify_id and item_type
    remove_status, result = remove_from_whitelist(user_id, spotify_id=spotify_id, item_type=item_type)

    assert remove_status == ITEM_REMOVED
    assert result == "Item successfully removed from whitelist."

    # 3. Verify removed from DB
    assert Whitelist.query.filter_by(user_id=user_id, spotify_id=spotify_id, item_type=item_type).count() == 0

def test_remove_nonexistent_item_by_id(db_session, new_user):
    """Test attempting to remove a whitelist item by a non-existent ID."""
    user_id = new_user.id
    non_existent_id = 99999

    # Ensure the ID doesn't exist
    assert Whitelist.query.filter_by(id=non_existent_id).count() == 0

    # Attempt to remove
    remove_status, result = remove_from_whitelist(user_id, whitelist_entry_id=non_existent_id)

    assert remove_status == ITEM_NOT_FOUND
    assert "not found" in result.lower()

def test_remove_nonexistent_item_by_spotify_id(db_session, new_user):
    """Test attempting to remove a whitelist item by non-existent spotify_id/type."""
    user_id = new_user.id
    non_existent_spotify_id = "does_not_exist_123"
    item_type = "track"

    # Ensure the item doesn't exist
    assert Whitelist.query.filter_by(user_id=user_id, spotify_id=non_existent_spotify_id, item_type=item_type).count() == 0

    # Attempt to remove
    remove_status, result = remove_from_whitelist(user_id, spotify_id=non_existent_spotify_id, item_type=item_type)

    assert remove_status == ITEM_NOT_FOUND
    assert "not found" in result.lower()

def test_remove_item_invalid_input(db_session, new_user):
    """Test calling remove_from_whitelist without sufficient identification info."""
    user_id = new_user.id

    # Call without ID or spotify_id/type
    remove_status, result = remove_from_whitelist(user_id)

    assert remove_status == INVALID_INPUT
    assert "either whitelist_entry_id or both" in result.lower()

    # Call with only spotify_id (missing type)
    remove_status_2, result_2 = remove_from_whitelist(user_id, spotify_id="some_id")
    assert remove_status_2 == INVALID_INPUT
    assert "both spotify_id and item_type" in result_2.lower() # Or use "either whitelist_entry_id or both"


# --- Tests for is_whitelisted --- #

def test_is_whitelisted_true(db_session, new_user):
    """Test is_whitelisted returns True for an item in the whitelist."""
    user_id = new_user.id
    spotify_id = "whitelisted_checker_song"
    item_type = "song"

    # Add to whitelist
    add_to_whitelist(user_id, spotify_id, item_type, "Checker Song")

    assert is_whitelisted(user_id, spotify_id, item_type) is True

def test_is_whitelisted_false(db_session, new_user):
    """Test is_whitelisted returns False for an item not in the whitelist."""
    user_id = new_user.id
    spotify_id = "not_whitelisted_checker_song"
    item_type = "song"

    # Ensure not in whitelist (it shouldn't be by default)
    assert Whitelist.query.filter_by(user_id=user_id, spotify_id=spotify_id, item_type=item_type).count() == 0

    assert is_whitelisted(user_id, spotify_id, item_type) is False

def test_is_whitelisted_false_for_different_user(db_session, new_user):
    """Test is_whitelisted returns False if item is whitelisted by another user."""
    user1_id = new_user.id
    user2_id = user1_id + 999 # Arbitrary second user ID

    spotify_id = "cross_user_check_song"
    item_type = "song"

    # Add to user1's whitelist
    add_to_whitelist(user1_id, spotify_id, item_type, "User1 Song")

    # Check against user2 (should be false)
    assert is_whitelisted(user2_id, spotify_id, item_type) is False


# --- Tests for get_user_whitelist --- #

def test_get_user_whitelist_empty(db_session, new_user):
    """Test getting the whitelist for a user with no entries."""
    user_id = new_user.id
    whitelist = get_user_whitelist(user_id)
    assert isinstance(whitelist, list)
    assert len(whitelist) == 0

def test_get_user_whitelist_single_item(db_session, new_user):
    """Test getting the whitelist with a single entry."""
    user_id = new_user.id
    spotify_id = "get_whitelist_song_1"
    item_type = "song"
    name = "Get Me Song"

    # Add one item
    status, added_item = add_to_whitelist(user_id, spotify_id, item_type, name)
    assert status in [ITEM_ADDED, ITEM_MOVED_FROM_BLACKLIST]

    # Get whitelist
    whitelist = get_user_whitelist(user_id)
    assert isinstance(whitelist, list)
    assert len(whitelist) == 1
    assert whitelist[0].id == added_item.id
    assert whitelist[0].spotify_id == spotify_id
    assert whitelist[0].name == name

def test_get_user_whitelist_multiple_items(db_session, new_user):
    """Test getting the whitelist with multiple entries of different types."""
    user_id = new_user.id

    items_to_add = [
        ("song_multi_1", "song", "Song 1"),
        ("artist_multi_1", "artist", "Artist 1"),
        ("album_multi_1", "album", "Album 1"),
        ("song_multi_2", "song", "Song 2"),
    ]
    added_ids = set()

    # Add multiple items
    for spotify_id, item_type, name in items_to_add:
        status, added_item = add_to_whitelist(user_id, spotify_id, item_type, name)
        assert status in [ITEM_ADDED, ITEM_MOVED_FROM_BLACKLIST]
        added_ids.add(added_item.id)

    # Get whitelist
    whitelist = get_user_whitelist(user_id)
    assert isinstance(whitelist, list)
    assert len(whitelist) == len(items_to_add)

    # Verify all added items are present
    retrieved_ids = {item.id for item in whitelist}
    assert retrieved_ids == added_ids

def test_get_user_whitelist_only_returns_user_items(db_session, new_user):
    """Test get_user_whitelist only returns items for the specified user."""
    user1_id = new_user.id
    user2_id = user1_id + 999 # Arbitrary second user ID

    # Add items for user1
    add_to_whitelist(user1_id, "user1_song", "song", "User 1 Song")
    add_to_whitelist(user1_id, "user1_artist", "artist", "User 1 Artist")

    # Add items for user2 (simulated - these won't actually be added to DB for user2_id)
    # But we also need to add *actual* items for user1 that user2 *shouldn't* get
    status, user1_item = add_to_whitelist(user1_id, "another_user1_song", "song", "Another User 1 Song")
    assert status in [ITEM_ADDED, ITEM_MOVED_FROM_BLACKLIST]

    # Simulate adding an item for user2 by adding it for user1 and checking user2 list
    # Add an item for user1 that we expect NOT to see when querying user2
    add_to_whitelist(user1_id, "song_for_user1_only", "song", "U1 Only Song")


    # Get whitelist for user1
    whitelist1 = get_user_whitelist(user1_id)
    assert len(whitelist1) >= 3 # Should have at least the 3 items explicitly added for user1

    # Get whitelist for user2 (should be empty as no items were added for this ID)
    whitelist2 = get_user_whitelist(user2_id)
    assert isinstance(whitelist2, list)
    assert len(whitelist2) == 0


# --- Tests for get_whitelist_entry_by_id --- #

def test_get_whitelist_entry_by_id_exists(db_session, new_user):
    """Test getting an existing whitelist entry by its ID."""
    user_id = new_user.id
    spotify_id = "get_entry_song_1"
    item_type = "song"

    # Add an item
    status, added_item = add_to_whitelist(user_id, spotify_id, item_type, "Entry Song")
    assert status in [ITEM_ADDED, ITEM_MOVED_FROM_BLACKLIST]
    entry_id = added_item.id

    # Get the entry by ID
    retrieved_entry = get_whitelist_entry_by_id(user_id, entry_id)

    assert retrieved_entry is not None
    assert retrieved_entry.id == entry_id
    assert retrieved_entry.user_id == user_id
    assert retrieved_entry.spotify_id == spotify_id

def test_get_whitelist_entry_by_id_not_exists(db_session, new_user):
    """Test getting a whitelist entry by an ID that does not exist for a user."""
    user_id = new_user.id
    non_existent_id = 99999 # Assuming this ID doesn't exist

    retrieved_entry = get_whitelist_entry_by_id(user_id, non_existent_id)

    assert retrieved_entry is None

def test_get_whitelist_entry_by_id_wrong_user(db_session, new_user):
    """Test getting a whitelist entry fails if the user ID doesn't match the entry owner."""
    user1_id = new_user.id
    user2_id = user1_id + 999 # Arbitrary different user ID

    # Add an item for user1
    status, added_item_user1 = add_to_whitelist(user1_id, "song_get_wrong_user", "song", "Wrong User Song")
    assert status in [ITEM_ADDED, ITEM_MOVED_FROM_BLACKLIST]
    entry_id_user1 = added_item_user1.id

    # Try to get user1's entry using user2's ID
    retrieved_entry = get_whitelist_entry_by_id(user2_id, entry_id_user1)

    # Should return None as user2 does not own this entry_id
    assert retrieved_entry is None

# --- Tests for Error Conditions --- #

from unittest.mock import patch

@patch('app.services.whitelist_service.db.session.commit')
def test_add_whitelist_commit_failure(mock_commit, db_session, new_user):
    """Test add_to_whitelist returns ERROR_OCCURRED on commit failure."""
    mock_commit.side_effect = Exception("DB commit failed")
    user_id = new_user.id
    spotify_id = "fail_add_song"
    item_type = "song"

    # Attempt to add
    status, result = add_to_whitelist(user_id, spotify_id, item_type, "Fail Add Song")

    assert status == ERROR_OCCURRED
    assert "An error occurred" in result # Check for the actual prefix
    # Ensure rollback was called (implicitly tested by checking state if needed,
    # but usually checking the return status is sufficient for service layer)

def test_remove_whitelist_commit_failure(db_session, new_user):
    """Test remove_from_whitelist returns ERROR_OCCURRED on commit failure."""
    user_id = new_user.id
    spotify_id = "fail_remove_song"
    item_type = "song"

    # Create item directly in DB for removal attempt
    item_to_remove = Whitelist(user_id=user_id, spotify_id=spotify_id, item_type=item_type, name="Fail Remove Me")
    db.session.add(item_to_remove)
    db.session.commit() # Commit without mock
    entry_id = item_to_remove.id

    # Attempt to remove by ID, mocking the commit within this specific call
    with patch('app.services.whitelist_service.db.session.commit', side_effect=Exception("DB commit failed")) as mock_commit_remove:
        status, result = remove_from_whitelist(user_id, whitelist_entry_id=entry_id)

    assert status == ERROR_OCCURRED
    assert "An error occurred" in result # Check for the actual prefix
