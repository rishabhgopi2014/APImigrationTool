# Troubleshooting Guide

## Overview

This guide helps you diagnose and resolve common issues when using the API Migration Orchestrator. Issues are organized by category with symptoms, causes, and solutions.

---

## Table of Contents

1. [Discovery Issues](#discovery-issues)
2. [Configuration Problems](#configuration-problems)
3. [Database & Connection Issues](#database--connection-issues)
4. [Migration Failures](#migration-failures)
5. [Traffic Management Issues](#traffic-management-issues)
6. [Performance Problems](#performance-problems)
7. [Lock & Conflict Issues](#lock--conflict-issues)
8. [Kubernetes & Gloo Issues](#kubernetes--gloo-issues)
9. [Web Dashboard Issues](#web-dashboard-issues)
10. [Common Error Messages](#common-error-messages)

---

## Discovery Issues

### Issue: No APIs Discovered

**Symptoms**:
```bash
python -m src.cli.main discover
✨ Discovered 0 APIs for payments-team
```

**Possible Causes & Solutions**:

**1. Filters Too Restrictive**
```yaml
# config.yaml
discovery:
  apic:
    filters:
      - "payment-*"  # Maybe APIs don't start with "payment-"
```

**Solution**: Broaden filters temporarily
```bash
# Check what APIs exist in APIC
curl -u $APIC_USERNAME:$APIC_PASSWORD https://apic.company.com/api/catalogs

# Update config with correct patterns
filters:
  - "payment*"
  - "*payment*"
  - "checkout-*"
```

**2. Wrong APIC Credentials**
```bash
# Test credentials manually
curl -u $APIC_USERNAME:$APIC_PASSWORD https://apic.company.com/api/health

# If fails, check environment variables
echo $APIC_USERNAME
echo $APIC_PASSWORD
```

**Solution**: Set correct credentials
```bash
export APIC_USERNAME="correct-username"
export APIC_PASSWORD="correct-password"
```

**3. Network Connectivity**
```bash
# Test APIC connectivity
ping apic.company.com
curl -k https://apic.company.com:9444
```

**Solution**: Check firewall rules, VPN connection

**4. Wrong APIC URL**
```yaml
# config.yaml - Wrong
credentials:
  url: "https://apic.company.com"  # Missing port

# Correct
credentials:
  url: "https://apic.company.com:9444"
```

---

### Issue: "Connection Timeout" During Discovery

**Symptoms**:
```
Error: Connection timeout after 30 seconds
Failed to discover APIs from APIC
```

**Causes**:
1. APIC server slow/overloaded
2. Network latency
3. Rate limiting too aggressive

**Solutions**:

```yaml
# config.yaml - Increase timeout and reduce rate limit
discovery:
  apic:
    timeout_seconds: 120  # Increase from 30 to 120
    rate_limit:
      max_requests_per_second: 5  # Reduce from 10 to 5
```

---

### Issue: APIs Discovered But No Traffic Metrics

**Symptoms**:
```
API: payment-gateway-api
Traffic: N/A
Error Rate: N/A
Risk Score: UNKNOWN
```

**Causes**:
1. Using mock data (demo mode)
2. APIC analytics not enabled
3. Insufficient permissions

**Solutions**:

**Check if using mock data**:
```python
# src/connectors/apic_connector.py
# Look for USE_MOCK_DATA flag
```

**Enable real APIC connection**:
```yaml
# config.yaml
discovery:
  apic:
    enabled: true
    use_mock: false  # Ensure this is false
    credentials:
      url: "https://apic.company.com:9444"
      username: "${APIC_USERNAME}"
      password: "${APIC_PASSWORD}"
```

**Check APIC permissions**:
- APIC user needs analytics read permissions
- Contact APIC admin to grant access

---

## Configuration Problems

### Issue: "Configuration File Not Found"

**Symptoms**:
```bash
python -m src.cli.main discover
Error: Configuration file 'config.yaml' not found
```

**Solution**:
```bash
# Create config from example
cp config.example.yaml config.yaml

# Verify location
ls -la config.yaml

# Edit with your settings
nano config.yaml
```

---

### Issue: "Invalid YAML Syntax"

**Symptoms**:
```
Error: YAML parsing error at line 45
```

**Causes**: Incorrect indentation, missing quotes, special characters

**Solutions**:

**Validate YAML syntax**:
```bash
# Use Python to validate
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# Or online validator: https://www.yamllint.com/
```

**Common YAML mistakes**:

```yaml
# ❌ Wrong - Missing quotes for special chars
url: https://apic.company.com:9444

# ✅ Correct
url: "https://apic.company.com:9444"

# ❌ Wrong - Inconsistent indentation
discovery:
  apic:
   enabled: true  # 3 spaces
    filters:       # 4 spaces

# ✅ Correct - Consistent 2 spaces
discovery:
  apic:
    enabled: true
    filters:
```

---

### Issue: "Environment Variable Not Set"

**Symptoms**:
```
Error: APIC_USERNAME environment variable not set
```

**Solutions**:

**Windows (PowerShell)**:
```powershell
# Set for current session
$env:APIC_USERNAME = "your-username"
$env:APIC_PASSWORD = "your-password"

# Set permanently
[System.Environment]::SetEnvironmentVariable('APIC_USERNAME', 'your-username', 'User')
```

**Linux/Mac**:
```bash
# Set for current session
export APIC_USERNAME="your-username"
export APIC_PASSWORD="your-password"

# Set permanently (add to ~/.bashrc or ~/.zshrc)
echo 'export APIC_USERNAME="your-username"' >> ~/.bashrc
echo 'export APIC_PASSWORD="your-password"' >> ~/.bashrc
source ~/.bashrc
```

**Using .env file** (recommended):
```bash
# Create .env file
cat > .env << EOF
APIC_USERNAME=your-username
APIC_PASSWORD=your-password
DATABASE_URL=postgresql://user:pass@localhost:5432/api_migration
REDIS_URL=redis://localhost:6379/0
EOF

# Add to .gitignore
echo ".env" >> .gitignore

# Python automatically loads .env via python-dotenv
```

---

## Database & Connection Issues

### Issue: "Cannot Connect to Database"

**Symptoms**:
```
Error: could not connect to server: Connection refused
Is the server running on host "localhost" (::1) and accepting TCP/IP connections on port 5432?
```

**Solutions**:

**1. Check if PostgreSQL is running**:
```bash
# Linux/Mac
sudo systemctl status postgresql
# or
ps aux | grep postgres

# Windows
sc query postgresql-x64-14
```

**2. Start PostgreSQL**:
```bash
# Linux/Mac
sudo systemctl start postgresql

# Windows
net start postgresql-x64-14

# Docker
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=password postgres:14
```

**3. Verify connection string**:
```bash
# Test connection
psql "postgresql://user:pass@localhost:5432/api_migration"

# If fails, check:
echo $DATABASE_URL

# Format should be:
# postgresql://username:password@host:port/database
```

**4. Create database if missing**:
```bash
# Connect as postgres user
psql -U postgres

# Create database
CREATE DATABASE api_migration;

# Create user
CREATE USER migration_user WITH PASSWORD 'secure_password';

# Grant permissions
GRANT ALL PRIVILEGES ON DATABASE api_migration TO migration_user;
```

**5. Run migrations**:
```bash
# Apply database schema
psql -U migration_user -d api_migration -f migrations/001_initial_schema.sql
```

---

### Issue: "Redis Connection Failed"

**Symptoms**:
```
Error: Error 111 connecting to localhost:6379. Connection refused.
```

**Solutions**:

**1. Check if Redis is running**:
```bash
# Check process
ps aux | grep redis

# Test connection
redis-cli ping
# Should return: PONG
```

**2. Start Redis**:
```bash
# Linux/Mac
sudo systemctl start redis

# Windows (WSL)
redis-server

# Docker
docker run -d -p 6379:6379 redis:7
```

**3. Verify Redis URL**:
```bash
echo $REDIS_URL
# Should be: redis://localhost:6379/0

# Test connection
redis-cli -u $REDIS_URL ping
```

---

## Migration Failures

### Issue: "Migration Failed During Mirroring"

**Symptoms**:
```
Error: Mirroring failed for payment-gateway-api
Reason: High response mismatch rate (15%)
```

**Causes**:
1. APIC and Gloo return different responses
2. Timing issues (timestamp fields)
3. Backend differences

**Solutions**:

**1. Compare responses manually**:
```bash
# Request to APIC
curl -H "Authorization: Bearer $TOKEN" https://apic.company.com/api/v2/payments/123

# Request to Gloo
curl -H "Authorization: Bearer $TOKEN" https://gloo.company.com/api/v2/payments/123

# Use diff
diff apic_response.json gloo_response.json
```

**2. Exclude dynamic fields**:
```yaml
# config.yaml
migration:
  mirroring:
    exclude_fields:
      - "timestamp"
      - "request_id"
      - "server_time"
```

**3. Increase mismatch threshold**:
```yaml
migration:
  mirroring:
    mismatch_threshold: 0.20  # Allow 20% mismatch
```

---

### Issue: "Rollback Triggered Automatically"

**Symptoms**:
```
⚠️  AUTO-ROLLBACK: payment-gateway-api
Reason: Error rate exceeded threshold (6.2% > 5%)
```

**Causes**: Gloo Gateway misconfiguration or backend issues

**Solutions**:

**1. Check Gloo logs**:
```bash
kubectl logs -n gloo-system deployment/gateway-proxy --tail=100

# Look for errors
```

**2. Review error patterns**:
```bash
python -m src.cli.main metrics payment-gateway-api --errors

# Analyze common errors:
# - 502 Bad Gateway → Backend unreachable
# - 401 Unauthorized → Auth config issue
# - 500 Internal Server Error → Upstream error
```

**3. Fix configuration**:

**502 errors**:
```yaml
# upstream.yaml - Check backend host/port
spec:
  static:
    hosts:
      - addr: apic-gateway.company.com  # Verify correct
        port: 8443  # Verify correct port
```

**401 errors**:
```yaml
# authconfig.yaml - Verify OAuth settings
spec:
  configs:
    - oauth2:
        oidcAuthorizationCode:
          issuerUrl: "https://auth.company.com"  # Verify
          clientId: "correct-client-id"
          clientSecretRef:
            name: oauth-secret
            namespace: gloo-system
```

**4. Adjust rollback threshold**:
```yaml
# config.yaml - If errors are expected temporarily
migration:
  rollback:
    error_threshold: 0.10  # Increase to 10%
    window_minutes: 10  # Increase evaluation window
```

---

### Issue: "Traffic Not Shifting"

**Symptoms**:
```bash
python -m src.cli.main shift payment-api --to 50
✓ Command executed
# But traffic remains at 0%
```

**Solutions**:

**1. Check VirtualService**:
```bash
kubectl get virtualservice -n gloo-system payment-api-vs -o yaml

# Look for weightedDestinations
spec:
  virtualHost:
    routes:
      - matchers:
          - prefix: /api
        routeAction:
          multi:
            destinations:
              - destination:
                  upstream:
                    name: gloo-upstream
                weight: 50  # Should be 50
              - destination:
                  upstream:
                    name: apic-upstream
                weight: 50  # Should be 50
```

**2. Verify Upstreams are healthy**:
```bash
kubectl get upstream -n gloo-system

# Check status
kubectl describe upstream payment-api-upstream -n gloo-system

# Should show: Status: Accepted
```

**3. Test traffic manually**:
```bash
# Send requests and check which backend receives them
for i in {1..100}; do
  curl -s https://gloo.company.com/api/v2/test -H "X-Request-ID: $i"
done

# Check Gloo logs
kubectl logs -n gloo-system deployment/gateway-proxy | grep "upstream_cluster"
```

---

## Traffic Management Issues

### Issue: "High Latency After Migration"

**Symptoms**:
```
Before migration: p95=120ms
After migration:  p95=850ms
```

**Causes**:
1. Gloo Gateway not optimized
2. Network path longer
3. Missing caching

**Solutions**:

**1. Enable connection pooling**:
```yaml
# upstream.yaml
spec:
  static:
    hosts:
      - addr: backend.company.com
        port: 443
  connectionConfig:
    maxRequestsPerConnection: 100
    connectTimeout: 5s
```

**2. Enable caching**:
```yaml
# virtualservice.yaml
spec:
  virtualHost:
    routes:
      - matchers:
          - prefix: /api
        options:
          caching:
            cachingServiceRef:
              name: redis-cache
              namespace: gloo-system
            maxAge: 60s
```

**3. Check network path**:
```bash
# Trace route
traceroute backend.company.com

# Check DNS resolution time
dig backend.company.com
```

---

### Issue: "Canary Phase Stuck"

**Symptoms**:
```bash
python -m src.cli.main status payment-api
Status: CANARY_10 (stuck for 8 hours)
```

**Causes**: Waiting for approval or monitoring duration

**Solutions**:

**1. Check if approval required**:
```yaml
# config.yaml
migration:
  traffic_shifting:
    approval_required: true  # If true, must approve manually
```

**2. Approve next phase**:
```bash
python -m src.cli.main approve payment-api

# Or shift directly
python -m src.cli.main shift payment-api --to 50
```

**3. Check monitoring duration**:
```yaml
# config.yaml
migration:
  traffic_shifting:
    monitoring_duration:
      per_phase_minutes: 120  # 2 hours per phase
```

---

## Performance Problems

### Issue: "Discovery Takes Too Long"

**Symptoms**:
```bash
python -m src.cli.main discover
# Hangs for 10+ minutes
```

**Solutions**:

**1. Reduce rate limiting**:
```yaml
# config.yaml
discovery:
  apic:
    rate_limit:
      max_requests_per_second: 20  # Increase
```

**2. Use batch mode**:
```bash
python -m src.cli.main discover --batch --parallel=5
```

**3. Enable caching**:
```yaml
discovery:
  apic:
    cache_ttl_hours: 24  # Cache for 24 hours
```

---

### Issue: "Database Queries Slow"

**Symptoms**:
```bash
python -m src.cli.main list
# Takes 30+ seconds
```

**Solutions**:

**1. Add database indexes**:
```sql
CREATE INDEX idx_apis_team ON apis(team);
CREATE INDEX idx_apis_risk_level ON apis(risk_level);
CREATE INDEX idx_migrations_status ON migrations(status);
```

**2. Analyze slow queries**:
```bash
# Enable query logging
# postgresql.conf
log_min_duration_statement = 1000  # Log queries > 1s

# Check logs
tail -f /var/log/postgresql/postgresql-14-main.log
```

**3. Increase connection pool**:
```yaml
# config.yaml
database:
  pool_size: 20  # Increase from 10
  max_overflow: 40  # Increase from 20
```

---

## Lock & Conflict Issues

### Issue: "Cannot Acquire Lock"

**Symptoms**:
```
❌ Error: API locked by alice@company.com (started 2h ago)
```

**Solutions**:

**1. Contact lock owner**:
```bash
# Get lock details
python -m src.cli.main locks

# Email user listed in lock
```

**2. Wait for lock expiration**:
```
Locks auto-expire after 1 hour (default TTL)
```

**3. Force unlock** (admin only):
```bash
python -m src.cli.main unlock payment-api --force

# Requires admin approval
```

---

### Issue: "Stale Locks"

**Symptoms**:
```
API locked by alice@company.com (started 25h ago)
# Alice's laptop crashed yesterday
```

**Solutions**:

**Check Redis**:
```bash
redis-cli

# List all locks
KEYS lock:api:*

# Check specific lock
GET lock:api:payment-gateway-api

# Manual unlock
DEL lock:api:payment-gateway-api
```

**Adjust lock TTL**:
```yaml
# config.yaml
redis:
  lock_ttl_seconds: 1800  # 30 minutes instead of 1 hour
```

---

## Kubernetes & Gloo Issues

### Issue: "kubectl Command Not Found"

**Symptoms**:
```
Error: kubectl: command not found
```

**Solution**: Install kubectl
```bash
# Mac
brew install kubectl

# Linux
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Verify
kubectl version --client
```

---

### Issue: "Cannot Connect to Kubernetes Cluster"

**Symptoms**:
```
Error: The connection to the server localhost:8080 was refused
```

**Solutions**:

**1. Configure kubeconfig**:
```bash
# Check current context
kubectl config current-context

# Set context
kubectl config use-context production-cluster

# View config
kubectl config view
```

**2. For managed clusters (GKE, EKS, AKS)**:

```bash
# GKE
gcloud container clusters get-credentials gloo-cluster --zone us-central1-a

# EKS
aws eks update-kubeconfig --name gloo-cluster --region us-east-1

# AKS
az aks get-credentials --resource-group migration-rg --name gloo-cluster
```

---

### Issue: "VirtualService Not Accepted"

**Symptoms**:
```bash
kubectl get virtualservice -n gloo-system
NAME                  STATUS       REASON
payment-api-vs        Rejected     InvalidRouteAction
```

**Solutions**:

**1. Check VirtualService status**:
```bash
kubectl describe virtualservice payment-api-vs -n gloo-system

# Look for error message
```

**2. Validate YAML**:
```bash
kubectl apply -f virtualservice.yaml --dry-run=client -o yaml
```

**3. Common issues**:

**Missing upstream**:
```yaml
# Ensure upstream exists first
kubectl get upstream payment-api-upstream -n gloo-system

# If not, create it
kubectl apply -f upstream.yaml
```

**Invalid matcher**:
```yaml
# ❌ Wrong
matchers:
  - path: /api  # Should be prefix or exact

# ✅ Correct
matchers:
  - prefix: /api
```

---

## Web Dashboard Issues

### Issue: "Dashboard Not Loading"

**Symptoms**:
```
http://localhost:8000
# Browser shows "This site can't be reached"
```

**Solutions**:

**1. Check if server is running**:
```bash
# Look for uvicorn process
ps aux | grep uvicorn

# Check port
netstat -an | grep 8000  # Linux/Mac
netstat -an | findstr 8000  # Windows
```

**2. Start web server**:
```bash
# Windows
start_web.bat

# Linux/Mac
./start_web.sh

# Or manually
python -m uvicorn src.web.api:app --host 0.0.0.0 --port 8000
```

**3. Check server logs**:
```bash
# Look for errors in console output
# Common issues:
# - Port 8000 already in use
# - Import errors (missing dependencies)
# - Database connection failed
```

**4. Use different port**:
```bash
python -m uvicorn src.web.api:app --port 8001
# Open: http://localhost:8001
```

---

### Issue: "Dashboard Shows No Data"

**Symptoms**:
- Dashboard loads but shows 0 APIs
- Empty tables

**Solutions**:

**1. Discover APIs first**:
```bash
python -m src.cli.main discover
```

**2. Check API endpoint**:
```bash
# Test backend API
curl http://localhost:8000/api/apis

# Should return JSON array
```

**3. Check browser console**:
```
Open browser DevTools (F12)
Look for JavaScript errors or failed API calls
```

---

## Common Error Messages

### "FOREIGN KEY constraint failed"

**Cause**: Trying to create migration before API exists in database

**Solution**:
```bash
# Discover APIs first
python -m src.cli.main discover

# Then create migration
python -m src.cli.main plan payment-api
```

---

### "SSL: CERTIFICATE_VERIFY_FAILED"

**Cause**: APIC uses self-signed certificate

**Solution**:
```yaml
# config.yaml
discovery:
  apic:
    verify_ssl: false  # Only for dev/test environments
```

**Better solution** (production):
```bash
# Add APIC certificate to trusted store
# Or configure proper SSL certificates on APIC
```

---

### "permission denied"

**Cause**: Insufficient file permissions

**Solution**:
```bash
# Check file ownership
ls -la config.yaml

# Fix permissions
chmod 644 config.yaml
chown $USER:$USER config.yaml
```

---

### "ModuleNotFoundError: No module named 'X'"

**Cause**: Missing Python dependencies

**Solution**:
```bash
# Install all dependencies
pip install -r requirements.txt

# Or specific package
pip install <package-name>

# Verify installation
pip list | grep <package-name>
```

---

## Getting Help

### Enable Debug Logging

```yaml
# config.yaml
logging:
  level: "DEBUG"  # Change from INFO to DEBUG
  format: "text"  # Easier to read than JSON
```

```bash
# Run with verbose output
python -m src.cli.main discover --verbose
```

---

### Collect Diagnostic Information

```bash
# System info
python --version
kubectl version
redis-cli --version
psql --version

# Configuration
python -m src.cli.main validate-config

# Database connection
python -m src.cli.main test-db

# Redis connection
python -m src.cli.main test-redis

# Kubernetes connection
kubectl get nodes
```

---

### Export Logs

```bash
# Export CLI logs
python -m src.cli.main audit --export json > audit.json

# Export web dashboard logs
kubectl logs -n gloo-system deployment/gateway-proxy > gloo.log

# Export database state
pg_dump api_migration > backup.sql
```

---

## Escalation Path

1. **Check this troubleshooting guide**
2. **Review logs** (enable DEBUG logging)
3. **Check #api-migrations Slack channel** for similar issues
4. **Contact your team lead**
5. **Open ticket** with platform team

**Include in ticket**:
- Error message (full stack trace)
- Configuration (sanitized, no passwords)
- Steps to reproduce
- Environment (OS, Python version, etc.)
- Logs (last 100 lines)

---

## Related Documentation

- [Architecture](architecture.md)
- [Configuration Guide](configuration.md)
- [CLI Reference](cli-reference.md)
- [API Ownership Model](ownership.md)
