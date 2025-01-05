from sqlmesh import macro
import re
from constants import SQLMESH_DIR
import os
from typing import Union


def convert_duckdb_type_to_ibis(duckdb_type):
    # Convert to string and uppercase for consistency
    type_str = str(duckdb_type).upper()

    # Extract base type by removing anything after '(' if it exists
    # Handling dtype such as DECIMAL(18,3)
    base_type = type_str.split("(")[0].strip()

    type_mapping = {
        "TEXT": "String",
        "VARCHAR": "String",
        "CHAR": "String",
        "INT": "Int",
        "INTEGER": "Int",
        "BIGINT": "Int",
        "DECIMAL": "Decimal",
        "NUMERIC": "Decimal",
    }
    return type_mapping.get(base_type, "String")  # Default to String if unknown


@macro()
def get_sql_model_schema(evaluator, sql_file_name, folder_path_from_models_folder):
    """Get schema from a SQL model file.
    
    Args:
        evaluator: SQLMesh evaluator instance
        sql_file_name: Name of the SQL file without extension
        folder_path_from_models_folder: Path from models folder (e.g. 'edu' or 'wdi')
                                      The path should match the source data folder
    """
    file_path = f"{SQLMESH_DIR}/models/sources/{folder_path_from_models_folder}/{sql_file_name.lower()}.sql"
    with open(file_path, "r") as file:
        sql_content = file.read()

    # Regular expression to match the MODEL section
    model_pattern = re.compile(
        r"MODEL\s*\([\s\S]*?columns\s*\(\s*([\s\S]*?)\s*\)[\s\S]*?\)", re.IGNORECASE
    )
    match = model_pattern.search(sql_content)

    if not match:
        return {}

    columns_section = match.group(1)

    # Regular expression to extract column name and type
    # This pattern now accounts for column names with spaces, assuming they are quoted
    column_pattern = re.compile(r'"?([\w\s]+)"?\s+(\w+)', re.IGNORECASE)
    columns = column_pattern.findall(columns_section)

    # Convert list of tuples to dictionary
    columns_dict = {
        name.strip().lower(): convert_duckdb_type_to_ibis(str(col_type))
        for name, col_type in columns
    }

    return columns_dict


def get_s3_path(subfolder_filename: Union[str, str]) -> str:
    """
    Constructs an S3 path based on environment variables and the provided subfolder/filename.
    """
    bucket = os.environ.get('S3_BUCKET_NAME', 'osaa-mvp')
    target = os.environ.get('TARGET', 'prod').lower()
    username = os.environ.get('USERNAME', 'default').lower()
    
    if target == "prod":
        env_path = target
    else:
        env_path = f"{target}_{username}"
    
    if not isinstance(subfolder_filename, str):
        subfolder_filename = str(subfolder_filename).strip("'")
    
    path = f's3://{bucket}/{env_path}/landing/{subfolder_filename}.parquet'
    return path
