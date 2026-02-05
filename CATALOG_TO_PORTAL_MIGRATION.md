# 📚 Migrating APIC Catalogs & Collections to Gloo Portal

## Overview

**Yes, it is absolutely feasible** to migrate APIC catalogs and collections to Gloo Developer Portal! This guide shows you exactly how to do it.

---

## APIC → Gloo Portal Mapping

| APIC Concept | Gloo Portal Equivalent | Purpose |
|--------------|------------------------|---------|
| **Catalog** | **Portal** | Top-level environment/storefront |
| **Collection** | **API Product** | Logical grouping of related APIs |
| **API** | **Virtual Service + API Doc** | Individual API with documentation |
| **Plan** | **Usage Plan** (with rate limiting) | Rate limits and quotas |

---

## Architecture

```
APIC Structure:
┌─────────────────────────────────────────┐
│ Catalog: Production                      │
│ ├── Collection: Customer APIs            │
│ │   ├── API: Customer Preferences       │
│ │   ├── API: Customer Profile           │
│ │   └── Plan: Gold (10000 req/day)      │
│ ├── Collection: Payment APIs             │
│ │   ├── API: Payment Gateway            │
│ │   └── Plan: Silver (1000 req/day)     │
└─────────────────────────────────────────┘

Gloo Portal Structure:
┌─────────────────────────────────────────┐
│ Portal: Production Portal                │
│ ├── API Product: Customer APIs           │
│ │   ├── VirtualService: customer-pref   │
│ │   ├── VirtualService: customer-prof   │
│ │   ├── APIDoc: OpenAPI specs           │
│ │   └── RateLimitConfig: Gold plan      │
│ ├── API Product: Payment APIs            │
│ │   ├── VirtualService: payment-gw      │
│ │   ├── APIDoc: OpenAPI specs           │
│ │   └── RateLimitConfig: Silver plan    │
└─────────────────────────────────────────┘
```

---

## Step-by-Step Migration

### Step 1: Export APIC Catalog Structure

**Extract from APIC:**

```bash
# Using APIC REST API
curl -k -X GET "https://apic-server:9444/api/catalogs/production" \
  -H "Authorization: Bearer $TOKEN" \
  > apic-catalog-production.json

# Get all collections in catalog
curl -k -X GET "https://apic-server:9444/api/catalogs/production/collections" \
  -H "Authorization: Bearer $TOKEN" \
  > apic-collections.json

# Get all products in each collection
curl -k -X GET "https://apic-server:9444/api/catalogs/production/products" \
  -H "Authorization: Bearer $TOKEN" \
  > apic-products.json
```

**Or manually document:**

Create a mapping file:
```yaml
# catalog-mapping.yaml
catalogs:
  - name: production
    portal_name: production-portal
    collections:
      - name: Customer APIs
        product_name: customer-apis
        apis:
          - customer-preferences-api
          - customer-profile-api
        plans:
          - name: Gold
            rate_limit: 10000/day
          - name: Silver
            rate_limit: 1000/day
      
      - name: Payment APIs
        product_name: payment-apis
        apis:
          - payment-gateway-api
        plans:
          - name: Standard
            rate_limit: 5000/day
  
  - name: sandbox
    portal_name: sandbox-portal
    collections:
      - name: Test APIs
        product_name: test-apis
        apis:
          - test-api-1
```

---

### Step 2: Install Gloo Portal

```bash
# Requires Gloo Enterprise license
# Add Gloo Portal repo
helm repo add gloo-portal https://storage.googleapis.com/gloo-portal/helm
helm repo update

# Install Gloo Portal
helm install gloo-portal gloo-portal/gloo-portal \
  --namespace gloo-portal \
  --create-namespace \
  --set licenseKey=$GLOO_LICENSE_KEY

# Verify installation
kubectl get pods -n gloo-portal
```

---

### Step 3: Create Portal (for each APIC Catalog)

**For APIC Catalog "Production":**

