#!/bin/bash

# Add Azure Blob Storage to Existing Agent-Chat at airgb.agion.dev
# This script only adds storage without full redeployment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================${NC}"
echo -e "${BLUE}Add Storage to Existing Agent-Chat${NC}"
echo -e "${BLUE}Target: airgb.agion.dev${NC}"
echo -e "${BLUE}======================================${NC}"
echo ""

# Check Azure CLI
if ! command -v az &> /dev/null; then
    echo -e "${RED}❌ Azure CLI is not installed${NC}"
    exit 1
fi

# Login check
echo -e "${YELLOW}📝 Checking Azure login...${NC}"
if ! az account show &>/dev/null; then
    az login
fi

# Get resource information
echo -e "${YELLOW}Please provide existing Azure resource details:${NC}"
read -p "Resource Group name: " RESOURCE_GROUP
read -p "App Service name: " APP_NAME
read -p "Key Vault name (or Enter to create new): " KEY_VAULT

if [ -z "$KEY_VAULT" ]; then
    KEY_VAULT="kv-airgb-storage"
    echo -e "${YELLOW}Creating new Key Vault: $KEY_VAULT${NC}"
    LOCATION=$(az group show --name $RESOURCE_GROUP --query location -o tsv)
    az keyvault create --name $KEY_VAULT --resource-group $RESOURCE_GROUP --location $LOCATION --output none
fi

# Create Storage Account
STORAGE_ACCOUNT="airgbstorage$(date +%s | tail -c 6)"
CONTAINER_NAME="bpchat-files"

echo -e "${YELLOW}☁️  Creating Storage Account: $STORAGE_ACCOUNT${NC}"
LOCATION=$(az group show --name $RESOURCE_GROUP --query location -o tsv)

az storage account create \
    --name $STORAGE_ACCOUNT \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --sku Standard_LRS \
    --kind StorageV2 \
    --output none

STORAGE_CONNECTION_STRING=$(az storage account show-connection-string \
    --name $STORAGE_ACCOUNT \
    --resource-group $RESOURCE_GROUP \
    --query connectionString \
    --output tsv)

# Create container
az storage container create \
    --name $CONTAINER_NAME \
    --account-name $STORAGE_ACCOUNT \
    --public-access off \
    --output none

echo -e "${GREEN}✓ Storage created${NC}"

# Store in Key Vault
echo -e "${YELLOW}🔒 Storing connection string in Key Vault...${NC}"
az keyvault secret set \
    --vault-name $KEY_VAULT \
    --name "storage-connection-string" \
    --value "$STORAGE_CONNECTION_STRING" \
    --output none

# Get managed identity
IDENTITY_ID=$(az webapp identity show \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --query principalId \
    --output tsv 2>/dev/null || echo "")

if [ -z "$IDENTITY_ID" ]; then
    IDENTITY_ID=$(az webapp identity assign \
        --name $APP_NAME \
        --resource-group $RESOURCE_GROUP \
        --query principalId \
        --output tsv)
fi

# Grant Key Vault access
az keyvault set-policy \
    --name $KEY_VAULT \
    --object-id $IDENTITY_ID \
    --secret-permissions get list \
    --output none

echo -e "${GREEN}✓ Key Vault configured${NC}"

# Update App Service settings
echo -e "${YELLOW}⚙️  Updating App Service configuration...${NC}"
az webapp config appsettings set \
    --name $APP_NAME \
    --resource-group $RESOURCE_GROUP \
    --settings \
    STORAGE_BACKEND=azure \
    AZURE_STORAGE_CONNECTION_STRING="@Microsoft.KeyVault(SecretUri=https://${KEY_VAULT}.vault.azure.net/secrets/storage-connection-string/)" \
    AZURE_STORAGE_CONTAINER_NAME=$CONTAINER_NAME \
    AZURE_STORAGE_SAS_EXPIRY_DAYS=7 \
    --output none

echo -e "${GREEN}✓ Configuration updated${NC}"

# Restart app
echo -e "${YELLOW}🔄 Restarting application...${NC}"
az webapp restart --name $APP_NAME --resource-group $RESOURCE_GROUP --output none

echo ""
echo -e "${GREEN}✅ Storage Added Successfully!${NC}"
echo ""
echo "Storage Details:"
echo "  Account: $STORAGE_ACCOUNT"
echo "  Container: $CONTAINER_NAME"
echo "  Key Vault: $KEY_VAULT"
echo ""
echo "Connection String (save this):"
echo "$STORAGE_CONNECTION_STRING"
echo ""
echo "Test the storage:"
echo "  curl https://api-airgb.agion.dev/health/storage"
echo ""
