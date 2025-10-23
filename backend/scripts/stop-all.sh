#!/bin/bash
# Universal 1Password Credential Broker - Stop Script
# Gracefully stops all services

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
echo -e "${BLUE}   Universal 1Password Credential Broker - Shutdown${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Docker is not running${NC}"
    exit 1
fi

# Change to project directory
cd "$PROJECT_ROOT"

# Parse command line arguments
REMOVE_VOLUMES=""
REMOVE_IMAGES=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --clean)
            REMOVE_VOLUMES="--volumes"
            shift
            ;;
        --purge)
            REMOVE_VOLUMES="--volumes"
            REMOVE_IMAGES="--rmi local"
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Usage: $0 [--clean] [--purge]"
            echo "  --clean: Remove volumes (logs, data)"
            echo "  --purge: Remove volumes and images"
            exit 1
            ;;
    esac
done

# Stop services
echo -e "${YELLOW}Stopping services...${NC}"
docker-compose down $REMOVE_VOLUMES $REMOVE_IMAGES

echo ""
echo -e "${GREEN}✓${NC} All services stopped successfully"

if [ -n "$REMOVE_VOLUMES" ]; then
    echo -e "${GREEN}✓${NC} Volumes removed"
fi

if [ -n "$REMOVE_IMAGES" ]; then
    echo -e "${GREEN}✓${NC} Images removed"
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Shutdown complete${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Show remaining containers (if any)
RUNNING_CONTAINERS=$(docker ps --filter "name=1password" -q)
if [ -n "$RUNNING_CONTAINERS" ]; then
    echo -e "${YELLOW}⚠ Warning: Some 1Password containers are still running:${NC}"
    docker ps --filter "name=1password" --format "  - {{.Names}} ({{.Status}})"
    echo ""
fi

