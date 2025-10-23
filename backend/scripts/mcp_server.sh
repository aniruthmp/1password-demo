#!/bin/bash
#
# MCP Server Startup Script
# 
# This script properly initializes the Poetry environment and starts the MCP server
# with all necessary environment variables loaded from .env
#
# Usage:
#   ./scripts/mcp_server.sh [--log-level LEVEL]
#
# Options:
#   --log-level LEVEL    Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
#                        Default: INFO
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

# Default log level
LOG_LEVEL="INFO"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --log-level)
            LOG_LEVEL="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--log-level LEVEL]"
            echo ""
            echo "Options:"
            echo "  --log-level LEVEL    Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)"
            echo "                       Default: INFO"
            echo "  -h, --help          Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0                          # Start with INFO logging"
            echo "  $0 --log-level DEBUG        # Start with DEBUG logging"
            echo "  $0 --log-level ERROR        # Start with ERROR logging"
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
    print_status "Shutting down MCP server gracefully..."
    exit 0
}

# Trap signals for graceful shutdown
trap cleanup SIGINT SIGTERM

# Print header
echo ""
echo "============================================================"
echo "  1Password Credential Broker - MCP Server Launcher"
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
if ! poetry run python -c "import mcp" &> /dev/null; then
    print_warning "Dependencies not installed or incomplete"
    print_status "Installing dependencies..."
    poetry install
    print_success "Dependencies installed"
else
    print_success "Dependencies are installed"
fi
echo ""

# Step 7: Verify MCP server script exists
print_status "Verifying MCP server script..."
if [ ! -f "src/mcp/run_mcp.py" ]; then
    print_error "MCP server script not found: src/mcp/run_mcp.py"
    exit 1
fi
print_success "MCP server script found"
echo ""

# Step 8: Start the MCP server
echo "============================================================"
echo "  Starting MCP Server"
echo "============================================================"
echo ""
echo "Configuration:"
echo "  Log Level:        $LOG_LEVEL"
echo "  Connect Host:     $OP_CONNECT_HOST"
echo "  Vault ID:         $OP_VAULT_ID"
echo "  Transport:        stdio"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""
echo "============================================================"
echo ""

# Run the MCP server using Poetry
# Poetry automatically activates the virtual environment when using 'poetry run'
exec poetry run python src/mcp/run_mcp.py --log-level "$LOG_LEVEL"

