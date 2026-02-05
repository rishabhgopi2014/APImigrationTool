# 🚀 Quick Start - Testing Your Web Dashboard

## ✅ Everything is Ready!

Your API Migration Orchestrator web dashboard is fully implemented with:
- ✅ Platform selection toggles (APIC, Kafka, Salesforce, MuleSoft)
- ✅ Complete 5-step migration workflow  
- ✅ Mock data generator (24 APIs)
- ✅ Interactive traffic control slider
- ✅ Real-time activity logs

---

## 🎯 Test It Now

### Step 1: Restart Web Server

The server is currently running on port 8000. **Restart it** to load the new changes:

```powershell
# Press Ctrl+C to stop the running server, then:
python -m uvicorn src.web.api:app --host 0.0.0.0 --port 8000 --reload
```

> **Tip:** The `--reload` flag auto-reloads on file changes!

### Step 2: Open Browser

```
http://localhost:8000
```

### Step 3: Test Platform Toggles

At the top of the page, you should see **4 toggle switches**:
- ✅ IBM APIC (blue = enabled)
- ⬜ Kafka (gray = disabled)
- ⬜ Salesforce (gray = disabled)
- ⬜ Mule Soft (gray = disabled)

**Try this:**
1. Click to **disable APIC** → Button turns gray
2. Notice the "Discover APIs" button is now **disabled** (you can't click it)
3. **Re-enable APIC** → Button becomes clickable again
4. Enable **APIC + Kafka** together

### Step 4: Discover APIs

1. Make sure at least one platform is enabled
2. Click **"Discover APIs"** button
3. Wait 2-3 seconds
4. See **24 APIs** appear in the table below

### Step 5: Test Migration Workflow

1. **Select an API**: Click "Migrate" on any **LOW-risk** (green) API
2. Modal opens showing the API details
3. **Follow the workflow**:

**Step 1:** Click "Generate" → See YAML configs
**Step 2:** Click "Mark Deployed" → Unlocks step 3
**Step 3:** Click "Start Mirroring" → Status changes
**Step 4:** **Drag the slider** from 0% → 10% → 50% → 100%
**Step 5:** Click "Complete" → Success!

### Step 6: Test Emergency Rollback

At any time during steps 3-5:
1. Click the **red "Rollback"** button
2. Confirm the popup
3. Watch it revert to step 2

---

## 🎨 What Each Feature Does

### Platform Toggles
- **Visual switches** - Click to enable/disable
- **Validation** - Can't discover with all disabled
- **Color feedback** - Blue = on, Gray = off

### Migration Steps (1-5)

| Step | Button | Action |
|------|--------|--------|
| 1️⃣ Generate Config | Generate | Creates Kubernetes YAML |
| 2️⃣ Deploy | Mark Deployed | Confirms kubectl apply |
| 3️⃣ Mirroring | Start Mirroring | 24h validation phase |
| 4️⃣ Canary Rollout | Slider 0-100% | Gradual traffic shift |
| 5️⃣ Complete | Complete | Finalize migration |

### Traffic Slider
- Drag left = 0% to Gloo (100% legacy)
- Drag right = 100% to Gloo (0% legacy)
- Updates backend in real-time

---

## 🐛 Troubleshooting

**Platform toggles not working?**
- Hard refresh: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)

**"Discover" button stuck disabled?**
- Check if at least one platform is enabled (blue)
- Open browser console (F12) for errors

**Modal not showing steps?**
- Make sure you restarted the server after code changes
- Check browser console for JavaScript errors

**Slider not appearing?**
- Only shows in Step 4 (Canary Rollout)
- Complete steps 1-3 first

---

## 📊 Expected Behavior

### When You Click "Discover"
```
✓ Button shows "Discovering..." with spinner
✓ After 2-3 seconds, table fills with APIs
✓ Stats cards update (Total: 24, Critical: 3)
✓ Risk chart renders below
```

### When You Click "Migrate"
```
✓ Modal popup opens
✓ Shows API details (traffic, error rate, risk)
✓ Displays 5-step workflow with numbered circles
✓ Only Step 1 is active (blue)
✓ Other steps are gray (locked)
```

### When You Complete Each Step
```
Step 1: Generate Config
  → Button changes to "✓ Complete" (green)
  → YAML configs appear below (collapsible)
  → Step 2 unlocks

Step 2: Mark Deployed
  → kubectl commands shown
  → Step 3 unlocks

Step 3: Start Mirroring
  → Status shows "⏰ In Progress"
  → Step 4 unlocks
  → Slider appears

Step 4: Use Slider  
  → Drag to adjust percentage
  → Each change sends API request
  → Can increase gradually

Step 5: Complete (only when slider = 100%)
  → "🏆 Success!" shown
  → Migration finished
```

---

## 🎥 Quick Demo Flow

**Full test in 60 seconds:**

1. Enable APIC ✅
2. Click "Discover APIs" 🔍
3. Wait for table (24 APIs) 📊
4. Click "Migrate" on `customer-address-api` 🟢
5. Click "Generate" → See YAML ✅
6. Click "Mark Deployed" → See kubectl commands ✅
7. Click "Start Mirroring" → Status changes ✅
8. Drag slider 0 → 100% → Watch it update 📈
9. Click "Complete" → Mission accomplished! 🎉

---

## 📝 Notes

- **Mock Data**: Using 24 fake APIs (no real APIC needed)
- **Backend**: FastAPI REST API on port 8000
- **Frontend**: Vue.js 3 + Tailwind CSS
- **Auto-refresh**: Dashboard polls every 5 seconds

---

## 🆘 Need Help?

If something doesn't work:
1. Check browser console (F12) for errors
2. Check server logs in terminal
3. Verify server is running on correct port
4. Try hard refresh (Ctrl+Shift+R)

Enjoy your new visual API migration dashboard! 🚀
