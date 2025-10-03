
"""
API Blueprint for JSON endpoints
"""

from datetime import datetime

from flask import Blueprint, current_app, jsonify, session
from flask_login import current_user, login_required
from sqlalchemy import text

from .. import db
from ..models.models import AnalysisResult
from ..services.framework_loader import get_rules
from ..services.unified_analysis_service import UnifiedAnalysisService
from ..utils.freemium import (
    freemium_enabled,
    song_belongs_to_unlocked_playlist,
)

# Queue system removed - using direct analysis with worker parallelization

bp = Blueprint("api", __name__)


@bp.route("/spotify/playlist-count")
@login_required
def spotify_playlist_count():
    """Get user's Spotify playlist count for ETA calculation"""
    try:
        from ..services.spotify_service import SpotifyService
        
        spotify_service = SpotifyService(current_user)
        playlists = spotify_service.get_user_playlists()
        
        return jsonify({
            "success": True,
            "playlist_count": len(playlists) if playlists else 0
        })
    except Exception as e:
        current_app.logger.error(f"Error getting playlist count: {e}")
        return jsonify({"success": False, "error": str(e), "playlist_count": 0}), 500


@bp.route("/health")
def health():
    """Basic health check endpoint"""
    try:
        # Test database connection
        db.session.execute(text("SELECT 1"))
        rules = get_rules()
        return jsonify(
            {
                "status": "healthy",
                "database": "connected",
                "framework_hash": rules.get("version_hash", "unknown"),
                "timestamp": datetime.now().isoformat(),
            }
        )
    except Exception as e:
        current_app.logger.error(f"Health check failed: {e}")
        return jsonify({"status": "unhealthy", "error": str(e)}), 500

@bp.route("/songs/<int:id>/analyze", methods=['POST'])
@login_required
def analyze_song_single(id):
    current_app.logger.info(f"Received request to analyze song with ID: {id}")
    # Freemium check
    if freemium_enabled() and not current_user.is_admin:
        ok, allowed_pid = song_belongs_to_unlocked_playlist(id)
        if not ok:
            return jsonify(
                {
                    "error": "upgrade_required",
                    "message": "Song analysis is restricted on the free tier",
                }
            ), 402

    svc = UnifiedAnalysisService()
    analysis = svc.analyze_song(id)

    if analysis:
        return jsonify({"success": True, "analysis_id": analysis.id})
    else:
        return jsonify({"success": False, "message": "Analysis failed to start"}), 500




@bp.route("/songs/<int:id>/analysis-status", methods=["GET"])
@login_required
def get_song_analysis_status(id):
    analysis = AnalysisResult.query.filter_by(song_id=id).order_by(AnalysisResult.created_at.desc()).first()
    if analysis:
        return jsonify({
            "success": True,
            "completed": analysis.is_complete,
            "failed": analysis.error is not None,
            "error": analysis.error,
            "result": {
                "score": analysis.score,
                "explanation": analysis.explanation,
                "concerns": analysis.concerns if analysis.concerns else []
            }
        })
    else:
        return jsonify({"success": False, "completed": False, "failed": False, "error": "No analysis found"})



@bp.route("/analyze_playlist/<int:playlist_id>", methods=["POST"])
@login_required
def analyze_playlist(playlist_id):
    """Analyze all unanalyzed songs in a specific playlist (admin only)"""
    from sqlalchemy import func
    
    from ..models import AnalysisResult, Playlist, PlaylistSong, Song
    
    # Admin-only check
    if not current_user.is_admin:
        return jsonify({"success": False, "error": "Admin access required"}), 403
    
    try:
        # Verify playlist exists and belongs to user
        playlist = Playlist.query.get_or_404(playlist_id)
        if playlist.owner_id != current_user.id:
            return jsonify({"success": False, "error": "Playlist not found"}), 404
        
        # Get all unanalyzed songs in this playlist using existing query pattern
        unanalyzed_songs = db.session.query(Song).join(
            PlaylistSong
        ).outerjoin(
            AnalysisResult, Song.id == AnalysisResult.song_id
        ).filter(
            PlaylistSong.playlist_id == playlist_id,
            db.or_(
                AnalysisResult.id.is_(None),
                AnalysisResult.status != 'completed'
            )
        ).all()
        
        if not unanalyzed_songs:
            return jsonify({
                "success": True,
                "message": "All songs already analyzed",
                "total_songs": 0,
                "analyzed": 0
            })
        
        # Use the existing UnifiedAnalysisService to analyze each song
        svc = UnifiedAnalysisService()
        analyzed_count = 0
        failed_count = 0
        
        for song in unanalyzed_songs:
            try:
                svc.analyze_song(song.id)
                analyzed_count += 1
            except Exception as e:
                current_app.logger.error(f"Failed to analyze song {song.id}: {e}")
                failed_count += 1
        
        return jsonify({
            "success": True,
            "message": f"Analyzed {analyzed_count} songs",
            "total_songs": len(unanalyzed_songs),
            "analyzed": analyzed_count,
            "failed": failed_count
        })
        
    except Exception as e:
        current_app.logger.error(f"Error analyzing playlist {playlist_id}: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/dashboard/stats")
