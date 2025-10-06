"""
Main application routes for Music Disciple
"""

from flask import Blueprint, current_app, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import desc

from .. import db
from ..models import AnalysisResult, Playlist, PlaylistSong, Song

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Homepage - landing page"""
    return render_template("index.html")


@main_bp.route("/dashboard")
@login_required
def dashboard():
    """User dashboard - shows playlists and analysis status"""
    # Pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 30  # Limit to 30 playlists per page
    
    # Sort parameter
    sort_by = request.args.get('sort', 'updated-desc')  # Default: Recently Updated
    
    # Map sort options to SQLAlchemy order_by clauses
    sort_options = {
        'name-asc': Playlist.name.asc(),
        'name-desc': Playlist.name.desc(),
        'updated-desc': desc(Playlist.updated_at),  # Recently Updated (default)
        'updated-asc': Playlist.updated_at.asc(),
        'tracks-desc': desc(Playlist.track_count),  # Most Songs
        'tracks-asc': Playlist.track_count.asc(),
        'score-desc': desc(Playlist.overall_alignment_score),  # Highest Score
        'score-asc': Playlist.overall_alignment_score.asc(),
        'analyzed-desc': desc(Playlist.last_analyzed),  # Recently Analyzed
        'analyzed-asc': Playlist.last_analyzed.asc(),
    }
    
    # Get the appropriate order_by clause (default to updated-desc if invalid)
    order_by_clause = sort_options.get(sort_by, desc(Playlist.updated_at))
    
    # Get user's playlists with pagination and sorting
    playlists_query = Playlist.query.filter_by(owner_id=current_user.id).order_by(
        order_by_clause
    )
    
    # Get total count
    total_playlists = playlists_query.count()
    
    # Paginate
    playlists = playlists_query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    # Simplified stats - just counts, no complex joins
    stats = {
        'total_playlists': total_playlists,
        'total_songs': 0,  # Loaded async via /api/dashboard/stats
        'analyzed_songs': 0,  # Loaded async via /api/dashboard/stats
        'clean_playlists': 0
    }
    
    # Pagination info
    pagination = {
        'page': page,
        'per_page': per_page,
        'total_items': total_playlists,
        'total_pages': (total_playlists + per_page - 1) // per_page,
        'has_prev': playlists.has_prev,
        'has_next': playlists.has_next,
        'prev_num': playlists.prev_num,
        'next_num': playlists.next_num
    }
    
    return render_template(
        "dashboard.html",
        playlists=playlists.items,
        stats=stats,
        pagination=pagination,
        current_sort=sort_by,
        sync_status=None,
        last_sync_info=None,
        unlocked_playlist_id=None
    )


@main_bp.route("/sync-playlists", methods=["POST"])
@login_required
def sync_playlists():
    """Sync user's Spotify playlists"""
    import time
    start_time = time.time()
    
    try:
        from ..services.playlist_sync_service import PlaylistSyncService
        
        current_app.logger.info(f"Starting manual playlist sync for user {current_user.id}")
        
        sync_service = PlaylistSyncService()
        result = sync_service.sync_user_playlists(current_user)
        
        elapsed_time = int(time.time() - start_time)
        
        if result["status"] == "completed":
            playlists_count = result.get("playlists_synced", 0)
            tracks_count = result.get("total_tracks", 0)
            minutes = elapsed_time // 60
            seconds = elapsed_time % 60
            time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
            flash(f"✅ Successfully synced {playlists_count} playlists with {tracks_count} songs in {time_str}!", "success")
        else:
            error_msg = result.get("error", "Unknown error")
            flash(f"Sync failed: {error_msg}", "error")
            current_app.logger.error(f"Sync failed for user {current_user.id}: {error_msg}")
            
    except Exception as e:
        current_app.logger.error(f"Error syncing playlists for user {current_user.id}: {e}")
        flash(f"An error occurred while syncing playlists: {str(e)}", "error")
    
    return redirect(url_for("main.dashboard"))


