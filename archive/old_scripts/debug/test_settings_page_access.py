#!/usr/bin/env python3
"""
Test script to verify settings page is accessible via HTTP request
"""

import os
import sys

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models.models import User
from app.extensions import db
import traceback

def test_settings_page_access():
    """Test accessing the settings page via HTTP request"""
    app = create_app()
    
    with app.app_context():
        try:
            print("Testing settings page HTTP access...")
            
            # Get a sample user for testing
            user = User.query.first()
            if not user:
                print("No users found in database")
                return
                
            print(f"Testing with user: {user.display_name}")
            
            # Create a test client
            with app.test_client() as client:
                # Simulate login by setting session
                with client.session_transaction() as sess:
                    sess['_user_id'] = str(user.id)
                    sess['_fresh'] = True
                    
                print("1. Testing GET /settings...")
                response = client.get('/settings')
                print(f"   Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    print("   ✅ Settings page loads successfully")
                    
                    # Check for key content
                    data = response.get_data(as_text=True)
                    
                    checks = [
                        ('User Settings', 'Page title'),
                        ('Admin Controls', 'Admin section'),
                        ('Re-sync All Playlists', 'Re-sync functionality'),
                        ('Re-analyze All Songs', 'Re-analysis functionality'),
                        ('Profile Settings', 'Profile section'),
                        ('Account Statistics', 'Statistics section')
                    ]
                    
                    for check_text, description in checks:
                        if check_text in data:
                            print(f"   ✅ {description} present")
                        else:
                            print(f"   ❌ {description} missing")
                            
                    # Test form elements
                    form_elements = [
                        ('display_name', 'Display name input'),
                        ('email', 'Email input'),
                        ('admin/resync-all-playlists', 'Re-sync form action'),
                        ('admin/reanalyze-all-songs', 'Re-analysis form action')
                    ]
                    
                    for element, description in form_elements:
                        if element in data:
                            print(f"   ✅ {description} present")
                        else:
                            print(f"   ❌ {description} missing")
                            
                elif response.status_code == 302:
                    print(f"   ⚠️  Redirect to: {response.location}")
                else:
                    print(f"   ❌ Unexpected status code: {response.status_code}")
                    print(f"   Response data: {response.get_data(as_text=True)[:500]}")
                    
                print("\n2. Testing admin route availability...")
                
                # Test if admin routes are accessible (should require POST)
                admin_routes = [
                    '/admin/resync-all-playlists',
                    '/admin/reanalyze-all-songs'
                ]
                
                for route in admin_routes:
                    get_response = client.get(route)
                    print(f"   GET {route}: {get_response.status_code} (expected 405 or redirect)")
                    
                print("\n✅ Settings page access test completed!")
                
        except Exception as e:
            print(f"Error during settings page test: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    test_settings_page_access() 