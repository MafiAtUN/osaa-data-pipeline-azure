# Azure Deployment Guide for OSAA MVP

This guide will help you deploy the OSAA MVP application to Azure using Azure Blob Storage instead of AWS S3.

## Prerequisites

1. **Azure CLI** installed and configured
2. **Docker** installed locally
3. **Azure subscription** with appropriate permissions
4. **Azure Storage Account** created

## Azure Resource Setup

### 1. Create Azure Storage Account

```bash
# Create resource group
az group create --name osaa-data-pipeline --location eastus2

# Create storage account
az storage account create \
    --name osaaDataPipeline \
    --resource-group osaa-data-pipeline \
    --location eastus22 \
    --sku Standard_LRS \
    --kind StorageV2

# Create container
az storage container create \
    --name osaa-data-pipeline \
    --account-name osaaDataPipeline
```

### 2. Get Storage Account Credentials

```bash
# Get connection string
az storage account show-connection-string \
    --name osaaDataPipeline \
    --resource-group osaa-data-pipeline \
    --query connectionString \
    --output tsv

# Get account name
az storage account show \
    --name osaaDataPipeline \
    --resource-group osaa-data-pipeline \
    --query name \
    --output tsv
```

### 3. Create Service Principal (Optional - for production)

```bash
# Create service principal
az ad sp create-for-rbac \
    --name osaa-mvp-sp \
    --role "Storage Blob Data Contributor" \
    --scopes /subscriptions/{subscription-id}/resourceGroups/osaa-mvp-rg/providers/Microsoft.Storage/storageAccounts/osaaDataPipeline
```

## Configuration

### 1. Environment Variables

Copy the Azure environment template and configure it:

```bash
cp azure-env-template.txt .env
```

Update the `.env` file with your Azure credentials:

```bash
# Option 1: Connection String (Recommended for development)
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=osaaDataPipeline;AccountKey=yourkey==;EndpointSuffix=core.windows.net

# Option 2: Service Principal (Recommended for production)
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_TENANT_ID=your-tenant-id
AZURE_STORAGE_ACCOUNT_NAME=osaaDataPipeline

# Azure Blob Storage Settings
AZURE_STORAGE_CONTAINER_NAME=osaa-data-pipeline
ENABLE_AZURE_UPLOAD=true

# Environment Configuration
TARGET=dev
USERNAME=default
GATEWAY=local

# UI Configuration
UI_PORT=8080
```

### 2. Test Azure Credentials

Before deploying, test your Azure credentials:

```bash
python test_azure_credentials.py
```

This script will:
- Validate your Azure credentials
- Test blob storage access
- Upload test files
- Verify read/write permissions

## Deployment Options

### Option 1: Azure Container Instances (Recommended for simplicity)

Use the provided deployment script:

```bash
./deploy-azure.sh
```

This script will:
1. Create a resource group
2. Create an Azure Container Registry
3. Build and push the Docker image
4. Deploy to Azure Container Instances
5. Provide you with the public URL

### Option 2: Manual Azure Container Instances Deployment

```bash
# Build Docker image
docker build -t osaa-mvp-azure .

# Tag for Azure Container Registry
docker tag osaa-mvp-azure yourregistry.azurecr.io/osaa-mvp-azure:latest

# Push to registry
az acr login --name yourregistry
docker push yourregistry.azurecr.io/osaa-mvp-azure:latest

# Deploy to Container Instances
az container create \
    --resource-group osaa-mvp-rg \
    --name osaa-mvp \
    --image yourregistry.azurecr.io/osaa-mvp-azure:latest \
    --cpu 2 \
    --memory 4 \
    --dns-name-label osaa-mvp-azure \
    --ports 8080 \
    --environment-variables \
        AZURE_STORAGE_CONTAINER_NAME=osaa-data-pipeline \
        ENABLE_AZURE_UPLOAD=true \
        TARGET=prod \
        GATEWAY=local
```

### Option 3: Azure App Service (For web applications)

```bash
# Create App Service plan
az appservice plan create \
    --name osaa-mvp-plan \
    --resource-group osaa-mvp-rg \
    --sku B1 \
    --is-linux

# Create web app
az webapp create \
    --resource-group osaa-mvp-rg \
    --plan osaa-mvp-plan \
    --name osaa-mvp-app \
    --deployment-container-image-name yourregistry.azurecr.io/osaa-mvp-azure:latest

# Configure app settings
az webapp config appsettings set \
    --resource-group osaa-mvp-rg \
    --name osaa-mvp-app \
    --settings \
        AZURE_STORAGE_CONTAINER_NAME=osaa-data-pipeline \
        ENABLE_AZURE_UPLOAD=true \
        TARGET=prod
```

## Data Migration from AWS S3 (If Applicable)

If you have existing data in AWS S3, you can migrate it to Azure Blob Storage:

### Using AzCopy

```bash
# Install AzCopy (if not already installed)
# Download from: https://docs.microsoft.com/en-us/azure/storage/common/storage-use-azcopy-v10

# Set AWS credentials
export AWS_ACCESS_KEY_ID=your-access-key
export AWS_SECRET_ACCESS_KEY=your-secret-key

# Copy data from S3 to Azure
azcopy copy "https://s3.amazonaws.com/your-s3-bucket/" \
    "https://osaaDataPipeline.blob.core.windows.net/osaa-data-pipeline/" \
    --recursive
```

