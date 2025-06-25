"""
Main application routes for playlist management and song analysis
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from flask_login import login_required, current_user
from sqlalchemy import desc, func, and_

from .. import db
from ..models import User, Playlist, Song, AnalysisResult, Whitelist, PlaylistSong
from ..services.spotify_service import SpotifyService
from ..services.unified_analysis_service import UnifiedAnalysisService

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    """Homepage"""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return render_template('index.html')


@bp.route('/dashboard')
@login_required
def dashboard():
    """User dashboard showing playlists and stats"""
    # Get user's playlists with stats
    playlists = Playlist.query.filter_by(owner_id=current_user.id).all()
    
    # Calculate stats (using simple, working queries)
    total_playlists = len(playlists)
    total_songs = db.session.query(Song).join(PlaylistSong).join(Playlist).filter(
        Playlist.owner_id == current_user.id
    ).count()
    
    analyzed_songs = db.session.query(Song).join(AnalysisResult).join(PlaylistSong).join(Playlist).filter(
        Playlist.owner_id == current_user.id,
        AnalysisResult.status == 'completed'
    ).count()
    
    flagged_songs = db.session.query(Song).join(AnalysisResult).join(PlaylistSong).join(Playlist).filter(
        Playlist.owner_id == current_user.id,
        AnalysisResult.status == 'completed',
        AnalysisResult.concern_level.in_(['medium', 'high'])
    ).count()
    
    # Calculate clean playlists (playlists with no flagged songs)
    clean_playlists = db.session.query(Playlist).filter(
        Playlist.owner_id == current_user.id,
        ~Playlist.id.in_(
            db.session.query(Playlist.id).join(PlaylistSong).join(Song).join(AnalysisResult).filter(
                Playlist.owner_id == current_user.id,
                AnalysisResult.status == 'completed',
                AnalysisResult.concern_level.in_(['medium', 'high'])
            )
        )
    ).count()
    
    stats = {
        'total_playlists': total_playlists,
        'total_songs': total_songs,
        'analyzed_songs': analyzed_songs,
        'flagged_songs': flagged_songs,
        'clean_playlists': clean_playlists,
        'analysis_progress': round((analyzed_songs / total_songs * 100) if total_songs > 0 else 0, 1)
    }
    
    return render_template('dashboard.html', playlists=playlists, stats=stats)


@bp.route('/sync_playlists', methods=['GET', 'POST'])
@login_required
def sync_playlists():
    """Sync user's playlists from Spotify"""
    try:
        spotify = SpotifyService(current_user)
        count = spotify.sync_user_playlists()
        flash(f'Successfully refreshed {count} playlists from Spotify!', 'success')
    except Exception as e:
        current_app.logger.error(f'Playlist sync error: {e}')
        flash('Error refreshing playlists. Please try again.', 'error')
    
    return redirect(url_for('main.dashboard'))


@bp.route('/playlist/<int:playlist_id>')
@login_required
def playlist_detail(playlist_id):
    """Detailed view of a playlist with songs and analysis"""
    # Verify user has access to this playlist
    playlist = Playlist.query.filter_by(
        id=playlist_id,
        owner_id=current_user.id
    ).first_or_404()
    
    # Get songs with playlist position (simple query)
    songs_with_position = db.session.query(Song, PlaylistSong).join(
        PlaylistSong, Song.id == PlaylistSong.song_id
    ).filter(
        PlaylistSong.playlist_id == playlist_id
    ).order_by(PlaylistSong.track_position).all()
    
    # Build data structure for template
    songs_data = []
    for song, playlist_song in songs_with_position:
        # Get the most recent analysis for this song (same approach as song_detail)
        analysis = AnalysisResult.query.filter_by(song_id=song.id).order_by(desc(AnalysisResult.created_at)).first()
        
        # Check if song is whitelisted
        is_whitelisted = Whitelist.query.filter_by(
            user_id=current_user.id,
            spotify_id=song.spotify_id,
            item_type='song'
        ).first() is not None
        
        songs_data.append({
            'song': song,
            'analysis': analysis,  # Can be None
            'position': playlist_song.track_position,
            'is_whitelisted': is_whitelisted
        })
    
    # Simple template variables
    return render_template('playlist_detail.html', 
                         playlist=playlist,
                         songs=songs_data)


