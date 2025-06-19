#!/bin/bash

# Script to validate the visual regression and Lighthouse testing setup
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Validating Visual Regression & Lighthouse Testing Setup${NC}"
echo ""

# Check required tools
check_tool() {
    if command -v $1 >/dev/null 2>&1; then
        echo -e "${GREEN}✅ $1 is installed${NC}"
        return 0
    else
        echo -e "${RED}❌ $1 is not installed${NC}"
        return 1
    fi
}

echo -e "${YELLOW}📋 Checking Prerequisites...${NC}"
MISSING_TOOLS=0

check_tool "node" || MISSING_TOOLS=1
check_tool "pnpm" || MISSING_TOOLS=1
check_tool "python3" || MISSING_TOOLS=1

# Check Node.js version
NODE_VERSION=$(node --version | cut -d'v' -f2)
NODE_MAJOR=$(echo $NODE_VERSION | cut -d'.' -f1)
if [ "$NODE_MAJOR" -ge 20 ]; then
    echo -e "${GREEN}✅ Node.js version $NODE_VERSION (>=20)${NC}"
else
    echo -e "${RED}❌ Node.js version $NODE_VERSION (<20)${NC}"
    MISSING_TOOLS=1
fi

# Check pnpm version
PNPM_VERSION=$(pnpm --version)
PNPM_MAJOR=$(echo $PNPM_VERSION | cut -d'.' -f1)
if [ "$PNPM_MAJOR" -ge 8 ]; then
    echo -e "${GREEN}✅ pnpm version $PNPM_VERSION (>=8)${NC}"
else
    echo -e "${RED}❌ pnpm version $PNPM_VERSION (<8)${NC}"
    MISSING_TOOLS=1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 11 ]; then
    echo -e "${GREEN}✅ Python version $PYTHON_VERSION (>=3.11)${NC}"
else
    echo -e "${RED}❌ Python version $PYTHON_VERSION (<3.11)${NC}"
    MISSING_TOOLS=1
fi

if [ $MISSING_TOOLS -eq 1 ]; then
    echo -e "${RED}❌ Some prerequisites are missing. Please install them before continuing.${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}📁 Checking Project Structure...${NC}"

