# Architecture Documentation

## Overview

The **API Migration Orchestrator** is an enterprise-grade tool designed to safely migrate 1500+ APIs from legacy platforms (APIC, MuleSoft, Kafka, Swagger) to Gloo Gateway and Portal with zero-downtime, human oversight, and full rollback capabilities.

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Discovery Layer                                   │
│  ┌──────────┐  ┌─────────────┐  ┌────────┐  ┌──────────────┐       │
│  │  APIC    │  │  MuleSoft   │  │ Kafka  │  │   Swagger    │       │
│  │Connector │  │  Connector  │  │Connector│  │  Connector   │       │
│  └──────────┘  └─────────────┘  └────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Orchestration Engine                              │
│   ┌────────────┐  ┌───────────┐  ┌─────────────┐  ┌─────────┐     │
│   │ Inventory  │  │Translator │  │ Deployment  │  │  State  │     │
│   │  Manager   │  │  Engine   │  │ Controller  │  │ Manager │     │
│   └────────────┘  └───────────┘  └─────────────┘  └─────────┘     │
└─────────────────────────────────────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  Traffic Management Layer                            │
│   ┌────────────┐  ┌──────────┐  ┌───────────┐  ┌────────────┐     │
│   │ Mirroring  │  │  Canary  │  │ Rollback  │  │  Metrics   │     │
│   │   Engine   │  │Controller│  │  Manager  │  │ Collector  │     │
│   └────────────┘  └──────────┘  └───────────┘  └────────────┘     │
└─────────────────────────────────────────────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     Gloo Platform                                    │
│      ┌──────────────────┐          ┌──────────────────┐            │
│      │  Gloo Gateway    │          │   Gloo Portal    │            │
│      │  (Kubernetes)    │          │  (Developer Hub) │            │
│      └──────────────────┘          └──────────────────┘            │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. Discovery Layer

The Discovery Layer connects to multiple source platforms to identify APIs that need migration.

#### Connectors

**a) APIC Connector** (`src/connectors/apic_connector.py`)
- Connects to IBM API Connect via REST API
- Discovers APIs, products, catalogs, and plans
- Extracts API specifications (OpenAPI/Swagger)
- Retrieves authentication configurations (OAuth, API Key, JWT)
- Fetches rate limiting policies
- Collects traffic metrics and analytics

**b) MuleSoft Connector** (`src/connectors/mulesoft_connector.py`)
- Integrates with Anypoint Platform API
- Discovers APIs from Exchange
- Extracts RAML/OAS specifications
- Retrieves policies and SLA tiers

**c) Kafka Connector** (`src/connectors/kafka_connector.py`)
- Connects to Kafka clusters
- Discovers topics and consumer groups
- Maps Kafka topics to REST API endpoints
- Extracts schema registry information

**d) Swagger Connector** (`src/connectors/swagger_connector.py`)
- Reads OpenAPI/Swagger specifications
- Supports file-based and URL-based discovery
- Validates spec versions (2.0, 3.0, 3.1)

#### Discovery Process

1. **Authentication**: Connect using credentials from configuration
2. **Filtering**: Apply team-specific filters (e.g., `payment-*`)
3. **Extraction**: Pull API metadata and specifications
4. **Normalization**: Convert to unified internal format
5. **Storage**: Store in database with ownership tags

---

### 2. Inventory Manager

**Location**: `src/inventory/`

Manages the catalog of discovered APIs with risk assessment.

#### Risk Scoring Algorithm (`risk_scorer.py`)

**Risk Score Calculation**:
```python
risk_score = (
    traffic_factor * 0.4 +
    complexity_factor * 0.3 +
    error_rate_factor * 0.2 +
    dependency_factor * 0.1
)
```

**Factors**:
- **Traffic Factor**: Based on requests/day
  - < 10K: 0.1 (LOW)
  - 10K-100K: 0.3 (MEDIUM)
  - 100K-1M: 0.6 (HIGH)
  - > 1M: 0.9 (CRITICAL)

- **Complexity Factor**: Based on:
  - Number of endpoints
  - Authentication types (None=0.1, API Key=0.3, OAuth=0.7)
  - Number of integrations

