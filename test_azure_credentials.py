#!/usr/bin/env python3

import os
import logging
from datetime import datetime
import pandas as pd
import tempfile
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file in the current directory
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
logger.info(f"Loading .env file from: {env_path}")
load_dotenv(env_path, override=True)

def create_test_parquet():
    """Create a test Parquet file with sample data"""
    # Create sample data
    data = {
        'id': range(1, 6),
        'name': ['Test1', 'Test2', 'Test3', 'Test4', 'Test5'],
        'value': [10.5, 20.0, 30.7, 40.2, 50.9],
        'timestamp': [datetime.now()] * 5
    }
    df = pd.DataFrame(data)
    
    # Create a temporary file
    temp_file = tempfile.NamedTemporaryFile(suffix='.parquet', delete=False)
    
    # Write DataFrame to Parquet file
    df.to_parquet(temp_file.name, engine='pyarrow')
    
    return temp_file.name

def test_azure_credentials():
    """Test Azure credentials and blob storage access"""
    try:
        from azure.storage.blob import BlobServiceClient
        from azure.identity import DefaultAzureCredential, ClientSecretCredential
        from azure.core.exceptions import AzureError, ResourceNotFoundError
        
        logger.info("Testing Azure credentials...")
        
        # Get configuration
        connection_string = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
        client_id = os.getenv('AZURE_CLIENT_ID')
        client_secret = os.getenv('AZURE_CLIENT_SECRET')
        tenant_id = os.getenv('AZURE_TENANT_ID')
        account_name = os.getenv('AZURE_STORAGE_ACCOUNT_NAME')
        container_name = os.getenv('AZURE_STORAGE_CONTAINER_NAME', 'osaa-data-pipeline')
        
        logger.info(f"Account Name: {account_name}")
        logger.info(f"Container Name: {container_name}")
        logger.info(f"Client ID: {'*' * 16 + client_id[-4:] if client_id else 'Not Set'}")
        logger.info(f"Tenant ID: {tenant_id}")
        
        # Initialize blob service client
        if connection_string:
            logger.info("Using connection string authentication")
            blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        elif client_id and client_secret and tenant_id:
            logger.info("Using service principal authentication")
            credential = ClientSecretCredential(tenant_id, client_id, client_secret)
            blob_service_client = BlobServiceClient(
                account_url=f"https://{account_name}.blob.core.windows.net",
                credential=credential
            )
        else:
            logger.info("Using default Azure credentials")
            credential = DefaultAzureCredential()
            blob_service_client = BlobServiceClient(
                account_url=f"https://{account_name}.blob.core.windows.net",
                credential=credential
            )
        
        # Test connection by getting account information
        account_info = blob_service_client.get_account_information()
        logger.info(f"Successfully connected to Azure Storage Account")
        logger.info(f"Account Kind: {account_info.get('account_kind', 'Unknown')}")
        logger.info(f"SKU Name: {account_info.get('sku_name', 'Unknown')}")
        
        # Test container access
        logger.info(f"\nTesting container access: {container_name}")
        container_client = blob_service_client.get_container_client(container_name)
        
        try:
            # Try to get container properties
            properties = container_client.get_container_properties()
            logger.info(f"Container exists and accessible")
            logger.info(f"Container Last Modified: {properties.last_modified}")
        except ResourceNotFoundError:
            logger.warning(f"Container {container_name} does not exist")
            logger.info("Attempting to create container...")
            container_client.create_container()
            logger.info("Container created successfully")
        
        # Test blob operations
        target = os.getenv('TARGET', 'dev')
        username = os.getenv('USERNAME', 'test-user')
        
        # Construct blob path according to our project structure
        if target == "prod":
            base_path = "landing/test"
        else:
            base_path = f"dev/{target}_{username}/landing/test"
        
        # Test listing blobs
        logger.info(f"\nTesting blob listing with prefix: {base_path}")
        blob_list = container_client.list_blobs(name_starts_with=base_path, max_page_size=5)
        blob_names = [blob.name for blob in blob_list]
        
        if blob_names:
            logger.info("Found existing blobs:")
            for blob_name in blob_names:
                logger.info(f"- {blob_name}")
        else:
            logger.info(f"No existing blobs found with prefix: {base_path}")
        
        # Test writing to Azure Blob Storage
        logger.info("\nTesting Azure Blob Storage write access...")
        test_data = {
            'test': 'data',
            'timestamp': datetime.now().isoformat(),
            'environment': target,
            'username': username
        }
        
        import json
        test_key = f"{base_path}/credentials_test.json"
        
        logger.info(f"Attempting to write test file to blob: {test_key}")
        blob_client = container_client.get_blob_client(test_key)
        blob_client.upload_blob(json.dumps(test_data), overwrite=True)
        logger.info("Successfully wrote test file to Azure Blob Storage")
        
        # Verify the file was written
        logger.info("Verifying test file exists...")
        blob_properties = blob_client.get_blob_properties()
        logger.info(f"Test file verified (size: {blob_properties.size} bytes, last modified: {blob_properties.last_modified})")
        
        # Read back the contents
        blob_data = blob_client.download_blob().readall()
        data = json.loads(blob_data.decode('utf-8'))
        logger.info(f"File contents: {data}")
        
        # Test Parquet file upload
        logger.info("\nTesting Parquet file upload...")
        parquet_file = create_test_parquet()
        parquet_key = f"{base_path}/test_data.parquet"
        
        logger.info(f"Uploading Parquet file to blob: {parquet_key}")
        parquet_blob_client = container_client.get_blob_client(parquet_key)
        with open(parquet_file, 'rb') as f:
            parquet_blob_client.upload_blob(f, overwrite=True)
        logger.info("Successfully uploaded Parquet file")
        
        # Clean up temporary file
        os.unlink(parquet_file)
        
        # Verify the Parquet file was uploaded
        logger.info("Verifying Parquet file exists...")
        parquet_properties = parquet_blob_client.get_blob_properties()
        logger.info(f"Parquet file verified (size: {parquet_properties.size} bytes, last modified: {parquet_properties.last_modified})")
        
        # Test access to a specific Parquet file (if it exists)
        test_parquet_key = "prod/staging/master/indicators.parquet"
        logger.info(f"\nTesting access to Parquet file at blob: {test_parquet_key}")
        try:
            test_blob_client = container_client.get_blob_client(test_parquet_key)
            test_properties = test_blob_client.get_blob_properties()
            logger.info(f"Successfully accessed Parquet file (size: {test_properties.size} bytes, last modified: {test_properties.last_modified})")
        except ResourceNotFoundError:
            logger.info("Parquet file does not exist (this is expected for a new deployment)")
        except AzureError as e:
            logger.error(f"Error accessing Parquet file: {e}")
            raise
        
        logger.info("\n🎉 All Azure credentials and blob storage tests completed successfully!")
        
    except ImportError as e:
        logger.error(f"Missing Azure dependencies: {e}")
        logger.error("Please install: pip install azure-storage-blob azure-identity")
        raise
    except AzureError as e:
        logger.error(f"Azure operation failed: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise

def main():
    """Main test function"""
    try:
        logger.info("Starting Azure credentials and blob storage access test...")
        test_azure_credentials()
        
    except Exception as e:
        logger.error(f"Test failed: {e}")
        raise

if __name__ == "__main__":
    main()
