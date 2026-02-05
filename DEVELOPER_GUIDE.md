# Developer Guide - API Migration Orchestrator

## For Developers Migrating Their Team's APIs

This guide shows **step-by-step** how to use the tool to migrate your APIs from APIC/MuleSoft/Kafka to Gloo Gateway.

---

## 🎯 Your Migration Journey

### Phase 1: Setup (One-time, 15 minutes)
### Phase 2: Discovery & Planning (1-2 hours)
### Phase 3: Migrate Low-Risk APIs (1-2 days)
### Phase 4: Migrate Medium/High-Risk APIs (1-2 weeks)
### Phase 5: Decommission Legacy (After validation)

---

## 📋 Phase 1: Initial Setup

### Step 1: Get Your Team's Config

```bash
# Clone/navigate to the tool
cd APIMigration

# Copy example config
cp config.example.yaml config.yaml
```

### Step 2: Edit config.yaml for YOUR team

```yaml
# Example: Customer Services Team
owner:
  team: "customer-services"           # Your team name
  domain: "customer-management"       # Your business domain
  contact: "alice@company.com"        # Your email

discovery:
  # Enable ONLY platforms you use
  apic:
    enabled: true
    credentials:
      url: "https://apic.company.com"
      username: "${APIC_USERNAME}"    # Set via env var
      password: "${APIC_PASSWORD}"
    filters:
      - "customer-*"                  # Only YOUR APIs
      - "profile-*"
      - "account-*"
    exclude_patterns:
      - "*-internal-*"                # Skip internal/test APIs
      - "*-test-*"

  mulesoft:
    enabled: false                    # Disable if you don't use it

  kafka:
    enabled: false

  swagger:
    enabled: true
    credentials:
      url: "https://api-docs.company.com/customer"
```

### Step 3: Set Environment Variables

**Windows (PowerShell):**
```powershell
$env:APIC_USERNAME="your-username"
$env:APIC_PASSWORD="your-password"
$env:DATABASE_URL="postgresql://user:pass@localhost/migrations"
$env:REDIS_URL="redis://localhost:6379"
```

**Linux/Mac:**
```bash
export APIC_USERNAME="your-username"
export APIC_PASSWORD="your-password"
export DATABASE_URL="postgresql://user:pass@localhost/migrations"
export REDIS_URL="redis://localhost:6379"
```

**Best Practice:** Create a `.env` file (not committed to git):
```bash
# .env (add to .gitignore)
APIC_USERNAME=your-username
APIC_PASSWORD=your-password
DATABASE_URL=postgresql://user:pass@localhost/migrations
REDIS_URL=redis://localhost:6379
```

### Step 4: Validate Your Config

```bash
python -m src.cli.main validate-config

# Expected output:
# ✓ Configuration is valid!
# Owner:
#   Team: customer-services
#   Domain: customer-management
# Discovery:
#   APIC: enabled
#   Swagger: enabled
```

---

## 🔍 Phase 2: Discovery & Planning

### Step 1: Discover YOUR APIs

```bash
python -m src.cli.main discover

# What happens:
# 1. Connects to APIC (using your credentials)
# 2. Fetches only APIs matching your filters
# 3. Analyzes traffic patterns (req/day, errors, latency)
# 4. Calculates risk scores
# 5. Shows prioritized list
```

**Example Output:**
```
✨ Discovered APIs for customer-services (Sorted by Risk)
┌────────────────────────┬──────────┬───────────┬─────────┬──────┬──────────┐
│ API Name               │ Traffic  │ Error     │ Risk    │ Level│          │
├────────────────────────┼──────────┼───────────┼─────────┼──────┼──────────┤
│ customer-profile-api   │2,500,000 │ 0.35%     │ 0.82    │CRITICAL         │
│ customer-search-api    │  850,000 │ 0.12%     │ 0.56    │HIGH             │
│ customer-registration  │  120,000 │ 0.05%     │ 0.32    │MEDIUM           │
│ customer-address-api   │    8,500 │ 0.01%     │ 0.15    │LOW              │
└────────────────────────┴──────────┴───────────┴─────────┴──────────────────┘

📊 Risk Distribution:
  CRITICAL:  1 API  (migrate LAST)
  HIGH:      2 APIs (conservative approach)
  MEDIUM:    4 APIs (standard process)
  LOW:       3 APIs (START HERE!)

💡 Migration Strategy:
  • Start with LOW risk APIs to build confidence
  • Migrate CRITICAL APIs last with extensive testing
```

