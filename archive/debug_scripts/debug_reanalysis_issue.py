#!/usr/bin/env python3
"""
Comprehensive diagnostic script for the re-analysis issue.
This will test the admin_reanalyze_all_user_songs function directly and identify the exact problem.
"""

import os
import sys
import time
import logging
from datetime import datetime

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_redis_connectivity():
    """Test Redis connectivity for both local and Docker configurations"""
    logger.info("🔍 Testing Redis connectivity...")
    
    try:
        import redis
        
        # Test local Redis
        try:
            r_local = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            r_local.ping()
            logger.info("✅ Local Redis (localhost:6379) is accessible")
            
            # Check queue status
            queue_info = r_local.info('memory')
            logger.info(f"   Local Redis memory usage: {queue_info.get('used_memory_human', 'unknown')}")
            
        except Exception as e:
            logger.warning(f"⚠️  Local Redis (localhost:6379) not accessible: {e}")
        
        # Test Docker Redis (if in Docker environment)
        try:
            r_docker = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)
            r_docker.ping()
            logger.info("✅ Docker Redis (redis:6379) is accessible")
            
            # Check queue status
            queue_info = r_docker.info('memory')
            logger.info(f"   Docker Redis memory usage: {queue_info.get('used_memory_human', 'unknown')}")
            
        except Exception as e:
            logger.warning(f"⚠️  Docker Redis (redis:6379) not accessible: {e}")
        
        return True
        
    except ImportError:
        logger.error("❌ Redis package not installed")
        return False
    except Exception as e:
        logger.error(f"❌ Redis connectivity test failed: {e}")
        return False

def test_rq_worker_connectivity():
    """Test RQ worker connectivity and job queuing"""
    logger.info("🔍 Testing RQ worker connectivity...")
    
    try:
        from run import create_app
        app = create_app()
        
        with app.app_context():
            from app.extensions import rq
            
            # Check available queues
            queue_names = ['high', 'default', 'low']
            for queue_name in queue_names:
                try:
                    queue = rq.get_queue(queue_name)
                    queue_length = len(queue)
                    logger.info(f"✅ Queue '{queue_name}' accessible with {queue_length} jobs")
                except Exception as e:
                    logger.warning(f"⚠️  Queue '{queue_name}' not accessible: {e}")
            
            # Test simple job enqueue
            try:
                test_queue = rq.get_queue('default')
                job = test_queue.enqueue('time.sleep', 0.1, job_timeout=10)
                logger.info(f"✅ Test job enqueued successfully: {job.id}")
                return True
            except Exception as e:
                logger.error(f"❌ Failed to enqueue test job: {e}")
                return False
                
    except Exception as e:
        logger.error(f"❌ RQ worker connectivity test failed: {e}")
        return False

