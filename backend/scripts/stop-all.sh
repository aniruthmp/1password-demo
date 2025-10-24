#!/bin/bash
# Universal 1Password Credential Broker - Stop Script
# Gracefully stops all services (Docker or non-Docker)

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

# Parse command line arguments first
QUIET=false
FORCE=false
CLEAN_LOGS=false
REMOVE_VOLUMES=""
REMOVE_IMAGES=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --docker)
            DOCKER_MODE=true
            shift
            ;;
        --quiet)
            QUIET=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --clean-logs)
            CLEAN_LOGS=true
            shift
            ;;
        --clean)
            REMOVE_VOLUMES="--volumes"
            shift
            ;;
        --purge)
            REMOVE_VOLUMES="--volumes"
            REMOVE_IMAGES="--rmi local"
            shift
            ;;
        --help)
            echo "Usage: $0 [--docker] [--quiet] [--force] [--clean-logs] [--clean] [--purge]"
            echo ""
            echo "Options:"
            echo "  --docker       Stop Docker containers (default: stop Python processes)"
            echo "  --quiet        Suppress most output (non-Docker mode only)"
            echo "  --force        Force kill processes (SIGKILL instead of SIGTERM) (non-Docker mode only)"
            echo "  --clean-logs   Remove log files after stopping services (non-Docker mode only)"
            echo "  --clean        Remove volumes (logs, data) (Docker mode only)"
            echo "  --purge        Remove volumes and images (Docker mode only)"
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
    if [ "$QUIET" = false ]; then
        echo -e "$1"
    fi
}

print_msg "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
if [ "$DOCKER_MODE" = true ]; then
    print_msg "${BLUE}   Universal 1Password Credential Broker - Shutdown (Docker)${NC}"
else
    print_msg "${BLUE}   Universal 1Password Credential Broker - Shutdown (Non-Docker)${NC}"
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
    
    # Stop services
    print_msg "${YELLOW}Stopping services...${NC}"
    docker-compose down $REMOVE_VOLUMES $REMOVE_IMAGES
    
    print_msg ""
    print_msg "${GREEN}✓${NC} All services stopped successfully"
    
    if [ -n "$REMOVE_VOLUMES" ]; then
        print_msg "${GREEN}✓${NC} Volumes removed"
    fi
    
    if [ -n "$REMOVE_IMAGES" ]; then
        print_msg "${GREEN}✓${NC} Images removed"
    fi
    
    print_msg ""
    print_msg "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    print_msg "${GREEN}Shutdown complete${NC}"
    print_msg "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    print_msg ""
    
    # Show remaining containers (if any)
    RUNNING_CONTAINERS=$(docker ps --filter "name=1password" -q)
    if [ -n "$RUNNING_CONTAINERS" ]; then
        print_msg "${YELLOW}⚠ Warning: Some 1Password containers are still running:${NC}"
        docker ps --filter "name=1password" --format "  - {{.Names}} ({{.Status}})"
        print_msg ""
    fi
    
