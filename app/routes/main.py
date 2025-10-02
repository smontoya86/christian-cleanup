"""
Main application routes for Music Disciple
"""

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import desc, func

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
    # Get user's playlists
    playlists = Playlist.query.filter_by(owner_id=current_user.id).order_by(
        desc(Playlist.updated_at)
    ).all()
    
    # Calculate stats
    total_playlists = len(playlists)
    total_songs = db.session.query(func.count(Song.id.distinct())).join(
        Song.playlist_associations
    ).join(
        PlaylistSong.playlist
    ).filter(
        Playlist.owner_id == current_user.id
    ).scalar() or 0
    
    analyzed_songs = db.session.query(func.count(AnalysisResult.id.distinct())).join(
        AnalysisResult.song
    ).join(
        Song.playlist_associations
    ).join(
        PlaylistSong.playlist
    ).filter(
        Playlist.owner_id == current_user.id,
        AnalysisResult.status == 'completed'
    ).scalar() or 0
    
    stats = {
        'total_playlists': total_playlists,
        'total_songs': total_songs,
        'analyzed_songs': analyzed_songs,
        'clean_playlists': 0  # TODO: Implement clean playlist calculation
    }
    
    return render_template(
        "dashboard.html",
        playlists=playlists,
        stats=stats,
        pagination=None,  # TODO: Implement pagination
        sync_status=None,  # TODO: Implement sync status
        last_sync_info=None,  # TODO: Implement last sync info
        unlocked_playlist_id=None  # TODO: Implement freemium logic
    )


@main_bp.route("/sync-playlists", methods=["POST"])
@login_required
def sync_playlists():
    """Sync user's Spotify playlists"""
    # TODO: Implement playlist sync logic
    flash("Playlist sync coming soon!", "info")
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
    
    # Get songs in playlist with analysis results
    songs = []
    for song in playlist.songs:
        analysis_result = AnalysisResult.query.filter_by(song_id=song.id).first()
        songs.append({
            'song': song,
            'analysis_result': analysis_result
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
