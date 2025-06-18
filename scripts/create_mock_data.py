#!/usr/bin/env python3
"""
Mock Data Creation Script for Christian Music Curator Testing

This script creates realistic test data including:
- Test users with Spotify tokens
- Sample playlists with Christian and secular songs
- Analysis results with various scores and themes
- Whitelist/blacklist entries for curation testing

Usage:
    python scripts/create_mock_data.py
"""

import sys
import os
from datetime import datetime, timedelta
import random

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models.models import User, Playlist, Song, PlaylistSong, AnalysisResult

def create_mock_users():
    """Create test users with realistic Spotify data"""
    users = [
        {
            'spotify_id': 'test_user_1',
            'email': 'john.christian@example.com',
            'display_name': 'John Christian',
            'access_token': 'mock_access_token_1',
            'refresh_token': 'mock_refresh_token_1',
            'token_expiry': datetime.utcnow() + timedelta(hours=1)
        },
        {
            'spotify_id': 'test_user_2', 
            'email': 'mary.worship@example.com',
            'display_name': 'Mary Worship',
            'access_token': 'mock_access_token_2',
            'refresh_token': 'mock_refresh_token_2',
            'token_expiry': datetime.utcnow() + timedelta(hours=1)
        }
    ]
    
    created_users = []
    for user_data in users:
        # Check if user already exists
        existing_user = User.query.filter_by(spotify_id=user_data['spotify_id']).first()
        if existing_user:
            print(f"User {user_data['display_name']} already exists, skipping...")
            created_users.append(existing_user)
            continue
            
        user = User(
            spotify_id=user_data['spotify_id'],
            email=user_data['email'],
            display_name=user_data['display_name'],
            access_token=user_data['access_token'],
            refresh_token=user_data['refresh_token'],
            token_expiry=user_data['token_expiry']
        )
        db.session.add(user)
        created_users.append(user)
        print(f"Created user: {user.display_name}")
    
    db.session.commit()
    return created_users

def create_mock_songs():
    """Create a variety of Christian and secular songs for testing"""
    songs_data = [
        # Christian Songs
        {
            'spotify_id': 'christian_song_1',
            'title': 'Amazing Grace',
            'artist': 'Chris Tomlin',
            'album': 'Worship Collection',
            'duration_ms': 240000,
            'lyrics': """Amazing grace, how sweet the sound
That saved a wretch like me
I once was lost, but now I'm found
Was blind, but now I see

'Twas grace that taught my heart to fear
And grace my fears relieved
How precious did that grace appear
The hour I first believed""",
            'analysis_score': 95,
            'themes': ['worship', 'salvation', 'grace'],
            'concern_level': 'low'
        },
        {
            'spotify_id': 'christian_song_2',
            'title': 'How Great Thou Art',
            'artist': 'Hillsong Worship',
            'album': 'Modern Hymns',
            'duration_ms': 280000,
            'lyrics': """O Lord my God, when I in awesome wonder
Consider all the worlds thy hands have made
I see the stars, I hear the rolling thunder
Thy power throughout the universe displayed

Then sings my soul, my Savior God, to thee
How great thou art, how great thou art
Then sings my soul, my Savior God, to thee
How great thou art, how great thou art""",
            'analysis_score': 98,
            'themes': ['worship', 'praise', 'creation'],
            'concern_level': 'low'
        },
        {
            'spotify_id': 'christian_song_3',
            'title': 'Blessed Be Your Name',
            'artist': 'Matt Redman',
            'album': 'Worship Songs',
            'duration_ms': 260000,
            'lyrics': """Blessed be your name in the land that is plentiful
Where your streams of abundance flow
Blessed be your name

Blessed be your name when I'm found in the desert place
Though I walk through the wilderness
Blessed be your name

Every blessing you pour out I'll turn back to praise
When the darkness closes in, Lord, still I will say
Blessed be the name of the Lord""",
            'analysis_score': 92,
            'themes': ['faith', 'trust', 'praise'],
            'concern_level': 'low'
        },
        # Questionable Content Songs
        {
            'spotify_id': 'questionable_song_1',
            'title': 'Party All Night',
            'artist': 'Secular Artist',
            'album': 'Club Hits',
            'duration_ms': 200000,
            'lyrics': """We're gonna party all night long
Drinking till the break of dawn
Money, cars, and diamond rings
These are just a few of my favorite things

Turn the music up real loud
Get crazy with the crowd
Live it up while we're young
Party till the morning sun""",
            'analysis_score': 45,
            'themes': [],
            'concern_level': 'high',
            'problematic_content': {
                'substance_abuse': ['drinking'],
                'materialism': ['money', 'cars', 'diamond rings']
            }
        },
        {
            'spotify_id': 'questionable_song_2',
            'title': 'Heartbreak Blues',
            'artist': 'Rock Band',
            'album': 'Emotional Journey',
            'duration_ms': 220000,
            'lyrics': """My heart is broken, can't you see
Life has no meaning without you and me
Sometimes I wonder if it's worth the fight
Drowning my sorrows every single night

The pain inside just won't go away
Wish I could find a better way
But darkness follows me around
Lost and never to be found""",
            'analysis_score': 65,
            'themes': [],
            'concern_level': 'medium',
            'problematic_content': {
                'depression': ['heartbreak', 'no meaning', 'darkness'],
                'substance_abuse': ['drowning sorrows']
            }
        },
        # Clean Secular Songs
        {
            'spotify_id': 'clean_song_1',
            'title': 'Beautiful Day',
            'artist': 'Positive Vibes',
            'album': 'Sunshine Collection',
            'duration_ms': 190000,
            'lyrics': """It's a beautiful day, the sun is shining bright
Everything feels right, everything's alright
Walking down the street with a smile on my face
This world's a beautiful place

Friends and family all around
Love and laughter can be found
Grateful for this life I live
So much joy that I can give""",
            'analysis_score': 85,
            'themes': ['gratitude', 'joy'],
            'concern_level': 'low'
        },
        {
            'spotify_id': 'clean_song_2',
            'title': 'Dreams Come True',
            'artist': 'Inspirational Artists',
            'album': 'Hope & Dreams',
            'duration_ms': 210000,
            'lyrics': """Chase your dreams, don't give up hope
Climb that mountain, walk that rope
Every step you take today
Brings you closer to your way

Believe in yourself, you can make it through
All your dreams can still come true
Work hard, stay strong, keep moving on
Success will come before too long""",
            'analysis_score': 80,
            'themes': ['hope', 'perseverance'],
            'concern_level': 'low'
        }
    ]
    
    created_songs = []
    for song_data in songs_data:
        # Check if song already exists
        existing_song = Song.query.filter_by(spotify_id=song_data['spotify_id']).first()
        if existing_song:
            print(f"Song '{song_data['title']}' already exists, skipping...")
            created_songs.append(existing_song)
            continue
            
        song = Song(
            spotify_id=song_data['spotify_id'],
            title=song_data['title'],
            artist=song_data['artist'],
            album=song_data['album'],
            duration_ms=song_data['duration_ms'],
            lyrics=song_data['lyrics']
        )
        db.session.add(song)
        db.session.flush()  # Get the ID
        
        # Create analysis result
        analysis = AnalysisResult(
            song_id=song.id,
            status='completed',
            score=song_data['analysis_score'],
            concern_level=song_data['concern_level'],
            themes=song_data['themes'],
            problematic_content=song_data.get('problematic_content', {}),
            created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30))
        )
        db.session.add(analysis)
        
        created_songs.append(song)
        print(f"Created song: {song.title} by {song.artist}")
    
    db.session.commit()
    return created_songs

