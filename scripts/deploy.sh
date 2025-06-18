#!/bin/bash

# Christian Music Curator - Production Deployment Script
# Comprehensive deployment with safety checks and rollback capability

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOYMENT_ENV="${1:-production}"
BACKUP_DIR="${PROJECT_ROOT}/backups"
LOG_FILE="${PROJECT_ROOT}/logs/deployment.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO:${NC} $1" | tee -a "$LOG_FILE"
}

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Start deployment
log "🚀 Starting Christian Music Curator deployment (Environment: $DEPLOYMENT_ENV)"

# Function to check prerequisites
check_prerequisites() {
    log "🔍 Checking deployment prerequisites..."
    
    # Check if Docker is installed and running
    if ! command -v docker &> /dev/null; then
        error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        error "Docker daemon is not running"
        exit 1
    fi
    
    # Check if Docker Compose is available
    if ! command -v docker-compose &> /dev/null; then
        error "Docker Compose is not installed or not in PATH"
        exit 1
    fi
    
    # Check for required files
    local required_files=(
        "docker-compose.prod.yml"
        "Dockerfile.prod"
        "deploy/nginx/nginx.conf"
    )
    
    for file in "${required_files[@]}"; do
        if [[ ! -f "$PROJECT_ROOT/$file" ]]; then
            error "Required file not found: $file"
            exit 1
        fi
    done
    
    # Check if .env.prod exists
    if [[ ! -f "$PROJECT_ROOT/.env.prod" ]]; then
        error ".env.prod file not found. Please create it from deploy/production.env.example"
        exit 1
    fi
    
    log "✅ Prerequisites check passed"
}

