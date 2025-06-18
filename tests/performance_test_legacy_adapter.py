#!/usr/bin/env python3
"""
Performance test for legacy adapter caching optimizations.
"""

import time
import pytest
from unittest.mock import patch, MagicMock

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def test_legacy_adapter_caching_performance():
    """Test that caching reduces redundant orchestrator calls."""
    
    # Mock the orchestrator at import time to avoid model loading
    with patch('app.utils.analysis.legacy_adapter.AnalysisOrchestrator') as MockOrchestrator:
        mock_orchestrator_instance = MagicMock()
        mock_result = MagicMock()
        mock_result.purity_flags = []
        mock_result.biblical_themes = []
        mock_result.overall_score = 0.8
        mock_result.concerns = []
        mock_orchestrator_instance.analyze_song.return_value = mock_result
        MockOrchestrator.return_value = mock_orchestrator_instance
        
        # Now import and create SongAnalyzer
        from app.utils.analysis.legacy_adapter import SongAnalyzer
        analyzer = SongAnalyzer()
        
        # Test data
        title = "Amazing Grace"
        artist = "Chris Tomlin"
        lyrics = "Amazing grace how sweet the sound that saved a wretch like me"
        
        # First call - should hit orchestrator
        start_time = time.time()
        result1 = analyzer.analyze_song(title, artist, lyrics)
        first_call_time = time.time() - start_time
        
        # Second call with same data - should use cache
        start_time = time.time() 
        result2 = analyzer.analyze_song(title, artist, lyrics)
        second_call_time = time.time() - start_time
        
        # Third call with same data - should use cache
        start_time = time.time()
        result3 = analyzer.analyze_song(title, artist, lyrics)
        third_call_time = time.time() - start_time
        
        # Verify orchestrator was only called once
        assert mock_orchestrator_instance.analyze_song.call_count == 1, f"Expected 1 orchestrator call, got {mock_orchestrator_instance.analyze_song.call_count}"
        
        # Verify all results are identical (from cache)
        assert result1 == result2 == result3, "Cached results should be identical"
        
        # Verify cache performance improvement
        # Second and third calls should be significantly faster
        assert second_call_time < first_call_time * 0.8, f"Second call should be faster due to caching. First: {first_call_time:.4f}s, Second: {second_call_time:.4f}s"
        assert third_call_time < first_call_time * 0.8, f"Third call should be faster due to caching. First: {first_call_time:.4f}s, Third: {third_call_time:.4f}s"
        
        print(f"✅ Performance Test Results:")
        print(f"   First call (orchestrator):  {first_call_time:.4f}s")
        print(f"   Second call (cache):        {second_call_time:.4f}s")
        print(f"   Third call (cache):         {third_call_time:.4f}s")
        print(f"   Cache speedup: {first_call_time/second_call_time:.1f}x faster")
        print(f"   Orchestrator calls: {mock_orchestrator_instance.analyze_song.call_count}/3")


def test_cache_invalidation_on_different_content():
    """Test that cache is properly invalidated for different content."""
    
    with patch('app.utils.analysis.legacy_adapter.AnalysisOrchestrator') as MockOrchestrator:
        mock_orchestrator_instance = MagicMock()
        mock_result = MagicMock()
        mock_result.purity_flags = []
        mock_result.biblical_themes = []
        mock_result.overall_score = 0.8
        mock_result.concerns = []
        mock_orchestrator_instance.analyze_song.return_value = mock_result
        MockOrchestrator.return_value = mock_orchestrator_instance
        
        from app.utils.analysis.legacy_adapter import SongAnalyzer
        analyzer = SongAnalyzer()
        
        # First song
        analyzer.analyze_song("Amazing Grace", "Chris Tomlin", "Amazing grace lyrics")
        
        # Different song - should trigger new orchestrator call
        analyzer.analyze_song("How Great Thou Art", "Chris Tomlin", "How great thou art lyrics")
        
        # Different artist - should trigger new orchestrator call  
        analyzer.analyze_song("Amazing Grace", "Hillsong", "Amazing grace lyrics")
        
        # Different lyrics - should trigger new orchestrator call
        analyzer.analyze_song("Amazing Grace", "Chris Tomlin", "Different lyrics entirely")
        
        # Verify orchestrator was called for each unique combination
        assert mock_orchestrator_instance.analyze_song.call_count == 4, f"Expected 4 orchestrator calls for different content, got {mock_orchestrator_instance.analyze_song.call_count}"
        
        print(f"✅ Cache Invalidation Test: {mock_orchestrator_instance.analyze_song.call_count}/4 unique calls made")


def test_backward_compatibility_verification():
    """Test that refactored adapter maintains exact backward compatibility."""
    
    with patch('app.utils.analysis.legacy_adapter.AnalysisOrchestrator') as MockOrchestrator:
        mock_orchestrator_instance = MagicMock()
        mock_result = MagicMock()
        mock_result.purity_flags = ['profanity']
        mock_result.biblical_themes = ['redemption', 'grace']
        mock_result.overall_score = 0.85
        mock_result.concerns = ['mild_language']
        mock_orchestrator_instance.analyze_song.return_value = mock_result
        MockOrchestrator.return_value = mock_orchestrator_instance
        
        from app.utils.analysis.legacy_adapter import SongAnalyzer
        analyzer = SongAnalyzer()
        
        # Test that all expected legacy attributes exist
        assert hasattr(analyzer, 'lyrics_fetcher'), "Legacy lyrics_fetcher attribute missing"
        assert hasattr(analyzer, 'christian_rubric'), "Legacy christian_rubric attribute missing"
        assert hasattr(analyzer, 'content_detector'), "Legacy content_detector attribute missing"
        
        # Test that legacy method signature works
        result = analyzer.analyze_song("Test Song", "Test Artist", "Test lyrics")
        
        # Verify legacy result format
        assert isinstance(result, dict), "Result should be a dictionary"
        assert 'christian_purity_flags_details' in result, "Legacy christian_purity_flags_details field missing"
        assert 'christian_positive_themes_detected' in result, "Legacy christian_positive_themes_detected field missing"
        assert 'christian_score' in result, "Legacy christian_score field missing"
        
        print(f"✅ Backward Compatibility Test: All legacy interfaces preserved")


if __name__ == "__main__":
    print("🔍 Testing Legacy Adapter Performance Optimizations...")
    
    test_legacy_adapter_caching_performance()
    test_cache_invalidation_on_different_content()
    test_backward_compatibility_verification()
    
    print("\n🎉 All performance tests passed!")
    print("✅ Caching optimizations are working correctly")
    print("✅ Backward compatibility maintained")
    print("✅ Performance improvements verified") 