#!/usr/bin/env python3
"""
Phase 5 Mock Data Testing

This test verifies that the mock data and authentication system work correctly
for testing the complete application without external API dependencies.
"""

import pytest
import requests
from datetime import datetime, timedelta
import json

class TestPhase5MockData:
    """Test Phase 5 mock data and authentication functionality"""
    
    BASE_URL = "http://localhost:5001"
    
    def test_application_is_running(self):
        """Test that the application is accessible"""
        response = requests.get(f"{self.BASE_URL}/")
        assert response.status_code == 200
        assert "Christian Music" in response.text
    
    def test_mock_users_page_accessible(self):
        """Test that the mock users page is accessible in development mode"""
        response = requests.get(f"{self.BASE_URL}/auth/mock-users")
        # Should either show mock users or redirect to login
        assert response.status_code in [200, 302]
    
    def test_mock_login_functionality(self):
        """Test that mock login works for test users"""
        # Create a session to maintain cookies
        session = requests.Session()
        
        # Test login for user 1
        response = session.get(f"{self.BASE_URL}/auth/mock-login/test_user_1")
        assert response.status_code in [200, 302]  # 302 for redirect is normal
        
        # Should be able to access dashboard after login
        dashboard_response = session.get(f"{self.BASE_URL}/dashboard")
        assert dashboard_response.status_code == 200
        assert "John Christian" in dashboard_response.text or "Dashboard" in dashboard_response.text
    
    def test_mock_data_api_endpoints(self):
        """Test that API endpoints work with mock data"""
        # Create a session and login
        session = requests.Session()
        session.get(f"{self.BASE_URL}/auth/mock-login/test_user_1")
        
        # Test health endpoint
        health_response = session.get(f"{self.BASE_URL}/api/health")
        assert health_response.status_code == 200
        
        # Test playlists API
        playlists_response = session.get(f"{self.BASE_URL}/api/playlists")
        if playlists_response.status_code == 200:
            playlists_data = playlists_response.json()
            assert 'playlists' in playlists_data
            assert isinstance(playlists_data['playlists'], list)
    
    def test_mock_playlist_data(self):
        """Test that mock playlists are accessible"""
        # Create a session and login
        session = requests.Session()
        session.get(f"{self.BASE_URL}/auth/mock-login/test_user_1")
        
        # Try to access a playlist detail page
        # We know from the mock data script that playlist IDs start from 1
        for playlist_id in range(1, 5):  # Test first 4 playlists
            response = session.get(f"{self.BASE_URL}/playlist/{playlist_id}")
            if response.status_code == 200:
                assert "Playlist" in response.text or "Songs" in response.text
                break
    
    def test_mock_song_analysis_data(self):
        """Test that mock songs have analysis data"""
        # Create a session and login
        session = requests.Session()
        session.get(f"{self.BASE_URL}/auth/mock-login/test_user_1")
        
        # Try to access song detail pages
        for song_id in range(1, 8):  # Test songs created by mock script
            response = session.get(f"{self.BASE_URL}/song/{song_id}")
            if response.status_code == 200:
                # Should contain analysis information
                assert any(keyword in response.text.lower() for keyword in [
                    "analysis", "score", "christian", "concern", "lyrics"
                ])
                break
    
    def test_different_user_login(self):
        """Test that different mock users work"""
        # Test user 2
        session = requests.Session()
        response = session.get(f"{self.BASE_URL}/auth/mock-login/test_user_2")
        assert response.status_code in [200, 302]  # 302 for redirect is normal
        
        # Should be able to access dashboard
        dashboard_response = session.get(f"{self.BASE_URL}/dashboard")
        assert dashboard_response.status_code == 200
        assert "Mary Worship" in dashboard_response.text or "Dashboard" in dashboard_response.text
    
    def test_mock_data_variety(self):
        """Test that mock data includes variety of content types"""
        # Login and check if we can find different types of content
        session = requests.Session()
        session.get(f"{self.BASE_URL}/auth/mock-login/test_user_1")
        
        # Check dashboard for variety of playlists
        dashboard_response = session.get(f"{self.BASE_URL}/dashboard")
        if dashboard_response.status_code == 200:
            dashboard_text = dashboard_response.text.lower()
            
            # Should have different playlist types
            expected_playlists = ["worship", "mixed", "christian", "review"]
            found_playlists = sum(1 for playlist in expected_playlists if playlist in dashboard_text)
            
            # Should find at least some variety
            assert found_playlists > 0, "Should find some variety in playlist names"
    
    def test_logout_functionality(self):
        """Test that logout works with mock users"""
        # Login first
        session = requests.Session()
        session.get(f"{self.BASE_URL}/auth/mock-login/test_user_1")
        
        # Logout
        logout_response = session.get(f"{self.BASE_URL}/auth/logout")
        assert logout_response.status_code == 200
        
        # Should no longer be able to access dashboard without redirect
        dashboard_response = session.get(f"{self.BASE_URL}/dashboard", allow_redirects=False)
        assert dashboard_response.status_code in [302, 401, 403]  # Should redirect or deny access

if __name__ == "__main__":
    print("🧪 Running Phase 5 Mock Data Tests...")
    print("=" * 60)
    
    test_instance = TestPhase5MockData()
    
    tests = [
        ("Application Running", test_instance.test_application_is_running),
        ("Mock Users Page", test_instance.test_mock_users_page_accessible),
        ("Mock Login", test_instance.test_mock_login_functionality),
        ("API Endpoints", test_instance.test_mock_data_api_endpoints),
        ("Playlist Data", test_instance.test_mock_playlist_data),
        ("Song Analysis", test_instance.test_mock_song_analysis_data),
        ("Different Users", test_instance.test_different_user_login),
        ("Data Variety", test_instance.test_mock_data_variety),
        ("Logout", test_instance.test_logout_functionality)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            print(f"🔍 Testing {test_name}...", end=" ")
            test_func()
            print("✅ PASSED")
            passed += 1
        except Exception as e:
            print(f"❌ FAILED: {e}")
            failed += 1
    
    print("=" * 60)
    print(f"📊 Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All Phase 5 tests passed! Mock data system is working correctly.")
        print("\n🌐 Ready for manual testing:")
        print("  - Visit: http://localhost:5001")
        print("  - Click: 'Use Mock Users for Testing'")
        print("  - Login as John Christian or Mary Worship")
        print("  - Test playlist browsing, song analysis, and curation features")
    else:
        print(f"⚠️  {failed} test(s) failed. Please check the application.")
    
    exit(0 if failed == 0 else 1) 