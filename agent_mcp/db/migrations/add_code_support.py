#!/usr/bin/env python3
"""
Migration script to add code-aware RAG support to existing databases.

This script:
1. Adds the metadata column to rag_chunks table if missing
2. Adds the last_indexed_code entry to rag_meta if missing
3. Re-creates the rag_embeddings table with the new dimension (3072)
"""

import sqlite3
import sys
from pathlib import Path

# Add parent directories to path to import our modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from agent_mcp.db.connection import get_db_connection
from agent_mcp.core.config import logger, EMBEDDING_DIMENSION


def migrate_database():
    """Run the migration to add code-aware support."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Check if metadata column exists in rag_chunks
        cursor.execute("PRAGMA table_info(rag_chunks)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'metadata' not in columns:
            logger.info("Adding metadata column to rag_chunks table...")
            cursor.execute("ALTER TABLE rag_chunks ADD COLUMN metadata TEXT")
            logger.info("Metadata column added successfully.")
        else:
            logger.info("Metadata column already exists in rag_chunks table.")
        
        # 2. Add last_indexed_code to rag_meta if missing
        cursor.execute("SELECT meta_value FROM rag_meta WHERE meta_key = ?", ('last_indexed_code',))
        if cursor.fetchone() is None:
            logger.info("Adding last_indexed_code to rag_meta...")
            cursor.execute(
                "INSERT INTO rag_meta (meta_key, meta_value) VALUES (?, ?)",
                ('last_indexed_code', '1970-01-01T00:00:00Z')
            )
            logger.info("last_indexed_code added successfully.")
        else:
            logger.info("last_indexed_code already exists in rag_meta.")
        
        # 3. Check embedding dimension
        # First check if rag_embeddings exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rag_embeddings'")
        if cursor.fetchone() is not None:
            # Get current dimension
            cursor.execute("PRAGMA table_info(rag_embeddings)")
            table_info = cursor.fetchall()
            
            # For virtual tables, we need to check differently
            # Try to get the SQL that created the table
            cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='rag_embeddings'")
            create_sql = cursor.fetchone()
            
            # Extract current dimension from SQL
            current_dim = None
            if '1024' in create_sql[0]:
                current_dim = 1024
            elif '1536' in create_sql[0]:
                current_dim = 1536
            elif '3072' in create_sql[0]:
                current_dim = 3072
            
            if current_dim and current_dim != EMBEDDING_DIMENSION:
                logger.warning(f"rag_embeddings table uses {current_dim} dimensions but config uses {EMBEDDING_DIMENSION}.")
                logger.warning(f"To use {EMBEDDING_DIMENSION} dimensions, you need to:")
                logger.warning("1. Delete all existing embeddings: DELETE FROM rag_embeddings;")
                logger.warning("2. Drop and recreate the table: DROP TABLE rag_embeddings;")
                logger.warning("3. Re-run the server to recreate with new dimensions")
                logger.warning("4. Let the indexer re-generate all embeddings")
                logger.warning("Note: The server will automatically handle this when dimension changes are detected.")
            elif create_sql and str(EMBEDDING_DIMENSION) in create_sql[0]:
                logger.info(f"rag_embeddings table already uses {EMBEDDING_DIMENSION} dimensions.")
            else:
                logger.info("Could not determine current embedding dimensions.")
        else:
            logger.info("rag_embeddings table does not exist. It will be created with correct dimensions on first run.")
        
        # Commit all changes
        conn.commit()
        logger.info("Migration completed successfully!")
        
    except sqlite3.Error as e:
        logger.error(f"Database error during migration: {e}")
        if conn:
            conn.rollback()
        raise
    except Exception as e:
        logger.error(f"Unexpected error during migration: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    print("Agent-MCP Code-Aware RAG Migration")
    print("==================================")
    print(f"This will migrate your database to support code-aware RAG with {EMBEDDING_DIMENSION} dimensions.")
    print()
    
    response = input("Do you want to proceed? (y/N): ")
    if response.lower() == 'y':
        migrate_database()
    else:
        print("Migration cancelled.")