### Step 2: Review Discovered APIs

```bash
# List all your APIs
python -m src.cli.main list

# Filter by risk level
python -m src.cli.main list --risk LOW

# View details of specific API
python -m src.cli.main details customer-address-api
```

### Step 3: Create Migration Order

Based on risk scores, plan your migration order:

**Week 1-2: Low Risk (Fast Wins)**
1. `customer-address-api` (8K req/day, no auth)
2. `customer-preferences-api` (12K req/day, API key)
3. `customer-notifications-api` (25K req/day, API key)

**Week 3-4: Medium Risk**
4. `customer-registration-api` (120K req/day, JWT)
5. `customer-lookup-api` (200K req/day, JWT)

**Week 5-6: High Risk**
6. `customer-search-api` (850K req/day, OAuth)

**Week 7+: Critical (Requires Approval)**
7. `customer-profile-api` (2.5M req/day, OAuth)

---

## 🚀 Phase 3: Migrate Your First API

### Choose a LOW-risk API to start

Let's migrate `customer-address-api` (8,500 req/day, LOW risk).

### Step 1: Generate Migration Plan

```bash
python -m src.cli.main plan customer-address-api

# Generates:
# - Gloo Gateway VirtualService
# - Upstream configuration
# - AuthConfig (if needed)
# - RateLimitConfig
# - Migration checklist
```

**Tool Output:**
```
📝 Generated migration plan for customer-address-api

Files created:
✓ plans/customer-address-api/virtualservice.yaml
✓ plans/customer-address-api/upstream.yaml
✓ plans/customer-address-api/authconfig.yaml
✓ plans/customer-address-api/migration-checklist.md

Risk Level: LOW (0.15)
Recommended approach:
  • Traffic mirroring: 24 hours
  • Canary phases: 10% → 50% → 100%
  • Approval required: Team lead
```

### Step 2: Review Generated Gloo Configs

**Generated files in `plans/customer-address-api/`:**

`virtualservice.yaml`:
```yaml
apiVersion: gateway.solo.io/v1
kind: VirtualService
metadata:
  name: customer-address-api-vs
  namespace: gloo-system
spec:
  virtualHost:
    domains:
      - customer-address-api.company.com
    routes:
      - matchers:
          - prefix: /customer/v2
        routeAction:
          single:
            upstream:
              name: customer-address-api-upstream
```

`upstream.yaml`:
```yaml
apiVersion: gloo.solo.io/v1
kind: Upstream
metadata:
  name: customer-address-api-upstream
  namespace: gloo-system
spec:
  static:
    hosts:
      - addr: apic-gateway.company.com
        port: 443
```

### Step 3: Deploy to Gloo Gateway

```bash
# Apply configs to Kubernetes
kubectl apply -f plans/customer-address-api/upstream.yaml
kubectl apply -f plans/customer-address-api/virtualservice.yaml
kubectl apply -f plans/customer-address-api/authconfig.yaml

# Verify deployment
kubectl get virtualservice -n gloo-system
kubectl get upstream -n gloo-system
```

### Step 4: Start Traffic Mirroring (24 hours)

```bash
python -m src.cli.main mirror customer-address-api --duration 24h

# What happens:
# 1. 100% traffic still goes to APIC
# 2. Duplicate traffic sent to Gloo Gateway
# 3. Compare responses for differences
# 4. Log any errors or mismatches
```

