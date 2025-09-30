"""Module for handling data promotion between environments in Azure Blob Storage.

This module provides functionality to promote data from development to production
environments within Azure Blob Storage.
"""

from pipeline.exceptions import AzureOperationError
from pipeline.logging_config import create_logger
from pipeline.azure_config import AZURE_STORAGE_CONTAINER_NAME
from pipeline.azure_utils import (
    azure_blob_init,
    list_azure_blobs,
    copy_azure_blob,
    delete_azure_blob,
    blob_exists
)

logger = create_logger(__name__)

def promote_environment(
    source_env: str = "dev",
    target_env: str = "prod",
    folder: str = "landing",
) -> None:
    """
    Promote contents from source to target environment using Azure Blob Storage.

    Args:
        source_env: Source environment (default: "dev")
        target_env: Target environment (default: "prod")
        folder: Folder to promote (default: "landing")

    Raises:
        AzureOperationError: If promotion operation fails
    """
    try:
        source_prefix = f"{source_env}/{folder}/"
        target_prefix = f"{target_env}/{folder}/"

        logger.info(f"Starting promotion from {source_prefix} to {target_prefix}")
        
        # Initialize Azure Blob Service Client
        blob_service_client = azure_blob_init()
        
        # Get list of all blobs in source
        source_blobs = set()
        source_blob_list = list_azure_blobs(prefix=source_prefix, container_name=AZURE_STORAGE_CONTAINER_NAME)
        
        for blob_name in source_blob_list:
            source_blobs.add(blob_name)
            target_blob_name = blob_name.replace(source_prefix, target_prefix, 1)
            
            # Copy blob to new location
            logger.info(f"Copying {blob_name} to {target_blob_name}")
            copy_azure_blob(
                source_blob_name=blob_name,
                dest_blob_name=target_blob_name,
                source_container=AZURE_STORAGE_CONTAINER_NAME,
                dest_container=AZURE_STORAGE_CONTAINER_NAME
            )

        # Get list of all blobs in target and delete those not in source
        target_blob_list = list_azure_blobs(prefix=target_prefix, container_name=AZURE_STORAGE_CONTAINER_NAME)
        
        for blob_name in target_blob_list:
            corresponding_source_blob = blob_name.replace(target_prefix, source_prefix, 1)
            
            if corresponding_source_blob not in source_blobs:
                logger.info(f"Deleting {blob_name} from target")
                delete_azure_blob(blob_name, AZURE_STORAGE_CONTAINER_NAME)
            
        logger.info("✅ Promotion completed successfully")

    except Exception as e:
        error_msg = f"Azure promotion operation failed: {str(e)}"
        logger.error(error_msg)
        raise AzureOperationError(error_msg)

if __name__ == "__main__":
    promote_environment()