- **Error Rate Factor**: Current production error rate
  - < 0.1%: 0.1
  - 0.1%-1%: 0.5
  - > 1%: 0.9

- **Dependency Factor**: Number of downstream dependencies

**Risk Levels**:
- **LOW**: 0.0 - 0.3 → Fast-track migration
- **MEDIUM**: 0.3 - 0.6 → Standard process
- **HIGH**: 0.6 - 0.8 → Conservative approach
- **CRITICAL**: 0.8 - 1.0 → Extensive testing required

---

### 3. Translator Engine

**Location**: `src/translator/`

Converts legacy API configurations to Gloo Gateway resources.

#### Gloo Generator (`gloo_generator.py`)

Generates Kubernetes YAML resources:

**a) VirtualService** - Routing configuration
```yaml
apiVersion: gateway.solo.io/v1
kind: VirtualService
metadata:
  name: <api-name>-vs
  namespace: gloo-system
spec:
  virtualHost:
    domains:
      - <api-domain>
    routes:
      - matchers:
          - prefix: <base-path>
        routeAction:
          single:
            upstream:
              name: <api-name>-upstream
```

**b) Upstream** - Backend target
```yaml
apiVersion: gloo.solo.io/v1
kind: Upstream
metadata:
  name: <api-name>-upstream
  namespace: gloo-system
spec:
  static:
    hosts:
      - addr: <backend-host>
        port: <backend-port>
  sslConfig:
    sni: <backend-sni>
```

**c) AuthConfig** - Authentication policies
```yaml
apiVersion: enterprise.gloo.solo.io/v1
kind: AuthConfig
metadata:
  name: <api-name>-auth
  namespace: gloo-system
spec:
  configs:
    - oauth2:
        oidcAuthorizationCode:
          appUrl: <app-url>
          clientId: <client-id>
          issuerUrl: <issuer-url>
```

**d) RateLimitConfig** - Rate limiting rules
```yaml
apiVersion: ratelimit.solo.io/v1alpha1
kind: RateLimitConfig
metadata:
  name: <api-name>-ratelimit
  namespace: gloo-system
spec:
  raw:
    descriptors:
      - key: generic_key
        rateLimit:
          requestsPerUnit: <rpm>
          unit: MINUTE
```

#### Conversion Logic

1. **Path Translation**: APIC base path → Gloo matcher
2. **Auth Mapping**: APIC OAuth → Gloo AuthConfig
3. **Rate Limit Conversion**: APIC rate plans → Gloo RateLimitConfig
4. **Header Transformation**: APIC header manipulation → Gloo transformations
5. **Response Caching**: APIC caching → Gloo caching policies

---

### 4. State Manager

**Location**: `src/state/`

Manages migration state with persistence and distributed locking.

#### Database Schema (`migrations/001_initial_schema.sql`)

**Tables**:

**a) `apis`** - Discovered APIs
```sql
CREATE TABLE apis (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    platform VARCHAR(50),
    team VARCHAR(100),
    domain VARCHAR(100),
    risk_score DECIMAL(3,2),
    risk_level VARCHAR(20),
    traffic_per_day INTEGER,
    error_rate DECIMAL(5,2),
    spec_json JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**b) `migrations`** - Migration tracking
```sql
CREATE TABLE migrations (
    id SERIAL PRIMARY KEY,
    api_id INTEGER REFERENCES apis(id),
    status VARCHAR(50),
    traffic_percentage INTEGER DEFAULT 0,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    locked_by VARCHAR(255),
    lock_expires_at TIMESTAMP
);
```

**c) `audit_logs`** - Immutable audit trail
```sql
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT NOW(),
    user_email VARCHAR(255),
    api_name VARCHAR(255),
    action VARCHAR(100),
    details JSONB,
    correlation_id UUID
);
```

#### Distributed Locking (Redis)

**Lock Mechanism**:
```python
# Acquire lock
redis.set(f"lock:api:{api_name}", user_email, ex=3600)

# Check lock
locked_by = redis.get(f"lock:api:{api_name}")

