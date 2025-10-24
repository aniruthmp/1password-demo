#!/bin/bash
# Universal 1Password Credential Broker - Automated Demo Script
# Generates random traffic to all 3 servers for dashboard metrics

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Server configuration
A2A_URL="http://localhost:8000"
ACP_URL="http://localhost:8001"
BEARER_TOKEN="dev-token-change-in-production"

# Test resources (customize these based on your 1Password vault)
DATABASES=("test-database" "production-db" "staging-postgres" "dev-mysql")
APIS=("stripe-api" "github-api" "slack-api" "aws-api")
SSH_KEYS=("production-server" "staging-server" "dev-server")

# Test counter
TEST_COUNT=0
SUCCESS_COUNT=0
FAILURE_COUNT=0

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Universal 1Password Credential Broker - Demo Script        ║${NC}"
echo -e "${BLUE}║           Automated Testing for Dashboard Metrics              ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Parse arguments
ITERATIONS=10
DELAY=2
CONTINUOUS=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -n|--iterations)
            ITERATIONS="$2"
            shift 2
            ;;
        -d|--delay)
            DELAY="$2"
            shift 2
            ;;
        -c|--continuous)
            CONTINUOUS=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo ""
            echo "Options:"
            echo "  -n, --iterations N    Number of test iterations (default: 10)"
            echo "  -d, --delay N         Delay between tests in seconds (default: 2)"
            echo "  -c, --continuous      Run continuously (Ctrl+C to stop)"
            echo "  -h, --help            Show this help message"
            echo ""
            echo "Example:"
            echo "  $0 -n 20 -d 1         # Run 20 tests with 1 second delay"
            echo "  $0 -c                 # Run continuously"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Check MCP availability
check_mcp() {
    echo -e "${CYAN}Checking MCP server availability...${NC}"
    
    if ! command -v poetry &> /dev/null; then
        echo -e "  ${YELLOW}⚠${NC} Poetry not found, MCP tests will be skipped"
        return 1
    fi
    
    # Check if we're in the right directory for Poetry
    if [ ! -f "pyproject.toml" ]; then
        echo -e "  ${YELLOW}⚠${NC} Not in Poetry project directory, MCP tests will be skipped"
        return 1
    fi
    
    # Check if MCP dependencies are installed
    if ! poetry run python -c "import mcp" &> /dev/null; then
        echo -e "  ${YELLOW}⚠${NC} MCP dependencies not installed, MCP tests will be skipped"
        return 1
    fi
    
    echo -e "  ${GREEN}✓${NC} MCP Server (Poetry-based stdio)"
    return 0
}

# Check if servers are running
check_servers() {
    echo -e "${CYAN}Checking server availability...${NC}"
    
    # Check A2A
    if curl -s -f "$A2A_URL/health" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} A2A Server (port 8000)"
    else
        echo -e "  ${RED}✗${NC} A2A Server not responding"
        echo -e "${YELLOW}Please start servers with: ./scripts/start-all.sh${NC}"
        exit 1
    fi
    
    # Check ACP
    if curl -s -f "$ACP_URL/health" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} ACP Server (port 8001)"
    else
        echo -e "  ${RED}✗${NC} ACP Server not responding"
        echo -e "${YELLOW}Please start servers with: ./scripts/start-all.sh${NC}"
        exit 1
    fi
    
    # Check MCP availability
    check_mcp
    
    echo ""
}

