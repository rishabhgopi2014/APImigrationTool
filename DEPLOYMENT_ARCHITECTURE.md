# 🏗️ Deployment Architecture - Where to Deploy What

## Overview

This guide explains **where each component runs** during an actual API migration from APIC to Gloo Gateway.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Your Company Network                             │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  Migration Orchestrator Tool (This Codebase)               │    │
│  │  ────────────────────────────────────────────────────────  │    │
│  │  Where: Laptop, Jump Server, or CI/CD Pipeline             │    │
│  │  Purpose: Generate configs, monitor migration              │    │
│  │                                                             │    │
│  │  Components:                                                │    │
│  │  - Python scripts (discovery, generation)                  │    │
│  │  - Web dashboard (FastAPI + Vue.js) [Optional]             │    │
│  │  - kubectl CLI (to apply configs)                          │    │
│  └──────────────┬──────────────────────────┬───────────────────┘    │
│                 │                          │                         │
│                 │ Discovers APIs           │ Deploys YAML            │
│                 ▼                          ▼                         │
│  ┌─────────────────────────┐   ┌──────────────────────────────┐   │
│  │  Legacy APIC Server     │   │  Kubernetes Cluster          │   │
│  │  ─────────────────────  │   │  ─────────────────────────   │   │
│  │  Where: Data center     │   │  Where: GKE, EKS, AKS, or    │   │
│  │  Port: 9444 (HTTPS)     │   │         on-prem K8s          │   │
│  │                          │   │                               │   │
│  │  What's here:            │   │  What's deployed here:        │   │
│  │  - Existing APIs         │   │  ┌────────────────────────┐  │   │
│  │  - OAuth providers       │   │  │  Gloo Gateway          │  │   │
│  │  - Rate limit configs    │   │  │  (gloo-system ns)      │  │   │
│  │  - API metadata          │   │  │  ──────────────────    │  │   │
│  └──────────────────────────┘   │  │  - VirtualService      │  │   │
│                                   │  │  - Upstream            │  │   │
│                                   │  │  - AuthConfig          │  │   │
│                                   │  │  - RateLimitConfig     │  │   │
│                                   │  │  - Gateway Proxy pods  │  │   │
│                                   │  └────────────────────────┘  │   │
│                                   │                               │   │
│                                   │  Receives:                    │   │
│                                   │  - Generated YAML from tool  │   │
│                                   │  - kubectl apply commands     │   │
│                                   └───────────────────────────────┘   │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  API Consumers (External Users/Apps)                        │    │
│  │  ────────────────────────────────────────────────────────   │    │
│  │  During migration: Traffic goes through Gloo Gateway        │    │
│  │  - 0% → 5% → 25% → 50% → 100% gradual shift                │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Component Deployment Details

### 1. **Migration Orchestrator Tool** (This Codebase)

**Where to Deploy:**

#### Option A: Developer Laptop (Recommended for Initial Testing)
```bash
# Your Windows/Mac/Linux machine
Location: C:\Users\Admin\OneDrive\Documents\APIMigration
Purpose: Testing, config generation, monitoring
Access Required: 
  - Network access to APIC (port 9444)
  - kubectl access to Kubernetes cluster
  - Internet access (for dependencies)
```

**Pros:**
- ✅ Easy to run and test
- ✅ Full control
- ✅ Quick iterations

**Cons:**
- ❌ Not always-on
- ❌ Depends on laptop being connected

---

#### Option B: Jump Server / Bastion Host (Recommended for Production)
```bash
# Dedicated Linux server in your data center
Location: jump-server.company.com
Purpose: Centralized migration operations
Setup:
  1. Clone repo: git clone <repo-url>
  2. Install Python: sudo apt install python3.10
  3. Install dependencies: pip install -r requirements.txt
  4. Configure .env with credentials
  5. Install kubectl
  6. Set up kubeconfig for cluster access
```

**Pros:**
- ✅ Always available
- ✅ Shared access for team
- ✅ Better security (inside network)
- ✅ Can run web dashboard 24/7

**Cons:**
- ❌ Requires server setup
- ❌ Team needs VPN/SSH access

---

#### Option C: CI/CD Pipeline (Best for Automation)
```yaml
# GitLab CI / GitHub Actions / Jenkins
# .gitlab-ci.yml example

stages:
  - discover
  - generate
  - deploy

discover-apis:
  stage: discover
  script:
    - python -m src.discovery.apic_client
    - python bulk_generate_configs.py --output-dir ./configs
  artifacts:
    paths:
      - configs/

deploy-to-k8s:
  stage: deploy
  script:
    - kubectl apply -f configs/ -R
  only:
    - main
```

