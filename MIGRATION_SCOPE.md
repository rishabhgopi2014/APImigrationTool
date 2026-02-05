# 📦 APIC to Gloo Gateway - Complete Migration Scope

## Overview

This guide explains **what gets migrated** from IBM API Connect (APIC) to Gloo Gateway and how APIC concepts map to Gloo Gateway equivalents.

---

## TL;DR - What Migrates?

| APIC Component | Migrates to Gloo? | Gloo Equivalent | Migration Method |
|----------------|-------------------|-----------------|------------------|
| **APIs (routes, paths)** | ✅ Yes | VirtualService | **Automated** |
| **Backend URLs** | ✅ Yes | Upstream | **Automated** |
| **Authentication** | ✅ Yes | AuthConfig | **Automated** |
| **Rate Limiting** | ✅ Yes | RateLimitConfig | **Automated** |
| **Catalogs** | ⚠️ Partial | Gloo Portal API Products | **Manual** |
| **Collections** | ⚠️ Partial | Gloo Portal API Products | **Manual** |
| **Plans (pricing)** | ⚠️ Partial | Rate Limiting | **Manual** |
| **Applications (consumers)** | ⚠️ Partial | OAuth Clients / API Keys | **Manual** |
| **Subscriptions** | ⚠️ Partial | API Key Management | **Manual** |
| **Developer Portal** | ✅ Yes | Gloo Portal | **New Setup** |
| **Analytics** | ✅ Yes | Prometheus + Grafana | **New Setup** |
| **Policies (custom)** | ❌ No | Lua Scripts / Transformations | **Rewrite** |

---

## Detailed Migration Breakdown

### 1. **APIs (Routes & Endpoints)** ✅ **Fully Automated**

**APIC Concept:**
- API definitions with paths, methods, parameters
- OpenAPI/Swagger specs
- Request/response schemas

**Gloo Gateway Equivalent:**
- **VirtualService** - Defines routing rules, matchers, domains

**Migration:**
```
APIC API Definition
    ↓
GlooConfigGenerator.generate()
    ↓
VirtualService YAML
```

**What Gets Migrated:**
- ✅ Base path (e.g., `/customer/v1`)
- ✅ HTTP methods (GET, POST, PUT, DELETE)
- ✅ Path parameters and query strings
- ✅ Headers matching
- ✅ Domains/hosts

**Example:**
```yaml
# APIC: /customer/v1/preferences [GET, PUT]
# Becomes:
apiVersion: gateway.solo.io/v1
kind: VirtualService
spec:
  virtualHost:
    routes:
      - matchers:
          - prefix: /customer/v1/preferences
            methods: [GET, PUT]
```

---

### 2. **Backend Targets** ✅ **Fully Automated**

**APIC Concept:**
- Backend service URLs
- Load balancing across multiple backends
- Health checks

**Gloo Gateway Equivalent:**
- **Upstream** - Defines backend service location

**Migration:**
```
APIC Backend URL: https://legacy-api.company.com:8443
    ↓
GlooConfigGenerator._generate_upstream()
    ↓
Upstream YAML (static or Kubernetes service)
```

**What Gets Migrated:**
- ✅ Backend host/IP
- ✅ Backend port
- ✅ TLS/HTTPS configuration
- ⚠️ Load balancing (may need manual tuning)
- ⚠️ Health checks (add manually if needed)

**Example:**
```yaml
apiVersion: gloo.solo.io/v1
kind: Upstream
spec:
  static:
    hosts:
      - addr: legacy-api.company.com
        port: 8443
  sslConfig:
    sni: legacy-api.company.com
```

---

### 3. **Authentication** ✅ **Automated with Manual Secrets**

**APIC Concept:**
- OAuth 2.0 providers
- API Key validation
- JWT validation
- Basic Auth
- Mutual TLS

**Gloo Gateway Equivalent:**
- **AuthConfig** - Defines authentication policies

**Migration:**
```
APIC Auth Type: OAuth
    ↓
GlooConfigGenerator._generate_auth_config()
    ↓
AuthConfig YAML
```

**What Gets Migrated:**
- ✅ OAuth provider URL
- ✅ API Key header name
- ✅ JWT issuer/audience
- ✅ Basic auth configuration
- ⚠️ Client secrets (manual creation required)

**Manual Steps:**
```bash
# Create OAuth client secret
kubectl create secret generic oauth-client-secret \
  --from-literal=client-secret=<your-secret> \
  -n gloo-system

# Create API keys
kubectl create secret generic api-keys \
  --from-file=apikeys.txt \
  -n gloo-system
```

