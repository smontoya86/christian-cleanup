"""
API Blueprint for JSON endpoints

Analysis Endpoint Structure:
- Single Song Analysis: POST /songs/<id>/analyze (queue analysis)
- Single Song Status: GET /songs/<id>/analysis-status (check status)
- Single Song Results: GET /song/<id>/analysis (get results)

- Playlist Analysis (Unanalyzed): POST /playlists/<id>/analyze-unanalyzed (queue only unanalyzed)
- Playlist Analysis (All): POST /playlists/<id>/reanalyze-all (force requeue all)
- Playlist Status: GET /playlists/<id>/analysis-status (consolidated progress & status)

- Overall Status: GET /analysis/status (user-wide analysis progress)
- Admin Status: GET /admin/reanalysis-status (admin-level view)

- Queue Management: GET /queue/status (queue status and health)
- Worker Health: GET /worker/health (worker status and monitoring)
- Job Status: GET /jobs/<job_id>/status (individual job tracking)
- Queue Health: GET /queue/health (queue system health check)

Note: Different endpoint patterns maintained for backward compatibility with frontend JavaScript
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
from ..services.rules_rag import build_index as rag_build_index
from ..services.rules_rag import status as rag_status
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


@bp.route("/admin/warm", methods=["POST"])
@login_required
@admin_required
def admin_warm():
    """Warm up RAG and LLM to reduce first-request latency."""
    started = time.time()
    steps = {}
    try:
        t0 = time.time()
        # Rebuild RAG (no force by default to reuse index)
        try:
            rag_info = rag_build_index(force=False)
        except Exception as e:
            rag_info = {"enabled": False, "error": str(e)}
        steps["rag"] = {"t": round(time.time() - t0, 3), "info": rag_info}

        # Analyzer preflight and minimal LLM warmup
        t1 = time.time()
        from ..services.analyzer_cache import initialize_analyzer

        analyzer = initialize_analyzer()
        ok = True
        msg = "ready"
        if hasattr(analyzer, "preflight"):
            ok, msg = analyzer.preflight()
        steps["preflight"] = {"ok": ok, "message": msg, "t": round(time.time() - t1, 3)}

        # Optional tiny chat prompt to prime KV cache
        warm = {}
        try:
            base = os.environ.get("LLM_API_BASE_URL")
            model = os.environ.get("LLM_MODEL")
            if base and model and ok:
                t2 = time.time()
                resp = _req.post(
                    f"{base.rstrip('/')}/chat/completions",
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": "You are a fast JSON responder."},
                            {"role": "user", "content": "ping"},
                        ],
                        "max_tokens": 1,
                        "temperature": 0,
                    },
                    timeout=10,
                )
                warm = {"status": resp.status_code, "t": round(time.time() - t2, 3)}
            else:
                warm = {"skipped": True}
        except Exception as e:
            warm = {"error": str(e)}
        steps["llm_warm"] = warm

        return jsonify(
            {"success": True, "t_total": round(time.time() - started, 3), "steps": steps}
        ), 200
    except Exception as e:
        return jsonify(
            {
                "success": False,
                "error": str(e),
                "t_total": round(time.time() - started, 3),
                "steps": steps,
            }
        ), 500


@bp.route("/admin/diagnostics", methods=["GET"])
@login_required
@admin_required
def admin_diagnostics():
    """Comprehensive diagnostics: DB, Redis, LLM preflight, RAG, and safe config echo."""
    info = {
        "timestamp": datetime.now().isoformat(),
        "app": "christian-music-curator",
        "environment": os.environ.get("FLASK_ENV") or current_app.config.get("ENV"),
    }

    # DB check
    try:
        db.session.execute(text("SELECT 1"))
        info["database"] = {"status": "ok"}
    except Exception as e:
        info["database"] = {"status": "error", "message": str(e)}

    # Redis check
    try:
        import redis

        r = redis.from_url(
            current_app.config.get(
                "RQ_REDIS_URL", os.environ.get("REDIS_URL", "redis://redis:6379/0")
            )
        )
        r.ping()
        info["redis"] = {"status": "ok"}
    except Exception as e:
        info["redis"] = {"status": "error", "message": str(e)}

    # RAG status
    try:
        info["rag"] = rag_status()
    except Exception as e:
        info["rag"] = {"enabled": False, "error": str(e)}

    # LLM preflight + config
    llm_cfg = {
        "api_base": os.environ.get("LLM_API_BASE_URL"),
        "model": os.environ.get("LLM_MODEL"),
    }
    try:
        from ..services.analyzer_cache import initialize_analyzer

        analyzer = initialize_analyzer()
        if hasattr(analyzer, "preflight"):
            ok, msg = analyzer.preflight()
            info["llm"] = {"ready": bool(ok), "message": msg, **llm_cfg}
        else:
            info["llm"] = {"ready": True, "message": "local analyzer", **llm_cfg}
    except Exception as e:
        info["llm"] = {"ready": False, "message": str(e), **llm_cfg}

    # Backfill settings (safe)
    info["backfill"] = {
        "workers": os.environ.get("BACKFILL_WORKERS"),
        "batch_size": os.environ.get("BACKFILL_BATCH_SIZE"),
        "autobackoff": os.environ.get("BACKFILL_AUTOBACKOFF", "1") in ("1", "true", "True"),
        "min_workers": os.environ.get("BACKFILL_MIN_WORKERS", "1"),
        "min_batch": os.environ.get("BACKFILL_MIN_BATCH", "5"),
    }

    # Redis URL masked
    raw_redis = current_app.config.get("RQ_REDIS_URL", os.environ.get("REDIS_URL"))
    if raw_redis:
        try:
            from urllib.parse import urlparse

            p = urlparse(raw_redis)
            masked = f"{p.scheme}://{p.hostname}:{p.port or ''}{p.path or ''}"
        except Exception:
            masked = "set"
        info["config"] = {"redis_url": masked}
    else:
        info["config"] = {"redis_url": None}

    return jsonify({"success": True, "diagnostics": info}), 200

@bp.route("/admin/llm-router", methods=["GET"])
@login_required
@admin_required
def admin_llm_router_config():
    """Expose current LLM router configuration and a dry-run route decision.

    Optional query param: batch_size (int) to simulate routing decision.
    """
    try:
        batch_size = request.args.get("batch_size", type=int)
        cfg = {
            "interactive": {
                "api_base": os.environ.get("LLM_INTERACTIVE_API_BASE_URL")
                or os.environ.get("LLM_API_BASE_URL"),
                "model": os.environ.get("LLM_INTERACTIVE_MODEL")
                or os.environ.get("LLM_MODEL"),
            },
            "bulk": {
                "api_base": os.environ.get("LLM_BULK_API_BASE_URL")
                or os.environ.get("LLM_API_BASE_URL"),
                "model": os.environ.get("LLM_BULK_MODEL") or os.environ.get("LLM_MODEL"),
            },
            "threshold": int(os.environ.get("LLM_ROUTER_BULK_THRESHOLD", "150")),
            "enabled": os.environ.get("USE_LLM_ANALYZER", "0") in ("1", "true", "True"),
        }

        route = None
        if batch_size is not None:
            route = "bulk" if batch_size >= cfg["threshold"] else "interactive"

        return jsonify({
            "success": True,
            "router": cfg,
            "dry_run": {
                "batch_size": batch_size,
                "route": route,
            },
        })
    except Exception as e:
        current_app.logger.error(f"LLM router config error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500



@bp.route("/admin/reload-framework", methods=["POST"])
@login_required
@admin_required
def reload_framework():
    """Reload framework docs into analyzer registry."""
    try:
        rules = get_rules(force_refresh=True)
        # Optionally rebuild RAG index if enabled
        try:
            rag_info = rag_build_index(force=True)
        except Exception:
            rag_info = {"enabled": False}
        return jsonify(
            {"success": True, "hash": rules.get("version_hash", "unknown"), "rag": rag_info}
        ), 200
    except Exception as e:
        current_app.logger.error(f"Framework reload failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/admin/rag/rebuild", methods=["POST"])
@login_required
@admin_required
def admin_rag_rebuild():
    try:
        info = rag_build_index(force=True)
        return jsonify({"success": True, "rag": info}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/admin/rag/status", methods=["GET"])
@login_required
@admin_required
def admin_rag_status():
    try:
        return jsonify({"success": True, "rag": rag_status()}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/admin/backfill-all", methods=["POST"])
@login_required
@admin_required
def backfill_all_songs():
    """Re-analyze all songs using the current framework in a background thread.

    Includes songs without lyrics; the analysis flow will attempt lyric fetching
    across available providers before proceeding. Forces re-analysis to apply
    the latest framework outputs.
    """
    try:
        # Prevent overlapping backfills via Redis lock
        tracker = get_progress_tracker()
        redis_client = getattr(tracker.persistence, "redis", None)
        # Allow override with ?force=1 to ignore resume mode, but still block if lock exists
        force_full = request.args.get("force", "0") in ("1", "true", "True")
        resume_mode = request.args.get("resume", "1") in ("1", "true", "True") and not force_full

        if redis_client:
            try:
                # NX lock with 24h expiry
                acquired = redis_client.set("progress:backfill_lock", "1", nx=True, ex=24 * 3600)
                if not acquired:
                    # Report the current job id if present
                    current_job = redis_client.get("progress:current_backfill_job")
                    return jsonify(
                        {
                            "success": False,
                            "error": "backfill_already_running",
                            "job_id": current_job,
                        }
                    ), 409
            except Exception:
                pass

        # Preflight LLM endpoint if analyzer will use it
        try:
            from ..services.analyzer_cache import initialize_analyzer

            analyzer = initialize_analyzer()
            preflight_ok = True
            preflight_msg = "ready"
            if hasattr(analyzer, "preflight"):
                preflight_ok, preflight_msg = analyzer.preflight()
            if not preflight_ok:
                return jsonify(
                    {"success": False, "error": "llm_unavailable", "message": preflight_msg}
                ), 503
        except Exception as _e:
            current_app.logger.warning(f"[Backfill] Preflight skipped/failed: {_e}")
        app_obj = current_app._get_current_object()

        # Detect framework hash to decide resume vs full
        rules = get_rules()
        framework_hash = rules.get("version_hash", "unknown")
        if redis_client and resume_mode:
            try:
                last_hash = redis_client.get("progress:last_framework_hash")
                if last_hash and last_hash != framework_hash:
                    current_app.logger.info(
                        "[Backfill] Framework changed since last run; disabling resume mode (full reanalysis)"
                    )
                    resume_mode = False
            except Exception:
                pass

        def _runner():
            with app_obj.app_context():
                svc = UnifiedAnalysisService()
                # Pull eligible songs; split by lyrics presence for optimal processing
                completed_subq = (
                    db.session.query(AnalysisResult.song_id)
                    # No status filter needed - only completed analyses exist
                    .distinct()
                )
                base_with_lyrics = db.session.query(Song.id).filter(
                    Song.lyrics.isnot(None),
                    db.func.length(db.func.trim(Song.lyrics)) > 0,
                    Song.lyrics != "Lyrics not available",
                )
                base_missing_lyrics = db.session.query(Song.id).filter(
                    (Song.lyrics.is_(None))
                    | (db.func.length(db.func.trim(Song.lyrics)) == 0)
                    | (Song.lyrics == "Lyrics not available")
                )
                if resume_mode:
                    base_with_lyrics = base_with_lyrics.filter(~Song.id.in_(completed_subq))
                    base_missing_lyrics = base_missing_lyrics.filter(~Song.id.in_(completed_subq))

                ids_with_lyrics = [sid for (sid,) in base_with_lyrics.all()]
                ids_missing_lyrics = [sid for (sid,) in base_missing_lyrics.all()]

                total = len(ids_with_lyrics) + len(ids_missing_lyrics)
                start_ts = time.time()
                app_obj.config["BACKFILL_STATE"] = {
                    "status": "running",
                    "total": total,
                    "with_lyrics": len(ids_with_lyrics),
                    "missing_lyrics": len(ids_missing_lyrics),
                    "analyzed": 0,
                    "failed": 0,
                    "started_at": start_ts,
                    "updated_at": start_ts,
                }
                app_obj.logger.info(
                    f"[Backfill] Starting framework backfill. with_lyrics={len(ids_with_lyrics)}, missing_lyrics={len(ids_missing_lyrics)}, total={total}"
                )

                workers = int(os.getenv("BACKFILL_WORKERS") or os.getenv("ANALYSIS_WORKERS") or "3")
                batch_size = int(os.getenv("BACKFILL_BATCH_SIZE") or "25")

                analyzed = 0
                failed = 0

                # Initialize Redis-backed progress tracker
                job_id = f"backfill:{uuid.uuid4()}"
                # Seed estimate: 8s/song default; tracker will adapt as we complete
                progress = tracker.start_job_tracking(
                    job_id,
                    JobType.SONG_ANALYSIS,
                    total_items=total,
                    estimated_duration_per_item=8.0,
                )
                app_obj.config["BACKFILL_CURRENT_JOB"] = job_id
                # Persist current backfill job id for discovery from any worker
                try:
                    if tracker.persistence.redis:
                        tracker.persistence.redis.set(
                            "progress:current_backfill_job", job_id, ex=24 * 3600
                        )
                        # Record framework hash used for this run
                        tracker.persistence.redis.set(
                            "progress:last_framework_hash", framework_hash, ex=7 * 24 * 3600
                        )
                except Exception:
                    pass

                def _log_progress(prefix: str = "[Backfill]"):
                    now = time.time()
                    processed = analyzed + failed
                    elapsed = max(1.0, now - start_ts)
                    rate = processed / elapsed  # songs/sec
                    remaining = max(0, total - processed)
                    eta_seconds = int(remaining / rate) if rate > 0 else -1
                    eta_minutes = eta_seconds // 60 if eta_seconds >= 0 else -1
                    app_obj.config["BACKFILL_STATE"].update(
                        {
                            "analyzed": analyzed,
                            "failed": failed,
                            "updated_at": now,
                            "rate_s_per": round(rate, 2),
                            "eta_seconds": eta_seconds,
                        }
                    )
                    app_obj.logger.info(
                        f"{prefix} Progress: analyzed={analyzed}, failed={failed}, total={total}, rate={rate:.2f} s/s, eta≈{eta_minutes}m"
                    )
                    # Update Redis-backed progress
                    try:
                        tracker.update_job_progress(
                            job_id,
                            completed_items=analyzed + failed,
                            current_step="batch_processing",
                            message=f"Processed {analyzed+failed}/{total}",
                        )
                    except Exception:
                        pass

                def _process_batch(batch_ids):
                    # Each worker needs its own app context
                    with app_obj.app_context():
                        try:
                            # Ensure a clean session in case a prior error left it dirty
                            db.session.rollback()
                            app_obj.logger.info(f"[Backfill] batch start size={len(batch_ids)}")
                            result = svc.analyze_songs_batch(
                                batch_ids, user_id=None, batch_size=batch_size
                            )
                            app_obj.logger.info(
                                f"[Backfill] batch done size={len(batch_ids)} analyzed={result.get('total_analyzed', len(batch_ids))}"
                            )
                            return ("ok", result.get("total_analyzed", len(batch_ids)))
                        except Exception as e:
                            db.session.rollback()
                            msg = str(e)
                            app_obj.logger.error(
                                f"[Backfill] Batch failed ({len(batch_ids)} songs): {msg}"
                            )
                            if "timed out" in msg.lower() or "timeout" in msg.lower():
                                return ("timeout", len(batch_ids))
                            return ("err", len(batch_ids))
                        finally:
                            # Close out the session for this thread
                            db.session.remove()

                def _process_single(sid):
                    with app_obj.app_context():
                        try:
                            song_obj = db.session.get(Song, sid)
                            if not song_obj:
                                return ("err", sid)
                            analysis_data = svc.analyze_song_complete(
                                song_obj, force=True, user_id=None
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
                                score=analysis_data.get("score"),
                                concern_level=analysis_data.get("concern_level"),
                                themes=analysis_data.get("themes", []),
                                explanation=analysis_data.get("explanation"),
                                purity_flags_details=analysis_data.get("detailed_concerns", []),
                                positive_themes_identified=analysis_data.get("positive_themes", []),
                                biblical_themes=analysis_data.get("biblical_themes", []),
                                supporting_scripture=analysis_data.get("supporting_scripture", []),
                            )
                            db.session.commit()
                            return ("ok", sid)
                        except Exception as e:
                            db.session.rollback()
                            app_obj.logger.error(f"[Backfill] Failed song {sid}: {e}")
                            return ("err", sid)
                        finally:
                            db.session.remove()

                # 1) Process songs WITH lyrics using batched parallel workers (with adaptive backoff)
                if ids_with_lyrics:
                    batches = [
                        ids_with_lyrics[i : i + batch_size]
                        for i in range(0, len(ids_with_lyrics), batch_size)
                    ]
                    app_obj.logger.info(
                        f"[Backfill] Dispatching {len(batches)} batches with {workers} workers (batch_size={batch_size})"
                    )

                    # Adaptive backoff controls
                    enable_backoff = os.getenv("BACKFILL_AUTOBACKOFF", "1") in ("1", "true", "True")
                    min_workers = int(os.getenv("BACKFILL_MIN_WORKERS", "1"))
                    min_batch = int(os.getenv("BACKFILL_MIN_BATCH", "5"))
                    consec_timeouts = 0
                    current_workers = workers
                    current_batch_size = batch_size

                    # Submit in waves so we can adapt between batches
                    idx_next = 0
                    active = []
                    with ThreadPoolExecutor(max_workers=workers) as executor:
                        # Prime initial wave
                        while idx_next < len(batches) and len(active) < current_workers:
                            active.append(executor.submit(_process_batch, batches[idx_next]))
                            idx_next += 1
                        # Process results and refill waves
                        while active:
                            for fut in as_completed(active, timeout=None):
                                try:
                                    status, count = fut.result()
                                except Exception as e:
                                    status, count = ("err", 0)
                                    app_obj.logger.error(f"[Backfill] batch future error: {e}")
                                if status == "ok":
                                    analyzed += count if isinstance(count, int) else 0
                                    consec_timeouts = 0
                                elif status == "timeout":
                                    failed += count if isinstance(count, int) else 0
                                    consec_timeouts += 1
                                else:
                                    failed += count if isinstance(count, int) else 0
                                    consec_timeouts = 0
                                _log_progress()
                                active.remove(fut)

                                # Adapt on repeated timeouts
                                if enable_backoff and consec_timeouts >= 2:
                                    # Reduce pressure
                                    if current_workers > min_workers:
                                        current_workers -= 1
                                    if current_batch_size > min_batch:
                                        current_batch_size = max(min_batch, current_batch_size // 2)
                                    app_obj.logger.warning(
                                        f"[Backfill] Auto-backoff engaged → workers={current_workers}, batch_size={current_batch_size}"
                                    )
                                    # Re-slice remaining ids into new batch size
                                    remaining = []
                                    for j in range(idx_next, len(batches)):
                                        remaining.extend(batches[j])
                                    batches = batches[:idx_next] + [
                                        remaining[k : k + current_batch_size]
                                        for k in range(0, len(remaining), current_batch_size)
                                    ]
                                    consec_timeouts = 0

                                # Refill up to current_workers
                                while idx_next < len(batches) and len(active) < current_workers:
                                    active.append(
                                        executor.submit(_process_batch, batches[idx_next])
                                    )
                                    idx_next += 1
                            # Loop continues until active emptied

                # 2) Process songs MISSING lyrics with lighter parallelism (avoid provider rate limits)
                if ids_missing_lyrics:
                    lyric_workers = max(1, min(2, workers))
                    app_obj.logger.info(
                        f"[Backfill] Processing {len(ids_missing_lyrics)} songs missing lyrics with {lyric_workers} workers"
                    )
                    with ThreadPoolExecutor(max_workers=lyric_workers) as executor:
                        futures = [
                            executor.submit(_process_single, sid) for sid in ids_missing_lyrics
                        ]
                        for idx, fut in enumerate(as_completed(futures), 1):
                            status, _ = fut.result()
                            if status == "ok":
                                analyzed += 1
                            else:
                                failed += 1
                            # Log progress more frequently for singles (lyrics fetching)
                            if idx % 5 == 0:
                                _log_progress()

                app_obj.config["BACKFILL_STATE"].update(
                    {
                        "status": "finished",
                        "analyzed": analyzed,
                        "failed": failed,
                        "finished_at": time.time(),
                    }
                )
                app_obj.logger.info(
                    f"[Backfill] Finished: analyzed={analyzed}, failed={failed}, total={total}"
                )
                try:
                    tracker.complete_job_tracking(job_id, success=True)
                except Exception:
                    pass
                finally:
                    # Release lock
                    try:
                        if redis_client:
                            redis_client.delete("progress:backfill_lock")
                    except Exception:
                        pass

        threading.Thread(target=_runner, daemon=True).start()
        return jsonify(
            {
                "success": True,
                "message": "Backfill started in background",
                "job_id": app_obj.config.get("BACKFILL_CURRENT_JOB"),
            }
        ), 202
    except Exception as e:
        current_app.logger.error(f"Backfill start failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/admin/backfill-status", methods=["GET"])
@login_required
@admin_required
def backfill_status():
    """Return current backfill progress and ETA via Redis-backed tracker.

    Optional query param: job_id. If not provided, uses the latest recorded backfill job id.
    """
    tracker = get_progress_tracker()
    job_id = request.args.get("job_id")
    try:
        if not job_id and tracker.persistence.redis:
            job_id = tracker.persistence.redis.get("progress:current_backfill_job")
    except Exception:
        job_id = job_id or None

    if not job_id:
        # Fall back to in-memory snapshot
        state = current_app.config.get("BACKFILL_STATE") or {"status": "idle", "total": 0}
        total = int(state.get("total", 0)) or 0
        processed = int(state.get("analyzed", 0)) + int(state.get("failed", 0))
        pct = round((processed / total * 100.0), 2) if total else 0.0
        return jsonify(
            {
                "success": True,
                "status": state.get("status", "idle"),
                "total": total,
                "processed": processed,
                "progress_percent": pct,
                "job_id": None,
            }
        )

    progress = tracker.get_job_progress(job_id)
    if not progress:
        return jsonify(
            {
                "success": True,
                "status": "idle",
                "job_id": job_id,
                "message": "No active progress found",
            }
        ), 200

    p = progress.to_dict()
    # Include heartbeat for better UI confidence
    heartbeat = None
    try:
        if tracker.persistence.redis is not None:
            key = f"{tracker.persistence.key_prefix}{job_id}"
            hb = tracker.persistence.redis.hget(key, "heartbeat")
            heartbeat = int(hb) if hb else None
    except Exception:
        heartbeat = None

    return jsonify(
        {
            "success": True,
            "job_id": job_id,
            "status": "running" if not p["is_complete"] else "finished",
            "total": p["total_items"],
            "processed": p["completed_items"],
            "progress_percent": round(p["current_progress"] * 100.0, 2),
            "eta_seconds": int(p["eta_seconds"]),
            "eta_minutes": int(p["eta_seconds"] // 60) if p["eta_seconds"] is not None else None,
            "started_at": p["start_time"],
            "message": p.get("current_message"),
            "heartbeat": heartbeat,
        }
    )


@bp.route("/health/detailed")
def detailed_health_check():
    """Comprehensive health check with detailed system status"""
    try:
        # Force refresh for detailed checks
        system_health = health_monitor.get_system_health(force_refresh=True)

        # Convert to JSON-serializable format
        health_data = health_monitor.to_dict(system_health)

        # Set appropriate HTTP status based on health
        if system_health.status.value == "healthy":
            status_code = 200
        elif system_health.status.value == "warning":
            status_code = 200  # Still operational
        else:  # critical
            status_code = 503  # Service unavailable

        return jsonify(health_data), status_code

    except Exception as e:
        current_app.logger.error(f"Detailed health check failed: {e}")
        return jsonify(
            {
                "status": "critical",
                "timestamp": datetime.now().isoformat(),
                "error": f"Health monitoring system failed: {str(e)}",
                "checks": [],
            }
        ), 503


@bp.route("/health/ready")
def readiness_check():
    """Kubernetes-style readiness probe"""
    try:
        # Check critical dependencies only
        db.session.execute(text("SELECT 1")).scalar()

        # Redis preferred for progress; warn if unavailable
        try:
            import redis

            redis_client = redis.from_url(
                current_app.config.get("RQ_REDIS_URL", "redis://redis:6379/0")
            )
            redis_client.ping()
        except Exception as _redis_error:
            return jsonify({"status": "not ready", "error": "redis_unavailable"}), 503

        return jsonify({"status": "ready"}), 200

    except Exception as e:
        current_app.logger.error(f"Readiness check failed: {e}")
        return jsonify({"status": "not ready", "error": str(e)}), 503


@bp.route("/health/live")
def liveness_check():
    """Kubernetes-style liveness probe"""
    # Very basic check - just ensure the application is responding
    return jsonify({"status": "alive", "timestamp": datetime.now().isoformat()}), 200


@bp.route("/playlists")
@login_required
def get_playlists():
    """Get user's playlists as JSON"""
    playlists = Playlist.query.filter_by(owner_id=current_user.id).all()

    playlist_data = []
    unlocked_id = None
    if freemium_enabled() and not current_user.is_admin:
        unlocked_id = free_playlist_id_for_user(current_user.id)

    for playlist in playlists:
        song_count = PlaylistSong.query.filter_by(playlist_id=playlist.id).count()
        analyzed_count = (
            db.session.query(Song.id)
            .join(AnalysisResult, Song.id == AnalysisResult.song_id)
            .join(PlaylistSong)
            .filter(PlaylistSong.playlist_id == playlist.id)  # No status filter needed - only completed analyses exist
            .distinct()
            .count()
        )

        playlist_data.append(
            {
                "id": playlist.id,
                "name": playlist.name,
                "description": playlist.description,
                "song_count": song_count,
                "analyzed_count": analyzed_count,
                "analysis_progress": round(
                    (analyzed_count / song_count * 100) if song_count > 0 else 0, 1
                ),
                "image_url": playlist.image_url,
                "spotify_url": f"https://open.spotify.com/playlist/{playlist.spotify_id}"
                if playlist.spotify_id
                else None,
                "score": mask_playlist_score_for_user(playlist.id, playlist.score),
                "overall_alignment_score": mask_playlist_score_for_user(
                    playlist.id, playlist.overall_alignment_score
                ),
                "is_unlocked": (unlocked_id is None)
                or (playlist.id == unlocked_id)
                or current_user.is_admin
                or not freemium_enabled(),
                "last_analyzed": playlist.last_analyzed.isoformat()
                if playlist.last_analyzed
                else None,
            }
        )

    return jsonify({"playlists": playlist_data})


