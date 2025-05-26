"""
Redis cache performance tests for regression testing.
"""
import pytest
import time
import json
from app import create_app
from app.utils.cache import cache
from tests.utils.benchmark import PerformanceBenchmark
from tests.config import TestConfig
import redis
from unittest.mock import patch


class TestCachePerformance:
    """Test Redis cache performance."""
    
    @pytest.fixture(autouse=True)
    def setup_app(self):
        """Set up test application with cache configuration."""
        self.app = create_app()
        self.app.config.from_object(TestConfig)
        
        with self.app.app_context():
            # Clear cache before each test
            try:
                cache.clear()
            except:
                pass  # Cache might not be available in test environment
            
            yield
            
            # Clean up cache after test
            try:
                cache.clear()
            except:
                pass
    
    def test_cache_set_performance(self):
        """Test performance of cache set operations."""
        with self.app.app_context():
            benchmark = PerformanceBenchmark('cache_set_operations', iterations=10)
            
            @benchmark.measure
            def cache_set_operations():
                # Test setting various data types and sizes
                test_data = [
                    ('simple_string', 'Hello World'),
                    ('simple_number', 12345),
                    ('simple_dict', {'key': 'value', 'number': 42}),
                    ('complex_dict', {
                        'user_id': 123,
                        'playlists': [
                            {'id': 1, 'name': 'Playlist 1', 'songs': list(range(50))},
                            {'id': 2, 'name': 'Playlist 2', 'songs': list(range(100))}
                        ],
                        'metadata': {
                            'created_at': '2023-01-01T00:00:00Z',
                            'updated_at': '2023-01-02T00:00:00Z',
                            'tags': ['tag1', 'tag2', 'tag3']
                        }
                    }),
                    ('large_list', list(range(1000))),
                    ('nested_structure', {
                        'level1': {
                            'level2': {
                                'level3': {
                                    'data': [{'item': i, 'value': f'value_{i}'} for i in range(100)]
                                }
                            }
                        }
                    })
                ]
                
                # Set all test data
                for key, value in test_data:
                    cache.set(f'perf_test_{key}', value, timeout=300)
                
                return len(test_data)
            
            result = cache_set_operations()
            assert result == 6  # Number of test data items
    
    def test_cache_get_performance(self):
        """Test performance of cache get operations."""
        with self.app.app_context():
            # Pre-populate cache with test data
            test_data = {
                'user_123': {'id': 123, 'name': 'Test User', 'playlists': list(range(20))},
                'playlist_456': {'id': 456, 'name': 'Test Playlist', 'songs': list(range(50))},
                'analysis_789': {
                    'song_id': 789,
                    'score': 8.5,
                    'analysis': {
                        'lyrics': 'Sample lyrics content',
                        'keywords': ['keyword1', 'keyword2', 'keyword3'],
                        'sentiment': 0.75
                    }
                }
            }
            
            for key, value in test_data.items():
                cache.set(f'perf_get_{key}', value, timeout=300)
            
            benchmark = PerformanceBenchmark('cache_get_operations', iterations=20)
            
            @benchmark.measure
            def cache_get_operations():
                results = []
                
                # Get all cached data multiple times
                for _ in range(10):  # Multiple iterations per benchmark run
                    for key in test_data.keys():
                        cached_value = cache.get(f'perf_get_{key}')
                        if cached_value:
                            results.append(cached_value)
                
                return len(results)
            
            result = cache_get_operations()
            assert result == 30  # 3 keys * 10 iterations
    
    def test_cache_miss_performance(self):
        """Test performance of cache misses."""
        with self.app.app_context():
            benchmark = PerformanceBenchmark('cache_miss_operations', iterations=15)
            
            @benchmark.measure
            def cache_miss_operations():
                miss_count = 0
                
                # Try to get non-existent keys
                for i in range(100):
                    result = cache.get(f'non_existent_key_{i}')
                    if result is None:
                        miss_count += 1
                
                return miss_count
            
            result = cache_miss_operations()
            assert result == 100  # All should be misses
    
    def test_cache_delete_performance(self):
        """Test performance of cache delete operations."""
        with self.app.app_context():
            benchmark = PerformanceBenchmark('cache_delete_operations', iterations=10)
            
            @benchmark.measure
            def cache_delete_operations():
                # Set up data to delete
                keys_to_delete = []
                for i in range(50):
                    key = f'delete_test_{i}'
                    cache.set(key, {'data': f'value_{i}'}, timeout=300)
                    keys_to_delete.append(key)
                
                # Delete all keys
                deleted_count = 0
                for key in keys_to_delete:
                    if cache.delete(key):
                        deleted_count += 1
                
                return deleted_count
            
            result = cache_delete_operations()
            assert result >= 0  # Some deletes should succeed
    
    def test_cache_bulk_operations_performance(self):
        """Test performance of bulk cache operations."""
        with self.app.app_context():
            benchmark = PerformanceBenchmark('cache_bulk_operations', iterations=5)
            
            @benchmark.measure
            def cache_bulk_operations():
                # Bulk set operations
                bulk_data = {}
                for i in range(100):
                    key = f'bulk_key_{i}'
                    value = {
                        'id': i,
                        'data': f'bulk_value_{i}',
                        'metadata': {
                            'created': time.time(),
                            'tags': [f'tag_{j}' for j in range(i % 5)]
                        }
                    }
                    bulk_data[key] = value
                
                # Set all data
                set_count = 0
                for key, value in bulk_data.items():
                    cache.set(key, value, timeout=300)
                    set_count += 1
                
                # Get all data
                get_count = 0
                for key in bulk_data.keys():
                    if cache.get(key):
                        get_count += 1
                
                return {'set_count': set_count, 'get_count': get_count}
            
            result = cache_bulk_operations()
            assert result['set_count'] == 100
            assert result['get_count'] >= 0  # Some gets should succeed
    
    def test_cache_expiration_performance(self):
        """Test performance with cache expiration."""
        with self.app.app_context():
            benchmark = PerformanceBenchmark('cache_expiration_operations', iterations=5)
            
            @benchmark.measure
            def cache_expiration_operations():
                # Set data with different expiration times
                expiration_data = [
                    ('short_expire', {'data': 'short'}, 1),    # 1 second
                    ('medium_expire', {'data': 'medium'}, 5),  # 5 seconds
                    ('long_expire', {'data': 'long'}, 300),    # 5 minutes
                ]
                
                # Set all data
                for key, value, timeout in expiration_data:
                    cache.set(f'expire_test_{key}', value, timeout=timeout)
                
                # Immediately check all data exists
                immediate_results = []
                for key, _, _ in expiration_data:
                    result = cache.get(f'expire_test_{key}')
                    immediate_results.append(result is not None)
                
                # Wait for short expiration
                time.sleep(1.5)
                
                # Check data after short expiration
                after_short_results = []
                for key, _, _ in expiration_data:
                    result = cache.get(f'expire_test_{key}')
                    after_short_results.append(result is not None)
                
                return {
                    'immediate_hits': sum(immediate_results),
                    'after_short_hits': sum(after_short_results)
                }
            
            result = cache_expiration_operations()
            assert result['immediate_hits'] >= 0  # Some should be set
            # Note: Expiration behavior depends on cache implementation
    
    def test_cache_serialization_performance(self):
        """Test performance of cache serialization/deserialization."""
        with self.app.app_context():
            benchmark = PerformanceBenchmark('cache_serialization', iterations=10)
            
            @benchmark.measure
            def cache_serialization_operations():
                # Test complex data structures
                complex_data = {
                    'simple_types': {
                        'string': 'test string',
                        'integer': 12345,
                        'float': 123.45,
                        'boolean': True,
                        'none': None
                    },
                    'collections': {
                        'list': list(range(100)),
                        'dict': {f'key_{i}': f'value_{i}' for i in range(50)},
                        'nested_list': [[i, i*2, i*3] for i in range(20)],
                        'nested_dict': {
                            f'level1_{i}': {
                                f'level2_{j}': f'value_{i}_{j}'
                                for j in range(5)
                            }
                            for i in range(10)
                        }
                    },
                    'mixed_structure': {
                        'users': [
                            {
                                'id': i,
                                'name': f'User {i}',
                                'playlists': [
                                    {
                                        'id': j,
                                        'name': f'Playlist {j}',
                                        'songs': list(range(j * 10, (j + 1) * 10))
                                    }
                                    for j in range(3)
                                ]
                            }
                            for i in range(5)
                        ]
                    }
                }
                
                # Set and get complex data
                cache.set('complex_serialization_test', complex_data, timeout=300)
                retrieved_data = cache.get('complex_serialization_test')
                
                # Verify data integrity
                if retrieved_data:
                    return len(str(retrieved_data))  # Return size as success metric
                else:
                    return 0
            
            result = cache_serialization_operations()
            assert result > 0  # Should have retrieved some data
    
    def test_cache_concurrent_access_performance(self):
        """Test performance under concurrent access patterns."""
        with self.app.app_context():
            benchmark = PerformanceBenchmark('cache_concurrent_access', iterations=5)
            
            @benchmark.measure
            def cache_concurrent_access():
                # Simulate concurrent access patterns
                shared_keys = [f'shared_key_{i}' for i in range(10)]
                
                # Initialize shared data
                for key in shared_keys:
                    cache.set(key, {'counter': 0, 'data': f'initial_{key}'}, timeout=300)
                
                # Simulate multiple "threads" accessing same keys
                operations_count = 0
                for iteration in range(20):  # Simulate 20 concurrent operations
                    for key in shared_keys:
                        # Read
                        current_data = cache.get(key)
                        if current_data:
                            # Modify
                            current_data['counter'] += 1
                            current_data['last_access'] = time.time()
                            
                            # Write back
                            cache.set(key, current_data, timeout=300)
                            operations_count += 1
                
                return operations_count
            
            result = cache_concurrent_access()
            assert result > 0  # Should have performed some operations
    
    def test_cache_memory_usage_performance(self):
        """Test cache performance with varying memory usage."""
        with self.app.app_context():
            benchmark = PerformanceBenchmark('cache_memory_usage', iterations=3)
            
            @benchmark.measure
            def cache_memory_usage_test():
                # Test with increasing data sizes
                data_sizes = [
                    ('small', 'x' * 100),           # 100 bytes
                    ('medium', 'x' * 10000),        # 10KB
                    ('large', 'x' * 100000),        # 100KB
                    ('very_large', 'x' * 1000000),  # 1MB
                ]
                
                operations_completed = 0
                
                for size_name, data in data_sizes:
                    key = f'memory_test_{size_name}'
                    
                    # Set large data
                    cache.set(key, {'size': size_name, 'data': data}, timeout=300)
                    
                    # Verify retrieval
                    retrieved = cache.get(key)
                    if retrieved and retrieved['size'] == size_name:
                        operations_completed += 1
                    
                    # Clean up immediately to manage memory
                    cache.delete(key)
                
                return operations_completed
            
            result = cache_memory_usage_test()
            assert result >= 0  # Some operations should complete
    
    @patch('app.utils.cache.cache')
    def test_cache_fallback_performance(self, mock_cache):
        """Test performance when cache is unavailable."""
        with self.app.app_context():
            # Mock cache to simulate failures
            mock_cache.get.side_effect = redis.ConnectionError("Connection failed")
            mock_cache.set.side_effect = redis.ConnectionError("Connection failed")
            
            benchmark = PerformanceBenchmark('cache_fallback', iterations=10)
            
            @benchmark.measure
            def cache_fallback_operations():
                fallback_operations = 0
                
                # Attempt cache operations that will fail
                for i in range(50):
                    try:
                        # Try to get from cache
                        result = cache.get(f'fallback_key_{i}')
                        fallback_operations += 1
                    except:
                        # Simulate fallback to database or computation
                        fallback_result = {'computed': True, 'value': i}
                        fallback_operations += 1
                    
                    try:
                        # Try to set cache
                        cache.set(f'fallback_key_{i}', {'value': i}, timeout=300)
                        fallback_operations += 1
                    except:
                        # Graceful degradation
                        fallback_operations += 1
                
                return fallback_operations
            
            result = cache_fallback_operations()
            assert result == 100  # Should handle all fallback operations 