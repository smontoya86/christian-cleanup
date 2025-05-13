# app/services/blacklist_service.py
from app import db
from app.models import Blacklist, Whitelist # Import both models
from sqlalchemy.exc import IntegrityError
from flask import current_app

# Status Constants (can potentially be shared with whitelist_service later)
ITEM_ADDED = 1
ITEM_ALREADY_EXISTS = 2
ITEM_MOVED_FROM_WHITELIST = 3 # Specific status for moving
ITEM_REMOVED = 4
ITEM_NOT_FOUND = 5
INVALID_INPUT = 6
ERROR_OCCURRED = 0

def add_to_blacklist(user_id, spotify_id, item_type, name=None, reason=None):
    """Adds an item to the user's blacklist. Moves from whitelist if present.

    Returns:
        tuple: (status_code, result_or_error)
               result_or_error is the Blacklist object on success/exists/moved,
               or an error message string on failure.
    """
    try:
        # 1. Check if already blacklisted
        existing_blacklist_entry = Blacklist.query.filter_by(
            user_id=user_id,
            spotify_id=spotify_id,
            item_type=item_type
        ).first()

        if existing_blacklist_entry:
            # Optionally update reason if provided and different
            if reason and existing_blacklist_entry.reason != reason:
                existing_blacklist_entry.reason = reason
                db.session.commit()
                current_app.logger.info(f"Updated reason for blacklisted item {item_type} ID {spotify_id} for user {user_id}.")
                # Using ITEM_ALREADY_EXISTS, though a specific REASON_UPDATED could be added
                return ITEM_ALREADY_EXISTS, existing_blacklist_entry 
            current_app.logger.info(f"Item {item_type} ID {spotify_id} already blacklisted for user {user_id}.")
            return ITEM_ALREADY_EXISTS, existing_blacklist_entry

        # 2. Check if whitelisted and remove if it is
        item_was_whitelisted = False
        existing_whitelist_entry = Whitelist.query.filter_by(
            user_id=user_id,
            spotify_id=spotify_id,
            item_type=item_type
        ).first()

        if existing_whitelist_entry:
            db.session.delete(existing_whitelist_entry)
            item_was_whitelisted = True
            current_app.logger.info(f"Removing whitelisted item {item_type} ID {spotify_id} before blacklisting for user {user_id}.")
            # Commit the deletion before adding to blacklist
            # db.session.commit() # Moved commit to after successful blacklist add

        # 3. Add to blacklist
        new_entry = Blacklist(
            user_id=user_id,
            spotify_id=spotify_id,
            item_type=item_type,
            name=name,
            reason=reason
        )
        db.session.add(new_entry)
        db.session.commit() # Commit add and potential whitelist delete together
        
        if item_was_whitelisted:
            current_app.logger.info(f"Moved {item_type} ID {spotify_id} from whitelist to blacklist for user {user_id}.")
            return ITEM_MOVED_FROM_WHITELIST, new_entry
        else:
            current_app.logger.info(f"Added {item_type} ID {spotify_id} to blacklist for user {user_id}.")
            return ITEM_ADDED, new_entry

    except IntegrityError: # Fallback for blacklist unique constraint
        db.session.rollback()
        current_app.logger.warning(f"Integrity error (likely duplicate) adding {item_type} ID {spotify_id} to blacklist for user {user_id}.")
        existing_entry = Blacklist.query.filter_by(user_id=user_id, spotify_id=spotify_id, item_type=item_type).first()
        return ITEM_ALREADY_EXISTS, existing_entry
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
            entry = Blacklist.query.filter_by(id=blacklist_entry_id, user_id=user_id).first()
        elif spotify_id and item_type:
            entry = Blacklist.query.filter_by(
                user_id=user_id,
                spotify_id=spotify_id,
                item_type=item_type
            ).first()
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
    return Blacklist.query.filter_by(
        user_id=user_id,
        spotify_id=spotify_id,
        item_type=item_type
    ).count() > 0

def get_user_blacklist(user_id, item_type=None):
    """Retrieves all blacklist entries for a user, optionally filtered by item_type."""
    query = Blacklist.query.filter_by(user_id=user_id)
    if item_type:
        query = query.filter_by(item_type=item_type)
    return query.all()

def get_blacklist_entry_by_id(blacklist_entry_id, user_id):
    """Retrieves a specific blacklist entry by its ID, ensuring it belongs to the user."""
    return Blacklist.query.filter_by(id=blacklist_entry_id, user_id=user_id).first()
