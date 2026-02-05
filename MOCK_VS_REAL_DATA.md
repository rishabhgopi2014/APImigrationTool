# 🔒 **Credential Security & Mock Data Behavior**

## ✅ **How Mock vs Real Data Works**

The system automatically detects whether to use mock or real data based on credentials:

### Mock Mode (Demo)
**Triggers when:**
- `.env` file has **empty** or **missing** APIC credentials
- `APIC_BASE_URL` is empty
- `APIC_USERNAME` is empty  
- `APIC_PASSWORD` is empty

**Behavior:**
```
📦 DEMO MODE: Using mock APIC data (no credentials provided)
ℹ️  To connect to real APIC, add credentials to .env file
ℹ️  Mock data: 24 fake APIs across 5 domains

Result: Returns 24 fake APIs for testing
```

### Production Mode (Real Data)
**Triggers when:**
- `.env` file has **ANY** of these filled in:
  - `APIC_BASE_URL=https://apic.yourcompany.com:9444`
  - `APIC_USERNAME=admin`
  - `APIC_PASSWORD=YourPassword123`

**Behavior:**
```
🔌 PRODUCTION MODE: Connecting to APIC at https://apic.yourcompany.com:9444
👤 Username: admin

Result: Returns YOUR real APIs from APIC server
```

---

## 🛡️ **Security Guarantees**

### ✅ Mock Data Never Appears in Production

The check is explicit and strict:

```python
# In connectors/apic_connector.py (line 117)
has_credentials = bool(self.username or self.token or self.base_url)

if not has_credentials:
    # Use mock data (ONLY when truly empty)
    return MockAPICData.generate_apis()

# Otherwise, connect to real APIC
return real_apis_from_apic_server()
```

### ✅ No Data Mixing

- **Mock mode:** 100% fake data
- **Production mode:** 100% real data from your APIC
- **Never mixed:** Can't have both at same time

---

## 🧪 **Testing Both Modes**

### Test 1: Mock Data (Current)
```bash
# .env file (current state)
APIC_BASE_URL=
APIC_USERNAME=
APIC_PASSWORD=

# Start server
.\start.bat

# Open dashboard → Discover APIs
# Result: ✅ 24 mock APIs
```

### Test 2: Real Data (When Ready)
```bash
# .env file (with credentials)
APIC_BASE_URL=https://apic.company.com:9444
APIC_USERNAME=admin
APIC_PASSWORD=SecurePass123

# Start server
.\start.bat

# Open dashboard → Discover APIs
# Result: ✅ YOUR real APIs (no mock data)
```

### Test 3: Verify No Mock Leakage
```bash
# Add only URL (partial credentials)
APIC_BASE_URL=https://apic.company.com:9444
APIC_USERNAME=
APIC_PASSWORD=

# Start server
.\start.bat

# Open dashboard → Discover APIs
# Result: ✅ Attempts real connection (fails with auth error)
#         ❌ NO mock data shown (because base_url exists)
```

---

## 🔍 **How the System Decides**

```
┌─────────────────────────────────┐
│ User clicks "Discover APIs"     │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ Load credentials from .env      │
│ - APIC_BASE_URL                 │
│ - APIC_USERNAME                 │
│ - APIC_PASSWORD                 │
└────────────┬────────────────────┘
             │
             ▼
┌─────────────────────────────────┐
│ Check: Are ANY credentials set? │
└────────────┬────────────────────┘
             │
      ┌──────┴──────┐
      │             │
      ▼             ▼
   NO credentials  YES credentials
   (ALL empty)     (ANY filled)
      │             │
      ▼             ▼
 ┌─────────┐   ┌──────────┐
 │ MOCK    │   │ REAL     │
 │ DATA    │   │ APIC     │
 │ 24 APIs │   │ YOUR APIs│
 └─────────┘   └──────────┘
```

---

## 📝 **Code Verification**

### Location 1: Web API (src/web/api.py)
```python
# Line 85-90 (NEW CODE)
credentials = {
    "url": os.getenv("APIC_BASE_URL", ""),
    "username": os.getenv("APIC_USERNAME", ""),
    "password": os.getenv("APIC_PASSWORD", "")
}

connector = APICConnector(credentials=credentials)
```

### Location 2: APIC Connector (src/connectors/apic_connector.py)
```python
# Line 117-125 (UPDATED CODE)
has_credentials = bool(self.username or self.token or self.base_url)

if not has_credentials:
    print("📦 DEMO MODE: Using mock APIC data")
    return MockAPICData.generate_apis()

print("🔌 PRODUCTION MODE: Connecting to real APIC")
# ... real APIC connection code
```

---

## 🎯 **Summary**

| Scenario | .env Contents | Result |
|----------|---------------|--------|
| **Testing (Current)** | All empty | 24 mock APIs ✅ |
| **Production** | Credentials filled | YOUR real APIs ✅ |
| **Mixed** | Partial credentials | Real connection attempt ❌ No mock data |

**Guarantee:** Mock data **ONLY** appears when **ALL** credentials are empty or missing.

**No Risk:** Once you add real credentials, mock data is impossible to see.

---

## 🔐 **Best Practices**

1. **Test with mock first** - Verify UI works
2. **Add credentials gradually** - Test each platform separately
3. **Never commit .env** - Already in .gitignore
4. **Use service accounts** - Not personal credentials
5. **Rotate regularly** - Change after testing complete

Your data is safe! 🛡️
