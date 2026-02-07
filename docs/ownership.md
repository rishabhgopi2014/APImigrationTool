# API Ownership Model

## Overview

The API Migration Orchestrator uses a **multi-tenant ownership model** to ensure that teams can independently migrate their APIs without conflicts or interference. This document explains how ownership works, team isolation mechanisms, and best practices for collaborative migrations.

---

## Core Concepts

### 1. Ownership Metadata

Every API in the system has associated ownership metadata:

```yaml
owner:
  team: "payments-team"           # Team identifier
  domain: "payment-services"      # Business domain
  contact: "payments@company.com" # Team contact
  component: "checkout"           # Optional: sub-component
```

**Fields**:
- **team**: Unique identifier for the team (e.g., `payments-team`, `inventory-team`)
- **domain**: Business domain or service area (e.g., `payment-services`, `warehouse-operations`)
- **contact**: Team email for notifications and conflict resolution
- **component**: Optional field for large teams managing multiple components

---

### 2. API Tagging

When APIs are discovered, they are automatically tagged with ownership information:

**Database Schema**:
```sql
CREATE TABLE apis (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    platform VARCHAR(50),
    team VARCHAR(100),              -- Ownership
    domain VARCHAR(100),             -- Ownership
    contact VARCHAR(255),            -- Ownership
    component VARCHAR(100),          -- Ownership
    risk_score DECIMAL(3,2),
    spec_json JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**Example**:
```json
{
  "name": "payment-gateway-api",
  "platform": "APIC",
  "team": "payments-team",
  "domain": "payment-services",
  "contact": "payments@company.com",
  "component": "checkout",
  "risk_score": 0.82
}
```

---

## Team Isolation Mechanisms

### 1. Discovery Filters

Each team configures filters to discover only their APIs.

**Example - Payments Team**:
```yaml
# config.yaml
owner:
  team: "payments-team"
  domain: "payment-services"

discovery:
  apic:
    enabled: true
    filters:
      - "payment-*"      # payment-gateway-api, payment-refund-api
      - "checkout-*"     # checkout-cart-api, checkout-billing-api
      - "billing-*"      # billing-invoice-api
```

**Example - Inventory Team**:
```yaml
# config.yaml
owner:
  team: "inventory-team"
  domain: "warehouse-operations"

discovery:
  apic:
    enabled: true
    filters:
      - "inventory-*"    # inventory-lookup-api, inventory-sync-api
      - "warehouse-*"    # warehouse-management-api
      - "stock-*"        # stock-allocation-api
```

**Result**: Each team only sees and manages their own APIs.

---

### 2. Database Filtering

All database queries are scoped to the team's ownership:

**Query Example**:
```python
# Fetch APIs for current team
def get_team_apis(team_name):
    return db.query(API).filter(
        API.team == team_name
    ).all()
```

**SQL**:
```sql
SELECT * FROM apis
WHERE team = 'payments-team';
```

**Result**: Teams cannot access or modify other teams' APIs.

---

### 3. Distributed Locking

**Purpose**: Prevent simultaneous migrations of the same API by multiple users.

#### How Locks Work

**Acquire Lock** (when migration starts):
```python
import redis

def acquire_lock(api_name, user_email):
    lock_key = f"lock:api:{api_name}"
    success = redis_client.set(
        lock_key,
        user_email,
        ex=3600,  # 1-hour expiration
        nx=True   # Only set if not exists
    )
    return success
```

**Check Lock** (before migration):
```python
def check_lock(api_name):
    lock_key = f"lock:api:{api_name}"
    locked_by = redis_client.get(lock_key)
    return locked_by  # Returns user email or None
```

**Release Lock** (after completion):
```python
def release_lock(api_name):
    lock_key = f"lock:api:{api_name}"
    redis_client.delete(lock_key)
```

#### Lock Scenarios

**Scenario 1: Successful Lock Acquisition**
```bash
# Alice starts migration
alice$ python -m src.cli.main migrate payment-gateway-api
🔒 Acquired lock for payment-gateway-api
✓ Starting migration...
```

**Scenario 2: Lock Conflict**
```bash
# Bob tries to migrate same API
bob$ python -m src.cli.main migrate payment-gateway-api
❌ Error: API locked by alice@company.com (started 30m ago)
   Contact: alice@company.com
   Team: payments-team
   
   Options:
   1. Wait for alice to complete
   2. Contact alice to coordinate
   3. Force unlock (admin only): unlock --force