**Monitoring:**
```bash
# Check mirroring status
python -m src.cli.main status customer-address-api

# Expected:
# API: customer-address-api
# Status: MIRRORING
# Duration: 6h 23m / 24h
# Success rate: 99.8%
# Errors: 12 (review in dashboard)
```

### Step 5: Review Mirror Results

After 24 hours:

```bash
python -m src.cli.main mirror-report customer-address-api

# Shows comparison:
# Requests mirrored: 8,234
# Successful: 8,222 (99.85%)
# Response mismatches: 2 (0.02%)
# Latency comparison:
#   APIC avg: 52ms
#   Gloo avg: 48ms (8% faster!)
# 
# ✓ Ready to proceed with canary rollout
```

### Step 6: Canary Rollout (Gradual Traffic Shift)

**10% Canary:**
```bash
python -m src.cli.main shift customer-address-api --to 10

# Now:
# - 10% traffic → Gloo Gateway
# - 90% traffic → APIC
# 
# Monitor for 2-4 hours
```

**Monitor:**
```bash
python -m src.cli.main status customer-address-api

# Status: CANARY_10
# Gloo traffic: 850 req/hour
# Error rate: 0.01% (same as APIC ✓)
# Latency: 48ms avg
```

**50% Canary (if 10% looks good):**
```bash
python -m src.cli.main shift customer-address-api --to 50

# Monitor for 4-8 hours
```

**100% Cutover:**
```bash
python -m src.cli.main shift customer-address-api --to 100

# All traffic now on Gloo Gateway!
# APIC receives 0%
```

### Step 7: Validate & Monitor

```bash
# Monitor for 24-48 hours
python -m src.cli.main status customer-address-api

# If stable:
python -m src.cli.main complete customer-address-api

# Marks migration as COMPLETED
```

### Step 8: Rollback (if needed)

```bash
# If errors spike during canary:
python -m src.cli.main rollback customer-address-api

# Instantly:
# - 100% traffic back to APIC
# - Gloo Gateway receives 0%
# - Status: ROLLED_BACK
# 
# Investigate issues, fix configs, retry later
```

---

## 📊 Daily Workflow

### Morning: Check Migration Status

```bash
python -m src.cli.main status

# Shows all your APIs:
# customer-address-api      : COMPLETED ✓
# customer-preferences-api  : CANARY_50 (monitoring)
# customer-registration-api : PLANNED (ready to deploy)
# customer-profile-api      : DISCOVERED (not started)
```

### During Work: Monitor Active Migrations

```bash
# Check canary progress
python -m src.cli.main metrics customer-preferences-api

# Requests: 6,234 (last hour)
# Error rate: 0.05%
# Latency p95: 89ms
# Status: Healthy ✓
```

### End of Day: Record Progress

```bash
# View audit log
python -m src.cli.main audit --today

# 09:15 - alice@company.com - Started mirroring customer-preferences-api
# 14:32 - alice@company.com - Shifted customer-preferences-api to 10%
# 16:48 - bob@company.com   - Approved 50% shift for customer-preferences-api
```

---

## 👥 Team Collaboration

### Multiple Developers on Same Team

**Developer A (Alice):**
```bash
# Alice migrates customer APIs
python -m src.cli.main discover  # Sees only customer-* APIs
python -m src.cli.main plan customer-address-api
```

**Developer B (Bob):**
```bash
# Bob migrates different customer APIs
# Uses same config (same team)
python -m src.cli.main discover  # Sees same customer-* APIs
python -m src.cli.main plan customer-search-api
```

**Conflict Prevention:**
- Tool uses **distributed locking** (Redis)
- If Alice is migrating `customer-address-api`, Bob cannot touch it
- Bob sees: "❌ API locked by alice@company.com (started 2h ago)"

### Check What's Locked

```bash
python -m src.cli.main locks

# Active Migration Locks:
# API Name              | Locked By             | Started
# customer-address-api  | alice@company.com    | 2h ago
# customer-search-api   | bob@company.com      | 30m ago
```