else
    # Non-Docker mode
    print_msg "${GREEN}✓${NC} Non-Docker mode selected"
    
    # Function to stop a service by PID file
    stop_service() {
        local service_name="$1"
        local pid_file="$2"
        local signal="${3:-TERM}"
        
        if [ -f "$pid_file" ]; then
            local pid=$(cat "$pid_file")
            if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
                print_msg "${YELLOW}Stopping $service_name (PID: $pid)...${NC}"
                
                # Send signal to process
                if kill -$signal "$pid" 2>/dev/null; then
                    # Wait for graceful shutdown
                    local count=0
                    while kill -0 "$pid" 2>/dev/null && [ $count -lt 10 ]; do
                        sleep 1
                        count=$((count + 1))
                    done
                    
                    # Check if still running
                    if kill -0 "$pid" 2>/dev/null; then
                        if [ "$FORCE" = true ]; then
                            print_msg "${YELLOW}Force killing $service_name...${NC}"
                            kill -KILL "$pid" 2>/dev/null || true
                        else
                            print_msg "${RED}Warning: $service_name did not stop gracefully${NC}"
                            return 1
                        fi
                    fi
                    
                    print_msg "${GREEN}✓${NC} $service_name stopped"
                else
                    print_msg "${YELLOW}Warning: Could not send signal to $service_name (PID: $pid)${NC}"
                fi
            else
                print_msg "${YELLOW}Warning: $service_name PID file exists but process is not running${NC}"
            fi
            
            # Remove PID file
            rm -f "$pid_file"
        else
            print_msg "${YELLOW}Warning: $service_name PID file not found${NC}"
        fi
    }
    
    # Function to find and kill processes by name pattern
    kill_by_pattern() {
        local pattern="$1"
        local service_name="$2"
        
        # Find processes matching the pattern
        local pids=$(pgrep -f "$pattern" 2>/dev/null || true)
        
        if [ -n "$pids" ]; then
            print_msg "${YELLOW}Found running $service_name processes: $pids${NC}"
            
            for pid in $pids; do
                if [ "$FORCE" = true ]; then
                    kill -KILL "$pid" 2>/dev/null || true
                else
                    kill -TERM "$pid" 2>/dev/null || true
                fi
            done
            
            # Wait for processes to stop
            sleep 2
            
            # Check if any are still running
            local remaining=$(pgrep -f "$pattern" 2>/dev/null || true)
            if [ -n "$remaining" ]; then
                if [ "$FORCE" = true ]; then
                    print_msg "${YELLOW}Force killing remaining $service_name processes...${NC}"
                    echo "$remaining" | xargs kill -KILL 2>/dev/null || true
                else
                    print_msg "${RED}Warning: Some $service_name processes may still be running${NC}"
                fi
            fi
            
            print_msg "${GREEN}✓${NC} $service_name processes stopped"
        fi
    }
    
    print_msg "${YELLOW}Stopping services...${NC}"
    
    # Stop services using PID files
    stop_service "A2A Server" "$PID_DIR/a2a-server.pid"
    stop_service "ACP Server" "$PID_DIR/acp-server.pid"
    # Note: MCP Server doesn't run as background daemon, so no PID file to stop
    
    # Also try to kill any remaining processes by pattern (as backup)
    kill_by_pattern "src/a2a/run_a2a.py" "A2A"
    kill_by_pattern "src/acp/run_acp.py" "ACP"
    # Note: MCP Server runs interactively via stdio, so no pattern killing needed
    
    print_msg ""
    print_msg "${GREEN}✓${NC} All services stopped successfully"
    
    # Clean up log files if requested
    if [ "$CLEAN_LOGS" = true ]; then
        print_msg ""
        print_msg "${YELLOW}Cleaning log files...${NC}"
        rm -f "$PROJECT_ROOT/logs/a2a-server.log"
        rm -f "$PROJECT_ROOT/logs/acp-server.log"
        # Note: MCP Server doesn't generate log files as it runs interactively
        print_msg "${GREEN}✓${NC} Log files removed"
    fi
    
    print_msg ""
    print_msg "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    print_msg "${GREEN}Shutdown complete${NC}"
    print_msg "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    print_msg ""
    
    # Show any remaining processes (if not quiet)
    if [ "$QUIET" = false ]; then
        REMAINING_A2A=$(pgrep -f "src/a2a/run_a2a.py" 2>/dev/null || true)
        REMAINING_ACP=$(pgrep -f "src/acp/run_acp.py" 2>/dev/null || true)
        # Note: MCP Server runs interactively via stdio, so no process checking needed
        
        if [ -n "$REMAINING_A2A" ] || [ -n "$REMAINING_ACP" ]; then
            echo -e "${YELLOW}⚠ Warning: Some processes may still be running:${NC}"
            [ -n "$REMAINING_A2A" ] && echo -e "  - A2A Server (PIDs: $REMAINING_A2A)"
            [ -n "$REMAINING_ACP" ] && echo -e "  - ACP Server (PIDs: $REMAINING_ACP)"
            echo ""
            echo -e "${YELLOW}Use --force to force kill remaining processes${NC}"
        fi
    fi
fi