@bp.route("/playlist/<int:playlist_id>/songs")
@login_required
def get_playlist_songs(playlist_id):
    """Get songs in a playlist with analysis status"""
    playlist = Playlist.query.filter_by(id=playlist_id, owner_id=current_user.id).first_or_404()
    # Freemium: block song list details for locked playlists
    if freemium_enabled() and not current_user.is_admin and not is_playlist_unlocked(playlist_id):
        return jsonify(
            {
                "error": "upgrade_required",
                "message": "Playlist access is restricted on the free tier",
            }
        ), 402

    songs_query = (
        db.session.query(Song, AnalysisResult, PlaylistSong)
        .join(PlaylistSong, Song.id == PlaylistSong.song_id)
        .outerjoin(AnalysisResult, Song.id == AnalysisResult.song_id)
        .filter(PlaylistSong.playlist_id == playlist_id)
        .order_by(PlaylistSong.track_position)
    )

    songs_data = []
    for song, analysis, playlist_song in songs_query:
        song_data = {
            "id": song.id,
            "name": song.title,
            "artist": song.artist,
            "album": song.album,
            "duration_ms": song.duration_ms,
            "position": playlist_song.track_position,
            "spotify_url": f"https://open.spotify.com/track/{song.spotify_id}"
            if song.spotify_id
            else None,
            "analysis_status": "completed" if analysis else "pending",
            "analysis_score": analysis.score if analysis else None,
            "concern_level": analysis.concern_level if analysis else None,
            "detected_themes": analysis.themes if analysis else [],
            "analysis_date": analysis.created_at.isoformat() if analysis else None,
        }
        songs_data.append(song_data)

    return jsonify(
        {
            "playlist": {
                "id": playlist.id,
                "name": playlist.name,
                "description": playlist.description,
            },
            "songs": songs_data,
        }
    )


