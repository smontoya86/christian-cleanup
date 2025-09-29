#!/bin/bash

# Christian Music Analysis Application Development Script
# Provides common development tasks and utilities

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Christian Music Analysis Application Development Script"
    echo ""
    echo "Usage: $0 <command>"
    echo ""
    echo "Commands:"
    echo "  start       - Start the application (with port cleanup)"
    echo "  stop        - Stop all services"
    echo "  restart     - Restart the application (with port cleanup)"
    echo "  logs        - Show application logs"
    echo "  eval        - Run the evaluation script"
    echo "  status      - Check service status"
    echo "  clean       - Clean up Docker resources"
    echo "  build       - Build the application"
    echo "  test        - Run tests (evaluation)"
    echo "  help        - Show this help message"
    echo ""
}

# Function to cleanup port 5001
cleanup_port() {
    print_status "Cleaning up port 5001..."
    
    PIDS=$(lsof -ti:5001 2>/dev/null || true)
    
    if [ -n "$PIDS" ]; then
        print_status "Found processes on port 5001: $PIDS"
        kill -9 $PIDS 2>/dev/null || true
        sleep 2
        print_success "Port 5001 cleaned up"
    else
        print_success "Port 5001 is already free"
    fi
}

# Function to start services
start_services() {
    print_status "Starting services..."
    
    cleanup_port
    
    # Stop any existing services
    /usr/local/bin/docker-compose down --volumes 2>/dev/null || true
    docker stop ollama-standalone 2>/dev/null || true
    docker rm ollama-standalone 2>/dev/null || true
    
    # Start ollama
    print_status "Starting Ollama service..."
    docker run -d --name ollama-standalone -p 11434:11434 ollama/ollama:latest
    
    # Wait for ollama
    sleep 10
    
    # Ensure model is available
    print_status "Ensuring language model is available..."
    docker exec ollama-standalone ollama pull tinydolphin 2>/dev/null || true
    
    # Start main services
    print_status "Starting application services..."
    /usr/local/bin/docker-compose up -d --build
    
    print_success "All services started"
}

# Function to stop services
stop_services() {
    print_status "Stopping services..."
    
    /usr/local/bin/docker-compose down --volumes 2>/dev/null || true
    docker stop ollama-standalone 2>/dev/null || true
    docker rm ollama-standalone 2>/dev/null || true
    
    cleanup_port
    
    print_success "All services stopped"
}

# Function to show logs
show_logs() {
    print_status "Showing application logs..."
    /usr/local/bin/docker-compose logs -f web
}

# Function to run evaluation
run_evaluation() {
    print_status "Running evaluation script..."
    /usr/local/bin/docker-compose exec web python evaluate.py
}

# Function to check status
check_status() {
    print_status "Checking service status..."
    
    echo ""
    echo "Docker Compose Services:"
    /usr/local/bin/docker-compose ps
    
    echo ""
    echo "Ollama Service:"
    if docker ps | grep -q ollama-standalone; then
        print_success "Ollama is running"
    else
        print_warning "Ollama is not running"
    fi
    
    echo ""
    echo "Port 5001 Status:"
    if lsof -ti:5001 >/dev/null 2>&1; then
        print_warning "Port 5001 is in use"
        lsof -i:5001
    else
        print_success "Port 5001 is free"
    fi
    
    echo ""
    echo "Ollama API Status:"
    if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        print_success "Ollama API is responding"
    else
        print_warning "Ollama API is not responding"
    fi
}

# Function to clean up Docker resources
clean_docker() {
    print_status "Cleaning up Docker resources..."
    
    stop_services
    
    print_status "Removing unused Docker resources..."
    docker system prune -f
    
    print_success "Docker cleanup complete"
}

# Function to build application
build_app() {
    print_status "Building application..."
    
    cleanup_port
    /usr/local/bin/docker-compose build
    
    print_success "Build complete"
}

# Function to run tests
run_tests() {
    print_status "Running tests (evaluation)..."
    run_evaluation
}

# Main command handling
case "${1:-}" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        stop_services
        start_services
        ;;
    logs)
        show_logs
        ;;
    eval)
        run_evaluation
        ;;
    status)
        check_status
        ;;
    clean)
        clean_docker
        ;;
    build)
        build_app
        ;;
    test)
        run_tests
        ;;
    help|--help|-h)
        show_usage
        ;;
    "")
        print_error "No command specified"
        echo ""
        show_usage
        exit 1
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_usage
        exit 1
        ;;
esac
