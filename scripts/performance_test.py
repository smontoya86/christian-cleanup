#!/usr/bin/env python3
"""
Performance Testing Script for Christian Music Curator
Tests page load times, database queries, and API endpoints
"""

import time
import requests
import statistics
from app import create_app
from app.models import Song, AnalysisResult, Playlist, PlaylistSong
from app.extensions import db

def test_endpoint(url, name, runs=5):
    """Test an endpoint multiple times and return statistics"""
    times = []
    for i in range(runs):
        start = time.time()
        try:
            response = requests.get(url, timeout=10)
            end = time.time()
            if response.status_code == 200:
                times.append((end - start) * 1000)  # Convert to milliseconds
            else:
                print(f"  ❌ {name} returned status {response.status_code}")
                return None
        except Exception as e:
            print(f"  ❌ {name} failed: {e}")
            return None
    
    if times:
        avg = statistics.mean(times)
        median = statistics.median(times)
        min_time = min(times)
        max_time = max(times)
        return {
            'avg': avg,
            'median': median,
            'min': min_time,
            'max': max_time,
            'times': times
        }
    return None

def test_database_queries():
    """Test database query performance"""
    print("\n🗄️  DATABASE QUERY PERFORMANCE")
    print("=" * 50)
    
    app = create_app()
    with app.app_context():
        queries = [
            ("Count all songs", lambda: db.session.query(Song).count()),
            ("Count completed analysis", lambda: db.session.query(AnalysisResult).filter(AnalysisResult.status == 'completed').count()),
            ("Count playlists", lambda: db.session.query(Playlist).count()),
            ("Get recent analysis (5)", lambda: db.session.query(AnalysisResult).order_by(AnalysisResult.created_at.desc()).limit(5).all()),
            ("Get playlist with songs", lambda: db.session.query(Playlist).join(PlaylistSong).limit(1).first()),
            ("Complex join query", lambda: db.session.query(Song, AnalysisResult).join(AnalysisResult).limit(10).all()),
        ]
        
        for name, query_func in queries:
            times = []
            for _ in range(5):
                start = time.time()
                try:
                    result = query_func()
                    end = time.time()
                    times.append((end - start) * 1000)
                except Exception as e:
                    print(f"  ❌ {name}: Error - {e}")
                    continue
            
            if times:
                avg = statistics.mean(times)
                print(f"  ✅ {name}: {avg:.1f}ms avg (min: {min(times):.1f}ms, max: {max(times):.1f}ms)")

def test_web_performance():
    """Test web page and API performance"""
    print("\n🌐 WEB PAGE & API PERFORMANCE")
    print("=" * 50)
    
    base_url = "http://localhost:5001"
    
    endpoints = [
        ("/", "Home Page"),
        ("/health", "Health Check"),
        ("/dashboard", "Dashboard"),
        ("/playlist/3", "Playlist Detail"),
        ("/api/analysis/progress", "Progress API"),
        ("/api/analysis/performance", "Performance API"),
        ("/api/playlists/3/analysis-status", "Analysis Status API"),
    ]
    
    for endpoint, name in endpoints:
        url = f"{base_url}{endpoint}"
        result = test_endpoint(url, name)
        
        if result:
            if result['avg'] < 50:
                status = "🟢 Excellent"
            elif result['avg'] < 200:
                status = "🟡 Good"
            elif result['avg'] < 1000:
                status = "🟠 Acceptable"
            else:
                status = "🔴 Slow"
                
            print(f"  {status} {name}: {result['avg']:.1f}ms avg (min: {result['min']:.1f}ms, max: {result['max']:.1f}ms)")

def test_concurrent_requests():
    """Test how the app handles concurrent requests"""
    print("\n⚡ CONCURRENT REQUEST PERFORMANCE")
    print("=" * 50)
    
    import threading
    import queue
    
    def make_request(url, result_queue):
        start = time.time()
        try:
            response = requests.get(url, timeout=10)
            end = time.time()
            result_queue.put((end - start) * 1000)
        except Exception as e:
            result_queue.put(None)
    
    # Test concurrent dashboard requests
    url = "http://localhost:5001/dashboard"
    result_queue = queue.Queue()
    threads = []
    
    # Start 10 concurrent requests
    start_time = time.time()
    for i in range(10):
        thread = threading.Thread(target=make_request, args=(url, result_queue))
        threads.append(thread)
        thread.start()
    
    # Wait for all to complete
    for thread in threads:
        thread.join()
    
    total_time = (time.time() - start_time) * 1000
    
    # Collect results
    times = []
    while not result_queue.empty():
        result = result_queue.get()
        if result is not None:
            times.append(result)
    
    if times:
        avg = statistics.mean(times)
        print(f"  ✅ 10 concurrent dashboard requests:")
        print(f"     Total time: {total_time:.1f}ms")
        print(f"     Average response: {avg:.1f}ms")
        print(f"     Successful requests: {len(times)}/10")

def main():
    print("🚀 CHRISTIAN MUSIC CURATOR - PERFORMANCE TEST")
    print("=" * 60)
    
    # Test database performance
    test_database_queries()
    
    # Test web performance
    test_web_performance()
    
    # Test concurrent performance
    test_concurrent_requests()
    
    print("\n✅ Performance testing complete!")
    print("\nPerformance Guidelines:")
    print("  🟢 Excellent: < 50ms")
    print("  🟡 Good: 50-200ms") 
    print("  🟠 Acceptable: 200ms-1s")
    print("  🔴 Slow: > 1s")

if __name__ == "__main__":
    main() 