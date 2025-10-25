#!/bin/bash
# FastAPI Dashboard Runner - Using Poetry for Dependency Management
# This script runs the dashboard using Poetry for dependency management

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the absolute path to frontend directory
FRONTEND_DIR="$(cd "$(dirname "$0")" && pwd)"
export OP_CONNECT_HOST="http://localhost:8080"

echo -e "${BLUE}Starting FastAPI Dashboard with Poetry from: ${FRONTEND_DIR}${NC}"

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo -e "${RED}Error: Poetry is not installed.${NC}"
    echo -e "${YELLOW}Install with: curl -sSL https://install.python-poetry.org | python3 -${NC}"
    exit 1
fi

# Change to frontend directory
cd "$FRONTEND_DIR"

# Check if pyproject.toml exists
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}Error: pyproject.toml not found in frontend directory.${NC}"
    exit 1
fi

# Check if Poetry environment is set up
if ! poetry env info &> /dev/null; then
    echo -e "${YELLOW}Poetry environment not found. Installing dependencies...${NC}"
    poetry install
fi

echo -e "${GREEN}✓ Poetry environment ready${NC}"

# Check if .env exists in frontend
if [ ! -f "$FRONTEND_DIR/.env" ]; then
    echo -e "${YELLOW}Warning: .env file not found in frontend directory.${NC}"
    echo -e "${YELLOW}You may need to create a .env file with your configuration.${NC}"
fi

# Check if port 3000 is available
if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo -e "${RED}Error: Port 3000 is already in use.${NC}"
    echo -e "${YELLOW}Kill with: lsof -ti:3000 | xargs kill -9${NC}"
    exit 1
fi

# Start the server
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Starting FastAPI Dashboard Server${NC}"
echo -e "${GREEN}(Using Poetry for Dependencies)${NC}"
echo -e "${GREEN}========================================${NC}"
echo -e "${BLUE}Dashboard URL:${NC} http://localhost:3000"
echo -e "${BLUE}Health Check:${NC} http://localhost:3000/health"
echo -e "${BLUE}WebSocket:${NC} ws://localhost:3000/ws"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

# Run with poetry from frontend directory
cd "$FRONTEND_DIR"

# Add backend to Python path for imports and run uvicorn
BACKEND_DIR="$(cd "$(dirname "$0")/../backend" && pwd)"
PYTHONPATH="$BACKEND_DIR:$PYTHONPATH" poetry run uvicorn app:app \
  --host 0.0.0.0 \
  --port 3000 \
  --reload \
  --log-level info