---

### 4. **Rate Limiting** ✅ **Automated**

**APIC Concept:**
- Plans with request quotas (e.g., 1000 req/min)
- Burst limits
- Usage tracking

**Gloo Gateway Equivalent:**
- **RateLimitConfig** - Defines rate limiting rules

**Migration:**
```
APIC Plan: 1000 req/min
    ↓
GlooConfigGenerator._generate_rate_limit_config()
    ↓
RateLimitConfig YAML
```

**What Gets Migrated:**
- ✅ Requests per unit (minute, hour, day)
- ✅ Rate limit descriptors
- ⚠️ Pricing tiers (not applicable in Gloo)

**Example:**
```yaml
apiVersion: ratelimit.solo.io/v1alpha1
kind: RateLimitConfig
spec:
  raw:
    setDescriptors:
      - rateLimit:
          requestsPerUnit: 1000
          unit: MINUTE
```

---

### 5. **Catalogs** ⚠️ **Manual Migration to Gloo Portal**

**APIC Concept:**
- Catalogs: Collections of API products for different environments (dev, test, prod)
- Visibility controls
- Lifecycle management

**Gloo Gateway Equivalent:**
- **Gloo Portal API Products** - Logical grouping of APIs

**Migration Strategy:**

#### **Option A: Flatten (Recommended for Simple Cases)**
- Don't migrate catalog structure
- Deploy all APIs to single Gloo Gateway instance
- Use Kubernetes namespaces for environment separation

```bash
# Production APIs
kubectl apply -f api1.yaml -n gloo-prod

# Staging APIs
kubectl apply -f api1.yaml -n gloo-staging
```

#### **Option B: Gloo Portal Products (For Developer Portal)**
```yaml
# Create API Product in Gloo Portal
apiVersion: portal.gloo.solo.io/v1beta1
kind: APIProduct
metadata:
  name: customer-apis-product
  namespace: gloo-system
spec:
  displayName: Customer APIs
  description: APIs for customer management
  apis:
    - apiVersion: gateway.solo.io/v1
      kind: VirtualService
      name: customer-preferences-api-vs
      namespace: gloo-system
    - apiVersion: gateway.solo.io/v1
      kind: VirtualService
      name: customer-profile-api-vs
      namespace: gloo-system
```

**Migration Steps:**
1. ❌ **No automated migration** - manual recreation
2. Identify APIC catalogs and their purposes
3. Decide if you need Gloo Portal products
4. Manually create API products in Gloo Portal
5. Group related APIs

---

### 6. **Collections** ⚠️ **Manual - Use Kubernetes Labels**

**APIC Concept:**
- Collections: Groupings of related APIs
- Tags and metadata

**Gloo Gateway Equivalent:**
- **Kubernetes Labels and Annotations**

**Migration Strategy:**

Add labels to VirtualServices:
```yaml
apiVersion: gateway.solo.io/v1
kind: VirtualService
metadata:
  name: customer-api-vs
  labels:
    collection: "customer-services"
    domain: "customer"
    team: "customer-team"
    criticality: "high"
```

Query by collection:
```bash
# Get all APIs in "customer-services" collection
kubectl get vs -l collection=customer-services -n gloo-system

# Get all high-criticality APIs
kubectl get vs -l criticality=high -n gloo-system
```

---

### 7. **Plans (Pricing/Tiers)** ⚠️ **Partial - Use Rate Limiting**

**APIC Concept:**
- Plans: Bronze (100 req/day), Silver (1000 req/day), Gold (10000 req/day)
- Billing integration
- Usage tracking

**Gloo Gateway Equivalent:**
- **RateLimitConfig** - Technical rate limiting only
- ❌ **No billing/pricing** - requires external system

**Migration Strategy:**

#### **Rate Limiting Only:**
```yaml
# Bronze Plan → 100 req/day
apiVersion: ratelimit.solo.io/v1alpha1
kind: RateLimitConfig
metadata:
  name: bronze-plan-rl
spec:
  raw:
    setDescriptors:
      - rateLimit:
          requestsPerUnit: 100
          unit: DAY
```

#### **Billing/Usage Tracking:**
- ❌ Not built into Gloo Gateway
- Use external solutions:
  - **Moesif** - API analytics and billing
  - **Kong Konnect** - Has billing features
  - **Custom solution** - Track in Prometheus + custom billing system