# Function to validate environment configuration
validate_environment() {
    log "🔧 Validating environment configuration..."
    
    # Source environment file
    set -a
    source "$PROJECT_ROOT/.env.prod"
    set +a
    
    # Check required environment variables
    local required_vars=(
        "SECRET_KEY"
        "DATABASE_URL"
        "REDIS_URL"
        "SPOTIFY_CLIENT_ID"
        "SPOTIFY_CLIENT_SECRET"
        "POSTGRES_USER"
        "POSTGRES_PASSWORD"
        "POSTGRES_DB"
    )
    
    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            error "Required environment variable not set: $var"
            exit 1
        fi
    done
    
    # Check SECRET_KEY strength
    if [[ ${#SECRET_KEY} -lt 32 ]]; then
        error "SECRET_KEY must be at least 32 characters long for production"
        exit 1
    fi
    
    # Validate database URL format
    if [[ ! "$DATABASE_URL" =~ ^postgresql:// ]]; then
        error "DATABASE_URL must be a PostgreSQL connection string"
        exit 1
    fi
    
    log "✅ Environment configuration validated"
}

# Function to create backup
create_backup() {
    if [[ "$DEPLOYMENT_ENV" == "production" ]]; then
        log "💾 Creating pre-deployment backup..."
        
        mkdir -p "$BACKUP_DIR"
        local backup_name="backup_$(date +%Y%m%d_%H%M%S)"
        local backup_path="$BACKUP_DIR/$backup_name"
        
        # Create backup directory
        mkdir -p "$backup_path"
        
        # Backup database if running
        if docker-compose -f docker-compose.prod.yml ps db | grep -q "Up"; then
            log "Backing up database..."
            docker-compose -f docker-compose.prod.yml exec -T db pg_dump -U "$POSTGRES_USER" "$POSTGRES_DB" > "$backup_path/database.sql"
        fi
        
        # Backup volumes if they exist
        if [[ -d "$PROJECT_ROOT/data" ]]; then
            log "Backing up data volumes..."
            cp -r "$PROJECT_ROOT/data" "$backup_path/"
        fi
        
        # Create backup metadata
        cat > "$backup_path/metadata.json" << EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "deployment_env": "$DEPLOYMENT_ENV",
    "git_commit": "$(git rev-parse HEAD 2>/dev/null || echo 'unknown')",
    "git_branch": "$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo 'unknown')"
}
EOF
        
        echo "$backup_name" > "$BACKUP_DIR/latest_backup"
        log "✅ Backup created: $backup_name"
    fi
}

# Function to prepare infrastructure
prepare_infrastructure() {
    log "🏗️ Preparing infrastructure..."
    
    # Create necessary directories
    local directories=(
        "data/postgres"
        "data/redis"
        "data/prometheus"
        "data/grafana"
        "data/loki"
        "logs"
        "uploads"
        "backups"
    )
    
    for dir in "${directories[@]}"; do
        mkdir -p "$PROJECT_ROOT/$dir"
        # Set appropriate permissions
        chmod 755 "$PROJECT_ROOT/$dir"
    done
    
    # Create SSL directory if it doesn't exist
    mkdir -p "$PROJECT_ROOT/deploy/ssl"
    
    # Generate self-signed certificates if none exist (for testing)
    if [[ ! -f "$PROJECT_ROOT/deploy/ssl/cert.pem" ]]; then
        warning "No SSL certificates found. Generating self-signed certificates for testing..."
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout "$PROJECT_ROOT/deploy/ssl/key.pem" \
            -out "$PROJECT_ROOT/deploy/ssl/cert.pem" \
            -subj "/C=US/ST=State/L=City/O=Organization/OU=OrgUnit/CN=localhost"
        
        warning "⚠️  Using self-signed certificates. Replace with proper certificates for production!"
    fi
    
    log "✅ Infrastructure prepared"
}

# Function to build and deploy
deploy_application() {
    log "🔨 Building and deploying application..."
    
    cd "$PROJECT_ROOT"
    
    # Pull latest images
    log "Pulling latest base images..."
    docker-compose -f docker-compose.prod.yml pull
    
    # Build application images
    log "Building application images..."
    docker-compose -f docker-compose.prod.yml build --no-cache
    
    # Deploy with rolling update strategy
    log "Deploying services..."
    
    # Start database and Redis first
    docker-compose -f docker-compose.prod.yml up -d db redis
    
    # Wait for database to be ready
    log "Waiting for database to be ready..."
    timeout 60 bash -c 'until docker-compose -f docker-compose.prod.yml exec -T db pg_isready -U $POSTGRES_USER; do sleep 2; done'
    
    # Wait for Redis to be ready
    log "Waiting for Redis to be ready..."
    timeout 30 bash -c 'until docker-compose -f docker-compose.prod.yml exec -T redis redis-cli ping; do sleep 2; done'
    
    # Deploy the rest of the services
    docker-compose -f docker-compose.prod.yml up -d
    
    log "✅ Application deployed"
}

# Function to run health checks
run_health_checks() {
    log "🩺 Running health checks..."
    
    local max_attempts=30
    local attempt=0
    
    while [[ $attempt -lt $max_attempts ]]; do
        if curl -sf http://localhost/health >/dev/null 2>&1; then
            log "✅ Basic health check passed"
            break
        fi
        
        attempt=$((attempt + 1))
        if [[ $attempt -eq $max_attempts ]]; then
            error "Health check failed after $max_attempts attempts"
            return 1
        fi
        
        info "Health check attempt $attempt/$max_attempts failed, retrying in 10 seconds..."
        sleep 10
    done
    
    # Run detailed health check
    if curl -sf http://localhost/api/health/detailed >/dev/null 2>&1; then
        log "✅ Detailed health check passed"
    else
        warning "⚠️  Detailed health check failed, but basic check passed"
    fi
    
    # Check all services are running
    local expected_services=("nginx" "web" "worker" "db" "redis" "prometheus" "grafana")
    for service in "${expected_services[@]}"; do
        if docker-compose -f docker-compose.prod.yml ps "$service" | grep -q "Up"; then
            log "✅ Service $service is running"
        else
            error "❌ Service $service is not running"
            return 1
        fi
    done
    
    log "✅ All health checks passed"
}

# Function to cleanup old resources
cleanup_old_resources() {
    log "🧹 Cleaning up old resources..."
    
    # Remove unused Docker images
    docker image prune -f
    
    # Remove old backup files (keep last 10)
    if [[ -d "$BACKUP_DIR" ]]; then
        find "$BACKUP_DIR" -maxdepth 1 -type d -name "backup_*" | sort -r | tail -n +11 | xargs rm -rf
    fi
    
    # Clean up old log files (keep last 30 days)
    find "$PROJECT_ROOT/logs" -name "*.log" -mtime +30 -delete 2>/dev/null || true
    
    log "✅ Cleanup completed"
}

# Function to rollback deployment
rollback_deployment() {
    error "🔄 Rolling back deployment..."
    
    # Stop current services
    docker-compose -f docker-compose.prod.yml down
    
    # Restore from latest backup if available
    if [[ -f "$BACKUP_DIR/latest_backup" ]]; then
        local backup_name=$(cat "$BACKUP_DIR/latest_backup")
        local backup_path="$BACKUP_DIR/$backup_name"
        
        if [[ -d "$backup_path" ]]; then
            log "Restoring from backup: $backup_name"
            
            # Restore data volumes
            if [[ -d "$backup_path/data" ]]; then
                rm -rf "$PROJECT_ROOT/data"
                cp -r "$backup_path/data" "$PROJECT_ROOT/"
            fi
            
            # Start services
            docker-compose -f docker-compose.prod.yml up -d db redis
            
            # Restore database
            if [[ -f "$backup_path/database.sql" ]]; then
                timeout 60 bash -c 'until docker-compose -f docker-compose.prod.yml exec -T db pg_isready -U $POSTGRES_USER; do sleep 2; done'
                docker-compose -f docker-compose.prod.yml exec -T db psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" < "$backup_path/database.sql"
            fi
            
            # Start all services
            docker-compose -f docker-compose.prod.yml up -d
            
            log "✅ Rollback completed"
        else
            error "Backup not found: $backup_path"
            exit 1
        fi
    else
        error "No backup available for rollback"
        exit 1
    fi
}

# Function to show deployment status
show_deployment_status() {
    log "📊 Deployment Status Summary"
    echo
    
    # Service status
    info "Service Status:"
    docker-compose -f docker-compose.prod.yml ps
    echo
    
    # Resource usage
    info "Resource Usage:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}"
    echo
    
    # Useful URLs
    info "Access URLs:"
    echo "  Application: https://localhost (or your domain)"
    echo "  Health Check: https://localhost/health"
    echo "  Grafana Dashboard: http://localhost:3000"
    echo "  Prometheus: http://localhost:9090"
    echo
    
    # Next steps
    info "Next Steps:"
    echo "  1. Configure DNS to point to your server"
    echo "  2. Replace self-signed certificates with proper SSL certificates"
    echo "  3. Set up automated backups"
    echo "  4. Configure monitoring alerts"
    echo "  5. Test disaster recovery procedures"
}

# Main deployment flow
main() {
    # Trap errors for rollback
    trap 'error "Deployment failed! Check logs for details."; rollback_deployment; exit 1' ERR
    
    check_prerequisites
    validate_environment
    create_backup
    prepare_infrastructure
    deploy_application
    run_health_checks
    cleanup_old_resources
    
    log "🎉 Deployment completed successfully!"
    show_deployment_status
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "rollback")
        rollback_deployment
        ;;
    "status")
        show_deployment_status
        ;;
    "health")
        run_health_checks
        ;;
    *)
        echo "Usage: $0 [deploy|rollback|status|health]"
        echo
        echo "Commands:"
        echo "  deploy   - Deploy the application (default)"
        echo "  rollback - Rollback to previous version"
        echo "  status   - Show deployment status"
        echo "  health   - Run health checks"
        exit 1
        ;;
esac 