#!/bin/bash

# Script to delete all Germany West Azure resources
# WARNING: This will permanently delete resources! Make sure migration is complete first!

set -e

echo "=================================================="
echo "DELETE GERMANY WEST AZURE RESOURCES"
echo "=================================================="

# Configuration
LOCATION="germanywestcentral"
GERMANY_RG="rg-bpchat"
GERMANY_ACR="bpchatregistry"

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

# List all Germany West resources
list_germany_resources() {
    print_status "Listing all resources in Germany West Central..."
    
    echo ""
    print_status "Resource Groups in Germany West:"
    az group list --query "[?location=='$LOCATION'].{Name:name, Location:location}" --output table
    
    echo ""
    print_status "Container Registries in Germany West:"
    az acr list --query "[?location=='$LOCATION'].{Name:name, ResourceGroup:resourceGroup}" --output table
    
    echo ""
    print_status "Container Instances in Germany West:"
    az container list --query "[?location=='$LOCATION'].{Name:name, ResourceGroup:resourceGroup}" --output table
    
    echo ""
    print_status "Storage Accounts in Germany West:"
    az storage account list --query "[?location=='$LOCATION'].{Name:name, ResourceGroup:resourceGroup}" --output table
    
    echo ""
    print_status "All resources in $GERMANY_RG resource group:"
    az resource list --resource-group $GERMANY_RG --output table 2>/dev/null || echo "Resource group not found or empty"
}

# Delete Container Instances
delete_container_instances() {
    print_status "Checking for Container Instances..."
    
    CONTAINERS=$(az container list --query "[?location=='$LOCATION'].{name:name, rg:resourceGroup}" -o tsv)
    
    if [ -z "$CONTAINERS" ]; then
        print_status "No container instances found in Germany West"
        return
    fi
    
    echo "$CONTAINERS" | while IFS=$'\t' read -r name rg; do
        print_warning "Deleting container instance: $name in $rg"
        if az container delete --name "$name" --resource-group "$rg" --yes; then
            print_status "✅ Deleted: $name"
        else
            print_error "❌ Failed to delete: $name"
        fi
    done
}

# Delete Storage Accounts
delete_storage_accounts() {
    print_status "Checking for Storage Accounts..."
    
    STORAGE_ACCOUNTS=$(az storage account list --query "[?location=='$LOCATION'].{name:name, rg:resourceGroup}" -o tsv)
    
    if [ -z "$STORAGE_ACCOUNTS" ]; then
        print_status "No storage accounts found in Germany West"
        return
    fi
    
    echo "$STORAGE_ACCOUNTS" | while IFS=$'\t' read -r name rg; do
        print_warning "Deleting storage account: $name in $rg"
        if az storage account delete --name "$name" --resource-group "$rg" --yes; then
            print_status "✅ Deleted: $name"
        else
            print_error "❌ Failed to delete: $name"
        fi
    done
}

# Delete Container Registry
delete_container_registry() {
    print_status "Checking for Container Registry..."
    
    if az acr show --name $GERMANY_ACR --resource-group $GERMANY_RG &>/dev/null; then
        print_warning "Deleting container registry: $GERMANY_ACR"
        if az acr delete --name $GERMANY_ACR --resource-group $GERMANY_RG --yes; then
            print_status "✅ Deleted ACR: $GERMANY_ACR"
        else
            print_error "❌ Failed to delete ACR: $GERMANY_ACR"
        fi
    else
        print_status "Container registry $GERMANY_ACR not found"
    fi
}

