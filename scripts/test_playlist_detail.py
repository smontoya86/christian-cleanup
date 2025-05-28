#!/usr/bin/env python3
"""
Test Playlist Detail Route
Verify that the playlist detail functionality works correctly after SongStatus fix
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

def test_playlist_detail(user_identifier=None):
    """Test the playlist detail route functionality"""
    print("🧪 TESTING PLAYLIST DETAIL ROUTE")
    print("=" * 50)
    
    try:
        from app import create_app, db
        from app.models import User, Playlist, Song, PlaylistSong, AnalysisResult
        from app.main.routes import get_playlist_detail_data
        from app.services.song_status_service import SongStatus
        
        app = create_app()
        
        with app.app_context():
            # Get user by identifier or use user ID 2 as fallback
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
            
            print(f"Testing with user: {user.display_name} (ID: {user.id}, Spotify ID: {user.spotify_id})")
            
            # Get a playlist
            playlist = db.session.query(Playlist).filter_by(owner_id=user.id).first()
            if not playlist:
                print("❌ No playlists found for user")
                return
                
            print(f"Testing playlist: {playlist.name} (Spotify ID: {playlist.spotify_id})")
            
            # Test the get_playlist_detail_data function
            print("\n🔍 TESTING get_playlist_detail_data Function")
            print("-" * 40)
            
            try:
                playlist_data = get_playlist_detail_data(playlist.spotify_id, user.id, page=1)
                
                if playlist_data is None:
                    print("❌ get_playlist_detail_data returned None")
                    return
                
                print(f"✅ Function returned data successfully")
                print(f"Keys in playlist_data: {list(playlist_data.keys())}")
                
                songs_with_status = playlist_data.get('songs_with_status', [])
                print(f"Number of songs: {len(songs_with_status)}")
                
                # Test the first few songs to ensure status works
                print("\n📋 TESTING SONG STATUS OBJECTS")
                print("-" * 40)
                
                for i, item in enumerate(songs_with_status[:3]):
                    print(f"\nSong {i+1}:")
                    
                    # Check if the item has the required fields
                    track = item.get('track')
                    status = item.get('status')
                    status_service = item.get('status_service')
                    song_db_id = item.get('song_db_id')
                    
                    if track:
                        # Handle podcast episodes where artist names might be None
                        artists = track.get('artists', [])
                        artist_names = [a['name'] for a in artists if a.get('name') is not None]
                        artist_str = ', '.join(artist_names) if artist_names else 'Unknown Artist'
                        print(f"  Track: {track.get('name', 'Unknown')} by {artist_str}")
                    
                    print(f"  Status: {status}")
                    print(f"  Song DB ID: {song_db_id}")
                    
                    # Test SongStatus service
                    if status_service and hasattr(status_service, 'display_message'):
                        print(f"  Status Message: {status_service.display_message}")
                        print(f"  Status Color Class: {status_service.color_class}")
                        print(f"  ✅ SongStatus service working correctly")
                    else:
                        print(f"  ⚠️  SongStatus service not available or incomplete")
                        print(f"  Status service type: {type(status_service)}")
                
                print("\n✅ Playlist detail data generation working correctly!")
                
            except Exception as e:
                print(f"❌ Error in get_playlist_detail_data: {e}")
                import traceback
                traceback.print_exc()
                return
            
            # Test SongStatus directly
            print("\n🔧 TESTING SongStatus Class Directly")
            print("-" * 40)
            
            try:
                # Get a song from the database
                song = db.session.query(Song).join(
                    PlaylistSong, Song.id == PlaylistSong.song_id
                ).filter(PlaylistSong.playlist_id == playlist.id).first()
                
                if song:
                    analysis_result = db.session.query(AnalysisResult).filter_by(
                        song_id=song.id, status='completed'
                    ).first()
                    
                    print(f"Test song: {song.title} by {song.artist}")
                    print(f"Has analysis: {analysis_result is not None}")
                    
                    # Create SongStatus instance
                    status_service = SongStatus(
                        song=song,
                        analysis_result=analysis_result,
                        is_whitelisted=False,
                        is_blacklisted=False,
                        is_preferred=False
                    )
                    
                    print(f"Status message: {status_service.display_message}")
                    print(f"Status color: {status_service.color_class}")
                    print("✅ SongStatus class working correctly!")
                    
                else:
                    print("⚠️  No songs found in playlist")
                    
            except Exception as e:
                print(f"❌ Error testing SongStatus: {e}")
                import traceback
                traceback.print_exc()
        
        print("\n🎯 TEST COMPLETE")
        print("=" * 30)
        
    except Exception as e:
        print(f"❌ SCRIPT ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test playlist detail route")
    parser.add_argument("--user", type=str, help="User identifier (ID, Spotify ID, or display name)")
    args = parser.parse_args()
    test_playlist_detail(args.user) 