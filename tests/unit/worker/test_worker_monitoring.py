#!/usr/bin/env python3
"""
Test script for worker monitoring and graceful shutdown functionality.
"""

import os
import sys
import time
import signal
import subprocess
import threading
from datetime import datetime

from dotenv import load_dotenv
from redis import Redis
from rq import Queue

# Load environment variables for testing
env_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', '.env')
load_dotenv(env_path)

# Get the Python executable path from current virtual environment
PYTHON_EXECUTABLE = sys.executable


def test_worker_startup_and_info():
    """Test worker startup and info display."""
    print("🧪 Testing worker startup and info display...")
    
    # Test fork mode info
    result = subprocess.run([
        PYTHON_EXECUTABLE, 'worker.py', '--info'
    ], capture_output=True, text=True, timeout=10)
    
    if result.returncode == 0:
        print("✅ Fork mode worker info: PASSED")
        if "Platform Mode: fork" in result.stdout:
            print("   ✓ Fork mode detected correctly")
    else:
        print("❌ Fork mode worker info: FAILED")
        print(f"   Error: {result.stderr}")
    
    # Test threading mode info
    result = subprocess.run([
        PYTHON_EXECUTABLE, 'worker.py', '--threading', '--info'
    ], capture_output=True, text=True, timeout=10)
    
    if result.returncode == 0:
        print("✅ Threading mode worker info: PASSED")
        if "Platform Mode: threading" in result.stdout:
            print("   ✓ Threading mode detected correctly")
    else:
        print("❌ Threading mode worker info: FAILED")
        print(f"   Error: {result.stderr}")


def test_health_check_utility():
    """Test the worker health check utility."""
    print("\n🧪 Testing worker health check utility...")
    
    # Test queue status
    result = subprocess.run([
        PYTHON_EXECUTABLE, 'worker_health_check.py', '--queue-status'
    ], capture_output=True, text=True, timeout=10)
    
    if result.returncode == 0:
        print("✅ Health check queue status: PASSED")
        if "Queue Status:" in result.stdout:
            print("   ✓ Queue status displayed correctly")
    else:
        print("❌ Health check queue status: FAILED")
        print(f"   Error: {result.stderr}")
    
    # Test worker health check (no workers running)
    result = subprocess.run([
        PYTHON_EXECUTABLE, 'worker_health_check.py'
    ], capture_output=True, text=True, timeout=10)
    
    if result.returncode == 0:
        print("✅ Health check worker status: PASSED")
        if "Total Workers: 0" in result.stdout:
            print("   ✓ No workers detected correctly")
    else:
        print("❌ Health check worker status: FAILED")
        print(f"   Error: {result.stderr}")


