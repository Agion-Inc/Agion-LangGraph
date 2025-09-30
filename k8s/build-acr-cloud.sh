#!/bin/bash

# Configuration
ACR_NAME="bpchatregistry"
RESOURCE_GROUP="Agent-Chat"
BACKEND_IMAGE="airgb-backend:latest"
FRONTEND_IMAGE="airgb-frontend:latest"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Building AIRGB images using ACR Build (no local Docker required)...${NC}"
echo ""

# Navigate to Agent-Chat directory
cd /Users/mikko/Documents/Github/RG-Brands/Agent-Chat

# Build backend image in ACR
echo -e "${GREEN}🔧 Building backend image in ACR...${NC}"
az acr build \
    --registry $ACR_NAME \
    --image $BACKEND_IMAGE \
    --file Dockerfile.backend.prod \
    . \
    --platform linux/amd64

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to build backend image${NC}"
    exit 1
fi

# Build frontend image in ACR
echo -e "${GREEN}🎨 Building frontend image in ACR...${NC}"
az acr build \
    --registry $ACR_NAME \
    --image $FRONTEND_IMAGE \
    --file Dockerfile.frontend.prod \
    . \
    --platform linux/amd64

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to build frontend image${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Images successfully built in ACR!${NC}"
echo ""
echo -e "${YELLOW}📦 Images:${NC}"
echo "   Backend:  ${ACR_NAME}.azurecr.io/${BACKEND_IMAGE}"
echo "   Frontend: ${ACR_NAME}.azurecr.io/${FRONTEND_IMAGE}"
echo ""
echo -e "${GREEN}Next step: Run ./k8s/deploy-aks.sh to deploy to AKS${NC}"
