# Agent-Chat Backend Deployment Guide

## 🚀 Quick Start

### Prerequisites
- Azure Account with active subscription
- Azure CLI installed (`az --version`)
- Python 3.11+ (for local testing)
- Git

### One-Command Deployment

```bash
# Make the script executable
chmod +x deploy-azure.sh

# Run the deployment script
./deploy-azure.sh
```

This script will:
1. Create all required Azure resources
2. Configure Azure Blob Storage
3. Set up Key Vault for secrets
4. Deploy the application
5. Configure monitoring and logging

## 📋 Deployment Options

### Option 1: Azure App Service (Recommended)

**Pros:**
- Managed platform
- Auto-scaling
- Built-in monitoring
- Easy SSL/custom domain setup

**Deploy:**
```bash
./deploy-azure.sh
```

### Option 2: Azure Container Instances

**Pros:**
- Container-based deployment
- More control over environment
- Good for microservices architecture

**Deploy:**
```bash
# Build Docker image
docker build -f Dockerfile.azure -t bpchat-backend:latest .

# Push to Azure Container Registry
az acr build --registry <your-registry> --image bpchat-backend:latest .

# Deploy to ACI
az container create \
  --resource-group rg-bpchat \
  --name bpchat-backend \
  --image <your-registry>.azurecr.io/bpchat-backend:latest \
  --ports 8000 \
  --environment-variables \
    STORAGE_BACKEND=azure \
    AZURE_STORAGE_CONNECTION_STRING="<connection-string>" \
  --dns-name-label bpchat-api
```

### Option 3: Azure Kubernetes Service (AKS)

**Pros:**
- Enterprise-scale
- Advanced orchestration
- Multi-region support

**Deploy:**
See `k8s/` directory for Kubernetes manifests (if needed, we can create these).

## 🔧 Configuration

### Environment Variables

Create a `.env.production` file based on `.env.production.example`:

```bash
cp .env.production.example .env.production
# Edit with your values
vim .env.production
```

### Required Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| `STORAGE_BACKEND` | Storage type | `azure` |
| `AZURE_STORAGE_CONNECTION_STRING` | Azure Storage connection | `DefaultEndpoints...` |
| `AZURE_STORAGE_CONTAINER_NAME` | Blob container name | `bpchat-files` |
| `DATABASE_URL` | Database connection | `postgresql://...` |
| `REQUESTY_AI_API_KEY` | AI API key | `sk-...` |
| `JWT_SECRET_KEY` | JWT signing key | Random 32+ char string |
| `CORS_ORIGINS` | Allowed origins | `["https://frontend.com"]` |

## 🏗️ Architecture

```
┌─────────────────────┐
│   Azure Traffic     │
│     Manager         │
└──────────┬──────────┘
           │
┌──────────▼──────────┐
│   App Service /     │
│   Container         │
├─────────────────────┤
│   Agent-Chat Backend   │
│   (FastAPI)         │
└──────────┬──────────┘
           │
    ┌──────┴──────┐
    │             │
┌───▼───┐    ┌───▼───┐
│ Azure │    │  SQL  │
│ Blob  │    │  DB   │
└───────┘    └───────┘
```

## 📦 Azure Resources Created

1. **Resource Group**: `rg-bpchat`
   - Contains all resources

2. **Storage Account**: `bpchatstorage`
   - Blob storage for files
   - Hot tier for frequent access

3. **App Service Plan**: `asp-bpchat`
   - B2 tier (can be scaled)
   - Linux environment

4. **Web App**: `bpchat-backend`
   - Python 3.11 runtime
   - Managed identity enabled

5. **Key Vault**: `kv-bpchat`
   - Secure secret storage
   - Managed identity access

6. **PostgreSQL** (optional):
   - Production database
   - SSL enforced

## 🔐 Security Setup

### 1. Key Vault Integration

All secrets are stored in Azure Key Vault:

```bash
# Store a secret
az keyvault secret set \
  --vault-name kv-bpchat \
  --name "api-key" \
  --value "your-secret-value"

# Reference in App Service
VARIABLE_NAME="@Microsoft.KeyVault(SecretUri=https://kv-bpchat.vault.azure.net/secrets/api-key/)"
```

### 2. Managed Identity

The app uses managed identity to access Key Vault:

```bash
# Enable managed identity
az webapp identity assign --name bpchat-backend --resource-group rg-bpchat

# Grant Key Vault access
az keyvault set-policy \
  --name kv-bpchat \
  --object-id <identity-id> \
  --secret-permissions get list
```

### 3. Network Security

```bash
# Configure IP restrictions (optional)
az webapp config access-restriction add \
  --name bpchat-backend \
  --resource-group rg-bpchat \
  --rule-name "AllowSpecificIP" \
  --priority 100 \
  --action Allow \
  --ip-address "YOUR.IP.ADDRESS/32"
```

## 📊 Monitoring

### Application Insights

```bash
# Create Application Insights
az monitor app-insights component create \
  --app bpchat-insights \
  --location eastus \
  --resource-group rg-bpchat

# Connect to Web App
az webapp config appsettings set \
  --name bpchat-backend \
  --resource-group rg-bpchat \
  --settings APPLICATIONINSIGHTS_CONNECTION_STRING="<connection-string>"
```

### View Logs

```bash
# Stream logs
az webapp log tail --name bpchat-backend --resource-group rg-bpchat

# Download logs
az webapp log download --name bpchat-backend --resource-group rg-bpchat
```

## 🔄 Deployment Methods

### Git Deployment

```bash
# Add Azure remote
git remote add azure <deployment-url>

# Push to deploy
git push azure main:master
```

