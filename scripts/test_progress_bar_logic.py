#!/usr/bin/env python3
"""
Test the progress bar logic and API response
"""

import os
import sys
import json

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models.models import User

def test_progress_bar_logic():
    """Test if the progress bar should be visible with current data"""
    app = create_app()
    
    with app.app_context():
        try:
            print("=" * 80)
            print("PROGRESS BAR LOGIC TEST")
            print("=" * 80)
            
            user = User.query.first()
            if not user:
                print("❌ No users found")
                return
                
            print(f"\n📊 Testing for user: {user.display_name}")
            
            # Test the API endpoint directly
            with app.test_client() as client:
                # Simulate login
                with client.session_transaction() as sess:
                    sess['_user_id'] = str(user.id)
                    sess['_fresh'] = True
                
                response = client.get('/api/analysis/status')
                print(f"\n🌐 API Response Status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.get_json()
                    print(f"\n📈 API Response Data:")
                    print(f"   Total Songs: {data.get('total_songs', 0)}")
                    print(f"   Completed: {data.get('completed', 0)}")
                    print(f"   In Progress: {data.get('in_progress', 0)}")
                    print(f"   Pending: {data.get('pending', 0)}")
                    print(f"   Progress %: {data.get('progress_percentage', 0)}")
                    print(f"   Has Active Analysis: {data.get('has_active_analysis', False)}")
                    
                    # Simulate JavaScript logic
                    total_songs = data.get('total_songs', 0)
                    completed = data.get('completed', 0)
                    in_progress = data.get('in_progress', 0)
                    pending = data.get('pending', 0)
                    has_active_analysis = data.get('has_active_analysis', False)
                    progress_percentage = data.get('progress_percentage', 0)
                    
                    print(f"\n🔍 Progress Bar Visibility Logic:")
                    
                    has_data = total_songs > 0
                    has_in_progress = in_progress > 0
                    has_pending = pending > 0
                    total_progress = progress_percentage
                    
                    print(f"   has_data: {has_data} (total_songs: {total_songs})")
                    print(f"   has_in_progress: {has_in_progress} (in_progress: {in_progress})")
                    print(f"   has_pending: {has_pending} (pending: {pending})")
                    print(f"   has_active_analysis: {has_active_analysis}")
                    print(f"   total_progress: {total_progress}% (< 100: {total_progress < 100})")
                    
                    should_show = has_data and (has_in_progress or has_pending or has_active_analysis or total_progress < 100)
                    
                    print(f"\n🎯 RESULT: Progress bar should {'SHOW' if should_show else 'HIDE'}")
                    
                    if should_show:
                        print("   ✅ Progress bar should be visible")
                        if total_progress < 1:
                            print("   ⚠️  Very low progress - this is expected after re-analysis")
                        else:
                            print(f"   📊 Normal progress display: {total_progress:.1f}%")
                    else:
                        print("   ❌ Progress bar should be hidden")
                        print("   🔧 Check these conditions:")
                        print(f"      - Has data: {has_data}")
                        print(f"      - Has work to do: {has_in_progress or has_pending or has_active_analysis or total_progress < 100}")
                
                else:
                    print(f"❌ API Error: {response.get_data(as_text=True)}")
            
            print("\n" + "=" * 80)
            print("TEST COMPLETE")
            print("=" * 80)
            
        except Exception as e:
            print(f"❌ Error during test: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_progress_bar_logic() 