"""Azure configuration module for project settings and environment variables.

This module manages Azure-specific configuration settings and environment-specific
parameters for the United Nations OSAA MVP project.
"""

import logging
import os
import sys

import colorlog
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential, ClientSecretCredential
from azure.core.exceptions import AzureError, ResourceNotFoundError

from pipeline.exceptions import ConfigurationError

# get the local root directory
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# Define the LOCAL DATA directory relative to the root
DATALAKE_DIR = os.path.join(ROOT_DIR, "data")
RAW_DATA_DIR = os.getenv("RAW_DATA_DIR", os.path.join(DATALAKE_DIR, "raw"))
STAGING_DATA_DIR = os.path.join(DATALAKE_DIR, "staging")
MASTER_DATA_DIR = os.path.join(STAGING_DATA_DIR, "master")

# Allow both Docker and local environment DuckDB path
DB_PATH = os.getenv(
    "DB_PATH", os.path.join(ROOT_DIR, "sqlMesh", "unosaa_data_pipeline.db")
)

# Environment configurations
TARGET = os.getenv("TARGET", "dev").lower()
USERNAME = os.getenv("USERNAME", "default").lower()

# Construct Azure Blob environment path
AZURE_ENV = TARGET if TARGET == "prod" else f"dev/{TARGET}_{USERNAME}"

ENABLE_AZURE_UPLOAD = os.getenv("ENABLE_AZURE_UPLOAD", "true").lower() == "true"

# Azure Blob Storage configurations
AZURE_STORAGE_ACCOUNT_NAME = os.getenv("AZURE_STORAGE_ACCOUNT_NAME")
AZURE_STORAGE_CONTAINER_NAME = os.getenv("AZURE_STORAGE_CONTAINER_NAME", "osaa-data-pipeline")
AZURE_STORAGE_CONNECTION_STRING = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")

LANDING_AREA_FOLDER = f"{AZURE_ENV}/landing"
STAGING_AREA_FOLDER = f"{AZURE_ENV}/staging"


# Logging configuration
def create_logger():
    """
    Create a structured, color-coded logger with clean output.

    :return: Configured logger instance
    """
    # Create logger
    logger = colorlog.getLogger(__name__)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Remove any existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # Create console handler
    console_handler = colorlog.StreamHandler()

    # Custom log format with clear structure
    formatter = colorlog.ColoredFormatter(
        # Structured format with clear sections
        "%(log_color)s[%(levelname)s]%(reset)s %(blue)s[%(name)s]%(reset)s %(message)s",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
        secondary_log_colors={},
    )
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


# Global logger instance
logger = create_logger()


def validate_config():
    """
    Validate critical configuration parameters.
    Raises ConfigurationError if any required config is missing or invalid.

    :raises ConfigurationError: If configuration is invalid
    """
    # Validate root directories
    required_dirs = [
        ("ROOT_DIR", ROOT_DIR),
        ("DATALAKE_DIR", DATALAKE_DIR),
        ("RAW_DATA_DIR", RAW_DATA_DIR),
        ("STAGING_DATA_DIR", STAGING_DATA_DIR),
        ("MASTER_DATA_DIR", MASTER_DATA_DIR),
    ]

    for dir_name, dir_path in required_dirs:
        if not dir_path:
            raise ConfigurationError(
                f"Missing required directory configuration: {dir_name}"
            )

        # Create directory if it doesn't exist
        try:
            os.makedirs(dir_path, exist_ok=True)
        except Exception as e:
            raise ConfigurationError(
                f"Unable to create directory {dir_name} at {dir_path}: {e}"
            )

    # Validate DB Path
    if not DB_PATH:
        raise ConfigurationError("Database path (DB_PATH) is not configured")

    try:
        # Ensure DB directory exists
        db_dir = os.path.dirname(DB_PATH)
        os.makedirs(db_dir, exist_ok=True)
    except Exception as e:
        raise ConfigurationError(
            f"Unable to create database directory at {db_dir}: {e}"
        )

    # Validate Azure Configuration
    if ENABLE_AZURE_UPLOAD:
        if not AZURE_STORAGE_CONTAINER_NAME:
            raise ConfigurationError(
                "Azure upload is enabled but no container name is specified"
            )

        # Validate Azure folder configurations
        azure_folders = [
            ("LANDING_AREA_FOLDER", LANDING_AREA_FOLDER),
            ("STAGING_AREA_FOLDER", STAGING_AREA_FOLDER),
        ]

        for folder_name, folder_path in azure_folders:
            if not folder_path:
                raise ConfigurationError(
                    f"Missing Azure folder configuration: {folder_name}"
                )

    # Validate environment configurations
    if not TARGET:
        raise ConfigurationError("TARGET environment is not set")

    # Log validation success (optional)
    logger.info("Configuration validation successful")


