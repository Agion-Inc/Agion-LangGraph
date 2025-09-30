#!/bin/bash

# Migration script for moving ACR images from Germany West to Sweden Central
# This ensures no data loss before cleaning up Germany West resources

set -e

echo "=================================================="
echo "ACR Migration: Germany West -> Sweden Central"
echo "=================================================="

# Configuration
GERMANY_RG="rg-bpchat"
GERMANY_ACR="bpchatregistry"
SWEDEN_RG=""  # Will be detected automatically
SWEDEN_ACR=""  # Will be detected automatically
LOCATION="swedencentral"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if logged in to Azure
check_azure_login() {
    print_status "Checking Azure login status..."
    if ! az account show &>/dev/null; then
        print_error "Not logged in to Azure. Please run: az login"
        exit 1
    fi
    print_status "Azure login confirmed"
}

# List all images in Germany West ACR
list_germany_images() {
    print_status "Listing images in Germany West ACR ($GERMANY_ACR)..."
    
    if ! az acr repository list --name $GERMANY_ACR --resource-group $GERMANY_RG &>/dev/null; then
        print_warning "Germany West ACR not found or not accessible"
        return 1
    fi
    
    IMAGES=$(az acr repository list --name $GERMANY_ACR --resource-group $GERMANY_RG --output tsv)
    
    if [ -z "$IMAGES" ]; then
        print_warning "No images found in Germany West ACR"
        return 1
    fi
    
    echo "Found images:"
    echo "$IMAGES" | while IFS= read -r image; do
        echo "  - $image"
        # Get all tags for this image
        TAGS=$(az acr repository show-tags --name $GERMANY_ACR --repository $image --resource-group $GERMANY_RG --output tsv)
        for tag in $TAGS; do
            echo "    • $image:$tag"
        done
    done
    
    return 0
}

# Find existing Sweden Central ACR
find_sweden_acr() {
    print_status "Finding existing ACR in Sweden Central..."
    
    # List all ACRs in Sweden Central
    SWEDEN_ACRS=$(az acr list --query "[?location=='$LOCATION'].{name:name, rg:resourceGroup}" -o tsv)
    
    if [ -z "$SWEDEN_ACRS" ]; then
        print_error "No ACR found in Sweden Central"
        print_error "Please create an ACR in Sweden Central first"
        exit 1
    fi
    
    echo "Found ACRs in Sweden Central:"
    echo "$SWEDEN_ACRS" | while IFS=$'\t' read -r name rg; do
        echo "  - $name (Resource Group: $rg)"
    done
    
    # Use the first one found
    SWEDEN_ACR=$(echo "$SWEDEN_ACRS" | head -n1 | cut -f1)
    SWEDEN_RG=$(echo "$SWEDEN_ACRS" | head -n1 | cut -f2)
    
    print_status "Using ACR: $SWEDEN_ACR in Resource Group: $SWEDEN_RG"
    
    # Verify the ACR exists and get details
    if ! az acr show --name $SWEDEN_ACR --resource-group $SWEDEN_RG &>/dev/null; then
        print_error "Failed to access ACR: $SWEDEN_ACR"
        exit 1
    fi
    
    # Get ACR credentials
    print_status "Getting ACR credentials..."
    SWEDEN_ACR_LOGIN_SERVER=$(az acr show --name $SWEDEN_ACR --resource-group $SWEDEN_RG --query loginServer -o tsv)
    echo "Sweden ACR Login Server: $SWEDEN_ACR_LOGIN_SERVER"
    
    # Enable admin user if not already enabled
    ADMIN_ENABLED=$(az acr show --name $SWEDEN_ACR --resource-group $SWEDEN_RG --query adminUserEnabled -o tsv)
    if [ "$ADMIN_ENABLED" != "true" ]; then
        print_status "Enabling admin user on ACR..."
        az acr update --name $SWEDEN_ACR --resource-group $SWEDEN_RG --admin-enabled true
    fi
}

# Import images from Germany to Sweden
import_images() {
    print_status "Starting image migration..."
    
    # Get Germany ACR login server
    GERMANY_ACR_LOGIN_SERVER=$(az acr show --name $GERMANY_ACR --resource-group $GERMANY_RG --query loginServer -o tsv)
    
    # Get list of repositories
    IMAGES=$(az acr repository list --name $GERMANY_ACR --resource-group $GERMANY_RG --output tsv)
    
    if [ -z "$IMAGES" ]; then
        print_warning "No images to migrate"
        return 0
    fi
    
    # Track migration status
    MIGRATED=0
    FAILED=0
    
    echo "$IMAGES" | while IFS= read -r image; do
        # Get all tags for this repository
        TAGS=$(az acr repository show-tags --name $GERMANY_ACR --repository $image --resource-group $GERMANY_RG --output tsv)
        
        for tag in $TAGS; do
            SOURCE_IMAGE="$GERMANY_ACR_LOGIN_SERVER/$image:$tag"
            TARGET_IMAGE="$image:$tag"
            
            print_status "Migrating $SOURCE_IMAGE -> $SWEDEN_ACR/$TARGET_IMAGE"
            
            # Use ACR import to copy image directly between registries
            if az acr import \
                --name $SWEDEN_ACR \
                --resource-group $SWEDEN_RG \
                --source $SOURCE_IMAGE \
                --image $TARGET_IMAGE \
                --registry $GERMANY_ACR \
                --force 2>/dev/null; then
                print_status "✅ Successfully migrated: $image:$tag"
                ((MIGRATED++))
            else
                print_error "❌ Failed to migrate: $image:$tag"
                ((FAILED++))
            fi
        done
    done
    
    echo ""
    print_status "Migration Summary:"
    echo "  ✅ Migrated: $MIGRATED images"
    if [ $FAILED -gt 0 ]; then
        echo "  ❌ Failed: $FAILED images"
    fi
}

