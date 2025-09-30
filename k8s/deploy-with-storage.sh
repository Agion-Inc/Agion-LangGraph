#!/bin/bash

# Configuration
NAMESPACE="agion-airgb"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Deploying AIRGB with Persistent Storage...${NC}"
echo ""

# Create persistent volume claims
echo -e "${YELLOW}💾 Creating persistent volume claims...${NC}"
kubectl apply -f persistent-volume.yaml

# Wait for PVCs to be bound
echo -e "${YELLOW}⏳ Waiting for storage to be provisioned...${NC}"
kubectl wait --for=condition=Bound pvc/airgb-storage-pvc -n $NAMESPACE --timeout=60s
kubectl wait --for=condition=Bound pvc/airgb-database-pvc -n $NAMESPACE --timeout=60s

# Check if backend has existing data we need to backup
echo -e "${YELLOW}📦 Checking for existing data...${NC}"
POD_NAME=$(kubectl get pod -n $NAMESPACE -l app=airgb-backend -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

if [ -n "$POD_NAME" ]; then
    echo -e "${YELLOW}📋 Backing up existing database...${NC}"
    kubectl cp $NAMESPACE/$POD_NAME:/app/data/bpchat.db /tmp/bpchat-backup.db 2>/dev/null || echo "No existing database to backup"
    
    echo -e "${YELLOW}📁 Listing existing uploaded files...${NC}"
    kubectl exec -n $NAMESPACE $POD_NAME -- find /app/uploads -type f 2>/dev/null | head -20 || echo "No uploaded files found"
fi

# Apply the updated backend deployment
echo -e "${GREEN}🔧 Updating backend deployment with persistent storage...${NC}"
kubectl apply -f backend-deployment.yaml

# Wait for rollout
echo -e "${YELLOW}⏳ Waiting for backend rollout...${NC}"
kubectl rollout status deployment/airgb-backend -n $NAMESPACE --timeout=300s

# Restore database if we have a backup
if [ -f "/tmp/bpchat-backup.db" ]; then
    echo -e "${YELLOW}📥 Restoring database backup...${NC}"
    NEW_POD=$(kubectl get pod -n $NAMESPACE -l app=airgb-backend -o jsonpath='{.items[0].metadata.name}')
    kubectl cp /tmp/bpchat-backup.db $NAMESPACE/$NEW_POD:/app/data/bpchat.db
    echo -e "${GREEN}✅ Database restored${NC}"
fi

echo ""
echo -e "${GREEN}✅ Deployment complete with persistent storage!${NC}"
echo ""

# Show storage status
echo -e "${YELLOW}📊 Storage Status:${NC}"
kubectl get pvc -n $NAMESPACE
echo ""

# Show pod status
echo -e "${YELLOW}🔍 Pod Status:${NC}"
kubectl get pods -n $NAMESPACE
echo ""

echo -e "${GREEN}📝 Notes:${NC}"
echo "  • Database is now persistent at /app/data/ (5GB)"
echo "  • Uploaded files are now persistent at /app/uploads/ (10GB)"
echo "  • Data will survive pod restarts and redeployments"
echo "  • Storage is using Azure Premium SSD for performance"
echo ""
echo -e "${YELLOW}⚠️  Important:${NC}"
echo "  • Only one backend pod can run at a time (SQLite limitation)"
echo "  • To scale, consider migrating to PostgreSQL"
echo "  • Regular backups are recommended"
