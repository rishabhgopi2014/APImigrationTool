# Configuration Guide

## Overview

The API Migration Orchestrator uses a YAML-based configuration system that allows each team to customize discovery settings, migration behavior, and system integration.

---

## Configuration File Structure

### Location

**Default**: `config.yaml` (create from `config.example.yaml`)

```bash
cp config.example.yaml config.yaml
```

### Full Configuration Template

```yaml
# ============================================================
# OWNERSHIP METADATA
# ============================================================
owner:
  team: "your-team-name"              # Required: Your team identifier
  domain: "your-domain"                # Required: Business domain
  contact: "team@company.com"          # Required: Team contact email
  component: "optional-component"      # Optional: Specific component

# ============================================================
# SELECTIVE DISCOVERY CONTROLS
# ============================================================
discovery:
  # IBM API Connect (APIC)
  apic:
    enabled: true                      # Enable/disable APIC discovery
    credentials:
      url: "https://apic.company.com"  # APIC server URL
      username: "${APIC_USERNAME}"     # Use env var (recommended)
      password: "${APIC_PASSWORD}"
    filters:
      - "payment-*"                    # Glob patterns to match
      - "checkout-*"
      - "*-gateway"
    exclude_patterns:
      - "*-internal-*"                 # Patterns to exclude
      - "*-deprecated-*"
      - "*-test-*"
    tags:
      - "payment"                      # Filter by APIC tags
      - "production"
    rate_limit:
      max_requests_per_second: 10      # Throttle APIC API calls

  # MuleSoft Anypoint Platform
  mulesoft:
    enabled: false
    credentials:
      url: "https://anypoint.mulesoft.com"
      username: "${MULESOFT_USERNAME}"
      password: "${MULESOFT_PASSWORD}"
    filters:
      - "Payment*"
      - "Checkout*"
    tags:
      - "payment-domain"

  # Apache Kafka
  kafka:
    enabled: false
    credentials:
      bootstrap_servers:
        - "kafka-1.company.com:9092"
        - "kafka-2.company.com:9092"
      security_protocol: "SASL_SSL"
      sasl_mechanism: "PLAIN"
      sasl_username: "${KAFKA_USERNAME}"
      sasl_password: "${KAFKA_PASSWORD}"
    topics:
      - "payment.events.*"             # Topic patterns
      - "checkout.transactions.*"
    consumer_groups:
      - "payment-*"

  # Swagger/OpenAPI Specs
  swagger:
    enabled: false
    credentials:
      url: "https://api-docs.company.com"
      token: "${SWAGGER_API_TOKEN}"
    filters:
      - "/payment-api/*"
      - "/checkout-api/*"

# ============================================================
# GLOO GATEWAY & PORTAL CONFIGURATION
# ============================================================
gloo:
  gateway:
    namespace: "gloo-system"           # Kubernetes namespace for Gloo
    cluster: "production-cluster"      # K8s cluster context name
    helm_release: "gloo"               # Helm release name
  portal:
    enabled: true
    url: "https://portal.gloo.company.com"
    namespace: "gloo-portal"

# ============================================================
# MIGRATION EXECUTION SETTINGS
# ============================================================
migration:
  traffic_shifting:
    phases: [5, 25, 50, 100]           # Traffic shift percentages
    approval_required: true             # Require approval per phase
    monitoring_duration:
      per_phase_minutes: 120            # Monitor each phase for 2h
      mirroring_hours: 24               # Mirror traffic for 24h

  rollback:
    auto_rollback_enabled: true
    error_threshold: 0.05               # Rollback if error rate > 5%
    latency_threshold_ms: 2000          # Rollback if p95 > 2000ms
    error_count_threshold: 100          # Rollback after 100 errors
    window_minutes: 5                   # Evaluation window

# ============================================================
# DATABASE & CACHE
# ============================================================
database:
  url: "${DATABASE_URL}"                # PostgreSQL connection string
  # Example: postgresql://user:pass@localhost:5432/api_migration
  pool_size: 10
  max_overflow: 20
  echo: false                           # Set to true for SQL debugging

redis:
  url: "${REDIS_URL}"                   # Redis connection string
  # Example: redis://localhost:6379/0
  lock_ttl_seconds: 3600                # Lock expiration (1 hour)
  key_prefix: "api_migration:"

# ============================================================
# LOGGING & OBSERVABILITY
# ============================================================
logging:
  level: "INFO"                         # DEBUG, INFO, WARNING, ERROR
  format: "json"                        # json or text
  correlation_id: true                  # Add correlation IDs
  output:
    console: true
    file: "logs/migration.log"
  rotation:
    max_bytes: 10485760                 # 10MB
    backup_count: 5

# ============================================================
# NOTIFICATION CHANNELS
# ============================================================
notifications:
  slack:
    enabled: true
    webhook_url: "${SLACK_WEBHOOK_URL}"
    channel: "#api-migrations"
    username: "Migration Bot"
    events:
      - migration_started
      - migration_completed
      - rollback_triggered
      - error_threshold_exceeded
  
  email:
    enabled: true
    smtp_server: "smtp.company.com"
    smtp_port: 587
    use_tls: true
    username: "${SMTP_USERNAME}"
    password: "${SMTP_PASSWORD}"
    from: "api-migration@company.com"
    to:
      - "team@company.com"
    events:
      - migration_completed
      - rollback_triggered

# ============================================================
# SECURITY
# ============================================================
security:
  api_key: "${API_KEY}"                 # For web dashboard authentication
  allowed_users:
    - "alice@company.com"
    - "bob@company.com"
  kubernetes:
    kubeconfig_path: "~/.kube/config"
    context: "production-cluster"
```