**Pros:**
- ✅ Fully automated
- ✅ Git version control
- ✅ Audit trail
- ✅ Can schedule migrations

**Cons:**
- ❌ Requires CI/CD setup
- ❌ Less manual control

---

### 2. **Kubernetes Cluster with Gloo Gateway**

**Where to Deploy:** Cloud or On-Premises Kubernetes

#### Cloud Options:

**Google Kubernetes Engine (GKE):**
```bash
# Create cluster
gcloud container clusters create gloo-migration-cluster \
  --zone us-central1-a \
  --num-nodes 3 \
  --machine-type n1-standard-2

# Install Gloo Gateway
helm repo add gloo https://storage.googleapis.com/solo-public-helm
helm install gloo gloo/gloo --namespace gloo-system --create-namespace
```

**Amazon EKS:**
```bash
# Create cluster
eksctl create cluster \
  --name gloo-migration \
  --region us-east-1 \
  --nodes 3 \
  --node-type t3.medium

# Install Gloo
helm install gloo gloo/gloo --namespace gloo-system --create-namespace
```

**Azure AKS:**
```bash
# Create cluster
az aks create \
  --resource-group migration-rg \
  --name gloo-cluster \
  --node-count 3 \
  --node-vm-size Standard_D2s_v3

# Install Gloo
helm install gloo gloo/gloo --namespace gloo-system --create-namespace
```

#### On-Premises Options:

**Existing Kubernetes Cluster:**
```bash
# If you already have Kubernetes
# Just install Gloo Gateway
helm install gloo gloo/gloo --namespace gloo-system --create-namespace

# Verify installation
kubectl get pods -n gloo-system
```

**What Gets Deployed Here:**
- ✅ VirtualService resources (routing rules)
- ✅ Upstream resources (backend targets)
- ✅ AuthConfig resources (authentication)
- ✅ RateLimitConfig resources (rate limiting)
- ✅ Gloo Gateway proxy pods (actual gateway)

---

### 3. **Legacy APIC Server**

**Where:** Stays in your existing data center

**No Changes Required:**
- ❌ Don't modify APIC during migration
- ❌ Don't shutdown APIC until 100% complete
- ✅ Keep running as-is
- ✅ Acts as backend target during transition

**Network Requirements:**
- Kubernetes cluster must reach APIC (outbound HTTPS on port 8443/9444)
- Configure firewall rules if needed

---

## Deployment Workflow

### Phase 1: Setup (One-Time)

**Step 1: Set Up Migration Tool**
```bash
# Choose: Laptop, Jump Server, or CI/CD

# On your chosen location:
git clone <your-repo>/APIMigration
cd APIMigration
pip install -r requirements.txt

# Configure credentials
cp .env.template .env
nano .env  # Add APIC credentials
```

**Step 2: Set Up Kubernetes Cluster**
```bash
# Create or use existing cluster
# Install Gloo Gateway
helm install gloo gloo/gloo -n gloo-system --create-namespace

# Configure kubectl on migration tool server
kubectl config set-cluster gloo-cluster --server=https://k8s-api.company.com
kubectl config set-credentials admin --token=<token>
kubectl config use-context gloo-cluster
```

**Step 3: Verify Connectivity**
```bash
# From migration tool location:

# Test APIC access
curl -k https://apic.company.com:9444/api/health

# Test Kubernetes access
kubectl get ns

# Test Gloo installation
kubectl get pods -n gloo-system
```

---

### Phase 2: Migration Execution

**Step 1: Discover APIs** (Runs on Migration Tool)
```bash
# On migration tool server/laptop
python bulk_generate_configs.py --output-dir ./generated-configs
```

**Step 2: Review Configs** (Manual Review)
```bash
# Review generated YAML
cd generated-configs
cat SUMMARY.md
less customer-api/virtualservice.yaml
```

**Step 3: Deploy to Kubernetes** (From Migration Tool to K8s)
```bash
# Apply generated configs to Kubernetes cluster
kubectl apply -f generated-configs/customer-api/

# Verify deployment
kubectl get vs,upstream -n gloo-system
```

**Step 4: Monitor** (Via WebDashboard or kubectl)
```bash
# Option A: Web dashboard (if running)
# Visit http://jump-server:8000

# Option B: kubectl
kubectl logs -n gloo-system deployment/gateway-proxy -f
```

---

## Network Requirements

### Connectivity Matrix

