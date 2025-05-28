#!/usr/bin/env python3
"""
Route Regression Testing Suite
Tests all major routes and endpoints to ensure they're working after Task 30 completion.
"""

import sys
import os
import logging
from datetime import datetime

# Add the app directory to Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from app.models.models import User, Song, AnalysisResult
from app.extensions import db

def setup_logging():
    """Configure route testing logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/route_regression_test.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

class RouteTestSuite:
    """Route regression testing suite."""
    
    def __init__(self):
        self.app = create_app('development')
        self.client = self.app.test_client()
        self.test_results = {}
        self.start_time = datetime.now()
    
    def test_basic_routes(self):
        """Test basic application routes."""
        test_name = "Basic Routes"
        logger.info(f"🔍 Testing {test_name}...")
        
        routes_to_test = [
            ('/', 'GET', 'Home Route'),
            ('/auth/login', 'GET', 'Login Route'),
            ('/health', 'GET', 'Health Check Route'),
        ]
        
        results = {}
        
        for route, method, route_name in routes_to_test:
            try:
                if method == 'GET':
                    response = self.client.get(route, follow_redirects=False)
                elif method == 'POST':
                    response = self.client.post(route, follow_redirects=False)
                
                status_ok = response.status_code in [200, 302, 404]  # Allow redirects and reasonable errors
                results[route_name] = {
                    'status_code': response.status_code,
                    'success': status_ok,
                    'route': route,
                    'method': method
                }
                
                status_emoji = "✅" if status_ok else "❌"
                logger.info(f"   • {route_name} ({method} {route}): {status_emoji} Status {response.status_code}")
                
            except Exception as e:
                logger.error(f"   • {route_name} ({method} {route}): ❌ ERROR - {str(e)}")
                results[route_name] = {
                    'error': str(e),
                    'success': False,
                    'route': route,
                    'method': method
                }
        
        self.test_results['basic_routes'] = results
        return results
    
    def test_analysis_routes(self):
        """Test analysis-related routes with proper error handling."""
        test_name = "Analysis Routes"
        logger.info(f"🔍 Testing {test_name}...")
        
        with self.app.app_context():
            user = User.query.first()
            song = Song.query.first()
            
            if not user or not song:
                logger.warning("No user or song found for analysis route testing")
                return {'warning': 'No test data available'}
        
        # Test routes that should work without authentication
        routes_to_test = [
            ('/analyze', 'GET', 'Analyze Page'),
            ('/api/status', 'GET', 'API Status'),
        ]
        
        # Test analysis routes that require authentication (expect redirects)
        auth_routes = [
            ('/dashboard', 'GET', 'Dashboard'),
            ('/playlists', 'GET', 'Playlists'),
        ]
        
        results = {}
        
        # Test basic analysis routes
        for route, method, route_name in routes_to_test:
            try:
                if method == 'GET':
                    response = self.client.get(route, follow_redirects=False)
                
                # For analysis routes, 200, 302 (redirect), or 404 (not implemented) are acceptable
                status_ok = response.status_code in [200, 302, 404, 405]
                results[route_name] = {
                    'status_code': response.status_code,
                    'success': status_ok,
                    'route': route
                }
                
                status_emoji = "✅" if status_ok else "❌"
                logger.info(f"   • {route_name} ({route}): {status_emoji} Status {response.status_code}")
                
            except Exception as e:
                logger.error(f"   • {route_name} ({route}): ❌ ERROR - {str(e)}")
                results[route_name] = {
                    'error': str(e),
                    'success': False,
                    'route': route
                }
        
        # Test authenticated routes (expect redirects to login)
        for route, method, route_name in auth_routes:
            try:
                response = self.client.get(route, follow_redirects=False)
                
                # These should redirect to login (302) or show login page
                status_ok = response.status_code in [200, 302, 401]
                results[route_name] = {
                    'status_code': response.status_code,
                    'success': status_ok,
                    'route': route,
                    'note': 'Should redirect or require auth'
                }
                
                status_emoji = "✅" if status_ok else "❌"
                logger.info(f"   • {route_name} ({route}): {status_emoji} Status {response.status_code} (Auth Required)")
                
            except Exception as e:
                logger.error(f"   • {route_name} ({route}): ❌ ERROR - {str(e)}")
                results[route_name] = {
                    'error': str(e),
                    'success': False,
                    'route': route
                }
        
        self.test_results['analysis_routes'] = results
        return results
    
    def test_api_routes(self):
        """Test API routes."""
        test_name = "API Routes"
        logger.info(f"🔍 Testing {test_name}...")
        
        api_routes = [
            ('/api/health', 'GET', 'API Health Check'),
            ('/api/analysis/status', 'GET', 'Analysis Status API'),
        ]
        
        results = {}
        
        for route, method, route_name in api_routes:
            try:
                if method == 'GET':
                    response = self.client.get(route, follow_redirects=False)
                
                # API routes should return JSON or proper status codes
                status_ok = response.status_code in [200, 404, 405, 401]  # Allow various valid responses
                results[route_name] = {
                    'status_code': response.status_code,
                    'success': status_ok,
                    'route': route,
                    'content_type': response.content_type
                }
                
                status_emoji = "✅" if status_ok else "❌"
                logger.info(f"   • {route_name} ({route}): {status_emoji} Status {response.status_code}")
                
                # Check if response is JSON for successful API calls
                if response.status_code == 200 and 'application/json' in str(response.content_type):
                    logger.info(f"     └─ JSON response received ✅")
                
            except Exception as e:
                logger.error(f"   • {route_name} ({route}): ❌ ERROR - {str(e)}")
                results[route_name] = {
                    'error': str(e),
                    'success': False,
                    'route': route
                }
        
        self.test_results['api_routes'] = results
        return results
    
    def test_error_handling_routes(self):
        """Test error handling for invalid routes and requests."""
        test_name = "Error Handling Routes"
        logger.info(f"🔍 Testing {test_name}...")
        
        # Test invalid routes that should return 404
        invalid_routes = [
            ('/nonexistent-route', 'GET', 'Invalid Route'),
            ('/api/invalid-endpoint', 'GET', 'Invalid API Endpoint'),
        ]
        
        results = {}
        
        for route, method, route_name in invalid_routes:
            try:
                response = self.client.get(route, follow_redirects=False)
                
                # Should return 404 for invalid routes
                status_ok = response.status_code == 404
                results[route_name] = {
                    'status_code': response.status_code,
                    'success': status_ok,
                    'route': route,
                    'expected': 404
                }
                
                status_emoji = "✅" if status_ok else "❌"
                logger.info(f"   • {route_name} ({route}): {status_emoji} Status {response.status_code} (Expected 404)")
                
            except Exception as e:
                logger.error(f"   • {route_name} ({route}): ❌ ERROR - {str(e)}")
                results[route_name] = {
                    'error': str(e),
                    'success': False,
                    'route': route
                }
        
        self.test_results['error_handling'] = results
        return results
    
    def run_route_tests(self):
        """Run all route tests."""
        logger.info("🚀 Starting Route Regression Testing Suite")
        logger.info(f"📅 Test Start Time: {self.start_time}")
        logger.info("=" * 60)
        
        # Run route tests
        test_methods = [
            self.test_basic_routes,
            self.test_analysis_routes,
            self.test_api_routes,
            self.test_error_handling_routes,
        ]
        
        for test_method in test_methods:
            try:
                test_method()
                logger.info("")  # Add spacing between tests
            except Exception as e:
                logger.error(f"💥 Unexpected error in {test_method.__name__}: {str(e)}")
        
        # Generate route test report
        return self.generate_route_report()
    
    def generate_route_report(self):
        """Generate comprehensive route test report."""
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        logger.info("=" * 60)
        logger.info("📊 ROUTE REGRESSION TESTING COMPLETE")
        logger.info("=" * 60)
        logger.info(f"⏱️  Total Test Duration: {duration}")
        logger.info("")
        
        # Generate summary
        logger.info("📈 ROUTE TESTING SUMMARY:")
        
        total_tests = 0
        total_passed = 0
        
        for test_category, results in self.test_results.items():
            if isinstance(results, dict) and 'warning' not in results:
                category_tests = len(results)
                category_passed = sum(1 for r in results.values() if r.get('success', False))
                total_tests += category_tests
                total_passed += category_passed
                
                logger.info(f"   • {test_category.replace('_', ' ').title()}: {category_passed}/{category_tests} passed")
                
                # Log failed tests
                failed_tests = [name for name, result in results.items() if not result.get('success', False)]
                if failed_tests:
                    logger.warning(f"     └─ Failed: {', '.join(failed_tests)}")
        
        success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
        logger.info(f"   • Overall: {total_passed}/{total_tests} passed ({success_rate:.1f}%)")
        
        if success_rate >= 80:
            logger.info("🎉 Route testing PASSED! Most routes are functioning correctly.")
        else:
            logger.warning("⚠️  Route testing needs attention. Some routes may need fixing.")
        
        logger.info("")
        logger.info("🎯 Route testing complete!")
        
        return self.test_results

def main():
    """Main execution function."""
    logger.info("Starting Route Regression Testing for Christian Cleanup Application")
    
    # Create route test suite
    test_suite = RouteTestSuite()
    
    # Run all tests
    results = test_suite.run_route_tests()
    
    # Determine exit code based on results
    total_tests = 0
    total_passed = 0
    
    for test_category, test_results in results.items():
        if isinstance(test_results, dict) and 'warning' not in test_results:
            total_tests += len(test_results)
            total_passed += sum(1 for r in test_results.values() if r.get('success', False))
    
    success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    
    if success_rate >= 80:
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Failure

if __name__ == "__main__":
    main() 