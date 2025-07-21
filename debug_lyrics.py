#!/usr/bin/env python3
"""
Debug script to test lyrics fetching system
"""
import os
import sys
sys.path.append('/app')

from app import create_app
from app.utils.lyrics.lyrics_fetcher import LyricsFetcher
from app.models.models import Song

def test_lyrics_fetching():
    print("=== LYRICS FETCHING DEBUG ===")
    
    # Check environment variables
    genius_key = os.getenv('LYRICSGENIUS_API_KEY')
    genius_token = os.getenv('GENIUS_ACCESS_TOKEN')
    
    print(f"\n1. Environment Check:")
    print(f"   LYRICSGENIUS_API_KEY: {'✅ Set' if genius_key else '❌ Not set'}")
    print(f"   GENIUS_ACCESS_TOKEN: {'✅ Set' if genius_token else '❌ Not set'}")
    
    if genius_key:
        print(f"   Key preview: {genius_key[:10]}...")
    
    # Test lyrics fetcher initialization
    print(f"\n2. LyricsFetcher Initialization:")
    try:
        fetcher = LyricsFetcher()
        print("   ✅ LyricsFetcher initialized successfully")
        
        # Check providers
        print(f"   Available providers: {len(fetcher.providers)}")
        for i, provider in enumerate(fetcher.providers):
            print(f"     {i+1}. {provider.__class__.__name__}")
            
    except Exception as e:
        print(f"   ❌ Failed to initialize LyricsFetcher: {e}")
        return
    
    # Test lyrics fetching with a known Christian song
    print(f"\n3. Test Lyrics Fetching:")
    test_songs = [
        ("Amazing Grace", "John Newton"),
        ("How Great Thou Art", "Stuart Hine"),
        ("Blessed Assurance", "Fanny Crosby")
    ]
    
    for title, artist in test_songs:
        print(f"\n   Testing: '{title}' by {artist}")
        try:
            lyrics = fetcher.fetch_lyrics(title, artist)
            if lyrics and len(lyrics.strip()) > 50:
                print(f"   ✅ Found lyrics ({len(lyrics)} chars)")
                print(f"   Preview: {lyrics[:100]}...")
            elif lyrics:
                print(f"   ⚠️  Found short lyrics ({len(lyrics)} chars): {lyrics}")
            else:
                print(f"   ❌ No lyrics found")
        except Exception as e:
            print(f"   ❌ Error fetching lyrics: {e}")
    
    # Test with actual songs from database
    print(f"\n4. Database Songs Test:")
    app = create_app()
    with app.app_context():
        songs = Song.query.limit(3).all()
        for song in songs:
            print(f"\n   Testing DB song: '{song.title}' by {song.artist}")
            try:
                lyrics = fetcher.fetch_lyrics(song.title, song.artist)
                if lyrics and len(lyrics.strip()) > 50:
                    print(f"   ✅ Found lyrics ({len(lyrics)} chars)")
                elif lyrics:
                    print(f"   ⚠️  Found short lyrics ({len(lyrics)} chars)")
                else:
                    print(f"   ❌ No lyrics found")
                    
                # Check current lyrics in database
                if song.lyrics:
                    print(f"   📁 DB has lyrics: {len(song.lyrics)} chars")
                else:
                    print(f"   📁 DB lyrics: None")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    test_lyrics_fetching() 