#!/usr/bin/env python3
"""
Trigger Sync Progress
Start a playlist sync to demonstrate the sync progress indicators
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import time

def trigger_sync_progress():
    """Trigger a playlist sync to demonstrate the progress indicators"""
    print("🎭 TRIGGERING SYNC PROGRESS DEMONSTRATION")
    print("=" * 50)
    
    # Check if the Flask app is running
    try:
        response = requests.get('http://localhost:5001/dashboard', timeout=5)
        if response.status_code == 200:
            print("✅ Flask app is running")
        else:
            print(f"⚠️  Flask app returned status {response.status_code}")
            return
    except requests.exceptions.RequestException as e:
        print(f"❌ Flask app is not running or not accessible: {e}")
        print("Please start the Flask app with: python run.py")
        return
    
    print("\n1. CHECKING CURRENT SYNC STATUS")
    print("-" * 40)
    
    try:
        # Check current sync status
        status_response = requests.get('http://localhost:5001/api/sync/status', timeout=5)
        if status_response.status_code == 200:
            status_data = status_response.json()
            print(f"Has active sync: {status_data.get('has_active_sync', False)}")
            
            if status_data.get('has_active_sync'):
                print("⚠️  A sync is already in progress!")
                print("📊 Go to http://localhost:5001/dashboard to see the progress indicator")
                return
        else:
            print(f"⚠️  Could not check sync status: {status_response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"⚠️  Could not check sync status: {e}")
    
    print("\n2. TRIGGERING PLAYLIST SYNC")
    print("-" * 40)
    print("🚀 Starting playlist sync...")
    print("   This will trigger the sync progress indicator on the dashboard")
    
    try:
        # Trigger a playlist sync
        sync_response = requests.post('http://localhost:5001/sync-playlists', 
                                    data={}, 
                                    timeout=10,
                                    allow_redirects=False)
        
        if sync_response.status_code in [200, 302]:  # 302 is redirect after POST
            print("✅ Playlist sync triggered successfully!")
        else:
            print(f"⚠️  Sync trigger returned status {sync_response.status_code}")
            print(f"Response: {sync_response.text[:200]}...")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to trigger sync: {e}")
        return
    
    print("\n3. MONITORING SYNC PROGRESS")
    print("-" * 40)
    print("📊 Go to your dashboard at http://localhost:5001/dashboard")
    print("🎯 You should now see the 'Playlist Sync in Progress' indicator!")
    print("⏱️  The indicator will show:")
    print("   • Elapsed time and ETA")
    print("   • Progress bar with percentage")
    print("   • Processed/Remaining counts")
    print("   • Processing rate")
    
    # Monitor the sync progress
    print("\n🔄 Monitoring sync progress for 60 seconds...")
    print("   (The sync progress will update every 2 seconds)")
    
    start_time = time.time()
    last_status = None
    
    try:
        while time.time() - start_time < 60:  # Monitor for 60 seconds
            try:
                status_response = requests.get('http://localhost:5001/api/sync/status', timeout=5)
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    
                    if status_data.get('has_active_sync'):
                        if status_data != last_status:
                            elapsed = int(time.time() - start_time)
                            print(f"   [{elapsed:02d}s] Sync still active - check dashboard for live updates")
                            last_status = status_data
                    else:
                        print("   ✅ Sync completed!")
                        print("   📊 The progress indicator should now be hidden")
                        break
                        
            except requests.exceptions.RequestException:
                pass  # Continue monitoring
                
            time.sleep(5)  # Check every 5 seconds
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Monitoring stopped by user")
    
    print("\n" + "=" * 50)
    print("✅ SYNC PROGRESS DEMONSTRATION COMPLETE")
    print("\nWhat you should have seen:")
    print("• Sync progress indicator appeared immediately")
    print("• Real-time updates every 2 seconds")
    print("• Progress bar showing completion percentage")
    print("• Elapsed time and ETA calculations")
    print("• Processing rate and remaining counts")
    print("• Indicator disappeared when sync completed")

if __name__ == "__main__":
    trigger_sync_progress() 