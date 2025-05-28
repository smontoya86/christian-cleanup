#!/usr/bin/env python3
"""
Direct Bulk Re-analysis Script for Enhanced Song Analysis
Uses direct analysis calls instead of RQ tasks for reliable enhanced data population.

Usage: python scripts/bulk_reanalyze_direct.py [--batch-size=10] [--dry-run] [--force-all]
"""

import os
import sys
import time
import logging
import argparse
from datetime import datetime

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from app import create_app
from app.models.models import Song, AnalysisResult
from app.extensions import db
from app.services.unified_analysis_service import UnifiedAnalysisService  # Updated import
from app.utils.database import get_by_filter

def setup_logging():
    """Configure logging for the bulk re-analysis."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/bulk_reanalyze_direct.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

class DirectBulkReanalyzer:
    """Handles direct bulk re-analysis of songs for enhanced analysis fields."""
    
    def __init__(self, app, user_id=None):
        self.app = app
        self.user_id = user_id
        
    def get_songs_needing_enhancement(self, force_all=False):
        """Get all songs that need enhanced analysis data."""
        with self.app.app_context():
            if force_all:
                # Get all songs with analysis results regardless of enhanced fields
                query = db.session.query(Song).join(AnalysisResult).filter(
                    AnalysisResult.score.isnot(None)
                )
                logger.info("🔄 Force mode: Will re-analyze ALL analyzed songs")
            else:
                # Get only songs missing enhanced analysis fields
                query = db.session.query(Song).join(AnalysisResult).filter(
                    AnalysisResult.score.isnot(None),
                    AnalysisResult.purity_flags_details.is_(None)
                )
                logger.info("📊 Standard mode: Will re-analyze songs missing enhanced data")
                
            songs = query.all()
            logger.info(f"📋 Found {len(songs)} songs that need enhanced analysis")
            return songs
    
    def analyze_song_batch(self, songs_batch, batch_num, total_batches):
        """Analyze a batch of songs using direct implementation."""
        logger.info(f"🔄 Processing batch {batch_num}/{total_batches} ({len(songs_batch)} songs)")
        
        successful = 0
        failed = 0
        enhanced_populated = 0
        
        # Initialize the unified analysis service
        analysis_service = UnifiedAnalysisService()
        
        for song in songs_batch:
            try:
                with self.app.app_context():
                    logger.info(f"🎵 Analyzing: '{song.title}' by {song.artist} (ID: {song.id})")
                    
                    # Determine user ID
                    user_id = self.user_id
                    if user_id is None:
                        from app.models import User
                        user = User.query.first()
                        if not user:
                            logger.error("No users found in database")
                            continue
                        user_id = user.id
                        logger.warning(f"No user specified, using first available user: {user.display_name} (ID: {user_id})")
                    
                    # Use unified analysis service (direct implementation, no RQ)
                    result = analysis_service.execute_comprehensive_analysis(
                        song_id=song.id, 
                        user_id=user_id, 
                        force_reanalysis=True
                    )
                    
                    if result:
                        successful += 1
                        logger.info(f"✅ Analysis completed for song ID {song.id}")
                        
                        # Check if enhanced data was populated
                        db.session.refresh(song)  # Refresh to get latest data
                        analysis = get_by_filter(AnalysisResult, song_id=song.id)
                        
                        if analysis and analysis.purity_flags_details is not None:
                            enhanced_populated += 1
                            purity_count = len(analysis.purity_flags_details or [])
                            theme_count = len(analysis.positive_themes_identified or [])
                            biblical_count = len(analysis.biblical_themes or [])
                            scripture_count = len(analysis.supporting_scripture or {})
                            
                            logger.info(f"🎯 Enhanced data populated: {purity_count} flags, {theme_count} themes, {biblical_count} biblical, {scripture_count} scripture")
                        else:
                            logger.warning(f"⚠️  Enhanced data not populated for song ID {song.id}")
                    else:
                        failed += 1
                        logger.warning(f"❌ Analysis failed for song ID {song.id}")
                        
            except Exception as e:
                failed += 1
                logger.error(f"❌ Error analyzing song '{song.title}' (ID: {song.id}): {str(e)}")
                
        logger.info(f"📊 Batch {batch_num} complete: {successful} successful, {failed} failed, {enhanced_populated} enhanced")
        return successful, failed, enhanced_populated
    
    def run_bulk_reanalysis(self, batch_size=10, dry_run=False, force_all=False):
        """Run the direct bulk re-analysis process."""
        start_time = datetime.now()
        logger.info(f"🚀 Starting direct bulk re-analysis at {start_time}")
        
        if dry_run:
            logger.info("🧪 DRY RUN MODE - No actual analysis will be performed")
            
        # Get songs that need enhancement
        songs_to_analyze = self.get_songs_needing_enhancement(force_all)
        
        if not songs_to_analyze:
            logger.info("✅ No songs need enhanced analysis. All done!")
            return
            
        if dry_run:
            logger.info(f"🧪 DRY RUN: Would analyze {len(songs_to_analyze)} songs in batches of {batch_size}")
            for i, song in enumerate(songs_to_analyze[:10]):  # Show first 10
                logger.info(f"   {i+1}. '{song.title}' by {song.artist} (ID: {song.id})")
            if len(songs_to_analyze) > 10:
                logger.info(f"   ... and {len(songs_to_analyze) - 10} more songs")
            return
            
        # Process songs in batches
        total_successful = 0
        total_failed = 0
        total_enhanced = 0
        total_batches = (len(songs_to_analyze) + batch_size - 1) // batch_size
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(songs_to_analyze))
            batch = songs_to_analyze[start_idx:end_idx]
            
            batch_successful, batch_failed, batch_enhanced = self.analyze_song_batch(batch, batch_num + 1, total_batches)
            total_successful += batch_successful
            total_failed += batch_failed
            total_enhanced += batch_enhanced
            
            # Brief pause between batches to avoid overwhelming the system
            if batch_num < total_batches - 1:
                logger.info("⏸️  Pausing 5 seconds between batches...")
                time.sleep(5)
                
        # Final report
        end_time = datetime.now()
        duration = end_time - start_time
        
        logger.info("🎉 Direct bulk re-analysis completed!")
        logger.info(f"📊 Final Statistics:")
        logger.info(f"   • Total songs processed: {len(songs_to_analyze)}")
        logger.info(f"   • Successful analyses: {total_successful}")
        logger.info(f"   • Failed analyses: {total_failed}")
        logger.info(f"   • Enhanced data populated: {total_enhanced}")
        logger.info(f"   • Success rate: {(total_successful/len(songs_to_analyze)*100):.1f}%")
        logger.info(f"   • Enhancement rate: {(total_enhanced/len(songs_to_analyze)*100):.1f}%")
        logger.info(f"   • Total duration: {duration}")
        logger.info(f"   • Average per song: {duration.total_seconds()/len(songs_to_analyze):.1f} seconds")
        
        return total_successful, total_failed, total_enhanced

def get_user_by_identifier(identifier):
    """Get user by ID, Spotify ID, or display name"""
    from app.models import User
    
    try:
        # Try as integer ID first
        user_id = int(identifier)
        user = User.query.filter_by(id=user_id).first()
        if user:
            return user
    except ValueError:
        # Not an integer, try as Spotify ID
        user = User.query.filter_by(spotify_id=identifier).first()
        if user:
            return user
    
    # Try as display name
    user = User.query.filter_by(display_name=identifier).first()
    return user

def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(description='Direct bulk re-analyze songs for enhanced analysis data')
    parser.add_argument('--batch-size', type=int, default=10, help='Number of songs to process per batch (default: 10)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be analyzed without actually doing it')
    parser.add_argument('--force-all', action='store_true', help='Re-analyze ALL songs, not just those missing enhanced data')
    parser.add_argument('--user', type=str, help='User identifier (ID, Spotify ID, or display name)')
    
    args = parser.parse_args()
    
    # Create Flask app
    app = create_app('development')
    
    # Determine user ID
    user_id = None
    if args.user:
        with app.app_context():
            user = get_user_by_identifier(args.user)
            if user:
                user_id = user.id
                logger.info(f"Using user: {user.display_name} (ID: {user_id})")
            else:
                logger.error(f"❌ User not found with identifier: {args.user}")
                sys.exit(1)
    
    # Create direct bulk reanalyzer
    reanalyzer = DirectBulkReanalyzer(app, user_id)
    
    # Run the bulk re-analysis
    try:
        result = reanalyzer.run_bulk_reanalysis(
            batch_size=args.batch_size,
            dry_run=args.dry_run,
            force_all=args.force_all
        )
        
        if not args.dry_run and result:
            successful, failed, enhanced = result
            exit_code = 0 if failed == 0 else 1
            sys.exit(exit_code)
            
    except KeyboardInterrupt:
        logger.info("🛑 Direct bulk re-analysis interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 Direct bulk re-analysis failed: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main() 