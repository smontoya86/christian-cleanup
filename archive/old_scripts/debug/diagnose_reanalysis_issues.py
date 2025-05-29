#!/usr/bin/env python3
"""
Diagnostic script to investigate re-analysis and progress bar issues
"""

import os
import sys
import json
import time
from datetime import datetime
import argparse

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models.models import User, Playlist, Song, AnalysisResult
from app.extensions import db, rq
import traceback

def get_user_by_identifier(identifier):
    """Get user by ID or Spotify ID"""
    try:
        # Try as integer ID first
        user_id = int(identifier)
        user = User.query.get(user_id)
        if user:
            return user
    except ValueError:
        # Not an integer, try as Spotify ID
        user = User.query.filter_by(spotify_id=identifier).first()
        if user:
            return user
    
    # Try as display name
    user = User.query.filter_by(display_name=identifier).first()
    return user

def diagnose_reanalysis_issues(user_identifier=None):
    """Comprehensive diagnosis of re-analysis behavior"""
    app = create_app()
    
    with app.app_context():
        try:
            print("=" * 80)
            print("CHRISTIAN MUSIC CURATOR - RE-ANALYSIS DIAGNOSTIC")
            print("=" * 80)
            
            # Get user by identifier or use first user as fallback
            if user_identifier:
                user = get_user_by_identifier(user_identifier)
                if not user:
                    print(f"❌ User not found with identifier: {user_identifier}")
                    print("Available users:")
                    users = User.query.limit(5).all()
                    for u in users:
                        print(f"   - ID: {u.id}, Spotify ID: {u.spotify_id}, Display Name: {u.display_name}")
                    return
            else:
                user = User.query.first()
                if not user:
                    print("❌ No users found in database")
                    return
                print(f"⚠️  No user specified, using first user: {user.display_name} (ID: {user.id})")
                
            print(f"\n📊 ANALYZING USER: {user.display_name} (ID: {user.id}, Spotify ID: {user.spotify_id})")
            print("-" * 50)
            
            # 1. Current State Analysis
            print("\n1️⃣ CURRENT DATABASE STATE:")
            total_playlists = user.playlists.count()
            print(f"   Total Playlists: {total_playlists}")
            
            # Get all songs across user's playlists
            from app.models.models import PlaylistSong
            from sqlalchemy import func
            
            total_songs_result = db.session.query(func.count(PlaylistSong.song_id.distinct())).join(
                Song, PlaylistSong.song_id == Song.id
            ).filter(PlaylistSong.playlist_id.in_([p.id for p in user.playlists])).scalar()
            
            total_songs = total_songs_result or 0
            print(f"   Total Unique Songs: {total_songs}")
            
            # Count current analysis results
            analyzed_songs_result = db.session.query(func.count(AnalysisResult.song_id.distinct())).join(
                Song, AnalysisResult.song_id == Song.id
            ).join(
                PlaylistSong, Song.id == PlaylistSong.song_id
            ).filter(PlaylistSong.playlist_id.in_([p.id for p in user.playlists])).scalar()
            
            analyzed_songs = analyzed_songs_result or 0
            pending_songs = total_songs - analyzed_songs
            
            print(f"   Analyzed Songs: {analyzed_songs}")
            print(f"   Pending Songs: {pending_songs}")
            
            if total_songs > 0:
                progress_percentage = (analyzed_songs / total_songs) * 100
                print(f"   Current Progress: {progress_percentage:.1f}%")
            
            # 2. Queue Analysis
            print("\n2️⃣ BACKGROUND QUEUE ANALYSIS:")
            try:
                # Get queue status
                queue = rq.get_queue()
                print(f"   Queue Length: {len(queue)}")
                print(f"   Failed Jobs: {queue.failed_job_registry.count}")
                print(f"   Scheduled Jobs: {queue.scheduled_job_registry.count}")
                print(f"   Started Jobs: {queue.started_job_registry.count}")
                
                # List active jobs
                started_jobs = queue.started_job_registry.get_job_ids()
                if started_jobs:
                    print(f"   Active Job IDs: {started_jobs}")
                    for job_id in started_jobs[:3]:  # Show first 3
                        try:
                            job = queue.fetch_job(job_id)
                            if job:
                                print(f"     - {job.func_name}: {job.args[:2] if job.args else 'no args'}")
                        except:
                            pass
                else:
                    print("   No active jobs currently running")
                    
            except Exception as e:
                print(f"   ❌ Error checking queue: {e}")
            
            # 3. Progress API Test
            print("\n3️⃣ PROGRESS API TEST:")
            try:
                with app.test_client() as client:
                    # Simulate login
                    with client.session_transaction() as sess:
                        sess['_user_id'] = str(user.id)
                        sess['_fresh'] = True
                    
                    # Test the analysis status API
                    response = client.get('/api/analysis/status')
                    print(f"   Status Code: {response.status_code}")
                    
                    if response.status_code == 200:
                        data = response.get_json()
                        print(f"   API Response:")
                        print(f"     - Total Songs: {data.get('total_songs', 'N/A')}")
                        print(f"     - Completed: {data.get('completed', 'N/A')}")
                        print(f"     - In Progress: {data.get('in_progress', 'N/A')}")
                        print(f"     - Pending: {data.get('pending', 'N/A')}")
                        print(f"     - Progress %: {data.get('progress_percentage', 'N/A')}")
                        print(f"     - Has Active Analysis: {data.get('has_active_analysis', 'N/A')}")
                        print(f"     - Current Song: {data.get('current_song', 'N/A')}")
                    else:
                        print(f"   ❌ API Error: {response.get_data(as_text=True)}")
                        
            except Exception as e:
                print(f"   ❌ Error testing API: {e}")
            
            # 4. Analysis of Admin Re-analysis Function
            print("\n4️⃣ ADMIN RE-ANALYSIS FUNCTION ANALYSIS:")
            print("   Current Implementation Issues:")
            print("   ❌ Queues one job per playlist (causes multiple 30+ min messages)")
            print("   ❌ Each job has 30-minute timeout")
            print("   ❌ No coordination between playlist jobs")
            print("   ❌ Progress bar resets when analysis results are cleared")
            
            # 5. Recommended Solutions
            print("\n5️⃣ RECOMMENDED SOLUTIONS:")
            print("   ✅ Single coordinated re-analysis job")
            print("   ✅ Shorter timeout per playlist, longer overall timeout")
            print("   ✅ Preserve progress indication during re-analysis")
            print("   ✅ Clear status messaging about what's happening")
            
            # 6. Simulate Better Re-analysis
            print("\n6️⃣ TESTING IMPROVED RE-ANALYSIS APPROACH:")
            print("   This would:")
            playlists = user.playlists.all()
            estimated_time_per_playlist = 2  # minutes
            total_estimated_time = len(playlists) * estimated_time_per_playlist
            
            print(f"   - Process {len(playlists)} playlists sequentially")
            print(f"   - Estimated time: {total_estimated_time} minutes")
            print(f"   - Show progress updates during processing")
            print(f"   - Maintain overall progress indicator")
            
            # 7. Progress Bar JavaScript Test
            print("\n7️⃣ DASHBOARD PROGRESS BAR BEHAVIOR:")
            print("   JavaScript calls: /api/analysis/status every 3 seconds")
            print("   Expected behavior:")
            if progress_percentage < 100:
                print("   ✅ Progress bar should be visible")
                print(f"   ✅ Should show {progress_percentage:.1f}% progress")
            else:
                print("   ⚠️  Progress bar should be hidden (100% complete)")
            
            # 8. Solution Implementation Preview
            print("\n8️⃣ PROPOSED IMPLEMENTATION FIX:")
            print("   1. Modify admin_reanalyze_all_songs to queue single job")
            print("   2. Create master re-analysis function that processes playlists sequentially")
            print("   3. Update progress tracking to handle re-analysis state")
            print("   4. Improve user messaging during re-analysis")
            
            print("\n" + "=" * 80)
            print("DIAGNOSIS COMPLETE - ISSUES IDENTIFIED")
            print("=" * 80)
            
        except Exception as e:
            print(f"❌ Error during diagnosis: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the re-analysis diagnostic script")
    parser.add_argument("--user", type=str, help="User ID, Spotify ID, or display name")
    args = parser.parse_args()
    diagnose_reanalysis_issues(args.user) 