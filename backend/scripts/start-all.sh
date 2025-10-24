#!/bin/bash
# Universal 1Password Credential Broker - Startup Script
# Starts all services (MCP, A2A, ACP) using Python directly or Docker containers

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
LOGS_DIR="$PROJECT_ROOT/logs"
PID_DIR="$PROJECT_ROOT/logs"

# Default mode is non-Docker
DOCKER_MODE=false

# Parse command line arguments first
START_A2A=true
START_ACP=true
LOG_LEVEL="INFO"
BUILD_FLAG=""
DETACH_FLAG="-d"
export OP_CONNECT_HOST="http://localhost:8080"

while [[ $# -gt 0 ]]; do
    case $1 in
        --docker)
            DOCKER_MODE=true
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
        --without-a2a)
            START_A2A=false
            shift
            ;;
        --without-acp)
            START_ACP=false
            shift
            ;;
        --log-level)
            LOG_LEVEL="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [--docker] [--build] [--foreground] [--without-a2a] [--without-acp] [--log-level LEVEL]"
            echo ""
            echo "Options:"
            echo "  --docker          Start services using Docker containers (default: Python directly)"
            echo "  --build           Build Docker images before starting (Docker mode only)"
            echo "  --foreground      Run Docker containers in foreground (Docker mode only)"
            echo "  --without-a2a     Skip starting A2A server (non-Docker mode only)"
            echo "  --without-acp     Skip starting ACP server (non-Docker mode only)"
            echo "  --log-level       Set log level (DEBUG, INFO, WARNING, ERROR, CRITICAL) (non-Docker mode only)"
            echo "  --help            Show this help message"
            echo ""
            echo "Note: MCP Server runs interactively via stdio and is not managed by this script"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
if [ "$DOCKER_MODE" = true ]; then
    echo -e "${BLUE}   Universal 1Password Credential Broker - Startup (Docker)${NC}"
else
    echo -e "${BLUE}   Universal 1Password Credential Broker - Startup (Non-Docker)${NC}"
fi
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

# Load environment variables
source "$PROJECT_ROOT/.env"

# Set OP_CONNECT_HOST based on mode
if [ "$DOCKER_MODE" = true ]; then
    export OP_CONNECT_HOST="http://host.docker.internal:8080"
    echo -e "${GREEN}✓${NC} Using Docker mode - OP_CONNECT_HOST set to host.docker.internal"
else
    echo -e "${GREEN}✓${NC} Using non-Docker mode - OP_CONNECT_HOST set to localhost"
fi

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

# Create necessary directories
echo -e "${BLUE}Creating directories...${NC}"
mkdir -p "$LOGS_DIR"
mkdir -p "$PROJECT_ROOT/data"
echo -e "${GREEN}✓${NC} Directories created"
echo ""

# Change to project directory
cd "$PROJECT_ROOT"

if [ "$DOCKER_MODE" = true ]; then
    # Docker mode
    echo -e "${GREEN}✓${NC} Docker mode selected"
    
    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        echo -e "${RED}❌ Error: Docker is not running${NC}"
        echo -e "${YELLOW}Please start Docker Desktop or Docker daemon${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓${NC} Docker is running"
    
    # Stop any existing containers
    echo -e "${BLUE}Stopping existing containers...${NC}"
    docker-compose down > /dev/null 2>&1 || true
    echo -e "${GREEN}✓${NC} Existing containers stopped"
    echo ""
    
    # Start services
    echo -e "${BLUE}Starting services...${NC}"
    if [ -n "$BUILD_FLAG" ]; then
        echo -e "${YELLOW}Building Docker images...${NC}"
    fi
    
    docker-compose up $BUILD_FLAG $DETACH_FLAG
    
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
        echo -e "${GREEN}MCP Server:${NC}  Available for interactive use (stdio-based)"
        echo -e "  - Usage:     ${BLUE}docker-compose run --rm mcp-server${NC}"
        echo -e "  - Demo:       ${BLUE}poetry run python demos/mcp_demo.py${NC}"
        echo -e "  - Note:       ${YELLOW}MCP runs interactively via stdio${NC}"
        echo ""
        echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "${YELLOW}Useful Commands:${NC}"
        echo -e "  View logs:        docker-compose logs -f"
        echo -e "  Stop services:    ./scripts/stop-all.sh"
        echo -e "  Check health:     ./scripts/health-check.sh"
        echo -e "  Run A2A demo:     python demos/a2a_demo.py"
        echo -e "  Run ACP demo:     python demos/acp_demo.py"
        echo -e "  Run MCP demo:     python demos/mcp_demo.py"
        echo ""
        
        # Wait a moment for services to start
        echo -e "${YELLOW}Waiting for services to initialize...${NC}"
        sleep 5
        
        # Run health check
        "$SCRIPT_DIR/health-check.sh" --quiet
    fi
    
