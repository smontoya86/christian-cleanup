#!/usr/bin/env python3
"""
Database Performance Analysis Script
Analyzes current database performance and identifies optimization opportunities
"""

import time
import sys
import os
sys.path.append('/app')

from app import create_app
from app.models import Song, AnalysisResult, Playlist, PlaylistSong, User
from app.extensions import db
from sqlalchemy import text, func
from datetime import datetime

def analyze_database_performance():
    """Analyze current database performance"""
    app = create_app()
    
    with app.app_context():
        print("🔍 DATABASE PERFORMANCE ANALYSIS")
        print("=" * 60)
        
        # 1. Table sizes and counts
        print("\n📊 TABLE STATISTICS")
        print("-" * 30)
        
        tables = [
            ('Users', User),
            ('Songs', Song), 
            ('Playlists', Playlist),
            ('Playlist Songs', PlaylistSong),
            ('Analysis Results', AnalysisResult)
        ]
        
        for table_name, model in tables:
            start = time.time()
            count = db.session.query(model).count()
            elapsed = (time.time() - start) * 1000
            print(f"{table_name:20}: {count:,} records ({elapsed:.1f}ms)")
        
        # 2. Analysis completion rate
        print("\n📈 ANALYSIS STATISTICS")
        print("-" * 30)
        
        start = time.time()
        total_songs = db.session.query(Song).count()
        elapsed = (time.time() - start) * 1000
        print(f"Total Songs: {total_songs:,} ({elapsed:.1f}ms)")
        
        start = time.time()
        completed_analysis = db.session.query(AnalysisResult).filter(
            AnalysisResult.status == 'completed'
        ).count()
        elapsed = (time.time() - start) * 1000
        print(f"Completed Analysis: {completed_analysis:,} ({elapsed:.1f}ms)")
        
        if total_songs > 0:
            completion_rate = (completed_analysis / total_songs) * 100
            print(f"Completion Rate: {completion_rate:.1f}%")
        
        # 3. Slow query analysis
        print("\n🐌 SLOW QUERY ANALYSIS")
        print("-" * 30)
        
        # Test progress API query performance
        start = time.time()
        progress_query = db.session.query(
            func.count(Song.id).label('total_songs'),
            func.count(AnalysisResult.id).label('analyzed_songs')
        ).outerjoin(AnalysisResult, Song.id == AnalysisResult.song_id).first()
        elapsed = (time.time() - start) * 1000
        print(f"Progress API Query: {elapsed:.1f}ms")
        
        # Test performance API query
        start = time.time()
        performance_query = db.session.query(
            func.count(AnalysisResult.id).label('completed_count')
        ).filter(AnalysisResult.status == 'completed').first()
        elapsed = (time.time() - start) * 1000
        print(f"Performance API Query: {elapsed:.1f}ms")
        
        # Test complex playlist analysis query
        start = time.time()
        playlist_query = db.session.query(Playlist).join(PlaylistSong).join(Song).join(AnalysisResult).limit(10).all()
        elapsed = (time.time() - start) * 1000
        print(f"Complex Playlist Query: {elapsed:.1f}ms")
        
        # 4. Index analysis
        print("\n🔍 INDEX ANALYSIS")
        print("-" * 30)
        
        # Check for existing indexes
        index_queries = [
            ("Songs by Spotify ID", "SELECT COUNT(*) FROM songs WHERE spotify_id = 'test'"),
            ("Analysis by Song ID", "SELECT COUNT(*) FROM analysis_results WHERE song_id = 1"),
            ("Analysis by Status", "SELECT COUNT(*) FROM analysis_results WHERE status = 'completed'"),
            ("Playlist Songs Join", "SELECT COUNT(*) FROM playlist_songs ps JOIN songs s ON ps.song_id = s.id"),
        ]
        
        for query_name, query in index_queries:
            start = time.time()
            result = db.session.execute(text(query)).scalar()
            elapsed = (time.time() - start) * 1000
            print(f"{query_name:25}: {elapsed:.1f}ms")
        
        # 5. Recommendations
        print("\n💡 OPTIMIZATION RECOMMENDATIONS")
        print("-" * 40)
        
        recommendations = []
        
        # Check if we need composite indexes
        if completed_analysis > 1000:
            recommendations.append("✅ Add composite index on (song_id, status) for analysis_results")
            recommendations.append("✅ Add index on concern_level for filtering")
        
        # Check playlist performance
        playlist_count = db.session.query(Playlist).count()
        if playlist_count > 100:
            recommendations.append("✅ Add composite index on (playlist_id, track_position) for playlist_songs")
        
        # Check for missing indexes
        recommendations.extend([
            "✅ Add index on songs.explicit for filtering",
            "✅ Add index on analysis_results.analyzed_at for time-based queries",
            "✅ Consider partitioning analysis_results by status"
        ])
        
        for rec in recommendations:
            print(rec)
        
        # 6. Performance targets
        print("\n🎯 PERFORMANCE TARGETS")
        print("-" * 30)
        print("Progress API: < 400ms (currently varies)")
        print("Performance API: < 500ms (currently varies)")
        print("Playlist Detail: < 100ms (currently varies)")
        print("Dashboard Load: < 50ms (currently varies)")

if __name__ == "__main__":
    analyze_database_performance() 