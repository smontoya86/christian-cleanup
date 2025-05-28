#!/usr/bin/env python3
"""
Debug API Response - Check exact data being returned
"""

import sys
import os
import json

# Add the app directory to the Python path
sys.path.append('/app')

def debug_api_response():
    """Debug the exact API response and shouldShow logic"""
    print("🔍 DEBUGGING API RESPONSE")
    print("=" * 50)
    
    try:
        from app import create_app, db
        from app.models import User
        from app.services.background_analysis_service import BackgroundAnalysisService
        
        app = create_app()
        
        with app.app_context():
            user = db.session.query(User).first()
            if not user:
                print("❌ No users found")
                return
            
            print(f"Testing with user: {user.display_name}")
            
            # Get the exact API response
            data = BackgroundAnalysisService.get_analysis_progress_for_user(user.id)
            
            print("\n📊 API Response:")
            for key, value in data.items():
                print(f"  {key}: {value} (type: {type(value).__name__})")
            
            print(f"\n🎯 Should Show Logic:")
            has_active = data.get('has_active_analysis', False)
            pending = data.get('pending', 0)
            pending_check = pending > 0
            should_show = has_active or pending_check
            
            print(f"  has_active_analysis: {has_active} (type: {type(has_active).__name__})")
            print(f"  pending: {pending} (type: {type(pending).__name__})")
            print(f"  pending > 0: {pending_check}")
            print(f"  should_show: {should_show}")
            
            if should_show:
                print("✅ Progress indicator SHOULD be visible")
            else:
                print("❌ Progress indicator should be hidden")
                
            # Test JavaScript logic simulation
            print(f"\n🔧 JavaScript Logic Simulation:")
            print(f"  data.has_active_analysis: {data.get('has_active_analysis')}")
            print(f"  data.pending: {data.get('pending')}")
            print(f"  data.pending && data.pending > 0: {data.get('pending') and data.get('pending') > 0}")
            js_should_show = data.get('has_active_analysis') or (data.get('pending') and data.get('pending') > 0)
            print(f"  JavaScript shouldShow: {js_should_show}")
            
            if js_should_show != should_show:
                print("⚠️  MISMATCH between Python and JavaScript logic!")
            else:
                print("✅ Python and JavaScript logic match")
                
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_api_response() 