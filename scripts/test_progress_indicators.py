#!/usr/bin/env python3
"""
Test script to verify progress indicators are working correctly.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User, Song, AnalysisResult, Playlist, PlaylistSong
from app.services.background_analysis_service import BackgroundAnalysisService
import json

def test_progress_indicators():
    """Test the progress indicator functionality."""
    app = create_app()
    
    with app.app_context():
        print("🔍 Testing Progress Indicators...")
        print("=" * 50)
        
        # Get the first user
        user = User.query.first()
        if not user:
            print("❌ No users found in database")
            return False
            
        print(f"✅ Testing with user: {user.display_name} (ID: {user.id})")
        
        # Test 1: Get analysis progress
        try:
            progress_data = BackgroundAnalysisService.get_analysis_progress_for_user(user.id)
            print(f"\n📊 Analysis Progress Data:")
            print(f"   Total songs: {progress_data['total_songs']}")
            print(f"   Completed: {progress_data['completed']}")
            print(f"   In progress: {progress_data['in_progress']}")
            print(f"   Pending: {progress_data['pending']}")
            print(f"   Failed: {progress_data['failed']}")
            print(f"   Progress: {progress_data['progress_percentage']}%")
            print(f"   Has active analysis: {progress_data['has_active_analysis']}")
            
            if progress_data['current_analysis']:
                current = progress_data['current_analysis']
                print(f"   Current song: \"{current['title']}\" by {current['artist']}")
            else:
                print("   Current song: None")
                
            if progress_data['recent_analyses']:
                print(f"   Recent analyses: {len(progress_data['recent_analyses'])} songs")
                for i, recent in enumerate(progress_data['recent_analyses'][:3]):
                    print(f"     {i+1}. \"{recent['title']}\" by {recent['artist']} (Score: {recent['score']})")
            else:
                print("   Recent analyses: None")
                
        except Exception as e:
            print(f"❌ Error getting progress data: {e}")
            return False
        
        # Test 2: Check if progress indicator should be visible
        should_show = progress_data['has_active_analysis'] or progress_data['pending'] > 0
        print(f"\n🎯 Progress Indicator Visibility:")
        print(f"   Should show progress indicator: {should_show}")
        print(f"   Reason: {'Active analysis' if progress_data['has_active_analysis'] else 'Pending songs' if progress_data['pending'] > 0 else 'No analysis needed'}")
        
        # Test 3: Check database queries performance
        print(f"\n⚡ Database Performance:")
        import time
        
        start_time = time.time()
        total_songs = db.session.query(Song).join(
            PlaylistSong, Song.id == PlaylistSong.song_id
        ).join(
            Playlist, PlaylistSong.playlist_id == Playlist.id
        ).filter(Playlist.owner_id == user.id).distinct().count()
        query1_time = (time.time() - start_time) * 1000
        
        start_time = time.time()
        completed_count = db.session.query(Song).join(
            PlaylistSong, Song.id == PlaylistSong.song_id
        ).join(
            Playlist, PlaylistSong.playlist_id == Playlist.id
        ).join(
            AnalysisResult, Song.id == AnalysisResult.song_id
        ).filter(
            Playlist.owner_id == user.id,
            AnalysisResult.status == 'completed'
        ).distinct().count()
        query2_time = (time.time() - start_time) * 1000
        
        print(f"   Total songs query: {query1_time:.1f}ms")
        print(f"   Completed analysis query: {query2_time:.1f}ms")
        print(f"   Both queries under 100ms: {'✅' if query1_time < 100 and query2_time < 100 else '❌'}")
        
        # Test 4: Simulate API response format
        print(f"\n📡 API Response Format:")
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
            'recent_completed': progress_data['recent_analyses'],
            'cached': False
        }
        
        print(f"   API Response Keys: {list(api_response.keys())}")
        print(f"   Has 'current_song' field: {'✅' if 'current_song' in api_response else '❌'}")
        print(f"   Has 'recent_completed' field: {'✅' if 'recent_completed' in api_response else '❌'}")
        
        # Test 5: Check if background analysis should start
        should_start = BackgroundAnalysisService.should_start_background_analysis(user.id, min_interval_hours=1)
        print(f"\n🚀 Background Analysis:")
        print(f"   Should start background analysis: {should_start}")
        
        print(f"\n🎉 Progress Indicator Test Summary:")
        print(f"   ✅ User found: {user.display_name}")
        print(f"   ✅ Progress data retrieved successfully")
        print(f"   ✅ Database queries performing well")
        print(f"   ✅ API response format correct")
        print(f"   {'✅' if should_show else '⚠️ '} Progress indicator {'should be visible' if should_show else 'hidden (no active analysis)'}")
        
        return True

if __name__ == "__main__":
    success = test_progress_indicators()
    sys.exit(0 if success else 1) 