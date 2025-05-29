"""
Analysis Blueprint Routes - Analysis operations, status checking, and data retrieval.

This file contains the routes for:
- Song analysis status checking
- Playlist analysis status checking  
- Individual song analysis operations
- Playlist batch analysis operations
- Analysis data retrieval endpoints
- Administrative reanalysis operations
"""

import uuid
from datetime import datetime
from flask import render_template, flash, redirect, url_for, request, current_app, jsonify, session, abort, has_request_context
from flask_login import login_required, current_user as flask_login_current_user

# Import the blueprint
from . import analysis_bp

# Import required modules
from app import db
from app.models import User, Song, AnalysisResult, PlaylistSong, Playlist
from app.auth.decorators import spotify_token_required
from app.services.unified_analysis_service import UnifiedAnalysisService
from app.utils.database import get_by_id, get_by_filter
from app.utils.cache import cache

@analysis_bp.route('/api/songs/<int:song_id>/analysis-status', methods=['GET'])
@login_required
def get_song_analysis_status(song_id):
    """
    Endpoint to check the status of a song analysis.
    
    Query Parameters:
        task_id: Optional task ID to check job status
    """
    try:
        # Get the song with proper ownership check
        song = get_by_id(Song, song_id)
        if not song:
            return jsonify({
                'success': False,
                'error': 'song_not_found',
                'message': 'Song not found'
            }), 404
            
        # Check if the song belongs to a playlist owned by the current user
        user_playlist_ids = [p.id for p in flask_login_current_user.playlists]
        song_playlist_ids = [assoc.playlist_id for assoc in song.playlist_associations]
        
        if not song_playlist_ids or not any(pid in user_playlist_ids for pid in song_playlist_ids):
            return jsonify({
                'success': False,
                'error': 'unauthorized',
                'message': 'You do not have permission to view this song'
            }), 403
            
        task_id = request.args.get('task_id')
        if task_id:
            job = current_app.task_queue.fetch_job(task_id)
            if job:
                if job.is_failed:
                    return jsonify({
                        'success': False,
                        'error': 'analysis_failed',
                        'message': f'Analysis failed: {str(job.exc_info)}',
                        'song_id': song_id
                    })
                elif job.is_finished:
                    # Refresh the song to get updated analysis
                    db.session.refresh(song)
                    # Include both christian_ and non-christian fields for backward compatibility
                    return jsonify({
                        'success': True,
                        'completed': True,
                        'song_id': song_id,
                        'analysis': {
                            'score': song.score,
                            'christian_score': song.score,  # Add christian_ prefixed fields
                            'concern_level': song.concern_level,
                            'christian_concern_level': song.concern_level,  # Add christian_ prefixed fields
                            'updated_at': song.updated_at.isoformat() if song.updated_at else None
                        }
                    })
                else:
                    # Job is still running
                    return jsonify({
                        'success': True,
                        'in_progress': True,
                        'message': 'Analysis in progress...',
                        'song_id': song_id
                    })
        
        # If no task_id or job not found, return current song analysis status
        if song.score is not None:
            # Include both christian_ and non-christian fields for backward compatibility
            analysis_data = {
                'score': song.score,
                'christian_score': song.score,  # Add christian_ prefixed fields
                'concern_level': song.concern_level,
                'christian_concern_level': song.concern_level,  # Add christian_ prefixed fields
                'updated_at': song.updated_at.isoformat() if song.updated_at else None
            }
        else:
            analysis_data = None
            
        return jsonify({
            'success': True,
            'song_id': song_id,
            'has_analysis': song.score is not None,
            'analysis': analysis_data
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in get_song_analysis_status: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'status_check_error',
            'message': f'Failed to check analysis status: {str(e)}'
        }), 500

