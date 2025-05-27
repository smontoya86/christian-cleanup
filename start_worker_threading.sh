#!/bin/bash

# Threading-Based Worker Startup Script
# This script starts the RQ worker in threading mode as an alternative to fork mode

echo "Starting Christian Cleanup RQ Worker in Threading Mode..."

# Detect if we're running on macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "macOS detected: Configuring threading mode for optimal compatibility"
    
    # Set environment variables for threading mode
    export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
    export RQ_WORKER_USE_THREADING=true
    export NSUnbufferedIO=YES
    
    echo "Threading mode environment configured:"
    echo "  OBJC_DISABLE_INITIALIZE_FORK_SAFETY=$OBJC_DISABLE_INITIALIZE_FORK_SAFETY"
    echo "  RQ_WORKER_USE_THREADING=$RQ_WORKER_USE_THREADING"
    echo "  NSUnbufferedIO=$NSUnbufferedIO"
else
    echo "Non-macOS environment detected: Threading mode can still be used for testing"
    export RQ_WORKER_USE_THREADING=true
fi

# Check if virtual environment should be activated
if [ -f "venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
elif [ -f ".venv/bin/activate" ]; then
    echo "Activating virtual environment (.venv)..."
    source .venv/bin/activate
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found. Make sure environment variables are set."
fi

echo "Starting worker in threading mode..."
echo "Press Ctrl+C to stop the worker"
echo ""

# Start the worker with threading flag and pass any additional arguments
python worker.py --threading "$@"

echo "Worker stopped." 