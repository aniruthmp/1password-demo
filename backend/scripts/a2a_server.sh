#!/bin/bash
#
# A2A Server Startup Script
# 
# This script properly initializes the Poetry environment and starts the A2A server
# with all necessary environment variables loaded from .env
#
# Usage:
#   ./scripts/a2a_server.sh [--port PORT] [--log-level LEVEL] [--reload]
#
# Options:
#   --port PORT              Set server port (default: 8000)
#   --host HOST              Set server host (default: 0.0.0.0)
#   --log-level LEVEL        Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
#                            Default: INFO
#   --reload                 Enable auto-reload for development
#   --workers WORKERS        Number of worker processes (default: 1)
#
# Prerequisites:
#   - Poetry must be installed
#   - .env file must exist with required configuration
#   - Dependencies must be installed (run: poetry install)
#

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$BACKEND_DIR")"

# Default values
PORT="8000"
HOST="0.0.0.0"
LOG_LEVEL="INFO"
RELOAD=""
WORKERS="1"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            PORT="$2"
            shift 2
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        --log-level)
            LOG_LEVEL="$2"
            shift 2
            ;;
        --reload)
            RELOAD="--reload"
            shift
            ;;
        --workers)
            WORKERS="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --port PORT              Set server port (default: 8000)"
            echo "  --host HOST              Set server host (default: 0.0.0.0)"
            echo "  --log-level LEVEL        Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
            echo "                           Default: INFO"
            echo "  --reload                 Enable auto-reload for development"
            echo "  --workers WORKERS        Number of worker processes (default: 1)"
            echo "  -h, --help               Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                              # Start with default settings"
            echo "  $0 --port 8001                  # Start on port 8001"
            echo "  $0 --reload --log-level DEBUG   # Development mode with debug logging"
            echo "  $0 --workers 4                  # Start with 4 worker processes"
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Validate log level
case $LOG_LEVEL in
    DEBUG|INFO|WARNING|ERROR|CRITICAL)
        ;;
    *)
        echo -e "${RED}❌ Invalid log level: $LOG_LEVEL${NC}"
        echo "Valid levels: DEBUG, INFO, WARNING, ERROR, CRITICAL"
        exit 1
        ;;
esac

# Validate port
if ! [[ "$PORT" =~ ^[0-9]+$ ]] || [ "$PORT" -lt 1 ] || [ "$PORT" -gt 65535 ]; then
    echo -e "${RED}❌ Invalid port: $PORT${NC}"
    echo "Port must be a number between 1 and 65535"
    exit 1
fi

# Function to print status messages
print_status() {
    echo -e "${BLUE}➜${NC} $1"
}

print_success() {
    echo -e "${GREEN}✅${NC} $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC}  $1"
}

# Function to cleanup on exit
cleanup() {
    echo ""
    print_status "Shutting down A2A server gracefully..."
    exit 0
}

# Trap signals for graceful shutdown
trap cleanup SIGINT SIGTERM

# Print header
echo ""
echo "============================================================"
echo "  1Password Credential Broker - A2A Server Launcher"
echo "============================================================"
echo ""

# Step 1: Change to backend directory
print_status "Changing to backend directory..."
cd "$BACKEND_DIR" || {
    print_error "Failed to change to backend directory: $BACKEND_DIR"
    exit 1
}
print_success "Working directory: $BACKEND_DIR"
echo ""

# Step 2: Check if .env file exists
print_status "Checking for .env file..."
if [ ! -f ".env" ]; then
    print_error ".env file not found!"
    echo ""
    echo "Please create a .env file with the following variables:"
    echo "  OP_CONNECT_HOST=http://localhost:8080"
    echo "  OP_CONNECT_TOKEN=your_connect_token"
    echo "  OP_VAULT_ID=your_vault_id"
    echo "  JWT_SECRET_KEY=your_secret_key_at_least_32_chars"
    echo "  A2A_BEARER_TOKEN=your_bearer_token_for_a2a_auth"
    echo ""
    echo "You can copy from .env.example:"
    echo "  cp .env.example .env"
    exit 1
fi
print_success ".env file found"
echo ""

