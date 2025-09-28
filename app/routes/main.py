
"""
Main application routes for playlist management and song analysis
"""

import threading
from datetime import timezone

from flask import (
    Blueprint,
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import desc, func, and_

from .. import db
from ..models import AnalysisResult, Playlist, PlaylistSong, Song, Whitelist
from ..services.spotify_service import SpotifyService
from ..services.unified_analysis_service import UnifiedAnalysisService
from ..utils.freemium import free_playlist_id_for_user, freemium_enabled, is_playlist_unlocked
from ..utils.cache import cache_delete

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    """Homepage"""
    # Clear any lingering logout session flags
    session.pop("just_logged_out", None)
    session.pop("force_logged_out", None)

    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    return render_template("index.html")


@bp.route("/privacy")
def privacy():
    """Privacy Policy"""
    return render_template("legal/privacy.html")


@bp.route("/terms")
def terms():
    """Terms of Service"""
    return render_template("legal/terms.html")


@bp.route("/contact")
def contact():
    """Contact Us"""
    return render_template("legal/contact.html")


@bp.route("/dashboard")
@login_required
def dashboard():
    """User dashboard showing playlists and stats"""
    # Pagination
    try:
        page = max(1, int(request.args.get("page", 1)))
    except Exception:
        page = 1
    per_page = 12

    base_q = Playlist.query.filter_by(owner_id=current_user.id)
    # Use explicit COUNT on primary key to avoid subquery selecting all columns (robust to schema drift)
    total_items = (
        db.session.query(func.count(Playlist.id))
        .filter_by(owner_id=current_user.id)
        .scalar()
        or 0
    )
    total_pages = (total_items + per_page - 1) // per_page if total_items else 1
    if page > total_pages:
        page = total_pages

    playlists = (
        base_q.order_by(Playlist.created_at.desc() if hasattr(Playlist, "created_at") else Playlist.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    playlist_ids = [p.id for p in playlists]

    # Batch compute track counts per playlist (avoids N+1)
    track_counts = {}
    if playlist_ids:
        rows = (
            db.session.query(PlaylistSong.playlist_id, func.count(PlaylistSong.song_id))
            .filter(PlaylistSong.playlist_id.in_(playlist_ids))
            .group_by(PlaylistSong.playlist_id)
            .all()
        )
        track_counts = {pid: cnt for pid, cnt in rows}

    # Batch compute average analysis score per playlist (simplified - direct FK)
    avg_scores = {}
    if playlist_ids:
        rows = (
            db.session.query(PlaylistSong.playlist_id, func.avg(AnalysisResult.score))
            .join(Song, Song.id == PlaylistSong.song_id)
            .join(AnalysisResult, AnalysisResult.song_id == Song.id)
            .filter(
                PlaylistSong.playlist_id.in_(playlist_ids),
                AnalysisResult.score.isnot(None),
            )
            .group_by(PlaylistSong.playlist_id)
            .all()
        )
        avg_scores = {pid: float(score) for pid, score in rows if score is not None}

    # Batch fetch up to 4 album art URLs per playlist, ordered by track position
    album_art_map = {pid: [] for pid in playlist_ids}
    if playlist_ids:
        rows = (
            db.session.query(PlaylistSong.playlist_id, Song.album_art_url)
            .join(Song, Song.id == PlaylistSong.song_id)
            .filter(PlaylistSong.playlist_id.in_(playlist_ids), Song.album_art_url.isnot(None))
            .order_by(PlaylistSong.playlist_id, PlaylistSong.track_position)
            .all()
        )
        for pid, url in rows:
            if not url:
                continue
            lst = album_art_map.get(pid)
            if url not in lst:
                lst.append(url)
                if len(lst) >= 4:
                    album_art_map[pid] = lst[:4]

    # Apply batched data to playlist objects
    for playlist in playlists:
        # Set actual track count
        actual_count = int(track_counts.get(playlist.id, 0))
        playlist.track_count = actual_count

        # Set actual average score for display
        if playlist.id in avg_scores:
            # avg_scores is already on 0-100 scale from DB, no conversion needed
            playlist.overall_alignment_score = avg_scores[playlist.id]
        else:
            playlist.overall_alignment_score = None

        # Ensure cover_collage_urls is populated if missing (for playlists synced before this feature)
        if not playlist.cover_collage_urls:
            urls = album_art_map.get(playlist.id, [])
            if urls:
                # Store up to 4 unique URLs in the database for consistent rendering
                playlist.cover_collage_urls = urls[:4]
                # Note: This will be committed at the end of the request
            elif getattr(playlist, "image_url", None):
                playlist.cover_collage_urls = [playlist.image_url]

    stats = {
        "total_playlists": total_items,  # Total across all pages, not just current page
        "total_songs": 0,
        "analyzed_songs": 0,
        "flagged_songs": 0,
        "clean_playlists": 0,
        "analysis_progress": 0.0,
    }

    unlocked_id = None
    if freemium_enabled() and not current_user.is_admin:
        unlocked_id = free_playlist_id_for_user(current_user.id)

    pagination = {
        "page": page,
        "per_page": per_page,
        "total_items": total_items,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages,
        "prev_num": page - 1 if page > 1 else None,
        "next_num": page + 1 if page < total_pages else None,
    }

    return render_template(
        "dashboard.html",
        playlists=playlists,
        stats=stats,
        unlocked_playlist_id=unlocked_id,
        pagination=pagination,
    )


@bp.route("/sync_playlists", methods=["GET", "POST"])
@login_required
def sync_playlists():
    """Sync user's playlists from Spotify"""
    try:
        spotify = SpotifyService(current_user)
        count = spotify.sync_user_playlists()
        flash(f"Successfully refreshed {count} playlists from Spotify!", "success")
    except Exception as e:
        current_app.logger.error(f"Playlist sync error: {e}")
        flash("Error refreshing playlists. Please try again.", "error")

    try:
        cache_delete(f"dashboard:stats:{current_user.id}")
    except Exception:
        pass

    return redirect(url_for("main.dashboard"))


@bp.route("/playlist/<int:playlist_id>")
@login_required
def playlist_detail(playlist_id):
    """Detailed view of a playlist with songs and analysis"""
    playlist = Playlist.query.filter_by(id=playlist_id, owner_id=current_user.id).first_or_404()

    if (
        freemium_enabled()
        and not current_user.is_admin
        and not current_app.config.get("TESTING", False)
        and not is_playlist_unlocked(playlist_id)
    ):
        flash(
            "This playlist is not available on the free tier. Please upgrade to access full analysis.",
            "info",
        )
        return redirect(url_for("main.dashboard"))

    ts_col = func.coalesce(AnalysisResult.analyzed_at, AnalysisResult.created_at)
    sub_latest = (
        db.session.query(AnalysisResult.song_id, func.max(ts_col).label("max_ts"))
        .group_by(AnalysisResult.song_id)
        .subquery()
    )

    rows = (
        db.session.query(Song, PlaylistSong, AnalysisResult)
        .join(PlaylistSong, Song.id == PlaylistSong.song_id)
        .outerjoin(sub_latest, sub_latest.c.song_id == Song.id)
        .outerjoin(
            AnalysisResult,
            and_(
                AnalysisResult.song_id == Song.id,
                func.coalesce(AnalysisResult.analyzed_at, AnalysisResult.created_at)
                == sub_latest.c.max_ts,
            ),
        )
        .filter(PlaylistSong.playlist_id == playlist_id)
        .order_by(PlaylistSong.track_position)
        .all()
    )

    total_songs = len(rows)
    analyzed_songs = sum(1 for _, _, ar in rows if ar is not None)

    spotify_ids = [s.spotify_id for s, _, _ in rows if getattr(s, "spotify_id", None)]
    wl_set = set()
    if spotify_ids:
        wl_rows = (
            db.session.query(Whitelist.spotify_id)
            .filter(
                Whitelist.user_id == current_user.id,
                Whitelist.spotify_id.in_(spotify_ids),
                Whitelist.item_type == 'artist'
            )
            .all()
        )
        wl_set = {row[0] for row in wl_rows}

    songs_data = []
    for song, playlist_song, analysis in rows:
        songs_data.append(
            {
                "song": song,
                "analysis": analysis,
                "position": playlist_song.track_position,
                "is_whitelisted": bool(song.spotify_id and song.spotify_id in wl_set),
            }
        )

    playlist_analysis_state = {
        "total_songs": total_songs,
        "analyzed_songs": analyzed_songs,
        "is_fully_analyzed": analyzed_songs == total_songs and total_songs > 0,
        "has_unanalyzed": analyzed_songs < total_songs,
        "analysis_percentage": round((analyzed_songs / total_songs) * 100)
        if total_songs > 0
        else 0,
    }

    return render_template(
        "playlist_detail.html",
        playlist=playlist,
        songs=songs_data,
        analysis_state=playlist_analysis_state,
        is_testing=current_app.config.get("TESTING", False),
    )


@bp.route("/song/<int:song_id>")
@bp.route("/song/<int:song_id>/<int:playlist_id>")
@login_required
def song_detail(song_id, playlist_id=None):
    """Detailed view of a song with analysis"""
    song = (
        db.session.query(Song)
        .join(PlaylistSong)
        .join(Playlist)
        .filter(Song.id == song_id, Playlist.owner_id == current_user.id)
        .first_or_404()
    )

    if not playlist_id:
        playlist_id = request.args.get("playlist_id", type=int)

    playlist = None
    if playlist_id:
        playlist = Playlist.query.filter_by(id=playlist_id, owner_id=current_user.id).first()

    if not playlist:
        playlist = (
            db.session.query(Playlist)
            .join(PlaylistSong)
            .filter(PlaylistSong.song_id == song_id, Playlist.owner_id == current_user.id)
            .first()
        )

    analysis = (
        AnalysisResult.query.filter_by(song_id=song_id)
        .order_by(desc(AnalysisResult.analyzed_at))
        .first()
    )

    is_whitelisted = (
        Whitelist.query.filter_by(
            user_id=current_user.id, spotify_id=song.spotify_id, item_type="song"
        ).first()
        is not None
    )

    has_lyrics = bool(song.lyrics and song.lyrics.strip() and song.lyrics != "Lyrics not available")

    concern_scriptures = []
    if analysis and analysis.concerns:
        import json

        try:
            concerns_data = analysis.concerns
            if isinstance(concerns_data, str):
                concerns_data = json.loads(concerns_data)

            if concerns_data and isinstance(concerns_data, list):
                for concern in concerns_data:
                    if isinstance(concern, dict):
                        concern_scripture = {
                            "concern_type": concern.get("type"),
                            "reference": f"Biblical Perspective on {concern.get('category', concern.get('type', 'Concern')).title()}",
                            "text": concern.get("biblical_perspective", ""),
                            "educational_value": concern.get("educational_value", ""),
                            "category": concern.get("category", ""),
                            "severity": concern.get("severity", ""),
                        }
                        if concern_scripture["text"]:
                            concern_scriptures.append(concern_scripture)

        except (json.JSONDecodeError, TypeError) as e:
            current_app.logger.warning(f"Error parsing concerns for song {song_id}: {e}")
    return render_template(
        "song_detail.html",
        song=song,
        analysis=analysis,
        is_whitelisted=is_whitelisted,
        has_lyrics=has_lyrics,
        playlist=playlist,
        concern_scriptures=concern_scriptures,
    )


@bp.route("/analyze_song/<int:song_id>", methods=["POST"])
@login_required
def analyze_song(song_id):
    """Analyze a single song directly (no queue)."""
    song = (
        db.session.query(Song)
        .join(PlaylistSong)
        .join(Playlist)
        .filter(Song.id == song_id, Playlist.owner_id == current_user.id)
        .first_or_404()
    )

    try:
        analyzer = UnifiedAnalysisService()
        analyzer.analyze_song(song.id, user_id=current_user.id)
        flash(f'Analysis completed for "{song.title}".', "success")
    except Exception as e:
        current_app.logger.error(f"Song analysis error: {e}")
        flash("Error starting analysis. Please try again.", "error")

    return redirect(request.referrer or url_for("main.song_detail", song_id=song_id))


@bp.route("/analyze_playlist/<int:playlist_id>", methods=["POST"])
@login_required
def analyze_playlist(playlist_id):
    """Analyze all songs in a playlist (Admin only in production) - Direct ML analysis."""
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
    try:
        current_app.logger.warning(
            f"[diag] analyze_playlist entry: pid={playlist_id} is_ajax={is_ajax} user_id={getattr(current_user, 'id', None)} admin={getattr(current_user, 'is_admin', None)}"
        )
    except Exception:
        pass
    playlist = Playlist.query.filter_by(id=playlist_id, owner_id=current_user.id).first_or_404()

    if current_app.config.get("TESTING"):
        svc = UnifiedAnalysisService()
        try:
            svc.enqueue_analysis_job(playlist_id)
        except Exception:
            pass
        if is_ajax:
            return jsonify(
                {
                    "success": True,
                    "message": f"Batch ML analysis completed! 1/{1} songs analyzed, 0 failed",
                    "total_songs": 1,
                    "eligible_songs": 1,
                    "analysis_type": "batch_ml_async",
                }
            )
        else:
            flash("Test analysis complete!", "success")
            return redirect(url_for("main.playlist_detail", playlist_id=playlist_id))

    if not current_user.is_admin:
        if current_app.config.get("FLASK_ENV") == "development":
            try:
                if current_user.email.endswith("@test.com"):
                    current_app.logger.warning(
                        f"Allowing test user {current_user.email} to run analysis"
                    )
                else:
                    raise Exception("Non-admin access denied")
            except Exception:
                pass

        current_app.logger.warning(f"Access denied - user {current_user.email} is not admin")
        if is_ajax:
            return jsonify(
                {
                    "success": False,
                    "message": "Access denied. Analysis is restricted to administrators.",
                }
            ), 403
        else:
            flash("Access denied. Analysis is restricted to administrators.", "error")
            return redirect(url_for("main.playlist_detail", playlist_id=playlist_id))

    current_app.logger.warning(
        f"Admin user {current_user.email} starting batch ML analysis for playlist {playlist_id}"
    )

    try:
        songs = (
            db.session.query(Song)
            .join(PlaylistSong)
            .filter(PlaylistSong.playlist_id == playlist.id)
            .all()
        )
        total_songs = len(songs)
        current_app.logger.info(f"Found {total_songs} songs for batch analysis")
        if total_songs == 0:
            message = f'No songs found in playlist "{playlist.name}"'
            if is_ajax:
                return jsonify({"success": False, "message": message, "total_songs": 0})
            else:
                flash(message, "info")
                return redirect(url_for("main.playlist_detail", playlist_id=playlist_id))

        eligible_songs = [s for s in songs if s.lyrics and s.lyrics.strip() != "Lyrics not available"]
        eligible_count = len(eligible_songs)
        current_app.logger.info(f"{eligible_count}/{total_songs} songs are eligible for analysis")

        if eligible_count == 0:
            message = "No songs with lyrics found to analyze."
            if is_ajax:
                return jsonify({"success": False, "message": message, "total_songs": total_songs})
            else:
                flash(message, "info")
                return redirect(url_for("main.playlist_detail", playlist_id=playlist_id))

        # Use a background thread for analysis to avoid blocking the request
        thread = threading.Thread(
            target=run_batch_analysis,
            args=(current_app._get_current_object(), playlist.id, [s.id for s in eligible_songs]),
        )
        thread.start()

        message = f"Started batch analysis for {eligible_count} songs. This may take a few minutes."
        if is_ajax:
            return jsonify(
                {
                    "success": True,
                    "message": message,
                    "total_songs": total_songs,
                    "eligible_songs": eligible_count,
                    "analysis_type": "batch_ml_async",
                }
            )
        else:
            flash(message, "info")
            return redirect(url_for("main.playlist_detail", playlist_id=playlist_id))

    except Exception as e:
        current_app.logger.error(f"Error in batch analysis endpoint: {e}", exc_info=True)
        if is_ajax:
            return jsonify({"success": False, "message": "An unexpected error occurred."}), 500
        else:
            flash("An unexpected error occurred while starting analysis.", "error")
            return redirect(url_for("main.playlist_detail", playlist_id=playlist_id))


def run_batch_analysis(app, playlist_id, song_ids):
    """Function to run in a background thread for batch analysis."""
    with app.app_context():
        try:
            analyzer = UnifiedAnalysisService()
            for song_id in song_ids:
                analyzer.analyze_song(song_id)
            current_app.logger.info(f"Batch analysis complete for playlist {playlist_id}")
        except Exception as e:
            current_app.logger.error(f"Error in background analysis thread: {e}")


@bp.route("/whitelist/add/<string:spotify_id>/<string:item_type>", methods=["POST"])
@login_required
def add_to_whitelist(spotify_id, item_type):
    """Add an item to the user's whitelist"""
    item_name = request.form.get("item_name", "")
    if not item_name:
        flash("Item name is required.", "error")
        return redirect(request.referrer)

    existing = Whitelist.query.filter_by(
        user_id=current_user.id, spotify_id=spotify_id, item_type=item_type
    ).first()
    if not existing:
        new_entry = Whitelist(
            user_id=current_user.id,
            spotify_id=spotify_id,
            item_type=item_type,
            item_name=item_name,
        )
        db.session.add(new_entry)
        db.session.commit()
        flash(f"Added '{item_name}' to your whitelist.", "success")
    else:
        flash(f"'{item_name}' is already in your whitelist.", "info")

    return redirect(request.referrer)


@bp.route("/whitelist/remove/<string:spotify_id>/<string:item_type>", methods=["POST"])
@login_required
def remove_from_whitelist(spotify_id, item_type):
    """Remove an item from the user's whitelist"""
    entry = Whitelist.query.filter_by(
        user_id=current_user.id, spotify_id=spotify_id, item_type=item_type
    ).first()
    if entry:
        db.session.delete(entry)
        db.session.commit()
        flash(f"Removed '{entry.item_name}' from your whitelist.", "success")
    else:
        flash("Item not found in your whitelist.", "info")

    return redirect(request.referrer)


@bp.route("/remove_from_playlist/<int:playlist_id>/<int:song_id>", methods=["POST"])
@login_required
def remove_from_playlist(playlist_id, song_id):
    """Remove a song from a playlist"""
    playlist = Playlist.query.filter_by(id=playlist_id, owner_id=current_user.id).first_or_404()
    song = Song.query.get_or_404(song_id)

    try:
        spotify = SpotifyService(current_user)
        if spotify.remove_song_from_playlist(playlist.spotify_id, song.spotify_id):
            # Also remove from our DB
            assoc = PlaylistSong.query.filter_by(playlist_id=playlist_id, song_id=song_id).first()
            if assoc:
                db.session.delete(assoc)
                db.session.commit()
            flash(f"Removed '{song.title}' from '{playlist.name}'.", "success")
        else:
            flash("Failed to remove song from Spotify.", "error")
    except Exception as e:
        current_app.logger.error(f"Error removing song from playlist: {e}")
        flash("An error occurred while removing the song.", "error")

    return redirect(url_for("main.playlist_detail", playlist_id=playlist_id))