@bp.route("/song/<int:song_id>/analysis")
@login_required
def get_song_analysis(song_id):
    """Get detailed analysis for a song"""
    # Verify user has access to this song
    song = (
        db.session.query(Song)
        .join(PlaylistSong)
        .join(Playlist)
        .filter(Song.id == song_id, Playlist.owner_id == current_user.id)
        .first_or_404()
    )

    # Freemium: ensure song is in unlocked playlist
    if freemium_enabled() and not current_user.is_admin:
        ok, allowed_pid = song_belongs_to_unlocked_playlist(song_id)
        if not ok:
            return jsonify(
                {
                    "error": "upgrade_required",
                    "message": "Song analysis is restricted on the free tier",
                }
            ), 402

    analysis = (
        AnalysisResult.query.filter_by(song_id=song_id)
        .order_by(AnalysisResult.analyzed_at.desc())
        .first()
    )

    song_data = {
        "id": song.id,
        "name": song.title,
        "artist": song.artist,
        "album": song.album,
        "lyrics": song.lyrics,
        "spotify_url": f"https://open.spotify.com/track/{song.spotify_id}"
        if song.spotify_id
        else None,
    }

    analysis_data = None
    if analysis:
        analysis_data = {
                            "status": "completed",  # All analyses are completed now
            "score": analysis.score,
            "purity_score": analysis.purity_score or analysis.score,
            "formation_risk": analysis.formation_risk,
            "doctrinal_clarity": analysis.doctrinal_clarity,
            "confidence": analysis.confidence,
            "needs_review": analysis.needs_review,
            "verdict": analysis.verdict,
            "concern_level": analysis.concern_level,
            "themes": analysis.themes or [],
            "analysis_details": analysis.problematic_content or {},
            "supporting_scripture": getattr(analysis, "supporting_scripture", None) or [],
            "biblical_themes": getattr(analysis, "biblical_themes", None) or [],
            "concerns": getattr(analysis, "concerns", None) or [],
            "created_at": analysis.created_at.isoformat(),
        }

    return jsonify({"song": song_data, "analysis": analysis_data})


