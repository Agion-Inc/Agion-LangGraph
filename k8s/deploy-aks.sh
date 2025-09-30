#!/bin/bash

# Configuration
RESOURCE_GROUP="agion-platform-prod"
AKS_NAME="agion-mvp-mvp-aks"
ACR_NAME="bpchatregistry"
NAMESPACE="agion-airgb"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Deploying AIRGB to AKS cluster in Sweden Central...${NC}"
echo ""

# Check if user is logged in to Azure
echo -e "${YELLOW}Checking Azure CLI authentication...${NC}"
if ! az account show &>/dev/null; then
    echo -e "${RED}❌ Not logged in to Azure. Please run: az login${NC}"
    exit 1
fi

# Get AKS credentials
echo -e "${YELLOW}📥 Getting AKS credentials...${NC}"
az aks get-credentials --resource-group $RESOURCE_GROUP --name $AKS_NAME --overwrite-existing

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to get AKS credentials${NC}"
    exit 1
fi

# Test cluster connectivity
echo -e "${YELLOW}Testing cluster connectivity...${NC}"
kubectl cluster-info &>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Cannot connect to cluster${NC}"
    exit 1
fi

# Create namespace
echo -e "${GREEN}📦 Creating namespace...${NC}"
kubectl apply -f namespace.yaml

# Create ACR pull secret
echo -e "${GREEN}🔐 Creating ACR pull secret...${NC}"
ACR_PASSWORD=$(az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)
if [ -z "$ACR_PASSWORD" ]; then
    echo -e "${RED}❌ Failed to get ACR password${NC}"
    exit 1
fi

kubectl delete secret acr-secret -n $NAMESPACE --ignore-not-found
kubectl create secret docker-registry acr-secret \
    --namespace=$NAMESPACE \
    --docker-server=${ACR_NAME}.azurecr.io \
    --docker-username=$ACR_NAME \
    --docker-password="$ACR_PASSWORD"

# Apply ConfigMaps
echo -e "${GREEN}📝 Creating ConfigMaps...${NC}"
kubectl apply -f frontend-nginx-configmap.yaml

# Deploy backend
echo -e "${GREEN}🔧 Deploying backend...${NC}"
kubectl apply -f backend-deployment.yaml

# Deploy frontend
echo -e "${GREEN}🎨 Deploying frontend...${NC}"
kubectl apply -f frontend-deployment.yaml

# Deploy ingress
echo -e "${GREEN}🌐 Deploying ingress...${NC}"
kubectl apply -f ingress-simple.yaml

# Wait for deployments
echo -e "${YELLOW}⏳ Waiting for deployments to be ready...${NC}"
kubectl rollout status deployment/airgb-backend -n $NAMESPACE --timeout=300s
kubectl rollout status deployment/airgb-frontend -n $NAMESPACE --timeout=300s

# Get pod status
echo ""
echo -e "${GREEN}✅ Deployment complete!${NC}"
echo ""
echo -e "${YELLOW}📊 Pod Status:${NC}"
kubectl get pods -n $NAMESPACE -o wide
echo ""
echo -e "${YELLOW}🔍 Service Status:${NC}"
kubectl get svc -n $NAMESPACE
echo ""
echo -e "${YELLOW}🌐 Ingress Status:${NC}"
kubectl get ingress -n $NAMESPACE
echo ""

# Get ingress details
INGRESS_IP=$(kubectl get ingress -n $NAMESPACE -o jsonpath='{.items[0].status.loadBalancer.ingress[0].ip}' 2>/dev/null)
if [ -n "$INGRESS_IP" ]; then
    echo -e "${GREEN}🔗 Ingress IP: $INGRESS_IP${NC}"
    echo -e "${YELLOW}⚠️  Make sure airgb.agion.dev points to this IP${NC}"
else
    echo -e "${YELLOW}⏳ Ingress IP not yet assigned. Check back in a few minutes with:${NC}"
    echo "   kubectl get ingress -n $NAMESPACE"
fi

echo ""
echo -e "${GREEN}🔗 Application will be available at:${NC}"
echo "   https://airgb.agion.dev"
echo ""
echo -e "${YELLOW}📋 Useful commands:${NC}"
echo "   # Check pod logs:"
echo "   kubectl logs -f deployment/airgb-backend -n $NAMESPACE"
echo "   kubectl logs -f deployment/airgb-frontend -n $NAMESPACE"
echo ""
echo "   # Get pod details:"
echo "   kubectl describe pod -l app=airgb-backend -n $NAMESPACE"
echo "   kubectl describe pod -l app=airgb-frontend -n $NAMESPACE"
echo ""
echo "   # Restart deployments:"
echo "   kubectl rollout restart deployment/airgb-backend -n $NAMESPACE"
echo "   kubectl rollout restart deployment/airgb-frontend -n $NAMESPACE"
echo ""
echo "   # Port-forward for local testing:"
echo "   kubectl port-forward -n $NAMESPACE svc/airgb-backend-service 8000:8000"
echo "   kubectl port-forward -n $NAMESPACE svc/airgb-frontend-service 8080:80"
