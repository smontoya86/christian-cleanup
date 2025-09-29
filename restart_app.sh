#!/bin/bash

# Christian Music Analysis Application Restart Script
# This script automatically cleans up port 5001 and restarts the application

echo "🔄 Starting application restart process..."

# Function to kill processes on port 5001
cleanup_port() {
    echo "🧹 Cleaning up port 5001..."
    
    # Find and kill processes using port 5001
    PIDS=$(lsof -ti:5001 2>/dev/null)
    
    if [ -n "$PIDS" ]; then
        echo "Found processes on port 5001: $PIDS"
        echo "Killing processes..."
        kill -9 $PIDS 2>/dev/null
        sleep 2
        
        # Verify port is free
        if lsof -ti:5001 >/dev/null 2>&1; then
            echo "⚠️  Warning: Port 5001 may still be in use"
        else
            echo "✅ Port 5001 is now free"
        fi
    else
        echo "✅ Port 5001 is already free"
    fi
}

# Function to stop Docker services
stop_services() {
    echo "🛑 Stopping Docker services..."
    /usr/local/bin/docker-compose down --volumes 2>/dev/null || true
    
    # Stop standalone ollama if running
    docker stop ollama-standalone 2>/dev/null || true
    docker rm ollama-standalone 2>/dev/null || true
}

# Function to start Docker services
start_services() {
    echo "🚀 Starting Docker services..."
    
    # Start standalone ollama first
    echo "Starting Ollama service..."
    docker run -d --name ollama-standalone -p 11434:11434 ollama/ollama:latest
    
    # Wait for ollama to be ready
    echo "Waiting for Ollama to be ready..."
    sleep 10
    
    # Pull the model if not already available
    echo "Ensuring language model is available..."
    docker exec ollama-standalone ollama pull tinydolphin 2>/dev/null || true
    
    # Start the main application services
    echo "Starting application services..."
    /usr/local/bin/docker-compose up -d --build
    
    echo "✅ All services started successfully"
}

# Function to verify services are running
verify_services() {
    echo "🔍 Verifying services..."
    
    # Check if ollama is responding
    if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        echo "✅ Ollama service is responding"
    else
        echo "⚠️  Warning: Ollama service may not be ready yet"
    fi
    
    # Check if web service is running
    if /usr/local/bin/docker-compose ps | grep -q "web.*Up"; then
        echo "✅ Web service is running"
    else
        echo "⚠️  Warning: Web service may not be ready yet"
    fi
    
    echo "🎉 Application restart complete!"
    echo "📝 You can now run the evaluation script with:"
    echo "   /usr/local/bin/docker-compose exec web python evaluate.py"
}

# Main execution
main() {
    cleanup_port
    stop_services
    start_services
    verify_services
}

# Run the main function
main "$@"
