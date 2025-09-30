"""
Custom exceptions for the pipeline module.

This module defines a hierarchy of exceptions to provide more
precise error handling and debugging across the pipeline.
"""


class PipelineBaseError(Exception):
    """
    Base exception for all pipeline-related errors.

    All custom exceptions in the pipeline should inherit from this class.
    Provides a common base for catching and handling pipeline-specific errors.
    """

    pass


class ConfigurationError(PipelineBaseError):
    """
    Raised when there are configuration-related issues.

    This exception is used when:
    - Required configuration parameters are missing
    - Configuration values are invalid
    - Environment setup is incorrect
    """

    pass


class S3OperationError(PipelineBaseError):
    """
    Raised for S3-specific operation errors.

    Covers issues such as:
    - Authentication failures
    - Connection problems
    - File upload/download errors
    - Bucket or object access issues
    """

    pass


class S3ConfigurationError(S3OperationError):
    """
    Raised for S3 configuration or connection issues.

    Covers problems with:
    - AWS credentials
    - S3 client initialization
    - Access configuration
    """

    pass


class AzureOperationError(PipelineBaseError):
    """
    Raised for Azure Blob Storage-specific operation errors.

    Covers issues such as:
    - Authentication failures
    - Connection problems
    - File upload/download errors
    - Container or blob access issues
    """

    pass


class AzureConfigurationError(AzureOperationError):
    """
    Raised for Azure configuration or connection issues.

    Covers problems with:
    - Azure credentials
    - Azure Blob Service Client initialization
    - Access configuration
    """

    pass


class IngestError(PipelineBaseError):
    """
    Raised during the data ingestion process.

    Covers errors specific to data ingestion, including:
    - File conversion problems
    - Source data validation failures
    - Ingestion pipeline interruptions
    """

    pass


class FileConversionError(IngestError):
    """
    Raised for errors during file conversion.

    Specific to issues encountered while converting files,
    such as:
    - Unsupported file formats
    - Conversion process failures
    - Data integrity issues during conversion
    """

    pass
