#!/usr/bin/env python3
"""
Debug User Cache Issues
Debug cache issues for a specific user
"""

import sys
import os
import json
import argparse
from datetime import datetime

# Add the app directory to the Python path
sys.path.append('/app')

def get_user_by_identifier(identifier):
    """Get user by ID, Spotify ID, or display name"""
    from app.models import User
    from app.extensions import db
    
    try:
        # Try as integer ID first
        user_id = int(identifier)
        user = db.session.query(User).filter_by(id=user_id).first()
        if user:
            return user
    except ValueError:
        # Not an integer, try as Spotify ID
        user = db.session.query(User).filter_by(spotify_id=identifier).first()
        if user:
            return user
    
    # Try as display name
    user = db.session.query(User).filter_by(display_name=identifier).first()
    return user

def debug_user_cache(user_identifier=None):
    """Debug cache issues for a specific user"""
    print(f"🔍 DEBUGGING USER CACHE ISSUES")
    print("=" * 50)
    
    try:
        from app import create_app, db
        from app.models import User, Playlist
        from app.utils.cache import cache, invalidate_playlist_cache
        from app.main.routes import get_dashboard_data
        
        app = create_app()
        
        with app.app_context():
            # Get user by identifier or use user ID 2 as fallback (for compatibility)
            if user_identifier:
                user = get_user_by_identifier(user_identifier)
                if not user:
                    print(f"❌ User not found with identifier: {user_identifier}")
                    print("Available users:")
                    users = db.session.query(User).limit(5).all()
                    for u in users:
                        print(f"   - ID: {u.id}, Spotify ID: {u.spotify_id}, Display Name: {u.display_name}")
                    return
            else:
                # Default to user ID 2 for backward compatibility
                user = db.session.query(User).filter_by(id=2).first()
                if not user:
                    print("❌ Default user ID 2 not found, using first available user")
                    user = db.session.query(User).first()
                    if not user:
                        print("❌ No users found in database")
                        return
                print(f"⚠️  No user specified, using user: {user.display_name} (ID: {user.id})")
            
            print(f"User: {user.display_name} (ID: {user.id}, Spotify ID: {user.spotify_id})")
            
            # Check playlists for user
            playlists = db.session.query(Playlist).filter_by(owner_id=user.id).all()
            print(f"Found {len(playlists)} playlists for user {user.display_name}")
            
            # Clear cache specifically for user
            print("\n🧹 CLEARING USER CACHE")
            print("-" * 40)
            
            # Clear dashboard cache for user
            for page in range(1, 10):  # Clear first 10 pages
                cache_key = f"dashboard_{user.id}_{page}"
                result = cache.delete(cache_key)
                if result:
                    print(f"✅ Cleared cache key: {cache_key}")
            
            # Clear general cache keys that might affect user
            general_keys = [
                f"dashboard_{user.id}",
                f"user_{user.id}_playlists", 
                f"user_{user.id}_stats",
                f"playlist_sync_{user.id}",
                f"analysis_status_{user.id}"
            ]
            
            for key in general_keys:
                result = cache.delete(key)
                if result:
                    print(f"✅ Cleared general cache: {key}")
            
            # Clear playlist detail cache for user's playlists
            print(f"\n🧹 CLEARING PLAYLIST CACHES FOR {len(playlists)} PLAYLISTS")
            print("-" * 60)
            
            cleared_count = 0
            for playlist in playlists:
                for page in range(1, 5):  # Clear first 4 pages of each playlist
                    cache_key = f"playlist_detail_{playlist.spotify_id}_{user.id}_{page}"
                    result = cache.delete(cache_key)
                    if result:
                        cleared_count += 1
                        if cleared_count <= 10:  # Only show first 10 to avoid spam
                            print(f"✅ Cleared: {cache_key}")
                    
                    # Also try without page number
                    cache_key_no_page = f"playlist_detail_{playlist.spotify_id}_{user.id}"
                    result2 = cache.delete(cache_key_no_page)
                    if result2:
                        cleared_count += 1
            
            print(f"✅ Cleared {cleared_count} playlist cache entries")
            
            # Test dashboard data generation for user
            print("\n🧪 TESTING DASHBOARD DATA FOR USER")
            print("-" * 50)
            
            try:
                dashboard_data = get_dashboard_data(user.id, page=1)
                playlists_data = dashboard_data['playlists']
                
                print(f"✅ Dashboard data generated successfully")
                print(f"✅ Found {len(playlists_data)} playlists in dashboard data")
                
                # Test first few playlists
                for i, playlist in enumerate(playlists_data[:3]):
                    print(f"\nPlaylist {i+1}:")
                    print(f"  Type: {type(playlist)}")
                    print(f"  Name: {getattr(playlist, 'name', 'NO NAME')}")
                    print(f"  Score: {getattr(playlist, 'score', 'NO SCORE')}")
                    
                    # Test template logic
                    try:
                        if playlist.score is not None:
                            score_percent = playlist.score * 100
                            print(f"  Template test: {score_percent:.1f}% ✅")
                        else:
                            print(f"  Template test: Not Analyzed ✅")
                    except Exception as e:
                        print(f"  Template test: ❌ {e}")
                        
            except Exception as e:
                print(f"❌ Error generating dashboard data: {e}")
                import traceback
                traceback.print_exc()
            
            # Force cache invalidation
            print("\n🔥 FORCE CACHE INVALIDATION")
            print("-" * 40)
            
            try:
                invalidate_playlist_cache()
                print("✅ General playlist cache invalidated")
                
                # Also try to clear all cache (if possible)
                cache.clear()
                print("✅ All cache cleared")
                
            except Exception as e:
                print(f"⚠️  Warning during cache clearing: {e}")
            
        print("\n🎯 SUMMARY FOR USER")
        print("=" * 30)
        print("✅ All cache for user has been cleared")
        print("✅ Fresh dashboard data will be generated")
        print("💡 Try refreshing the dashboard again")
        
    except Exception as e:
        print(f"❌ SCRIPT ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Debug cache issues for a specific user")
    parser.add_argument("--user", type=str, help="User ID, Spotify ID, or display name")
    args = parser.parse_args()
    debug_user_cache(args.user) 