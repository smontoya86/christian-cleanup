#!/bin/bash

# 🐳 Docker Helper Script for Christian Music Curator
# This script provides easy access to common Docker operations

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Container names
WEB_CONTAINER="web"
DB_CONTAINER="db"
REDIS_CONTAINER="redis"
WORKER_CONTAINER="worker"

echo -e "${BLUE}🐳 Christian Music Curator - Docker Helper${NC}"
echo -e "${YELLOW}⚠️  This is a DOCKER-FIRST project. All commands run in containers.${NC}"
echo ""

# Function to check if containers are running
check_containers() {
    echo -e "${BLUE}📋 Checking container status...${NC}"
    docker compose ps
    echo ""
}

# Function to show logs
show_logs() {
    echo -e "${BLUE}📜 Container logs (Ctrl+C to exit):${NC}"
    docker compose logs -f "$1"
}

# Function to restart services
restart_service() {
    echo -e "${BLUE}🔄 Restarting $1...${NC}"
    docker compose restart "$1"
    echo -e "${GREEN}✅ $1 restarted${NC}"
}

# Function to check analysis status
check_analysis() {
    echo -e "${BLUE}🔍 Checking analysis status...${NC}"

    # Get background analysis status with formatted output
    echo -e "${GREEN}Background analysis status:${NC}"
    curl -s http://localhost:5001/api/background-analysis/public-status | jq -r '
        if .active then
            "✅ Active: " + .message + "\n📊 Progress: " + (.recent_completed|tostring) + "/" + (.total_songs|tostring) + " songs\n⏱️  Rate: " + (.processing_rate|tostring) + "/hr, ETA: " + (.estimated_hours|tostring) + "h"
        else
            "❌ " + .message
        end
    ' 2>/dev/null || echo "❌ Failed to get analysis status"

    echo ""
    echo -e "${BLUE}📊 Redis status:${NC}"
    docker compose exec -T $REDIS_CONTAINER redis-cli info server | head -5 || true
}

# Function to check basic job health
check_job_health() {
    echo -e "${BLUE}🔍 Basic Job Health Check${NC}"
    echo ""

    # Check for active analysis jobs
    echo -e "${BLUE}Checking job status...${NC}"
    active_job=$(docker exec ${REDIS_CONTAINER} redis-cli get "analysis_active")

    if [ -z "$active_job" ]; then
        echo -e "${GREEN}✅ No active analysis jobs${NC}"
    else
        echo -e "${GREEN}✅ Active analysis job: $active_job${NC}"

        # Check if job exists in jobs list
        job_exists=$(docker exec ${REDIS_CONTAINER} redis-cli sismember "analysis_jobs" "$active_job")
        if [ "$job_exists" = "1" ]; then
            echo -e "${GREEN}✅ Job properly registered in queue${NC}"
        else
            echo -e "${YELLOW}⚠️  Active job not found in jobs list - potential orphan${NC}"
            echo -e "${BLUE}💡 Restart web service to reconnect: docker compose restart web${NC}"
        fi
    fi

    # Check worker health
    echo ""
    echo -e "${BLUE}Worker Status:${NC} (workers removed; analysis runs in web)"
    echo -e "${GREEN}✅ OK${NC}"
}

# Function to show simple recovery instructions
show_recovery_help() {
    echo -e "${BLUE}🔧 Simple Job Recovery${NC}"
    echo ""
    echo "If you find orphaned jobs (analysis stuck):"
    echo ""
    echo -e "${GREEN}1. Restart web service:${NC}"
    echo "   docker compose restart web"
    echo ""
    echo -e "${GREEN}2. Check if it worked:${NC}"
    echo "   ./docker-helper.sh analysis"
    echo ""
    echo -e "${GREEN}3. If still stuck, restart web:${NC}" 
    echo "   docker compose restart web"
    echo ""

    # Show recent app logs for recovery information
    echo -e "${BLUE}Recent application logs:${NC}"
    docker logs ${WEB_CONTAINER} 2>&1 | grep -E "(Reconnected|orphaned)" | tail -3 || echo "No recent recovery messages found"
}

# Function to access shells
access_shell() {
    case $1 in
        "web")
            echo -e "${BLUE}🌐 Accessing web container shell...${NC}"
            docker compose exec -it $WEB_CONTAINER bash
            ;;
        "db")
            echo -e "${BLUE}🗄️  Accessing database shell...${NC}"
            docker compose exec -it $DB_CONTAINER psql -U postgres -d spotify_cleanup
            ;;
        "redis")
            echo -e "${BLUE}🔧 Accessing Redis CLI...${NC}"
            docker compose exec -it $REDIS_CONTAINER redis-cli
            ;;
        "worker")
            echo -e "${RED}❌ Worker service has been removed. Use 'web' instead.${NC}"
            ;;
        *)
            echo -e "${RED}❌ Invalid shell option. Use: web, db, redis, or worker${NC}"
            ;;
    esac
}

# Main menu
case ${1:-menu} in
    "status"|"ps")
        check_containers
        ;;
    "logs")
        show_logs ${2:-"web"}
        ;;
    "restart")
        restart_service ${2:-"web"}
        ;;
    "analysis")
        check_analysis
        ;;
    "health-check"|"health")
        check_job_health
        ;;
    "recover-jobs"|"recover")
        show_recovery_help
        ;;
    "shell")
        access_shell ${2:-"web"}
        ;;
    "up")
        echo -e "${BLUE}🚀 Starting all services...${NC}"
        docker compose up -d
        echo -e "${GREEN}✅ All services started${NC}"
        ;;
    "down")
        echo -e "${BLUE}🛑 Stopping all services...${NC}"
        docker compose down
        echo -e "${GREEN}✅ All services stopped${NC}"
        ;;
    "build")
        echo -e "${BLUE}🔨 Building and starting services...${NC}"
        docker compose up -d --build
        echo -e "${GREEN}✅ Services built and started${NC}"
        ;;
    "clean")
        echo -e "${BLUE}🧹 Cleaning up unused Docker resources...${NC}"
        docker system prune -f
        echo -e "${GREEN}✅ Cleanup complete${NC}"
        ;;
    "help"|"menu"|*)
        echo -e "${GREEN}Available commands:${NC}"
        echo ""
        echo -e "${YELLOW}Service Management:${NC}"
        echo "  $0 up          - Start all services"
        echo "  $0 down        - Stop all services"
        echo "  $0 build       - Build and start services"
        echo "  $0 restart web - Restart web service"
        echo ""
        echo -e "${YELLOW}Monitoring:${NC}"
        echo "  $0 status      - Check container status"
        echo "  $0 logs web    - Show web service logs"
        echo "  $0 analysis    - Check background analysis status"
        echo "  $0 health      - Check basic job health status"
        echo "  $0 recover     - Show simple recovery instructions"
        echo ""
        echo -e "${YELLOW}Access:${NC}"
        echo "  $0 shell web   - Access web container shell"
        echo "  $0 shell db    - Access database shell"
        echo "  $0 shell redis - Access Redis CLI"
        echo "  $0 shell worker- (removed)"
        echo ""
        echo -e "${YELLOW}Maintenance:${NC}"
        echo "  $0 clean       - Clean unused Docker resources"
        echo ""
        echo -e "${BLUE}🌐 Web Application: ${GREEN}http://localhost:5001${NC}"
        echo -e "${BLUE}📊 Monitoring: ${GREEN}http://localhost:3000${NC} (Grafana)"
        echo ""
        ;;
esac