```yaml
# production-portal.yaml
apiVersion: portal.gloo.solo.io/v1beta1
kind: Portal
metadata:
  name: production-portal
  namespace: gloo-portal
spec:
  displayName: Production API Portal
  description: Production APIs for external partners and customers
  
  # Domain where portal is accessible
  domains:
    - portal.company.com
  
  # Branding
  banner:
    fetchUrl: https://company.com/logo.png
  primaryColor: "#0033A0"
  
  # Authentication (optional)
  oidcAuth:
    clientId: portal-client
    clientSecret:
      name: portal-oauth-secret
      namespace: gloo-portal
    issuerUrl: https://auth.company.com
  
  # Published API Products (will create in next step)
  publishedApiProducts:
    - name: customer-apis
      namespace: gloo-portal
    - name: payment-apis
      namespace: gloo-portal
```

**Apply:**
```bash
kubectl apply -f production-portal.yaml
```

**For APIC Catalog "Sandbox":**

```yaml
# sandbox-portal.yaml
apiVersion: portal.gloo.solo.io/v1beta1
kind: Portal
metadata:
  name: sandbox-portal
  namespace: gloo-portal
spec:
  displayName: Sandbox API Portal
  description: Test and development APIs
  domains:
    - sandbox-portal.company.com
  publishedApiProducts:
    - name: test-apis
      namespace: gloo-portal
```

---

### Step 4: Create API Products (for each APIC Collection)

**For APIC Collection "Customer APIs":**

```yaml
# customer-apis-product.yaml
apiVersion: portal.gloo.solo.io/v1beta1
kind: APIProduct
metadata:
  name: customer-apis
  namespace: gloo-portal
  labels:
    catalog: production
    collection: customer-apis
spec:
  displayName: Customer APIs
  description: |
    APIs for managing customer data including preferences and profiles.
    Ideal for CRM integrations and customer-facing applications.
  
  # Link to VirtualServices (the migrated APIs)
  apis:
    - apiRef:
        name: customer-preferences-api-vs
        namespace: gloo-system
    - apiRef:
        name: customer-profile-api-vs
        namespace: gloo-system
  
  # Versions (optional)
  versions:
    - name: v1
      apis:
        - apiRef:
            name: customer-preferences-api-vs
            namespace: gloo-system
  
  # Usage Plans (from APIC Plans)
  usagePlans:
    - name: gold-plan
      displayName: Gold Plan
      description: High-volume plan with 10,000 requests per day
      rateLimit:
        requestsPerUnit: 10000
        unit: DAY
      authPolicy:
        apiKey: {}
    
    - name: silver-plan
      displayName: Silver Plan
      description: Standard plan with 1,000 requests per day
      rateLimit:
        requestsPerUnit: 1000
        unit: DAY
      authPolicy:
        apiKey: {}
```

**For APIC Collection "Payment APIs":**

```yaml
# payment-apis-product.yaml
apiVersion: portal.gloo.solo.io/v1beta1
kind: APIProduct
metadata:
  name: payment-apis
  namespace: gloo-portal
  labels:
    catalog: production
    collection: payment-apis
spec:
  displayName: Payment APIs
  description: Secure payment processing APIs
  
  apis:
    - apiRef:
        name: payment-gateway-api-vs
        namespace: gloo-system
  
  usagePlans:
    - name: standard-plan
      displayName: Standard Plan
      rateLimit:
        requestsPerUnit: 5000
        unit: DAY
      authPolicy:
        oauth:
          authorizationUrl: https://auth.company.com/oauth/authorize
          tokenUrl: https://auth.company.com/oauth/token
```

**Apply:**
```bash
kubectl apply -f customer-apis-product.yaml
kubectl apply -f payment-apis-product.yaml
```

---

### Step 5: Create API Documentation

**Export OpenAPI specs from APIC:**

```bash
# For each API, export its OpenAPI spec
curl -k -X GET "https://apic-server:9444/api/apis/customer-preferences-api/spec" \
  -H "Authorization: Bearer $TOKEN" \
  > customer-preferences-openapi.yaml
```

**Create APIDoc resource:**

```yaml
# customer-preferences-apidoc.yaml
apiVersion: portal.gloo.solo.io/v1beta1
kind: APIDoc
metadata:
  name: customer-preferences-api-doc
  namespace: gloo-portal
spec:
  # Link to API Product
  productName: customer-apis
  
  # OpenAPI spec (inline or from ConfigMap)
  openApi:
    inlineString: |
      openapi: 3.0.0
      info:
        title: Customer Preferences API
        version: 1.0.0
        description: Manage customer preferences
      servers:
        - url: https://api.company.com
      paths:
        /customer/v1/preferences:
          get:
            summary: Get customer preferences
            responses:
              '200':
                description: Success
                content:
                  application/json:
                    schema:
                      type: object
                      properties:
                        customerId:
                          type: string
                        preferences:
                          type: object
          put:
            summary: Update customer preferences
            responses:
              '200':
                description: Updated
```

