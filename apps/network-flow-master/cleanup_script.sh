#!/bin/bash
echo "Cleaning up unnecessary files and optimizing for deployment..."

# Remove test output files and other temporary files
find . -name "*.pyc" -type f -delete
find . -name "__pycache__" -type d -exec rm -rf {} +
find . -name ".pytest_cache" -type d -exec rm -rf {} +
find . -name "*.log" -type f -delete
find . -name ".DS_Store" -type f -delete

# Make sure directories exist
mkdir -p uploads/mibs
mkdir -p logs

# Create empty __init__.py files if needed
touch uploads/__init__.py
touch logs/__init__.py

echo "Cleanup complete!"