# Get random element from array
get_random() {
    local arr=("$@")
    local size=${#arr[@]}
    local index=$((RANDOM % size))
    echo "${arr[$index]}"
}

# Test A2A Server
test_a2a() {
    local test_type=$((RANDOM % 3))
    
    case $test_type in
        0)
            # Test agent card discovery
            echo -e "${MAGENTA}[A2A Test #$TEST_COUNT]${NC} ${CYAN}Agent Card Discovery${NC}"
            echo -e "  ${BLUE}→${NC} GET $A2A_URL/agent-card"
            
            response=$(curl -s -w "\n%{http_code}" "$A2A_URL/agent-card")
            http_code=$(echo "$response" | tail -n1)
            body=$(echo "$response" | sed '$d')
            
            if [ "$http_code" = "200" ]; then
                agent_name=$(echo "$body" | python3 -c "import sys, json; print(json.load(sys.stdin)['name'])" 2>/dev/null || echo "N/A")
                echo -e "  ${GREEN}✓${NC} Success (200) - Agent: $agent_name"
                ((SUCCESS_COUNT++))
            else
                echo -e "  ${RED}✗${NC} Failed ($http_code)"
                ((FAILURE_COUNT++))
            fi
            ;;
            
        1)
            # Test database credentials request
            local db=$(get_random "${DATABASES[@]}")
            echo -e "${MAGENTA}[A2A Test #$TEST_COUNT]${NC} ${CYAN}Database Credentials${NC}"
            echo -e "  ${BLUE}→${NC} POST $A2A_URL/task"
            echo -e "  ${BLUE}→${NC} Database: ${YELLOW}$db${NC}"
            echo -e "  ${BLUE}→${NC} TTL: 5 minutes"
            
            task_data=$(cat <<EOF
{
  "task_id": "demo-task-$(date +%s)-$RANDOM",
  "capability_name": "request_database_credentials",
  "parameters": {
    "database_name": "$db",
    "duration_minutes": 5
  },
  "requesting_agent_id": "demo-automation-script"
}
EOF
)
            
            response=$(curl -s -w "\n%{http_code}" -X POST "$A2A_URL/task" \
                -H "Content-Type: application/json" \
                -H "Authorization: Bearer $BEARER_TOKEN" \
                -d "$task_data")
            
            http_code=$(echo "$response" | tail -n1)
            body=$(echo "$response" | sed '$d')
            
            if [ "$http_code" = "200" ]; then
                status=$(echo "$body" | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo "unknown")
                echo -e "  ${GREEN}✓${NC} Success (200) - Status: $status"
                if [ "$status" = "completed" ]; then
                    ((SUCCESS_COUNT++))
                else
                    ((FAILURE_COUNT++))
                fi
            else
                echo -e "  ${RED}✗${NC} Failed ($http_code)"
                ((FAILURE_COUNT++))
            fi
            ;;
            
        2)
            # Test API credentials request
            local api=$(get_random "${APIS[@]}")
            echo -e "${MAGENTA}[A2A Test #$TEST_COUNT]${NC} ${CYAN}API Credentials${NC}"
            echo -e "  ${BLUE}→${NC} POST $A2A_URL/task"
            echo -e "  ${BLUE}→${NC} API: ${YELLOW}$api${NC}"
            echo -e "  ${BLUE}→${NC} Scopes: read, write"
            
            task_data=$(cat <<EOF
{
  "task_id": "demo-task-$(date +%s)-$RANDOM",
  "capability_name": "request_api_credentials",
  "parameters": {
    "api_name": "$api",
    "scopes": ["read", "write"],
    "duration_minutes": 5
  },
  "requesting_agent_id": "demo-automation-script"
}
EOF
)
            
            response=$(curl -s -w "\n%{http_code}" -X POST "$A2A_URL/task" \
                -H "Content-Type: application/json" \
                -H "Authorization: Bearer $BEARER_TOKEN" \
                -d "$task_data")
            
            http_code=$(echo "$response" | tail -n1)
            body=$(echo "$response" | sed '$d')
            
            if [ "$http_code" = "200" ]; then
                status=$(echo "$body" | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo "unknown")
                echo -e "  ${GREEN}✓${NC} Success (200) - Status: $status"
                if [ "$status" = "completed" ]; then
                    ((SUCCESS_COUNT++))
                else
                    ((FAILURE_COUNT++))
                fi
            else
                echo -e "  ${RED}✗${NC} Failed ($http_code)"
                ((FAILURE_COUNT++))
            fi
            ;;
    esac
    echo ""
}

