#!/usr/bin/env python3
"""
Test Dashboard Live - Check what's happening in the browser
"""

import sys
import os
import time
import json
import requests
from datetime import datetime

def test_dashboard_live():
    """Test the dashboard in a live environment"""
    print("🌐 TESTING DASHBOARD LIVE")
    print("=" * 50)
    
    # Try different URLs depending on where we're running from
    urls_to_try = [
        "http://web:5000",  # From inside Docker container
        "http://localhost:5001",  # From host machine
        "http://127.0.0.1:5001"  # Alternative host
    ]
    
    base_url = None
    for url in urls_to_try:
        try:
            response = requests.get(f"{url}/health", timeout=2)
            if response.status_code == 200:
                base_url = url
                print(f"✅ Found working URL: {base_url}")
                break
        except:
            continue
    
    if not base_url:
        print("❌ Could not find a working URL for the application")
        return
    
    print("\n1. TESTING API ENDPOINT ACCESSIBILITY")
    print("-" * 40)
    
    # Test the API endpoint directly
    try:
        response = requests.get(f"{base_url}/api/analysis/status", timeout=10)
        print(f"API Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ API endpoint is accessible!")
            print(f"Response data: {json.dumps(data, indent=2)}")
            
            # Check if we should show progress
            should_show = data.get('has_active_analysis', False) or (data.get('pending', 0) > 0)
            print(f"\nShould show progress indicator: {should_show}")
            print(f"  - has_active_analysis: {data.get('has_active_analysis', False)}")
            print(f"  - pending songs: {data.get('pending', 0)}")
            
        elif response.status_code == 401:
            print("⚠️  API requires authentication (expected for unauthenticated request)")
            print("This means the endpoint exists but requires login")
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Could not reach API endpoint: {e}")
        return
    
    print("\n2. TESTING DASHBOARD PAGE")
    print("-" * 40)
    
    try:
        response = requests.get(f"{base_url}/dashboard", timeout=10)
        print(f"Dashboard Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Dashboard page is accessible!")
            
            # Check if the progress indicator elements are in the HTML
            html_content = response.text
            
            elements_to_check = [
                'analysisProgressAlert',
                'analysisProgress',
                'analysisCompleted',
                'analysisInProgress',
                'analysisPending',
                'currentAnalysis',
                'recentAnalysis'
            ]
            
            print("\nChecking for progress indicator elements in HTML:")
            for element_id in elements_to_check:
                if f'id="{element_id}"' in html_content:
                    print(f"  ✅ {element_id} found")
                else:
                    print(f"  ❌ {element_id} missing")
            
            # Check for JavaScript functions
            js_functions = [
                'updateAnalysisProgress',
                'checkAnalysisStatus',
                'hideAnalysisProgress'
            ]
            
            print("\nChecking for JavaScript functions:")
            for func_name in js_functions:
                if f'function {func_name}' in html_content:
                    print(f"  ✅ {func_name} found")
                else:
                    print(f"  ❌ {func_name} missing")
            
            # Check if the monitoring is set up
            if 'analysisCheckInterval = setInterval(checkAnalysisStatus, 3000)' in html_content:
                print("  ✅ Analysis monitoring interval found")
            else:
                print("  ❌ Analysis monitoring interval missing")
                
        elif response.status_code == 302:
            print("⚠️  Dashboard redirects (probably to login page)")
            print("This means authentication is required")
        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Could not reach dashboard: {e}")
    
    print("\n3. MANUAL TESTING INSTRUCTIONS")
    print("-" * 40)
    print("🎯 To test the dashboard manually:")
    print("1. Open your browser and go to: http://localhost:5001")
    print("2. Log in with your Spotify account")
    print("3. Go to the dashboard")
    print("4. Open browser Developer Tools (F12)")
    print("5. Go to the Console tab")
    print("6. Look for these messages:")
    print("   - 'updateAnalysisProgress called with: ...'")
    print("   - 'Analysis progress: X/Y (Z in progress, W pending)'")
    print("   - Any error messages")
    print("7. Go to the Network tab")
    print("8. Look for requests to '/api/analysis/status'")
    print("9. Check if they return 200 OK with data")
    
    print("\n4. DEBUGGING CHECKLIST")
    print("-" * 40)
    print("If the progress indicator is not showing:")
    print("□ Check browser console for JavaScript errors")
    print("□ Check Network tab for failed API requests")
    print("□ Verify you're logged in (check for 401 errors)")
    print("□ Check if 'analysisProgressAlert' element exists in DOM")
    print("□ Check if the element has 'display: none' style")
    print("□ Verify API returns has_active_analysis=true or pending>0")
    print("□ Check if updateAnalysisProgress function is being called")
    
    print("\n5. QUICK FIX TEST")
    print("-" * 40)
    print("To force the progress indicator to show:")
    print("1. Open browser console on the dashboard")
    print("2. Run this JavaScript:")
    print("   document.getElementById('analysisProgressAlert').style.display = 'block';")
    print("3. If it appears, the issue is with the show/hide logic")
    print("4. If it doesn't appear, the HTML elements are missing")
    
    print("\n" + "=" * 50)
    print("✅ LIVE TESTING COMPLETE")

if __name__ == "__main__":
    test_dashboard_live() 