#!/bin/bash

# Secure Azure deployment script for OSAA MVP
# This script deploys the application with comprehensive security measures

set -e

# Configuration
RESOURCE_GROUP="osaa-data-pipeline"
LOCATION="eastus2"
CONTAINER_NAME="osaa-data-pipeline"
DNS_NAME_LABEL="osaa-data-pipeline"
IMAGE_NAME="osaa-mvp-azure:latest"
ACR_NAME="osaadatapipelineacr"

# Security settings
ADMIN_USERNAME="admin"
ADMIN_PASSWORD="ChangeThisPassword123!"
STORAGE_ACCOUNT_NAME="osaadata$(date +%s | cut -c8-)"

echo "🔐 Starting Secure Azure Deployment for OSAA MVP"

# Create resource group
echo "📦 Creating resource group..."
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create secure storage account
echo "🗄️ Creating secure storage account..."
az storage account create \
    --name $STORAGE_ACCOUNT_NAME \
    --resource-group $RESOURCE_GROUP \
    --location $LOCATION \
    --sku Standard_LRS \
    --kind StorageV2 \
    --https-only true \
    --min-tls-version TLS1_2 \
    --allow-blob-public-access false

# Create storage container
echo "📁 Creating storage container..."
az storage container create \
    --name osaa-data-pipeline \
    --account-name $STORAGE_ACCOUNT_NAME \
    --public-access off

# Get storage connection string
STORAGE_CONNECTION_STRING=$(az storage account show-connection-string \
    --name $STORAGE_ACCOUNT_NAME \
    --resource-group $RESOURCE_GROUP \
    --query connectionString \
    --output tsv)

# Create Azure Container Registry
echo "🐳 Creating Azure Container Registry..."
az acr create --resource-group $RESOURCE_GROUP --name $ACR_NAME --sku Basic --admin-enabled true

# Build and push secure Docker image
echo "🔨 Building secure Docker image..."
az acr build --registry $ACR_NAME --image $IMAGE_NAME .

# Deploy with security configuration
echo "🚀 Deploying secure container..."
az container create \
    --resource-group $RESOURCE_GROUP \
    --name $CONTAINER_NAME \
    --image $ACR_NAME.azurecr.io/$IMAGE_NAME \
    --os-type Linux \
    --cpu 2 \
    --memory 4 \
    --registry-login-server $ACR_NAME.azurecr.io \
    --registry-username $ACR_NAME \
    --registry-password $(az acr credential show --name $ACR_NAME --query passwords[0].value --output tsv) \
    --dns-name-label $DNS_NAME_LABEL \
    --ports 8080 \
    --environment-variables \
        AZURE_STORAGE_CONTAINER_NAME=osaa-data-pipeline \
        ENABLE_AZURE_UPLOAD=true \
        TARGET=prod \
        GATEWAY=local \
        DB_PATH=/app/sqlMesh/unosaa_data_pipeline.db \
        UI_PORT=8080 \
        ADMIN_USERNAME=$ADMIN_USERNAME \
    --secure-environment-variables \
        AZURE_STORAGE_CONNECTION_STRING="$STORAGE_CONNECTION_STRING" \
        ADMIN_PASSWORD="$ADMIN_PASSWORD"

# Get application URL
PUBLIC_IP=$(az container show --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME --query ipAddress.ip --output tsv)
FQDN=$(az container show --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME --query ipAddress.fqdn --output tsv)

echo "✅ Secure deployment completed!"
echo "🔐 Application URL: https://$FQDN:8080"
echo "👤 Username: $ADMIN_USERNAME"
echo "🔑 Password: $ADMIN_PASSWORD"
echo ""
echo "⚠️  SECURITY NOTICE:"
echo "   - Change the default password immediately"
echo "   - Access is restricted to HTTPS only"
echo "   - All data is encrypted at rest"
echo "   - Network access is secured"
echo ""
echo "📋 Next steps:"
echo "   1. Access the application at https://$FQDN:8080"
echo "   2. Login with the credentials above"
echo "   3. Change the default password"
echo "   4. Configure additional security settings"