@bp.route('/song/<int:song_id>')
@login_required
def song_detail(song_id):
    """Detailed view of a song with analysis"""
    # Verify user has access to this song
    song = db.session.query(Song).join(PlaylistSong).join(Playlist).filter(
        Song.id == song_id,
        Playlist.owner_id == current_user.id
    ).first_or_404()
    
    analysis = AnalysisResult.query.filter_by(song_id=song_id).order_by(desc(AnalysisResult.created_at)).first()
    
    is_whitelisted = Whitelist.query.filter_by(
        user_id=current_user.id,
        spotify_id=song.spotify_id,
        item_type='song'
    ).first() is not None
    

    
    # Check if song has lyrics (for Biblical sections display)
    has_lyrics = bool(song.lyrics and song.lyrics.strip() and song.lyrics != "Lyrics not available")
    
    return render_template('song_detail.html', 
                         song=song, 
                         analysis=analysis, 
                         is_whitelisted=is_whitelisted,
                         has_lyrics=has_lyrics)


@bp.route('/analyze_song/<int:song_id>', methods=['POST'])
@login_required
def analyze_song(song_id):
    """Analyze a single song"""
    # Verify user has access to this song
    song = db.session.query(Song).join(PlaylistSong).join(Playlist).filter(
        Song.id == song_id,
        Playlist.owner_id == current_user.id
    ).first_or_404()
    
    try:
        analyzer = UnifiedAnalysisService()
        analyzer.enqueue_analysis_job(song.id, user_id=current_user.id)
        flash(f'Analysis started for "{song.title}". Check back in a moment for results!', 'info')
    except Exception as e:
        current_app.logger.error(f'Song analysis error: {e}')
        flash('Error starting analysis. Please try again.', 'error')
    
    return redirect(request.referrer or url_for('main.song_detail', song_id=song_id))


