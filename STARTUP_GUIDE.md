# 🚀 Quick Start - Launch the Application

## **EASIEST WAY: Use the Startup Script**

### Windows:
```powershell
.\start.bat
```

### Linux/Mac:
```bash
./start.sh
```

That's it! The script will:
- ✅ Check for `.env` file (create if missing)
- ✅ Install dependencies
- ✅ Kill any existing server on port 8000
- ✅ Start the application
- ✅ Open at http://localhost:8000

---

## 📁 Where is the .env File?

**Location:** `c:\Users\Admin\OneDrive\Documents\APIMigration\.env`

### Quick Edit:
```powershell
notepad .env
```

---

## 🔑 Adding Real Platform Credentials

### Current Setup (Mock Data)
Your `.env` file is currently **empty for credentials** = uses **mock data**

### To Connect to Real APIC:

**1. Open `.env` file:**
```powershell
notepad .env
```

**2. Fill in these lines:**
```bash
APIC_BASE_URL=https://your-apic-server.com:9444
APIC_USERNAME=your-admin-username
APIC_PASSWORD=your-secure-password
APIC_ORG=your-organization
```

**3. Restart:**
```powershell
.\start.bat
```

**4. Discover:**
- Open http://localhost:8000
- Click "Discover APIs"
- Now shows YOUR REAL APIs from APIC! 🎉

---

## 📝 Template File vs Actual File

### `.env.template` (Template)
- **Location:** `.env.template`
- **Purpose:** Reference/documentation
- **Safe to commit:** YES (no secrets)
- **Contains:** Examples and placeholders

### `.env` (Actual)
- **Location:** `.env` 
- **Purpose:** Real configuration
- **Safe to commit:** NO (contains secrets)
- **Contains:** Your actual credentials
- **Git status:** Ignored by .gitignore

---

## 🎯 Different Scenarios

### Scenario 1: Test UI Only (Current)
```bash
# .env file
APIC_BASE_URL=
APIC_USERNAME=
APIC_PASSWORD=

# Result: 24 mock APIs
```

### Scenario 2: Connect to Real APIC
```bash
# .env file
APIC_BASE_URL=https://apic.yourcompany.com:9444
APIC_USERNAME=admin
APIC_PASSWORD=YourPassword123
APIC_ORG=main-org

# Result: All your real APIC APIs (100s-1000s)
```

### Scenario 3: Multiple Platforms
```bash
# .env file
APIC_ENABLED=true
APIC_BASE_URL=https://apic.yourcompany.com:9444
APIC_USERNAME=admin
APIC_PASSWORD=Pass123

KAFKA_ENABLED=true
KAFKA_BOOTSTRAP_SERVERS=kafka1:9092,kafka2:9092
KAFKA_SASL_USERNAME=kafka-admin
KAFKA_SASL_PASSWORD=KafkaPass123

# Result: APIs from APIC + Kafka topics
```

---

## 🔄 Workflow

### Initial Setup (One Time):
```powershell
1. Clone/download project
2. Run: .\start.bat
3. Script creates .env automatically
4. Dashboard opens with mock data
```

### Add Real Credentials (When Ready):
```powershell
1. Edit: notepad .env
2. Add APIC_BASE_URL, USERNAME, PASSWORD
3. Save file
4. Restart: .\start.bat
5. Dashboard now shows real APIs
```

---

## 📂 File Structure

```
APIMigration/
├── .env                  ← YOUR CREDENTIALS (edit this)
├── .env.template         ← Template/reference (don't edit)
├── start.bat             ← WINDOWS STARTUP (run this)
├── start.sh              ← LINUX/MAC STARTUP
├── .gitignore            ← Protects .env from Git
├── requirements.txt      ← Python dependencies
└── src/
    └── web/
        ├── api.py        ← Backend (FastAPI)
        └── static/
            └── index.html ← Frontend (Vue.js)
```

---

## ⚡ Quick Commands Reference

```powershell
# Start application
.\start.bat

# Edit credentials
notepad .env

# View environment template
notepad .env.template

# Check what's running on port 8000
netstat -ano | findstr :8000

# Kill process on port 8000
Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process -Force
```

---

## 🔐 Security Notes

✅ `.env` is in `.gitignore` → Safe from Git commits
✅ `.env.template` has no secrets → Safe to share
❌ Never commit real credentials to Git
❌ Never share `.env` file contents

---

## 🆘 Troubleshooting

**"Port 8000 already in use"**
```powershell
# Startup script handles this automatically
# Or manually kill:
Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process -Force
```

**"Can't find .env file"**
```powershell
# Script creates it automatically
# Or manually:
copy .env.template .env
```

**"Still showing mock data after adding credentials"**
```powershell
# Did you restart?
# Kill server (Ctrl+C) and run:
.\start.bat
```

---

## ✅ Summary

**To start with mock data (testing):**
```powershell
.\start.bat
# Opens http://localhost:8000 with 24 mock APIs
```

**To connect to real APIC:**
```powershell
1. notepad .env
2. Add APIC_BASE_URL, USERNAME, PASSWORD
3. Save
4. .\start.bat
# Opens http://localhost:8000 with YOUR real APIs
```

The startup script handles everything else! 🚀
