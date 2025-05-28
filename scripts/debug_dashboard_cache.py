#!/usr/bin/env python3
"""
Debug Dashboard Cache Issues
This script will check the database, clear cache, and show why playlists aren't displaying
"""

import sys
import os
import json
from datetime import datetime

# Add the app directory to the Python path
sys.path.append('/app')

def debug_dashboard_cache():
    """Debug dashboard cache and playlist display issues"""
    print("🔍 DEBUGGING DASHBOARD CACHE ISSUES")
    print("=" * 50)
    
    try:
        from app import create_app, db
        from app.models import User, Song, AnalysisResult, Playlist, PlaylistSong
        from app.utils.cache import cache, invalidate_playlist_cache
        from app.main.routes import get_dashboard_data
        
        app = create_app()
        
        with app.app_context():
            print("\n1. CHECKING DATABASE CONTENT")
            print("-" * 40)
            
            # Get first user
            user = db.session.query(User).first()
            if not user:
                print("❌ No users found in database")
                return
            
            print(f"✅ Found user: {user.display_name} (ID: {user.id})")
            
            # Check playlists
            playlists = db.session.query(Playlist).filter_by(owner_id=user.id).all()
            print(f"📁 Total playlists in database: {len(playlists)}")
            
            if playlists:
                for i, playlist in enumerate(playlists[:5]):  # Show first 5
                    print(f"   {i+1}. {playlist.name} (ID: {playlist.spotify_id})")
                if len(playlists) > 5:
                    print(f"   ... and {len(playlists) - 5} more")
            
            # Check songs
            total_songs = db.session.query(Song).join(
                PlaylistSong, Song.id == PlaylistSong.song_id
            ).join(
                Playlist, PlaylistSong.playlist_id == Playlist.id
            ).filter(Playlist.owner_id == user.id).count()
            
            analyzed_songs = db.session.query(Song).join(
                PlaylistSong, Song.id == PlaylistSong.song_id
            ).join(
                Playlist, PlaylistSong.playlist_id == Playlist.id
            ).join(
                AnalysisResult, Song.id == AnalysisResult.song_id
            ).filter(
                Playlist.owner_id == user.id,
                AnalysisResult.status == 'completed'
            ).count()
            
            print(f"🎵 Total songs: {total_songs}")
            print(f"📊 Analyzed songs: {analyzed_songs}")
            
            print("\n2. CHECKING CACHE STATUS")
            print("-" * 40)
            
            # Check if cache is working
            try:
                cache.set('test_key', 'test_value', expiry=10)
                cached_value = cache.get('test_key')
                if cached_value == 'test_value':
                    print("✅ Cache is working")
                else:
                    print("❌ Cache is not working properly")
            except Exception as e:
                print(f"❌ Cache error: {e}")
            
            # Check dashboard cache keys
            try:
                # Clear all dashboard cache
                print("🧹 Clearing dashboard cache...")
                invalidate_playlist_cache()
                print("✅ Dashboard cache cleared")
            except Exception as e:
                print(f"❌ Error clearing cache: {e}")
            
            print("\n3. TESTING get_dashboard_data FUNCTION")
            print("-" * 40)
            
            # Test the dashboard data function directly
            try:
                dashboard_data = get_dashboard_data(user.id, page=1)
                print(f"📊 Dashboard data retrieved:")
                print(f"   Playlists returned: {len(dashboard_data['playlists'])}")
                print(f"   Stats: {dashboard_data['stats']}")
                print(f"   Pagination: {dashboard_data['pagination']}")
                
                if dashboard_data['playlists']:
                    print("✅ Playlists found in dashboard data!")
                    for i, playlist in enumerate(dashboard_data['playlists'][:3]):
                        print(f"   {i+1}. {playlist.name}")
                else:
                    print("❌ No playlists found in dashboard data")
                    
                    # Debug why no playlists
                    print("\n   🔍 DEBUGGING NO PLAYLISTS:")
                    query = Playlist.query.filter_by(owner_id=user.id).order_by(Playlist.updated_at.desc())
                    all_playlists = query.all()
                    print(f"   Raw query returned: {len(all_playlists)} playlists")
                    
                    if all_playlists:
                        print(f"   First playlist: {all_playlists[0].name}")
                        print(f"   Owner ID matches: {all_playlists[0].owner_id == user.id}")
                    
            except Exception as e:
                print(f"❌ Error getting dashboard data: {e}")
                import traceback
                traceback.print_exc()
            
            print("\n4. TESTING PAGINATION")
            print("-" * 40)
            
            # Test pagination directly
            try:
                playlists_query = Playlist.query.filter_by(owner_id=user.id).order_by(Playlist.updated_at.desc())
                paginated = playlists_query.paginate(page=1, per_page=25, error_out=False)
                
                print(f"📄 Pagination test:")
                print(f"   Total items: {paginated.total}")
                print(f"   Items on page: {len(paginated.items)}")
                print(f"   Total pages: {paginated.pages}")
                print(f"   Current page: {paginated.page}")
                
                if paginated.items:
                    print("✅ Pagination working correctly")
                else:
                    print("❌ Pagination returned no items")
                    
            except Exception as e:
                print(f"❌ Pagination error: {e}")
            
            print("\n5. RECOMMENDATIONS")
            print("-" * 40)
            
            if playlists and total_songs > 0:
                print("✅ Database has data - this appears to be a cache or query issue")
                print("💡 Try refreshing the page or clearing browser cache")
                print("💡 Check if there are any JavaScript errors in browser console")
            else:
                print("❌ Database appears to be missing playlist/song data")
                print("💡 You may need to sync playlists from Spotify")
                
    except Exception as e:
        print(f"❌ Script error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_dashboard_cache() 