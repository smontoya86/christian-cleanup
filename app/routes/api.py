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

from flask import Blueprint, jsonify, request, current_app, Response
from flask_login import login_required, current_user
from datetime import datetime
from sqlalchemy import text

from .. import db
from ..models.models import Playlist, Song, AnalysisResult, PlaylistSong, User, Whitelist
from ..services.spotify_service import SpotifyService
from ..services.unified_analysis_service import UnifiedAnalysisService
from ..services.priority_analysis_queue import (
    PriorityAnalysisQueue, enqueue_song_analysis, JobPriority
)
from ..services.priority_queue_worker import get_worker_status
from ..utils.health_monitor import health_monitor
from ..utils.prometheus_metrics import get_metrics, metrics_collector
from ..utils.auth import admin_required

bp = Blueprint('api', __name__)


@bp.route('/health')
def health():
    """Basic health check endpoint"""
    try:
        # Test database connection
        db.session.execute(text('SELECT 1'))
        return jsonify({
            'status': 'healthy',
            'database': 'connected',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        current_app.logger.error(f'Health check failed: {e}')
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500


@bp.route('/health/detailed')
def detailed_health_check():
    """Comprehensive health check with detailed system status"""
    try:
        # Force refresh for detailed checks
        system_health = health_monitor.get_system_health(force_refresh=True)
        
        # Convert to JSON-serializable format
        health_data = health_monitor.to_dict(system_health)
        
        # Set appropriate HTTP status based on health
        if system_health.status.value == 'healthy':
            status_code = 200
        elif system_health.status.value == 'warning':
            status_code = 200  # Still operational
        else:  # critical
            status_code = 503  # Service unavailable
        
        return jsonify(health_data), status_code
        
    except Exception as e:
        current_app.logger.error(f'Detailed health check failed: {e}')
        return jsonify({
            'status': 'critical',
            'timestamp': datetime.now().isoformat(),
            'error': f'Health monitoring system failed: {str(e)}',
            'checks': []
        }), 503


@bp.route('/health/ready')
def readiness_check():
    """Kubernetes-style readiness probe"""
    try:
        # Check critical dependencies only
        db.session.execute(text('SELECT 1')).scalar()
        
        import redis
        redis_client = redis.from_url(current_app.config.get('RQ_REDIS_URL', 'redis://redis:6379/0'))
        redis_client.ping()
        
        return jsonify({'status': 'ready'}), 200
        
    except Exception as e:
        current_app.logger.error(f'Readiness check failed: {e}')
        return jsonify({'status': 'not ready', 'error': str(e)}), 503


@bp.route('/health/live')
def liveness_check():
    """Kubernetes-style liveness probe"""
    # Very basic check - just ensure the application is responding
    return jsonify({
        'status': 'alive',
        'timestamp': datetime.now().isoformat()
    }), 200


@bp.route('/playlists')
@login_required
def get_playlists():
    """Get user's playlists as JSON"""
    playlists = Playlist.query.filter_by(owner_id=current_user.id).all()
    
    playlist_data = []
    for playlist in playlists:
        song_count = PlaylistSong.query.filter_by(playlist_id=playlist.id).count()
        analyzed_count = db.session.query(Song.id).join(AnalysisResult).join(PlaylistSong).filter(
            PlaylistSong.playlist_id == playlist.id,
            AnalysisResult.status == 'completed'
        ).distinct().count()
        
        playlist_data.append({
            'id': playlist.id,
            'name': playlist.name,
            'description': playlist.description,
            'song_count': song_count,
            'analyzed_count': analyzed_count,
            'analysis_progress': round((analyzed_count / song_count * 100) if song_count > 0 else 0, 1),
            'image_url': playlist.image_url,
            'spotify_url': f'https://open.spotify.com/playlist/{playlist.spotify_id}' if playlist.spotify_id else None,
            'score': playlist.score,
            'overall_alignment_score': playlist.overall_alignment_score,
            'last_analyzed': playlist.last_analyzed.isoformat() if playlist.last_analyzed else None
        })
    
    return jsonify({'playlists': playlist_data})


@bp.route('/playlist/<int:playlist_id>/songs')
@login_required
def get_playlist_songs(playlist_id):
    """Get songs in a playlist with analysis status"""
    playlist = Playlist.query.filter_by(
        id=playlist_id,
        owner_id=current_user.id
    ).first_or_404()
    
    songs_query = db.session.query(Song, AnalysisResult, PlaylistSong).join(
        PlaylistSong, Song.id == PlaylistSong.song_id
    ).outerjoin(
        AnalysisResult, Song.id == AnalysisResult.song_id
    ).filter(
        PlaylistSong.playlist_id == playlist_id
            ).order_by(PlaylistSong.track_position)
    
    songs_data = []
    for song, analysis, playlist_song in songs_query:
        song_data = {
            'id': song.id,
            'name': song.title,
            'artist': song.artist,
            'album': song.album,
            'duration_ms': song.duration_ms,
            'position': playlist_song.track_position,
            'spotify_url': f'https://open.spotify.com/track/{song.spotify_id}' if song.spotify_id else None,
            'analysis_status': analysis.status if analysis else 'pending',
            'analysis_score': analysis.score if analysis else None,
            'concern_level': analysis.concern_level if analysis else None,
            'detected_themes': analysis.themes if analysis else [],
            'analysis_date': analysis.created_at.isoformat() if analysis else None
        }
        songs_data.append(song_data)
    
    return jsonify({
        'playlist': {
            'id': playlist.id,
            'name': playlist.name,
            'description': playlist.description
        },
        'songs': songs_data
    })


@bp.route('/song/<int:song_id>/analysis')
@login_required
def get_song_analysis(song_id):
    """Get detailed analysis for a song"""
    # Verify user has access to this song
    song = db.session.query(Song).join(PlaylistSong).join(Playlist).filter(
        Song.id == song_id,
        Playlist.owner_id == current_user.id
    ).first_or_404()
    
    analysis = AnalysisResult.query.filter_by(song_id=song_id).order_by(
        AnalysisResult.created_at.desc()
    ).first()
    
    song_data = {
        'id': song.id,
        'name': song.title,
        'artist': song.artist,
        'album': song.album,
        'lyrics': song.lyrics,
        'spotify_url': f'https://open.spotify.com/track/{song.spotify_id}' if song.spotify_id else None
    }
    
    analysis_data = None
    if analysis:
        analysis_data = {
            'status': analysis.status,
            'score': analysis.score,
            'concern_level': analysis.concern_level,
            'themes': analysis.themes or [],
            'analysis_details': analysis.problematic_content or {},
            'created_at': analysis.created_at.isoformat(),
            'concerns': analysis.concerns or []
        }
    
    return jsonify({
        'song': song_data,
        'analysis': analysis_data
    })



@bp.route('/search_songs')
@login_required
def search_songs():
    """Search user's songs"""
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'songs': []})
    
    # Search in user's songs
    songs = db.session.query(Song, AnalysisResult).join(PlaylistSong).join(Playlist).outerjoin(
        AnalysisResult, Song.id == AnalysisResult.song_id
            ).filter(
        Playlist.owner_id == current_user.id,
        db.or_(
            Song.title.ilike(f'%{query}%'),
            Song.artist.ilike(f'%{query}%'),
            Song.album.ilike(f'%{query}%')
        )
    ).limit(20).all()
    
    songs_data = []
    for song, analysis in songs:
        songs_data.append({
            'id': song.id,
            'name': song.title,
            'artist': song.artist,
            'album': song.album,
            'analysis_status': analysis.status if analysis else 'pending',
            'concern_level': analysis.concern_level if analysis else None,
            'spotify_url': f'https://open.spotify.com/track/{song.spotify_id}' if song.spotify_id else None
        })
    
    return jsonify({'songs': songs_data})