### GitHub Actions

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Azure

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: azure/webapps-deploy@v2
        with:
          app-name: bpchat-backend
          publish-profile: ${{ secrets.AZURE_WEBAPP_PUBLISH_PROFILE }}
```

### ZIP Deployment

```bash
# Create ZIP
zip -r deploy.zip . -x "*.git*" "*.env" "venv/*"

# Deploy
az webapp deployment source config-zip \
  --name bpchat-backend \
  --resource-group rg-bpchat \
  --src deploy.zip
```

## 🧪 Testing

### Local Testing with Azure Storage

```bash
# Set environment variables
export STORAGE_BACKEND=azure
export AZURE_STORAGE_CONNECTION_STRING="your-connection-string"

# Run test script
python test_azure_storage.py
```

### Docker Testing

```bash
# Build and run with Docker Compose
docker-compose -f docker-compose.azure.yml up

# Test with Azurite (local Azure emulator)
docker-compose -f docker-compose.azure.yml --profile dev up
```

### API Testing

```bash
# Health check
curl https://bpchat-backend.azurewebsites.net/health

# Upload file
curl -X POST https://bpchat-backend.azurewebsites.net/api/v1/files/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@test.xlsx"

# Get storage stats
curl https://bpchat-backend.azurewebsites.net/api/v1/files/storage/stats
```

## 🔧 Troubleshooting

### Common Issues

#### 1. Application won't start

```bash
# Check logs
az webapp log tail --name bpchat-backend --resource-group rg-bpchat

# Verify environment variables
az webapp config appsettings list --name bpchat-backend --resource-group rg-bpchat

# Restart the app
az webapp restart --name bpchat-backend --resource-group rg-bpchat
```

#### 2. Storage connection fails

```bash
# Test connection string
python -c "from azure.storage.blob import BlobServiceClient; client = BlobServiceClient.from_connection_string('your-string'); print('Connected!')"

# Verify container exists
az storage container list --connection-string "your-connection-string"
```

#### 3. Database connection issues

```bash
# Test database connection
python -c "import asyncpg; import asyncio; asyncio.run(asyncpg.connect('your-database-url'))"

# Check firewall rules
az postgres server firewall-rule list --resource-group rg-bpchat --server bpchat-db-server
```

## 📈 Scaling

### Manual Scaling

```bash
# Scale up (change tier)
az appservice plan update \
  --name asp-bpchat \
  --resource-group rg-bpchat \
  --sku S1

# Scale out (add instances)
az webapp update \
  --name bpchat-backend \
  --resource-group rg-bpchat \
  --minimum-elastic-instance-count 2
```

### Auto-scaling

```bash
# Enable autoscale
az monitor autoscale create \
  --resource-group rg-bpchat \
  --resource bpchat-backend \
  --resource-type Microsoft.Web/sites \
  --min-count 1 \
  --max-count 10 \
  --count 2

# Add CPU rule
az monitor autoscale rule create \
  --resource-group rg-bpchat \
  --autoscale-name bpchat-autoscale \
  --condition "CpuPercentage > 70 avg 5m" \
  --scale out 1
```

## 🔄 Updates and Maintenance

### Update Application

```bash
# Via Git
git push azure main:master

# Via ZIP
az webapp deployment source config-zip --name bpchat-backend --resource-group rg-bpchat --src deploy.zip
```

### Database Migrations

```bash
# SSH into App Service
az webapp ssh --name bpchat-backend --resource-group rg-bpchat

# Run migrations
python -m alembic upgrade head
```

### Backup

```bash
# Create backup
az webapp config backup create \
  --resource-group rg-bpchat \
  --webapp-name bpchat-backend \
  --backup-name "backup-$(date +%Y%m%d-%H%M%S)" \
  --container-url "https://storage.blob.core.windows.net/backups?<sas-token>"
```

## 💰 Cost Optimization

### Tips to Reduce Costs

1. **Use B-series VMs** for predictable workloads
2. **Enable auto-shutdown** for dev/test environments
3. **Use Azure Storage lifecycle policies** to move old files to cool/archive tiers
4. **Monitor with Cost Analysis** in Azure Portal
5. **Use reserved instances** for long-term deployments (up to 72% savings)

### Estimated Monthly Costs

| Service | Tier | Est. Cost |
|---------|------|-----------|
| App Service | B2 | ~$55 |
| Storage Account | Hot, 100GB | ~$2 |
| PostgreSQL | Basic, 1 vCore | ~$25 |
| Key Vault | Standard | ~$0.03/secret |
| **Total** | | **~$82/month** |

## 🆘 Support

### Resources

- [Azure App Service Docs](https://docs.microsoft.com/azure/app-service/)
- [Azure Blob Storage Docs](https://docs.microsoft.com/azure/storage/blobs/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)

### Get Help

1. Check application logs
2. Review this documentation
3. Check Azure Service Health
4. Contact Azure Support

## ✅ Post-Deployment Checklist

- [ ] Verify application is running (`/health` endpoint)
- [ ] Test file upload/download
- [ ] Configure custom domain
- [ ] Set up SSL certificate
- [ ] Configure backup strategy
- [ ] Set up monitoring alerts
- [ ] Test auto-scaling
- [ ] Document API endpoints
- [ ] Update frontend configuration
- [ ] Security scan
- [ ] Performance testing
- [ ] Disaster recovery plan

## 🎉 Success!

Your Agent-Chat backend is now deployed to Azure with:
- ☁️ Azure Blob Storage for files
- 🔐 Key Vault for secrets
- 📊 Application Insights for monitoring
- 🔄 Auto-scaling capability
- 🛡️ Enterprise-grade security

Access your API at: `https://bpchat-backend.azurewebsites.net`
