# 🌐 Web Dashboard Guide

## Quick Start - Visual Interface!

Instead of using CLI commands, you can now use a **beautiful web interface**!

### Start the Dashboard

**Windows:**
```bash
start_web.bat
```

**Linux/Mac:**
```bash
./start_web.sh
```

**Manual:**
```bash
pip install -r requirements.txt
python -m uvicorn src.web.api:app --host 0.0.0.0 --port 8000 --reload
```

Then open your browser to:
```
http://localhost:8000
```

---

## 🎨 Dashboard Features

### 1. **API Discovery** (Visual)
- Click **"Discover APIs"** button
- See all your APIs in a sortable table
- View risk scores with color-coding:
  - 🔴 **CRITICAL** (red)
  - 🟠 **HIGH** (orange)
  - 🟡 **MEDIUM** (yellow)
  - 🟢 **LOW** (green)
- Interactive risk distribution chart

### 2. **Migration Planning** (One Click)
- Click **"Migrate"** button on any API
- See API details in popup modal
- Click **"Generate Gloo Gateway Config"**
- View generated YAML configs instantly
- Copy/paste to apply to Kubernetes

### 3. **Traffic Management** (Visual Slider)
- See all active migrations
- Use **traffic slider** to shift traffic:
  - Drag slider to 10% (canary start)
  - Drag to 50% (half traffic)
  - Drag to 100% (full cutover)
- One-click **"Rollback"** button for emergencies

### 4. **Real-Time Monitoring**
- Live activity logs (terminal-style)
- Auto-refresh every 5 seconds
- See migration status for all APIs
- Track completed vs in-progress

---

## 📸 Dashboard Screenshots

### Main Dashboard
![Dashboard Overview](docs/dashboard-overview.png)

**Shows**:
- Total APIs discovered
- Risk distribution (Critical/High/Medium/Low counts)
- Active migrations count
- Completed migrations

### API Discovery Tab
![API Discovery](docs/api-discovery.png)

**Features**:
- Sortable table with all APIs
- Traffic volume per API
- Error rates
- Risk scores with color badges
- "Migrate" buttons

### Migration Control Tab
![Migration Control](docs/migration-control.png)

**Features**:
- Traffic percentage slider (0-100%)
- Current migration status
- Start mirroring button
- Emergency rollback button

### Activity Logs Tab
![Activity Logs](docs/activity-logs.png)

**Features**:
- Real-time log streaming
- Color-coded by severity
- Timestamp for each action
- Terminal-style display

---

## 🚀 Complete Workflow (Visual)

### Step 1: Open Dashboard
```
http://localhost:8000
```

### Step 2: Discover APIs
1. Click **"Discover APIs"** button (top left)
2. Wait 2-3 seconds
3. See all your APIs appear in table
4. View risk distribution chart

### Step 3: Select LOW-Risk API
1. Find a **GREEN (LOW)** risk API in the table
2. Click **"Migrate"** button
3. Modal popup shows API details

### Step 4: Generate Config
1. In the modal, scroll down
2. Click **"Generate Gloo Gateway Config"**
3. See generated YAML for:
   - VirtualService
   - Upstream
   - AuthConfig
   - RateLimitConfig

### Step 5: Deploy (Manual)
1. Copy YAML from dashboard
2. Save to file: `api-config.yaml`
3. Apply to Kubernetes:
   ```bash
   kubectl apply -f api-config.yaml
   ```

### Step 6: Traffic Mirroring
1. Go to **"Active Migrations"** tab
2. Find your API
3. Click **"Start Mirroring"**
4. Monitor for 24 hours (dashboard shows status)

### Step 7: Canary Rollout (Visual Slider!)
1. In **"Active Migrations"** tab
2. See traffic slider (0% → 100%)
3. **Drag slider to 10%** → Traffic shifts to 10% Gloo
4. Wait 2-4 hours, monitor logs
5. **Drag slider to 50%** → Traffic shifts to 50% Gloo
6. Wait, monitor
7. **Drag slider to 100%** → Full cutover! 🎉

### Step 8: Monitor
- Switch to **"Activity Logs"** tab
- See real-time events
- Check error rates
- Verify successful migration

### Step 9: Rollback (If Needed)
1. In **"Active Migrations"** tab
2. Click **"Rollback"** button
3. Confirm popup
4. 100% traffic instantly back to APIC ✅

---

## 💡 Visual vs CLI

| Task | CLI Command | Web Dashboard |
|------|-------------|---------------|
| **Discover APIs** | `python -m src.cli discover` | Click "Discover APIs" button |
| **View risk score** | Read terminal output | See color-coded badges |
| **Generate plan** | `python -m src.cli plan <api>` | Click "Migrate" → "Generate Config" |
| **Shift traffic** | `python -m src.cli shift <api> --to 50` | Drag slider to 50% |
| **Rollback** | `python -m src.cli rollback <api>` | Click "Rollback" button |
| **View logs** | `python -m src.cli audit` | Switch to "Activity Logs" tab |
| **Monitor status** | `python -m src.cli status` | See live dashboard stats |

**Dashboard Advantages**:
- ✅ No command memorization
- ✅ Visual risk indicators
- ✅ Real-time updates
- ✅ Traffic slider (no typing percentages)
- ✅ One-click actions
- ✅ Charts and graphs

---

## 🎯 Best Practices

1. **Keep Dashboard Open**: Leave it running, auto-refreshes every 5 seconds
2. **Monitor Logs Tab**: During canary rollout, watch for errors
3. **Use Slider Carefully**: Make small increments for HIGH/CRITICAL APIs
4. **Bookmark**: Add `http://localhost:8000` to browser bookmarks

---

## 🔧 Troubleshooting

### "Cannot GET /"
- Make sure web server is running: `./start_web.sh`
- Check terminal for errors

### "No APIs discovered"
- Click "Discover APIs" button first
- Check that mock data is working
- For real APIC, set environment variables

### Charts not showing
- Refresh browser (F5)
- Clear cache (Ctrl+Shift+R)

### Traffic slider not working
- Must start mirroring first
- Check "Active Migrations" tab for status

---

## 📱 Mobile Support

Dashboard is responsive! Access from:
- Desktop browser (recommended)
- Tablet
- Mobile phone (for viewing only, controls may be small)

---

## 🚀 Production Deployment

For production use:

```bash
# Use production WSGI server
pip install gunicorn

# Start with multiple workers
gunicorn -w 4 -k uvicorn.workers.UvicornWorker src.web.api:app --bind 0.0.0.0:8000
```

---

## Next: Try It Now!

```bash
./start_web.bat     # Windows
./start_web.sh      # Linux/Mac

# Then open: http://localhost:8000
```

**Enjoy the visual experience!** 🎨
