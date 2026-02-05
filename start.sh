#!/bin/bash
# =========================================================================
# API Migration Orchestrator - Unified Startup Script (Linux/Mac)
# =========================================================================
# Launches the complete application (Backend FastAPI + Web Dashboard)
# The frontend is served by the backend, so only one server is needed.
# =========================================================================

clear
echo ""
echo "========================================================================="
echo "  API Migration Orchestrator - Starting Application"
echo "========================================================================="
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "[WARNING] .env file not found. Creating from template..."
    if [ -f ".env.template" ]; then
        cp ".env.template" ".env"
        echo "[OK] Created .env file from template"
        echo "[INFO] Edit .env to add real platform credentials"
    else
        echo "[WARNING] .env.template not found. Using default settings."
    fi
    echo ""
fi

# Load environment from .env if it exists
if [ -f ".env" ]; then
    echo "[OK] Loading environment from .env file..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check Python installation
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed or not in PATH"
    echo "[INFO] Please install Python 3.9+ from python.org"
    exit 1
fi

echo "[OK] Python is installed"
echo ""

# Install/upgrade dependencies
echo "========================================================================="
echo "  Installing Dependencies..."
echo "========================================================================="
echo ""
python3 -m pip install --upgrade pip --quiet
pip3 install -r requirements.txt --quiet
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to install dependencies"
    exit 1
fi
echo "[OK] Dependencies installed"
echo ""

# Kill any existing server on port 8000
echo "[INFO] Checking for existing server on port 8000..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true

# Create logs directory if it doesn't exist
mkdir -p logs

echo ""
echo "========================================================================="
echo "  Starting Web Application"
echo "========================================================================="
echo ""
echo "  Backend API:   http://localhost:8000/api"
echo "  Web Dashboard: http://localhost:8000"
echo "  API Docs:      http://localhost:8000/docs"
echo ""
echo "  Press Ctrl+C to stop the server"
echo "========================================================================="
echo ""

# Start the FastAPI server (which serves both backend API and frontend)
python3 -m uvicorn src.web.api:app --host 0.0.0.0 --port 8000 --reload

echo ""
echo "[INFO] Server stopped"
