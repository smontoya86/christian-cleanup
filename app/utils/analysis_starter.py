"""
Background user analysis starter and status helper.
"""

from __future__ import annotations

import threading
import time
from typing import List

from app import db
from app.models import AnalysisResult, Playlist, PlaylistSong, Song
from app.services.unified_analysis_service import UnifiedAnalysisService


def start_user_analysis(app, user_id: int) -> dict:
    """Start background analysis for a user's eligible songs.

    Returns a dict with 'queued' count and 'job_id'.
    """
    with app.app_context():
        # Gather user's distinct songs
        songs: List[Song] = (
            db.session.query(Song)
            .join(PlaylistSong)
            .join(Playlist)
            .filter(Playlist.owner_id == user_id)
            .distinct()
            .all()
        )

        # Filter eligible (has lyrics) and not already completed
        eligible_ids: List[int] = []
        for s in songs:
            if not (s.lyrics and s.lyrics.strip() and s.lyrics != "Lyrics not available"):
                continue
            latest = (
                AnalysisResult.query.filter_by(song_id=s.id)
                .order_by(AnalysisResult.created_at.desc())
                .first()
            )
            if latest:
                continue  # All stored analyses are completed by definition
            eligible_ids.append(s.id)

        # Create or update progress snapshot
        state = app.config.setdefault("USER_ANALYSIS_PROGRESS", {})
        import uuid

        job_id = f"user-analysis:{uuid.uuid4()}"
        state[user_id] = {
            "active": True,
            "total_songs": len(eligible_ids),
            "completed": 0,
            "failed": 0,
            "started_at": time.time(),
            "job_id": job_id,
        }

        def _runner(app_inst, uid, ids):
            with app_inst.app_context():
                svc = UnifiedAnalysisService()
                completed = 0
                failed = 0
                for sid in ids:
                    try:
                        song_obj = db.session.get(Song, sid)
                        if not song_obj:
                            failed += 1
                            continue
                        ar = svc.analysis_service.analyze_song(
                            song_obj.title or song_obj.name, song_obj.artist, song_obj.lyrics or ""
                        )
                        analysis = (
                            AnalysisResult.query.filter_by(song_id=sid)
                            .order_by(AnalysisResult.created_at.desc())
                            .first()
                        )
                        if not analysis:
                            analysis = AnalysisResult(song_id=sid)
                            db.session.add(analysis)
                        analysis.mark_completed(
                            score=ar.scoring_results.get("final_score", 85),
                            concern_level=svc._map_concern_level(
                                ar.scoring_results.get("quality_level", "Unknown")
                            ),
                            themes=ar.biblical_analysis.get("themes", []),
                            explanation=ar.scoring_results.get("explanation", "Analysis completed"),
                            purity_flags_details=ar.content_analysis.get("detailed_concerns", []),
                            positive_themes_identified=ar.biblical_analysis.get("themes", []),
                            biblical_themes=ar.biblical_analysis.get("themes", []),
                            supporting_scripture=ar.biblical_analysis.get(
                                "supporting_scripture", []
                            ),
                        )
                        db.session.commit()
                        completed += 1
                    except Exception:
                        db.session.rollback()
                        failed += 1
                    finally:
                        prog = app_inst.config.get("USER_ANALYSIS_PROGRESS", {})
                        if uid in prog:
                            prog[uid]["completed"] = completed
                            prog[uid]["failed"] = failed
                prog = app_inst.config.get("USER_ANALYSIS_PROGRESS", {})
                if uid in prog:
                    prog[uid]["active"] = False

        threading.Thread(target=_runner, args=(app, user_id, eligible_ids), daemon=True).start()
        return {"queued": len(eligible_ids), "job_id": job_id}


def get_user_analysis_status(app, user_id: int) -> dict:
    """Return the current analysis progress snapshot for a user."""
    with app.app_context():
        prog = app.config.get("USER_ANALYSIS_PROGRESS", {})
        snap = prog.get(user_id)
        if not snap:
            return {"active": False}
        # Basic estimate: assume 30 songs/hour
        remaining = max(0, snap["total_songs"] - (snap["completed"] + snap["failed"]))
        estimated_hours = remaining / 30.0 if remaining > 0 else -1
        return {
            "status": "success",
            "active": snap["active"],
            "total_songs": snap["total_songs"],
            "recent_completed": snap["completed"],
            "processing_rate": 30,  # rough default
            "estimated_hours": estimated_hours,
            "job_id": snap.get("job_id"),
        }
