# CLI Reference

## Overview

The API Migration Orchestrator provides a comprehensive command-line interface for discovering, planning, executing, and monitoring API migrations from legacy platforms to Gloo Gateway.

---

## Installation & Setup

### Quick Start

```bash
# Navigate to project directory
cd APIMigration

# Install dependencies
pip install -r requirements.txt

# Set up configuration
cp config.example.yaml config.yaml
# Edit config.yaml with your team settings

# Set environment variables
export APIC_USERNAME="your-username"
export APIC_PASSWORD="your-password"
export DATABASE_URL="postgresql://user:pass@localhost:5432/api_migration"
export REDIS_URL="redis://localhost:6379/0"
```

---

## Command Structure

```bash
python -m src.cli.main <command> [options] [arguments]
```

**Alternative**: Create an alias
```bash
# Add to ~/.bashrc or ~/.zshrc
alias migrate="python -m src.cli.main"

# Usage
migrate discover
migrate plan payment-api
```

---

## Commands Reference

### Discovery Commands

#### `discover`

Discover APIs from configured platforms (APIC, MuleSoft, Kafka, Swagger).

**Syntax**:
```bash
python -m src.cli.main discover [OPTIONS]
```

**Options**:
- `--platform <name>`: Discover from specific platform only (`apic`, `mulesoft`, `kafka`, `swagger`)
- `--batch`: Enable batch processing mode
- `--force`: Re-discover even if cached
- `--dry-run`: Preview without saving to database

**Examples**:

```bash
# Discover from all enabled platforms
python -m src.cli.main discover

# Discover only from APIC
python -m src.cli.main discover --platform apic

# Batch mode for large-scale discovery
python -m src.cli.main discover --batch

# Preview discovery without saving
python -m src.cli.main discover --dry-run
```

**Output**:
```
✨ Discovered APIs for payments-team (Sorted by Risk)
┌────────────────────────┬──────────┬───────────┬─────────┬──────┬──────────┐
│ API Name               │ Platform │ Traffic   │ Error   │ Risk │ Level    │
├────────────────────────┼──────────┼───────────┼─────────┼──────┼──────────┤
│ payment-gateway-api    │ APIC     │2,500,000  │ 0.35%   │ 0.82 │ CRITICAL │
│ payment-refund-api     │ APIC     │  850,000  │ 0.12%   │ 0.56 │ HIGH     │
│ checkout-cart-api      │ APIC     │  120,000  │ 0.05%   │ 0.32 │ MEDIUM   │
│ payment-webhook-api    │ APIC     │    8,500  │ 0.01%   │ 0.15 │ LOW      │
└────────────────────────┴──────────┴───────────┴─────────┴──────┴──────────┘

📊 Risk Distribution:
  CRITICAL:  1 API  (migrate LAST with extensive testing)
  HIGH:      3 APIs (conservative canary rollout)
  MEDIUM:    8 APIs (standard migration process)
  LOW:       6 APIs (fast-track candidates - START HERE!)

💡 Migration Strategy:
  • Start with LOW risk APIs to build confidence
  • Migrate CRITICAL APIs last with extensive mirroring
```

---

#### `list`

List discovered APIs with filtering options.

**Syntax**:
```bash
python -m src.cli.main list [OPTIONS]
```

