#!/usr/bin/env python3
"""
Comprehensive System Health Check
Tests all major components after refactoring
"""

import sys
import os
import time
import requests
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def print_test(name, status, message=""):
    icon = "✅" if status else "❌"
    print(f"{icon} {name}")
    if message:
        print(f"   └─ {message}")

def test_imports():
    """Test that all core imports work"""
    print_header("1. Testing Core Imports")
    
    tests = []
    
    # Test Flask app creation
    try:
        from app import create_app
        app = create_app()
        tests.append(("Flask app creation", True, "App created successfully"))
    except Exception as e:
        tests.append(("Flask app creation", False, str(e)))
        return tests
    
    # Test database models
    try:
        from app.models.models import User, Song, AnalysisResult, Playlist
        tests.append(("Database models", True, "All models imported"))
    except Exception as e:
        tests.append(("Database models", False, str(e)))
    
    # Test analyzer imports
    try:
        from app.services.analyzers import RouterAnalyzer
        analyzer = RouterAnalyzer()
        tests.append(("RouterAnalyzer", True, f"Type: {type(analyzer).__name__}"))
    except Exception as e:
        tests.append(("RouterAnalyzer", False, str(e)))
    
    # Test provider resolver
    try:
        from app.services.provider_resolver import get_analyzer
        analyzer = get_analyzer()
        tests.append(("Provider Resolver", True, f"Returns: {type(analyzer).__name__}"))
    except Exception as e:
        tests.append(("Provider Resolver", False, str(e)))
    
    # Test analyzer cache
    try:
        from app.services.analyzer_cache import get_shared_analyzer
        analyzer = get_shared_analyzer()
        tests.append(("Analyzer Cache", True, f"Cached: {type(analyzer).__name__}"))
    except Exception as e:
        tests.append(("Analyzer Cache", False, str(e)))
    
    # Test analysis service
    try:
        from app.services.simplified_christian_analysis_service import SimplifiedChristianAnalysisService
        service = SimplifiedChristianAnalysisService()
        has_concern = hasattr(service, 'concern_detector')
        has_scripture = hasattr(service, 'scripture_mapper')
        tests.append(("Analysis Service", True, f"Concern detector: {has_concern}, Scripture mapper: {has_scripture}"))
    except Exception as e:
        tests.append(("Analysis Service", False, str(e)))
    
    # Test lyrics fetcher
    try:
        from app.utils.lyrics.lyrics_fetcher import LyricsFetcher
        fetcher = LyricsFetcher()
        tests.append(("Lyrics Fetcher", True, "Initialized successfully"))
    except Exception as e:
        tests.append(("Lyrics Fetcher", False, str(e)))
    
    for name, status, message in tests:
        print_test(name, status, message)
    
    return tests

def test_database_connection():
    """Test database connectivity"""
    print_header("2. Testing Database Connection")
    
    tests = []
    
    try:
        from app import create_app
        from app.extensions import db
        
        app = create_app()
        with app.app_context():
            # Try to execute a simple query
            result = db.session.execute(db.text("SELECT 1"))
            tests.append(("Database connection", True, "Connection successful"))
            
            # Check if tables exist
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            tests.append(("Database tables", len(tables) > 0, f"Found {len(tables)} tables"))
            
    except Exception as e:
        tests.append(("Database connection", False, str(e)))
    
    for name, status, message in tests:
        print_test(name, status, message)
    
    return tests

def test_redis_connection():
    """Test Redis connectivity"""
    print_header("3. Testing Redis Connection")
    
    tests = []
    
    try:
        import redis
        # Try Docker service name first, then localhost
        redis_host = os.getenv('REDIS_HOST', 'redis')
        r = redis.Redis(host=redis_host, port=6379, db=0, decode_responses=True)
        r.ping()
        tests.append(("Redis connection", True, f"Ping successful (host: {redis_host})"))
        
        # Test set/get
        test_key = "health_check_test"
        test_value = "test_value"
        r.set(test_key, test_value, ex=10)
        retrieved = r.get(test_key)
        tests.append(("Redis operations", retrieved == test_value, f"Set/Get working"))
        r.delete(test_key)
        
    except Exception as e:
        tests.append(("Redis connection", False, str(e)))
    
    for name, status, message in tests:
        print_test(name, status, message)
    
    return tests

def test_web_service():
    """Test web service endpoints"""
    print_header("4. Testing Web Service")
    
    tests = []
    base_url = "http://localhost:5001"
    
    # Test home page
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        tests.append(("Home page", response.status_code == 200, f"Status: {response.status_code}"))
    except Exception as e:
        tests.append(("Home page", False, str(e)))
    
    # Test API status endpoint (optional - may not exist)
    try:
        response = requests.get(f"{base_url}/api/status", timeout=5)
        # 404 is ok if endpoint doesn't exist
        tests.append(("API status (optional)", True, f"Status: {response.status_code}"))
    except Exception as e:
        tests.append(("API status (optional)", True, f"Endpoint not found (expected)"))
    
    for name, status, message in tests:
        print_test(name, status, message)
    
    return tests

