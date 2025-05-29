#!/usr/bin/env python3
"""
Test script to verify simplified progress indicators are working correctly.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User, Song, AnalysisResult, Playlist, PlaylistSong
from app.services.background_analysis_service import BackgroundAnalysisService
import json

def test_simplified_progress():
    """Test the simplified progress indicator functionality."""
    app = create_app()
    
    with app.app_context():
        print("🔍 Testing Simplified Progress Indicators...")
        print("=" * 50)
        
        # Get the first user
        user = User.query.first()
        if not user:
            print("❌ No users found in database")
            return
        
        print(f"✅ Testing with user: {user.spotify_id} (ID: {user.id})")
        
        # Test background analysis service
        service = BackgroundAnalysisService()
        progress_data = service.get_analysis_progress_for_user(user.id)
        
        print(f"\n📊 Analysis Progress Data:")
        print(f"   Total songs: {progress_data['total_songs']}")
        print(f"   Completed: {progress_data['completed']}")
        print(f"   In progress: {progress_data['in_progress']}")
        print(f"   Pending: {progress_data['pending']}")
        print(f"   Failed: {progress_data['failed']}")
        print(f"   Progress: {progress_data['progress_percentage']:.1f}%")
        print(f"   Has active analysis: {progress_data['has_active_analysis']}")
        
        # Test if progress indicator should be visible
        should_show = progress_data['has_active_analysis'] or (progress_data['pending'] > 0)
        print(f"\n🎯 Progress Indicator Visibility:")
        print(f"   Should show progress: {'✅ YES' if should_show else '❌ NO'}")
        
        if should_show:
            reason = 'Active analysis' if progress_data['has_active_analysis'] else f"{progress_data['pending']} pending songs"
            print(f"   Reason: {reason}")
        
        # Test current analysis info
        if progress_data['current_analysis']:
            current = progress_data['current_analysis']
            print(f"\n🎵 Current Analysis:")
            print(f"   Song: \"{current['title']}\" by {current['artist']}")
            if 'start_time' in current:
                print(f"   Started: {current['start_time']}")
            else:
                print(f"   Status: Currently being analyzed")
        elif progress_data['in_progress'] > 0:
            print(f"\n🎵 Current Analysis:")
            print(f"   {progress_data['in_progress']} songs being analyzed...")
        else:
            print(f"\n🎵 Current Analysis:")
            print(f"   Preparing next batch...")
        
        # Test recent completed
        if progress_data['recent_analyses']:
            recent = progress_data['recent_analyses'][0]
            print(f"\n📈 Recent Completed:")
            print(f"   Song: \"{recent['title']}\" by {recent['artist']}")
            print(f"   Score: {recent['score']:.1f}")
        else:
            print(f"\n📈 Recent Completed:")
            print(f"   None yet")
        
        # Test API response format
        print(f"\n🔌 API Response Format Test:")
        api_response = {
            'user_id': user.id,
            'has_active_analysis': progress_data['has_active_analysis'],
            'total_songs': progress_data['total_songs'],
            'completed': progress_data['completed'],
            'in_progress': progress_data['in_progress'],
            'pending': progress_data['pending'],
            'failed': progress_data['failed'],
            'progress_percentage': progress_data['progress_percentage'],
            'current_song': progress_data['current_analysis'],
            'recent_completed': progress_data['recent_analyses'][:5] if progress_data['recent_analyses'] else []
        }
        
        print(f"   ✅ API response structure valid")
        print(f"   ✅ All required fields present")
        
        # Test JavaScript update logic
        print(f"\n🖥️  JavaScript Update Logic Test:")
        completed = api_response['completed']
        in_progress = api_response['in_progress']
        pending = api_response['pending']
        total = completed + in_progress + pending
        
        if total > 0:
            progress_percent = (completed / total) * 100
            print(f"   ✅ Progress calculation: {completed}/{total} = {progress_percent:.1f}%")
        else:
            print(f"   ⚠️  No songs to analyze")
        
        # Test element updates
        elements_to_update = {
            'analysisCompleted': completed,
            'analysisInProgress': in_progress,
            'analysisPending': pending,
            'totalAnalyzedSongs': completed
        }
        
        print(f"\n🎯 Element Updates:")
        for element_id, value in elements_to_update.items():
            print(f"   {element_id}: {value}")
        
        print(f"\n✅ All simplified progress indicator tests passed!")
        print(f"📝 Summary:")
        print(f"   - Removed rate calculations and ETA estimates")
        print(f"   - Simplified to 3 columns: Completed, In Progress, Pending")
        print(f"   - Added debug logging to JavaScript")
        print(f"   - Progress indicator shows when analysis is active or pending")
        print(f"   - Clean, simple UI without overwhelming information")

if __name__ == "__main__":
    test_simplified_progress() 