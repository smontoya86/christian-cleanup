#!/usr/bin/env python3
"""
Cleanup Test Analyses
Remove the test in-progress analysis records
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import AnalysisResult

def cleanup_test_analyses():
    """Remove test in-progress analysis records"""
    app = create_app()
    
    with app.app_context():
        print("🧹 CLEANING UP TEST ANALYSES")
        print("=" * 50)
        
        # Get all in-progress analyses
        in_progress_analyses = db.session.query(AnalysisResult).filter_by(status='in_progress').all()
        
        print(f"Found {len(in_progress_analyses)} in-progress analyses to clean up")
        
        if in_progress_analyses:
            print("\n1. REMOVING IN-PROGRESS ANALYSES")
            print("-" * 40)
            
            for analysis in in_progress_analyses:
                db.session.delete(analysis)
                print(f"   Removed in-progress analysis for song ID {analysis.song_id}")
            
            db.session.commit()
            print(f"✅ Removed {len(in_progress_analyses)} in-progress analyses")
        else:
            print("ℹ️  No in-progress analyses found to clean up")
        
        # Show final status
        print("\n2. FINAL ANALYSIS STATUS")
        print("-" * 40)
        
        from app.models import Song
        total_songs = db.session.query(Song).count()
        completed = db.session.query(AnalysisResult).filter_by(status='completed').count()
        in_progress = db.session.query(AnalysisResult).filter_by(status='in_progress').count()
        pending = total_songs - completed - in_progress
        
        print(f"Total songs: {total_songs}")
        print(f"Completed: {completed}")
        print(f"In progress: {in_progress}")
        print(f"Pending: {pending}")
        
        print("\n" + "=" * 50)
        print("✅ CLEANUP COMPLETE")
        print("\nThe progress indicator should now be hidden on your dashboard.")

if __name__ == "__main__":
    cleanup_test_analyses() 