def test_analyzer_functionality():
    """Test analyzer with a sample song"""
    print_header("5. Testing Analyzer Functionality")
    
    tests = []
    
    try:
        from app import create_app
        from app.services.simplified_christian_analysis_service import SimplifiedChristianAnalysisService
        
        app = create_app()
        with app.app_context():
            service = SimplifiedChristianAnalysisService()
            
            # Test with simple Christian song
            test_title = "Amazing Grace"
            test_artist = "John Newton"
            test_lyrics = """
Amazing grace, how sweet the sound
That saved a wretch like me
I once was lost, but now am found
Was blind, but now I see
"""
            
            print(f"   Testing analysis with: '{test_title}' by {test_artist}")
            
            # This will use the OpenAI API if configured
            try:
                result = service.analyze_song_content(test_title, test_artist, test_lyrics)
                
                has_score = 'overall_score' in result or 'score' in result
                has_verdict = 'verdict' in result
                has_themes = ('biblical_themes' in result or 'themes' in result or 
                             'themes_positive' in result or 'detected_themes' in result)
                has_analysis = 'analysis' in result or 'biblical_analysis' in result
                
                tests.append(("Analysis execution", True, "Analysis completed"))
                tests.append(("Analysis has score", has_score, f"Score present: {has_score}"))
                tests.append(("Analysis has verdict", has_verdict, f"Verdict present: {has_verdict}"))
                tests.append(("Analysis structure", has_themes or has_analysis, f"Themes/Analysis present"))
                
                # Print sample output
                if has_score:
                    score = result.get('overall_score') or result.get('score', 'N/A')
                    print(f"   └─ Sample score: {score}")
                
            except Exception as e:
                error_msg = str(e)
                if "OPENAI_API_KEY" in error_msg or "401" in error_msg:
                    tests.append(("Analysis execution", False, "OpenAI API key not configured (expected in dev)"))
                else:
                    tests.append(("Analysis execution", False, error_msg))
                
    except Exception as e:
        tests.append(("Analyzer setup", False, str(e)))
    
    for name, status, message in tests:
        print_test(name, status, message)
    
    return tests

def test_environment_config():
    """Test environment configuration"""
    print_header("6. Testing Environment Configuration")
    
    tests = []
    
    # Check critical environment variables
    required_vars = [
        ("POSTGRES_USER", os.getenv("POSTGRES_USER")),
        ("POSTGRES_PASSWORD", os.getenv("POSTGRES_PASSWORD")),
        ("POSTGRES_DB", os.getenv("POSTGRES_DB")),
    ]
    
    optional_vars = [
        ("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY")),
        ("SPOTIFY_CLIENT_ID", os.getenv("SPOTIFY_CLIENT_ID")),
        ("GENIUS_ACCESS_TOKEN", os.getenv("GENIUS_ACCESS_TOKEN")),
    ]
    
    for var_name, var_value in required_vars:
        tests.append((f"Env: {var_name}", var_value is not None, f"{'Set' if var_value else 'Missing'}"))
    
    for var_name, var_value in optional_vars:
        status_msg = "Set" if var_value else "Not set (optional)"
        tests.append((f"Env: {var_name}", True, status_msg))
    
    for name, status, message in tests:
        print_test(name, status, message)
    
    return tests

def test_no_legacy_code():
    """Verify no legacy code imports"""
    print_header("7. Testing for Legacy Code")
    
    tests = []
    
    # Check that old modules don't exist
    legacy_modules = [
        "app.services.intelligent_llm_router",
        "app.services.rules_rag",
        "app.utils.analysis.embedding_index",
        "app.utils.analysis.theology_kb",
        "app.services.enhanced_concern_detector",
        "app.services.enhanced_scripture_mapper",
    ]
    
    for module_name in legacy_modules:
        try:
            __import__(module_name)
            tests.append((f"Legacy: {module_name}", False, "Still importable (should be deleted)"))
        except ModuleNotFoundError:
            tests.append((f"Legacy: {module_name}", True, "Properly removed"))
        except Exception as e:
            tests.append((f"Legacy: {module_name}", True, f"Import error (expected): {type(e).__name__}"))
    
    for name, status, message in tests:
        print_test(name, status, message)
    
    return tests

def generate_report(all_tests):
    """Generate final test report"""
    print_header("Test Summary Report")
    
    total_tests = sum(len(tests) for tests in all_tests)
    passed_tests = sum(1 for tests in all_tests for _, status, _ in tests if status)
    failed_tests = total_tests - passed_tests
    
    print(f"Total Tests: {total_tests}")
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
    
    if failed_tests > 0:
        print(f"\n{'='*60}")
        print("Failed Tests:")
        print(f"{'='*60}")
        for tests in all_tests:
            for name, status, message in tests:
                if not status:
                    print(f"❌ {name}: {message}")
    
    print(f"\n{'='*60}")
    print(f"Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}\n")
    
    return failed_tests == 0

if __name__ == "__main__":
    print_header("Christian Cleanup - System Health Check")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_tests = []
    
    # Run all test suites
    all_tests.append(test_imports())
    all_tests.append(test_database_connection())
    all_tests.append(test_redis_connection())
    all_tests.append(test_web_service())
    all_tests.append(test_analyzer_functionality())
    all_tests.append(test_environment_config())
    all_tests.append(test_no_legacy_code())
    
    # Generate report
    success = generate_report(all_tests)
    
    sys.exit(0 if success else 1)

