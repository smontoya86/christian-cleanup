#!/bin/bash

# Health check script for the Christian music analysis application
# This script verifies that all services are running correctly

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✅${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

# Function to check if a service is responding
check_service() {
    local service_name="$1"
    local url="$2"
    local timeout="${3:-5}"
    
    if curl -s --max-time "$timeout" "$url" >/dev/null 2>&1; then
        print_success "$service_name is responding"
        return 0
    else
        print_error "$service_name is not responding"
        return 1
    fi
}

# Function to check Docker container status
check_container() {
    local container_name="$1"
    
    if docker ps --format "table {{.Names}}\t{{.Status}}" | grep -q "$container_name.*Up"; then
        print_success "$container_name container is running"
        return 0
    else
        print_error "$container_name container is not running"
        return 1
    fi
}

# Function to check port availability
check_port() {
    local port="$1"
    local service_name="$2"
    
    if lsof -ti:"$port" >/dev/null 2>&1; then
        print_success "$service_name is listening on port $port"
        return 0
    else
        print_error "$service_name is not listening on port $port"
        return 1
    fi
}

# Main health check function
main_healthcheck() {
    echo "🏥 Christian Music Analysis Application Health Check"
    echo "=================================================="
    echo ""
    
    local exit_code=0
    
    # Check Docker containers
    echo "📦 Checking Docker containers..."
    check_container "christian-cleanup_web_1" || exit_code=1
    check_container "christian-cleanup_db_1" || exit_code=1
    check_container "christian-cleanup_redis_1" || exit_code=1
    check_container "ollama-standalone" || exit_code=1
    echo ""
    
    # Check ports
    echo "🔌 Checking ports..."
    check_port "5001" "Web application" || exit_code=1
    check_port "5432" "PostgreSQL database" || exit_code=1
    check_port "6379" "Redis cache" || exit_code=1
    check_port "11434" "Ollama service" || exit_code=1
    echo ""
    
    # Check service endpoints
    echo "🌐 Checking service endpoints..."
    check_service "Web application" "http://localhost:5001" 10 || exit_code=1
    check_service "Ollama API" "http://localhost:11434/api/tags" 5 || exit_code=1
    echo ""
    
    # Check database connectivity
    echo "🗄️ Checking database connectivity..."
    if /usr/local/bin/docker-compose exec -T db pg_isready -U postgres >/dev/null 2>&1; then
        print_success "PostgreSQL database is ready"
    else
        print_error "PostgreSQL database is not ready"
        exit_code=1
    fi
    echo ""
    
    # Check Redis connectivity
    echo "📊 Checking Redis connectivity..."
    if /usr/local/bin/docker-compose exec -T redis redis-cli ping | grep -q "PONG"; then
        print_success "Redis cache is responding"
    else
        print_error "Redis cache is not responding"
        exit_code=1
    fi
    echo ""
    
    # Summary
    if [ $exit_code -eq 0 ]; then
        print_success "All health checks passed! 🎉"
        echo ""
        echo "🚀 Application is ready for use"
        echo "📝 Run evaluation with: ./dev.sh eval"
    else
        print_error "Some health checks failed! 🚨"
        echo ""
        echo "🔧 Try restarting with: ./dev.sh restart"
    fi
    
    return $exit_code
}

# Run health check
main_healthcheck "$@"
