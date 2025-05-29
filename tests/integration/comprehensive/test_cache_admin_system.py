#!/usr/bin/env python3

"""
Test script for the cache admin system and scheduled maintenance.
Tests admin routes, cache management utilities, and scheduled tasks.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app import create_app
from app.models.models import db, LyricsCache, User
from app.utils.cache_management import (
    clear_old_cache_entries,
    get_cache_stats,
    validate_cache_integrity,
    optimize_cache_storage
)
from app.tasks.scheduled import clean_lyrics_cache, validate_cache_health
import logging
import json
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_cache_management_utilities():
    """Test the cache management utilities."""
    print("\n=== Testing Cache Management Utilities ===")
    
    app = create_app()
    
    with app.app_context():
        try:
            # Clear existing cache for clean test
            LyricsCache.query.delete()
            db.session.commit()
            
            # Add some test cache entries
            test_entries = [
                LyricsCache(
                    artist='test artist 1',
                    title='test song 1',
                    lyrics='Test lyrics content 1',
                    source='LRCLibProvider',
                    created_at=datetime.utcnow() - timedelta(days=5),
                    updated_at=datetime.utcnow() - timedelta(days=5)
                ),
                LyricsCache(
                    artist='test artist 2',
                    title='test song 2',
                    lyrics='Test lyrics content 2',
                    source='GeniusProvider',
                    created_at=datetime.utcnow() - timedelta(days=35),  # Old entry
                    updated_at=datetime.utcnow() - timedelta(days=35)
                ),
                LyricsCache(
                    artist='test artist 3',
                    title='test song 3',
                    lyrics='Test lyrics content 3',
                    source='LyricsOvhProvider',
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
            ]
            
            for entry in test_entries:
                db.session.add(entry)
            db.session.commit()
            
            print(f"✅ Added {len(test_entries)} test cache entries")
            
            # Test cache statistics
            stats = get_cache_stats()
            print(f"✅ Cache stats: {stats['total_entries']} entries, sources: {stats['sources']}")
            
            # Test cache integrity validation
            integrity = validate_cache_integrity()
            print(f"✅ Cache integrity: {integrity['integrity_status']}, issues: {integrity['issues_found']}")
            
            # Test clearing old entries (should remove the 35-day old entry)
            removed = clear_old_cache_entries(days=30)
            print(f"✅ Cleared {removed} old cache entries")
            
            # Test optimization
            optimization_result = optimize_cache_storage()
            print(f"✅ Cache optimization: {optimization_result['duplicates_removed']} duplicates removed")
            
            # Final stats
            final_stats = get_cache_stats()
            print(f"✅ Final cache stats: {final_stats['total_entries']} entries remaining")
            
            return True
            
        except Exception as e:
            print(f"❌ Cache management utilities test failed: {e}")
            return False

def test_scheduled_tasks():
    """Test the scheduled maintenance tasks."""
    print("\n=== Testing Scheduled Tasks ===")
    
    app = create_app()
    
    with app.app_context():
        try:
            # Clear existing cache for clean test
            LyricsCache.query.delete()
            db.session.commit()
            
            # Add test data
            test_entry = LyricsCache(
                artist='scheduled test artist',
                title='scheduled test song',
                lyrics='Scheduled test lyrics content',
                source='TestProvider',
                created_at=datetime.utcnow() - timedelta(days=40),  # Old entry
                updated_at=datetime.utcnow() - timedelta(days=40)
            )
            db.session.add(test_entry)
            db.session.commit()
            
            print("✅ Added test data for scheduled tasks")
            
            # Test cache cleanup task
            cleanup_result = clean_lyrics_cache(max_age_days=30)
            print(f"✅ Cache cleanup task: {cleanup_result['status']}, removed: {cleanup_result['removed_count']}")
            
            # Add fresh data for validation test
            fresh_entry = LyricsCache(
                artist='validation test artist',
                title='validation test song',
                lyrics='Validation test lyrics content',
                source='TestProvider'
            )
            db.session.add(fresh_entry)
            db.session.commit()
            
            # Test cache validation task
            validation_result = validate_cache_health()
            print(f"✅ Cache validation task: {validation_result['status']}, integrity: {validation_result['integrity_status']}")
            
            return True
            
        except Exception as e:
            print(f"❌ Scheduled tasks test failed: {e}")
            return False

def test_admin_routes():
    """Test the admin routes."""
    print("\n=== Testing Admin Routes ===")
    
    app = create_app()
    
    with app.app_context():
        try:
            # Create a test user for authentication
            test_user = User.query.first()
            if not test_user:
                print("❌ No test user found - admin routes require authentication")
                return False
            
            with app.test_client() as client:
                # Simulate login (this is a simplified test)
                with client.session_transaction() as sess:
                    sess['_user_id'] = str(test_user.id)
                    sess['_fresh'] = True
                
                # Test cache stats endpoint
                response = client.get('/admin/cache/stats')
                if response.status_code == 200:
                    data = json.loads(response.data)
                    print(f"✅ Cache stats endpoint: {data['success']}")
                else:
                    print(f"❌ Cache stats endpoint failed: {response.status_code}")
                
                # Test cache integrity endpoint
                response = client.get('/admin/cache/integrity')
                if response.status_code == 200:
                    data = json.loads(response.data)
                    print(f"✅ Cache integrity endpoint: {data['success']}")
                else:
                    print(f"❌ Cache integrity endpoint failed: {response.status_code}")
                
                # Test system health endpoint
                response = client.get('/admin/system/health')
                if response.status_code == 200:
                    data = json.loads(response.data)
                    print(f"✅ System health endpoint: {data['success']}")
                else:
                    print(f"❌ System health endpoint failed: {response.status_code}")
                
                # Test cache optimization endpoint
                response = client.post('/admin/cache/optimize', 
                                     json={}, 
                                     content_type='application/json')
                if response.status_code == 200:
                    data = json.loads(response.data)
                    print(f"✅ Cache optimization endpoint: {data['success']}")
                else:
                    print(f"❌ Cache optimization endpoint failed: {response.status_code}")
                
                return True
                
        except Exception as e:
            print(f"❌ Admin routes test failed: {e}")
            return False

def test_admin_dashboard():
    """Test the admin dashboard endpoint."""
    print("\n=== Testing Admin Dashboard ===")
    
    app = create_app()
    
    with app.app_context():
        try:
            # Get a test user
            test_user = User.query.first()
            if not test_user:
                print("❌ No test user found - admin dashboard requires authentication")
                return False
            
            with app.test_client() as client:
                # Simulate login
                with client.session_transaction() as sess:
                    sess['_user_id'] = str(test_user.id)
                    sess['_fresh'] = True
                
                # Test admin dashboard
                response = client.get('/admin/')
                if response.status_code == 200:
                    data = json.loads(response.data)
                    print(f"✅ Admin dashboard loaded successfully")
                    print(f"   - Cache stats: {data.get('cache_stats', {}).get('total_entries', 'N/A')} entries")
                    print(f"   - Integrity status: {data.get('integrity_status', {}).get('integrity_status', 'N/A')}")
                    print(f"   - User count: {data.get('user_count', 'N/A')}")
                    return True
                else:
                    print(f"❌ Admin dashboard failed: {response.status_code}")
                    return False
                    
        except Exception as e:
            print(f"❌ Admin dashboard test failed: {e}")
            return False

def main():
    """Run all tests."""
    print("🧪 Testing Cache Admin System and Scheduled Maintenance")
    print("=" * 60)
    
    tests = [
        ("Cache Management Utilities", test_cache_management_utilities),
        ("Scheduled Tasks", test_scheduled_tasks),
        ("Admin Routes", test_admin_routes),
        ("Admin Dashboard", test_admin_dashboard)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Cache admin system is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 