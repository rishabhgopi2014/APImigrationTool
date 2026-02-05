# Quick Start Cheat Sheet

## 1️⃣ First Time Setup (15 min)

```bash
# Copy config
cp config.example.yaml config.yaml

# Edit config.yaml - set YOUR team name and filters
# Example:
#   team: "customer-services"
#   filters: ["customer-*", "profile-*"]

# Set credentials (environment variables)
export APIC_USERNAME="your-username"
export APIC_PASSWORD="your-password"

# Validate
python -m src.cli.main validate-config
```

---

## 2️⃣ Discover Your APIs (5 min)

```bash
python -m src.cli.main discover

# Shows YOUR APIs with risk scores:
# ✓ customer-address-api    - LOW (8K req/day)
# ✓ customer-profile-api    - CRITICAL (2.5M req/day)
```

---

## 3️⃣ Migrate First API (Start with LOW risk!)

### Generate Plan
```bash
python -m src.cli.main plan customer-address-api
```

### Deploy to Kubernetes
```bash
kubectl apply -f plans/customer-address-api/
```

### Traffic Mirroring (24 hours)
```bash
python -m src.cli.main mirror customer-address-api --duration 24h
```

### Canary Rollout
```bash
# 10% traffic to Gloo
python -m src.cli.main shift customer-address-api --to 10

# Monitor for 2-4 hours, then:
python -m src.cli.main shift customer-address-api --to 50

# Monitor, then full cutover:
python -m src.cli.main shift customer-address-api --to 100
```

### Complete
```bash
python -m src.cli.main complete customer-address-api
```

---

## 🆘 Emergency Rollback

```bash
python -m src.cli.main rollback customer-address-api
# ← Instant 100% back to APIC
```

---

## 📊 Daily Commands

```bash
# Check status
python -m src.cli.main status

# View metrics
python -m src.cli.main metrics <api-name>

# See who's working on what
python -m src.cli.main locks
```

---

## 💡 Migration Order

1. **LOW risk** (1-2 days) ← START HERE
2. **MEDIUM risk** (1 week)
3. **HIGH risk** (2 weeks)
4. **CRITICAL risk** (careful planning, multiple approvals)

---

## Full Guide

See [DEVELOPER_GUIDE.md](file:///c:/Users/Admin/OneDrive/Documents/APIMigration/DEVELOPER_GUIDE.md) for complete instructions!
