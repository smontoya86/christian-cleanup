#!/usr/bin/env python3
"""
Docker Production Readiness Test Suite
Comprehensive test to validate all functionality works in Docker environment
"""

import sys
import os
import time
import requests
import subprocess
import json
from datetime import datetime, timedelta
import docker

class DockerProductionTester:
    def __init__(self):
        self.docker_client = docker.from_env()
        self.container = None
        self.base_url = 'http://localhost:5001'
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

    def start_docker_services(self):
        """Start Docker services using docker-compose"""
        print("🐳 Starting Docker services...")
        try:
            # Stop any existing services
            subprocess.run(['docker-compose', 'down'], 
                         capture_output=True, cwd='/Users/sammontoya/christian cleanup windsurf')
            
            # Start services
            result = subprocess.run(['docker-compose', 'up', '-d'], 
                                  capture_output=True, text=True,
                                  cwd='/Users/sammontoya/christian cleanup windsurf')
            
            if result.returncode != 0:
                print(f"❌ Failed to start Docker services: {result.stderr}")
                return False
            
            # Wait for services to be ready
            print("⏳ Waiting for services to start...")
            time.sleep(30)  # Give more time for Docker services
            
            # Check if web service is responding
            max_retries = 10
            for i in range(max_retries):
                try:
                    response = requests.get(f"{self.base_url}/", timeout=5)
                    if response.status_code == 200:
                        print("✅ Docker services started successfully")
                        return True
                except requests.exceptions.RequestException:
                    if i < max_retries - 1:
                        print(f"⏳ Waiting for web service... (attempt {i+1}/{max_retries})")
                        time.sleep(5)
                    else:
                        print("❌ Web service not responding after retries")
                        return False
            
            return False
                
        except Exception as e:
            print(f"❌ Failed to start Docker services: {e}")
            return False

    def stop_docker_services(self):
        """Stop Docker services"""
        print("🛑 Stopping Docker services...")
        try:
            result = subprocess.run(['docker-compose', 'down'], 
                                  capture_output=True, text=True,
                                  cwd='/Users/sammontoya/christian cleanup windsurf')
            if result.returncode == 0:
                print("✅ Docker services stopped successfully")
            else:
                print(f"⚠️ Warning stopping services: {result.stderr}")
        except Exception as e:
            print(f"⚠️ Error stopping Docker services: {e}")

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
                failed_endpoints.append(f"{name} (Connection failed: {str(e)})")
        
        duration = (time.time() - start_time) * 1000
        
        if failed_endpoints:
            self.log_test(test_name, 'FAIL', f'Failed endpoints: {failed_endpoints}', duration)
            return False
        else:
            self.log_test(test_name, 'PASS', f'All {len(endpoints)} endpoints responding', duration)
            return True

    def test_api_endpoints_performance(self):
        """Test API endpoints performance"""
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
                    if endpoint_duration > 2000:  # Should be under 2 seconds for Docker
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

    def test_database_connectivity(self):
        """Test database connectivity through Docker"""
        test_name = "Database Connectivity"
        start_time = time.time()
        
        try:
            # Execute a database test command in the web container
            result = subprocess.run([
                'docker-compose', 'exec', '-T', 'web', 
                'python', '-c', 
                '''
import sys
sys.path.append("/app")
from app import create_app
from app.extensions import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    result = db.session.execute(text("SELECT COUNT(*) FROM songs")).scalar()
    print(f"Songs in database: {result}")
'''
            ], capture_output=True, text=True, cwd='/Users/sammontoya/christian cleanup windsurf')
            
            duration = (time.time() - start_time) * 1000
            
            if result.returncode == 0 and "Songs in database:" in result.stdout:
                song_count = result.stdout.strip().split(": ")[-1]
                self.log_test(test_name, 'PASS', f'Database accessible, {song_count} songs found', duration)
                return True
            else:
                self.log_test(test_name, 'FAIL', f'Database test failed: {result.stderr}', duration)
                return False
                
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.log_test(test_name, 'FAIL', f'Database test failed: {str(e)}', duration)
            return False

    def test_redis_connectivity(self):
        """Test Redis connectivity through Docker"""
        test_name = "Redis Connectivity"
        start_time = time.time()
        
        try:
            # Test Redis connectivity through the web container
            result = subprocess.run([
                'docker-compose', 'exec', '-T', 'web', 
                'python', '-c', 
                '''
import sys
sys.path.append("/app")
from app import create_app
from app.api.routes import get_cache_key, cache_response, get_cached_response

app = create_app()
with app.app_context():
    test_key = get_cache_key("docker_test", user_id=999)
    cache_response(test_key, {"test": "docker_data"}, ttl=60)
    cached = get_cached_response(test_key)
    if cached and cached.get("test") == "docker_data":
        print("Redis working")
    else:
        print("Redis failed")
'''
            ], capture_output=True, text=True, cwd='/Users/sammontoya/christian cleanup windsurf')
            
            duration = (time.time() - start_time) * 1000
            
            if result.returncode == 0 and "Redis working" in result.stdout:
                self.log_test(test_name, 'PASS', 'Redis caching working correctly', duration)
                return True
            else:
                self.log_test(test_name, 'FAIL', f'Redis test failed: {result.stderr}', duration)
                return False
                
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.log_test(test_name, 'FAIL', f'Redis test failed: {str(e)}', duration)
            return False

    def test_performance_indexes(self):
        """Test that performance indexes exist in Docker database"""
        test_name = "Performance Indexes"
        start_time = time.time()
        
        try:
            # Check indexes through the web container
            result = subprocess.run([
                'docker-compose', 'exec', '-T', 'web', 
                'python', '-c', 
                '''
import sys
sys.path.append("/app")
from app import create_app
from app.extensions import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    indexes = db.session.execute(text("""
        SELECT indexname FROM pg_indexes 
        WHERE schemaname = 'public' AND indexname LIKE 'idx_%'
    """)).fetchall()
    
    index_names = [row[0] for row in indexes]
    expected = ['idx_analysis_results_status', 'idx_songs_spotify_id_new', 'idx_playlists_owner_id']
    missing = [idx for idx in expected if idx not in index_names]
    
    if missing:
        print(f"Missing indexes: {missing}")
    else:
        print(f"All indexes present: {len(index_names)} total")
'''
            ], capture_output=True, text=True, cwd='/Users/sammontoya/christian cleanup windsurf')
            
            duration = (time.time() - start_time) * 1000
            
            if result.returncode == 0 and "All indexes present" in result.stdout:
                index_count = result.stdout.strip().split(": ")[-1].split(" ")[0]
                self.log_test(test_name, 'PASS', f'All performance indexes present ({index_count} total)', duration)
                return True
            else:
                self.log_test(test_name, 'FAIL', f'Index check failed: {result.stdout}{result.stderr}', duration)
                return False
                
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.log_test(test_name, 'FAIL', f'Index test failed: {str(e)}', duration)
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
                response = requests.get(f"{self.base_url}{endpoint}", timeout=15)
                response_time = (time.time() - response_start) * 1000
                
                if response_time > 3000:  # Should be under 3 seconds for Docker
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

    def test_docker_health(self):
        """Test Docker container health"""
        test_name = "Docker Health"
        start_time = time.time()
        
        try:
            # Check container status
            result = subprocess.run(['docker-compose', 'ps'], 
                                  capture_output=True, text=True,
                                  cwd='/Users/sammontoya/christian cleanup windsurf')
            
            duration = (time.time() - start_time) * 1000
            
            if result.returncode == 0:
                # Check if all services are up
                if "Up" in result.stdout and "web" in result.stdout:
                    self.log_test(test_name, 'PASS', 'All Docker services healthy', duration)
                    return True
                else:
                    self.log_test(test_name, 'FAIL', f'Some services not healthy: {result.stdout}', duration)
                    return False
            else:
                self.log_test(test_name, 'FAIL', f'Docker health check failed: {result.stderr}', duration)
                return False
                
        except Exception as e:
            duration = (time.time() - start_time) * 1000
            self.log_test(test_name, 'FAIL', f'Docker health test failed: {str(e)}', duration)
            return False

    def run_production_tests(self):
        """Run all Docker production readiness tests"""
        print("🐳 DOCKER PRODUCTION READINESS TEST SUITE")
        print("=" * 60)
        
        # Start Docker services
        if not self.start_docker_services():
            print("❌ Cannot proceed - Docker services failed to start")
            return False
        
        try:
            # Run all tests
            tests = [
                self.test_docker_health,
                self.test_basic_endpoints,
                self.test_database_connectivity,
                self.test_performance_indexes,
                self.test_redis_connectivity,
                self.test_api_endpoints_performance,
                self.test_response_times,
            ]
            
            for test in tests:
                test()
                time.sleep(1)  # Brief pause between tests
            
            # Print summary
            print(f"\n📊 DOCKER PRODUCTION TEST SUMMARY")
            print("=" * 40)
            print(f"✅ Passed: {len(self.passed_tests)}")
            print(f"❌ Failed: {len(self.failed_tests)}")
            
            if self.failed_tests:
                print(f"\n❌ FAILED TESTS:")
                for test in self.failed_tests:
                    print(f"   - {test}")
                
                print(f"\n🚨 DOCKER PRODUCTION READINESS: FAILED")
                print("   Please fix the failing tests before deploying.")
                return False
            else:
                print(f"\n🎉 DOCKER PRODUCTION READINESS: PASSED!")
                print("   Application is ready for production deployment.")
                return True
                
        finally:
            # Always stop the Docker services
            self.stop_docker_services()

def main():
    """Run Docker production readiness testing"""
    tester = DockerProductionTester()
    success = tester.run_production_tests()
    
    # Write results to log file
    with open('docker_production_test.log', 'w') as f:
        f.write(f"Docker Production Readiness Test Results - {datetime.now().isoformat()}\n")
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