"""
Shared utility functions for blueprints.

This module contains functions that are used across multiple blueprints
to avoid code duplication and maintain consistency.
"""

from flask import current_app
from app import db


def calculate_playlist_score(playlist):
    """Calculate the overall score for a playlist based on analyzed songs."""
    try:
        # Get all analysis results for songs in this playlist
        analyzed_songs = []
        for song in playlist.songs:
            analysis_result = song.analysis_results.first()
            if analysis_result and analysis_result.status == 'completed' and analysis_result.score is not None:
                analyzed_songs.append(analysis_result.score)
        
        if not analyzed_songs:
            return None  # No analyzed songs
            
        # Calculate average score (analysis results are 0-100)
        average_score = sum(analyzed_songs) / len(analyzed_songs)
        
        # Update the playlist's overall_alignment_score
        playlist.overall_alignment_score = average_score
        
        return average_score
        
    except Exception as e:
        current_app.logger.error(f"Error calculating playlist score for {playlist.id}: {e}")
        return None


def update_playlist_score(playlist_id):
    """Update the score for a specific playlist.
    
    This is a wrapper around calculate_playlist_score that fetches
    the playlist and commits the changes.
    """
    try:
        from app.models import Playlist
        playlist = Playlist.query.get(playlist_id)
        if playlist:
            calculate_playlist_score(playlist)
            db.session.commit()
            return playlist.overall_alignment_score
        return None
    except Exception as e:
        current_app.logger.error(f"Error updating playlist score for {playlist_id}: {e}")
        db.session.rollback()
        return None 