# Test ACP Server
test_acp() {
    local test_type=$((RANDOM % 4))
    
    case $test_type in
        0)
            # Test agent discovery
            echo -e "${MAGENTA}[ACP Test #$TEST_COUNT]${NC} ${CYAN}Agent Discovery${NC}"
            echo -e "  ${BLUE}→${NC} GET $ACP_URL/agents"
            
            response=$(curl -s -w "\n%{http_code}" "$ACP_URL/agents")
            http_code=$(echo "$response" | tail -n1)
            body=$(echo "$response" | sed '$d')
            
            if [ "$http_code" = "200" ]; then
                count=$(echo "$body" | python3 -c "import sys, json; print(json.load(sys.stdin)['count'])" 2>/dev/null || echo "0")
                echo -e "  ${GREEN}✓${NC} Success (200) - Found $count agent(s)"
                ((SUCCESS_COUNT++))
            else
                echo -e "  ${RED}✗${NC} Failed ($http_code)"
                ((FAILURE_COUNT++))
            fi
            ;;
            
        1)
            # Test database credentials with natural language
            local db=$(get_random "${DATABASES[@]}")
            echo -e "${MAGENTA}[ACP Test #$TEST_COUNT]${NC} ${CYAN}Natural Language - Database${NC}"
            echo -e "  ${BLUE}→${NC} POST $ACP_URL/run"
            echo -e "  ${BLUE}→${NC} Request: ${YELLOW}\"Get database credentials for $db\"${NC}"
            
            acp_data=$(cat <<EOF
{
  "agent_name": "credential-broker",
  "input": [
    {
      "role": "user",
      "parts": [
        {
          "content": "Get database credentials for $db",
          "content_type": "text/plain"
        }
      ]
    }
  ]
}
EOF
)
            
            response=$(curl -s -w "\n%{http_code}" -X POST "$ACP_URL/run" \
                -H "Content-Type: application/json" \
                -d "$acp_data")
            
            http_code=$(echo "$response" | tail -n1)
            body=$(echo "$response" | sed '$d')
            
            if [ "$http_code" = "200" ]; then
                status=$(echo "$body" | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo "unknown")
                run_id=$(echo "$body" | python3 -c "import sys, json; print(json.load(sys.stdin)['run_id'][:8])" 2>/dev/null || echo "N/A")
                echo -e "  ${GREEN}✓${NC} Success (200) - Status: $status, Run: $run_id..."
                ((SUCCESS_COUNT++))
            else
                echo -e "  ${RED}✗${NC} Failed ($http_code)"
                ((FAILURE_COUNT++))
            fi
            ;;
            
        2)
            # Test API credentials with natural language
            local api=$(get_random "${APIS[@]}")
            echo -e "${MAGENTA}[ACP Test #$TEST_COUNT]${NC} ${CYAN}Natural Language - API${NC}"
            echo -e "  ${BLUE}→${NC} POST $ACP_URL/run"
            echo -e "  ${BLUE}→${NC} Request: ${YELLOW}\"I need API credentials for $api for 10 minutes\"${NC}"
            
            acp_data=$(cat <<EOF
{
  "agent_name": "credential-broker",
  "input": [
    {
      "role": "user",
      "parts": [
        {
          "content": "I need API credentials for $api for 10 minutes",
          "content_type": "text/plain"
        }
      ]
    }
  ]
}
EOF
)
            
            response=$(curl -s -w "\n%{http_code}" -X POST "$ACP_URL/run" \
                -H "Content-Type: application/json" \
                -d "$acp_data")
            
            http_code=$(echo "$response" | tail -n1)
            body=$(echo "$response" | sed '$d')
            
            if [ "$http_code" = "200" ]; then
                status=$(echo "$body" | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo "unknown")
                echo -e "  ${GREEN}✓${NC} Success (200) - Status: $status"
                ((SUCCESS_COUNT++))
            else
                echo -e "  ${RED}✗${NC} Failed ($http_code)"
                ((FAILURE_COUNT++))
            fi
            ;;
            
        3)
            # Test SSH credentials with natural language
            local ssh=$(get_random "${SSH_KEYS[@]}")
            echo -e "${MAGENTA}[ACP Test #$TEST_COUNT]${NC} ${CYAN}Natural Language - SSH${NC}"
            echo -e "  ${BLUE}→${NC} POST $ACP_URL/run"
            echo -e "  ${BLUE}→${NC} Request: ${YELLOW}\"Get SSH keys for $ssh\"${NC}"
            
            acp_data=$(cat <<EOF
{
  "agent_name": "credential-broker",
  "input": [
    {
      "role": "user",
      "parts": [
        {
          "content": "Get SSH keys for $ssh",
          "content_type": "text/plain"
        }
      ]
    }
  ]
}
EOF
)
            
            response=$(curl -s -w "\n%{http_code}" -X POST "$ACP_URL/run" \
                -H "Content-Type: application/json" \
                -d "$acp_data")
            
            http_code=$(echo "$response" | tail -n1)
            body=$(echo "$response" | sed '$d')
            
            if [ "$http_code" = "200" ]; then
                status=$(echo "$body" | python3 -c "import sys, json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo "unknown")
                echo -e "  ${GREEN}✓${NC} Success (200) - Status: $status"
                ((SUCCESS_COUNT++))
            else
                echo -e "  ${RED}✗${NC} Failed ($http_code)"
                ((FAILURE_COUNT++))
            fi
            ;;
    esac
    echo ""
}

