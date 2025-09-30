"""Azure catalog module for managing data catalog and metadata.

This module provides functionality for creating and managing
data catalog entries and metadata for the United Nations OSAA MVP project using Azure Blob Storage.
"""

from typing import Any

import ibis

from pipeline.logging_config import create_logger, log_exception
from pipeline.azure_utils import azure_blob_path_to_url

# Set up logging
logger = create_logger(__name__)


def save_azure_blob(table_exp: ibis.Expr, blob_path: str) -> None:
    """Save the Ibis table expression to Azure Blob Storage as a Parquet file.

    Args:
        table_exp: Ibis table expression to be saved.
        blob_path: The blob path where the Parquet file will be saved.
    """
    try:
        # Convert blob path to full Azure URL
        azure_url = azure_blob_path_to_url(blob_path)
        table_exp.to_parquet(azure_url)
        logger.info(f"📤 Table successfully uploaded to Azure Blob Storage: {azure_url}")
        logger.info(f"   🔍 Table details: {table_exp}")

    except Exception as e:
        log_exception(logger, e, context="Azure Blob Storage Upload")
        raise


def save_duckdb(table_exp: ibis.Expr, local_db: Any) -> None:
    """Save the Ibis table expression locally to a DuckDB database.

    Args:
        table_exp: Ibis table expression to be saved.
        local_db: Connection to the local DuckDB database.
    """
    try:
        local_db.create_table("master", table_exp.execute(), overwrite=True)
        logger.info("🗄️ Table successfully created in persistent DuckDB")
        logger.info(f"   🔍 Table details: {table_exp}")

    except Exception as e:
        log_exception(logger, e, context="DuckDB Creation")
        raise


def save_parquet(table_exp: ibis.Expr, local_path: str) -> None:
    """Save the Ibis table expression locally as a Parquet file.

    Args:
        table_exp: Ibis table expression to be saved.
        local_path: Local file path where the Parquet file will be saved.
    """
    try:
        table_exp.to_parquet(local_path)
        logger.info(f"💾 Table successfully saved to local Parquet file: {local_path}")
        logger.info(f"   🔍 Table details: {table_exp}")

    except Exception as e:
        log_exception(logger, e, context="Parquet Save")
        raise


# TODO: Function to save the data remotely to Azure SQL Database or other Azure services