**Options**:
- `--risk <level>`: Filter by risk level (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`)
- `--platform <name>`: Filter by platform
- `--status <status>`: Filter by migration status
- `--sort <field>`: Sort by field (`risk`, `traffic`, `name`, `error_rate`)
- `--team <name>`: Filter by team (multi-tenant)
- `--format <type>`: Output format (`table`, `json`, `csv`)

**Examples**:

```bash
# List all APIs
python -m src.cli.main list

# List only LOW risk APIs
python -m src.cli.main list --risk LOW

# List APIs from APIC sorted by traffic
python -m src.cli.main list --platform apic --sort traffic

# Export to JSON
python -m src.cli.main list --format json > apis.json

# List completed migrations
python -m src.cli.main list --status COMPLETED
```

---

#### `details`

Show detailed information about a specific API.

**Syntax**:
```bash
python -m src.cli.main details <api-name>
```

**Examples**:

```bash
python -m src.cli.main details payment-gateway-api
```

**Output**:
```
API: payment-gateway-api
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Platform: IBM API Connect
Team: payments-team
Domain: payment-services

Risk Assessment:
  Risk Score: 0.82
  Risk Level: CRITICAL
  Recommendation: Extensive testing required

Traffic Metrics:
  Requests/day: 2,500,000
  Requests/sec: ~29
  Peak traffic: 150 req/sec (14:00-15:00)

Performance:
  Avg latency: 145ms
  P95 latency: 320ms
  P99 latency: 580ms
  Error rate: 0.35%

Authentication:
  Type: OAuth 2.0
  Provider: company-oauth.com
  Scopes: payment:read, payment:write

Rate Limiting:
  Default: 1000 req/min
  Premium: 10000 req/min

Endpoints: 12
  POST   /api/v2/payments
  GET    /api/v2/payments/{id}
  DELETE /api/v2/payments/{id}
  POST   /api/v2/refunds
  ... (8 more)

Dependencies: 3
  - customer-profile-api
  - fraud-detection-service
  - payment-processor-backend

Migration Status: DISCOVERED
Last Updated: 2026-02-06 10:30:00
```

---

### Planning Commands

#### `plan`

Generate Gloo Gateway configuration for an API.

**Syntax**:
```bash
python -m src.cli.main plan <api-name> [OPTIONS]
```

**Options**:
- `--output-dir <path>`: Output directory (default: `plans/<api-name>`)
- `--format <type>`: Output format (`yaml`, `json`)
- `--include-portal`: Include Gloo Portal configuration
- `--dry-run`: Preview without saving files

**Examples**:

```bash
# Generate plan for specific API
python -m src.cli.main plan payment-gateway-api

# Custom output directory
python -m src.cli.main plan payment-gateway-api --output-dir ./configs

# Include portal configuration
python -m src.cli.main plan payment-gateway-api --include-portal

# Preview without saving
python -m src.cli.main plan payment-gateway-api --dry-run
```

**Generated Files**:
```
plans/payment-gateway-api/
├── virtualservice.yaml       # Routing configuration
├── upstream.yaml             # Backend target
├── authconfig.yaml           # Authentication
├── ratelimit.yaml            # Rate limiting
├── transformation.yaml       # Header/body transformations
├── portal.yaml               # Portal configuration (if --include-portal)
└── migration-checklist.md    # Migration checklist
```

**Output**:
```
📝 Generated migration plan for payment-gateway-api

Files created:
✓ plans/payment-gateway-api/virtualservice.yaml
✓ plans/payment-gateway-api/upstream.yaml
✓ plans/payment-gateway-api/authconfig.yaml
✓ plans/payment-gateway-api/ratelimit.yaml
✓ plans/payment-gateway-api/migration-checklist.md

Risk Level: CRITICAL (0.82)
Recommended approach:
  • Traffic mirroring: 48-72 hours
  • Canary phases: 1% → 5% → 10% → 25% → 50% → 100%
  • Monitoring: 4 hours per phase
  • Approval required: Team Lead + Director

Next steps:
1. Review generated configs
2. Apply to Kubernetes: kubectl apply -f plans/payment-gateway-api/
3. Start mirroring: python -m src.cli.main mirror payment-gateway-api
```

---

#### `validate`

Validate generated Gloo Gateway configurations.

**Syntax**:
```bash
python -m src.cli.main validate <api-name> [OPTIONS]
```

**Options**:
- `--config-dir <path>`: Configuration directory (default: `plans/<api-name>`)
- `--strict`: Enable strict validation
- `--kubernetes`: Validate against live Kubernetes cluster

**Examples**:

```bash
# Validate generated configs
python -m src.cli.main validate payment-gateway-api

# Strict validation with schema checks
python -m src.cli.main validate payment-gateway-api --strict

# Validate against Kubernetes cluster
python -m src.cli.main validate payment-gateway-api --kubernetes
```

**Output**:
```
✓ VirtualService: valid
✓ Upstream: valid
✓ AuthConfig: valid
✓ RateLimitConfig: valid

All configurations are valid!
```

---

### Migration Commands

#### `deploy`

Deploy Gloo Gateway configurations to Kubernetes.

**Syntax**:
```bash
python -m src.cli.main deploy <api-name> [OPTIONS]
```

**Options**:
- `--config-dir <path>`: Configuration directory
- `--namespace <name>`: Kubernetes namespace (default: `gloo-system`)
- `--dry-run`: Show kubectl commands without executing
- `--wait`: Wait for deployment to be ready

**Examples**:

```bash
# Deploy configurations
python -m src.cli.main deploy payment-gateway-api

# Deploy to custom namespace
python -m src.cli.main deploy payment-gateway-api --namespace gloo-prod

# Preview kubectl commands
python -m src.cli.main deploy payment-gateway-api --dry-run

# Deploy and wait for readiness
python -m src.cli.main deploy payment-gateway-api --wait
```

**Output**:
```
📦 Deploying payment-gateway-api to Kubernetes

Applying configurations:
✓ upstream.yaml applied
✓ virtualservice.yaml applied
✓ authconfig.yaml applied
✓ ratelimit.yaml applied

Verifying deployment:
✓ Upstream is ready
✓ VirtualService is accepted
✓ Gateway proxy updated

Deployment complete!
```

---

#### `mirror`

Start traffic mirroring to Gloo Gateway.

**Syntax**:
```bash
python -m src.cli.main mirror <api-name> [OPTIONS]
```

**Options**:
- `--duration <hours>`: Mirroring duration in hours (default: 24)
- `--percentage <num>`: Percentage of traffic to mirror (default: 100)
- `--compare`: Enable response comparison

**Examples**:

```bash
# Start 24-hour mirroring
python -m src.cli.main mirror payment-gateway-api

# Mirror for 48 hours
python -m src.cli.main mirror payment-gateway-api --duration 48

# Mirror 50% of traffic
python -m src.cli.main mirror payment-gateway-api --percentage 50

# Mirror with response comparison
python -m src.cli.main mirror payment-gateway-api --compare
```

**Output**:
```
🔍 Starting traffic mirroring for payment-gateway-api

Configuration:
  Duration: 24 hours
  Mirror percentage: 100%
  Response comparison: enabled

Status: MIRRORING
Started: 2026-02-06 10:30:00
Expected end: 2026-02-07 10:30:00

Monitor progress:
  python -m src.cli.main status payment-gateway-api
```

---

#### `shift`

Shift traffic to Gloo Gateway (canary rollout).

**Syntax**:
```bash
python -m src.cli.main shift <api-name> --to <percentage> [OPTIONS]
```

**Options**:
- `--to <percentage>`: Target traffic percentage (required)
- `--force`: Skip approval (use with caution)
- `--monitor-duration <minutes>`: Monitoring duration (default: 120)

**Examples**:

```bash
# Shift 10% traffic to Gloo
python -m src.cli.main shift payment-gateway-api --to 10

# Shift 50% with custom monitoring
python -m src.cli.main shift payment-gateway-api --to 50 --monitor-duration 240

# Force shift (skip approval)
python -m src.cli.main shift payment-gateway-api --to 100 --force
```

**Output**:
```
⚖️  Shifting traffic for payment-gateway-api

Current: 10% Gloo, 90% APIC
Target:  50% Gloo, 50% APIC

Approval required:
  Team lead must approve 50% shift
  Risk level: CRITICAL
  Recommendation: Monitor for 4 hours before next phase

Approve shift? (yes/no): yes

✓ Traffic shifted to 50%

Monitoring for 2 hours...
  Error rate: 0.34% (stable)
  Latency p95: 138ms (improved!)
  
Shift successful!
```

---

#### `rollback`

Rollback to legacy gateway (emergency).

**Syntax**:
```bash
python -m src.cli.main rollback <api-name> [OPTIONS]
```

**Options**:
- `--reason <text>`: Rollback reason (for audit log)
- `--confirm`: Skip confirmation prompt

**Examples**:

```bash
# Rollback with confirmation
python -m src.cli.main rollback payment-gateway-api

# Rollback with reason
python -m src.cli.main rollback payment-gateway-api --reason "High error rate detected"

# Emergency rollback (no confirmation)
python -m src.cli.main rollback payment-gateway-api --confirm
```

**Output**:
```
⚠️  ROLLBACK: payment-gateway-api

Current traffic: 50% Gloo, 50% APIC
After rollback: 0% Gloo, 100% APIC

Are you sure? (yes/no): yes

✓ Traffic rolled back to APIC
✓ Gloo Gateway disabled
✓ Audit log updated

Status: ROLLED_BACK
Reason: High error rate detected

Next steps:
1. Investigate root cause
2. Fix configuration issues
3. Retry migration when ready
```

---

### Monitoring Commands

#### `status`

Show migration status for API(s).

**Syntax**:
```bash
python -m src.cli.main status [<api-name>] [OPTIONS]
```

**Options**:
- `--watch`: Continuously monitor (refresh every 5s)
- `--detailed`: Show detailed metrics

**Examples**:

```bash
# Status of specific API
python -m src.cli.main status payment-gateway-api

# Status of all APIs
python -m src.cli.main status

# Continuously monitor
python -m src.cli.main status payment-gateway-api --watch

# Detailed metrics
python -m src.cli.main status payment-gateway-api --detailed
```

**Output (single API)**:
```
API: payment-gateway-api
Status: CANARY_50
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Traffic Distribution:
  Gloo Gateway: 50% (12,500 req/hour)
  APIC Legacy:  50% (12,500 req/hour)

Metrics (last hour):
  Total requests: 25,000
  Error rate: 0.34% (stable)
  Latency p50: 89ms
  Latency p95: 138ms
  Latency p99: 245ms

Health: ✓ HEALTHY

Started: 2026-02-06 08:00:00
Current phase: 50% (monitoring for 2h)
Next phase: 100% (after approval)
```

**Output (all APIs)**:
```
Migration Status Dashboard
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌────────────────────────┬──────────────┬──────────┬─────────────┐
│ API Name               │ Status       │ Traffic  │ Health      │
├────────────────────────┼──────────────┼──────────┼─────────────┤
│ payment-gateway-api    │ CANARY_50    │ 50%      │ ✓ HEALTHY   │
│ payment-refund-api     │ MIRRORING    │ 0%       │ ✓ HEALTHY   │
│ checkout-cart-api      │ PLANNED      │ N/A      │ N/A         │
│ payment-webhook-api    │ COMPLETED    │ 100%     │ ✓ HEALTHY   │
└────────────────────────┴──────────────┴──────────┴─────────────┘

Summary:
  Total: 18 APIs
  Completed: 5
  In Progress: 2
  Planned: 7
  Discovered: 4
```

---

#### `metrics`

Show detailed metrics for an API.

**Syntax**:
```bash
python -m src.cli.main metrics <api-name> [OPTIONS]
```

**Options**:
- `--window <duration>`: Time window (`1h`, `24h`, `7d`)
- `--export <format>`: Export to file (`csv`, `json`)

**Examples**:

```bash
# Last hour metrics
python -m src.cli.main metrics payment-gateway-api

# Last 24 hours
python -m src.cli.main metrics payment-gateway-api --window 24h

# Export to CSV
python -m src.cli.main metrics payment-gateway-api --export csv
```

**Output**:
```
Metrics: payment-gateway-api (Last 1 hour)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Traffic:
  Total requests: 25,000
  Successful: 24,915 (99.66%)
  Errors (4xx): 45 (0.18%)
  Errors (5xx): 40 (0.16%)

Latency (milliseconds):
  Min: 35ms
  Avg: 89ms
  P50: 85ms
  P95: 138ms
  P99: 245ms
  Max: 892ms

Comparison (Gloo vs APIC):
  Error rate: 0.34% vs 0.35% (✓ better)
  Latency p95: 138ms vs 145ms (✓ 5% faster)
  
Geographical:
  US-East: 15,000 req (60%)
  EU-West: 7,500 req (30%)
  Asia-Pacific: 2,500 req (10%)
```

---

### Administrative Commands

#### `locks`

Show active migration locks.

**Syntax**:
```bash
python -m src.cli.main locks [OPTIONS]
```

**Options**:
- `--team <name>`: Filter by team

**Examples**:

```bash
# Show all locks
python -m src.cli.main locks

# Show locks for specific team
python -m src.cli.main locks --team payments-team
```

**Output**:
```
Active Migration Locks
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌────────────────────────┬───────────────────┬─────────────┬──────────┐
│ API Name               │ Locked By         │ Team        │ Started  │
├────────────────────────┼───────────────────┼─────────────┼──────────┤
│ payment-gateway-api    │ alice@company.com │ payments    │ 2h ago   │
│ payment-refund-api     │ bob@company.com   │ payments    │ 30m ago  │
│ inventory-lookup-api   │ carol@company.com │ inventory   │ 5h ago   │
└────────────────────────┴───────────────────┴─────────────┴──────────┘
```

---

#### `unlock`

Release a migration lock (admin only).

**Syntax**:
```bash
python -m src.cli.main unlock <api-name> [OPTIONS]
```

**Options**:
- `--force`: Force unlock without confirmation

**Examples**:

```bash
# Unlock with confirmation
python -m src.cli.main unlock payment-gateway-api

# Force unlock
python -m src.cli.main unlock payment-gateway-api --force
```

---

#### `audit`

View audit logs.

**Syntax**:
```bash
python -m src.cli.main audit [OPTIONS]
```

**Options**:
- `--api <name>`: Filter by API name
- `--user <email>`: Filter by user
- `--action <type>`: Filter by action type
- `--today`: Show today's logs only
- `--since <date>`: Logs since date (YYYY-MM-DD)
- `--export <format>`: Export to file (`csv`, `json`)

**Examples**:

```bash
# View all audit logs
python -m src.cli.main audit

# Today's logs
python -m src.cli.main audit --today

# Logs for specific API
python -m src.cli.main audit --api payment-gateway-api

# Logs for specific user
python -m src.cli.main audit --user alice@company.com

# Logs since specific date
python -m src.cli.main audit --since 2026-02-01

# Export to CSV
python -m src.cli.main audit --export csv
```

**Output**:
```
Audit Logs
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

2026-02-06 14:32:15 | alice@company.com | payment-gateway-api | TRAFFIC_SHIFT
  Details: Shifted traffic to 50%
  Correlation ID: abc-123-def

2026-02-06 10:30:00 | alice@company.com | payment-gateway-api | START_MIRROR
  Details: Started traffic mirroring (24h)
  Correlation ID: xyz-789-uvw

2026-02-06 09:15:45 | bob@company.com | payment-refund-api | GENERATE_PLAN
  Details: Generated Gloo Gateway configuration
  Correlation ID: mno-456-pqr
```

---

#### `validate-config`

Validate configuration file.

**Syntax**:
```bash
python -m src.cli.main validate-config [OPTIONS]
```

**Options**:
- `--config-file <path>`: Config file path (default: `config.yaml`)

**Examples**:

```bash
# Validate default config
python -m src.cli.main validate-config

# Validate custom config
python -m src.cli.main validate-config --config-file custom.yaml
```

---

## Common Workflows

### Workflow 1: First-Time Migration

```bash
# 1. Discover APIs
python -m src.cli.main discover

# 2. List low-risk APIs
python -m src.cli.main list --risk LOW

# 3. Generate plan for low-risk API
python -m src.cli.main plan payment-webhook-api

# 4. Validate plan
python -m src.cli.main validate payment-webhook-api

# 5. Deploy to Kubernetes
python -m src.cli.main deploy payment-webhook-api

# 6. Start 24h mirroring
python -m src.cli.main mirror payment-webhook-api

# 7. Check status
python -m src.cli.main status payment-webhook-api --watch

# 8. Start canary rollout
python -m src.cli.main shift payment-webhook-api --to 10
python -m src.cli.main shift payment-webhook-api --to 50
python -m src.cli.main shift payment-webhook-api --to 100

# 9. Monitor metrics
python -m src.cli.main metrics payment-webhook-api

# 10. Mark as complete
python -m src.cli.main complete payment-webhook-api
```

### Workflow 2: Batch Migration

```bash
# Discover all APIs
python -m src.cli.main discover --batch

# Generate plans for all low-risk APIs
for api in $(python -m src.cli.main list --risk LOW --format json | jq -r '.[].name'); do
  python -m src.cli.main plan "$api"
done

# Deploy in batch
python -m src.cli.main deploy --all --risk LOW
```

### Workflow 3: Emergency Rollback

```bash
# Monitor API
python -m src.cli.main status payment-gateway-api

# If issues detected, rollback immediately
python -m src.cli.main rollback payment-gateway-api --confirm

# View audit log
python -m src.cli.main audit --api payment-gateway-api
```

---

## Exit Codes

- `0`: Success
- `1`: General error
- `2`: Invalid arguments
- `3`: Configuration error
- `4`: Connection error (database, Redis, APIC)
- `5`: Validation error
- `6`: Lock conflict
- `7`: Threshold exceeded (auto-rollback triggered)

---

## Related Documentation

- [Architecture](architecture.md)
- [Configuration Guide](configuration.md)
- [API Ownership Model](ownership.md)
- [Troubleshooting](troubleshooting.md)
