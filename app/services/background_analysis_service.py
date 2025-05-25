"""
Background Analysis Service
Automatically analyzes all songs in all playlists for users in the background
"""

from flask import current_app
from ..models import User, Playlist, Song, AnalysisResult, PlaylistSong
from .. import db
from ..services.analysis_service import perform_christian_song_analysis_and_store
from sqlalchemy import and_
import time
from datetime import datetime, timedelta


class BackgroundAnalysisService:
    """Service to handle background analysis of all user songs"""
    
    @staticmethod
    def start_background_analysis_for_user(user_id, max_songs_per_batch=50):
        """
        Start background analysis for all unanalyzed songs for a user
        
        Args:
            user_id (int): The user ID to analyze songs for
            max_songs_per_batch (int): Maximum number of songs to analyze in one batch
            
        Returns:
            dict: Status information about the analysis
        """
        try:
            current_app.logger.info(f"Starting background analysis for user {user_id}")
            
            # Get all unanalyzed songs for this user across all their playlists
            unanalyzed_songs = db.session.query(Song).join(
                PlaylistSong, Song.id == PlaylistSong.song_id
            ).join(
                Playlist, PlaylistSong.playlist_id == Playlist.id
            ).outerjoin(
                AnalysisResult, Song.id == AnalysisResult.song_id
            ).filter(
                and_(
                    Playlist.owner_id == user_id,
                    AnalysisResult.id.is_(None)  # No analysis result exists
                )
            ).distinct().limit(max_songs_per_batch).all()
            
            if not unanalyzed_songs:
                current_app.logger.info(f"No unanalyzed songs found for user {user_id}")
                return {
                    'status': 'complete',
                    'message': 'All songs are already analyzed',
                    'songs_queued': 0,
                    'total_unanalyzed': 0
                }
            
            # Queue analysis jobs for each song
            jobs_queued = 0
            failed_jobs = 0
            
            for song in unanalyzed_songs:
                try:
                    job = perform_christian_song_analysis_and_store(song.id, user_id=user_id)
                    if job:
                        jobs_queued += 1
                        current_app.logger.debug(f"Queued analysis job for song {song.id}: {song.title}")
                    else:
                        failed_jobs += 1
                        current_app.logger.warning(f"Failed to queue analysis for song {song.id}: {song.title}")
                        
                except Exception as e:
                    failed_jobs += 1
                    current_app.logger.error(f"Error queuing analysis for song {song.id}: {e}")
            
            # Get total count of remaining unanalyzed songs
            total_unanalyzed = db.session.query(Song).join(
                PlaylistSong, Song.id == PlaylistSong.song_id
            ).join(
                Playlist, PlaylistSong.playlist_id == Playlist.id
            ).outerjoin(
                AnalysisResult, Song.id == AnalysisResult.song_id
            ).filter(
                and_(
                    Playlist.owner_id == user_id,
                    AnalysisResult.id.is_(None)
                )
            ).distinct().count()
            
            current_app.logger.info(
                f"Background analysis batch for user {user_id}: "
                f"{jobs_queued} jobs queued, {failed_jobs} failed, "
                f"{total_unanalyzed} total unanalyzed remaining"
            )
            
            return {
                'status': 'started',
                'message': f'Queued {jobs_queued} songs for analysis',
                'songs_queued': jobs_queued,
                'failed_jobs': failed_jobs,
                'total_unanalyzed': total_unanalyzed,
                'batch_size': max_songs_per_batch
            }
            
        except Exception as e:
            current_app.logger.error(f"Error in background analysis for user {user_id}: {e}")
            return {
                'status': 'error',
                'message': f'Failed to start background analysis: {str(e)}',
                'songs_queued': 0,
                'total_unanalyzed': 0
            }
    
    @staticmethod
    def get_analysis_progress_for_user(user_id):
        """
        Get analysis progress statistics for a user
        
        Args:
            user_id (int): The user ID to get progress for
            
        Returns:
            dict: Progress information
        """
        try:
            # Get total songs for user
            total_songs = db.session.query(Song).join(
                PlaylistSong, Song.id == PlaylistSong.song_id
            ).join(
                Playlist, PlaylistSong.playlist_id == Playlist.id
            ).filter(Playlist.owner_id == user_id).distinct().count()
            
            # Get completed analyses
            completed_analyses = db.session.query(Song).join(
                PlaylistSong, Song.id == PlaylistSong.song_id
            ).join(
                Playlist, PlaylistSong.playlist_id == Playlist.id
            ).join(
                AnalysisResult, Song.id == AnalysisResult.song_id
            ).filter(
                and_(
                    Playlist.owner_id == user_id,
                    AnalysisResult.status == 'completed'
                )
            ).distinct().count()
            
            # Get in-progress analyses
            in_progress_analyses = db.session.query(Song).join(
                PlaylistSong, Song.id == PlaylistSong.song_id
            ).join(
                Playlist, PlaylistSong.playlist_id == Playlist.id
            ).join(
                AnalysisResult, Song.id == AnalysisResult.song_id
            ).filter(
                and_(
                    Playlist.owner_id == user_id,
                    AnalysisResult.status == 'in_progress'
                )
            ).distinct().count()
            
            # Get failed analyses
            failed_analyses = db.session.query(Song).join(
                PlaylistSong, Song.id == PlaylistSong.song_id
            ).join(
                Playlist, PlaylistSong.playlist_id == Playlist.id
            ).join(
                AnalysisResult, Song.id == AnalysisResult.song_id
            ).filter(
                and_(
                    Playlist.owner_id == user_id,
                    AnalysisResult.status == 'failed'
                )
            ).distinct().count()
            
            pending_analyses = total_songs - completed_analyses - in_progress_analyses - failed_analyses
            
            # Calculate progress percentage
            progress_percentage = (completed_analyses / total_songs * 100) if total_songs > 0 else 0
            
            # Get current analysis (most recent in-progress)
            current_analysis = db.session.query(Song, AnalysisResult).join(
                PlaylistSong, Song.id == PlaylistSong.song_id
            ).join(
                Playlist, PlaylistSong.playlist_id == Playlist.id
            ).join(
                AnalysisResult, Song.id == AnalysisResult.song_id
            ).filter(
                and_(
                    Playlist.owner_id == user_id,
                    AnalysisResult.status == 'in_progress'
                )
            ).order_by(AnalysisResult.created_at.desc()).first()
            
            # Get recent completed analyses (last 5)
            recent_analyses = db.session.query(Song, AnalysisResult).join(
                PlaylistSong, Song.id == PlaylistSong.song_id
            ).join(
                Playlist, PlaylistSong.playlist_id == Playlist.id
            ).join(
                AnalysisResult, Song.id == AnalysisResult.song_id
            ).filter(
                and_(
                    Playlist.owner_id == user_id,
                    AnalysisResult.status == 'completed'
                )
            ).order_by(AnalysisResult.updated_at.desc()).limit(5).all()
            
            return {
                'total_songs': total_songs,
                'completed': completed_analyses,
                'in_progress': in_progress_analyses,
                'pending': pending_analyses,
                'failed': failed_analyses,
                'progress_percentage': round(progress_percentage, 1),
                'has_active_analysis': in_progress_analyses > 0,
                'current_analysis': {
                    'title': current_analysis[0].title if current_analysis else None,
                    'artist': current_analysis[0].artist if current_analysis else None,
                    'started_at': current_analysis[1].created_at.isoformat() if current_analysis else None
                } if current_analysis else None,
                'recent_analyses': [
                    {
                        'title': song.title,
                        'artist': song.artist,
                        'score': analysis.score,
                        'completed_at': analysis.updated_at.isoformat() if analysis.updated_at else None
                    }
                    for song, analysis in recent_analyses
                ]
            }
            
        except Exception as e:
            current_app.logger.error(f"Error getting analysis progress for user {user_id}: {e}")
            return {
                'total_songs': 0,
                'completed': 0,
                'in_progress': 0,
                'pending': 0,
                'failed': 0,
                'progress_percentage': 0,
                'has_active_analysis': False,
                'current_analysis': None,
                'recent_analyses': []
            }
    
    @staticmethod
    def should_start_background_analysis(user_id, min_interval_hours=24):
        """
        Check if background analysis should be started for a user
        
        Args:
            user_id (int): The user ID to check
            min_interval_hours (int): Minimum hours between background analysis runs
            
        Returns:
            bool: True if background analysis should be started
        """
        try:
            # Check if user has any unanalyzed songs
            unanalyzed_count = db.session.query(Song).join(
                PlaylistSong, Song.id == PlaylistSong.song_id
            ).join(
                Playlist, PlaylistSong.playlist_id == Playlist.id
            ).outerjoin(
                AnalysisResult, Song.id == AnalysisResult.song_id
            ).filter(
                and_(
                    Playlist.owner_id == user_id,
                    AnalysisResult.id.is_(None)
                )
            ).distinct().count()
            
            if unanalyzed_count == 0:
                return False
            
            # Check if there's already active analysis
            active_analysis = db.session.query(AnalysisResult).join(
                Song, AnalysisResult.song_id == Song.id
            ).join(
                PlaylistSong, Song.id == PlaylistSong.song_id
            ).join(
                Playlist, PlaylistSong.playlist_id == Playlist.id
            ).filter(
                and_(
                    Playlist.owner_id == user_id,
                    AnalysisResult.status == 'in_progress'
                )
            ).first()
            
            if active_analysis:
                return False  # Don't start if analysis is already running
            
            # Check last analysis time (optional rate limiting)
            last_analysis = db.session.query(AnalysisResult).join(
                Song, AnalysisResult.song_id == Song.id
            ).join(
                PlaylistSong, Song.id == PlaylistSong.song_id
            ).join(
                Playlist, PlaylistSong.playlist_id == Playlist.id
            ).filter(
                Playlist.owner_id == user_id
            ).order_by(AnalysisResult.created_at.desc()).first()
            
            if last_analysis:
                time_since_last = datetime.utcnow() - last_analysis.created_at
                if time_since_last < timedelta(hours=min_interval_hours):
                    return False  # Too soon since last analysis
            
            return True
            
        except Exception as e:
            current_app.logger.error(f"Error checking if background analysis should start for user {user_id}: {e}")
            return False 