@main_bp.route("/playlist/<int:playlist_id>")
@login_required
def playlist_detail(playlist_id):
    """Show playlist details and songs"""
    playlist = Playlist.query.get_or_404(playlist_id)
    
    # Check if user owns this playlist
    if playlist.owner_id != current_user.id:
        flash("You don't have permission to view this playlist.", "error")
        return redirect(url_for("main.dashboard"))
    
    # Get songs in playlist with analysis results (optimized with single query)
    from sqlalchemy.orm import joinedload
    
    # Get all song IDs in this playlist
    song_ids = [s.id for s in playlist.songs]
    
    # Fetch all analysis results in one query
    analysis_map = {}
    if song_ids:
        analyses = AnalysisResult.query.filter(
            AnalysisResult.song_id.in_(song_ids)
        ).all()
        analysis_map = {a.song_id: a for a in analyses}
    
    # Build songs list with cached analysis results
    songs = []
    for song in playlist.songs:
        songs.append({
            'song': song,
            'analysis_result': analysis_map.get(song.id)
        })
    
    analysis_state = {
        'total_songs': len(songs),
        'analyzed_songs': sum(1 for item in songs if item['analysis_result']),
        'analysis_percentage': round((sum(1 for item in songs if item['analysis_result']) / len(songs) * 100) if songs else 0, 1),
        'is_fully_analyzed': all(item['analysis_result'] for item in songs)
    }
    
    return render_template(
        "playlist_detail.html",
        playlist=playlist,
        songs=songs,
        analysis_state=analysis_state
    )


@main_bp.route("/playlist/<int:playlist_id>/remove/<int:song_id>", methods=["POST"])
@login_required
def remove_from_playlist(playlist_id, song_id):
    """Remove a song from a playlist (syncs with Spotify)"""
    try:
        # Get the playlist and verify ownership
        playlist = Playlist.query.get_or_404(playlist_id)
        
        if playlist.owner_id != current_user.id:
            flash("You don't have permission to modify this playlist.", "error")
            return redirect(url_for("main.dashboard"))
        
        # Remove the playlist-song association from local database
        playlist_song = PlaylistSong.query.filter_by(
            playlist_id=playlist_id,
            song_id=song_id
        ).first()
        
        if playlist_song:
            # First, sync removal to Spotify
            if playlist.spotify_id:
                try:
                    from ..services.spotify_service import SpotifyService
                    spotify_service = SpotifyService(current_user)
                    success = spotify_service.remove_song_from_playlist(playlist.spotify_id, song_id)
                    
                    if not success:
                        current_app.logger.warning(f"Failed to remove song {song_id} from Spotify playlist {playlist.spotify_id}, but continuing with local removal")
                except Exception as spotify_error:
                    current_app.logger.error(f"Error syncing removal to Spotify: {spotify_error}")
                    flash("Song removed locally, but failed to sync with Spotify. Try syncing your playlists again.", "warning")
            
            # Remove from local database
            db.session.delete(playlist_song)
            db.session.commit()
            flash("Song removed from playlist.", "success")
        else:
            flash("Song not found in playlist.", "warning")
            
    except Exception as e:
        current_app.logger.error(f"Error removing song {song_id} from playlist {playlist_id}: {e}")
        flash("An error occurred while removing the song.", "error")
        db.session.rollback()
    
    return redirect(url_for("main.playlist_detail", playlist_id=playlist_id))


@main_bp.route("/song/<int:song_id>")
@login_required
def song_detail(song_id):
    """Show song analysis details"""
    song = Song.query.get_or_404(song_id)
    
    # Get playlist_id from query params if provided
    playlist_id = request.args.get('playlist_id', type=int)
    playlist = None
    if playlist_id:
        playlist = Playlist.query.get(playlist_id)
        if playlist and playlist.owner_id != current_user.id:
            flash("You don't have permission to view this content.", "error")
            return redirect(url_for("main.dashboard"))
    
    # Get analysis result
    analysis_result = AnalysisResult.query.filter_by(song_id=song.id).first()
    
    # Get lyrics
    lyrics = song.lyrics if song.lyrics else None
    
    # Check if song is whitelisted
    is_whitelisted = False
    if current_user.is_authenticated:
        from ..models import Whitelist
        is_whitelisted = Whitelist.query.filter_by(
            user_id=current_user.id,
            spotify_id=song.spotify_id,
            item_type='song'
        ).first() is not None
    
    return render_template(
        "song_detail.html",
        song=song,
        analysis=analysis_result,
        lyrics=lyrics,
        is_whitelisted=is_whitelisted,
        playlist=playlist
    )


@main_bp.route("/contact")
def contact():
    """Contact page"""
    return render_template("legal/contact.html")


@main_bp.route("/privacy")
def privacy():
    """Privacy policy page"""
    return render_template("legal/privacy.html")


@main_bp.route("/terms")
def terms():
    """Terms of service page"""
    return render_template("legal/terms.html")


@main_bp.route("/settings")
@login_required
def user_settings():
    """User settings page"""
    return render_template("user_settings.html", user=current_user)
