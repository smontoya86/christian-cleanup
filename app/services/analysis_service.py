from flask import current_app
import logging
import json
from datetime import datetime
from ..extensions import rq, db
from ..models import Song, AnalysisResult
from ..utils.analysis import SongAnalyzer

logger = logging.getLogger(__name__)

def _execute_song_analysis_impl(song_id: int, user_id: int = None):
    """
    Core song analysis implementation.
    This is called from within an application context by _execute_song_analysis_task.
    
    Args:
        song_id: ID of the song to analyze
        user_id: Optional ID of the user who requested the analysis
    """
    from ..models import Song, AnalysisResult, User
    from ..extensions import db
    
    task_logger = current_app.logger
    task_logger.info(f"Starting analysis for song ID: {song_id}")

    try:
        # Start a new session for this job
        song = db.session.get(Song, song_id)
        if not song:
            task_logger.error(f"Song with ID {song_id} not found in database")
            return None

        task_logger.info(f"Analyzing song: {song.title} by {song.artist} (ID: {song_id}) for user_id: {user_id}")
        
        # Create the analyzer with the user_id
        analyzer = SongAnalyzer(user_id=user_id)
        analysis_output = analyzer.analyze_song(title=song.title, artist=song.artist)

        if analysis_output.get('error'):
            task_logger.error(f"Analysis error for song {song.id}: {analysis_output['error']}")
            return None

        # The analysis output contains the results directly
        christian_analysis_data = analysis_output
        
        if not christian_analysis_data:
            task_logger.error(f"No analysis data returned for song {song.id}")
            return None
            
        task_logger.info(f"Analysis results for song {song.id}: {christian_analysis_data}")

        # Start a new transaction for storing results
        try:
            # Extract relevant data from the analysis results
            themes = christian_analysis_data.get('themes', {})
            concerns = christian_analysis_data.get('concerns', [])
            score = christian_analysis_data.get('christian_score')
            concern_level = christian_analysis_data.get('christian_concern_level', 'Low')
            
            # Generate explanation
            explanation = f"Analysis completed with score: {score} ({concern_level} concern)"
            if concerns:
                explanation += f"\nConcerns: {', '.join(concerns)}"
            
            # Check for existing analysis
            existing_analysis = AnalysisResult.query.filter_by(song_id=song.id).first()
            
            if existing_analysis:
                # Update existing analysis
                task_logger.info(f"Updating existing analysis for song {song.id}")
                existing_analysis.mark_completed(
                    score=score,
                    concern_level=concern_level,
                    themes=themes,
                    concerns=concerns,
                    explanation=explanation
                )
            else:
                # Create new analysis
                task_logger.info(f"Creating new analysis for song {song.id}")
                analysis_result = AnalysisResult(
                    song_id=song.id,
                    status=AnalysisResult.STATUS_COMPLETED,
                    themes=themes,
                    concerns=concerns,
                    score=score,
                    concern_level=concern_level,
                    explanation=explanation
                )
                db.session.add(analysis_result)
            
            # Update the song's last_analyzed timestamp
            song.last_analyzed = datetime.utcnow()
            
            db.session.commit()
            task_logger.info(f"Analysis completed and saved for song: {song.title} (ID: {song.id})")
            return christian_analysis_data
            
        except Exception as e:
            db.session.rollback()
            task_logger.exception(f"Database error saving analysis for song {song.id}: {e}")
            return None

    except Exception as e:
        task_logger.exception(f"Error during analysis of song {song_id}: {e}")
        return None

def _execute_song_analysis_task(song_id: int, user_id: int = None, **kwargs):
    """
    Wrapper function that ensures the task runs within a Flask application context.
    This is the actual function that gets called by RQ.
    
    Args:
        song_id: ID of the song to analyze
        user_id: Optional ID of the user who requested the analysis
        **kwargs: Additional keyword arguments (for RQ compatibility)
    """
    import os
    from flask import current_app
    from .. import create_app
    
    # Create a new app instance for the background task
    app = create_app()
    
    with app.app_context():
        try:
            # Ensure environment variables are set from the app config
            if 'LYRICSGENIUS_API_KEY' not in os.environ and 'LYRICSGENIUS_API_KEY' in app.config:
                os.environ['LYRICSGENIUS_API_KEY'] = app.config['LYRICSGENIUS_API_KEY']
            if 'BIBLE_API_KEY' not in os.environ and 'BIBLE_API_KEY' in app.config:
                os.environ['BIBLE_API_KEY'] = app.config['BIBLE_API_KEY']
                
            current_app.logger.info(f"Starting song analysis task for song_id={song_id}, user_id={user_id}")
            
            # Call the implementation
            result = _execute_song_analysis_impl(song_id, user_id)
            
            current_app.logger.info(f"Completed song analysis task for song_id={song_id}")
            return result
            
        except Exception as e:
            current_app.logger.exception(f"Error in _execute_song_analysis_task for song_id={song_id}: {e}")
            raise  # Re-raise to mark the job as failed

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
    try:
        # Ensure we have a database session and the song exists
        from ..models import Song, User
        
        # Commit any pending changes to ensure the song is in the database
        db.session.commit()
        
        # Verify the song exists
        song = db.session.get(Song, song_id)
        if not song:
            logger.error(f"Cannot enqueue analysis: Song with ID {song_id} not found in database")
            return None
            
        # If user_id was provided, verify it's valid
        if user_id is not None:
            user = db.session.get(User, user_id)
            if not user:
                logger.warning(f"User with ID {user_id} not found, but continuing with analysis")
                user_id = None
            
        logger.info(f"Enqueueing Christian song analysis for song: {song.title} (ID: {song_id}) requested by user ID: {user_id or 'system'}")
        
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
                logger.info(f"Song analysis task for song ID {song_id} enqueued with job ID: {job.id}")
                return job
            else:
                logger.error(f"Failed to enqueue job for song ID {song_id}")
                return None
                
        except Exception as e:
            logger.exception(f"Error enqueueing job for song ID {song_id}: {e}")
            return None
        
    except Exception as e:
        logger.exception(f"Error enqueueing song analysis task for song ID {song_id}: {e}")
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
