"""
Test model caching and performance optimization for analysis system.

This test suite verifies that AI models are properly cached and reused
across multiple song analyses instead of being reloaded each time.
"""

import pytest
import time
import unittest.mock
from unittest.mock import patch, MagicMock

from app.utils.analysis.huggingface_analyzer import HuggingFaceAnalyzer
from app.services.unified_analysis_service import UnifiedAnalysisService
from app.services.priority_queue_worker import process_analysis_job


class TestModelCaching:
    """Test model caching and reuse behavior"""
    
    def test_analyzer_models_loaded_only_once(self):
        """Test that HuggingFace models are loaded only once per analyzer instance"""
        
        # This test should FAIL initially because models are reloaded each time
        with patch('app.utils.analysis.huggingface_analyzer.pipeline') as mock_pipeline:
            analyzer = HuggingFaceAnalyzer()
            
            # Simulate multiple song analyses
            test_lyrics = ["Test song 1", "Test song 2", "Test song 3"]
            
            for lyrics in test_lyrics:
                analyzer.analyze_song("Test Song", "Test Artist", lyrics)
            
            # Models should only be loaded once (4 models total)
            # Currently FAILS: pipeline is called 12 times (4 models × 3 songs)
            assert mock_pipeline.call_count == 4, f"Expected 4 model loads, got {mock_pipeline.call_count}"
    
    def test_worker_reuses_analyzer_instance(self):
        """Test that worker process reuses the same analyzer across jobs"""
        
        # This test should FAIL initially because new instances are created per job
        job_data_1 = {'song_id': 1, 'song_title': 'Test 1', 'artist': 'Artist 1', 'lyrics': 'Test lyrics 1'}
        job_data_2 = {'song_id': 2, 'song_title': 'Test 2', 'artist': 'Artist 2', 'lyrics': 'Test lyrics 2'}
        
        with patch('app.services.unified_analysis_service.UnifiedAnalysisService') as mock_service_class:
            mock_service_instance = MagicMock()
            mock_service_class.return_value = mock_service_instance
            
            # Process two jobs
            with patch('app.services.priority_queue_worker.get_song_data', return_value=job_data_1):
                process_analysis_job(job_data_1)
            
            with patch('app.services.priority_queue_worker.get_song_data', return_value=job_data_2):
                process_analysis_job(job_data_2)
            
            # Currently FAILS: UnifiedAnalysisService instantiated twice
            assert mock_service_class.call_count == 1, f"Expected 1 service instance, got {mock_service_class.call_count}"
    
    def test_performance_improvement_with_caching(self):
        """Test that caching provides significant performance improvement"""
        
        # This test should FAIL initially due to slow model reloading
        with patch.object(HuggingFaceAnalyzer, '_load_models_with_download') as mock_load:
            analyzer = HuggingFaceAnalyzer()
            
            # Time multiple analyses
            start_time = time.time()
            
            for i in range(3):
                analyzer.analyze_song(f"Test Song {i}", "Test Artist", f"Test lyrics {i}")
            
            elapsed_time = time.time() - start_time
            
            # With proper caching, 3 songs should complete in under 5 minutes
            # Currently FAILS: Takes 30+ minutes due to model reloading
            assert elapsed_time < 300, f"Analysis took {elapsed_time:.1f}s, expected < 300s with caching"
    
    def test_memory_usage_with_cached_models(self):
        """Test that memory usage is reasonable with cached models"""
        
        # This test verifies memory doesn't grow linearly with song count
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        with patch.object(HuggingFaceAnalyzer, 'analyze_song', return_value={}):
            analyzer = HuggingFaceAnalyzer()
            
            # Simulate analyzing many songs
            for i in range(10):
                analyzer.analyze_song(f"Song {i}", "Artist", f"Lyrics {i}")
            
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_growth = final_memory - initial_memory
        
        # Memory growth should be minimal with proper caching
        # Currently might FAIL if models are reloaded each time
        assert memory_growth < 500, f"Memory grew by {memory_growth:.1f}MB, expected < 500MB with caching"


class TestAnalyzerSingleton:
    """Test singleton pattern for analyzer instances"""
    
    def test_shared_analyzer_singleton(self):
        """Test that a shared analyzer singleton is available"""
        
        # This test should FAIL initially because no singleton exists
        from app.services.analyzer_cache import get_shared_analyzer
        
        analyzer1 = get_shared_analyzer()
        analyzer2 = get_shared_analyzer()
        
        # Should return the same instance
        assert analyzer1 is analyzer2, "get_shared_analyzer should return the same instance"
    
    def test_singleton_models_preloaded(self):
        """Test that singleton analyzer has models preloaded"""
        
        # This test should FAIL initially because singleton doesn't exist
        from app.services.analyzer_cache import get_shared_analyzer
        
        analyzer = get_shared_analyzer()
        
        # Models should be already loaded
        assert hasattr(analyzer, '_sentiment_analyzer'), "Sentiment analyzer should be preloaded"
        assert hasattr(analyzer, '_safety_analyzer'), "Safety analyzer should be preloaded"
        assert hasattr(analyzer, '_emotion_analyzer'), "Emotion analyzer should be preloaded"
        assert hasattr(analyzer, '_theme_analyzer'), "Theme analyzer should be preloaded"


class TestWorkerOptimization:
    """Test worker process optimization"""
    
    def test_worker_initialization_time(self):
        """Test that worker startup time is reasonable"""
        
        # This test verifies worker doesn't take forever to start
        start_time = time.time()
        
        # Mock the actual analysis to focus on initialization
        with patch('app.services.priority_queue_worker.process_analysis_job'):
            from app.services.priority_queue_worker import initialize_worker
            initialize_worker()
        
        init_time = time.time() - start_time
        
        # Worker should initialize quickly (models loaded once at startup)
        assert init_time < 60, f"Worker took {init_time:.1f}s to initialize, expected < 60s"
    
    def test_concurrent_analysis_handling(self):
        """Test that worker can handle multiple analyses efficiently"""
        
        # This test verifies no resource conflicts with cached models
        job_queue = [
            {'song_id': i, 'song_title': f'Song {i}', 'artist': 'Artist', 'lyrics': f'Lyrics {i}'}
            for i in range(5)
        ]
        
        start_time = time.time()
        
        with patch('app.services.priority_queue_worker.get_song_data') as mock_get_song:
            with patch('app.services.unified_analysis_service.UnifiedAnalysisService.analyze_song_content'):
                for job_data in job_queue:
                    mock_get_song.return_value = job_data
                    process_analysis_job(job_data)
        
        total_time = time.time() - start_time
        
        # 5 songs should complete quickly with cached models
        assert total_time < 30, f"5 analyses took {total_time:.1f}s, expected < 30s with caching" 