#!/usr/bin/env python3
"""
Fix No Lyrics Analyses

This script addresses the issue where 97% of song analyses have no lyrics.
It clears all analyses with missing lyrics and triggers re-analysis with
proper lyrics fetching enabled.
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import func

from app import create_app
from app.extensions import db
from app.models.models import AnalysisResult, Playlist, Song, User
from app.services.unified_analysis_service import UnifiedAnalysisService
from app.utils.lyrics.lyrics_fetcher import LyricsFetcher


def clear_no_lyrics_analyses():
    """Clear all analyses for songs that have no lyrics or empty lyrics."""

    app = create_app()
    with app.app_context():
        print("🧹 Clearing No-Lyrics Analyses")
        print("=" * 60)

        # Find songs without lyrics
        songs_without_lyrics = (
            db.session.query(Song.id)
            .filter(
                db.or_(
                    Song.lyrics == None,
                    Song.lyrics == "",
                    Song.lyrics == "No lyrics found",
                    func.length(Song.lyrics) <= 10,
                )
            )
            .subquery()
        )

        # Count analyses for songs without lyrics
        no_lyrics_count = (
            db.session.query(AnalysisResult)
            .filter(AnalysisResult.song_id.in_(db.session.query(songs_without_lyrics.c.id)))
            .count()
        )

        print(f"📊 Found {no_lyrics_count:,} analyses for songs with no/minimal lyrics")

        if no_lyrics_count == 0:
            print("✅ No analyses to clear!")
            return

        # Delete analyses for songs without lyrics
        deleted = (
            db.session.query(AnalysisResult)
            .filter(AnalysisResult.song_id.in_(db.session.query(songs_without_lyrics.c.id)))
            .delete(synchronize_session=False)
        )

        db.session.commit()
        print(f"🗑️  Deleted {deleted:,} no-lyrics analyses")

        # Count remaining analyses
        remaining = db.session.query(AnalysisResult).count()
        print(f"📈 Remaining analyses: {remaining:,}")


def test_lyrics_fetching():
    """Test lyrics fetching functionality."""

    app = create_app()
    with app.app_context():
        print("\n🔍 Testing Lyrics Fetching")
        print("=" * 60)

        # Check API key
        genius_key = os.getenv("LYRICSGENIUS_API_KEY")
        if not genius_key or genius_key == "your-genius-api-key-here":
            print("❌ No valid Genius API key found!")
            return False

        print("✅ Genius API key configured")

        # Test lyrics fetcher
        lyrics_fetcher = LyricsFetcher()

        # Test with a known Christian song
        test_songs = [
            ("Amazing Grace", "Chris Tomlin"),
            ("How Great Thou Art", "Carrie Underwood"),
            ("What a Beautiful Name", "Hillsong Worship"),
        ]

        success_count = 0
        for title, artist in test_songs:
            print(f"🎵 Testing: '{title}' by {artist}")
            try:
                lyrics = lyrics_fetcher.fetch_lyrics(title, artist)
                if lyrics and len(lyrics.strip()) > 50:
                    print(f"   ✅ SUCCESS: Found {len(lyrics)} characters")
                    success_count += 1
                else:
                    print("   ❌ No lyrics found")
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")

        print(f"\n📊 Lyrics fetching success rate: {success_count}/{len(test_songs)}")
        return success_count > 0


def trigger_reanalysis(user_id=None):
    """Trigger re-analysis for songs without lyrics."""

    app = create_app()
    with app.app_context():
        print("\n🚀 Triggering Re-Analysis")
        print("=" * 60)

        if user_id is None:
            # Find the first user with playlists
            user = db.session.query(User).join(Playlist).first()
            if not user:
                print("❌ No users with playlists found!")
                return
            user_id = user.id
            print(f"📋 Using user: {user.display_name} (ID: {user_id})")

        # Use the unified analysis service
        analysis_service = UnifiedAnalysisService()

        try:
            # Start background analysis
            job_id = analysis_service.enqueue_background_analysis(user_id)
            print("✅ Background analysis started!")
            print(f"🆔 Job ID: {job_id}")
            print("🌐 Monitor progress at: http://localhost:5001/dashboard")

        except Exception as e:
            print(f"❌ Failed to start analysis: {str(e)}")


def main():
    """Main function to fix no-lyrics analyses."""

    print("🎵 Christian Cleanup - Fix No Lyrics Analyses")
    print("=" * 80)

    # Step 1: Clear no-lyrics analyses
    clear_no_lyrics_analyses()

    # Step 2: Test lyrics fetching
    if not test_lyrics_fetching():
        print("\n❌ Lyrics fetching test failed. Check API configuration.")
        return

    # Step 3: Trigger re-analysis
    trigger_reanalysis()

    print("\n✅ Process completed!")
    print("🔄 Monitor the dashboard for analysis progress")
    print("📊 New analyses should include lyrics from Genius API")


if __name__ == "__main__":
    main()
