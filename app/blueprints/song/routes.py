"""
Song Blueprint Routes - Individual song viewing and details.

This file contains the routes for:
- Song detail viewing
- Song information display
"""

import json
from flask import render_template, flash, redirect, url_for, request, current_app, jsonify
from flask_login import login_required, current_user as flask_login_current_user

# Import the blueprint
from . import song_bp

# Import required modules
from app import db
from app.models import User, Song, AnalysisResult, PlaylistSong, Playlist, Whitelist, Blacklist
from app.auth.decorators import spotify_token_required
from app.utils.database import get_by_id

@song_bp.route('/songs/<int:song_id>')
@song_bp.route('/songs/<int:song_id>/')
@login_required
@spotify_token_required
def song_detail(song_id):
    """Display detailed information for a single song."""
    try:
        # Get the song from the database
        song = get_by_id(Song, song_id)
        if not song:
            flash("Song not found", 'error')
            return redirect(url_for('core.dashboard'))
        
        # Check if the user has access to this song through their playlists
        user_playlists = [p.id for p in flask_login_current_user.playlists]
        song_playlists = db.session.query(PlaylistSong.playlist_id).filter_by(song_id=song_id).all()
        song_playlist_ids = [p[0] for p in song_playlists]
        
        if not any(pid in user_playlists for pid in song_playlist_ids):
            flash("You don't have access to view this song", 'error')
            return redirect(url_for('core.dashboard'))
        
        # Get the playlists this song appears in (that the user owns)
        playlists = db.session.query(Playlist).join(
            PlaylistSong, Playlist.id == PlaylistSong.playlist_id
        ).filter(
            PlaylistSong.song_id == song_id,
            Playlist.owner_id == flask_login_current_user.id
        ).all()
        
        # Function to safely parse JSON fields
        def safe_json_parse(field_value, default=None):
            if field_value is None:
                return default
            if isinstance(field_value, (dict, list)):
                return field_value
            try:
                return json.loads(field_value)
            except (json.JSONDecodeError, TypeError):
                current_app.logger.warning(f"Failed to parse JSON field: {field_value}")
                return default
        
        # Get analysis results for this song
        analysis_result = AnalysisResult.query.filter_by(
            song_id=song_id, 
            status='completed'
        ).first()
        
        # Prepare song data for template
        song_data = {
            'id': song.id,
            'title': song.title,
            'artist': song.artist,
            'album': song.album,
            'duration_ms': song.duration_ms,
            'spotify_id': song.spotify_id,
            'spotify_url': song.spotify_url,
            'preview_url': song.preview_url,
            'analysis': None,
            'playlists': playlists
        }
        
        # Add analysis data if available
        if analysis_result:
            song_data['analysis'] = {
                'score': analysis_result.score,
                'concern_level': analysis_result.concern_level,
                'explanation': analysis_result.explanation,
                'analysis_details': safe_json_parse(analysis_result.analysis_details, {}),
                'created_at': analysis_result.created_at,
                'updated_at': analysis_result.updated_at
            }
        
        # Check if song is in whitelist or blacklist
        whitelist_entry = Whitelist.query.filter_by(
            user_id=flask_login_current_user.id,
            item_type='song',
            spotify_id=song.spotify_id
        ).first()
        
        blacklist_entry = Blacklist.query.filter_by(
            user_id=flask_login_current_user.id,
            item_type='song',
            spotify_id=song.spotify_id
        ).first()
        
        song_data['in_whitelist'] = whitelist_entry is not None
        song_data['in_blacklist'] = blacklist_entry is not None
        song_data['whitelist_id'] = whitelist_entry.id if whitelist_entry else None
        song_data['blacklist_id'] = blacklist_entry.id if blacklist_entry else None
        
        return render_template('song_detail.html', song=song_data)
        
    except Exception as e:
        current_app.logger.error(f"Error in song_detail: {e}")
        flash(f"Error loading song details: {str(e)}", 'error')
        return redirect(url_for('core.dashboard'))
