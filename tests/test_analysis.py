#!/usr/bin/env python3
"""
Test script to enqueue some songs for analysis to verify the worker is processing correctly.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.services.unified_analysis_service import UnifiedAnalysisService
from app.models.models import Song
from app.utils.database import get_all_by_filter  # Add SQLAlchemy 2.0 utilities

def test_song_analysis():
    app = create_app()
    
    with app.app_context():
        # Get a few songs to analyze using SQLAlchemy 2.0 pattern
        songs = get_all_by_filter(Song)[:5]  # Get first 5 songs
        print(f"Found {len(songs)} songs to test analysis")
        
        # Initialize unified analysis service
        analysis_service = UnifiedAnalysisService()
        
        for song in songs:
            print(f"Enqueuing analysis for: {song.title} by {song.artist}")
            # Use the unified analysis service
            analysis_service.enqueue_analysis_job(song.id)
            
        print(f"✅ Processed {len(songs)} songs for analysis")
        print("Analysis should be complete now...")

if __name__ == '__main__':
    test_song_analysis()
