#!/usr/bin/env python3
"""
Performance Database Indexes Creation Script
Creates indexes identified as critical for performance optimization
"""

import time
import sys
import os
sys.path.append('/app')

from app import create_app
from app.extensions import db
from sqlalchemy import text

def create_performance_indexes():
    """Create performance-critical database indexes"""
    app = create_app()
    
    with app.app_context():
        print("🚀 CREATING PERFORMANCE INDEXES")
        print("=" * 60)
        
        # List of indexes to create with their performance impact
        indexes = [
            {
                'name': 'idx_analysis_results_status',
                'sql': 'CREATE INDEX IF NOT EXISTS idx_analysis_results_status ON analysis_results (status);',
                'description': 'Index on analysis_results.status for filtering completed analyses',
                'impact': 'High - Used in Progress API and Performance API'
            },
            {
                'name': 'idx_analysis_results_analyzed_at',
                'sql': 'CREATE INDEX IF NOT EXISTS idx_analysis_results_analyzed_at ON analysis_results (analyzed_at DESC);',
                'description': 'Index on analysis_results.analyzed_at for time-based ordering',
                'impact': 'High - Used in Progress API for recent results'
            },
            {
                'name': 'idx_analysis_results_song_id',
                'sql': 'CREATE INDEX IF NOT EXISTS idx_analysis_results_song_id_new ON analysis_results (song_id);',
                'description': 'Index on analysis_results.song_id for joins',
                'impact': 'High - Used in all song-analysis joins'
            },
            {
                'name': 'idx_playlist_songs_playlist_id',
                'sql': 'CREATE INDEX IF NOT EXISTS idx_playlist_songs_playlist_id ON playlist_songs (playlist_id);',
                'description': 'Index on playlist_songs.playlist_id for playlist queries',
                'impact': 'High - Used in playlist detail views'
            },
            {
                'name': 'idx_playlist_songs_track_position',
                'sql': 'CREATE INDEX IF NOT EXISTS idx_playlist_songs_track_position ON playlist_songs (playlist_id, track_position);',
                'description': 'Composite index for playlist song ordering',
                'impact': 'Medium - Used for ordered playlist display'
            },
            {
                'name': 'idx_playlists_owner_id',
                'sql': 'CREATE INDEX IF NOT EXISTS idx_playlists_owner_id ON playlists (owner_id);',
                'description': 'Index on playlists.owner_id for user playlist queries',
                'impact': 'High - Used in dashboard'
            },
            {
                'name': 'idx_playlists_updated_at',
                'sql': 'CREATE INDEX IF NOT EXISTS idx_playlists_updated_at ON playlists (updated_at DESC);',
                'description': 'Index on playlists.updated_at for recent playlists',
                'impact': 'Medium - Used in dashboard ordering'
            },
            {
                'name': 'idx_songs_explicit',
                'sql': 'CREATE INDEX IF NOT EXISTS idx_songs_explicit ON songs (explicit);',
                'description': 'Index on songs.explicit for filtering',
                'impact': 'Medium - Used in content filtering'
            },
            {
                'name': 'idx_songs_spotify_id_new',
                'sql': 'CREATE UNIQUE INDEX IF NOT EXISTS idx_songs_spotify_id_new ON songs (spotify_id);',
                'description': 'Unique index on songs.spotify_id for lookups',
                'impact': 'High - Used for song identification'
            },
            {
                'name': 'idx_analysis_results_composite',
                'sql': 'CREATE INDEX IF NOT EXISTS idx_analysis_results_composite ON analysis_results (song_id, status, analyzed_at DESC);',
                'description': 'Composite index for complex analysis queries',
                'impact': 'Very High - Covers multiple query patterns'
            }
        ]
        
        created_indexes = []
        failed_indexes = []
        
        for index in indexes:
            print(f"\n📝 Creating: {index['name']}")
            print(f"   Description: {index['description']}")
            print(f"   Impact: {index['impact']}")
            
            try:
                start_time = time.time()
                db.session.execute(text(index['sql']))
                db.session.commit()
                end_time = time.time()
                
                creation_time = (end_time - start_time) * 1000
                print(f"   ✅ Created in {creation_time:.1f}ms")
                created_indexes.append(index['name'])
                
            except Exception as e:
                print(f"   ❌ Failed: {str(e)}")
                failed_indexes.append((index['name'], str(e)))
                db.session.rollback()
        
        # Summary
        print(f"\n📊 INDEX CREATION SUMMARY")
        print("=" * 40)
        print(f"✅ Successfully created: {len(created_indexes)} indexes")
        for idx in created_indexes:
            print(f"   - {idx}")
        
        if failed_indexes:
            print(f"\n❌ Failed to create: {len(failed_indexes)} indexes")
            for idx, error in failed_indexes:
                print(f"   - {idx}: {error}")
        
        # Verify indexes exist
        print(f"\n🔍 VERIFYING INDEXES")
        print("-" * 30)
        
        verify_query = """
        SELECT indexname, tablename, indexdef 
        FROM pg_indexes 
        WHERE schemaname = 'public' 
        AND indexname LIKE 'idx_%'
        ORDER BY tablename, indexname;
        """
        
        result = db.session.execute(text(verify_query)).fetchall()
        
        print(f"Found {len(result)} performance indexes:")
        for row in result:
            print(f"   - {row[1]}.{row[0]}")
        
        print(f"\n🎯 NEXT STEPS")
        print("-" * 20)
        print("1. Run performance tests to measure improvement")
        print("2. Monitor query performance in production")
        print("3. Consider additional indexes based on usage patterns")

if __name__ == "__main__":
    create_performance_indexes() 