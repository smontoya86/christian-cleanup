#!/usr/bin/env python3
"""
Test script to check if the worker can import and execute the admin_reanalyze_all_user_songs function.
This will test the exact import path and execution that RQ workers use.
"""

import os
import sys
import logging
import argparse
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_worker_import():
    """Test importing the function the way RQ workers do"""
    logger.info("🔍 Testing worker import path...")
    
    try:
        # Test the exact import path that RQ uses
        logger.info("Testing import: app.main.routes.admin_reanalyze_all_user_songs")
        
        # This is the same way RQ imports functions
        from app.main.routes import admin_reanalyze_all_user_songs
        
        logger.info("✅ Successfully imported admin_reanalyze_all_user_songs")
        logger.info(f"Function object: {admin_reanalyze_all_user_songs}")
        logger.info(f"Function module: {admin_reanalyze_all_user_songs.__module__}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Import failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def get_user_by_identifier(identifier):
    """Get user by ID, Spotify ID, or display name"""
    try:
        from run import create_app
        app = create_app()
        
        with app.app_context():
            from app.models import User
            from app.extensions import db
            
            try:
                # Try as integer ID first
                user_id = int(identifier)
                user = db.session.query(User).filter_by(id=user_id).first()
                if user:
                    return user
            except ValueError:
                # Not an integer, try as Spotify ID
                user = db.session.query(User).filter_by(spotify_id=identifier).first()
                if user:
                    return user
            
            # Try as display name
            user = db.session.query(User).filter_by(display_name=identifier).first()
            return user
            
    except Exception as e:
        logger.error(f"Error looking up user: {e}")
        return None

def test_rq_job_creation(user_id=None):
    """Test creating an RQ job with the exact same parameters"""
    logger.info("🔍 Testing RQ job creation...")
    
    try:
        # Initialize Flask app
        from run import create_app
        app = create_app()
        
        with app.app_context():
            from app.extensions import rq
            from app.models import User
            
            # Determine user ID to use
            if user_id is None:
                # Use first available user as fallback
                user = User.query.first()
                if not user:
                    logger.error("No users found in database")
                    return None
                user_id = user.id
                logger.warning(f"No user specified, using first available user: {user.display_name} (ID: {user_id})")
            else:
                user = User.query.get(user_id)
                if not user:
                    logger.error(f"User ID {user_id} not found")
                    return None
                logger.info(f"Using specified user: {user.display_name} (ID: {user_id})")
            
            logger.info("✅ Flask app and RQ initialized")
            
            # Get the default queue using Flask-RQ2's get_queue() method
            queue = rq.get_queue()
            logger.info(f"✅ Got queue: {queue.name}")
            
            # Test creating a job with the exact same parameters as the admin route
            logger.info("Creating job with string import path...")
            
            job = queue.enqueue(
                'app.main.routes.admin_reanalyze_all_user_songs',
                user_id=user_id,  # Use the determined user_id
                job_timeout='2h',  # Same as in the admin route
                job_id=f'reanalyze_all_user_{user_id}_{int(datetime.now().timestamp())}'
            )
            
            logger.info(f"✅ Job created successfully!")
            logger.info(f"Job ID: {job.id}")
            logger.info(f"Job status: {job.get_status()}")
            logger.info(f"Job function: {job.func_name}")
            logger.info(f"Job args: {job.args}")
            logger.info(f"Job kwargs: {job.kwargs}")
            
            return job
            
    except Exception as e:
        logger.error(f"❌ RQ job creation failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return None

def test_job_execution(user_id=None):
    """Test if a worker can actually process the job"""
    logger.info("🔍 Testing job execution by worker...")
    
    try:
        # Create a job first
        job = test_rq_job_creation(user_id)
        if not job:
            logger.error("❌ Could not create job for testing")
            return False
            
        logger.info(f"⏳ Waiting for worker to process job {job.id}...")
        
        # Wait a bit for the worker to pick up the job
        import time
        time.sleep(5)
        
        # Check job status
        status = job.get_status()
        logger.info(f"Job status after 5 seconds: {status}")
        
        if status == 'finished':
            logger.info("✅ Job completed successfully!")
            result = job.result
            logger.info(f"Job result: {result}")
            return True
        elif status == 'failed':
            logger.error("❌ Job failed!")
            logger.error(f"Job exception: {job.exc_info}")
            return False
        else:
            logger.info(f"⏳ Job still {status}, waiting longer...")
            time.sleep(10)
            
            final_status = job.get_status()
            logger.info(f"Final job status: {final_status}")
            
            if final_status == 'finished':
                logger.info("✅ Job completed after extended wait!")
                return True
            else:
                logger.warning(f"⚠️ Job did not complete, final status: {final_status}")
                if final_status == 'failed':
                    logger.error(f"Job exception: {job.exc_info}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Job execution test failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test worker import and execution")
    parser.add_argument("--user", type=str, help="User identifier (ID, Spotify ID, or display name)")
    args = parser.parse_args()
    
    # Determine user ID
    user_id = None
    if args.user:
        user = get_user_by_identifier(args.user)
        if user:
            user_id = user.id
            logger.info(f"Using user: {user.display_name} (ID: {user_id})")
        else:
            logger.error(f"User not found: {args.user}")
            sys.exit(1)
    
    print("=" * 60)
    print("🔍 WORKER IMPORT AND EXECUTION TEST")
    print("=" * 60)
    
    # Test 1: Import
    print("\n🧪 TEST 1: Function Import")
    print("-" * 30)
    import_success = test_worker_import()
    
    if not import_success:
        print("\n🚨 CRITICAL: Function import failed - RQ workers can't import the function")
        sys.exit(1)
    
    # Test 2: Job Creation
    print("\n🧪 TEST 2: RQ Job Creation")
    print("-" * 30)
    job = test_rq_job_creation(user_id)
    
    if not job:
        print("\n🚨 CRITICAL: Job creation failed")
        sys.exit(1)
    
    # Test 3: Job Execution
    print("\n🧪 TEST 3: Job Execution by Worker")
    print("-" * 35)
    execution_success = test_job_execution(user_id)
    
    # Summary
    print("\n📊 TEST SUMMARY")
    print("=" * 60)
    print(f"Function Import: {'✅ PASS' if import_success else '❌ FAIL'}")
    print(f"Job Creation: {'✅ PASS' if job else '❌ FAIL'}")
    print(f"Job Execution: {'✅ PASS' if execution_success else '❌ FAIL'}")
    
    if not execution_success:
        print("\n⚠️  JOB EXECUTION FAILING - This is likely the root cause")
        sys.exit(1)
    else:
        print("\n✅ ALL TESTS PASSED - Re-analysis should work")
        sys.exit(0) 