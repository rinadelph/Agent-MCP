# Agent-MCP/mcp_template/mcp_server_src/db/schema.py
import sqlite3

# Imports from our own modules
from ..core.config import logger, EMBEDDING_DIMENSION # EMBEDDING_DIMENSION from config
from .connection import get_db_connection, check_vss_loadability, is_vss_loadable
# No direct need for globals here, VSS loadability is checked via connection module functions.

# Original location: main.py lines 265-370 (init_database function)
def check_embedding_dimension_compatibility(conn: sqlite3.Connection) -> bool:
    """
    Check if the current rag_embeddings table dimension matches the configured dimension.
    Returns True if compatible or table doesn't exist, False if incompatible.
    """
    cursor = conn.cursor()
    
    # Check if rag_embeddings exists
    cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='rag_embeddings'")
    result = cursor.fetchone()
    
    if result is None:
        # Table doesn't exist, so it's compatible (will be created with correct dimension)
        return True
    
    create_sql = result[0]
    
    # Check if the current dimension matches the configured dimension
    if f"FLOAT[{EMBEDDING_DIMENSION}]" in create_sql:
        return True
    
    # Check for old dimensions
    if "FLOAT[1024]" in create_sql or "FLOAT[1536]" in create_sql or "FLOAT[3072]" in create_sql:
        current_dim = None
        if "FLOAT[1024]" in create_sql:
            current_dim = 1024
        elif "FLOAT[1536]" in create_sql:
            current_dim = 1536
        elif "FLOAT[3072]" in create_sql:
            current_dim = 3072
        
        if current_dim != EMBEDDING_DIMENSION:
            logger.warning(f"Embedding dimension mismatch: table has {current_dim}, config expects {EMBEDDING_DIMENSION}")
            # If it's 1024 (very old version), always recreate
            if current_dim == 1024:
                logger.info("Detected very old embedding dimension (1024), will recreate table")
            return False
    
    return True


def handle_embedding_dimension_change(conn: sqlite3.Connection) -> None:
    """
    Handle embedding dimension changes by dropping and recreating the embeddings table.
    This will cause all embeddings to be regenerated.
    """
    cursor = conn.cursor()
    
    logger.warning("Handling embedding dimension change...")
    
    # Delete all embeddings
    cursor.execute("DELETE FROM rag_embeddings")
    
    # Drop the old table
    cursor.execute("DROP TABLE IF EXISTS rag_embeddings")
    
    # Clear all stored hashes to force re-indexing
    cursor.execute("DELETE FROM rag_meta WHERE meta_key LIKE 'hash_%'")
    
    # Reset last indexed timestamps to force re-indexing
    cursor.execute("UPDATE rag_meta SET meta_value = '1970-01-01T00:00:00Z' WHERE meta_key LIKE 'last_indexed_%'")
    
    logger.info("Cleared embeddings and reset indexing timestamps for dimension change")


