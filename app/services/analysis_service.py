from flask import current_app
import logging
import json
from ..extensions import rq, db
from ..models import Song, AnalysisResult
from ..utils.analysis import SongAnalyzer

logger = logging.getLogger(__name__)

def _execute_song_analysis_impl(song_id: int):
    """
    Core song analysis implementation.
    This is called from within an application context by _execute_song_analysis_task.
    """
    from ..models import Song, AnalysisResult
    from ..extensions import db
    
    task_logger = current_app.logger
    task_logger.info(f"Starting analysis for song ID: {song_id}")

    try:
        # Start a new session for this job
        song = db.session.get(Song, song_id)
        if not song:
            task_logger.error(f"Song with ID {song_id} not found in database")
            return None

        task_logger.info(f"Analyzing song: {song.title} by {song.artist} (ID: {song_id})")
        
        analyzer = SongAnalyzer() 
        analysis_output = analyzer.analyze_song(title=song.title, artist=song.artist)

        if analysis_output.get('error'):
            task_logger.error(f"Analysis error for song {song.id}: {analysis_output['error']}")
            return None

        christian_analysis_data = analysis_output.get('christian_song_analysis')
        if not christian_analysis_data:
            task_logger.error(f"No analysis data returned for song {song.id}")
            return None

        # Start a new transaction for storing results
        try:
            existing_analysis = AnalysisResult.query.filter_by(song_id=song.id).first()
            if existing_analysis:
                task_logger.info(f"Updating existing analysis for song {song.id}")
                existing_analysis.themes = json.dumps(christian_analysis_data)
                existing_analysis.raw_score = christian_analysis_data.get('overall_score')
                existing_analysis.concern_level = christian_analysis_data.get('concern_level')
            else:
                task_logger.info(f"Creating new analysis for song {song.id}")
                analysis_result = AnalysisResult(
                    song_id=song.id,
                    themes=json.dumps(christian_analysis_data),
                    raw_score=christian_analysis_data.get('overall_score'),
                    concern_level=christian_analysis_data.get('concern_level')
                )
                db.session.add(analysis_result)
            
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

@rq.job('default')
def _execute_song_analysis_task(song_id: int):
    """
    Wrapper function that ensures the task runs within a Flask application context.
    This is the actual function that gets called by RQ.
    """
    from .. import create_app
    
    # Create a new app instance for the background task
    app = create_app()
    
    with app.app_context():
        return _execute_song_analysis_impl(song_id)

def perform_christian_song_analysis_and_store(song_id: int):
    """
    Enqueues a song analysis task to be processed by an RQ worker.
    Ensures the song is committed to the database before enqueuing.
    Returns the Job object if enqueued successfully, None otherwise.
    """
    try:
        # Ensure we have a database session and the song exists
        from ..models import Song
        
        # Commit any pending changes to ensure the song is in the database
        db.session.commit()
        
        # Verify the song exists
        song = db.session.get(Song, song_id)
        if not song:
            logger.error(f"Cannot enqueue analysis: Song with ID {song_id} not found in database")
            return None
            
        logger.info(f"Enqueueing Christian song analysis for song: {song.title} (ID: {song_id})")
        
        # Enqueue the job
        job = _execute_song_analysis_task.queue(song_id)
        logger.info(f"Song analysis task for song ID {song_id} enqueued with job ID: {job.id}")
        return job
        
    except Exception as e:
        logger.exception(f"Error enqueueing song analysis task for song ID {song_id}: {e}")
        return None

# Placeholder functions for future implementation
def analyze_playlist_content(playlist_id, user_id):
    """
    Placeholder function.
    Analyzes the content of a given playlist.
    """
    logger.debug(f"Placeholder: analyze_playlist_content called for playlist {playlist_id}, user {user_id}")
    # TODO: Implement actual analysis logic (Task 5)
    return {}

def get_playlist_analysis_results(playlist_id, user_id):
    """
    Placeholder function.
    Retrieves stored analysis results for a playlist.
    """
    logger.debug(f"Placeholder: get_playlist_analysis_results called for playlist {playlist_id}, user {user_id}")
    # TODO: Implement retrieval logic (Task 5)
    return None
