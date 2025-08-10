# Agent-MCP/mcp_template/mcp_server_src/db/connection.py
import sqlite3
import os  # Still needed for os.environ if get_db_path is not used directly for some reason
from pathlib import Path

# Import the sqlite_vec library if available.
# This allows the module to be imported even if sqlite_vec is not installed,
# and the loadability check will handle its absence.
try:
    import sqlite_vec
except ImportError:
    sqlite_vec = None  # Allows checks like `if sqlite_vec:`

# Imports from our core configuration module
from ..core.config import logger, get_db_path
from ..core import globals as g  # For setting global VSS flags

# Import write queue for serializing database write operations
from .write_queue import get_write_queue, execute_write_operation

# Module-level flags for VSS loadability, now directly using the global ones.
# These are initialized in mcp_server_src.core.globals
# _vss_load_tested: bool = False # Replaced by g.global_vss_load_tested
# _vss_load_successful: bool = False # Replaced by g.global_vss_load_successful


def is_vss_loadable() -> bool:
    """
    Returns whether the sqlite-vec extension was successfully loaded during the initial check.
    This function relies on `check_vss_loadability` having been called, typically at startup.
    """
    if not g.global_vss_load_tested:
        # It's better if check_vss_loadability is explicitly called once at startup.
        # Calling it here on-demand might lead to multiple checks or unexpected timing.
        logger.warning(
            "is_vss_loadable() called before initial VSS loadability check. Performing check now."
        )
        check_vss_loadability()
    return g.global_vss_load_successful


# Original location: main.py lines 203-226 (check_vss_loadability function)
def check_vss_loadability() -> bool:
    """
    Tries loading sqlite-vec on a temporary in-memory connection to see if it works.
    Sets global flags `g.global_vss_load_tested` and `g.global_vss_load_successful`.
    This function should be called once at application startup.
    """
    if g.global_vss_load_tested:
        return g.global_vss_load_successful

    if sqlite_vec is None:
        logger.error(
            "sqlite-vec library is not installed. RAG functionality will be disabled."
        )
        g.global_vss_load_successful = False
        g.global_vss_load_tested = True
        return False

    logger.info("Performing initial check for sqlite-vec loadability...")
    temp_conn = None
    try:
        # Using an in-memory database for this check is safest.
        temp_conn = sqlite3.connect(":memory:")
        temp_conn.enable_load_extension(True)
        sqlite_vec.load(
            temp_conn
        )  # Call the load function from the imported sqlite_vec
        temp_conn.enable_load_extension(False)
        logger.info("sqlite-vec extension appears loadable.")
        g.global_vss_load_successful = True
    except AttributeError:  # From main.py:207 (original line numbers)
        logger.error(
            "Installed sqlite3 version doesn't support enable_load_extension. sqlite-vec cannot be loaded."
        )
        g.global_vss_load_successful = False
    except sqlite3.Error as e:  # Catch sqlite3 specific errors during load
        logger.error(
            f"SQLite error during initial check for sqlite-vec: {e}", exc_info=True
        )
        g.global_vss_load_successful = False
    except Exception as e:  # From main.py:210 (original line numbers)
        logger.error(
            f"Initial check: Failed to load sqlite-vec extension: {e}", exc_info=True
        )
        logger.error(
            "RAG functionality will be disabled. Ensure 'sqlite-vec' is installed and SQLite supports extensions."
        )
        g.global_vss_load_successful = False
    finally:
        if temp_conn:
            temp_conn.close()

    g.global_vss_load_tested = True
    return g.global_vss_load_successful


