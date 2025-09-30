"""Azure ingest module for data processing and Azure Blob Storage upload.

This module handles the ingestion of CSV files, converting them to Parquet,
and optionally uploading them to Azure Blob Storage for the United Nations OSAA MVP project.
"""

import os
import re
import tempfile

import duckdb
from typing import Dict, Optional

from pipeline.azure_config import (
    ENABLE_AZURE_UPLOAD,
    LANDING_AREA_FOLDER,
    RAW_DATA_DIR,
    AZURE_STORAGE_CONTAINER_NAME,
    TARGET,
    USERNAME,
)
from pipeline.exceptions import (
    FileConversionError,
    IngestError,
    AzureOperationError,
)
from pipeline.logging_config import create_logger, log_exception
from pipeline.azure_utils import azure_blob_init, upload_file_to_azure_blob, azure_blob_path_to_url

# Initialize logger
logger = create_logger(__name__)


class AzureIngest:
    """Manage the data ingestion process for the United Nations OSAA MVP project using Azure Blob Storage.

    This class handles the conversion of CSV files to Parquet format,
    manages database connections, and optionally uploads processed files
    to Azure Blob Storage. It provides methods for file processing, table creation,
    and data transformation.

    Key features:
    - Convert CSV files to Parquet
    - Create and manage database tables
    - Optionally upload processed files to Azure Blob Storage
    - Handle environment-specific configurations
    """

    def __init__(self) -> None:
        """Initialize the AzureIngestProcess with DuckDB connection and Azure Blob Service Client.

        Sets up a DuckDB connection and optionally initializes an Azure Blob Service Client
        based on the configuration settings.
        """
        logger.info("Initializing Azure Ingest Process")

        # Initialize DuckDB with required extensions
        self.con = duckdb.connect()
        self.con.install_extension('httpfs')
        self.con.load_extension('httpfs')
        
        if ENABLE_AZURE_UPLOAD:
            logger.info("Initializing Azure Blob Service Client...")
            self.azure_client = azure_blob_init()
            logger.info("Azure Blob Service Client Initialized")
        else:
            logger.warning("Azure upload is disabled")
            self.azure_client = None

    def setup_azure_secret(self):
        """
        Set up the Azure Blob Storage secret in DuckDB for Azure access.

        :raises AzureOperationError: If there are issues setting up Azure secret
        """
        if not ENABLE_AZURE_UPLOAD:
            logger.info("Azure upload disabled, skipping Azure secret setup")
            return

        try:
            logger.info("🔐 Setting up Azure Blob Storage Secret in DuckDB")
            logger.info("   Creating Azure secret with connection string or credentials")

            # For Azure, we'll use a different approach than AWS
            # We can either use connection string or account key
            from pipeline.azure_config import AZURE_STORAGE_CONNECTION_STRING
            
            if AZURE_STORAGE_CONNECTION_STRING:
                # Extract account name and key from connection string
                import re
                account_match = re.search(r'AccountName=([^;]+)', AZURE_STORAGE_CONNECTION_STRING)
                key_match = re.search(r'AccountKey=([^;]+)', AZURE_STORAGE_CONNECTION_STRING)
                
                if account_match and key_match:
                    account_name = account_match.group(1)
                    account_key = key_match.group(1)
                    
                    # Drop existing secret if it exists
                    self.con.sql("DROP SECRET IF EXISTS my_azure_secret")
                    logger.info("   Dropped existing Azure secret")

                    # Create the SQL statement for Azure
                    sql_statement = f"""
                        CREATE PERSISTENT SECRET my_azure_secret (
                            TYPE AZURE,
                            ACCOUNT_NAME '{account_name}',
                            ACCOUNT_KEY '{account_key}'
                        )
                    """
                    
                    self.con.sql(sql_statement)
                    logger.info("   ✅ Azure secret created successfully in DuckDB")
                else:
                    logger.warning("   Could not extract account name/key from connection string")
                    logger.warning("   Azure Blob Storage access may be limited")
            else:
                logger.warning("   No Azure Storage connection string found")
                logger.warning("   Azure Blob Storage access may be limited")

        except Exception as e:
            error_msg = f"Failed to setup Azure secret in DuckDB: {str(e)}"
            logger.error(error_msg)
            raise AzureOperationError(error_msg)

    def convert_csv_to_parquet(self, csv_file_path: str, output_path: str) -> str:
        """
        Convert a CSV file to Parquet format using DuckDB.

        :param csv_file_path: Path to the input CSV file
        :param output_path: Path for the output Parquet file
        :return: Path to the converted Parquet file
        :raises FileConversionError: If conversion fails
        """
        try:
            logger.info(f"Converting CSV to Parquet: {csv_file_path}")

            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)

            # Use DuckDB to convert CSV to Parquet
            query = f"""
                COPY (
                    SELECT * FROM read_csv_auto('{csv_file_path}')
                ) TO '{output_path}' (FORMAT PARQUET)
            """

            self.con.sql(query)
            logger.info(f"✅ Successfully converted to Parquet: {output_path}")

            return output_path

        except Exception as e:
            error_msg = f"CSV to Parquet conversion failed for {csv_file_path}: {str(e)}"
            logger.error(error_msg)
            raise FileConversionError(error_msg)

    def upload_to_azure_blob(self, local_file_path: str, blob_path: str) -> None:
        """
        Upload a local file to Azure Blob Storage.

        :param local_file_path: Local file path to upload
        :param blob_path: Blob path in Azure Blob Storage
        :raises AzureOperationError: If upload fails
        """
        if not ENABLE_AZURE_UPLOAD:
            logger.info("Azure upload disabled, skipping upload")
            return

        try:
            logger.info(f"Uploading to Azure Blob Storage: {blob_path}")
            upload_file_to_azure_blob(local_file_path, blob_path, AZURE_STORAGE_CONTAINER_NAME)
            logger.info(f"✅ Successfully uploaded to Azure Blob Storage: {blob_path}")

        except Exception as e:
            error_msg = f"Azure upload failed for {local_file_path}: {str(e)}"
            logger.error(error_msg)
            raise AzureOperationError(error_msg)

    def process_data_sources(self) -> None:
        """
        Process all data sources in the raw data directory.

        This method:
        1. Scans the raw data directory for CSV files
        2. Converts each CSV to Parquet format
        3. Optionally uploads to Azure Blob Storage
        """
        try:
            logger.info("Starting data source processing")
            logger.info(f"Raw data directory: {RAW_DATA_DIR}")
            logger.info(f"Azure upload enabled: {ENABLE_AZURE_UPLOAD}")

            if not os.path.exists(RAW_DATA_DIR):
                logger.warning(f"Raw data directory does not exist: {RAW_DATA_DIR}")
                return

            # Setup Azure secret for DuckDB if needed
            self.setup_azure_secret()

            processed_count = 0
            
            # Walk through all subdirectories in raw data
            for root, dirs, files in os.walk(RAW_DATA_DIR):
                for file in files:
                    if file.lower().endswith('.csv'):
                        csv_path = os.path.join(root, file)
                        relative_path = os.path.relpath(csv_path, RAW_DATA_DIR)
                        
                        # Create output path (replace .csv with .parquet)
                        parquet_filename = os.path.splitext(file)[0] + '.parquet'
                        parquet_path = os.path.join(RAW_DATA_DIR.replace('raw', 'staging'), 
                                                  os.path.dirname(relative_path), 
                                                  parquet_filename)
                        
                        try:
                            # Convert CSV to Parquet
                            converted_path = self.convert_csv_to_parquet(csv_path, parquet_path)
                            
                            # Upload to Azure Blob Storage if enabled
                            if ENABLE_AZURE_UPLOAD:
                                # Create blob path
                                blob_path = f"{LANDING_AREA_FOLDER}/{relative_path.replace('.csv', '.parquet')}"
                                self.upload_to_azure_blob(converted_path, blob_path)
                            
                            processed_count += 1
                            logger.info(f"✅ Processed: {relative_path}")
                            
                        except Exception as e:
                            logger.error(f"❌ Failed to process {relative_path}: {str(e)}")
                            continue

            logger.info(f"🎉 Data processing completed. Processed {processed_count} files.")

        except Exception as e:
            error_msg = f"Data source processing failed: {str(e)}"
            logger.error(error_msg)
            raise IngestError(error_msg)

    def run(self) -> None:
        """
        Execute the complete ingestion process.

        This is the main entry point for the ingestion process.
        """
        try:
            logger.info("🚀 Starting Azure Ingest Process")
            logger.info(f"Target environment: {TARGET}")
            logger.info(f"Username: {USERNAME}")
            logger.info(f"Azure container: {AZURE_STORAGE_CONTAINER_NAME}")

            # Process all data sources
            self.process_data_sources()

            logger.info("✅ Azure Ingest Process completed successfully")

        except Exception as e:
            error_msg = f"Azure Ingest Process failed: {str(e)}"
            logger.error(error_msg)
            raise IngestError(error_msg)


def main():
    """Main entry point for the Azure ingest module."""
    try:
        ingest_process = AzureIngest()
        ingest_process.run()
    except Exception as e:
        logger.error(f"Ingest process failed: {str(e)}")
        raise


if __name__ == "__main__":
    main()
