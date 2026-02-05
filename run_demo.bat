@echo off
REM API Migration Orchestrator - Demo Launcher
REM Runs the complete demo without needing APIC credentials

echo ========================================
echo  API Migration Orchestrator - Demo
echo ========================================
echo.
echo Installing dependencies...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt

echo.
echo ========================================
echo Running demo...
echo ========================================
echo.

python demo.py

echo.
echo ========================================
echo Demo complete!
echo ========================================
pause