@login_required
def get_dashboard_stats():
    """Get dashboard stats"""
    from sqlalchemy import func
    
    from ..models import AnalysisResult, Playlist, PlaylistSong, Song
    
    try:
        # Get total playlists
        total_playlists = Playlist.query.filter_by(owner_id=current_user.id).count()
        
        # Get total songs (distinct across all playlists)
        total_songs = db.session.query(func.count(func.distinct(Song.id))).join(
            PlaylistSong
        ).join(
            Playlist
        ).filter(
            Playlist.owner_id == current_user.id
        ).scalar() or 0
        
        # Get analyzed songs count
        analyzed_songs = db.session.query(func.count(func.distinct(AnalysisResult.song_id))).join(
            AnalysisResult.song_rel
        ).join(
            Song.playlist_associations
        ).join(
            PlaylistSong.playlist
        ).filter(
            Playlist.owner_id == current_user.id,
            AnalysisResult.status == 'completed'
        ).scalar() or 0
        
        # Calculate analysis progress percentage
        analysis_progress = (analyzed_songs / total_songs * 100) if total_songs > 0 else 0
        
        # Get clean playlists (score >= 75%)
        clean_playlists = Playlist.query.filter(
            Playlist.owner_id == current_user.id,
            Playlist.overall_alignment_score >= 0.75
        ).count()
        
        return jsonify({
            "success": True,
            "totals": {
                "total_playlists": total_playlists,
                "total_songs": total_songs,
                "analyzed_songs": analyzed_songs,
                "analysis_progress": round(analysis_progress, 1),
                "clean_playlists": clean_playlists
            }
        })
    except Exception as e:
        current_app.logger.error(f"Error getting dashboard stats: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/analysis/start-all", methods=["POST"])
@login_required
def start_batch_analysis():
    """Start batch analysis for all unanalyzed songs for the current user"""
    try:
        current_app.logger.info(f"Starting batch analysis for user {current_user.id}")
        
        svc = UnifiedAnalysisService()
        result = svc.auto_analyze_user_after_sync(current_user.id)
        
        if result.get("success"):
            return jsonify({
                "success": True,
                "message": result.get("message"),
                "songs_analyzed": result.get("songs_analyzed", 0),
                "songs_failed": result.get("songs_failed", 0),
                "total_songs": result.get("total_songs", 0)
            })
        else:
            return jsonify({
                "success": False,
                "error": result.get("error", "Analysis failed")
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"Batch analysis failed for user {current_user.id}: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route("/analysis/progress", methods=["GET"])
@login_required
def get_analysis_progress():
    """Get the current analysis progress for the current user"""
    try:
        svc = UnifiedAnalysisService()
        progress = svc.get_analysis_progress(current_user.id)
        
        if progress.get("success"):
            return jsonify(progress)
        else:
            return jsonify({
                "success": False,
                "error": progress.get("error", "Failed to get progress")
            }), 500
            
    except Exception as e:
        current_app.logger.error(f"Failed to get progress for user {current_user.id}: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route("/clear-analysis-modal", methods=["POST"])
@login_required
def clear_analysis_modal():
    """Clear the analysis modal session flag"""
    session.pop('show_analysis_modal', None)
    session.pop('sync_info', None)
    return jsonify({"success": True})


@bp.route("/background-analysis/public-status")
def get_background_analysis_public_status():
    """Get background analysis public status"""
    # Implement logic to get background analysis public status
    return jsonify({"success": True, "status": {}})