@bp.route('/sync-status')
@login_required
def sync_status():
    """Get sync status for user's playlists"""
    try:
        # Count playlists by sync status
        total_playlists = Playlist.query.filter_by(owner_id=current_user.id).count()
        
        return jsonify({
            'status': 'success',
            'total_playlists': total_playlists,
            'sync_active': False,  # Would check for active sync jobs
            'last_sync': None,      # Would get from database
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        current_app.logger.error(f'Sync status check failed: {e}')
        return jsonify({
            'status': 'error',
            'error': str(e)
        }), 500


@bp.route('/stats')
@login_required
def get_user_stats():
    """Get comprehensive user statistics"""
    total_playlists = Playlist.query.filter_by(owner_id=current_user.id).count()
    
    total_songs = db.session.query(Song).join(PlaylistSong).join(Playlist).filter(
        Playlist.owner_id == current_user.id
    ).count()
    
    # Fix: Count unique songs with completed analysis (not total completed analysis records)
    analyzed_songs = db.session.query(Song.id).join(AnalysisResult).join(PlaylistSong).join(Playlist).filter(
        Playlist.owner_id == current_user.id,
        AnalysisResult.status == 'completed'
    ).distinct().count()
    
    # Count by concern level (using distinct song IDs to avoid duplicates)
    concern_counts = db.session.query(
        AnalysisResult.concern_level,
        db.func.count(db.func.distinct(AnalysisResult.song_id))
    ).join(Song).join(PlaylistSong).join(Playlist).filter(
        Playlist.owner_id == current_user.id,
        AnalysisResult.status == 'completed'
    ).group_by(AnalysisResult.concern_level).all()
    
    concern_dict = dict(concern_counts)
    
    return jsonify({
        'total_playlists': total_playlists,
        'total_songs': total_songs,
        'analyzed_songs': analyzed_songs,
        'analysis_progress': round((analyzed_songs / total_songs * 100) if total_songs > 0 else 0, 1),
        'concern_levels': {
            'low': concern_dict.get('low', 0),
            'medium': concern_dict.get('medium', 0),
            'high': concern_dict.get('high', 0)
        },
        'flagged_songs': concern_dict.get('medium', 0) + concern_dict.get('high', 0)
    })


@bp.route('/metrics')
def metrics():
    """Prometheus metrics endpoint"""
    try:
        metrics_data = get_metrics()
        return Response(metrics_data, mimetype='text/plain')
    except Exception as e:
        current_app.logger.error(f'Error generating metrics: {e}')
        metrics_collector.record_error('metrics_generation_error', 'api')
        return jsonify({'error': 'Metrics unavailable'}), 500


@bp.route('/playlists/<int:playlist_id>/analysis-status')
@login_required
def get_playlist_analysis_status(playlist_id):
    """Get playlist analysis status (consolidates functionality from analysis_progress)"""
    playlist = Playlist.query.filter_by(
        id=playlist_id,
        owner_id=current_user.id
    ).first_or_404()

    total_songs = PlaylistSong.query.filter_by(playlist_id=playlist_id).count()
    
    # Count unique songs by analysis status (fix duplicate counting)
    status_counts = db.session.query(
        AnalysisResult.status,
        db.func.count(db.func.distinct(AnalysisResult.song_id))
    ).join(Song).join(PlaylistSong).filter(
        PlaylistSong.playlist_id == playlist_id
    ).group_by(AnalysisResult.status).all()
    
    status_dict = dict(status_counts)
    completed_count = status_dict.get('completed', 0)
    failed_count = status_dict.get('failed', 0)
    in_progress_count = status_dict.get('in_progress', 0)
    pending_count = total_songs - sum(status_dict.values())
    
    progress_percentage = round((completed_count / total_songs * 100) if total_songs > 0 else 0, 1)
    
    return jsonify({
        # Frontend-expected format
        'success': True,
        'completed': progress_percentage == 100.0,
        'progress': progress_percentage,
        'analyzed_count': completed_count,
        'total_count': total_songs,
        'message': f'Analysis {progress_percentage}% complete ({completed_count}/{total_songs} songs)',
        
        # Detailed status breakdown (replaces analysis_progress endpoint)
        'playlist_id': playlist_id,
        'detailed_status': {
            'completed': completed_count,
            'failed': failed_count,
            'pending': pending_count,
            'in_progress': in_progress_count
        }
    })


@bp.route('/songs/<int:song_id>/analysis-status')
@login_required
def get_song_analysis_status(song_id):
    """Get song analysis status (frontend-expected endpoint)"""
    # Verify user has access to this song
    song = db.session.query(Song).join(PlaylistSong).join(Playlist).filter(
        Song.id == song_id,
        Playlist.owner_id == current_user.id
    ).first_or_404()

    analysis = AnalysisResult.query.filter_by(song_id=song_id).order_by(
        AnalysisResult.created_at.desc()
    ).first()
    
    if analysis and analysis.status == 'completed':
        return jsonify({
            'success': True,
            'completed': True,
            'has_analysis': True,
            'status': analysis.status,
            'progress': 100,
            'stage': 'Analysis complete',
            'score': analysis.score,
            'concern_level': analysis.concern_level,
            'message': 'Analysis completed',
            'result': {
                'id': analysis.id,
                'score': analysis.score,
                'concern_level': analysis.concern_level,
                'status': analysis.status,
                'themes': analysis.themes or [],
                'explanation': analysis.explanation,
                'created_at': analysis.created_at.isoformat() if analysis.created_at else None
            },
            'analysis': {
                'id': analysis.id,
                'score': analysis.score,
                'concern_level': analysis.concern_level,
                'status': analysis.status,
                'themes': analysis.themes or [],
                'explanation': analysis.explanation,
                'created_at': analysis.created_at.isoformat() if analysis.created_at else None
            }
        })
    elif analysis and analysis.status == 'pending':
        # Calculate estimated progress based on time elapsed
        created_at = analysis.created_at
        if created_at:
            elapsed_seconds = (datetime.now() - created_at).total_seconds()
            # Estimate progress: most songs take 30-60 seconds to analyze
            # Progress increases rapidly in first 30 seconds, then levels off
            if elapsed_seconds < 5:
                progress = 10
                stage = 'Fetching lyrics...'
            elif elapsed_seconds < 15:
                progress = 30
                stage = 'Analyzing content...'
            elif elapsed_seconds < 30:
                progress = 60
                stage = 'Processing themes...'
            elif elapsed_seconds < 45:
                progress = 80
                stage = 'Generating score...'
            else:
                progress = 90
                stage = 'Finalizing analysis...'
        else:
            progress = 5
            stage = 'Starting analysis...'
            
        return jsonify({
            'success': True,
            'completed': False,
            'has_analysis': False,
            'status': 'pending',
            'progress': progress,
            'stage': stage,
            'message': 'Analysis in progress'
        })
    elif analysis and analysis.status == 'failed':
        return jsonify({
            'success': False,
            'completed': True,
            'failed': True,
            'has_analysis': False,
            'status': 'failed',
            'progress': 0,
            'stage': 'Analysis failed',
            'error': 'Analysis failed',
            'message': 'Analysis failed'
        })
    else:
        return jsonify({
            'success': True,
            'completed': False,
            'has_analysis': False,
            'status': 'pending',
            'progress': 0,
            'stage': 'Initializing...',
            'message': 'Analysis not started'
        })


@bp.route('/songs/<int:song_id>/analyze', methods=['POST'])
@login_required
def analyze_single_song(song_id):
    """Analyze a single song using priority queue system"""
    try:
        # Verify user has access to this song
        song = db.session.query(Song).join(PlaylistSong).join(Playlist).filter(
            Song.id == song_id,
            Playlist.owner_id == current_user.id
        ).first()
        
        if not song:
            return jsonify({
                'status': 'error',
                'message': f'Song with ID {song_id} not found or access denied'
            }), 404

        # Create or update analysis record to 'pending' status for progress tracking
        existing_analysis = AnalysisResult.query.filter_by(song_id=song_id).first()
        if existing_analysis:
            existing_analysis.status = 'pending'
            existing_analysis.updated_at = db.func.now()
        else:
            new_analysis = AnalysisResult(song_id=song_id, status='pending')
            db.session.add(new_analysis)
        
        db.session.commit()

        # Enqueue analysis job with HIGH priority (individual song requests)
        job = enqueue_song_analysis(
            song_id=song_id,
            user_id=current_user.id,
            priority=JobPriority.HIGH,
            metadata={
                'song_title': song.title,
                'artist': song.artist,
                'requested_at': datetime.now().isoformat()
            }
        )
        
        return jsonify({
            'success': True,
            'status': 'success',
            'message': 'Song queued for analysis',
            'song_id': song_id,
            'job_id': job.job_id
        })

    except ValueError as e:
        current_app.logger.error(f'Song not found: {e}')
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 404
    except Exception as e:
        current_app.logger.error(f'Single song analysis error: {e}')
        return jsonify({
            'status': 'error',
            'error': str(e),
            'message': 'Analysis service error occurred'
        }), 500


@bp.route('/playlists/<int:playlist_id>/analyze-unanalyzed', methods=['POST'])
@login_required
def start_playlist_analysis_unanalyzed(playlist_id):
    """Start analysis for unanalyzed songs in playlist using priority queue"""
    try:
        playlist = Playlist.query.filter_by(
            id=playlist_id,
            owner_id=current_user.id
        ).first_or_404()

        # Get unanalyzed songs
        unanalyzed_songs = db.session.query(Song).join(PlaylistSong).outerjoin(AnalysisResult).filter(
            PlaylistSong.playlist_id == playlist_id,
            AnalysisResult.id.is_(None)
        ).all()

        if not unanalyzed_songs:
            return jsonify({
                'status': 'success',
                'success': True,
                'message': 'All songs already analyzed',
                'queued_count': 0
            })

        # Use unified analysis service to queue playlist analysis
        analysis_service = UnifiedAnalysisService()
        job = analysis_service.enqueue_playlist_analysis(
            playlist_id=playlist_id,
            user_id=current_user.id,
            priority='medium'  # Playlist analysis = MEDIUM priority
        )
        
        return jsonify({
            'status': 'success',
            'success': True,
            'message': f'Queued {len(unanalyzed_songs)} songs for analysis',
            'queued_count': len(unanalyzed_songs),
            'job_id': job.id
        })

    except Exception as e:
        current_app.logger.error(f'Playlist analysis error: {e}')
        return jsonify({
            'status': 'error',
            'success': False,
            'error': str(e),
            'message': 'Failed to start playlist analysis'
        }), 500


@bp.route('/playlists/<int:playlist_id>/reanalyze-all', methods=['POST'])
@login_required
def reanalyze_all_playlist_songs(playlist_id):
    """Reanalyze all songs in playlist using priority queue"""
    try:
        playlist = Playlist.query.filter_by(
            id=playlist_id,
            owner_id=current_user.id
        ).first_or_404()

        # Get all songs in playlist
        songs = db.session.query(Song).join(PlaylistSong).filter(
            PlaylistSong.playlist_id == playlist_id
        ).all()

        if not songs:
            return jsonify({
                'success': True,
                'message': 'No songs found in playlist',
                'queued_count': 0
            })

        # Use unified analysis service to queue playlist reanalysis
        analysis_service = UnifiedAnalysisService()
        job = analysis_service.enqueue_playlist_analysis(
            playlist_id=playlist_id,
            user_id=current_user.id,
            priority='medium'  # Playlist reanalysis = MEDIUM priority
        )
        
        return jsonify({
            'success': True,
            'message': f'Queued {len(songs)} songs for reanalysis',
            'queued_count': len(songs),
            'job_id': job.id
        })

    except Exception as e:
        current_app.logger.error(f'Playlist reanalysis error: {e}')
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to start playlist reanalysis'
        }), 500


