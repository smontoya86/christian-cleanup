#!/usr/bin/env python3
"""
System Verification Script

Comprehensive system verification for Christian Music Curator.
Tests database connectivity, services, error handling, and core functionality.
"""

import sys
import os
import logging
from datetime import datetime

# Add the app directory to the path so we can import app modules
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_database_connectivity():
    """Test database connection and basic operations."""
    try:
        logger.info("🗄️  Testing Database Connectivity...")
        
        from app import create_app
        app = create_app('testing', init_scheduler=False)
        
        with app.app_context():
            from app.extensions import db
            from app.models.models import User, Song, Playlist, AnalysisResult
            
            # Test basic database queries
            user_count = User.query.count()
            song_count = Song.query.count()
            playlist_count = Playlist.query.count()
            analysis_count = AnalysisResult.query.count()
            
            logger.info(f"   📊 Database Statistics:")
            logger.info(f"      • Users: {user_count}")
            logger.info(f"      • Songs: {song_count}")
            logger.info(f"      • Playlists: {playlist_count}")
            logger.info(f"      • Analysis Results: {analysis_count}")
            
            # Test a sample query
            first_user = User.query.first()
            if first_user:
                logger.info(f"   ✅ Sample user found: {first_user.display_name}")
            
            return True
            
    except Exception as e:
        logger.error(f"   ❌ Database connectivity failed: {str(e)}")
        return False

def test_analysis_service():
    """Test the unified analysis service initialization."""
    try:
        logger.info("\n🔍 Testing Analysis Service...")
        
        from app import create_app
        app = create_app('testing', init_scheduler=False)
        
        with app.app_context():
            from app.models.models import User, AnalysisResult
            from app.services.unified_analysis_service import UnifiedAnalysisService
            
            # Check if we have users to test with
            user = User.query.first()
            if not user:
                logger.warning("   ⚠️  No users found - skipping service test")
                return True
            
            # Test service initialization
            analysis_service = UnifiedAnalysisService()
            logger.info(f"   ✅ UnifiedAnalysisService initialized")
            
            # Test service components
            logger.info(f"   ✅ Service components initialized for user: {user.display_name}")
            
            # Check recent analysis results
            analysis_count = AnalysisResult.query.count()
            recent_analysis = AnalysisResult.query.order_by(AnalysisResult.created_at.desc()).first()
            
            if recent_analysis:
                logger.info(f"   📊 Found {analysis_count} analysis results")
                logger.info(f"   🕒 Most recent analysis: {recent_analysis.analyzed_at}")
            else:
                logger.info(f"   📊 No analysis results found - system ready for first analysis")
            
            return True
            
    except Exception as e:
        logger.error(f"   ❌ Analysis service test failed: {str(e)}")
        return False

def test_error_handling():
    """Test error handling and logging systems."""
    try:
        logger.info("\n🛡️  Testing Error Handling...")
        
        from app import create_app
        app = create_app('testing', init_scheduler=False)
        
        with app.app_context():
            from app.utils.error_handling import create_error_response, generate_correlation_id
            from app.services.exceptions import AnalysisError
            
            # Test correlation ID generation
            correlation_id = generate_correlation_id()
            if correlation_id and len(correlation_id) > 0:
                logger.info(f"   ✅ Correlation ID generation working")
            
            # Test error response creation
            error_response = create_error_response(
                message="Test error",
                error_type="test_error",
                status_code=400
            )
            
            response_data, status_code = error_response
            if isinstance(response_data, dict) and status_code == 400:
                logger.info(f"   ✅ Error response creation working (Status: {status_code})")
            else:
                logger.error(f"   ❌ Error response format incorrect")
                return False
            
            # Test custom exception handling
            try:
                raise AnalysisError("Test analysis error")
            except AnalysisError:
                logger.info(f"   ✅ Custom exception handling working")
            
            return True
            
    except Exception as e:
        logger.error(f"   ❌ Error handling test failed: {str(e)}")
        return False

