"""
Whitelist Blueprint Routes - Whitelist and blacklist management operations.

This file contains the routes for:
- Adding/removing items to/from whitelist and blacklist
- Playlist and song list management
- List item editing and bulk operations
- API endpoints for list management
"""

import json
from flask import render_template, flash, redirect, url_for, request, current_app, jsonify
from flask_login import login_required, current_user as flask_login_current_user

# Import the blueprint
from . import whitelist_bp

# Import required modules
from app import db
from app.models import User, Song, Playlist, Whitelist, Blacklist, PlaylistSong
from app.auth.decorators import spotify_token_required
from app.utils.database import get_by_id

@whitelist_bp.route('/whitelist_playlist/<string:playlist_id>', methods=['POST'])
@login_required
def whitelist_playlist(playlist_id):
    """Add a playlist to the user's whitelist."""
    try:
        user_id = flask_login_current_user.id
        
        # Get playlist information
        playlist = Playlist.query.filter_by(spotify_id=playlist_id, owner_id=user_id).first()
        if not playlist:
            flash("Playlist not found or access denied", 'error')
            return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))
        
        # Check if already whitelisted
        existing = Whitelist.query.filter_by(
            user_id=user_id,
            item_type='playlist',
            spotify_id=playlist_id
        ).first()
        
        if existing:
            flash(f"Playlist '{playlist.name}' is already in your whitelist", 'info')
        else:
            # Add to whitelist
            whitelist_entry = Whitelist(
                user_id=user_id,
                item_type='playlist',
                spotify_id=playlist_id,
                name=playlist.name,
                artist=None  # Playlists don't have artists
            )
            db.session.add(whitelist_entry)
            db.session.commit()
            
            current_app.logger.info(f"User {user_id} whitelisted playlist {playlist_id}")
            flash(f"✅ Playlist '{playlist.name}' added to your whitelist", 'success')
        
        return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))
        
    except Exception as e:
        current_app.logger.error(f"Error whitelisting playlist {playlist_id}: {e}")
        db.session.rollback()
        flash(f"Error adding playlist to whitelist: {str(e)}", 'error')
        return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))

@whitelist_bp.route('/blacklist_song/<string:playlist_id>/<string:track_id>', methods=['POST'])
@login_required
def blacklist_song(playlist_id, track_id):
    """Add a song to the user's blacklist."""
    try:
        user_id = flask_login_current_user.id
        
        # Get song information via playlist association
        playlist_song = PlaylistSong.query.join(
            Playlist, PlaylistSong.playlist_id == Playlist.id
        ).filter(
            Playlist.spotify_id == playlist_id,
            Playlist.owner_id == user_id,
            PlaylistSong.spotify_track_id == track_id
        ).first()
        
        if not playlist_song:
            flash("Song not found in your playlists", 'error')
            return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))
        
        song = playlist_song.song
        
        # Check if already blacklisted
        existing = Blacklist.query.filter_by(
            user_id=user_id,
            item_type='song',
            spotify_id=song.spotify_id
        ).first()
        
        if existing:
            flash(f"'{song.title}' by {song.artist} is already in your blacklist", 'info')
        else:
            # Add to blacklist
            blacklist_entry = Blacklist(
                user_id=user_id,
                item_type='song',
                spotify_id=song.spotify_id,
                name=song.title,
                artist=song.artist
            )
            db.session.add(blacklist_entry)
            db.session.commit()
            
            current_app.logger.info(f"User {user_id} blacklisted song {song.spotify_id}")
            flash(f"🚫 '{song.title}' by {song.artist} added to your blacklist", 'success')
        
        return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))
        
    except Exception as e:
        current_app.logger.error(f"Error blacklisting song {track_id}: {e}")
        db.session.rollback()
        flash(f"Error adding song to blacklist: {str(e)}", 'error')
        return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))