# Update K8s deployments to use new registry
update_k8s_deployments() {
    print_status "Updating K8s deployment files to use Sweden ACR..."
    
    K8S_DIR="/Users/mikko/Documents/Github/RG-Brands/Agent-Chat/k8s"
    OLD_REGISTRY="$GERMANY_ACR.azurecr.io"
    NEW_REGISTRY="$SWEDEN_ACR.azurecr.io"
    
    if [ -d "$K8S_DIR" ]; then
        print_status "Updating registry references in K8s files..."
        
        # Find all YAML files and update registry references
        find "$K8S_DIR" -name "*.yaml" -o -name "*.yml" | while read -r file; do
            if grep -q "$OLD_REGISTRY" "$file"; then
                print_status "Updating: $(basename $file)"
                sed -i.bak "s|$OLD_REGISTRY|$NEW_REGISTRY|g" "$file"
            fi
        done
        
        # Also check deployment scripts
        DEPLOY_SCRIPTS=(
            "/Users/mikko/Documents/Github/RG-Brands/Agent-Chat/deploy-to-aks.sh"
            "/Users/mikko/Documents/Github/RG-Brands/Agent-Chat/backend/deploy-to-aks-airgb.sh"
        )
        
        for script in "${DEPLOY_SCRIPTS[@]}"; do
            if [ -f "$script" ] && grep -q "$OLD_REGISTRY" "$script"; then
                print_status "Updating: $(basename $script)"
                sed -i.bak "s|$OLD_REGISTRY|$NEW_REGISTRY|g" "$script"
            fi
        done
        
        print_status "K8s files updated. Backup files created with .bak extension"
    else
        print_warning "K8s directory not found: $K8S_DIR"
    fi
}

# Create ACR secret for K8s
create_acr_secret() {
    print_status "Creating ACR secret for Kubernetes..."
    
    # Get Sweden ACR credentials
    SWEDEN_ACR_USERNAME=$(az acr credential show --name $SWEDEN_ACR --resource-group $SWEDEN_RG --query username -o tsv)
    SWEDEN_ACR_PASSWORD=$(az acr credential show --name $SWEDEN_ACR --resource-group $SWEDEN_RG --query passwords[0].value -o tsv)
    SWEDEN_ACR_LOGIN_SERVER=$(az acr show --name $SWEDEN_ACR --resource-group $SWEDEN_RG --query loginServer -o tsv)
    
    cat <<EOF > /tmp/acr-secret-sweden.yaml
apiVersion: v1
kind: Secret
metadata:
  name: acr-secret
  namespace: agion-airgb
type: kubernetes.io/dockerconfigjson
data:
  .dockerconfigjson: $(echo -n "{\"auths\":{\"$SWEDEN_ACR_LOGIN_SERVER\":{\"username\":\"$SWEDEN_ACR_USERNAME\",\"password\":\"$SWEDEN_ACR_PASSWORD\"}}}" | base64)
EOF
    
    print_status "ACR secret YAML created at: /tmp/acr-secret-sweden.yaml"
    echo ""
    print_warning "To apply this secret to your AKS cluster, run:"
    echo "kubectl apply -f /tmp/acr-secret-sweden.yaml"
}

# Verify migration
verify_migration() {
    print_status "Verifying migration..."
    
    print_status "Images in Sweden Central ACR:"
    az acr repository list --name $SWEDEN_ACR --resource-group $SWEDEN_RG --output table
    
    echo ""
    print_status "To test the new images, you can:"
    echo "1. Update your AKS cluster to use the new registry"
    echo "2. Apply the new ACR secret: kubectl apply -f /tmp/acr-secret-sweden.yaml"
    echo "3. Restart your deployments: kubectl rollout restart deployment -n agion-airgb"
}

# Main execution
main() {
    echo ""
    check_azure_login
    
    echo ""
    print_status "Step 1: Checking Germany West ACR..."
    if ! list_germany_images; then
        print_warning "No images found in Germany West. Skipping migration."
        exit 0
    fi
    
    echo ""
    read -p "Do you want to proceed with migration? (y/n): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_warning "Migration cancelled"
        exit 0
    fi
    
    echo ""
    print_status "Step 2: Finding Sweden Central ACR..."
    find_sweden_acr
    
    echo ""
    print_status "Step 3: Migrating images..."
    import_images
    
    echo ""
    print_status "Step 4: Updating K8s deployments..."
    update_k8s_deployments
    
    echo ""
    print_status "Step 5: Creating ACR secret for K8s..."
    create_acr_secret
    
    echo ""
    print_status "Step 6: Verification..."
    verify_migration
    
    echo ""
    print_status "🎉 Migration completed!"
    print_warning "⚠️  DO NOT delete Germany West resources until you've verified everything works from Sweden Central"
    echo ""
    echo "Next steps:"
    echo "1. Apply the new ACR secret to AKS"
    echo "2. Deploy the updated K8s manifests"
    echo "3. Verify the application works"
    echo "4. Only then run: ./delete-germany-west-resources.sh"
}

# Run main function
main