# Release lock
redis.delete(f"lock:api:{api_name}")
```

**Lock Features**:
- 1-hour TTL (auto-expires to prevent stale locks)
- Force-release with admin approval
- Lock ownership tracking (who, when)

---

### 5. Traffic Management

Handles progressive traffic shifting with safety mechanisms.

#### Mirroring Engine

**Purpose**: Duplicate traffic to Gloo without affecting users

**Process**:
1. Configure Envoy shadow traffic
2. Send 100% traffic to APIC (production)
3. Send copy to Gloo Gateway (shadow)
4. Compare responses (latency, status, body)
5. Log mismatches for investigation

**Configuration**:
```yaml
routes:
  - matchers:
      - prefix: /api
    routeAction:
      single:
        upstream:
          name: apic-upstream
    options:
      shadowing:
        upstream:
          name: gloo-upstream
        percentage: 100
```

#### Canary Controller

**Canary Phases**: 5% → 25% → 50% → 100%

**Weighted Routing**:
```yaml
routes:
  - matchers:
      - prefix: /api
    routeAction:
      multi:
        destinations:
          - destination:
              upstream:
                name: gloo-upstream
            weight: 50  # 50% to Gloo
          - destination:
              upstream:
                name: apic-upstream
            weight: 50  # 50% to APIC
```

#### Rollback Manager

**Auto-Rollback Triggers**:
- Error rate > 5% (configurable)
- Latency p95 > 2000ms (configurable)
- Manual trigger via CLI/Dashboard

**Rollback Process**:
1. Detect threshold breach
2. Log incident to audit trail
3. Shift 100% traffic back to APIC
4. Update migration status to `ROLLED_BACK`
5. Send notifications (Slack, email)
6. Lock API for investigation

---

### 6. Multi-Tenant Architecture

Ensures team isolation and prevents conflicts.

#### Ownership Model

**Every API has**:
- `team`: Team name (e.g., "payments-team")
- `domain`: Business domain (e.g., "payment-services")
- `contact`: Team email

**Filter Enforcement**:
```yaml
# Team A config
discovery:
  apic:
    filters: ["payment-*", "checkout-*"]

# Team B config
discovery:
  apic:
    filters: ["inventory-*", "warehouse-*"]
```

**Database Filtering**:
```sql
SELECT * FROM apis
WHERE team = 'payments-team'
  AND name LIKE 'payment-%';
```

#### Conflict Prevention

**Distributed Locks** prevent simultaneous migrations:
- Team A migrates `payment-api` → Lock acquired
- Team B tries to migrate `payment-api` → Denied
- Error message: "API locked by alice@company.com (started 2h ago)"

---

### 7. Web Dashboard

**Location**: `src/web/`

Provides visual interface for migration management.

#### Backend API (`api.py`)

**FastAPI Endpoints**:
- `POST /api/discover` - Trigger discovery
- `GET /api/apis` - List discovered APIs
- `POST /api/plan` - Generate Gloo configs
- `POST /api/migrate/{name}/mirror` - Start mirroring
- `POST /api/migrate/{name}/shift` - Shift traffic
- `POST /api/migrate/{name}/rollback` - Rollback
- `GET /api/status` - Migration status
- `WS /ws/logs` - Real-time log streaming

#### Frontend (`static/index.html`)

**Vue.js Components**:
- Dashboard (stats, charts)
- API table (sortable, filterable)
- Migration controls (slider, buttons)
- Real-time logs (terminal view)
- Modal dialogs (API details, YAML configs)

---

## Data Flow

### Discovery Flow

```
1. User triggers discovery (CLI or Web)
2. Config loader reads config.yaml
3. Filter engine applies team-specific filters
4. Connectors fetch APIs from platforms
5. Risk scorer calculates risk levels
6. APIs stored in PostgreSQL with ownership tags
7. Results displayed to user (sorted by risk)
```

### Migration Flow

```
1. User selects API for migration
2. Translator generates Gloo YAML configs
3. User reviews and approves configs
4. Deployment controller applies to Kubernetes
5. Mirroring engine starts shadow traffic (24h)
6. User reviews mirroring results
7. Canary controller shifts traffic progressively
8. Metrics collector monitors error rates/latency
9. On success: Complete migration
   On failure: Auto-rollback to legacy
