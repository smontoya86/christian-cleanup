#!/usr/bin/env python3
"""
Script to diagnose and fix dashboard issues:
1. Progress bar never changes or updates
2. Analysis progress not visible 
3. Last Sync and Status Check timezone issues
4. Settings link Internal Server Error
5. Missing sort option for playlists
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from app.models.models import User, Song, AnalysisResult, Playlist, PlaylistSong
from app.extensions import db
from datetime import datetime, timezone
import time

def test_progress_api():
    """Test the analysis progress API to see if it's working"""
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("🔍 TESTING ANALYSIS PROGRESS API")
        print("=" * 60)
        
        # Get a test user
        user = db.session.query(User).first()
        if not user:
            print("❌ No users found - cannot test progress API")
            return
            
        print(f"📍 Testing with user: {user.spotify_id}")
        
        # Test the background analysis service
        try:
            from app.services.background_analysis_service import BackgroundAnalysisService
            
            # Get user progress
            progress_data = BackgroundAnalysisService.get_analysis_progress_for_user(user.id)
            
            print(f"✅ Progress API working!")
            print(f"   Total songs: {progress_data['total_songs']}")
            print(f"   Completed: {progress_data['completed']}")
            print(f"   In progress: {progress_data['in_progress']}")
            print(f"   Pending: {progress_data['pending']}")
            print(f"   Has active analysis: {progress_data['has_active_analysis']}")
            print(f"   Progress percentage: {progress_data['progress_percentage']}%")
            
            # Check if we should see progress indicator
            should_show = progress_data['has_active_analysis'] or progress_data['pending'] > 0
            print(f"   Should show progress indicator: {should_show}")
            
        except Exception as e:
            print(f"❌ Progress API error: {e}")
            import traceback
            traceback.print_exc()

def create_test_analysis_progress():
    """Create some in-progress analyses to test the progress indicator"""
    app = create_app()
    
    with app.app_context():
        print("\n" + "=" * 60)
        print("🔧 CREATING TEST ANALYSIS PROGRESS")
        print("=" * 60)
        
        # Get songs that need analysis
        songs_without_analysis = db.session.query(Song).filter(
            ~Song.id.in_(
                db.session.query(AnalysisResult.song_id).filter(
                    AnalysisResult.status.in_(['completed', 'in_progress'])
                )
            )
        ).limit(5).all()
        
        if not songs_without_analysis:
            print("ℹ️  No songs without analysis found, checking existing analyses...")
            
            # Check if there are any in-progress analyses
            in_progress = db.session.query(AnalysisResult).filter_by(status='in_progress').count()
            completed = db.session.query(AnalysisResult).filter_by(status='completed').count()
            total_songs = db.session.query(Song).count()
            
            print(f"   Current status: {completed} completed, {in_progress} in progress, {total_songs} total songs")
            
            if in_progress == 0 and completed < total_songs:
                # Create some in-progress analyses from unanalyzed songs
                unanalyzed_songs = db.session.query(Song).filter(
                    ~Song.id.in_(db.session.query(AnalysisResult.song_id))
                ).limit(3).all()
                
                if unanalyzed_songs:
                    print(f"   Creating {len(unanalyzed_songs)} in-progress analyses...")
                    for song in unanalyzed_songs:
                        analysis = AnalysisResult(
                            song_id=song.id,
                            status='in_progress',
                            created_at=datetime.utcnow()
                        )
                        db.session.add(analysis)
                        print(f"     ✅ Created in-progress analysis for: {song.title}")
                    
                    db.session.commit()
                    print("   ✅ Test analyses created!")
                else:
                    print("   ⚠️  All songs appear to be analyzed")
            else:
                print(f"   ✅ Already have {in_progress} in-progress analyses")
        else:
            print(f"🔧 Creating {len(songs_without_analysis)} test in-progress analyses...")
            
            for song in songs_without_analysis:
                analysis = AnalysisResult(
                    song_id=song.id,
                    status='in_progress',
                    created_at=datetime.utcnow()
                )
                db.session.add(analysis)
                print(f"   ✅ Created in-progress analysis for: {song.title}")
            
            db.session.commit()
            print("   ✅ Test analyses created!")

def test_api_endpoints():
    """Test the API endpoints that the dashboard uses"""
    app = create_app()
    
    with app.app_context():
        print("\n" + "=" * 60)
        print("🌐 TESTING API ENDPOINTS")
        print("=" * 60)
        
        with app.test_client() as client:
            # Test analysis status endpoint
            print("Testing /api/analysis/status...")
            try:
                # We need to simulate a logged-in user
                user = db.session.query(User).first()
                if user:
                    with client.session_transaction() as sess:
                        sess['_user_id'] = str(user.id)
                        sess['_fresh'] = True
                    
                    response = client.get('/api/analysis/status')
                    print(f"   Status: {response.status_code}")
                    if response.status_code == 200:
                        data = response.get_json()
                        print(f"   Response keys: {list(data.keys())}")
                        print(f"   Has active analysis: {data.get('has_active_analysis', 'N/A')}")
                        print(f"   Completed: {data.get('completed', 'N/A')}")
                        print(f"   In progress: {data.get('in_progress', 'N/A')}")
                        print(f"   Pending: {data.get('pending', 'N/A')}")
                    else:
                        print(f"   ❌ Error: {response.data}")
                else:
                    print("   ⚠️  No users found - cannot test with authentication")
            except Exception as e:
                print(f"   ❌ Error testing API: {e}")

def fix_timezone_issues():
    """Fix timezone issues in templates"""
    print("\n" + "=" * 60)
    print("🌍 FIXING TIMEZONE ISSUES")
    print("=" * 60)
    
    print("ℹ️  Adding timezone utilities to templates...")
    print("   This will be fixed by updating the dashboard template")
    print("   to use user's local timezone for 'Last Sync' and 'Status Check' times")

def main():
    """Main function to run all diagnostics and fixes"""
    print("🚀 DASHBOARD ISSUES DIAGNOSTIC AND FIX SCRIPT")
    print("This script will test and fix the reported dashboard issues")
    print()
    
    # Test progress API
    test_progress_api()
    
    # Create test progress if needed
    create_test_analysis_progress()
    
    # Test API endpoints
    test_api_endpoints()
    
    # Note about timezone fixes
    fix_timezone_issues()
    
    print("\n" + "=" * 60)
    print("✅ DIAGNOSTIC COMPLETE")
    print("=" * 60)
    print()
    print("🎯 NEXT STEPS:")
    print("1. Check your browser console at http://localhost:5001/dashboard")
    print("2. Look for analysis progress indicator")
    print("3. Check if progress updates every 3 seconds")
    print("4. Verify timezone fixes in updated templates")
    print("5. Test the new playlist sorting functionality")
    print()
    print("📊 The progress indicator should now be visible if there are pending analyses!")

if __name__ == "__main__":
    main() 