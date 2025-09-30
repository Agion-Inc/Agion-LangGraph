#!/bin/bash

# Configuration
RESOURCE_GROUP="agion-platform-prod"
AKS_NAME="agion-mvp-mvp-aks"
NAMESPACE="agion-airgb"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}⚠️  This will remove AIRGB deployment from AKS cluster${NC}"
read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Cleanup cancelled."
    exit 0
fi

echo -e "${YELLOW}🧹 Cleaning up AIRGB deployment...${NC}"

# Get AKS credentials
echo -e "${YELLOW}📥 Getting AKS credentials...${NC}"
az aks get-credentials --resource-group $RESOURCE_GROUP --name $AKS_NAME --overwrite-existing

# Delete ingress
echo -e "${YELLOW}Deleting ingress...${NC}"
kubectl delete ingress airgb-ingress -n $NAMESPACE --ignore-not-found

# Delete services
echo -e "${YELLOW}Deleting services...${NC}"
kubectl delete service airgb-backend-service airgb-frontend-service -n $NAMESPACE --ignore-not-found

# Delete deployments
echo -e "${YELLOW}Deleting deployments...${NC}"
kubectl delete deployment airgb-backend airgb-frontend -n $NAMESPACE --ignore-not-found

# Delete configmaps
echo -e "${YELLOW}Deleting configmaps...${NC}"
kubectl delete configmap frontend-nginx-config -n $NAMESPACE --ignore-not-found

# Delete secret
echo -e "${YELLOW}Deleting secrets...${NC}"
kubectl delete secret acr-secret airgb-tls-secret -n $NAMESPACE --ignore-not-found

# Ask if namespace should be deleted
read -p "Delete namespace $NAMESPACE? (yes/no): " delete_ns
if [ "$delete_ns" == "yes" ]; then
    kubectl delete namespace $NAMESPACE --ignore-not-found
    echo -e "${GREEN}✅ Namespace deleted${NC}"
fi

echo ""
echo -e "${GREEN}✅ Cleanup complete!${NC}"