@analysis_bp.route('/api/playlists/<string:playlist_id>/analysis-status/', methods=['GET'])
@analysis_bp.route('/api/playlists/<string:playlist_id>/analysis-status', methods=['GET'])  # For backward compatibility
@login_required
def get_analysis_status(playlist_id):
    """
    Endpoint to check the status of playlist or song analysis.
    Returns detailed information about the analysis progress.
    
    Query Parameters:
        task_id: Optional task ID to check job status
        song_id: Optional song ID to check status for a specific song
    """
    try:
        if not playlist_id:
            current_app.logger.error("Missing playlist_id in get_analysis_status")
            return jsonify({
                'success': False,
                'error': 'missing_playlist_id',
                'message': 'Playlist ID is required'
            }), 400
            
        task_id = request.args.get('task_id')
        song_id = request.args.get('song_id')
        current_app.logger.info(f"Checking analysis status for playlist {playlist_id}, task_id: {task_id}, song_id: {song_id}")
        
        # If checking status for a specific song
        if song_id:
            song = get_by_id(Song, song_id)
            if not song:
                abort(404)
                
            # If song has a score, return it
            if song.score is not None:
                return jsonify({
                    'success': True,
                    'completed': True,
                    'song_id': song_id,
                    'analysis': {
                        'score': song.score,
                        'concern_level': song.concern_level,
                        'updated_at': song.updated_at.isoformat() if song.updated_at else None
                    }
                })
            
            # If no score but we have a task_id, check job status
            if task_id:
                job = current_app.task_queue.fetch_job(task_id)
                if job:
                    if job.is_failed:
                        error_msg = f'Analysis failed: {str(job.exc_info)}'
                        current_app.logger.error(f"Job {task_id} failed: {error_msg}")
                        return jsonify({
                            'success': False,
                            'error': 'analysis_failed',
                            'message': error_msg,
                            'song_id': song_id
                        }), 500
                    elif job.is_finished:
                        # Refresh the song to get updated analysis
                        db.session.refresh(song)
                        if song.score is not None:
                            return jsonify({
                                'success': True,
                                'completed': True,
                                'song_id': song_id,
                                'analysis': {
                                    'score': song.score,
                                    'concern_level': song.concern_level,
                                    'updated_at': song.updated_at.isoformat() if song.updated_at else None
                                }
                            })
                    
                    # Job is still running
                    return jsonify({
                        'success': True,
                        'in_progress': True,
                        'message': 'Analysis in progress...',
                        'song_id': song_id
                    })
                
            # No task_id or job not found
            return jsonify({
                'success': True,
                'song_id': song_id,
                'has_analysis': song.score is not None,
                'analysis': {
                    'score': song.score,
                    'concern_level': song.concern_level,
                    'updated_at': song.updated_at.isoformat() if song.updated_at else None
                } if song.score is not None else None
            })
        
        # If no song_id but we have a task_id, check job status for the playlist
        if task_id:
            try:
                job = current_app.task_queue.fetch_job(task_id)
                if job:
                    if job.is_failed:
                        error_msg = f'Analysis failed: {str(job.exc_info)}'
                        current_app.logger.error(f"Job {task_id} failed: {error_msg}")
                        return jsonify({
                            'success': False,
                            'error': 'analysis_failed',
                            'message': error_msg,
                            'playlist_id': playlist_id
                        }), 500
                    elif job.is_finished:
                        return jsonify({
                            'success': True,
                            'completed': True,
                            'playlist_id': playlist_id,
                            'message': 'Analysis completed successfully'
                        })
                    else:
                        # Job is still running
                        return jsonify({
                            'success': True,
                            'in_progress': True,
                            'message': 'Analysis in progress...',
                            'playlist_id': playlist_id
                        })
            except Exception as e:
                current_app.logger.error(f"Error checking job status: {e}")
        
        # Return general playlist analysis status
        return jsonify({
            'success': True,
            'playlist_id': playlist_id,
            'message': 'Analysis status checked'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in get_analysis_status: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'status_check_error',
            'message': f'Failed to check analysis status: {str(e)}'
        }), 500

@analysis_bp.route('/api/songs/<int:song_id>/analyze/', methods=['POST'])
@analysis_bp.route('/api/songs/<int:song_id>/analyze', methods=['POST'])  # For backward compatibility
@login_required
@spotify_token_required
def analyze_song_route(song_id):
    """Route handler for analyzing/re-analyzing a single song."""
    from app.utils.error_handling import (
        safe_analysis_operation, validate_analysis_request, 
        UnifiedAnalysisServiceError, DatabaseError
    )
    
    def _analyze_song_operation():
        """Internal function to perform the song analysis operation."""
        # Validate request parameters
        context = validate_analysis_request(song_id=song_id, user_id=flask_login_current_user.id)
        current_app.logger.info(f"Starting analysis for song {song_id}")
        
        # Get the song
        song = get_by_id(Song, song_id)
        if not song:
            from flask import abort
            abort(404)
        current_app.logger.info(f"Found song: {song.title} by {song.artist}")
        
        # Enqueue the analysis task using unified service
        try:
            analysis_service = UnifiedAnalysisService()
            job = analysis_service.enqueue_analysis_job(song_id, user_id=flask_login_current_user.id, priority='high')
            
            if job:
                current_app.logger.info(f"Song analysis task enqueued for song {song_id} with job ID: {job.id}")
                return jsonify({
                    'success': True,
                    'message': f'Analysis started for "{song.title}"',
                    'job_id': job.id,
                    'song_id': song_id
                })
            else:
                raise UnifiedAnalysisServiceError("Failed to enqueue analysis task")
                
        except Exception as e:
            raise UnifiedAnalysisServiceError(f"Analysis service error: {str(e)}")
    
    # Use the safe operation wrapper
    context = {'song_id': song_id, 'user_id': flask_login_current_user.id}
    return safe_analysis_operation(
        operation_func=_analyze_song_operation,
        operation_name="analyze_song",
        context=context
    )

