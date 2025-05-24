#!/usr/bin/env python3
"""
Script to calculate and update playlist scores for existing playlists.
This should help fix the issue where playlists show "Not Analyzed" instead of their actual scores.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.models import Playlist, Song, AnalysisResult
from app.utils.database import get_all_by_filter, safe_commit  # Add SQLAlchemy 2.0 utilities

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
        
        return average_score
        
    except Exception as e:
        print(f"Error calculating playlist score for {playlist.id}: {e}")
        return None

def main():
    app = create_app()
    
    with app.app_context():
        # Get all playlists using SQLAlchemy 2.0 pattern
        playlists = get_all_by_filter(Playlist)
        print(f"Found {len(playlists)} playlists to check")
        
        updated_count = 0
        for playlist in playlists:
            # Calculate score
            score = calculate_playlist_score(playlist)
            
            if score is not None:
                old_score = playlist.overall_alignment_score
                playlist.overall_alignment_score = score
                
                print(f"Playlist '{playlist.name}': {old_score} -> {score:.1f}")
                updated_count += 1
            else:
                analyzed_songs_count = sum(1 for song in playlist.songs 
                                         if song.analysis_results.first() and 
                                         song.analysis_results.first().status == 'completed')
                print(f"Playlist '{playlist.name}': No analyzed songs (has {analyzed_songs_count} analyzed out of {len(playlist.songs)} total)")
        
        if updated_count > 0:
            success = safe_commit(f"Failed to commit playlist score updates")
            if success:
                print(f"\nSuccessfully updated {updated_count} playlist scores!")
            else:
                print(f"\nError committing changes.")
        else:
            print("\nNo playlist scores to update.")

if __name__ == '__main__':
    main() 