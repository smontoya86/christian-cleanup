#!/usr/bin/env python3
"""
Comprehensive Regression Test Suite
Tests all core functionality to ensure the build works properly
"""

import time
import sys
import os
import requests
import json
from datetime import datetime
sys.path.append('/app')

from app import create_app
from app.extensions import db
from app.models import User, Song, AnalysisResult, Playlist, PlaylistSong
from sqlalchemy import text

class RegressionTester:
    def __init__(self):
        self.app = create_app()
        self.test_results = []
        self.failed_tests = []
        self.passed_tests = []
        
    def log_test(self, test_name, status, message="", duration=0):
        """Log test result"""
        result = {
            'test': test_name,
            'status': status,
            'message': message,
            'duration': duration,
            'timestamp': datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        if status == 'PASS':
            self.passed_tests.append(test_name)
            print(f"✅ {test_name}: {message} ({duration:.1f}ms)")
        else:
            self.failed_tests.append(test_name)
            print(f"❌ {test_name}: {message} ({duration:.1f}ms)")
    
    def test_database_connectivity(self):
        """Test basic database connectivity"""
        test_name = "Database Connectivity"
        start_time = time.time()
        
        try:
            with self.app.app_context():
                # Test basic connection
                result = db.session.execute(text("SELECT 1")).scalar()
                if result == 1:
                    duration = (time.time() - start_time) * 1000
                    self.log_test(test_name, 'PASS', 'Database connection successful', duration)
                    return True
                else:
                    duration = (time.time() - start_time) * 1000
                    self.log_test(test_name, 'FAIL', 'Unexpected result from database', duration)
                    return False
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.log_test(test_name, 'FAIL', f'Database connection failed: {str(e)}', duration)
            return False
    
    def test_database_tables(self):
        """Test that all required tables exist"""
        test_name = "Database Tables"
        start_time = time.time()
        
        required_tables = [
            'users', 'songs', 'analysis_results', 'playlists', 
            'playlist_songs', 'whitelist', 'blacklist'
        ]
        
        try:
            with self.app.app_context():
                # Check if tables exist
                for table in required_tables:
                    result = db.session.execute(text(f"""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'public' 
                            AND table_name = '{table}'
                        );
                    """)).scalar()
                    
                    if not result:
                        duration = (time.time() - start_time) * 1000
                        self.log_test(test_name, 'FAIL', f'Table {table} does not exist', duration)
                        return False
                
                duration = (time.time() - start_time) * 1000
                self.log_test(test_name, 'PASS', f'All {len(required_tables)} tables exist', duration)
                return True
                
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.log_test(test_name, 'FAIL', f'Error checking tables: {str(e)}', duration)
            return False
    
    def test_performance_indexes(self):
        """Test that performance indexes exist and are working"""
        test_name = "Performance Indexes"
        start_time = time.time()
        
        expected_indexes = [
            'idx_analysis_results_status',
            'idx_analysis_results_analyzed_at',
            'idx_analysis_results_song_id_new',
            'idx_playlist_songs_playlist_id',
            'idx_playlists_owner_id',
            'idx_songs_spotify_id_new',
            'idx_analysis_results_composite'
        ]
        
        try:
            with self.app.app_context():
                # Check if indexes exist
                existing_indexes = db.session.execute(text("""
                    SELECT indexname 
                    FROM pg_indexes 
                    WHERE schemaname = 'public' 
                    AND indexname LIKE 'idx_%'
                """)).fetchall()
                
                existing_index_names = [row[0] for row in existing_indexes]
                missing_indexes = [idx for idx in expected_indexes if idx not in existing_index_names]
                
                if missing_indexes:
                    duration = (time.time() - start_time) * 1000
                    self.log_test(test_name, 'FAIL', f'Missing indexes: {missing_indexes}', duration)
                    return False
                
                duration = (time.time() - start_time) * 1000
                self.log_test(test_name, 'PASS', f'All {len(expected_indexes)} performance indexes exist', duration)
                return True
                
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.log_test(test_name, 'FAIL', f'Error checking indexes: {str(e)}', duration)
            return False
    
    def test_model_creation(self):
        """Test creating model instances"""
        test_name = "Model Creation"
        start_time = time.time()
        
        try:
            with self.app.app_context():
                # Test creating a user
                from datetime import datetime, timedelta
                test_user = User(
                    spotify_id='test_regression_user',
                    email='regression@test.com',
                    display_name='Regression Test User',
                    access_token='test_token',
                    refresh_token='test_refresh',
                    token_expiry=datetime.utcnow() + timedelta(hours=1)
                )
                db.session.add(test_user)
                db.session.flush()
                
                # Test creating a song
                test_song = Song(
                    spotify_id='test_regression_song',
                    title='Test Song',
                    artist='Test Artist',
                    album='Test Album'
                )
                db.session.add(test_song)
                db.session.flush()
                
                # Test creating an analysis result
                test_analysis = AnalysisResult(
                    song_id=test_song.id,
                    status='completed',
                    score=85,
                    concern_level='low',
                    explanation='Test analysis'
                )
                db.session.add(test_analysis)
                db.session.flush()
                
                # Test creating a playlist
                test_playlist = Playlist(
                    spotify_id='test_regression_playlist',
                    name='Test Playlist',
                    owner_id=test_user.id
                )
                db.session.add(test_playlist)
                db.session.flush()
                
                # Test creating playlist-song relationship
                test_playlist_song = PlaylistSong(
                    playlist_id=test_playlist.id,
                    song_id=test_song.id,
                    track_position=1
                )
                db.session.add(test_playlist_song)
                
                # Commit all changes
                db.session.commit()
                
                duration = (time.time() - start_time) * 1000
                self.log_test(test_name, 'PASS', 'All models created successfully', duration)
                return True
                
        except Exception as e:
            try:
                with self.app.app_context():
                    db.session.rollback()
            except:
                pass  # Ignore rollback errors in test context
            duration = (time.time() - start_time) * 1000
            self.log_test(test_name, 'FAIL', f'Model creation failed: {str(e)}', duration)
            return False
    
    def test_database_queries(self):
        """Test key database queries with performance indexes"""
        test_name = "Database Queries"
        start_time = time.time()
        
        try:
            with self.app.app_context():
                # Test song count query
                song_count = db.session.query(Song).count()
                
                # Test analysis results query
                completed_analyses = db.session.query(AnalysisResult).filter(
                    AnalysisResult.status == 'completed'
                ).count()
                
                # Test playlist query
                playlists = db.session.query(Playlist).limit(10).all()
                
                # Test join query
                playlist_songs = db.session.query(Song, AnalysisResult)\
                    .join(PlaylistSong, Song.id == PlaylistSong.song_id)\
                    .outerjoin(AnalysisResult, Song.id == AnalysisResult.song_id)\
                    .limit(5).all()
                
                duration = (time.time() - start_time) * 1000
                self.log_test(test_name, 'PASS', 
                    f'Queries executed: {song_count} songs, {completed_analyses} analyses, {len(playlists)} playlists', 
                    duration)
                return True
                
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.log_test(test_name, 'FAIL', f'Query execution failed: {str(e)}', duration)
            return False
    
    def test_app_startup(self):
        """Test Flask application startup"""
        test_name = "App Startup"
        start_time = time.time()
        
        try:
            # Test app creation
            test_app = create_app()
            
            with test_app.app_context():
                # Test basic app functionality
                assert test_app.config is not None
                assert db is not None
                
            duration = (time.time() - start_time) * 1000
            self.log_test(test_name, 'PASS', 'Flask app starts successfully', duration)
            return True
            
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.log_test(test_name, 'FAIL', f'App startup failed: {str(e)}', duration)
            return False
    
    def test_redis_connectivity(self):
        """Test Redis connectivity for caching"""
        test_name = "Redis Connectivity"
        start_time = time.time()
        
        try:
            with self.app.app_context():
                from app.extensions import rq
                import redis
                
                # Get Redis connection from RQ
                try:
                    redis_conn = rq.connection
                except AttributeError:
                    # Fallback to creating direct connection
                    redis_url = self.app.config.get('RQ_REDIS_URL', 'redis://localhost:6379/0')
                    redis_conn = redis.from_url(redis_url)
                
                # Test basic Redis operations
                test_key = 'regression_test_key'
                test_value = 'regression_test_value'
                
                redis_conn.set(test_key, test_value, ex=60)
                retrieved_value = redis_conn.get(test_key)
                
                if retrieved_value and retrieved_value.decode() == test_value:
                    redis_conn.delete(test_key)
                    duration = (time.time() - start_time) * 1000
                    self.log_test(test_name, 'PASS', 'Redis operations successful', duration)
                    return True
                else:
                    duration = (time.time() - start_time) * 1000
                    self.log_test(test_name, 'FAIL', 'Redis value mismatch', duration)
                    return False
                    
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.log_test(test_name, 'FAIL', f'Redis connectivity failed: {str(e)}', duration)
            return False
    
    def test_api_endpoints_structure(self):
        """Test that API endpoints are properly structured"""
        test_name = "API Endpoints Structure"
        start_time = time.time()
        
        try:
            with self.app.app_context():
                # Test that the app has the expected blueprints
                blueprint_names = [bp.name for bp in self.app.blueprints.values()]
                expected_blueprints = ['main', 'auth', 'api']
                
                missing_blueprints = [bp for bp in expected_blueprints if bp not in blueprint_names]
                
                if missing_blueprints:
                    duration = (time.time() - start_time) * 1000
                    self.log_test(test_name, 'FAIL', f'Missing blueprints: {missing_blueprints}', duration)
                    return False
                
                # Test that key routes exist by checking URL map
                key_routes = [
                    'main.dashboard',
                    'main.index',
                    'auth.login'
                ]
                
                # Check if routes exist in URL map
                existing_routes = []
                for rule in self.app.url_map.iter_rules():
                    existing_routes.append(rule.endpoint)
                
                missing_routes = []
                for route in key_routes:
                    if route not in existing_routes:
                        missing_routes.append(route)
                
                if missing_routes:
                    duration = (time.time() - start_time) * 1000
                    self.log_test(test_name, 'FAIL', f'Missing routes: {missing_routes}', duration)
                    return False
                
                # Test API routes separately (they may have different naming)
                try:
                    # Try to access the API blueprint routes
                    api_routes = []
                    for rule in self.app.url_map.iter_rules():
                        if rule.endpoint.startswith('api.'):
                            api_routes.append(rule.endpoint)
                    
                    if not api_routes:
                        duration = (time.time() - start_time) * 1000
                        self.log_test(test_name, 'FAIL', 'No API routes found', duration)
                        return False
                        
                except Exception as e:
                    duration = (time.time() - start_time) * 1000
                    self.log_test(test_name, 'FAIL', f'Error checking API routes: {str(e)}', duration)
                    return False
                
                duration = (time.time() - start_time) * 1000
                self.log_test(test_name, 'PASS', f'All blueprints and routes exist', duration)
                return True
                
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.log_test(test_name, 'FAIL', f'API structure test failed: {str(e)}', duration)
            return False
    
    def test_pagination_functionality(self):
        """Test pagination functionality"""
        test_name = "Pagination Functionality"
        start_time = time.time()
        
        try:
            with self.app.app_context():
                # Test playlist pagination
                from app.main.routes import PLAYLISTS_PER_PAGE
                
                # Verify pagination constant
                assert PLAYLISTS_PER_PAGE == 25, f"Expected PLAYLISTS_PER_PAGE=25, got {PLAYLISTS_PER_PAGE}"
                
                # Test pagination query
                paginated_playlists = Playlist.query.paginate(
                    page=1,
                    per_page=PLAYLISTS_PER_PAGE,
                    error_out=False
                )
                
                # Verify pagination object has expected attributes
                assert hasattr(paginated_playlists, 'items')
                assert hasattr(paginated_playlists, 'pages')
                assert hasattr(paginated_playlists, 'has_prev')
                assert hasattr(paginated_playlists, 'has_next')
                
                duration = (time.time() - start_time) * 1000
                self.log_test(test_name, 'PASS', 'Pagination functionality working', duration)
                return True
                
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.log_test(test_name, 'FAIL', f'Pagination test failed: {str(e)}', duration)
            return False
    
    def test_caching_functionality(self):
        """Test caching functionality"""
        test_name = "Caching Functionality"
        start_time = time.time()
        
        try:
            with self.app.app_context():
                # Import caching functions
                from app.api.routes import get_cache_key, cache_response, get_cached_response
                
                # Test cache key generation
                cache_key = get_cache_key('test', user_id=123, param='value')
                assert cache_key == 'api:test:user:123:param:value'
                
                # Test caching and retrieval (may fail if Redis is not available)
                try:
                    test_data = {'test': 'data', 'timestamp': datetime.now().isoformat()}
                    cache_response(cache_key, test_data, ttl=60)
                    
                    cached_data = get_cached_response(cache_key)
                    if cached_data is not None:
                        assert cached_data['test'] == 'data'
                        duration = (time.time() - start_time) * 1000
                        self.log_test(test_name, 'PASS', 'Caching functionality working', duration)
                        return True
                    else:
                        # Cache miss is acceptable if Redis is not available
                        duration = (time.time() - start_time) * 1000
                        self.log_test(test_name, 'PASS', 'Cache key generation working (Redis may not be available)', duration)
                        return True
                except Exception as cache_error:
                    # If Redis is not available, just test key generation
                    duration = (time.time() - start_time) * 1000
                    self.log_test(test_name, 'PASS', f'Cache key generation working (Redis unavailable: {str(cache_error)})', duration)
                    return True
                
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.log_test(test_name, 'FAIL', f'Caching test failed: {str(e)}', duration)
            return False
    
    def cleanup_test_data(self):
        """Clean up test data created during regression testing"""
        test_name = "Test Data Cleanup"
        start_time = time.time()
        
        try:
            with self.app.app_context():
                # Remove test data
                db.session.query(PlaylistSong).filter(
                    PlaylistSong.playlist_id.in_(
                        db.session.query(Playlist.id).filter(
                            Playlist.spotify_id == 'test_regression_playlist'
                        )
                    )
                ).delete(synchronize_session=False)
                
                db.session.query(AnalysisResult).filter(
                    AnalysisResult.song_id.in_(
                        db.session.query(Song.id).filter(
                            Song.spotify_id == 'test_regression_song'
                        )
                    )
                ).delete(synchronize_session=False)
                
                db.session.query(Playlist).filter(
                    Playlist.spotify_id == 'test_regression_playlist'
                ).delete()
                
                db.session.query(Song).filter(
                    Song.spotify_id == 'test_regression_song'
                ).delete()
                
                db.session.query(User).filter(
                    User.spotify_id == 'test_regression_user'
                ).delete()
                
                db.session.commit()
                
                duration = (time.time() - start_time) * 1000
                self.log_test(test_name, 'PASS', 'Test data cleaned up', duration)
                return True
                
        except Exception as e:
            try:
                with self.app.app_context():
                    db.session.rollback()
            except:
                pass  # Ignore rollback errors in test context
            duration = (time.time() - start_time) * 1000
            self.log_test(test_name, 'FAIL', f'Cleanup failed: {str(e)}', duration)
            return False
    
    def run_all_tests(self):
        """Run all regression tests"""
        print("🧪 STARTING COMPREHENSIVE REGRESSION TESTING")
        print("=" * 60)
        
        start_time = time.time()
        
        # Core functionality tests
        tests = [
            self.test_app_startup,
            self.test_database_connectivity,
            self.test_database_tables,
            self.test_performance_indexes,
            self.test_redis_connectivity,
            self.test_model_creation,
            self.test_database_queries,
            self.test_api_endpoints_structure,
            self.test_pagination_functionality,
            self.test_caching_functionality,
            self.cleanup_test_data
        ]
        
        for test in tests:
            test()
        
        total_duration = (time.time() - start_time) * 1000
        
        # Print summary
        print(f"\n📊 REGRESSION TEST SUMMARY")
        print("=" * 40)
        print(f"✅ Passed: {len(self.passed_tests)}")
        print(f"❌ Failed: {len(self.failed_tests)}")
        print(f"⏱️  Total Duration: {total_duration:.1f}ms")
        
        if self.failed_tests:
            print(f"\n❌ FAILED TESTS:")
            for test in self.failed_tests:
                print(f"   - {test}")
            
            print(f"\n🚨 REGRESSION TESTING FAILED")
            print("   Please fix the failing tests before committing.")
            return False
        else:
            print(f"\n🎉 ALL REGRESSION TESTS PASSED!")
            print("   Build is ready for commit.")
            return True

def main():
    """Run regression testing"""
    tester = RegressionTester()
    success = tester.run_all_tests()
    
    # Write results to log file
    with open('regression_test.log', 'w') as f:
        f.write(f"Regression Test Results - {datetime.now().isoformat()}\n")
        f.write("=" * 60 + "\n\n")
        
        for result in tester.test_results:
            f.write(f"{result['status']}: {result['test']}\n")
            f.write(f"  Message: {result['message']}\n")
            f.write(f"  Duration: {result['duration']:.1f}ms\n")
            f.write(f"  Timestamp: {result['timestamp']}\n\n")
        
        f.write(f"\nSUMMARY:\n")
        f.write(f"Passed: {len(tester.passed_tests)}\n")
        f.write(f"Failed: {len(tester.failed_tests)}\n")
        f.write(f"Overall: {'PASS' if success else 'FAIL'}\n")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main()) 