@analysis_bp.route('/api/songs/<int:song_id>/reanalyze/', methods=['POST'])
@analysis_bp.route('/api/songs/<int:song_id>/reanalyze', methods=['POST'])  # For backward compatibility
@login_required
@spotify_token_required  
def reanalyze_song_route(song_id):
    """Route handler for re-analyzing a single song (alias for analyze_song_route)."""
    return analyze_song_route(song_id)

@analysis_bp.route('/api/playlists/<string:playlist_id>/analyze-unanalyzed/', methods=['POST'])
@analysis_bp.route('/api/playlists/<string:playlist_id>/analyze-unanalyzed', methods=['POST'])  # For backward compatibility
@login_required
@spotify_token_required
def analyze_unanalyzed_songs_route(playlist_id):
    """Route handler for analyzing unanalyzed songs in a playlist."""
    from app.utils.error_handling import (
        safe_analysis_operation, validate_analysis_request, 
        AnalysisError
    )
    
    def _analyze_unanalyzed_operation():
        """Internal function to perform the unanalyzed songs analysis operation."""
        # Validate request parameters
        context = validate_analysis_request(playlist_id=playlist_id, user_id=flask_login_current_user.id)
        current_app.logger.info(f"Starting analysis for unanalyzed songs in playlist {playlist_id}")
        
        # Get the user ID from the current user and pass it explicitly
        user_id = flask_login_current_user.id
        return analyze_unanalyzed_songs(playlist_id, user_id=user_id)
    
    # Use the safe operation wrapper
    context = {'playlist_id': playlist_id, 'user_id': flask_login_current_user.id}
    return safe_analysis_operation(
        operation_func=_analyze_unanalyzed_operation,
        operation_name="analyze_unanalyzed_songs",
        context=context,
        error_redirect=url_for('playlist.playlist_detail', playlist_id=playlist_id)
    )

@analysis_bp.route('/api/playlists/<string:playlist_id>/reanalyze-all/', methods=['POST'])
@analysis_bp.route('/api/playlists/<string:playlist_id>/reanalyze-all', methods=['POST'])  # For backward compatibility
@login_required
@spotify_token_required
def reanalyze_all_songs_route(playlist_id):
    """Route handler for re-analyzing ALL songs in a playlist (not just unanalyzed ones)."""
    from app.utils.error_handling import (
        safe_analysis_operation, validate_analysis_request, 
        AnalysisError
    )
    
    def _reanalyze_all_operation():
        """Internal function to perform the reanalyze all songs operation."""
        # Validate request parameters
        context = validate_analysis_request(playlist_id=playlist_id, user_id=flask_login_current_user.id)
        current_app.logger.info(f"Starting re-analysis for ALL songs in playlist {playlist_id}")
        
        # Get the user ID from the current user and pass it explicitly
        user_id = flask_login_current_user.id
        return reanalyze_all_songs(playlist_id, user_id=user_id)
    
    # Use the safe operation wrapper
    context = {'playlist_id': playlist_id, 'user_id': flask_login_current_user.id}
    return safe_analysis_operation(
        operation_func=_reanalyze_all_operation,
        operation_name="reanalyze_all_songs",
        context=context,
        error_redirect=url_for('playlist.playlist_detail', playlist_id=playlist_id)
    )

