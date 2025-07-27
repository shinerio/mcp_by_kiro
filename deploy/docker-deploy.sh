#!/bin/bash
# Docker Deployment Script for MCP Base64 Server
# This script helps deploy the server using Docker and Docker Compose

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
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

# Default values
ACTION="start"
SERVICE="mcp-base64-server"
BUILD_ARGS=""
COMPOSE_FILE="docker-compose.yml"

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [ACTION] [OPTIONS]

Actions:
    start           Start the services (default)
    stop            Stop the services
    restart         Restart the services
    build           Build the Docker images
    logs            Show service logs
    status          Show service status
    clean           Clean up containers and images

Options:
    -s, --service NAME      Service name (default: mcp-base64-server)
    -f, --file FILE         Docker Compose file (default: docker-compose.yml)
    -d, --detach            Run in detached mode
    --build                 Force rebuild images
    --dev                   Use development configuration
    --prod                  Use production configuration
    -h, --help              Show this help message

Examples:
    $0 start                # Start the default service
    $0 start --dev          # Start in development mode
    $0 build --prod         # Build production images
    $0 logs -s nginx        # Show nginx logs
    $0 clean                # Clean up everything

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        start|stop|restart|build|logs|status|clean)
            ACTION="$1"
            shift
            ;;
        -s|--service)
            SERVICE="$2"
            shift 2
            ;;
        -f|--file)
            COMPOSE_FILE="$2"
            shift 2
            ;;
        -d|--detach)
            DETACH_FLAG="-d"
            shift
            ;;
        --build)
            BUILD_FLAG="--build"
            shift
            ;;
        --dev)
            SERVICE="mcp-base64-server-dev"
            export LOG_LEVEL=DEBUG
            export FLASK_ENV=development
            shift
            ;;
        --prod)
            SERVICE="mcp-base64-server"
            export LOG_LEVEL=INFO
            export FLASK_ENV=production
            shift
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed or not in PATH"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    print_error "Docker Compose is not installed or not in PATH"
    exit 1
fi

# Use docker compose or docker-compose based on availability
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

# Check if compose file exists
if [[ ! -f "$COMPOSE_FILE" ]]; then
    print_error "Docker Compose file not found: $COMPOSE_FILE"
    exit 1
fi

# Load environment variables if .env file exists
if [[ -f ".env" ]]; then
    print_info "Loading environment variables from .env file"
    export $(grep -v '^#' .env | xargs)
fi

# Execute the requested action
case $ACTION in
    start)
        print_info "Starting service: $SERVICE"
        $DOCKER_COMPOSE -f "$COMPOSE_FILE" up $DETACH_FLAG $BUILD_FLAG "$SERVICE"
        if [[ -n "$DETACH_FLAG" ]]; then
            print_success "Service started in detached mode"
            print_info "Use '$0 logs -s $SERVICE' to view logs"
            print_info "Use '$0 status' to check service status"
        fi
        ;;
    
    stop)
        print_info "Stopping service: $SERVICE"
        $DOCKER_COMPOSE -f "$COMPOSE_FILE" stop "$SERVICE"
        print_success "Service stopped"
        ;;
    
    restart)
        print_info "Restarting service: $SERVICE"
        $DOCKER_COMPOSE -f "$COMPOSE_FILE" restart "$SERVICE"
        print_success "Service restarted"
        ;;
    
    build)
        print_info "Building Docker images for service: $SERVICE"
        $DOCKER_COMPOSE -f "$COMPOSE_FILE" build "$SERVICE"
        print_success "Images built successfully"
        ;;
    
    logs)
        print_info "Showing logs for service: $SERVICE"
        $DOCKER_COMPOSE -f "$COMPOSE_FILE" logs -f "$SERVICE"
        ;;
    
    status)
        print_info "Service status:"
        $DOCKER_COMPOSE -f "$COMPOSE_FILE" ps
        ;;
    
    clean)
        print_warning "This will remove all containers, networks, and images"
        read -p "Are you sure? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "Stopping all services..."
            $DOCKER_COMPOSE -f "$COMPOSE_FILE" down
            
            print_info "Removing containers..."
            docker container prune -f
            
            print_info "Removing images..."
            docker image prune -f
            
            print_info "Removing volumes..."
            docker volume prune -f
            
            print_success "Cleanup completed"
        else
            print_info "Cleanup cancelled"
        fi
        ;;
    
    *)
        print_error "Unknown action: $ACTION"
        show_usage
        exit 1
        ;;
esac