---

## Configuration Sections

### 1. Ownership Metadata

Identifies your team and domain for multi-tenant isolation.

```yaml
owner:
  team: "payments-team"
  domain: "payment-services"
  contact: "payments-team@company.com"
  component: "checkout"
```

**Fields**:
- `team`: Unique team identifier (lowercase, no spaces)
- `domain`: Business domain (e.g., "customer-management", "inventory")
- `contact`: Team email for lock conflicts and notifications
- `component`: Optional sub-component for large teams

**Usage**:
- All discovered APIs are tagged with team/domain
- Used for filtering APIs in multi-team environments
- Appears in audit logs and dashboards

---

### 2. Discovery Configuration

#### 2.1 APIC (IBM API Connect)

```yaml
discovery:
  apic:
    enabled: true
    credentials:
      url: "https://apic.company.com"
      username: "${APIC_USERNAME}"
      password: "${APIC_PASSWORD}"
    filters:
      - "payment-*"
      - "checkout-*"
    exclude_patterns:
      - "*-test-*"
    tags:
      - "payment"
    rate_limit:
      max_requests_per_second: 10
```

**Credential Fields**:
- `url`: APIC server URL (typically port 9444 for management API)
- `username`/`password`: APIC credentials (use environment variables)

**Filter Patterns**:
- Glob patterns to match API names
- `payment-*`: Matches `payment-gateway`, `payment-refund`, etc.
- `*-api`: Matches `customer-api`, `order-api`, etc.
- `checkout-*-api`: Matches `checkout-cart-api`, `checkout-billing-api`

**Exclude Patterns**:
- APIs to skip even if they match filters
- Common exclusions: `*-internal-*`, `*-test-*`, `*-deprecated-*`

**Tags**:
- Filter by APIC tags/labels
- Useful for environment-specific discovery (e.g., "production" tag)

**Rate Limiting**:
- Prevents overwhelming APIC with API calls
- Default: 10 requests/second

#### 2.2 MuleSoft

```yaml
discovery:
  mulesoft:
    enabled: true
    credentials:
      url: "https://anypoint.mulesoft.com"
      username: "${MULESOFT_USERNAME}"
      password: "${MULESOFT_PASSWORD}"
    filters:
      - "Payment*"
      - "Checkout*"
    tags:
      - "payment-domain"
```

**Note**: MuleSoft uses different naming conventions (often PascalCase)

#### 2.3 Kafka

```yaml
discovery:
  kafka:
    enabled: true
    credentials:
      bootstrap_servers:
        - "kafka-1.company.com:9092"
      security_protocol: "SASL_SSL"
      sasl_mechanism: "PLAIN"
      sasl_username: "${KAFKA_USERNAME}"
      sasl_password: "${KAFKA_PASSWORD}"
    topics:
      - "payment.events.*"
      - "checkout.transactions.*"
    consumer_groups:
      - "payment-*"
```

**Security Protocols**:
- `PLAINTEXT`: No encryption (dev only)
- `SSL`: TLS encryption
- `SASL_PLAINTEXT`: SASL auth, no encryption
- `SASL_SSL`: SASL auth + TLS (recommended)

**Topic Patterns**:
- Use wildcards: `payment.*`, `*.events`, `payment.*.v1`

#### 2.4 Swagger/OpenAPI

```yaml
discovery:
  swagger:
    enabled: true
    credentials:
      url: "https://api-docs.company.com"
      token: "${SWAGGER_API_TOKEN}"
    filters:
      - "/payment-api/*"
```

---

### 3. Gloo Gateway Configuration

```yaml
gloo:
  gateway:
    namespace: "gloo-system"
    cluster: "production-cluster"
    helm_release: "gloo"
  portal:
    enabled: true
    url: "https://portal.gloo.company.com"
    namespace: "gloo-portal"
```

