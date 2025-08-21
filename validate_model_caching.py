#!/usr/bin/env python3
"""
Simple validation script for model caching implementation.
Tests the key functionality without requiring pytest infrastructure.
"""

import sys
import time
import traceback

from app.services.simplified_christian_analysis_service import SimplifiedChristianAnalysisService
from app.utils.analysis.huggingface_analyzer import HuggingFaceAnalyzer


def test_singleton_pattern():
    """Test that the same analyzer instance is returned"""
    print("🧪 Testing singleton pattern...")

    analyzer1 = HuggingFaceAnalyzer.get_instance()
    analyzer2 = HuggingFaceAnalyzer.get_instance()

    if analyzer1 is analyzer2:
        print("✅ Singleton pattern working - same instance returned")
        return True
    else:
        print("❌ Singleton pattern failed - different instances returned")
        return False


def test_instantiation_performance():
    """Test that subsequent instantiations are fast"""
    print("🧪 Testing instantiation performance...")

    # First instantiation - may be slow
    start_time = time.time()
    analyzer1 = HuggingFaceAnalyzer.get_instance()
    first_time = time.time() - start_time
    print(f"   First instantiation: {first_time:.3f}s")

    # Second instantiation - should be fast
    start_time = time.time()
    analyzer2 = HuggingFaceAnalyzer.get_instance()
    second_time = time.time() - start_time
    print(f"   Second instantiation: {second_time:.3f}s")

    if second_time < 0.1:  # Should be very fast for cached instance
        print("✅ Performance test passed - cached instantiation is fast")
        return True
    else:
        print(f"❌ Performance test failed - cached instantiation took {second_time:.3f}s")
        return False


def test_service_instantiation():
    """Test that SimplifiedChristianAnalysisService instantiation works"""
    print("🧪 Testing service instantiation...")

    start_time = time.time()
    try:
        service = SimplifiedChristianAnalysisService()
        instantiation_time = time.time() - start_time
        print(f"   Service instantiation: {instantiation_time:.3f}s")

        if instantiation_time < 30.0:  # Should complete within 30 seconds
            print("✅ Service instantiation test passed")
            return True
        else:
            print(f"❌ Service instantiation too slow: {instantiation_time:.3f}s")
            return False
    except Exception as e:
        instantiation_time = time.time() - start_time
        print(f"❌ Service instantiation failed after {instantiation_time:.3f}s: {e}")
        traceback.print_exc()
        return False


def test_multiple_service_instances():
    """Test that creating multiple service instances doesn't reload models"""
    print("🧪 Testing multiple service instances...")

    start_time = time.time()
    try:
        service1 = SimplifiedChristianAnalysisService()
        first_service_time = time.time() - start_time
        print(f"   First service: {first_service_time:.3f}s")

        start_time = time.time()
        service2 = SimplifiedChristianAnalysisService()
        second_service_time = time.time() - start_time
        print(f"   Second service: {second_service_time:.3f}s")

        start_time = time.time()
        service3 = SimplifiedChristianAnalysisService()
        third_service_time = time.time() - start_time
        print(f"   Third service: {third_service_time:.3f}s")

        # Second and third should be much faster
        if second_service_time < 5.0 and third_service_time < 5.0:
            print("✅ Multiple service instances test passed")
            return True
        else:
            print(
                f"❌ Multiple service instances too slow: {second_service_time:.3f}s, {third_service_time:.3f}s"
            )
            return False
    except Exception as e:
        print(f"❌ Multiple service instances failed: {e}")
        traceback.print_exc()
        return False


def main():
    """Run all validation tests"""
    print("🚀 Starting Model Caching Validation Tests")
    print("=" * 50)

    tests = [
        test_singleton_pattern,
        test_instantiation_performance,
        test_service_instantiation,
        test_multiple_service_instances,
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
        print("-" * 30)

    print(f"📊 Results: {passed} passed, {failed} failed")

    if failed == 0:
        print("🎉 All tests passed! Model caching is working correctly.")
        return 0
    else:
        print("🚨 Some tests failed. Model caching needs fixes.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
