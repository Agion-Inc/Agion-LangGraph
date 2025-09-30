# Agent-Chat Agion Deployment Guide

## 🚀 Quick Start

Deploy Agent-Chat to Azure using your existing Agion PostgreSQL infrastructure.

### Prerequisites
- Azure CLI installed
- Access to Agion PostgreSQL server
- Azure subscription

## Step 1: Database Setup

### Option A: Automated Setup (Recommended)
```bash
# Make script executable
chmod +x setup-agion-database.sh

# Run database setup
./setup-agion-database.sh
```

This will:
1. Prompt for your Agion PostgreSQL details
2. Create `bpchat_db` database
3. Create dedicated user with secure password
4. Save connection string to `.env.production.database`

### Option B: Manual Setup
```sql
-- Connect to your Agion PostgreSQL as admin
psql -h your-agion-postgres.postgres.database.azure.com -U admin_user -d postgres

-- Run the setup SQL
\i setup-agion-database.sql
```

## Step 2: Configure Environment

1. Copy the production template:
```bash
cp .env.production.example .env.production
```

2. Update `.env.production` with your values:
```bash
# Database - Use the connection string from Step 1
DATABASE_URL=postgresql+asyncpg://bpchat_user:password@your-agion-postgres.postgres.database.azure.com:5432/bpchat_db?sslmode=require

# Storage
STORAGE_BACKEND=azure

# API Keys
REQUESTY_AI_API_KEY=your-api-key

# CORS - Update with your domains
CORS_ORIGINS=["https://airgb.agion.dev","https://api-airgb.agion.dev"]
```

## Step 3: Initialize Database Schema

```bash
# Make script executable
chmod +x init_database.py

# Initialize the database tables
python init_database.py

# Or just verify connection
python init_database.py --verify
```

## Step 4: Deploy to Azure

```bash
# Make deployment script executable
chmod +x deploy-azure-agion.sh

# Run deployment
./deploy-azure-agion.sh
```

The script will:
1. Create Azure resources (Storage, Key Vault, App Service)
2. Configure with your Agion PostgreSQL
3. Deploy the application
4. Initialize database schema

## 📊 Architecture

```
┌─────────────────────────────────────────┐
│         Agion Infrastructure            │
├─────────────────────────────────────────┤
│                                         │
│   ┌──────────────┐    ┌─────────────┐  │
│   │   Agent-Chat    │    │  Other Apps │  │
│   │   Backend    │    │             │  │
│   └──────┬───────┘    └──────┬──────┘  │
│          │                   │          │
│          └─────────┬─────────┘          │
│                    ▼                    │
│         ┌──────────────────┐            │
│         │  PostgreSQL      │            │
│         ├──────────────────┤            │
│         │ • agion_data     │            │
│         │ • bpchat_db      │ ← Your DB  │
│         └──────────────────┘            │
│                    │                    │
│   ┌────────────────┼────────────────┐   │
│   │                ▼                │   │
│   │  ┌──────────────────┐          │   │
│   │  │  Azure Blob      │          │   │
│   │  │  Storage         │          │   │
│   │  └──────────────────┘          │   │
│   │                                 │   │
│   │  ┌──────────────────┐          │   │
│   │  │  Azure App       │          │   │
│   │  │  Service         │          │   │
│   │  └──────────────────┘          │   │
│   └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

## 🧪 Testing

### 1. Test Database Connection
```bash
# Using the init script
python init_database.py --verify

# Or using psql
psql "$DATABASE_URL" -c "SELECT version();"
```

### 2. Test Locally
```bash
# Start with production config
python start_server_production.py
```

### 3. Test Deployed App
```bash
# Health check
curl https://bpchat-backend.azurewebsites.net/health

# Storage health
curl https://bpchat-backend.azurewebsites.net/health/storage

# Database tables
curl https://bpchat-backend.azurewebsites.net/health/detailed
```

## 🔧 Configuration Details

### Database Connection String Format
```
postgresql+asyncpg://username:password@host:port/database?sslmode=require
```

### Required Environment Variables
| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | Agion PostgreSQL connection | `postgresql+asyncpg://...` |
| `STORAGE_BACKEND` | Storage type | `azure` |
| `AZURE_STORAGE_CONNECTION_STRING` | Blob storage connection | Auto-generated |
| `REQUESTY_AI_API_KEY` | AI API key | `sk-...` |
| `JWT_SECRET_KEY` | JWT signing key | Auto-generated |

## 🚨 Troubleshooting

### Database Connection Issues
```bash
# Check if database exists
psql -h your-host -U admin -l | grep bpchat_db

# Test connection
python -c "
import asyncio
import asyncpg
asyncio.run(asyncpg.connect('$DATABASE_URL'))
"
```

### Azure Deployment Issues
```bash
# View logs
az webapp log tail --name bpchat-backend --resource-group rg-bpchat

# SSH into container
az webapp ssh --name bpchat-backend --resource-group rg-bpchat

# Restart app
az webapp restart --name bpchat-backend --resource-group rg-bpchat
```

## 📝 Post-Deployment

1. **Change default admin password** (if created):
   - Default: `admin` / `changeme`
   - Update immediately after first login

2. **Configure monitoring**:
   ```bash
   az monitor app-insights component create \
     --app bpchat-insights \
     --resource-group rg-bpchat \
     --location eastus
   ```

3. **Set up backups**:
   - Database: Already handled by Agion infrastructure
   - Blob storage: Configure lifecycle policies

## 🔒 Security Checklist

- [ ] Changed default admin password
- [ ] Configured CORS for your domains only
- [ ] Enabled HTTPS only on App Service
- [ ] Set up IP restrictions if needed
- [ ] Configured firewall rules for PostgreSQL
- [ ] Enabled audit logging

## 💰 Cost Estimate

Using Agion PostgreSQL reduces costs:
- **App Service (B2)**: ~$55/month
- **Storage (100GB)**: ~$2/month
- **PostgreSQL**: $0 (using existing Agion)
- **Total**: ~$57/month (vs $82 with separate PostgreSQL)

## 📞 Support

For issues specific to:
- **Database**: Check Agion PostgreSQL logs
- **Application**: Check App Service logs
- **Storage**: Check blob storage metrics

## ✅ Deployment Complete!

Your Agent-Chat backend is now deployed with:
- ✅ Agion PostgreSQL integration
- ✅ Azure Blob Storage for files
- ✅ Secure Key Vault for secrets
- ✅ Auto-scaling App Service
- ✅ Health monitoring endpoints

Access your API at: `https://bpchat-backend.azurewebsites.net`
