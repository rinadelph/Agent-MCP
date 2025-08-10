# Agent-MCP Database Utilities
"""
Standardized database utilities for the Agent-MCP system.
Provides consistent database operations with proper error handling.
"""

import sqlite3
import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Union
from contextlib import contextmanager
from functools import wraps

from ..core.config import logger
from .error_utils import DatabaseError, safe_database_operation

@contextmanager
def get_db_connection_context():
    """
    Context manager for database connections with proper error handling.
    
    Yields:
        sqlite3.Connection: Database connection
        
    Raises:
        DatabaseError: If connection fails
    """
    conn = None
    try:
        from ..db.connection import get_db_connection
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        yield conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}", exc_info=True)
        raise DatabaseError(f"Database connection failed: {e}")
    finally:
        if conn:
            try:
                conn.close()
            except Exception as e:
                logger.warning(f"Error closing database connection: {e}")

def execute_query(query: str, params: Tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
    """
    Execute a SELECT query and return results as dictionaries.
    
    Args:
        query: SQL query string
        params: Query parameters
        
    Returns:
        List of dictionaries representing query results
        
    Raises:
        DatabaseError: If query execution fails
    """
    with get_db_connection_context() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            logger.error(f"Query execution failed: {e}", exc_info=True)
            raise DatabaseError(f"Query execution failed: {e}")

def execute_update(query: str, params: Tuple[Any, ...] = ()) -> int:
    """
    Execute an UPDATE/INSERT/DELETE query and return affected row count.
    
    Args:
        query: SQL query string
        params: Query parameters
        
    Returns:
        Number of affected rows
        
    Raises:
        DatabaseError: If query execution fails
    """
    with get_db_connection_context() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
        except sqlite3.Error as e:
            logger.error(f"Update execution failed: {e}", exc_info=True)
            raise DatabaseError(f"Update execution failed: {e}")

def execute_transaction(queries: List[Tuple[str, Tuple[Any, ...]]]) -> None:
    """
    Execute multiple queries in a single transaction.
    
    Args:
        queries: List of (query, params) tuples
        
    Raises:
        DatabaseError: If any query fails
    """
    with get_db_connection_context() as conn:
        cursor = conn.cursor()
        try:
            for query, params in queries:
                cursor.execute(query, params)
            conn.commit()
        except sqlite3.Error as e:
            conn.rollback()
            logger.error(f"Transaction failed: {e}", exc_info=True)
            raise DatabaseError(f"Transaction failed: {e}")

def safe_query(func):
    """
    Decorator for safe query operations.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function with error handling
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except sqlite3.Error as e:
            logger.error(f"Database query failed in {func.__name__}: {e}", exc_info=True)
            raise DatabaseError(f"Database query failed: {e}")
    return wrapper

def validate_table_exists(table_name: str) -> bool:
    """
    Check if a table exists in the database.
    
    Args:
        table_name: Name of the table to check
        
    Returns:
        True if table exists, False otherwise
    """
    query = """
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name=?
    """
    try:
        result = execute_query(query, (table_name,))
        return len(result) > 0
    except DatabaseError:
        return False

def get_table_schema(table_name: str) -> List[Dict[str, Any]]:
    """
    Get the schema for a table.
    
    Args:
        table_name: Name of the table
        
    Returns:
        List of column information dictionaries
    """
    query = "PRAGMA table_info(?)"
    return execute_query(query, (table_name,))

def count_rows(table_name: str, where_clause: str = "", params: Tuple[Any, ...] = ()) -> int:
    """
    Count rows in a table with optional WHERE clause.
    
    Args:
        table_name: Name of the table
        where_clause: Optional WHERE clause
        params: Parameters for WHERE clause
        
    Returns:
        Number of rows
    """
    query = f"SELECT COUNT(*) as count FROM {table_name}"
    if where_clause:
        query += f" WHERE {where_clause}"
    
    result = execute_query(query, params)
    return result[0]['count'] if result else 0

def insert_record(table_name: str, data: Dict[str, Any]) -> int:
    """
    Insert a record into a table.
    
    Args:
        table_name: Name of the table
        data: Dictionary of column names and values
        
    Returns:
        ID of the inserted record
    """
    columns = list(data.keys())
    placeholders = ','.join(['?' for _ in columns])
    values = tuple(data.values())
    
    query = f"INSERT INTO {table_name} ({','.join(columns)}) VALUES ({placeholders})"
    
    with get_db_connection_context() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(query, values)
            conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            logger.error(f"Insert failed: {e}", exc_info=True)
            raise DatabaseError(f"Insert failed: {e}")

def update_record(table_name: str, data: Dict[str, Any], where_clause: str, where_params: Tuple[Any, ...]) -> int:
    """
    Update records in a table.
    
    Args:
        table_name: Name of the table
        data: Dictionary of column names and new values
        where_clause: WHERE clause for update
        where_params: Parameters for WHERE clause
        
    Returns:
        Number of affected rows
    """
    set_clause = ','.join([f"{col}=?" for col in data.keys()])
    query = f"UPDATE {table_name} SET {set_clause} WHERE {where_clause}"
    params = tuple(data.values()) + where_params
    
    return execute_update(query, params)

def delete_records(table_name: str, where_clause: str, params: Tuple[Any, ...]) -> int:
    """
    Delete records from a table.
    
    Args:
        table_name: Name of the table
        where_clause: WHERE clause for deletion
        params: Parameters for WHERE clause
        
    Returns:
        Number of affected rows
    """
    query = f"DELETE FROM {table_name} WHERE {where_clause}"
    return execute_update(query, params)

def json_serializable(obj: Any) -> Any:
    """
    Convert an object to JSON serializable format.
    
    Args:
        obj: Object to convert
        
    Returns:
        JSON serializable object
    """
    if isinstance(obj, (dict, list, str, int, float, bool, type(None))):
        return obj
    else:
        return str(obj)

def prepare_json_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Prepare data for JSON storage in database.
    
    Args:
        data: Dictionary to prepare
        
    Returns:
        Dictionary with JSON serializable values
    """
    return {key: json_serializable(value) for key, value in data.items()}

def store_json_data(table_name: str, data: Dict[str, Any], json_columns: List[str]) -> int:
    """
    Store data with JSON serialization for specified columns.
    
    Args:
        table_name: Name of the table
        data: Dictionary of column names and values
        json_columns: List of column names to serialize as JSON
        
    Returns:
        ID of the inserted record
    """
    prepared_data = data.copy()
    for col in json_columns:
        if col in prepared_data and prepared_data[col] is not None:
            prepared_data[col] = json.dumps(prepared_data[col])
    
    return insert_record(table_name, prepared_data)

def load_json_data(record: Dict[str, Any], json_columns: List[str]) -> Dict[str, Any]:
    """
    Load and deserialize JSON data from a database record.
    
    Args:
        record: Database record dictionary
        json_columns: List of column names that contain JSON data
        
    Returns:
        Dictionary with deserialized JSON values
    """
    result = record.copy()
    for col in json_columns:
        if col in result and result[col] is not None:
            try:
                result[col] = json.loads(result[col])
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Failed to deserialize JSON for column {col}")
                result[col] = None
    
    return result
