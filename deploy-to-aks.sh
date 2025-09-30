#!/bin/bash

# Configuration
RESOURCE_GROUP="agion-platform-prod"
AKS_NAME="agion-mvp-mvp-aks"
ACR_NAME="bpchatregistry"
NAMESPACE="agion-airgb"

echo "🚀 Deploying AIRGB to AKS cluster..."

# Get AKS credentials
echo "📥 Getting AKS credentials..."
az aks get-credentials --resource-group $RESOURCE_GROUP --name $AKS_NAME --overwrite-existing

# Create namespace
echo "📦 Creating namespace..."
kubectl apply -f k8s/namespace.yaml

# Create ACR pull secret
echo "🔐 Creating ACR pull secret..."
kubectl delete secret acr-secret -n $NAMESPACE --ignore-not-found
kubectl create secret docker-registry acr-secret \
    --namespace=$NAMESPACE \
    --docker-server=${ACR_NAME}.azurecr.io \
    --docker-username=$ACR_NAME \
    --docker-password=$(az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)

# Deploy backend
echo "🔧 Deploying backend..."
kubectl apply -f k8s/backend-deployment.yaml

# Deploy frontend
echo "🎨 Deploying frontend..."
kubectl apply -f k8s/frontend-deployment.yaml

# Deploy ingress
echo "🌐 Deploying ingress..."
kubectl apply -f k8s/ingress.yaml

# Wait for deployments
echo "⏳ Waiting for deployments to be ready..."
kubectl rollout status deployment/airgb-backend -n $NAMESPACE --timeout=300s
kubectl rollout status deployment/airgb-frontend -n $NAMESPACE --timeout=300s

# Get status
echo "✅ Deployment complete!"
echo ""
echo "📊 Deployment Status:"
kubectl get all -n $NAMESPACE
echo ""
echo "🌐 Ingress Status:"
kubectl get ingress -n $NAMESPACE
echo ""
echo "🔗 Application will be available at:"
echo "   https://airgb.agion.dev"
echo ""
echo "📝 Note: DNS propagation may take a few minutes"
echo "   Make sure airgb.agion.dev points to 20.240.91.78"
echo ""
echo "📋 To check logs:"
echo "   kubectl logs -f deployment/airgb-backend -n $NAMESPACE"
echo "   kubectl logs -f deployment/airgb-frontend -n $NAMESPACE"
echo ""
echo "🔄 To update deployment:"
echo "   kubectl rollout restart deployment/airgb-backend -n $NAMESPACE"
echo "   kubectl rollout restart deployment/airgb-frontend -n $NAMESPACE"
