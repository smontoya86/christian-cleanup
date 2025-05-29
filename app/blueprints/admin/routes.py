"""
Admin Blueprint Routes - Administrative functions and operations.

This file contains the routes for:
- Administrative playlist resyncing
- Administrative song reanalysis  
- Admin status monitoring
- Analysis administration endpoints
"""

from flask import render_template, flash, redirect, url_for, request, current_app, jsonify
from flask_login import login_required, current_user as flask_login_current_user

# Import the blueprint
from . import admin_bp

# Import required modules
from app import db
from app.models import User, Song, AnalysisResult, PlaylistSong, Playlist
from app.auth.decorators import spotify_token_required
from app.services.spotify_service import SpotifyService
from app.services.unified_analysis_service import UnifiedAnalysisService

@admin_bp.route('/admin/resync-all-playlists', methods=['POST'])
@login_required
@spotify_token_required
def admin_resync_all_playlists():
    """Admin endpoint to resync all playlists for the current user."""
    try:
        user_id = flask_login_current_user.id
        current_app.logger.info(f"Admin resync all playlists initiated by user {user_id}")
        
        # Initialize Spotify service
        spotify_service = SpotifyService()
        
        # Get all user playlists from Spotify
        try:
            spotify_playlists = spotify_service.get_user_playlists(flask_login_current_user)
            current_app.logger.info(f"Retrieved {len(spotify_playlists)} playlists from Spotify")
        except Exception as e:
            current_app.logger.error(f"Failed to get playlists from Spotify: {e}")
            flash(f"Failed to retrieve playlists from Spotify: {str(e)}", 'error')
            return redirect(url_for('core.dashboard'))
        
        sync_results = {
            'total_playlists': len(spotify_playlists),
            'updated': 0,
            'created': 0,
            'errors': 0
        }
        
        # Sync each playlist
        for spotify_playlist in spotify_playlists:
            try:
                # Check if playlist exists in database
                existing_playlist = Playlist.query.filter_by(
                    spotify_id=spotify_playlist['id'],
                    owner_id=user_id
                ).first()
                
                if existing_playlist:
                    # Update existing playlist
                    existing_playlist.name = spotify_playlist['name']
                    existing_playlist.description = spotify_playlist.get('description', '')
                    existing_playlist.image_url = spotify_playlist['images'][0]['url'] if spotify_playlist.get('images') else None
                    existing_playlist.track_count = spotify_playlist['tracks']['total']
                    sync_results['updated'] += 1
                    current_app.logger.debug(f"Updated playlist {spotify_playlist['name']}")
                else:
                    # Create new playlist
                    new_playlist = Playlist(
                        spotify_id=spotify_playlist['id'],
                        name=spotify_playlist['name'],
                        description=spotify_playlist.get('description', ''),
                        owner_id=user_id,
                        image_url=spotify_playlist['images'][0]['url'] if spotify_playlist.get('images') else None,
                        track_count=spotify_playlist['tracks']['total']
                    )
                    db.session.add(new_playlist)
                    sync_results['created'] += 1
                    current_app.logger.debug(f"Created new playlist {spotify_playlist['name']}")
                    
            except Exception as e:
                current_app.logger.error(f"Error syncing playlist {spotify_playlist.get('name', 'Unknown')}: {e}")
                sync_results['errors'] += 1
                continue
        
        # Commit all changes
        db.session.commit()
        
        current_app.logger.info(f"Admin resync completed: {sync_results}")
        flash(f"✅ Resync completed! Updated: {sync_results['updated']}, Created: {sync_results['created']}, Errors: {sync_results['errors']}", 'success')
        
        return redirect(url_for('core.dashboard'))
        
    except Exception as e:
        current_app.logger.error(f"Error in admin resync all playlists: {e}")
        db.session.rollback()
        flash(f"Error during resync: {str(e)}", 'error')
        return redirect(url_for('core.dashboard'))