def create_mock_playlists(users, songs):
    """Create playlists for users with mixed content"""
    playlists_data = [
        {
            'user_index': 0,  # John Christian
            'name': 'Sunday Worship',
            'description': 'Songs for Sunday morning worship service',
            'spotify_id': 'playlist_worship_1',
            'song_indices': [0, 1, 2],  # All Christian songs
            'image_url': 'https://via.placeholder.com/300x300?text=Worship'
        },
        {
            'user_index': 0,  # John Christian
            'name': 'Mixed Playlist',
            'description': 'A mix of different music styles',
            'spotify_id': 'playlist_mixed_1',
            'song_indices': [0, 3, 5, 6],  # Christian + questionable + clean
            'image_url': 'https://via.placeholder.com/300x300?text=Mixed'
        },
        {
            'user_index': 1,  # Mary Worship
            'name': 'Christian Favorites',
            'description': 'My favorite Christian songs',
            'spotify_id': 'playlist_christian_1',
            'song_indices': [0, 1, 2, 6],  # Mostly Christian + one clean
            'image_url': 'https://via.placeholder.com/300x300?text=Christian'
        },
        {
            'user_index': 1,  # Mary Worship
            'name': 'Needs Review',
            'description': 'Playlist that needs content review',
            'spotify_id': 'playlist_review_1',
            'song_indices': [3, 4, 5],  # Questionable content songs
            'image_url': 'https://via.placeholder.com/300x300?text=Review'
        }
    ]
    
    created_playlists = []
    for playlist_data in playlists_data:
        user = users[playlist_data['user_index']]
        
        # Check if playlist already exists
        existing_playlist = Playlist.query.filter_by(
            spotify_id=playlist_data['spotify_id'],
            owner_id=user.id
        ).first()
        if existing_playlist:
            print(f"Playlist '{playlist_data['name']}' already exists, skipping...")
            created_playlists.append(existing_playlist)
            continue
        
        playlist = Playlist(
            owner_id=user.id,
            spotify_id=playlist_data['spotify_id'],
            name=playlist_data['name'],
            description=playlist_data['description'],
            image_url=playlist_data['image_url'],
            track_count=len(playlist_data['song_indices'])
        )
        db.session.add(playlist)
        db.session.flush()  # Get the ID
        
        # Add songs to playlist
        for position, song_index in enumerate(playlist_data['song_indices']):
            song = songs[song_index]
            playlist_song = PlaylistSong(
                playlist_id=playlist.id,
                song_id=song.id,
                track_position=position,
                added_at_spotify=datetime.utcnow() - timedelta(days=random.randint(1, 100))
            )
            db.session.add(playlist_song)
        
        created_playlists.append(playlist)
        print(f"Created playlist: {playlist.name} for {user.display_name} with {len(playlist_data['song_indices'])} songs")
    
    db.session.commit()
    return created_playlists

def main():
    """Main function to create all mock data"""
    print("🎵 Creating mock data for Christian Music Curator...")
    print("=" * 60)
    
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        print("📊 Creating mock users...")
        users = create_mock_users()
        
        print("\n🎵 Creating mock songs with analysis...")
        songs = create_mock_songs()
        
        print("\n📋 Creating mock playlists...")
        playlists = create_mock_playlists(users, songs)
        
        print("\n✅ Mock data creation completed!")
        print("=" * 60)
        print(f"Created:")
        print(f"  👥 {len(users)} users")
        print(f"  🎵 {len(songs)} songs")
        print(f"  📋 {len(playlists)} playlists")
        print(f"\n🌐 You can now test the application at: http://localhost:5001")
        print(f"📧 Test user emails:")
        for user in users:
            print(f"    - {user.email} ({user.display_name})")

if __name__ == '__main__':
    main() 