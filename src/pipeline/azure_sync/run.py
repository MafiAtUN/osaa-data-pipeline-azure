"""Module for handling Azure Blob Storage synchronization of SQLMesh database files.

This module provides functionality to sync SQLMesh database files with Azure Blob Storage,
including downloading existing DBs and uploading updated ones.
"""

import os
import sys
from pathlib import Path
from typing import Optional

from azure.core.exceptions import ResourceNotFoundError

from pipeline.exceptions import AzureOperationError
from pipeline.logging_config import create_logger
from pipeline.azure_config import AZURE_STORAGE_CONTAINER_NAME
from pipeline.azure_utils import (
    azure_blob_init,
    download_file_from_azure_blob,
    upload_file_to_azure_blob,
    blob_exists
)

logger = create_logger(__name__)

def sync_db_with_azure_blob(operation: str, db_path: str, container_name: str, blob_key: str) -> None:
    """
    Sync SQLMesh database with Azure Blob Storage.

    Args:
        operation: Either "download" or "upload"
        db_path: Local path to the SQLMesh database file
        container_name: Azure Blob Storage container name
        blob_key: Key (path) in Azure Blob Storage container

    Raises:
        AzureOperationError: If Azure operations fail
    """
    try:
        if operation == "download":
            logger.info("Attempting to download DB from Azure Blob Storage...")
            try:
                if blob_exists(blob_key, container_name):
                    # File exists, download it
                    os.makedirs(os.path.dirname(db_path), exist_ok=True)
                    download_file_from_azure_blob(blob_key, db_path, container_name)
                    logger.info("Successfully downloaded existing DB from Azure Blob Storage")
                else:
                    logger.info("No existing DB found in Azure Blob Storage, skipping download...")
                    
            except Exception as e:
                raise AzureOperationError(f"Error checking Azure blob: {str(e)}")
                    
        elif operation == "upload":
            # Only allow uploads in prod/qa environments
            if os.getenv('TARGET', '').lower() not in ['prod', 'qa']:
                logger.warning("Upload operation restricted to prod/qa targets only")
                return
                
            logger.info("Uploading DB to Azure Blob Storage...")
            if os.path.exists(db_path):
                upload_file_to_azure_blob(db_path, blob_key, container_name)
                logger.info("Successfully uploaded DB to Azure Blob Storage")
            else:
                logger.warning(f"Local DB file not found at {db_path}, skipping upload")
                
    except Exception as e:
        error_msg = f"Azure {operation} operation failed: {str(e)}"
        logger.error(error_msg)
        raise AzureOperationError(error_msg)

def get_db_paths(db_filename: Optional[str] = "unosaa_data_pipeline.db") -> tuple[str, str]:
    """
    Get the local and Azure Blob Storage paths for the database file.
    
    Args:
        db_filename: Name of the database file
        
    Returns:
        Tuple of (local_path, blob_key)
    """
    local_path = f"sqlMesh/{db_filename}"
    blob_key = db_filename
    return local_path, blob_key

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ["download", "upload"]:
        print("Usage: python -m pipeline.azure_sync.run [download|upload]")
        sys.exit(1)

    operation = sys.argv[1]
    local_path, blob_key = get_db_paths()
    sync_db_with_azure_blob(operation, local_path, AZURE_STORAGE_CONTAINER_NAME, blob_key)
