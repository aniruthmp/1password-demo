#!/bin/bash
# Universal 1Password Credential Broker - Health Check Script
# Verifies all services are running and healthy (Docker or non-Docker)

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
PID_DIR="$PROJECT_ROOT/logs"

# Default mode is non-Docker
DOCKER_MODE=false

# Parse command line arguments
QUIET_MODE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --docker)
            DOCKER_MODE=true
            shift
            ;;
        --quiet)
            QUIET_MODE=true
            shift
            ;;
        --help)
            echo "Usage: $0 [--docker] [--quiet]"
            echo ""
            echo "Options:"
            echo "  --docker       Check Docker containers (default: check Python processes)"
            echo "  --quiet        Suppress most output"
            echo "  --help         Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Function to print messages (respects --quiet flag)
print_msg() {
    if [ "$QUIET_MODE" = false ]; then
        echo -e "$1"
    fi
}

print_msg "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
if [ "$DOCKER_MODE" = true ]; then
    print_msg "${BLUE}   Universal 1Password Credential Broker - Health Check (Docker)${NC}"
else
    print_msg "${BLUE}   Universal 1Password Credential Broker - Health Check (Non-Docker)${NC}"
fi
print_msg "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
print_msg ""

# Change to project directory
cd "$PROJECT_ROOT"

if [ "$DOCKER_MODE" = true ]; then
    # Docker mode
    print_msg "${GREEN}✓${NC} Docker mode selected"
    
    # Check if Docker is running
    if ! docker info > /dev/null 2>&1; then
        print_msg "${RED}❌ Error: Docker is not running${NC}"
        exit 1
    fi
    
    print_msg "${GREEN}✓${NC} Docker is running"
    
    # Function to check Docker service health
    check_docker_service() {
        local service_name=$1
        local health_url=$2
        local container_name=$3
        
        print_msg "${BLUE}Checking ${service_name}...${NC}"
        
        # Check if container is running
        if ! docker ps --format '{{.Names}}' | grep -q "^${container_name}$"; then
            print_msg "${RED}❌ ${service_name} container is not running${NC}"
            return 1
        fi
        
        # Check container health status
        HEALTH_STATUS=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "none")
        
        if [ "$HEALTH_STATUS" == "healthy" ]; then
            print_msg "${GREEN}✓${NC} Container health: ${GREEN}healthy${NC}"
        elif [ "$HEALTH_STATUS" == "starting" ]; then
            print_msg "${YELLOW}⏳${NC} Container health: ${YELLOW}starting${NC}"
        elif [ "$HEALTH_STATUS" == "unhealthy" ]; then
            print_msg "${RED}❌ Container health: ${RED}unhealthy${NC}"
            return 1
        fi
        
        # Check HTTP endpoint
        if [ -n "$health_url" ]; then
            HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$health_url" 2>/dev/null || echo "000")
            
            if [ "$HTTP_CODE" == "200" ]; then
                print_msg "${GREEN}✓${NC} HTTP health check: ${GREEN}passed${NC}"
            else
                print_msg "${RED}❌ HTTP health check failed (HTTP $HTTP_CODE)${NC}"
                return 1
            fi
            
            # Get detailed status
            STATUS_RESPONSE=$(curl -s "$health_url" 2>/dev/null)
            print_msg "${GREEN}✓${NC} ${service_name} is ${GREEN}healthy${NC}"
            print_msg "  Status: $(echo "$STATUS_RESPONSE" | jq -r '.status // "ok"' 2>/dev/null || echo "ok")"
        fi
        
        print_msg ""
        return 0
    }
    
    # Track overall health
    ALL_HEALTHY=true
    
    # Check A2A Server
    if ! check_docker_service "A2A Server" "http://localhost:8000/health" "1password-a2a-server"; then
        ALL_HEALTHY=false
    fi
    
    # Check ACP Server
    if ! check_docker_service "ACP Server" "http://localhost:8001/health" "1password-acp-server"; then
        ALL_HEALTHY=false
    fi
    
    # Check MCP Server (if running)
    if docker ps --format '{{.Names}}' | grep -q "^1password-mcp-server$"; then
        if ! check_docker_service "MCP Server" "" "1password-mcp-server"; then
            ALL_HEALTHY=false
        fi
    fi
    