@whitelist_bp.route('/blacklist_playlist/<string:playlist_id>', methods=['POST'])
@login_required
def blacklist_playlist(playlist_id):
    """Add a playlist to the user's blacklist."""
    try:
        user_id = flask_login_current_user.id
        
        # Get playlist information
        playlist = Playlist.query.filter_by(spotify_id=playlist_id, owner_id=user_id).first()
        if not playlist:
            flash("Playlist not found or access denied", 'error')
            return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))
        
        # Check if already blacklisted
        existing = Blacklist.query.filter_by(
            user_id=user_id,
            item_type='playlist',
            spotify_id=playlist_id
        ).first()
        
        if existing:
            flash(f"Playlist '{playlist.name}' is already in your blacklist", 'info')
        else:
            # Add to blacklist
            blacklist_entry = Blacklist(
                user_id=user_id,
                item_type='playlist',
                spotify_id=playlist_id,
                name=playlist.name,
                artist=None  # Playlists don't have artists
            )
            db.session.add(blacklist_entry)
            db.session.commit()
            
            current_app.logger.info(f"User {user_id} blacklisted playlist {playlist_id}")
            flash(f"🚫 Playlist '{playlist.name}' added to your blacklist", 'success')
        
        return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))
        
    except Exception as e:
        current_app.logger.error(f"Error blacklisting playlist {playlist_id}: {e}")
        db.session.rollback()
        flash(f"Error adding playlist to blacklist: {str(e)}", 'error')
        return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))

@whitelist_bp.route('/whitelist_song/<string:playlist_id>/<string:track_id>', methods=['POST'])
@login_required
def whitelist_song(playlist_id, track_id):
    """Add a song to the user's whitelist."""
    try:
        user_id = flask_login_current_user.id
        
        # Get song information via playlist association
        playlist_song = PlaylistSong.query.join(
            Playlist, PlaylistSong.playlist_id == Playlist.id
        ).filter(
            Playlist.spotify_id == playlist_id,
            Playlist.owner_id == user_id,
            PlaylistSong.spotify_track_id == track_id
        ).first()
        
        if not playlist_song:
            flash("Song not found in your playlists", 'error')
            return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))
        
        song = playlist_song.song
        
        # Check if already whitelisted
        existing = Whitelist.query.filter_by(
            user_id=user_id,
            item_type='song',
            spotify_id=song.spotify_id
        ).first()
        
        if existing:
            flash(f"'{song.title}' by {song.artist} is already in your whitelist", 'info')
        else:
            # Add to whitelist
            whitelist_entry = Whitelist(
                user_id=user_id,
                item_type='song',
                spotify_id=song.spotify_id,
                name=song.title,
                artist=song.artist
            )
            db.session.add(whitelist_entry)
            db.session.commit()
            
            current_app.logger.info(f"User {user_id} whitelisted song {song.spotify_id}")
            flash(f"✅ '{song.title}' by {song.artist} added to your whitelist", 'success')
        
        return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))
        
    except Exception as e:
        current_app.logger.error(f"Error whitelisting song {track_id}: {e}")
        db.session.rollback()
        flash(f"Error adding song to whitelist: {str(e)}", 'error')
        return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))

@whitelist_bp.route('/remove_whitelist_playlist/<string:playlist_id>', methods=['POST'])
@login_required
def remove_whitelist_playlist(playlist_id):
    """Remove a playlist from the user's whitelist."""
    try:
        user_id = flask_login_current_user.id
        
        # Find and remove the whitelist entry
        whitelist_entry = Whitelist.query.filter_by(
            user_id=user_id,
            item_type='playlist',
            spotify_id=playlist_id
        ).first()
        
        if whitelist_entry:
            playlist_name = whitelist_entry.name
            db.session.delete(whitelist_entry)
            db.session.commit()
            
            current_app.logger.info(f"User {user_id} removed playlist {playlist_id} from whitelist")
            flash(f"Playlist '{playlist_name}' removed from your whitelist", 'success')
        else:
            flash("Playlist not found in your whitelist", 'info')
        
        return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))
        
    except Exception as e:
        current_app.logger.error(f"Error removing playlist {playlist_id} from whitelist: {e}")
        db.session.rollback()
        flash(f"Error removing playlist from whitelist: {str(e)}", 'error')
        return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))

