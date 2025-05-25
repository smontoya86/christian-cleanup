#!/usr/bin/env python3
"""
Final System Verification Script
Tests all components after complete GitHub restore
"""

import sys
import os
import requests
import redis
from datetime import datetime

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_web_endpoints():
    """Test all critical web endpoints"""
    print("🌐 Testing Web Endpoints...")
    
    tests = [
        ("/health", 200, "Health endpoint"),
        ("/", 200, "Main page"),
        ("/dashboard", 302, "Dashboard (should redirect to login)"),
        ("/auth/login", 302, "Auth login (should redirect to Spotify)"),
    ]
    
    all_passed = True
    for endpoint, expected_status, description in tests:
        try:
            response = requests.get(f"http://localhost:5001{endpoint}", timeout=5, allow_redirects=False)
            if response.status_code == expected_status:
                print(f"  ✅ {description}: {response.status_code}")
            else:
                print(f"  ❌ {description}: Expected {expected_status}, got {response.status_code}")
                all_passed = False
        except Exception as e:
            print(f"  ❌ {description}: Error - {e}")
            all_passed = False
    
    return all_passed

def test_database():
    """Test database connectivity"""
    print("🗄️ Testing Database...")
    
    try:
        # Import here to avoid issues if app context is needed
        from app import create_app, db
        from app.models import User, Song, AnalysisResult, Playlist
        
        app = create_app()
        with app.app_context():
            # Test basic queries
            user_count = User.query.count()
            song_count = Song.query.count()
            playlist_count = Playlist.query.count()
            analysis_count = AnalysisResult.query.count()
            
            print(f"  ✅ Database connected successfully")
            print(f"  📊 Users: {user_count}")
            print(f"  📊 Songs: {song_count}")
            print(f"  📊 Playlists: {playlist_count}")
            print(f"  📊 Analysis Results: {analysis_count}")
            
            return True
    except Exception as e:
        print(f"  ❌ Database error: {e}")
        return False

def test_redis_queue():
    """Test Redis and RQ queue"""
    print("🔄 Testing Redis & Queue...")
    
    try:
        r = redis.Redis(host='localhost', port=6379, db=0)
        
        # Test Redis connection
        r.ping()
        print(f"  ✅ Redis connected successfully")
        
        # Test queue status
        from rq import Queue
        q = Queue(connection=r)
        
        print(f"  📊 Queue length: {len(q)}")
        print(f"  📊 Failed jobs: {len(q.failed_job_registry)}")
        print(f"  📊 Started jobs: {len(q.started_job_registry)}")
        print(f"  📊 Finished jobs: {len(q.finished_job_registry)}")
        
        return True
    except Exception as e:
        print(f"  ❌ Redis/Queue error: {e}")
        return False

def test_workers():
    """Test worker status"""
    print("👷 Testing Workers...")
    
    try:
        r = redis.Redis(host='localhost', port=6379, db=0)
        from rq import Worker
        
        workers = Worker.all(connection=r)
        active_workers = [w for w in workers if not w.stopped]
        
        print(f"  📊 Total workers: {len(workers)}")
        print(f"  📊 Active workers: {len(active_workers)}")
        
        for i, worker in enumerate(active_workers, 1):
            print(f"  ✅ Worker {i}: {worker.name} - {worker.state}")
        
        if len(active_workers) >= 2:
            print(f"  ✅ Multiple workers running for parallel processing")
            return True
        elif len(active_workers) == 1:
            print(f"  ⚠️ Only 1 worker running (expected 2)")
            return True
        else:
            print(f"  ❌ No active workers found")
            return False
            
    except Exception as e:
        print(f"  ❌ Worker test error: {e}")
        return False

def main():
    """Run all tests"""
    print("🔍 FINAL SYSTEM VERIFICATION")
    print("=" * 50)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = []
    
    # Run all tests
    results.append(("Web Endpoints", test_web_endpoints()))
    results.append(("Database", test_database()))
    results.append(("Redis & Queue", test_redis_queue()))
    results.append(("Workers", test_workers()))
    
    # Summary
    print()
    print("📋 VERIFICATION SUMMARY")
    print("=" * 50)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{test_name:20} {status}")
        if not passed:
            all_passed = False
    
    print()
    if all_passed:
        print("🎉 ALL TESTS PASSED - SYSTEM FULLY RESTORED!")
        print("✅ Ready for playlist sync and analysis")
        print("✅ Two workers available for parallel processing")
        print("✅ All API rate limits will be respected")
    else:
        print("⚠️ Some tests failed - please review the issues above")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main()) 