**Or load from ConfigMap:**

```yaml
# Store OpenAPI spec in ConfigMap
kubectl create configmap customer-pref-openapi \
  --from-file=openapi.yaml=customer-preferences-openapi.yaml \
  -n gloo-portal

# Reference in APIDoc
apiVersion: portal.gloo.solo.io/v1beta1
kind: APIDoc
metadata:
  name: customer-preferences-api-doc
  namespace: gloo-portal
spec:
  productName: customer-apis
  openApi:
    configMap:
      name: customer-pref-openapi
      namespace: gloo-portal
      key: openapi.yaml
```

**Apply:**
```bash
kubectl apply -f customer-preferences-apidoc.yaml
```

---

### Step 6: Verify Portal

```bash
# Get Portal URL
kubectl get portal production-portal -n gloo-portal -o jsonpath='{.status.portalUrl}'

# Check API Products
kubectl get apiproducts -n gloo-portal

# Check API Docs
kubectl get apidocs -n gloo-portal

# Check status
kubectl describe portal production-portal -n gloo-portal
```

**Access Portal:**
```
https://portal.company.com
```

You should see:
- ✅ All API Products (collections)
- ✅ All APIs with documentation
- ✅ Usage plans with rate limits
- ✅ Interactive API explorer

---

## Automation Script

Let me create a migration script to automate this:

```python
# migrate_catalog_to_portal.py

import yaml
import sys
from pathlib import Path

def migrate_catalog_to_portal(catalog_mapping_file, output_dir):
    """
    Migrate APIC catalogs and collections to Gloo Portal
    
    Args:
        catalog_mapping_file: Path to catalog-mapping.yaml
        output_dir: Directory to write Gloo Portal YAML files
    """
    
    # Load catalog mapping
    with open(catalog_mapping_file) as f:
        mapping = yaml.safe_load(f)
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    for catalog in mapping['catalogs']:
        catalog_name = catalog['name']
        portal_name = catalog['portal_name']
        
        # Create Portal resource
        portal = {
            'apiVersion': 'portal.gloo.solo.io/v1beta1',
            'kind': 'Portal',
            'metadata': {
                'name': portal_name,
                'namespace': 'gloo-portal'
            },
            'spec': {
                'displayName': f'{catalog_name.title()} API Portal',
                'description': f'Portal for {catalog_name} APIs',
                'domains': [f'{portal_name}.company.com'],
                'publishedApiProducts': []
            }
        }
        
        # Create API Products for each collection
        for collection in catalog['collections']:
            collection_name = collection['name']
            product_name = collection['product_name']
            
            # Add to portal
            portal['spec']['publishedApiProducts'].append({
                'name': product_name,
                'namespace': 'gloo-portal'
            })
            
            # Create API Product
            api_product = {
                'apiVersion': 'portal.gloo.solo.io/v1beta1',
                'kind': 'APIProduct',
                'metadata': {
                    'name': product_name,
                    'namespace': 'gloo-portal',
                    'labels': {
                        'catalog': catalog_name,
                        'collection': product_name
                    }
                },
                'spec': {
                    'displayName': collection_name,
                    'description': f'API Product for {collection_name}',
                    'apis': [],
                    'usagePlans': []
                }
            }
            
            # Add APIs to product
            for api_name in collection['apis']:
                api_product['spec']['apis'].append({
                    'apiRef': {
                        'name': f'{api_name}-vs',
                        'namespace': 'gloo-system'
                    }
                })
            
            # Add usage plans
            for plan in collection.get('plans', []):
                # Parse rate limit (e.g., "10000/day" -> 10000, DAY)
                rate_str = plan['rate_limit']
                requests, unit = rate_str.split('/')
                
                usage_plan = {
                    'name': plan['name'].lower().replace(' ', '-'),
                    'displayName': plan['name'],
                    'description': f'{plan["name"]} plan with {rate_str} requests',
                    'rateLimit': {
                        'requestsPerUnit': int(requests),
                        'unit': unit.upper()
                    },
                    'authPolicy': {
                        'apiKey': {}
                    }
                }
                api_product['spec']['usagePlans'].append(usage_plan)
            
            # Write API Product
            product_file = output_path / f'{product_name}-product.yaml'
            with open(product_file, 'w') as f:
                yaml.dump(api_product, f, default_flow_style=False)
            print(f'✅ Created: {product_file}')
        
        # Write Portal
        portal_file = output_path / f'{portal_name}-portal.yaml'
        with open(portal_file, 'w') as f:
            yaml.dump(portal, f, default_flow_style=False)
        print(f'✅ Created: {portal_file}')
    
    print(f'\n📊 Summary:')
    print(f'   Catalogs migrated: {len(mapping["catalogs"])}')
    print(f'   API Products created: {sum(len(c["collections"]) for c in mapping["catalogs"])}')
    print(f'   Output directory: {output_path.absolute()}')
    print(f'\nNext steps:')
    print(f'   1. Review generated YAML files')
    print(f'   2. kubectl apply -f {output_dir}/')
    print(f'   3. Access portal at configured domain')

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print('Usage: python migrate_catalog_to_portal.py <catalog-mapping.yaml> <output-dir>')
        sys.exit(1)
    
    migrate_catalog_to_portal(sys.argv[1], sys.argv[2])
```

