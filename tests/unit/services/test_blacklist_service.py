import pytest
from unittest.mock import patch
from app import db
from app.models import User, Whitelist, Blacklist
from app.services.blacklist_service import (
    add_to_blacklist,
    ITEM_ADDED, ITEM_ALREADY_EXISTS, ITEM_MOVED_FROM_WHITELIST, ERROR_OCCURRED,
    remove_from_blacklist, ITEM_REMOVED, ITEM_NOT_FOUND, INVALID_INPUT,
    is_blacklisted, get_user_blacklist, get_blacklist_entry_by_id
)

# --- Tests for add_to_blacklist --- #

def test_add_new_item_to_blacklist(db_session, new_user):
    """Test adding a completely new item to the blacklist."""
    user_id = new_user.id
    spotify_id = "new_song_bl_123"
    item_type = "song"
    name = "Test Blacklist Song"
    reason = "Testing blacklist add"

    status, result = add_to_blacklist(user_id, spotify_id, item_type, name, reason)

    assert status == ITEM_ADDED
    assert isinstance(result, Blacklist)
    assert result.spotify_id == spotify_id
    assert result.item_type == item_type
    assert result.user_id == user_id
    assert result.name == name
    assert result.reason == reason

    # Verify in DB
    entry_in_db = Blacklist.query.filter_by(user_id=user_id, spotify_id=spotify_id, item_type=item_type).first()
    assert entry_in_db is not None
    assert entry_in_db.id == result.id

def test_add_existing_item_to_blacklist(db_session, new_user):
    """Test adding an item that already exists in the blacklist."""
    user_id = new_user.id
    spotify_id = "existing_song_bl_456"
    item_type = "song"

    # Add the item first
    initial_status, initial_result = add_to_blacklist(user_id, spotify_id, item_type, name="Initial BL Name")
    assert initial_status == ITEM_ADDED
    initial_entry_id = initial_result.id

    # Attempt to add it again, potentially with a new reason
    new_reason = "Updated BL reason"
    status, result = add_to_blacklist(user_id, spotify_id, item_type, name="Does name update?", reason=new_reason)

    assert status == ITEM_ALREADY_EXISTS
    assert isinstance(result, Blacklist)
    assert result.id == initial_entry_id # Should be the same DB entry
    assert result.reason == new_reason # Reason SHOULD update even if status is ITEM_ALREADY_EXISTS
    assert result.name == "Initial BL Name" # Name should NOT update on existing add

    # Verify count in DB (should still be 1)
    count = Blacklist.query.filter_by(user_id=user_id, spotify_id=spotify_id, item_type=item_type).count()
    assert count == 1

def test_add_whitelisted_item_to_blacklist(db_session, new_user):
    """Test adding an item to the blacklist that is currently whitelisted."""
    user_id = new_user.id
    spotify_id = "whitelisted_song_bl_789"
    item_type = "song"

    # 1. Add to whitelist first
    whitelist_entry = Whitelist(user_id=user_id, spotify_id=spotify_id, item_type=item_type, name="Whitelisted Song")
    db.session.add(whitelist_entry)
    db.session.commit()
    assert Whitelist.query.filter_by(user_id=user_id, spotify_id=spotify_id).count() == 1
    assert Blacklist.query.filter_by(user_id=user_id, spotify_id=spotify_id).count() == 0

    # 2. Attempt to add to blacklist
    blacklist_reason = "Moving from whitelist"
    status, result = add_to_blacklist(user_id, spotify_id, item_type, name="Blacklisted Name", reason=blacklist_reason)

    assert status == ITEM_MOVED_FROM_WHITELIST
    assert isinstance(result, Blacklist)
    assert result.spotify_id == spotify_id
    assert result.reason == blacklist_reason
    assert result.name == "Blacklisted Name"

    # 3. Verify it's removed from whitelist and added to blacklist in DB
    assert Whitelist.query.filter_by(user_id=user_id, spotify_id=spotify_id).count() == 0
    assert Blacklist.query.filter_by(user_id=user_id, spotify_id=spotify_id).count() == 1
    assert Blacklist.query.first().id == result.id