# Test MCP Server (via Poetry-based stdio communication)
test_mcp() {
    echo -e "${MAGENTA}[MCP Test #$TEST_COUNT]${NC} ${CYAN}MCP Protocol Test${NC}"
    echo -e "  ${BLUE}→${NC} Testing MCP server via Poetry stdio"
    
    local resource_type=$(get_random "database" "api" "ssh")
    local resource_name=""
    
    case $resource_type in
        database)
            resource_name=$(get_random "${DATABASES[@]}")
            ;;
        api)
            resource_name=$(get_random "${APIS[@]}")
            ;;
        ssh)
            resource_name=$(get_random "${SSH_KEYS[@]}")
            ;;
    esac
    
    echo -e "  ${BLUE}→${NC} Resource: ${YELLOW}$resource_type/$resource_name${NC}"
    
    # Check if Poetry is available
    if ! command -v poetry &> /dev/null; then
        echo -e "  ${YELLOW}⚠${NC} Poetry not found, skipping MCP test"
        ((FAILURE_COUNT++))
        echo ""
        return
    fi
    
    # Create temporary Python script for MCP test using Poetry
    local temp_script=$(mktemp)
    cat > "$temp_script" <<'PYTHON_EOF'
import asyncio
import sys
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from the backend directory
backend_dir = Path(__file__).parent.parent
env_path = backend_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Ensure OP_CONNECT_HOST is set (it might be commented out in .env)
if not os.getenv("OP_CONNECT_HOST"):
    os.environ["OP_CONNECT_HOST"] = "http://localhost:8080"

from mcp.client.session import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

async def quick_test(resource_type, resource_name):
    # Use Poetry to run the MCP server with proper environment
    server_params = StdioServerParameters(
        command="poetry",
        args=["run", "python", "src/mcp/run_mcp.py", "--log-level", "ERROR"],
        env=os.environ.copy(),
    )
    
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # Test basic MCP functionality
                result = await session.call_tool(
                    "get_credentials",
                    arguments={
                        "resource_type": resource_type,
                        "resource_name": resource_name,
                        "requesting_agent_id": "demo-automation-script",
                        "ttl_minutes": 5,
                    },
                )
                return True
    except Exception as e:
        # MCP test might fail if resource doesn't exist, which is expected
        return False

if __name__ == "__main__":
    success = asyncio.run(quick_test(sys.argv[1], sys.argv[2]))
    sys.exit(0 if success else 1)