---

## 🆘 Troubleshooting

### "No APIs discovered"
```bash
# Check your filters
python -m src.cli.main validate-config

# Make sure filters match your API names:
# filters: ["customer-*"]  ✓
# filters: ["payment-*"]   ✗ (wrong domain)
```

### "Cannot connect to APIC"
```bash
# Check credentials
echo $APIC_USERNAME
echo $APIC_PASSWORD

# Test connection
curl -u $APIC_USERNAME:$APIC_PASSWORD https://apic.company.com/api
```

### "Risk scores all unknown"
- Real APIC connection needed for traffic metrics
- Demo mode (no credentials) uses mock data

### "Migration locked by another user"
```bash
# View locks
python -m src.cli.main locks

# If lock is stale (user left 2 days ago):
python -m src.cli.main unlock customer-address-api --force
# Requires admin approval
```

---

## 📚 Quick Reference

### Common Commands

```bash
# Discovery
python -m src.cli.main discover                    # Find your APIs
python -m src.cli.main list --risk LOW             # List low-risk APIs
python -m src.cli.main details <api-name>          # API details

# Planning
python -m src.cli.main plan <api-name>             # Generate Gloo configs

# Migration
python -m src.cli.main mirror <api-name>           # Start mirroring
python -m src.cli.main shift <api-name> --to 10    # Canary 10%
python -m src.cli.main shift <api-name> --to 50    # Canary 50%
python -m src.cli.main shift <api-name> --to 100   # Full cutover

# Monitoring
python -m src.cli.main status                      # All migrations
python -m src.cli.main status <api-name>           # Specific API
python -m src.cli.main metrics <api-name>          # Traffic metrics

# Recovery
python -m src.cli.main rollback <api-name>         # Emergency rollback

# Admin
python -m src.cli.main locks                       # Active locks
python -m src.cli.main audit --today               # Today's actions
```

---

## 🎓 Best Practices

### 1. Start Small
- Pick 1-2 LOW-risk APIs for first migration
- Build confidence before tackling HIGH/CRITICAL

### 2. Monitor Actively
- Check canary metrics every 2-4 hours
- Don't leave canary unattended overnight (for HIGH/CRITICAL)

### 3. Document Issues
- If you rollback, document why
- Share learnings with team

### 4. Communicate
- Announce migrations in team chat
- Coordinate with other developers
- Get approvals for HIGH/CRITICAL APIs

### 5. Incremental Approach
- LOW risk: Aggressive canary (10% → 50% → 100%)
- MEDIUM risk: Standard canary (5% → 25% → 50% → 100%)
- HIGH risk: Conservative canary (1% → 5% → 10% → 25% → 50% → 100%)
- CRITICAL risk: Ultra-conservative (1% → 3% → 5% → 10%...)

---

## 📅 Example Migration Timeline

**Team: Customer Services (10 APIs)**

### Week 1
- Mon: Setup config, discover APIs
- Tue-Fri: Migrate 2 LOW-risk APIs (fast wins!)

### Week 2-3
- Migrate 4 MEDIUM-risk APIs (1-2 per week)

### Week 4-5
- Migrate 3 HIGH-risk APIs (careful canary)

### Week 6+
- Migrate 1 CRITICAL API (extended testing)
- Get director approval
- 7-day mirroring
- Ultra-conservative canary

---

## 🔗 Need Help?

- **Config issues**: Review `config.example.yaml`
- **Gloo Gateway docs**: https://docs.solo.io/gloo-gateway/
- **Architecture**: See [implementation_plan.md](file:///C:/Users/Admin/.gemini/antigravity/brain/7e19ff0a-cc6f-49bc-a122-e7ef8b386b47/implementation_plan.md)
- **Migration guide**: See [walkthrough.md](file:///C:/Users/Admin/.gemini/antigravity/brain/7e19ff0a-cc6f-49bc-a122-e7ef8b386b47/walkthrough.md)

**Happy migrating! 🚀**