# --- Tests for remove_from_blacklist --- #

def test_remove_bl_item_by_id(db_session, new_user):
    """Test removing a blacklist item by its database ID."""
    user_id = new_user.id
    spotify_id = "song_to_remove_bl_by_id"
    item_type = "song"

    # 1. Add item first
    status, added_item = add_to_blacklist(user_id, spotify_id, item_type, "Remove Me BL")
    assert status in [ITEM_ADDED, ITEM_MOVED_FROM_WHITELIST]
    entry_id = added_item.id
    assert Blacklist.query.filter_by(id=entry_id).count() == 1

    # 2. Remove the item by ID
    remove_status, remove_result = remove_from_blacklist(user_id, blacklist_entry_id=entry_id)

    assert remove_status == ITEM_REMOVED
    assert remove_result == "Item successfully removed from blacklist."

    # 3. Verify it's gone from DB
    assert Blacklist.query.filter_by(id=entry_id).count() == 0

def test_remove_bl_item_by_spotify_id_and_type(db_session, new_user):
    """Test removing a blacklist item by its spotify_id and item_type."""
    user_id = new_user.id
    spotify_id = "song_to_remove_bl_by_spotify"
    item_type = "song"

    # 1. Add item first
    status, added_item = add_to_blacklist(user_id, spotify_id, item_type, "Remove Me BL Spotify")
    assert status in [ITEM_ADDED, ITEM_MOVED_FROM_WHITELIST]
    assert Blacklist.query.filter_by(user_id=user_id, spotify_id=spotify_id, item_type=item_type).count() == 1

    # 2. Remove the item by spotify_id and type
    remove_status, remove_result = remove_from_blacklist(user_id, spotify_id=spotify_id, item_type=item_type)

    assert remove_status == ITEM_REMOVED
    assert remove_result == "Item successfully removed from blacklist."

    # 3. Verify it's gone from DB
    assert Blacklist.query.filter_by(user_id=user_id, spotify_id=spotify_id, item_type=item_type).count() == 0

def test_remove_nonexistent_bl_item_by_id(db_session, new_user):
    """Test attempting to remove a blacklist item by a non-existent ID."""
    user_id = new_user.id
    non_existent_id = 99998 # Assuming this ID doesn't exist

    remove_status, remove_result = remove_from_blacklist(user_id, blacklist_entry_id=non_existent_id)

    assert remove_status == ITEM_NOT_FOUND
    assert remove_result == "Blacklist entry not found."

def test_remove_nonexistent_bl_item_by_spotify_id(db_session, new_user):
    """Test attempting to remove a blacklist item by non-existent spotify_id/type."""
    user_id = new_user.id
    spotify_id = "nonexistent_bl_song"
    item_type = "song"

    remove_status, remove_result = remove_from_blacklist(user_id, spotify_id=spotify_id, item_type=item_type)

    assert remove_status == ITEM_NOT_FOUND
    assert remove_result == "Blacklist entry not found."

def test_remove_bl_item_invalid_input(db_session, new_user):
    """Test calling remove_from_blacklist without sufficient identification info."""
    user_id = new_user.id

    # Call with no identifiers
    remove_status, remove_result = remove_from_blacklist(user_id)
    assert remove_status == INVALID_INPUT
    assert remove_result == "Either blacklist_entry_id or both spotify_id and item_type must be provided."

    # Call with only spotify_id
    remove_status, remove_result = remove_from_blacklist(user_id, spotify_id="some_id")
    assert remove_status == INVALID_INPUT
    assert remove_result == "Either blacklist_entry_id or both spotify_id and item_type must be provided."

    # Call with only item_type
    remove_status, remove_result = remove_from_blacklist(user_id, item_type="song")
    assert remove_status == INVALID_INPUT
    assert remove_result == "Either blacklist_entry_id or both spotify_id and item_type must be provided."