@admin_bp.route('/admin/reanalyze-all-songs', methods=['POST'])
@login_required
@spotify_token_required
def admin_reanalyze_all_songs():
    """Admin endpoint to reanalyze all songs for the current user."""
    try:
        user_id = flask_login_current_user.id
        current_app.logger.info(f"Admin reanalyze all songs initiated by user {user_id}")
        
        # Get all songs for the user across all playlists
        user_songs = db.session.query(Song).join(
            PlaylistSong, Song.id == PlaylistSong.song_id
        ).join(
            Playlist, PlaylistSong.playlist_id == Playlist.id
        ).filter(Playlist.owner_id == user_id).distinct().all()
        
        total_songs = len(user_songs)
        
        if total_songs == 0:
            flash("No songs found to reanalyze", 'info')
            return redirect(url_for('core.dashboard'))
        
        current_app.logger.info(f"Found {total_songs} songs to reanalyze for user {user_id}")
        
        # Use unified analysis service to reanalyze all songs
        analysis_service = UnifiedAnalysisService()
        enqueued_count = 0
        
        for song in user_songs:
            try:
                job = analysis_service.enqueue_analysis_job(
                    song.id, 
                    user_id=user_id, 
                    priority='low',
                    force_reanalysis=True
                )
                if job:
                    enqueued_count += 1
                    current_app.logger.debug(f"Enqueued reanalysis for song {song.id}: {song.title}")
            except Exception as e:
                current_app.logger.error(f"Failed to enqueue reanalysis for song {song.id}: {e}")
                continue
        
        current_app.logger.info(f"Admin reanalysis: {enqueued_count}/{total_songs} songs enqueued")
        
        if enqueued_count > 0:
            flash(f"✅ Reanalysis started for {enqueued_count} songs! Check dashboard for progress.", 'success')
        else:
            flash("⚠️ No songs were enqueued for reanalysis. Check logs for details.", 'warning')
        
        return redirect(url_for('core.dashboard'))
        
    except Exception as e:
        current_app.logger.error(f"Error in admin reanalyze all songs: {e}")
        flash(f"Error starting reanalysis: {str(e)}", 'error')
        return redirect(url_for('core.dashboard'))

@admin_bp.route('/api/admin/reanalysis-status', methods=['GET'])
@login_required
def get_admin_reanalysis_status():
    """Check the status of the admin re-analysis job"""
    try:
        user_id = flask_login_current_user.id
        
        # Look for any active re-analysis job for this user
        from app.extensions import rq
        queue = rq.get_queue()
        
        # Find the most recent reanalysis job for this user
        active_job = None
        job_prefix = f'reanalyze_all_user_{user_id}_'
        
        # Check running jobs first
        for job in queue.started_job_registry.get_job_ids():
            if job.startswith(job_prefix):
                try:
                    active_job = queue.fetch_job(job)
                    if active_job and not active_job.is_finished:
                        break
                except Exception:
                    continue
        
        # If no running job, check deferred jobs
        if not active_job:
            for job in queue.deferred_job_registry.get_job_ids():
                if job.startswith(job_prefix):
                    try:
                        active_job = queue.fetch_job(job)
                        if active_job and not active_job.is_finished:
                            break
                    except Exception:
                        continue
        
        # If no active job, check recent jobs in the queue
        if not active_job:
            for job in queue.jobs[:10]:  # Check last 10 jobs
                if hasattr(job, 'id') and job.id.startswith(job_prefix):
                    if not job.is_finished:
                        active_job = job
                        break
        
        if not active_job:
            return jsonify({
                'active': False,
                'message': 'No active re-analysis job found'
            })
        
        # Get job status and progress
        if active_job.is_failed:
            error_info = str(active_job.exc_info) if active_job.exc_info else 'Unknown error'
            return jsonify({
                'active': False,
                'failed': True,
                'error': error_info,
                'message': 'Re-analysis job failed'
            })
        
        if active_job.is_finished:
            return jsonify({
                'active': False,
                'completed': True,
                'message': 'Re-analysis completed successfully'
            })
        
        # Job is active, get progress info
        progress_data = {
            'active': True,
            'job_id': active_job.id,
            'progress': 0,
            'current_song': 'Initializing...',
            'processed': 0,
            'total': 0,
            'successful': 0,
            'failed': 0,
            'message': 'Re-analysis in progress...'
        }
        
        if active_job.meta:
            progress_data.update({
                'progress': active_job.meta.get('progress', 0),
                'current_song': active_job.meta.get('current_song', 'Processing...'),
                'processed': active_job.meta.get('processed', 0),
                'total': active_job.meta.get('total', 0),
                'successful': active_job.meta.get('successful', 0),
                'failed': active_job.meta.get('failed', 0)
            })
            
            if active_job.meta.get('completed'):
                progress_data['active'] = False
                progress_data['completed'] = True
                progress_data['message'] = 'Re-analysis completed successfully'
        
        return jsonify(progress_data)
        
    except Exception as e:
        current_app.logger.error(f"Error checking admin reanalysis status: {e}")
        return jsonify({
            'error': True,
            'message': f'Failed to check re-analysis status: {str(e)}'
        }), 500

