#!/usr/bin/env python3
"""
Test to verify what's happening with the specific playlist causing 500 errors.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.models import Playlist, Song, PlaylistSong, User
from app.utils.database import get_by_filter, get_all_by_filter, count_by_filter  # Add SQLAlchemy 2.0 utilities

def test_playlist_detail_simulation():
    app = create_app()
    
    with app.app_context():
        print("Testing playlist detail route simulation...")
        
        # Test with a specific playlist
        playlist_id = "1U8Fwac8vpvD1s98MVNK79"
        playlist = get_by_filter(Playlist, spotify_id=playlist_id)
        
        if playlist:
            print(f"✓ Found playlist: {playlist.name}")
            print(f"  Playlist ID: {playlist.id}, Spotify ID: {playlist.spotify_id}")
            print(f"  Owner ID: {playlist.owner_id}")
            print(f"  Songs count: {len(playlist.songs)}")
            
            # Check if owner exists
            owner = db.session.get(User, playlist.owner_id)
            if owner:
                print(f"✓ Owner found: {owner.display_name or owner.id}")
                print(f"  Spotify ID: {owner.spotify_id}")
                print(f"  Has access token: {bool(owner.access_token)}")
                print(f"  Token expires at: {owner.token_expiry}")
                
                # Test if ensure_token_valid() works without throwing exceptions
                try:
                    token_valid = owner.ensure_token_valid()
                    print(f"✓ ensure_token_valid() returned: {token_valid}")
                except Exception as e:
                    print(f"✗ ensure_token_valid() threw exception: {e}")
                    return False
                    
            else:
                print("✗ Owner not found!")
                
            # Test basic playlist data structure that the route expects
            try:
                playlist_details = {
                    'spotify_id': playlist.spotify_id,
                    'name': playlist.name,
                    'description': playlist.description,
                    'image_url': playlist.image_url,
                    'total_tracks': len(playlist.songs),
                    'score': playlist.overall_alignment_score
                }
                print("✓ Playlist details structure OK")
            except Exception as e:
                print(f"✗ Error creating playlist details: {e}")
                
        else:
            print(f"✗ Playlist {playlist_id} not found in database")
            
            # Check total playlists using SQLAlchemy 2.0 pattern
            total_playlists = count_by_filter(Playlist)
            print(f"Total playlists in DB: {total_playlists}")
            
            # Try with the first available playlist
            sample_playlist = get_by_filter(Playlist)  # Get first playlist
            if sample_playlist:
                print(f"Sample playlist: {sample_playlist.name} (ID: {sample_playlist.spotify_id})")

def test_route_requirements():
    """Test the basic requirements for playlist access."""
    with create_app().app_context():
        print("Testing route requirements...")
        # Just verify user exists using SQLAlchemy 2.0 pattern
        user = get_by_filter(User)  # Get first user

def test_token_refresh_simulation():
    """Test token refresh simulation."""
    with create_app().app_context():
        print("Testing token refresh simulation...")
        # Check if user exists using SQLAlchemy 2.0 pattern
        user = get_by_filter(User)  # Get first user

if __name__ == '__main__':
    test_playlist_detail_simulation()
    test_route_requirements()
    test_token_refresh_simulation() 