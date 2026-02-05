# Generated Gloo Portal Resources

## Summary

- **Portals:** 1
- **API Products:** 1
- **Usage Plans:** 2

## Deployment

```bash
# Deploy all resources
./deploy.sh
```

## Verification

```bash
# Check Portals
kubectl get portals -n gloo-portal

# Check API Products
kubectl get apiproducts -n gloo-portal

# Get Portal URL
kubectl get portal production-portal -n gloo-portal -o jsonpath="{.status.portalUrl}"
```
