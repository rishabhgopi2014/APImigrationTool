# API Migration Orchestrator

**Enterprise-grade tool for safely migrating 1500+ APIs from legacy platforms (APIC, MuleSoft, Kafka, Swagger) to Gloo Gateway and Portal with zero-downtime, human oversight, and full rollback capabilities.**

## 🎯 Key Features

- **Multi-Tenant Architecture**: Each team migrates only their domain APIs with isolated state
- **Selective Discovery**: Enable/disable discovery per platform with granular filters
- **Zero-Downtime Migration**: Traffic mirroring → canary rollout (5% → 25% → 50% → 100%)
- **Human-in-the-Loop**: Approval gates at every phase with visual diff comparison
- **Automatic Rollback**: Rollback on error thresholds or manual trigger
- **Enterprise Scale**: Handles 1500+ APIs with batch processing and distributed locking
- **Full Auditability**: Immutable audit logs for compliance and troubleshooting

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Discovery Layer                          │
│  ┌──────┐  ┌─────────┐  ┌───────┐  ┌─────────┐            │
│  │ APIC │  │MuleSoft │  │ Kafka │  │ Swagger │            │
│  └──────┘  └─────────┘  └───────┘  └─────────┘            │
└─────────────────────────────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              Orchestration Engine                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │Inventory │  │Translator│  │Deployment│                 │
│  │ Manager  │  │  Engine  │  │Controller│                 │
│  └──────────┘  └──────────┘  └──────────┘                 │
└─────────────────────────────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              Traffic Management                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │
│  │Mirroring │  │  Canary  │  │ Rollback │                 │
│  │  Engine  │  │Controller│  │  Manager │                 │
│  └──────────┘  └──────────┘  └──────────┘                 │
└─────────────────────────────────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  Gloo Platform                              │
│    ┌──────────────────┐     ┌──────────────────┐           │
│    │  Gloo Gateway    │     │   Gloo Portal    │           │
│    └──────────────────┘     └──────────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- PostgreSQL 12+
- Redis 6+
- Kubernetes cluster with Gloo Gateway installed
- Access to legacy API platforms (APIC, MuleSoft, etc.)

### Installation

```bash
# Clone repository
git clone <repository-url>
cd APIMigration

# Install dependencies
pip install -r requirements.txt

# Set up database
psql -U postgres -f migrations/001_initial_schema.sql

# Copy and customize configuration
cp config.example.yaml config.yaml
# Edit config.yaml with your team's settings

# Set environment variables
export APIC_USERNAME=your_username
export APIC_PASSWORD=your_password
export DATABASE_URL=postgresql://user:pass@localhost:5432/api_migration
export REDIS_URL=redis://localhost:6379/0
```

### Configuration for Your Team

Edit `config.yaml` to specify:

1. **Ownership**: Your team name and domain
2. **Discovery Filters**: API patterns you want to migrate (e.g., `payment-*`)
3. **Portal Selection**: Enable only the portals you have access to

**Example Configurations for Different Teams**:

```yaml
# Customer Services Team
owner:
  team: "customer-services"
  domain: "customer-management"

discovery:
  apic:
    filters: ["customer-*", "profile-*", "account-*"]
    
# Inventory Team  
owner:
  team: "inventory-team"
  domain: "warehouse-operations"

discovery:
  apic:
    filters: ["inventory-*", "warehouse-*", "stock-*"]
  kafka:
    topics: ["inventory.updates.*", "warehouse.events.*"]
    
# Order Management Team
owner:
  team: "order-team"
  domain: "order-fulfillment"

discovery:
  apic:
    filters: ["order-*", "fulfillment-*", "shipping-*"]
```

## 📋 Usage

### 1. Discover Your APIs

```bash
# Discover APIs with automatic traffic analysis
python -m src.cli discover

# Example output:
# ✨ Discovered APIs for customer-services (Sorted by Risk)
# ┌──────────────────────┬──────────┬───────────┬─────────┬─────────┬──────┬──────────┬────────┐
# │ API Name             │ Platform │ Traffic   │ Error   │ Latency │ Risk │ Risk     │ Auth   │
# │                      │          │ (req/day) │ Rate    │ (ms)    │Score │ Level    │        │
# ├──────────────────────┼──────────┼───────────┼─────────┼─────────┼──────┼──────────┼────────┤
# │ customer-profile-api │ APIC     │ 2,500,000 │ 0.35%   │ 145     │ 0.82 │ CRITICAL │ OAuth  │
# │ account-api-v2       │ APIC     │ 850,000   │ 0.12%   │ 89      │ 0.56 │ HIGH     │ JWT    │
# │ customer-search      │ APIC     │ 120,000   │ 0.05%   │ 52      │ 0.32 │ MEDIUM   │ API Key│
# │ profile-batch        │ APIC     │ 8,500     │ 0.01%   │ 210     │ 0.15 │ LOW      │ None   │
# └──────────────────────┴──────────┴───────────┴─────────┴─────────┴──────┴──────────┴────────┘
#
# 📊 Risk Distribution:
#   CRITICAL:  1 API  - Migrate last with extensive mirroring
#   HIGH:      5 APIs - Conservative canary rollout
#   MEDIUM:   12 APIs - Standard migration process
#   LOW:       6 APIs - Fast-track candidates
#
# 💡 Migration Strategy:
#   • Start with LOW risk APIs to build confidence
#   • Migrate CRITICAL APIs last with extensive testing
```

