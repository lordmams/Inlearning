#!/bin/bash

# ===============================================
# InLearning Deployment Script
# ===============================================

set -euo pipefail

# Configuration
ENVIRONMENT=${1:-staging}
PROJECT_DIR="/opt/inlearning-${ENVIRONMENT}"
BACKUP_DIR="/opt/backups/inlearning"
COMPOSE_FILE="docker-compose.${ENVIRONMENT}.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] ✓${NC} $1"
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] ⚠${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ✗${NC} $1"
}

# Function to check if service is healthy
check_service_health() {
    local service=$1
    local url=$2
    local max_attempts=30
    local attempt=1

    log "Checking health of $service..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "$url" > /dev/null 2>&1; then
            success "$service is healthy"
            return 0
        fi
        
        warning "Attempt $attempt/$max_attempts: $service not ready yet..."
        sleep 2
        ((attempt++))
    done
    
    error "$service failed health check"
    return 1
}

# Function to create backup
create_backup() {
    log "Creating backup..."
    
    mkdir -p "$BACKUP_DIR"
    BACKUP_FILE="$BACKUP_DIR/inlearning-$(date +%Y%m%d_%H%M%S).tar.gz"
    
    # Backup database
    if docker-compose -f "$COMPOSE_FILE" exec -T db pg_dump -U $POSTGRES_USER $POSTGRES_DB > "$BACKUP_DIR/db-$(date +%Y%m%d_%H%M%S).sql"; then
        success "Database backup created"
    else
        error "Database backup failed"
        return 1
    fi
    
    # Backup volumes and configurations
    tar -czf "$BACKUP_FILE" \
        --exclude="*/logs/*" \
        --exclude="*/cache/*" \
        "$PROJECT_DIR"
    
    success "Backup created: $BACKUP_FILE"
}

# Function to update code
update_code() {
    log "Updating code from repository..."
    
    cd "$PROJECT_DIR"
    
    # Fetch latest changes
    git fetch origin
    
    if [ "$ENVIRONMENT" = "production" ]; then
        git checkout main
        git pull origin main
    else
        git checkout develop
        git pull origin develop
    fi
    
    success "Code updated successfully"
}

# Function to update environment variables
update_environment() {
    log "Updating environment variables..."
    
    if [ -f ".env.${ENVIRONMENT}" ]; then
        cp ".env.${ENVIRONMENT}" .env
        success "Environment variables updated"
    else
        warning "No environment file found for $ENVIRONMENT"
    fi
}

# Function to pull Docker images
pull_images() {
    log "Pulling Docker images..."
    
    if docker-compose -f "$COMPOSE_FILE" pull; then
        success "Docker images pulled successfully"
    else
        error "Failed to pull Docker images"
        return 1
    fi
}

# Function to run database migrations
run_migrations() {
    log "Running database migrations..."
    
    if docker-compose -f "$COMPOSE_FILE" exec -T app python manage.py migrate; then
        success "Database migrations completed"
    else
        error "Database migrations failed"
        return 1
    fi
}

# Function to collect static files
collect_static() {
    log "Collecting static files..."
    
    if docker-compose -f "$COMPOSE_FILE" exec -T app python manage.py collectstatic --noinput; then
        success "Static files collected"
    else
        error "Static files collection failed"
        return 1
    fi
}

# Function to deploy with zero downtime
deploy_services() {
    log "Deploying services with zero downtime..."
    
    # Deploy services one by one
    local services=("app" "flask_api" "orchestrator")
    
    for service in "${services[@]}"; do
        log "Deploying $service..."
        
        # Start new container
        docker-compose -f "$COMPOSE_FILE" up -d --no-deps "$service"
        
        # Check health
        case $service in
            "app")
                check_service_health "$service" "http://localhost:8080/health/"
                ;;
            "flask_api")
                check_service_health "$service" "http://localhost:5000/health"
                ;;
            "orchestrator")
                check_service_health "$service" "http://localhost:8090/health"
                ;;
        esac
        
        if [ $? -eq 0 ]; then
            success "$service deployed successfully"
        else
            error "$service deployment failed"
            return 1
        fi
    done
}

# Function to run post-deployment tasks
post_deployment() {
    log "Running post-deployment tasks..."
    
    # Clear cache
    docker-compose -f "$COMPOSE_FILE" exec -T redis redis-cli FLUSHDB
    
    # Warm up cache
    curl -s "http://localhost:8080/" > /dev/null
    
    # Update search index
    docker-compose -f "$COMPOSE_FILE" exec -T app python manage.py update_index
    
    success "Post-deployment tasks completed"
}

# Function to cleanup old images
cleanup() {
    log "Cleaning up old Docker images..."
    
    # Remove unused images
    docker image prune -f
    
    # Remove old backups (keep last 10)
    find "$BACKUP_DIR" -name "*.tar.gz" -type f | sort -r | tail -n +11 | xargs rm -f
    find "$BACKUP_DIR" -name "*.sql" -type f | sort -r | tail -n +11 | xargs rm -f
    
    success "Cleanup completed"
}

# Function to send notification
send_notification() {
    local status=$1
    local message=$2
    
    if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"[$ENVIRONMENT] $message - Status: $status\"}" \
            "$SLACK_WEBHOOK_URL" > /dev/null 2>&1
    fi
    
    if [ -n "${EMAIL_RECIPIENT:-}" ]; then
        echo "$message" | mail -s "InLearning Deployment - $ENVIRONMENT" "$EMAIL_RECIPIENT"
    fi
}

# Main deployment function
main() {
    log "Starting deployment to $ENVIRONMENT environment..."
    
    # Validate environment
    if [[ ! "$ENVIRONMENT" =~ ^(staging|production)$ ]]; then
        error "Invalid environment. Use 'staging' or 'production'"
        exit 1
    fi
    
    # Check if running as deployment user
    if [ "$USER" != "deploy" ] && [ "$ENVIRONMENT" = "production" ]; then
        error "Production deployments must be run as 'deploy' user"
        exit 1
    fi
    
    # Change to project directory
    cd "$PROJECT_DIR" || {
        error "Project directory not found: $PROJECT_DIR"
        exit 1
    }
    
    # Execute deployment steps
    if create_backup && \
       update_code && \
       update_environment && \
       pull_images && \
       deploy_services && \
       run_migrations && \
       collect_static && \
       post_deployment && \
       cleanup; then
        
        success "Deployment to $ENVIRONMENT completed successfully! 🚀"
        send_notification "SUCCESS" "Deployment completed successfully"
        
        # Display service status
        log "Current service status:"
        docker-compose -f "$COMPOSE_FILE" ps
        
    else
        error "Deployment to $ENVIRONMENT failed! 💥"
        send_notification "FAILED" "Deployment failed"
        
        # Show recent logs for debugging
        log "Recent logs for debugging:"
        docker-compose -f "$COMPOSE_FILE" logs --tail=20
        
        exit 1
    fi
}

# Handle script interruption
trap 'error "Deployment interrupted"; exit 1' INT TERM

# Run main function
main "$@" 