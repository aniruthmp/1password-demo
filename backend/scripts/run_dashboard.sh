#!/bin/bash
# Script to run the Streamlit dashboard for the Universal 1Password Credential Broker

set -e

# Color output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}============================================${NC}"
echo -e "${BLUE}  1Password Credential Broker Dashboard    ${NC}"
echo -e "${BLUE}============================================${NC}"
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

# Check if .env exists
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo -e "${YELLOW}Warning: .env file not found in $PROJECT_ROOT${NC}"
    echo -e "${YELLOW}Please copy .env.example to .env and configure it.${NC}"
    exit 1
fi

# Load environment variables
export $(grep -v '^#' "$PROJECT_ROOT/.env" | xargs)

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo -e "${YELLOW}Poetry not found. Please install Poetry first:${NC}"
    echo -e "${YELLOW}  curl -sSL https://install.python-poetry.org | python3 -${NC}"
    exit 1
fi

# Check if dependencies are installed
echo -e "${GREEN}✓ Checking dependencies...${NC}"
cd "$PROJECT_ROOT"
poetry install --extras ui --no-interaction --quiet

echo -e "${GREEN}✓ Environment loaded${NC}"
echo -e "${GREEN}✓ Starting Streamlit dashboard...${NC}"
echo ""
echo -e "${BLUE}Dashboard will be available at: http://localhost:8501${NC}"
echo ""

# Run Streamlit dashboard using Poetry's virtual environment
poetry run streamlit run src/ui/dashboard.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false

echo ""
echo -e "${GREEN}Dashboard stopped.${NC}"

