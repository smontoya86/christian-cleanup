#!/usr/bin/env python3
"""
Simulate Analysis Progress
Create some in-progress analysis records to demonstrate the progress indicators
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import Song, AnalysisResult
from datetime import datetime
import time
import random

def simulate_analysis_progress():
    """Simulate analysis progress to demonstrate the progress indicators"""
    app = create_app()
    
    with app.app_context():
        print("🎭 SIMULATING ANALYSIS PROGRESS")
        print("=" * 50)
        
        # Get some songs that haven't been analyzed yet
        unanalyzed_songs = db.session.query(Song).outerjoin(AnalysisResult).filter(
            AnalysisResult.id.is_(None)
        ).limit(10).all()
        
        if not unanalyzed_songs:
            print("⚠️  No unanalyzed songs found. Let's use some existing songs.")
            # Get some random songs
            unanalyzed_songs = db.session.query(Song).limit(10).all()
        
        print(f"Found {len(unanalyzed_songs)} songs to simulate analysis on")
        
        # Create some in-progress analysis records
        print("\n1. CREATING IN-PROGRESS ANALYSIS RECORDS")
        print("-" * 40)
        
        in_progress_count = 0
        for i, song in enumerate(unanalyzed_songs[:3]):  # Create 3 in-progress analyses
            # Check if analysis already exists
            existing = db.session.query(AnalysisResult).filter_by(song_id=song.id).first()
            if existing:
                # Update existing to in-progress
                existing.status = 'in_progress'
                existing.created_at = datetime.utcnow()
                print(f"   Updated existing analysis for \"{song.title}\" by {song.artist}")
            else:
                # Create new in-progress analysis
                analysis = AnalysisResult(
                    song_id=song.id,
                    status='in_progress',
                    created_at=datetime.utcnow()
                )
                db.session.add(analysis)
                print(f"   Created in-progress analysis for \"{song.title}\" by {song.artist}")
            
            in_progress_count += 1
        
        db.session.commit()
        print(f"✅ Created {in_progress_count} in-progress analysis records")
        
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
        
        print("\n3. PROGRESS INDICATOR SHOULD NOW BE VISIBLE")
        print("-" * 40)
        print("🎯 Go to your dashboard at http://localhost:5001/dashboard")
        print("📊 You should now see the 'Song Analysis in Progress' indicator!")
        print("⏱️  The indicator will show:")
        print("   • Current songs being analyzed")
        print("   • Progress percentage")
        print("   • Elapsed time and ETA")
        print("   • Processing rate")
        
        # Simulate completing some analyses over time
        print("\n4. SIMULATING ANALYSIS COMPLETION")
        print("-" * 40)
        print("🔄 Starting simulation of analysis completion...")
        print("   (This will complete analyses every 10 seconds)")
        print("   (Press Ctrl+C to stop)")
        
        try:
            completed_count = 0
            while in_progress > 0 and completed_count < 5:
                time.sleep(10)  # Wait 10 seconds
                
                # Complete one analysis
                in_progress_analysis = db.session.query(AnalysisResult).filter_by(
                    status='in_progress'
                ).first()
                
                if in_progress_analysis:
                    # Complete the analysis with a random score
                    in_progress_analysis.status = 'completed'
                    in_progress_analysis.analyzed_at = datetime.utcnow()
                    in_progress_analysis.score = random.uniform(60, 95)  # Random score between 60-95
                    
                    # Get the song info
                    song = db.session.query(Song).get(in_progress_analysis.song_id)
                    
                    db.session.commit()
                    completed_count += 1
                    in_progress -= 1
                    
                    print(f"   ✅ Completed analysis for \"{song.title}\" by {song.artist} (Score: {in_progress_analysis.score:.1f})")
                    print(f"      Remaining in progress: {in_progress}")
                    
                    if in_progress == 0:
                        print("\n🎉 All simulated analyses completed!")
                        print("📊 The progress indicator should now be hidden")
                        break
                else:
                    break
                    
        except KeyboardInterrupt:
            print("\n\n⏹️  Simulation stopped by user")
            
        print("\n" + "=" * 50)
        print("✅ ANALYSIS PROGRESS SIMULATION COMPLETE")
        print("\nWhat you should have seen:")
        print("• Progress indicator appeared when analyses were in-progress")
        print("• Real-time updates every 3 seconds")
        print("• Current song being analyzed")
        print("• Progress percentage and ETA")
        print("• Indicator disappeared when all analyses completed")
        
        # Clean up any remaining in-progress analyses
        remaining = db.session.query(AnalysisResult).filter_by(status='in_progress').all()
        if remaining:
            print(f"\n🧹 Cleaning up {len(remaining)} remaining in-progress analyses...")
            for analysis in remaining:
                analysis.status = 'completed'
                analysis.analyzed_at = datetime.utcnow()
                analysis.score = random.uniform(70, 90)
            db.session.commit()
            print("✅ Cleanup complete")

if __name__ == "__main__":
    simulate_analysis_progress() 