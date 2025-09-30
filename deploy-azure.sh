#!/bin/bash

# Azure deployment script for OSAA MVP
# This script deploys the application to Azure Container Instances

set -e

# Configuration
RESOURCE_GROUP="osaa-data-pipeline"
LOCATION="eastus2"
CONTAINER_NAME="osaa-data-pipeline"
DNS_NAME_LABEL="osaa-data-pipeline"
IMAGE_NAME="osaa-mvp-azure:latest"
ACR_NAME="osaadatapipelineacr"  # Azure Container Registry name

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Azure deployment for OSAA MVP${NC}"

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo -e "${RED}❌ Azure CLI is not installed. Please install it first.${NC}"
    echo "Visit: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli"
    exit 1
fi

# Check if user is logged in
if ! az account show &> /dev/null; then
    echo -e "${YELLOW}⚠️  You are not logged in to Azure CLI. Please log in:${NC}"
    az login
fi

echo -e "${GREEN}✅ Azure CLI is ready${NC}"

# Create resource group if it doesn't exist
echo -e "${YELLOW}📦 Creating resource group...${NC}"
az group create --name $RESOURCE_GROUP --location $LOCATION

# Create Azure Container Registry
echo -e "${YELLOW}📦 Creating Azure Container Registry...${NC}"
az acr create --resource-group $RESOURCE_GROUP --name $ACR_NAME --sku Basic --admin-enabled true

# Get ACR login server
ACR_LOGIN_SERVER=$(az acr show --name $ACR_NAME --resource-group $RESOURCE_GROUP --query loginServer --output tsv)

# Build and push Docker image to ACR
echo -e "${YELLOW}🐳 Building and pushing Docker image to Azure Container Registry...${NC}"
az acr build --registry $ACR_NAME --image $IMAGE_NAME .

# Create container instance
echo -e "${YELLOW}🚀 Deploying container to Azure Container Instances...${NC}"

# Check if .env file exists for environment variables
if [ -f ".env" ]; then
    echo -e "${GREEN}✅ Found .env file, using environment variables from it${NC}"
    # Source environment variables from .env file
    source .env
else
    echo -e "${YELLOW}⚠️  No .env file found. Using default environment variables${NC}"
    echo -e "${YELLOW}   Please update the container with proper Azure credentials after deployment${NC}"
fi

# Deploy container instance
az container create \
    --resource-group $RESOURCE_GROUP \
    --name $CONTAINER_NAME \
    --image $ACR_LOGIN_SERVER/$IMAGE_NAME \
    --cpu 2 \
    --memory 4 \
    --registry-login-server $ACR_LOGIN_SERVER \
    --registry-username $ACR_NAME \
    --registry-password $(az acr credential show --name $ACR_NAME --query passwords[0].value --output tsv) \
    --dns-name-label $DNS_NAME_LABEL \
    --ports 8080 \
    --environment-variables \
        AZURE_STORAGE_CONTAINER_NAME="${AZURE_STORAGE_CONTAINER_NAME:-osaa-data-pipeline}" \
        ENABLE_AZURE_UPLOAD="${ENABLE_AZURE_UPLOAD:-true}" \
        TARGET="${TARGET:-prod}" \
        GATEWAY="${GATEWAY:-local}" \
        DB_PATH="${DB_PATH:-/app/sqlMesh/unosaa_data_pipeline.db}" \
        UI_PORT="${UI_PORT:-8080}" \
    --secure-environment-variables \
        AZURE_STORAGE_CONNECTION_STRING="${AZURE_STORAGE_CONNECTION_STRING}" \
        AZURE_CLIENT_ID="${AZURE_CLIENT_ID}" \
        AZURE_CLIENT_SECRET="${AZURE_CLIENT_SECRET}" \
        AZURE_TENANT_ID="${AZURE_TENANT_ID}" \
        AZURE_STORAGE_ACCOUNT_NAME="${AZURE_STORAGE_ACCOUNT_NAME}"

# Get the public IP and FQDN
echo -e "${YELLOW}🔍 Getting deployment information...${NC}"
PUBLIC_IP=$(az container show --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME --query ipAddress.ip --output tsv)
FQDN=$(az container show --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME --query ipAddress.fqdn --output tsv)

echo -e "${GREEN}🎉 Deployment completed successfully!${NC}"
echo -e "${GREEN}📍 Application URL: http://$FQDN:8080${NC}"
echo -e "${GREEN}📍 Public IP: $PUBLIC_IP${NC}"
echo -e "${GREEN}📍 Resource Group: $RESOURCE_GROUP${NC}"
echo -e "${GREEN}📍 Container Name: $CONTAINER_NAME${NC}"

# Show container status
echo -e "${YELLOW}📊 Container Status:${NC}"
az container show --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME --query instanceView.state --output tsv

echo -e "${YELLOW}📋 Useful commands:${NC}"
echo -e "${YELLOW}   View logs: az container logs --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME${NC}"
echo -e "${YELLOW}   Stop container: az container stop --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME${NC}"
echo -e "${YELLOW}   Delete container: az container delete --resource-group $RESOURCE_GROUP --name $CONTAINER_NAME${NC}"
echo -e "${YELLOW}   Delete resource group: az group delete --name $RESOURCE_GROUP${NC}"

echo -e "${GREEN}✅ Azure deployment completed!${NC}"