**Gateway Fields**:
- `namespace`: Kubernetes namespace where Gloo is installed
- `cluster`: kubectl context name (from `~/.kube/config`)
- `helm_release`: Helm release name (for upgrades)

**Portal Fields**:
- `enabled`: Whether to publish APIs to Gloo Portal
- `url`: Portal developer URL
- `namespace`: Portal namespace (if separate from gateway)

---

### 4. Migration Settings

#### 4.1 Traffic Shifting

```yaml
migration:
  traffic_shifting:
    phases: [5, 25, 50, 100]
    approval_required: true
    monitoring_duration:
      per_phase_minutes: 120
      mirroring_hours: 24
```

**Phases**:
- List of traffic percentages for canary rollout
- Default: `[5, 25, 50, 100]`
- Conservative: `[1, 5, 10, 25, 50, 75, 100]`
- Aggressive: `[10, 50, 100]`

**Approval**:
- `true`: Require manual approval between phases
- `false`: Auto-proceed if metrics are healthy

**Monitoring Duration**:
- `per_phase_minutes`: How long to monitor each canary phase
- `mirroring_hours`: Duration of mirroring before first canary

#### 4.2 Rollback

```yaml
migration:
  rollback:
    auto_rollback_enabled: true
    error_threshold: 0.05
    latency_threshold_ms: 2000
    error_count_threshold: 100
    window_minutes: 5
```

**Thresholds**:
- `error_threshold`: Error rate (0.05 = 5%)
- `latency_threshold_ms`: P95 latency in milliseconds
- `error_count_threshold`: Absolute error count
- `window_minutes`: Time window for evaluation

**Example**: Rollback if error rate exceeds 5% within any 5-minute window

---

### 5. Database Configuration

```yaml
database:
  url: "${DATABASE_URL}"
  pool_size: 10
  max_overflow: 20
  echo: false
```

**Connection String Format**:
```
postgresql://username:password@host:port/database
```

**Example**:
```
postgresql://migration_user:secure_pass@db.company.com:5432/api_migration
```

**Pool Settings**:
- `pool_size`: Number of persistent connections
- `max_overflow`: Additional connections when pool is full
- `echo`: Log all SQL queries (for debugging)

---

### 6. Redis Configuration

```yaml
redis:
  url: "${REDIS_URL}"
  lock_ttl_seconds: 3600
  key_prefix: "api_migration:"
```

**Connection String Format**:
```
redis://host:port/db
redis://:password@host:port/db
```

**Lock TTL**:
- How long locks persist (auto-expire to prevent stale locks)
- Default: 3600 seconds (1 hour)

**Key Prefix**:
- Namespace for Redis keys
- Prevents conflicts with other applications using same Redis

---

### 7. Logging Configuration

```yaml
logging:
  level: "INFO"
  format: "json"
  correlation_id: true
  output:
    console: true
    file: "logs/migration.log"
  rotation:
    max_bytes: 10485760
    backup_count: 5
```

**Log Levels**:
- `DEBUG`: Very verbose (development)
- `INFO`: Standard (production)
- `WARNING`: Warnings and errors only
- `ERROR`: Errors only

**Log Formats**:
- `json`: Structured JSON (recommended for production)
- `text`: Human-readable (development)

**Rotation**:
- `max_bytes`: Max log file size (10MB default)
- `backup_count`: Number of old logs to keep

---

### 8. Notifications

#### Slack

```yaml
notifications:
  slack:
    enabled: true
    webhook_url: "${SLACK_WEBHOOK_URL}"
    channel: "#api-migrations"
    username: "Migration Bot"
    events:
      - migration_started
      - migration_completed
      - rollback_triggered
```

**Setup**:
1. Create Slack webhook: https://api.slack.com/messaging/webhooks
2. Set environment variable: `SLACK_WEBHOOK_URL`
3. Choose channel and events

**Events**:
- `migration_started`
- `migration_completed`
- `rollback_triggered`
- `error_threshold_exceeded`
- `canary_phase_completed`

#### Email

```yaml
notifications:
  email:
    enabled: true
    smtp_server: "smtp.company.com"
    smtp_port: 587
    use_tls: true
    username: "${SMTP_USERNAME}"
    password: "${SMTP_PASSWORD}"
    from: "api-migration@company.com"
    to:
      - "team@company.com"
```

---

## Environment Variables

### Required Variables

```bash
# APIC Credentials
export APIC_USERNAME="your-username"
export APIC_PASSWORD="your-password"

# Database
export DATABASE_URL="postgresql://user:pass@localhost:5432/api_migration"

# Redis
export REDIS_URL="redis://localhost:6379/0"
```

### Optional Variables

```bash
# MuleSoft
export MULESOFT_USERNAME="your-username"
export MULESOFT_PASSWORD="your-password"

# Kafka
export KAFKA_USERNAME="your-username"
export KAFKA_PASSWORD="your-password"

# Notifications
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/..."
export SMTP_USERNAME="smtp-user"
export SMTP_PASSWORD="smtp-password"

# API Security
export API_KEY="your-api-key"
```