def validate_azure_credentials():
    """
    Validate Azure credentials with structured error handling.

    Performs comprehensive checks:
    - Verifies presence of required environment variables
    - Validates Azure credential format
    - Attempts BlobServiceClient creation
    - Performs lightweight container listing test

    :raises ConfigurationError: If credentials are invalid or missing
    """

    def _mask_sensitive(value):
        """Mask sensitive information in logs."""
        return "*" * len(value) if value else "NOT SET"

    try:
        # Credential validation stages
        logger.info("Validating Azure Credentials")

        # Check for connection string first (highest priority)
        if AZURE_STORAGE_CONNECTION_STRING:
            logger.info("Using Azure Storage Connection String")
            try:
                blob_service_client = BlobServiceClient.from_connection_string(
                    AZURE_STORAGE_CONNECTION_STRING
                )
                # Test connection
                blob_service_client.get_account_information()
                logger.info("Azure credentials validated successfully with connection string")
                return
            except AzureError as e:
                logger.error(f"Azure Connection String Error: {e}")
                raise ConfigurationError(f"Azure Connection String Failed: {e}")

        # Check for service principal credentials
        if AZURE_CLIENT_ID and AZURE_CLIENT_SECRET and AZURE_TENANT_ID:
            logger.info("Using Azure Service Principal Credentials")
            try:
                credential = ClientSecretCredential(
                    tenant_id=AZURE_TENANT_ID,
                    client_id=AZURE_CLIENT_ID,
                    client_secret=AZURE_CLIENT_SECRET
                )
                if not AZURE_STORAGE_ACCOUNT_NAME:
                    raise ConfigurationError("AZURE_STORAGE_ACCOUNT_NAME is required when using service principal")
                
                blob_service_client = BlobServiceClient(
                    account_url=f"https://{AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net",
                    credential=credential
                )
                # Test connection
                blob_service_client.get_account_information()
                logger.info("Azure credentials validated successfully with service principal")
                return
            except AzureError as e:
                logger.error(f"Azure Service Principal Error: {e}")
                raise ConfigurationError(f"Azure Service Principal Failed: {e}")

        # Check for default credentials (managed identity, CLI, etc.)
        logger.info("Attempting to use Default Azure Credentials")
        try:
            credential = DefaultAzureCredential()
            if not AZURE_STORAGE_ACCOUNT_NAME:
                raise ConfigurationError("AZURE_STORAGE_ACCOUNT_NAME is required when using default credentials")
            
            blob_service_client = BlobServiceClient(
                account_url=f"https://{AZURE_STORAGE_ACCOUNT_NAME}.blob.core.windows.net",
                credential=credential
            )
            # Test connection
            blob_service_client.get_account_information()
            logger.info("Azure credentials validated successfully with default credentials")
            return
        except AzureError as e:
            logger.error(f"Azure Default Credentials Error: {e}")
            raise ConfigurationError(f"Azure Default Credentials Failed: {e}")

        # If we get here, no valid credential method was found
        raise ConfigurationError(
            "No valid Azure authentication method found. Please set one of:\n"
            "- AZURE_STORAGE_CONNECTION_STRING\n"
            "- AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID, AZURE_STORAGE_ACCOUNT_NAME\n"
            "- Default Azure Credentials with AZURE_STORAGE_ACCOUNT_NAME"
        )

    except Exception as e:
        # Structured error reporting
        logger.critical("🔒 AZURE CREDENTIALS VALIDATION FAILED 🔒")
        logger.critical(f"Error Type: {type(e).__name__}")
        logger.critical(f"Error Details: {str(e)}")

        # Concise troubleshooting guide
        troubleshooting_steps = [
            "1. Verify Azure credentials in .env",
            "2. Check Azure Storage account permissions",
            "3. Confirm Azure Storage account name and container",
            "4. Ensure proper Azure authentication setup",
        ]

        logger.critical("Troubleshooting:")
        for step in troubleshooting_steps:
            logger.critical(f"  {step}")

        logger.critical("Contact Azure administrator for assistance.")

        raise


# Validate configuration and Azure credentials when module is imported
try:
    validate_config()
    if ENABLE_AZURE_UPLOAD:
        validate_azure_credentials()
except ConfigurationError as config_error:
    sys.exit(1)