@bp.route('/analysis/status')
@login_required
def get_analysis_status():
    """Get overall analysis status for the current user with queue information"""
    try:
        # Get queue status from priority queue
        queue = PriorityAnalysisQueue()
        queue_status = queue.get_queue_status()
        
        # Get all user's playlists
        user_playlists = Playlist.query.filter_by(owner_id=current_user.id).all()
        
        total_songs = 0
        analyzed_songs = 0
        
        for playlist in user_playlists:
            playlist_total = PlaylistSong.query.filter_by(playlist_id=playlist.id).count()
            playlist_analyzed = db.session.query(Song.id).join(AnalysisResult).join(PlaylistSong).filter(
                PlaylistSong.playlist_id == playlist.id,
                AnalysisResult.status == 'completed'
            ).distinct().count()
            
            total_songs += playlist_total
            analyzed_songs += playlist_analyzed
        
        progress_percentage = round((analyzed_songs / total_songs * 100) if total_songs > 0 else 0, 1)
        
        return jsonify({
            'status': 'success',
            'success': True,
            'active': progress_percentage < 100.0,
            'completed': progress_percentage == 100.0,
            'progress': progress_percentage,
            'analyzed_count': analyzed_songs,
            'total_count': total_songs,
            'queue_length': queue_status.get('total_jobs', 0),
            'pending_jobs': queue_status.get('pending_jobs', 0),
            'in_progress_jobs': queue_status.get('in_progress_jobs', 0),
            'estimated_completion_minutes': queue_status.get('estimated_completion_time', 0),
            'message': f'Analysis {progress_percentage}% complete ({analyzed_songs}/{total_songs} songs)'
        })
        
    except Exception as e:
        current_app.logger.error(f'Analysis status error: {e}')
        return jsonify({
            'status': 'error',
            'success': False,
            'error': str(e),
            'message': 'Failed to get analysis status'
        }), 500


