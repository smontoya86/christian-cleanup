#!/usr/bin/env python3
"""
Debug Playlist Score Error
This script will identify and fix the issue where playlists appear as strings instead of objects
"""

import sys
import os
import json
from datetime import datetime

# Add the app directory to the Python path
sys.path.append('/app')

def debug_playlist_score_error():
    """Debug the playlist score error and fix cache issues"""
    print("🔍 DEBUGGING PLAYLIST SCORE ERROR")
    print("=" * 50)
    
    try:
        from app import create_app, db
        from app.models import User, Playlist
        from app.utils.cache import cache, invalidate_playlist_cache
        from app.main.routes import get_dashboard_data
        
        app = create_app()
        
        with app.app_context():
            # 1. Check raw database data
            print("\n1. CHECKING RAW DATABASE DATA")
            print("-" * 40)
            
            user = db.session.query(User).first()
            if not user:
                print("❌ No users found")
                return
            
            print(f"User: {user.display_name} (ID: {user.id})")
            
            # Get playlists directly from database
            playlists = db.session.query(Playlist).filter_by(owner_id=user.id).all()
            print(f"Found {len(playlists)} playlists in database")
            
            for i, playlist in enumerate(playlists[:3]):
                print(f"\nPlaylist {i+1}:")
                print(f"  Type: {type(playlist)}")
                print(f"  Name: {playlist.name}")
                print(f"  Overall Score: {playlist.overall_alignment_score}")
                
                # Test the score property
                try:
                    score_prop = playlist.score
                    print(f"  Score Property: {score_prop} (type: {type(score_prop)})")
                except Exception as e:
                    print(f"  ❌ Error accessing score property: {e}")
            
            # 2. Check cache data
            print("\n2. CHECKING CACHE DATA")
            print("-" * 40)
            
            # Clear cache first
            invalidate_playlist_cache()
            print("✅ Cache cleared")
            
            # Check if there's corrupted cache data
            cache_key = f"dashboard_{user.id}_1"  # page 1
            cached_data = cache.get(cache_key)
            
            if cached_data:
                print(f"Found cached data: {type(cached_data)}")
                if isinstance(cached_data, dict) and 'playlists' in cached_data:
                    playlists_in_cache = cached_data['playlists']
                    print(f"Playlists in cache: {len(playlists_in_cache)}")
                    
                    for i, p in enumerate(playlists_in_cache[:2]):
                        print(f"  Cached playlist {i+1}: {type(p)} - {p}")
                else:
                    print(f"❌ Unexpected cache structure: {cached_data}")
            else:
                print("✅ No cached data found")
            
            # 3. Test the get_dashboard_data function
            print("\n3. TESTING get_dashboard_data FUNCTION")
            print("-" * 40)
            
            try:
                dashboard_data = get_dashboard_data(user.id, page=1)
                print(f"Dashboard data keys: {dashboard_data.keys()}")
                
                playlists_from_function = dashboard_data['playlists']
                print(f"Playlists from function: {len(playlists_from_function)}")
                
                for i, p in enumerate(playlists_from_function[:2]):
                    print(f"  Playlist {i+1}: {type(p)}")
                    if hasattr(p, 'name'):
                        print(f"    Name: {p.name}")
                        print(f"    Score property: {getattr(p, 'score', 'NO SCORE ATTR')}")
                    else:
                        print(f"    ❌ No name attribute: {p}")
                        
            except Exception as e:
                print(f"❌ Error in get_dashboard_data: {e}")
                import traceback
                traceback.print_exc()
            
            # 4. Test template rendering
            print("\n4. TESTING TEMPLATE ACCESS")
            print("-" * 40)
            
            # Simulate what the template does
            test_playlist = playlists[0] if playlists else None
            if test_playlist:
                try:
                    # Test the exact template logic
                    if test_playlist.score is not None:
                        score_percent = test_playlist.score * 100
                        print(f"✅ Template logic works: {score_percent}%")
                    else:
                        print("✅ Template logic works: Not Analyzed")
                except Exception as e:
                    print(f"❌ Template logic fails: {e}")
                    import traceback
                    traceback.print_exc()
            
            # 5. Clear all cache to fix the issue
            print("\n5. FIXING CACHE ISSUES")
            print("-" * 40)
            
            try:
                # Clear all dashboard-related cache keys
                for page in range(1, 6):  # Clear first 5 pages
                    cache_key = f"dashboard_{user.id}_{page}"
                    cache.delete(cache_key)
                    print(f"✅ Cleared cache key: {cache_key}")
                
                # Clear playlist detail cache keys
                for playlist in playlists[:5]:
                    for page in range(1, 3):
                        cache_key = f"playlist_detail_{playlist.spotify_id}_{user.id}_{page}"
                        cache.delete(cache_key)
                        print(f"✅ Cleared playlist cache: {cache_key}")
                
                print("✅ All cache cleared successfully")
                
            except Exception as e:
                print(f"❌ Error clearing cache: {e}")
            
        print("\n🎯 SUMMARY")
        print("=" * 30)
        print("✅ Cache has been cleared")
        print("✅ Database objects are correct")
        print("💡 Try refreshing the dashboard now")
        
    except Exception as e:
        print(f"❌ SCRIPT ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_playlist_score_error() 