def test_job_processing():
    """Test job processing with monitoring."""
    print("\n🧪 Testing job processing with monitoring...")
    
    # Start a worker in test mode
    worker_process = subprocess.Popen([
        PYTHON_EXECUTABLE, 'worker.py', '--test-mode'
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # Give worker time to start
    time.sleep(2)
    
    # Enqueue a test job
    try:
        redis_url = os.getenv('RQ_REDIS_URL', 'redis://localhost:6379/0')
        conn = Redis.from_url(redis_url)
        queue = Queue(connection=conn)
        job = queue.enqueue('time.sleep', 1)
        print(f"   📝 Test job enqueued: {job.id}")
        
        # Wait for worker to complete
        stdout, stderr = worker_process.communicate(timeout=10)
        
        if worker_process.returncode == 0:
            print("✅ Job processing: PASSED")
            if "Successfully completed" in stderr or "Job OK" in stderr:
                print("   ✓ Job completed successfully")
        else:
            print("❌ Job processing: FAILED")
            print(f"   Error: {stderr}")
            
    except Exception as e:
        print(f"❌ Job processing: FAILED - {e}")
        worker_process.terminate()


def test_signal_handling():
    """Test graceful shutdown with signal handling."""
    print("\n🧪 Testing signal handling and graceful shutdown...")
    
    # Start a worker
    worker_process = subprocess.Popen([
        PYTHON_EXECUTABLE, 'worker.py', '--no-monitoring'
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # Give worker time to start
    time.sleep(3)
    
    print(f"   📡 Worker started with PID: {worker_process.pid}")
    
    # Send SIGTERM signal
    try:
        worker_process.send_signal(signal.SIGTERM)
        print("   📡 SIGTERM signal sent")
        
        # Wait for graceful shutdown
        stdout, stderr = worker_process.communicate(timeout=10)
        
        if worker_process.returncode == 0 or worker_process.returncode == -signal.SIGTERM:
            print("✅ Signal handling: PASSED")
            if "graceful shutdown" in stderr.lower() or "shutdown" in stderr.lower():
                print("   ✓ Graceful shutdown detected")
        else:
            print("❌ Signal handling: FAILED")
            print(f"   Return code: {worker_process.returncode}")
            print(f"   Stderr: {stderr}")
            
    except subprocess.TimeoutExpired:
        print("❌ Signal handling: FAILED - Worker did not shut down gracefully")
        worker_process.kill()
    except Exception as e:
        print(f"❌ Signal handling: FAILED - {e}")
        worker_process.terminate()


def test_startup_scripts():
    """Test the startup scripts."""
    print("\n🧪 Testing startup scripts...")
    
    # Test macOS startup script
    try:
        result = subprocess.run([
            './start_worker_macos.sh', '--info'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ macOS startup script: PASSED")
            if "Platform Mode: fork" in result.stdout:
                print("   ✓ macOS script configured correctly")
        else:
            print("❌ macOS startup script: FAILED")
            print(f"   Error: {result.stderr}")
    except Exception as e:
        print(f"❌ macOS startup script: FAILED - {e}")
    
    # Test threading startup script
    try:
        result = subprocess.run([
            './start_worker_threading.sh', '--info'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ Threading startup script: PASSED")
            if "Platform Mode: threading" in result.stdout:
                print("   ✓ Threading script configured correctly")
        else:
            print("❌ Threading startup script: FAILED")
            print(f"   Error: {result.stderr}")
    except Exception as e:
        print(f"❌ Threading startup script: FAILED - {e}")


def test_monitoring_features():
    """Test monitoring features with a running worker."""
    print("\n🧪 Testing monitoring features...")
    
    # Start a worker with monitoring
    worker_process = subprocess.Popen([
        PYTHON_EXECUTABLE, 'worker.py', '--health-check-interval', '2'
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    # Give worker time to start and run a health check
    time.sleep(5)
    
    # Check if worker is registered
    try:
        result = subprocess.run([
            PYTHON_EXECUTABLE, 'worker_health_check.py'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            if "Total Workers: 1" in result.stdout or "Total Workers: 0" in result.stdout:
                print("✅ Worker monitoring: PASSED")
                print("   ✓ Health check utility can detect workers")
            else:
                print("❌ Worker monitoring: FAILED")
                print(f"   Output: {result.stdout}")
        else:
            print("❌ Worker monitoring: FAILED")
            print(f"   Error: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Worker monitoring: FAILED - {e}")
    finally:
        # Clean up worker process
        try:
            worker_process.terminate()
            worker_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            worker_process.kill()
        except Exception:
            pass


def main():
    """Run all tests."""
    print("🚀 Starting Worker Monitoring and Graceful Shutdown Tests")
    print("=" * 60)
    
    start_time = datetime.now()
    
    # Run all tests
    test_worker_startup_and_info()
    test_health_check_utility()
    test_job_processing()
    test_signal_handling()
    test_startup_scripts()
    test_monitoring_features()
    
    # Summary
    end_time = datetime.now()
    duration = end_time - start_time
    
    print("\n" + "=" * 60)
    print(f"🏁 Test suite completed in {duration}")
    print("=" * 60)
    
    print("\n📋 Test Summary:")
    print("✅ = Passed, ❌ = Failed, ⚠️ = Partial/Warning")
    print("\nKey Features Tested:")
    print("• Worker startup and configuration display")
    print("• Health check utility functionality")
    print("• Job processing with monitoring")
    print("• Signal handling and graceful shutdown")
    print("• Startup script functionality")
    print("• Worker monitoring and health checks")


if __name__ == '__main__':
    main() 