#!/bin/bash
# Start Web Dashboard

echo "========================================"
echo " API Migration Orchestrator - Web UI"
echo "========================================"
echo ""
echo "Installing dependencies..."
python3 -m pip install --quiet -r requirements.txt

echo ""
echo "Starting web server..."
echo ""
echo "Dashboard will be available at:"
echo "  http://localhost:8000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

python3 -m uvicorn src.web.api:app --host 0.0.0.0 --port 8000 --reload
