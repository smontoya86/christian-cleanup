#!/usr/bin/env python3
"""
Create Persistent Analysis Progress
Create in-progress analysis records that persist so you can see the progress indicators
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import Song, AnalysisResult
from datetime import datetime

def create_persistent_analysis():
    """Create persistent in-progress analysis records"""
    app = create_app()
    
    with app.app_context():
        print("🎭 CREATING PERSISTENT ANALYSIS PROGRESS")
        print("=" * 50)
        
        # Get some songs that haven't been analyzed yet
        unanalyzed_songs = db.session.query(Song).outerjoin(AnalysisResult).filter(
            AnalysisResult.id.is_(None)
        ).limit(5).all()
        
        if not unanalyzed_songs:
            print("⚠️  No unanalyzed songs found. Using existing songs.")
            # Get some random songs and remove their existing analyses
            songs = db.session.query(Song).limit(5).all()
            for song in songs:
                existing = db.session.query(AnalysisResult).filter_by(song_id=song.id).first()
                if existing:
                    db.session.delete(existing)
            db.session.commit()
            unanalyzed_songs = songs
        
        print(f"Found {len(unanalyzed_songs)} songs to create analyses for")
        
        # Create persistent in-progress analysis records
        print("\n1. CREATING PERSISTENT IN-PROGRESS ANALYSES")
        print("-" * 40)
        
        created_count = 0
        for song in unanalyzed_songs:
            # Create new in-progress analysis
            analysis = AnalysisResult(
                song_id=song.id,
                status='in_progress',
                created_at=datetime.utcnow()
            )
            db.session.add(analysis)
            print(f"   Created in-progress analysis for \"{song.title}\" by {song.artist}")
            created_count += 1
        
        db.session.commit()
        print(f"✅ Created {created_count} persistent in-progress analysis records")
        
        # Show current status
        print("\n2. CURRENT ANALYSIS STATUS")
        print("-" * 40)
        
        total_songs = db.session.query(Song).count()
        completed = db.session.query(AnalysisResult).filter_by(status='completed').count()
        in_progress = db.session.query(AnalysisResult).filter_by(status='in_progress').count()
        pending = total_songs - completed - in_progress
        
        print(f"Total songs: {total_songs}")
        print(f"Completed: {completed}")
        print(f"In progress: {in_progress}")
        print(f"Pending: {pending}")
        
        print("\n3. PROGRESS INDICATOR IS NOW ACTIVE")
        print("-" * 40)
        print("🎯 Go to your dashboard at http://localhost:5001/dashboard")
        print("📊 You should now see the 'Song Analysis in Progress' indicator!")
        print("⏱️  The indicator will show:")
        print("   • Current songs being analyzed")
        print("   • Progress percentage")
        print("   • Elapsed time and ETA")
        print("   • Processing rate")
        print("   • Recent completed analyses")
        
        print("\n4. TO CLEAN UP LATER")
        print("-" * 40)
        print("🧹 To remove these test analyses later, run:")
        print("   python scripts/cleanup_test_analyses.py")
        
        print("\n" + "=" * 50)
        print("✅ PERSISTENT ANALYSIS PROGRESS CREATED")
        print("\nThe progress indicator should now be visible on your dashboard!")
        print("It will update every 3 seconds with live data.")

if __name__ == "__main__":
    create_persistent_analysis() 