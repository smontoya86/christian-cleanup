#!/usr/bin/env python3
"""
Test script to diagnose the settings route internal server error
"""

import os
import sys

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models.models import User
from app.extensions import db
import traceback

def test_settings_route():
    """Test the settings route functionality"""
    app = create_app()
    
    with app.app_context():
        try:
            print("Testing settings route components...")
            
            # Test User model access
            print("1. Testing User model...")
            user_count = User.query.count()
            print(f"   Found {user_count} users in database")
            
            # Test getting a sample user
            print("2. Testing user retrieval...")
            sample_user = User.query.first()
            if sample_user:
                print(f"   Sample user: {sample_user.display_name} ({sample_user.spotify_id})")
                
                # Test user attributes that are used in the template
                print("3. Testing user attributes...")
                attrs_to_check = [
                    'display_name', 'email', 'spotify_id', 'created_at', 
                    'updated_at', 'token_expiry', 'is_token_expired'
                ]
                
                for attr in attrs_to_check:
                    try:
                        value = getattr(sample_user, attr)
                        print(f"   {attr}: {value}")
                    except AttributeError as e:
                        print(f"   ERROR - {attr}: {e}")
                    except Exception as e:
                        print(f"   ERROR - {attr}: {e}")
                        
            else:
                print("   No users found in database")
                
            # Test template rendering (without actual request)
            print("4. Testing template existence...")
            template_path = "app/templates/user_settings.html"
            if os.path.exists(template_path):
                print(f"   Template exists: {template_path}")
            else:
                print(f"   Template missing: {template_path}")
                
            print("\nSettings route diagnostic complete!")
            
        except Exception as e:
            print(f"Error during settings route test: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    test_settings_route() 