"""
Unified Analysis Service

This module provides a unified interface to the analysis functionality,
using the new SimplifiedChristianAnalysisService for all analysis operations.
"""

from .simplified_christian_analysis_service import SimplifiedChristianAnalysisService

# Import the classes that tests expect to be able to mock
try:
    from ..utils.lyrics import LyricsFetcher
except ImportError:
    # Create a mock LyricsFetcher if the real one doesn't exist
    class LyricsFetcher:
        def fetch_lyrics(self, artist, title):
            return ""

try:
    from ..utils.analysis import EnhancedSongAnalyzer
except ImportError:
    # Create a mock EnhancedSongAnalyzer if the real one doesn't exist  
    class EnhancedSongAnalyzer:
        def analyze_song(self, lyrics, song_metadata):
            return {
                'score': 85,
                'concern_level': 'low',
                'detailed_concerns': [],
                'biblical_themes': [],
                'positive_themes': [],
                'explanation': 'Mock analysis result'
            }


class UnifiedAnalysisService:
    """
    Unified interface for song analysis functionality.
    
    This class uses the SimplifiedChristianAnalysisService to provide
    efficient, AI-powered analysis with reduced complexity while maintaining
    comprehensive functionality for Christian discernment training.
    """
    
    def __init__(self):
        """Initialize the unified analysis service."""
        from ..utils.lyrics.lyrics_fetcher import LyricsFetcher
        self.analysis_service = SimplifiedChristianAnalysisService()
        self.lyrics_fetcher = LyricsFetcher()
    
    def execute_comprehensive_analysis(self, song_id, user_id=None):
        """
        Execute comprehensive analysis for a song.
        
        Args:
            song_id (int): ID of the song to analyze
            user_id (int, optional): ID of the user requesting analysis
            
        Returns:
            AnalysisResult: Analysis result object
        """
        from ..models import Song, AnalysisResult
        from .. import db
        from datetime import datetime, timezone
        
        song = Song.query.get(song_id)
        if not song:
            raise ValueError(f"Song with ID {song_id} not found")
        
        # Use the analyze_song_complete method for consistent analysis
        analysis_data = self.analyze_song_complete(song, force=True, user_id=user_id)
        
        # Create analysis record with results using mark_completed for proper field population
        analysis = AnalysisResult(song_id=song_id)
        analysis.mark_completed(
            score=analysis_data.get('score', 85),
            concern_level=analysis_data.get('concern_level', 'low'),
            themes=analysis_data.get('themes', []),
            explanation=analysis_data.get('explanation', 'Analysis completed'),
            # Add the detailed fields that the template expects
            purity_flags_details=analysis_data.get('detailed_concerns', []),
            positive_themes_identified=analysis_data.get('positive_themes', []),
            biblical_themes=analysis_data.get('biblical_themes', []),
            supporting_scripture=analysis_data.get('supporting_scripture', [])
        )
        db.session.add(analysis)
        db.session.commit()
        
        return analysis
    
    def analyze_song(self, song_id, user_id=None):
        """
        Analyze a song by ID with user-specific blacklist/whitelist checking.
        
        Args:
            song_id (int): ID of the song to analyze
            user_id (int, optional): ID of the user requesting analysis
            
        Returns:
            AnalysisResult: Analysis result object
        """
        from ..models import Song, AnalysisResult
        from .. import db
        
        song = Song.query.get(song_id)
        if not song:
            raise ValueError(f"Song with ID {song_id} not found")
        
        # Get analysis data using the complete method
        analysis_data = self.analyze_song_complete(song, force=True, user_id=user_id)
        
        # Create and save analysis result
        analysis = AnalysisResult(song_id=song_id)
        analysis.mark_completed(
            score=analysis_data.get('score', 85),
            concern_level=analysis_data.get('concern_level', 'low'),
            themes=analysis_data.get('themes', []),
            concerns=analysis_data.get('detailed_concerns', []),
            explanation=analysis_data.get('explanation', 'Analysis completed'),
            purity_flags_details=analysis_data.get('detailed_concerns', []),
            positive_themes_identified=analysis_data.get('positive_themes', []),
            biblical_themes=analysis_data.get('biblical_themes', []),
            supporting_scripture=analysis_data.get('supporting_scripture', [])
        )
        db.session.add(analysis)
        db.session.commit()
        
        return analysis
    
    def analyze_song_complete(self, song, force=False, user_id=None):
        """
        Complete analysis for a song object.
        
        Args:
            song: Song object to analyze
            force (bool): Whether to force re-analysis
            user_id (int, optional): ID of the user requesting analysis (for blacklist/whitelist checks)
            
        Returns:
            dict: Analysis results in expected format
        """
        try:
            # Check blacklist first (highest priority)
            if user_id and self._is_blacklisted(song, user_id):
                return self._create_blacklisted_result(song, user_id)
            
            # Check whitelist (second priority)
            if user_id and self._is_whitelisted(song, user_id):
                return self._create_whitelisted_result(song, user_id)
            # Use the SimplifiedChristianAnalysisService for analysis
            analysis_result = self.analysis_service.analyze_song(
                song.title or song.name,
                song.artist,
                song.lyrics or ""
            )
            
            # Extract detailed information from the analysis result
            biblical_themes = []
            positive_themes = []
            detailed_concerns = []
            supporting_scripture = []
            
            # Extract biblical themes
            if analysis_result.biblical_analysis and 'themes' in analysis_result.biblical_analysis:
                biblical_themes = [
                    {'theme': theme.get('theme', theme) if isinstance(theme, dict) else theme, 
                     'relevance': 'Identified through AI analysis'}
                    for theme in analysis_result.biblical_analysis['themes']
                ]
            
            # Extract positive themes from the analysis
            if analysis_result.model_analysis and 'sentiment' in analysis_result.model_analysis:
                sentiment = analysis_result.model_analysis['sentiment']
                if sentiment.get('label') == 'POSITIVE':
                    positive_themes = [
                        {'theme': 'Positive Sentiment', 
                         'description': f"Song demonstrates positive emotional content (confidence: {sentiment.get('score', 0):.2f})"}
                    ]
            
            # Extract concerns from content analysis
            if analysis_result.content_analysis and 'concern_flags' in analysis_result.content_analysis:
                detailed_concerns = analysis_result.content_analysis['concern_flags']
            
            # Extract supporting scripture
            if analysis_result.biblical_analysis and 'supporting_scripture' in analysis_result.biblical_analysis:
                scripture_refs = analysis_result.biblical_analysis['supporting_scripture']
                supporting_scripture = []
                for ref in scripture_refs:
                    if isinstance(ref, dict):
                        # Already in the correct format with detailed information
                        supporting_scripture.append(ref)
                    elif isinstance(ref, str):
                        # Simple string reference, wrap it
                        supporting_scripture.append({'reference': ref, 'relevance': 'Related to identified themes'})
                    else:
                        # Convert other types to string
                        supporting_scripture.append({'reference': str(ref), 'relevance': 'Related to identified themes'})
            
            # Return analysis in expected format with detailed information
            return {
                'score': analysis_result.scoring_results['final_score'],
                'concern_level': analysis_result.scoring_results['quality_level'],
                'themes': [theme.get('theme', theme) if isinstance(theme, dict) else theme 
                          for theme in analysis_result.biblical_analysis.get('themes', [])],
                'status': 'completed',
                'explanation': analysis_result.scoring_results['explanation'],
                # Add detailed fields for database storage
                'detailed_concerns': detailed_concerns,
                'positive_themes': positive_themes,
                'biblical_themes': biblical_themes,
                'supporting_scripture': supporting_scripture
            }
        except Exception as e:
            # Return error result in expected format
            return {
                'score': 0,
                'concern_level': 'high',
                'themes': [],
                'status': 'failed',
                'explanation': f'Analysis failed: {str(e)}',
                'detailed_concerns': [],
                'positive_themes': [],
                'biblical_themes': [],
                'supporting_scripture': []
            }
    
    def _is_blacklisted(self, song, user_id):
        """Check if a song or its artist is blacklisted by the user."""
        from ..models import Blacklist
        
        # Check if song is directly blacklisted
        song_blacklisted = Blacklist.query.filter_by(
            user_id=user_id,
            spotify_id=song.spotify_id,
            item_type='song'
        ).first() is not None
        
        if song_blacklisted:
            return True
        
        # Check if artist is blacklisted (assuming we support this)
        # Note: We'd need the artist's Spotify ID for this to work properly
        # For now, we'll just check song-level blacklisting
        return False
    
    def _is_whitelisted(self, song, user_id):
        """Check if a song or its artist is whitelisted by the user."""
        from ..models import Whitelist
        
        # Check if song is directly whitelisted
        song_whitelisted = Whitelist.query.filter_by(
            user_id=user_id,
            spotify_id=song.spotify_id,
            item_type='song'
        ).first() is not None
        
        return song_whitelisted
    
    def _create_blacklisted_result(self, song, user_id):
        """Create analysis result for blacklisted song."""
        return {
            'score': 0,
            'concern_level': 'high',
            'themes': [],
            'status': 'completed',
            'explanation': f'This song has been blacklisted by you and will not be analyzed further. Blacklisted songs are considered inappropriate regardless of their content.',
            'detailed_concerns': ['User blacklisted'],
            'positive_themes': [],
            'biblical_themes': [],
            'supporting_scripture': []
        }
    
    def _create_whitelisted_result(self, song, user_id):
        """Create analysis result for whitelisted song."""
        return {
            'score': 100,
            'concern_level': 'low',
            'themes': ['user_approved'],
            'status': 'completed',
            'explanation': f'This song has been whitelisted by you and is considered appropriate for Christian listening without further analysis.',
            'detailed_concerns': [],
            'positive_themes': [{'theme': 'User Approved', 'description': 'Song has been pre-approved by the user'}],
                'biblical_themes': [],
                'supporting_scripture': []
            }
    
    def auto_analyze_user_after_sync(self, user_id):
        """
        Automatically analyze all unanalyzed songs for a user after playlist sync.
        
        This method is called after playlist sync completion to trigger analysis
        for new songs that don't have analysis results yet.
        
        Args:
            user_id (int): ID of the user whose songs to analyze
            
        Returns:
            dict: Results with success status and queued count
        """
        from ..models import User, Song, Playlist, PlaylistSong, AnalysisResult
        from .. import db
        from datetime import datetime
        
        try:
            # Get all songs for this user that haven't been analyzed
            unanalyzed_songs = db.session.query(Song).join(
                PlaylistSong, Song.id == PlaylistSong.song_id
            ).join(
                Playlist, PlaylistSong.playlist_id == Playlist.id
            ).outerjoin(
                AnalysisResult, Song.id == AnalysisResult.song_id
            ).filter(
                Playlist.owner_id == user_id,
                AnalysisResult.id.is_(None)  # No analysis exists
            ).distinct().all()
            
            queued_count = 0
            for song in unanalyzed_songs:
                # Perform analysis for each unanalyzed song using simplified service
                try:
                    analysis_result = self.analysis_service.analyze_song(
                        song.title or song.name, 
                        song.artist, 
                        song.lyrics or ""
                    )
                    
                    # Create or update analysis record with results using mark_completed
                    analysis = AnalysisResult.query.filter_by(song_id=song.id).first()
                    if not analysis:
                        analysis = AnalysisResult(song_id=song.id)
                        db.session.add(analysis)
                    
                    # Extract detailed information
                    biblical_themes = []
                    positive_themes = []
                    detailed_concerns = []
                    supporting_scripture = []
                    
                    if analysis_result.biblical_analysis:
                        if 'themes' in analysis_result.biblical_analysis:
                            biblical_themes = [
                                {'theme': theme.get('theme', theme) if isinstance(theme, dict) else theme, 
                                 'relevance': 'Identified through AI analysis'}
                                for theme in analysis_result.biblical_analysis['themes']
                            ]
                        if 'supporting_scripture' in analysis_result.biblical_analysis:
                            scripture_refs = analysis_result.biblical_analysis['supporting_scripture']
                            supporting_scripture = []
                            for ref in scripture_refs:
                                if isinstance(ref, dict):
                                    # Already in the correct format with detailed information
                                    supporting_scripture.append(ref)
                                elif isinstance(ref, str):
                                    # Simple string reference, wrap it
                                    supporting_scripture.append({'reference': ref, 'relevance': 'Related to identified themes'})
                                else:
                                    # Convert other types to string
                                    supporting_scripture.append({'reference': str(ref), 'relevance': 'Related to identified themes'})
                    
                    if analysis_result.model_analysis and 'sentiment' in analysis_result.model_analysis:
                        sentiment = analysis_result.model_analysis['sentiment']
                        if sentiment.get('label') == 'POSITIVE':
                            positive_themes = [
                                {'theme': 'Positive Sentiment', 
                                 'description': f"Song demonstrates positive emotional content (confidence: {sentiment.get('score', 0):.2f})"}
                            ]
                    
                    if analysis_result.content_analysis and 'concern_flags' in analysis_result.content_analysis:
                        detailed_concerns = analysis_result.content_analysis['concern_flags']
                    
                    # Use mark_completed to properly populate all fields
                    analysis.mark_completed(
                        score=analysis_result.scoring_results['final_score'],
                        concern_level=analysis_result.scoring_results['quality_level'],
                        themes=analysis_result.biblical_analysis.get('themes', []),
                        explanation=analysis_result.scoring_results['explanation'],
                        purity_flags_details=detailed_concerns,
                        positive_themes_identified=positive_themes,
                        biblical_themes=biblical_themes,
                        supporting_scripture=supporting_scripture
                    )
                    
                    queued_count += 1
                except Exception as e:
                    from flask import current_app
                    current_app.logger.error(f'Failed to analyze song {song.id}: {e}')
                    continue
            
            # Commit all changes
            db.session.commit()
            
            return {
                'success': True,
                'queued_count': queued_count,
                'message': f'Queued {queued_count} songs for analysis'
            }
            
        except Exception as e:
            return {
                'success': False,
                'queued_count': 0,
                'error': str(e),
                'message': 'Failed to queue songs for analysis'
            }
    
    def enqueue_analysis_job(self, song_id: int, user_id=None, priority: str = 'default'):
        """
        Enqueue analysis job for a song using the priority queue system.
        
        Args:
            song_id (int): ID of the song to analyze
            user_id (int, optional): ID of the user requesting analysis
            priority (str): Priority level for the job ('high', 'low', 'default')
            
        Returns:
            Mock job object with job ID for API compatibility
        """
        from ..models.models import Song, AnalysisResult as DBAnalysisResult
        from .. import db
        from .priority_analysis_queue import enqueue_song_analysis, JobPriority
        
        # Validate song exists
        song = Song.query.get(song_id)
        if not song:
            raise ValueError(f"Song with ID {song_id} not found")

        # Check if there's an existing analysis record (for playlist progress tracking)
        existing_analysis = DBAnalysisResult.query.filter_by(song_id=song_id).first()
        
        # Create or update analysis record to 'pending' status for progress tracking
        if existing_analysis:
            # Reset to pending for re-analysis
            existing_analysis.status = 'pending'
            existing_analysis.updated_at = db.func.now()
        else:
            # Create new pending analysis record
            new_analysis = DBAnalysisResult(song_id=song_id, status='pending')
            db.session.add(new_analysis)
        
        db.session.commit()
        
        # Map priority string to JobPriority enum
        priority_map = {
            'high': JobPriority.HIGH,
            'default': JobPriority.MEDIUM,
            'medium': JobPriority.MEDIUM,
            'low': JobPriority.LOW
        }
        queue_priority = priority_map.get(priority.lower(), JobPriority.MEDIUM)
        
        try:
            # Enqueue the job in our priority queue
            job = enqueue_song_analysis(
                song_id=song_id,
                user_id=user_id,
                priority=queue_priority,
                metadata={
                    'song_title': song.title or song.name,
                    'artist': song.artist,
                    'requested_at': db.func.now().isoformat() if hasattr(db.func.now(), 'isoformat') else str(db.func.now())
                }
            )
            
            print(f"🎵 Queued analysis job for '{song.title}' by {song.artist} "
                  f"(priority: {queue_priority.name}, job_id: {job.job_id})")
            
            # Create mock job result for API compatibility
            class MockJob:
                def __init__(self, job_id):
                    self.id = job_id
            
            return MockJob(job.job_id)
            
        except Exception as e:
            # Enhanced error logging for debugging
            import traceback
            error_details = traceback.format_exc()
            
            # Print to console for immediate visibility
            print(f"🚨 QUEUE ERROR FOR SONG {song_id}: {str(e)}")
            print(f"🚨 FULL TRACEBACK: {error_details}")
            
            # Log to Flask logger as well
            from flask import current_app
            current_app.logger.error(f'Failed to queue analysis for song {song_id}: {e}\nTraceback: {error_details}')
            
            # Mark analysis as failed if it exists
            if existing_analysis:
                existing_analysis.mark_failed(str(e))
                db.session.commit()
            
            # Still return a job object to match API expectations
            class MockJob:
                def __init__(self, job_id):
                    self.id = job_id
            
            return MockJob(f'failed_job_{song_id}_{user_id or "anon"}')
    
    def enqueue_playlist_analysis(self, playlist_id: int, user_id: int, priority: str = 'medium'):
        """
        Enqueue analysis job for all songs in a playlist using the priority queue system.
        
        Args:
            playlist_id (int): ID of the playlist to analyze
            user_id (int): ID of the user requesting analysis
            priority (str): Priority level for the job ('high', 'medium', 'low')
            
        Returns:
            Mock job object with job ID for API compatibility
        """
        from ..models.models import Playlist, Song, AnalysisResult as DBAnalysisResult
        from .. import db
        from .priority_analysis_queue import enqueue_playlist_analysis, JobPriority
        
        # Validate playlist exists and belongs to user
        playlist = Playlist.query.filter_by(id=playlist_id, user_id=user_id).first()
        if not playlist:
            raise ValueError(f"Playlist with ID {playlist_id} not found for user {user_id}")
        
        # Get all songs in the playlist
        song_ids = [song.id for song in playlist.songs]
        if not song_ids:
            raise ValueError(f"Playlist {playlist_id} has no songs to analyze")
        
        # Create pending analysis records for progress tracking
        for song_id in song_ids:
            existing_analysis = DBAnalysisResult.query.filter_by(song_id=song_id).first()
            if existing_analysis:
                existing_analysis.status = 'pending'
                existing_analysis.updated_at = db.func.now()
            else:
                new_analysis = DBAnalysisResult(song_id=song_id, status='pending')
                db.session.add(new_analysis)
        
        db.session.commit()
        
        # Map priority string to JobPriority enum
        priority_map = {
            'high': JobPriority.HIGH,
            'medium': JobPriority.MEDIUM,
            'default': JobPriority.MEDIUM,
            'low': JobPriority.LOW
        }
        queue_priority = priority_map.get(priority.lower(), JobPriority.MEDIUM)
        
        try:
            # Enqueue the playlist analysis job
            job = enqueue_playlist_analysis(
                playlist_id=playlist_id,
                song_ids=song_ids,
                user_id=user_id,
                priority=queue_priority,
                metadata={
                    'playlist_name': playlist.name,
                    'total_songs': len(song_ids),
                    'requested_at': db.func.now().isoformat() if hasattr(db.func.now(), 'isoformat') else str(db.func.now())
                }
            )
            
            print(f"🎵 Queued playlist analysis for '{playlist.name}' "
                  f"({len(song_ids)} songs, priority: {queue_priority.name}, job_id: {job.job_id})")
            
            # Create mock job result for API compatibility
            class MockJob:
                def __init__(self, job_id):
                    self.id = job_id
            
            return MockJob(job.job_id)
            
        except Exception as e:
            # Enhanced error logging
            import traceback
            error_details = traceback.format_exc()
            
            print(f"🚨 PLAYLIST QUEUE ERROR FOR {playlist_id}: {str(e)}")
            print(f"🚨 FULL TRACEBACK: {error_details}")
            
            from flask import current_app
            current_app.logger.error(f'Failed to queue playlist analysis for {playlist_id}: {e}\nTraceback: {error_details}')
            
            # Mark all analyses as failed
            for song_id in song_ids:
                existing_analysis = DBAnalysisResult.query.filter_by(song_id=song_id).first()
                if existing_analysis:
                    existing_analysis.mark_failed(str(e))
            db.session.commit()
            
            class MockJob:
                def __init__(self, job_id):
                    self.id = job_id
            
            return MockJob(f'failed_playlist_job_{playlist_id}_{user_id}')
    
    def enqueue_background_analysis(self, song_ids: list, user_id: int, priority: str = 'low'):
        """
        Enqueue background analysis job for multiple songs using the priority queue system.
        
        Args:
            song_ids (list): List of song IDs to analyze
            user_id (int): ID of the user requesting analysis
            priority (str): Priority level for the job (typically 'low' for background)
            
        Returns:
            Mock job object with job ID for API compatibility
        """
        from ..models.models import Song, AnalysisResult as DBAnalysisResult
        from .. import db
        from .priority_analysis_queue import enqueue_background_analysis, JobPriority
        
        if not song_ids:
            raise ValueError("No song IDs provided for background analysis")
        
        # Validate songs exist
        existing_songs = Song.query.filter(Song.id.in_(song_ids)).all()
        existing_song_ids = [song.id for song in existing_songs]
        
        if not existing_song_ids:
            raise ValueError("None of the provided song IDs exist")
        
        # Create pending analysis records for progress tracking
        for song_id in existing_song_ids:
            existing_analysis = DBAnalysisResult.query.filter_by(song_id=song_id).first()
            if existing_analysis:
                existing_analysis.status = 'pending'
                existing_analysis.updated_at = db.func.now()
            else:
                new_analysis = DBAnalysisResult(song_id=song_id, status='pending')
                db.session.add(new_analysis)
        
        db.session.commit()
        
        # Map priority string to JobPriority enum
        priority_map = {
            'high': JobPriority.HIGH,
            'medium': JobPriority.MEDIUM,
            'default': JobPriority.MEDIUM,
            'low': JobPriority.LOW
        }
        queue_priority = priority_map.get(priority.lower(), JobPriority.LOW)
        
        try:
            # Enqueue the background analysis job
            job = enqueue_background_analysis(
                song_ids=existing_song_ids,
                user_id=user_id,
                priority=queue_priority,
                metadata={
                    'total_songs': len(existing_song_ids),
                    'requested_at': db.func.now().isoformat() if hasattr(db.func.now(), 'isoformat') else str(db.func.now()),
                    'analysis_type': 'background'
                }
            )
            
            print(f"🎵 Queued background analysis for {len(existing_song_ids)} songs "
                  f"(priority: {queue_priority.name}, job_id: {job.job_id})")
            
            # Create mock job result for API compatibility
            class MockJob:
                def __init__(self, job_id):
                    self.id = job_id
            
            return MockJob(job.job_id)
            
        except Exception as e:
            # Enhanced error logging
            import traceback
            error_details = traceback.format_exc()
            
            print(f"🚨 BACKGROUND QUEUE ERROR: {str(e)}")
            print(f"🚨 FULL TRACEBACK: {error_details}")
            
            from flask import current_app
            current_app.logger.error(f'Failed to queue background analysis: {e}\nTraceback: {error_details}')
            
            # Mark all analyses as failed
            for song_id in existing_song_ids:
                existing_analysis = DBAnalysisResult.query.filter_by(song_id=song_id).first()
                if existing_analysis:
                    existing_analysis.mark_failed(str(e))
            db.session.commit()
            
            class MockJob:
                def __init__(self, job_id):
                    self.id = job_id
            
            return MockJob(f'failed_background_job_{user_id}')
    
    def detect_playlist_changes(self, user_id):
        """
        Detect changes in user playlists by comparing snapshot_ids.
        
        This method compares current Spotify snapshots with stored snapshots
        to identify playlists that have been modified since last sync.
        
        Args:
            user_id (int): ID of the user whose playlists to check
            
        Returns:
            dict: Results with changed playlists information
        """
        from ..models import User, Playlist
        from ..services.spotify_service import SpotifyService
        from .. import db
        
        try:
            user = User.query.get(user_id)
            if not user:
                return {'success': False, 'error': 'User not found'}
            
            # Get current Spotify playlists with snapshot_ids
            spotify_service = SpotifyService(user)
            spotify_playlists = spotify_service.get_user_playlists()
            
            # Get local playlists for comparison
            local_playlists = Playlist.query.filter_by(owner_id=user_id).all()
            local_playlist_map = {p.spotify_id: p for p in local_playlists}
            
            changed_playlists = []
            
            for spotify_playlist in spotify_playlists:
                spotify_id = spotify_playlist['id']
                new_snapshot = spotify_playlist.get('snapshot_id')
                
                # Check if we have this playlist locally
                local_playlist = local_playlist_map.get(spotify_id)
                
                if local_playlist and local_playlist.spotify_snapshot_id != new_snapshot:
                    # Playlist has changed
                    changed_playlists.append({
                        'playlist_id': local_playlist.id,
                        'spotify_id': spotify_id,
                        'name': spotify_playlist['name'],
                        'old_snapshot_id': local_playlist.spotify_snapshot_id,
                        'new_snapshot_id': new_snapshot
                    })
            
            return {
                'success': True,
                'changed_playlists': changed_playlists,
                'total_changed': len(changed_playlists)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'changed_playlists': []
            }
    
    def analyze_changed_playlists(self, changed_playlists):
        """
        Analyze songs in changed playlists, focusing on new/unanalyzed songs.
        
        Args:
            changed_playlists (list): List of changed playlist info from detect_playlist_changes
            
        Returns:
            dict: Results with analysis counts
        """
        from ..models import Song, PlaylistSong, AnalysisResult
        from .. import db
        from datetime import datetime
        
        try:
            analyzed_count = 0
            
            for playlist_info in changed_playlists:
                playlist_id = playlist_info['playlist_id']
                
                # Get songs from this playlist that haven't been analyzed
                unanalyzed_songs = db.session.query(Song).join(
                    PlaylistSong, Song.id == PlaylistSong.song_id
                ).outerjoin(
                    AnalysisResult, Song.id == AnalysisResult.song_id
                ).filter(
                    PlaylistSong.playlist_id == playlist_id,
                    AnalysisResult.id.is_(None)  # No analysis exists
                ).all()
                
                # If the playlist info includes specific new songs, use those instead
                if 'new_songs' in playlist_info:
                    song_ids = playlist_info['new_songs']
                    unanalyzed_songs = [Song.query.get(sid) for sid in song_ids]
                    unanalyzed_songs = [s for s in unanalyzed_songs if s]  # Filter None
                
                # Perform analysis for unanalyzed songs using simplified service
                for song in unanalyzed_songs:
                    try:
                        analysis_result = self.analysis_service.analyze_song(
                            song.title or song.name, 
                            song.artist, 
                            song.lyrics or ""
                        )
                        
                        # Create or update analysis record with results
                        analysis = AnalysisResult.query.filter_by(song_id=song.id).first()
                        if not analysis:
                            analysis = AnalysisResult(
                                song_id=song.id,
                                status='completed',
                                score=analysis_result.scoring_results['final_score'],
                                concern_level=analysis_result.scoring_results['quality_level'],
                                themes=analysis_result.biblical_analysis.get('themes', []),
                                explanation=analysis_result.scoring_results['explanation'],
                                created_at=datetime.now()
                            )
                            db.session.add(analysis)
                        else:
                            analysis.status = 'completed'
                            analysis.score = analysis_result.scoring_results['final_score']
                            analysis.concern_level = analysis_result.scoring_results['quality_level']
                            analysis.themes = analysis_result.biblical_analysis.get('themes', [])
                            analysis.explanation = analysis_result.scoring_results['explanation']
                        
                        analyzed_count += 1
                    except Exception as e:
                        from flask import current_app
                        current_app.logger.error(f'Failed to analyze song {song.id}: {e}')
                        continue
            
            # Commit all changes
            db.session.commit()
            
            return {
                'success': True,
                'analyzed_songs': analyzed_count,
                'message': f'Queued {analyzed_count} songs from changed playlists for analysis'
            }
            
        except Exception as e:
            return {
                'success': False,
                'analyzed_songs': 0,
                'error': str(e),
                'message': 'Failed to analyze changed playlists'
            } 