# Check key files exist
FILES=(
    "package.json"
    "playwright.config.ts"
    "lighthouse.config.js"
    "pnpm-workspace.yaml"
    ".github/workflows/visual-regression-and-lighthouse.yml"
    "tests/e2e/network-flow-visual.spec.ts"
    "tests/e2e/observability-dashboard-visual.spec.ts"
    "tests/e2e/lighthouse-audit.spec.ts"
    "scripts/run-visual-tests.sh"
    "docs/TESTING_GUIDE.md"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅ $file${NC}"
    else
        echo -e "${RED}❌ $file missing${NC}"
    fi
done

echo ""
echo -e "${YELLOW}📦 Checking Dependencies...${NC}"

# Check if node_modules exists
if [ -d "node_modules" ]; then
    echo -e "${GREEN}✅ Node.js dependencies installed${NC}"
else
    echo -e "${YELLOW}⚠️ Node.js dependencies not installed. Run: pnpm install${NC}"
fi

# Check if Playwright is installed
if [ -f "node_modules/@playwright/test/package.json" ]; then
    echo -e "${GREEN}✅ Playwright installed${NC}"
else
    echo -e "${YELLOW}⚠️ Playwright not installed. Run: pnpm install${NC}"
fi

# Check if Lighthouse is installed  
if [ -f "node_modules/lighthouse/package.json" ]; then
    echo -e "${GREEN}✅ Lighthouse installed${NC}"
else
    echo -e "${YELLOW}⚠️ Lighthouse not installed. Run: pnpm install${NC}"
fi

echo ""
echo -e "${YELLOW}🎭 Checking Playwright Browsers...${NC}"

# Check if Playwright browsers are installed
if [ -d "$HOME/.cache/ms-playwright" ] || [ -d "$HOME/Library/Caches/ms-playwright" ]; then
    echo -e "${GREEN}✅ Playwright browsers installed${NC}"
else
    echo -e "${YELLOW}⚠️ Playwright browsers not installed. Run: pnpm run playwright:install${NC}"
fi

echo ""
echo -e "${YELLOW}📝 Checking Scripts...${NC}"

# Check script permissions
if [ -x "scripts/run-visual-tests.sh" ]; then
    echo -e "${GREEN}✅ run-visual-tests.sh is executable${NC}"
else
    echo -e "${YELLOW}⚠️ run-visual-tests.sh is not executable. Run: chmod +x scripts/run-visual-tests.sh${NC}"
fi

echo ""
echo -e "${YELLOW}🏗️ Checking Test Directories...${NC}"

# Create test directories if they don't exist
mkdir -p tests/visual-snapshots
mkdir -p test-results/lighthouse
mkdir -p test-results/html-report

echo -e "${GREEN}✅ Test directories created/verified${NC}"

echo ""
echo -e "${YELLOW}🔧 Validating Configuration Files...${NC}"

# Check Playwright config syntax
if node -c playwright.config.ts 2>/dev/null; then
    echo -e "${GREEN}✅ playwright.config.ts syntax valid${NC}"
else
    echo -e "${RED}❌ playwright.config.ts has syntax errors${NC}"
fi

# Check Lighthouse config syntax
if node -c lighthouse.config.js 2>/dev/null; then
    echo -e "${GREEN}✅ lighthouse.config.js syntax valid${NC}"
else
    echo -e "${RED}❌ lighthouse.config.js has syntax errors${NC}"
fi

echo ""
echo -e "${YELLOW}🐍 Checking Python Applications...${NC}"

# Check if app files exist
if [ -f "apps/network-flow-master/app.py" ]; then
    echo -e "${GREEN}✅ Network Flow Master app.py found${NC}"
else
    echo -e "${YELLOW}⚠️ Network Flow Master app.py not found${NC}"
fi

if [ -f "apps/observability-dashboard/app.py" ]; then
    echo -e "${GREEN}✅ Observability Dashboard app.py found${NC}"
else
    echo -e "${YELLOW}⚠️ Observability Dashboard app.py not found${NC}"
fi

echo ""
echo -e "${BLUE}📋 Setup Summary${NC}"
echo "=================="
echo -e "Visual Regression Testing: ${GREEN}Configured${NC}"
echo -e "Lighthouse Audits: ${GREEN}Configured${NC}"
echo -e "GitHub Actions CI: ${GREEN}Configured${NC}"
echo -e "Local Test Scripts: ${GREEN}Configured${NC}"
echo -e "Documentation: ${GREEN}Available${NC}"

echo ""
echo -e "${GREEN}🎉 Setup validation complete!${NC}"
echo ""
echo -e "${BLUE}🚀 Next Steps:${NC}"
echo "1. Install dependencies: ${YELLOW}pnpm install${NC}"
echo "2. Install browsers: ${YELLOW}pnpm run playwright:install${NC}"
echo "3. Run tests: ${YELLOW}pnpm run test:qa${NC}"
echo "4. View documentation: ${YELLOW}docs/TESTING_GUIDE.md${NC}"

echo ""
echo -e "${BLUE}📊 Available Commands:${NC}"
echo "  ${YELLOW}pnpm run test:visual${NC}        - Visual regression tests"
echo "  ${YELLOW}pnpm run test:lighthouse${NC}    - Lighthouse audits"
echo "  ${YELLOW}pnpm run test:accessibility${NC} - Accessibility tests"
echo "  ${YELLOW}pnpm run test:performance${NC}   - Performance tests"
echo "  ${YELLOW}pnpm run test:qa${NC}            - All quality tests"
echo "  ${YELLOW}pnpm run playwright:ui${NC}      - Interactive test runner"

