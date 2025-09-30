# AIRGB AKS Deployment Guide

## Overview
This directory contains all the Kubernetes manifests and scripts needed to deploy the Agent-Chat application (AIRGB) to your existing AKS cluster in Sweden Central.

## Architecture
- **Namespace**: `agion-airgb`
- **Frontend**: React app served by Nginx on port 80
- **Backend**: FastAPI Python app on port 8000
- **Ingress**: NGINX Ingress Controller routing to both services
- **Domain**: airgb.agion.dev

## Prerequisites
1. Azure CLI installed and logged in
2. Docker installed for building images
3. kubectl installed
4. Access to the AKS cluster: `agion-mvp-mvp-aks`
5. Access to the ACR: `bpchatregistry`

## Quick Deployment

### Step 1: Build and Push Images
```bash
cd /Users/mikko/Documents/Github/RG-Brands/Agent-Chat/k8s
chmod +x build-and-push.sh
./build-and-push.sh
```

This will:
- Build the backend Docker image
- Build the frontend Docker image
- Push both images to Azure Container Registry

### Step 2: Deploy to AKS
```bash
chmod +x deploy-aks.sh
./deploy-aks.sh
```

This will:
- Create the namespace `agion-airgb`
- Create ACR pull secret for image authentication
- Deploy backend service and deployment
- Deploy frontend service and deployment
- Configure ingress for airgb.agion.dev
- Wait for all pods to be ready

## Manual Deployment

If you prefer to deploy manually, run these commands in order:

```bash
# Get AKS credentials
az aks get-credentials --resource-group agion-platform-prod --name agion-mvp-mvp-aks

# Create namespace
kubectl apply -f namespace.yaml

# Create ACR pull secret
ACR_PASSWORD=$(az acr credential show --name bpchatregistry --query "passwords[0].value" -o tsv)
kubectl create secret docker-registry acr-secret \
    --namespace=agion-airgb \
    --docker-server=bpchatregistry.azurecr.io \
    --docker-username=bpchatregistry \
    --docker-password="$ACR_PASSWORD"

# Deploy ConfigMaps
kubectl apply -f frontend-nginx-configmap.yaml

# Deploy backend
kubectl apply -f backend-deployment.yaml

# Deploy frontend
kubectl apply -f frontend-deployment.yaml

# Deploy ingress
kubectl apply -f ingress-simple.yaml

# Check deployment status
kubectl get all -n agion-airgb
```

## Verify Deployment

### Check Pod Status
```bash
kubectl get pods -n agion-airgb
```

All pods should show `Running` status.

### Check Logs
```bash
# Backend logs
kubectl logs -f deployment/airgb-backend -n agion-airgb

# Frontend logs
kubectl logs -f deployment/airgb-frontend -n agion-airgb
```

### Check Ingress
```bash
kubectl get ingress -n agion-airgb
```

The ingress should show an external IP address. Ensure your DNS (airgb.agion.dev) points to this IP.

### Local Testing with Port-Forward
```bash
# Test backend directly
kubectl port-forward -n agion-airgb svc/airgb-backend-service 8000:8000

# Test frontend directly
kubectl port-forward -n agion-airgb svc/airgb-frontend-service 8080:80
```

Then visit:
- Backend: http://localhost:8000/docs
- Frontend: http://localhost:8080

## Troubleshooting

### Pods Not Starting
```bash
# Describe pod for detailed error
kubectl describe pod <pod-name> -n agion-airgb

# Check events
kubectl get events -n agion-airgb --sort-by='.lastTimestamp'
```

### Image Pull Errors
```bash
# Verify ACR secret exists
kubectl get secret acr-secret -n agion-airgb

# Recreate if needed
kubectl delete secret acr-secret -n agion-airgb
# Then run the create secret command again
```

### Connection Issues
```bash
# Check service endpoints
kubectl get endpoints -n agion-airgb

# Test internal connectivity
kubectl run -it --rm debug --image=alpine --restart=Never -n agion-airgb -- sh
# Inside the pod:
wget -O- http://airgb-backend-service:8000/api/v1/health
wget -O- http://airgb-frontend-service
```

### Update Deployment
```bash
# After building new images
kubectl rollout restart deployment/airgb-backend -n agion-airgb
kubectl rollout restart deployment/airgb-frontend -n agion-airgb

# Watch rollout status
kubectl rollout status deployment/airgb-backend -n agion-airgb
kubectl rollout status deployment/airgb-frontend -n agion-airgb
```

## Cleanup
To remove the deployment:

```bash
chmod +x cleanup.sh
./cleanup.sh
```

This will remove all resources but ask for confirmation before deleting the namespace.

## Configuration Files

### Kubernetes Manifests
- `namespace.yaml` - Creates the agion-airgb namespace
- `backend-deployment.yaml` - Backend deployment and service
- `frontend-deployment.yaml` - Frontend deployment and service
- `frontend-nginx-configmap.yaml` - Nginx configuration for frontend
- `ingress-simple.yaml` - Ingress routing configuration

### Scripts
- `build-and-push.sh` - Build and push Docker images to ACR
- `deploy-aks.sh` - Complete deployment script
- `cleanup.sh` - Remove deployment from cluster

## Environment Variables

### Backend
- `ENVIRONMENT`: production
- `DATABASE_URL`: SQLite database path
- `JWT_SECRET_KEY`: JWT authentication key
- `REQUESTY_AI_API_KEY`: AI service API key
- `CORS_ORIGINS`: Allowed origins for CORS
- `PYDANTIC_DISABLE_PLUGINS`: Disable Pydantic plugins (avoids network issues)

### Frontend
- `REACT_APP_API_URL`: Empty (uses relative URLs through ingress)
- `REACT_APP_ENVIRONMENT`: production
- `REACT_APP_ACCESS_PASSWORD`: RGBrands2025

## Security Notes
1. The JWT secret and API keys are currently in the manifests - consider using Kubernetes Secrets or Azure Key Vault for production
2. The access password is hardcoded - consider using environment-specific configuration
3. SSL/TLS is handled by the ingress controller with cert-manager

## Support
For issues or questions, check:
1. Pod logs using `kubectl logs`
2. Pod descriptions using `kubectl describe`
3. Ingress configuration
4. DNS resolution for airgb.agion.dev