# --- Tests for is_blacklisted --- #

def test_is_blacklisted_true(db_session, new_user):
    """Test is_blacklisted returns True for an item in the blacklist."""
    user_id = new_user.id
    spotify_id = "is_blacklisted_song"
    item_type = "song"
    add_to_blacklist(user_id, spotify_id, item_type, "Is BL")

    assert is_blacklisted(user_id, spotify_id, item_type) is True

def test_is_blacklisted_false(db_session, new_user):
    """Test is_blacklisted returns False for an item not in the blacklist."""
    user_id = new_user.id
    spotify_id = "not_blacklisted_song"
    item_type = "song"

    assert is_blacklisted(user_id, spotify_id, item_type) is False

def test_is_blacklisted_false_for_different_user(db_session, new_user):
    """Test is_blacklisted returns False if item is blacklisted by another user."""
    user1_id = new_user.id
    user2_id = user1_id + 998 # Arbitrary different user ID
    spotify_id = "diff_user_bl_song"
    item_type = "song"

    # Blacklist item for user1
    add_to_blacklist(user1_id, spotify_id, item_type, "User1 BL")

    # Check if blacklisted for user2
    assert is_blacklisted(user2_id, spotify_id, item_type) is False


# --- Tests for get_user_blacklist --- #

def test_get_user_blacklist_empty(db_session, new_user):
    """Test getting the blacklist for a user with no entries."""
    user_id = new_user.id
    blacklist = get_user_blacklist(user_id)
    assert isinstance(blacklist, list)
    assert len(blacklist) == 0

def test_get_user_blacklist_single_item(db_session, new_user):
    """Test getting the blacklist with a single entry."""
    user_id = new_user.id
    spotify_id = "single_bl_item_1"
    item_type = "playlist"

    status, added_item = add_to_blacklist(user_id, spotify_id, item_type, "Single BL Playlist")
    assert status in [ITEM_ADDED, ITEM_MOVED_FROM_WHITELIST]

    blacklist = get_user_blacklist(user_id)
    assert len(blacklist) == 1
    assert blacklist[0].id == added_item.id
    assert blacklist[0].spotify_id == spotify_id
    assert blacklist[0].item_type == item_type

def test_get_user_blacklist_multiple_items(db_session, new_user):
    """Test getting the blacklist with multiple entries of different types."""
    user_id = new_user.id
    spotify_id1 = "multi_bl_song_1"
    item_type1 = "song"
    spotify_id2 = "multi_bl_playlist_2"
    item_type2 = "playlist"
    spotify_id3 = "multi_bl_song_3"
    item_type3 = "song"

    add_to_blacklist(user_id, spotify_id1, item_type1, "Multi BL 1")
    add_to_blacklist(user_id, spotify_id2, item_type2, "Multi BL 2")
    add_to_blacklist(user_id, spotify_id3, item_type3, "Multi BL 3")

    blacklist = get_user_blacklist(user_id)
    assert len(blacklist) == 3

    retrieved_spotify_ids = {item.spotify_id for item in blacklist}
    assert retrieved_spotify_ids == {spotify_id1, spotify_id2, spotify_id3}

def test_get_user_blacklist_only_returns_user_items(db_session, new_user):
    """Test get_user_blacklist only returns items for the specified user."""
    user1_id = new_user.id
    user2_id = user1_id + 997 # Arbitrary different user ID

    # Items for user 1
    add_to_blacklist(user1_id, "user1_bl_song1", "song", "U1 Song1")
    add_to_blacklist(user1_id, "user1_bl_playlist1", "playlist", "U1 Playlist1")

    # Item for user 2
    add_to_blacklist(user2_id, "user2_bl_song1", "song", "U2 Song1")

    # Get blacklist for user1
    blacklist1 = get_user_blacklist(user1_id)
    assert len(blacklist1) == 2
    assert {item.spotify_id for item in blacklist1} == {"user1_bl_song1", "user1_bl_playlist1"}

    # Get blacklist for user2
    blacklist2 = get_user_blacklist(user2_id)
    assert len(blacklist2) == 1
    assert blacklist2[0].spotify_id == "user2_bl_song1"