| From | To | Port | Protocol | Purpose |
|------|-----|------|----------|---------|
| Migration Tool | APIC Server | 9444 | HTTPS | API discovery |
| Migration Tool | Kubernetes API | 6443 | HTTPS | Deploy configs |
| Kubernetes | APIC Server | 8443 | HTTPS | Backend proxying |
| End Users | Gloo Gateway | 80/443 | HTTP/HTTPS | API traffic |
| Gloo Gateway | APIC | 8443 | HTTPS | Legacy backend |

### Firewall Rules Needed

```bash
# Allow migration tool → APIC
Source: <migration-tool-ip>
Destination: <apic-server-ip>:9444
Action: ALLOW

# Allow Kubernetes → APIC
Source: <k8s-cluster-cidr>
Destination: <apic-server-ip>:8443
Action: ALLOW

# Allow users → Gloo
Source: 0.0.0.0/0 (internet)
Destination: <gloo-gateway-lb-ip>:443
Action: ALLOW
```

---

## Recommended Deployment Strategy

### For Small Teams (< 10 people)

```
Migration Tool: Developer laptops
Kubernetes: GKE/EKS (managed service)
Deployment: Manual kubectl apply
Monitoring: kubectl + web dashboard
```

### For Medium Teams (10-50 people)

```
Migration Tool: Jump server (Linux VM)
Kubernetes: GKE/EKS/AKS with autoscaling
Deployment: GitOps with ArgoCD/Flux
Monitoring: Prometheus + Grafana
```

### For Large Teams (50+ people)

```
Migration Tool: CI/CD pipeline (GitLab/GitHub Actions)
Kubernetes: Multi-cluster (staging + production)
Deployment: GitOps with policy enforcement
Monitoring: Enterprise observability platform
```

---

## Security Considerations

### Migration Tool Server

```bash
# Protect credentials
chmod 600 .env
chown root:root .env

# Use secrets management
# Store credentials in HashiCorp Vault or AWS Secrets Manager

# Audit access
# Log all kubectl commands
# Track who ran migrations
```

### Kubernetes Cluster

```bash
# Network policies
kubectl apply -f network-policies/

# RBAC for Gloo resources
kubectl apply -f rbac/gloo-admin-role.yaml

# Secrets for auth configs
kubectl create secret generic oauth-client-secret \
  --from-literal=client-secret=<secret> \
  -n gloo-system
```

---

## Quick Start Examples

### Example 1: Laptop → GKE Deployment

```bash
# On your laptop (Windows/Mac/Linux)
cd C:\Users\YourName\Migration
python bulk_generate_configs.py --output-dir ./configs

# Deploy to GKE
gcloud container clusters get-credentials gloo-cluster --zone=us-central1-a
kubectl apply -f configs/customer-api/

# Monitor
kubectl get vs -n gloo-system --watch
```

### Example 2: Jump Server → On-Prem K8s

```bash
# SSH to jump server
ssh admin@jump-server.company.com

# Navigate to migration tool
cd /opt/api-migration

# Generate configs
python3 bulk_generate_configs.py --output-dir /tmp/configs

# Deploy
kubectl --kubeconfig=/etc/kubernetes/admin.conf apply -f /tmp/configs/

# Monitor
kubectl logs -f -n gloo-system deployment/gateway-proxy
```

### Example 3: GitLab CI → EKS

```yaml
# .gitlab-ci.yml
deploy_apis:
  stage: deploy
  image: alpine/k8s:1.24.0
  script:
    - aws eks update-kubeconfig --name gloo-cluster --region us-east-1
    - python bulk_generate_configs.py --output-dir ./configs
    - kubectl apply -f ./configs/ -R
  only:
    - main
```

---

## Summary

**Where to Run Migration Tool:**
- 💻 **Development/Testing:** Your laptop
- 🖥️ **Production:** Jump server or CI/CD pipeline

**Where Kubernetes/Gloo Runs:**
- ☁️ **Cloud:** GKE, EKS, AKS (recommended for new deployments)
- 🏢 **On-Prem:** Your existing Kubernetes cluster

**Where APIC Stays:**
- 🏛️ **Existing location:** Don't move, keep as backend during migration

**Key Point:** The migration tool is just a **config generator**. It doesn't need to be always-on. You can run it from anywhere that has:
1. Network access to APIC
2. kubectl access to Kubernetes
3. Python 3.10+

After configs are deployed to Kubernetes, the tool is no longer needed (until next API migration).

---

## Next Steps

1. ✅ Choose deployment location for migration tool
2. ✅ Verify network connectivity (tool → APIC → K8s)
3. ✅ Install dependencies on chosen server
4. ✅ Configure `.env` with credentials
5. ✅ Test with one low-risk API
6. ✅ Scale to more APIs

**You're ready to deploy!** 🚀
