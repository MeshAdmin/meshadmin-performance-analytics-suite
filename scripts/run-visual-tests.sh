#!/bin/bash

# Script to run visual regression and Lighthouse tests locally
# This mimics the CI environment for local development

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Visual Regression & Lighthouse Test Suite${NC}"

# Check if required tools are installed
command -v pnpm >/dev/null 2>&1 || { echo -e "${RED}❌ pnpm is required but not installed${NC}"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo -e "${RED}❌ Python 3 is required but not installed${NC}"; exit 1; }

# Create test directories
echo -e "${YELLOW}📁 Creating test directories...${NC}"
mkdir -p test-results/visual-snapshots
mkdir -p test-results/lighthouse
mkdir -p test-results/html-report

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}📦 Installing Node.js dependencies...${NC}"
    pnpm install
fi

# Install Playwright browsers if needed
echo -e "${YELLOW}🎭 Ensuring Playwright browsers are installed...${NC}"
pnpm exec playwright install --with-deps

# Function to start apps
start_apps() {
    echo -e "${YELLOW}🔄 Starting applications...${NC}"
    
    # Start network-flow-master app
    if [ -f "apps/network-flow-master/app.py" ]; then
        echo "Starting Network Flow Master on port 5000..."
        cd apps/network-flow-master
        python3 app.py &
        NETWORK_FLOW_PID=$!
        echo $NETWORK_FLOW_PID > ../../network-flow.pid
        cd ../..
    else
        echo -e "${YELLOW}⚠️ Network Flow Master app.py not found, skipping...${NC}"
    fi
    
    # Start observability-dashboard app
    if [ -f "apps/observability-dashboard/app.py" ]; then
        echo "Starting Observability Dashboard on port 8080..."
        cd apps/observability-dashboard
        python3 app.py &
        DASHBOARD_PID=$!
        echo $DASHBOARD_PID > ../../dashboard.pid
        cd ../..
    else
        echo -e "${YELLOW}⚠️ Observability Dashboard app.py not found, skipping...${NC}"
    fi
    
    echo -e "${YELLOW}⏳ Waiting for applications to start...${NC}"
    sleep 15
    
    # Verify apps are running
    if [ -f "network-flow.pid" ]; then
        if curl -f http://localhost:5000 >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Network Flow Master is running${NC}"
        else
            echo -e "${RED}❌ Network Flow Master failed to start${NC}"
        fi
    fi
    
    if [ -f "dashboard.pid" ]; then
        if curl -f http://localhost:8080 >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Observability Dashboard is running${NC}"
        else
            echo -e "${RED}❌ Observability Dashboard failed to start${NC}"
        fi
    fi
}

# Function to stop apps
stop_apps() {
    echo -e "${YELLOW}🛑 Stopping applications...${NC}"
    
    if [ -f "network-flow.pid" ]; then
        kill $(cat network-flow.pid) 2>/dev/null || true
        rm -f network-flow.pid
    fi
    
    if [ -f "dashboard.pid" ]; then
        kill $(cat dashboard.pid) 2>/dev/null || true
        rm -f dashboard.pid
    fi
    
    # Kill any remaining chrome processes
    pkill -f "chrome.*remote-debugging-port" 2>/dev/null || true
}

# Trap to ensure cleanup on exit
trap stop_apps EXIT

# Start applications
start_apps

# Run tests based on arguments
case "${1:-all}" in
    "visual")
        echo -e "${BLUE}📸 Running Visual Regression Tests...${NC}"
        pnpm exec playwright test tests/e2e/*visual*.spec.ts
        ;;
    "lighthouse")
        echo -e "${BLUE}🏮 Running Lighthouse Audits...${NC}"
        # Start Chrome in debugging mode for Lighthouse
        google-chrome --remote-debugging-port=9222 --headless --disable-gpu --no-sandbox &
        sleep 5
        pnpm exec playwright test --project=chromium tests/e2e/lighthouse-audit.spec.ts
        ;;
    "accessibility") 
        echo -e "${BLUE}♿ Running Accessibility Tests...${NC}"
        google-chrome --remote-debugging-port=9222 --headless --disable-gpu --no-sandbox &
        sleep 5
        pnpm exec playwright test --project=chromium tests/e2e/lighthouse-audit.spec.ts --grep "accessibility"
        ;;
    "performance")
        echo -e "${BLUE}⚡ Running Performance Tests...${NC}"
        google-chrome --remote-debugging-port=9222 --headless --disable-gpu --no-sandbox &
        sleep 5
        pnpm exec playwright test --project=chromium tests/e2e/lighthouse-audit.spec.ts --grep "budget"
        ;;
    "all"|*)
        echo -e "${BLUE}🎯 Running All Tests...${NC}"
        
        echo -e "${YELLOW}1/3 Visual Regression Tests${NC}"
        pnpm exec playwright test tests/e2e/*visual*.spec.ts
        
        echo -e "${YELLOW}2/3 Lighthouse Audits${NC}"
        google-chrome --remote-debugging-port=9222 --headless --disable-gpu --no-sandbox &
        sleep 5
        pnpm exec playwright test --project=chromium tests/e2e/lighthouse-audit.spec.ts
        ;;
esac

echo -e "${GREEN}✅ Tests completed!${NC}"
echo -e "${BLUE}📊 Test results available in:${NC}"
echo -e "  - Visual snapshots: ./tests/visual-snapshots/"
echo -e "  - Lighthouse reports: ./test-results/lighthouse/"
echo -e "  - HTML report: ./test-results/html-report/"

# Check if any tests failed
if [ $? -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed!${NC}"
else
    echo -e "${RED}❌ Some tests failed. Check the reports for details.${NC}"
    exit 1
fi

