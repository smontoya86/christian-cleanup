#!/usr/bin/env python3
"""
Cleanup Degraded Analyses Script

This script finds and re-analyzes songs that have degraded analyses
(fallback responses from API failures). Run this periodically to ensure
all songs have proper biblical analyses.

Usage:
    python scripts/utilities/cleanup_degraded_analyses.py
    
Or via Docker:
    docker-compose exec web python scripts/utilities/cleanup_degraded_analyses.py
"""

import sys
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app import create_app, db
from app.models import AnalysisResult, Song
from app.services.unified_analysis_service import UnifiedAnalysisService
from sqlalchemy import or_

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def find_degraded_analyses():
    """Find all songs with degraded analyses"""
    return db.session.query(AnalysisResult, Song).join(
        Song, AnalysisResult.song_id == Song.id
    ).filter(
        or_(
            AnalysisResult.explanation.like('%temporarily unavailable%'),
            AnalysisResult.explanation.like('%service error%'),
            AnalysisResult.explanation.like('%manual review%'),
            AnalysisResult.explanation.like('%Service protection engaged%'),
            AnalysisResult.explanation.like('%Maximum retry attempts exceeded%')
        )
    ).all()


def cleanup_degraded_analyses(dry_run=False):
    """
    Find and re-analyze songs with degraded analyses
    
    Args:
        dry_run: If True, only report what would be done without making changes
    """
    app = create_app()
    
    with app.app_context():
        logger.info("🔍 Scanning for degraded analyses...")
        
        degraded = find_degraded_analyses()
        
        if not degraded:
            logger.info("✅ No degraded analyses found! All songs have proper analyses.")
            return
        
        logger.info(f"⚠️  Found {len(degraded)} songs with degraded analyses:\n")
        
        for analysis, song in degraded:
            logger.info(f"  - Song ID {song.id}: '{song.title}' by {song.artist}")
            logger.info(f"    Score: {analysis.score}, Created: {analysis.created_at}")
            logger.info(f"    Reason: {analysis.explanation[:80]}...\n")
        
        if dry_run:
            logger.info("🔍 DRY RUN: No changes made. Run without --dry-run to fix.")
            return
        
        # Confirm before proceeding
        response = input(f"\n🔧 Re-analyze {len(degraded)} songs? (yes/no): ").strip().lower()
        if response != 'yes':
            logger.info("❌ Cancelled by user")
            return
        
        # Re-analyze each song
        service = UnifiedAnalysisService()
        success_count = 0
        failed_count = 0
        
        for analysis, song in degraded:
            try:
                logger.info(f"\n🎵 Re-analyzing '{song.title}' by {song.artist}...")
                
                # Delete old degraded analysis
                AnalysisResult.query.filter_by(song_id=song.id).delete()
                db.session.commit()
                
                # Re-analyze
                service.analyze_song(song.id, user_id=None)
                
                # Verify new analysis
                new_analysis = AnalysisResult.query.filter_by(song_id=song.id).first()
                if new_analysis and 'temporarily unavailable' not in new_analysis.explanation:
                    logger.info(f"   ✅ Success! New score: {new_analysis.score}, Verdict: {new_analysis.verdict}")
                    success_count += 1
                else:
                    logger.warning(f"   ⚠️  Re-analysis returned another degraded response")
                    failed_count += 1
                    
            except Exception as e:
                logger.error(f"   ❌ Failed: {e}")
                failed_count += 1
                db.session.rollback()
        
        logger.info(f"\n🎉 Cleanup complete!")
        logger.info(f"   ✅ Successfully re-analyzed: {success_count}")
        logger.info(f"   ❌ Failed: {failed_count}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Cleanup degraded song analyses')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Report what would be done without making changes')
    
    args = parser.parse_args()
    
    cleanup_degraded_analyses(dry_run=args.dry_run)

