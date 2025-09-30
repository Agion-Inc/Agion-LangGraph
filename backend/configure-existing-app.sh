#!/bin/bash

# Configure Existing Agent-Chat App Service
# Updates configuration without redeployment

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}Configure Existing Agent-Chat${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# Load current config
if [ -f ".env.production" ]; then
    export $(grep -v '^#' .env.production | xargs)
fi

echo -e "${YELLOW}Enter your existing Azure resources:${NC}"
read -p "Resource Group: " RG
read -p "App Service Name: " APP

echo ""
echo -e "${YELLOW}Choose configuration to update:${NC}"
echo "1) Add Azure Blob Storage only"
echo "2) Add PostgreSQL only" 
echo "3) Add both Storage and PostgreSQL"
echo "4) Just update environment variables"
read -p "Choice (1-4): " CHOICE

case $CHOICE in
    1)
        # Storage only
        echo -e "${YELLOW}Creating Storage Account...${NC}"
        STORAGE="airgbstorage$(date +%s | tail -c 6)"
        LOCATION=$(az group show --name $RG --query location -o tsv)
        
        az storage account create \
            --name $STORAGE \
            --resource-group $RG \
            --location $LOCATION \
            --sku Standard_LRS \
            --output none
            
        CONN_STR=$(az storage account show-connection-string \
            --name $STORAGE \
            --resource-group $RG \
            --query connectionString -o tsv)
            
        az storage container create \
            --name bpchat-files \
            --connection-string "$CONN_STR" \
            --output none
            
        # Update app settings
        az webapp config appsettings set \
            --name $APP \
            --resource-group $RG \
            --settings \
            STORAGE_BACKEND=azure \
            AZURE_STORAGE_CONNECTION_STRING="$CONN_STR" \
            AZURE_STORAGE_CONTAINER_NAME=bpchat-files \
            --output none
            
        echo -e "${GREEN}✓ Storage configured${NC}"
        echo "Connection String: $CONN_STR"
        ;;
        
    2)
        # PostgreSQL only
        echo -e "${YELLOW}Enter PostgreSQL details:${NC}"
        read -p "Host: " PG_HOST
        read -p "Database [bpchat_db]: " PG_DB
        PG_DB=${PG_DB:-bpchat_db}
        read -p "User [bpchat_user]: " PG_USER
        PG_USER=${PG_USER:-bpchat_user}
        read -s -p "Password: " PG_PASS
        echo ""
        
        DB_URL="postgresql+asyncpg://${PG_USER}:${PG_PASS}@${PG_HOST}:5432/${PG_DB}?sslmode=require"
        
        az webapp config appsettings set \
            --name $APP \
            --resource-group $RG \
            --settings \
            DATABASE_URL="$DB_URL" \
            --output none
            
        echo -e "${GREEN}✓ PostgreSQL configured${NC}"
        ;;
        
    3)
        # Both
        echo "Run this script twice - once for storage (1), once for PostgreSQL (2)"
        ;;
        
    4)
        # Just env vars
        echo -e "${YELLOW}Updating environment variables...${NC}"
        
        az webapp config appsettings set \
            --name $APP \
            --resource-group $RG \
            --settings \
            ENVIRONMENT=production \
            PYDANTIC_DISABLE_PLUGINS=1 \
            PYTHONUNBUFFERED=1 \
            CORS_ORIGINS="[\"https://airgb.agion.dev\",\"https://api-airgb.agion.dev\"]" \
            REQUESTY_AI_API_KEY="$REQUESTY_AI_API_KEY" \
            JWT_SECRET_KEY="$JWT_SECRET_KEY" \
            ACCESS_PASSWORD="$ACCESS_PASSWORD" \
            --output none
            
        echo -e "${GREEN}✓ Environment updated${NC}"
        ;;
esac

# Restart
echo -e "${YELLOW}Restarting app...${NC}"
az webapp restart --name $APP --resource-group $RG --output none

echo ""
echo -e "${GREEN}✅ Configuration Complete!${NC}"
echo ""
echo "Test endpoints:"
echo "  https://api-airgb.agion.dev/health"
echo "  https://api-airgb.agion.dev/health/storage"
echo ""