```

**Scenario 3: Automatic Lock Expiration**
```bash
# Lock auto-expires after 1 hour (TTL)
# If alice's laptop crashes or network disconnects
# Bob can acquire lock after 1 hour
bob$ python -m src.cli.main migrate payment-gateway-api
🔒 Acquired lock for payment-gateway-api (previous lock expired)
```

#### Lock Management

**View Active Locks**:
```bash
python -m src.cli.main locks

# Output:
┌────────────────────────┬───────────────────┬─────────────┬──────────┐
│ API Name               │ Locked By         │ Team        │ Started  │
├────────────────────────┼───────────────────┼─────────────┼──────────┤
│ payment-gateway-api    │ alice@company.com │ payments    │ 30m ago  │
│ inventory-lookup-api   │ carol@company.com │ inventory   │ 2h ago   │
└────────────────────────┴───────────────────┴─────────────┴──────────┘
```

**Force Unlock** (admin only):
```bash
# If lock is stale (user left, forgot to unlock)
python -m src.cli.main unlock payment-gateway-api --force

# Output:
⚠️  Force unlocking payment-gateway-api
Previously locked by: alice@company.com
Are you sure? (yes/no): yes
✓ Lock released
✓ Audit log updated
```

---

### 4. Audit Trail

All actions are logged with team/user attribution.

**Audit Log Schema**:
```sql
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    user_email VARCHAR(255),
    team VARCHAR(100),
    api_name VARCHAR(255),
    action VARCHAR(100),
    details JSONB,
    correlation_id UUID
);
```

**Example Log Entry**:
```json
{
  "timestamp": "2026-02-06T14:32:15Z",
  "user_email": "alice@company.com",
  "team": "payments-team",
  "api_name": "payment-gateway-api",
  "action": "TRAFFIC_SHIFT",
  "details": {
    "from_percentage": 10,
    "to_percentage": 50,
    "risk_level": "CRITICAL"
  },
  "correlation_id": "abc-123-def-456"
}
```

**Query Audit Logs**:
```bash
# View team's audit trail
python -m src.cli.main audit --team payments-team

# View specific user's actions
python -m src.cli.main audit --user alice@company.com

# View specific API's history
python -m src.cli.main audit --api payment-gateway-api
```

---

## Multi-Team Scenarios

### Scenario 1: Separate Teams, Separate APIs

**Situation**: Two teams migrating completely different APIs.

**Teams**:
- **Payments Team**: Migrating `payment-*` APIs
- **Inventory Team**: Migrating `inventory-*` APIs

**Configuration**:

**Payments Team** (`config.yaml`):
```yaml
owner:
  team: "payments-team"
  domain: "payment-services"
  contact: "payments@company.com"

discovery:
  apic:
    filters: ["payment-*", "checkout-*"]
```

**Inventory Team** (`config.yaml`):
```yaml
owner:
  team: "inventory-team"
  domain: "warehouse-operations"
  contact: "inventory@company.com"

discovery:
  apic:
    filters: ["inventory-*", "warehouse-*"]
```

**Result**: Teams work independently without conflicts.

---

### Scenario 2: Same Team, Multiple Developers

**Situation**: Multiple developers on the same team migrating different APIs.

**Team**: Payments Team
**Developers**: Alice, Bob, Carol

**Process**:

**Alice**:
```bash
alice$ python -m src.cli.main discover  # Sees all payment-* APIs
alice$ python -m src.cli.main migrate payment-gateway-api
🔒 Acquired lock for payment-gateway-api
```

**Bob** (same team, different API):
```bash
bob$ python -m src.cli.main discover  # Sees same payment-* APIs
bob$ python -m src.cli.main migrate payment-refund-api
🔒 Acquired lock for payment-refund-api
✓ No conflict (different API)
```

**Carol** (tries same API as Alice):
```bash
carol$ python -m src.cli.main migrate payment-gateway-api
❌ Error: API locked by alice@company.com (started 1h ago)
   Team: payments-team
   Contact: alice@company.com