@bp.route('/analyze_playlist/<int:playlist_id>', methods=['POST'])
@login_required
def analyze_playlist(playlist_id):
    """Analyze all songs in a playlist"""
    playlist = Playlist.query.filter_by(
        id=playlist_id,
        owner_id=current_user.id
    ).first_or_404()
    
    # Check if this is an AJAX request
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    
    try:
        analyzer = UnifiedAnalysisService()
        # Get song count for playlist
        song_count = db.session.query(Song).join(PlaylistSong).filter(
            PlaylistSong.playlist_id == playlist.id
        ).count()
        
        # Queue analysis for all songs in playlist
        songs = db.session.query(Song).join(PlaylistSong).filter(
            PlaylistSong.playlist_id == playlist.id
        ).all()
        
        job_count = 0
        errors = []
        
        # For AJAX requests, create pending analysis records first for progress tracking
        if is_ajax:
            from ..models.models import AnalysisResult
            from datetime import datetime
            
            for song in songs:
                try:
                    # Check if analysis already exists
                    existing_analysis = AnalysisResult.query.filter_by(song_id=song.id).first()
                    if not existing_analysis:
                        # Create pending analysis record for progress tracking
                        pending_analysis = AnalysisResult(
                            song_id=song.id,
                            status='pending',
                            created_at=datetime.utcnow()
                        )
                        db.session.add(pending_analysis)
                        job_count += 1
                    else:
                        # If already analyzed, count it as queued for progress calculation
                        job_count += 1
                except Exception as song_error:
                    error_msg = f'Failed to create pending analysis for song {song.id}: {song_error}'
                    current_app.logger.warning(error_msg)
                    errors.append(error_msg)
            
            # Commit pending analyses
            db.session.commit()
            
            # Start background processing (we'll do this synchronously but with progress updates)
            if job_count > 0:
                # Import here to avoid circular imports
                from threading import Thread
                
                # Capture context before thread starts
                app = current_app._get_current_object()
                user_id = current_user.id  # Capture user_id before thread starts
                song_ids = [song.id for song in songs]  # Get song IDs instead of objects
                
                def process_playlist_analysis():
                    """Process playlist analysis in background thread"""
                    with app.app_context():
                        try:
                            app.logger.info(f'Starting background analysis for playlist {playlist_id} with {len(song_ids)} songs')
                            
                            for i, song_id in enumerate(song_ids, 1):
                                try:
                                    # Get fresh song object in this thread's context
                                    song = Song.query.get(song_id)
                                    if not song:
                                        app.logger.warning(f'Song {song_id} not found, skipping')
                                        continue
                                        
                                    app.logger.info(f'Processing song {i}/{len(song_ids)}: {song.title}')
                                    
                                    # Check if this song needs analysis
                                    analysis = AnalysisResult.query.filter_by(song_id=song_id).first()
                                    if analysis and analysis.status == 'pending':
                                        # Update status to in_progress
                                        analysis.status = 'in_progress'
                                        db.session.commit()
                                        
                                        # Perform the actual analysis
                                        analyzer.enqueue_analysis_job(song_id, user_id=user_id)
                                        
                                        app.logger.info(f'Completed analysis for song {i}/{len(song_ids)}: {song.title}')
                                    else:
                                        app.logger.info(f'Skipping song {i}/{len(song_ids)}: {song.title} (already analyzed)')
                                        
                                except Exception as song_error:
                                    app.logger.error(f'Failed to analyze song {song_id}: {song_error}')
                                    # Mark as failed
                                    try:
                                        analysis = AnalysisResult.query.filter_by(song_id=song_id).first()
                                        if analysis:
                                            analysis.status = 'failed'
                                            db.session.commit()
                                    except Exception as db_error:
                                        app.logger.error(f'Failed to update analysis status: {db_error}')
                            
                            app.logger.info(f'Completed background analysis for playlist {playlist_id}')
                        except Exception as e:
                            app.logger.error(f'Background analysis thread failed: {e}')
                
                # Start background thread
                thread = Thread(target=process_playlist_analysis)
                thread.daemon = True
                thread.start()
        else:
            # For non-AJAX requests, do synchronous analysis
            for song in songs:
                try:
                    analyzer.enqueue_analysis_job(song.id, user_id=current_user.id)
                    job_count += 1
                except Exception as song_error:
                    error_msg = f'Failed to queue song {song.id}: {song_error}'
                    current_app.logger.warning(error_msg)
                    errors.append(error_msg)
        
        if is_ajax:
            if job_count > 0:
                return jsonify({
                    'success': True,
                    'message': f'Analysis started for {job_count} songs',
                    'jobs_queued': job_count,
                    'total_songs': len(songs),
                    'errors': errors
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'No songs could be queued for analysis',
                    'errors': errors
                }), 400
        else:
            flash(f'Analysis started for {job_count} songs in "{playlist.name}". Check back for results!', 'info')
            return redirect(url_for('main.playlist_detail', playlist_id=playlist_id))
            
    except Exception as e:
        error_msg = f'Playlist analysis error: {e}'
        current_app.logger.error(error_msg)
        
        if is_ajax:
            return jsonify({
                'success': False,
                'message': 'Error starting playlist analysis. Please try again.',
                'error': str(e)
            }), 500
        else:
            flash('Error starting playlist analysis. Please try again.', 'error')
            return redirect(url_for('main.playlist_detail', playlist_id=playlist_id))


@bp.route('/whitelist_song/<int:song_id>', methods=['POST'])
@login_required
def whitelist_song(song_id):
    """Add a song to user's whitelist"""
    # Verify user has access to this song
    song = db.session.query(Song).join(PlaylistSong).join(Playlist).filter(
        Song.id == song_id,
        Playlist.owner_id == current_user.id
    ).first_or_404()
    
    # Check if already whitelisted
    existing = Whitelist.query.filter_by(
        user_id=current_user.id,
        spotify_id=song.spotify_id,
        item_type='song'
    ).first()
    
    if not existing:
        whitelist_entry = Whitelist(
            user_id=current_user.id,
            spotify_id=song.spotify_id,
            item_type='song',
            name=f"{song.artist} - {song.title}",
            reason=request.form.get('reason', 'User approved')
        )
        db.session.add(whitelist_entry)
        db.session.commit()
        flash(f'"{song.title}" added to your whitelist!', 'success')
    else:
        flash(f'"{song.title}" is already in your whitelist.', 'info')
    
    return redirect(request.referrer or url_for('main.song_detail', song_id=song_id))


