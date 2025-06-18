"""
Analysis service for song content analysis

Wraps the existing analysis engine and manages background job queuing
"""

from datetime import datetime, timezone
from typing import Optional

from flask import current_app
from flask_rq2 import RQ
from rq import get_current_job

from .. import db
from ..models import Song, AnalysisResult, Playlist, PlaylistSong
from ..utils.analysis import analyze_song_content
from ..utils.lyrics.lyrics_fetcher import LyricsFetcher


class AnalysisService:
    """Service for managing song content analysis"""
    
    def __init__(self):
        self.rq = RQ()
        self.lyrics_fetcher = LyricsFetcher()
    
    def analyze_song(self, song: Song, force: bool = False) -> bool:
        """Queue a song for analysis"""
        # Check if already analyzed recently (unless forced)
        if not force:
            recent_analysis = AnalysisResult.query.filter_by(
                song_id=song.id,
                status='completed'
            ).order_by(AnalysisResult.created_at.desc()).first()
            
            if recent_analysis:
                # Don't re-analyze if completed within last 7 days
                days_since = (datetime.now(timezone.utc) - recent_analysis.created_at).days
                if days_since < 7:
                    return False
        
        # Create pending analysis record
        analysis = AnalysisResult(
            song_id=song.id,
            status='pending',
            created_at=datetime.now(timezone.utc)
        )
        db.session.add(analysis)
        db.session.commit()
        
        # Queue the analysis job
        try:
            job = self.rq.get_queue().enqueue(
                _analyze_song_task,
                song.id,
                analysis.id,
                timeout=300  # 5 minutes timeout
            )
            current_app.logger.info(f'Queued analysis job {job.id} for song {song.id}')
            return True
        except Exception as e:
            current_app.logger.error(f'Failed to queue analysis for song {song.id}: {e}')
            analysis.status = 'failed'
            analysis.error_message = str(e)
            db.session.commit()
            return False
    
    def analyze_playlist(self, playlist: Playlist, force: bool = False) -> int:
        """Queue all songs in a playlist for analysis"""
        songs = db.session.query(Song).join(PlaylistSong).filter(
            PlaylistSong.playlist_id == playlist.id
        ).all()
        
        queued_count = 0
        for song in songs:
            if self.analyze_song(song, force=force):
                queued_count += 1
        
        return queued_count
    
    def analyze_user_collection(self, user_id: int, force: bool = False) -> int:
        """Queue all songs in a user's collection for analysis"""
        songs = db.session.query(Song).join(PlaylistSong).join(Playlist).filter(
            Playlist.user_id == user_id
        ).distinct().all()
        
        queued_count = 0
        for song in songs:
            if self.analyze_song(song, force=force):
                queued_count += 1
        
        return queued_count
    
    def get_analysis_status(self, song_id: int) -> Optional[AnalysisResult]:
        """Get the latest analysis result for a song"""
        return AnalysisResult.query.filter_by(song_id=song_id).order_by(
            AnalysisResult.created_at.desc()
        ).first()
    
    def batch_analyze(self, songs: list, force: bool = False) -> list:
        """Analyze multiple songs and return list of results"""
        results = []
        for song in songs:
            result = self.analyze_song(song, force=force)
            results.append(result)
        return results


def _analyze_song_task(song_id: int, analysis_id: int):
    """Background task to analyze a song"""
    from flask import current_app
    from .. import db
    
    # Get the song and analysis record
    song = Song.query.get(song_id)
    analysis = AnalysisResult.query.get(analysis_id)
    
    if not song or not analysis:
        current_app.logger.error(f'Song {song_id} or analysis {analysis_id} not found')
        return
    
    try:
        # Update status to in_progress
        analysis.status = 'processing'
        db.session.commit()
        
        # Fetch lyrics if not available
        if not song.lyrics:
            try:
                lyrics_fetcher = LyricsFetcher()
                lyrics = lyrics_fetcher.fetch_lyrics(song.artist, song.name)
                if lyrics:
                    song.lyrics = lyrics
                    db.session.commit()
            except Exception as e:
                current_app.logger.warning(f'Failed to fetch lyrics for song {song_id}: {e}')
        
        # Perform analysis
        if song.lyrics:
            result = analyze_song_content(song.lyrics, song.name, song.artist)
            
            # Update analysis record with results
            analysis.score = result.get('final_score', 0)
            analysis.concern_level = result.get('concern_level', 'unknown')
            analysis.themes = result.get('detected_themes', [])
            analysis.concerns = result.get('flagged_content', [])
            analysis.problematic_content = result.get('details', {})
            analysis.status = 'completed'
        else:
            # No lyrics available
            analysis.score = 85  # Default neutral score
            analysis.concern_level = 'low'
            analysis.themes = []
            analysis.concerns = []
            analysis.problematic_content = {'note': 'No lyrics available for analysis'}
            analysis.status = 'completed'
        
        db.session.commit()
        
        current_app.logger.info(f'Completed analysis for song {song_id}: score={analysis.score}')
        
    except Exception as e:
        current_app.logger.error(f'Analysis failed for song {song_id}: {e}')
        analysis.status = 'failed'
        analysis.error_message = str(e)
        db.session.commit() 