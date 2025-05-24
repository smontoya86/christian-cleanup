from flask import current_app
import logging
import json
from datetime import datetime
from ..extensions import rq, db
from ..models import Song, AnalysisResult
from ..utils.analysis_adapter import SongAnalyzer
from ..utils.database import get_by_id  # Add SQLAlchemy 2.0 utility

logger = logging.getLogger(__name__)

def _execute_song_analysis_impl(song_id: int, user_id: int = None):
    """
    Implementation function that performs the actual song analysis.
    Fixed session management to avoid persistence errors.
    
    Args:
        song_id: ID of the song to analyze  
        user_id: Optional ID of the user who requested the analysis
    """
    from app.utils.database import db
    
    try:
        # Get song with explicit session handling using SQLAlchemy 2.0 pattern
        song = get_by_id(Song, song_id)
        if not song:
            raise ValueError(f"Song with ID {song_id} not found")
        
        # Create local variables to avoid session issues
        song_title = song.title
        song_artist = song.artist
        spotify_track_id = song.spotify_track_id
        is_explicit = song.is_explicit
        
        logging.info(f"Analyzing song: {song_title} by {song_artist} (ID: {song_id}) for user_id: {user_id}")
        
        # Initialize services
        lyrics_fetcher = LyricsFetcher()
        user_service = UserService()
        
        # Get analysis configuration
        if user_id:
            analysis_config = user_service.get_analysis_config(user_id)
        else:
            logging.info(f"Using default analysis config for user {user_id or 1}")
            analysis_config = user_service.get_analysis_config(1)  # Default user
        
        # Initialize enhanced analyzer
        analyzer = SongAnalyzer(
            lyrics_fetcher=lyrics_fetcher,
            analysis_config=analysis_config,
            user_id=user_id or 1
        )
        
        # Perform enhanced analysis
        result = analyzer.analyze_song(
            song_title=song_title,
            artist_name=song_artist,
            lyrics=None,  # Will fetch from Genius
            spotify_track_id=spotify_track_id,
            is_explicit=is_explicit,
            song_id=song_id
        )
        
        if result:
            logging.info(f"✅ Analysis completed for song ID {song_id}")
            # Explicitly commit the session to ensure persistence
            db.session.commit()
            return result
        else:
            logging.error(f"❌ Analysis failed for song ID {song_id}: No result returned")
            db.session.rollback()
            return None
            
    except Exception as e:
        logging.error(f"❌ Error analyzing song '{song_title if 'song_title' in locals() else 'Unknown'}' (ID: {song_id}): {str(e)}")
        # Rollback on error to clean up session state
        db.session.rollback()
        raise e

def _execute_song_analysis_task(song_id: int, user_id: int = None, **kwargs):
    """
    Background task function that executes the song analysis.
    This function is called by RQ workers and uses proper Flask app context.
    
    Args:
        song_id: ID of the song to analyze
        user_id: Optional ID of the user who requested the analysis
        **kwargs: Additional keyword arguments (for RQ compatibility)
    """
    from flask import current_app
    
    # Ensure we're in an application context
    if not current_app:
        # Create application context for RQ worker
        from app import create_app
        app = create_app('development')
        with app.app_context():
            return _execute_song_analysis_impl(song_id, user_id)
    else:
        # We're already in an app context
        return _execute_song_analysis_impl(song_id, user_id)

def perform_christian_song_analysis_and_store(song_id: int, user_id: int = None):
    """
    Enqueues a song analysis task to be processed by an RQ worker.
    Ensures the song is committed to the database before enqueuing.
    
    Args:
        song_id: ID of the song to analyze
        user_id: Optional ID of the user who requested the analysis
        
    Returns:
        Job object if enqueued successfully, None otherwise.
    """
    from flask import current_app
    
    # Use the current app context instead of creating a new one
    try:
        # Ensure environment variables are set from the app config
        import os
        if 'LYRICSGENIUS_API_KEY' not in os.environ and 'LYRICSGENIUS_API_KEY' in current_app.config:
            os.environ['LYRICSGENIUS_API_KEY'] = current_app.config['LYRICSGENIUS_API_KEY']
        if 'BIBLE_API_KEY' not in os.environ and 'BIBLE_API_KEY' in current_app.config:
            os.environ['BIBLE_API_KEY'] = current_app.config['BIBLE_API_KEY']
        
        # Ensure we have a database session and the song exists
        from ..models import Song, User
        
        # Commit any pending changes to ensure the song is in the database
        db.session.commit()
        
        # Verify the song exists
        song = db.session.get(Song, song_id)
        if not song:
            current_app.logger.error(f"Cannot enqueue analysis: Song with ID {song_id} not found in database")
            return None
            
        # If user_id was provided, verify it's valid
        if user_id is not None:
            user = db.session.get(User, user_id)
            if not user:
                current_app.logger.warning(f"User with ID {user_id} not found, but continuing with analysis")
                user_id = None
            
        current_app.logger.info(f"Enqueueing Christian song analysis for song: {song.title} (ID: {song_id}) requested by user ID: {user_id or 'system'}")
        
        try:
            # Get the default queue
            from ..extensions import rq
            
            # Enqueue the job with user context using the queue's enqueue method
            job = rq.get_queue().enqueue(
                'app.services.analysis_service._execute_song_analysis_task',
                song_id=song_id,
                user_id=user_id,
                job_timeout=current_app.config.get('RQ_JOB_TIMEOUT', 600)  # Default 10 minutes
            )
            
            if job:
                current_app.logger.info(f"Song analysis task for song ID {song_id} enqueued with job ID: {job.id}")
                return job
            else:
                current_app.logger.error(f"Failed to enqueue job for song ID {song_id}")
                return None
                
        except Exception as e:
            current_app.logger.exception(f"Error enqueueing job for song ID {song_id}: {e}")
            return None
            
    except Exception as e:
        current_app.logger.exception(f"Unexpected error in perform_christian_song_analysis_and_store: {e}")
        return None

