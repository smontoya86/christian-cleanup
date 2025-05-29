#!/usr/bin/env python3
"""
Debug Real-time Dashboard Error
Test exactly what the dashboard route is receiving when it fails
"""

import sys
import os
import json
from datetime import datetime

# Add the app directory to the Python path
sys.path.append('/app')

def debug_realtime_error():
    """Debug what's happening in the dashboard route in real-time"""
    print("🔍 DEBUGGING REAL-TIME DASHBOARD ERROR")
    print("=" * 50)
    
    try:
        from app import create_app, db
        from app.models import User, Playlist
        from app.utils.cache import cache, invalidate_playlist_cache
        from app.main.routes import get_dashboard_data
        
        app = create_app()
        
        with app.app_context():
            # Get user 2
            user = db.session.query(User).filter_by(id=2).first()
            print(f"User: {user.display_name} (ID: {user.id})")
            
            # Clear ALL cache completely
            print("\n🧹 COMPLETE CACHE FLUSH")
            print("-" * 40)
            
            try:
                # Get all cache keys that might be related
                # Since we can't list Redis keys easily, let's delete known patterns
                cache_patterns = [
                    f"dashboard_{user.id}",
                    f"dashboard_{user.id}_1",
                    f"dashboard_{user.id}_2", 
                    f"dashboard_{user.id}_3",
                    "playlist_sync_status",
                    "analysis_cache",
                    "user_playlists",
                ]
                
                for pattern in cache_patterns:
                    cache.delete(pattern)
                    print(f"✅ Deleted: {pattern}")
                
                # Also invalidate using the built-in function
                invalidate_playlist_cache()
                print("✅ invalidate_playlist_cache() called")
                
            except Exception as e:
                print(f"⚠️  Cache clear warning: {e}")
            
            # Test the exact dashboard data generation
            print("\n🧪 TESTING DASHBOARD DATA GENERATION")
            print("-" * 50)
            
            try:
                # This is what the dashboard route calls
                print("Calling get_dashboard_data(user.id, page=1)...")
                dashboard_data = get_dashboard_data(user.id, page=1)
                
                print(f"✅ Function returned successfully")
                print(f"Keys in dashboard_data: {list(dashboard_data.keys())}")
                
                playlists = dashboard_data.get('playlists', [])
                print(f"Number of playlists: {len(playlists)}")
                
                # Check each playlist in detail
                print("\n📋 DETAILED PLAYLIST INSPECTION")
                print("-" * 40)
                
                problem_found = False
                for i, item in enumerate(playlists):
                    print(f"\nItem {i+1}:")
                    print(f"  Type: {type(item)}")
                    print(f"  Class name: {item.__class__.__name__}")
                    
                    if isinstance(item, str):
                        print(f"  ❌ PROBLEM: Item is a string: '{item}'")
                        problem_found = True
                    elif hasattr(item, 'name'):
                        print(f"  Name: {item.name}")
                        print(f"  Has score attr: {hasattr(item, 'score')}")
                        
                        # Test the exact template line that's failing
                        try:
                            if item.score is not None:
                                score_val = item.score * 100
                                print(f"  Template test (score * 100): {score_val} ✅")
                            else:
                                print(f"  Template test: 'null' ✅")
                        except Exception as e:
                            print(f"  ❌ Template test FAILED: {e}")
                            problem_found = True
                    else:
                        print(f"  ❌ PROBLEM: Item has no 'name' attribute")
                        print(f"  Item content: {repr(item)}")
                        problem_found = True
                    
                    # Only check first 5 to avoid spam
                    if i >= 4:
                        break
                
                if not problem_found:
                    print("\n✅ All playlists look correct!")
                else:
                    print("\n❌ Found problematic playlist data!")
                
                # Check the stats too
                stats = dashboard_data.get('stats', {})
                print(f"\nStats: {stats}")
                
            except Exception as e:
                print(f"❌ Error in get_dashboard_data: {e}")
                import traceback
                traceback.print_exc()
            
            # Test direct database query
            print("\n🗄️  TESTING DIRECT DATABASE QUERY")
            print("-" * 50)
            
            try:
                # This is the exact query from get_dashboard_data
                playlists_query = Playlist.query.filter_by(owner_id=user.id)\
                    .order_by(Playlist.updated_at.desc())
                
                direct_playlists = playlists_query.limit(25).all()
                print(f"Direct query returned {len(direct_playlists)} playlists")
                
                for i, playlist in enumerate(direct_playlists[:3]):
                    print(f"\nDirect playlist {i+1}:")
                    print(f"  Type: {type(playlist)}")
                    print(f"  Name: {playlist.name}")
                    print(f"  Score: {playlist.score}")
                    
            except Exception as e:
                print(f"❌ Error in direct query: {e}")
                import traceback
                traceback.print_exc()
            
        print("\n🎯 DIAGNOSIS COMPLETE")
        print("=" * 30)
        
    except Exception as e:
        print(f"❌ SCRIPT ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_realtime_error() 