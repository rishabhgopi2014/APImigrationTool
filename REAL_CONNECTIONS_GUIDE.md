# 🔌 Connecting to Real Platforms - Configuration Guide

## Current Setup: Mock Data (Demo Mode)

**Right now, your dashboard is using MOCK DATA** - 24 fake APIs that don't require any real credentials.

This is **by design** so you can test the tool immediately without needing:
- APIC server access
- Kafka cluster credentials  
- Salesforce org credentials
- MuleSoft Anypoint credentials

---

## How Mock vs Real Data Works

### Mock Mode (Current)
When the connectors detect **no credentials**, they automatically use mock data:

```python
# In src/connectors/apic_connector.py
if not self.username and not self.token:
    print("📦 Using mock APIC data (no credentials provided)")
    return MockAPICData.generate_apis()  # Returns 24 fake APIs
```

### Real Mode (Production)
When you **provide credentials**, connectors switch to real API calls:

```python
# With credentials
if self.username and self.token:
    response = requests.get(f"{self.base_url}/api/apis", 
                           auth=(self.username, self.password))
    return real_apis_from_apic  # Returns actual APIs from APIC
```

---

## 🔑 Setting Up Real Platform Credentials

### Option 1: Environment Variables (Recommended for Testing)

Create a `.env` file in your project root:

```bash
# IBM APIC Configuration
APIC_BASE_URL=https://your-apic-server.com:9444
APIC_USERNAME=your-admin-username
APIC_PASSWORD=your-secure-password
APIC_ORG=your-org-name

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=kafka1:9092,kafka2:9092,kafka3:9092
KAFKA_SASL_USERNAME=your-kafka-user
KAFKA_SASL_PASSWORD=your-kafka-password

# Salesforce Configuration
SALESFORCE_INSTANCE_URL=https://your-instance.salesforce.com
SALESFORCE_CLIENT_ID=your-connected-app-client-id
SALESFORCE_CLIENT_SECRET=your-connected-app-secret
SALESFORCE_USERNAME=your-sf-username
SALESFORCE_PASSWORD=your-sf-password

# MuleSoft Configuration
MULESOFT_BASE_URL=https://anypoint.mulesoft.com
MULESOFT_USERNAME=your-anypoint-username
MULESOFT_PASSWORD=your-anypoint-password
MULESOFT_ORG_ID=your-organization-id
```

### Option 2: config.yaml (Recommended for Production)

Edit `config/environments/production.yaml`:

```yaml
platforms:
  apic:
    enabled: true
    base_url: "https://your-apic-server.com:9444"
    username: "{{APIC_USERNAME}}"  # References env var
    password: "{{APIC_PASSWORD}}"
    org: "{{APIC_ORG}}"
    verify_ssl: false
    timeout: 30
    
  kafka:
    enabled: true
    bootstrap_servers:
      - "kafka1.yourcompany.com:9092"
      - "kafka2.yourcompany.com:9092"
    sasl_username: "{{KAFKA_USERNAME}}"
    sasl_password: "{{KAFKA_PASSWORD}}"
    sasl_mechanism: "PLAIN"
    security_protocol: "SASL_SSL"
    
  salesforce:
    enabled: true
    instance_url: "https://yourinstance.salesforce.com"
    client_id: "{{SF_CLIENT_ID}}"
    client_secret: "{{SF_CLIENT_SECRET}}"
    username: "{{SF_USERNAME}}"
    password: "{{SF_PASSWORD}}"
    
  mulesoft:
    enabled: true
    base_url: "https://anypoint.mulesoft.com"
    username: "{{MULESOFT_USERNAME}}"
    password: "{{MULESOFT_PASSWORD}}"
    org_id: "{{MULESOFT_ORG_ID}}"
```

---

## 🚀 How to Use Real Data

### Step 1: Add Credentials

Choose ONE method:
- **Quick test**: Create `.env` file with credentials
- **Production**: Edit `config/environments/production.yaml`

### Step 2: Restart Web Server

```powershell
# Stop old server (if running)
Get-Process -Id (Get-NetTCPConnection -LocalPort 8000).OwningProcess | Stop-Process -Force

# Start with environment
python -m uvicorn src.web.api:app --host 0.0.0.0 --port 8000
```

### Step 3: Discover from Real Platforms

1. Open http://localhost:8000
2. **Enable platforms** with toggles (APIC, Kafka, etc.)
3. Click **"Discover APIs"**
4. Backend detects credentials → **fetches REAL APIs** instead of mock

---

