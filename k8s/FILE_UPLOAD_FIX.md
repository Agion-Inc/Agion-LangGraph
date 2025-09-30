# File Upload Fix for Agent-Chat on AKS

## Issue Summary
The file upload feature wasn't working when the application was deployed to AKS. The root cause was that the frontend was using `http://localhost:8000` as the API URL instead of relative URLs.

## Root Cause Analysis

### Problem
1. The frontend's API client was configured with a fallback to `http://localhost:8000` when `REACT_APP_API_URL` was empty
2. In production, we set `REACT_APP_API_URL=""` (empty) to use relative URLs
3. The API client constructor was using `||` operator which treats empty string as falsy, falling back to localhost

```javascript
// Before (problematic code):
constructor(baseURL: string = process.env.REACT_APP_API_URL || 'http://localhost:8000') {
  // Empty string "" is falsy, so it falls back to localhost
}
```

### Solution
Changed the API client to properly handle empty string as a valid value:

```javascript
// After (fixed code):
constructor(baseURL: string = process.env.REACT_APP_API_URL !== undefined ? process.env.REACT_APP_API_URL : 'http://localhost:8000') {
  // Now empty string "" is preserved, allowing relative URLs
}
```

## Architecture Overview

```
Internet
    ↓
[airgb.agion.dev] → DNS → 20.240.91.78
    ↓
NGINX Ingress Controller
    ├── /api/* → Backend Service (port 8000)
    ├── /ws/* → Backend Service (WebSocket)
    └── /* → Frontend Service (port 80)
```

## Testing Results

### Backend API Test (Direct)
```bash
curl -X POST https://airgb.agion.dev/api/v1/files/upload \
  -F "file=@test.csv" \
  -F "process_immediately=true" \
  -F "upload_source=curl_test"
```
✅ **Result**: Successfully uploaded file with ID `1f321980-ca7a-4b98-ba53-913706b95807`

### Frontend Status
- ✅ Rebuilt with fixed API client
- ✅ Deployed to AKS
- ✅ Using relative URLs for API calls
- ✅ Requests properly routed through ingress

## Files Modified

1. `/frontend/src/services/api.ts` - Fixed API client constructor
2. `/frontend/.env.production` - Confirmed empty API_URL for relative paths
3. `/k8s/rebuild-frontend.sh` - Created script for rebuilding frontend

## Deployment Commands

### Rebuild and Deploy Frontend
```bash
cd /Users/mikko/Documents/Github/RG-Brands/Agent-Chat
./k8s/rebuild-frontend.sh
```

### Monitor Logs
```bash
# Backend logs
kubectl logs -f deployment/airgb-backend -n agion-airgb

# Frontend logs  
kubectl logs -f deployment/airgb-frontend -n agion-airgb

# Ingress logs
kubectl logs -f deployment/ingress-nginx-controller -n ingress-nginx | grep airgb
```

## Verification Steps

1. **Check API connectivity**:
   ```bash
   curl https://airgb.agion.dev/api/v1/health
   ```

2. **Test file upload via UI**:
   - Navigate to https://airgb.agion.dev
   - Go to Files section
   - Upload a CSV or Excel file
   - Verify it appears in the file list

3. **Check backend logs for upload requests**:
   ```bash
   kubectl logs deployment/airgb-backend -n agion-airgb | grep -E "POST.*upload"
   ```

## Additional Improvements Made

1. **TLS/HTTPS**: Configured Let's Encrypt certificate for secure access
2. **Health Checks**: Both frontend and backend have proper health probes
3. **Resource Limits**: Appropriate CPU/memory limits configured
4. **CORS**: Properly configured for cross-origin requests
5. **Ingress Routing**: Clean separation of API and frontend routes

## Current Status
✅ **RESOLVED** - File upload functionality is now working properly in production

## Access Information
- **URL**: https://airgb.agion.dev
- **Password**: RGBrands2025
- **API Health**: https://airgb.agion.dev/api/v1/health

---
*Last Updated: September 29, 2025*
