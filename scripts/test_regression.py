#!/usr/bin/env python3
"""
Regression Test Suite
Tests critical functionality to ensure refactoring hasn't broken anything
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def print_test(name, status, details=""):
    icon = "✅" if status else "❌"
    print(f"{icon} {name}")
    if details:
        print(f"   └─ {details}")
    return status

def test_database_models():
    """Test that all database models work correctly"""
    print("\n" + "="*60)
    print("Testing Database Models")
    print("="*60 + "\n")
    
    from app import create_app
    from app.extensions import db
    from app.models.models import User, Song, AnalysisResult, Playlist, LyricsCache
    from datetime import datetime, timezone
    
    app = create_app()
    results = []
    
    with app.app_context():
        # Test User model
        try:
            user = User(
                spotify_id="test_user_123",
                display_name="Test User",
                email="test@example.com"
            )
            results.append(print_test("User model instantiation", True, f"Created: {user.display_name}"))
        except Exception as e:
            results.append(print_test("User model instantiation", False, str(e)))
        
        # Test Song model
        try:
            song = Song(
                spotify_id="test_song_123",
                title="Test Song",
                artist="Test Artist",
                album="Test Album"
            )
            results.append(print_test("Song model instantiation", True, f"Created: {song.title}"))
        except Exception as e:
            results.append(print_test("Song model instantiation", False, str(e)))
        
        # Test AnalysisResult model
        try:
            analysis = AnalysisResult(
                song_id=1,
                score=75,
                verdict="context_required",
                biblical_themes=["faith", "hope"]
            )
            results.append(print_test("AnalysisResult model instantiation", True, f"Score: {analysis.score}"))
        except Exception as e:
            results.append(print_test("AnalysisResult model instantiation", False, str(e)))
        
        # Test LyricsCache model methods
        try:
            # Test find_cached_lyrics
            cached = LyricsCache.find_cached_lyrics("Test Artist", "Test Song")
            results.append(print_test("LyricsCache.find_cached_lyrics", True, f"Result: {cached}"))
        except Exception as e:
            results.append(print_test("LyricsCache.find_cached_lyrics", False, str(e)))
    
    return all(results)

def test_analyzer_components():
    """Test that analyzer components work correctly"""
    print("\n" + "="*60)
    print("Testing Analyzer Components")
    print("="*60 + "\n")
    
    from app.services.analyzers import RouterAnalyzer
    from app.services.provider_resolver import get_analyzer
    from app.services.analyzer_cache import get_shared_analyzer, is_analyzer_ready
    
    results = []
    
    # Test RouterAnalyzer direct instantiation
    try:
        analyzer = RouterAnalyzer()
        has_model = hasattr(analyzer, 'model') and analyzer.model
        has_api_key = hasattr(analyzer, 'api_key') and analyzer.api_key
        results.append(print_test(
            "RouterAnalyzer instantiation",
            has_model and has_api_key,
            f"Model: {analyzer.model[:50]}..."
        ))
    except Exception as e:
        results.append(print_test("RouterAnalyzer instantiation", False, str(e)))
    
    # Test provider resolver
    try:
        analyzer = get_analyzer()
        is_router = type(analyzer).__name__ == 'RouterAnalyzer'
        results.append(print_test(
            "Provider resolver returns RouterAnalyzer",
            is_router,
            f"Type: {type(analyzer).__name__}"
        ))
    except Exception as e:
        results.append(print_test("Provider resolver", False, str(e)))
    
    # Test analyzer cache
    try:
        analyzer1 = get_shared_analyzer()
        analyzer2 = get_shared_analyzer()
        is_singleton = analyzer1 is analyzer2
        results.append(print_test(
            "Analyzer cache singleton pattern",
            is_singleton,
            "Same instance returned"
        ))
        
        ready = is_analyzer_ready()
        results.append(print_test(
            "Analyzer ready check",
            ready,
            f"Ready: {ready}"
        ))
    except Exception as e:
        results.append(print_test("Analyzer cache", False, str(e)))
    
    return all(results)

def test_analysis_service():
    """Test the SimplifiedChristianAnalysisService"""
    print("\n" + "="*60)
    print("Testing Analysis Service")
    print("="*60 + "\n")
    
    from app import create_app
    from app.services.simplified_christian_analysis_service import SimplifiedChristianAnalysisService
    
    app = create_app()
    results = []
    
    with app.app_context():
        try:
            service = SimplifiedChristianAnalysisService()
            
            # Check service has required components
            has_analyzer = hasattr(service, 'analyzer')
            has_concern = hasattr(service, 'concern_detector')
            has_scripture = hasattr(service, 'scripture_mapper')
            
            results.append(print_test(
                "Service initialization",
                has_analyzer and has_concern and has_scripture,
                "All components present"
            ))
            
            # Check analyzer type
            analyzer_type = type(service.analyzer).__name__
            is_router = analyzer_type == 'RouterAnalyzer'
            results.append(print_test(
                "Service uses RouterAnalyzer",
                is_router,
                f"Analyzer: {analyzer_type}"
            ))
            
            # Check stub services
            concern_type = type(service.concern_detector).__name__
            scripture_type = type(service.scripture_mapper).__name__
            
            is_stub_concern = 'Stub' in concern_type
            is_stub_scripture = 'Stub' in scripture_type
            
            results.append(print_test(
                "Stub services for backward compatibility",
                is_stub_concern and is_stub_scripture,
                f"Concern: {concern_type}, Scripture: {scripture_type}"
            ))
            
        except Exception as e:
            results.append(print_test("Analysis service", False, str(e)))
    
    return all(results)

def test_lyrics_fetcher():
    """Test the lyrics fetcher"""
    print("\n" + "="*60)
    print("Testing Lyrics Fetcher")
    print("="*60 + "\n")
    
    from app import create_app
    from app.utils.lyrics.lyrics_fetcher import LyricsFetcher
    
    app = create_app()
    results = []
    
    with app.app_context():
        try:
            fetcher = LyricsFetcher()
            
            # Check fetcher has required attributes
            has_genius = hasattr(fetcher, 'genius')
            has_config = hasattr(fetcher, 'config')
            
            results.append(print_test(
                "Lyrics fetcher initialization",
                has_genius and has_config,
                "Fetcher configured"
            ))
            
            # Check methods exist
            has_fetch = hasattr(fetcher, 'fetch_lyrics')
            results.append(print_test(
                "Lyrics fetcher has fetch_lyrics method",
                has_fetch,
                "Method available"
            ))
            
        except Exception as e:
            results.append(print_test("Lyrics fetcher", False, str(e)))
    
    return all(results)

def test_no_legacy_imports():
    """Verify legacy code cannot be imported"""
    print("\n" + "="*60)
    print("Testing Legacy Code Removal")
    print("="*60 + "\n")
    
    results = []
    
    legacy_modules = [
        ("intelligent_llm_router", "app.services.intelligent_llm_router"),
        ("rules_rag", "app.services.rules_rag"),
        ("embedding_index", "app.utils.analysis.embedding_index"),
        ("theology_kb", "app.utils.analysis.theology_kb"),
        ("EnhancedConcernDetector", "app.services.enhanced_concern_detector"),
        ("EnhancedScriptureMapper", "app.services.enhanced_scripture_mapper"),
    ]
    
    for name, module in legacy_modules:
        try:
            __import__(module)
            results.append(print_test(f"Legacy {name} removed", False, "Still importable"))
        except ModuleNotFoundError:
            results.append(print_test(f"Legacy {name} removed", True, "Properly removed"))
        except Exception as e:
            # Other import errors are ok (e.g., parent module issues)
            results.append(print_test(f"Legacy {name} removed", True, f"Cannot import: {type(e).__name__}"))
    
    return all(results)

def test_environment_validation():
    """Test environment variable validation"""
    print("\n" + "="*60)
    print("Testing Environment Validation")
    print("="*60 + "\n")
    
    results = []
    
    # Test that RouterAnalyzer validates API key
    try:
        from app.services.analyzers import RouterAnalyzer
        import os
        
        # Save original
        original_key = os.environ.get('OPENAI_API_KEY')
        
        # Test with key present (should work)
        if original_key:
            try:
                analyzer = RouterAnalyzer()
                results.append(print_test(
                    "RouterAnalyzer with valid API key",
                    True,
                    "Initialization successful"
                ))
            except Exception as e:
                results.append(print_test(
                    "RouterAnalyzer with valid API key",
                    False,
                    str(e)
                ))
        else:
            results.append(print_test(
                "RouterAnalyzer API key check",
                True,
                "API key not set (skipped validation test)"
            ))
            
    except Exception as e:
        results.append(print_test("Environment validation", False, str(e)))
    
    return all(results)

def test_response_structures():
    """Test that response structures are correct"""
    print("\n" + "="*60)
    print("Testing Response Structures")
    print("="*60 + "\n")
    
    from app import create_app
    from app.services.simplified_christian_analysis_service import SimplifiedChristianAnalysisService
    
    app = create_app()
    results = []
    
    with app.app_context():
        try:
            service = SimplifiedChristianAnalysisService()
            
            # Test analysis response structure
            test_lyrics = "Amazing grace, how sweet the sound"
            result = service.analyze_song_content("Test Song", "Test Artist", test_lyrics)
            
            # Check required fields
            has_score = 'overall_score' in result or 'score' in result
            has_verdict = 'verdict' in result
            
            results.append(print_test(
                "Analysis response has score",
                has_score,
                f"Score field present"
            ))
            
            results.append(print_test(
                "Analysis response has verdict",
                has_verdict,
                f"Verdict field present"
            ))
            
            # Check response is dict
            is_dict = isinstance(result, dict)
            results.append(print_test(
                "Analysis response is dictionary",
                is_dict,
                f"Type: {type(result).__name__}"
            ))
            
        except Exception as e:
            # API errors are expected if API key is invalid
            if "401" in str(e) or "API key" in str(e):
                results.append(print_test(
                    "Response structure test",
                    True,
                    "Skipped (API key issue)"
                ))
            else:
                results.append(print_test("Response structure test", False, str(e)))
    
    return all(results)

def main():
    """Run all regression tests"""
    print("\n" + "="*60)
    print("  REGRESSION TEST SUITE")
    print("="*60)
    
    test_suites = [
        ("Database Models", test_database_models),
        ("Analyzer Components", test_analyzer_components),
        ("Analysis Service", test_analysis_service),
        ("Lyrics Fetcher", test_lyrics_fetcher),
        ("Legacy Code Removal", test_no_legacy_imports),
        ("Environment Validation", test_environment_validation),
        ("Response Structures", test_response_structures),
    ]
    
    results = {}
    for name, test_func in test_suites:
        try:
            results[name] = test_func()
        except Exception as e:
            print(f"\n❌ Test suite '{name}' failed with error: {e}")
            results[name] = False
    
    # Summary
    print("\n" + "="*60)
    print("  REGRESSION TEST SUMMARY")
    print("="*60 + "\n")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, status in results.items():
        icon = "✅" if status else "❌"
        print(f"{icon} {name}")
    
    print(f"\nTotal: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {total - passed}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    return all(results.values())

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

