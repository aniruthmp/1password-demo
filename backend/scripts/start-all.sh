#!/bin/bash
# Universal 1Password Credential Broker - Startup Script
# Starts all services (MCP, A2A, ACP)

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   Universal 1Password Credential Broker - Startup${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Check if .env file exists
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo -e "${RED}❌ Error: .env file not found${NC}"
    echo -e "${YELLOW}Please create .env file from .env.example and configure your credentials${NC}"
    echo -e "Run: cp .env.example .env"
    exit 1
fi

echo -e "${GREEN}✓${NC} Found .env configuration"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Docker is not running${NC}"
    echo -e "${YELLOW}Please start Docker Desktop or Docker daemon${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} Docker is running"

# Load environment variables
source "$PROJECT_ROOT/.env"

# Check required environment variables
REQUIRED_VARS=("OP_CONNECT_HOST" "OP_CONNECT_TOKEN" "JWT_SECRET_KEY")
MISSING_VARS=()

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -ne 0 ]; then
    echo -e "${RED}❌ Error: Missing required environment variables:${NC}"
    for var in "${MISSING_VARS[@]}"; do
        echo -e "  - ${YELLOW}${var}${NC}"
    done
    echo -e "${YELLOW}Please configure these in your .env file${NC}"
    exit 1
fi

echo -e "${GREEN}✓${NC} All required environment variables configured"
echo ""

# Parse command line arguments
PROFILE=""
BUILD_FLAG=""
DETACH_FLAG="-d"

while [[ $# -gt 0 ]]; do
    case $1 in
        --with-mcp)
            PROFILE="--profile mcp"
            shift
            ;;
        --build)
            BUILD_FLAG="--build"
            shift
            ;;
        --foreground)
            DETACH_FLAG=""
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Usage: $0 [--with-mcp] [--build] [--foreground]"
            exit 1
            ;;
    esac
done

# Create necessary directories
echo -e "${BLUE}Creating directories...${NC}"
mkdir -p "$PROJECT_ROOT/logs"
mkdir -p "$PROJECT_ROOT/data"
echo -e "${GREEN}✓${NC} Directories created"
echo ""

# Stop any existing containers
echo -e "${BLUE}Stopping existing containers...${NC}"
cd "$PROJECT_ROOT"
docker-compose down > /dev/null 2>&1 || true
echo -e "${GREEN}✓${NC} Existing containers stopped"
echo ""

# Start services
echo -e "${BLUE}Starting services...${NC}"
if [ -n "$BUILD_FLAG" ]; then
    echo -e "${YELLOW}Building Docker images...${NC}"
fi

docker-compose $PROFILE up $BUILD_FLAG $DETACH_FLAG

if [ -n "$DETACH_FLAG" ]; then
    echo ""
    echo -e "${GREEN}✓${NC} Services started successfully"
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}   Service Status${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${GREEN}A2A Server:${NC}  http://localhost:8000"
    echo -e "  - Agent Card: ${BLUE}http://localhost:8000/agent-card${NC}"
    echo -e "  - Health:     ${BLUE}http://localhost:8000/health${NC}"
    echo -e "  - Status:     ${BLUE}http://localhost:8000/status${NC}"
    echo ""
    echo -e "${GREEN}ACP Server:${NC}  http://localhost:8001"
    echo -e "  - Agents:     ${BLUE}http://localhost:8001/agents${NC}"
    echo -e "  - Health:     ${BLUE}http://localhost:8001/health${NC}"
    echo -e "  - Status:     ${BLUE}http://localhost:8001/status${NC}"
    echo ""
    if [ -n "$PROFILE" ]; then
        echo -e "${GREEN}MCP Server:${NC}  Running (stdio-based, use demo script)"
        echo ""
    fi
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${YELLOW}Useful Commands:${NC}"
    echo -e "  View logs:        docker-compose logs -f"
    echo -e "  Stop services:    ./scripts/stop-all.sh"
    echo -e "  Check health:     ./scripts/health-check.sh"
    echo -e "  Run A2A demo:     python demos/a2a_demo.py"
    echo -e "  Run ACP demo:     python demos/acp_demo.py"
    echo ""
    
    # Wait a moment for services to start
    echo -e "${YELLOW}Waiting for services to initialize...${NC}"
    sleep 5
    
    # Run health check
    "$SCRIPT_DIR/health-check.sh" --quiet
fi