# Placeholder functions for future implementation
def analyze_playlist_content(playlist_id, user_id):
    """
    Analyzes all songs in the specified playlist.
    
    Args:
        playlist_id: ID of the playlist to analyze
        user_id: ID of the user who requested the analysis
        
    Returns:
        dict: A summary of the analysis operation
    """
    from ..models import Playlist, Song
    
    logger.info(f"Starting analysis for playlist {playlist_id} requested by user {user_id}")
    
    try:
        # Get the playlist with its songs
        playlist = db.session.get(Playlist, playlist_id)
        if not playlist:
            logger.error(f"Playlist {playlist_id} not found")
            return {"error": "Playlist not found"}
            
        # Ensure we have a valid user_id
        if not user_id:
            logger.error(f"No user_id provided for playlist analysis {playlist_id}")
            return {"error": "User ID is required for analysis"}
            
        # Enqueue analysis for each song in the playlist
        song_count = 0
        enqueued_songs = []
        failed_songs = []
        
        for song in playlist.songs:
            try:
                logger.info(f"Enqueuing analysis for song {song.id} in playlist {playlist_id} for user {user_id}")
                job = perform_christian_song_analysis_and_store(song.id, user_id)
                if job:
                    song_count += 1
                    enqueued_songs.append(song.id)
                    logger.debug(f"Successfully enqueued analysis for song {song.id} (Job ID: {job.id})")
                else:
                    logger.error(f"Failed to enqueue analysis for song {song.id} in playlist {playlist_id}")
                    failed_songs.append(song.id)
            except Exception as e:
                logger.exception(f"Unexpected error enqueuing song {song.id} for analysis: {e}")
                failed_songs.append(song.id)
        
        # Update the playlist's last analyzed timestamp
        from datetime import datetime
        try:
            playlist.last_analyzed_at = datetime.utcnow()
            db.session.add(playlist)
            db.session.commit()
            logger.info(f"Updated last_analyzed_at for playlist {playlist_id}")
        except Exception as e:
            logger.exception(f"Error updating last_analyzed_at for playlist {playlist_id}: {e}")
            db.session.rollback()
        
        logger.info(f"Enqueued analysis for {song_count}/{len(playlist.songs)} songs in playlist {playlist_id}")
        
        result = {
            "success": True,
            "message": f"Analysis initiated for {song_count} songs in playlist '{playlist.name}'",
            "playlist_id": playlist_id,
            "playlist_name": playlist.name,
            "songs_analyzed": song_count,
            "total_songs": len(playlist.songs),
            "enqueued_songs": enqueued_songs,
            "failed_songs": failed_songs
        }
        
        if failed_songs:
            result["warning"] = f"Failed to enqueue {len(failed_songs)} songs for analysis"
            
        logger.info(f"Playlist analysis summary: {result}")
        return result
        
    except Exception as e:
        logger.exception(f"Error analyzing playlist {playlist_id}: {e}")
        return {
            "error": f"An error occurred while analyzing the playlist: {str(e)}",
            "playlist_id": playlist_id,
            "user_id": user_id
        }

def get_playlist_analysis_results(playlist_id, user_id):
    """
    Retrieves stored analysis results for a playlist.
    
    Args:
        playlist_id: ID of the playlist to get results for
        user_id: ID of the user requesting the results
        
    Returns:
        dict: A summary of the analysis results for the playlist
    """
    from ..models import Playlist, Song, AnalysisResult
    from sqlalchemy import func
    
    logger.info(f"Retrieving analysis results for playlist {playlist_id} for user {user_id}")
    
    try:
        # Get the playlist with its songs and analysis results
        playlist = db.session.query(Playlist).options(
            db.joinedload(Playlist.songs).joinedload(Song.analysis_result)
        ).filter_by(id=playlist_id).first()
        
        if not playlist:
            logger.error(f"Playlist {playlist_id} not found")
            return {"error": "Playlist not found"}
        
        # Calculate statistics
        total_songs = len(playlist.songs)
        analyzed_songs = [s for s in playlist.songs if hasattr(s, 'analysis_result') and s.analysis_result]
        analyzed_count = len(analyzed_songs)
        
        # Calculate average score if we have analyzed songs
        avg_score = None
        if analyzed_count > 0:
            total_score = sum(float(s.analysis_result.raw_score or 0) for s in analyzed_songs)
            avg_score = round(total_score / analyzed_count, 2)
        
        # Count songs by concern level
        concern_levels = {}
        for song in analyzed_songs:
            level = song.analysis_result.concern_level
            concern_levels[level] = concern_levels.get(level, 0) + 1
        
        # Prepare the response
        result = {
            "success": True,
            "playlist_id": playlist_id,
            "playlist_name": playlist.name,
            "total_songs": total_songs,
            "analyzed_songs": analyzed_count,
            "percent_analyzed": round((analyzed_count / total_songs * 100) if total_songs > 0 else 0, 2),
            "average_score": avg_score,
            "concern_levels": concern_levels,
            "last_analyzed": playlist.last_analyzed_at.isoformat() if playlist.last_analyzed_at else None
        }
        
        logger.info(f"Retrieved analysis results for playlist {playlist_id}: {result}")
        return result
        
    except Exception as e:
        logger.exception(f"Error retrieving analysis results for playlist {playlist_id}: {e}")
        return {"error": f"An error occurred while retrieving analysis results: {str(e)}"}