@bp.route('/admin/reanalysis-status')
@login_required
@admin_required
def get_admin_reanalysis_status():
    """Get admin reanalysis status (placeholder for now)"""
    # For now, return no active reanalysis since this is admin-only functionality
    return jsonify({
        'active': False,
        'completed': False,
        'progress': 0,
        'message': 'No active reanalysis'
    })


@bp.route('/analyze-all', methods=['POST'])
@login_required
def analyze_all_user_songs():
    """User endpoint to trigger analysis for all unanalyzed songs in their playlists"""
    try:
        user_id = current_user.id
        
        # Check how many songs actually need analysis
        total_unique_songs = db.session.query(Song.id).join(PlaylistSong).join(Playlist).filter(
            Playlist.owner_id == user_id
        ).distinct().count()

        if total_unique_songs == 0:
            return jsonify({
                'success': True,
                'message': 'No songs found in your playlists',
                'queued_count': 0,
                'user_id': user_id,
                'already_complete': True
            })

        # Count songs with completed analysis
        completed_songs = db.session.query(Song.id).join(PlaylistSong).join(Playlist).join(
            AnalysisResult, Song.id == AnalysisResult.song_id
        ).filter(
            Playlist.owner_id == user_id,
            AnalysisResult.status == 'completed'
        ).distinct().count()

        unanalyzed_count = total_unique_songs - completed_songs

        # If all songs are already analyzed, return success with appropriate message
        if unanalyzed_count == 0:
            return jsonify({
                'success': True,
                'message': f'All {total_unique_songs:,} songs are already analyzed',
                'queued_count': 0,
                'total_songs': total_unique_songs,
                'completed_songs': completed_songs,
                'user_id': user_id,
                'already_complete': True
            })

        # Use background analysis with MEDIUM priority for user-triggered analysis
        analysis_service = UnifiedAnalysisService()
        job = analysis_service.enqueue_background_analysis(
            user_id=user_id,
            priority='medium'  # User-triggered analysis = MEDIUM priority
        )
        
        return jsonify({
            'success': True,
            'message': f'Queued {unanalyzed_count:,} unanalyzed songs for analysis',
            'queued_count': unanalyzed_count,
            'total_songs': total_unique_songs,
            'completed_songs': completed_songs,
            'user_id': user_id,
            'job_id': job.id,
            'already_complete': False
        })

    except ValueError as e:
        if "No unanalyzed songs found" in str(e):
            # This should be caught by our check above, but just in case
            return jsonify({
                'success': True,
                'message': 'All songs are already analyzed',
                'queued_count': 0,
                'user_id': user_id,
                'already_complete': True
            })
        else:
            current_app.logger.error(f'User analysis error: {e}')
            return jsonify({
                'success': False,
                'error': str(e),
                'message': 'Failed to start analysis for your songs'
            }), 500
    except Exception as e:
        current_app.logger.error(f'User analysis error: {e}')
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to start analysis for your songs'
        }), 500


