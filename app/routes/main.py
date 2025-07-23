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
    
    # Calculate track counts and analysis scores for each playlist
    for playlist in playlists:
        # Calculate track count from associations
        playlist.track_count = len(playlist.song_associations)
        
        # Calculate analysis score from completed song analyses
        if playlist.track_count > 0:
            # Get all completed analyses for songs in this playlist
            completed_analyses = db.session.query(AnalysisResult.score).join(
                Song, AnalysisResult.song_id == Song.id
            ).join(
                PlaylistSong, Song.id == PlaylistSong.song_id
            ).filter(
                PlaylistSong.playlist_id == playlist.id,
                AnalysisResult.status == 'completed'
            ).all()
            
            if completed_analyses:
                # Calculate average score from completed analyses
                scores = [analysis.score for analysis in completed_analyses if analysis.score is not None]
                if scores:
                    avg_score = sum(scores) / len(scores)
                    # Store as 0-100 scale in overall_alignment_score for the score property to work
                    playlist.overall_alignment_score = avg_score
    
    # Calculate overall stats (using simple, working queries)
    total_playlists = len(playlists)
    total_songs = db.session.query(Song.id).join(PlaylistSong).join(Playlist).filter(
        Playlist.owner_id == current_user.id
    ).distinct().count()
    
    # Count unique songs with completed analysis
    analyzed_songs = db.session.query(Song.id).join(AnalysisResult).join(PlaylistSong).join(Playlist).filter(
        Playlist.owner_id == current_user.id,
        AnalysisResult.status == 'completed'
    ).distinct().count()
    
    # Count unique songs with flagged analysis
    flagged_songs = db.session.query(Song.id).join(AnalysisResult).join(PlaylistSong).join(Playlist).filter(
        Playlist.owner_id == current_user.id,
        AnalysisResult.status == 'completed',
        AnalysisResult.concern_level.in_(['medium', 'high'])
    ).distinct().count()
    
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
    
    # Check if there's already a background analysis job running (quick check only)
    if total_songs > 0 and analyzed_songs < total_songs:
        unanalyzed_count = total_songs - analyzed_songs
        
        try:
            # Quick check without starting anything automatically
            from ..services.priority_analysis_queue import PriorityAnalysisQueue
            queue = PriorityAnalysisQueue()
            queue_status = queue.get_queue_status()
            
            # Check if background analysis is already running
            has_background_jobs = any(
                job.get('job_type') == 'BACKGROUND_ANALYSIS' and job.get('status') in ['pending', 'in_progress']
                for job in queue_status.get('jobs', [])
            )
            
            # Only show flash message if analysis is NOT active (to avoid duplicate with template banner)
            if has_background_jobs:
                # Analysis is running - don't show flash message, JavaScript will handle the UI
                pass
            else:
                # Don't show flash message at all - let the template banner handle it
                # This prevents duplicate "analyze all" messages
                pass
            
        except Exception as e:
            current_app.logger.warning(f'Failed to check background analysis status for user {current_user.id}: {e}')
            # Don't show flash message on error either - template banner is sufficient
    
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
    
    # Build data structure for template and calculate analysis statistics
    songs_data = []
    total_songs = len(songs_with_position)
    analyzed_songs = 0
    
    for song, playlist_song in songs_with_position:
        # Get the most recent analysis for this song (fix ordering to use analyzed_at)
        analysis = AnalysisResult.query.filter_by(song_id=song.id).order_by(desc(AnalysisResult.analyzed_at)).first()
        
        # Count completed analyses
        if analysis and analysis.status == 'completed':
            analyzed_songs += 1
        
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
    
    # Determine playlist analysis state
    playlist_analysis_state = {
        'total_songs': total_songs,
        'analyzed_songs': analyzed_songs,
        'is_fully_analyzed': analyzed_songs == total_songs and total_songs > 0,
        'has_unanalyzed': analyzed_songs < total_songs,
        'analysis_percentage': round((analyzed_songs / total_songs) * 100) if total_songs > 0 else 0
    }
    
    # Template variables with analysis state
    return render_template('playlist_detail.html', 
                         playlist=playlist,
                         songs=songs_data,
                         analysis_state=playlist_analysis_state)


