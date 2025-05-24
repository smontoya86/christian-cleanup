# app/services/whitelist_service.py
from app import db
from app.models import Whitelist, Blacklist
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from flask import current_app
from datetime import datetime
from ..utils.database import get_by_filter, get_all_by_filter, safe_add_and_commit, safe_delete_and_commit, count_by_filter  # Add SQLAlchemy 2.0 utilities

# Status Constants
ITEM_ADDED = 1
ITEM_ALREADY_EXISTS = 2
ITEM_MOVED_FROM_BLACKLIST = 3 # Specific case for moving item from blacklist
REASON_UPDATED = 4 # Specific case for updating reason on existing entry
ITEM_REMOVED = 5
ITEM_NOT_FOUND = 6
INVALID_INPUT = 7
ERROR_OCCURRED = 0
ITEM_MOVED_FROM_WHITELIST = 8

def add_to_whitelist(user_id, spotify_id, item_type, name=None, reason=None):
    """Adds an item to the user's whitelist.

    Checks if the item exists in the blacklist first. If so, removes it
    from the blacklist and adds it to the whitelist, returning ITEM_MOVED_FROM_BLACKLIST.

    If the item already exists in the whitelist, updates the reason if provided and
    different, returning REASON_UPDATED, otherwise returns ITEM_ALREADY_EXISTS.

    If the item is not in either list, adds it to the whitelist and returns ITEM_ADDED.

    Returns:
        tuple: (status_code, result_or_error)
               result_or_error is the Whitelist object on success/exists/updated,
               or an error message string on failure.
    """
    try:
        # 1. Check if the item exists in the Whitelist first
        existing_whitelist_entry = get_by_filter(Whitelist,
            user_id=user_id,
            spotify_id=spotify_id,
            item_type=item_type
        )

        if existing_whitelist_entry:
            if reason and existing_whitelist_entry.reason != reason:
                existing_whitelist_entry.reason = reason
                db.session.commit()
                current_app.logger.info(f"Updated reason for whitelisted item {item_type} ID {spotify_id} for user {user_id}.")
                return REASON_UPDATED, existing_whitelist_entry
            current_app.logger.info(f"Item {item_type} ID {spotify_id} already whitelisted for user {user_id}.")
            return ITEM_ALREADY_EXISTS, existing_whitelist_entry

        # 2. If not in Whitelist, check if it exists in the Blacklist
        moved_from_blacklist = False
        existing_blacklist_entry = get_by_filter(Blacklist,
            user_id=user_id,
            spotify_id=spotify_id,
            item_type=item_type
        )

        if existing_blacklist_entry:
            db.session.delete(existing_blacklist_entry)
            # Commit the deletion before adding to whitelist to avoid potential conflicts
            db.session.commit()
            moved_from_blacklist = True
            current_app.logger.info(f"Removed {item_type} ID {spotify_id} from blacklist for user {user_id} before adding to whitelist.")

        # 3. Add the new entry to the Whitelist
        new_entry = Whitelist(
            user_id=user_id,
            spotify_id=spotify_id,
            item_type=item_type,
            name=name,
            reason=reason
        )
        db.session.add(new_entry)
        db.session.commit() # Commit the addition

        if moved_from_blacklist:
            current_app.logger.info(f"Moved {item_type} ID {spotify_id} from blacklist to whitelist for user {user_id}.")
            return ITEM_MOVED_FROM_BLACKLIST, new_entry
        else:
            current_app.logger.info(f"Added {item_type} ID {spotify_id} to whitelist for user {user_id}.")
            return ITEM_ADDED, new_entry

    except IntegrityError: # Fallback if concurrent add happened
        db.session.rollback()
        current_app.logger.warning(f"Integrity error likely due to concurrent add for {item_type} ID {spotify_id}, user {user_id}.")
        # Re-query to return the existing entry
        existing_entry = get_by_filter(Whitelist, user_id=user_id, spotify_id=spotify_id, item_type=item_type)
        if existing_entry: # Should exist if IntegrityError occurred
             # Decide if it's ALREADY_EXISTS or REASON_UPDATED based on if reason was provided and differs
             if reason and existing_entry.reason != reason:
                 return REASON_UPDATED, existing_entry # Reason likely updated by other process
             else:
                 return ITEM_ALREADY_EXISTS, existing_entry
        else: # Should not happen, but handle gracefully
             current_app.logger.error(f"IntegrityError occurred but entry not found for {item_type} ID {spotify_id}, user {user_id}.")
             return ERROR_OCCURRED, "Integrity error occurred, but couldn't find existing entry."
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding {item_type} ID {spotify_id} to whitelist for user {user_id}: {e}", exc_info=True)
        return ERROR_OCCURRED, f"An error occurred: {str(e)}"