# Delete Resource Groups
delete_resource_groups() {
    print_status "Checking for Resource Groups in Germany West..."
    
    # First, try to delete the known Agent-Chat resource group
    if az group show --name $GERMANY_RG &>/dev/null; then
        LOCATION_CHECK=$(az group show --name $GERMANY_RG --query location -o tsv)
        if [ "$LOCATION_CHECK" == "$LOCATION" ]; then
            print_warning "Deleting resource group: $GERMANY_RG"
            if az group delete --name $GERMANY_RG --yes --no-wait; then
                print_status "✅ Started deletion of resource group: $GERMANY_RG (running in background)"
            else
                print_error "❌ Failed to delete resource group: $GERMANY_RG"
            fi
        else
            print_status "Resource group $GERMANY_RG is not in Germany West (it's in $LOCATION_CHECK)"
        fi
    else
        print_status "Resource group $GERMANY_RG not found"
    fi
    
    # Check for any other resource groups in Germany West
    OTHER_RGS=$(az group list --query "[?location=='$LOCATION' && name!='$GERMANY_RG'].name" -o tsv)
    
    if [ ! -z "$OTHER_RGS" ]; then
        echo ""
        print_warning "Found other resource groups in Germany West:"
        echo "$OTHER_RGS"
        echo ""
        read -p "Do you want to delete these as well? (y/n): " -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "$OTHER_RGS" | while read -r rg; do
                print_warning "Deleting resource group: $rg"
                if az group delete --name "$rg" --yes --no-wait; then
                    print_status "✅ Started deletion of: $rg"
                else
                    print_error "❌ Failed to delete: $rg"
                fi
            done
        fi
    fi
}

# Verify deletion
verify_deletion() {
    print_status "Verifying resource deletion..."
    
    sleep 5  # Give Azure a moment to process
    
    echo ""
    print_status "Remaining resources in Germany West:"
    
    REMAINING_RGS=$(az group list --query "[?location=='$LOCATION'].name" -o tsv)
    REMAINING_ACRS=$(az acr list --query "[?location=='$LOCATION'].name" -o tsv)
    REMAINING_CONTAINERS=$(az container list --query "[?location=='$LOCATION'].name" -o tsv)
    REMAINING_STORAGE=$(az storage account list --query "[?location=='$LOCATION'].name" -o tsv)
    
    if [ -z "$REMAINING_RGS" ] && [ -z "$REMAINING_ACRS" ] && [ -z "$REMAINING_CONTAINERS" ] && [ -z "$REMAINING_STORAGE" ]; then
        print_status "✅ All Germany West resources have been deleted or are being deleted"
    else
        print_warning "Some resources may still be deleting (this can take several minutes):"
        [ ! -z "$REMAINING_RGS" ] && echo "  - Resource Groups: $REMAINING_RGS"
        [ ! -z "$REMAINING_ACRS" ] && echo "  - Container Registries: $REMAINING_ACRS"
        [ ! -z "$REMAINING_CONTAINERS" ] && echo "  - Container Instances: $REMAINING_CONTAINERS"
        [ ! -z "$REMAINING_STORAGE" ] && echo "  - Storage Accounts: $REMAINING_STORAGE"
        echo ""
        print_status "Run 'az group delete --name <resource-group> --yes' to delete remaining resource groups"
    fi
}

# Main execution
main() {
    echo ""
    print_error "⚠️  WARNING: This script will PERMANENTLY DELETE all Germany West resources!"
    print_warning "Make sure you have:"
    print_warning "  1. Migrated all container images to Sweden Central"
    print_warning "  2. Updated all K8s deployments to use the new registry"
    print_warning "  3. Verified the application works from Sweden Central"
    echo ""
    
    check_azure_login
    
    echo ""
    print_status "Current Germany West resources:"
    list_germany_resources
    
    echo ""
    print_error "THIS ACTION CANNOT BE UNDONE!"
    read -p "Are you SURE you want to delete all Germany West resources? Type 'DELETE' to confirm: " CONFIRM
    
    if [ "$CONFIRM" != "DELETE" ]; then
        print_warning "Deletion cancelled. You must type 'DELETE' to confirm."
        exit 0
    fi
    
    echo ""
    print_status "Starting deletion process..."
    
    # Delete resources in order (least dependent first)
    echo ""
    print_status "Step 1: Deleting Container Instances..."
    delete_container_instances
    
    echo ""
    print_status "Step 2: Deleting Storage Accounts..."
    delete_storage_accounts
    
    echo ""
    print_status "Step 3: Deleting Container Registry..."
    delete_container_registry
    
    echo ""
    print_status "Step 4: Deleting Resource Groups..."
    delete_resource_groups
    
    echo ""
    print_status "Step 5: Verification..."
    verify_deletion
    
    echo ""
    print_status "🎉 Germany West cleanup completed!"
    print_warning "Note: Resource group deletion runs in the background and may take several minutes to complete."
    print_status "You can check the status with: az group list --query \"[?location=='$LOCATION'].name\" -o table"
}

# Run main function
main
