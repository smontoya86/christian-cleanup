"""
Freemium utilities: determine which playlist is unlocked for a free user
and enforce masking for other playlists.

Rules:
- Free plan allows exactly 1 unlocked playlist: the first playlist (by created_at, id)
  that has at least 1 song. Empty playlists are ignored.
- Admins are always fully unlocked.
"""

from __future__ import annotations

from typing import Optional, Tuple

from flask import current_app
from flask_login import current_user

from ..extensions import db
from ..models.models import Playlist, PlaylistSong


def freemium_enabled() -> bool:
    return bool(current_app.config.get("FREEMIUM_ENABLED", True))


def free_playlist_id_for_user(user_id: int) -> Optional[int]:
    """Return the unlocked playlist id for the user, or None if none eligible."""
    # Find first playlist with at least 1 song
    subq = (
        db.session.query(Playlist.id)
        .join(PlaylistSong, PlaylistSong.playlist_id == Playlist.id)
        .filter(Playlist.owner_id == user_id)
        .group_by(Playlist.id)
        .subquery()
    )
    row = (
        db.session.query(Playlist.id)
        .filter(Playlist.owner_id == user_id, Playlist.id.in_(db.select(subq.c.id)))
        .order_by(Playlist.created_at.asc(), Playlist.id.asc())
        .first()
    )
    return row[0] if row else None


def is_playlist_unlocked(playlist_id: int) -> bool:
    """Return True if the current user can fully access this playlist under freemium."""
    if not current_user.is_authenticated:
        return False
    if getattr(current_user, "is_admin", False):
        return True
    if not freemium_enabled():
        return True
    allowed_id = free_playlist_id_for_user(current_user.id)
    return allowed_id is not None and int(playlist_id) == int(allowed_id)


def song_belongs_to_unlocked_playlist(song_id: int) -> Tuple[bool, Optional[int]]:
    """Check if the song is in the unlocked playlist for the current user.

    Returns (is_unlocked, playlist_id_found)
    """
    if not current_user.is_authenticated:
        return False, None
    if getattr(current_user, "is_admin", False) or not freemium_enabled():
        return True, None
    allowed_id = free_playlist_id_for_user(current_user.id)
    if allowed_id is None:
        return False, None
    # Does this song belong to that playlist for this user?
    exists_in_allowed = (
        db.session.query(PlaylistSong)
        .join(Playlist, Playlist.id == PlaylistSong.playlist_id)
        .filter(
            PlaylistSong.song_id == song_id,
            PlaylistSong.playlist_id == allowed_id,
            Playlist.owner_id == current_user.id,
        )
        .first()
        is not None
    )
    return exists_in_allowed, allowed_id


def mask_playlist_score_for_user(playlist_id: int, score_value):
    """Return score_value if unlocked; otherwise None to mask in API responses."""
    return score_value if is_playlist_unlocked(playlist_id) else None
