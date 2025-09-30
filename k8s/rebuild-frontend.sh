#!/bin/bash

# Configuration
ACR_NAME="bpchatregistry"
FRONTEND_IMAGE="${ACR_NAME}.azurecr.io/airgb-frontend:latest"
NAMESPACE="agion-airgb"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Rebuilding and deploying frontend with API fix...${NC}"
echo ""

# No need for Docker login when using ACR Build
echo -e "${YELLOW}🔐 Using ACR Build (no Docker required)...${NC}"

# Navigate to Agent-Chat directory
cd /Users/mikko/Documents/Github/RG-Brands/Agent-Chat

# Build frontend image using ACR
echo -e "${GREEN}🎨 Building frontend image in ACR...${NC}"
az acr build \
    --registry $ACR_NAME \
    --image airgb-frontend:latest \
    --file Dockerfile.frontend.prod \
    . \
    --platform linux/amd64

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to build frontend image${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Frontend image built and pushed!${NC}"

# Restart frontend deployment
echo -e "${YELLOW}🔄 Restarting frontend deployment...${NC}"
kubectl rollout restart deployment/airgb-frontend -n $NAMESPACE

# Wait for rollout
echo -e "${YELLOW}⏳ Waiting for rollout to complete...${NC}"
kubectl rollout status deployment/airgb-frontend -n $NAMESPACE --timeout=300s

echo ""
echo -e "${GREEN}✅ Frontend deployment updated!${NC}"
echo ""
echo -e "${YELLOW}📋 Check the deployment:${NC}"
kubectl get pods -n $NAMESPACE
echo ""
echo -e "${GREEN}🔗 Application available at: https://airgb.agion.dev${NC}"
