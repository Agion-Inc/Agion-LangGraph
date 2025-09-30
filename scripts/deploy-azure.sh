#!/bin/bash
# Azure Deployment Script for Agent-Chat
# Builds and deploys containers to Azure Container Instances

set -e

echo "🚀 Starting Agent-Chat Azure Deployment..."

# Configuration
RESOURCE_GROUP="rg-bpchat"
LOCATION="germanywestcentral"
ACR_NAME="bpchatregistry"
FRONTEND_IMAGE="bpchat-frontend:latest"
BACKEND_IMAGE="bpchat-backend:latest"

# Navigate to project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/.."
cd "$PROJECT_ROOT"

echo "📦 Building Docker images..."

# Build backend image
echo "Building backend..."
docker build -t $ACR_NAME.azurecr.io/$BACKEND_IMAGE -f backend/Dockerfile backend/

# Build frontend image (ensure build exists)
echo "Building frontend..."
if [ ! -d "frontend/build" ]; then
    echo "Frontend build directory not found. Building React app first..."
    cd frontend
    npm install
    npm run build
    cd ..
fi
docker build -t $ACR_NAME.azurecr.io/$FRONTEND_IMAGE -f frontend/Dockerfile frontend/

echo "🔐 Logging into Azure Container Registry..."
az acr login --name $ACR_NAME

echo "📤 Pushing images to ACR..."
docker push $ACR_NAME.azurecr.io/$BACKEND_IMAGE
docker push $ACR_NAME.azurecr.io/$FRONTEND_IMAGE

echo "🎯 Deploying to Azure Container Instances..."
az container create --resource-group $RESOURCE_GROUP --file azure-deploy.yaml

echo "✅ Deployment complete!"
echo "🌐 Access your application at: http://9.141.174.130"
echo "📊 Check container status with: az container show --resource-group $RESOURCE_GROUP --name bpchat-app"