# Helper functions for admin operations
def admin_reanalyze_all_user_songs(user_id):
    """
    Background job to reanalyze all songs for a user.
    This is called by the background job system.
    """
    from app import create_app
    
    # Create app context for background job
    app = create_app()
    with app.app_context():
        try:
            current_app.logger.info(f"Starting admin reanalysis background job for user {user_id}")
            
            # Get user
            user = db.session.get(User, user_id)
            if not user:
                current_app.logger.error(f"User {user_id} not found for admin reanalysis")
                return {'status': 'error', 'message': 'User not found'}
            
            # Get all songs for the user
            user_songs = db.session.query(Song).join(
                PlaylistSong, Song.id == PlaylistSong.song_id
            ).join(
                Playlist, PlaylistSong.playlist_id == Playlist.id
            ).filter(Playlist.owner_id == user_id).distinct().all()
            
            total_songs = len(user_songs)
            processed = 0
            successful = 0
            failed = 0
            
            current_app.logger.info(f"Found {total_songs} songs to reanalyze for user {user_id}")
            
            # Use the unified analysis service
            analysis_service = UnifiedAnalysisService()
            
            for i, song in enumerate(user_songs):
                try:
                    current_app.logger.debug(f"Reanalyzing song {song.id}: {song.title}")
                    
                    # Enqueue individual analysis job
                    job = analysis_service.enqueue_analysis_job(
                        song.id,
                        user_id=user_id,
                        priority='low',
                        force_reanalysis=True
                    )
                    
                    if job:
                        successful += 1
                        current_app.logger.debug(f"Successfully enqueued reanalysis for song {song.id}")
                    else:
                        failed += 1
                        current_app.logger.warning(f"Failed to enqueue reanalysis for song {song.id}")
                    
                    processed += 1
                    
                    # Update progress every 10 songs
                    if processed % 10 == 0:
                        progress = round((processed / total_songs) * 100, 1)
                        current_app.logger.info(f"Admin reanalysis progress: {processed}/{total_songs} ({progress}%)")
                
                except Exception as e:
                    failed += 1
                    processed += 1
                    current_app.logger.error(f"Error reanalyzing song {song.id}: {e}")
                    continue
            
            result = {
                'status': 'completed',
                'total_songs': total_songs,
                'processed': processed,
                'successful': successful,
                'failed': failed,
                'message': f'Reanalysis completed: {successful} successful, {failed} failed'
            }
            
            current_app.logger.info(f"Admin reanalysis completed for user {user_id}: {result}")
            return result
            
        except Exception as e:
            current_app.logger.error(f"Error in admin reanalysis background job: {e}")
            return {
                'status': 'error',
                'message': str(e)
            }

def _admin_reanalyze_all_user_songs_impl(user_id):
    """
    Implementation function for admin reanalysis.
    This handles the actual reanalysis logic.
    """
    try:
        current_app.logger.info(f"Starting admin reanalysis implementation for user {user_id}")
        
        # Get all songs for the user across all playlists
        user_songs = db.session.query(Song).join(
            PlaylistSong, Song.id == PlaylistSong.song_id
        ).join(
            Playlist, PlaylistSong.playlist_id == Playlist.id
        ).filter(Playlist.owner_id == user_id).distinct().all()
        
        total_songs = len(user_songs)
        
        if total_songs == 0:
            return {
                'status': 'completed',
                'message': 'No songs found to reanalyze',
                'total_songs': 0,
                'processed': 0,
                'successful': 0,
                'failed': 0
            }
        
        current_app.logger.info(f"Found {total_songs} songs to reanalyze for user {user_id}")
        
        # Use unified analysis service for consistent reanalysis
        analysis_service = UnifiedAnalysisService()
        processed = 0
        successful = 0
        failed = 0
        
        for song in user_songs:
            try:
                # Enqueue analysis job for each song
                job = analysis_service.enqueue_analysis_job(
                    song.id,
                    user_id=user_id,
                    priority='low',
                    force_reanalysis=True
                )
                
                if job:
                    successful += 1
                    current_app.logger.debug(f"Successfully enqueued reanalysis for song {song.id}: {song.title}")
                else:
                    failed += 1
                    current_app.logger.warning(f"Failed to enqueue reanalysis for song {song.id}: {song.title}")
                
                processed += 1
                
            except Exception as e:
                failed += 1
                processed += 1
                current_app.logger.error(f"Error processing song {song.id} for reanalysis: {e}")
                continue
        
        result = {
            'status': 'completed',
            'total_songs': total_songs,
            'processed': processed,
            'successful': successful,
            'failed': failed,
            'message': f'Admin reanalysis completed: {successful} jobs enqueued, {failed} failed'
        }
        
        current_app.logger.info(f"Admin reanalysis implementation completed: {result}")
        return result
        
    except Exception as e:
        current_app.logger.error(f"Error in admin reanalysis implementation: {e}")
        return {
            'status': 'error',
            'message': str(e),
            'total_songs': 0,
            'processed': 0,
            'successful': 0,
            'failed': 0
        }
