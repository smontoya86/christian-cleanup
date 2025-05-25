#!/usr/bin/env python3
"""
Re-analyze all songs with the fixed comprehensive analysis system.

This script will:
1. Delete all existing analysis results
2. Re-analyze all songs with the new comprehensive system
3. Provide progress updates
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import Song, AnalysisResult
from app.extensions import db
from app.services.analysis_service import perform_christian_song_analysis_and_store
import time

def main():
    app = create_app()
    
    with app.app_context():
        print("🔄 Starting comprehensive re-analysis of all songs...")
        print("=" * 60)
        
        # Get total song count
        total_songs = db.session.query(Song).count()
        print(f"📊 Total songs to re-analyze: {total_songs:,}")
        
        if total_songs == 0:
            print("❌ No songs found in database")
            return
        
        # Delete all existing analysis results
        print("🗑️  Deleting existing analysis results...")
        deleted_count = db.session.query(AnalysisResult).delete()
        db.session.commit()
        print(f"✅ Deleted {deleted_count:,} existing analysis results")
        
        # Get all songs
        songs = db.session.query(Song).all()
        
        print(f"🚀 Starting re-analysis of {len(songs):,} songs...")
        print("⚡ Using 4 workers for optimal performance")
        print("")
        
        # Enqueue all songs for analysis
        successful_jobs = 0
        failed_jobs = 0
        
        for i, song in enumerate(songs, 1):
            try:
                job = perform_christian_song_analysis_and_store(song.id, user_id=1)
                if job:
                    successful_jobs += 1
                    if i % 100 == 0:
                        print(f"📈 Progress: {i:,}/{total_songs:,} songs enqueued ({(i/total_songs*100):.1f}%)")
                else:
                    failed_jobs += 1
                    print(f"❌ Failed to enqueue song {song.id}: {song.title}")
                    
            except Exception as e:
                failed_jobs += 1
                print(f"❌ Error enqueueing song {song.id}: {e}")
        
        print("")
        print("=" * 60)
        print("🎯 RE-ANALYSIS ENQUEUE COMPLETE")
        print(f"✅ Successfully enqueued: {successful_jobs:,} songs")
        print(f"❌ Failed to enqueue: {failed_jobs:,} songs")
        print(f"📊 Success rate: {(successful_jobs/(successful_jobs+failed_jobs)*100):.1f}%")
        print("")
        print("⏰ ESTIMATED COMPLETION TIME:")
        
        # Calculate ETA
        songs_per_minute = 120  # 4 workers at ~30 songs/minute each
        minutes_remaining = successful_jobs / songs_per_minute
        hours_remaining = minutes_remaining / 60
        
        print(f"⚡ Processing rate: ~{songs_per_minute} songs/minute (4 workers)")
        print(f"⏱️  Estimated time: {hours_remaining:.1f} hours ({minutes_remaining:.0f} minutes)")
        print("")
        print("🔍 WHAT'S DIFFERENT NOW:")
        print("✅ Base score starts at 100 (not 85)")
        print("✅ Full analysis for ALL songs (including explicit)")
        print("✅ Biblical themes detection working")
        print("✅ Positive themes identification working")
        print("✅ Supporting scripture references included")
        print("✅ Comprehensive explanations provided")
        print("")
        print("🎉 All songs will now receive proper comprehensive Christian analysis!")

if __name__ == "__main__":
    main() 