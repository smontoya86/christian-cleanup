#!/usr/bin/env python3
"""Quick test to verify core functionality."""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app
from app.models.models import User, Song, AnalysisResult
from app.services.unified_analysis_service import UnifiedAnalysisService
from scripts.utils.script_logging import (
    get_script_logger, 
    log_operation_start, 
    log_operation_success,
    log_milestone
)

def main():
    # Set up logging for this script
    logger = get_script_logger('quick_test')
    
    log_operation_start(logger, "Quick system test", test_type="core_functionality")
    
    try:
        app = create_app()
        with app.app_context():
            
            # Database connectivity test
            log_milestone(logger, "Testing database connectivity")
            user_count = User.query.count()
            song_count = Song.query.count()
            analysis_count = AnalysisResult.query.count()
            
            logger.info("Database connectivity verified", extra={
                'extra_fields': {
                    'test': 'database_connectivity',
                    'users': user_count,
                    'songs': song_count,
                    'analyses': analysis_count,
                    'status': 'success'
                }
            })
            
            # UnifiedAnalysisService test
            log_milestone(logger, "Testing UnifiedAnalysisService initialization")
            service = UnifiedAnalysisService()
            
            logger.info("UnifiedAnalysisService initialized successfully", extra={
                'extra_fields': {
                    'test': 'analysis_service',
                    'service_type': type(service).__name__,
                    'status': 'success'
                }
            })
            
            # User data test
            if user_count > 0:
                user = User.query.first()
                logger.info("User data verification", extra={
                    'extra_fields': {
                        'test': 'user_data',
                        'first_user_id': user.id,
                        'first_user_name': user.display_name,
                        'status': 'success'
                    }
                })
            else:
                logger.warning("No users found in database", extra={
                    'extra_fields': {
                        'test': 'user_data',
                        'status': 'no_data'
                    }
                })
            
            log_operation_success(
                logger, 
                "Quick system test", 
                user_count=user_count,
                song_count=song_count,
                analysis_count=analysis_count
            )
            
    except Exception as e:
        from scripts.utils.script_logging import log_operation_error
        log_operation_error(logger, "Quick system test", e)
        raise

if __name__ == "__main__":
    main() 