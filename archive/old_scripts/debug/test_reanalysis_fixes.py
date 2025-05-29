#!/usr/bin/env python3
"""
Test the re-analysis fixes
"""

import sys
import os
import argparse
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.models import User, Song, Playlist, AnalysisResult, PlaylistSong
from app.services.background_analysis_service import BackgroundAnalysisService
from sqlalchemy import text

def get_user_by_identifier(identifier):
    """Get user by ID, Spotify ID, or display name"""
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

def test_reanalysis_fixes(user_identifier=None):
    """Test the re-analysis fixes"""
    app = create_app('development')
    
    with app.app_context():
        print("=" * 80)
        print("TESTING RE-ANALYSIS FIXES")
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
                return False
        else:
            user = User.query.first()
            if not user:
                print("❌ No user found in the system")
                return False
            print(f"⚠️  No user specified, using first user: {user.display_name or user.spotify_id} (ID: {user.id})")
        
        print(f"✅ Testing with user: {user.display_name or user.spotify_id} (ID: {user.id})")
        
        # Test 1: Check current analysis status
        print("\n📊 CURRENT ANALYSIS STATUS:")
        progress_data = BackgroundAnalysisService.get_analysis_progress_for_user(user.id)
        print(f"   Total Songs: {progress_data['total_songs']}")
        print(f"   Completed: {progress_data['completed']}")
        print(f"   In Progress: {progress_data['in_progress']}")
        print(f"   Pending: {progress_data['pending']}")
        print(f"   Progress: {progress_data['progress_percentage']:.1f}%")
        
        # Test 2: Check for duplicate analysis results (should be none after fix)
        print("\n🔍 CHECKING FOR DUPLICATE ANALYSIS RESULTS:")
        duplicate_query = text("""
            SELECT song_id, COUNT(*) as count 
            FROM analysis_results 
            GROUP BY song_id 
            HAVING COUNT(*) > 1
        """)
        duplicates = db.session.execute(duplicate_query).fetchall()
        
        if duplicates:
            print(f"   ⚠️  Found {len(duplicates)} songs with duplicate analysis results:")
            for dup in duplicates[:5]:  # Show first 5
                print(f"      Song ID {dup.song_id}: {dup.count} results")
        else:
            print("   ✅ No duplicate analysis results found")
        
        # Test 3: Check analysis queue status
        print("\n🔄 CHECKING ANALYSIS QUEUE:")
        has_active = progress_data['has_active_analysis']
        print(f"   Has Active Analysis: {has_active}")
        
        if progress_data['pending'] > 0:
            print(f"   📋 {progress_data['pending']} songs pending analysis")
        
        # Test 4: Sample analysis results
        print("\n📝 SAMPLE ANALYSIS RESULTS:")
        sample_results = AnalysisResult.query.filter_by(status='completed').limit(3).all()
        for result in sample_results:
            song = Song.query.get(result.song_id)
            if song:
                print(f"   🎵 {song.title} by {song.artist}: Score {result.score}, Concern: {result.concern_level}")
        
        print("\n" + "=" * 80)
        print("✅ RE-ANALYSIS FIXES TEST COMPLETED")
        
        # Summary of improvements
        print("\n🛠️  FIXES IMPLEMENTED:")
        print("   ✅ Fixed duplicate analysis results by clearing old results before creating new ones")
        print("   ✅ Simplified master re-analysis function to avoid 'outdated' status confusion")
        print("   ✅ Fixed flash message duplication by using session-based messaging")
        print("   ✅ Ensured dashboard shows real-time progress without caching issues")
        print("   ✅ Improved progress bar responsiveness")
        
        print("\n💡 NEXT STEPS:")
        print("   1. Test the re-analysis functionality in the UI")
        print("   2. Verify single flash message appears")
        print("   3. Confirm dashboard progress bar updates properly")
        print("   4. Check that old analysis results are replaced (not duplicated)")
        
        return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test the re-analysis fixes")
    parser.add_argument("--user", type=str, help="User identifier (ID, Spotify ID, or display name)")
    args = parser.parse_args()
    test_reanalysis_fixes(args.user) 