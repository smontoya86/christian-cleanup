#!/usr/bin/env python3
"""
Test Dashboard Access
Check if the dashboard and progress indicators are working
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from requests.auth import HTTPBasicAuth
import json

def test_dashboard_access():
    """Test dashboard access and progress indicators"""
    print("🧪 TESTING DASHBOARD ACCESS")
    print("=" * 50)
    
    base_url = "http://localhost:5001"
    
    # Test if Flask app is running
    print("\n1. TESTING FLASK APP CONNECTIVITY")
    print("-" * 40)
    
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Flask app is running and healthy")
        else:
            print(f"⚠️  Flask app returned status {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Flask app is not accessible: {e}")
        print("Please make sure the Flask app is running with: python run.py")
        return
    
    # Test dashboard access (will redirect to login)
    print("\n2. TESTING DASHBOARD ACCESS")
    print("-" * 40)
    
    try:
        response = requests.get(f"{base_url}/dashboard", timeout=5, allow_redirects=False)
        if response.status_code == 302:
            print("✅ Dashboard requires authentication (as expected)")
            print(f"   Redirects to: {response.headers.get('Location', 'unknown')}")
        elif response.status_code == 200:
            print("⚠️  Dashboard is accessible without authentication")
        else:
            print(f"⚠️  Dashboard returned unexpected status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Could not access dashboard: {e}")
    
    # Test API endpoints (will require authentication)
    print("\n3. TESTING API ENDPOINTS")
    print("-" * 40)
    
    endpoints = [
        "/api/sync-status",
        "/api/analysis/status"
    ]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code == 401:
                print(f"✅ {endpoint} requires authentication (as expected)")
            elif response.status_code == 200:
                print(f"⚠️  {endpoint} is accessible without authentication")
                try:
                    data = response.json()
                    print(f"   Response: {json.dumps(data, indent=2)}")
                except:
                    print(f"   Response: {response.text[:100]}...")
            else:
                print(f"⚠️  {endpoint} returned status {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Could not access {endpoint}: {e}")
    
    print("\n4. CHECKING PROGRESS INDICATOR SETUP")
    print("-" * 40)
    
    # Check if we have in-progress analyses
    from app import create_app, db
    from app.models import AnalysisResult, Song
    
    app = create_app()
    with app.app_context():
        total_songs = db.session.query(Song).count()
        completed = db.session.query(AnalysisResult).filter_by(status='completed').count()
        in_progress = db.session.query(AnalysisResult).filter_by(status='in_progress').count()
        pending = total_songs - completed - in_progress
        
        print(f"Database status:")
        print(f"   Total songs: {total_songs}")
        print(f"   Completed analyses: {completed}")
        print(f"   In progress analyses: {in_progress}")
        print(f"   Pending analyses: {pending}")
        
        if in_progress > 0:
            print("✅ In-progress analyses found - progress indicator should be visible")
        else:
            print("ℹ️  No in-progress analyses - progress indicator will be hidden")
            print("   Run: python scripts/create_persistent_analysis.py to create test data")
    
    print("\n5. INSTRUCTIONS FOR TESTING")
    print("-" * 40)
    print("🎯 To see the progress indicators:")
    print("   1. Make sure you're logged into the app at http://localhost:5001")
    print("   2. Go to the dashboard at http://localhost:5001/dashboard")
    print("   3. If you have in-progress analyses, you should see:")
    print("      • 'Song Analysis in Progress' alert with yellow background")
    print("      • Progress bar showing completion percentage")
    print("      • Current song being analyzed")
    print("      • Processing rate and ETA")
    print("      • Recent completed analyses")
    print("   4. The indicator updates every 3 seconds automatically")
    print("   5. To trigger a sync progress indicator:")
    print("      • Click 'Sync Playlists' button on the dashboard")
    print("      • You should see 'Playlist Sync in Progress' alert")
    
    print("\n" + "=" * 50)
    print("✅ DASHBOARD ACCESS TEST COMPLETE")
    
    if in_progress > 0:
        print("\n🎉 You should be able to see the progress indicators now!")
        print("   Go to http://localhost:5001/dashboard (after logging in)")
    else:
        print("\n💡 To see the progress indicators in action:")
        print("   Run: python scripts/create_persistent_analysis.py")
        print("   Then go to the dashboard to see the indicators")

if __name__ == "__main__":
    test_dashboard_access() 