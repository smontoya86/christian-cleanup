#!/usr/bin/env python3
"""
Debug UI Issues Script
Comprehensive debugging to identify root causes of UI problems
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User, Playlist, Song, PlaylistSong, AnalysisResult
from app.services.spotify_service import SpotifyService
from sqlalchemy import text
import json

def debug_ui_issues():
    """Debug the UI issues reported by user"""
    app = create_app()
    
    with app.app_context():
        print("🔍 DEBUGGING UI ISSUES")
        print("=" * 50)
        
        # 1. Check database state
        print("\n1. DATABASE STATE CHECK")
        print("-" * 30)
        
        # Get user count
        user_count = db.session.query(User).count()
        print(f"Users in database: {user_count}")
        
        if user_count == 0:
            print("❌ No users found - this could be the root cause!")
            return
        
        # Get first user for testing
        user = db.session.query(User).first()
        print(f"Testing with user: {user.id} - {user.display_name}")
        
        # Check playlists
        playlists = db.session.query(Playlist).filter_by(owner_id=user.id).all()
        print(f"Playlists for user: {len(playlists)}")
        
        if len(playlists) == 0:
            print("❌ No playlists found - this explains missing playlist names/art!")
            return
        
        # 2. Check playlist data integrity
        print("\n2. PLAYLIST DATA INTEGRITY")
        print("-" * 30)
        
        for i, playlist in enumerate(playlists[:5]):  # Check first 5
            print(f"\nPlaylist {i+1}:")
            print(f"  ID: {playlist.id}")
            print(f"  Spotify ID: {playlist.spotify_id}")
            print(f"  Name: {playlist.name}")
            print(f"  Image URL: {playlist.image_url}")
            print(f"  Description: {playlist.description}")
            print(f"  Score: {playlist.score}")
            print(f"  Overall Score: {getattr(playlist, 'overall_alignment_score', 'N/A')}")
            
            # Check if name or image_url are None/empty
            if not playlist.name:
                print(f"  ❌ ISSUE: Playlist name is empty!")
            if not playlist.image_url:
                print(f"  ⚠️  WARNING: No image URL")
        
        # 3. Check playlist songs relationship
        print("\n3. PLAYLIST SONGS RELATIONSHIP")
        print("-" * 30)
        
        for playlist in playlists[:3]:
            songs_count = db.session.query(PlaylistSong).filter_by(playlist_id=playlist.id).count()
            print(f"Playlist '{playlist.name}': {songs_count} songs")
            
            # Check if songs relationship is working
            try:
                songs_via_relationship = len(playlist.songs)
                print(f"  Via relationship: {songs_via_relationship} songs")
                if songs_count != songs_via_relationship:
                    print(f"  ❌ MISMATCH: Direct query vs relationship!")
            except Exception as e:
                print(f"  ❌ ERROR accessing songs relationship: {e}")
        
        # 4. Check Spotify service initialization
        print("\n4. SPOTIFY SERVICE CHECK")
        print("-" * 30)
        
        try:
            # Check if user has valid token
            print(f"User access token exists: {bool(user.access_token)}")
            print(f"User token expiry: {user.token_expiry}")
            
            if user.access_token:
                # Try to initialize Spotify service
                spotify_service = SpotifyService(user.access_token)
                print(f"Spotify service initialized: {bool(spotify_service.sp)}")
                
                # Try a simple API call
                try:
                    profile = spotify_service.get_user_profile()
                    print(f"Spotify API call successful: {bool(profile)}")
                    if profile:
                        print(f"  User profile: {profile.get('display_name', 'N/A')}")
                except Exception as e:
                    print(f"❌ Spotify API call failed: {e}")
            else:
                print("❌ No access token - this explains Spotify API errors!")
                
        except Exception as e:
            print(f"❌ Error checking Spotify service: {e}")
        
        # 5. Check sync status service
        print("\n5. SYNC STATUS CHECK")
        print("-" * 30)
        
        try:
            from app.services.playlist_sync_service import get_sync_status
            sync_status = get_sync_status(user.id)
            print(f"Sync status retrieved: {bool(sync_status)}")
            if sync_status:
                print(f"  Has active sync: {sync_status.get('has_active_sync', 'N/A')}")
                print(f"  Active jobs: {len(sync_status.get('active_jobs', []))}")
        except Exception as e:
            print(f"❌ Error checking sync status: {e}")
        
        # 6. Check database indexes
        print("\n6. DATABASE INDEXES CHECK")
        print("-" * 30)
        
        try:
            indexes = db.session.execute(text("""
                SELECT indexname FROM pg_indexes 
                WHERE schemaname = 'public' AND indexname LIKE 'idx_%'
            """)).fetchall()
            
            print(f"Performance indexes found: {len(indexes)}")
            for idx in indexes:
                print(f"  - {idx[0]}")
                
        except Exception as e:
            print(f"❌ Error checking indexes: {e}")
        
        # 7. Test playlist detail route logic
        print("\n7. PLAYLIST DETAIL ROUTE TEST")
        print("-" * 30)
        
        if playlists:
            test_playlist = playlists[0]
            print(f"Testing playlist detail for: {test_playlist.spotify_id}")
            
            # Check if the playlist ID format is correct
            spotify_id = test_playlist.spotify_id
            print(f"Spotify ID: '{spotify_id}'")
            print(f"Spotify ID length: {len(spotify_id) if spotify_id else 0}")
            
            # Spotify playlist IDs should be 22 characters
            if not spotify_id or len(spotify_id) != 22:
                print(f"❌ INVALID Spotify ID format! Expected 22 chars, got {len(spotify_id) if spotify_id else 0}")
            else:
                print(f"✅ Spotify ID format looks correct")
        
        # 8. Check for missing constants
        print("\n8. MISSING CONSTANTS CHECK")
        print("-" * 30)
        
        try:
            from app.main.routes import SONGS_PER_PAGE
            print(f"SONGS_PER_PAGE constant: {SONGS_PER_PAGE}")
        except ImportError:
            print("❌ SONGS_PER_PAGE constant not found - this could cause playlist detail errors!")
        
        # 9. Summary and recommendations
        print("\n9. SUMMARY & RECOMMENDATIONS")
        print("-" * 30)
        
        issues_found = []
        
        if user_count == 0:
            issues_found.append("No users in database")
        elif len(playlists) == 0:
            issues_found.append("No playlists for user")
        else:
            # Check for common issues
            empty_names = sum(1 for p in playlists if not p.name)
            empty_images = sum(1 for p in playlists if not p.image_url)
            
            if empty_names > 0:
                issues_found.append(f"{empty_names} playlists with empty names")
            if empty_images > 0:
                issues_found.append(f"{empty_images} playlists with no image URLs")
            if not user.access_token:
                issues_found.append("User has no Spotify access token")
        
        if issues_found:
            print("❌ ISSUES FOUND:")
            for issue in issues_found:
                print(f"  - {issue}")
        else:
            print("✅ No obvious issues found in database")
        
        print("\n🔧 RECOMMENDED FIXES:")
        if not user.access_token:
            print("  1. User needs to re-authenticate with Spotify")
        if len(playlists) == 0:
            print("  2. Run playlist sync to populate database")
        if any(not p.name for p in playlists):
            print("  3. Update playlist records with missing names")
        if any(not p.image_url for p in playlists):
            print("  4. Update playlist records with missing image URLs")

if __name__ == "__main__":
    debug_ui_issues() 