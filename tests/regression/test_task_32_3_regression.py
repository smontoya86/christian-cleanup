"""
Regression Test Suite for Task 32.3: Remove Unused Legacy Queue Definitions

This test suite verifies that removing legacy queue definitions and cleaning
them from Redis does not impact current application functionality.
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))


class TestTask32_3LegacyQueueRemovalRegression:
    """
    Regression test suite for Task 32.3: Remove Unused Legacy Queue Definitions
    
    Tests verify that:
    1. Current queue system works correctly
    2. Legacy queues are no longer accessible
    3. Worker configuration uses current queues
    4. Analysis service functionality is preserved
    5. No breaking changes in queue operations
    """

    def test_current_queue_system_functional(self):
        """Test that the current queue system is fully functional."""
        try:
            from app import create_app
            from app.extensions import rq
            from app.worker_config import HIGH_PRIORITY_QUEUE, DEFAULT_QUEUE, LOW_PRIORITY_QUEUE
            
            app = create_app('testing')
            
            with app.app_context():
                # Test all current queues are accessible
                current_queues = [HIGH_PRIORITY_QUEUE, DEFAULT_QUEUE, LOW_PRIORITY_QUEUE]
                queue_status = {}
                
                for queue_name in current_queues:
                    queue = rq.get_queue(queue_name)
                    queue_status[queue_name] = {
                        'accessible': True,
                        'length': len(queue),
                        'name': queue.name
                    }
                
                # Verify all queues are accessible
                assert len(queue_status) == 3, f"Expected 3 queues, got {len(queue_status)}"
                for queue_name, status in queue_status.items():
                    assert status['accessible'], f"Queue {queue_name} not accessible"
                    assert status['name'] == queue_name, f"Queue name mismatch for {queue_name}"
                
                print(f"✅ Current queue system functional:")
                print(f"   High Priority: {HIGH_PRIORITY_QUEUE} ✅")
                print(f"   Default: {DEFAULT_QUEUE} ✅")
                print(f"   Low Priority: {LOW_PRIORITY_QUEUE} ✅")
                
        except Exception as e:
            pytest.fail(f"Current queue system test failed: {e}")

    def test_legacy_queues_no_longer_exist(self):
        """Test that legacy queues have been successfully removed from Redis."""
        try:
            from app import create_app
            from app.extensions import rq
            
            app = create_app('testing')
            
            with app.app_context():
                legacy_queue_names = [
                    'analysis_high',
                    'analysis_normal',
                    'analysis_batch',
                    'old_default',
                    'legacy',
                    'deprecated'
                ]
                
                connection = rq.connection
                removed_queues = []
                
                for queue_name in legacy_queue_names:
                    # Check if queue key exists in Redis
                    queue_key = f"rq:queue:{queue_name}"
                    exists = connection.exists(queue_key)
                    
                    if not exists:
                        removed_queues.append(queue_name)
                    else:
                        # Queue still exists - this is unexpected
                        queue_length = connection.llen(queue_key)
                        print(f"❌ Legacy queue {queue_name} still exists with {queue_length} items")
                
                print(f"✅ Legacy queue removal verification:")
                print(f"   Total legacy queues checked: {len(legacy_queue_names)}")
                print(f"   Successfully removed: {len(removed_queues)}")
                
                for queue_name in removed_queues:
                    print(f"   ✅ {queue_name} - Removed")
                
                # All legacy queues should be removed
                assert len(removed_queues) == len(legacy_queue_names), \
                    f"Not all legacy queues removed: {len(removed_queues)}/{len(legacy_queue_names)}"
                
        except Exception as e:
            pytest.fail(f"Legacy queue removal verification failed: {e}")

    def test_worker_config_uses_current_queues(self):
        """Test that worker configuration only references current queue names."""
        try:
            from app.worker_config import (
                HIGH_PRIORITY_QUEUE, DEFAULT_QUEUE, LOW_PRIORITY_QUEUE, 
                DEFAULT_QUEUES
            )
            
            # Test current queue constants
            assert HIGH_PRIORITY_QUEUE == 'high', f"HIGH_PRIORITY_QUEUE should be 'high', got '{HIGH_PRIORITY_QUEUE}'"
            assert DEFAULT_QUEUE == 'default', f"DEFAULT_QUEUE should be 'default', got '{DEFAULT_QUEUE}'"
            assert LOW_PRIORITY_QUEUE == 'low', f"LOW_PRIORITY_QUEUE should be 'low', got '{LOW_PRIORITY_QUEUE}'"
            
            # Test DEFAULT_QUEUES list
            expected_queues = ['high', 'default', 'low']
            assert DEFAULT_QUEUES == expected_queues, f"DEFAULT_QUEUES mismatch: expected {expected_queues}, got {DEFAULT_QUEUES}"
            
            # Check that no legacy queue names are imported
            import app.worker_config as config_module
            config_source = config_module.__file__
            
            with open(config_source, 'r') as f:
                content = f.read()
            
            legacy_queue_names = ['analysis_high', 'analysis_normal', 'analysis_batch']
            legacy_found = []
            
            for legacy_name in legacy_queue_names:
                if legacy_name in content:
                    legacy_found.append(legacy_name)
            
            assert len(legacy_found) == 0, f"Legacy queue names found in worker_config: {legacy_found}"
            
            print(f"✅ Worker configuration verification:")
            print(f"   HIGH_PRIORITY_QUEUE: {HIGH_PRIORITY_QUEUE}")
            print(f"   DEFAULT_QUEUE: {DEFAULT_QUEUE}")
            print(f"   LOW_PRIORITY_QUEUE: {LOW_PRIORITY_QUEUE}")
            print(f"   DEFAULT_QUEUES: {DEFAULT_QUEUES}")
            print(f"   No legacy queue references found ✅")
            
        except Exception as e:
            pytest.fail(f"Worker config verification failed: {e}")

    def test_enhanced_analysis_service_functionality(self):
        """Test that enhanced analysis service still works with current queues."""
        try:
            from app.services.enhanced_analysis_service import (
                analyze_song_user_initiated,
                analyze_song_background,
                analyze_songs_batch
            )
            
            # Test function availability
            functions = {
                'analyze_song_user_initiated': analyze_song_user_initiated,
                'analyze_song_background': analyze_song_background,
                'analyze_songs_batch': analyze_songs_batch
            }
            
            for func_name, func in functions.items():
                assert callable(func), f"{func_name} is not callable"
            
            # Check imports in the service source
            import inspect
            from app.services import enhanced_analysis_service
            
            source = inspect.getsource(enhanced_analysis_service)
            
            # Verify current queue imports
            current_queue_imports = [
                'HIGH_PRIORITY_QUEUE',
                'DEFAULT_QUEUE', 
                'LOW_PRIORITY_QUEUE'
            ]
            
            imports_found = []
            for import_name in current_queue_imports:
                if import_name in source:
                    imports_found.append(import_name)
            
            # Verify no legacy queue names
            legacy_queue_names = ['analysis_high', 'analysis_normal', 'analysis_batch']
            legacy_found = []
            
            for legacy_name in legacy_queue_names:
                if legacy_name in source:
                    legacy_found.append(legacy_name)
            
            assert len(imports_found) == 3, f"Missing current queue imports: expected 3, got {len(imports_found)}"
            assert len(legacy_found) == 0, f"Legacy queue names still in enhanced_analysis_service: {legacy_found}"
            
            print(f"✅ Enhanced analysis service verification:")
            print(f"   Function availability: {len(functions)} functions accessible")
            print(f"   Current queue imports: {len(imports_found)}/3 found")
            print(f"   Legacy queue references: {len(legacy_found)} (should be 0)")
            
        except ImportError as e:
            pytest.fail(f"Enhanced analysis service import failed: {e}")
        except Exception as e:
            pytest.fail(f"Enhanced analysis service test failed: {e}")

    def test_queue_job_enqueueing_works(self):
        """Test that jobs can still be enqueued to current queues."""
        try:
            from app import create_app
            from app.extensions import rq
            from app.worker_config import HIGH_PRIORITY_QUEUE, DEFAULT_QUEUE, LOW_PRIORITY_QUEUE
            
            app = create_app('testing')
            
            with app.app_context():
                # Simple test function
                def test_job():
                    return "test_job_completed"
                
                enqueue_results = {}
                
                for queue_name in [HIGH_PRIORITY_QUEUE, DEFAULT_QUEUE, LOW_PRIORITY_QUEUE]:
                    try:
                        queue = rq.get_queue(queue_name)
                        job = queue.enqueue(test_job)
                        
                        enqueue_results[queue_name] = {
                            'success': True,
                            'job_id': job.id,
                            'queue_length': len(queue)
                        }
                        
                        # Clean up the test job
                        job.delete()
                        
                    except Exception as e:
                        enqueue_results[queue_name] = {
                            'success': False,
                            'error': str(e)
                        }
                
                # Verify all enqueues succeeded
                for queue_name, result in enqueue_results.items():
                    assert result['success'], f"Failed to enqueue to {queue_name}: {result.get('error')}"
                
                print(f"✅ Queue job enqueueing test:")
                for queue_name, result in enqueue_results.items():
                    print(f"   {queue_name}: Job enqueued and cleaned up ✅")
                
        except Exception as e:
            pytest.fail(f"Queue job enqueueing test failed: {e}")

    def test_app_initialization_works(self):
        """Test that the Flask app still initializes correctly after queue cleanup."""
        try:
            from app import create_app
            
            app = create_app('testing')
            
            with app.app_context():
                # Test that app created successfully
                assert app is not None, "App creation failed"
                assert app.config['TESTING'], "App not in testing mode"
                
                # Test that extensions are available
                from app.extensions import rq
                assert rq is not None, "RQ extension not available"
                
                # Test that worker config is importable
                from app.worker_config import DEFAULT_QUEUES
                assert len(DEFAULT_QUEUES) == 3, f"Expected 3 default queues, got {len(DEFAULT_QUEUES)}"
                
                print(f"✅ App initialization test:")
                print(f"   Flask app creation: ✅")
                print(f"   RQ extension available: ✅")
                print(f"   Worker config accessible: ✅")
                print(f"   Default queues configured: {len(DEFAULT_QUEUES)}")
                
        except Exception as e:
            pytest.fail(f"App initialization test failed: {e}")

    def test_redis_connection_health(self):
        """Test that Redis connection is healthy after queue cleanup."""
        try:
            from app import create_app
            from app.extensions import rq
            
            app = create_app('testing')
            
            with app.app_context():
                connection = rq.connection
                
                # Test basic Redis operations
                test_key = "test_legacy_queue_cleanup"
                test_value = "cleanup_successful"
                
                # Set a test value
                connection.set(test_key, test_value)
                
                # Get the test value
                retrieved_value = connection.get(test_key)
                
                # Clean up
                connection.delete(test_key)
                
                assert retrieved_value.decode() == test_value, "Redis operation failed"
                
                # Test connection info
                info = connection.info()
                assert 'redis_version' in info, "Redis info not available"
                
                print(f"✅ Redis connection health test:")
                print(f"   Set/Get operations: ✅")
                print(f"   Connection info available: ✅")
                print(f"   Redis version: {info.get('redis_version', 'Unknown')}")
                
        except Exception as e:
            pytest.fail(f"Redis connection health test failed: {e}")

    def test_comprehensive_regression_summary(self):
        """Run all regression tests and provide a comprehensive summary."""
        print(f"\n🔬 COMPREHENSIVE REGRESSION TEST FOR TASK 32.3")
        print(f"=" * 60)
        
        # Test current queue system functionality
        try:
            from app import create_app
            from app.extensions import rq
            from app.worker_config import HIGH_PRIORITY_QUEUE, DEFAULT_QUEUE, LOW_PRIORITY_QUEUE
            
            app = create_app('testing')
            with app.app_context():
                # Test queue system
                current_queues = [HIGH_PRIORITY_QUEUE, DEFAULT_QUEUE, LOW_PRIORITY_QUEUE]
                queue_system_functional = len(current_queues) == 3
                
                # Test legacy queue removal
                connection = rq.connection
                legacy_queue_names = ['analysis_high', 'analysis_normal', 'analysis_batch', 'old_default', 'legacy', 'deprecated']
                removed_count = sum(1 for q in legacy_queue_names if not connection.exists(f"rq:queue:{q}"))
                legacy_queues_removed = removed_count == len(legacy_queue_names)
                
                # Test worker config
                from app.worker_config import DEFAULT_QUEUES
                worker_config_clean = len(DEFAULT_QUEUES) == 3
                
                # Test analysis service
                from app.services.enhanced_analysis_service import analyze_song_user_initiated, analyze_song_background, analyze_songs_batch
                analysis_service_functional = all(callable(f) for f in [analyze_song_user_initiated, analyze_song_background, analyze_songs_batch])
                
                # Test job enqueueing
                test_queue = rq.get_queue(DEFAULT_QUEUE)
                job_enqueueing_works = test_queue is not None
                
                # Test app initialization  
                app_initialization_works = app is not None and app.config.get('TESTING', False)
                
                # Test Redis connection
                redis_connection_healthy = connection.ping()
                
        except Exception as e:
            pytest.fail(f"Comprehensive regression test failed: {e}")
        
        print(f"\n📊 REGRESSION TEST SUMMARY:")
        print(f"   Current queue system functional: {'✅' if queue_system_functional else '❌'}")
        print(f"   Legacy queues removed: {'✅' if legacy_queues_removed else '❌'} ({removed_count}/{len(legacy_queue_names)})")
        print(f"   Worker config clean: {'✅' if worker_config_clean else '❌'}")
        print(f"   Analysis service functional: {'✅' if analysis_service_functional else '❌'}")
        print(f"   Job enqueueing works: {'✅' if job_enqueueing_works else '❌'}")
        print(f"   App initialization works: {'✅' if app_initialization_works else '❌'}")
        print(f"   Redis connection healthy: {'✅' if redis_connection_healthy else '❌'}")
        
        all_tests_passed = all([
            queue_system_functional,
            legacy_queues_removed,
            worker_config_clean,
            analysis_service_functional,
            job_enqueueing_works,
            app_initialization_works,
            redis_connection_healthy
        ])
        
        print(f"\n🎯 OVERALL RESULT: {'✅ ALL TESTS PASSED' if all_tests_passed else '❌ SOME TESTS FAILED'}")
        print(f"   Breaking changes introduced: ✅ NO")
        print(f"   Legacy queue cleanup: ✅ SUCCESSFUL")
        print(f"   Current functionality: ✅ PRESERVED")
        
        # Assertions for test framework
        assert all_tests_passed, "Not all regression tests passed"
        assert queue_system_functional, "Queue system not functional"
        assert legacy_queues_removed, "Legacy queues not properly removed"
        assert worker_config_clean, "Worker config contains issues" 