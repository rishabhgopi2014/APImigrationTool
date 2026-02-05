# 🔄 APIC to Gloo Gateway Conversion - Architecture Guide

## ❌ **NOT Using glooctl**

The tool does **NOT** use `glooctl` CLI. Instead, it uses **pure Python code** to generate Kubernetes YAML manifests directly.

### Why Not glooctl?

1. **Automation**: Python code can be automated, `glooctl` requires manual CLI execution
2. **Customization**: Full control over config generation logic
3. **Scale**: Can process 1500+ APIs programmatically
4. **Integration**: Works seamlessly with web dashboard and REST API

---

## ✅ **How It Actually Works**

### Architecture Overview

```
┌─────────────────┐
│  APIC API Data  │ (Discovery)
│  - Routes       │
│  - Auth         │
│  - Rate Limits  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  GlooConfig     │ (Translation Logic)
│  Generator      │
│  (Python)       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Kubernetes YAML │ (Output)
│ - VirtualService│
│ - Upstream      │
│ - AuthConfig    │
│ - RateLimitConf│
└─────────────────┘
         │
         ▼
┌─────────────────┐
│  kubectl apply  │ (Deployment)
└─────────────────┘
```

---

## 🔧 **Conversion Logic (Pure Python)**

### File: `src/translator/gloo_generator.py`

The entire conversion is in **one Python class**: `GlooConfigGenerator`

### Step 1: Input (APIC API Data)
```python
# What we get from APIC
api = DiscoveredAPI(
    name="payment-gateway-api",
    base_path="/payment/v1",
    auth_methods=["oauth", "api-key"],
    rate_limit=1000,  # requests/minute
    backend_host="legacy-apic-gateway.com"
)
```

### Step 2: Generate Gloo Configs
```python
generator = GlooConfigGenerator(namespace="gloo-system")
gloo_config = generator.generate(api, backend_host="legacy-apic-gateway.com")
```

### Step 3: Output (Kubernetes YAML)
```yaml
# VirtualService (Routing)
apiVersion: gateway.solo.io/v1
kind: VirtualService
metadata:
  name: payment-gateway-api-vs
  namespace: gloo-system
spec:
  virtualHost:
    domains:
      - 'api.company.com'
    routes:
      - matchers:
          - prefix: '/payment/v1'
        routeAction:
          single:
            upstream:
              name: payment-gateway-api-upstream
              namespace: gloo-system

---
# Upstream (Backend Target)
apiVersion: gloo.solo.io/v1
kind: Upstream
metadata:
  name: payment-gateway-api-upstream
  namespace: gloo-system
spec:
  static:
    hosts:
      - addr: legacy-apic-gateway.com
        port: 443

---
# AuthConfig (OAuth/API Key)
apiVersion: enterprise.gloo.solo.io/v1
kind: AuthConfig
metadata:
  name: payment-gateway-api-auth
  namespace: gloo-system
spec:
  configs:
    - oauth2:
        oidcAuthorizationCode:
          clientId: "client-id"
          clientSecretRef:
            name: oauth-secret
            namespace: gloo-system
```

---

## 📋 **Conversion Mapping**

### APIC Concept → Gloo Gateway Resource

| APIC Field | Gloo Gateway Resource | Details |
|------------|----------------------|---------|
| **API Base Path** | `VirtualService.routes.matchers.prefix` | URL routing |
| **Backend Host** | `Upstream.static.hosts.addr` | Target server |
| **OAuth Config** | `AuthConfig.oauth2` | Authentication |
| **API Key** | `AuthConfig.apiKey` | API key validation |
| **Rate Limit** | `RateLimitConfig.requests_per_unit` | Traffic throttling |
| **JWT** | `AuthConfig.jwt` | Token validation |
| **CORS** | `VirtualService.virtualHost.options.cors` | Cross-origin |

---

## 🔍 **Detailed Conversion Logic**

### 1. VirtualService Generation

**APIC Input:**
```json
{
  "name": "payment-gateway-api",
  "base_path": "/payment/v1",
  "endpoints": [
    {"path": "/transactions", "method": "POST"},
    {"path": "/refunds", "method": "POST"}
  ]
}
```

**Python Code:**
```python
def generate_virtual_service(self, api: DiscoveredAPI) -> Dict:
    return {
        "apiVersion": "gateway.solo.io/v1",
        "kind": "VirtualService",
        "metadata": {
            "name": f"{api.name}-vs",
            "namespace": self.namespace
        },
        "spec": {
            "virtualHost": {
                "domains": ["*"],
                "routes": [{
                    "matchers": [{
                        "prefix": api.base_path
                    }],
                    "routeAction": {
                        "single": {
                            "upstream": {
                                "name": f"{api.name}-upstream",
                                "namespace": self.namespace
                            }
                        }
                    }
                }]
            }
        }
    }
```

### 2. Upstream Generation

**Python Code:**
```python
def generate_upstream(self, api: DiscoveredAPI, backend_host: str) -> Dict:
    return {
        "apiVersion": "gloo.solo.io/v1",
        "kind": "Upstream",
        "metadata": {
            "name": f"{api.name}-upstream",
            "namespace": self.namespace
        },
        "spec": {
            "static": {
                "hosts": [{
                    "addr": backend_host,
                    "port": 443
                }]
            }
        }
    }
```

