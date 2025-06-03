"""Database utility functions for robust database operations"""
import sqlite3
import asyncio
import time
from typing import Any, Callable, Optional, TypeVar, Union
from functools import wraps
import random

from ..core.config import logger

T = TypeVar('T')


class DatabaseError(Exception):
    """Base exception for database operations"""
    pass


class DatabaseLockError(DatabaseError):
    """Raised when database is locked"""
    pass


def retry_on_lock(
    func: Callable[..., T],
    max_retries: int = 5,
    initial_delay: float = 0.1,
    max_delay: float = 2.0,
    backoff_factor: float = 2.0,
    jitter: bool = True
) -> T:
    """
    Retry a function on database lock errors with exponential backoff.
    
    Args:
        func: The function to retry
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        backoff_factor: Factor to multiply delay by after each retry
        jitter: Add random jitter to delays to prevent thundering herd
    
    Returns:
        The result of the function call
    
    Raises:
        DatabaseLockError: If all retries are exhausted
    """
    last_exception = None
    delay = initial_delay
    
    for attempt in range(max_retries + 1):
        try:
            return func()
        except sqlite3.OperationalError as e:
            if "database is locked" not in str(e):
                raise
            
            last_exception = e
            if attempt == max_retries:
                break
            
            # Calculate delay with optional jitter
            if jitter:
                actual_delay = delay * (0.5 + random.random())
            else:
                actual_delay = delay
            
            logger.warning(
                f"Database locked (attempt {attempt + 1}/{max_retries + 1}), "
                f"retrying in {actual_delay:.2f}s..."
            )
            
            # Run diagnostics on first lock detection
            if attempt == 0:
                try:
                    from .lock_diagnostics import log_database_lock_diagnostics
                    log_database_lock_diagnostics()
                except Exception as diag_e:
                    logger.debug(f"Could not run lock diagnostics: {diag_e}")
            
            time.sleep(actual_delay)
            
            # Exponential backoff
            delay = min(delay * backoff_factor, max_delay)
    
    raise DatabaseLockError(
        f"Database remained locked after {max_retries + 1} attempts"
    ) from last_exception


def with_retry(
    max_retries: int = 5,
    initial_delay: float = 0.1,
    max_delay: float = 2.0,
    backoff_factor: float = 2.0,
    jitter: bool = True
):
    """
    Decorator to retry database operations on lock errors.
    
    Can be used with both sync and async functions.
    """
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                last_exception = None
                delay = initial_delay
                
                for attempt in range(max_retries + 1):
                    try:
                        return await func(*args, **kwargs)
                    except sqlite3.OperationalError as e:
                        if "database is locked" not in str(e):
                            raise
                        
                        last_exception = e
                        if attempt == max_retries:
                            break
                        
                        # Calculate delay with optional jitter
                        if jitter:
                            actual_delay = delay * (0.5 + random.random())
                        else:
                            actual_delay = delay
                        
                        logger.warning(
                            f"Database locked (attempt {attempt + 1}/{max_retries + 1}), "
                            f"retrying in {actual_delay:.2f}s..."
                        )
                        
                        # Run diagnostics on first lock detection
                        if attempt == 0:
                            try:
                                from .lock_diagnostics import log_database_lock_diagnostics
                                log_database_lock_diagnostics()
                            except Exception as diag_e:
                                logger.debug(f"Could not run lock diagnostics: {diag_e}")
                        
                        await asyncio.sleep(actual_delay)
                        
                        # Exponential backoff
                        delay = min(delay * backoff_factor, max_delay)
                
                raise DatabaseLockError(
                    f"Database remained locked after {max_retries + 1} attempts"
                ) from last_exception
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                return retry_on_lock(
                    lambda: func(*args, **kwargs),
                    max_retries=max_retries,
                    initial_delay=initial_delay,
                    max_delay=max_delay,
                    backoff_factor=backoff_factor,
                    jitter=jitter
                )
            return sync_wrapper
    
    return decorator


def configure_connection_for_migration(conn: sqlite3.Connection) -> None:
    """
    Configure a database connection for migration operations.
    
    Sets appropriate pragmas for better concurrency and performance during migrations.
    """
    # Set a long timeout for locked databases
    conn.execute("PRAGMA busy_timeout = 30000;")  # 30 seconds
    
    # Use Write-Ahead Logging for better concurrency
    conn.execute("PRAGMA journal_mode = WAL;")
    
    # Synchronous mode NORMAL is faster but still safe with WAL
    conn.execute("PRAGMA synchronous = NORMAL;")
    
    # Increase cache size for better performance
    conn.execute("PRAGMA cache_size = -64000;")  # 64MB cache
    
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON;")
    
    logger.debug("Database connection configured for migration")


def execute_in_transaction(
    conn: sqlite3.Connection,
    operations: list[Callable[[sqlite3.Cursor], None]],
    batch_size: Optional[int] = None
) -> None:
    """
    Execute multiple operations in a transaction with optional batching.
    
    Args:
        conn: Database connection
        operations: List of functions that take a cursor and perform operations
        batch_size: If provided, commit after every batch_size operations
    """
    cursor = conn.cursor()
    
    try:
        if batch_size is None:
            # Execute all operations in a single transaction
            conn.execute("BEGIN IMMEDIATE;")
            for op in operations:
                op(cursor)
            conn.commit()
        else:
            # Execute in batches
            for i in range(0, len(operations), batch_size):
                conn.execute("BEGIN IMMEDIATE;")
                batch = operations[i:i + batch_size]
                for op in batch:
                    op(cursor)
                conn.commit()
                
                if i + batch_size < len(operations):
                    # Small delay between batches to allow other processes
                    time.sleep(0.01)
                    
    except Exception as e:
        conn.rollback()
        raise


def check_database_health(conn: sqlite3.Connection) -> dict[str, Any]:
    """
    Check the health of the database connection and return diagnostics.
    
    Returns:
        Dictionary with health information
    """
    cursor = conn.cursor()
    health = {}
    
    try:
        # Check if we can execute a simple query
        cursor.execute("SELECT 1")
        health['can_query'] = True
        
        # Check journal mode
        cursor.execute("PRAGMA journal_mode")
        health['journal_mode'] = cursor.fetchone()[0]
        
        # Check busy timeout
        cursor.execute("PRAGMA busy_timeout")
        health['busy_timeout'] = cursor.fetchone()[0]
        
        # Check if any transactions are active
        cursor.execute("PRAGMA wal_checkpoint(PASSIVE)")
        checkpoint_result = cursor.fetchone()
        health['wal_pages'] = checkpoint_result[1] if checkpoint_result else 0
        
        # Count active connections (approximate)
        try:
            cursor.execute("PRAGMA database_list")
            health['database_list'] = cursor.fetchall()
        except:
            health['database_list'] = []
        
        health['status'] = 'healthy'
        
    except sqlite3.OperationalError as e:
        health['status'] = 'unhealthy'
        health['error'] = str(e)
        if "database is locked" in str(e):
            health['locked'] = True
    
    return health