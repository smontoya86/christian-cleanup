#!/usr/bin/env python3
"""
Minimal Mock Data Creation Script for Christian Music Curator Testing

This script creates test data by directly inserting into the database,
avoiding model definition issues.

Usage:
    python scripts/create_minimal_mock_data.py
"""

import os
import random
import sys
from datetime import datetime, timedelta

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from app import create_app, db


def create_mock_data():
    """Create test data directly via SQL"""
    print("🎵 Creating minimal mock data...")

    # Create Flask app context
    app = create_app()

    with app.app_context():
        conn = db.engine.connect()
        trans = conn.begin()

        try:
            # Create test users
            print("📊 Creating mock users...")

            # Check if users exist first
            user1_exists = conn.execute(
                text("SELECT id FROM users WHERE spotify_id = 'test_user_1'")
            ).fetchone()
            user2_exists = conn.execute(
                text("SELECT id FROM users WHERE spotify_id = 'test_user_2'")
            ).fetchone()

            if not user1_exists:
                conn.execute(
                    text("""
                    INSERT INTO users (spotify_id, email, display_name, access_token, refresh_token, token_expiry, created_at, updated_at, is_admin)
                    VALUES ('test_user_1', 'john.christian@example.com', 'John Christian', 'mock_token_1', 'mock_refresh_1', :expiry, :now, :now, false)
                """),
                    {"expiry": datetime.utcnow() + timedelta(hours=1), "now": datetime.utcnow()},
                )
                print("Created user: John Christian")
            else:
                print("User John Christian already exists")

            if not user2_exists:
                conn.execute(
                    text("""
                    INSERT INTO users (spotify_id, email, display_name, access_token, refresh_token, token_expiry, created_at, updated_at, is_admin)
                    VALUES ('test_user_2', 'mary.worship@example.com', 'Mary Worship', 'mock_token_2', 'mock_refresh_2', :expiry, :now, :now, false)
                """),
                    {"expiry": datetime.utcnow() + timedelta(hours=1), "now": datetime.utcnow()},
                )
                print("Created user: Mary Worship")
            else:
                print("User Mary Worship already exists")

            # Get user IDs
            user1_id = conn.execute(
                text("SELECT id FROM users WHERE spotify_id = 'test_user_1'")
            ).fetchone()[0]
            user2_id = conn.execute(
                text("SELECT id FROM users WHERE spotify_id = 'test_user_2'")
            ).fetchone()[0]

            # Create test songs
            print("\n🎵 Creating mock songs...")

            songs_data = [
                (
                    "christian_song_1",
                    "Amazing Grace",
                    "Chris Tomlin",
                    "Worship Collection",
                    240000,
                    "Amazing grace, how sweet the sound\nThat saved a wretch like me",
                    False,
                ),
                (
                    "christian_song_2",
                    "How Great Thou Art",
                    "Hillsong Worship",
                    "Modern Hymns",
                    280000,
                    "O Lord my God, when I in awesome wonder\nConsider all the worlds thy hands have made",
                    False,
                ),
                (
                    "questionable_song_1",
                    "Party All Night",
                    "Secular Artist",
                    "Club Hits",
                    200000,
                    "We're gonna party all night long\nDrinking till the break of dawn",
                    False,
                ),
                (
                    "clean_song_1",
                    "Beautiful Day",
                    "Positive Vibes",
                    "Sunshine Collection",
                    190000,
                    "It's a beautiful day, the sun is shining bright\nEverything feels right",
                    False,
                ),
            ]

            song_ids = []
            for spotify_id, title, artist, album, duration, lyrics, explicit in songs_data:
                # Check if song exists
                existing_song = conn.execute(
                    text("SELECT id FROM songs WHERE spotify_id = :spotify_id"),
                    {"spotify_id": spotify_id},
                ).fetchone()

                if not existing_song:
                    result = conn.execute(
                        text("""
                        INSERT INTO songs (spotify_id, title, artist, album, duration_ms, lyrics, explicit, created_at, updated_at)
                        VALUES (:spotify_id, :title, :artist, :album, :duration_ms, :lyrics, :explicit, :now, :now)
                        RETURNING id
                    """),
                        {
                            "spotify_id": spotify_id,
                            "title": title,
                            "artist": artist,
                            "album": album,
                            "duration_ms": duration,
                            "lyrics": lyrics,
                            "explicit": explicit,
                            "now": datetime.utcnow(),
                        },
                    )
                    song_id = result.fetchone()[0]
                    song_ids.append(song_id)
                    print(f"Created song: {title} by {artist}")
                else:
                    song_ids.append(existing_song[0])
                    print(f"Song '{title}' already exists")

            # Create analysis results
            print("\n📊 Creating analysis results...")

            analysis_data = [
                (song_ids[0], "completed", 95.0, "Low", '["worship", "salvation", "grace"]', "{}"),
                (song_ids[1], "completed", 98.0, "Low", '["worship", "praise", "creation"]', "{}"),
                (
                    song_ids[2],
                    "completed",
                    45.0,
                    "High",
                    "[]",
                    '{"substance_abuse": ["drinking"], "materialism": ["money", "cars"]}',
                ),
                (song_ids[3], "completed", 85.0, "Low", '["gratitude", "joy"]', "{}"),
            ]

            for song_id, status, score, concern_level, themes, problematic_content in analysis_data:
                # Check if analysis exists
                existing_analysis = conn.execute(
                    text("SELECT id FROM analysis_results WHERE song_id = :song_id"),
                    {"song_id": song_id},
                ).fetchone()

                if not existing_analysis:
                    conn.execute(
                        text("""
                        INSERT INTO analysis_results (song_id, status, score, concern_level, themes, problematic_content, analyzed_at, created_at, updated_at)
                        VALUES (:song_id, :status, :score, :concern_level, :themes, :problematic_content, :analyzed_at, :now, :now)
                    """),
                        {
                            "song_id": song_id,
                            "status": status,
                            "score": score,
                            "concern_level": concern_level,
                            "themes": themes,
                            "problematic_content": problematic_content,
                            "analyzed_at": datetime.utcnow()
                            - timedelta(days=random.randint(1, 30)),
                            "now": datetime.utcnow(),
                        },
                    )
                    print(f"Created analysis for song ID {song_id}")
                else:
                    print(f"Analysis for song ID {song_id} already exists")

            # Create playlists
            print("\n📋 Creating playlists...")

            playlists_data = [
                (
                    user1_id,
                    "playlist_worship_1",
                    "Sunday Worship",
                    "Songs for Sunday morning worship service",
                    "https://via.placeholder.com/300x300?text=Worship",
                    2,
                    [0, 1],
                ),
                (
                    user1_id,
                    "playlist_mixed_1",
                    "Mixed Playlist",
                    "A mix of different music styles",
                    "https://via.placeholder.com/300x300?text=Mixed",
                    3,
                    [0, 2, 3],
                ),
                (
                    user2_id,
                    "playlist_christian_1",
                    "Christian Favorites",
                    "My favorite Christian songs",
                    "https://via.placeholder.com/300x300?text=Christian",
                    3,
                    [0, 1, 3],
                ),
                (
                    user2_id,
                    "playlist_review_1",
                    "Needs Review",
                    "Playlist that needs content review",
                    "https://via.placeholder.com/300x300?text=Review",
                    1,
                    [2],
                ),
            ]

            for (
                owner_id,
                spotify_id,
                name,
                description,
                image_url,
                track_count,
                song_indices,
            ) in playlists_data:
                # Check if playlist exists
                existing_playlist = conn.execute(
                    text(
                        "SELECT id FROM playlists WHERE spotify_id = :spotify_id AND owner_id = :owner_id"
                    ),
                    {"spotify_id": spotify_id, "owner_id": owner_id},
                ).fetchone()

                if not existing_playlist:
                    result = conn.execute(
                        text("""
                        INSERT INTO playlists (owner_id, spotify_id, name, description, image_url, track_count, created_at, updated_at)
                        VALUES (:owner_id, :spotify_id, :name, :description, :image_url, :track_count, :now, :now)
                        RETURNING id
                    """),
                        {
                            "owner_id": owner_id,
                            "spotify_id": spotify_id,
                            "name": name,
                            "description": description,
                            "image_url": image_url,
                            "track_count": track_count,
                            "now": datetime.utcnow(),
                        },
                    )
                    playlist_id = result.fetchone()[0]
                    print(f"Created playlist: {name}")

                    # Add songs to playlist
                    for position, song_index in enumerate(song_indices):
                        conn.execute(
                            text("""
                            INSERT INTO playlist_songs (playlist_id, song_id, track_position, added_at_spotify)
                            VALUES (:playlist_id, :song_id, :track_position, :added_at)
                        """),
                            {
                                "playlist_id": playlist_id,
                                "song_id": song_ids[song_index],
                                "track_position": position,
                                "added_at": datetime.utcnow()
                                - timedelta(days=random.randint(1, 100)),
                            },
                        )
                else:
                    print(f"Playlist '{name}' already exists")

            trans.commit()
            print("\n✅ Mock data creation completed!")
            print("=" * 60)
            print("🌐 You can now test the application at: http://localhost:5001")
            print("🔑 Mock login URLs:")
            print("    - http://localhost:5001/auth/mock-login/test_user_1 (John Christian)")
            print("    - http://localhost:5001/auth/mock-login/test_user_2 (Mary Worship)")
            print("🧪 Mock users page: http://localhost:5001/auth/mock-users")

        except Exception as e:
            trans.rollback()
            print(f"Error creating mock data: {e}")
            raise
        finally:
            conn.close()


if __name__ == "__main__":
    create_mock_data()
