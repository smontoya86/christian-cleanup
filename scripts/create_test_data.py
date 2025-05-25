#!/usr/bin/env python3
"""
Test Data Creation Script
Creates realistic test data for performance testing
"""

import time
import sys
import os
import random
from datetime import datetime, timedelta
sys.path.append('/app')

from app import create_app
from app.models import Song, AnalysisResult, Playlist, PlaylistSong, User
from app.extensions import db

def create_test_data():
    """Create test data for performance testing"""
    app = create_app()
    
    with app.app_context():
        print("🚀 CREATING TEST DATA FOR PERFORMANCE TESTING")
        print("=" * 60)
        
        # Create test user
        print("\n👤 Creating test user...")
        test_user = User(
            spotify_id='perf_test_user_001',
            email='performance@test.com',
            display_name='Performance Test User',
            access_token='test_access_token_001',
            refresh_token='test_refresh_token_001',
            token_expiry=datetime.utcnow() + timedelta(hours=1)
        )
        db.session.add(test_user)
        db.session.flush()
        print(f"✅ Created user: {test_user.display_name}")
        
        # Create test songs
        print(f"\n🎵 Creating test songs...")
        songs = []
        artists = ['Christian Artist ' + str(i) for i in range(1, 21)]  # 20 artists
        albums = ['Christian Album ' + str(i) for i in range(1, 51)]   # 50 albums
        
        for i in range(1000):  # Create 1000 songs
            song = Song(
                spotify_id=f'test_song_{i:04d}',
                title=f'Christian Song {i}',
                artist=random.choice(artists),
                album=random.choice(albums),
                duration_ms=180000 + random.randint(-60000, 120000),  # 2-5 minutes
                explicit=random.choice([True, False]) if i % 10 == 0 else False  # 10% explicit
            )
            songs.append(song)
            db.session.add(song)
            
            if i % 100 == 0:
                print(f"   Created {i+1} songs...")
        
        db.session.flush()
        print(f"✅ Created {len(songs)} songs")
        
        # Create analysis results for 70% of songs
        print(f"\n📊 Creating analysis results...")
        analysis_count = 0
        statuses = ['completed', 'pending', 'failed']
        concern_levels = ['low', 'medium', 'high']
        
        for i, song in enumerate(songs):
            if random.random() < 0.7:  # 70% of songs have analysis
                analysis = AnalysisResult(
                    song_id=song.id,
                    status=random.choice(statuses) if i % 20 != 0 else 'completed',  # 95% completed
                    score=random.randint(60, 100),
                    concern_level=random.choice(concern_levels),
                    explanation=f'Test analysis explanation for song {i}. This song demonstrates Christian values through its lyrics and message.',
                    analyzed_at=datetime.utcnow() - timedelta(days=random.randint(0, 30))
                )
                db.session.add(analysis)
                analysis_count += 1
            
            if i % 100 == 0:
                print(f"   Created {analysis_count} analysis results...")
        
        db.session.flush()
        print(f"✅ Created {analysis_count} analysis results")
        
        # Create test playlists
        print(f"\n📋 Creating test playlists...")
        playlists = []
        for i in range(50):  # Create 50 playlists
            playlist = Playlist(
                spotify_id=f'test_playlist_{i:03d}',
                name=f'Christian Playlist {i}',
                owner_id=test_user.id,
                updated_at=datetime.utcnow() - timedelta(days=random.randint(0, 100))
            )
            playlists.append(playlist)
            db.session.add(playlist)
        
        db.session.flush()
        print(f"✅ Created {len(playlists)} playlists")
        
        # Add songs to playlists
        print(f"\n🔗 Adding songs to playlists...")
        playlist_song_count = 0
        
        for playlist in playlists:
            # Each playlist gets 10-50 songs
            num_songs = random.randint(10, 50)
            selected_songs = random.sample(songs, min(num_songs, len(songs)))
            
            for position, song in enumerate(selected_songs, 1):
                playlist_song = PlaylistSong(
                    playlist_id=playlist.id,
                    song_id=song.id,
                    track_position=position
                )
                db.session.add(playlist_song)
                playlist_song_count += 1
        
        db.session.commit()
        print(f"✅ Created {playlist_song_count} playlist-song relationships")
        
        # Summary
        print(f"\n📊 TEST DATA SUMMARY")
        print("=" * 40)
        print(f"👤 Users: 1")
        print(f"🎵 Songs: {len(songs)}")
        print(f"📊 Analysis Results: {analysis_count}")
        print(f"📋 Playlists: {len(playlists)}")
        print(f"🔗 Playlist Songs: {playlist_song_count}")
        
        # Verify data
        print(f"\n🔍 VERIFYING DATA")
        print("-" * 30)
        
        total_songs = db.session.query(Song).count()
        total_analyses = db.session.query(AnalysisResult).count()
        completed_analyses = db.session.query(AnalysisResult).filter(AnalysisResult.status == 'completed').count()
        total_playlists = db.session.query(Playlist).count()
        
        print(f"✅ Songs in database: {total_songs:,}")
        print(f"✅ Analysis results: {total_analyses:,}")
        print(f"✅ Completed analyses: {completed_analyses:,}")
        print(f"✅ Playlists: {total_playlists:,}")
        
        completion_rate = (completed_analyses / total_songs) * 100 if total_songs > 0 else 0
        print(f"✅ Analysis completion rate: {completion_rate:.1f}%")

if __name__ == "__main__":
    create_test_data() 