PYTHON_EOF
    
    # Run with timeout to prevent hanging
    local timeout_cmd="timeout"
    if ! command -v timeout > /dev/null 2>&1; then
        if command -v gtimeout > /dev/null 2>&1; then
            timeout_cmd="gtimeout"
        else
            # No timeout available, skip MCP test
            echo -e "  ${YELLOW}⚠${NC} Timeout command not available, skipping MCP test"
            ((FAILURE_COUNT++))
            echo ""
            return
        fi
    fi
    
    # Change to backend directory where Poetry project is located
    cd "$PROJECT_ROOT" && $timeout_cmd 10 poetry run python "$temp_script" "$resource_type" "$resource_name" > /dev/null 2>&1
    exit_code=$?
    rm -f "$temp_script"
    
    if [ $exit_code -eq 0 ]; then
        echo -e "  ${GREEN}✓${NC} Success - MCP server responded correctly"
        ((SUCCESS_COUNT++))
    elif [ $exit_code -eq 124 ]; then
        echo -e "  ${YELLOW}⚠${NC} MCP test timed out"
        ((FAILURE_COUNT++))
    else
        echo -e "  ${YELLOW}⚠${NC} MCP test completed (resource may not exist)"
        ((FAILURE_COUNT++))
    fi
    echo ""
}

# Run single test iteration
run_test() {
    ((TEST_COUNT++))
    
    # Randomly select which server to test (33% A2A, 33% ACP, 33% MCP)
    local rand=$((RANDOM % 3))
    
    if [ $rand -eq 0 ]; then
        test_a2a
    elif [ $rand -eq 1 ]; then
        test_acp
    else
        # MCP tests - check if Poetry is available
        if command -v poetry &> /dev/null; then
            test_mcp
        else
            # Fallback to A2A if Poetry not available
            test_a2a
        fi
    fi
}

# Print statistics
print_stats() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}   Test Statistics${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    echo -e "  Total Tests:      ${CYAN}$TEST_COUNT${NC}"
    echo -e "  Successful:       ${GREEN}$SUCCESS_COUNT${NC}"
    echo -e "  Failed/Warning:   ${YELLOW}$FAILURE_COUNT${NC}"
    
    if [ $TEST_COUNT -gt 0 ]; then
        success_rate=$((SUCCESS_COUNT * 100 / TEST_COUNT))
        echo -e "  Success Rate:     ${CYAN}${success_rate}%${NC}"
    fi
    
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    echo ""
}

# Main execution
main() {
    check_servers
    
    echo -e "${GREEN}Configuration:${NC}"
    if [ "$CONTINUOUS" = true ]; then
        echo -e "  Mode:       ${CYAN}Continuous${NC} (Ctrl+C to stop)"
    else
        echo -e "  Iterations: ${CYAN}$ITERATIONS${NC}"
    fi
    echo -e "  Delay:      ${CYAN}${DELAY}s${NC}"
    echo ""
    echo -e "${YELLOW}Starting automated tests...${NC}"
    echo -e "${YELLOW}Watch metrics on dashboard: ${CYAN}http://localhost:8501${NC}"
    echo ""
    
    # Trap Ctrl+C to show stats before exit
    trap 'echo ""; echo "Interrupted by user"; print_stats; exit 0' INT
    
    if [ "$CONTINUOUS" = true ]; then
        # Run continuously
        while true; do
            run_test
            sleep "$DELAY"
        done
    else
        # Run for specified iterations
        for ((i=1; i<=ITERATIONS; i++)); do
            run_test
            
            # Don't sleep after last iteration
            if [ $i -lt $ITERATIONS ]; then
                sleep "$DELAY"
            fi
        done
        
        print_stats
        
        echo -e "${GREEN}✓ Demo complete!${NC}"
        echo -e "${CYAN}View the results in the Streamlit Dashboard:${NC}"
        echo -e "  ${BLUE}http://localhost:8501${NC}"
        echo ""
    fi
}

# Run main function
main