### Using .env File

Create `.env` file (add to `.gitignore`):

```bash
# .env
APIC_USERNAME=your-username
APIC_PASSWORD=your-password
DATABASE_URL=postgresql://user:pass@localhost/api_migration
REDIS_URL=redis://localhost:6379/0
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

Load automatically:
```bash
# Python script loads .env
from dotenv import load_dotenv
load_dotenv()
```

---

## Configuration Examples

### Example 1: Payments Team

```yaml
owner:
  team: "payments-team"
  domain: "payment-services"
  contact: "payments@company.com"

discovery:
  apic:
    enabled: true
    filters:
      - "payment-*"
      - "checkout-*"
      - "billing-*"
    exclude_patterns:
      - "*-test-*"

migration:
  traffic_shifting:
    phases: [5, 25, 50, 100]
    approval_required: true
```

### Example 2: Inventory Team

```yaml
owner:
  team: "inventory-team"
  domain: "warehouse-operations"
  contact: "inventory@company.com"

discovery:
  apic:
    enabled: true
    filters:
      - "inventory-*"
      - "warehouse-*"
      - "stock-*"
  kafka:
    enabled: true
    topics:
      - "inventory.updates.*"
      - "warehouse.events.*"

migration:
  traffic_shifting:
    phases: [10, 50, 100]
    approval_required: false
```

### Example 3: Multi-Platform Team

```yaml
owner:
  team: "integration-team"
  domain: "integration-hub"
  contact: "integrations@company.com"

discovery:
  apic:
    enabled: true
    filters: ["integration-*"]
  mulesoft:
    enabled: true
    filters: ["Integration*"]
  swagger:
    enabled: true
    filters: ["/integration-api/*"]

migration:
  traffic_shifting:
    phases: [1, 5, 10, 25, 50, 75, 100]
    approval_required: true
    monitoring_duration:
      per_phase_minutes: 240
```

---

## Validation

### Validate Configuration

```bash
python -m src.cli.main validate-config

# Output:
# ✓ Configuration is valid!
# Owner:
#   Team: payments-team
#   Domain: payment-services
# Discovery:
#   APIC: enabled (3 filters)
#   Kafka: enabled (2 topics)
```

### Common Validation Errors

**Missing Required Fields**:
```
❌ Error: owner.team is required
```

**Invalid Filter Patterns**:
```
❌ Error: Filter pattern '*-payment-*-test' is too broad
```

**Database Connection Failed**:
```
❌ Error: Cannot connect to database: postgresql://localhost:5432/api_migration
   Check DATABASE_URL environment variable
```

---

## Configuration Best Practices

### 1. Use Environment Variables for Secrets

**❌ Bad**:
```yaml
apic:
  credentials:
    username: "admin"
    password: "secret123"
```

**✅ Good**:
```yaml
apic:
  credentials:
    username: "${APIC_USERNAME}"
    password: "${APIC_PASSWORD}"
```

### 2. Start with Conservative Settings

For first migration:
```yaml
migration:
  traffic_shifting:
    phases: [1, 5, 10, 25, 50, 100]
    approval_required: true
    monitoring_duration:
      per_phase_minutes: 240
  rollback:
    auto_rollback_enabled: true
    error_threshold: 0.01  # 1% (strict)
```

### 3. Use Specific Filters

**❌ Too broad**:
```yaml
filters:
  - "*"  # Matches everything!
```

**✅ Specific**:
```yaml
filters:
  - "payment-gateway-*"
  - "payment-refund-*"
  - "checkout-*-api"
```

### 4. Enable Notifications

```yaml
notifications:
  slack:
    enabled: true
  email:
    enabled: true
```

### 5. Use Version Control

- Commit `config.example.yaml` to git
- Add `config.yaml` to `.gitignore`
- Document team-specific config in README

---

## Troubleshooting

### Issue: "Cannot load configuration"

**Cause**: YAML syntax error

**Solution**:
```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('config.yaml'))"
```

### Issue: "Environment variable not set"

**Cause**: Missing env var (e.g., `${APIC_USERNAME}`)

**Solution**:
```bash
# Check if set
echo $APIC_USERNAME

# Set if missing
export APIC_USERNAME="your-username"
```

### Issue: "No APIs discovered"

**Cause**: Filters too restrictive

**Solution**:
```yaml
# Temporarily broaden filters
filters:
  - "payment-*"
  - "*-payment-*"  # Add variations
```

---

## Related Documentation

- [Architecture](architecture.md)
- [CLI Reference](cli-reference.md)
- [API Ownership Model](ownership.md)
- [Troubleshooting](troubleshooting.md)
