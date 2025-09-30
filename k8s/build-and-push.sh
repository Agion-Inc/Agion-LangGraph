#!/bin/bash

# Configuration
ACR_NAME="bpchatregistry"
BACKEND_IMAGE="${ACR_NAME}.azurecr.io/airgb-backend:latest"
FRONTEND_IMAGE="${ACR_NAME}.azurecr.io/airgb-frontend:latest"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Building and pushing AIRGB images to Azure Container Registry...${NC}"
echo ""

# Login to ACR
echo -e "${YELLOW}🔐 Logging in to ACR...${NC}"
az acr login --name $ACR_NAME
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to login to ACR${NC}"
    exit 1
fi

# Navigate to Agent-Chat directory
cd ..

# Build backend image
echo -e "${GREEN}🔧 Building backend image...${NC}"
docker build -t $BACKEND_IMAGE -f Dockerfile.backend.prod .
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to build backend image${NC}"
    exit 1
fi

# Build frontend image
echo -e "${GREEN}🎨 Building frontend image...${NC}"
docker build -t $FRONTEND_IMAGE -f Dockerfile.frontend.prod .
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to build frontend image${NC}"
    exit 1
fi

# Push backend image
echo -e "${GREEN}📤 Pushing backend image...${NC}"
docker push $BACKEND_IMAGE
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to push backend image${NC}"
    exit 1
fi

# Push frontend image
echo -e "${GREEN}📤 Pushing frontend image...${NC}"
docker push $FRONTEND_IMAGE
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to push frontend image${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Images successfully built and pushed!${NC}"
echo ""
echo -e "${YELLOW}📦 Images:${NC}"
echo "   Backend:  $BACKEND_IMAGE"
echo "   Frontend: $FRONTEND_IMAGE"
echo ""
echo -e "${GREEN}Next step: Run ./k8s/deploy-aks.sh to deploy to AKS${NC}"
