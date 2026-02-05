# 🚀 API Migration Orchestrator - Demo Guide

## Quick Start (No APIC Credentials Needed!)

This demo shows the complete API migration workflow using **realistic mock data**.

### Windows

```bash
run_demo.bat
```

### Linux/Mac

```bash
chmod +x run_demo.sh
./run_demo.sh
```

### Manual Run

```bash
# Install dependencies
pip install -r requirements.txt

# Run demo
python demo.py
```

---

## What The Demo Shows

### 1. 🔍 API Discovery from APIC

Discovers APIs matching a team's filters (e.g., `customer-*` for Customer Services team):

```
✓ Discovered 6 APIs matching filter 'customer-*'
  - customer-profile-api
  - customer-search-api
  - customer-registration-api
  - customer-preferences-api
  - customer-notifications-api
  - customer-address-api
```

### 2. 📊 Traffic Analysis & Risk Scoring

Analyzes each API's traffic pattern and calculates risk:

| API Name                   | Traffic (req/day) | Error Rate | Risk Level |
|----------------------------|-------------------|------------|------------|
| customer-profile-api       | 2,500,000         | 0.35%      | CRITICAL   |
| customer-search-api        | 850,000           | 0.12%      | HIGH       |
| customer-registration-api  | 120,000           | 0.05%      | MEDIUM     |
| customer-address-api       | 8,500             | 0.01%      | LOW        |

**Risk Distribution:**
- CRITICAL: 1 API (migrate last with extensive testing)
- HIGH: 2 APIs (conservative rollout)
- MEDIUM: 2 APIs (standard migration)
- LOW: 1 API (fast-track candidate)

### 3. ⚙️ Gloo Gateway Config Generation

Generates Kubernetes CRDs for a LOW-risk API:

#### VirtualService (Routing)
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

#### Upstream (Backend)
```yaml
apiVersion: gloo.solo.io/v1
kind: Upstream
metadata:
  name: customer-address-api-upstream
spec:
  static:
    hosts:
      - addr: apic-gateway.company.com
        port: 443
```

#### AuthConfig (if API has auth)
```yaml
apiVersion: enterprise.gloo.solo.io/v1
kind: AuthConfig
metadata:
  name: customer-address-api-auth
spec:
  configs:
    - apiKeyAuth:
        headerName: X-API-Key
```

#### RateLimitConfig
```yaml
apiVersion: ratelimit.solo.io/v1alpha1
kind: RateLimitConfig
metadata:
  name: customer-address-api-ratelimit
spec:
  raw:
    descriptors:
      - key: generic_key
        value: customer-address-api
        rateLimit:
          requestsPerUnit: 1000
          unit: MINUTE
```

---

## Understanding The Output

### Color-Coded Risk Levels

- 🟢 **LOW** (0.0-0.25): Fast-track migration
  - Low traffic, stable, simple auth
  - Recommendation: Standard or accelerated rollout
  
- 🟡 **MEDIUM** (0.25-0.5): Standard process
  - Moderate traffic, standard auth
  - Recommendation: Normal mirroring + canary phases
  
- 🔴 **HIGH** (0.5-0.75): Conservative rollout
  - High traffic or complex auth
  - Recommendation: Extended mirroring (3-5 days)
  
- 🔴 **CRITICAL** (0.75-1.0): Maximum caution
  - Very high traffic (1M+ req/day) or critical systems
  - Recommendation: 7+ day mirroring, tiny canary increments

### Migration Recommendations

The system automatically suggests:
- **Mirroring duration**: 24 hrs (MEDIUM) to 7+ days (CRITICAL)
- **Canary phases**: Aggressive (10%→50%→100%) to Conservative (1%→3%→5%...)
- **Approval requirements**: Single approver vs. multiple team leads
- **Timing**: Anytime vs. low-traffic windows only

---

## Mock Data Details

The demo uses realistic mock data simulating:

### Domains
- **Customer** (6 APIs): Profile, search, registration, preferences, notifications, address
- **Inventory** (5 APIs): Lookup, sync, allocation, warehouse stock, product availability
- **Order** (5 APIs): Create, status, fulfillment, history, tracking
- **Payment** (4 APIs): Gateway, validation, refunds, history
- **Shipping** (4 APIs): Calculation, tracking, carrier integration, delivery schedule

### Traffic Patterns
- **Critical**: 2-5M requests/day
- **High**: 500K-2M requests/day
- **Medium**: 50K-500K requests/day
- **Low**: 1K-50K requests/day

### Auth Methods
- OAuth2
- JWT
- API Key
- HTTP Basic
- None (public APIs)

---

## Next Steps

After running the demo:

1. **Review Generated Configs**: Study the YAML output to understand Gloo Gateway structure

2. **Customize for Real Use**:
   - Edit `config.example.yaml` → `config.yaml`
   - Add your APIC credentials
   - Set your team name and domain filters

3. **Real Discovery**:
   ```bash
   python -m src.cli.main discover
   ```

4. **Generate Migration Plans**:
   ```bash
   python -m src.cli.main plan <api-name>
   ```

5. **Apply to Kubernetes**:
   ```bash
   kubectl apply -f virtualservice.yaml
   kubectl apply -f upstream.yaml
   kubectl apply -f authconfig.yaml
   ```

---

## What's Missing (Future Work)

This demo shows the **discovery and planning** phase. For a complete migration, you'll need:

- ✅ API Discovery (DONE)
- ✅ Risk Scoring (DONE)
- ✅ Gloo Config Generation (DONE)
- ⏳ Traffic Mirroring Engine (parallel traffic to both platforms)
- ⏳ Canary Rollout Controller (gradual traffic shift)
- ⏳ Automated Rollback (revert on errors)
- ⏳ Web Dashboard (approval UI)
- ⏳ Gloo Portal Integration (publish to developer portal)

The foundation is complete - the remaining components build on this architecture!

---

## Questions?

- **Issue**: No APIs discovered
  - **Solution**: Check your filter patterns in config.yaml
  
- **Issue**: Risk scores all MEDIUM
  - **Solution**: Real APIC will have actual traffic data; mock data is randomized
  
- **Issue**: Need different domains
  - **Solution**: Edit `src/connectors/mock_data.py` to add your domains

