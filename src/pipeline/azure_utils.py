"""Azure utilities module for Azure Blob Storage operations.

This module provides utility functions for Azure Blob Storage operations,
replacing the AWS S3 utilities in the original application.
"""

import os
import tempfile
from typing import Any, Optional, Tuple
from pathlib import Path

from azure.storage.blob import BlobServiceClient, BlobClient
from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.core.exceptions import AzureError, ResourceNotFoundError

from pipeline.azure_config import (
    AZURE_STORAGE_ACCOUNT_NAME,
    AZURE_STORAGE_CONTAINER_NAME,
    AZURE_STORAGE_CONNECTION_STRING,
    AZURE_CLIENT_ID,
    AZURE_CLIENT_SECRET,
    AZURE_TENANT_ID,
)
from pipeline.logging_config import create_logger
from pipeline.exceptions import AzureOperationError

logger = create_logger(__name__)


def log_azure_initialization_error(error):
    """Log Azure initialization error with troubleshooting steps."""
    logger.critical("❌ Azure Blob Storage initialization failed")
    logger.critical(f"Error: {error}")
    logger.critical("Troubleshooting steps:")
    logger.critical("1. Verify Azure Storage account name and credentials")
    logger.critical("2. Check network connectivity to Azure")
    logger.critical("3. Ensure Azure Storage account has proper permissions")


def azure_blob_init(return_credential: bool = False) -> Tuple[Any, Optional[Any]]:
    """
    Initialize Azure Blob Service Client.

    :param return_credential: If True, returns both client and credential
    :return: BlobServiceClient, and optionally the credential
    :raises AzureError: If Azure initialization fails
    """
    logger = create_logger(__name__)

    try:
        # Priority 1: Connection String
        if AZURE_STORAGE_CONNECTION_STRING:
            logger.info("Using Azure Storage Connection String")
            blob_service_client = BlobServiceClient.from_connection_string(
                AZURE_STORAGE_CONNECTION_STRING
            )
            return (blob_service_client, None) if return_credential else blob_service_client

        # Priority 2: Service Principal
        if AZURE_CLIENT_ID and AZURE_CLIENT_SECRET and AZURE_TENANT_ID:
            logger.info("Using Azure Service Principal Credentials")
            credential = ClientSecretCredential(
                tenant_id=AZURE_TENANT_ID,
                client_id=AZURE_CLIENT_ID,
                client_secret=AZURE_CLIENT_SECRET
            )
            
            if not AZURE_STORAGE_ACCOUNT_NAME:
                raise ValueError("AZURE_STORAGE_ACCOUNT_NAME is required when using service principal")
            
            blob_service_client = BlobServiceClient(
                account_url=f"https://{AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net",
                credential=credential
            )
            return (blob_service_client, credential) if return_credential else blob_service_client

        # Priority 3: Default Credentials
        logger.info("Using Default Azure Credentials")
        credential = DefaultAzureCredential()
        
        if not AZURE_STORAGE_ACCOUNT_NAME:
            raise ValueError("AZURE_STORAGE_ACCOUNT_NAME is required when using default credentials")
        
        blob_service_client = BlobServiceClient(
            account_url=f"https://{AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net",
            credential=credential
        )

        # Verify Azure access
        try:
            blob_service_client.get_account_information()
            logger.info("Azure Blob Service Client initialized successfully.")
        except AzureError as access_error:
            logger.error(f"Azure Access Error: {access_error}")
            raise

        return (blob_service_client, credential) if return_credential else blob_service_client

    except Exception as e:
        logger.critical(f"Failed to initialize Azure Blob Service Client: {e}")
        log_azure_initialization_error(e)
        raise


def azure_blob_path_to_url(blob_path: str) -> str:
    """
    Convert Azure blob path to full URL.
    
    :param blob_path: Blob path (e.g., 'dev/landing/data.parquet')
    :return: Full Azure blob URL
    """
    if AZURE_STORAGE_ACCOUNT_NAME:
        return f"https://{AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net/{AZURE_STORAGE_CONTAINER_NAME}/{blob_path}"
    elif AZURE_STORAGE_CONNECTION_STRING:
        # Extract account name from connection string
        # This is a simplified approach - in production you might want more robust parsing
        import re
        match = re.search(r'AccountName=([^;]+)', AZURE_STORAGE_CONNECTION_STRING)
        if match:
            account_name = match.group(1)
            return f"https://{account_name}.blob.core.windows.net/{AZURE_STORAGE_CONTAINER_NAME}/{blob_path}"
    
    raise ValueError("Unable to construct Azure blob URL - missing storage account information")


def upload_file_to_azure_blob(local_file_path: str, blob_path: str, container_name: Optional[str] = None) -> None:
    """
    Upload a local file to Azure Blob Storage.
    
    :param local_file_path: Local file path to upload
    :param blob_path: Blob path in the container
    :param container_name: Container name (uses default if None)
    :raises AzureOperationError: If upload fails
    """
    try:
        blob_service_client = azure_blob_init()
        container = container_name or AZURE_STORAGE_CONTAINER_NAME
        
        blob_client = blob_service_client.get_blob_client(
            container=container,
            blob=blob_path
        )
        
        with open(local_file_path, 'rb') as data:
            blob_client.upload_blob(data, overwrite=True)
        
        logger.info(f"Successfully uploaded {local_file_path} to Azure blob: {blob_path}")
        
    except Exception as e:
        error_msg = f"Azure upload operation failed: {str(e)}"
        logger.error(error_msg)
        raise AzureOperationError(error_msg)


