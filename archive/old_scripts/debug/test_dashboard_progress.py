#!/usr/bin/env python3
"""
Test the dashboard progress bar functionality
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import User, Song, Playlist, AnalysisResult, PlaylistSong
from app.services.background_analysis_service import BackgroundAnalysisService
import requests
import json

def test_dashboard_progress():
    """Test the dashboard progress bar functionality"""
    app = create_app('development')
    
    with app.app_context():
        print("=" * 80)
        print("TESTING DASHBOARD PROGRESS BAR FUNCTIONALITY")
        print("=" * 80)
        
        # Get the test user
        user = User.query.first()
        if not user:
            print("❌ No user found in the system")
            return False
        
        print(f"📊 TESTING FOR USER: {user.display_name}")
        print("-" * 50)
        
        # 1. Test the progress calculation directly
        print("1️⃣ DIRECT PROGRESS CALCULATION:")
        background_service = BackgroundAnalysisService()
        progress_data = background_service.get_analysis_progress_for_user(user.id)
        
        print(f"   Total Songs: {progress_data['total_songs']}")
        print(f"   Completed: {progress_data['completed']}")
        print(f"   In Progress: {progress_data['in_progress']}")
        print(f"   Pending: {progress_data['pending']}")
        print(f"   Progress %: {progress_data['progress_percentage']}")
        print(f"   Has Active: {progress_data['has_active_analysis']}")
        
        # 2. Simulate the API call that the dashboard makes
        print("\n2️⃣ SIMULATING DASHBOARD API CALL:")
        with app.test_client() as client:
            # First login (simulate)
            with client.session_transaction() as sess:
                sess['user_id'] = str(user.id)
                sess['_fresh'] = True
            
            # Call the API endpoint
            response = client.get('/api/analysis/status')
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                api_data = response.get_json()
                print("   API Response:")
                for key, value in api_data.items():
                    if key == 'current_song' and value:
                        print(f"     - {key}: {value['title']} by {value['artist']}")
                    else:
                        print(f"     - {key}: {value}")
            else:
                print(f"   ❌ API Error: {response.data}")
        
        # 3. Test progress bar visibility logic
        print("\n3️⃣ PROGRESS BAR VISIBILITY LOGIC:")
        should_show = progress_data['progress_percentage'] < 100
        print(f"   Progress %: {progress_data['progress_percentage']}")
        print(f"   Should show progress bar: {should_show}")
        
        if should_show:
            print("   ✅ Progress bar should be visible on dashboard")
        else:
            print("   ℹ️ Progress bar would be hidden (100% complete)")
        
        # 4. Test edge cases
        print("\n4️⃣ TESTING EDGE CASES:")
        
        # Test with no songs
        empty_progress = {
            'total_songs': 0,
            'completed_songs': 0,
            'in_progress_songs': 0,
            'pending_songs': 0,
            'progress_percentage': 0,
            'has_active_analysis': False
        }
        print(f"   Empty progress: {empty_progress['progress_percentage']}%")
        
        # Test with 100% completion
        complete_progress = {
            'total_songs': 100,
            'completed_songs': 100,
            'in_progress_songs': 0,
            'pending_songs': 0,
            'progress_percentage': 100,
            'has_active_analysis': False
        }
        print(f"   Complete progress: {complete_progress['progress_percentage']}%")
        
        return True

if __name__ == "__main__":
    test_dashboard_progress() 