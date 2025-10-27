
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
                "concerns": analysis.concerns if analysis.concerns else [],
                "verdict": analysis.verdict,
                "formation_risk": analysis.formation_risk,
                "narrative_voice": analysis.narrative_voice,
                "lament_filter_applied": analysis.lament_filter_applied,
                "biblical_themes": analysis.biblical_themes if analysis.biblical_themes else [],
                "supporting_scripture": analysis.supporting_scripture if analysis.supporting_scripture else []
            }
        })
    else:
        return jsonify({"success": False, "completed": False, "failed": False, "error": "No analysis found"})



@bp.route("/analyze_playlist/<int:playlist_id>", methods=["POST"])
@login_required
def analyze_playlist(playlist_id):
    """Queue playlist analysis as a background job (admin only)"""
    from ..models import Playlist
    from ..queue import enqueue_playlist_analysis
    
    # Admin-only check
    if not current_user.is_admin:
        return jsonify({"success": False, "error": "Admin access required"}), 403
    
    try:
        # Verify playlist exists and belongs to user
        playlist = Playlist.query.get_or_404(playlist_id)
        if playlist.owner_id != current_user.id:
            return jsonify({"success": False, "error": "Playlist not found"}), 404
        
        # Queue the analysis job
        job_id = enqueue_playlist_analysis(playlist_id, current_user.id)
        
        return jsonify({
            "success": True,
            "message": "Playlist analysis started in background",
            "job_id": job_id,
            "playlist_id": playlist_id,
            "playlist_name": playlist.name,
            "status": "queued"
        })
        
    except Exception as e:
        current_app.logger.error(f"Error queuing playlist analysis: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/analysis/status/<job_id>", methods=["GET"])
@login_required
def get_analysis_status(job_id):
    """Get the status of a background analysis job"""
    from rq.job import Job

    from ..queue import analysis_queue
    
    try:
        job = Job.fetch(job_id, connection=analysis_queue.connection)
        
        response = {
            "job_id": job_id,
            "status": job.get_status(),
            "created_at": job.created_at.isoformat() if job.created_at else None,
        }
        
        # Add progress info based on status
        if job.is_finished:
            response["result"] = job.result
            response["finished_at"] = job.ended_at.isoformat() if job.ended_at else None
            
        elif job.is_failed:
            response["error"] = str(job.exc_info) if job.exc_info else "Unknown error"
            response["failed_at"] = job.ended_at.isoformat() if job.ended_at else None
            
        elif job.is_started:
            # Get custom progress metadata
            progress = job.meta.get('progress', {})
            response["progress"] = progress
            response["started_at"] = job.started_at.isoformat() if job.started_at else None
            
        elif job.is_queued:
            position = job.get_position()
            response["position"] = position if position is not None else 0
        
        return jsonify(response)
        
    except Exception as e:
        current_app.logger.error(f"Error fetching job status for {job_id}: {e}")
        return jsonify({
            "error": "Job not found or expired",
            "job_id": job_id
        }), 404


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