def download_file_from_azure_blob(blob_path: str, local_file_path: str, container_name: Optional[str] = None) -> None:
    """
    Download a file from Azure Blob Storage.
    
    :param blob_path: Blob path in the container
    :param local_file_path: Local file path to save to
    :param container_name: Container name (uses default if None)
    :raises AzureOperationError: If download fails
    """
    try:
        blob_service_client = azure_blob_init()
        container = container_name or AZURE_STORAGE_CONTAINER_NAME
        
        blob_client = blob_service_client.get_blob_client(
            container=container,
            blob=blob_path
        )
        
        # Ensure local directory exists
        os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
        
        with open(local_file_path, 'wb') as download_file:
            download_file.write(blob_client.download_blob().readall())
        
        logger.info(f"Successfully downloaded Azure blob: {blob_path} to {local_file_path}")
        
    except ResourceNotFoundError:
        logger.info(f"Blob not found: {blob_path}")
        raise
    except Exception as e:
        error_msg = f"Azure download operation failed: {str(e)}"
        logger.error(error_msg)
        raise AzureOperationError(error_msg)


def list_azure_blobs(prefix: str = "", container_name: Optional[str] = None) -> list:
    """
    List blobs in Azure Blob Storage with optional prefix.
    
    :param prefix: Prefix to filter blobs
    :param container_name: Container name (uses default if None)
    :return: List of blob names
    """
    try:
        blob_service_client = azure_blob_init()
        container = container_name or AZURE_STORAGE_CONTAINER_NAME
        
        blob_list = blob_service_client.get_container_client(container).list_blobs(name_starts_with=prefix)
        return [blob.name for blob in blob_list]
        
    except Exception as e:
        error_msg = f"Azure list operation failed: {str(e)}"
        logger.error(error_msg)
        raise AzureOperationError(error_msg)


def delete_azure_blob(blob_path: str, container_name: Optional[str] = None) -> None:
    """
    Delete a blob from Azure Blob Storage.
    
    :param blob_path: Blob path in the container
    :param container_name: Container name (uses default if None)
    :raises AzureOperationError: If deletion fails
    """
    try:
        blob_service_client = azure_blob_init()
        container = container_name or AZURE_STORAGE_CONTAINER_NAME
        
        blob_client = blob_service_client.get_blob_client(
            container=container,
            blob=blob_path
        )
        
        blob_client.delete_blob()
        logger.info(f"Successfully deleted Azure blob: {blob_path}")
        
    except Exception as e:
        error_msg = f"Azure delete operation failed: {str(e)}"
        logger.error(error_msg)
        raise AzureOperationError(error_msg)


def copy_azure_blob(source_blob_path: str, dest_blob_path: str, 
                   source_container: Optional[str] = None, 
                   dest_container: Optional[str] = None) -> None:
    """
    Copy a blob within Azure Blob Storage.
    
    :param source_blob_path: Source blob path
    :param dest_blob_path: Destination blob path
    :param source_container: Source container name (uses default if None)
    :param dest_container: Destination container name (uses default if None)
    :raises AzureOperationError: If copy fails
    """
    try:
        blob_service_client = azure_blob_init()
        source_cont = source_container or AZURE_STORAGE_CONTAINER_NAME
        dest_cont = dest_container or AZURE_STORAGE_CONTAINER_NAME
        
        source_blob_client = blob_service_client.get_blob_client(
            container=source_cont,
            blob=source_blob_path
        )
        
        dest_blob_client = blob_service_client.get_blob_client(
            container=dest_cont,
            blob=dest_blob_path
        )
        
        # Start the copy operation
        copy_source = source_blob_client.url
        dest_blob_client.start_copy_from_url(copy_source)
        
        logger.info(f"Successfully started copy from {source_blob_path} to {dest_blob_path}")
        
    except Exception as e:
        error_msg = f"Azure copy operation failed: {str(e)}"
        logger.error(error_msg)
        raise AzureOperationError(error_msg)


def blob_exists(blob_path: str, container_name: Optional[str] = None) -> bool:
    """
    Check if a blob exists in Azure Blob Storage.
    
    :param blob_path: Blob path in the container
    :param container_name: Container name (uses default if None)
    :return: True if blob exists, False otherwise
    """
    try:
        blob_service_client = azure_blob_init()
        container = container_name or AZURE_STORAGE_CONTAINER_NAME
        
        blob_client = blob_service_client.get_blob_client(
            container=container,
            blob=blob_path
        )
        
        blob_client.get_blob_properties()
        return True
        
    except ResourceNotFoundError:
        return False
    except Exception as e:
        logger.error(f"Error checking blob existence: {e}")
        raise AzureOperationError(f"Error checking blob existence: {e}")


# File path and naming utilities (keeping original functionality)
def get_filename_from_path(file_path: str) -> str:
    """
    Extract filename from a file path.

    :param file_path: Full file path
    :return: Filename with extension
    """
    return Path(file_path).name


def get_file_extension(file_path: str) -> str:
    """
    Extract file extension from a file path.

    :param file_path: Full file path
    :return: File extension (with dot)
    """
    return Path(file_path).suffix


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for Azure blob storage.
    Azure blob names can contain most characters but we'll be conservative.

    :param filename: Original filename
    :return: Sanitized filename
    """
    # Replace problematic characters
    import re
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip('. ')
    # Limit length (Azure has a 1024 char limit for blob names)
    if len(sanitized) > 1000:
        name, ext = os.path.splitext(sanitized)
        sanitized = name[:1000-len(ext)] + ext
    return sanitized