def remove_from_whitelist(user_id, whitelist_entry_id=None, spotify_id=None, item_type=None):
    """Removes an item from the user's whitelist.
    Returns:
        tuple: (status_code, message)
    """
    try:
        if whitelist_entry_id:
            entry = get_by_filter(Whitelist, id=whitelist_entry_id, user_id=user_id)
        elif spotify_id and item_type:
            entry = get_by_filter(Whitelist,
                user_id=user_id,
                spotify_id=spotify_id,
                item_type=item_type
            )
        else:
            return INVALID_INPUT, "Either whitelist_entry_id or both spotify_id and item_type must be provided."

        if entry:
            db.session.delete(entry)
            db.session.commit()
            current_app.logger.info(f"Removed item ID {entry.spotify_id} ({entry.item_type}) from whitelist for user {user_id}.")
            return ITEM_REMOVED, "Item successfully removed from whitelist."
        else:
            current_app.logger.info(f"Whitelist entry not found for user {user_id} with given criteria.")
            return ITEM_NOT_FOUND, "Whitelist entry not found."
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error removing item from whitelist for user {user_id}: {e}", exc_info=True)
        return ERROR_OCCURRED, f"An error occurred: {str(e)}"

def is_whitelisted(user_id, spotify_id, item_type):
    """Checks if a specific item is whitelisted by the user."""
    return count_by_filter(Whitelist, 
        user_id=user_id, 
        spotify_id=spotify_id, 
        item_type=item_type
    ) > 0

def get_user_whitelist(user_id, item_type=None):
    """Retrieves all whitelist entries for a user, optionally filtered by item_type."""
    if item_type:
        return get_all_by_filter(Whitelist, user_id=user_id, item_type=item_type)
    else:
        return get_all_by_filter(Whitelist, user_id=user_id)

def get_whitelist_entry_by_id(whitelist_entry_id, user_id):
    """Retrieves a specific whitelist entry by its ID, ensuring it belongs to the user."""
    return get_by_filter(Whitelist, id=whitelist_entry_id, user_id=user_id)

# --- Blacklist Functions ---

