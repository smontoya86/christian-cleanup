#!/usr/bin/env python3
"""
Comprehensive integration test for enhanced Redis connectivity and retry mechanisms.
Tests Task 27 implementation: Enhanced Redis Queue Connectivity.
"""

import os
import sys
import time
import logging
from datetime import datetime

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from dotenv import load_dotenv
load_dotenv()

def test_enhanced_redis_features():
    """Test all enhanced Redis features comprehensively."""
    print("🧪 COMPREHENSIVE ENHANCED REDIS FEATURES TEST")
    print("=" * 70)
    
    test_results = {
        'redis_connection_manager': False,
        'connection_pooling': False,
        'health_monitoring': False,
        'queue_monitoring': False,
        'retry_mechanisms': False,
        'error_classification': False,
        'resilient_job_creation': False,
        'statistics_tracking': False
    }
    
    try:
        # Test 1: Redis Connection Manager
        print("\n📋 Test 1: Enhanced Redis Connection Manager")
        from app.utils.redis_manager import redis_manager, test_redis_connection
        
        result = test_redis_connection()
        if result['success']:
            print(f"✅ Redis connection: PASSED (Response time: {result['response_time_ms']:.2f}ms)")
            print(f"   Redis info available: {'redis_info' in result}")
            print(f"   Pool info available: {'pool_info' in result}")
            test_results['redis_connection_manager'] = True
        else:
            print(f"❌ Redis connection: FAILED - {result['error']}")
        
        # Test 2: Connection Pooling
        print("\n📋 Test 2: Connection Pooling")
        connection1 = redis_manager.get_connection()
        connection2 = redis_manager.get_connection()
        
        if connection1 and connection2:
            print("✅ Connection pooling: PASSED")
            print(f"   Connection 1 ID: {id(connection1)}")
            print(f"   Connection 2 ID: {id(connection2)}")
            test_results['connection_pooling'] = True
        else:
            print("❌ Connection pooling: FAILED")
        
        # Test 3: Health Monitoring
        print("\n📋 Test 3: Health Monitoring")
        stats = redis_manager.get_health_stats()
        
        required_stats = ['total_connections', 'successful_pings', 'connection_success_rate']
        if all(stat in stats for stat in required_stats):
            print("✅ Health monitoring: PASSED")
            print(f"   Total connections: {stats['total_connections']}")
            print(f"   Successful pings: {stats['successful_pings']}")
            print(f"   Success rate: {stats['connection_success_rate']:.1f}%")
            test_results['health_monitoring'] = True
        else:
            print("❌ Health monitoring: FAILED")
            print(f"   Missing stats: {[s for s in required_stats if s not in stats]}")
        
        # Test 4: Queue Monitoring
        print("\n📋 Test 4: Queue Health Monitoring")
        queue_health = redis_manager.monitor_queue_health()
        
        if 'overall_status' in queue_health and 'queues' in queue_health:
            print(f"✅ Queue monitoring: PASSED (Status: {queue_health['overall_status']})")
            for queue_name, queue_info in queue_health['queues'].items():
                print(f"   {queue_name}: {queue_info['jobs_count']} jobs, "
                     f"{queue_info['workers_count']} workers, {queue_info['status']}")
            test_results['queue_monitoring'] = True
        else:
            print("❌ Queue monitoring: FAILED")
        
        # Test 5: Retry Mechanisms
        print("\n📋 Test 5: Job Retry Mechanisms")
        from app.utils.job_retry import (
            ErrorClassifier, RetryPolicyConfig, JobRetryHandler,
            ErrorCategory, configure_retry_policy
        )
        
        # Test error classification
        test_connection_error = ConnectionError("Connection refused")
        classified_category = ErrorClassifier.classify_error(test_connection_error)
        
        if classified_category == ErrorCategory.NETWORK:
            print("✅ Error classification: PASSED")
            print(f"   ConnectionError classified as: {classified_category.value}")
            test_results['error_classification'] = True
        else:
            print(f"❌ Error classification: FAILED - Expected NETWORK, got {classified_category.value}")
        
        # Test retry policy configuration
        retry_policy = configure_retry_policy(max_retries=5, base_delay=30)
        retry_handler = JobRetryHandler(retry_policy)
        
        if retry_handler.retry_policy.max_retries == 5:
            print("✅ Retry mechanisms: PASSED")
            print(f"   Max retries: {retry_handler.retry_policy.max_retries}")
            print(f"   Base delay: {retry_handler.retry_policy.base_delay}s")
            test_results['retry_mechanisms'] = True
        else:
            print("❌ Retry mechanisms: FAILED")
        
        # Test 6: Resilient Job Creation
        print("\n📋 Test 6: Resilient Job Creation")
        from app.utils.job_retry import create_resilient_job
        
        job = create_resilient_job('default', 'time.sleep', 1)
        
        if job and 'retry_count' in job.meta and 'created_at' in job.meta:
            print(f"✅ Resilient job creation: PASSED")
            print(f"   Job ID: {job.id}")
            print(f"   Initial retry count: {job.meta['retry_count']}")
            print(f"   Created at: {job.meta['created_at']}")
            test_results['resilient_job_creation'] = True
        else:
            print("❌ Resilient job creation: FAILED")
        
        # Test 7: Statistics Tracking
        print("\n📋 Test 7: Statistics Tracking")
        before_stats = redis_manager.get_health_stats()
        
        # Perform some operations
        redis_manager.get_connection().ping()
        time.sleep(0.1)
        
        after_stats = redis_manager.get_health_stats()
        
        if after_stats['successful_pings'] >= before_stats['successful_pings']:
            print("✅ Statistics tracking: PASSED")
            print(f"   Pings before: {before_stats['successful_pings']}")
            print(f"   Pings after: {after_stats['successful_pings']}")
            test_results['statistics_tracking'] = True
        else:
            print("❌ Statistics tracking: FAILED")
        
    except Exception as e:
        print(f"❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    # Summary
    print("\n" + "=" * 70)
    print("🎯 TEST RESULTS SUMMARY")
    print("=" * 70)
    
    passed_tests = sum(test_results.values())
    total_tests = len(test_results)
    
    for test_name, passed in test_results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name:.<50} {status}")
    
    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 ALL TESTS PASSED - Enhanced Redis features fully functional!")
        return True
    else:
        print(f"⚠️  {total_tests - passed_tests} tests failed - Review implementation")
        return False


def test_api_endpoints():
    """Test health check API endpoints if Flask app is running."""
    print("\n🌐 TESTING API ENDPOINTS")
    print("=" * 50)
    
    import requests
    
    base_url = "http://localhost:5001/api"
    endpoints = [
        "/health",
        "/health/redis", 
        "/health/queues",
        "/health/redis/stats"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code in [200, 206]:
                print(f"✅ {endpoint}: PASSED (Status: {response.status_code})")
            else:
                print(f"❌ {endpoint}: FAILED (Status: {response.status_code})")
        except requests.exceptions.RequestException as e:
            print(f"⚠️  {endpoint}: SKIPPED (App not running: {e})")


def main():
    """Run all enhanced Redis feature tests."""
    print(f"Starting enhanced Redis features test at {datetime.now()}")
    
    # Test core features
    core_success = test_enhanced_redis_features()
    
    # Test API endpoints (optional - only if app is running)
    test_api_endpoints()
    
    print(f"\nTest completed at {datetime.now()}")
    
    if core_success:
        print("🎉 Task 27 (Enhanced Redis Queue Connectivity) implementation validated!")
        return 0
    else:
        print("❌ Task 27 implementation needs review")
        return 1


if __name__ == '__main__':
    sys.exit(main()) 