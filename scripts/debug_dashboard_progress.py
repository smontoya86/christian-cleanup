#!/usr/bin/env python3
"""
Debug Dashboard Progress Issues
Tests the dashboard progress functionality to identify why it's not working
"""

import sys
import os
import time
import json
from datetime import datetime

# Add the app directory to the Python path
sys.path.append('/app')

def test_dashboard_progress():
    """Test dashboard progress functionality"""
    print("🔍 DEBUGGING DASHBOARD PROGRESS ISSUES")
    print("=" * 50)
    
    try:
        from app import create_app, db
        from app.models import User, Song, AnalysisResult, Playlist, PlaylistSong
        from app.services.background_analysis_service import BackgroundAnalysisService
        
        app = create_app()
        
        with app.app_context():
            print("\n1. CHECKING DATABASE STATUS")
            print("-" * 30)
            
            # Check if we have any users
            user_count = db.session.query(User).count()
            print(f"Total users: {user_count}")
            
            if user_count == 0:
                print("❌ No users found - this might be the issue!")
                return
            
            # Get the first user for testing
            test_user = db.session.query(User).first()
            print(f"Test user: {test_user.display_name} (ID: {test_user.id})")
            
            # Check songs and analyses
            total_songs = db.session.query(Song).count()
            total_analyses = db.session.query(AnalysisResult).count()
            completed_analyses = db.session.query(AnalysisResult).filter_by(status='completed').count()
            in_progress_analyses = db.session.query(AnalysisResult).filter_by(status='in_progress').count()
            pending_analyses = total_songs - completed_analyses - in_progress_analyses
            
            print(f"Total songs: {total_songs}")
            print(f"Total analyses: {total_analyses}")
            print(f"Completed: {completed_analyses}")
            print(f"In progress: {in_progress_analyses}")
            print(f"Pending: {pending_analyses}")
            
            print("\n2. TESTING BACKGROUND ANALYSIS SERVICE")
            print("-" * 30)
            
            try:
                progress_data = BackgroundAnalysisService.get_analysis_progress_for_user(test_user.id)
                print("✅ BackgroundAnalysisService.get_analysis_progress_for_user() works")
                print(f"Progress data: {json.dumps(progress_data, indent=2)}")
            except Exception as e:
                print(f"❌ BackgroundAnalysisService failed: {e}")
                import traceback
                traceback.print_exc()
                return
            
            print("\n3. TESTING API ENDPOINT DIRECTLY")
            print("-" * 30)
            
            try:
                # Test the API endpoint logic directly
                from app.api.routes import analysis_status
                from flask import g
                from flask_login import current_user
                
                # Mock the current_user for testing
                with app.test_request_context():
                    # Manually set the current user
                    from flask_login import login_user
                    login_user(test_user)
                    
                    # Call the endpoint function directly
                    response = analysis_status()
                    print("✅ API endpoint function works")
                    print(f"Response: {response.get_data(as_text=True)}")
                    
            except Exception as e:
                print(f"❌ API endpoint failed: {e}")
                import traceback
                traceback.print_exc()
                return
            
            print("\n4. TESTING FLASK ROUTES")
            print("-" * 30)
            
            try:
                # Test with Flask test client
                with app.test_client() as client:
                    # Try to access the endpoint (will fail due to auth, but should show route exists)
                    response = client.get('/api/analysis/status')
                    print(f"Route response status: {response.status_code}")
                    print(f"Route response: {response.get_data(as_text=True)}")
                    
                    if response.status_code == 401:
                        print("✅ Route exists but requires authentication (expected)")
                    else:
                        print(f"⚠️  Unexpected status code: {response.status_code}")
                        
            except Exception as e:
                print(f"❌ Flask route test failed: {e}")
                import traceback
                traceback.print_exc()
                return
            
            print("\n5. CHECKING URL RULES")
            print("-" * 30)
            
            # Check if the route is registered
            api_routes = []
            for rule in app.url_map.iter_rules():
                if '/api/' in rule.rule:
                    api_routes.append(f"{rule.rule} -> {rule.endpoint}")
            
            print("API routes found:")
            for route in sorted(api_routes):
                print(f"  {route}")
            
            # Check specifically for analysis status
            analysis_routes = [route for route in api_routes if 'analysis' in route.lower()]
            print(f"\nAnalysis-related routes: {len(analysis_routes)}")
            for route in analysis_routes:
                print(f"  {route}")
            
            print("\n6. CREATING TEST DATA")
            print("-" * 30)
            
            # Create some test in-progress analyses if none exist
            if in_progress_analyses == 0:
                print("Creating test in-progress analyses...")
                
                # Get some songs
                songs = db.session.query(Song).limit(3).all()
                if songs:
                    for song in songs:
                        # Check if analysis already exists
                        existing = db.session.query(AnalysisResult).filter_by(song_id=song.id).first()
                        if not existing:
                            analysis = AnalysisResult(
                                song_id=song.id,
                                status='in_progress',
                                created_at=datetime.utcnow()
                            )
                            db.session.add(analysis)
                            print(f"  Created in-progress analysis for: {song.title}")
                    
                    db.session.commit()
                    print("✅ Test data created")
                else:
                    print("❌ No songs found to create test data")
            
            print("\n7. FINAL STATUS CHECK")
            print("-" * 30)
            
            # Re-check progress after creating test data
            try:
                progress_data = BackgroundAnalysisService.get_analysis_progress_for_user(test_user.id)
                print("Final progress data:")
                print(f"  Has active analysis: {progress_data['has_active_analysis']}")
                print(f"  Total songs: {progress_data['total_songs']}")
                print(f"  Completed: {progress_data['completed']}")
                print(f"  In progress: {progress_data['in_progress']}")
                print(f"  Pending: {progress_data['pending']}")
                
                if progress_data['has_active_analysis'] or progress_data['pending'] > 0:
                    print("✅ Progress indicator should now be visible!")
                else:
                    print("⚠️  No active analysis or pending songs - indicator will be hidden")
                    
            except Exception as e:
                print(f"❌ Final status check failed: {e}")
            
            print("\n" + "=" * 50)
            print("🎯 DEBUGGING COMPLETE")
            print("\nNext steps:")
            print("1. Check browser console for JavaScript errors")
            print("2. Check Network tab for failed API calls")
            print("3. Verify user is logged in")
            print("4. Check if progress indicator elements exist in DOM")
            
    except Exception as e:
        print(f"❌ Debug script failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_dashboard_progress() 