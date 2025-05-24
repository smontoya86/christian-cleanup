#!/usr/bin/env python3
"""
Fix missing PlaylistSong associations by syncing playlist contents from Spotify.
This addresses the issue where playlists exist but have no songs.
"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.models import Playlist, Song, PlaylistSong, User
from app.services.spotify_service import SpotifyService
from app.utils.database import get_by_filter, get_all_by_filter, count_by_filter  # Add SQLAlchemy 2.0 utilities

def fix_playlist_songs():
    app = create_app()
    
    with app.app_context():
        print("🔄 Fixing missing PlaylistSong associations...")
        
        # Get user and ensure token is valid
        user = get_by_filter(User)  # Get first user
        if not user:
            print("❌ No users found in database")
            return
            
        print(f"👤 Working with user: {user.display_name}")
        
        # Refresh token if needed
        if not user.ensure_token_valid():
            print("❌ Unable to refresh user token")
            return
            
        print("✅ User token is valid")
        
        # Initialize Spotify service
        sp = SpotifyService(user.access_token)
        if not sp.sp:
            print("❌ Failed to create Spotify service")
            return
            
        print("✅ Spotify service initialized")
        
        # Get all playlists with no songs using SQLAlchemy 2.0 pattern
        playlists = get_all_by_filter(Playlist, owner_id=user.id)
        print(f"📋 Found {len(playlists)} playlists to check")
        
        fixed_count = 0
        for playlist in playlists:
            current_song_count = len(playlist.songs)
            print(f"\n🎵 Checking playlist: {playlist.name}")
            print(f"   Current songs in DB: {current_song_count}")
            
            if current_song_count > 0:
                print("   ✅ Already has songs, skipping")
                continue
                
            try:
                # Get playlist tracks from Spotify
                print("   📥 Fetching tracks from Spotify...")
                tracks_response = sp.get_playlist_items(
                    playlist.spotify_id,
                    fields='items(track(id,name,artists(name),album(name,images),duration_ms))',
                    limit=50  # Start with first 50 tracks
                )
                
                if not tracks_response or not tracks_response.get('items'):
                    print("   ⚠️  No tracks found on Spotify")
                    continue
                    
                spotify_track_count = len(tracks_response['items'])
                print(f"   📱 Found {spotify_track_count} tracks on Spotify")
                
                added_songs = 0
                for idx, item in enumerate(tracks_response['items']):
                    track_data = item.get('track')
                    if not track_data or not track_data.get('id'):
                        continue
                        
                    song_spotify_id = track_data['id']
                    
                    # Find or create song in database using SQLAlchemy 2.0 pattern
                    song_in_db = get_by_filter(Song, spotify_id=song_spotify_id)
                    if not song_in_db:
                        # Create new song
                        album_data = track_data.get('album')
                        album_art_url = None
                        if album_data and album_data.get('images') and len(album_data['images']) > 0:
                            album_art_url = album_data['images'][0]['url']

                        song_in_db = Song(
                            spotify_id=song_spotify_id,
                            title=track_data.get('name', 'Unknown Title'),
                            artist=', '.join([artist['name'] for artist in track_data.get('artists', [])]),
                            album=album_data.get('name', 'Unknown Album') if album_data else 'Unknown Album',
                            album_art_url=album_art_url,
                            duration_ms=track_data.get('duration_ms')
                        )
                        db.session.add(song_in_db)
                        db.session.flush()  # Get the ID
                        
                    # Create PlaylistSong association using SQLAlchemy 2.0 pattern
                    playlist_song_assoc = get_by_filter(PlaylistSong, 
                        playlist_id=playlist.id, 
                        song_id=song_in_db.id
                    )
                    
                    if not playlist_song_assoc:
                        playlist_song_assoc = PlaylistSong(
                            playlist_id=playlist.id,
                            song_id=song_in_db.id,
                            track_position=idx
                        )
                        db.session.add(playlist_song_assoc)
                        added_songs += 1
                        
                # Commit changes for this playlist
                db.session.commit()
                print(f"   ✅ Added {added_songs} song associations")
                fixed_count += 1
                
            except Exception as e:
                print(f"   ❌ Error processing playlist: {e}")
                db.session.rollback()
                continue
                
        print(f"\n🎉 Fixed {fixed_count} playlists")
        
        # Verify the fix using SQLAlchemy 2.0 pattern
        total_associations = count_by_filter(PlaylistSong)
        print(f"📊 Total PlaylistSong associations now: {total_associations}")

if __name__ == '__main__':
    fix_playlist_songs() 