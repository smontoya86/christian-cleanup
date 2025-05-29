#!/usr/bin/env python3
"""
Test script to test the actual settings template rendering
"""

import os
import sys

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models.models import User
from app.extensions import db
from flask import render_template_string, render_template
import traceback

def test_settings_template_render():
    """Test the settings template rendering"""
    app = create_app()
    
    with app.app_context():
        try:
            print("Testing settings template rendering...")
            
            # Get a sample user
            sample_user = User.query.first()
            if not sample_user:
                print("No users found in database")
                return
                
            print(f"Testing with user: {sample_user.display_name}")
            
            # Try to render the template
            print("Attempting to render user_settings.html...")
            
            # Create a test request context
            with app.test_request_context():
                try:
                    rendered = render_template('user_settings.html', user=sample_user)
                    print("Template rendered successfully!")
                    print(f"Rendered template length: {len(rendered)} characters")
                    
                    # Check if the template contains expected content
                    if 'User Settings' in rendered:
                        print("✓ Template contains 'User Settings' title")
                    else:
                        print("✗ Template missing 'User Settings' title")
                        
                    if sample_user.display_name in rendered:
                        print(f"✓ Template contains user display name: {sample_user.display_name}")
                    else:
                        print(f"✗ Template missing user display name: {sample_user.display_name}")
                        
                except Exception as template_error:
                    print(f"Template rendering error: {template_error}")
                    print("Full traceback:")
                    traceback.print_exc()
                    
                    # Try a minimal template test
                    print("\nTrying minimal template test...")
                    try:
                        minimal = render_template_string('<h1>Test</h1>')
                        print("Minimal template works")
                    except Exception as minimal_error:
                        print(f"Even minimal template fails: {minimal_error}")
                        
        except Exception as e:
            print(f"Error during template test: {e}")
            traceback.print_exc()

if __name__ == "__main__":
    test_settings_template_render() 