# Step 3: Load environment variables from .env
print_status "Loading environment variables from .env..."
set -a  # Automatically export all variables
source .env
set +a  # Stop auto-export
print_success "Environment variables loaded"
echo ""

# Step 4: Verify required environment variables
print_status "Verifying required environment variables..."
MISSING_VARS=()

if [ -z "$OP_CONNECT_HOST" ]; then
    MISSING_VARS+=("OP_CONNECT_HOST")
fi
if [ -z "$OP_CONNECT_TOKEN" ]; then
    MISSING_VARS+=("OP_CONNECT_TOKEN")
fi
if [ -z "$OP_VAULT_ID" ]; then
    MISSING_VARS+=("OP_VAULT_ID")
fi
if [ -z "$JWT_SECRET_KEY" ]; then
    MISSING_VARS+=("JWT_SECRET_KEY")
fi

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    print_error "Missing required environment variables:"
    for var in "${MISSING_VARS[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo "Please update your .env file with all required variables."
    exit 1
fi
print_success "All required environment variables present"

# Optional warning for A2A bearer token
if [ -z "$A2A_BEARER_TOKEN" ]; then
    print_warning "A2A_BEARER_TOKEN not set, using default (dev-token-change-in-production)"
    print_warning "For production, set A2A_BEARER_TOKEN in .env"
fi
echo ""

# Step 5: Check if Poetry is installed
print_status "Checking for Poetry installation..."
if ! command -v poetry &> /dev/null; then
    print_error "Poetry is not installed!"
    echo ""
    echo "Please install Poetry:"
    echo "  curl -sSL https://install.python-poetry.org | python3 -"
    exit 1
fi
print_success "Poetry is installed: $(poetry --version)"
echo ""

# Step 6: Check if dependencies are installed
print_status "Checking Poetry dependencies..."
if ! poetry run python -c "import fastapi" &> /dev/null; then
    print_warning "Dependencies not installed or incomplete"
    print_status "Installing dependencies..."
    poetry install
    print_success "Dependencies installed"
else
    print_success "Dependencies are installed"
fi
echo ""

# Step 7: Verify A2A server script exists
print_status "Verifying A2A server script..."
if [ ! -f "src/a2a/run_a2a.py" ]; then
    print_error "A2A server script not found: src/a2a/run_a2a.py"
    exit 1
fi
print_success "A2A server script found"
echo ""

# Step 8: Check if port is available
print_status "Checking if port $PORT is available..."
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    print_error "Port $PORT is already in use!"
    echo ""
    echo "Please stop the service using port $PORT or use a different port:"
    echo "  $0 --port 8001"
    exit 1
fi
print_success "Port $PORT is available"
echo ""

# Step 9: Start the A2A server
echo "============================================================"
echo "  Starting A2A Server"
echo "============================================================"
echo ""
echo "Configuration:"
echo "  Host:             $HOST"
echo "  Port:             $PORT"
echo "  Log Level:        $LOG_LEVEL"
echo "  Connect Host:     $OP_CONNECT_HOST"
echo "  Vault ID:         $OP_VAULT_ID"
echo "  Workers:          $WORKERS"
if [ -n "$RELOAD" ]; then
echo "  Auto-reload:      Enabled"
fi
echo ""
echo "API Endpoints:"
echo "  Agent Card:       http://${HOST}:${PORT}/agent-card"
echo "  Task Execution:   http://${HOST}:${PORT}/task"
echo "  Health Check:     http://${HOST}:${PORT}/health"
echo "  API Docs:         http://${HOST}:${PORT}/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""
echo "============================================================"
echo ""

# Build command arguments
CMD_ARGS="--host $HOST --port $PORT --log-level $(echo $LOG_LEVEL | tr '[:upper:]' '[:lower:]')"

if [ -n "$RELOAD" ]; then
    CMD_ARGS="$CMD_ARGS --reload"
else
    CMD_ARGS="$CMD_ARGS --workers $WORKERS"
fi

# Run the A2A server using Poetry
# Poetry automatically activates the virtual environment when using 'poetry run'
exec poetry run python src/a2a/run_a2a.py $CMD_ARGS