@analysis_bp.route('/api/analysis/playlist/<string:playlist_id>')
@login_required
def playlist_analysis_data(playlist_id):
    """API endpoint for lazy loading playlist analysis data."""
    try:
        user_id = flask_login_current_user.id
        
        # Get cached data if available
        cache_key = f"playlist_analysis:{user_id}:{playlist_id}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return jsonify(cached_data)
        
        # Get playlist data from database
        playlist = Playlist.query.filter_by(spotify_id=playlist_id, owner_id=user_id).first()
        if not playlist:
            abort(404)
        
        # Get songs in the playlist
        songs = db.session.query(Song).join(
            PlaylistSong, Song.id == PlaylistSong.song_id
        ).filter(PlaylistSong.playlist_id == playlist.id).all()
        
        # Format data for frontend
        analysis_data = {
            'songs': [],
            'summary': {
                'total_songs': len(songs),
                'analyzed_songs': 0,
                'pending_analysis': 0,
                'average_score': 0
            }
        }
        
        total_score = 0
        analyzed_count = 0
        
        for song in songs:
            result = AnalysisResult.query.filter_by(song_id=song.id, status='completed').first()
            song_data = {
                'id': song.id,
                'title': song.title,
                'artist': song.artist,
                'album': song.album,
                'status': 'pending'
            }
            
            if result:
                song_data['status'] = 'analyzed'
                song_data['score'] = result.score
                song_data['details'] = {
                    'concern_level': result.concern_level,
                    'explanation': result.explanation
                }
                total_score += result.score
                analyzed_count += 1
            else:
                analysis_data['summary']['pending_analysis'] += 1
            
            analysis_data['songs'].append(song_data)
        
        if analyzed_count > 0:
            analysis_data['summary']['average_score'] = round(total_score / analyzed_count, 1)
        
        analysis_data['summary']['analyzed_songs'] = analyzed_count
        
        # Cache the result
        cache.set(cache_key, analysis_data, timeout=300)  # 5 minutes cache
        
        return jsonify(analysis_data)
        
    except Exception as e:
        current_app.logger.error(f"Error getting playlist analysis data for {playlist_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@analysis_bp.route('/api/analysis/song/<int:song_id>')
@login_required
def song_analysis_data(song_id):
    """API endpoint for lazy loading individual song analysis data."""
    try:
        user_id = flask_login_current_user.id
        
        # Get cached data if available
        cache_key = f"song_analysis:{user_id}:{song_id}"
        cached_data = cache.get(cache_key)
        if cached_data:
            return jsonify(cached_data)
        
        # Get song data from database
        song = Song.query.filter_by(id=song_id).first()
        if not song:
            abort(404)
        
        # Verify user has access to this song
        playlist_song = PlaylistSong.query.filter_by(song_id=song.id).first()
        if not playlist_song:
            return jsonify({'error': 'Unauthorized'}), 403
            
        playlist = Playlist.query.filter_by(id=playlist_song.playlist_id, owner_id=user_id).first()
        if not playlist:
            return jsonify({'error': 'Unauthorized'}), 403
        
        result = AnalysisResult.query.filter_by(song_id=song.id, status='completed').first()
        
        if result:
            analysis_data = {
                'id': song.id,
                'title': song.title,
                'artist': song.artist,
                'album': song.album,
                'status': 'analyzed',
                'score': result.score,
                'details': {
                    'concern_level': result.concern_level,
                    'explanation': result.explanation
                }
            }
        else:
            analysis_data = {
                'id': song.id,
                'title': song.title,
                'artist': song.artist,
                'album': song.album,
                'status': 'pending'
            }
        
        # Cache the result
        cache.set(cache_key, analysis_data, timeout=300)  # 5 minutes cache
        
        return jsonify(analysis_data)
        
    except Exception as e:
        current_app.logger.error(f"Error getting song analysis data for {song_id}: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@analysis_bp.route('/comprehensive_reanalyze_all_user_songs/<int:user_id>')
@login_required
def comprehensive_reanalyze_all_user_songs(user_id=None):
    """
    Comprehensive re-analysis of all user songs using the unified analysis service.
    This replaces all fragmented analysis approaches with one comprehensive system.
    """
    from app.services.unified_analysis_service import unified_analysis_service
    
    try:
        # Verify user exists and has permission
        if user_id is None:
            user_id = flask_login_current_user.id
        
        if user_id != flask_login_current_user.id and not getattr(flask_login_current_user, 'is_admin', False):
            flash('Access denied: You can only re-analyze your own songs.', 'error')
            return redirect(url_for('core.dashboard'))
        
        user = db.session.get(User, user_id)
        if not user:
            flash(f'User with ID {user_id} not found.', 'error')
            return redirect(url_for('core.dashboard'))
        
        current_app.logger.info(f"Starting comprehensive re-analysis for user {user_id} ({user.email})")
        
        # Use the unified analysis service for comprehensive biblical analysis
        result = unified_analysis_service.analyze_user_songs(
            user_id=user_id,
            force_reanalysis=True,  # Re-analyze everything
            max_songs=None  # Analyze all songs
        )
        
        if result['status'] == 'started':
            flash(f"✅ Comprehensive biblical re-analysis started! "
                  f"{result['songs_analyzed']} songs queued for analysis. "
                  f"Check the dashboard for progress.", 'success')
            current_app.logger.info(f"Comprehensive re-analysis queued: {result}")
        elif result['status'] == 'complete':
            flash('All songs are already analyzed with comprehensive biblical analysis.', 'info')
        else:
            flash(f"Error starting comprehensive re-analysis: {result['message']}", 'error')
            current_app.logger.error(f"Comprehensive re-analysis failed: {result}")
        
        return redirect(url_for('core.dashboard'))
        
    except Exception as e:
        current_app.logger.error(f"Error in comprehensive re-analysis for user {user_id}: {e}")
        flash(f'Error starting comprehensive re-analysis: {str(e)}', 'error')
        return redirect(url_for('core.dashboard'))

# Helper functions for the analysis operations
def analyze_unanalyzed_songs(playlist_id, user_id=None):
    """Analyze only the unanalyzed songs in a playlist.
    
    Args:
        playlist_id (str): The Spotify ID of the playlist to analyze
        user_id (int, optional): The ID of the user who owns the playlist. 
                              Required when called from a background job.
    """
    current_app.logger.info(f"analyze_unanalyzed_songs called for playlist_id: {playlist_id}, user_id: {user_id}")
    
    try:
        # Get the user ID from the current user if not provided
        if user_id is None:
            if not has_request_context() or not hasattr(flask_login_current_user, 'id') or not flask_login_current_user.is_authenticated:
                current_app.logger.error("No user_id provided and no authenticated current_user available")
                if has_request_context() and request and hasattr(request, 'is_json') and request.is_json:
                    return jsonify({"error": "User authentication required"}), 401
                return "User authentication required", 401
            user_id = flask_login_current_user.id
            
        # Get the playlist from the database
        playlist = Playlist.query.filter_by(spotify_id=playlist_id, owner_id=user_id).first()
        if not playlist:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"success": False, "message": "Playlist not found or access denied"}), 404
            flash("Playlist not found or access denied", 'error')
            return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))
            
        # Get all songs in the playlist that don't have analysis results
        unanalyzed_songs = Song.query.join(
            PlaylistSong, 
            Song.id == PlaylistSong.song_id
        ).filter(
            PlaylistSong.playlist_id == playlist.id,
            ~Song.analysis_results.any()
        ).all()
        
        total_songs = len(unanalyzed_songs)
        analyzed_count = 0
        
        if total_songs == 0:
            response_data = {
                "success": True, 
                "message": "No unanalyzed songs found in the playlist.",
                "analyzed_count": 0,
                "total_songs": 0
            }
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify(response_data)
            flash(response_data["message"], 'info')
            return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))
        
        # Generate a unique task ID for this batch of analyses
        batch_id = str(uuid.uuid4())
        current_app.logger.info(f"Starting batch analysis with ID: {batch_id}")
        
        # Process each unanalyzed song
        for i, song in enumerate(unanalyzed_songs, 1):
            current_app.logger.info(f"Starting analysis for song {song.id} for user {user_id}")
            
            try:
                # Call the unified analysis service using the background task
                analysis_service = UnifiedAnalysisService()
                job = analysis_service.enqueue_analysis_job(song.id, user_id=user_id, priority='low')
                if job:
                    # The analysis is happening in the background
                    analyzed_count += 1
                    job_id = job.get_id() if hasattr(job, 'get_id') else str(job.id) if hasattr(job, 'id') else 'unknown'
                    current_app.logger.info(f"Started analysis job {job_id} for song {song.id}")
                    
                    # Update the song's last_analyzed timestamp
                    song.last_analyzed = datetime.utcnow()
                    db.session.add(song)
                    
                    # Commit every 5 songs to avoid long transactions
                    if i % 5 == 0 or i == len(unanalyzed_songs):
                        db.session.commit()
                        current_app.logger.debug(f"Committed database changes after song {i}")
                else:
                    current_app.logger.warning(f"Analysis job for song {song.id} was not created")
                    
            except Exception as e:
                current_app.logger.error(f"Error starting analysis for song {song.id}: {e}")
                continue
        
        # Final commit
        db.session.commit()
        
        response_data = {
            "success": True,
            "message": f"Analysis started for {analyzed_count} unanalyzed songs.",
            "analyzed_count": analyzed_count,
            "total_songs": total_songs,
            "batch_id": batch_id
        }
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(response_data)
            
        flash(response_data["message"], 'success')
        return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))
        
    except Exception as e:
        current_app.logger.error(f"Error in analyze_unanalyzed_songs: {e}")
        db.session.rollback()
        
        error_response = {
            "success": False,
            "message": f"Error starting analysis: {str(e)}"
        }
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(error_response), 500
            
        flash(error_response["message"], 'error')
        return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))

