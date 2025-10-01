
"""
API Blueprint for JSON endpoints
"""

import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta

import requests as _req
from flask import Blueprint, Response, current_app, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import text

from app.utils.analysis_starter import get_user_analysis_status

from .. import db
from ..models.models import AnalysisResult, Playlist, PlaylistSong, Song, User, Whitelist
from ..services.framework_loader import get_rules
from ..services.progress_tracker import JobType, get_progress_tracker
from ..services.unified_analysis_service import UnifiedAnalysisService
from ..utils.auth import admin_required
from ..utils.correlation import get_request_id
from ..utils.freemium import (
    free_playlist_id_for_user,
    freemium_enabled,
    is_playlist_unlocked,
    mask_playlist_score_for_user,
    song_belongs_to_unlocked_playlist,
)
from ..utils.ga4 import send_event_async
from ..utils.cache import cache_get_json, cache_set_json

# Queue system removed - using direct analysis with worker parallelization
from ..utils.health_monitor import health_monitor
from ..utils.prometheus_metrics import get_metrics, metrics_collector
from ..utils.request_validation import (
    GA4CompletedSchema,
    TestSemanticDetectionSchema,
    WhitelistAddSchema,
    WhitelistQuerySchema,
    validate_json,
    validate_query,
)

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

@bp.route("/background-analysis/public-status")
def get_background_analysis_public_status():
    """Get background analysis public status"""
    # Implement logic to get background analysis public status
    return jsonify({"success": True, "status": {}})