@bp.route("/search_songs")
@login_required
def search_songs():
    """Search user's songs"""
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"songs": []})

    # Search in user's songs
    songs = (
        db.session.query(Song, AnalysisResult)
        .join(PlaylistSong)
        .join(Playlist)
        .outerjoin(AnalysisResult, Song.id == AnalysisResult.song_id)
        .filter(
            Playlist.owner_id == current_user.id,
            db.or_(
                Song.title.ilike(f"%{query}%"),
                Song.artist.ilike(f"%{query}%"),
                Song.album.ilike(f"%{query}%"),
            ),
        )
        .limit(20)
        .all()
    )

    songs_data = []
    for song, analysis in songs:
        songs_data.append(
            {
                "id": song.id,
                "name": song.title,
                "artist": song.artist,
                "album": song.album,
                "analysis_status": "completed" if analysis else "pending",
                "concern_level": analysis.concern_level if analysis else None,
                "spotify_url": f"https://open.spotify.com/track/{song.spotify_id}"
                if song.spotify_id
                else None,
            }
        )

    return jsonify({"songs": songs_data})


@bp.route("/sync-status")
@login_required
def sync_status():
    """Get sync status for user's playlists"""
    try:
        # Count playlists by sync status
        total_playlists = Playlist.query.filter_by(owner_id=current_user.id).count()

        return jsonify(
            {
                "status": "success",
                "total_playlists": total_playlists,
                "sync_active": False,  # Would check for active sync jobs
                "last_sync": None,  # Would get from database
                "timestamp": datetime.now().isoformat(),
            }
        )
    except Exception as e:
        current_app.logger.error(f"Sync status check failed: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500


@bp.route("/stats")
@login_required
def get_user_stats():
    """Get comprehensive user statistics"""
    total_playlists = Playlist.query.filter_by(owner_id=current_user.id).count()

    total_songs = (
        db.session.query(Song)
        .join(PlaylistSong)
        .join(Playlist)
        .filter(Playlist.owner_id == current_user.id)
        .count()
    )

    # Fix: Count unique songs with completed analysis (not total completed analysis records)
    analyzed_songs = (
        db.session.query(Song.id)
        .join(AnalysisResult, Song.id == AnalysisResult.song_id)
        .join(PlaylistSong)
        .join(Playlist)
        .filter(Playlist.owner_id == current_user.id)  # No status filter needed - only completed analyses exist
        .distinct()
        .count()
    )

    # Count by concern level (using distinct song IDs to avoid duplicates)
    concern_counts = (
        db.session.query(
            AnalysisResult.concern_level, db.func.count(db.func.distinct(AnalysisResult.song_id))
        )
        .join(Song, AnalysisResult.song_id == Song.id)
        .join(PlaylistSong)
        .join(Playlist)
        .filter(Playlist.owner_id == current_user.id)  # No status filter needed - only completed analyses exist
        .group_by(AnalysisResult.concern_level)
        .all()
    )

    concern_dict = dict(concern_counts)

    return jsonify(
        {
            "total_playlists": total_playlists,
            "total_songs": total_songs,
            "analyzed_songs": analyzed_songs,
            "analysis_progress": round(
                (analyzed_songs / total_songs * 100) if total_songs > 0 else 0, 1
            ),
            "concern_levels": {
                "low": concern_dict.get("low", 0),
                "medium": concern_dict.get("medium", 0),
                "high": concern_dict.get("high", 0),
            },
            "flagged_songs": concern_dict.get("medium", 0) + concern_dict.get("high", 0),
        }
    )


@bp.route("/metrics")
def metrics():
    """Prometheus metrics endpoint"""
    try:
        metrics_data = get_metrics()
        return Response(metrics_data, mimetype="text/plain")
    except Exception as e:
        current_app.logger.error(f"Error generating metrics: {e}")
        metrics_collector.record_error("metrics_generation_error", "api")
        return jsonify({"error": "Metrics unavailable"}), 500


@bp.route("/playlists/<int:playlist_id>/analysis-status")
@login_required
def get_playlist_analysis_status(playlist_id):
    """Get playlist analysis status (consolidates functionality from analysis_progress)"""
    playlist = Playlist.query.filter_by(id=playlist_id, owner_id=current_user.id).first_or_404()

    total_songs = PlaylistSong.query.filter_by(playlist_id=playlist_id).count()
    # Optional client-provided start time (epoch seconds) for fresh-progress calc
    since_ts = request.args.get("since", type=float)

    # If a re-analysis batch is active, compute progress using updated_at since the batch start
    # Discover active batch from Redis first, then in-memory fallback
    active = None
    try:
        import os
        try:
            import redis  # type: ignore
        except Exception:
            redis = None
        if redis is not None:
            try:
                url = current_app.config.get("RQ_REDIS_URL") or os.environ.get("REDIS_URL")
                if url:
                    rc = redis.from_url(url)  # type: ignore
                    raw = rc.get(f"progress:playlist:{playlist_id}")
                    if raw:
                        import json
                        active = json.loads(raw)
            except Exception:
                active = None
    except Exception:
        active = None
    if active is None:
        active = current_app.config.get("ACTIVE_PLAYLIST_BATCH", {}).get(playlist_id)
    completed_count = 0
    if since_ts:
        try:
            from datetime import datetime, timezone

            start_dt = datetime.fromtimestamp(float(since_ts), tz=timezone.utc)
            completed_count = (
                db.session.query(db.func.count(AnalysisResult.song_id))
                .join(Song, Song.id == AnalysisResult.song_id)
                .join(PlaylistSong, PlaylistSong.song_id == Song.id)
                .filter(PlaylistSong.playlist_id == playlist_id)
                .filter(AnalysisResult.updated_at >= start_dt)
                .scalar()
                or 0
            )
        except Exception:
            completed_count = 0
    elif active and active.get("start_ts"):
        try:
            from datetime import datetime, timezone

            start_dt = datetime.fromtimestamp(float(active["start_ts"]), tz=timezone.utc)
            completed_count = (
                db.session.query(db.func.count(AnalysisResult.song_id))
                .join(Song, Song.id == AnalysisResult.song_id)
                .join(PlaylistSong, PlaylistSong.song_id == Song.id)
                .filter(PlaylistSong.playlist_id == playlist_id)
                .filter(AnalysisResult.updated_at >= start_dt)
                .scalar()
                or 0
            )
        except Exception:
            completed_count = 0
    else:
        # Accurate progress (no active batch): count ONLY the latest AnalysisResult per song
        sub_latest = (
            db.session.query(
                AnalysisResult.song_id, db.func.max(AnalysisResult.created_at).label("max_created")
            )
            .join(Song, Song.id == AnalysisResult.song_id)
            .join(PlaylistSong, PlaylistSong.song_id == Song.id)
        )
        sub_latest = (
            sub_latest.filter(PlaylistSong.playlist_id == playlist_id)
            .group_by(AnalysisResult.song_id)
            .subquery()
        )

        completed_count = (
            db.session.query(db.func.count(AnalysisResult.song_id))
            .join(
                sub_latest,
                (sub_latest.c.song_id == AnalysisResult.song_id)
                & (sub_latest.c.max_created == AnalysisResult.created_at),
            )
            .scalar()
            or 0
        )

    # Simplified status tracking - only completed and pending
    failed_count = 0  # No failed analyses stored
    in_progress_count = 0  # No in-progress analyses stored
    
    # Pending are songs without any analysis row
    counted = completed_count
    # Consider only eligible songs (with lyrics) as part of total for progress, to avoid stalls at ~95%
    eligible_total = (
        db.session.query(db.func.count(Song.id))
        .join(PlaylistSong)
        .filter(
            PlaylistSong.playlist_id == playlist_id,
            Song.lyrics.isnot(None),
            db.func.length(db.func.trim(Song.lyrics)) > 0,
            Song.lyrics != "Lyrics not available",
        )
        .scalar()
        or 0
    )
    # Use eligible_total if it is > 0 and <= total_songs; otherwise fall back to total_songs.
    # If an active batch exists and recorded an eligible count, use that for the denominator.
    if active and isinstance(active.get("eligible"), int) and active.get("eligible") > 0:
        denom = int(active.get("eligible"))
    else:
        denom = eligible_total if 0 < eligible_total <= total_songs else total_songs
    pending_count = max(0, denom - (completed_count + failed_count + in_progress_count))

    progress_percentage = round((completed_count / denom * 100) if denom > 0 else 0, 1)

    # Include active batch diagnostics for admin UI if available
    diag = {}
    if active:
        try:
            import time
            diag = {
                "active_batch": True,
                "eligible": active.get("eligible"),
                "seconds_since_start": int(time.time() - active.get("start_ts", time.time())),
                "started_by": active.get("user"),
            }
        except Exception:
            diag = {"active_batch": True}

    return jsonify(
        {
            # Frontend-expected format
            "success": True,
            "completed": progress_percentage == 100.0,
            "progress": progress_percentage,
            "analyzed_count": completed_count,
            "total_count": denom,
            "message": f"Analysis {progress_percentage}% complete ({completed_count}/{total_songs} songs)",
            # Detailed status breakdown (replaces analysis_progress endpoint)
            "playlist_id": playlist_id,
            "detailed_status": {
                "completed": completed_count,
                "failed": failed_count,
                "pending": pending_count,
                "in_progress": in_progress_count,
            },
            **({"diag": diag} if diag else {}),
        }
    )


@bp.route("/analysis/progress")
@login_required
def analysis_progress_alias():
    """Back-compat alias for progress endpoint (now consolidated in status)."""
    return get_analysis_status()


@bp.route("/songs/<int:song_id>/analysis-status")
@login_required
def get_song_analysis_status(song_id):
    """Get song analysis status with progress tracking for queue system"""
    # Verify user has access to this song
    song = (
        db.session.query(Song)
        .join(PlaylistSong)
        .join(Playlist)
        .filter(Song.id == song_id, Playlist.owner_id == current_user.id)
        .first_or_404()
    )

    analysis = (
        AnalysisResult.query.filter_by(song_id=song_id)
        .order_by(AnalysisResult.analyzed_at.desc())
        .first()
    )

    if analysis:  # All analyses are completed now
        return jsonify(
            {
                "success": True,
                "completed": True,
                "has_analysis": True,
                "status": "completed",
                "progress": 100,
                "stage": "Analysis complete",
                "score": analysis.score,
                "concern_level": analysis.concern_level,
                "message": "Analysis completed using cached models",
                "result": {
                    "id": analysis.id,
                    "score": analysis.score,
                    "concern_level": analysis.concern_level,
                    "status": "completed",
                    "themes": analysis.themes or [],
                    "explanation": analysis.explanation,
                    "supporting_scripture": getattr(analysis, "supporting_scripture", None) or [],
                    "biblical_themes": getattr(analysis, "biblical_themes", None) or [],
                    "concerns": getattr(analysis, "concerns", None) or [],
                    "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
                },
                "analysis": {
                    "id": analysis.id,
                    "score": analysis.score,
                    "concern_level": analysis.concern_level,
                    "status": "completed",
                    "themes": analysis.themes or [],
                    "explanation": analysis.explanation,
                    "supporting_scripture": getattr(analysis, "supporting_scripture", None) or [],
                    "biblical_themes": getattr(analysis, "biblical_themes", None) or [],
                    "concerns": getattr(analysis, "concerns", None) or [],
                    "created_at": analysis.created_at.isoformat() if analysis.created_at else None,
                },
            }
        )
    elif False:  # No pending status anymore - all stored analyses are completed
        # Calculate estimated progress based on time elapsed
        created_at = analysis.created_at
        if created_at:
            elapsed_seconds = (datetime.now() - created_at).total_seconds()
            # With cached models, analysis should be much faster
            if elapsed_seconds < 2:
                progress = 20
                stage = "Using cached AI models..."
            elif elapsed_seconds < 5:
                progress = 60
                stage = "Analyzing content..."
            elif elapsed_seconds < 10:
                progress = 90
                stage = "Finalizing results..."
            else:
                progress = 95
                stage = "Almost complete..."
        else:
            progress = 10
            stage = "Starting analysis..."

        return jsonify(
            {
                "success": True,
                "completed": False,
                "has_analysis": False,
                "status": "pending",
                "progress": progress,
                "stage": stage,
                "message": "Analysis in progress with cached models",
            }
        )
    elif False:  # No failed status anymore - all stored analyses are completed
        return jsonify(
            {
                "success": False,
                "completed": True,
                "failed": True,
                "has_analysis": False,
                "status": "failed",
                "progress": 0,
                "stage": "Analysis failed",
                "error": "Analysis failed",
                "message": "Analysis failed",
            }
        )
    else:
        # No analysis found - ready to start
        return jsonify(
            {
                "success": True,
                "completed": False,
                "has_analysis": False,
                "status": "not_started",
                "progress": 0,
                "stage": "Ready to analyze",
                "message": "Click Analyze to start analysis with cached models",
            }
        )


@bp.route("/songs/<int:song_id>/analyze", methods=["POST"])
@login_required
def analyze_single_song(song_id):
    """Analyze a single song directly using the simplified local analyzer (no queue)."""
    try:
        # Verify user has access to this song
        song = (
            db.session.query(Song)
            .join(PlaylistSong)
            .join(Playlist)
            .filter(Song.id == song_id, Playlist.owner_id == current_user.id)
            .first()
        )

        if not song:
            return jsonify(
                {"status": "error", "message": f"Song with ID {song_id} not found or access denied"}
            ), 404

        # Perform synchronous analysis now (MVP: no background queue)
        analysis_service = UnifiedAnalysisService()
        analysis = analysis_service.analyze_song(song_id, user_id=current_user.id)

        current_app.logger.info(f"✅ Analysis completed for song {song_id} ({song.title})")

        return jsonify(
            {
                "success": True,
                "status": "success",
                "message": "Analysis completed using local models",
                "song_id": song_id,
                "analysis_id": analysis.id if hasattr(analysis, "id") else None,
            }
        )

    except ValueError as e:
        current_app.logger.error(f"Song not found: {e}")
        return jsonify({"status": "error", "message": str(e)}), 404
    except Exception as e:
        current_app.logger.error(f"Song analysis queueing error: {e}")
        return jsonify(
            {"status": "error", "error": str(e), "message": "Analysis service error occurred"}
        ), 500


@bp.route("/playlists/<int:playlist_id>/analyze-unanalyzed", methods=["POST"])
@login_required
def start_playlist_analysis_unanalyzed(playlist_id):
    """Analyze only unanalyzed songs in a playlist directly (no queue)."""
    try:
        playlist = Playlist.query.filter_by(id=playlist_id, owner_id=current_user.id).first_or_404()

        # Find songs in this playlist that don't have a completed analysis
        song_ids = [
            sid
            for (sid,) in db.session.query(Song.id)
            .join(PlaylistSong)
            .filter(PlaylistSong.playlist_id == playlist_id)
            .distinct()
            .all()
        ]

        if not song_ids:
            return jsonify(
                {"success": True, "message": "No songs found in playlist", "analyzed_count": 0}
            )

        analyzed_count = 0
        errors = []
        service = UnifiedAnalysisService()

        for sid in song_ids:
            exists = AnalysisResult.query.filter_by(song_id=sid, status="completed").first()
            if exists:
                continue
            try:
                service.analyze_song(sid, user_id=current_user.id)
                analyzed_count += 1
            except Exception as song_error:
                errors.append(f"Failed to analyze song {sid}: {song_error}")

        return jsonify(
            {
                "success": True,
                "message": f"Analyzed {analyzed_count} songs directly",
                "analyzed_count": analyzed_count,
                "total_songs": len(song_ids),
                "errors": errors,
            }
        )

    except Exception as e:
        current_app.logger.error(f"Playlist analysis error: {e}")
        return jsonify(
            {"success": False, "error": str(e), "message": "Failed to analyze playlist"}
        ), 500


@bp.route("/playlists/<int:playlist_id>/reanalyze-all", methods=["POST"])
@login_required
def reanalyze_all_playlist_songs(playlist_id):
    """DEPRECATED: Queue system removed - use /analyze_playlist/<id> for direct batch analysis"""
    current_app.logger.warning(
        f"Deprecated endpoint /playlists/{playlist_id}/reanalyze-all called - redirecting to direct analysis"
    )

    # Check admin access (analysis is admin-only now)
    if not current_user.is_admin:
        return jsonify(
            {
                "success": False,
                "message": "Access denied. Analysis is restricted to administrators.",
                "deprecated": True,
                "new_endpoint": f"/analyze_playlist/{playlist_id}",
            }
        ), 403

    return jsonify(
        {
            "success": False,
            "message": "This endpoint is deprecated. Queue system removed. Use direct batch analysis instead.",
            "deprecated": True,
            "new_endpoint": f"/analyze_playlist/{playlist_id}",
            "instructions": "Use POST /analyze_playlist/<id> for direct ML batch analysis",
        }
    ), 410  # 410 Gone - endpoint permanently removed


@bp.route("/analysis/status")
@login_required
def get_analysis_status():
    """Get overall analysis status for the current user (queue system removed)"""
    try:
        # Get all user's playlists
        user_playlists = Playlist.query.filter_by(owner_id=current_user.id).all()

        total_songs = 0
        analyzed_songs = 0

        for playlist in user_playlists:
            playlist_total = PlaylistSong.query.filter_by(playlist_id=playlist.id).count()
            playlist_analyzed = (
                db.session.query(Song.id)
                .join(AnalysisResult, Song.id == AnalysisResult.song_id)
                .join(PlaylistSong)
                .filter(
                    PlaylistSong.playlist_id == playlist.id, # No status filter needed - only completed analyses exist
                )
                .distinct()
                .count()
            )

            total_songs += playlist_total
            analyzed_songs += playlist_analyzed

        progress_percentage = round(
            (analyzed_songs / total_songs * 100) if total_songs > 0 else 0, 1
        )

        return jsonify(
            {
                "status": "success",
                "success": True,
                "active": progress_percentage < 100.0,
                "completed": progress_percentage == 100.0,
                "progress": progress_percentage,
                "analyzed_count": analyzed_songs,
                "total_count": total_songs,
                "queue_length": 0,  # Queue system removed
                "pending_jobs": 0,  # Queue system removed
                "in_progress_jobs": 0,  # Queue system removed
                "estimated_completion_minutes": 0,  # Queue system removed
                "message": f"Analysis {progress_percentage}% complete ({analyzed_songs}/{total_songs} songs)",
            }
        )

    except Exception as e:
        current_app.logger.error(f"Analysis status error: {e}")
        return jsonify(
            {
                "status": "error",
                "success": False,
                "error": str(e),
                "message": "Failed to get analysis status",
            }
        ), 500


@bp.route("/admin/reanalysis-status")
@login_required
@admin_required
def get_admin_reanalysis_status():
    """Get admin reanalysis status (placeholder for now)"""
    # For now, return no active reanalysis since this is admin-only functionality
    return jsonify(
        {"active": False, "completed": False, "progress": 0, "message": "No active reanalysis"}
    )


@bp.route("/analyze-all", methods=["POST"])
@login_required
def analyze_all_user_songs():
    """User endpoint to trigger background analysis for all unanalyzed songs (non-blocking)."""
    try:
        user_id = current_user.id

        # Collect user's unique songs
        songs = (
            db.session.query(Song)
            .join(PlaylistSong)
            .join(Playlist)
            .filter(Playlist.owner_id == user_id)
            .distinct()
            .all()
        )

        if not songs:
            return jsonify(
                {
                    "success": True,
                    "message": "No songs found in your playlists",
                    "queued_count": 0,
                    "user_id": user_id,
                    "already_complete": True,
                }
            )

        # Filter eligible (with lyrics) and not already completed
        eligible_ids = []
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

        if not eligible_ids:
            return jsonify(
                {
                    "success": True,
                    "message": "All eligible songs already analyzed",
                    "queued_count": 0,
                    "user_id": user_id,
                    "already_complete": True,
                }
            )

        # Initialize simple in-memory progress (per user)
        state = current_app.config.setdefault("USER_ANALYSIS_PROGRESS", {})
        job_id = f"user-analysis:{uuid.uuid4()}"
        state[user_id] = {
            "active": True,
            "total_songs": len(eligible_ids),
            "completed": 0,
            "failed": 0,
            "started_at": time.time(),
            "job_id": job_id,
        }

        app_obj = current_app._get_current_object()

        def _run_user_analysis(app_inst, uid, ids):
            from app.services.analyzer_cache import get_shared_analyzer, is_analyzer_ready

            with app_inst.app_context():
                try:
                    if not is_analyzer_ready():
                        _ = get_shared_analyzer()
                except Exception:
                    pass
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
                    except Exception as _e:
                        db.session.rollback()
                        failed += 1
                    finally:
                        prog = app_inst.config.get("USER_ANALYSIS_PROGRESS", {})
                        if uid in prog:
                            prog[uid]["completed"] = completed
                            prog[uid]["failed"] = failed
                # Mark finished
                prog = app_inst.config.get("USER_ANALYSIS_PROGRESS", {})
                if uid in prog:
                    prog[uid]["active"] = False

        threading.Thread(
            target=_run_user_analysis, args=(app_obj, user_id, eligible_ids), daemon=True
        ).start()

        return jsonify(
            {
                "success": True,
                "message": f"Started background analysis for {len(eligible_ids)} eligible songs",
                "queued_count": len(eligible_ids),
                "user_id": user_id,
                "already_complete": False,
                "job_id": job_id,
            }
        )

    except Exception as e:
        current_app.logger.error(f"User analysis error: {e}")
        return jsonify(
            {
                "success": False,
                "error": str(e),
                "message": "Failed to start analysis for your songs",
            }
        ), 500


@bp.route("/admin/reanalyze-user/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def admin_reanalyze_user(user_id):
    """Admin-only endpoint to trigger reanalysis for a specific user"""
    try:
        # Validate target user exists
        target_user = db.session.get(User, user_id)
        if not target_user:
            return jsonify({"success": False, "error": f"User with ID {user_id} not found"}), 404

        # Check how many songs actually need analysis
        total_unique_songs = (
            db.session.query(Song.id)
            .join(PlaylistSong)
            .join(Playlist)
            .filter(Playlist.owner_id == user_id)
            .distinct()
            .count()
        )

        if total_unique_songs == 0:
            return jsonify(
                {
                    "success": True,
                    "message": f"No songs found for user {target_user.display_name or target_user.email}",
                    "queued_count": 0,
                    "user_id": user_id,
                    "already_complete": True,
                }
            )

        # Count songs with completed analysis
        completed_songs = (
            db.session.query(Song.id)
            .join(PlaylistSong)
            .join(Playlist)
            .join(AnalysisResult, Song.id == AnalysisResult.song_id)
            .filter(Playlist.owner_id == user_id)  # No status filter needed - only completed analyses exist
            .distinct()
            .count()
        )

        unanalyzed_count = total_unique_songs - completed_songs

        # MVP: Perform direct analysis sequentially (no queue) for ALL songs (re-analysis allowed)
        analysis_service = UnifiedAnalysisService()
        analyzed = 0
        # Fetch IDs of all songs for this user (including those already analyzed)
        song_ids = [
            sid
            for (sid,) in db.session.query(Song.id)
            .join(PlaylistSong)
            .join(Playlist)
            .filter(Playlist.owner_id == user_id)
            .distinct()
            .all()
        ]
        for sid in song_ids:
            try:
                analysis_service.analyze_song(sid, user_id=user_id)
                analyzed += 1
            except Exception as _e:
                current_app.logger.error(f"Failed to analyze song {sid} (admin): {_e}")
                continue

        # For backward-compat tests that expect a 'queued_count', report attempted items
        return jsonify(
            {
                "success": True,
                "message": f"Analyzed {analyzed:,} songs directly for user {target_user.display_name or target_user.email}",
                "queued_count": len(song_ids),
                "total_songs": total_unique_songs,
                "completed_songs": completed_songs + analyzed,
                "user_id": user_id,
                "already_complete": analyzed == 0,
            }
        )

    except ValueError as e:
        if "No unanalyzed songs found" in str(e):
            # This should be caught by our check above, but just in case
            return jsonify(
                {
                    "success": True,
                    "message": f"All songs are already analyzed for user {target_user.display_name or target_user.email}",
                    "queued_count": 0,
                    "user_id": user_id,
                    "already_complete": True,
                }
            )
        else:
            current_app.logger.error(f"Admin reanalysis error: {e}")
            return jsonify(
                {
                    "success": False,
                    "error": str(e),
                    "message": f"Failed to start background analysis for user {user_id}",
                }
            ), 500
    except Exception as e:
        current_app.logger.error(f"Admin reanalysis error: {e}")
        return jsonify(
            {
                "success": False,
                "error": str(e),
                "message": f"Failed to start background analysis for user {user_id}",
            }
        ), 500


# Whitelist Management API
@bp.route("/whitelist", methods=["POST"])
@login_required
@validate_json(WhitelistAddSchema)
def add_whitelist_item():
    """
    Add an item to the user's whitelist.

    If the item exists on the blacklist, it will be moved to the whitelist.
    If the item already exists on the whitelist, the reason will be updated.
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({"success": False, "error": "No JSON data provided"}), 400

        # Validate required fields
        spotify_id = data.get("spotify_id")
        item_type = data.get("item_type")

        if not spotify_id:
            return jsonify({"success": False, "error": "spotify_id is required"}), 400

        if not item_type:
            return jsonify({"success": False, "error": "item_type is required"}), 400

        # Validate item_type
        valid_types = ["song", "artist", "playlist"]
        if item_type not in valid_types:
            return jsonify(
                {"success": False, "error": f'item_type must be one of: {", ".join(valid_types)}'}
            ), 400

        name = data.get("name", "")
        reason = data.get("reason", "")

        # Check if item already exists in whitelist
        existing_entry = Whitelist.query.filter_by(
            user_id=current_user.id, spotify_id=spotify_id, item_type=item_type
        ).first()

        if existing_entry:
            # Update existing entry's reason
            existing_entry.reason = reason
            if name:
                existing_entry.name = name
            db.session.commit()

            return jsonify(
                {
                    "success": True,
                    "message": "Whitelist item reason updated",
                    "item": existing_entry.to_dict(),
                }
            ), 200

        # Create new whitelist entry
        whitelist_entry = Whitelist(
            user_id=current_user.id,
            spotify_id=spotify_id,
            item_type=item_type,
            name=name,
            reason=reason,
        )

        db.session.add(whitelist_entry)
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": "Item added to whitelist",
                "item": whitelist_entry.to_dict(),
                "request_id": get_request_id(),
            }
        ), 201

    except Exception as e:
        current_app.logger.error(f"Error adding whitelist item: {e}")
        db.session.rollback()
        return jsonify(
            {
                "success": False,
                "error": "Failed to add item to whitelist",
                "request_id": get_request_id(),
            }
        ), 500


@bp.route("/whitelist", methods=["GET"])
@login_required
@validate_query(WhitelistQuerySchema)
def get_whitelist_items():
    """
    Get all items in the user's whitelist.

    Optional query parameter:
    - item_type: Filter by specific item type (song, artist, playlist)
    """
    try:
        item_type_filter = request.args.get("item_type")

        query = Whitelist.query.filter_by(user_id=current_user.id)

        if item_type_filter:
            valid_types = ["song", "artist", "playlist"]
            if item_type_filter not in valid_types:
                return jsonify(
                    {
                        "success": False,
                        "error": f'Invalid item_type. Must be one of: {", ".join(valid_types)}',
                    }
                ), 400
            query = query.filter_by(item_type=item_type_filter)

        whitelist_items = query.order_by(Whitelist.added_date.desc()).all()

        return jsonify(
            {
                "success": True,
                "items": [item.to_dict() for item in whitelist_items],
                "total_count": len(whitelist_items),
                "request_id": get_request_id(),
            }
        ), 200

    except Exception as e:
        current_app.logger.error(f"Error retrieving whitelist items: {e}")
        return jsonify(
            {
                "success": False,
                "error": "Failed to retrieve whitelist items",
                "request_id": get_request_id(),
            }
        ), 500


@bp.route("/whitelist/<int:entry_id>", methods=["DELETE"])
@login_required
def remove_whitelist_item(entry_id):
    """
    Remove a specific item from the user's whitelist.
    """
    try:
        whitelist_entry = Whitelist.query.filter_by(id=entry_id, user_id=current_user.id).first()

        if not whitelist_entry:
            return jsonify({"success": False, "error": "Whitelist entry not found"}), 404

        item_name = (
            whitelist_entry.name or f"{whitelist_entry.item_type} {whitelist_entry.spotify_id}"
        )

        db.session.delete(whitelist_entry)
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": "Item removed from whitelist",
                "request_id": get_request_id(),
            }
        ), 200

    except Exception as e:
        current_app.logger.error(f"Error removing whitelist item {entry_id}: {e}")
        db.session.rollback()
        return jsonify(
            {
                "success": False,
                "error": "Failed to remove item from whitelist",
                "request_id": get_request_id(),
            }
        ), 500


@bp.route("/whitelist/clear", methods=["POST"])
@login_required
def clear_whitelist():
    """
    Remove all items from the user's whitelist.
    """
    try:
        deleted_count = Whitelist.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()

        return jsonify(
            {
                "success": True,
                "message": "All whitelist items cleared",
                "items_removed": deleted_count,
                "request_id": get_request_id(),
            }
        ), 200

    except Exception as e:
        current_app.logger.error(f"Error clearing whitelist: {e}")
        db.session.rollback()
        return jsonify(
            {
                "success": False,
                "error": "Failed to clear whitelist",
                "request_id": get_request_id(),
            }
        ), 500


@bp.errorhandler(404)
def api_not_found(error):
    """API 404 handler"""
    return jsonify({"error": "Endpoint not found"}), 404


@bp.errorhandler(500)
def api_error(error):
    """API 500 handler"""
    current_app.logger.error(f"API error: {error}")
    return jsonify({"error": "Internal server error"}), 500


# Add the endpoint paths that the frontend JavaScript expects
@bp.route("/analyze_song/<int:song_id>", methods=["POST"])
@login_required
def api_analyze_song(song_id):
    """API endpoint for analyzing a single song (matches frontend expectation)"""
    return analyze_single_song(song_id)


@bp.route("/song_analysis_status/<int:song_id>")
@login_required
def api_song_analysis_status(song_id):
    """API endpoint for song analysis status (matches frontend expectation)"""
    return get_song_analysis_status(song_id)
# Lightweight dashboard stats for async UI update
@bp.route("/dashboard/stats")
@login_required
def get_dashboard_stats():
    try:
        # 60s Redis cache per user
        cache_key = f"dashboard:stats:{current_user.id}"
        cached = cache_get_json(cache_key)
        if cached:
            return jsonify(cached)
        # Total playlists for current user
        total_playlists = (
            db.session.query(db.func.count(Playlist.id))
            .filter(Playlist.owner_id == current_user.id)
            .scalar()
            or 0
        )

        # Total unique songs across user's playlists
        total_songs = (
            db.session.query(db.func.count(db.func.distinct(Song.id)))
            .join(PlaylistSong, PlaylistSong.song_id == Song.id)
            .join(Playlist, Playlist.id == PlaylistSong.playlist_id)
            .filter(Playlist.owner_id == current_user.id)
            .scalar()
            or 0
        )

        # Unique analyzed songs (completed) across user's playlists
        analyzed_songs = (
            db.session.query(db.func.count(db.func.distinct(Song.id)))
            .join(AnalysisResult, AnalysisResult.song_id == Song.id)
            .join(PlaylistSong, PlaylistSong.song_id == Song.id)
            .join(Playlist, Playlist.id == PlaylistSong.playlist_id)
            .filter(
                Playlist.owner_id == current_user.id,
                # No status filter needed - only completed analyses exist,
            )
            .scalar()
            or 0
        )

        # Unique flagged songs (completed + medium/high concern)
        flagged_songs = (
            db.session.query(db.func.count(db.func.distinct(Song.id)))
            .join(AnalysisResult, AnalysisResult.song_id == Song.id)
            .join(PlaylistSong, PlaylistSong.song_id == Song.id)
            .join(Playlist, Playlist.id == PlaylistSong.playlist_id)
            .filter(
                Playlist.owner_id == current_user.id,
                # No status filter needed - only completed analyses exist,
                AnalysisResult.concern_level.in_(["medium", "high"]),
            )
            .scalar()
            or 0
        )

        progress_pct = round((analyzed_songs / total_songs * 100.0), 1) if total_songs > 0 else 0.0

        # Clean playlists (average score >= 75%) - count playlists with high avg scores (simplified)
        clean_playlists_subquery = (
            db.session.query(Playlist.id)
            .join(PlaylistSong, PlaylistSong.playlist_id == Playlist.id)
            .join(Song, Song.id == PlaylistSong.song_id)
            .join(AnalysisResult, AnalysisResult.song_id == Song.id)
            .filter(Playlist.owner_id == current_user.id)
            .group_by(Playlist.id)
            .having(db.func.avg(AnalysisResult.score) >= 0.75)
        )
        
        clean_playlists = len(clean_playlists_subquery.all())

        payload = {
            "success": True,
            "totals": {
                "total_playlists": int(total_playlists),
                "total_songs": int(total_songs),
                "analyzed_songs": int(analyzed_songs),
                "flagged_songs": int(flagged_songs),
                "clean_playlists": int(clean_playlists),
                "analysis_progress": progress_pct,
            },
        }
        cache_set_json(cache_key, payload, ttl_seconds=60)
        return jsonify(payload)
    except Exception as e:
        current_app.logger.error(f"Dashboard stats error: {e}")
        return jsonify({"success": False, "error": "stats_error", "message": str(e)}), 500



# Additional back-compat endpoints expected by legacy tests
@bp.route("/playlists/<int:playlist_id>/analyze", methods=["POST"])
@login_required
def legacy_playlist_analyze_alias(playlist_id):
    return start_playlist_analysis_unanalyzed(playlist_id)


## Removed queue/worker endpoints: /queue/status, /worker/health, /jobs/<id>/status, /queue/health


## Removed progress endpoints: /progress/<id>, /progress, /progress/cleanup


@bp.route("/admin/update-playlist-scores", methods=["POST"])
@login_required
def admin_update_playlist_scores():
    """Admin endpoint to manually update all playlist scores"""
    try:
        if not current_user.is_admin:
            return jsonify({"success": False, "error": "Admin access required"}), 403

        # Lazy import via importlib to avoid hard dependency in MVP
        import importlib

        try:
            module = importlib.import_module("app.services.playlist_scoring_service")
            PlaylistScoringService = getattr(module, "PlaylistScoringService")
            scoring_service = PlaylistScoringService()
            result = scoring_service.update_all_playlist_scores()
        except ModuleNotFoundError:
            return jsonify(
                {"success": False, "error": "PlaylistScoringService not available in this build"}
            ), 501

        return jsonify(
            {
                "success": True,
                "message": f'Updated scores for {result["updated_count"]} playlists',
                "updated_count": result["updated_count"],
                "total_playlists": result["total_playlists"],
                "errors": result.get("errors", []),
            }
        )

    except Exception as e:
        current_app.logger.error(f"Admin playlist score update error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/admin/recompute-has-flagged", methods=["POST"])
@login_required
@admin_required
def admin_recompute_has_flagged():
    """
    Recompute Playlist.has_flagged for all playlists (or a specific user's playlists).

    Body (optional JSON): {"user_id": <int>} to limit to a single user.
    """
    try:
        payload = request.get_json(silent=True) or {}
        user_id = payload.get("user_id")

        # Build UPDATE with EXISTS to set has_flagged based on completed analyses with medium/high concern
        if user_id:
            sql = text(
                """
                UPDATE playlists
                SET has_flagged = EXISTS (
                  SELECT 1
                  FROM playlist_songs ps
                  JOIN analysis_results ar ON ar.song_id = ps.song_id
                  WHERE ps.playlist_id = playlists.id
                    -- All stored analyses are completed in simplified model
                    AND LOWER(ar.concern_level) IN ('medium','high')
                )
                WHERE owner_id = :uid
                """
            )
            db.session.execute(sql, {"uid": int(user_id)})
        else:
            sql = text(
                """
                UPDATE playlists
                SET has_flagged = EXISTS (
                  SELECT 1
                  FROM playlist_songs ps
                  JOIN analysis_results ar ON ar.song_id = ps.song_id
                  WHERE ps.playlist_id = playlists.id
                    -- All stored analyses are completed in simplified model
                    AND LOWER(ar.concern_level) IN ('medium','high')
                )
                """
            )
            db.session.execute(sql)

        db.session.commit()

        # Report counts
        base_query = Playlist.query
        if user_id:
            base_query = base_query.filter(Playlist.owner_id == int(user_id))
        total = base_query.count()
        flagged = base_query.filter(Playlist.has_flagged.is_(True)).count()

        return jsonify(
            {
                "success": True,
                "message": "has_flagged recomputed",
                "scope": "user" if user_id else "all",
                "total_playlists": total,
                "flagged_playlists": flagged,
            }
        )
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Admin recompute has_flagged error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@bp.route("/admin/prune-analyses", methods=["POST"])
@login_required
@admin_required
def admin_prune_analyses():
    """
    Prune old AnalysisResult rows with non-useful statuses to control growth.

    Defaults:
    - statuses: ['failed', 'pending']
    - retention_days: 30

    Body (optional JSON): {"statuses": [...], "retention_days": <int>}
    """
    try:
        payload = request.get_json(silent=True) or {}
        statuses = payload.get("statuses") or ["failed", "pending"]
        retention_days = int(payload.get("retention_days") or 30)

        cutoff = datetime.now().astimezone() - timedelta(days=retention_days)

        # No failed or pending analyses exist in simplified model - skip pruning
        deleted_count = 0
        # q = AnalysisResult.query.filter(
        #     AnalysisResult.created_at < cutoff,
        # )
        # No pruning needed - all analyses are completed and valid

        return jsonify(
            {
                "success": True,
                "deleted": int(deleted_count or 0),
                "retention_days": retention_days,
                "statuses": statuses,
            }
        )
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Admin prune analyses error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


def get_background_analysis_progress():
    """Get accurate background analysis progress for the active job - DISABLED (using direct analysis)"""
    try:
        # OLD QUEUE SYSTEM REMOVED - using direct analysis now
        return {
            "active": False,
            "message": "Background analysis disabled - using direct ML analysis",
        }

        # Only process background analysis jobs
        if job_data.get("job_type") != "background_analysis":
            return {"active": False, "message": "Active job is not a background analysis"}

        user_id = job_data.get("user_id")
        metadata = job_data.get("metadata", {})
        total_songs = metadata.get("total_songs", 0)
        user_name = metadata.get("user_name", "Unknown User")

        if not user_id or not total_songs:
            return {"active": False, "message": "Invalid background analysis job data"}

        # Get song IDs from metadata for accurate filtering
        song_ids = metadata.get("song_ids", [])

        if song_ids:
            # Count analyses for specific songs in the job
            completed_analyses = AnalysisResult.query.filter(
                AnalysisResult.song_id.in_(song_ids), # No status filter needed - only completed analyses exist
            ).count()

            failed_analyses = 0  # No failed analyses in simplified model

            in_progress_analyses = 0  # No in-progress analyses in simplified model
        else:
            # Fallback: count all analyses for user
            completed_analyses = AnalysisResult.query.filter(
                AnalysisResult.user_id == user_id, # No status filter needed - only completed analyses exist
            ).count()

            failed_analyses = 0  # No failed analyses in simplified model

            in_progress_analyses = 0  # No in-progress analyses in simplified model

        # Calculate progress
        total_processed = completed_analyses + failed_analyses
        progress_percentage = (total_processed / total_songs * 100) if total_songs > 0 else 0

        # Calculate ETA based on recent processing rate
        remaining_songs = total_songs - total_processed
        eta_data = calculate_processing_rate_eta(remaining_songs)

        return {
            "active": True,
            "progress_percentage": round(progress_percentage, 1),
            "total_songs": total_songs,
            "completed_analyses": completed_analyses,
            "failed_analyses": failed_analyses,
            "in_progress_analyses": in_progress_analyses,
            "remaining_songs": remaining_songs,
            "user_id": user_id,
            "user_name": user_name,
            "job_id": job_data.get("job_id"),
            **eta_data,
        }

    except Exception as e:
        current_app.logger.error(f"Background analysis progress error: {e}")
        return {
            "active": False,
            "error": str(e),
            "message": "Failed to get background analysis progress",
        }


def calculate_processing_rate_eta(remaining_songs):
    """Calculate ETA based on actual recent processing rate"""
    try:
        from datetime import datetime, timedelta, timezone

        # Look at completions in the last 10 minutes for rate calculation
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=10)

        recent_completions = (
            AnalysisResult.query.filter(
                # No status filter needed - only completed analyses exist, AnalysisResult.updated_at >= cutoff_time
            )
            .order_by(AnalysisResult.updated_at.desc())
            .limit(100)
            .all()
        )

        if len(recent_completions) < 2:
            # Fallback: use a conservative estimate
            analyses_per_hour = 30  # Conservative estimate
        else:
            # Calculate actual rate from recent completions
            time_span_minutes = 10  # We looked at last 10 minutes
            analyses_per_minute = len(recent_completions) / time_span_minutes
            analyses_per_hour = analyses_per_minute * 60

            # Ensure we have a reasonable minimum rate
            analyses_per_hour = max(analyses_per_hour, 10)

        # Calculate ETA
        if analyses_per_hour > 0:
            estimated_hours = remaining_songs / analyses_per_hour
            estimated_minutes = int(estimated_hours * 60)
        else:
            estimated_hours = 0
            estimated_minutes = 0

        return {
            "analyses_per_hour": round(analyses_per_hour, 1),
            "estimated_hours": round(estimated_hours, 1),
            "estimated_minutes": estimated_minutes,
            "sample_period_minutes": 10,
            "recent_completions_count": len(recent_completions),
        }

    except Exception as e:
        current_app.logger.error(f"ETA calculation error: {e}")
        return {
            "analyses_per_hour": 30,  # Conservative fallback
            "estimated_hours": remaining_songs / 30 if remaining_songs > 0 else 0,
            "estimated_minutes": int((remaining_songs / 30 * 60)) if remaining_songs > 0 else 0,
            "sample_period_minutes": 10,
            "recent_completions_count": 0,
            "error": str(e),
        }


@bp.route("/background-analysis/status")
@login_required
def get_background_analysis_status():
    """API endpoint for accurate background analysis progress"""
    try:
        progress_data = get_background_analysis_progress()

        return jsonify({"status": "success", "success": True, **progress_data})

    except Exception as e:
        current_app.logger.error(f"Background analysis status API error: {e}")
        return jsonify(
            {
                "status": "error",
                "success": False,
                "error": str(e),
                "message": "Failed to get background analysis status",
            }
        ), 500


@bp.route("/analysis/processing-rate")
def get_processing_rate():
    """API endpoint for current processing rate information"""
    try:
        # Calculate rate for informational purposes
        eta_data = calculate_processing_rate_eta(0)  # 0 remaining for rate calc only

        return jsonify(
            {
                "status": "success",
                "success": True,
                "analyses_per_minute": round(eta_data["analyses_per_hour"] / 60, 2),
                "analyses_per_hour": eta_data["analyses_per_hour"],
                "sample_period_minutes": eta_data["sample_period_minutes"],
                "recent_completions_count": eta_data["recent_completions_count"],
            }
        )
    except Exception as e:
        current_app.logger.error(f"Processing rate API error: {e}")
        return jsonify(
            {
                "status": "error",
                "success": False,
                "error": str(e),
                "message": "Failed to get processing rate",
            }
        ), 500


@bp.route("/ga4/analyze-completed", methods=["POST"])
@login_required
@validate_json(GA4CompletedSchema)
def ga4_analyze_completed():
    """Server-side GA4 event for analysis completion (best-effort)."""
    try:
        data = request.get_json(force=True, silent=True) or {}
        completed = int(data.get("completed_songs") or 0)
        total = int(data.get("total_songs") or 0)
        params = {"completed_songs": completed, "total_songs": total, "event_category": "analysis"}
        send_event_async(current_app, "analyze_completed", params, user_id=str(current_user.id))
        return jsonify({"success": True})
    except Exception as e:
        current_app.logger.debug(f"GA4 analyze_completed error (ignored): {e}")
        return jsonify({"success": True})


@bp.route("/analysis/performance")
def analysis_performance_alias():
    """Back-compat alias to expose performance metrics similar to processing-rate."""
    return get_processing_rate()


@bp.route("/background-analysis/public-status")
def get_background_analysis_public_status():
    """Public endpoint to expose simple per-user analysis status from memory."""
    try:
        uid = None
        try:
            uid = current_user.id  # may be anonymous
        except Exception:
            uid = None
        # If no user context, return inactive
        if not uid:
            return jsonify({"status": "success", "active": False})
        status = get_user_analysis_status(current_app._get_current_object(), uid)
        return jsonify(status)
    except Exception as e:
        current_app.logger.error(f"Public background analysis status error: {e}")
        return jsonify({"status": "error", "active": False}), 200


@bp.route("/test/semantic-detection", methods=["POST"])
@login_required
@admin_required
@validate_json(TestSemanticDetectionSchema)
def test_semantic_detection():
    """Test endpoint for enhanced semantic theme detection."""
    try:
        data = request.get_json()
        title = data.get("title", "Test Song")
        artist = data.get("artist", "Test Artist")
        lyrics = data.get("lyrics", "")

        if not lyrics:
            return jsonify({"success": False, "error": "Lyrics are required for testing"}), 400

        # Test the enhanced analysis
        from app.services.simplified_christian_analysis_service import (
            SimplifiedChristianAnalysisService,
        )

        analysis_service = SimplifiedChristianAnalysisService()

        result = analysis_service.analyze_song(title, artist, lyrics)

        # Get precision metrics
        precision_report = analysis_service.get_analysis_precision_report()

        return jsonify(
            {
                "success": True,
                "analysis": {
                    "score": result.scoring_results["final_score"],
                    "quality_level": result.scoring_results["quality_level"],
                    "explanation": result.scoring_results["explanation"],
                    "themes_detected": len(result.biblical_analysis["themes"]),
                    "themes": [
                        theme.get("theme", str(theme)) if isinstance(theme, dict) else str(theme)
                        for theme in result.biblical_analysis["themes"]
                    ],
                    "concerns": len(result.content_analysis.get("detailed_concerns", [])),
                    "scripture_references": len(
                        result.biblical_analysis.get("supporting_scripture", [])
                    ),
                },
                "precision_metrics": precision_report,
                "message": "Enhanced semantic detection active",
            }
        )

    except Exception as e:
        current_app.logger.error(f"Error in semantic detection test: {e}")
        return jsonify({"success": False, "error": str(e)}), 500



@bp.route("/llm/status", methods=["GET"])
@login_required
def llm_provider_status():
    """
    Get the current LLM provider status and configuration.
    
    Returns information about which LLM provider is currently being used,
    health status of all providers, and routing configuration.
    """
    try:
        from ..services.intelligent_llm_router import get_intelligent_router
        
        router = get_intelligent_router()
        provider_info = router.get_provider_info()
        
        return jsonify({
            "success": True,
            "current_provider": provider_info.get("current_provider"),
            "current_endpoint": provider_info.get("current_endpoint"),
            "current_model": provider_info.get("current_model"),
            "providers": provider_info.get("providers", []),
            "total_providers": provider_info.get("total_providers", 0),
            "healthy_providers": provider_info.get("healthy_providers", 0),
            "router_status": "active" if provider_info.get("current_provider") else "no_providers_available",
            "timestamp": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        current_app.logger.error(f"Error getting LLM provider status: {e}")
        return jsonify({
            "success": False,
            "error": str(e),
            "router_status": "error"
        }), 500


@bp.route("/llm/force-provider", methods=["POST"])
@login_required
@admin_required
def force_llm_provider():
    """
    Force the LLM router to use a specific provider (admin only).
    
    Request body should contain:
    {
        "provider": "runpod|ollama|openai"
    }
    """
    try:
        data = request.get_json()
        if not data or "provider" not in data:
            return jsonify({
                "success": False,
                "error": "Provider name required in request body"
            }), 400
        
        provider_name = data["provider"]
        
        from ..services.intelligent_llm_router import get_intelligent_router
        
        router = get_intelligent_router()
        success = router.force_provider(provider_name)
        
        if success:
            return jsonify({
                "success": True,
                "message": f"Forced LLM provider to: {provider_name}",
                "current_provider": provider_name
            })
        else:
            return jsonify({
                "success": False,
                "error": f"Failed to force provider: {provider_name} (not available or unhealthy)"
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"Error forcing LLM provider: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@bp.route("/llm/reset-cache", methods=["POST"])
@login_required
@admin_required
def reset_llm_cache():
    """
    Reset the LLM provider cache to force re-detection (admin only).
    """
    try:
        from ..services.intelligent_llm_router import get_intelligent_router
        
        router = get_intelligent_router()
        router.reset_provider_cache()
        
        return jsonify({
            "success": True,
            "message": "LLM provider cache reset successfully"
        })
        
    except Exception as e:
        current_app.logger.error(f"Error resetting LLM cache: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
