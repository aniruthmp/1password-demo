#!/bin/bash
# Universal 1Password Credential Broker - Health Check Script
# Verifies all services are running and healthy

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

# Parse command line arguments
QUIET_MODE=false
if [ "$1" == "--quiet" ]; then
    QUIET_MODE=true
fi

if [ "$QUIET_MODE" == false ]; then
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}   Universal 1Password Credential Broker - Health Check${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Error: Docker is not running${NC}"
    exit 1
fi

# Change to project directory
cd "$PROJECT_ROOT"

# Function to check service health
check_service() {
    local service_name=$1
    local health_url=$2
    local container_name=$3
    
    if [ "$QUIET_MODE" == false ]; then
        echo -e "${BLUE}Checking ${service_name}...${NC}"
    fi
    
    # Check if container is running
    if ! docker ps --format '{{.Names}}' | grep -q "^${container_name}$"; then
        echo -e "${RED}❌ ${service_name} container is not running${NC}"
        return 1
    fi
    
    # Check container health status
    HEALTH_STATUS=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "none")
    
    if [ "$HEALTH_STATUS" == "healthy" ]; then
        if [ "$QUIET_MODE" == false ]; then
            echo -e "${GREEN}✓${NC} Container health: ${GREEN}healthy${NC}"
        fi
    elif [ "$HEALTH_STATUS" == "starting" ]; then
        if [ "$QUIET_MODE" == false ]; then
            echo -e "${YELLOW}⏳${NC} Container health: ${YELLOW}starting${NC}"
        fi
    elif [ "$HEALTH_STATUS" == "unhealthy" ]; then
        echo -e "${RED}❌ Container health: ${RED}unhealthy${NC}"
        return 1
    fi
    
    # Check HTTP endpoint
    if [ -n "$health_url" ]; then
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$health_url" 2>/dev/null || echo "000")
        
        if [ "$HTTP_CODE" == "200" ]; then
            if [ "$QUIET_MODE" == false ]; then
                echo -e "${GREEN}✓${NC} HTTP health check: ${GREEN}passed${NC}"
            fi
        else
            echo -e "${RED}❌ HTTP health check failed (HTTP $HTTP_CODE)${NC}"
            return 1
        fi
        
        # Get detailed status
        STATUS_RESPONSE=$(curl -s "$health_url" 2>/dev/null)
        if [ "$QUIET_MODE" == false ]; then
            echo -e "${GREEN}✓${NC} ${service_name} is ${GREEN}healthy${NC}"
            echo -e "  Status: $(echo "$STATUS_RESPONSE" | jq -r '.status // "ok"' 2>/dev/null || echo "ok")"
        fi
    fi
    
    if [ "$QUIET_MODE" == false ]; then
        echo ""
    fi
    
    return 0
}

# Track overall health
ALL_HEALTHY=true

# Check A2A Server
if ! check_service "A2A Server" "http://localhost:8000/health" "1password-a2a-server"; then
    ALL_HEALTHY=false
fi

# Check ACP Server
if ! check_service "ACP Server" "http://localhost:8001/health" "1password-acp-server"; then
    ALL_HEALTHY=false
fi

# Check MCP Server (if running)
if docker ps --format '{{.Names}}' | grep -q "^1password-mcp-server$"; then
    if ! check_service "MCP Server" "" "1password-mcp-server"; then
        ALL_HEALTHY=false
    fi
fi

# Summary
if [ "$QUIET_MODE" == false ]; then
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
fi

if [ "$ALL_HEALTHY" == true ]; then
    if [ "$QUIET_MODE" == false ]; then
        echo -e "${GREEN}✓ All services are healthy${NC}"
        echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "${YELLOW}Service Endpoints:${NC}"
        echo -e "  A2A Server: ${BLUE}http://localhost:8000${NC}"
        echo -e "  ACP Server: ${BLUE}http://localhost:8001${NC}"
        echo ""
        echo -e "${YELLOW}View detailed status:${NC}"
        echo -e "  curl http://localhost:8000/status | jq"
        echo -e "  curl http://localhost:8001/status | jq"
        echo ""
    else
        echo -e "${GREEN}✓ All services healthy${NC}"
    fi
    exit 0
else
    if [ "$QUIET_MODE" == false ]; then
        echo -e "${RED}❌ Some services are unhealthy${NC}"
        echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "${YELLOW}Troubleshooting:${NC}"
        echo -e "  View logs:    docker-compose logs -f"
        echo -e "  Restart:      ./scripts/stop-all.sh && ./scripts/start-all.sh"
        echo ""
    else
        echo -e "${RED}❌ Service health check failed${NC}"
    fi
    exit 1
fi