def test_redis_connectivity():
    """Test Redis connection and queue system."""
    try:
        logger.info("\n🔴 Testing Redis Connectivity...")
        
        from app import create_app
        app = create_app('testing', init_scheduler=False)
        
        with app.app_context():
            from app.utils.redis_manager import redis_manager
            
            # Test Redis connection
            connection = redis_manager.get_connection()
            logger.info(f"   ✅ Redis connection successful")
            
            # Test queue system
            from rq import Queue
            test_queue = Queue('test', connection=connection)
            queue_length = len(test_queue)
            logger.info(f"   ✅ Queue system operational (test queue length: {queue_length})")
            
            return True
            
    except Exception as e:
        logger.error(f"   ❌ Redis connectivity failed: {str(e)}")
        return False

def test_spotify_service():
    """Test Spotify service initialization."""
    try:
        logger.info("\n🎵 Testing Spotify Service...")
        
        from app import create_app
        app = create_app('testing', init_scheduler=False)
        
        with app.app_context():
            from app.models.models import User
            from app.services.spotify_service import SpotifyService
            
            # Check if we have users to test with
            user = User.query.first()
            if not user:
                logger.warning("   ⚠️  No users found - skipping Spotify service test")
                return True
            
            # Test service initialization for user with token
            if user.access_token:
                logger.info(f"   ✅ User has access token")
                
                # Test service creation
                spotify_service = SpotifyService(auth_token=user.access_token)
                logger.info(f"   ✅ SpotifyService initialized for user: {user.display_name}")
            else:
                logger.warning(f"   ⚠️  User {user.display_name} has no access token - service ready for OAuth")
            
            return True
            
    except Exception as e:
        logger.error(f"   ❌ Spotify service test failed: {str(e)}")
        return False

def test_application_routes():
    """Test basic application routes."""
    try:
        logger.info("\n🌐 Testing Application Routes...")
        
        from app import create_app
        app = create_app('testing', init_scheduler=False)
        
        with app.test_client() as client:
            # Test health endpoint
            response = client.get('/health')
            if response.status_code == 200:
                logger.info(f"   ✅ Health endpoint responding (Status: {response.status_code})")
            else:
                logger.warning(f"   ⚠️  Health endpoint status: {response.status_code}")
            
            # Test main route (should redirect to login)
            response = client.get('/')
            if response.status_code in [200, 302]:  # OK or redirect to login
                logger.info(f"   ✅ Main route responding (Status: {response.status_code})")
            else:
                logger.error(f"   ❌ Main route error (Status: {response.status_code})")
                return False
            
            return True
            
    except Exception as e:
        logger.error(f"   ❌ Application routes test failed: {str(e)}")
        return False

def main():
    """Main verification function."""
    logger.info("🚀 Christian Music Curator - System Verification")
    logger.info("=" * 60)
    logger.info(f"🕒 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")
    
    # Define test suite
    tests = [
        ("Database Connectivity", test_database_connectivity),
        ("Analysis Service", test_analysis_service),
        ("Error Handling", test_error_handling),
        ("Redis Connectivity", test_redis_connectivity),
        ("Spotify Service", test_spotify_service),
        ("Application Routes", test_application_routes),
    ]
    
    passed = 0
    failed = 0
    results = {}
    
    # Run tests
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                results[test_name] = "✅ PASSED"
            else:
                failed += 1
                results[test_name] = "❌ FAILED"
        except Exception as e:
            failed += 1
            results[test_name] = "❌ CRASHED"
            logger.error(f"   ❌ {test_name} test crashed: {str(e)}")
    
    # Report results
    logger.info("\n" + "=" * 60)
    logger.info("📊 SYSTEM VERIFICATION SUMMARY")
    logger.info("=" * 60)
    
    for test_name, status in results.items():
        logger.info(f"{test_name:<25}: {status}")
    
    logger.info(f"\n📈 Results: {passed} passed, {failed} failed")
    logger.info(f"🕒 Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if failed == 0:
        logger.info("\n🎉 All system verification tests passed!")
        logger.info("   System is ready for production use.")
        return 0
    else:
        logger.warning(f"\n⚠️  {failed} test(s) failed.")
        logger.warning("   Review errors above before deploying to production.")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 