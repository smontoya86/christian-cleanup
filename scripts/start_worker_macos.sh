#!/bin/bash

# macOS Worker Startup Script
# This script ensures proper fork safety configuration for macOS before starting the RQ worker

echo "Starting Christian Cleanup RQ Worker on macOS..."

# Detect if we're running on macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "macOS detected: Configuring fork safety measures"
    
    # Set the critical environment variable for Objective-C fork safety
    export OBJC_DISABLE_INITIALIZE_FORK_SAFETY=YES
    
    # Additional macOS-specific environment variables that may help
    export NSUnbufferedIO=YES
    
    echo "Fork safety environment configured:"
    echo "  OBJC_DISABLE_INITIALIZE_FORK_SAFETY=$OBJC_DISABLE_INITIALIZE_FORK_SAFETY"
    echo "  NSUnbufferedIO=$NSUnbufferedIO"
else
    echo "Non-macOS system detected, using standard configuration"
fi

# Start the Python worker with the configured environment
echo "Starting Python worker..."
exec python worker.py "$@" 