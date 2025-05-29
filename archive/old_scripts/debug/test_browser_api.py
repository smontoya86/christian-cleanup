#!/usr/bin/env python3
"""
Test Browser API - Simulate what the browser should see
"""

import sys
import os
import time
import json
from datetime import datetime

# Add the app directory to the Python path
sys.path.append('/app')

def test_browser_api():
    """Test what the browser should see when calling the API"""
    print("🌐 TESTING BROWSER API SIMULATION")
    print("=" * 50)
    
    try:
        from app import create_app, db
        from app.models import User, Song, AnalysisResult, Playlist, PlaylistSong
        from app.services.background_analysis_service import BackgroundAnalysisService
        from flask_login import login_user
        
        app = create_app()
        
        with app.app_context():
            # Get a test user
            test_user = db.session.query(User).first()
            if not test_user:
                print("❌ No users found")
                return
            
            print(f"Testing with user: {test_user.display_name}")
            
            # Test the API endpoint with authentication
            with app.test_client() as client:
                with client.session_transaction() as sess:
                    # Simulate login
                    sess['_user_id'] = str(test_user.id)
                    sess['_fresh'] = True
                
                print("\n1. TESTING API ENDPOINT WITH AUTH")
                print("-" * 40)
                
                response = client.get('/api/analysis/status')
                print(f"Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.get_json()
                    print("✅ API endpoint works with authentication!")
                    print(f"Response data: {json.dumps(data, indent=2)}")
                    
                    # Check what should trigger the progress indicator
                    should_show = data.get('has_active_analysis', False) or (data.get('pending', 0) > 0)
                    print(f"\nShould show progress indicator: {should_show}")
                    print(f"  - has_active_analysis: {data.get('has_active_analysis', False)}")
                    print(f"  - pending songs: {data.get('pending', 0)}")
                    print(f"  - completed: {data.get('completed', 0)}")
                    print(f"  - in_progress: {data.get('in_progress', 0)}")
                    print(f"  - total_songs: {data.get('total_songs', 0)}")
                    
                    if not should_show:
                        print("\n⚠️  ISSUE FOUND: No active analysis or pending songs!")
                        print("This is why the progress indicator isn't updating.")
                        
                        # Let's create some test analysis jobs
                        print("\n2. CREATING TEST ANALYSIS JOBS")
                        print("-" * 40)
                        
                        # Get some songs that need analysis
                        songs_needing_analysis = db.session.query(Song).outerjoin(AnalysisResult).filter(
                            AnalysisResult.id.is_(None)
                        ).limit(5).all()
                        
                        if songs_needing_analysis:
                            print(f"Found {len(songs_needing_analysis)} songs that need analysis")
                            
                            # Create some in-progress analyses
                            for i, song in enumerate(songs_needing_analysis[:3]):
                                analysis = AnalysisResult(
                                    song_id=song.id,
                                    status='in_progress' if i < 2 else 'pending',
                                    created_at=datetime.utcnow()
                                )
                                db.session.add(analysis)
                                print(f"  Created {analysis.status} analysis for: {song.title}")
                            
                            db.session.commit()
                            print("✅ Test analysis jobs created")
                            
                            # Test the API again
                            print("\n3. TESTING API AFTER CREATING JOBS")
                            print("-" * 40)
                            
                            response = client.get('/api/analysis/status')
                            if response.status_code == 200:
                                data = response.get_json()
                                print("Updated response data:")
                                print(f"  - has_active_analysis: {data.get('has_active_analysis', False)}")
                                print(f"  - pending: {data.get('pending', 0)}")
                                print(f"  - in_progress: {data.get('in_progress', 0)}")
                                print(f"  - completed: {data.get('completed', 0)}")
                                
                                should_show_now = data.get('has_active_analysis', False) or (data.get('pending', 0) > 0)
                                print(f"\nShould show progress indicator now: {should_show_now}")
                                
                                if should_show_now:
                                    print("✅ Progress indicator should now be visible and updating!")
                                else:
                                    print("❌ Still no reason to show progress indicator")
                        else:
                            print("❌ No songs found that need analysis")
                    
                else:
                    print(f"❌ API endpoint failed: {response.status_code}")
                    print(f"Response: {response.get_data(as_text=True)}")
                
                print("\n4. TESTING JAVASCRIPT SIMULATION")
                print("-" * 40)
                
                # Simulate what the JavaScript should do
                print("JavaScript should:")
                print("1. Call fetch('/api/analysis/status') every 3 seconds")
                print("2. Check if response.has_active_analysis || response.pending > 0")
                print("3. If true, show the progress indicator")
                print("4. Update the progress bar and stats")
                
                print("\n5. BROWSER DEBUGGING STEPS")
                print("-" * 40)
                print("To debug in the browser:")
                print("1. Open Developer Tools (F12)")
                print("2. Go to Console tab")
                print("3. Look for these messages:")
                print("   - '🔍 checkAnalysisStatus() called at...'")
                print("   - '📡 API response status: 200'")
                print("   - '📊 API response data: {...}'")
                print("4. If you see 401 errors, the user isn't logged in properly")
                print("5. If you see the data but no updates, check the updateAnalysisProgress function")
                
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_browser_api() 