@bp.route('/admin/reanalyze-user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def admin_reanalyze_user(user_id):
    """Admin-only endpoint to trigger reanalysis for a specific user"""
    try:
        # Validate target user exists
        target_user = User.query.get(user_id)
        if not target_user:
            return jsonify({
                'success': False,
                'error': f'User with ID {user_id} not found'
            }), 404

        # Check how many songs actually need analysis
        total_unique_songs = db.session.query(Song.id).join(PlaylistSong).join(Playlist).filter(
            Playlist.owner_id == user_id
        ).distinct().count()

        if total_unique_songs == 0:
            return jsonify({
                'success': True,
                'message': f'No songs found for user {target_user.display_name or target_user.email}',
                'queued_count': 0,
                'user_id': user_id,
                'already_complete': True
            })

        # Count songs with completed analysis
        completed_songs = db.session.query(Song.id).join(PlaylistSong).join(Playlist).join(
            AnalysisResult, Song.id == AnalysisResult.song_id
        ).filter(
            Playlist.owner_id == user_id,
            AnalysisResult.status == 'completed'
        ).distinct().count()

        unanalyzed_count = total_unique_songs - completed_songs

        # If all songs are already analyzed, return success with appropriate message
        if unanalyzed_count == 0:
            return jsonify({
                'success': True,
                'message': f'All {total_unique_songs:,} songs are already analyzed for user {target_user.display_name or target_user.email}',
                'queued_count': 0,
                'total_songs': total_unique_songs,
                'completed_songs': completed_songs,
                'user_id': user_id,
                'already_complete': True
            })

        # Use background analysis with LOW priority for admin-triggered reanalysis
        analysis_service = UnifiedAnalysisService()
        job = analysis_service.enqueue_background_analysis(
            user_id=user_id,
            priority='low'  # Admin reanalysis = LOW priority (background)
        )
        
        return jsonify({
            'success': True,
            'message': f'Queued {unanalyzed_count:,} unanalyzed songs for background analysis for user {target_user.display_name or target_user.email}',
            'queued_count': unanalyzed_count,
            'total_songs': total_unique_songs,
            'completed_songs': completed_songs,
            'user_id': user_id,
            'job_id': job.id,
            'already_complete': False
        })

    except ValueError as e:
        if "No unanalyzed songs found" in str(e):
            # This should be caught by our check above, but just in case
            return jsonify({
                'success': True,
                'message': f'All songs are already analyzed for user {target_user.display_name or target_user.email}',
                'queued_count': 0,
                'user_id': user_id,
                'already_complete': True
            })
        else:
            current_app.logger.error(f'Admin reanalysis error: {e}')
            return jsonify({
                'success': False,
                'error': str(e),
                'message': f'Failed to start background analysis for user {user_id}'
            }), 500
    except Exception as e:
        current_app.logger.error(f'Admin reanalysis error: {e}')
        return jsonify({
            'success': False,
            'error': str(e),
            'message': f'Failed to start background analysis for user {user_id}'
        }), 500





# Whitelist Management API
@bp.route('/whitelist', methods=['POST'])
@login_required
def add_whitelist_item():
    """
    Add an item to the user's whitelist.
    
    If the item exists on the blacklist, it will be moved to the whitelist.
    If the item already exists on the whitelist, the reason will be updated.
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No JSON data provided'
            }), 400
            
        # Validate required fields
        spotify_id = data.get('spotify_id')
        item_type = data.get('item_type')
        
        if not spotify_id:
            return jsonify({
                'success': False,
                'error': 'spotify_id is required'
            }), 400
            
        if not item_type:
            return jsonify({
                'success': False,
                'error': 'item_type is required'
            }), 400
            
        # Validate item_type
        valid_types = ['song', 'artist', 'playlist']
        if item_type not in valid_types:
            return jsonify({
                'success': False,
                'error': f'item_type must be one of: {", ".join(valid_types)}'
            }), 400
            
        name = data.get('name', '')
        reason = data.get('reason', '')
        

            
        # Check if item already exists in whitelist
        existing_entry = Whitelist.query.filter_by(
            user_id=current_user.id,
            spotify_id=spotify_id,
            item_type=item_type
        ).first()
        
        if existing_entry:
            # Update existing entry's reason
            existing_entry.reason = reason
            if name:
                existing_entry.name = name
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Whitelist item reason updated',
                'item': existing_entry.to_dict()
            }), 200
            
        # Create new whitelist entry
        whitelist_entry = Whitelist(
            user_id=current_user.id,
            spotify_id=spotify_id,
            item_type=item_type,
            name=name,
            reason=reason
        )
        
        db.session.add(whitelist_entry)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Item added to whitelist',
            'item': whitelist_entry.to_dict()
        }), 201
        
    except Exception as e:
        current_app.logger.error(f'Error adding whitelist item: {e}')
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Failed to add item to whitelist'
        }), 500


@bp.route('/whitelist', methods=['GET'])
@login_required
def get_whitelist_items():
    """
    Get all items in the user's whitelist.
    
    Optional query parameter:
    - item_type: Filter by specific item type (song, artist, playlist)
    """
    try:
        item_type_filter = request.args.get('item_type')
        
        query = Whitelist.query.filter_by(user_id=current_user.id)
        
        if item_type_filter:
            valid_types = ['song', 'artist', 'playlist']
            if item_type_filter not in valid_types:
                return jsonify({
                    'success': False,
                    'error': f'Invalid item_type. Must be one of: {", ".join(valid_types)}'
                }), 400
            query = query.filter_by(item_type=item_type_filter)
            
        whitelist_items = query.order_by(Whitelist.added_date.desc()).all()
        
        return jsonify({
            'success': True,
            'items': [item.to_dict() for item in whitelist_items],
            'total_count': len(whitelist_items)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Error retrieving whitelist items: {e}')
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve whitelist items'
        }), 500


@bp.route('/whitelist/<int:entry_id>', methods=['DELETE'])
@login_required
def remove_whitelist_item(entry_id):
    """
    Remove a specific item from the user's whitelist.
    """
    try:
        whitelist_entry = Whitelist.query.filter_by(
            id=entry_id,
            user_id=current_user.id
        ).first()
        
        if not whitelist_entry:
            return jsonify({
                'success': False,
                'error': 'Whitelist entry not found'
            }), 404
            
        item_name = whitelist_entry.name or f"{whitelist_entry.item_type} {whitelist_entry.spotify_id}"
        
        db.session.delete(whitelist_entry)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Item removed from whitelist'
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Error removing whitelist item {entry_id}: {e}')
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Failed to remove item from whitelist'
        }), 500


@bp.route('/whitelist/clear', methods=['POST'])
@login_required  
def clear_whitelist():
    """
    Remove all items from the user's whitelist.
    """
    try:
        deleted_count = Whitelist.query.filter_by(user_id=current_user.id).delete()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'All whitelist items cleared',
            'items_removed': deleted_count
        }), 200
        
    except Exception as e:
        current_app.logger.error(f'Error clearing whitelist: {e}')
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': 'Failed to clear whitelist'
        }), 500


@bp.errorhandler(404)
def api_not_found(error):
    """API 404 handler"""
    return jsonify({'error': 'Endpoint not found'}), 404


@bp.errorhandler(500)
def api_error(error):
    """API 500 handler"""
    current_app.logger.error(f'API error: {error}')
    return jsonify({'error': 'Internal server error'}), 500


# Add the endpoint paths that the frontend JavaScript expects
@bp.route('/analyze_song/<int:song_id>', methods=['POST'])
@login_required
def api_analyze_song(song_id):
    """API endpoint for analyzing a single song (matches frontend expectation)"""
    return analyze_single_song(song_id)


@bp.route('/song_analysis_status/<int:song_id>')
@login_required
def api_song_analysis_status(song_id):
    """API endpoint for song analysis status (matches frontend expectation)"""
    return get_song_analysis_status(song_id)


# New Queue Management Endpoints

@bp.route('/queue/status')
@login_required
def get_queue_status():
    """Get detailed queue status and health information"""
    try:
        queue = PriorityAnalysisQueue()
        queue_status = queue.get_queue_status()
        
        # Sanitize active job data to avoid massive song_ids arrays
        active_job = queue_status.get('active_job', None)
        if active_job and isinstance(active_job, dict):
            # Create a copy and remove/summarize large arrays
            sanitized_active_job = active_job.copy()
            metadata = sanitized_active_job.get('metadata', {})
            
            if 'song_ids' in metadata:
                # Replace massive song_ids array with just count and sample
                song_ids = metadata['song_ids']
                sanitized_metadata = metadata.copy()
                sanitized_metadata['song_ids_count'] = len(song_ids)
                sanitized_metadata['song_ids_sample'] = song_ids[:5] if song_ids else []
                # Remove the massive array
                del sanitized_metadata['song_ids']
                sanitized_active_job['metadata'] = sanitized_metadata
        else:
            sanitized_active_job = active_job
        
        return jsonify({
            'status': 'success',
            'queue': {
                'total_jobs': queue_status.get('total_jobs', 0),
                'pending_jobs': queue_status.get('pending_jobs', 0),
                'in_progress_jobs': queue_status.get('in_progress_jobs', 0),
                'completed_jobs': queue_status.get('completed_jobs', 0),
                'failed_jobs': queue_status.get('failed_jobs', 0),
                'priority_breakdown': queue_status.get('priority_counts', {}),
                'estimated_completion_minutes': queue_status.get('estimated_completion_time', 0),
                'active_job': sanitized_active_job
            }
        })
        
    except Exception as e:
        current_app.logger.error(f'Queue status error: {e}')
        return jsonify({
            'status': 'error',
            'error': str(e),
            'message': 'Failed to get queue status'
        }), 500


@bp.route('/worker/health')
@login_required
def get_worker_health():
    """Get worker health and status information"""
    try:
        worker_status = get_worker_status()
        
        return jsonify({
            'status': 'success',
            'worker': {
                'status': worker_status.get('status', 'unknown'),
                'uptime_seconds': worker_status.get('uptime_seconds', 0),
                'jobs_processed': worker_status.get('jobs_processed', 0),
                'jobs_failed': worker_status.get('jobs_failed', 0),
                'jobs_interrupted': worker_status.get('jobs_interrupted', 0),
                'last_heartbeat': worker_status.get('last_heartbeat', None),
                'current_job': worker_status.get('current_job', None)
            }
        })
        
    except Exception as e:
        current_app.logger.error(f'Worker health error: {e}')
        return jsonify({
            'status': 'error',
            'error': str(e),
            'message': 'Failed to get worker health'
        }), 500


@bp.route('/jobs/<job_id>/status')
@login_required
def get_job_status(job_id):
    """Get status of a specific analysis job with progress information"""
    try:
        from ..services.progress_tracker import get_progress_tracker
        
        queue = PriorityAnalysisQueue()
        job = queue.get_job(job_id)
        
        if not job:
            return jsonify({
                'status': 'error',
                'message': f'Job with ID {job_id} not found'
            }), 404
        
        # Get progress information if available
        tracker = get_progress_tracker()
        progress = tracker.get_job_progress(job_id)
        
        job_data = {
            'job_id': job.job_id,
            'status': job.status.name,
            'job_type': job.job_type.name,
            'priority': job.priority.name,
            'created_at': job.created_at,
            'started_at': getattr(job, 'started_at', None),
            'metadata': job.metadata
        }
        
        # Add progress information if available
        if progress:
            job_data['progress'] = progress.to_dict()
        else:
            # Fallback progress info from job metadata
            job_data['progress'] = getattr(job, 'progress', 0)
            job_data['estimated_completion_minutes'] = getattr(job, 'estimated_completion_time', 0)
        
        return jsonify({
            'status': 'success',
            'job': job_data
        })
        
    except Exception as e:
        current_app.logger.error(f'Job status error: {e}')
        return jsonify({
            'status': 'error',
            'error': str(e),
            'message': 'Failed to get job status'
        }), 500


@bp.route('/queue/health')
@login_required  
def get_queue_health():
    """Get queue system health check information"""
    try:
        queue = PriorityAnalysisQueue()
        health_status = queue.health_check()
        
        if not health_status.get('redis_connected', False):
            return jsonify({
                'status': 'error',
                'queue_health': health_status
            }), 503  # Service Unavailable
        
        return jsonify({
            'status': 'success',
            'queue_health': health_status
        })
        
    except Exception as e:
        current_app.logger.error(f'Queue health check error: {e}')
        return jsonify({
            'status': 'error',
            'queue_health': {
                'redis_connected': False,
                'queue_accessible': False,
                'error': str(e)
            }
        }), 503


# Progress Tracking Endpoints

@bp.route('/progress/<job_id>')
@login_required
def get_job_progress(job_id):
    """Get detailed progress for a specific job"""
    try:
        from ..services.progress_tracker import get_progress_tracker
        
        tracker = get_progress_tracker()
        progress = tracker.get_job_progress(job_id)
        
        if not progress:
            return jsonify({
                'success': False,
                'error': 'Job progress not found'
            }), 404
        
        return jsonify({
            'success': True,
            'progress': progress.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Error getting job progress for {job_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/progress')
@login_required
def get_all_progress():
    """Get progress for all active jobs"""
    try:
        from ..services.progress_tracker import get_progress_tracker
        
        tracker = get_progress_tracker()
        all_progress = tracker.get_all_active_progress()
        
        # Convert to serializable format
        progress_data = {}
        for job_id, progress in all_progress.items():
            progress_data[job_id] = progress.to_dict()
        
        return jsonify({
            'success': True,
            'active_jobs': progress_data,
            'total_active': len(progress_data)
        })
        
    except Exception as e:
        logger.error(f"Error getting all progress: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/progress/cleanup', methods=['POST'])
@admin_required
def cleanup_stale_progress():
    """Clean up stale progress tracking jobs (admin only)"""
    try:
        from ..services.progress_tracker import get_progress_tracker
        
        tracker = get_progress_tracker()
        max_age_hours = request.json.get('max_age_hours', 24) if request.json else 24
        
        tracker.cleanup_stale_jobs(max_age_hours=max_age_hours)
        
        return jsonify({
            'success': True,
            'message': f'Cleaned up jobs older than {max_age_hours} hours'
        })
        
    except Exception as e:
        logger.error(f"Error cleaning up stale progress: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@bp.route('/admin/update-playlist-scores', methods=['POST'])
@login_required  
def admin_update_playlist_scores():
    """Admin endpoint to manually update all playlist scores"""
    try:
        if not current_user.is_admin:
            return jsonify({
                'success': False,
                'error': 'Admin access required'
            }), 403
            
        from app.services.playlist_scoring_service import PlaylistScoringService
        
        scoring_service = PlaylistScoringService()
        result = scoring_service.update_all_playlist_scores()
        
        return jsonify({
            'success': True,
            'message': f'Updated scores for {result["updated_count"]} playlists',
            'updated_count': result['updated_count'],
            'total_playlists': result['total_playlists'],
            'errors': result.get('errors', [])
        })
        
    except Exception as e:
        current_app.logger.error(f'Admin playlist score update error: {e}')
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def get_background_analysis_progress():
    """Get accurate background analysis progress for the active job"""
    try:
        from app.services.priority_analysis_queue import PriorityAnalysisQueue
        
        queue = PriorityAnalysisQueue()
        active_job = queue.get_active_job()
        
        if not active_job:
            return {
                'active': False,
                'message': 'No active background analysis job'
            }
        
        job_data = active_job.to_dict()
        
        # Only process background analysis jobs
        if job_data.get('job_type') != 'background_analysis':
            return {
                'active': False,
                'message': 'Active job is not a background analysis'
            }
        
        user_id = job_data.get('user_id')
        metadata = job_data.get('metadata', {})
        total_songs = metadata.get('total_songs', 0)
        user_name = metadata.get('user_name', 'Unknown User')
        
        if not user_id or not total_songs:
            return {
                'active': False,
                'message': 'Invalid background analysis job data'
            }
        
        # Get song IDs from metadata for accurate filtering
        song_ids = metadata.get('song_ids', [])
        
        if song_ids:
            # Count analyses for specific songs in the job
            completed_analyses = AnalysisResult.query.filter(
                AnalysisResult.song_id.in_(song_ids),
                AnalysisResult.status == 'completed'
            ).count()
            
            failed_analyses = AnalysisResult.query.filter(
                AnalysisResult.song_id.in_(song_ids),
                AnalysisResult.status == 'failed'
            ).count()
            
            in_progress_analyses = AnalysisResult.query.filter(
                AnalysisResult.song_id.in_(song_ids),
                AnalysisResult.status == 'in_progress'
            ).count()
        else:
            # Fallback: count all analyses for user
            completed_analyses = AnalysisResult.query.filter(
                AnalysisResult.user_id == user_id,
                AnalysisResult.status == 'completed'
            ).count()
            
            failed_analyses = AnalysisResult.query.filter(
                AnalysisResult.user_id == user_id,
                AnalysisResult.status == 'failed'
            ).count()
            
            in_progress_analyses = AnalysisResult.query.filter(
                AnalysisResult.user_id == user_id,
                AnalysisResult.status == 'in_progress'
            ).count()
        
        # Calculate progress
        total_processed = completed_analyses + failed_analyses
        progress_percentage = (total_processed / total_songs * 100) if total_songs > 0 else 0
        
        # Calculate ETA based on recent processing rate
        remaining_songs = total_songs - total_processed
        eta_data = calculate_processing_rate_eta(remaining_songs)
        
        return {
            'active': True,
            'progress_percentage': round(progress_percentage, 1),
            'total_songs': total_songs,
            'completed_analyses': completed_analyses,
            'failed_analyses': failed_analyses,
            'in_progress_analyses': in_progress_analyses,
            'remaining_songs': remaining_songs,
            'user_id': user_id,
            'user_name': user_name,
            'job_id': job_data.get('job_id'),
            **eta_data
        }
        
    except Exception as e:
        current_app.logger.error(f'Background analysis progress error: {e}')
        return {
            'active': False,
            'error': str(e),
            'message': 'Failed to get background analysis progress'
        }


def calculate_processing_rate_eta(remaining_songs):
    """Calculate ETA based on actual recent processing rate"""
    try:
        from datetime import datetime, timedelta
        
        # Look at completions in the last 10 minutes for rate calculation
        cutoff_time = datetime.utcnow() - timedelta(minutes=10)
        
        recent_completions = AnalysisResult.query.filter(
            AnalysisResult.status == 'completed',
            AnalysisResult.updated_at >= cutoff_time
        ).order_by(AnalysisResult.updated_at.desc()).limit(100).all()
        
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
            'analyses_per_hour': round(analyses_per_hour, 1),
            'estimated_hours': round(estimated_hours, 1),
            'estimated_minutes': estimated_minutes,
            'sample_period_minutes': 10,
            'recent_completions_count': len(recent_completions)
        }
        
    except Exception as e:
        current_app.logger.error(f'ETA calculation error: {e}')
        return {
            'analyses_per_hour': 30,  # Conservative fallback
            'estimated_hours': remaining_songs / 30 if remaining_songs > 0 else 0,
            'estimated_minutes': int((remaining_songs / 30 * 60)) if remaining_songs > 0 else 0,
            'sample_period_minutes': 10,
            'recent_completions_count': 0,
            'error': str(e)
        }


@bp.route('/background-analysis/status')
@login_required
def get_background_analysis_status():
    """API endpoint for accurate background analysis progress"""
    try:
        progress_data = get_background_analysis_progress()
        
        return jsonify({
            'status': 'success',
            'success': True,
            **progress_data
        })
        
    except Exception as e:
        current_app.logger.error(f'Background analysis status API error: {e}')
        return jsonify({
            'status': 'error',
            'success': False,
            'error': str(e),
            'message': 'Failed to get background analysis status'
        }), 500


@bp.route('/analysis/processing-rate')
def get_processing_rate():
    """API endpoint for current processing rate information"""
    try:
        # Calculate rate for informational purposes
        eta_data = calculate_processing_rate_eta(0)  # 0 remaining for rate calc only
        
        return jsonify({
            'status': 'success',
            'success': True,
            'analyses_per_minute': round(eta_data['analyses_per_hour'] / 60, 2),
            'analyses_per_hour': eta_data['analyses_per_hour'],
            'sample_period_minutes': eta_data['sample_period_minutes'],
            'recent_completions_count': eta_data['recent_completions_count']
        })
        
    except Exception as e:
        current_app.logger.error(f'Processing rate API error: {e}')
        return jsonify({
            'status': 'error',
            'success': False,
            'error': str(e),
            'message': 'Failed to get processing rate'
        }), 500 

@bp.route('/background-analysis/public-status')
def get_background_analysis_public_status():
    """Public endpoint for background analysis detection (no auth required)"""
    try:
        from app.services.priority_analysis_queue import PriorityAnalysisQueue
        
        queue = PriorityAnalysisQueue()
        active_job = queue.get_active_job()
        
        if not active_job:
            return jsonify({
                'status': 'success',
                'active': False,
                'message': 'No active background analysis'
            })
        
        job_data = active_job.to_dict()
        
        # Only process background analysis jobs
        if job_data.get('job_type') != 'background_analysis':
            return jsonify({
                'status': 'success',
                'active': False,
                'message': 'Active job is not background analysis'
            })
        
        # **SIMPLE VALIDATION**: Check if workers are actually processing jobs
        queue_length = queue.redis.llen('rq:queue:analysis') or 0
        if queue_length == 0:
            # No jobs in queue - check if analysis completed or stalled
            completed_recently = db.session.execute(
                text("SELECT COUNT(*) FROM analysis_results WHERE created_at > NOW() - INTERVAL '10 minutes'")
            ).scalar()
            
            if completed_recently == 0:
                # No jobs in queue AND no recent completions = stalled job
                current_app.logger.warning("🧹 Detected stale background analysis tracking - cleaning up")
                queue.redis.delete('analysis_active')
                return jsonify({
                    'status': 'success',
                    'active': False,
                    'message': 'Background analysis job was stale - cleaned up'
                })
        
        # Return basic progress information without sensitive data
        metadata = job_data.get('metadata', {})
        user_name = metadata.get('user_name', 'Unknown User')
        user_id = job_data.get('user_id')
        
        # Get REAL-TIME counts from database, not stale metadata
        from app.models.models import AnalysisResult, Song, PlaylistSong, Playlist
        
        if user_id:
            # Get accurate user-specific counts
            total_songs = db.session.query(Song.id).join(PlaylistSong).join(Playlist).filter(
                Playlist.owner_id == user_id
            ).distinct().count()
            
            completed_analyses = db.session.query(Song.id).join(AnalysisResult).join(PlaylistSong).join(Playlist).filter(
                Playlist.owner_id == user_id,
                AnalysisResult.status == 'completed'
            ).distinct().count()
        else:
            # Fallback to metadata if no user_id available
            total_songs = metadata.get('total_songs', 0)
            completed_analyses = AnalysisResult.query.filter(
                AnalysisResult.status == 'completed'
            ).count()
        
        # Calculate ETA based on remaining songs
        remaining_songs = max(0, total_songs - completed_analyses)
        eta_data = calculate_processing_rate_eta(remaining_songs)
        
        return jsonify({
            'status': 'success',
            'active': True,
            'job_id': job_data.get('job_id'),
            'total_songs': total_songs,
            'user_name': user_name,
            'recent_completed': completed_analyses,  # Now using ALL completed analyses, not just recent
            'processing_rate': eta_data['analyses_per_hour'],
            'estimated_hours': eta_data['estimated_hours'],
            'message': f'Background analysis active for {user_name}'
        })
        
    except Exception as e:
        current_app.logger.error(f'Public background analysis status error: {e}')
        return jsonify({
            'status': 'error',
            'active': False,
            'error': str(e),
            'message': 'Failed to get background analysis status'
        }), 500


@bp.route('/api/test/semantic-detection', methods=['POST'])
@login_required
def test_semantic_detection():
    """Test endpoint for enhanced semantic theme detection."""
    try:
        data = request.get_json()
        title = data.get('title', 'Test Song')
        artist = data.get('artist', 'Test Artist') 
        lyrics = data.get('lyrics', '')
        
        if not lyrics:
            return jsonify({
                'success': False,
                'error': 'Lyrics are required for testing'
            }), 400
        
        # Test the enhanced analysis
        from app.services.simplified_christian_analysis_service import SimplifiedChristianAnalysisService
        analysis_service = SimplifiedChristianAnalysisService()
        
        result = analysis_service.analyze_song(title, artist, lyrics)
        
        # Get precision metrics
        precision_report = analysis_service.get_analysis_precision_report()
        
        return jsonify({
            'success': True,
            'analysis': {
                'score': result.scoring_results['final_score'],
                'quality_level': result.scoring_results['quality_level'],
                'explanation': result.scoring_results['explanation'],
                'themes_detected': len(result.biblical_analysis['themes']),
                'themes': [
                    theme.get('theme', str(theme)) if isinstance(theme, dict) else str(theme)
                    for theme in result.biblical_analysis['themes']
                ],
                'concerns': len(result.content_analysis.get('detailed_concerns', [])),
                'scripture_references': len(result.biblical_analysis.get('supporting_scripture', []))
            },
            'precision_metrics': precision_report,
            'message': 'Enhanced semantic detection active'
        })
        
    except Exception as e:
        logger.error(f"Error in semantic detection test: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500