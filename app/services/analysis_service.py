"""
DEPRECATED: This module is being phased out in favor of unified_analysis_service.py

⚠️ WARNING: This analysis service has INCORRECT FIELD MAPPINGS and is deprecated.
Please use UnifiedAnalysisService from app.services.unified_analysis_service instead.

The field mapping in this service uses incorrect prefixed field names like:
- christian_concern_level (should be: concern_level)
- christian_purity_flags_details (should be: purity_flags)
- christian_positive_themes_detected (should be: positive_themes)
etc.

UnifiedAnalysisService has the CORRECT field mappings and comprehensive biblical analysis.
"""

import warnings
warnings.warn(
    "analysis_service.py is deprecated. Use UnifiedAnalysisService instead for correct field mappings.",
    DeprecationWarning,
    stacklevel=2
)

from flask import current_app
import logging
import json
from datetime import datetime
from ..extensions import rq, db
from ..models import Song, AnalysisResult
from ..utils.analysis_adapter import SongAnalyzer
from ..utils.database import get_by_id  # Add SQLAlchemy 2.0 utility
from ..utils.lyrics import LyricsFetcher
import time
import hashlib

logger = logging.getLogger(__name__)

# Global cache for analysis results to avoid re-analyzing identical songs
_analysis_cache = {}
_lyrics_cache = {}

def _get_song_cache_key(title: str, artist: str, is_explicit: bool) -> str:
    """Generate a cache key for a song based on title, artist, and explicit flag"""
    content = f"{title.lower().strip()}|{artist.lower().strip()}|{is_explicit}"
    return hashlib.md5(content.encode()).hexdigest()

def _execute_song_analysis_impl(song_id: int, user_id: int = None):
    """
    Core implementation of song analysis that stores comprehensive results.
    This function performs the actual analysis and database operations.
    """
    start_time = time.time()
    
    try:
        # Get song from database
        song = db.session.get(Song, song_id)
        if not song:
            logging.error(f"Song with ID {song_id} not found in database")
            return None
            
        song_title = song.title
        song_artist = song.artist
        is_explicit = song.explicit
        
        # Check cache first
        cache_key = _get_song_cache_key(song_title, song_artist, is_explicit)
        if cache_key in _analysis_cache:
            cached_result = _analysis_cache[cache_key]
            logging.info(f"⚡ Using cached analysis for: {song_title}")
            
            # Clear any existing analysis results for this song (for re-analysis scenarios)
            existing_results = AnalysisResult.query.filter_by(song_id=song_id).all()
            for existing_result in existing_results:
                db.session.delete(existing_result)
            
            # Create AnalysisResult from cached data with comprehensive fields
            analysis_result = AnalysisResult(
                song_id=song_id,
                status=AnalysisResult.STATUS_COMPLETED,
                score=cached_result.get('christian_score', 85),
                concern_level=cached_result.get('christian_concern_level', 'Low'),
                purity_flags_details=json.dumps(cached_result.get('christian_purity_flags_details', [])),
                positive_themes_identified=json.dumps(cached_result.get('christian_positive_themes_detected', [])),
                biblical_themes=json.dumps(cached_result.get('christian_biblical_themes', [])),
                supporting_scripture=json.dumps(cached_result.get('christian_supporting_scripture', {})),
                concerns=json.dumps(cached_result.get('christian_detailed_concerns', [])),
                explanation=cached_result.get('explanation', ''),
                analyzed_at=datetime.utcnow(),
                created_at=datetime.utcnow()
            )
            
            # Save to database
            db.session.add(analysis_result)
            db.session.commit()
            
            elapsed = time.time() - start_time
            logging.info(f"✅ Cached analysis completed for song ID {song_id} in {elapsed:.2f}s")
            return analysis_result
        
        # Initialize services with optimizations
        lyrics_fetcher = LyricsFetcher()
        
        # Initialize enhanced analyzer (it handles its own configuration)
        analyzer = SongAnalyzer(user_id=user_id or 1)
        
        # Always perform comprehensive analysis (including for explicit songs)
        # The enhanced analyzer will handle explicit content appropriately while still doing full analysis
        result = analyzer.analyze_song(
            title=song_title,
            artist=song_artist,
            lyrics_text=None,  # Will fetch from Genius if needed
            is_explicit=is_explicit
        )
        
        if result:
            # Cache the result for future identical songs
            _analysis_cache[cache_key] = result
            
            # Limit cache size to prevent memory issues
            if len(_analysis_cache) > 1000:
                # Remove oldest 100 entries
                oldest_keys = list(_analysis_cache.keys())[:100]
                for key in oldest_keys:
                    del _analysis_cache[key]
            
            # Clear any existing analysis results for this song (for re-analysis scenarios)
            existing_results = AnalysisResult.query.filter_by(song_id=song_id).all()
            for existing_result in existing_results:
                db.session.delete(existing_result)
            
            # Create new AnalysisResult with comprehensive data mapping
            analysis_result = AnalysisResult(
                song_id=song_id,
                status=AnalysisResult.STATUS_COMPLETED,
                score=result.get('christian_score', 85),
                concern_level=result.get('christian_concern_level', 'Low'),
                # Map comprehensive analysis fields to database
                purity_flags_details=json.dumps(result.get('christian_purity_flags_details', [])),
                positive_themes_identified=json.dumps(result.get('christian_positive_themes_detected', [])),
                biblical_themes=json.dumps(result.get('christian_biblical_themes', [])),
                supporting_scripture=json.dumps(result.get('christian_supporting_scripture', {})),
                concerns=json.dumps(result.get('christian_detailed_concerns', [])),
                explanation=result.get('explanation', ''),
                analyzed_at=datetime.utcnow(),
                created_at=datetime.utcnow()
            )
            
            # Save to database
            db.session.add(analysis_result)
            db.session.commit()
            
            elapsed = time.time() - start_time
            
            # Log comprehensive analysis completion
            biblical_themes_count = len(result.get('christian_biblical_themes', []))
            concerns_count = len(result.get('christian_detailed_concerns', []))
            positive_themes_count = len(result.get('christian_positive_themes_detected', []))
            
            logging.info(f"✅ Comprehensive analysis completed for song ID {song_id}: "
                        f"Score={result.get('christian_score')}, Level={result.get('christian_concern_level')}, "
                        f"Biblical Themes={biblical_themes_count}, Concerns={concerns_count}, "
                        f"Positive Themes={positive_themes_count} in {elapsed:.2f}s")
            return analysis_result
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
            
        current_app.logger.info(f"Enqueueing comprehensive Christian song analysis for song: {song.title} (ID: {song_id}) requested by user ID: {user_id or 'system'}")
        
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
                current_app.logger.info(f"Comprehensive song analysis task for song ID {song_id} enqueued with job ID: {job.id}")
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
    
    # Implementation would go here
    return {"status": "not_implemented"}

def get_playlist_analysis_results(playlist_id, user_id):
    """
    Retrieves analysis results for all songs in a playlist.
    
    Args:
        playlist_id: ID of the playlist
        user_id: ID of the user requesting the results
        
    Returns:
        dict: Analysis results for the playlist
    """
    from ..models import Playlist, Song, AnalysisResult
    
    logger.info(f"Retrieving analysis results for playlist {playlist_id} for user {user_id}")
    
    # Implementation would go here
    return {"status": "not_implemented"}
