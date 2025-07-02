#!/usr/bin/env python3
"""
Test Lyrics Fetching

This script tests the lyrics fetching functionality to identify why 97% of songs
have no lyrics and verify that the system can fetch lyrics when properly configured.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.utils.lyrics.lyrics_fetcher import LyricsFetcher
from app.models.models import Song, User, Playlist, PlaylistSong
from app.extensions import db

def test_lyrics_fetching():
    """Test lyrics fetching functionality."""
    
    app = create_app()
    with app.app_context():
        print("🔍 Testing Lyrics Fetching Functionality")
        print("=" * 60)
        
        # Check environment variables
        genius_key = os.getenv('LYRICSGENIUS_API_KEY')
        genius_token = os.getenv('GENIUS_ACCESS_TOKEN')
        
        print(f"📋 Environment Variables:")
        print(f"   LYRICSGENIUS_API_KEY: {'✅ Set' if genius_key else '❌ Not set'}")
        print(f"   GENIUS_ACCESS_TOKEN: {'✅ Set' if genius_token else '❌ Not set'}")
        
        if genius_key:
            print(f"   LYRICSGENIUS_API_KEY value: {genius_key[:10]}...")
        if genius_token:
            print(f"   GENIUS_ACCESS_TOKEN value: {genius_token[:10]}...")
        
        # Initialize lyrics fetcher
        print(f"\n🔧 Initializing LyricsFetcher...")
        fetcher = LyricsFetcher()
        
        # Check what providers are available
        print(f"📊 Available providers: {len(fetcher.providers)}")
        for i, provider in enumerate(fetcher.providers):
            print(f"   {i+1}. {provider.get_provider_name()}")
        
        # Test with some sample songs
        test_songs = [
            ("Amazing Grace", "Chris Tomlin"),
            ("How Great Thou Art", "Chris Tomlin"), 
            ("Oceans (Where Feet May Fail)", "Hillsong UNITED"),
            ("What a Beautiful Name", "Hillsong Worship"),
            ("Good Good Father", "Chris Tomlin")
        ]
        
        print(f"\n🎵 Testing lyrics fetching with {len(test_songs)} sample songs:")
        
        successful_fetches = 0
        failed_fetches = 0
        
        for title, artist in test_songs:
            print(f"\n   Testing: '{title}' by {artist}")
            try:
                lyrics = fetcher.fetch_lyrics(title, artist)
                if lyrics and len(lyrics.strip()) > 10:
                    print(f"   ✅ SUCCESS: Found {len(lyrics)} characters")
                    print(f"      Preview: {lyrics[:100]}...")
                    successful_fetches += 1
                else:
                    print(f"   ❌ FAILED: No lyrics found")
                    failed_fetches += 1
            except Exception as e:
                print(f"   ❌ ERROR: {e}")
                failed_fetches += 1
        
        print(f"\n📊 Results Summary:")
        print(f"   ✅ Successful fetches: {successful_fetches}/{len(test_songs)}")
        print(f"   ❌ Failed fetches: {failed_fetches}/{len(test_songs)}")
        print(f"   Success rate: {(successful_fetches/len(test_songs)*100):.1f}%")
        
        # Test with actual songs from database
        print(f"\n🗄️  Testing with actual database songs...")
        
        # Get Sam's user
        sam = User.query.filter_by(email='smontoya86@gmail.com').first()
        if not sam:
            print("❌ User not found")
            return
        
        # Get a few songs without lyrics
        songs_without_lyrics = db.session.query(Song).join(
            PlaylistSong, Song.id == PlaylistSong.song_id
        ).join(
            Playlist, PlaylistSong.playlist_id == Playlist.id
        ).filter(
            Playlist.owner_id == sam.id,
            db.or_(Song.lyrics.is_(None), Song.lyrics == '')
        ).limit(5).all()
        
        print(f"   Found {len(songs_without_lyrics)} songs without lyrics")
        
        db_successful_fetches = 0
        db_failed_fetches = 0
        
        for song in songs_without_lyrics:
            print(f"\n   Testing DB song: '{song.title}' by {song.artist}")
            try:
                lyrics = fetcher.fetch_lyrics(song.title, song.artist)
                if lyrics and len(lyrics.strip()) > 10:
                    print(f"   ✅ SUCCESS: Found {len(lyrics)} characters")
                    print(f"      Preview: {lyrics[:100]}...")
                    db_successful_fetches += 1
                else:
                    print(f"   ❌ FAILED: No lyrics found")
                    db_failed_fetches += 1
            except Exception as e:
                print(f"   ❌ ERROR: {e}")
                db_failed_fetches += 1
        
        print(f"\n📊 Database Songs Results:")
        print(f"   ✅ Successful fetches: {db_successful_fetches}/{len(songs_without_lyrics)}")
        print(f"   ❌ Failed fetches: {db_failed_fetches}/{len(songs_without_lyrics)}")
        if len(songs_without_lyrics) > 0:
            print(f"   Success rate: {(db_successful_fetches/len(songs_without_lyrics)*100):.1f}%")
        
        # Provide recommendations
        print(f"\n💡 Recommendations:")
        
        if not genius_key and not genius_token:
            print("   1. ⚠️  Add a Genius API key to your .env file")
            print("      - Go to https://genius.com/api-clients")
            print("      - Sign up for a free account")
            print("      - Create a new API client")
            print("      - Generate a Client Access Token")
            print("      - Add LYRICSGENIUS_API_KEY=your_token_here to .env")
        
        if successful_fetches == 0 and db_successful_fetches == 0:
            print("   2. ⚠️  No lyrics were fetched successfully")
            print("      - Check your internet connection")
            print("      - Verify API key is valid")
            print("      - Check if lyrics providers are accessible")
        
        if successful_fetches > 0 or db_successful_fetches > 0:
            print("   2. ✅ Lyrics fetching is working!")
            print("      - You can now re-run analysis to fetch missing lyrics")
            print("      - The analysis will automatically fetch lyrics for songs that need them")

if __name__ == "__main__":
    test_lyrics_fetching() 