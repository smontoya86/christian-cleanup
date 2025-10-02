
"""
API Blueprint for JSON endpoints
"""

from datetime import datetime

from flask import Blueprint, current_app, jsonify
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



@bp.route("/dashboard/stats")
@login_required
def get_dashboard_stats():
    """Get dashboard stats"""
    # Implement logic to get dashboard stats
    return jsonify({"success": True, "stats": {}})


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


@bp.route("/background-analysis/public-status")
def get_background_analysis_public_status():
    """Get background analysis public status"""
    # Implement logic to get background analysis public status
    return jsonify({"success": True, "status": {}})

