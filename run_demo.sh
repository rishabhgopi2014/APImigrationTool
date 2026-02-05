#!/bin/bash
# API Migration Orchestrator - Demo Launcher
# Runs the complete demo without needing APIC credentials

echo "========================================"
echo " API Migration Orchestrator - Demo"
echo "========================================"
echo ""
echo "Installing dependencies..."
python3 -m pip install --quiet --upgrade pip
python3 -m pip install --quiet -r requirements.txt

echo ""
echo "========================================"
echo "Running demo..."
echo "========================================"
echo ""

python3 demo.py

echo ""
echo "========================================"
echo "Demo complete!"
echo "========================================"
