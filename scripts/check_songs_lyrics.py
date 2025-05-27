#!/usr/bin/env python3
"""
Check the current state of songs and their analysis in the database.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.models.models import Song, AnalysisResult
from app.extensions import db
import json

def check_songs_state():
    app = create_app()
    with app.app_context():
        # Check songs with lyrics vs without
        total_songs = db.session.query(Song).count()
        songs_with_lyrics = db.session.query(Song).filter(
            Song.lyrics.isnot(None), 
            Song.lyrics != '', 
            Song.lyrics != 'Lyrics not available'
        ).count()
        
        print(f'Total songs: {total_songs}')
        print(f'Songs with lyrics: {songs_with_lyrics}')
        print(f'Songs without lyrics: {total_songs - songs_with_lyrics}')
        
        # Check a few sample songs
        print('\nSample songs:')
        sample_songs = db.session.query(Song).limit(10).all()
        for song in sample_songs:
            has_lyrics = song.lyrics and song.lyrics not in ['', 'Lyrics not available']
            analysis = db.session.query(AnalysisResult).filter_by(song_id=song.id, status='completed').first()
            has_analysis = analysis is not None
            
            if analysis and analysis.biblical_themes:
                try:
                    biblical_themes = json.loads(analysis.biblical_themes) if isinstance(analysis.biblical_themes, str) else analysis.biblical_themes
                    theme_count = len(biblical_themes) if biblical_themes else 0
                except:
                    theme_count = 0
            else:
                theme_count = 0
                
            print(f'  {song.title[:30]:30} | Lyrics: {str(has_lyrics):5} | Analysis: {str(has_analysis):5} | Themes: {theme_count}')
        
        # Find one song with lyrics for testing
        song_with_lyrics = db.session.query(Song).filter(
            Song.lyrics.isnot(None), 
            Song.lyrics != '', 
            Song.lyrics != 'Lyrics not available'
        ).first()
        
        if song_with_lyrics:
            print(f'\nFound song with lyrics: "{song_with_lyrics.title}" by {song_with_lyrics.artist}')
            print(f'Lyrics preview: {song_with_lyrics.lyrics[:100]}...')
            
            analysis = db.session.query(AnalysisResult).filter_by(song_id=song_with_lyrics.id, status='completed').first()
            if analysis:
                print(f'Analysis version: {getattr(analysis, "analysis_version", "unknown")}')
                print(f'Biblical themes stored: {bool(analysis.biblical_themes)}')
                print(f'Supporting scripture stored: {bool(analysis.supporting_scripture)}')
                
                if analysis.biblical_themes:
                    try:
                        themes = json.loads(analysis.biblical_themes) if isinstance(analysis.biblical_themes, str) else analysis.biblical_themes
                        print(f'Biblical themes count: {len(themes) if themes else 0}')
                        if themes:
                            print(f'First theme: {themes[0]}')
                    except Exception as e:
                        print(f'Error parsing biblical themes: {e}')
                
            else:
                print('No completed analysis found')

if __name__ == '__main__':
    check_songs_state() 