else
    # Non-Docker mode
    echo -e "${GREEN}✓${NC} Non-Docker mode selected"
    
    # Check if Python is available
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Error: Python 3 is not installed or not in PATH${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓${NC} Python 3 is available"
    
    # Check if Poetry is available
    if ! command -v poetry &> /dev/null; then
        echo -e "${RED}❌ Error: Poetry is not installed${NC}"
        echo -e "${YELLOW}Please install Poetry: https://python-poetry.org/docs/#installation${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓${NC} Poetry is available"
    
    # Stop any existing services
    echo -e "${BLUE}Stopping existing services...${NC}"
    "$SCRIPT_DIR/stop-all.sh" --quiet 2>/dev/null || true
    echo -e "${GREEN}✓${NC} Existing services stopped"
    echo ""
    
    # Install dependencies if needed
    echo -e "${BLUE}Checking dependencies...${NC}"
    if [ ! -d ".venv" ] || [ ! -f "poetry.lock" ]; then
        echo -e "${YELLOW}Installing dependencies with Poetry...${NC}"
        poetry install
    fi
    echo -e "${GREEN}✓${NC} Dependencies ready"
    echo ""
    
    # Start services
    echo -e "${BLUE}Starting services...${NC}"
    
    # Convert log level to lowercase for Python scripts
    PYTHON_LOG_LEVEL=$(echo "$LOG_LEVEL" | tr '[:upper:]' '[:lower:]')
    
    # Start A2A Server
    if [ "$START_A2A" = true ]; then
        echo -e "${YELLOW}Starting A2A Server...${NC}"
        nohup poetry run python src/a2a/run_a2a.py \
            --host 0.0.0.0 \
            --port 8000 \
            --log-level "$PYTHON_LOG_LEVEL" \
            > "$LOGS_DIR/a2a-server.log" 2>&1 &
        echo $! > "$PID_DIR/a2a-server.pid"
        echo -e "${GREEN}✓${NC} A2A Server started (PID: $(cat "$PID_DIR/a2a-server.pid"))"
    fi
    
    # Start ACP Server
    if [ "$START_ACP" = true ]; then
        echo -e "${YELLOW}Starting ACP Server...${NC}"
        nohup poetry run python src/acp/run_acp.py \
            --host 0.0.0.0 \
            --port 8001 \
            --log-level "$PYTHON_LOG_LEVEL" \
            > "$LOGS_DIR/acp-server.log" 2>&1 &
        echo $! > "$PID_DIR/acp-server.pid"
        echo -e "${GREEN}✓${NC} ACP Server started (PID: $(cat "$PID_DIR/acp-server.pid"))"
    fi
    
    # MCP Server runs interactively via stdio and is not managed by this script
    echo -e "${YELLOW}Note: MCP Server runs interactively via stdio and is not managed by this script${NC}"
    echo -e "${YELLOW}To use MCP Server, run: poetry run python src/mcp/run_mcp.py${NC}"
    
    echo ""
    echo -e "${GREEN}✓${NC} All services started successfully"
    echo ""
    
    # Wait a moment for services to start
    echo -e "${YELLOW}Waiting for services to initialize...${NC}"
    sleep 5
    
    # Check service status
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}   Service Status${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    if [ "$START_A2A" = true ]; then
        A2A_PID=$(cat "$PID_DIR/a2a-server.pid" 2>/dev/null || echo "")
        if [ -n "$A2A_PID" ] && kill -0 "$A2A_PID" 2>/dev/null; then
            echo -e "${GREEN}A2A Server:${NC}  http://localhost:8000 (PID: $A2A_PID)"
            echo -e "  - Agent Card: ${BLUE}http://localhost:8000/agent-card${NC}"
            echo -e "  - Health:     ${BLUE}http://localhost:8000/health${NC}"
            echo -e "  - Status:     ${BLUE}http://localhost:8000/status${NC}"
            echo -e "  - Log:        ${BLUE}$LOGS_DIR/a2a-server.log${NC}"
        else
            echo -e "${RED}A2A Server:${NC}  Failed to start"
        fi
        echo ""
    fi
    
    if [ "$START_ACP" = true ]; then
        ACP_PID=$(cat "$PID_DIR/acp-server.pid" 2>/dev/null || echo "")
        if [ -n "$ACP_PID" ] && kill -0 "$ACP_PID" 2>/dev/null; then
            echo -e "${GREEN}ACP Server:${NC}  http://localhost:8001 (PID: $ACP_PID)"
            echo -e "  - Agents:     ${BLUE}http://localhost:8001/agents${NC}"
            echo -e "  - Health:     ${BLUE}http://localhost:8001/health${NC}"
            echo -e "  - Status:     ${BLUE}http://localhost:8001/status${NC}"
            echo -e "  - Log:        ${BLUE}$LOGS_DIR/acp-server.log${NC}"
        else
            echo -e "${RED}ACP Server:${NC}  Failed to start"
        fi
        echo ""
    fi
    
    echo -e "${GREEN}MCP Server:${NC}  Available for interactive use (stdio-based)"
    echo -e "  - Usage:     ${BLUE}poetry run python src/mcp/run_mcp.py${NC}"
    echo -e "  - Demo:       ${BLUE}poetry run python demos/mcp_demo.py${NC}"
    echo -e "  - Note:       ${YELLOW}MCP runs interactively, not as background service${NC}"
    echo ""
    
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${YELLOW}Useful Commands:${NC}"
    echo -e "  View logs:        tail -f $LOGS_DIR/*.log"
    echo -e "  Stop services:     ./scripts/stop-all.sh"
    echo -e "  Check health:      ./scripts/health-check.sh"
    echo -e "  Run A2A demo:      poetry run python demos/a2a_demo.py"
    echo -e "  Run ACP demo:      poetry run python demos/acp_demo.py"
    echo -e "  Run MCP demo:      poetry run python demos/mcp_demo.py"
    echo ""
    
    # Run health check if available
    if [ -f "$SCRIPT_DIR/health-check.sh" ]; then
        echo -e "${YELLOW}Running health check...${NC}"
        "$SCRIPT_DIR/health-check.sh" --quiet 2>/dev/null || true
    fi
fi

echo -e "${GREEN}Startup complete!${NC}"
