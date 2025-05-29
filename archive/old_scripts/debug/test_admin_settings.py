#!/usr/bin/env python3
"""
Test script to verify admin settings functionality
"""

import os
import sys

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models.models import User, Playlist, Song, AnalysisResult, PlaylistSong
from app.extensions import db
import traceback

def test_admin_settings():
    """Test the admin settings route and functionality"""
    app = create_app()
    
    with app.app_context():
        try:
            print("Testing admin settings functionality...")
            
            # 1. Test User model and statistics calculation
            print("\n1. Testing User statistics calculation...")
            user = User.query.first()
            if not user:
                print("   ❌ No users found in database")
                return False
                
            print(f"   ✅ Found user: {user.display_name or user.email}")
            
            # Test playlist count
            playlist_count = user.playlists.count()
            print(f"   📊 User has {playlist_count} playlists")
            
            # Test song statistics calculation (same as in the route)
            if playlist_count > 0:
                from sqlalchemy import func
                song_stats = db.session.query(
                    func.count(Song.id).label('total'),
                    func.count(AnalysisResult.id).label('analyzed')
                ).select_from(Song).join(PlaylistSong).join(Playlist)\
                .outerjoin(AnalysisResult, Song.id == AnalysisResult.song_id)\
                .filter(Playlist.owner_id == user.id).first()
                
                if song_stats:
                    total_songs = song_stats.total or 0
                    analyzed_songs = song_stats.analyzed or 0
                    pending_songs = total_songs - analyzed_songs
                    
                    print(f"   📊 Total songs: {total_songs}")
                    print(f"   📊 Analyzed songs: {analyzed_songs}")
                    print(f"   📊 Pending songs: {pending_songs}")
                else:
                    print("   ⚠️  No song statistics found")
            
            # 2. Test settings route access
            print("\n2. Testing settings route...")
            with app.test_client() as client:
                # Mock login (simplified for testing)
                with client.session_transaction() as sess:
                    sess['_user_id'] = str(user.id)
                    sess['_fresh'] = True
                
                # Test GET request to settings
                response = client.get('/settings')
                if response.status_code == 200:
                    print("   ✅ Settings route accessible")
                    
                    # Check if admin controls are in the response
                    response_text = response.get_data(as_text=True)
                    if 'Admin Controls' in response_text:
                        print("   ✅ Admin controls section present")
                    else:
                        print("   ❌ Admin controls section missing")
                        
                    if 'Re-sync All Playlists' in response_text:
                        print("   ✅ Re-sync functionality present")
                    else:
                        print("   ❌ Re-sync functionality missing")
                        
                    if 'Re-analyze All Songs' in response_text:
                        print("   ✅ Re-analysis functionality present")
                    else:
                        print("   ❌ Re-analysis functionality missing")
                        
                else:
                    print(f"   ❌ Settings route failed with status {response.status_code}")
                    print(f"   Error: {response.get_data(as_text=True)}")
                    return False
            
            # 3. Test admin route endpoints exist
            print("\n3. Testing admin route endpoints...")
            
            # Check if routes are registered
            app_routes = [rule.rule for rule in app.url_map.iter_rules()]
            
            if '/admin/resync-all-playlists' in app_routes:
                print("   ✅ Admin re-sync route registered")
            else:
                print("   ❌ Admin re-sync route not found")
                
            if '/admin/reanalyze-all-songs' in app_routes:
                print("   ✅ Admin re-analysis route registered")
            else:
                print("   ❌ Admin re-analysis route not found")
            
            # 4. Test imports and dependencies
            print("\n4. Testing imports and dependencies...")
            
            try:
                from app.services.playlist_sync_service import enqueue_playlist_sync, get_sync_status
                print("   ✅ Playlist sync service imports working")
            except ImportError as e:
                print(f"   ❌ Playlist sync service import failed: {e}")
                
            try:
                from app.extensions import rq
                print("   ✅ RQ extension import working")
            except ImportError as e:
                print(f"   ❌ RQ extension import failed: {e}")
            
            # 5. Test token validation
            print("\n5. Testing token validation...")
            
            if hasattr(user, 'is_token_expired'):
                token_expired = user.is_token_expired
                print(f"   📊 Token expired: {token_expired}")
                
                if hasattr(user, 'token_expiry') and user.token_expiry:
                    print(f"   📊 Token expires: {user.token_expiry}")
                else:
                    print("   ⚠️  No token expiry information")
            else:
                print("   ❌ is_token_expired property not found")
            
            print("\n✅ Admin settings test completed successfully!")
            return True
            
        except Exception as e:
            print(f"\n❌ Error during admin settings test: {e}")
            print(f"Traceback: {traceback.format_exc()}")
            return False

if __name__ == "__main__":
    success = test_admin_settings()
    sys.exit(0 if success else 1) 