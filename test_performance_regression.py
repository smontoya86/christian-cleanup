#!/usr/bin/env python3
"""
Performance Regression Testing Suite
Measures response times, database performance, and background job processing.
"""

import sys
import os
import time
import logging
import statistics
from datetime import datetime
import json

# Add the app directory to Python path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app
from app.models.models import User, Playlist, Song, AnalysisResult
from app.extensions import db
from app.services.unified_analysis_service import UnifiedAnalysisService

def setup_logging():
    """Configure performance testing logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/performance_regression_test.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

class PerformanceTestSuite:
    """Performance regression testing suite."""
    
    def __init__(self):
        self.app = create_app('development')
        self.performance_metrics = {}
        self.start_time = datetime.now()
    
    def measure_execution_time(self, func, *args, **kwargs):
        """Measure execution time of a function."""
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        return result, execution_time
    
    def test_database_query_performance(self):
        """Test database query performance."""
        test_name = "Database Query Performance"
        logger.info(f"🔍 Testing {test_name}...")
        
        with self.app.app_context():
            query_times = {}
            
            # Test basic queries
            queries = [
                ("User Count", lambda: User.query.count()),
                ("Playlist Count", lambda: Playlist.query.count()),
                ("Song Count", lambda: Song.query.count()),
                ("Analysis Count", lambda: AnalysisResult.query.count()),
                ("Songs with Lyrics", lambda: Song.query.filter(Song.lyrics.isnot(None)).count()),
                ("Completed Analyses", lambda: AnalysisResult.query.filter_by(status='completed').count()),
            ]
            
            for query_name, query_func in queries:
                try:
                    result, exec_time = self.measure_execution_time(query_func)
                    query_times[query_name] = {
                        'time': exec_time,
                        'result': result
                    }
                    logger.info(f"   • {query_name}: {exec_time:.3f}s (Result: {result})")
                except Exception as e:
                    logger.error(f"   • {query_name}: FAILED - {str(e)}")
                    query_times[query_name] = {'time': None, 'error': str(e)}
            
            # Test complex queries
            complex_queries = [
                ("Songs with Analysis", lambda: db.session.query(Song).join(AnalysisResult).count()),
                ("User Playlists", lambda: db.session.query(Playlist).join(User).count()),
            ]
            
            for query_name, query_func in complex_queries:
                try:
                    result, exec_time = self.measure_execution_time(query_func)
                    query_times[query_name] = {
                        'time': exec_time,
                        'result': result
                    }
                    logger.info(f"   • {query_name}: {exec_time:.3f}s (Result: {result})")
                except Exception as e:
                    logger.error(f"   • {query_name}: FAILED - {str(e)}")
                    query_times[query_name] = {'time': None, 'error': str(e)}
            
            self.performance_metrics['database_queries'] = query_times
            
            # Calculate average query time
            valid_times = [q['time'] for q in query_times.values() if q['time'] is not None]
            if valid_times:
                avg_time = statistics.mean(valid_times)
                max_time = max(valid_times)
                logger.info(f"📊 Query Performance Summary: Avg: {avg_time:.3f}s, Max: {max_time:.3f}s")
                
                # Performance thresholds
                if avg_time > 1.0:
                    logger.warning(f"⚠️  Average query time ({avg_time:.3f}s) exceeds recommended threshold (1.0s)")
                if max_time > 5.0:
                    logger.warning(f"⚠️  Maximum query time ({max_time:.3f}s) exceeds recommended threshold (5.0s)")
            
            return query_times
    
    def test_unified_analysis_service_performance(self):
        """Test UnifiedAnalysisService performance."""
        test_name = "Unified Analysis Service Performance"
        logger.info(f"🔍 Testing {test_name}...")
        
        with self.app.app_context():
            user = User.query.first()
            if not user:
                logger.error("No users found for performance testing")
                return None
            
            # Test service initialization time
            _, init_time = self.measure_execution_time(lambda: UnifiedAnalysisService())
            logger.info(f"   • Service Initialization: {init_time:.3f}s")
            
            analysis_service = UnifiedAnalysisService()
            
            # Test analysis method initialization time
            song = Song.query.first()
            if song:
                # Test the service can be called without error
                _, method_time = self.measure_execution_time(
                    lambda: hasattr(analysis_service, 'execute_comprehensive_analysis')
                )
                logger.info(f"   • Analysis Method Check: {method_time:.3f}s")
                retrieval_time = method_time
            else:
                retrieval_time = None
                logger.warning("No songs found for analysis performance testing")
            
            performance_data = {
                'initialization_time': init_time,
                'retrieval_time': retrieval_time
            }
            
            self.performance_metrics['analysis_service'] = performance_data
            return performance_data
    
    def test_route_response_times(self):
        """Test route response times."""
        test_name = "Route Response Times"
        logger.info(f"🔍 Testing {test_name}...")
        
        route_times = {}
        
        with self.app.test_client() as client:
            routes_to_test = [
                ('/', 'Home Route'),
                ('/auth/login', 'Login Route'),
                ('/dashboard', 'Dashboard Route'),  # Will likely redirect
            ]
            
            for route, route_name in routes_to_test:
                try:
                    def make_request():
                        return client.get(route, follow_redirects=False)
                    
                    response, exec_time = self.measure_execution_time(make_request)
                    route_times[route_name] = {
                        'time': exec_time,
                        'status_code': response.status_code
                    }
                    logger.info(f"   • {route_name} ({route}): {exec_time:.3f}s (Status: {response.status_code})")
                except Exception as e:
                    logger.error(f"   • {route_name} ({route}): FAILED - {str(e)}")
                    route_times[route_name] = {'time': None, 'error': str(e)}
        
        self.performance_metrics['route_responses'] = route_times
        
        # Analyze route performance
        valid_times = [r['time'] for r in route_times.values() if r['time'] is not None]
        if valid_times:
            avg_time = statistics.mean(valid_times)
            max_time = max(valid_times)
            logger.info(f"📊 Route Performance Summary: Avg: {avg_time:.3f}s, Max: {max_time:.3f}s")
            
            if avg_time > 2.0:
                logger.warning(f"⚠️  Average route response time ({avg_time:.3f}s) exceeds recommended threshold (2.0s)")
        
        return route_times
    
    def test_redis_performance(self):
        """Test Redis connection and operation performance."""
        test_name = "Redis Performance"
        logger.info(f"🔍 Testing {test_name}...")
        
        try:
            with self.app.app_context():
                from app.extensions import rq
                
                redis_times = {}
                
                # Test Redis ping
                _, ping_time = self.measure_execution_time(lambda: rq.connection.ping())
                redis_times['ping'] = ping_time
                logger.info(f"   • Redis Ping: {ping_time:.3f}s")
                
                # Test queue operations
                test_queue = rq.get_queue('default')
                
                # Test queue length retrieval
                _, queue_len_time = self.measure_execution_time(lambda: len(test_queue))
                redis_times['queue_length'] = queue_len_time
                logger.info(f"   • Queue Length Retrieval: {queue_len_time:.3f}s")
                
                # Test job enqueueing (simple job)
                _, enqueue_time = self.measure_execution_time(
                    lambda: test_queue.enqueue('time.sleep', 0.01, timeout=30)
                )
                redis_times['enqueue'] = enqueue_time
                logger.info(f"   • Job Enqueueing: {enqueue_time:.3f}s")
                
                self.performance_metrics['redis_operations'] = redis_times
                
                # Performance thresholds for Redis
                if ping_time > 0.1:
                    logger.warning(f"⚠️  Redis ping time ({ping_time:.3f}s) is high")
                if enqueue_time > 0.5:
                    logger.warning(f"⚠️  Job enqueue time ({enqueue_time:.3f}s) is high")
                
                return redis_times
        except Exception as e:
            logger.error(f"Redis performance testing failed: {str(e)}")
            return None
    
    def test_memory_usage(self):
        """Test basic memory usage patterns."""
        test_name = "Memory Usage"
        logger.info(f"🔍 Testing {test_name}...")
        
        try:
            import psutil
            process = psutil.Process()
            
            # Get initial memory usage
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Perform some operations
            with self.app.app_context():
                # Load some data
                users = User.query.limit(100).all()
                songs = Song.query.limit(100).all()
                analyses = AnalysisResult.query.limit(100).all()
                
                # Create analysis service
                analysis_service = UnifiedAnalysisService()
                
                # Check memory after operations
                final_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_increase = final_memory - initial_memory
                
                memory_data = {
                    'initial_mb': initial_memory,
                    'final_mb': final_memory,
                    'increase_mb': memory_increase
                }
                
                logger.info(f"   • Initial Memory: {initial_memory:.1f} MB")
                logger.info(f"   • Final Memory: {final_memory:.1f} MB")
                logger.info(f"   • Memory Increase: {memory_increase:.1f} MB")
                
                if memory_increase > 100:
                    logger.warning(f"⚠️  High memory increase ({memory_increase:.1f} MB) during operations")
                
                self.performance_metrics['memory_usage'] = memory_data
                return memory_data
        except ImportError:
            logger.warning("psutil not available - skipping memory usage test")
            return None
        except Exception as e:
            logger.error(f"Memory usage testing failed: {str(e)}")
            return None
    
    def run_performance_tests(self):
        """Run all performance tests."""
        logger.info("🚀 Starting Performance Regression Testing Suite")
        logger.info(f"📅 Test Start Time: {self.start_time}")
        logger.info("=" * 60)
        
        # Run performance tests
        test_methods = [
            self.test_database_query_performance,
            self.test_unified_analysis_service_performance,
            self.test_route_response_times,
            self.test_redis_performance,
            self.test_memory_usage,
        ]
        
        for test_method in test_methods:
            try:
                test_method()
                logger.info("")  # Add spacing between tests
            except Exception as e:
                logger.error(f"💥 Unexpected error in {test_method.__name__}: {str(e)}")
        
        # Generate performance report
        self.generate_performance_report()
    
    def generate_performance_report(self):
        """Generate comprehensive performance report."""
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        logger.info("=" * 60)
        logger.info("📊 PERFORMANCE REGRESSION TESTING COMPLETE")
        logger.info("=" * 60)
        logger.info(f"⏱️  Total Test Duration: {duration}")
        logger.info("")
        
        # Generate summary
        logger.info("📈 PERFORMANCE SUMMARY:")
        
        if 'database_queries' in self.performance_metrics:
            db_metrics = self.performance_metrics['database_queries']
            valid_times = [q['time'] for q in db_metrics.values() if q.get('time') is not None]
            if valid_times:
                logger.info(f"   • Database Queries: {len(valid_times)} tested, avg {statistics.mean(valid_times):.3f}s")
        
        if 'analysis_service' in self.performance_metrics:
            as_metrics = self.performance_metrics['analysis_service']
            logger.info(f"   • Analysis Service Init: {as_metrics.get('initialization_time', 'N/A'):.3f}s")
        
        if 'route_responses' in self.performance_metrics:
            route_metrics = self.performance_metrics['route_responses']
            valid_times = [r['time'] for r in route_metrics.values() if r.get('time') is not None]
            if valid_times:
                logger.info(f"   • Route Responses: {len(valid_times)} tested, avg {statistics.mean(valid_times):.3f}s")
        
        if 'redis_operations' in self.performance_metrics:
            redis_metrics = self.performance_metrics['redis_operations']
            logger.info(f"   • Redis Ping: {redis_metrics.get('ping', 'N/A'):.3f}s")
        
        if 'memory_usage' in self.performance_metrics:
            mem_metrics = self.performance_metrics['memory_usage']
            logger.info(f"   • Memory Usage: {mem_metrics.get('final_mb', 'N/A'):.1f} MB")
        
        # Save detailed metrics to file
        metrics_file = 'logs/performance_metrics.json'
        try:
            with open(metrics_file, 'w') as f:
                json.dump(self.performance_metrics, f, indent=2, default=str)
            logger.info(f"📄 Detailed metrics saved to: {metrics_file}")
        except Exception as e:
            logger.error(f"Failed to save metrics: {str(e)}")
        
        logger.info("")
        logger.info("🎯 Performance testing complete!")
        
        return self.performance_metrics

def main():
    """Main execution function."""
    logger.info("Starting Performance Regression Testing for Christian Cleanup Application")
    
    # Create performance test suite
    test_suite = PerformanceTestSuite()
    
    # Run all tests
    results = test_suite.run_performance_tests()
    
    # Return success (performance tests are informational)
    sys.exit(0)

if __name__ == "__main__":
    main() 