def test_database_connection():
    """Test the database connection and show which database we're connecting to"""
    logger.info("🔍 Testing database connection...")
    
    try:
        from run import create_app
        app = create_app()
        
        with app.app_context():
            from app.models import User, Song, Playlist, PlaylistSong
            from app import db
            
            # Log which database we're connecting to
            db_url = app.config.get('SQLALCHEMY_DATABASE_URI', 'NOT SET')
            logger.info(f"📊 Database URL: {db_url}")
            
            # Test basic connection
            user_count = User.query.count()
            song_count = Song.query.count()
            playlist_count = Playlist.query.count()
            
            logger.info(f"✅ Database connection working:")
            logger.info(f"   Users: {user_count}")
            logger.info(f"   Songs: {song_count}")
            logger.info(f"   Playlists: {playlist_count}")
            
            # List all users with more details
            users = User.query.all()
            for user in users:
                logger.info(f"   User {user.id}: {user.email} ({user.display_name})")
                
            return True, users[0].id if users else None
            
    except Exception as e:
        logger.error(f"❌ Database connection test failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False, None

def test_songs_query(user_id):
    """Test the actual songs query used in the re-analysis function"""
    logger.info(f"🔍 Testing the actual songs query for user {user_id}...")
    
    try:
        from run import create_app
        app = create_app()
        
        with app.app_context():
            from app.models import User, Song, Playlist, PlaylistSong
            from app import db
            
            user = db.session.get(User, user_id)
            if not user:
                logger.error(f"❌ User with ID {user_id} not found!")
                return False
                
            logger.info(f"✅ Found user: {user.email}")
            
            # Use the EXACT same query as the re-analysis function
            songs_query = db.session.query(Song).join(
                PlaylistSong, Song.id == PlaylistSong.song_id
            ).join(
                Playlist, PlaylistSong.playlist_id == Playlist.id
            ).filter(Playlist.owner_id == user_id).distinct()
            
            all_songs = songs_query.all()
            song_count = len(all_songs)
            
            logger.info(f"✅ Found {song_count} songs for user {user.email}")
            
            if song_count == 0:
                logger.error("❌ User has no songs to analyze!")
                return False
            else:
                logger.info(f"✅ Songs found: {[f'{s.title} by {s.artist}' for s in all_songs[:3]]}...")
                return True
                
    except Exception as e:
        logger.error(f"❌ Songs query test failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def test_analysis_service(user_id):
    """Test the analysis service directly"""
    logger.info(f"🔍 Testing unified analysis service for user {user_id}...")
    
    try:
        from run import create_app
        app = create_app()
        
        with app.app_context():
            from app.services.unified_analysis_service import UnifiedAnalysisService
            from app.models import Song, Playlist, PlaylistSong
            from app import db
            
            # Get songs for the correct user using the correct query
            songs_query = db.session.query(Song).join(
                PlaylistSong, Song.id == PlaylistSong.song_id
            ).join(
                Playlist, PlaylistSong.playlist_id == Playlist.id
            ).filter(Playlist.owner_id == user_id).distinct()
            
            song = songs_query.first()
            if not song:
                logger.error(f"❌ No songs found for user {user_id}")
                return False
                
            logger.info(f"🎵 Testing with song: '{song.title}' by {song.artist}")
            
            # Initialize unified analysis service
            analysis_service = UnifiedAnalysisService()
            
            start_time = time.time()
            result = analysis_service.execute_comprehensive_analysis(
                song_id=song.id, 
                user_id=user_id, 
                force_reanalysis=True
            )
            elapsed = time.time() - start_time
            
            logger.info(f"✅ Single song analysis completed in {elapsed:.2f} seconds")
            logger.info(f"Result: {result}")
            return True
            
    except Exception as e:
        logger.error(f"❌ Analysis service test failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

def test_reanalysis_function(user_id):
    """Test the admin_reanalyze_all_user_songs function directly"""
    logger.info(f"🔍 Starting comprehensive diagnostic test for user {user_id}...")
    
    try:
        # Initialize Flask app
        from run import create_app
        app = create_app()
        
        with app.app_context():
            logger.info("✅ Flask app context created successfully")
            
            # Import the function
            from app.main.routes import admin_reanalyze_all_user_songs
            logger.info("✅ Successfully imported admin_reanalyze_all_user_songs")
            
            # Test database connection
            from app.models import User, Song
            from app import db
            
            user_count = User.query.count()
            song_count = Song.query.count()
            logger.info(f"✅ Database connection working: {user_count} users, {song_count} songs")
            
            # Check for user with the correct ID
            user = db.session.get(User, user_id)
            if not user:
                logger.error(f"❌ User with ID {user_id} not found!")
                return False
                
            logger.info(f"✅ Found user: {user.email}")
            
            # Now test the function directly
            logger.info("🔄 Starting direct function call...")
            start_time = time.time()
            
            try:
                result = admin_reanalyze_all_user_songs(user_id=user_id)
                elapsed = time.time() - start_time
                
                logger.info(f"✅ Function completed in {elapsed:.2f} seconds")
                logger.info(f"Result: {result}")
                
                if elapsed < 5:
                    logger.warning("⚠️ Function completed suspiciously quickly - likely failed early")
                    return False
                else:
                    logger.info("✅ Function took reasonable time - likely successful")
                    return True
                    
            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(f"❌ Function failed after {elapsed:.2f} seconds: {e}")
                logger.error(f"Exception type: {type(e)}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                return False
                
    except Exception as e:
        logger.error(f"❌ Setup failed: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🔍 COMPREHENSIVE RE-ANALYSIS DIAGNOSTIC TEST")
    print("=" * 60)
    
    # Test 0: Redis Connectivity
    print("\n🧪 TEST 0: Redis Connectivity")
    print("-" * 40)
    redis_success = test_redis_connectivity()
    
    # Test 0.5: RQ Worker Connectivity
    print("\n🧪 TEST 0.5: RQ Worker Connectivity")
    print("-" * 40)
    rq_success = test_rq_worker_connectivity()
    
    # Test 1: Database Connection
    print("\n🧪 TEST 1: Database Connection")
    print("-" * 40)
    db_success, user_id = test_database_connection()
    
    if not db_success:
        print("\n🚨 CRITICAL: Database connection failed - cannot proceed")
        sys.exit(1)
    
    if not user_id:
        print("\n🚨 CRITICAL: No users found in database - cannot proceed")
        sys.exit(1)
    
    # Test 2: Songs Query
    print(f"\n🧪 TEST 2: Songs Query for User {user_id}")
    print("-" * 50)
    songs_success = test_songs_query(user_id)
    
    # Test 3: Analysis Service
    print(f"\n🧪 TEST 3: Analysis Service for User {user_id}")
    print("-" * 30)
    analysis_success = test_analysis_service(user_id)
    
    # Test 4: Re-analysis Function
    print(f"\n🧪 TEST 4: Re-analysis Function for User {user_id}")
    print("-" * 30)
    reanalysis_success = test_reanalysis_function(user_id)
    
    # Summary
    print("\n📊 DIAGNOSTIC SUMMARY")
    print("=" * 60)
    print(f"Redis Connectivity Test: {'✅ PASS' if redis_success else '❌ FAIL'}")
    print(f"RQ Worker Test: {'✅ PASS' if rq_success else '❌ FAIL'}")
    print(f"Database Connection Test: {'✅ PASS' if db_success else '❌ FAIL'}")
    print(f"Songs Query Test: {'✅ PASS' if songs_success else '❌ FAIL'}")
    print(f"Analysis Service Test: {'✅ PASS' if analysis_success else '❌ FAIL'}")
    print(f"Re-analysis Function Test: {'✅ PASS' if reanalysis_success else '❌ FAIL'}")
    
    if not redis_success:
        print("\n🚨 CRITICAL: Redis connectivity is failing - workers won't work")
        sys.exit(1)
    elif not rq_success:
        print("\n🚨 CRITICAL: RQ workers are not accessible - job queuing won't work")
        sys.exit(1)
    elif not songs_success:
        print("\n🚨 CRITICAL: Songs query is failing - no songs found for user")
        sys.exit(1)
    elif not analysis_success:
        print("\n⚠️  ANALYSIS SERVICE FAILING - Analysis engine has issues")
        sys.exit(1)
    elif not reanalysis_success:
        print("\n⚠️  RE-ANALYSIS FUNCTION FAILING - This is the root cause")
        sys.exit(1)
    else:
        print("\n✅ ALL TESTS PASSED - System appears healthy")
        sys.exit(0) 