10. Audit logger records all actions
```

---

## Deployment Architecture

### Component Locations

**Migration Orchestrator** (This codebase):
- Location: Developer laptop, jump server, or CI/CD pipeline
- Purpose: Generate configs, monitor migrations
- Components: Python scripts, web dashboard, kubectl CLI

**Kubernetes Cluster**:
- Location: GKE, EKS, AKS, or on-premises
- Components: Gloo Gateway, VirtualServices, Upstreams, AuthConfigs

**Legacy APIC Server**:
- Location: Existing data center
- Status: Stays running during migration
- Role: Backend target during transition

### Network Flow

```
End Users → Gloo Gateway → APIC Backend
                ↓
        Migration Orchestrator
                ↓
        Kubernetes API (kubectl)
```

---

## Security Architecture

### Credential Management

**Environment Variables**:
```bash
APIC_USERNAME=<username>
APIC_PASSWORD=<password>
DATABASE_URL=postgresql://...
REDIS_URL=redis://...
```

**Best Practice**: Use secrets management (HashiCorp Vault, AWS Secrets Manager)

### RBAC (Kubernetes)

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: gloo-migration-admin
rules:
  - apiGroups: ["gateway.solo.io", "gloo.solo.io"]
    resources: ["virtualservices", "upstreams"]
    verbs: ["get", "list", "create", "update", "delete"]
```

### Audit Trail

**Immutable Logs**:
- Every action logged with timestamp
- User attribution (email)
- Correlation IDs for tracing
- Cannot be deleted or modified

---

## Scalability

### Horizontal Scaling

**Database**: PostgreSQL with read replicas
**Cache**: Redis cluster for distributed locking
**Web Dashboard**: Multiple FastAPI instances behind load balancer

### Batch Operations

**Bulk Discovery**:
```bash
python -m src.cli discover --batch
```

**Parallel Migrations**:
- Multiple APIs migrated simultaneously
- Coordinated via distributed locks
- Resource limits prevent overload

### Performance Optimization

**Discovery**: Rate limiting to avoid overwhelming APIC
**Translation**: Cached templates for common patterns
**Monitoring**: Aggregated metrics (not per-request)

---

## Observability

### Metrics Collected

**API Metrics**:
- Requests per second
- Error rates (4xx, 5xx)
- Latency (p50, p95, p99)
- Throughput (bytes/sec)

**Migration Metrics**:
- APIs per phase (discovered, planned, migrated)
- Success/failure rates
- Rollback frequency
- Time to complete

**System Metrics**:
- Database query times
- Redis operations
- Kubernetes API calls
- Connector latencies

### Logging

**Structured Logging** (JSON format):
```json
{
  "timestamp": "2026-02-06T10:30:00Z",
  "level": "INFO",
  "component": "translator",
  "api": "payment-gateway-api",
  "action": "generate_virtualservice",
  "correlation_id": "abc123",
  "user": "alice@company.com"
}
```

---

## Technology Stack

**Backend**:
- Python 3.9+
- FastAPI (REST API)
- SQLAlchemy (ORM)
- Alembic (migrations)
- Redis (caching, locking)
- PostgreSQL (database)

**Frontend**:
- Vue.js 3
- Tailwind CSS
- Chart.js (visualizations)
- WebSocket (real-time updates)

**Infrastructure**:
- Kubernetes
- Gloo Gateway
- Helm (deployments)
- kubectl (CLI)

---

## Key Design Principles

1. **Safety First**: Zero-downtime migrations with rollback capabilities
2. **Human-in-the-Loop**: Approval gates at critical phases
3. **Multi-Tenant**: Team isolation with distributed locking
4. **Auditability**: Immutable logs for compliance
5. **Scalability**: Handles 1500+ APIs with batch operations
6. **Flexibility**: Supports multiple source platforms
7. **Observability**: Rich metrics and logging

---

## Related Documentation

- [Configuration Guide](configuration.md)
- [CLI Reference](cli-reference.md)
- [API Ownership Model](ownership.md)
- [Troubleshooting](troubleshooting.md)