### Using Azure Data Factory (For large datasets)

1. Create an Azure Data Factory
2. Create a linked service for AWS S3
3. Create a linked service for Azure Blob Storage
4. Create a pipeline to copy data

## Local Development

### 1. Run Locally with Docker

```bash
# Build the image
docker build -t osaa-mvp-azure .

# Run with Azure configuration
docker run -d \
    --name osaa-mvp-local \
    -p 8080:8080 \
    --env-file .env \
    osaa-mvp-azure

# Run specific commands
docker exec osaa-mvp-local /app/entrypoint.sh ingest
docker exec osaa-mvp-local /app/entrypoint.sh etl
docker exec osaa-mvp-local /app/entrypoint.sh ui
```

### 2. Run Individual Components

```bash
# Data ingestion
docker compose run --rm pipeline ingest

# ETL pipeline
docker compose run --rm pipeline etl

# SQLMesh UI
docker compose run --rm pipeline ui

# Configuration test
docker compose run --rm pipeline config_test
```

## Monitoring and Management

### View Logs

```bash
# Azure Container Instances
az container logs --resource-group osaa-mvp-rg --name osaa-mvp

# Local Docker
docker logs osaa-mvp-local
```

### Scale Container

```bash
# Update container with more resources
az container create \
    --resource-group osaa-mvp-rg \
    --name osaa-mvp \
    --image yourregistry.azurecr.io/osaa-mvp-azure:latest \
    --cpu 4 \
    --memory 8 \
    --dns-name-label osaa-mvp-azure \
    --ports 8080
```

### Update Application

```bash
# Build new image
docker build -t osaa-mvp-azure:latest .

# Push to registry
docker push yourregistry.azurecr.io/osaa-mvp-azure:latest

# Restart container
az container restart --resource-group osaa-mvp-rg --name osaa-mvp
```

## Security Considerations

### 1. Use Managed Identity (Recommended for production)

```bash
# Enable managed identity for container
az container create \
    --resource-group osaa-mvp-rg \
    --name osaa-mvp \
    --assign-identity \
    --image yourregistry.azurecr.io/osaa-mvp-azure:latest \
    --environment-variables \
        AZURE_STORAGE_ACCOUNT_NAME=osaaDataPipeline
```

### 2. Use Key Vault for Secrets

```bash
# Create Key Vault
az keyvault create \
    --name osaa-mvp-kv \
    --resource-group osaa-mvp-rg \
    --location eastus2

# Store connection string
az keyvault secret set \
    --vault-name osaa-mvp-kv \
    --name storage-connection-string \
    --value "your-connection-string"
```

### 3. Network Security

- Use private endpoints for storage account
- Configure network rules for storage account
- Use Azure Front Door for public access

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify Azure credentials
   - Check service principal permissions
   - Ensure storage account exists

2. **Container Won't Start**
   - Check container logs
   - Verify environment variables
   - Ensure image is pushed to registry

3. **Blob Storage Access Issues**
   - Verify container name
   - Check storage account permissions
   - Test with Azure Storage Explorer

### Debug Commands

```bash
# Test Azure connectivity
az storage account show --name osaaDataPipeline

# List containers
az storage container list --account-name osaaDataPipeline

# Check container logs
az container logs --resource-group osaa-mvp-rg --name osaa-mvp

# Execute commands in container
az container exec --resource-group osaa-mvp-rg --name osaa-mvp --exec-command "/bin/bash"
```

## Cost Optimization

### 1. Use Spot Instances

```bash
# Deploy with spot instance
az container create \
    --resource-group osaa-mvp-rg \
    --name osaa-mvp \
    --image yourregistry.azurecr.io/osaa-mvp-azure:latest \
    --priority Spot
```

### 2. Auto-shutdown

```bash
# Create auto-shutdown schedule
az resource update \
    --resource-group osaa-mvp-rg \
    --name osaa-mvp \
    --resource-type Microsoft.ContainerInstance/containerGroups \
    --set properties.restartPolicy=Never
```

### 3. Storage Optimization

- Use appropriate storage tier (Hot/Cool/Archive)
- Enable lifecycle management
- Use compression for large files

## Support and Resources

- [Azure Container Instances Documentation](https://docs.microsoft.com/en-us/azure/container-instances/)
- [Azure Blob Storage Documentation](https://docs.microsoft.com/en-us/azure/storage/blobs/)
- [Azure CLI Reference](https://docs.microsoft.com/en-us/cli/azure/)
- [Docker Documentation](https://docs.docker.com/)

## Migration Checklist

- [ ] Azure Storage Account created
- [ ] Container created in storage account
- [ ] Environment variables configured
- [ ] Azure credentials tested
- [ ] Docker image built and tested locally
- [ ] Application deployed to Azure
- [ ] Data migrated (if applicable)
- [ ] Monitoring configured
- [ ] Security settings applied
- [ ] Documentation updated

---

For additional support, please refer to the project documentation or contact the development team.