@bp.route('/song/<int:song_id>')
@bp.route('/song/<int:song_id>/<int:playlist_id>')
@login_required
def song_detail(song_id, playlist_id=None):
    """Detailed view of a song with analysis"""
    # Verify user has access to this song
    song = db.session.query(Song).join(PlaylistSong).join(Playlist).filter(
        Song.id == song_id,
        Playlist.owner_id == current_user.id
    ).first_or_404()
    
    # Get playlist_id from URL path parameter or query parameter
    if not playlist_id:
        playlist_id = request.args.get('playlist_id', type=int)
    
    # Get playlist info if playlist_id is provided
    playlist = None
    if playlist_id:
        playlist = Playlist.query.filter_by(
            id=playlist_id,
            owner_id=current_user.id
        ).first()
    
    # If no specific playlist provided, try to find one this song belongs to
    if not playlist:
        playlist = db.session.query(Playlist).join(PlaylistSong).filter(
            PlaylistSong.song_id == song_id,
            Playlist.owner_id == current_user.id
        ).first()
    
    analysis = AnalysisResult.query.filter_by(song_id=song_id).order_by(desc(AnalysisResult.analyzed_at)).first()
    
    is_whitelisted = Whitelist.query.filter_by(
        user_id=current_user.id,
        spotify_id=song.spotify_id,
        item_type='song'
    ).first() is not None
    

    
    # Check if song has lyrics (for Biblical sections display)
    has_lyrics = bool(song.lyrics and song.lyrics.strip() and song.lyrics != "Lyrics not available")
    
    # Extract concern scriptures from concerns data for detailed biblical foundations
    concern_scriptures = []
    if analysis and analysis.concerns:
        import json
        try:
            # Parse concerns if it's stored as JSON string
            concerns_data = analysis.concerns
            if isinstance(concerns_data, str):
                concerns_data = json.loads(concerns_data)
            
            # Extract scripture information from each concern
            if concerns_data and isinstance(concerns_data, list):
                for concern in concerns_data:
                    if isinstance(concern, dict):
                        # Create scripture entry from concern data
                        concern_scripture = {
                            'concern_type': concern.get('type'),
                            'reference': f"Biblical Perspective on {concern.get('category', concern.get('type', 'Concern')).title()}",
                            'text': concern.get('biblical_perspective', ''),
                            'educational_value': concern.get('educational_value', ''),
                            'category': concern.get('category', ''),
                            'severity': concern.get('severity', '')
                        }
                        if concern_scripture['text']:  # Only add if there's actual scripture content
                            concern_scriptures.append(concern_scripture)
                
        except (json.JSONDecodeError, TypeError) as e:
            current_app.logger.warning(f"Error parsing concerns for song {song_id}: {e}")
    return render_template('song_detail.html', 
                         song=song, 
                         analysis=analysis, 
                         is_whitelisted=is_whitelisted,
                         has_lyrics=has_lyrics,
                         playlist=playlist,
                         concern_scriptures=concern_scriptures)


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
        # Get all songs in the playlist
        songs = db.session.query(Song).join(PlaylistSong).filter(
            PlaylistSong.playlist_id == playlist.id
        ).all()
        
        if not songs:
            message = f'No songs found in playlist "{playlist.name}"'
            if is_ajax:
                return jsonify({
                    'success': False,
                    'message': message,
                    'jobs_queued': 0,
                    'total_songs': 0
                })
            else:
                flash(message, 'warning')
                return redirect(url_for('main.playlist_detail', playlist_id=playlist_id))
        
        # Use the unified analysis service to properly queue playlist analysis
        analyzer = UnifiedAnalysisService()
        
        # Queue each song individually for analysis
        job_count = 0
        errors = []
        
        for song in songs:
            try:
                # Queue analysis for this song using the proper system
                analyzer.enqueue_analysis_job(song.id, user_id=current_user.id)
                job_count += 1
            except Exception as song_error:
                error_msg = f'Failed to queue song "{song.title}": {song_error}'
                current_app.logger.warning(error_msg)
                errors.append(error_msg)
        
        # Return appropriate response
        if is_ajax:
            if job_count > 0:
                return jsonify({
                    'success': True,
                    'message': f'Analysis started for {job_count} songs. This will take several minutes to complete.',
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
            if job_count > 0:
                flash(f'Analysis started for {job_count} songs in "{playlist.name}". This will take several minutes - check back for results!', 'info')
            else:
                flash('No songs could be queued for analysis. Please try again.', 'error')
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