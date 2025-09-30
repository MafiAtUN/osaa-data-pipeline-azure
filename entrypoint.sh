#!/bin/bash
set -e  # Exit on error

case "$1" in
  "ingest")
    uv run python -m pipeline.azure_ingest.run
    ;;
  "transform")
    cd sqlMesh
    uv run sqlmesh --gateway "${GATEWAY:-local}" plan --auto-apply --include-unmodified --create-from prod --no-prompts "${TARGET:-dev}"
    ;;
  "transform_dry_run")
    export RAW_DATA_DIR=/app/data/raw
    export DRY_RUN_FLG=true

    echo "Start local ingestion"
    uv run python -m pipeline.azure_ingest.run
    echo "End ingestion"

    echo "Start sqlMesh"
    cd sqlMesh
    uv run sqlmesh --gateway "${GATEWAY:-local}" plan --auto-apply --include-unmodified --create-from prod --no-prompts "${TARGET:-dev}"
    echo "End sqlMesh"
    ;;
  "ui")
    # Start secure web interface instead of default SQLMesh UI
    uv run python -m pipeline.secure_ui
    ;;
  "sqlmesh_ui")
    # Original SQLMesh UI (for internal use)
    uv run sqlmesh ui --host "0.0.0.0" --port "${UI_PORT:-8080}"
    ;;
  "etl")
    echo "Starting pipeline"

    # Download DB from Azure Blob Storage (or create new if doesn't exist)
    echo "Downloading DB from Azure Blob Storage..."
    uv run python -m pipeline.azure_sync.run download

    echo "Start sqlMesh"
    cd sqlMesh
    uv run sqlmesh --gateway "${GATEWAY:-local}" plan --auto-apply --include-unmodified --create-from prod --no-prompts "${TARGET:-dev}"
    echo "End sqlMesh"

    # Upload updated DB back to Azure Blob Storage
    cd ..  # Return to root directory
    echo "Uploading DB to Azure Blob Storage..."
    uv run python -m pipeline.azure_sync.run upload
    ;;
  "config_test")
    uv run python -m pipeline.config_test
    ;;
  "promote")
    echo "Starting promotion from dev to prod..."
    uv run python -m pipeline.azure_promote.run
    echo "Promotion completed"
    ;;
  *)
    echo "Error: Invalid command '$1'"
    echo
    echo "Available commands:"
    echo "  ingest       - Run the data ingestion process"
    echo "  transform    - Run SQLMesh transformations"
    echo "  etl          - Run the complete pipeline (ingest + transform + upload)"
    echo "  ui           - Start the SQLMesh UI server"
    echo "  config_test  - Test and display current configuration settings"
    echo
    echo "Usage: docker compose run pipeline <command>"
    exit 1
    ;;
esac