```

**Result**: Same-team developers can work on different APIs simultaneously, but not the same API.

---

### Scenario 3: Shared API (Cross-Team)

**Situation**: An API is used by multiple teams (rare but possible).

**API**: `shared-customer-profile-api`
**Teams**: Payments Team, Order Team

**Solution 1: Primary Ownership**
```yaml
# Assign primary ownership to one team
owner:
  team: "customer-team"
  domain: "customer-services"
  collaborators:
    - "payments-team"
    - "order-team"
```

**Solution 2: Coordination**
- Designate one team as migration lead
- Other teams provide input during planning phase
- Use approval gates to ensure cross-team sign-off

---

## Ownership Best Practices

### 1. Clear Ownership Assignment

**✅ Good**:
```yaml
owner:
  team: "payments-team"
  domain: "payment-services"
  contact: "payments@company.com"
```

**❌ Bad**:
```yaml
owner:
  team: "team1"  # Vague
  domain: "apis"  # Too broad
  contact: "admin@company.com"  # Generic
```

### 2. Specific Discovery Filters

**✅ Good**:
```yaml
filters:
  - "payment-gateway-*"
  - "payment-refund-*"
  - "checkout-*-api"
```

**❌ Bad**:
```yaml
filters:
  - "*"  # Matches everything!
  - "api-*"  # Too broad
```

### 3. Consistent Naming Conventions

**API Naming Standard**:
```
<domain>-<component>-<version>-api

Examples:
- payment-gateway-v2-api
- inventory-lookup-v1-api
- customer-profile-v3-api
```

**Benefits**:
- Easy to filter: `payment-*`
- Clear ownership: Domain prefix
- Version management: Explicit versioning

### 4. Team Communication

**Coordination Channels**:
- Team Slack channel: `#api-migrations`
- Regular standups to discuss progress
- Shared dashboard for visibility

**Before Starting**:
```bash
# Check active migrations
python -m src.cli.main locks

# Announce in Slack
"Starting migration of payment-gateway-api. ETA: 2 days"
```

### 5. Lock Hygiene

**Always Release Locks**:
```bash
# On successful completion
python -m src.cli.main complete payment-gateway-api

# On manual stop
python -m src.cli.main cancel payment-gateway-api
```

**Avoid Stale Locks**:
- Locks auto-expire after 1 hour
- Don't leave migrations unattended
- Communicate if you need to pause

---

## Conflict Resolution

### Lock Conflicts

**Problem**: Developer A has locked an API, Developer B needs to work on it.

**Resolution Steps**:

1. **Check Lock Status**:
   ```bash
   python -m src.cli.main locks
   ```

2. **Contact Lock Owner**:
   - Email listed in lock details
   - Team Slack channel

3. **Wait for Completion** or **Coordinate**:
   - Ask Developer A for ETA
   - Coordinate handoff if needed

4. **Force Unlock** (admin only, last resort):
   ```bash
   python -m src.cli.main unlock payment-gateway-api --force
   # Only if lock is truly stale (user unavailable, system error)
   ```

### Ownership Conflicts

**Problem**: Two teams both claim ownership of an API.

**Resolution Steps**:

1. **Review API Metadata**:
   ```bash
   python -m src.cli.main details shared-api
   ```

2. **Check Historical Ownership**:
   ```bash
   python -m src.cli.main audit --api shared-api
   ```

3. **Escalate to Management**:
   - Product owner decides primary ownership
   - Update config accordingly

4. **Document Decision**:
   ```yaml
   # config.yaml
   owner:
     team: "customer-team"  # Primary owner
     domain: "customer-services"
     collaborators:
       - "payments-team"
       - "order-team"
   ```

---

## API Ownership Transitions

### Transferring Ownership

**Scenario**: API ownership changes from Team A to Team B.

**Process**:

1. **Document Transfer**:
   ```sql
   UPDATE apis
   SET team = 'team-b', domain = 'new-domain', contact = 'teamb@company.com'
   WHERE name = 'transferred-api';
   ```

