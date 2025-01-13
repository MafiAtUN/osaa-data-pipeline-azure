#!/bin/bash
set -e  # Exit on error

case "$1" in
  "ingest")
    python -m pipeline.ingest.run
    ;;
  "transform")
    cd sqlMesh
    sqlmesh --gateway "${GATEWAY:-local}" plan --auto-apply --include-unmodified --create-from prod --no-prompts "${TARGET:-dev}"
    ;;
  "transform_dry_run")
    export RAW_DATA_DIR=/app/data/raw

    echo "Start local ingestion"
    python -m pipeline.ingest.run
    echo "End ingestion"

    echo "Start sqlMesh"
    cd sqlMesh
    sqlmesh --gateway "${GATEWAY:-local}" plan --auto-apply --include-unmodified --create-from prod --no-prompts "${TARGET:-dev}"
    echo "End sqlMesh"
    ;;
  "ui")
    cd sqlMesh
    sqlmesh ui --port "${UI_PORT:-8080}"
    ;;
  "etl")
    echo "Starting pipeline"

    echo "Start ingestion"
    python -m pipeline.ingest.run
    echo "End ingestion"

    echo "Start sqlMesh"
    cd sqlMesh
    sqlmesh --gateway "${GATEWAY:-local}" plan --auto-apply --include-unmodified --create-from prod --no-prompts "${TARGET:-dev}"
    echo "End sqlMesh"
    ;;
  "config_test")
    python -m pipeline.config_test
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
