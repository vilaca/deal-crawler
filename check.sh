#!/bin/bash
# Comprehensive checks script for Deal Crawler
# This is a thin wrapper around make check-all with friendly output

set -e  # Exit on first error

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "🔍 Running comprehensive checks via Makefile..."
echo ""

# Run all checks using make
make check-all

echo ""
echo "✅ All checks completed!"