def init_database() -> None:
    """
    Initializes the SQLite database and creates tables if they don't exist.
    This function should be called once at application startup.
    """
    logger.info("Initializing database schema...")

    # Perform the VSS loadability check if it hasn't been done yet.
    # This ensures the check_vss_loadability sets the global flags correctly
    # before we decide whether to create the vector table.
    if not check_vss_loadability(): # This will run the check if not already run and return its success
        logger.warning("Initial VSS loadability check failed or VSS not available. RAG virtual table might not be created.")
    
    # `is_vss_loadable()` now reflects the outcome of the check.
    vss_is_actually_loadable = is_vss_loadable()

    conn = None
    try:
        conn = get_db_connection() # This connection will also attempt to load VSS if available
        cursor = conn.cursor()

        # Agents Table (Original main.py lines 271-284)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS agents (
                token TEXT PRIMARY KEY,
                agent_id TEXT UNIQUE NOT NULL,
                capabilities TEXT, -- JSON List
                created_at TEXT NOT NULL,
                status TEXT NOT NULL, -- e.g., 'created', 'active', 'terminated'
                current_task TEXT,    -- Task ID
                working_directory TEXT NOT NULL,
                color TEXT,           -- For dashboard visualization
                terminated_at TEXT,   -- Timestamp of termination
                updated_at TEXT       -- Timestamp of last update
            )
        ''')
        logger.debug("Agents table ensured.")

        # Tasks Table (Original main.py lines 287-303)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                assigned_to TEXT,     -- Agent ID or None
                created_by TEXT NOT NULL, -- Agent ID or 'admin'
                status TEXT NOT NULL,     -- e.g., 'pending', 'in_progress', 'completed', 'cancelled', 'failed'
                priority TEXT NOT NULL,   -- e.g., 'low', 'medium', 'high'
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                parent_task TEXT,         -- Task ID of parent task or None
                child_tasks TEXT,         -- JSON List of child Task IDs
                depends_on_tasks TEXT,    -- JSON List of Task IDs this task depends on
                notes TEXT                -- JSON List of note objects: [{"timestamp": "", "author": "", "content": ""}]
            )
        ''')
        logger.debug("Tasks table ensured.")

        # Agent Actions Table (Original main.py lines 306-317)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_actions (
                action_id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent_id TEXT NOT NULL, -- Can be agent_id or 'admin'
                action_type TEXT NOT NULL, -- e.g., 'assigned_task', 'started_work', 'completed_task', 'updated_context', 'locked_file'
                task_id TEXT,          -- Optional: Link action to a specific task_id
                timestamp TEXT NOT NULL,
                details TEXT           -- Optional JSON blob for extra info (e.g., context_key, filepath, tool args)
            )
        """)
        # Indexes for agent_actions (Original main.py lines 318-319)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_actions_agent_id_timestamp ON agent_actions (agent_id, timestamp DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_actions_task_id_timestamp ON agent_actions (task_id, timestamp DESC)")
        logger.debug("Agent_actions table and indexes ensured.")

        # Project Context Table (Original main.py lines 322-330)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS project_context (
                context_key TEXT PRIMARY KEY,
                value TEXT NOT NULL,         -- Stored as JSON string
                last_updated TEXT NOT NULL,
                updated_by TEXT NOT NULL,    -- Agent ID or 'admin' or 'server_startup'
                description TEXT
            )
        ''')
        logger.debug("Project_context table ensured.")

        # File Metadata Table (Original main.py lines 333-340)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS file_metadata (
                filepath TEXT PRIMARY KEY,   -- Normalized, absolute path
                metadata TEXT NOT NULL,      -- JSON object containing various metadata keys/values
                last_updated TEXT NOT NULL,
                updated_by TEXT NOT NULL,    -- Agent ID or 'admin'
                content_hash TEXT            -- SHA256 hash of file content, for change detection
            )
        ''')
        logger.debug("File_metadata table ensured.")

        # RAG Chunks Table (Original main.py lines 343-351)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS rag_chunks (
                chunk_id INTEGER PRIMARY KEY AUTOINCREMENT, -- Matches rowid for vec0 table
                source_type TEXT NOT NULL, -- e.g., 'markdown', 'context', 'filemeta', 'codefile', 'code', 'code_summary'
                source_ref TEXT NOT NULL,  -- Filepath, context_key, or other reference
                chunk_text TEXT NOT NULL,
                indexed_at TEXT NOT NULL,
                metadata TEXT -- JSON object with chunk-specific metadata (entities, language, etc.)
            )
        ''')
        # Index for rag_chunks (Original main.py line 352)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_rag_chunks_source_type_ref ON rag_chunks (source_type, source_ref)")
        logger.debug("Rag_chunks table and index ensured.")

        # RAG Meta Table (for tracking indexing progress, hashes, etc.)
        # (Original main.py lines 355-362)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS rag_meta (
                meta_key TEXT PRIMARY KEY, 
                meta_value TEXT
            )
        """)
        # Initialize default timestamps if not present (Original main.py lines 360-362)
        default_meta_entries = [
            ('last_indexed_markdown', '1970-01-01T00:00:00Z'),
            ('last_indexed_code', '1970-01-01T00:00:00Z'),     # NEW for code-aware indexing
            ('last_indexed_context', '1970-01-01T00:00:00Z'),
            ('last_indexed_filemeta', '1970-01-01T00:00:00Z'),
            ('last_indexed_tasks', '1970-01-01T00:00:00Z')     # NEW for System 8
            # Add other source types here as they are supported for indexing
        ]
        cursor.executemany("INSERT OR IGNORE INTO rag_meta (meta_key, meta_value) VALUES (?, ?)", default_meta_entries)
        logger.debug("Rag_meta table and default entries ensured.")

        # RAG Embeddings Table (Virtual Table using sqlite-vec)
        # (Original main.py lines 365-379)
        if vss_is_actually_loadable:
            # Check if we need to handle dimension changes
            if not check_embedding_dimension_compatibility(conn):
                logger.warning("Embedding dimension has changed. Recreating embeddings table...")
                handle_embedding_dimension_change(conn)
            
            try:
                # Explicitly define the embedding column and its dimensions.
                # The table name `rag_embeddings` and `vec0` module are from the original.
                # `chunk_id` is implicitly the rowid and links to `rag_chunks.chunk_id`.
                cursor.execute(f'''
                    CREATE VIRTUAL TABLE IF NOT EXISTS rag_embeddings USING vec0(
                        embedding FLOAT[{EMBEDDING_DIMENSION}] 
                    )
                ''')
                # Note: sqlite-vec's `vec0` uses `rowid` to link to the source table.
                # The `chunk_id` from `rag_chunks` will be used as the `rowid` when inserting into `rag_embeddings`.
                logger.info(f"Vector table 'rag_embeddings' (using vec0 with dimension {EMBEDDING_DIMENSION}) ensured.")
            except sqlite3.OperationalError as e_vec:
                # This can happen if vec0 module is not found by SQLite despite earlier checks,
                # or if the syntax is incorrect for the loaded version.
                logger.error(f"Failed to create VIRTUAL vector table 'rag_embeddings': {e_vec}. RAG search functionality will be impaired.")
                # This is a critical error for RAG, but the server might continue without it.
                # The original code raised a RuntimeError here (main.py:375).
                # For robustness, we log it as an error. RAG features will check `is_vss_loadable()`
                # and the existence of this table before attempting vector operations.
            except Exception as e_vec_other:
                logger.error(f"Unexpected error creating vector table 'rag_embeddings': {e_vec_other}", exc_info=True)
        else:
            logger.warning("Skipping creation of RAG virtual table 'rag_embeddings' as sqlite-vec extension is not loadable or available.")

        conn.commit()
        logger.info("Database schema initialized successfully.")

    except sqlite3.Error as e:
        logger.error(f"A database error occurred during schema initialization: {e}", exc_info=True)
        if conn:
            conn.rollback()
        # This is a critical failure; the application likely cannot proceed without a working DB.
        raise RuntimeError(f"Failed to initialize database schema: {e}") from e
    except Exception as e:
        logger.error(f"An unexpected error occurred during schema initialization: {e}", exc_info=True)
        if conn:
            conn.rollback()
        raise RuntimeError(f"Unexpected error during database schema initialization: {e}") from e
    finally:
        if conn:
            conn.close()
            logger.debug("Database connection closed after schema initialization.")