---

### 8. **Applications (Consumer Apps)** ⚠️ **Manual - Create OAuth Clients or API Keys**

**APIC Concept:**
- Applications: Represent consumer apps
- Credentials (client ID/secret, API keys)
- Subscriptions to APIs

**Gloo Gateway Equivalent:**
- **OAuth Clients** (for OAuth apps)
- **API Keys** (for API key apps)

**Migration Strategy:**

#### **For OAuth Applications:**
```bash
# Create OAuth client in your OAuth provider (e.g., Keycloak, Okta)
# Then reference in AuthConfig

kubectl create secret generic mobile-app-oauth \
  --from-literal=client-id=mobile-app-123 \
  --from-literal=client-secret=secret-xyz \
  -n gloo-system
```

#### **For API Key Applications:**
```bash
# Create API key secret
cat <<EOF > apikeys.txt
mobile-app-key-1
web-app-key-2
partner-app-key-3
EOF

kubectl create secret generic api-keys \
  --from-file=apikeys.txt \
  -n gloo-system
```

**Manual Work Required:**
1. Export application list from APIC
2. Recreate credentials in appropriate system (OAuth provider, API key store)
3. Notify app owners of new credentials
4. Update applications to use new auth endpoints

---

### 9. **Subscriptions** ⚠️ **Manual - Not Directly Supported**

**APIC Concept:**
- Subscriptions: Link between application and API
- Approval workflows
- Usage tracking per subscription

**Gloo Gateway Equivalent:**
- ❌ **No direct equivalent**
- **Workaround:** Use API keys with metadata

**Migration Strategy:**

#### **Option A: Simplify (Recommended)**
- Remove subscription model entirely
- Use API keys or OAuth tokens for access control
- All authenticated apps can access all APIs (or use scopes)

#### **Option B: Custom Implementation**
```yaml
# Use External Auth to implement custom subscription logic
apiVersion: enterprise.gloo.solo.io/v1
kind: AuthConfig
metadata:
  name: subscription-check
spec:
  configs:
    - extAuth:
        http:
          url: http://subscription-service.default.svc.cluster.local:8080/check
          # Custom service checks if app is subscribed to this API
```

---

### 10. **Developer Portal** ✅ **New Setup with Gloo Portal**

**APIC Concept:**
- Developer portal for API documentation
- Self-service registration
- API explorer
- Application management

**Gloo Gateway Equivalent:**
- **Gloo Portal** (Enterprise feature)

**Migration Strategy:**

#### **Install Gloo Portal:**
```bash
# Requires Gloo Enterprise license
helm install gloo-portal gloo-portal/gloo-portal \
  --namespace gloo-portal \
  --create-namespace
```

#### **Publish APIs:**
```yaml
apiVersion: portal.gloo.solo.io/v1beta1
kind: APIProduct
metadata:
  name: customer-apis
spec:
  displayName: Customer APIs
  description: APIs for customer management
  apis:
    - apiVersion: gateway.solo.io/v1
      kind: VirtualService
      name: customer-api-vs
```

#### **Create Documentation:**
```yaml
apiVersion: portal.gloo.solo.io/v1beta1
kind: APIDoc
metadata:
  name: customer-api-doc
spec:
  productName: customer-apis
  openApiSpec:
    # Import from APIC OpenAPI/Swagger spec
```

**Migration Steps:**
1. Export OpenAPI specs from APIC
2. Import into Gloo Portal
3. Configure portal theme/branding
4. Set up user registration (if needed)
5. Test API explorer functionality

---

### 11. **Analytics & Monitoring** ✅ **New Setup**

**APIC Concept:**
- Built-in analytics dashboard
- API usage metrics
- Performance monitoring

**Gloo Gateway Equivalent:**
- **Prometheus** - Metrics collection
- **Grafana** - Dashboards
- **Access Logs** - Request logging

**Migration Strategy:**

#### **Set Up Prometheus:**
```bash
# Gloo Gateway exposes Prometheus metrics by default
kubectl port-forward -n gloo-system deployment/gateway-proxy 9091:9091

# Scrape metrics
curl http://localhost:9091/metrics
```

#### **Key Metrics:**
- `envoy_http_downstream_rq_total` - Total requests
- `envoy_http_downstream_rq_xx` - Status codes (2xx, 4xx, 5xx)
- `envoy_http_downstream_rq_time` - Latency percentiles

