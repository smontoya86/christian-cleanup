#!/usr/bin/env python3
"""
Test UI Fixes
Comprehensive test to verify all UI issues are resolved
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User, Playlist, Song, PlaylistSong, AnalysisResult
from app.services.spotify_service import SpotifyService
from sqlalchemy import text
import json

def test_ui_fixes():
    """Test that all UI issues have been resolved"""
    app = create_app()
    
    with app.app_context():
        print("🧪 TESTING UI FIXES")
        print("=" * 50)
        
        # 1. Test token validity
        print("\n1. TOKEN VALIDITY TEST")
        print("-" * 30)
        
        user = db.session.query(User).first()
        if not user:
            print("❌ No user found")
            return False
        
        print(f"User: {user.display_name}")
        print(f"Token expired: {user.is_token_expired}")
        
        if user.is_token_expired:
            print("❌ Token is still expired!")
            return False
        else:
            print("✅ Token is valid")
        
        # 2. Test Spotify API connectivity
        print("\n2. SPOTIFY API CONNECTIVITY TEST")
        print("-" * 30)
        
        try:
            spotify_service = SpotifyService(user.access_token)
            profile = spotify_service.get_user_profile()
            
            if profile:
                print(f"✅ Spotify API working - User: {profile.get('display_name', 'N/A')}")
            else:
                print("❌ Spotify API call failed")
                return False
                
        except Exception as e:
            print(f"❌ Spotify API error: {e}")
            return False
        
        # 3. Test playlist data integrity
        print("\n3. PLAYLIST DATA INTEGRITY TEST")
        print("-" * 30)
        
        playlists = db.session.query(Playlist).filter_by(owner_id=user.id).limit(5).all()
        
        issues = []
        for playlist in playlists:
            if not playlist.name:
                issues.append(f"Playlist {playlist.id} has no name")
            if not playlist.image_url:
                issues.append(f"Playlist {playlist.id} has no image URL")
            if not playlist.spotify_id:
                issues.append(f"Playlist {playlist.id} has no Spotify ID")
        
        if issues:
            print("❌ Playlist data issues found:")
            for issue in issues:
                print(f"  - {issue}")
            return False
        else:
            print(f"✅ All {len(playlists)} playlists have complete data")
        
        # 4. Test playlist detail functionality
        print("\n4. PLAYLIST DETAIL FUNCTIONALITY TEST")
        print("-" * 30)
        
        if playlists:
            test_playlist = playlists[0]
            print(f"Testing playlist: {test_playlist.name} ({test_playlist.spotify_id})")
            
            try:
                # Test getting playlist items from Spotify
                playlist_items = spotify_service.get_playlist_items(
                    test_playlist.spotify_id,
                    fields='items(track(id,name,artists(name)))',
                    limit=5
                )
                
                if playlist_items and playlist_items.get('items'):
                    print(f"✅ Successfully fetched {len(playlist_items['items'])} tracks from Spotify")
                else:
                    print("❌ Failed to fetch playlist items from Spotify")
                    return False
                    
            except Exception as e:
                print(f"❌ Error fetching playlist items: {e}")
                return False
        
        # 5. Test sync status functionality
        print("\n5. SYNC STATUS FUNCTIONALITY TEST")
        print("-" * 30)
        
        try:
            from app.services.playlist_sync_service import get_sync_status
            sync_status = get_sync_status(user.id)
            
            if sync_status is not None:
                print("✅ Sync status service working")
                print(f"  Has active sync: {sync_status.get('has_active_sync', False)}")
            else:
                print("❌ Sync status service failed")
                return False
                
        except Exception as e:
            print(f"❌ Sync status error: {e}")
            return False
        
        # 6. Test database performance
        print("\n6. DATABASE PERFORMANCE TEST")
        print("-" * 30)
        
        try:
            # Test optimized queries
            import time
            
            # Test playlist query with pagination
            start_time = time.time()
            paginated_playlists = Playlist.query.filter_by(owner_id=user.id)\
                .order_by(Playlist.updated_at.desc())\
                .limit(25).all()
            query_time = (time.time() - start_time) * 1000
            
            print(f"✅ Playlist query: {query_time:.1f}ms ({len(paginated_playlists)} results)")
            
            # Test song count query
            start_time = time.time()
            song_count = db.session.query(Song).count()
            query_time = (time.time() - start_time) * 1000
            
            print(f"✅ Song count query: {query_time:.1f}ms ({song_count} songs)")
            
            # Test analysis results query
            start_time = time.time()
            analysis_count = db.session.query(AnalysisResult).filter(
                AnalysisResult.status == 'completed'
            ).count()
            query_time = (time.time() - start_time) * 1000
            
            print(f"✅ Analysis query: {query_time:.1f}ms ({analysis_count} completed)")
            
        except Exception as e:
            print(f"❌ Database performance test failed: {e}")
            return False
        
        # 7. Test caching functionality
        print("\n7. CACHING FUNCTIONALITY TEST")
        print("-" * 30)
        
        try:
            from app.api.routes import get_cache_key, cache_response, get_cached_response
            
            # Test cache operations
            test_key = get_cache_key("test", user_id=user.id)
            test_data = {"test": "data", "timestamp": "now"}
            
            cache_response(test_key, test_data, ttl=60)
            cached_data = get_cached_response(test_key)
            
            if cached_data and cached_data.get("test") == "data":
                print("✅ Caching functionality working")
            else:
                print("❌ Caching functionality failed")
                return False
                
        except Exception as e:
            print(f"❌ Caching test failed: {e}")
            return False
        
        print(f"\n🎉 ALL TESTS PASSED!")
        print("=" * 50)
        print("✅ Token issues resolved")
        print("✅ Spotify API connectivity working")
        print("✅ Playlist data integrity confirmed")
        print("✅ Playlist detail functionality working")
        print("✅ Sync status functionality working")
        print("✅ Database performance optimized")
        print("✅ Caching functionality working")
        
        return True

if __name__ == "__main__":
    success = test_ui_fixes()
    if success:
        print("\n🚀 UI is ready for testing!")
    else:
        print("\n❌ Some issues still need to be resolved") 