### 3. Auth Config Generation

**APIC Input:**
```json
{
  "auth_methods": ["oauth", "api-key"]
}
```

**Python Code:**
```python
def generate_auth_config(self, api: DiscoveredAPI) -> Dict:
    auth_configs = []
    
    if "oauth" in api.auth_methods:
        auth_configs.append({
            "oauth2": {
                "oidcAuthorizationCode": {
                    "clientId": "your-client-id",
                    "clientSecretRef": {
                        "name": "oauth-secret",
                        "namespace": self.namespace
                    }
                }
            }
        })
    
    if "api-key" in api.auth_methods:
        auth_configs.append({
            "apiKey": {
                "headerName": "X-API-Key"
            }
        })
    
    return {
        "apiVersion": "enterprise.gloo.solo.io/v1",
        "kind": "AuthConfig",
        "metadata": {
            "name": f"{api.name}-auth",
            "namespace": self.namespace
        },
        "spec": {
            "configs": auth_configs
        }
    }
```

### 4. Rate Limit Generation

**Python Code:**
```python
def generate_rate_limit_config(self, api: DiscoveredAPI) -> Dict:
    requests_per_minute = api.rate_limit or 1000
    
    return {
        "apiVersion": "ratelimit.solo.io/v1alpha1",
        "kind": "RateLimitConfig",
        "metadata": {
            "name": f"{api.name}-ratelimit",
            "namespace": self.namespace
        },
        "spec": {
            "raw": {
                "descriptors": [{
                    "key": "generic_key",
                    "value": "per_minute",
                    "rateLimit": {
                        "requestsPerUnit": requests_per_minute,
                        "unit": "MINUTE"
                    }
                }]
            }
        }
    }
```

---

## 🎯 **Complete Flow in Code**

### In the Dashboard (src/web/api.py)

```python
@app.post("/api/plan")
async def generate_migration_plan(request: MigrationPlanRequest):
    # 1. Find the API
    api_data = find_api_by_name(request.api_name)
    
    # 2. Create GlooConfigGenerator
    generator = GlooConfigGenerator(namespace="gloo-system")
    
    # 3. Generate all configs
    gloo_config = generator.generate(
        api=api_data,
        backend_host="legacy-apic-gateway.com"
    )
    
    # 4. Convert to YAML files
    yaml_files = gloo_config.to_yaml_files()
    # Returns:
    # {
    #   "virtualservice.yaml": "apiVersion: gateway...",
    #   "upstream.yaml": "apiVersion: gloo...",
    #   "authconfig.yaml": "apiVersion: enterprise...",
    #   "ratelimit.yaml": "apiVersion: ratelimit..."
    # }
    
    return {"configs": yaml_files}
```

---

## 📦 **Output Format**

The generator produces **4 YAML files**:

### 1. virtualservice.yaml
- **Purpose**: HTTP routing rules
- **Maps**: APIC base path → Gloo routes

### 2. upstream.yaml
- **Purpose**: Backend target definition
- **Maps**: APIC backend host → Gloo upstream

### 3. authconfig.yaml
- **Purpose**: Authentication/authorization
- **Maps**: APIC auth methods → Gloo auth policies

### 4. ratelimit.yaml
- **Purpose**: Traffic throttling
- **Maps**: APIC rate limits → Gloo rate limit config

---

## 🚀 **How to Deploy**

The generated YAML can be applied directly with kubectl:

```bash
# Copy YAML from dashboard or save to files
kubectl apply -f virtualservice.yaml
kubectl apply -f upstream.yaml
kubectl apply -f authconfig.yaml
kubectl apply -f ratelimit.yaml
```

No `glooctl` needed! Pure Kubernetes resources.

---

## 🔧 **Advantages of This Approach**

✅ **Programmatic**: Can process 1500+ APIs automatically
✅ **Repeatable**: Same input → same output
✅ **Testable**: Unit tests for conversion logic
✅ **Extensible**: Easy to add new transformations
✅ **Version Control**: YAML files can be committed to Git
✅ **CI/CD Ready**: Integrates with GitOps workflows

---

## 📝 **Key Files**

1. **Translator**: `src/translator/gloo_generator.py` (500+ lines)
   - Pure Python conversion logic
   - No external tools required

2. **Models**: `src/translator/gloo_generator.py` (GlooConfig class)
   - Dataclass for typed configs
   - YAML serialization

3. **API**: `src/web/api.py` (generate_migration_plan)
   - REST endpoint that calls generator
   - Returns YAML to dashboard

---

## 🎓 **Summary**

**Question:** Does it use glooctl?
**Answer:** No - it's pure Python code generation

**How it works:**
1. Parse APIC API data
2. Map to Gloo Gateway concepts
3. Generate Kubernetes YAML manifests
4. Return to user for deployment

**Benefits:**
- 100% automated
- No CLI tool dependencies
- Scalable to 1000s of APIs
- Fully customizable

The entire conversion is **code-driven**, not tool-driven! 🚀