---

## Complete Migration Workflow

### **1. Prepare Catalog Mapping**

Create `catalog-mapping.yaml` documenting your APIC structure:

```yaml
catalogs:
  - name: production
    portal_name: production-portal
    collections:
      - name: Customer APIs
        product_name: customer-apis
        apis:
          - customer-preferences-api
          - customer-profile-api
        plans:
          - name: Gold
            rate_limit: 10000/day
```

### **2. Generate Portal Resources**

```bash
python migrate_catalog_to_portal.py catalog-mapping.yaml ./portal-configs
```

### **3. Deploy to Kubernetes**

```bash
# Deploy Portal and API Products
kubectl apply -f portal-configs/

# Verify
kubectl get portals -n gloo-portal
kubectl get apiproducts -n gloo-portal
```

### **4. Add API Documentation**

For each API, create APIDoc with OpenAPI spec exported from APIC.

### **5. Access Portal**

```bash
# Get portal URL
kubectl get portal production-portal -n gloo-portal

# Access at configured domain
https://portal.company.com
```

---

## Benefits of Full Migration

**✅ Developer Portal:**
- Self-service API discovery
- Interactive API explorer
- Automatic documentation

**✅ API Products:**
- Logical grouping by business domain
- Version management
- Usage plan enforcement

**✅ Multiple Portals:**
- Separate production/sandbox portals
- Different branding per catalog
- Environment isolation

**✅ Usage Plans:**
- Rate limiting per plan
- API key or OAuth authentication
- Self-service subscription (if enabled)

---

## Migration Checklist

### **Prerequisites:**
- [ ] Gloo Enterprise license
- [ ] Gloo Portal installed
- [ ] Catalog mapping documented

### **For Each Catalog:**
- [ ] Create Portal resource
- [ ] Configure domain/branding
- [ ] Set up authentication (optional)

### **For Each Collection:**
- [ ] Create API Product
- [ ] Link to VirtualServices
- [ ] Define usage plans
- [ ] Add to Portal

### **For Each API:**
- [ ] Export OpenAPI spec from APIC
- [ ] Create APIDoc resource
- [ ] Link to API Product
- [ ] Test in portal

### **Verification:**
- [ ] Portal accessible at domain
- [ ] All API Products visible
- [ ] Documentation renders correctly
- [ ] API explorer works
- [ ] Usage plans enforced

---

## Summary

**Yes, you can migrate everything:**
- ✅ **Catalogs** → Gloo Portals
- ✅ **Collections** → API Products
- ✅ **APIs** → VirtualServices + APIDocs
- ✅ **Plans** → Usage Plans with rate limiting

**Migration approach:**
1. Use this tool to migrate APIs (automated)
2. Document catalog structure in YAML
3. Run migration script to generate Portal configs
4. Export OpenAPI specs from APIC
5. Deploy to Kubernetes
6. Access your new Gloo Portal!

**Result:** Full feature parity with APIC Developer Portal! 🎉