@whitelist_bp.route('/remove_blacklist_playlist/<string:playlist_id>', methods=['POST'])
@login_required
def remove_blacklist_playlist(playlist_id):
    """Remove a playlist from the user's blacklist."""
    try:
        user_id = flask_login_current_user.id
        
        # Find and remove the blacklist entry
        blacklist_entry = Blacklist.query.filter_by(
            user_id=user_id,
            item_type='playlist',
            spotify_id=playlist_id
        ).first()
        
        if blacklist_entry:
            playlist_name = blacklist_entry.name
            db.session.delete(blacklist_entry)
            db.session.commit()
            
            current_app.logger.info(f"User {user_id} removed playlist {playlist_id} from blacklist")
            flash(f"Playlist '{playlist_name}' removed from your blacklist", 'success')
        else:
            flash("Playlist not found in your blacklist", 'info')
        
        return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))
        
    except Exception as e:
        current_app.logger.error(f"Error removing playlist {playlist_id} from blacklist: {e}")
        db.session.rollback()
        flash(f"Error removing playlist from blacklist: {str(e)}", 'error')
        return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))

@whitelist_bp.route('/remove_whitelist_song/<string:playlist_id>/<string:track_id>', methods=['POST'])
@login_required
def remove_whitelist_song(playlist_id, track_id):
    """Remove a song from the user's whitelist."""
    try:
        user_id = flask_login_current_user.id
        
        # Get song spotify_id from track_id
        playlist_song = PlaylistSong.query.join(
            Playlist, PlaylistSong.playlist_id == Playlist.id
        ).filter(
            Playlist.spotify_id == playlist_id,
            Playlist.owner_id == user_id,
            PlaylistSong.spotify_track_id == track_id
        ).first()
        
        if not playlist_song:
            flash("Song not found in your playlists", 'error')
            return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))
        
        song_spotify_id = playlist_song.song.spotify_id
        
        # Find and remove the whitelist entry
        whitelist_entry = Whitelist.query.filter_by(
            user_id=user_id,
            item_type='song',
            spotify_id=song_spotify_id
        ).first()
        
        if whitelist_entry:
            song_info = f"'{whitelist_entry.name}' by {whitelist_entry.artist}"
            db.session.delete(whitelist_entry)
            db.session.commit()
            
            current_app.logger.info(f"User {user_id} removed song {song_spotify_id} from whitelist")
            flash(f"{song_info} removed from your whitelist", 'success')
        else:
            flash("Song not found in your whitelist", 'info')
        
        return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))
        
    except Exception as e:
        current_app.logger.error(f"Error removing song {track_id} from whitelist: {e}")
        db.session.rollback()
        flash(f"Error removing song from whitelist: {str(e)}", 'error')
        return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))

@whitelist_bp.route('/remove_blacklist_song/<string:playlist_id>/<string:track_id>', methods=['POST'])
@login_required
def remove_blacklist_song(playlist_id, track_id):
    """Remove a song from the user's blacklist."""
    try:
        user_id = flask_login_current_user.id
        
        # Get song spotify_id from track_id
        playlist_song = PlaylistSong.query.join(
            Playlist, PlaylistSong.playlist_id == Playlist.id
        ).filter(
            Playlist.spotify_id == playlist_id,
            Playlist.owner_id == user_id,
            PlaylistSong.spotify_track_id == track_id
        ).first()
        
        if not playlist_song:
            flash("Song not found in your playlists", 'error')
            return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))
        
        song_spotify_id = playlist_song.song.spotify_id
        
        # Find and remove the blacklist entry
        blacklist_entry = Blacklist.query.filter_by(
            user_id=user_id,
            item_type='song',
            spotify_id=song_spotify_id
        ).first()
        
        if blacklist_entry:
            song_info = f"'{blacklist_entry.name}' by {blacklist_entry.artist}"
            db.session.delete(blacklist_entry)
            db.session.commit()
            
            current_app.logger.info(f"User {user_id} removed song {song_spotify_id} from blacklist")
            flash(f"{song_info} removed from your blacklist", 'success')
        else:
            flash("Song not found in your blacklist", 'info')
        
        return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))
        
    except Exception as e:
        current_app.logger.error(f"Error removing song {track_id} from blacklist: {e}")
        db.session.rollback()
        flash(f"Error removing song from blacklist: {str(e)}", 'error')
        return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))

