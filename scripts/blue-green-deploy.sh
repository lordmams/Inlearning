#!/bin/bash

# ===============================================
# Blue-Green Deployment Script for InLearning
# ===============================================

set -euo pipefail

# Configuration
COMPOSE_FILE="docker-compose.production.yml"
BLUE_COMPOSE_FILE="docker-compose.blue.yml"
GREEN_COMPOSE_FILE="docker-compose.green.yml"
NGINX_CONFIG="/etc/nginx/sites-available/inlearning"
HEALTH_CHECK_URL="http://localhost"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] ✓${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ✗${NC} $1"
}

warning() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] ⚠${NC} $1"
}

# Determine current active environment
get_current_environment() {
    if docker-compose -f "$BLUE_COMPOSE_FILE" ps -q app 2>/dev/null | grep -q .; then
        if [ "$(docker-compose -f "$BLUE_COMPOSE_FILE" ps app | grep -c 'Up')" -gt 0 ]; then
            echo "blue"
            return
        fi
    fi
    
    if docker-compose -f "$GREEN_COMPOSE_FILE" ps -q app 2>/dev/null | grep -q .; then
        if [ "$(docker-compose -f "$GREEN_COMPOSE_FILE" ps app | grep -c 'Up')" -gt 0 ]; then
            echo "green"
            return
        fi
    fi
    
    echo "none"
}

# Health check function
health_check() {
    local environment=$1
    local port=$2
    local max_attempts=30
    local attempt=1
    
    log "Performing health check for $environment environment on port $port..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -f -s "http://localhost:$port/health/" > /dev/null 2>&1; then
            success "$environment environment is healthy"
            return 0
        fi
        
        warning "Attempt $attempt/$max_attempts: $environment environment not ready..."
        sleep 5
        ((attempt++))
    done
    
    error "$environment environment failed health check"
    return 1
}

# Deploy to inactive environment
deploy_to_inactive() {
    local current_env=$1
    local target_env
    local target_port
    local target_compose
    
    if [ "$current_env" = "blue" ]; then
        target_env="green"
        target_port="8081"
        target_compose="$GREEN_COMPOSE_FILE"
    elif [ "$current_env" = "green" ]; then
        target_env="blue"
        target_port="8080"
        target_compose="$BLUE_COMPOSE_FILE"
    else
        # First deployment, use blue
        target_env="blue"
        target_port="8080"
        target_compose="$BLUE_COMPOSE_FILE"
    fi
    
    log "Deploying to $target_env environment..."
    
    # Stop target environment if running
    docker-compose -f "$target_compose" down 2>/dev/null || true
    
    # Pull latest images
    docker-compose -f "$target_compose" pull
    
    # Start new environment
    docker-compose -f "$target_compose" up -d
    
    # Wait for services to be ready
    sleep 10
    
    # Run migrations on new environment
    docker-compose -f "$target_compose" exec -T app python manage.py migrate
    
    # Collect static files
    docker-compose -f "$target_compose" exec -T app python manage.py collectstatic --noinput
    
    # Health check
    if health_check "$target_env" "$target_port"; then
        success "$target_env environment deployed successfully"
        echo "$target_env"
        return 0
    else
        error "$target_env environment deployment failed"
        docker-compose -f "$target_compose" down
        return 1
    fi
}

# Switch traffic to new environment
switch_traffic() {
    local new_env=$1
    local new_port
    
    if [ "$new_env" = "blue" ]; then
        new_port="8080"
    else
        new_port="8081"
    fi
    
    log "Switching traffic to $new_env environment..."
    
    # Create new nginx config
    cat > "$NGINX_CONFIG" << EOF
upstream inlearning_backend {
    server localhost:$new_port;
}

server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://inlearning_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    location /health/ {
        proxy_pass http://inlearning_backend/health/;
        access_log off;
    }
}
EOF
    
    # Test nginx configuration
    if nginx -t; then
        # Reload nginx
        systemctl reload nginx
        success "Traffic switched to $new_env environment"
        
        # Final health check through nginx
        if health_check "$new_env" "80"; then
            success "Production health check passed"
            return 0
        else
            error "Production health check failed"
            return 1
        fi
    else
        error "Nginx configuration test failed"
        return 1
    fi
}

# Stop old environment
stop_old_environment() {
    local old_env=$1
    local old_compose
    
    if [ "$old_env" = "blue" ]; then
        old_compose="$BLUE_COMPOSE_FILE"
    elif [ "$old_env" = "green" ]; then
        old_compose="$GREEN_COMPOSE_FILE"
    else
        log "No old environment to stop"
        return 0
    fi
    
    log "Stopping old $old_env environment..."
    
    # Graceful shutdown with delay
    sleep 30
    
    docker-compose -f "$old_compose" down
    
    success "Old $old_env environment stopped"
}

# Rollback function
rollback() {
    local current_env=$1
    local previous_env
    local previous_port
    local previous_compose
    
    if [ "$current_env" = "blue" ]; then
        previous_env="green"
        previous_port="8081"
        previous_compose="$GREEN_COMPOSE_FILE"
    elif [ "$current_env" = "green" ]; then
        previous_env="blue"
        previous_port="8080"
        previous_compose="$BLUE_COMPOSE_FILE"
    else
        error "Cannot rollback: no previous environment"
        return 1
    fi
    
    warning "Rolling back to $previous_env environment..."
    
    # Check if previous environment is still running
    if docker-compose -f "$previous_compose" ps -q app 2>/dev/null | grep -q .; then
        switch_traffic "$previous_env"
        success "Rollback completed"
    else
        error "Previous environment is not available for rollback"
        return 1
    fi
}

# Main blue-green deployment
main() {
    log "Starting Blue-Green deployment..."
    
    # Check if we're in the right directory
    if [ ! -f "$COMPOSE_FILE" ]; then
        error "Production compose file not found. Are you in the right directory?"
        exit 1
    fi
    
    # Get current environment
    current_env=$(get_current_environment)
    log "Current environment: $current_env"
    
    # Deploy to inactive environment
    if new_env=$(deploy_to_inactive "$current_env"); then
        log "Deployment to $new_env successful"
    else
        error "Deployment failed"
        exit 1
    fi
    
    # Switch traffic
    if switch_traffic "$new_env"; then
        log "Traffic switch successful"
    else
        error "Traffic switch failed, attempting rollback..."
        if rollback "$new_env"; then
            error "Rollback successful, deployment aborted"
        else
            error "Rollback failed! Manual intervention required"
        fi
        exit 1
    fi
    
    # Stop old environment
    if [ "$current_env" != "none" ]; then
        stop_old_environment "$current_env"
    fi
    
    success "Blue-Green deployment completed successfully! 🎉"
    log "New environment: $new_env"
    log "Services status:"
    
    if [ "$new_env" = "blue" ]; then
        docker-compose -f "$BLUE_COMPOSE_FILE" ps
    else
        docker-compose -f "$GREEN_COMPOSE_FILE" ps
    fi
}

# Handle interruption
trap 'error "Deployment interrupted"; exit 1' INT TERM

# Run main function
main "$@" 