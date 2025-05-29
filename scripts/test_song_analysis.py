#!/usr/bin/env python3
"""
Test script to verify song analysis functionality.
Updated to use UnifiedAnalysisService instead of deprecated analysis_service.
"""
import os
import sys
import logging
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_song_analysis():
    """Test song analysis functionality using UnifiedAnalysisService."""
    try:
        from app import create_app
        from app.extensions import db
        from app.models import Song, AnalysisResult
        from app.services.unified_analysis_service import execute_comprehensive_analysis_task  # Updated import
        
        # Create Flask app and push app context
        app = create_app()
        with app.app_context():
            # Create test song
            test_song = Song(
                spotify_id=f"test_song_{int(datetime.utcnow().timestamp())}",
                title="Amazing Grace",
                artist="John Newton",
                album="Hymns",
                explicit=False,
                album_art_url="https://example.com/amazing_grace.jpg"
            )
            
            db.session.add(test_song)
            db.session.flush()  # Get the ID without committing
            
            logger.info(f"Created test song: {test_song.title} by {test_song.artist} (ID: {test_song.id})")
            
            # Trigger analysis using unified analysis service
            logger.info("Triggering song analysis using UnifiedAnalysisService...")
            job = execute_comprehensive_analysis_task(test_song.id, user_id=1)  # Updated function call
            
            if not job:
                logger.error("Failed to enqueue analysis job")
                return False
                
            logger.info(f"Analysis job enqueued with ID: {job.id}")
            logger.info("Check the RQ worker logs for analysis progress...")
            
            # Commit the song to the database
            db.session.commit()
            
            return True
            
    except Exception as e:
        logger.exception(f"Error testing song analysis: {e}")
        return False

if __name__ == "__main__":
    print("Testing song analysis functionality with UnifiedAnalysisService...\n")
    
    success = test_song_analysis()
    
    if success:
        print("\n✅ Song analysis test started successfully!")
        print("Check the RQ worker logs for analysis progress.")
        sys.exit(0)
    else:
        print("\n❌ Song analysis test failed!")
        print("Check the error messages above for details.")
        sys.exit(1)
