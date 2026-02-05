#!/bin/bash
# Deploy Gloo Portal resources

echo "Deploying Gloo Portal resources..."

# Install Gloo Portal (if not already installed)
# helm install gloo-portal gloo-portal/gloo-portal -n gloo-portal --create-namespace --set licenseKey=$GLOO_LICENSE_KEY

# Create namespace
kubectl create namespace gloo-portal --dry-run=client -o yaml | kubectl apply -f -

# Deploy Portal resources
kubectl apply -f ./demo-portal-configs/

# Verify
echo ""
echo "Portals:"
kubectl get portals -n gloo-portal
echo ""
echo "API Products:"
kubectl get apiproducts -n gloo-portal
