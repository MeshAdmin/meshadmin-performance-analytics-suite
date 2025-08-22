#!/bin/bash

# MeshAdmin Developer Dashboard Startup Script
# This script starts the unified development dashboard on port 5555

echo "🚀 Starting MeshAdmin Developer Dashboard..."
echo "============================================="

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not found. Please install Python 3."
    exit 1
fi

# Check if we're in the correct directory
if [[ ! -f "dev_dashboard.py" ]]; then
    echo "❌ dev_dashboard.py not found. Please run this script from the correct directory."
    exit 1
fi

# Use workspace-level virtual environment if available
WORKSPACE_VENV="../venv"
if [[ -d "$WORKSPACE_VENV" ]]; then
    echo "📦 Activating workspace virtual environment..."
    source "$WORKSPACE_VENV/bin/activate"
elif [[ -d "venv" ]]; then
    echo "📦 Activating local virtual environment..."
    source venv/bin/activate
fi

# Install required dependencies if not already installed
echo "📋 Checking dependencies..."
python3 -c "import flask, psutil, requests" 2>/dev/null || {
    echo "⚠️  Some dependencies are missing. Installing..."
    pip install flask psutil requests
}

# Clear any existing processes on port 5555
echo "🧹 Clearing port 5555..."
lsof -ti:5555 | xargs kill -9 2>/dev/null || true

# Start the dashboard
echo "🌟 Starting developer dashboard on http://localhost:5555"
echo "============================================="
echo ""
echo "Features:"
echo "  • Start/Stop/Restart all MeshAdmin services"
echo "  • Real-time service status monitoring"
echo "  • System resource monitoring"
echo "  • Service logs viewing"
echo "  • Port management"
echo "  • Quick access links to running services"
echo ""
echo "Press Ctrl+C to stop the dashboard and all managed services"
echo "============================================="

python3 dev_dashboard.py

