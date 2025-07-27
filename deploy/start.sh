#!/bin/bash
# MCP Base64 Server Startup Script
# This script provides a convenient way to start the server with different configurations

set -e

# Default values
TRANSPORT="stdio"
ENABLE_HTTP_SERVER="false"
LOG_LEVEL="INFO"
CONFIG_FILE="config.yaml"

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

# Function to show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    -t, --transport TYPE        Transport type: stdio or http (default: stdio)
    -s, --enable-http-server    Enable standalone HTTP API server
    -l, --log-level LEVEL       Log level: DEBUG, INFO, WARNING, ERROR (default: INFO)
    -c, --config FILE           Configuration file path (default: config.yaml)
    -p, --http-port PORT        HTTP API server port (default: 8080)
    -m, --mcp-port PORT         MCP HTTP transport port (default: 3000)
    -h, --help                  Show this help message

Examples:
    $0                          # Start with stdio transport
    $0 -t http -s               # Start with HTTP transport and API server
    $0 -t stdio -l DEBUG        # Start with stdio transport and debug logging
    $0 -c custom-config.yaml    # Start with custom configuration file

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--transport)
            TRANSPORT="$2"
            shift 2
            ;;
        -s|--enable-http-server)
            ENABLE_HTTP_SERVER="true"
            shift
            ;;
        -l|--log-level)
            LOG_LEVEL="$2"
            shift 2
            ;;
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -p|--http-port)
            HTTP_PORT="$2"
            shift 2
            ;;
        -m|--mcp-port)
            MCP_PORT="$2"
            shift 2
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

# Validate transport type
if [[ "$TRANSPORT" != "stdio" && "$TRANSPORT" != "http" ]]; then
    print_error "Invalid transport type: $TRANSPORT. Must be 'stdio' or 'http'"
    exit 1
fi

# Check if configuration file exists
if [[ ! -f "$CONFIG_FILE" ]]; then
    print_error "Configuration file not found: $CONFIG_FILE"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed or not in PATH"
    exit 1
fi

# Check if required Python packages are installed
print_info "Checking Python dependencies..."
if ! python3 -c "import yaml, psutil, flask" &> /dev/null; then
    print_warning "Some Python dependencies are missing. Installing..."
    pip3 install -r requirements.txt
fi

# Create logs directory if it doesn't exist
mkdir -p logs

# Build command line arguments
ARGS=("--transport" "$TRANSPORT" "--log-level" "$LOG_LEVEL" "--config" "$CONFIG_FILE")

if [[ "$ENABLE_HTTP_SERVER" == "true" ]]; then
    ARGS+=("--enable-http-server")
fi

if [[ -n "$HTTP_PORT" ]]; then
    ARGS+=("--http-server-port" "$HTTP_PORT")
fi

if [[ -n "$MCP_PORT" ]]; then
    ARGS+=("--http-port" "$MCP_PORT")
fi

# Print startup information
print_info "Starting MCP Base64 Server..."
print_info "Transport: $TRANSPORT"
print_info "HTTP Server: $ENABLE_HTTP_SERVER"
print_info "Log Level: $LOG_LEVEL"
print_info "Config File: $CONFIG_FILE"

# Start the server
print_info "Executing: python3 main.py ${ARGS[*]}"
exec python3 main.py "${ARGS[@]}"