# --- Tests for get_blacklist_entry_by_id --- #

def test_get_blacklist_entry_by_id_exists(db_session, new_user):
    """Test getting an existing blacklist entry by its ID."""
    user_id = new_user.id
    spotify_id = "get_bl_entry_song_1"
    item_type = "song"

    # Add an item
    status, added_item = add_to_blacklist(user_id, spotify_id, item_type, "Entry BL Song")
    assert status in [ITEM_ADDED, ITEM_MOVED_FROM_WHITELIST]
    entry_id = added_item.id

    # Get the entry by ID
    retrieved_entry = get_blacklist_entry_by_id(user_id, entry_id)

    assert retrieved_entry is not None
    assert retrieved_entry.id == entry_id
    assert retrieved_entry.user_id == user_id
    assert retrieved_entry.spotify_id == spotify_id

def test_get_blacklist_entry_by_id_not_exists(db_session, new_user):
    """Test getting a blacklist entry by an ID that does not exist for a user."""
    user_id = new_user.id
    non_existent_id = 99996 # Assuming this ID doesn't exist

    retrieved_entry = get_blacklist_entry_by_id(user_id, non_existent_id)

    assert retrieved_entry is None

def test_get_blacklist_entry_by_id_wrong_user(db_session, new_user):
    """Test getting a blacklist entry fails if the user ID doesn't match the entry owner."""
    user1_id = new_user.id
    user2_id = user1_id + 995 # Arbitrary different user ID

    # Add an item for user1
    status, added_item_user1 = add_to_blacklist(user1_id, "song_get_bl_wrong_user", "song", "Wrong User BL Song")
    assert status in [ITEM_ADDED, ITEM_MOVED_FROM_WHITELIST]
    entry_id_user1 = added_item_user1.id

    # Try to get user1's entry using user2's ID
    retrieved_entry = get_blacklist_entry_by_id(user2_id, entry_id_user1)

    # Should return None as user2 does not own this entry_id
    assert retrieved_entry is None

# --- Tests for Error Conditions --- #

@patch('app.services.blacklist_service.db.session.commit')
def test_add_blacklist_commit_failure(mock_commit, db_session, new_user):
    """Test add_to_blacklist returns ERROR_OCCURRED on commit failure."""
    mock_commit.side_effect = Exception("DB commit failed BL")
    user_id = new_user.id
    spotify_id = "fail_add_bl_song"
    item_type = "song"

    # Attempt to add
    status, result = add_to_blacklist(user_id, spotify_id, item_type, "Fail Add BL Song")

    assert status == ERROR_OCCURRED
    assert "An error occurred" in result # Check for the actual prefix

def test_remove_blacklist_commit_failure(db_session, new_user):
    """Test remove_from_blacklist returns ERROR_OCCURRED on commit failure."""
    user_id = new_user.id
    spotify_id = "fail_remove_bl_song"
    item_type = "song"

    # Create item directly in DB for removal attempt
    item_to_remove = Blacklist(user_id=user_id, spotify_id=spotify_id, item_type=item_type, name="Fail Remove Me BL")
    db.session.add(item_to_remove)
    db.session.commit() # Commit without mock
    entry_id = item_to_remove.id

    # Attempt to remove by ID, mocking the commit within this specific call
    with patch('app.services.blacklist_service.db.session.commit', side_effect=Exception("DB commit failed BL")) as mock_commit_remove:
        status, result = remove_from_blacklist(user_id, blacklist_entry_id=entry_id)

    assert status == ERROR_OCCURRED
    assert "An error occurred" in result # Check for the actual prefix
