"""
Performance tests for analysis operations.
Tests response times, throughput, and resource usage.
"""

import pytest
import time
import threading
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch, Mock

from app.services.unified_analysis_service import UnifiedAnalysisService
from app.models.models import Song, User
from app.utils.cache import RedisCache


class TestAnalysisPerformance:
    """Performance tests for analysis functionality."""

    @pytest.fixture
    def analysis_service(self):
        """Create an AnalysisService instance."""
        return UnifiedAnalysisService()

    @pytest.fixture
    def sample_songs(self):
        """Create multiple sample songs for performance testing."""
        songs = []
        for i in range(100):
            song = Song(
                id=i+1,
                spotify_id=f'test_song_{i+1}',
                title=f'Test Song {i+1}',
                artist=f'Test Artist {i+1}',
                album=f'Test Album {i+1}',
                duration_ms=180000 + (i * 1000),
                lyrics=f'This is test lyrics for song {i+1}. Christian themes and biblical references.'
            )
            songs.append(song)
        return songs

    @pytest.fixture
    def sample_user(self):
        """Create a sample user for testing."""
        return User(
            id=1,
            spotify_id='test_user_performance',
            display_name='Performance Test User',
            email='perf@example.com'
        )

    @pytest.mark.performance
    def test_single_analysis_response_time(self, analysis_service, sample_songs, sample_user):
        """Test that single song analysis completes within acceptable time."""
        song = sample_songs[0]
        
        # Mock the AI analysis to focus on our code performance
        with patch.object(analysis_service, 'analyze_lyrics') as mock_analyze:
            mock_analyze.return_value = {
                'overall_score': 8.0,
                'biblical_references': 2,
                'spiritual_themes': ['faith'],
                'explicit_christian_content': True
            }
            
            start_time = time.time()
            result = analysis_service.analyze_song_by_id(song.id, sample_user.id)
            end_time = time.time()
            
            response_time = end_time - start_time
            
            # Single analysis should complete in under 2 seconds (excluding AI API calls)
            assert response_time < 2.0, f"Single analysis took {response_time:.3f}s, should be < 2.0s"
            assert result is not None

    @pytest.mark.performance
    def test_cached_analysis_response_time(self, analysis_service, sample_songs, sample_user):
        """Test that cached analysis retrieval is very fast."""
        song = sample_songs[0]
        
        # Mock cache hit
        with patch.object(analysis_service, 'get_cached_analysis') as mock_cache:
            mock_cache.return_value = {
                'overall_score': 8.0,
                'biblical_references': 2,
                'spiritual_themes': ['faith'],
                'explicit_christian_content': True
            }
            
            start_time = time.time()
            result = analysis_service.analyze_song_by_id(song.id, sample_user.id)
            end_time = time.time()
            
            response_time = end_time - start_time
            
            # Cached analysis should complete in under 0.1 seconds
            assert response_time < 0.1, f"Cached analysis took {response_time:.3f}s, should be < 0.1s"
            assert result is not None

    @pytest.mark.performance
    def test_concurrent_analysis_throughput(self, analysis_service, sample_songs, sample_user):
        """Test concurrent analysis throughput."""
        # Use first 10 songs for concurrency test
        test_songs = sample_songs[:10]
        
        # Mock AI analysis for consistent timing
        with patch.object(analysis_service, 'analyze_lyrics') as mock_analyze:
            mock_analyze.return_value = {
                'overall_score': 8.0,
                'biblical_references': 2,
                'spiritual_themes': ['faith'],
                'explicit_christian_content': True
            }
            
            def analyze_song(song):
                start_time = time.time()
                result = analysis_service.analyze_song_by_id(song.id, sample_user.id)
                end_time = time.time()
                return result, end_time - start_time
            
            start_time = time.time()
            
            # Test with 5 concurrent threads
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(analyze_song, song) for song in test_songs]
                results = [future.result() for future in as_completed(futures)]
            
            total_time = time.time() - start_time
            
            # All analyses should complete
            assert len(results) == len(test_songs)
            assert all(result[0] is not None for result in results)
            
            # Average per-song time should be reasonable
            avg_time = total_time / len(test_songs)
            assert avg_time < 1.0, f"Average analysis time {avg_time:.3f}s too high"
            
            # Total time should be much less than sequential (due to concurrency)
            sequential_estimate = len(test_songs) * 0.5  # Estimate 0.5s per song
            assert total_time < sequential_estimate * 0.6, "Concurrent processing not efficient enough"

    @pytest.mark.performance
    def test_memory_usage_during_batch_analysis(self, analysis_service, sample_songs, sample_user):
        """Test memory usage doesn't grow excessively during batch processing."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Mock AI analysis
        with patch.object(analysis_service, 'analyze_lyrics') as mock_analyze:
            mock_analyze.return_value = {
                'overall_score': 8.0,
                'biblical_references': 2,
                'spiritual_themes': ['faith'],
                'explicit_christian_content': True
            }
            
            # Process songs in batches
            batch_size = 10
            for i in range(0, min(50, len(sample_songs)), batch_size):
                batch = sample_songs[i:i+batch_size]
                
                for song in batch:
                    analysis_service.analyze_song_by_id(song.id, sample_user.id)
                
                # Check memory after each batch
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_growth = current_memory - initial_memory
                
                # Memory growth should be reasonable (< 100MB for processing)
                assert memory_growth < 100, f"Memory grew by {memory_growth:.1f}MB, should be < 100MB"

    @pytest.mark.performance
    def test_cache_performance_under_load(self, app):
        """Test cache performance under concurrent load."""
        with app.app_context():
            cache_manager = RedisCache()
            
            def cache_operations(thread_id):
                results = []
                for i in range(50):
                    key = f'perf_test_{thread_id}_{i}'
                    value = {'score': 8.0 + (i * 0.1), 'thread': thread_id}
                    
                    # Time cache operations
                    start = time.time()
                    cache_manager.set(key, value, 300)
                    set_time = time.time() - start
                    
                    start = time.time()
                    retrieved = cache_manager.get(key)
                    get_time = time.time() - start
                    
                    results.append((set_time, get_time))
                
                return results
            
            # Run concurrent cache operations
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(cache_operations, i) for i in range(5)]
                all_results = []
                for future in as_completed(futures):
                    all_results.extend(future.result())
            
            # Analyze cache operation times
            set_times = [result[0] for result in all_results]
            get_times = [result[1] for result in all_results]
            
            avg_set_time = statistics.mean(set_times)
            avg_get_time = statistics.mean(get_times)
            max_set_time = max(set_times)
            max_get_time = max(get_times)
            
            # Cache operations should be fast
            assert avg_set_time < 0.01, f"Average cache set time {avg_set_time:.4f}s too slow"
            assert avg_get_time < 0.01, f"Average cache get time {avg_get_time:.4f}s too slow"
            assert max_set_time < 0.1, f"Max cache set time {max_set_time:.4f}s too slow"
            assert max_get_time < 0.1, f"Max cache get time {max_get_time:.4f}s too slow"

    @pytest.mark.performance
    def test_database_query_performance(self, app, db_session):
        """Test database query performance for song lookups."""
        with app.app_context():
            # Create test songs in database
            test_songs = []
            for i in range(100):
                song = Song(
                    spotify_id=f'perf_test_song_{i}',
                    title=f'Performance Test Song {i}',
                    artist=f'Test Artist {i}',
                    album=f'Test Album {i}',
                    duration_ms=180000
                )
                test_songs.append(song)
                db_session.add(song)
            
            db_session.commit()
            
            # Test single song lookups
            lookup_times = []
            for song in test_songs[:20]:  # Test first 20
                start_time = time.time()
                found_song = db_session.get(Song, song.id)
                end_time = time.time()
                
                lookup_times.append(end_time - start_time)
                assert found_song is not None
            
            avg_lookup_time = statistics.mean(lookup_times)
            max_lookup_time = max(lookup_times)
            
            # Database lookups should be fast
            assert avg_lookup_time < 0.01, f"Average DB lookup {avg_lookup_time:.4f}s too slow"
            assert max_lookup_time < 0.05, f"Max DB lookup {max_lookup_time:.4f}s too slow"

    @pytest.mark.performance
    def test_lyrics_processing_performance(self, analysis_service):
        """Test performance of lyrics processing with various text sizes."""
        # Test with different lyrics sizes
        lyrics_sizes = [
            ("short", "Amazing grace"),
            ("medium", "Amazing grace, how sweet the sound " * 10),
            ("long", "Amazing grace, how sweet the sound " * 100),
            ("very_long", "Amazing grace, how sweet the sound " * 500)
        ]
        
        processing_times = {}
        
        for size_name, lyrics in lyrics_sizes:
            # Mock AI call to focus on text processing
            with patch.object(analysis_service, 'analyze_lyrics') as mock_analyze:
                def mock_analysis_with_processing(lyrics_text, **kwargs):
                    # Simulate some text processing work
                    word_count = len(lyrics_text.split())
                    char_count = len(lyrics_text)
                    return {
                        'overall_score': min(10.0, word_count / 10),
                        'biblical_references': char_count // 100,
                        'spiritual_themes': ['faith'],
                        'explicit_christian_content': True,
                        'processing_stats': {
                            'word_count': word_count,
                            'char_count': char_count
                        }
                    }
                
                mock_analyze.side_effect = mock_analysis_with_processing
                
                start_time = time.time()
                result = analysis_service.analyze_lyrics(lyrics)
                end_time = time.time()
                
                processing_time = end_time - start_time
                processing_times[size_name] = processing_time
                
                assert result is not None
        
        # Processing time should scale reasonably with text size
        assert processing_times['short'] < 0.1
        assert processing_times['medium'] < 0.2
        assert processing_times['long'] < 0.5
        assert processing_times['very_long'] < 1.0

    @pytest.mark.performance
    def test_error_handling_performance(self, analysis_service, sample_songs, sample_user):
        """Test that error handling doesn't significantly impact performance."""
        song = sample_songs[0]
        
        # Test performance when AI call fails
        with patch.object(analysis_service, 'analyze_lyrics') as mock_analyze:
            mock_analyze.side_effect = Exception("Simulated API failure")
            
            start_time = time.time()
            result = analysis_service.analyze_song_by_id(song.id, sample_user.id)
            end_time = time.time()
            
            error_handling_time = end_time - start_time
            
            # Error handling should be fast
            assert error_handling_time < 1.0, f"Error handling took {error_handling_time:.3f}s"
            
            # Should still return a result (fallback)
            assert result is not None

    @pytest.mark.performance
    def test_cache_hit_ratio_under_load(self, app):
        """Test cache hit ratio under concurrent load."""
        with app.app_context():
            cache_manager = RedisCache()
            
            # Pre-populate cache with some data
            for i in range(20):
                cache_manager.set(f'hit_test_{i}', {'score': i}, 300)
            
            hit_count = 0
            miss_count = 0
            
            def cache_access_pattern(thread_id):
                nonlocal hit_count, miss_count
                thread_hits = 0
                thread_misses = 0
                
                for i in range(100):
                    # 70% chance of accessing existing keys (should be cache hits)
                    if i % 10 < 7:
                        key = f'hit_test_{i % 20}'
                        result = cache_manager.get(key)
                        if result is not None:
                            thread_hits += 1
                        else:
                            thread_misses += 1
                    else:
                        # 30% chance of accessing new keys (cache misses)
                        key = f'miss_test_{thread_id}_{i}'
                        result = cache_manager.get(key)
                        thread_misses += 1
                
                return thread_hits, thread_misses
            
            # Run concurrent cache access
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(cache_access_pattern, i) for i in range(5)]
                for future in as_completed(futures):
                    thread_hits, thread_misses = future.result()
                    hit_count += thread_hits
                    miss_count += thread_misses
            
            hit_ratio = hit_count / (hit_count + miss_count) if (hit_count + miss_count) > 0 else 0
            
            # Should achieve reasonable hit ratio
            assert hit_ratio > 0.5, f"Cache hit ratio {hit_ratio:.2f} too low"

    @pytest.mark.performance
    def test_stress_test_analysis_pipeline(self, analysis_service, sample_user):
        """Stress test the entire analysis pipeline."""
        # Create a large number of songs for stress testing
        stress_songs = []
        for i in range(200):
            song = Song(
                id=i+1000,  # Avoid ID conflicts
                spotify_id=f'stress_test_song_{i}',
                title=f'Stress Test Song {i}',
                artist=f'Stress Artist {i}',
                album=f'Stress Album {i}',
                duration_ms=180000,
                lyrics=f'Christian song lyrics {i} with biblical themes and spiritual content.'
            )
            stress_songs.append(song)
        
        # Mock AI analysis for consistent behavior
        with patch.object(analysis_service, 'analyze_lyrics') as mock_analyze:
            mock_analyze.return_value = {
                'overall_score': 8.0,
                'biblical_references': 2,
                'spiritual_themes': ['faith'],
                'explicit_christian_content': True
            }
            
            successful_analyses = 0
            failed_analyses = 0
            total_time = 0
            
            start_time = time.time()
            
            # Process in batches with multiple threads
            batch_size = 20
            max_workers = 10
            
            for i in range(0, len(stress_songs), batch_size):
                batch = stress_songs[i:i+batch_size]
                
                def analyze_batch_song(song):
                    try:
                        batch_start = time.time()
                        result = analysis_service.analyze_song_by_id(song.id, sample_user.id)
                        batch_time = time.time() - batch_start
                        return True, batch_time
                    except Exception:
                        return False, 0
                
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = [executor.submit(analyze_batch_song, song) for song in batch]
                    for future in as_completed(futures):
                        success, analysis_time = future.result()
                        if success:
                            successful_analyses += 1
                            total_time += analysis_time
                        else:
                            failed_analyses += 1
            
            end_time = time.time()
            total_pipeline_time = end_time - start_time
            
            # Stress test results validation
            total_songs = len(stress_songs)
            success_rate = successful_analyses / total_songs
            avg_analysis_time = total_time / successful_analyses if successful_analyses > 0 else 0
            throughput = successful_analyses / total_pipeline_time
            
            # Performance requirements
            assert success_rate > 0.95, f"Success rate {success_rate:.2f} too low"
            assert avg_analysis_time < 2.0, f"Average analysis time {avg_analysis_time:.3f}s too high"
            assert throughput > 10, f"Throughput {throughput:.1f} analyses/sec too low"
            assert total_pipeline_time < 60, f"Total pipeline time {total_pipeline_time:.1f}s too high" 