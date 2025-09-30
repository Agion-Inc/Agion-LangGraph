# SSL/TLS Setup Instructions for Agent-Chat

## ✅ Current Status: DNS Configured Correctly

Your DNS is already configured correctly:
- `airgb.agion.dev` → `20.52.202.193` (A record, gray cloud)
- `api-airgb.agion.dev` → `bpchat-backend-2025.azurewebsites.net` (CNAME, gray cloud)

## 🔧 Next Steps: Manual SSL Configuration

Since Azure CLI requires domain ownership verification, you'll need to complete the setup through the Azure Portal:

### 1. Add Custom Domains via Azure Portal

1. **Go to Azure Portal** → **App Services** → **bpchat-frontend-2025**
2. **Select "Custom domains"** from the left menu
3. **Click "+ Add custom domain"**
4. **Enter**: `airgb.agion.dev`
5. **Click "Validate"** - it should pass since DNS is configured

Repeat for `bpchat-backend-2025` with `api-airgb.agion.dev`

### 2. Add Free SSL Certificates

After domains are added:

1. **Go to "TLS/SSL settings"** → **Private Key Certificates (.pfx)**
2. **Click "+ Create App Service Managed Certificate"**
3. **Select your custom domain** from dropdown
4. **Click "Create"**

Repeat for both domains.

### 3. Bind SSL Certificates

1. **Go to "TLS/SSL settings"** → **Bindings**
2. **Click "+ Add TLS/SSL Binding"**
3. **Select custom domain** and **certificate**
4. **Choose "SNI SSL"**
5. **Click "Add Binding"**

### 4. Update Frontend Environment

After SSL is configured, update the frontend environment variable:

```bash
az webapp config appsettings set \
  --resource-group bpchat-rg \
  --name bpchat-frontend-2025 \
  --settings REACT_APP_API_URL="https://api-airgb.agion.dev"
```

### 5. Force HTTPS Redirect

Enable HTTPS-only mode:

```bash
az webapp update \
  --resource-group bpchat-rg \
  --name bpchat-frontend-2025 \
  --https-only true

az webapp update \
  --resource-group bpchat-rg \
  --name bpchat-backend-2025 \
  --https-only true
```

## 🎯 Expected Result

After completing these steps:
- ✅ `https://airgb.agion.dev` - Frontend with SSL
- ✅ `https://api-airgb.agion.dev` - Backend API with SSL
- ✅ Automatic HTTP → HTTPS redirect
- ✅ Free SSL certificates (auto-renewing)

## 🔍 Test URLs

Once complete, test these endpoints:
- `https://airgb.agion.dev` - Should load your React app
- `https://api-airgb.agion.dev/api/v1/health` - Should return API health status
- `https://api-airgb.agion.dev/docs` - Should load API documentation

## 💡 Alternative: CLI Commands (if portal doesn't work)

If you prefer CLI, you can create the domain verification records manually:

```bash
# Add TXT records to Cloudflare for domain verification:
# asuid.airgb.agion.dev → 2a6a9ad9a8ef57bf42a53630c2f657a88cdcdb462a2391037623b265320de649
# asuid.api-airgb.agion.dev → 2a6a9ad9a8ef57bf42a53630c2f657a88cdcdb462a2391037623b265320de649

# Then try adding domains via CLI:
az webapp config hostname add --webapp-name bpchat-frontend-2025 --resource-group bpchat-rg --hostname airgb.agion.dev
az webapp config hostname add --webapp-name bpchat-backend-2025 --resource-group bpchat-rg --hostname api-airgb.agion.dev
```

## 📋 Summary

You're almost done! The Azure App Service deployment is complete with:
- ✅ Static IP: `20.52.202.193`
- ✅ DNS configured correctly
- ✅ Apps running on Azure
- ⏳ SSL certificates (manual setup needed)

Total cost: €21-26/month vs the original €60-80/month Container Instances approach.