2. **Update Config** (Team B):
   ```yaml
   discovery:
     apic:
       filters:
         - "transferred-api"  # Add to Team B's filters
   ```

3. **Remove from Team A Config**:
   ```yaml
   discovery:
     apic:
       exclude_patterns:
         - "transferred-api"  # Exclude from Team A
   ```

4. **Audit Log Entry**:
   ```json
   {
     "action": "OWNERSHIP_TRANSFER",
     "details": {
       "api": "transferred-api",
       "from_team": "team-a",
       "to_team": "team-b",
       "approved_by": "manager@company.com"
     }
   }
   ```

---

## Monitoring & Reporting

### Team Dashboard

```bash
# View team's migration progress
python -m src.cli.main status --team payments-team

# Output:
Migration Dashboard - payments-team
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Total APIs: 15
  Completed: 5 (33%)
  In Progress: 2 (13%)
  Planned: 8 (54%)

Active Migrations:
  payment-gateway-api: CANARY_50 (alice@company.com)
  payment-refund-api: MIRRORING (bob@company.com)

Next Up (Risk Order):
  1. checkout-cart-api (LOW)
  2. billing-invoice-api (MEDIUM)
  3. payment-processor-api (CRITICAL)
```

### Cross-Team Visibility

**Platform Dashboard**:
```bash
# View all teams' progress (admin)
python -m src.cli.main status --all-teams

# Output:
Platform Migration Status
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

┌──────────────────┬───────┬───────────┬─────────────┬─────────┐
│ Team             │ Total │ Completed │ In Progress │ Planned │
├──────────────────┼───────┼───────────┼─────────────┼─────────┤
│ payments-team    │ 15    │ 5 (33%)   │ 2 (13%)     │ 8 (54%) │
│ inventory-team   │ 12    │ 8 (67%)   │ 1 (8%)      │ 3 (25%) │
│ customer-team    │ 20    │ 3 (15%)   │ 3 (15%)     │ 14 (70%)│
│ order-team       │ 18    │ 12 (67%)  │ 2 (11%)     │ 4 (22%) │
└──────────────────┴───────┴───────────┴─────────────┴─────────┘

Total Platform: 65 APIs
Completed: 28 (43%)
Target: 100% by Q2 2026
```

---

## Security Considerations

### Role-Based Access Control (RBAC)

**Roles**:
- **Developer**: Can migrate team's APIs
- **Team Lead**: Can approve high-risk migrations
- **Admin**: Can force-unlock, transfer ownership, view all teams

**Example RBAC Config**:
```yaml
security:
  rbac:
    teams:
      payments-team:
        developers:
          - alice@company.com
          - bob@company.com
        leads:
          - payments-lead@company.com
    admins:
      - platform-admin@company.com
```

### Audit & Compliance

**Audit Log Immutability**:
- Logs are append-only (cannot be deleted)
- Tampering detection with checksums
- Retention: 7 years (configurable)

**Compliance Reports**:
```bash
# Generate compliance report
python -m src.cli.main audit --export csv --since 2026-01-01

# Output: audit_2026-01-01_to_2026-02-06.csv
# Contains: timestamp, user, team, api, action, details
```

---

## Summary

**Key Ownership Principles**:

1. **Clear Ownership**: Every API has a single owning team
2. **Team Isolation**: Teams only see and manage their APIs
3. **Distributed Locking**: Prevents simultaneous migrations
4. **Audit Trail**: Full visibility into who did what
5. **Collaboration**: Teams can coordinate on shared APIs
6. **Self-Service**: Teams manage migrations independently
7. **Safety**: Locks and approval gates prevent conflicts

**Benefits**:
- ✅ Parallel migrations by multiple teams
- ✅ No conflicts or interference
- ✅ Full accountability and traceability
- ✅ Scalable to 1500+ APIs across 50+ teams

---

## Related Documentation

- [Architecture](architecture.md)
- [Configuration Guide](configuration.md)
- [CLI Reference](cli-reference.md)
- [Troubleshooting](troubleshooting.md)
