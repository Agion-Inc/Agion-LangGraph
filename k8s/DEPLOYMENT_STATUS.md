# Agent-Chat (AIRGB) AKS Deployment Status

## 🎉 Deployment Successful with TLS/HTTPS!

The Agent-Chat application has been successfully deployed to your AKS cluster in Sweden Central with full TLS/HTTPS support.

## 🔗 Access Information

- **Application URL**: https://airgb.agion.dev (🔒 Secured with Let's Encrypt)
- **API Health Check**: https://airgb.agion.dev/api/v1/health
- **Access Password**: RGBrands2025
- **HTTP Auto-Redirect**: Yes (HTTP → HTTPS)

## 📊 Current Status

### Infrastructure
- **AKS Cluster**: agion-mvp-mvp-aks (Sweden Central)
- **Namespace**: agion-airgb
- **Ingress Controller IP**: 20.240.91.78
- **DNS**: airgb.agion.dev → 20.240.91.78 ✅

### Deployments
- **Backend**: ✅ Running (airgb-backend-65fc59b5d4-9bb2g)
- **Frontend**: ✅ Running (airgb-frontend-7944d5c489-lrks9)

### Services
- **Backend Service**: ClusterIP 10.2.0.123:8000
- **Frontend Service**: ClusterIP 10.2.0.204:80

### Container Images
- **Backend**: bpchatregistry.azurecr.io/airgb-backend:latest
- **Frontend**: bpchatregistry.azurecr.io/airgb-frontend:latest

## 🔧 Useful Commands

### Check Application Status
```bash
# View pod status
kubectl get pods -n agion-airgb

# Check logs
kubectl logs -f deployment/airgb-backend -n agion-airgb
kubectl logs -f deployment/airgb-frontend -n agion-airgb

# Describe resources
kubectl describe ingress airgb-ingress -n agion-airgb
kubectl describe pod -l app=airgb-backend -n agion-airgb
```

### Update Deployment
```bash
# Rebuild and push new images
cd /Users/mikko/Documents/Github/RG-Brands/Agent-Chat
./k8s/build-acr-cloud.sh

# Restart deployments to pull new images
kubectl rollout restart deployment/airgb-backend -n agion-airgb
kubectl rollout restart deployment/airgb-frontend -n agion-airgb
```

### Local Testing
```bash
# Port-forward backend
kubectl port-forward -n agion-airgb svc/airgb-backend-service 8000:8000

# Port-forward frontend
kubectl port-forward -n agion-airgb svc/airgb-frontend-service 8080:80
```

## 📝 Notes

### SSL/HTTPS ✅
- **Status**: Fully configured and working
- **Certificate**: Let's Encrypt Production (Auto-renewed)
- **HTTP/2**: Enabled
- **HSTS**: Enabled (Strict-Transport-Security)
- **Auto-redirect**: HTTP automatically redirects to HTTPS

### Features Working
- ✅ Frontend accessible
- ✅ Backend API health check
- ✅ CORS configured for cross-origin requests
- ✅ WebSocket support configured
- ✅ Database (SQLite) initialized
- ✅ All agents registered and ready

### Next Steps
1. ✅ Test the application at https://airgb.agion.dev
2. ✅ SSL certificate configured and working
3. Monitor pod logs for any issues
4. Consider scaling replicas if needed

## 🚨 Troubleshooting

If you encounter issues:

1. **Check pod status**: `kubectl get pods -n agion-airgb`
2. **View logs**: `kubectl logs -f <pod-name> -n agion-airgb`
3. **Describe pod**: `kubectl describe pod <pod-name> -n agion-airgb`
4. **Check ingress**: `kubectl get ingress -n agion-airgb`
5. **Test connectivity**: `curl https://airgb.agion.dev/api/v1/health`
6. **Check certificate**: `kubectl get certificate -n agion-airgb`

## 📦 Cleanup

To remove the deployment:
```bash
cd /Users/mikko/Documents/Github/RG-Brands/Agent-Chat/k8s
./cleanup.sh
```

## 🔒 TLS/Certificate Information

### Certificate Details
- **Issuer**: Let's Encrypt Production
- **Domain**: airgb.agion.dev
- **Auto-renewal**: Yes (managed by cert-manager)
- **Certificate Name**: airgb-tls-certificate
- **Secret Name**: airgb-tls-certificate

### Security Headers Configured
- ✅ Strict-Transport-Security (HSTS)
- ✅ X-Frame-Options: SAMEORIGIN
- ✅ X-Content-Type-Options: nosniff
- ✅ X-XSS-Protection: 1; mode=block
- ✅ CORS properly configured

---

Last Updated: September 29, 2025, 6:57 AM UTC