### 2. Generate Migration Plan

```bash
# Generate Gloo Gateway configs for specific API
python -m src.cli plan --api payment-gateway-api

# Review generated configs
ls -la plans/payment-gateway-api/
# - virtual_service.yaml
# - route_table.yaml
# - auth_config.yaml
# - rate_limit_config.yaml
```

### 3. Validate Configs

```bash
# Validate against Gloo Gateway schemas
python -m src.cli validate --api payment-gateway-api

# Example output:
# ✓ VirtualService: valid
# ✓ RouteTable: valid
# ✓ AuthConfig: valid
# ✓ RateLimitConfig: valid
```

### 4. Deploy with Traffic Mirroring

```bash
# Deploy Gloo Gateway with 0% traffic (mirroring only)
python -m src.cli deploy --api payment-gateway-api --mirror

# Monitor comparison metrics
python -m src.cli status --api payment-gateway-api

# Example output:
# Traffic Mirroring Active (24h)
# - Requests mirrored: 1.2M
# - Latency diff: +12ms (p95)
# - Error rate: 0.01% vs 0.01% (legacy)
# - Payload mismatches: 3 (view details)
```

### 5. Gradual Traffic Shift

```bash
# Shift 5% of traffic to Gloo Gateway
python -m src.cli shift --api payment-gateway-api --phase 5%

# Requires approval in web dashboard
# Open: http://localhost:8080/approvals/payment-gateway-api

# After approval and monitoring, continue
python -m src.cli shift --api payment-gateway-api --phase 25%
python -m src.cli shift --api payment-gateway-api --phase 50%
python -m src.cli shift --api payment-gateway-api --phase 100%
```

### 6. Publish to Gloo Portal

```bash
# Publish migrated API to developer portal
python -m src.cli publish --api payment-gateway-api

# Notify developers
python -m src.cli notify --api payment-gateway-api
```

### 7. Rollback (if needed)

```bash
# Manual rollback to legacy gateway
python -m src.cli rollback --api payment-gateway-api

# Automatic rollback triggers on:
# - Error rate > 5% (configurable)
# - Latency > 2000ms p95 (configurable)
```

### 8. Web Dashboard

```bash
# Start web dashboard
python -m src.web.app

# Open browser: http://localhost:8080
# - View all migrations
# - Approve traffic shifts
# - Monitor metrics
# - View audit logs
# - Trigger rollbacks
```

## 🔒 Multi-Tenant Isolation

### How It Works

1. **Ownership Metadata**: Every API is tagged with team/domain from config
2. **Filtering**: You only see and migrate APIs matching your filters
3. **Distributed Locking**: Redis locks prevent simultaneous migrations
4. **Conflict Detection**: Alerts if you try to migrate an API another team is working on

### Example Scenario

**Payments Team** migrates `payment-gateway-api`:
```bash
# In team 1 terminal
payments-team$ python -m src.cli deploy --api payment-gateway-api
🔒 Acquired lock for payment-gateway-api
✓ Deploying...
```

**Checkout Team** tries to migrate the same API:
```bash
# In team 2 terminal
checkout-team$ python -m src.cli deploy --api payment-gateway-api
❌ Error: API locked by payments-team (started 5m ago)
   Contact: payments-team@company.com
```

## 📊 Monitoring & Observability

### Metrics Tracked

- **Traffic Metrics**: Requests/sec, error rates, latency percentiles
- **Comparison Metrics**: Legacy vs Gloo Gateway performance
- **Migration Progress**: APIs per phase (discovered → migrated → decommissioned)
- **Team Metrics**: Progress per team/domain

### Alerting

Automatic alerts on:
- Error rate threshold breach (default 5%)
- Latency degradation (default 2000ms p95)
- Payload mismatches during mirroring
- Migration stalls (no progress in 24h)

### Audit Logs

Every action is logged with:
- Timestamp
- User/team
- API affected
- Action (deploy, shift, rollback)
- Correlation ID for tracing

## 🧪 Testing

```bash
# Run unit tests
pytest tests/unit/

# Run integration tests
pytest tests/integration/

# Run end-to-end tests (requires test cluster)
pytest tests/e2e/
```

## 📚 Documentation

- [Architecture](docs/architecture.md)
- [Configuration Guide](docs/configuration.md)
- [CLI Reference](docs/cli-reference.md)
- [API Ownership Model](docs/ownership.md)
- [Troubleshooting](docs/troubleshooting.md)

## 🛠️ Advanced Usage

### Batch Operations

```bash
# Discover all APIs for your domain
python -m src.cli discover --batch

# Generate plans for all discovered APIs
python -m src.cli plan --all

# Deploy all low-risk APIs
python -m src.cli deploy --risk low --batch
```

### Custom Traffic Shift Phases

```yaml
# In config.yaml
migration:
  traffic_shifting:
    phases: [1, 5, 10, 25, 50, 75, 100]  # More granular
```

### Dry Run Mode

```bash
# Preview changes without executing
python -m src.cli deploy --api payment-gateway-api --dry-run
```

## 🤝 Support

- **Slack**: #api-migration-support
- **Email**: api-platform-team@company.com
- **Issues**: Internal JIRA project

## 📄 License

Internal use only - Company Proprietary