else
    # Non-Docker mode
    print_msg "${GREEN}✓${NC} Non-Docker mode selected"
    
    # Function to check non-Docker service health
    check_process_service() {
        local service_name=$1
        local health_url=$2
        local pid_file=$3
        
        print_msg "${BLUE}Checking ${service_name}...${NC}"
        
        # Check if process is running
        if [ -f "$pid_file" ]; then
            local pid=$(cat "$pid_file")
            if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
                print_msg "${GREEN}✓${NC} Process is running (PID: $pid)"
            else
                print_msg "${RED}❌ ${service_name} process is not running${NC}"
                return 1
            fi
        else
            print_msg "${RED}❌ ${service_name} PID file not found${NC}"
            return 1
        fi
        
        # Check HTTP endpoint
        if [ -n "$health_url" ]; then
            HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$health_url" 2>/dev/null || echo "000")
            
            if [ "$HTTP_CODE" == "200" ]; then
                print_msg "${GREEN}✓${NC} HTTP health check: ${GREEN}passed${NC}"
            else
                print_msg "${RED}❌ HTTP health check failed (HTTP $HTTP_CODE)${NC}"
                return 1
            fi
            
            # Get detailed status
            STATUS_RESPONSE=$(curl -s "$health_url" 2>/dev/null)
            print_msg "${GREEN}✓${NC} ${service_name} is ${GREEN}healthy${NC}"
            print_msg "  Status: $(echo "$STATUS_RESPONSE" | jq -r '.status // "ok"' 2>/dev/null || echo "ok")"
        fi
        
        print_msg ""
        return 0
    }
    
    # Track overall health
    ALL_HEALTHY=true
    
    # Check A2A Server
    if ! check_process_service "A2A Server" "http://localhost:8000/health" "$PID_DIR/a2a-server.pid"; then
        ALL_HEALTHY=false
    fi
    
    # Check ACP Server
    if ! check_process_service "ACP Server" "http://localhost:8001/health" "$PID_DIR/acp-server.pid"; then
        ALL_HEALTHY=false
    fi
    
    # Note: MCP Server runs interactively via stdio, so no health check needed
fi

# Summary
print_msg "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

if [ "$ALL_HEALTHY" = true ]; then
    if [ "$QUIET_MODE" = false ]; then
        print_msg "${GREEN}✓ All services are healthy${NC}"
        print_msg "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
        print_msg ""
        print_msg "${YELLOW}Service Endpoints:${NC}"
        print_msg "  A2A Server: ${BLUE}http://localhost:8000${NC}"
        print_msg "  ACP Server: ${BLUE}http://localhost:8001${NC}"
        print_msg ""
        print_msg "${YELLOW}View detailed status:${NC}"
        print_msg "  curl http://localhost:8000/status | jq"
        print_msg "  curl http://localhost:8001/status | jq"
        print_msg ""
    else
        print_msg "${GREEN}✓ All services healthy${NC}"
    fi
    exit 0
else
    if [ "$QUIET_MODE" = false ]; then
        print_msg "${RED}❌ Some services are unhealthy${NC}"
        print_msg "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
        print_msg ""
        print_msg "${YELLOW}Troubleshooting:${NC}"
        if [ "$DOCKER_MODE" = true ]; then
            print_msg "  View logs:    docker-compose logs -f"
            print_msg "  Restart:      ./scripts/stop-all.sh --docker && ./scripts/start-all.sh --docker"
        else
            print_msg "  View logs:    tail -f $PID_DIR/*.log"
            print_msg "  Restart:      ./scripts/stop-all.sh && ./scripts/start-all.sh"
        fi
        print_msg ""
    else
        print_msg "${RED}❌ Service health check failed${NC}"
    fi
    exit 1
fi