# API endpoints for list management
@whitelist_bp.route('/api/whitelist', methods=['GET'])
@login_required
def api_get_whitelist():
    """Get all whitelist items for the current user."""
    try:
        user_id = flask_login_current_user.id
        
        whitelist_items = Whitelist.query.filter_by(user_id=user_id).order_by(Whitelist.created_at.desc()).all()
        
        items = []
        for item in whitelist_items:
            items.append({
                'id': item.id,
                'type': item.item_type,
                'spotify_id': item.spotify_id,
                'name': item.name,
                'artist': item.artist,
                'created_at': item.created_at.isoformat() if item.created_at else None
            })
        
        return jsonify({
            'success': True,
            'items': items,
            'count': len(items)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting whitelist via API: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@whitelist_bp.route('/api/blacklist', methods=['GET'])
@login_required
def api_get_blacklist():
    """Get all blacklist items for the current user."""
    try:
        user_id = flask_login_current_user.id
        
        blacklist_items = Blacklist.query.filter_by(user_id=user_id).order_by(Blacklist.created_at.desc()).all()
        
        items = []
        for item in blacklist_items:
            items.append({
                'id': item.id,
                'type': item.item_type,
                'spotify_id': item.spotify_id,
                'name': item.name,
                'artist': item.artist,
                'created_at': item.created_at.isoformat() if item.created_at else None
            })
        
        return jsonify({
            'success': True,
            'items': items,
            'count': len(items)
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting blacklist via API: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@whitelist_bp.route('/api/whitelist/<int:item_id>', methods=['DELETE'])
@login_required
def api_delete_whitelist_item(item_id):
    """Delete a whitelist item via API."""
    try:
        user_id = flask_login_current_user.id
        
        whitelist_item = Whitelist.query.filter_by(id=item_id, user_id=user_id).first()
        if not whitelist_item:
            return jsonify({
                'success': False,
                'error': 'Whitelist item not found'
            }), 404
        
        item_info = {
            'name': whitelist_item.name,
            'type': whitelist_item.item_type,
            'artist': whitelist_item.artist
        }
        
        db.session.delete(whitelist_item)
        db.session.commit()
        
        current_app.logger.info(f"User {user_id} deleted whitelist item {item_id} via API")
        
        return jsonify({
            'success': True,
            'message': f"Removed '{item_info['name']}' from whitelist",
            'item': item_info
        })
        
    except Exception as e:
        current_app.logger.error(f"Error deleting whitelist item {item_id} via API: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@whitelist_bp.route('/api/blacklist/<int:item_id>', methods=['DELETE'])
@login_required
def api_delete_blacklist_item(item_id):
    """Delete a blacklist item via API."""
    try:
        user_id = flask_login_current_user.id
        
        blacklist_item = Blacklist.query.filter_by(id=item_id, user_id=user_id).first()
        if not blacklist_item:
            return jsonify({
                'success': False,
                'error': 'Blacklist item not found'
            }), 404
        
        item_info = {
            'name': blacklist_item.name,
            'type': blacklist_item.item_type,
            'artist': blacklist_item.artist
        }
        
        db.session.delete(blacklist_item)
        db.session.commit()
        
        current_app.logger.info(f"User {user_id} deleted blacklist item {item_id} via API")
        
        return jsonify({
            'success': True,
            'message': f"Removed '{item_info['name']}' from blacklist",
            'item': item_info
        })
        
    except Exception as e:
        current_app.logger.error(f"Error deleting blacklist item {item_id} via API: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Bulk operations
@whitelist_bp.route('/api/whitelist/clear', methods=['POST'])
@login_required
def api_clear_whitelist():
    """Clear all whitelist items for the current user."""
    try:
        user_id = flask_login_current_user.id
        
        deleted_count = Whitelist.query.filter_by(user_id=user_id).delete()
        db.session.commit()
        
        current_app.logger.info(f"User {user_id} cleared whitelist ({deleted_count} items)")
        
        return jsonify({
            'success': True,
            'message': f"Cleared {deleted_count} items from whitelist",
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        current_app.logger.error(f"Error clearing whitelist via API: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@whitelist_bp.route('/api/blacklist/clear', methods=['POST'])
@login_required
def api_clear_blacklist():
    """Clear all blacklist items for the current user."""
    try:
        user_id = flask_login_current_user.id
        
        deleted_count = Blacklist.query.filter_by(user_id=user_id).delete()
        db.session.commit()
        
        current_app.logger.info(f"User {user_id} cleared blacklist ({deleted_count} items)")
        
        return jsonify({
            'success': True,
            'message': f"Cleared {deleted_count} items from blacklist",
            'deleted_count': deleted_count
        })
        
    except Exception as e:
        current_app.logger.error(f"Error clearing blacklist via API: {e}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