# Original location: main.py lines 228-263 (get_db_connection function)
def get_db_connection() -> sqlite3.Connection:
    """
    Establishes and returns a connection to the SQLite database.
    If `is_vss_loadable()` is true, it attempts to load the sqlite-vec extension for this connection.
    """
    db_file_path = get_db_path()  # Uses the function from core.config

    # Ensure the directory for the database exists
    try:
        db_file_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(
            f"Failed to create directory for database at {db_file_path.parent}: {e}"
        )
        raise RuntimeError(f"Could not create database directory: {e}") from e

    conn = None
    try:
        # From main.py:225 (original line numbers)
        conn = sqlite3.connect(
            str(db_file_path), check_same_thread=False, timeout=10.0
        )  # Added timeout
        # From main.py:226 (original line numbers)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")  # Improve concurrency and performance
        conn.execute("PRAGMA foreign_keys = ON;")  # Enforce foreign key constraints

        # Attempt to load VSS extension if it was deemed loadable globally and sqlite_vec is imported
        if g.global_vss_load_successful and sqlite_vec:
            try:
                # From main.py:228 (original line numbers)
                conn.enable_load_extension(True)
                # From main.py:230 (original line numbers)
                sqlite_vec.load(conn)
                # logger.debug("sqlite-vec loaded for this database connection.") # From main.py:231
            except AttributeError:
                # This specific connection's sqlite3 might not support it, even if the check passed.
                # Or, sqlite_vec.load might fail for other reasons on this specific connection.
                logger.warning(
                    "This sqlite3 connection instance does not support enable_load_extension, or sqlite_vec.load failed."
                )
                # VSS features will not be available on this connection.
            except sqlite3.Error as e_load:  # Catch sqlite3 specific errors during load
                logger.error(
                    f"SQLite error loading sqlite-vec for new connection: {e_load}"
                )
            except Exception as e_load_ext:  # From main.py:232 (original line numbers)
                logger.error(
                    f"Failed to load sqlite-vec for new connection: {e_load_ext}"
                )
            finally:
                # Always disable extension loading after attempting, regardless of success.
                # From main.py:235-238 (original line numbers)
                try:
                    conn.enable_load_extension(False)
                except (
                    sqlite3.Error,
                    AttributeError,
                ):  # Catch errors if disabling also fails or not supported
                    pass
        else:
            if (
                sqlite_vec
            ):  # Only log this if sqlite_vec was imported but not deemed loadable
                logger.debug(
                    "sqlite-vec extension not loaded for this connection (globally not loadable or library not found)."
                )

    except (
        AttributeError
    ) as e_attr:  # From main.py:240, if sqlite3 itself is too old for enable_load_extension
        logger.error(
            f"The sqlite3 library version does not support enable_load_extension: {e_attr}. sqlite-vec cannot be used."
        )
        if conn:
            conn.close()
        # This is a critical issue if VSS is expected.
        raise RuntimeError(
            "SQLite version does not support extension loading."
        ) from e_attr
    except sqlite3.OperationalError as e_op:  # More specific error for DB file issues
        logger.error(
            f"SQLite OperationalError connecting to DB at '{db_file_path}': {e_op}",
            exc_info=True,
        )
        if conn:
            conn.close()
        raise RuntimeError(f"Failed to connect to database: {e_op}") from e_op
    except (
        sqlite3.Error
    ) as e_sql:  # From main.py:244 (original line numbers) - general SQLite errors
        logger.error(
            f"SQLite error connecting to or setting up DB connection at '{db_file_path}': {e_sql}",
            exc_info=True,
        )
        if conn:
            conn.close()
        raise RuntimeError(
            f"Database connection error: {e_sql}"
        ) from e_sql  # Re-raise as a more generic runtime error
    except (
        Exception
    ) as e_unexpected:  # From main.py:248 (original line numbers) - other unexpected errors
        logger.error(
            f"Unexpected error getting DB connection for '{db_file_path}': {e_unexpected}",
            exc_info=True,
        )
        if conn:
            conn.close()
        raise RuntimeError(
            f"Unexpected database connection error: {e_unexpected}"
        ) from e_unexpected

    if conn is None:  # Should not happen if exceptions are raised, but as a safeguard.
        raise RuntimeError(
            f"Failed to establish database connection to {db_file_path}."
        )

    return conn


def get_db_connection_read() -> sqlite3.Connection:
    """
    Get a database connection for read operations.
    This is an alias for get_db_connection() for clarity.
    """
    return get_db_connection()


async def execute_db_write(operation_func):
    """
    Execute a database write operation through the write queue.

    Args:
        operation_func: A function that performs the database write operation

    Returns:
        The result of the write operation
    """
    return await execute_write_operation(operation_func)