#### **Set Up Grafana:**
```bash
# Install Grafana
helm install grafana grafana/grafana -n monitoring

# Import Gloo dashboards
# Available at: https://github.com/solo-io/gloo/tree/master/install/grafana
```

---

### 12. **Custom Policies (Transformations)** ❌ **Manual Rewrite**

**APIC Concept:**
- DataPower policies (XML transformations, custom logic)
- GatewayScript
- XSLT transformations

**Gloo Gateway Equivalent:**
- **Transformation API** - Request/response transformation
- **Lua Scripts** - Custom logic

**Migration Strategy:**

#### **Simple Transformations:**
```yaml
# Gloo Transformation example
apiVersion: gateway.solo.io/v1
kind: VirtualService
spec:
  virtualHost:
    routes:
      - matchers:
          - prefix: /api/v1
        routeAction:
          single:
            upstream:
              name: backend
        options:
          stagedTransformations:
            regular:
              requestTransforms:
                - requestTransformation:
                    transformationTemplate:
                      headers:
                        x-custom-header:
                          text: "added-by-gloo"
                      body:
                        text: '{"wrapped": {{ body }} }'
```

#### **Complex Logic:**
- ❌ DataPower GatewayScript **does not** directly translate
- Rewrite as:
  - **Lua scripts** in Envoy
  - **External service** called via ExtAuth or HTTP callout
  - **Sidecar** in Kubernetes

**Recommendation:**
- Simplify policies where possible
- Move business logic to backend services
- Use Gloo transformations for simple header/body changes

---

## Migration Checklist

### **Phase 1: Core API Migration** (Automated)
- [x] APIs → VirtualService
- [x] Backends → Upstream
- [x] Auth → AuthConfig
- [x] Rate Limits → RateLimitConfig

### **Phase 2: Developer Experience** (Manual)
- [ ] Catalogs → Gloo Portal API Products (if needed)
- [ ] OpenAPI specs → Gloo Portal APIDoc
- [ ] Developer portal → Gloo Portal setup

### **Phase 3: Consumer Management** (Manual)
- [ ] Applications → OAuth clients or API keys
- [ ] Credentials → Secret creation
- [ ] Notification → Inform app owners

### **Phase 4: Monitoring** (New Setup)
- [ ] Prometheus → Install and configure
- [ ] Grafana → Install dashboards
- [ ] Alerts → Configure alerting rules

### **Phase 5: Custom Logic** (Rewrite)
- [ ] Review APIC policies
- [ ] Identify critical transformations
- [ ] Reimplement in Gloo or backend

---

## What This Tool Migrates

**✅ Automated by This Tool:**
1. API routing rules (VirtualService)
2. Backend targets (Upstream)
3. Authentication configs (AuthConfig)
4. Rate limiting (RateLimitConfig)

**⚠️ Requires Manual Work:**
1. Catalogs/Collections → Organize with labels or Gloo Portal
2. Applications → Recreate OAuth clients/API keys
3. Developer portal → Set up Gloo Portal
4. Analytics → Configure Prometheus/Grafana

**❌ Not Migrated (Requires Alternatives):**
1. Pricing/billing → External system
2. Subscriptions → Simplify or custom implementation
3. Custom policies → Rewrite in Lua or external service

---

## Recommendation

### **Minimal Migration** (API Functionality Only)
**Migrate:** APIs, backends, auth, rate limiting  
**Skip:** Catalogs, portal, applications  
**Result:** APIs work, but no developer portal or subscription management

### **Full Migration** (Complete Experience)
**Migrate:** Everything  
**Includes:** Gloo Portal, Prometheus, OAuth server, custom policies  
**Result:** Feature parity with APIC

### **Recommended Approach** (Pragmatic)
**Phase 1:** Migrate APIs, auth, rate limiting (this tool handles it)  
**Phase 2:** Set up monitoring (Prometheus/Grafana)  
**Phase 3:** Set up Gloo Portal (if you have developer portal needs)  
**Phase 4:** Recreate applications/subscriptions (if needed)  
**Phase 5:** Rewrite custom policies (as needed)

---

## Next Steps

1. ✅ Use this tool to **migrate APIs** (automated)
2. ✅ Review what **manual migrations** you need
3. ✅ Decide if you need **Gloo Portal**
4. ✅ Plan **monitoring setup**
5. ✅ Identify **custom policies** to rewrite

**The tool gives you 80% automation for the core API migration. The remaining 20% depends on your specific needs for portals, billing, and custom logic.**