def add_to_blacklist(user_id, spotify_id, item_type, name=None, reason=None):
    """Adds an item to the user's blacklist.

    Checks if the item exists in the whitelist first. If so, removes it
    from the whitelist and adds it to the blacklist, returning ITEM_MOVED_FROM_WHITELIST.

    If the item already exists in the blacklist, updates the reason if provided and
    different, returning REASON_UPDATED, otherwise returns ITEM_ALREADY_EXISTS.

    If the item is not in either list, adds it to the blacklist and returns ITEM_ADDED.

    Returns:
        tuple: (status_code, result_or_error)
               result_or_error is the Blacklist object on success/exists/updated,
               or an error message string on failure.
    """
    try:
        # 1. Check if the item exists in the Blacklist first
        existing_blacklist_entry = get_by_filter(Blacklist,
            user_id=user_id,
            spotify_id=spotify_id,
            item_type=item_type
        )

        if existing_blacklist_entry:
            if reason and existing_blacklist_entry.reason != reason:
                existing_blacklist_entry.reason = reason
                db.session.commit()
                current_app.logger.info(f"Updated reason for blacklisted item {item_type} ID {spotify_id} for user {user_id}.")
                return REASON_UPDATED, existing_blacklist_entry
            current_app.logger.info(f"Item {item_type} ID {spotify_id} already blacklisted for user {user_id}.")
            return ITEM_ALREADY_EXISTS, existing_blacklist_entry

        # 2. If not in Blacklist, check if it exists in the Whitelist
        moved_from_whitelist = False
        existing_whitelist_entry = get_by_filter(Whitelist,
            user_id=user_id,
            spotify_id=spotify_id,
            item_type=item_type
        )

        if existing_whitelist_entry:
            db.session.delete(existing_whitelist_entry)
            # Commit the deletion before adding to blacklist to avoid potential conflicts
            db.session.commit()
            moved_from_whitelist = True
            current_app.logger.info(f"Removed {item_type} ID {spotify_id} from whitelist for user {user_id} before adding to blacklist.")

        # 3. Add the new entry to the Blacklist
        new_entry = Blacklist(
            user_id=user_id,
            spotify_id=spotify_id,
            item_type=item_type,
            name=name,
            reason=reason
        )
        db.session.add(new_entry)
        db.session.commit() # Commit the addition

        if moved_from_whitelist:
            current_app.logger.info(f"Moved {item_type} ID {spotify_id} from whitelist to blacklist for user {user_id}.")
            return ITEM_MOVED_FROM_WHITELIST, new_entry
        else:
            current_app.logger.info(f"Added {item_type} ID {spotify_id} to blacklist for user {user_id}.")
            return ITEM_ADDED, new_entry

    except IntegrityError: # Fallback if concurrent add happened
        db.session.rollback()
        current_app.logger.warning(f"Integrity error likely due to concurrent blacklist add for {item_type} ID {spotify_id}, user {user_id}.")
        # Re-query to return the existing entry
        existing_entry = get_by_filter(Blacklist, user_id=user_id, spotify_id=spotify_id, item_type=item_type)
        if existing_entry: # Should exist if IntegrityError occurred
             if reason and existing_entry.reason != reason:
                 return REASON_UPDATED, existing_entry # Reason likely updated by other process
             else:
                 return ITEM_ALREADY_EXISTS, existing_entry
        else: # Should not happen, but handle gracefully
             current_app.logger.error(f"IntegrityError occurred but blacklist entry not found for {item_type} ID {spotify_id}, user {user_id}.")
             return ERROR_OCCURRED, "Integrity error occurred, but couldn't find existing blacklist entry."
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error adding {item_type} ID {spotify_id} to blacklist for user {user_id}: {e}", exc_info=True)
        return ERROR_OCCURRED, f"An error occurred: {str(e)}"

def remove_from_blacklist(user_id, blacklist_entry_id=None, spotify_id=None, item_type=None):
    """Removes an item from the user's blacklist.
    Returns:
        tuple: (status_code, message)
    """
    try:
        if blacklist_entry_id:
            entry = get_by_filter(Blacklist, id=blacklist_entry_id, user_id=user_id)
        elif spotify_id and item_type:
            entry = get_by_filter(Blacklist,
                user_id=user_id,
                spotify_id=spotify_id,
                item_type=item_type
            )
        else:
            return INVALID_INPUT, "Either blacklist_entry_id or both spotify_id and item_type must be provided."

        if entry:
            db.session.delete(entry)
            db.session.commit()
            current_app.logger.info(f"Removed item ID {entry.spotify_id} ({entry.item_type}) from blacklist for user {user_id}.")
            return ITEM_REMOVED, "Item successfully removed from blacklist."
        else:
            current_app.logger.info(f"Blacklist entry not found for user {user_id} with given criteria.")
            return ITEM_NOT_FOUND, "Blacklist entry not found."
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error removing item from blacklist for user {user_id}: {e}", exc_info=True)
        return ERROR_OCCURRED, f"An error occurred: {str(e)}"

def is_blacklisted(user_id, spotify_id, item_type):
    """Checks if a specific item is blacklisted by the user."""
    return count_by_filter(Blacklist,
        user_id=user_id,
        spotify_id=spotify_id,
        item_type=item_type
    ) > 0

def get_user_blacklist(user_id, item_type=None):
    """Retrieves all blacklist entries for a user, optionally filtered by item_type."""
    if item_type:
        return get_all_by_filter(Blacklist, user_id=user_id, item_type=item_type)
    else:
        return get_all_by_filter(Blacklist, user_id=user_id)

def get_blacklist_entry_by_id(blacklist_entry_id, user_id):
    """Retrieves a specific blacklist entry by its ID, ensuring it belongs to the user."""
    return get_by_filter(Blacklist, id=blacklist_entry_id, user_id=user_id)
