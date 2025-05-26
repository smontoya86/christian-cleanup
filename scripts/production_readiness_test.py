#!/usr/bin/env python3
"""
Production Readiness Test Suite
Comprehensive test to validate all functionality works in production environment
"""

import sys
import os
import time
import requests
import subprocess
import signal
import json
from datetime import datetime, timedelta
from threading import Thread
import psutil

sys.path.append('/app')

class ProductionTester:
    def __init__(self):
        self.app_process = None
        self.base_url = 'http://127.0.0.1:5001'
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

    def start_application(self):
        """Start the Flask application"""
        print("🚀 Starting Flask application...")
        try:
            self.app_process = subprocess.Popen(
                ['python', 'run.py'],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd='/Users/sammontoya/christian cleanup windsurf'
            )
            
            # Wait for app to start
            time.sleep(5)
            
            # Check if process is still running
            if self.app_process.poll() is None:
                print("✅ Application started successfully")
                return True
            else:
                print("❌ Application failed to start")
                return False
                
        except Exception as e:
            print(f"❌ Failed to start application: {e}")
            return False

    def stop_application(self):
        """Stop the Flask application"""
        if self.app_process:
            try:
                self.app_process.terminate()
                self.app_process.wait(timeout=10)
                print("✅ Application stopped successfully")
            except subprocess.TimeoutExpired:
                self.app_process.kill()
                print("⚠️ Application force-killed")
            except Exception as e:
                print(f"⚠️ Error stopping application: {e}")

    def test_basic_endpoints(self):
        """Test basic application endpoints"""
        test_name = "Basic Endpoints"
        start_time = time.time()
        
        endpoints = [
            ('/', 'Home Page'),
            ('/auth/login', 'Login Page'),
        ]
        
        failed_endpoints = []
        
        for endpoint, name in endpoints:
            try:
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                if response.status_code not in [200, 302]:
                    failed_endpoints.append(f"{name} (HTTP {response.status_code})")
            except requests.exceptions.RequestException as e:
                failed_endpoints.append(f"{name} (Connection failed)")
        
        duration = (time.time() - start_time) * 1000
        
        if failed_endpoints:
            self.log_test(test_name, 'FAIL', f'Failed endpoints: {failed_endpoints}', duration)
            return False
        else:
            self.log_test(test_name, 'PASS', f'All {len(endpoints)} endpoints responding', duration)
            return True

    def test_database_performance(self):
        """Test database performance with current data"""
        test_name = "Database Performance"
        start_time = time.time()
        
        try:
            from app import create_app
            from app.extensions import db
            from app.models import Song, AnalysisResult, Playlist
            from sqlalchemy import text
            
            app = create_app()
            with app.app_context():
                # Test song count query (should use index)
                song_start = time.time()
                song_count = db.session.query(Song).count()
                song_duration = (time.time() - song_start) * 1000
                
                # Test analysis status query (should use idx_analysis_results_status)
                analysis_start = time.time()
                completed_count = db.session.query(AnalysisResult).filter(
                    AnalysisResult.status == 'completed'
                ).count()
                analysis_duration = (time.time() - analysis_start) * 1000
                
                # Test playlist query (should use idx_playlists_owner_id)
                playlist_start = time.time()
                playlist_count = db.session.query(Playlist).count()
                playlist_duration = (time.time() - playlist_start) * 1000
                
                # Check if queries are fast enough
                slow_queries = []
                if song_duration > 100:  # Should be under 100ms
                    slow_queries.append(f"Song count: {song_duration:.1f}ms")
                if analysis_duration > 100:
                    slow_queries.append(f"Analysis status: {analysis_duration:.1f}ms")
                if playlist_duration > 100:
                    slow_queries.append(f"Playlist count: {playlist_duration:.1f}ms")
                
                duration = (time.time() - start_time) * 1000
                
                if slow_queries:
                    self.log_test(test_name, 'FAIL', f'Slow queries: {slow_queries}', duration)
                    return False
                else:
                    message = f'All queries fast: Songs({song_duration:.1f}ms), Analysis({analysis_duration:.1f}ms), Playlists({playlist_duration:.1f}ms)'
                    self.log_test(test_name, 'PASS', message, duration)
                    return True
                    
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.log_test(test_name, 'FAIL', f'Database test failed: {str(e)}', duration)
            return False

    def test_api_endpoints_performance(self):
        """Test API endpoints performance (without authentication for now)"""
        test_name = "API Performance"
        start_time = time.time()
        
        # Test API endpoints that don't require authentication
        api_endpoints = [
            '/api/whitelist',
            '/api/blacklist',
        ]
        
        slow_endpoints = []
        failed_endpoints = []
        
        for endpoint in api_endpoints:
            try:
                endpoint_start = time.time()
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                endpoint_duration = (time.time() - endpoint_start) * 1000
                
                # Check if endpoint responds (even if it returns 401/403 for auth)
                if response.status_code in [200, 401, 403, 302]:
                    if endpoint_duration > 1000:  # Should be under 1 second
                        slow_endpoints.append(f"{endpoint} ({endpoint_duration:.1f}ms)")
                else:
                    failed_endpoints.append(f"{endpoint} (HTTP {response.status_code})")
                    
            except requests.exceptions.RequestException as e:
                failed_endpoints.append(f"{endpoint} (Connection failed)")
        
        duration = (time.time() - start_time) * 1000
        
        if failed_endpoints or slow_endpoints:
            issues = failed_endpoints + slow_endpoints
            self.log_test(test_name, 'FAIL', f'API issues: {issues}', duration)
            return False
        else:
            self.log_test(test_name, 'PASS', f'All {len(api_endpoints)} API endpoints responding quickly', duration)
            return True

    def test_redis_caching(self):
        """Test Redis caching functionality"""
        test_name = "Redis Caching"
        start_time = time.time()
        
        try:
            from app import create_app
            from app.api.routes import get_cache_key, cache_response, get_cached_response
            
            app = create_app()
            with app.app_context():
                # Test cache operations
                test_key = get_cache_key('production_test', user_id=999)
                test_data = {'test': 'production_data', 'timestamp': datetime.now().isoformat()}
                
                # Test caching
                cache_response(test_key, test_data, ttl=60)
                
                # Test retrieval
                cached_data = get_cached_response(test_key)
                
                duration = (time.time() - start_time) * 1000
                
                if cached_data and cached_data.get('test') == 'production_data':
                    self.log_test(test_name, 'PASS', 'Redis caching working correctly', duration)
                    return True
                else:
                    self.log_test(test_name, 'FAIL', 'Redis cache retrieval failed', duration)
                    return False
                    
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.log_test(test_name, 'FAIL', f'Redis test failed: {str(e)}', duration)
            return False

    def test_pagination_performance(self):
        """Test pagination performance"""
        test_name = "Pagination Performance"
        start_time = time.time()
        
        try:
            from app import create_app
            from app.extensions import db
            from app.models import Playlist
            from app.main.routes import PLAYLISTS_PER_PAGE
            
            app = create_app()
            with app.app_context():
                # Test pagination query performance
                pagination_start = time.time()
                paginated = Playlist.query.paginate(
                    page=1,
                    per_page=PLAYLISTS_PER_PAGE,
                    error_out=False
                )
                pagination_duration = (time.time() - pagination_start) * 1000
                
                duration = (time.time() - start_time) * 1000
                
                if pagination_duration > 200:  # Should be under 200ms
                    self.log_test(test_name, 'FAIL', f'Pagination too slow: {pagination_duration:.1f}ms', duration)
                    return False
                else:
                    message = f'Pagination fast: {pagination_duration:.1f}ms, {len(paginated.items)} items'
                    self.log_test(test_name, 'PASS', message, duration)
                    return True
                    
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.log_test(test_name, 'FAIL', f'Pagination test failed: {str(e)}', duration)
            return False

    def test_memory_usage(self):
        """Test application memory usage"""
        test_name = "Memory Usage"
        start_time = time.time()
        
        try:
            if self.app_process:
                process = psutil.Process(self.app_process.pid)
                memory_info = process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024  # Convert to MB
                
                duration = (time.time() - start_time) * 1000
                
                if memory_mb > 500:  # Alert if over 500MB
                    self.log_test(test_name, 'FAIL', f'High memory usage: {memory_mb:.1f}MB', duration)
                    return False
                else:
                    self.log_test(test_name, 'PASS', f'Memory usage acceptable: {memory_mb:.1f}MB', duration)
                    return True
            else:
                duration = (time.time() - start_time) * 1000
                self.log_test(test_name, 'FAIL', 'No application process to monitor', duration)
                return False
                
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.log_test(test_name, 'FAIL', f'Memory test failed: {str(e)}', duration)
            return False

    def test_response_times(self):
        """Test overall response times"""
        test_name = "Response Times"
        start_time = time.time()
        
        endpoints_to_test = [
            ('/', 'Home'),
            ('/auth/login', 'Login'),
        ]
        
        slow_responses = []
        
        for endpoint, name in endpoints_to_test:
            try:
                response_start = time.time()
                response = requests.get(f"{self.base_url}{endpoint}", timeout=10)
                response_time = (time.time() - response_start) * 1000
                
                if response_time > 2000:  # Should be under 2 seconds
                    slow_responses.append(f"{name}: {response_time:.1f}ms")
                    
            except requests.exceptions.RequestException:
                slow_responses.append(f"{name}: Connection failed")
        
        duration = (time.time() - start_time) * 1000
        
        if slow_responses:
            self.log_test(test_name, 'FAIL', f'Slow responses: {slow_responses}', duration)
            return False
        else:
            self.log_test(test_name, 'PASS', f'All {len(endpoints_to_test)} endpoints respond quickly', duration)
            return True

    def run_production_tests(self):
        """Run all production readiness tests"""
        print("🏭 PRODUCTION READINESS TEST SUITE")
        print("=" * 60)
        
        # Start application
        if not self.start_application():
            print("❌ Cannot proceed - application failed to start")
            return False
        
        try:
            # Run all tests
            tests = [
                self.test_basic_endpoints,
                self.test_database_performance,
                self.test_api_endpoints_performance,
                self.test_redis_caching,
                self.test_pagination_performance,
                self.test_memory_usage,
                self.test_response_times,
            ]
            
            for test in tests:
                test()
                time.sleep(0.5)  # Brief pause between tests
            
            # Print summary
            print(f"\n📊 PRODUCTION TEST SUMMARY")
            print("=" * 40)
            print(f"✅ Passed: {len(self.passed_tests)}")
            print(f"❌ Failed: {len(self.failed_tests)}")
            
            if self.failed_tests:
                print(f"\n❌ FAILED TESTS:")
                for test in self.failed_tests:
                    print(f"   - {test}")
                
                print(f"\n🚨 PRODUCTION READINESS: FAILED")
                print("   Please fix the failing tests before deploying.")
                return False
            else:
                print(f"\n🎉 PRODUCTION READINESS: PASSED!")
                print("   Application is ready for production deployment.")
                return True
                
        finally:
            # Always stop the application
            self.stop_application()

def main():
    """Run production readiness testing"""
    tester = ProductionTester()
    success = tester.run_production_tests()
    
    # Write results to log file
    with open('production_test.log', 'w') as f:
        f.write(f"Production Readiness Test Results - {datetime.now().isoformat()}\n")
        f.write("=" * 60 + "\n\n")
        
        for result in tester.test_results:
            f.write(f"{result['status']}: {result['test']}\n")
            f.write(f"  Message: {result['message']}\n")
            f.write(f"  Duration: {result['duration']:.1f}ms\n")
            f.write(f"  Timestamp: {result['timestamp']}\n\n")
        
        f.write(f"\nSUMMARY:\n")
        f.write(f"Passed: {len(tester.passed_tests)}\n")
        f.write(f"Failed: {len(tester.failed_tests)}\n")
        f.write(f"Production Ready: {'YES' if success else 'NO'}\n")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main()) 