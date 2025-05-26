#!/usr/bin/env python3
"""
Debug script to check album art URL storage in the database.
This verifies that album art URLs are being properly stored and retrieved.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.models.models import Song, Playlist, User
from app.extensions import db

def check_album_art_storage():
    """Check album art URL storage in the database."""
    
    app = create_app()
    
    with app.app_context():
        # Check total songs in database
        total_songs = db.session.query(Song).count()
        print(f"Total songs in database: {total_songs}")
        
        # Check songs with album art URLs
        songs_with_album_art = db.session.query(Song).filter(
            Song.album_art_url.isnot(None), 
            Song.album_art_url != ''
        ).count()
        print(f"Songs with album art URLs: {songs_with_album_art}")
        
        # Calculate percentage
        if total_songs > 0:
            percentage = (songs_with_album_art / total_songs) * 100
            print(f"Percentage with album art: {percentage:.1f}%")
        
        # Show some examples
        print("\nExample songs with album art URLs:")
        sample_songs = db.session.query(Song).filter(
            Song.album_art_url.isnot(None), 
            Song.album_art_url != ''
        ).limit(5).all()
        
        for song in sample_songs:
            print(f"- {song.title} by {song.artist}")
            print(f"  Album Art URL: {song.album_art_url[:80]}...")
            print()
        
        # Check for songs without album art
        songs_without_album_art = db.session.query(Song).filter(
            db.or_(Song.album_art_url.is_(None), Song.album_art_url == '')
        ).limit(5).all()
        
        if songs_without_album_art:
            print("\nExample songs WITHOUT album art URLs:")
            for song in songs_without_album_art:
                print(f"- {song.title} by {song.artist}")
                print(f"  Album Art URL: {song.album_art_url}")
                print()

if __name__ == "__main__":
    check_album_art_storage() 