def reanalyze_all_songs(playlist_id, user_id=None):
    """Re-analyze ALL songs in a playlist (not just unanalyzed ones).
    
    Args:
        playlist_id (str): The Spotify ID of the playlist to analyze
        user_id (int, optional): The ID of the user who owns the playlist.
    """
    current_app.logger.info(f"reanalyze_all_songs called for playlist_id: {playlist_id}, user_id: {user_id}")
    
    try:
        # Get the user ID from the current user if not provided
        if user_id is None:
            if not has_request_context() or not hasattr(flask_login_current_user, 'id') or not flask_login_current_user.is_authenticated:
                current_app.logger.error("No user_id provided and no authenticated current_user available")
                if has_request_context() and request and hasattr(request, 'is_json') and request.is_json:
                    return jsonify({"error": "User authentication required"}), 401
                return "User authentication required", 401
            user_id = flask_login_current_user.id
            
        # Get the playlist from the database
        playlist = Playlist.query.filter_by(spotify_id=playlist_id, owner_id=user_id).first()
        if not playlist:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({"success": False, "message": "Playlist not found or access denied"}), 404
            flash("Playlist not found or access denied", 'error')
            return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))
            
        # Get ALL songs in the playlist
        all_songs = Song.query.join(
            PlaylistSong, 
            Song.id == PlaylistSong.song_id
        ).filter(PlaylistSong.playlist_id == playlist.id).all()
        
        total_songs = len(all_songs)
        analyzed_count = 0
        
        if total_songs == 0:
            response_data = {
                "success": True, 
                "message": "No songs found in the playlist.",
                "analyzed_count": 0,
                "total_songs": 0
            }
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify(response_data)
            flash(response_data["message"], 'info')
            return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))
        
        # Generate a unique task ID for this batch of analyses
        batch_id = str(uuid.uuid4())
        current_app.logger.info(f"Starting batch re-analysis with ID: {batch_id}")
        
        # Process each song for re-analysis
        for i, song in enumerate(all_songs, 1):
            current_app.logger.info(f"Starting re-analysis for song {song.id} for user {user_id}")
            
            try:
                # Call the unified analysis service using the background task
                analysis_service = UnifiedAnalysisService()
                job = analysis_service.enqueue_analysis_job(song.id, user_id=user_id, priority='low', force_reanalysis=True)
                if job:
                    analyzed_count += 1
                    job_id = job.get_id() if hasattr(job, 'get_id') else str(job.id) if hasattr(job, 'id') else 'unknown'
                    current_app.logger.info(f"Started re-analysis job {job_id} for song {song.id}")
                    
                    # Update the song's last_analyzed timestamp
                    song.last_analyzed = datetime.utcnow()
                    db.session.add(song)
                    
                    # Commit every 5 songs to avoid long transactions
                    if i % 5 == 0 or i == len(all_songs):
                        db.session.commit()
                        current_app.logger.debug(f"Committed database changes after song {i}")
                else:
                    current_app.logger.warning(f"Re-analysis job for song {song.id} was not created")
                    
            except Exception as e:
                current_app.logger.error(f"Error starting re-analysis for song {song.id}: {e}")
                continue
        
        # Final commit
        db.session.commit()
        
        response_data = {
            "success": True,
            "message": f"Re-analysis started for {analyzed_count} songs.",
            "analyzed_count": analyzed_count,
            "total_songs": total_songs,
            "batch_id": batch_id
        }
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(response_data)
            
        flash(response_data["message"], 'success')
        return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))
        
    except Exception as e:
        current_app.logger.error(f"Error in reanalyze_all_songs: {e}")
        db.session.rollback()
        
        error_response = {
            "success": False,
            "message": f"Error starting re-analysis: {str(e)}"
        }
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify(error_response), 500
            
        flash(error_response["message"], 'error')
        return redirect(url_for('playlist.playlist_detail', playlist_id=playlist_id))
