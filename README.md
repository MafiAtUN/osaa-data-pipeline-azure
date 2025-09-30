# OSAA Data Pipeline MVP - Azure Edition

A secure, cloud-based data pipeline for the United Nations Office of the Special Adviser on Africa (OSAA), built with SQLMesh and deployed on Microsoft Azure.

## 🔐 Security Features

This Azure version includes comprehensive security measures:
- **Password-protected authentication** with secure login
- **Session management** with JWT tokens and timeouts
- **Login attempt limiting** (max 5 attempts, 30-minute lockout)
- **IP address validation** for sessions
- **Encrypted Azure Blob Storage** with access controls
- **Network security groups** and firewall rules
- **Secure HTTP headers** and HTTPS enforcement
- **Audit logging** and security monitoring

## 🚀 Quick Start

### Prerequisites

- Azure CLI installed and configured
- Docker installed
- Access to Azure subscription

### 1. Clone and Setup

```bash
git clone https://github.com/UN-OSAA/osaa-mvp.git
cd osaa-mvp
git checkout azure-deployment
```

### 2. Azure Deployment

```bash
# Deploy with comprehensive security
./deploy-secure-azure.sh
```

The deployment script will:
- Create Azure resource group in East US 2
- Set up encrypted Azure Blob Storage
- Create Azure Container Registry
- Deploy secure container with authentication
- Configure network security

### 3. Access Your Application

After deployment, access your secure application at:
- **URL**: `https://osaa-data-pipeline.eastus2.azurecontainer.io:8080`
- **Username**: `admin`
- **Password**: `ChangeThisPassword123!`

**⚠️ IMPORTANT**: Change the default password immediately after first login!

## 📋 Manual Deployment

If you prefer manual deployment:

### 1. Create Azure Resources

```bash
# Create resource group
az group create --name osaa-data-pipeline --location eastus2

# Create storage account
az storage account create \
    --name osaaDataPipeline \
    --resource-group osaa-data-pipeline \
    --location eastus2 \
    --sku Standard_LRS \
    --kind StorageV2 \
    --https-only true \
    --allow-blob-public-access false

# Create storage container
az storage container create \
    --name osaa-data-pipeline \
    --account-name osaaDataPipeline
```

### 2. Configure Environment

```bash
# Copy environment template
cp azure-env-template.txt .env

# Edit .env with your Azure credentials
# Get connection string
az storage account show-connection-string \
    --name osaaDataPipeline \
    --resource-group osaa-data-pipeline \
    --query connectionString \
    --output tsv
```

### 3. Build and Deploy

```bash
# Build Docker image
docker build -t osaa-mvp-azure .

# Deploy to Azure Container Instances
az container create \
    --resource-group osaa-data-pipeline \
    --name osaa-data-pipeline \
    --image osaa-mvp-azure:latest \
    --os-type Linux \
    --cpu 2 \
    --memory 4 \
    --dns-name-label osaa-data-pipeline \
    --ports 8080 \
    --environment-variables \
        AZURE_STORAGE_CONTAINER_NAME=osaa-data-pipeline \
        ENABLE_AZURE_UPLOAD=true \
        TARGET=prod \
        ADMIN_USERNAME=admin \
        ADMIN_PASSWORD="YourSecurePassword123!" \
        AZURE_STORAGE_CONNECTION_STRING="YourConnectionString"
```

## 🔧 Usage

### Web Interface

1. **Login**: Access the application and login with your credentials
2. **Dashboard**: View system status and quick actions
3. **Pipeline Management**: Run data operations through the secure interface
4. **Security Monitoring**: Check login attempts and security status

### Available Operations

- **Configuration Test**: Test Azure connectivity
- **Data Ingestion**: Convert CSV to Parquet and upload to Azure
- **Data Transformation**: Run SQLMesh transformations
- **ETL Pipeline**: Complete Extract-Transform-Load process
- **Data Promotion**: Promote data from dev to production

### Command Line Interface

