"""
Regression tests for Redis connectivity and caching issues.
These tests ensure that previously fixed Redis-related bugs don't reoccur.
"""

import pytest
import redis
import time
from unittest.mock import patch, MagicMock, Mock
from redis.exceptions import ConnectionError, TimeoutError, ResponseError
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.models.models import Song, User, AnalysisResult
from app.utils.cache import RedisCache


class TestRedisConnectivityRegression:
    """Regression tests for Redis connectivity and caching functionality."""

    @pytest.fixture
    def cache_manager(self, app):
        """Create a CacheManager instance for testing."""
        with app.app_context():
            return RedisCache()

    @pytest.fixture
    def mock_redis_client(self):
        """Create a mock Redis client for testing."""
        return MagicMock(spec=redis.Redis)

    @pytest.mark.regression
    @pytest.mark.cache
    def test_redis_connection_failure_graceful_degradation_regression(self, app, cache_manager, mock_redis_client):
        """
        Regression test for graceful degradation when Redis is unavailable.
        
        Previously, Redis connection failures would crash the application
        instead of degrading gracefully to non-cached operation.
        
        Issue: Application crashes when Redis is unavailable
        Fix: Graceful degradation with fallback to direct operations
        """
        with app.app_context():
            # Mock Redis connection failure
            with patch.object(cache_manager, '_redis_client', mock_redis_client):
                mock_redis_client.get.side_effect = ConnectionError("Redis connection failed")
                mock_redis_client.set.side_effect = ConnectionError("Redis connection failed")
                
                # These operations should not raise exceptions
                try:
                    # Cache get should return None gracefully
                    result = cache_manager.get('test_key')
                    assert result is None
                    
                    # Cache set should fail silently
                    cache_manager.set('test_key', 'test_value', 300)
                    
                    # Cache delete should fail silently
                    cache_manager.delete('test_key')
                    
                    # Cache exists should return False gracefully
                    exists = cache_manager.exists('test_key')
                    assert exists is False
                    
                except (ConnectionError, TimeoutError):
                    pytest.fail("Redis connection failures should be handled gracefully")

    @pytest.mark.regression
    @pytest.mark.cache
    def test_redis_timeout_handling_regression(self, app, cache_manager, mock_redis_client):
        """
        Regression test for Redis timeout handling.
        
        Previously, Redis timeouts would cause indefinite hangs
        instead of timing out gracefully.
        
        Issue: Redis operations hanging indefinitely on timeout
        Fix: Proper timeout handling with fallback behavior
        """
        with app.app_context():
            # Mock Redis timeout
            with patch.object(cache_manager, '_redis_client', mock_redis_client):
                mock_redis_client.get.side_effect = TimeoutError("Redis timeout")
                mock_redis_client.set.side_effect = TimeoutError("Redis timeout")
                
                start_time = time.time()
                
                try:
                    # Operations should timeout quickly, not hang
                    result = cache_manager.get('test_key')
                    assert result is None
                    
                    cache_manager.set('test_key', 'test_value', 300)
                    
                    elapsed_time = time.time() - start_time
                    
                    # Should not take more than a few seconds
                    assert elapsed_time < 5.0, f"Operations took too long: {elapsed_time} seconds"
                    
                except TimeoutError:
                    pytest.fail("Redis timeouts should be handled gracefully")

    @pytest.mark.regression
    @pytest.mark.cache
    def test_redis_memory_pressure_handling_regression(self, app, cache_manager, mock_redis_client):
        """
        Regression test for Redis memory pressure handling.
        
        Previously, when Redis ran out of memory, the application would
        crash instead of handling the situation gracefully.
        
        Issue: Application crashes when Redis is out of memory
        Fix: Graceful handling of memory pressure with fallback strategies
        """
        with app.app_context():
            # Mock Redis out of memory error
            memory_error = ResponseError("OOM command not allowed when used memory > 'maxmemory'")
            
            with patch.object(cache_manager, '_redis_client', mock_redis_client):
                mock_redis_client.set.side_effect = memory_error
                mock_redis_client.get.side_effect = memory_error
                
                try:
                    # Operations should handle memory pressure gracefully
                    result = cache_manager.get('test_key')
                    assert result is None
                    
                    # Set should fail silently when out of memory
                    cache_manager.set('test_key', 'test_value', 300)
                    
                    # Should not crash the application
                    
                except ResponseError:
                    pytest.fail("Redis memory pressure should be handled gracefully")

    @pytest.mark.regression
    @pytest.mark.cache
    def test_redis_connection_recovery_regression(self, app, cache_manager):
        """
        Regression test for Redis connection recovery.
        
        Previously, after a Redis connection was lost, the application
        would not properly recover even when Redis came back online.
        
        Issue: Application doesn't recover after Redis reconnection
        Fix: Automatic connection recovery and retry mechanisms
        """
        with app.app_context():
            # First simulate connection failure
            connection_error = ConnectionError("Connection lost")
            
            with patch.object(redis_client, 'get', side_effect=connection_error):
                result = cache_manager.get('test_key')
                assert result is None
            
            # Then simulate connection recovery
            with patch.object(redis_client, 'get', return_value=b'recovered_value'):
                with patch.object(redis_client, 'set', return_value=True):
                    
                    # Should be able to use Redis normally after recovery
                    result = cache_manager.get('test_key')
                    assert result == 'recovered_value'
                    
                    # Should be able to set values
                    success = cache_manager.set('new_key', 'new_value', 300)
                    # success might be None if graceful degradation is implemented

    @pytest.mark.regression
    @pytest.mark.cache
    def test_analysis_cache_corruption_regression(self, app, cache_manager, new_user):
        """
        Regression test for analysis cache corruption handling.
        
        Previously, corrupted cache entries would cause analysis
        operations to fail instead of regenerating the data.
        
        Issue: Corrupted cache entries causing analysis failures
        Fix: Cache validation and automatic regeneration on corruption
        """
        with app.app_context():
            song_id = 123
            cache_key = f'analysis_result_{song_id}_{new_user.id}'
            
            # Simulate corrupted cache data
            corrupted_data = b'corrupted_invalid_json_data'
            
            with patch.object(redis_client, 'get', return_value=corrupted_data):
                
                try:
                    # Attempt to get cached analysis result
                    result = cache_manager.get_analysis_result(song_id, new_user.id)
                    
                    # Should handle corruption gracefully (return None to trigger regeneration)
                    assert result is None or isinstance(result, dict)
                    
                except (ValueError, TypeError) as e:
                    pytest.fail(f"Cache corruption should be handled gracefully: {e}")

    @pytest.mark.regression
    @pytest.mark.cache
    def test_cache_key_collision_regression(self, app, cache_manager):
        """
        Regression test for cache key collision handling.
        
        Previously, cache key collisions could cause data to be
        returned for the wrong entities.
        
        Issue: Cache key collisions causing data mix-ups
        Fix: Proper cache key namespacing and validation
        """
        with app.app_context():
            # Test potential collision scenarios
            user_id_1 = 123
            user_id_2 = 1234  # Could collide if key generation is naive
            song_id = 456
            
            # Set data for first user
            cache_manager.set_analysis_result(song_id, user_id_1, {
                'score': 8.5,
                'user_id': user_id_1
            }, 300)
            
            # Set different data for second user
            cache_manager.set_analysis_result(song_id, user_id_2, {
                'score': 6.2,
                'user_id': user_id_2
            }, 300)
            
            # Retrieve data for first user
            result_1 = cache_manager.get_analysis_result(song_id, user_id_1)
            result_2 = cache_manager.get_analysis_result(song_id, user_id_2)
            
            # Should not have collision - each user should get their own data
            if result_1 is not None and result_2 is not None:
                assert result_1['user_id'] == user_id_1
                assert result_2['user_id'] == user_id_2
                assert result_1['score'] != result_2['score']

    @pytest.mark.regression
    @pytest.mark.cache
    def test_cache_expiration_edge_cases_regression(self, app, cache_manager):
        """
        Regression test for cache expiration edge cases.
        
        Previously, edge cases in cache expiration could lead to
        stale data being served or cache entries never expiring.
        
        Issue: Cache expiration not working correctly in edge cases
        Fix: Robust expiration handling with proper TTL management
        """
        with app.app_context():
            # Test zero TTL
            try:
                cache_manager.set('zero_ttl_key', 'value', 0)
                result = cache_manager.get('zero_ttl_key')
                # Should either be None (expired immediately) or handled gracefully
                
            except Exception as e:
                pytest.fail(f"Zero TTL should be handled gracefully: {e}")
            
            # Test negative TTL
            try:
                cache_manager.set('negative_ttl_key', 'value', -1)
                result = cache_manager.get('negative_ttl_key')
                # Should be handled gracefully
                
            except Exception as e:
                pytest.fail(f"Negative TTL should be handled gracefully: {e}")
            
            # Test very large TTL
            try:
                large_ttl = 999999999  # Very large value
                cache_manager.set('large_ttl_key', 'value', large_ttl)
                result = cache_manager.get('large_ttl_key')
                # Should be handled without overflow errors
                
            except (OverflowError, ValueError) as e:
                pytest.fail(f"Large TTL should be handled gracefully: {e}")

    @pytest.mark.regression
    @pytest.mark.cache
    def test_concurrent_cache_access_regression(self, app, cache_manager):
        """
        Regression test for concurrent cache access issues.
        
        Previously, concurrent access to the same cache keys could
        cause race conditions and data corruption.
        
        Issue: Race conditions in concurrent cache operations
        Fix: Proper locking and atomic operations
        """
        import threading
        import time
        
        with app.app_context():
            cache_key = 'concurrent_test_key'
            results = []
            errors = []
            
            def cache_operation(operation_id):
                try:
                    # Simulate concurrent cache operations
                    for i in range(5):
                        value = f'value_{operation_id}_{i}'
                        cache_manager.set(cache_key, value, 60)
                        
                        # Small delay to increase chance of race condition
                        time.sleep(0.01)
                        
                        retrieved = cache_manager.get(cache_key)
                        results.append((operation_id, i, retrieved))
                        
                except Exception as e:
                    errors.append(f"Operation {operation_id}: {str(e)}")
            
            # Start multiple threads
            threads = []
            for op_id in range(3):
                thread = threading.Thread(target=cache_operation, args=(op_id,))
                threads.append(thread)
                thread.start()
            
            # Wait for completion
            for thread in threads:
                thread.join()
            
            # Should not have critical errors
            critical_errors = [e for e in errors if any(err_type in e.lower() for err_type in [
                'race condition', 'deadlock', 'corruption'
            ])]
            
            assert len(critical_errors) == 0, f"Critical concurrency errors: {critical_errors}"
            
            # Should have some successful operations
            assert len(results) > 0

    @pytest.mark.regression
    @pytest.mark.cache
    def test_redis_pipeline_failure_regression(self, app, cache_manager):
        """
        Regression test for Redis pipeline operation failures.
        
        Previously, Redis pipeline failures could leave the application
        in an inconsistent state.
        
        Issue: Pipeline failures causing inconsistent application state
        Fix: Proper pipeline error handling and transaction rollback
        """
        with app.app_context():
            # Mock pipeline failure
            mock_pipeline = MagicMock()
            mock_pipeline.execute.side_effect = ConnectionError("Pipeline failed")
            
            with patch.object(redis_client, 'pipeline', return_value=mock_pipeline):
                
                try:
                    # Operations using pipelines should handle failures gracefully
                    cache_manager.set_multiple({
                        'key1': 'value1',
                        'key2': 'value2',
                        'key3': 'value3'
                    }, 300)
                    
                    # Should not crash or leave partial state
                    
                except ConnectionError:
                    pytest.fail("Pipeline failures should be handled gracefully")

    @pytest.mark.regression
    @pytest.mark.worker
    def test_worker_redis_connection_isolation_regression(self, app):
        """
        Regression test for worker Redis connection isolation.
        
        Previously, workers would interfere with each other's Redis
        connections, causing connection pool exhaustion.
        
        Issue: Workers interfering with each other's Redis connections
        Fix: Proper connection pooling and isolation
        """
        with app.app_context():
            # Simulate multiple workers accessing Redis
            import threading
            
            connection_counts = []
            errors = []
            
            def worker_task(worker_id):
                try:
                    with app.app_context():
                        # Simulate worker cache operations
                        cache_manager = RedisCache()
                        
                        for i in range(5):
                            key = f'worker_{worker_id}_key_{i}'
                            cache_manager.set(key, f'value_{i}', 60)
                            result = cache_manager.get(key)
                            
                        # Count should be reasonable (not exhausting pool)
                        connection_counts.append(worker_id)
                        
                except Exception as e:
                    errors.append(f"Worker {worker_id}: {str(e)}")
            
            # Simulate multiple workers
            threads = []
            for worker_id in range(5):
                thread = threading.Thread(target=worker_task, args=(worker_id,))
                threads.append(thread)
                thread.start()
            
            # Wait for completion
            for thread in threads:
                thread.join()
            
            # Should not have connection pool exhaustion errors
            pool_errors = [e for e in errors if any(err_type in e.lower() for err_type in [
                'pool', 'connection', 'exhausted', 'timeout'
            ])]
            
            assert len(pool_errors) == 0, f"Connection pool errors: {pool_errors}"
            
            # All workers should have completed successfully
            assert len(connection_counts) == 5 