# Base Migration Class
"""
Base class for database migrations in Agent-MCP.
"""

import sqlite3
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime

from ...core.config import logger


class BaseMigration(ABC):
    """Base class for database migrations."""
    
    def __init__(self):
        self.version = self.get_version()
        self.description = self.get_description()
        self.created_at = datetime.now()
    
    @abstractmethod
    def get_version(self) -> str:
        """Get the migration version."""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Get the migration description."""
        pass
    
    @abstractmethod
    def up(self, conn: sqlite3.Connection) -> None:
        """Apply the migration."""
        pass
    
    @abstractmethod
    def down(self, conn: sqlite3.Connection) -> None:
        """Rollback the migration."""
        pass
    
    def execute_sql(self, conn: sqlite3.Connection, sql: str, params: Optional[tuple] = None) -> None:
        """Execute SQL with error handling."""
        try:
            cursor = conn.cursor()
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            conn.commit()
            logger.debug(f"Migration {self.version}: Executed SQL successfully")
        except sqlite3.Error as e:
            logger.error(f"Migration {self.version}: SQL execution failed: {e}")
            conn.rollback()
            raise
    
    def table_exists(self, conn: sqlite3.Connection, table_name: str) -> bool:
        """Check if a table exists."""
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        return cursor.fetchone() is not None
    
    def column_exists(self, conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
        """Check if a column exists in a table."""
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        return any(col[1] == column_name for col in columns)
    
    def get_table_columns(self, conn: sqlite3.Connection, table_name: str) -> List[str]:
        """Get all column names for a table."""
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        return [col[1] for col in columns]
    
    def add_column(self, conn: sqlite3.Connection, table_name: str, column_name: str, 
                   column_type: str, default_value: Optional[str] = None) -> None:
        """Add a column to an existing table."""
        if not self.column_exists(conn, table_name, column_name):
            sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            if default_value:
                sql += f" DEFAULT {default_value}"
            self.execute_sql(conn, sql)
            logger.info(f"Migration {self.version}: Added column {column_name} to {table_name}")
    
    def create_index(self, conn: sqlite3.Connection, index_name: str, table_name: str, 
                    columns: List[str], unique: bool = False) -> None:
        """Create an index on a table."""
        unique_str = "UNIQUE" if unique else ""
        columns_str = ", ".join(columns)
        sql = f"CREATE {unique_str} INDEX {index_name} ON {table_name} ({columns_str})"
        self.execute_sql(conn, sql)
        logger.info(f"Migration {self.version}: Created index {index_name} on {table_name}")
    
    def drop_index(self, conn: sqlite3.Connection, index_name: str) -> None:
        """Drop an index."""
        sql = f"DROP INDEX IF EXISTS {index_name}"
        self.execute_sql(conn, sql)
        logger.info(f"Migration {self.version}: Dropped index {index_name}")
    
    def rename_table(self, conn: sqlite3.Connection, old_name: str, new_name: str) -> None:
        """Rename a table."""
        sql = f"ALTER TABLE {old_name} RENAME TO {new_name}"
        self.execute_sql(conn, sql)
        logger.info(f"Migration {self.version}: Renamed table {old_name} to {new_name}")
    
    def drop_table(self, conn: sqlite3.Connection, table_name: str) -> None:
        """Drop a table."""
        sql = f"DROP TABLE IF EXISTS {table_name}"
        self.execute_sql(conn, sql)
        logger.info(f"Migration {self.version}: Dropped table {table_name}")
    
    def copy_table_data(self, conn: sqlite3.Connection, source_table: str, 
                       target_table: str, columns: Optional[List[str]] = None) -> None:
        """Copy data from one table to another."""
        if columns:
            columns_str = ", ".join(columns)
            sql = f"INSERT INTO {target_table} ({columns_str}) SELECT {columns_str} FROM {source_table}"
        else:
            sql = f"INSERT INTO {target_table} SELECT * FROM {source_table}"
        
        self.execute_sql(conn, sql)
        logger.info(f"Migration {self.version}: Copied data from {source_table} to {target_table}")
    
    def validate_migration(self, conn: sqlite3.Connection) -> bool:
        """Validate that the migration can be applied."""
        try:
            # Test the migration without committing
            conn.execute("BEGIN TRANSACTION")
            self.up(conn)
            conn.rollback()
            return True
        except Exception as e:
            logger.error(f"Migration {self.version} validation failed: {e}")
            return False
