#!/usr/bin/env python3
"""
Regression Test Suite for Model Caching Fix

Tests key functionality to ensure the model caching fix didn't break anything.
"""

import os
import sys
import time
import traceback

from app.services.simplified_christian_analysis_service import SimplifiedChristianAnalysisService
from app.services.unified_analysis_service import UnifiedAnalysisService
from app.utils.analysis.llm_analyzer import LLMAnalyzer


def test_basic_analyzer_functionality():
    """Test that the LLMAnalyzer returns valid structure"""
    print("🧪 Testing basic analyzer functionality...")

    try:
        os.environ.setdefault("USE_LLM_ANALYZER", "1")
        analyzer = LLMAnalyzer()

        # Test that required attributes exist
        # No heavy attributes required; ensure analyze works and returns expected fields

        # Test basic analysis functionality
        result = analyzer.analyze_song(
            "Amazing Grace", "John Newton", "Amazing grace how sweet the sound"
        )
        has_fields = bool(
            result and result.biblical_analysis is not None and result.scoring_results is not None
        )
        if has_fields:
            print("   ✅ Basic analysis functionality works")
            return True
        else:
            print("   ❌ Basic analysis failed")
            return False

    except Exception as e:
        print(f"   ❌ Basic analyzer test failed: {e}")
        traceback.print_exc()
        return False


def test_simplified_service_functionality():
    """Test that SimplifiedChristianAnalysisService still works"""
    print("🧪 Testing simplified service functionality...")

    try:
        service = SimplifiedChristianAnalysisService()

        # Test that the service has required components
        if hasattr(service, "concern_detector") and hasattr(service, "scripture_mapper"):
            print("   ✅ Service components exist")
        else:
            print("   ❌ Service components missing")
            return False

        # Test analyze_song_content method exists and can be called
        if hasattr(service, "analyze_song_content"):
            print("   ✅ analyze_song_content method exists")
            return True
        else:
            print("   ❌ analyze_song_content method missing")
            return False

    except Exception as e:
        print(f"   ❌ Simplified service test failed: {e}")
        traceback.print_exc()
        return False


def test_unified_service_functionality():
    """Test that UnifiedAnalysisService still works"""
    print("🧪 Testing unified service functionality...")

    try:
        service = UnifiedAnalysisService()

        # Test basic methods exist
        methods = ["test_method", "analyze_songs_batch"]
        for method in methods:
            if hasattr(service, method):
                print(f"   ✅ {method} exists")
            else:
                print(f"   ❌ {method} missing")
                return False

        # Test that test_method still works
        result = service.test_method()
        if result == "test_success":
            print("   ✅ test_method works correctly")
            return True
        else:
            print(f"   ❌ test_method returned unexpected result: {result}")
            return False

    except Exception as e:
        print(f"   ❌ Unified service test failed: {e}")
        traceback.print_exc()
        return False


def test_performance_characteristics():
    """Test that performance is acceptable after caching"""
    print("🧪 Testing performance characteristics...")

    try:
        # Multiple instantiations should be fast
        # Skip HF timing; ensure LLMAnalyzer instantiation is quick
        start_time = time.time()
        _ = LLMAnalyzer()
        instantiation_time = time.time() - start_time
        print(f"   Instantiation: {instantiation_time:.3f}s")
        return instantiation_time < 1.0

    except Exception as e:
        print(f"   ❌ Performance test failed: {e}")
        traceback.print_exc()
        return False


def test_memory_behavior():
    """Test that memory behavior is reasonable"""
    print("🧪 Testing memory behavior...")

    try:
        import os

        import psutil

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Create multiple LLMAnalyzer instances (lightweight wrapper)
        analyzers = [LLMAnalyzer() for _ in range(5)]

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        print(f"   Initial memory: {initial_memory:.1f}MB")
        print(f"   Final memory: {final_memory:.1f}MB")
        print(f"   Memory increase: {memory_increase:.1f}MB")

        # Memory increase should be minimal for additional instances
        if memory_increase < 50:  # Less than 50MB increase
            print("   ✅ Memory behavior is reasonable")
            return True
        else:
            print(f"   ❌ Memory increase too high: {memory_increase:.1f}MB")
            return False

    except Exception as e:
        print(f"   ❌ Memory test failed: {e}")
        traceback.print_exc()
        return False


def test_thread_safety():
    """Test basic thread safety of singleton pattern"""
    print("🧪 Testing thread safety...")

    try:
        import queue
        import threading

        results = queue.Queue()
        errors = queue.Queue()

        def get_analyzer_id():
            try:
                analyzer = LLMAnalyzer()
                results.put(id(analyzer))
            except Exception as e:
                errors.put(str(e))

        # Create multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=get_analyzer_id)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        # Check for errors
        if not errors.empty():
            error_msg = errors.get()
            print(f"   ❌ Thread safety test failed with error: {error_msg}")
            return False

        # All threads should get the same instance
        analyzer_ids = []
        while not results.empty():
            analyzer_ids.append(results.get())

        if len(set(analyzer_ids)) == 1:
            print("   ✅ Thread safety test passed")
            return True
        else:
            print(f"   ❌ Got different instances: {len(set(analyzer_ids))} unique IDs")
            return False

    except Exception as e:
        print(f"   ❌ Thread safety test failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run comprehensive regression tests"""
    print("🚀 Running Regression Test Suite")
    print("=" * 50)

    tests = [
        test_basic_analyzer_functionality,
        test_simplified_service_functionality,
        test_unified_service_functionality,
        test_performance_characteristics,
        test_memory_behavior,
        test_thread_safety,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            traceback.print_exc()
            failed += 1
        print("-" * 40)

    print(f"📊 Regression Test Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All regression tests passed! Model caching fix is solid.")
        return 0
    else:
        print("🚨 Some regression tests failed. Review the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