@bp.route('/remove_whitelist/<int:song_id>', methods=['POST'])
@login_required
def remove_whitelist(song_id):
    """Remove a song from user's whitelist"""
    song = db.session.query(Song).join(PlaylistSong).join(Playlist).filter(
        Song.id == song_id,
        Playlist.owner_id == current_user.id
    ).first_or_404()
    
    whitelist_entry = Whitelist.query.filter_by(
        user_id=current_user.id,
        spotify_id=song.spotify_id,
        item_type='song'
    ).first_or_404()
    
    song_name = song.title
    db.session.delete(whitelist_entry)
    db.session.commit()
    
    flash(f'"{song_name}" removed from your whitelist.', 'info')
    return redirect(request.referrer or url_for('main.dashboard'))





@bp.route('/remove_song/<int:playlist_id>/<int:song_id>', methods=['POST'])
@login_required
def remove_song_from_playlist(playlist_id, song_id):
    """Remove a song from a playlist"""
    playlist = Playlist.query.filter_by(
        id=playlist_id,
        owner_id=current_user.id
    ).first_or_404()
    
    try:
        spotify = SpotifyService(current_user)
        success = spotify.remove_song_from_playlist(playlist.spotify_id, song_id)
        
        if success:
            # Update local database
            playlist_song = PlaylistSong.query.filter_by(
                playlist_id=playlist_id,
                song_id=song_id
            ).first()
            if playlist_song:
                db.session.delete(playlist_song)
                db.session.commit()
            
            flash('Song removed from playlist successfully!', 'success')
        else:
            flash('Error removing song from playlist.', 'error')
            
    except Exception as e:
        current_app.logger.error(f'Remove song error: {e}')
        flash('Error removing song from playlist.', 'error')
    
    return redirect(url_for('main.playlist_detail', playlist_id=playlist_id))


@bp.route('/whitelist_playlist/<int:playlist_id>', methods=['POST'])
@login_required  
def whitelist_playlist(playlist_id):
    """Add a playlist to user's whitelist and cascade to all songs"""
    # Verify user has access to this playlist
    playlist = Playlist.query.filter_by(
        id=playlist_id,
        owner_id=current_user.id
    ).first_or_404()
    
    # Check if already whitelisted
    existing = Whitelist.query.filter_by(
        user_id=current_user.id,
        spotify_id=playlist.spotify_id,
        item_type='playlist'
    ).first()
    
    if not existing:
        # Calculate the score percentage for the reason
        score_percent = (playlist.score * 100) if playlist.score else 0
        
        # Whitelist the playlist
        whitelist_entry = Whitelist(
            user_id=current_user.id,
            spotify_id=playlist.spotify_id,
            item_type='playlist',
            name=playlist.name,
            reason=f'High scoring playlist ({score_percent:.1f}%)'
        )
        db.session.add(whitelist_entry)
        
        # CASCADE: Whitelist all songs in the playlist
        songs = db.session.query(Song).join(PlaylistSong).filter(
            PlaylistSong.playlist_id == playlist.id
        ).all()
        
        songs_whitelisted = 0
        for song in songs:
            # Check if song is already whitelisted
            existing_song = Whitelist.query.filter_by(
                user_id=current_user.id,
                spotify_id=song.spotify_id,
                item_type='song'
            ).first()
            
            if not existing_song:
                song_whitelist_entry = Whitelist(
                    user_id=current_user.id,
                    spotify_id=song.spotify_id,
                    item_type='song',
                    name=f"{song.artist} - {song.title}",
                    reason=f'Whitelisted with playlist "{playlist.name}"'
                )
                db.session.add(song_whitelist_entry)
                songs_whitelisted += 1
        
        db.session.commit()
        
        flash(f'"{playlist.name}" and {songs_whitelisted} songs added to your whitelist!', 'success')
    else:
        flash(f'"{playlist.name}" is already in your whitelist.', 'info')
    
    return redirect(request.referrer or url_for('main.dashboard'))


@bp.route('/settings')
@login_required
def settings():
    """User settings page"""
    return render_template('user_settings.html', user=current_user) 