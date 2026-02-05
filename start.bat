@echo off
REM =========================================================================
REM API Migration Orchestrator - Unified Startup Script
REM =========================================================================
REM Launches the complete application (Backend FastAPI + Web Dashboard)
REM The frontend is served by the backend, so only one server is needed.
REM =========================================================================

cls
echo.
echo =========================================================================
echo   API Migration Orchestrator - Starting Application
echo =========================================================================
echo.

REM Check if .env file exists
if not exist ".env" (
    echo [WARNING] .env file not found. Creating from template...
    if exist ".env.template" (
        copy ".env.template" ".env" >nul
        echo [OK] Created .env file from template
        echo [INFO] Edit .env to add real platform credentials
    ) else (
        echo [WARNING] .env.template not found. Using default settings.
    )
    echo.
)

REM Load environment from .env if it exists
if exist ".env" (
    echo [OK] Loading environment from .env file...
    for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
        set "%%a=%%b"
    )
)

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo [INFO] Please install Python 3.9+ from python.org
    pause
    exit /b 1
)

echo [OK] Python is installed
echo.

REM Install/upgrade dependencies
echo =========================================================================
echo   Installing Dependencies...
echo =========================================================================
echo.
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)
echo [OK] Dependencies installed
echo.

REM Kill any existing server on port 8000
echo [INFO] Checking for existing server on port 8000...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do (
    echo [INFO] Stopping existing process %%a...
    taskkill /F /PID %%a >nul 2>&1
)

REM Create logs directory if it doesn't exist
if not exist "logs" mkdir logs

echo.
echo =========================================================================
echo   Starting Web Application
echo =========================================================================
echo.
echo   Backend API:  http://localhost:8000/api
echo   Web Dashboard: http://localhost:8000
echo   API Docs:     http://localhost:8000/docs
echo.
echo   Press Ctrl+C to stop the server
echo =========================================================================
echo.

REM Start the FastAPI server (which serves both backend API and frontend)
python -m uvicorn src.web.api:app --host 0.0.0.0 --port 8000 --reload

echo.
echo [INFO] Server stopped
pause
