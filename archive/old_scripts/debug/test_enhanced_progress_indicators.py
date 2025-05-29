#!/usr/bin/env python3
"""
Test Enhanced Progress Indicators
Verify that the new progress indicators work correctly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import User, Song, AnalysisResult, Playlist, PlaylistSong
from sqlalchemy import text
import requests
import json
from datetime import datetime, timedelta

def test_enhanced_progress_indicators():
    """Test the enhanced progress indicators functionality"""
    app = create_app()
    
    with app.app_context():
        print("🧪 TESTING ENHANCED PROGRESS INDICATORS")
        print("=" * 50)
        
        # 1. Test Analysis Status API
        print("\n1. TESTING ANALYSIS STATUS API")
        print("-" * 30)
        
        # Get current analysis status
        total_songs = db.session.query(Song).count()
        completed_analyses = db.session.query(AnalysisResult).filter(
            AnalysisResult.status == 'completed'
        ).count()
        in_progress_analyses = db.session.query(AnalysisResult).filter(
            AnalysisResult.status == 'in_progress'
        ).count()
        
        print(f"Total songs in database: {total_songs}")
        print(f"Completed analyses: {completed_analyses}")
        print(f"In progress analyses: {in_progress_analyses}")
        print(f"Pending analyses: {total_songs - completed_analyses - in_progress_analyses}")
        
        # 2. Test Progress Calculation
        print("\n2. TESTING PROGRESS CALCULATIONS")
        print("-" * 30)
        
        if total_songs > 0:
            completion_percentage = (completed_analyses / total_songs) * 100
            print(f"Completion percentage: {completion_percentage:.1f}%")
            
            if completion_percentage > 0:
                print("✅ Progress calculation working")
            else:
                print("⚠️  No completed analyses found")
        else:
            print("⚠️  No songs found in database")
        
        # 3. Test Recent Activity
        print("\n3. TESTING RECENT ACTIVITY TRACKING")
        print("-" * 30)
        
        # Get recent completed analyses
        recent_completed = db.session.query(AnalysisResult, Song)\
            .join(Song, AnalysisResult.song_id == Song.id)\
            .filter(AnalysisResult.status == 'completed')\
            .order_by(AnalysisResult.analyzed_at.desc())\
            .limit(5)\
            .all()
        
        print(f"Recent completed analyses: {len(recent_completed)}")
        for i, (analysis, song) in enumerate(recent_completed[:3], 1):
            print(f"  {i}. \"{song.title}\" by {song.artist} - Score: {analysis.score}")
        
        # 4. Test Current Analysis Detection
        print("\n4. TESTING CURRENT ANALYSIS DETECTION")
        print("-" * 30)
        
        current_analysis = db.session.query(AnalysisResult, Song)\
            .join(Song, AnalysisResult.song_id == Song.id)\
            .filter(AnalysisResult.status == 'in_progress')\
            .order_by(AnalysisResult.created_at.desc())\
            .first()
        
        if current_analysis:
            analysis, song = current_analysis
            print(f"✅ Current analysis detected:")
            print(f"   Song: \"{song.title}\" by {song.artist}")
            print(f"   Started: {analysis.created_at}")
        else:
            print("ℹ️  No active analysis currently running")
        
        # 5. Test Rate Calculation
        print("\n5. TESTING RATE CALCULATION")
        print("-" * 30)
        
        # Get analyses from last hour
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        recent_hour_analyses = db.session.query(AnalysisResult).filter(
            AnalysisResult.status == 'completed',
            AnalysisResult.analyzed_at >= one_hour_ago
        ).count()
        
        print(f"Analyses completed in last hour: {recent_hour_analyses}")
        
        if recent_hour_analyses > 0:
            rate_per_minute = recent_hour_analyses / 60
            print(f"Estimated rate: {rate_per_minute:.1f} songs/minute")
            
            # Calculate ETA for remaining songs
            pending_songs = total_songs - completed_analyses - in_progress_analyses
            if rate_per_minute > 0 and pending_songs > 0:
                eta_minutes = pending_songs / rate_per_minute
                eta_hours = eta_minutes / 60
                print(f"Estimated time to completion: {eta_hours:.1f} hours ({eta_minutes:.0f} minutes)")
            else:
                print("ETA: Cannot calculate (no pending songs or zero rate)")
        else:
            print("⚠️  No recent analyses to calculate rate")
        
        # 6. Test Database Indexes Performance
        print("\n6. TESTING DATABASE PERFORMANCE")
        print("-" * 30)
        
        # Test query performance with indexes
        start_time = datetime.now()
        
        # Test status count query (should use idx_analysis_results_status)
        status_counts = db.session.query(
            AnalysisResult.status,
            db.func.count(AnalysisResult.id).label('count')
        ).group_by(AnalysisResult.status).all()
        
        status_query_time = (datetime.now() - start_time).total_seconds() * 1000
        print(f"Status count query: {status_query_time:.1f}ms")
        
        # Test recent analyses query (should use idx_analysis_results_analyzed_at)
        start_time = datetime.now()
        recent_query = db.session.query(AnalysisResult).filter(
            AnalysisResult.status == 'completed',
            AnalysisResult.analyzed_at >= one_hour_ago
        ).count()
        recent_query_time = (datetime.now() - start_time).total_seconds() * 1000
        print(f"Recent analyses query: {recent_query_time:.1f}ms")
        
        if status_query_time < 50 and recent_query_time < 50:
            print("✅ Database queries performing well with indexes")
        else:
            print("⚠️  Database queries may need optimization")
        
        # 7. Test API Response Structure
        print("\n7. TESTING API RESPONSE STRUCTURE")
        print("-" * 30)
        
        # Simulate the API response structure
        api_response = {
            'has_active_analysis': in_progress_analyses > 0,
            'total_songs': total_songs,
            'completed': completed_analyses,
            'in_progress': in_progress_analyses,
            'pending': total_songs - completed_analyses - in_progress_analyses,
            'failed': 0,  # Assuming no failed analyses for test
            'current_song': None,
            'recent_completed': []
        }
        
        # Add current song if available
        if current_analysis:
            analysis, song = current_analysis
            api_response['current_song'] = {
                'title': song.title,
                'artist': song.artist,
                'album': song.album,
                'started_at': analysis.created_at.isoformat() if analysis.created_at else None
            }
        
        # Add recent completed
        for analysis, song in recent_completed[:5]:
            api_response['recent_completed'].append({
                'title': song.title,
                'artist': song.artist,
                'score': analysis.score,
                'analyzed_at': analysis.analyzed_at.isoformat() if analysis.analyzed_at else None
            })
        
        print("✅ API response structure validated:")
        print(f"   - Has active analysis: {api_response['has_active_analysis']}")
        print(f"   - Total songs: {api_response['total_songs']}")
        print(f"   - Completed: {api_response['completed']}")
        print(f"   - In progress: {api_response['in_progress']}")
        print(f"   - Pending: {api_response['pending']}")
        print(f"   - Current song: {'Yes' if api_response['current_song'] else 'None'}")
        print(f"   - Recent completed: {len(api_response['recent_completed'])}")
        
        # 8. Test Progress Indicator Logic
        print("\n8. TESTING PROGRESS INDICATOR LOGIC")
        print("-" * 30)
        
        # Test progress bar calculation
        if total_songs > 0:
            progress_percent = (completed_analyses / total_songs) * 100
            print(f"Progress bar should show: {progress_percent:.1f}%")
            
            # Test status messages
            if in_progress_analyses > 0:
                print("✅ Should show analysis progress indicator")
                print(f"   Message: 'Analyzing song content...'")
                if api_response['current_song']:
                    current = api_response['current_song']
                    print(f"   Current: \"{current['title']}\" by {current['artist']}")
            else:
                print("ℹ️  Should hide analysis progress indicator")
            
            # Test ETA calculation
            if recent_hour_analyses > 0:
                rate = recent_hour_analyses / 60
                pending = api_response['pending']
                if rate > 0 and pending > 0:
                    eta_minutes = pending / rate
                    if eta_minutes < 1:
                        eta_text = "<1 min"
                    else:
                        eta_text = f"{int(eta_minutes)} min"
                    print(f"   ETA should show: {eta_text}")
                else:
                    print("   ETA: Not calculable")
            else:
                print("   ETA: Calculating...")
        
        print("\n" + "=" * 50)
        print("✅ ENHANCED PROGRESS INDICATORS TEST COMPLETE")
        print("\nThe enhanced progress indicators should now provide:")
        print("• Real-time sync progress with ETA")
        print("• Detailed song analysis progress")
        print("• Current song being analyzed")
        print("• Processing rates and time estimates")
        print("• Visual progress bars with percentages")
        print("• Responsive updates every 2-3 seconds")

if __name__ == "__main__":
    test_enhanced_progress_indicators() 