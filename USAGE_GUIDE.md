# Usage Guide: start.bat vs start_web.bat

## Quick Answer

**You only need to run ONE script**, depending on what you want to do:

| Script | Purpose | When to Use |
|--------|---------|-------------|
| **`start_web.bat`** | Web Dashboard only | ✅ **Recommended** - Visual interface for most users |
| **`start.bat`** | Full application stack | Advanced users needing background services |

---

## Detailed Breakdown

### Option 1: `start_web.bat` (Recommended)

**What it does**:
- Starts the FastAPI web server
- Serves the Vue.js dashboard at http://localhost:8000
- Provides REST API endpoints

**When to use**:
- ✅ You want to use the **visual web interface**
- ✅ You want to **discover and migrate APIs** through the browser
- ✅ You want to **monitor migrations** in real-time
- ✅ **Most common use case**

**How to run**:
```bash
.\start_web.bat
```

**Access**: Open browser → http://localhost:8000

**Features**:
- API discovery with visual table
- Risk scoring with color-coded badges
- One-click migration planning
- Traffic control slider
- Real-time logs
- Beautiful charts and graphs

---

### Option 2: `start.bat` (Advanced)

**What it does**:
- Starts the web dashboard (`start_web.bat`)
- **PLUS** additional background services:
  - Celery workers for async tasks
  - Migration scheduler
  - Metrics collector
  - Other background processes

**When to use**:
- You need **automated/scheduled** migrations
- You need **background job processing**
- You're running in **production** with multiple teams
- You need **full enterprise features**

**How to run**:
```bash
.\start.bat
```

**Note**: This starts multiple processes, so it uses more resources.

---

## Command Line Interface (CLI)

You can also use the CLI **without running any server**:

```bash
# Discover APIs (no server needed)
python -m src.cli.main discover

# Generate migration plan
python -m src.cli.main plan --api payment-gateway-api

# View status
python -m src.cli.main status
```

**When to use CLI**:
- ✅ Automation and scripting
- ✅ CI/CD pipelines
- ✅ Quick operations without browser
- ✅ Headless environments

---

## Comparison Table

| Feature | start_web.bat | start.bat | CLI only |
|---------|---------------|-----------|----------|
| Web Dashboard | ✅ | ✅ | ❌ |
| Visual Interface | ✅ | ✅ | ❌ |
| Background Jobs | ❌ | ✅ | ❌ |
| Scheduled Migrations | ❌ | ✅ | ❌ |
| Resource Usage | Low | High | Very Low |
| Best For | Individual use | Team/Production | Automation |

---

## Recommended Workflow

### For Individual Developers (You!)

```bash
# 1. Start web dashboard
.\start_web.bat

# 2. Open browser
http://localhost:8000

# 3. Use visual interface to:
#    - Discover APIs
#    - Generate plans
#    - Monitor migrations

# 4. (Optional) Use CLI for quick tasks
python -m src.cli.main list --risk LOW
```

### For Production Teams

```bash
# 1. Start full stack
.\start.bat

# 2. Web dashboard available at http://server:8000
# 3. Background workers handle scheduled migrations
# 4. Multiple developers can use simultaneously
```

---

## What Each Script Actually Does

### start_web.bat
```batch
@echo off
echo ========================================
echo  API Migration Orchestrator - Web UI
echo ========================================

echo Installing dependencies...
pip install -r requirements.txt

echo Starting web server...
python -m uvicorn src.web.api:app --host 0.0.0.0 --port 8000 --reload

echo Dashboard will be available at:
echo   http://localhost:8000
```

### start.bat (simplified)
```batch
@echo off
echo Starting full migration orchestrator...

REM Start web dashboard
start cmd /k ".\start_web.bat"

REM Start Celery workers
start cmd /k "celery -A src.worker worker --loglevel=info"

REM Start scheduler
start cmd /k "python -m src.scheduler"

echo All services started!
```

---

## Troubleshooting

### "Port 8000 already in use"

**Problem**: Another process is using port 8000

**Solution**:
```bash
# Find and kill process on port 8000 (Windows)
netstat -ano | findstr :8000
taskkill /PID <process_id> /F

# Or use different port
python -m uvicorn src.web.api:app --port 8001
```

### "Module not found" errors

**Problem**: Missing Python dependencies

**Solution**:
```bash
# Install all dependencies
pip install -r requirements.txt

# Or install specific missing module
pip install <module-name>
```

### Web dashboard not loading

**Check**:
1. Is the server running? Look for "Uvicorn running on..."
2. Try http://127.0.0.1:8000 instead of localhost
3. Check browser console (F12) for errors

---

## Summary

**For your use case (individual developer learning the tool)**:

✅ **Just run `start_web.bat`**

This gives you:
- Beautiful web interface
- All migration features
- Real-time monitoring
- Easy to use and understand

**You don't need `start.bat` unless**:
- You're deploying to production
- You need background job processing
- You have automated/scheduled migrations

---

## Quick Start

```bash
# 1. Open terminal inAPIMigration folder
cd C:\Users\Admin\OneDrive\Documents\APIMigration

# 2. Install all dependencies
pip install -r requirements.txt

# 3. Start web dashboard
.\start_web.bat

# 4. Open browser
# Navigate to: http://localhost:8000

# 5. Start using the visual interface!
```

That's it! 🎉