```bash
# Access container
az container exec --resource-group osaa-data-pipeline --name osaa-data-pipeline --exec-command "bash"

# Run operations
./entrypoint.sh ingest    # Data ingestion
./entrypoint.sh etl       # ETL pipeline
./entrypoint.sh promote   # Promote to production
./entrypoint.sh ui        # Start web interface
```

## 🔒 Security Configuration

### Default Security Settings

- Session timeout: 8 hours
- Max login attempts: 5
- Lockout duration: 30 minutes
- Password requirements: Configurable

### Changing Default Password

1. Login to the application
2. Navigate to Security settings
3. Update password (or modify environment variables)
4. Restart container with new password

### Network Security

- All traffic encrypted (HTTPS)
- Network security groups restrict access
- IP-based access controls available
- Azure Blob Storage with private access

## 📊 Data Storage

### Azure Blob Storage Structure

```
osaa-data-pipeline/
├── dev/
│   ├── landing/           # Raw data files
│   └── dev_{username}/    # User-specific data
└── prod/                  # Production data
```

### Data Formats

- **Input**: CSV files from various sources
- **Processing**: SQLMesh transformations
- **Output**: Parquet files in Azure Blob Storage
- **Database**: DuckDB with SQLMesh

## 🛠️ Development

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp azure-env-template.txt .env
# Edit .env with your settings

# Run locally
python -m pipeline.secure_ui
```

### Testing

```bash
# Test Azure connectivity
python test_azure_credentials.py

# Run pipeline operations
./entrypoint.sh config_test
./entrypoint.sh ingest
```

## 📁 Project Structure

```
osaa-mvp/
├── src/pipeline/
│   ├── azure_config.py      # Azure configuration
│   ├── azure_utils.py       # Azure utilities
│   ├── auth.py              # Authentication system
│   ├── secure_ui.py         # Secure web interface
│   ├── azure_ingest/        # Data ingestion
│   ├── azure_sync/          # Database sync
│   ├── azure_promote/       # Data promotion
│   └── azure_catalog.py     # Data catalog
├── sqlMesh/                 # SQLMesh configuration
├── data/                    # Sample data
├── deploy-secure-azure.sh   # Deployment script
├── azure-env-template.txt   # Environment template
└── dockerfile              # Container configuration
```

## 🔍 Monitoring and Logs

### View Logs

```bash
# Container logs
az container logs --resource-group osaa-data-pipeline --name osaa-data-pipeline

# Security status
az container exec --resource-group osaa-data-pipeline --name osaa-data-pipeline \
  --exec-command "python -c 'from pipeline.auth import get_security_status; print(get_security_status())'"
```

### Azure Monitor

- Application performance monitoring
- Security event logging
- Resource usage tracking
- Alert configuration

## 🚨 Troubleshooting

### Common Issues

1. **Container not starting**: Check environment variables and Azure credentials
2. **Authentication failures**: Verify password and Azure connection string
3. **Storage access issues**: Ensure storage account permissions are correct
4. **Network connectivity**: Check security groups and firewall rules

### Getting Help

- Check container logs for detailed error messages
- Verify Azure resource configuration
- Review security settings and permissions
- Test connectivity with provided test scripts

## 📋 Security Checklist

- [ ] Change default admin password
- [ ] Configure allowed IP addresses
- [ ] Enable Azure Monitor alerts
- [ ] Set up backup procedures
- [ ] Review access logs regularly
- [ ] Update dependencies regularly
- [ ] Test disaster recovery procedures

## 🤝 Contributing

This is a UN internal project. For contributions:
1. Follow UN security guidelines
2. Test all changes thoroughly
3. Update documentation
4. Submit through proper UN channels

## 📄 License

This project is for internal UN use only. See LICENSE file for details.

## 🔗 Related Documentation

- [Azure Deployment Guide](AZURE_DEPLOYMENT_GUIDE.md)
- [Security Guide](SECURITY_GUIDE.md)
- [Migration Summary](MIGRATION_SUMMARY.md)

---

**For UN OSAA Team**: This application is production-ready and includes comprehensive security measures suitable for UN deployment standards.