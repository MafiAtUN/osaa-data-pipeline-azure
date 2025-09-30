"""Local storage utilities for when Azure is disabled.

This module provides local file system operations when Azure Blob Storage
is not configured or disabled.
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

def get_local_paths():
    """Get local file system paths for data storage."""
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    
    return {
        'data_dir': os.path.join(root_dir, 'data'),
        'output_dir': os.path.join(root_dir, 'output'),
        'db_path': os.getenv('DB_PATH', os.path.join(root_dir, 'sqlMesh', 'unosaa_data_pipeline.db')),
        'raw_data_dir': os.getenv('RAW_DATA_DIR', os.path.join(root_dir, 'data', 'raw')),
        'staging_dir': os.path.join(root_dir, 'data', 'staging'),
        'master_dir': os.path.join(root_dir, 'data', 'master')
    }

def ensure_local_directories():
    """Ensure all required local directories exist."""
    paths = get_local_paths()
    
    for path_name, path in paths.items():
        if path_name != 'db_path':  # DB path is a file, not directory
            os.makedirs(path, exist_ok=True)
            logger.info(f"📁 Ensured directory exists: {path}")

def save_file_locally(file_path: str, content: bytes) -> str:
    """Save file content to local storage."""
    paths = get_local_paths()
    full_path = os.path.join(paths['output_dir'], file_path)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    
    with open(full_path, 'wb') as f:
        f.write(content)
    
    logger.info(f"💾 File saved locally: {full_path}")
    return full_path

def copy_file_locally(source_path: str, destination_path: str) -> str:
    """Copy file locally."""
    paths = get_local_paths()
    full_dest_path = os.path.join(paths['output_dir'], destination_path)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(full_dest_path), exist_ok=True)
    
    shutil.copy2(source_path, full_dest_path)
    logger.info(f"📋 File copied locally: {source_path} -> {full_dest_path}")
    return full_dest_path

def list_local_files(directory: str = "") -> list:
    """List files in local storage."""
    paths = get_local_paths()
    base_path = os.path.join(paths['output_dir'], directory)
    
    if not os.path.exists(base_path):
        return []
    
    files = []
    for root, dirs, filenames in os.walk(base_path):
        for filename in filenames:
            rel_path = os.path.relpath(os.path.join(root, filename), base_path)
            files.append(rel_path)
    
    return files

def get_local_file_info(file_path: str) -> Optional[dict]:
    """Get information about a local file."""
    paths = get_local_paths()
    full_path = os.path.join(paths['output_dir'], file_path)
    
    if not os.path.exists(full_path):
        return None
    
    stat = os.stat(full_path)
    return {
        'name': file_path,
        'size': stat.st_size,
        'modified': stat.st_mtime,
        'path': full_path
    }