## 📊 How Many APIs Will You Get?

### Mock Mode (Current)
- **APIC**: 6 customer-* APIs
- **Total**: 24 APIs across 5 domains

### Real Mode (With Credentials)
Depends on your actual platforms:
- **APIC**: Could be 100-1500+ APIs depending on your org
- **Kafka**: All topics you have access to
- **Salesforce**: Platform Events, REST APIs, SOAP APIs
- **MuleSoft**: All APIs in your Anypoint Exchange

---

## 🔍 Where to Get Real APIs

### IBM APIC
**What you'll get:**
- All APIs published in your APIC catalogs
- REST APIs
- SOAP wrappers
- GraphQL APIs

**Requirements:**
```
✓ APIC Manager URL (e.g., https://apic.yourcompany.com:9444)
✓ Admin username/password
✓ Organization name
✓ Network access to APIC server
```

### Kafka
**What you'll get:**
- All Kafka topics as potential API endpoints
- Topic metadata (partitions, replicas)
- Consumer group info

**Requirements:**
```
✓ Kafka bootstrap servers (broker URLs)
✓ SASL credentials (if auth enabled)
✓ Network access to Kafka cluster
```

### Salesforce
**What you'll get:**
- Platform Events
- Custom REST APIs
- Standard REST API endpoints
- SOAP API metadata

**Requirements:**
```
✓ Connected App credentials
✓ Salesforce username/password
✓ Instance URL
```

### MuleSoft Anypoint
**What you'll get:**
- All APIs in Exchange
- API implementations
- RAML/OAS specifications
- Proxy configurations

**Requirements:**
```
✓ Anypoint Platform credentials
✓ Organization ID
✓ API access permissions
```

---

## 🧪 Testing Both Modes

### Test Mock Data (No Setup Needed)
```powershell
# Just start server
python -m uvicorn src.web.api:app --port 8000

# Open dashboard → Discover
# Result: 24 mock APIs
```

### Test Real APIC Data
```powershell
# Set environment variables
$env:APIC_BASE_URL="https://apic.example.com:9444"
$env:APIC_USERNAME="admin"
$env:APIC_PASSWORD="your-password"
$env:APIC_ORG="main-org"

# Start server
python -m uvicorn src.web.api:app --port 8000

# Open dashboard → Enable APIC → Discover
# Result: Real APIs from your APIC server
```

---

## 🎯 Quick Decision Guide

**Want to test the UI and workflow?**
→ Use mock data (no setup needed, works now)

**Want to see YOUR ACTUAL APIs?**
→ Add credentials for your platform(s)

**Want to migrate REAL APIs to Gloo?**
→ Add credentials + configure Gloo Gateway connection

---

## 🔐 Security Best Practices

1. **Never commit credentials to Git**
   - Add `.env` to `.gitignore`
   - Use environment variables

2. **Use service accounts**
   - Don't use personal credentials
   - Create dedicated API migration accounts

3. **Rotate credentials regularly**
   - Change passwords after migration complete
   - Use temporary tokens when possible

4. **Encrypt config files**
   - Use Vault/Secrets Manager in production
   - Never store plaintext passwords

---

## 📝 Current Behavior Summary

**RIGHT NOW (March 2026):**
- ✅ Dashboard shows 24 **mock APIs** (fake data)
- ✅ No credentials needed
- ✅ Perfect for testing UI
- ❌ Not connected to real APIC/Kafka/Salesforce/MuleSoft

**TO GET REAL APIs:**
1. Add credentials (`.env` or `config.yaml`)
2. Restart server
3. Connectors auto-detect credentials
4. Discovery fetches from real platforms
5. You see YOUR actual APIs (100s-1000s)

---

## 🆘 Troubleshooting Real Connections

**"Still seeing only 24 APIs"**
- Check: Did you restart the server after adding credentials?
- Check: Are credentials correct? (test with curl/postman first)
- Check: Firewall/VPN access to platform servers?

**"Connection timeout"**
- Check: Can you ping the APIC/Kafka server?
- Check: Is the port open? (try telnet)
- Check: VPN connected if required?

**"Authentication failed"**
- Check: Username/password correct?
- Check: Account not locked?
- Check: Using correct org/realm?

---

## 🎓 Next Steps

1. **Keep using mock data** for now to test UI ✅
2. **Get credentials** from your platform admins
3. **Test connection** with curl/postman first
4. **Add to .env** file
5. **Restart server** and discover REAL APIs!

Your dashboard will work exactly the same way, just with YOUR APIs instead of mock data! 🚀
