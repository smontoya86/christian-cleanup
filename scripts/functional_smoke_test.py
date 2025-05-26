#!/usr/bin/env python3
"""
Functional Smoke Test
Quick test to verify the application starts and serves basic pages
"""

import sys
import os
import time
import requests
import subprocess
import signal
from threading import Thread

sys.path.append('/app')

def start_flask_app():
    """Start the Flask application in the background"""
    try:
        # Start the Flask app
        process = subprocess.Popen(
            ['python', 'run.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd='/Users/sammontoya/christian cleanup windsurf'
        )
        return process
    except Exception as e:
        print(f"❌ Failed to start Flask app: {e}")
        return None

def test_endpoints():
    """Test basic endpoints"""
    base_url = 'http://127.0.0.1:5001'
    
    # Wait for app to start
    print("⏳ Waiting for application to start...")
    time.sleep(3)
    
    test_results = []
    
    # Test endpoints
    endpoints = [
        ('/', 'Home Page'),
        ('/auth/login', 'Login Page'),
    ]
    
    for endpoint, name in endpoints:
        try:
            response = requests.get(f"{base_url}{endpoint}", timeout=5)
            if response.status_code in [200, 302]:  # 302 for redirects
                test_results.append(f"✅ {name}: HTTP {response.status_code}")
            else:
                test_results.append(f"❌ {name}: HTTP {response.status_code}")
        except requests.exceptions.RequestException as e:
            test_results.append(f"❌ {name}: Connection failed - {str(e)}")
    
    return test_results

def main():
    print("🧪 FUNCTIONAL SMOKE TEST")
    print("=" * 50)
    
    # Start Flask app
    app_process = start_flask_app()
    
    if not app_process:
        print("❌ Failed to start application")
        return False
    
    try:
        # Test endpoints
        results = test_endpoints()
        
        # Print results
        print("\n📊 SMOKE TEST RESULTS:")
        print("-" * 30)
        for result in results:
            print(result)
        
        # Check if all tests passed
        passed = all("✅" in result for result in results)
        
        if passed:
            print("\n🎉 SMOKE TEST PASSED!")
            print("Application is serving pages correctly.")
        else:
            print("\n🚨 SMOKE TEST FAILED!")
            print("Some endpoints are not responding correctly.")
        
        return passed
        
    finally:
        # Clean up - terminate the Flask app
        try:
            app_process.terminate()
            app_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            app_process.kill()
        except Exception:
            pass

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 