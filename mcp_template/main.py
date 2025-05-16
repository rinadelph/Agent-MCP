import anyio
import click
import mcp.types as types
import os
import json
import secrets
import datetime
import shutil
import signal
import sys
import sqlite3 # Added
import hashlib # Added for hashing
import random # Added for color selection
import re # Added for JSON sanitizing
from pathlib import Path
from dotenv import load_dotenv
from mcp.server.lowlevel import Server
from mcp.server.sse import SseServerTransport
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

# Load environment variables from .env file
load_dotenv()
from starlette.templating import Jinja2Templates
from starlette.responses import JSONResponse, Response # Added Response
import uvicorn
import uuid
import subprocess
import logging
from typing import Dict, List, Optional, Any, Union
import time # Added for sleep/retry
import glob # Added for file scanning
import zipfile
import io
import sqlite_vec # Added

# Import the graph data function
from .dashboard_api import get_graph_data as get_graph_data_impl
from .dashboard_api import get_task_tree_data as get_task_tree_data_impl # Import new function

# --- Configuration ---
DB_FILE_NAME = "mcp_state.db"

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("mcp_server.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("mcp_server")

# --- JSON Sanitization Utility ---
def sanitize_json_input(input_data):
    """
    Sanitize JSON input aggressively to handle hidden Unicode characters, 
    misplaced whitespace, and line breaks.
    
    Args:
        input_data: Can be a string (potentially malformed JSON) or a Python object
        
    Returns:
        Properly parsed Python object (dict, list, etc.)
    """
    # If already a Python object (dict/list), just return it
    if isinstance(input_data, (dict, list)):
        return input_data
        
    # If not a string, convert to string
    if not isinstance(input_data, str):
        try:
            input_data = str(input_data)
        except Exception as e:
            logger.error(f"Failed to convert input to string: {e}")
            raise ValueError(f"Input must be a JSON string or Python object, got {type(input_data)}")
    
    # Step 1: Initial direct parse attempt
    try:
        return json.loads(input_data)
    except json.JSONDecodeError:
        pass # Continue cleaning if direct parse fails
    
    # Step 2: Aggressive Whitespace Removal (Handles CR/LF/Spaces between elements)
    # Remove whitespace after opening braces/brackets
    cleaned = re.sub(r'([\{\[])\s+', r'\1', input_data)
    # Remove whitespace before closing braces/brackets
    cleaned = re.sub(r'\s+([\}\]])', r'\1', cleaned)
    # Remove whitespace after commas and colons
    cleaned = re.sub(r'([:,])\s+', r'\1', cleaned)
    # Remove whitespace before commas
    cleaned = re.sub(r'\s+(,)', r'\1', cleaned)
    # Remove line breaks that might be separating elements
    cleaned = cleaned.replace('\r\n', '').replace('\n', '').replace('\r', '')

    # Step 3: Remove Control Characters (excluding tab \t)
    cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', cleaned)
    
    # Step 4: Remove problematic Unicode (Zero-width spaces, BOM)
    cleaned = re.sub(r'[\u200B-\u200F\uFEFF\u2028\u2029]', '', cleaned)
    
    # Step 5: Try parsing the aggressively cleaned string
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        # Step 6: Fallback for potentially nested/escaped JSON or other oddities
        try:
            # Try to find the main JSON object/array within the string
            match = re.search(r'^\s*(\{.*\}|\[.*\])\s*$', cleaned, re.DOTALL)
            if match:
                return json.loads(match.group(1))
        except json.JSONDecodeError:
             pass # If even the extracted part fails, fall through
        except Exception as inner_e:
             logger.warning(f"Inner regex/parse fallback failed: {inner_e}")
             pass

        # Log the final failure state for debugging
        error_excerpt = cleaned[:100] + ('...' if len(cleaned) > 100 else '')
        logger.error(f"Aggressive JSON parsing failed: {e}, cleaned data (excerpt): {error_excerpt}")
        raise ValueError(f"Failed to parse JSON even after aggressive sanitization: {e}")

# Helper function for API request handling
async def get_sanitized_json_body(request):
    """
    Helper function to safely get and sanitize a JSON request body.
    
    Args:
        request: The starlette request object
        
    Returns:
        The sanitized JSON data as a Python object
        
    Raises:
        ValueError: If the request body is not valid JSON
    """
    try:
        # Get the raw body data
        raw_body = await request.body()
        # Sanitize and parse it
        return sanitize_json_input(raw_body)
    except Exception as e:
        logger.error(f"Failed to parse request body: {e}")
        raise ValueError(f"Invalid request body: {e}")

# --- End JSON Sanitization Utility ---

# Global state to track connections and agents
connections = {}  # Client ID -> Connection data
active_agents = {}  # Token -> Agent data
admin_token = None
tasks = {}  # Global task registry

# New global state for tracking files and working directories
file_map = {}  # filepath -> {"agent_id": agent_id, "timestamp": timestamp, "status": "editing/reading/etc"}
agent_working_dirs = {}  # agent_id -> working_directory_path
audit_log = []  # List of audit entries

# Agent profiles counter (start from 20 counting down)
agent_profile_counter = 20

# Define a list of distinct colors for agents
AGENT_COLORS = [
    "#FF5733", "#33FF57", "#3357FF", "#FF33A1", "#A133FF", "#33FFA1",
    "#FFBD33", "#33FFBD", "#BD33FF", "#FF3333", "#33FF33", "#3333FF",
    "#FF8C00", "#00CED1", "#9400D3", "#FF1493", "#7FFF00", "#1E90FF"
]
agent_color_index = 0 # Simple global index for cycling colors

# Global variables for cleanup
server_running = True

# --- OpenAI Integration ---
import openai
# Get API key from environment variables
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logger.error("OPENAI_API_KEY not found in environment variables. Please set it in your .env file.")
    print("ERROR: OPENAI_API_KEY not found in environment variables. Please set it in your .env file.")
    sys.exit(1)
EMBEDDING_MODEL = "text-embedding-3-large" # Updated model
CHAT_MODEL = "gpt-4.1-2025-04-14"
EMBEDDING_DIMENSION = 1024 # Dimension for text-embedding-3-large - REDUCED
MAX_EMBEDDING_BATCH_SIZE = 100 # OpenAI batch limit can vary, check latest docs
MAX_CONTEXT_TOKENS = 3000 # Max tokens to feed GPT-3.5 for context (approximate)

# Lazily initialize OpenAI client
openai_client = None

def get_openai_client():
    global openai_client
    if openai_client is None:
        try:
            openai_client = openai.OpenAI(api_key=OPENAI_API_KEY)
            # Test connection
            openai_client.models.list() 
            logger.info("OpenAI client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}", exc_info=True)
            openai_client = None # Ensure it stays None if init fails
            # Consider raising the error or handling depending on desired server behavior
    return openai_client

# --- End OpenAI Integration ---

# --- Database Setup ---

# Flag to check if vec extension is loadable *at all*
global_vss_load_tested = False
global_vss_load_successful = False

def check_vss_loadability():
    """Tries loading sqlite-vec on a temporary connection to see if it works."""
    global global_vss_load_tested, global_vss_load_successful
    if global_vss_load_tested:
        return global_vss_load_successful
    
    logger.info("Performing initial check for sqlite-vec loadability...")
    temp_conn = None
    try:
        # Need a distinct temporary in-memory DB or file DB for this check
        # Using the main DB path risks conflict if server is already running
        temp_conn = sqlite3.connect(":memory:") # Use in-memory for check
        temp_conn.enable_load_extension(True)
        sqlite_vec.load(temp_conn)
        temp_conn.enable_load_extension(False)
        logger.info("sqlite-vec extension appears loadable.")
        global_vss_load_successful = True
    except AttributeError:
         logger.error("sqlite3 version doesn't support enable_load_extension. sqlite-vec cannot be loaded.")
         global_vss_load_successful = False
    except Exception as e:
        logger.error(f"Initial check: Failed to load sqlite-vec extension: {e}", exc_info=True)
        logger.error("RAG functionality will be disabled. Ensure 'sqlite-vec' is installed correctly.")
        global_vss_load_successful = False
    finally:
        if temp_conn:
            temp_conn.close()
            
    global_vss_load_tested = True
    return global_vss_load_successful

def get_db_connection():
    """Establish and return a connection to the SQLite database, loading sqlite-vec."""
    project_dir = Path(os.environ.get("MCP_PROJECT_DIR", "."))
    agent_dir = project_dir / ".agent"
    db_path = agent_dir / DB_FILE_NAME
    conn = None
    try:
        conn = sqlite3.connect(str(db_path), check_same_thread=False) # Allow multithread/async access
        conn.row_factory = sqlite3.Row 
        # Enable and load extension for this connection
        conn.enable_load_extension(True)
        try:
            sqlite_vec.load(conn)
            # logger.debug("sqlite-vec loaded for connection.") # Use debug level
        except Exception as e:
            logger.error(f"Failed to load sqlite-vec for new connection: {e}")
            # Don't crash here, but RAG operations on this conn will fail
        finally:
             # Always disable extension loading after attempting
             try:
                 conn.enable_load_extension(False)
             except: pass
    except AttributeError as e:
        logger.error(f"This sqlite3 version doesn't support enable_load_extension: {e}. sqlite-vec cannot be loaded.")
        if conn: conn.close() # Close if connection happened but enable failed
        raise RuntimeError("SQLite extension loading not supported") from e
    except sqlite3.Error as e:
         logger.error(f"Error connecting to or setting up DB connection: {e}")
         if conn: conn.close()
         raise # Re-raise DB connection errors
    except Exception as e:
        logger.error(f"Unexpected error getting DB connection: {e}")
        if conn: conn.close()
        raise # Re-raise unexpected errors
        
    return conn

# Helper function to log agent actions to the new table
def _log_agent_action(cursor, agent_id, action_type, task_id=None, details=None):
    """Internal helper to insert into agent_actions table."""
    timestamp = datetime.datetime.now().isoformat()
    details_json = json.dumps(details) if details else None
    try:
        cursor.execute("""
            INSERT INTO agent_actions (agent_id, action_type, task_id, timestamp, details)
            VALUES (?, ?, ?, ?, ?)
        """, (agent_id, action_type, task_id, timestamp, details_json))
        # logger.debug(f"Logged action: {agent_id} - {action_type}") # Optional debug log
    except sqlite3.Error as e:
        # Log error but don't crash the primary operation
        logger.error(f"Failed to log agent action '{action_type}' for agent {agent_id}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error logging agent action: {e}")

def init_database():
    """Initialize the SQLite database and create tables if they don't exist."""
    # Check if VSS is loadable *once* using the global check
    vss_loadable = check_vss_loadability()
    
    # Get a connection (which will also try to load VSS for *this* connection)
    conn = get_db_connection()
    cursor = conn.cursor()

    # Agents Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agents (
            token TEXT PRIMARY KEY,
            agent_id TEXT UNIQUE NOT NULL,
            capabilities TEXT, -- JSON List
            created_at TEXT NOT NULL,
            status TEXT NOT NULL,
            current_task TEXT,
            working_directory TEXT NOT NULL,
            color TEXT, -- Added for visualization
            terminated_at TEXT,
            updated_at TEXT 
        )
    ''')

    # Tasks Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            task_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            assigned_to TEXT, -- Agent ID or None
            created_by TEXT NOT NULL, -- Agent ID or 'admin'
            status TEXT NOT NULL,
            priority TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            parent_task TEXT, -- Task ID or None
            child_tasks TEXT, -- JSON List of Task IDs
            depends_on_tasks TEXT, -- JSON List of Task IDs (NEW)
            notes TEXT -- JSON List of note objects
        )
    ''')
    
    # Agent Actions Table (NEW)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_actions (
            action_id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL, -- Can be agent_id or 'admin'
            action_type TEXT NOT NULL, -- e.g., 'assigned', 'started_work', 'completed', 'updated_context', 'locked_file'
            task_id TEXT, -- Optional: Link action to a specific task
            timestamp TEXT NOT NULL,
            details TEXT -- Optional JSON blob for extra info (e.g., context_key, filepath, tool args)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_actions_agent_time ON agent_actions (agent_id, timestamp DESC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_agent_actions_task_time ON agent_actions (task_id, timestamp DESC)")

    # Project Context Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS project_context (
            context_key TEXT PRIMARY KEY,
            value TEXT NOT NULL, -- Stored as JSON string
            last_updated TEXT NOT NULL,
            updated_by TEXT NOT NULL,
            description TEXT
        )
    ''')

    # File Metadata Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS file_metadata (
            filepath TEXT PRIMARY KEY,
            metadata TEXT NOT NULL, -- JSON object containing various metadata keys/values
            last_updated TEXT NOT NULL,
            updated_by TEXT NOT NULL,
            content_hash TEXT -- Added to detect content changes
        )
    ''')
    
    # RAG Chunks Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rag_chunks (
            chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_type TEXT NOT NULL, -- 'markdown', 'context', 'filemeta'
            source_ref TEXT NOT NULL, -- filepath or context_key
            chunk_text TEXT NOT NULL,
            indexed_at TEXT NOT NULL
        )
    ''')
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_rag_chunks_source ON rag_chunks (source_type, source_ref)")
    
    # RAG Meta Table (for tracking indexing progress)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rag_meta (
            meta_key TEXT PRIMARY KEY, 
            meta_value TEXT
        )
    """)
    # Initialize default timestamps if not present
    cursor.execute("INSERT OR IGNORE INTO rag_meta (meta_key, meta_value) VALUES (?, ?)", ('last_indexed_markdown', '1970-01-01T00:00:00Z'))
    cursor.execute("INSERT OR IGNORE INTO rag_meta (meta_key, meta_value) VALUES (?, ?)", ('last_indexed_context', '1970-01-01T00:00:00Z'))
    cursor.execute("INSERT OR IGNORE INTO rag_meta (meta_key, meta_value) VALUES (?, ?)", ('last_indexed_filemeta', '1970-01-01T00:00:00Z'))

    # RAG Embeddings Table (Only if extension is generally loadable)
    if vss_loadable:
        try:
            # Try explicit column name and dimension definition
            cursor.execute(f'''
                CREATE VIRTUAL TABLE IF NOT EXISTS rag_embeddings USING vec0(
                    embedding float[{EMBEDDING_DIMENSION}]
                )
            ''')
            logger.info("Vector table 'rag_embeddings' (using vec0) ensured.")
        except sqlite3.OperationalError as e:
             # If creation fails *even though* it seemed loadable, it's a critical error
             logger.error(f"Failed to create vector table 'rag_embeddings': {e}. RAG search might fail.")
             conn.close()
             raise RuntimeError(f"Failed to create required vector table 'rag_embeddings': {e}") from e
        except Exception as e:
            logger.error(f"Unexpected error creating vector table: {e}")
            conn.close()
            raise RuntimeError(f"Unexpected error creating vector table 'rag_embeddings': {e}") from e
    else:
        logger.warning("Skipping creation of RAG virtual table as sqlite-vec extension is not loadable.")

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully.")

# --- End Database Setup ---

# --- Utility Functions ---

def simple_chunker(text, chunk_size=500, overlap=50):
    """Very basic text chunking."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks

def markdown_aware_chunker(text, target_chunk_size=1000, min_chunk_size=200, overlap_lines=2):
    """Chunks Markdown text trying to respect structure (headings, paragraphs)."""
    if not text:
        return []

    chunks = []
    current_chunk = ""
    lines = text.split('\n')
    overlap_buffer = []

    for i, line in enumerate(lines):
        is_heading = line.strip().startswith('#')
        is_new_paragraph = (i > 0 and lines[i-1].strip() == "" and line.strip() != "")

        # Split condition: New heading or new paragraph, and current chunk isn't tiny
        if (is_heading or is_new_paragraph) and len(current_chunk) > min_chunk_size:
            if current_chunk:
                chunks.append(current_chunk.strip())
            # Start new chunk with overlap
            overlap_text = "\n".join(overlap_buffer)
            current_chunk = overlap_text + ("\n" if overlap_text else "") + line
        else:
            # Append line to current chunk
            current_chunk += "\n" + line

        # Handle very large chunks (fallback)
        if len(current_chunk) > target_chunk_size * 1.5: # Allow some flexibility
            # If it got too big, maybe just split it here using simple chunker logic
            # This is a basic fallback, could be improved with sentence splitting
            if current_chunk:
                 # Take the part exceeding the target size as the current chunk
                 split_point = target_chunk_size 
                 chunks.append(current_chunk[:split_point].strip()) 
                 # Keep the remainder as the start of the next chunk + overlap
                 overlap_text = "\n".join(overlap_buffer) 
                 current_chunk = overlap_text + ("\n" if overlap_text else "") + current_chunk[split_point:]
            else:
                # Should not happen if line was added, but safety first
                 current_chunk = line # Reset

        # Update overlap buffer
        overlap_buffer.append(line)
        if len(overlap_buffer) > overlap_lines:
            overlap_buffer.pop(0)

    # Add the last remaining chunk
    if current_chunk and current_chunk.strip():
        chunks.append(current_chunk.strip())

    # Final check for empty chunks
    return [chunk for chunk in chunks if chunk]

# --- End Utility Functions ---


# --- Background Tasks ---

rag_index_task = None

async def run_rag_indexing_periodically(interval_seconds=600): # Default to 10 minutes
    """Periodically scans sources and updates the RAG index in the database."""
    logger.info("Starting background RAG indexer...")
    # Initial sleep to allow server startup
    await anyio.sleep(10)
    
    client = get_openai_client() # Initialize client early
    if not client:
        logger.error("OpenAI client failed to initialize. RAG indexer stopping.")
        return

    while server_running:
        try:
            logger.info("Running RAG index update cycle...")
            start_time = time.time()
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Check if vec table exists as proxy for loaded extension
            try:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rag_embeddings'")
                vec_table_exists = cursor.fetchone() is not None
            except sqlite3.Error as e:
                 vec_table_exists = False 
                 logger.warning(f"Database error checking for rag_embeddings table: {e}. Assuming not available.")
                 
            if not vec_table_exists:
                 logger.warning("Vector table 'rag_embeddings' (using vec0) not found. Skipping RAG indexing cycle.")
                 conn.close()
                 await anyio.sleep(interval_seconds * 2) # Sleep longer if VSS fails
                 continue

            # Get last indexed timestamps
            cursor.execute("SELECT meta_key, meta_value FROM rag_meta")
            last_indexed = {row['meta_key']: row['meta_value'] for row in cursor.fetchall()}

            project_dir = Path(os.environ.get("MCP_PROJECT_DIR", "."))
            sources_to_process = [] # List of tuples: (source_type, source_ref, content, last_mod_time)

            # 1. Scan Markdown Files
            last_md_time_str = last_indexed.get('last_indexed_markdown', '1970-01-01T00:00:00Z')
            last_md_time = datetime.datetime.fromisoformat(last_md_time_str.replace('Z', '+00:00')).timestamp()
            max_md_mod_time = last_md_time
            md_sources_to_check = []
            
            # Define patterns to ignore
            IGNORE_DIRS = [
                'node_modules', '__pycache__', 'venv', 'env', '.venv', '.env', 
                'dist', 'build', 'site-packages', '.git', '.idea', '.vscode',
                'bin', 'obj', 'target', '.pytest_cache', '.ipynb_checkpoints'
            ]
            
            try:
                # Get all markdown files, but filter out ignored directories
                all_md_files = []
                for md_file_path in glob.glob(str(project_dir / "**/*.md"), recursive=True):
                    md_path_obj = Path(md_file_path)
                    
                    # Check if file is in an ignored directory
                    should_ignore = False
                    path_parts = md_path_obj.parts
                    for part in path_parts:
                        if (part in IGNORE_DIRS) or (part.startswith('.') and part != '.'):
                            should_ignore = True
                            break
                    
                    if not should_ignore:
                        all_md_files.append(md_path_obj)
                
                logger.info(f"Found {len(all_md_files)} markdown files to consider for indexing (after filtering)")
                
                # Process each non-ignored file
                for md_path_obj in all_md_files:
                    mod_time = md_path_obj.stat().st_mtime
                    # Basic time check first (optimization)
                    if mod_time > last_md_time: 
                        try:
                             content = md_path_obj.read_text(encoding='utf-8')
                             normalized_path = str(md_path_obj.relative_to(project_dir).as_posix())
                             # Calculate hash
                             current_hash = hashlib.sha256(content.encode('utf-8')).hexdigest()
                             md_sources_to_check.append(('markdown', normalized_path, content, mod_time, current_hash))
                             if mod_time > max_md_mod_time: # Track max mod time for timestamp update
                                 max_md_mod_time = mod_time
                        except Exception as e:
                            logger.warning(f"Failed to read or process markdown file {md_path_obj}: {e}")
            except Exception as e:
                 logger.error(f"Error scanning markdown files: {e}")

            # 2. Scan Project Context
            last_ctx_time_str = last_indexed.get('last_indexed_context', '1970-01-01T00:00:00Z')
            max_ctx_mod_time_str = last_ctx_time_str
            ctx_sources_to_check = []
            try:
                 # Check based on timestamp first
                 cursor.execute("SELECT context_key, value, description, last_updated FROM project_context WHERE last_updated > ?", (last_ctx_time_str,))
                 for row in cursor.fetchall():
                     key = row['context_key']
                     value_str = row['value'] # Keep as string for hashing consistency
                     desc = row['description'] or ""
                     last_mod = row['last_updated']
                     # Combine key, value (as string), and description for context hash
                     content_for_hash = f"Context Key: {key}\nDescription: {desc}\nValue: {value_str}"
                     # Calculate hash
                     current_hash = hashlib.sha256(content_for_hash.encode('utf-8')).hexdigest()
                     # Use the combined content for actual embedding too
                     content_for_embedding = content_for_hash 
                     ctx_sources_to_check.append(('context', key, content_for_embedding, last_mod, current_hash))
                     if last_mod > max_ctx_mod_time_str: # Track max mod time for timestamp update
                         max_ctx_mod_time_str = last_mod
            except Exception as e:
                 logger.error(f"Error scanning project context table: {e}")

            # 3. Scan File Metadata (Optional - Skipped for now)

            # Get stored hashes from rag_meta
            cursor.execute("SELECT meta_key, meta_value FROM rag_meta WHERE meta_key LIKE 'hash_%'")
            stored_hashes = {row['meta_key']: row['meta_value'] for row in cursor.fetchall()}

            sources_to_process = [] # List of tuples: (source_type, source_ref, content, current_hash) - mod_time removed

            # Filter sources based on hash comparison
            for source_type, source_ref, content, mod_time_or_iso, current_hash in md_sources_to_check + ctx_sources_to_check:
                 meta_key = f"hash_{source_type}_{source_ref}"
                 stored_hash = stored_hashes.get(meta_key)
                 if current_hash != stored_hash:
                      logger.info(f"Change detected for {source_type}: {source_ref} (Hash mismatch or new)")
                      sources_to_process.append((source_type, source_ref, content, current_hash))
                 # else: logger.debug(f"No change detected for {source_type}: {source_ref} (Hash match)")

            # --- Process Sources Needing Update ---
            if sources_to_process:
                logger.info(f"Processing {len(sources_to_process)} updated/new sources for RAG index.")
                
                processed_hashes_to_update = {} # Track hashes of successfully processed sources

                # It's safer to commit deletions separately first, then process updates
                logger.info("Deleting existing chunks for sources needing update...")
                delete_count = 0
                for source_type, source_ref, _, _ in sources_to_process:
                    # Delete from embeddings first (using rowid from chunks)
                    res_emb = cursor.execute("DELETE FROM rag_embeddings WHERE rowid IN (SELECT chunk_id FROM rag_chunks WHERE source_type = ? AND source_ref = ?)", (source_type, source_ref))
                    # Delete from chunks
                    res_chk = cursor.execute("DELETE FROM rag_chunks WHERE source_type = ? AND source_ref = ?", (source_type, source_ref))
                    if res_chk.rowcount > 0:
                         delete_count += res_chk.rowcount
                if delete_count > 0:
                    logger.info(f"Deleted {delete_count} old chunks.")
                    conn.commit() # Commit deletions before proceeding
                
                # Now, process chunks and embeddings for the sources_to_process list
                all_chunks_to_embed = []
                chunk_source_map = [] # Stores (source_type, source_ref, current_hash) for each chunk

                for source_type, source_ref, content, current_hash in sources_to_process:
                     # Use appropriate chunker based on source_type
                     if source_type == 'markdown':
                         chunks = markdown_aware_chunker(content)
                     else: # For context or other types
                         chunks = simple_chunker(content) # Use simple chunker for non-markdown
                         
                     if not chunks:
                         logger.warning(f"No chunks generated for {source_type}: {source_ref}")
                         continue
                         
                     for i, chunk in enumerate(chunks):
                         all_chunks_to_embed.append(chunk)
                         chunk_source_map.append((source_type, source_ref, current_hash)) # Include hash
                
                if all_chunks_to_embed:
                    logger.info(f"Generated {len(all_chunks_to_embed)} chunks for embedding.")
                    
                    # Higher concurrency for Tier 3 pricing (5000 RPM)
                    MAX_CONCURRENT_REQUESTS = 25  # Increased from 5 to 25
                    
                    # Define a truly async function for embedding that creates its own client
                    async def get_embeddings_batch(batch_chunks, batch_index, results_list):
                        """Process a single batch of embeddings asynchronously with direct HTTPX use."""
                        try:
                            # Create a separate client for each batch for true concurrency
                            # Using async client directly with HTTPX to ensure truly parallel requests
                            async_client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY)
                            response = await async_client.embeddings.create(
                                input=batch_chunks,
                                model=EMBEDDING_MODEL,
                                dimensions=EMBEDDING_DIMENSION
                            )
                            # Store results directly in the provided results list
                            for j, item in enumerate(response.data):
                                pos = batch_index + j
                                if pos < len(results_list):
                                    results_list[pos] = item.embedding
                            logger.info(f"Completed embedding batch starting at index {batch_index}")
                            return True
                        except Exception as e:
                            logger.error(f"OpenAI embedding API error in batch {batch_index}: {e}")
                            return False

                    # Get Embeddings from OpenAI using parallel processing
                    embeddings_successful = True
                    all_embeddings = [None] * len(all_chunks_to_embed)  # Pre-allocate with None
                    
                    # Use smaller batch size for more parallelism
                    PARALLEL_BATCH_SIZE = 50  # Smaller batches for more parallelism
                    
                    start_time = time.time()
                    
                    # Process batches in groups with controlled concurrency
                    for start_idx in range(0, len(all_chunks_to_embed), MAX_CONCURRENT_REQUESTS * PARALLEL_BATCH_SIZE):
                        batch_group_size = min(MAX_CONCURRENT_REQUESTS, 
                                              (len(all_chunks_to_embed) - start_idx + PARALLEL_BATCH_SIZE - 1) // PARALLEL_BATCH_SIZE)
                        
                        logger.info(f"Processing up to {batch_group_size} embedding batches in parallel (group starting at {start_idx})...")
                        
                        # Create and run tasks in a task group
                        try:
                            async with anyio.create_task_group() as tg:
                                for i in range(batch_group_size):
                                    batch_start = start_idx + i * PARALLEL_BATCH_SIZE
                                    if batch_start >= len(all_chunks_to_embed):
                                        break
                                    
                                    batch_end = min(batch_start + PARALLEL_BATCH_SIZE, len(all_chunks_to_embed))
                                    batch_chunks = all_chunks_to_embed[batch_start:batch_end]
                                    
                                    # Start the task to process this batch
                                    tg.start_soon(get_embeddings_batch, batch_chunks, batch_start, all_embeddings)
                        except Exception as e:
                            logger.error(f"Error in parallel batch processing: {e}")
                            embeddings_successful = False
                        
                        # Very minimal delay between batch groups - just enough to avoid overwhelming
                        if start_idx + MAX_CONCURRENT_REQUESTS * PARALLEL_BATCH_SIZE < len(all_chunks_to_embed):
                            await anyio.sleep(0.1)  # Reduced sleep time
                    
                    embedding_time = time.time() - start_time
                    logger.info(f"Completed all embedding batches in {embedding_time:.2f} seconds")
                    
                    # Check for any None values in embeddings that might have been missed
                    none_count = sum(1 for emb in all_embeddings if emb is None)
                    if none_count > 0:
                        logger.warning(f"{none_count} out of {len(all_embeddings)} embeddings failed to generate.")
                        if none_count > len(all_embeddings) // 2:  # If more than half failed
                            embeddings_successful = False
                            logger.error("Too many embedding failures, marking cycle as unsuccessful.")
                        
                    # Insert chunks and embeddings into DB
                    indexed_at = datetime.datetime.now().isoformat()
                    insert_count = 0
                    if embeddings_successful: # Only insert if all embedding calls were okay (or handle partial failure)
                        logger.info("Inserting new chunks and embeddings...")
                        for i, chunk in enumerate(all_chunks_to_embed):
                             embedding = all_embeddings[i]
                             if embedding is None: 
                                 logger.warning(f"Skipping chunk {i} due to missing embedding.")
                                 continue # Should not happen if embeddings_successful is True, but safety check
                             
                             source_type, source_ref, current_hash = chunk_source_map[i]
                             try:
                                 cursor.execute("INSERT INTO rag_chunks (source_type, source_ref, chunk_text, indexed_at) VALUES (?, ?, ?, ?)",
                                               (source_type, source_ref, chunk, indexed_at))
                                 chunk_rowid = cursor.lastrowid
                                 embedding_json = json.dumps(embedding) 
                                 cursor.execute("INSERT INTO rag_embeddings(rowid, embedding) VALUES (?, ?)", (chunk_rowid, embedding_json))
                                 insert_count += 1
                                 
                                 # Mark this source's hash to be updated in rag_meta
                                 meta_key = f"hash_{source_type}_{source_ref}"
                                 processed_hashes_to_update[meta_key] = current_hash

                             except sqlite3.Error as db_err:
                                  logger.error(f"DB Error inserting chunk/embedding for {source_type}:{source_ref} (Chunk index {i}): {db_err}")
                                  # Decide how to handle: stop cycle? rollback? log and continue?
                                  # For now, log and continue, but hash won't be updated.
                                  pass 
                        
                        logger.info(f"Successfully inserted {insert_count} chunks/embeddings.")
                        
                        # Update rag_meta with the new hashes for successfully processed sources
                        if processed_hashes_to_update:
                             logger.info(f"Updating {len(processed_hashes_to_update)} source hashes in rag_meta...")
                             meta_update_tuples = list(processed_hashes_to_update.items())
                             cursor.executemany("INSERT OR REPLACE INTO rag_meta (meta_key, meta_value) VALUES (?, ?)", meta_update_tuples)
                             
                    else:
                        logger.warning("Skipping DB insertion and hash updates for this cycle due to embedding API errors.")

            # Update last indexed *timestamps* regardless of hash checks
            # Only update if no errors occurred that would make timestamp unreliable
            if 'embeddings_successful' not in locals() or embeddings_successful: # Check if flag exists and is True
                new_md_time_iso = datetime.datetime.fromtimestamp(max_md_mod_time).isoformat() + "Z"
                cursor.execute("INSERT OR REPLACE INTO rag_meta (meta_key, meta_value) VALUES (?, ?)", ('last_indexed_markdown', new_md_time_iso))
                cursor.execute("INSERT OR REPLACE INTO rag_meta (meta_key, meta_value) VALUES (?, ?)", ('last_indexed_context', max_ctx_mod_time_str))
                # Update filemeta timestamp if it was scanned
            else:
                logger.warning("Skipping timestamp updates due to errors in the indexing cycle.")

            conn.commit() # Commit inserts/updates
            
            # Add diagnostic query to check if data was actually inserted
            try:
                diag_cursor = conn.cursor()
                diag_cursor.execute("SELECT COUNT(*) FROM rag_chunks")
                chunk_count = diag_cursor.fetchone()[0]
                diag_cursor.execute("SELECT COUNT(*) FROM rag_embeddings")
                embedding_count = diag_cursor.fetchone()[0]
                logger.info(f"DATABASE DIAGNOSTIC: Found {chunk_count} chunks and {embedding_count} embeddings in database")
            except Exception as e:
                logger.error(f"Error running database diagnostics: {e}")
                
            conn.close()
            elapsed = time.time() - start_time
            logger.info(f"RAG index update cycle finished in {elapsed:.2f} seconds.")

        except sqlite3.OperationalError as e:
             if "no such module: vec0" in str(e) or "vector search requires" in str(e):
                  logger.warning(f"Vector search module (vec0) not available or table missing. Skipping RAG cycle. Error: {e}")
             else:
                  logger.error(f"Database operational error in RAG indexing cycle: {e}", exc_info=True)
             if 'conn' in locals() and conn: conn.close()
        except Exception as e:
            logger.error(f"Error in RAG indexing cycle: {e}", exc_info=True)
            if 'conn' in locals() and conn: conn.close() # Ensure connection closed on error
        
        # Use a shorter sleep interval now that hashing skips unchanged files
        await anyio.sleep(max(30, interval_seconds / 5)) # e.g., sleep 60s if interval was 300s, min 30s
    logger.info("Background RAG indexer stopped.")

# --- End Background Tasks ---

def signal_handler(sig, frame):
    """Handle Ctrl+C and other termination signals"""
    global server_running
    
    print("\nShutting down MCP server gracefully...")
    server_running = False
    
    print("Server shutdown complete")
    sys.exit(0)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
signal.signal(signal.SIGTERM, signal_handler)  # Termination signal

def log_audit(agent_id: str, action: str, details: Dict[str, Any]) -> None:
    """Log an audit entry for agent actions"""
    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "agent_id": agent_id,
        "action": action,
        "details": details
    }
    audit_log.append(entry)
    logger.info(f"AUDIT: {agent_id} - {action} - {json.dumps(details)}")
    
    # Write to audit log file
    with open("agent_audit.log", "a") as f:
        f.write(f"{json.dumps(entry)}\n")

# Authentication functions
def generate_token():
    """Generate a secure random token"""
    return secrets.token_hex(16)

def verify_token(token, required_role="agent"):
    """Verify if a token is valid and has the required role"""
    if required_role == "admin" and token == admin_token:
        return True
    if required_role == "agent" and token in active_agents:
        return True
    # Allow admin token to be used for agent roles as well
    if required_role == "agent" and token == admin_token:
        return True # Admins can act as agents
    return False

def get_agent_id(token):
    """Get agent ID from token"""
    if token == admin_token:
        return "admin"
    if token in active_agents:
        return active_agents[token]["agent_id"]
    return None

# Project initialization
def init_agent_directory(project_dir):
    """Initialize the .agent directory structure in the project directory"""
    # Resolve to absolute path
    project_path = Path(project_dir).resolve()
    
    # Validate that the project directory is not the MCP directory itself (Keep as warning)
    mcp_path = Path(__file__).resolve().parent.parent
    if project_path == mcp_path or project_path in mcp_path.parents:
        print(f"WARNING: Initializing .agent in the MCP directory itself ({project_path}) is not recommended!")
        print(f"Please specify a project directory that is NOT the MCP codebase.")
        # Removed confirmation requirement, proceed with warning
    
    agent_dir = project_path / ".agent"
    
    # Create main directory structure (Simplified)
    directories = [
        "",
        # "agents", # Managed by DB
        # "tasks", # Managed by DB
        "logs", # Keep logs directory
        # "fileMap", # Not persisted
        # "fileMap/update_records", # Not persisted
        "locks", # Keep locks? Maybe not needed if file_map is in-memory only. Let's remove.
        "diffs", # Keep diffs? Assume yes for now.
        "notifications", # Keep notifications structure? Assume yes for now.
        "notifications/pending",
        "notifications/acknowledged",
    ]
    
    for directory in directories:
        (agent_dir / directory).mkdir(parents=True, exist_ok=True)
    
    # Create initial config file if it doesn't exist
    config_path = agent_dir / "config.json"
    if not config_path.exists():
        config = {
            "project_name": project_path.name,
            "created_at": datetime.datetime.now().isoformat(),
            "admin_token": admin_token,
            "mcp_version": "0.1.0"
        }
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
    
    # Create initial logs file (keep this mechanism)
    log_file = agent_dir / "logs" / f"{datetime.date.today().isoformat()}.json"
    if not log_file.exists():
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "event": "agent_directory_initialized",
            "details": "Initial setup of .agent directory"
        }
        with open(log_file, "w") as f:
            json.dump([log_entry], f, indent=2)
    
    # Removed task subdir creation
    
    # Removed project context JSON creation
    
    return agent_dir

# Tool implementation functions
async def create_agent_tool(token, agent_id, capabilities=None, working_directory=None):
    """Create a new agent with the given ID and capabilities"""
    global agent_profile_counter
    global active_agents
    global agent_working_dirs
    
    # Admin check remains the same
    if not verify_token(token, "admin"):
        return [types.TextContent(
            type="text",
            text="Unauthorized: Admin token required"
        )]
    
    # Check in-memory map first (most common case)
    if agent_id in agent_working_dirs: # Check agent_working_dirs as proxy for existence
         return [types.TextContent(
            type="text",
            text=f"Agent '{agent_id}' already exists (in memory)."
        )]
    
    # Double check in DB in case state is inconsistent
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT agent_id, color FROM agents") # Fetch existing colors too
    existing_agents = cursor.fetchall()
    existing_agent_ids = {row['agent_id'] for row in existing_agents}
    existing_colors = {row['color'] for row in existing_agents if row['color']}
    
    if agent_id in existing_agent_ids:
        conn.close()
        # Load into memory if found in DB but not memory (optional recovery logic)
        # ... (Could add logic here to load the agent found)
        return [types.TextContent(
            type="text",
            text=f"Agent '{agent_id}' already exists (in database)."
        )]

    # Generate token and prepare data
    agent_token = generate_token()
    created_at = datetime.datetime.now().isoformat()
    capabilities_json = json.dumps(capabilities or [])
    status = "created"
    
    # Assign a color
    global agent_color_index
    agent_color = AGENT_COLORS[agent_color_index % len(AGENT_COLORS)]
    agent_color_index += 1 # Cycle to next color
    # Optional: Could check if color is already in use and skip, but cycling is simpler
    
    # Determine working directory
    project_dir = os.environ.get("MCP_PROJECT_DIR", ".")
    if working_directory:
        agent_working_dir = os.path.abspath(working_directory)
    else:
        agent_working_dir = os.path.abspath(project_dir)
    
    # Insert into Database
    try:
        cursor.execute("""
            INSERT INTO agents (token, agent_id, capabilities, created_at, status, working_directory, color, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            agent_token, agent_id, capabilities_json, created_at, status, 
            agent_working_dir, agent_color, # Added color
            created_at
        ))
        # Log action
        _log_agent_action(cursor, "admin", "created_agent", details={'agent_id': agent_id})
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        conn.close()
        logger.error(f"Database error creating agent {agent_id}: {e}")
        return [types.TextContent(
            type="text",
            text=f"Database error creating agent: {e}"
        )]
    finally:
        conn.close()

    # Update in-memory state
    active_agents[agent_token] = {
        "agent_id": agent_id,
        "capabilities": capabilities or [],
        "created_at": created_at,
        "status": status,
        "current_task": None,
        "color": agent_color # Added color to in-memory state
    }
    agent_working_dirs[agent_id] = agent_working_dir
    
    # Log the agent creation (audit log remains the same)
    log_audit(
        "admin", 
        "create_agent", 
        {
            "agent_id": agent_id, 
            "capabilities": capabilities or [],
            "working_directory": agent_working_dir
        }
    )
    
    # Generate system prompt (remains the same, reads from agent_working_dirs)
    system_prompt = generate_system_prompt(agent_id, agent_token, token if agent_id.lower().startswith("admin") else None)
    
    # Launch Cursor window (remains the same)
    launch_status = ""
    try:
        # ... (Cursor launch code remains unchanged) ...
        profile_num = agent_profile_counter # Get profile number
        agent_profile_counter -= 1 # Update counter
        if agent_profile_counter < 1: agent_profile_counter = 20
        cursor_exe = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Cursor", "Cursor.exe")
        env = os.environ.copy()
        env["CURSOR_AGENT_ID"] = agent_id
        env["CURSOR_MCP_URL"] = f"http://localhost:{os.environ.get('PORT', '8080')}"
        env["CURSOR_WORKING_DIR"] = agent_working_dir
        if agent_id.lower().startswith("admin"): env["CURSOR_ADMIN_TOKEN"] = token
        else: env["CURSOR_AGENT_TOKEN"] = agent_token
        subprocess.Popen([
            "cmd", "/c", "start", f"Cursor Agent - {agent_id}", cursor_exe,
            f"--user-data-dir={profile_num}", "--max-memory=16384"
        ], env=env, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        launch_status = f"✅ Cursor window for agent '{agent_id}' launched with profile {profile_num}"
    except Exception as e:
        launch_status = f"❌ Failed to launch Cursor window: {str(e)}"
    
    # Log to console (remains the same)
    print(f"\n=== Agent '{agent_id}' Created ===")
    print(f"Token: {agent_token}")
    print(f"Assigned Color: {agent_color}")
    print(f"Working Directory: {agent_working_dir}")
    print(launch_status)
    print("\n=== System Prompt ===")
    print(system_prompt)
    
    return [types.TextContent(
        type="text",
        text=f"Agent '{agent_id}' created with token: {agent_token}\n"
             f"Assigned Color: {agent_color}\n"
             f"Working Directory: {agent_working_dir}\n"
             f"{launch_status}\n\n"
             f"=== System Prompt ===\n{system_prompt}"
    )]

def generate_system_prompt(agent_id, agent_token, admin_token=None):
    """Generate a system prompt for an agent"""
    base_prompt = """You are an AI agent running in Cursor, connected to a Multi-Agent Collaboration Protocol (MCP) server.

Your goal is to complete tasks efficiently and collaboratively using a shared, persistent knowledge base.

**Core Responsibilities & Tools:**
*   **File Safety:** Before modifying any file, use `check_file_status` to see if another agent is using it. Use `update_file_status` to claim files ('editing', 'reading', 'reviewing') before you start and 'released' when done.
*   **Task Management:** Use `view_tasks` to see your assigned tasks (filter by agent ID or status). Update progress with `update_task_status`. If a task is complex, use `request_assistance` or `create_self_task`.
*   **Project Context (Key-Value):** 
    *   Use `view_project_context` with `context_key` for specific values (e.g., API endpoints, configuration) or `search_query` to find relevant keys via keywords.
    *   (Admin) Use `update_project_context` to add/modify precise key-value context.
*   **File Metadata:** 
    *   Use `view_file_metadata` (with `filepath`) to understand a file's purpose, components, etc.
    *   (Admin) Use `update_file_metadata` to add/update structured information about specific files.
*   **RAG Querying:** Use `ask_project_rag` with a natural language `query` to ask broader questions about the project. The system will search across documentation, context, and metadata to synthesize an answer. (Index updates automatically in the background).
*   **Parallelization:** Analyze tasks for opportunities to work in parallel. Break down large tasks into smaller sub-tasks. Clearly define dependencies.
*   **Auditability:** Log all significant actions for tracking and debugging.

Your working directory is: {working_dir}
"""
    
    # Add agent-specific details (remains the same)
    agent_details = f"""Agent ID: {agent_id}
Agent Type: {"Admin" if admin_token else "Worker"}
"""
    
    # Add connection code (remains the same)
    connection_code = f""" ... """ # (Keep existing connection code generation)
    
    # Construct full prompt (remains the same)
    full_prompt = base_prompt.format(working_dir=agent_working_dirs.get(agent_id, os.getcwd())) + agent_details + "\nCopy-paste this to connect:\n```python\nimport requests\nimport json\n" + connection_code + "```" + "\n\nUse the available tools to interact with the MCP server and manage your work."
    return full_prompt

async def view_status_tool(token):
    """View the status of all agents and the MCP server"""
    if not verify_token(token, "admin"):
        return [types.TextContent(
            type="text",
            text="Unauthorized: Admin token required"
        )]
    
    # Log the status check
    log_audit("admin", "view_status", {})
    
    agent_status = {}
    for token, agent_data in active_agents.items():
        agent_id = agent_data["agent_id"]
        agent_status[agent_id] = {
            "status": agent_data.get("status", "unknown"),
            "current_task": agent_data.get("current_task"),
            "capabilities": agent_data.get("capabilities", []),
            "working_directory": agent_working_dirs.get(agent_id, "N/A")
        }
    
    status = {
        "active_connections": len(connections),
        "active_agents": len(active_agents),
        "agents": agent_status,
        "server_uptime": "N/A",  # TODO: Add server start time
        "file_map": file_map  # Include file map in status
    }
    
    return [types.TextContent(
        type="text",
        text=f"MCP Status: {json.dumps(status, indent=2)}"
    )]

async def terminate_agent_tool(token, agent_id):
    """Terminate an agent with the given ID"""
    global active_agents
    global agent_working_dirs # Added

    if not verify_token(token, "admin"):
        return [types.TextContent(
            type="text",
            text="Unauthorized: Admin token required"
        )]
    
    # Find the agent token from the in-memory map
    agent_token_to_terminate = None
    for t, data in active_agents.items():
        if data["agent_id"] == agent_id:
            agent_token_to_terminate = t
            break
    
    if not agent_token_to_terminate:
        # Check DB if not found in memory
        conn_check = get_db_connection()
        cursor_check = conn_check.cursor()
        cursor_check.execute("SELECT token FROM agents WHERE agent_id = ? AND status != ?", (agent_id, "terminated"))
        row = cursor_check.fetchone()
        conn_check.close()
        if row:
             # Agent exists in DB but not memory - proceed to terminate in DB
             agent_token_to_terminate = row["token"]
             logger.warning(f"Agent {agent_id} found in DB but not active memory. Proceeding with DB termination.")
        else:
            return [types.TextContent(
                type="text",
                text=f"Agent '{agent_id}' not found or already terminated."
            )]

    # Update agent status in Database
    terminated_at = datetime.datetime.now().isoformat()
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE agents 
            SET status = ?, terminated_at = ?, updated_at = ?
            WHERE agent_id = ?
        """, ("terminated", terminated_at, terminated_at, agent_id))
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Database error terminating agent {agent_id}: {e}")
        return [types.TextContent(
            type="text",
            text=f"Database error terminating agent: {e}"
        )]
    finally:
        conn.close()

    # Remove from active in-memory state if present
    if agent_token_to_terminate in active_agents:
        del active_agents[agent_token_to_terminate]
    if agent_id in agent_working_dirs:
        del agent_working_dirs[agent_id]
        
    log_audit("admin", "terminate_agent", {"agent_id": agent_id})
    
    return [types.TextContent(
        type="text",
        text=f"Agent '{agent_id}' terminated"
    )]

# Task management functions
async def assign_task_tool(token, agent_id, task_title, task_description, priority="medium", depends_on_tasks: Optional[List[str]] = None, parent_task_id: Optional[str] = None):
    """Admin tool to assign a task to an agent, optionally specifying dependencies and a parent task."""
    global tasks
    global active_agents # Needed to update agent's current_task in memory

    if not verify_token(token, "admin"):
        return [types.TextContent(
            type="text",
            text="Unauthorized: Admin token required"
        )]
    
    # Check if agent exists (in memory or DB)
    agent_exists = False
    assigned_agent_token = None
    if agent_id in agent_working_dirs: # Check memory first
        agent_exists = True
        for t, data in active_agents.items():
             if data["agent_id"] == agent_id:
                 assigned_agent_token = t
                 break
    else:
        # Check DB if not in memory
        conn_check = get_db_connection()
        cursor_check = conn_check.cursor()
        cursor_check.execute("SELECT token FROM agents WHERE agent_id = ? AND status != ?", (agent_id, "terminated"))
        row = cursor_check.fetchone()
        if row:
            agent_exists = True
            assigned_agent_token = row["token"] # Might not be in active_agents map
            logger.warning(f"Assigning task to agent {agent_id} found in DB but not active memory.")
        conn_check.close()

    if not agent_exists:
        return [types.TextContent(
            type="text",
            text=f"Agent '{agent_id}' not found or is terminated."
        )]
    
    # Generate task ID and timestamps
    task_id = f"task_{secrets.token_hex(6)}"
    created_at = datetime.datetime.now().isoformat()
    status = "pending"

    # Create task data dictionary
    task_data = {
        "task_id": task_id,
        "title": task_title,
        "description": task_description,
        "assigned_to": agent_id,
        "created_by": "admin",
        "status": status,
        "priority": priority,
        "created_at": created_at,
        "updated_at": created_at,
        "parent_task": parent_task_id, # Use the provided parent_task_id
        "child_tasks": json.dumps([]), # Store as JSON string
        "depends_on_tasks": json.dumps(depends_on_tasks or []), # Store dependencies
        "notes": json.dumps([]) # Store as JSON string
    }
    
    # Save task to database
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO tasks (task_id, title, description, assigned_to, created_by, status, priority, created_at, updated_at, parent_task, child_tasks, depends_on_tasks, notes)
            VALUES (:task_id, :title, :description, :assigned_to, :created_by, :status, :priority, :created_at, :updated_at, :parent_task, :child_tasks, :depends_on_tasks, :notes)
        """, task_data)
        
        # Update agent's current task in DB if they don't have one
        # Check in-memory first
        should_update_agent = False
        if assigned_agent_token and assigned_agent_token in active_agents:
             if active_agents[assigned_agent_token]["current_task"] is None:
                 should_update_agent = True
        else:
             # Check DB if agent not in memory map
             cursor.execute("SELECT current_task FROM agents WHERE agent_id = ?", (agent_id,))
             agent_row = cursor.fetchone()
             if agent_row and agent_row["current_task"] is None:
                 should_update_agent = True

        if should_update_agent:
            cursor.execute("UPDATE agents SET current_task = ?, updated_at = ? WHERE agent_id = ?", (task_id, created_at, agent_id))
        
        conn.commit()
        
        # Update agent's current task in memory if needed
        if should_update_agent and assigned_agent_token and assigned_agent_token in active_agents:
            active_agents[assigned_agent_token]["current_task"] = task_id
            
        # Add task to in-memory tasks dictionary
        tasks[task_id] = task_data
        tasks[task_id]["child_tasks"] = [] # Convert back from JSON for memory
        tasks[task_id]["depends_on_tasks"] = depends_on_tasks or [] # Convert back
        tasks[task_id]["notes"] = [] # Convert back from JSON for memory
            
        # Log Action
        _log_agent_action(cursor, "admin", "assigned_task", task_id=task_id, details={'agent_id': agent_id, 'title': task_title})
            
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Database error assigning task {task_id} to agent {agent_id}: {e}")
        return [types.TextContent(
            type="text",
            text=f"Database error assigning task: {e}"
        )]
    finally:
        conn.close()
    
    log_audit("admin", "assign_task", {"task_id": task_id, "agent_id": agent_id, "title": task_title})
    
    return [types.TextContent(
        type="text",
        text=f"Task '{task_id}' assigned to agent '{agent_id}'\nTitle: {task_title}"
    )]

async def create_self_task_tool(token, task_title, task_description, priority="medium", depends_on_tasks: Optional[List[str]] = None, parent_task_id: Optional[str] = None):
    """Agent tool to create a task for themselves, optionally specifying dependencies and a parent task. Defaults parent to current task if none provided."""
    global tasks
    global active_agents

    # Get agent ID from token (Admins can also create self tasks acting as 'admin')
    agent_id = get_agent_id(token)
    if not agent_id:
         return [types.TextContent(
            type="text",
            text="Unauthorized: Valid token required"
        )]
    
    # Determine the actual parent task ID
    actual_parent_task_id = parent_task_id # Use provided one if exists
    if actual_parent_task_id is None and token in active_agents:
        # Default to current task if none provided and agent is active
        actual_parent_task_id = active_agents[token].get("current_task")
    # If still None (agent not active or no current task), it remains None (root task for agent)

    # --- Hierarchy Validation ---
    if agent_id != "admin" and actual_parent_task_id is None:
        logger.warning(f"Agent '{agent_id}' attempted to create a root task implicitly.")
        return [types.TextContent(
            type="text",
            text="Error: Non-admin agents cannot create root tasks implicitly. Please use \'view_tasks\' to find an appropriate parent task ID and call \'create_self_task_tool\' again, providing the \'parent_task_id\' argument."
        )]
    # --- End Hierarchy Validation ---

    # Generate task ID and timestamps
    task_id = f"task_{secrets.token_hex(6)}"
    created_at = datetime.datetime.now().isoformat()
    status = "pending"
    
    # Prepare task data
    task_data = {
        "task_id": task_id,
        "title": task_title,
        "description": task_description,
        "assigned_to": agent_id,
        "created_by": agent_id,
        "status": status,
        "priority": priority,
        "created_at": created_at,
        "updated_at": created_at,
        "parent_task": actual_parent_task_id, # Use determined parent task ID
        "child_tasks": json.dumps([]),
        "depends_on_tasks": json.dumps(depends_on_tasks or []),
        "notes": json.dumps([])
    }
    
    # Save task to database
    conn = get_db_connection()
    cursor = conn.cursor()
    should_update_agent = False
    try:
        cursor.execute("""
            INSERT INTO tasks (task_id, title, description, assigned_to, created_by, status, priority, created_at, updated_at, parent_task, child_tasks, depends_on_tasks, notes)
            VALUES (:task_id, :title, :description, :assigned_to, :created_by, :status, :priority, :created_at, :updated_at, :parent_task, :child_tasks, :depends_on_tasks, :notes)
        """, task_data)
        
        # Update agent's current task in DB if they don't have one
        # Check in-memory state first
        if token in active_agents:
            if active_agents[token]["current_task"] is None:
                should_update_agent = True
        elif agent_id == "admin":
            # Admin doesn't have a persistent agent entry to update
             pass 
        else:
             # Check DB if agent not in memory map (shouldn't happen for self-task normally)
             cursor.execute("SELECT current_task FROM agents WHERE agent_id = ?", (agent_id,))
             agent_row = cursor.fetchone()
             if agent_row and agent_row["current_task"] is None:
                 should_update_agent = True

        if should_update_agent:
            cursor.execute("UPDATE agents SET current_task = ?, updated_at = ? WHERE agent_id = ?", (task_id, created_at, agent_id))

        conn.commit()
        
        # Update agent's current task in memory if needed
        if should_update_agent and token in active_agents:
            active_agents[token]["current_task"] = task_id
            
        # Add task to in-memory tasks dictionary
        tasks[task_id] = task_data
        tasks[task_id]["child_tasks"] = [] # Convert back from JSON for memory
        tasks[task_id]["depends_on_tasks"] = depends_on_tasks or []
        tasks[task_id]["notes"] = [] # Convert back from JSON for memory
        
        # Log Action
        _log_agent_action(cursor, agent_id, "created_self_task", task_id=task_id, details={'title': task_title})
        
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Database error creating self task {task_id} for agent {agent_id}: {e}")
        return [types.TextContent(
            type="text",
            text=f"Database error creating self task: {e}"
        )]
    finally:
        conn.close()

    log_audit(agent_id, "create_self_task", {"task_id": task_id, "title": task_title})

    return [types.TextContent(
        type="text",
        text=f"Self-assigned task '{task_id}' created\nTitle: {task_title}"
    )]

async def update_task_status_tool(
    token,
    task_id,
    status,
    notes=None,
    # --- Admin Only Fields ---
    title: Optional[str] = None,
    description: Optional[str] = None,
    priority: Optional[str] = None,
    assigned_to: Optional[str] = None,
    depends_on_tasks: Optional[List[str]] = None
):
    """Update the status and optionally other fields (admin only) of a task."""
    # Verify token
    try:
        if not verify_token(token):
            return [types.TextContent(
                type="text",
                text="Unauthorized: Invalid token"
            )]
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Token verification error: {str(e)}"
        )]
    
    # Get agent_id
    requesting_agent_id = get_agent_id(token)
    if not requesting_agent_id:
        return [types.TextContent(
            type="text",
            text="Unauthorized: Could not determine agent ID"
        )]
    
    # Verify task exists
    if task_id not in tasks:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        task_db = cursor.fetchone()
        conn.close()
        
        if not task_db:
            return [types.TextContent(
                type="text",
                text=f"Task {task_id} not found"
            )]
        
        # Add to in-memory cache
        tasks[task_id] = {
            "task_id": task_id,
            "title": task_db["title"],
            "description": task_db["description"],
            "status": task_db["status"],
            "assigned_to": task_db["assigned_to"],
            "priority": task_db["priority"],
            "created_at": task_db["created_at"],
            "updated_at": task_db["updated_at"],
            "parent_task": task_db["parent_task"],
            "child_tasks": task_db["child_tasks"],
            "depends_on_tasks": task_db["depends_on_tasks"],
            "notes": task_db["notes"]
        }
    
    task_data = tasks[task_id]
    
    # Verify the requesting agent owns the task or is an admin
    if task_data.get("assigned_to") != requesting_agent_id and not verify_token(token, required_role="admin"):
        return [types.TextContent(
            type="text",
            text="Unauthorized: You don't have permission to update this task"
        )]
    
    # Verify the status is valid
    valid_statuses = ["pending", "in_progress", "completed", "cancelled"]
    if status not in valid_statuses:
        return [types.TextContent(
            type="text",
            text=f"Invalid status: {status}. Valid statuses are: {', '.join(valid_statuses)}"
        )]
    
    # Update the task in memory
    task_data["status"] = status
    task_data["updated_at"] = datetime.datetime.now().isoformat()
    
    # Handle notes if provided
    if notes:
        # Safely process notes data
        task_notes = []
        
        # Check if notes field is already a list
        notes_data = task_data.get("notes")
        if isinstance(notes_data, list):
            task_notes = notes_data
        elif isinstance(notes_data, str) and notes_data.strip():
            try:
                task_notes = json.loads(notes_data)
            except json.JSONDecodeError:
                logger.warning(f"Could not decode notes JSON for {task_id}: {notes_data}")
                task_notes = []
        
        # Add the new note
        timestamp = datetime.datetime.now().isoformat()
        task_notes.append({
            "timestamp": timestamp,
            "author": requesting_agent_id,
            "content": notes
        })
        
        # Update the task notes in memory
        task_data["notes"] = task_notes
    
    # Update the task in the database
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Handle notes serialization for DB storage
    db_notes = json.dumps(task_data.get("notes", []))
    
    cursor.execute(
        "UPDATE tasks SET status = ?, updated_at = ?, notes = ? WHERE task_id = ?",
        (status, task_data["updated_at"], db_notes, task_id)
    )
    
    # Update file status if task is completed or cancelled
    if status in ["completed", "cancelled"] and "filepath" in task_data:
        cursor.execute("UPDATE file_status SET status = 'released' WHERE filepath = ?", (task_data["filepath"],))
        task_data["file_status"] = "released"
    
    # Log the action
    agent_id = get_agent_id(token) or "unknown"
    _log_agent_action(
        cursor,
        agent_id,
        "update_task_status",
        task_id=task_id,
        details=json.dumps({"status": status, "notes": notes})
    )

    conn.commit()
    conn.close()

    # Update parent task with task completion info if completed/cancelled
    if status in ["completed", "cancelled"] and task_data.get("parent_task"):
        parent_task_id = task_data["parent_task"]
        if parent_task_id in tasks:
            parent_task = tasks[parent_task_id]
            parent_task_notes = []

            # Safely process parent task notes
            parent_notes_data = parent_task.get("notes")
            if isinstance(parent_notes_data, list):
                parent_task_notes = parent_notes_data
            elif isinstance(parent_notes_data, str) and parent_notes_data.strip():
                try:
                    parent_task_notes = json.loads(parent_notes_data)
                except json.JSONDecodeError:
                    logger.warning(f"Could not decode notes JSON for parent task {parent_task_id}: {parent_notes_data}")
                    parent_task_notes = []

            # Add the new note
            timestamp = datetime.datetime.now().isoformat()
            parent_task_notes.append({
                "timestamp": timestamp,
                "author": "system",
                "content": f"Subtask {task_id} is now {status}"
            })

            # Update the parent task notes
            parent_task["notes"] = parent_task_notes
            parent_task["updated_at"] = datetime.datetime.now().isoformat()

            # Update in DB
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                "UPDATE tasks SET updated_at = ?, notes = ? WHERE task_id = ?",
                (parent_task["updated_at"], json.dumps(parent_task_notes), parent_task_id)
            )

            conn.commit()
            conn.close()

            # Removed parent task file writing logic

    # Return success response
    return [types.TextContent(
        type="text",
        text=f"Task {task_id} status updated to {status}"
    )]

async def view_tasks_tool(token, agent_id=None, status=None):
    """View tasks, optionally filtered by agent ID or status"""
    global tasks

    # Use get_agent_id for consistent token handling (allows admin)
    requesting_agent_id = get_agent_id(token)
    if not requesting_agent_id:
        return [types.TextContent(type="text", text="Unauthorized: Valid token required")]

    # Load tasks from DB if memory is empty (or force reload?)
    # For now, assume state loaded at start is sufficient unless specific issues arise.
    # if not tasks: ... logic to load from DB ...
    
    # Check permissions
    is_admin = verify_token(token, "admin")

    # Determine the target agent ID to filter by
    target_agent_id_filter = agent_id
    if not is_admin and agent_id is None:
        target_agent_id_filter = requesting_agent_id
    elif not is_admin and agent_id != requesting_agent_id:
         return [types.TextContent(
            type="text",
            text=f"Unauthorized: Non-admin agents can only view their own tasks or all tasks assigned to them."
        )]
    
    # Filter tasks from in-memory dictionary (loaded at startup)
    filtered_tasks_dict = {}
    for task_id, task in tasks.items():
        # Filter by agent
        if target_agent_id_filter and task.get("assigned_to") != target_agent_id_filter:
            continue
        
        # Filter by status
        if status and task.get("status") != status:
            continue
            
        filtered_tasks_dict[task_id] = task
    
    # Build response (remains the same, uses filtered_tasks_dict)
    if not filtered_tasks_dict:
        response_text = "No tasks found matching the criteria"
    else:
        response_text = "Tasks:\n\n"
        for task_id, task in filtered_tasks_dict.items():
            response_text += f"ID: {task_id}\n"
            response_text += f"Title: {task.get('title', 'N/A')}\n"
            response_text += f"Description: {task.get('description', 'No description')}\n"
            response_text += f"Status: {task.get('status')}\n"
            response_text += f"Priority: {task.get('priority', 'medium')}\n"
            response_text += f"Assigned to: {task.get('assigned_to')}\n"
            response_text += f"Created by: {task.get('created_by')}\n"
            response_text += f"Created: {task.get('created_at')}\n"
            response_text += f"Updated: {task.get('updated_at')}\n"
            if task.get('parent_task'):
                response_text += f"Parent task: {task['parent_task']}\n"
            
            # Safely handle child_tasks (might be list or JSON string)
            child_tasks_data = task.get('child_tasks')
            child_tasks_list = []
            if isinstance(child_tasks_data, list):
                child_tasks_list = child_tasks_data
            elif isinstance(child_tasks_data, str) and child_tasks_data.strip():
                try:
                    child_tasks_list = json.loads(child_tasks_data)
                except json.JSONDecodeError:
                    logger.warning(f"Could not decode child_tasks JSON for {task_id}: {child_tasks_data}")
                    child_tasks_list = ["Error decoding child tasks"]
            
            if child_tasks_list:
                response_text += f"Child tasks: {', '.join(child_tasks_list)}\n"
            
            # Safely handle notes (might be list or JSON string)
            notes_data = task.get('notes')
            notes_list = []
            if isinstance(notes_data, list):
                notes_list = notes_data
            elif isinstance(notes_data, str) and notes_data.strip():
                try:
                    notes_list = json.loads(notes_data)
                except json.JSONDecodeError:
                    logger.warning(f"Could not decode notes JSON for {task_id}: {notes_data}")
                    notes_list = [{"author": "System", "content": "Error decoding notes"}]
            
            if notes_list:
                response_text += f"Notes:\n"
                for note in notes_list:
                    # Ensure note is a dictionary before accessing keys
                    if isinstance(note, dict):
                        timestamp = note.get("timestamp", "Unknown time")
                        author = note.get("author", "Unknown")
                        content = note.get("content", "No content")
                        response_text += f"  - [{timestamp}] {author}: {content}\n"
                    else:
                         response_text += f"  - [Invalid Note Format: {str(note)}]\n"
            response_text += "\n"
    
    log_audit(requesting_agent_id, "view_tasks", {"filter_agent_id": agent_id, "filter_status": status})
    
    return [types.TextContent(
        type="text",
        text=response_text
    )]

async def request_assistance_tool(token, task_id, description):
    """Request assistance with a task from other agents or admin."""
    # Verify token
    try:
        if not verify_token(token):
            return [types.TextContent(
                type="text",
                text="Unauthorized: Invalid token"
            )]
    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Token verification error: {str(e)}"
        )]
    
    # Get agent_id
    requesting_agent_id = get_agent_id(token)
    if not requesting_agent_id:
        return [types.TextContent(
            type="text",
            text="Unauthorized: Could not determine agent ID"
        )]
    
    # Verify task exists
    if task_id not in tasks:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        task_db = cursor.fetchone()
        conn.close()
        
        if not task_db:
            return [types.TextContent(
                type="text",
                text=f"Task {task_id} not found"
            )]
        
        # Add to in-memory cache
        tasks[task_id] = {
            "task_id": task_id,
            "title": task_db["title"],
            "description": task_db["description"],
            "status": task_db["status"],
            "agent_id": task_db["agent_id"],
            "priority": task_db["priority"],
            "created_at": task_db["created_at"],
            "updated_at": task_db["updated_at"],
            "parent_task": task_db["parent_task"],
            "child_tasks": task_db["child_tasks"],
            "depends_on_tasks": task_db["depends_on_tasks"],
            "notes": task_db["notes"]
        }
    
    parent_task_data = tasks[task_id]
    
    # Verify the requesting agent owns the task or is an admin
    if parent_task_data.get("agent_id") != requesting_agent_id and not verify_token(token, required_role="admin"):
        return [types.TextContent(
            type="text",
            text="Unauthorized: You don't have permission to request assistance for this task"
        )]
    
    # Create a child assistance task
    child_task_id = f"task_{generate_id()}"
    child_task_title = f"Assistance for {task_id}: {parent_task_data.get('title', 'Untitled task')}"
    
    # Create notification for admin
    timestamp = datetime.datetime.now().isoformat()
    notification_id = f"notification_{generate_id()}"
    
    notification_data = {
        "id": notification_id,
        "type": "assistance_request",
        "source_agent_id": requesting_agent_id,
        "task_id": task_id,
        "child_task_id": child_task_id,
        "timestamp": timestamp,
        "description": description,
        "status": "pending"
    }
    
    # Save notification
    project_dir = os.environ.get("MCP_PROJECT_DIR", ".")
    notification_file = Path(project_dir) / ".agent" / "notifications" / "pending" / f"{notification_id}.json"
    
    os.makedirs(os.path.dirname(notification_file), exist_ok=True)
    
    with open(notification_file, "w") as f:
        json.dump(notification_data, f, indent=2)
    
    # Create the assistance task
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Insert the child task
    cursor.execute(
        """
        INSERT INTO tasks (task_id, title, description, status, agent_id, priority, 
                          created_at, updated_at, parent_task, depends_on_tasks)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            child_task_id,
            child_task_title,
            description,
            "pending",
            None,  # Not assigned yet
            "high",
            timestamp,
            timestamp,
            task_id,
            json.dumps([])
        )
    )
    
    # Update the parent task's child_tasks field
    # Safely process child_tasks data
    child_tasks_list = []
    
    # Check if child_tasks field is already a list
    child_tasks_data = parent_task_data.get("child_tasks")
    if isinstance(child_tasks_data, list):
        child_tasks_list = child_tasks_data
    elif isinstance(child_tasks_data, str) and child_tasks_data.strip():
        try:
            child_tasks_list = json.loads(child_tasks_data)
        except json.JSONDecodeError:
            logger.warning(f"Could not decode child_tasks JSON for {task_id}: {child_tasks_data}")
            child_tasks_list = []

    child_tasks_list.append(child_task_id)
    parent_task_data["child_tasks"] = child_tasks_list
    parent_task_data["updated_at"] = timestamp
    
    cursor.execute(
        "UPDATE tasks SET child_tasks = ?, updated_at = ? WHERE task_id = ?",
        (json.dumps(child_tasks_list), timestamp, task_id)
    )
    
    # Update parent task notes
    notes_list = []
    
    # Safely process notes data
    notes_data = parent_task_data.get("notes")
    if isinstance(notes_data, list):
        notes_list = notes_data
    elif isinstance(notes_data, str) and notes_data.strip():
        try:
            notes_list = json.loads(notes_data)
        except json.JSONDecodeError:
            logger.warning(f"Could not decode notes JSON for {task_id}: {notes_data}")
            notes_list = []
    
    notes_list.append({
        "timestamp": timestamp,
        "author": requesting_agent_id,
        "content": f"Requested assistance: {description}"
    })
    
    parent_task_data["notes"] = notes_list
    
    cursor.execute(
        "UPDATE tasks SET notes = ? WHERE task_id = ?",
        (json.dumps(notes_list), task_id)
    )
    
    # Add the child task to memory
    tasks[child_task_id] = {
        "task_id": child_task_id,
        "title": child_task_title,
        "description": description,
        "status": "pending",
        "agent_id": None,
        "priority": "high",
        "created_at": timestamp,
        "updated_at": timestamp,
        "parent_task": task_id,
        "child_tasks": json.dumps([]),
        "depends_on_tasks": json.dumps([]),
        "notes": json.dumps([])
    }
    
    # Log the action
    _log_agent_action(
        cursor, 
        requesting_agent_id, 
        "request_assistance", 
        task_id=task_id, 
        details=json.dumps({"description": description, "child_task_id": child_task_id})
    )
    
    conn.commit()
    conn.close()
    
    # Update task file
    parent_task_file_path = get_task_file_path(task_id, parent_task_data["status"])
    with open(parent_task_file_path, "w") as f:
        json.dump(parent_task_data, f, indent=2)
    
    # Create task file for child task
    child_task_file_path = get_task_file_path(child_task_id, "pending")
    with open(child_task_file_path, "w") as f:
        json.dump(tasks[child_task_id], f, indent=2)
    
    log_audit(requesting_agent_id, "request_assistance", {"task_id": task_id, "child_task_id": child_task_id, "description": description})
    
    return [types.TextContent(
        type="text",
        text=f"Assistance requested for task {task_id}. Child assistance task {child_task_id} created and notifications sent."
    )]

async def check_file_status_tool(token, filepath):
    """Check if a file is currently being used by another agent"""
    agent_id = get_agent_id(token)
    if not agent_id:
        return [types.TextContent(
            type="text",
            text="Unauthorized: Valid token required"
        )]
    
    # Resolve the filepath to absolute path
    if not os.path.isabs(filepath):
        working_dir = agent_working_dirs.get(agent_id, os.getcwd())
        abs_filepath = os.path.abspath(os.path.join(working_dir, filepath))
    else:
        abs_filepath = os.path.abspath(filepath)
    
    # Log the file status check
    log_audit(agent_id, "check_file_status", {"filepath": abs_filepath})
    
    # Check if file is in the file map
    if abs_filepath in file_map:
        file_info = file_map[abs_filepath]
        if file_info["agent_id"] == agent_id:
            return [types.TextContent(
                type="text",
                text=f"File '{filepath}' is currently being used by you ({agent_id}) since {file_info['timestamp']}. Status: {file_info['status']}"
            )]
        else:
            return [types.TextContent(
                type="text",
                text=f"File '{filepath}' is currently being used by agent '{file_info['agent_id']}' since {file_info['timestamp']}. Status: {file_info['status']}"
            )]
    else:
        return [types.TextContent(
            type="text",
            text=f"File '{filepath}' is not currently being used by any agent."
        )]

async def update_file_status_tool(token, filepath, status):
    """Update the status of a file (claim it for editing, release it, etc.)"""
    global file_map

    agent_id = get_agent_id(token)
    if not agent_id:
        return [types.TextContent(
            type="text",
            text="Unauthorized: Valid token required"
        )]
    
    # Resolve the filepath to absolute path
    if not os.path.isabs(filepath):
        working_dir = agent_working_dirs.get(agent_id, os.getcwd())
        abs_filepath = os.path.abspath(os.path.join(working_dir, filepath))
    else:
        abs_filepath = os.path.abspath(filepath)
    
    # Validate status
    valid_statuses = ["editing", "reading", "reviewing", "released"]
    if status not in valid_statuses:
        return [types.TextContent(
            type="text",
            text=f"Invalid status: {status}. Must be one of: {', '.join(valid_statuses)}"
        )]
    
    # Check if file is already in use
    if abs_filepath in file_map and file_map[abs_filepath]["agent_id"] != agent_id and status != "released":
        current_agent = file_map[abs_filepath]["agent_id"]
        return [types.TextContent(
            type="text",
            text=f"File '{filepath}' is already being used by agent '{current_agent}'. Cannot claim it."
        )]
    
    # Update the file map
    if status == "released":
        if abs_filepath in file_map and file_map[abs_filepath]["agent_id"] == agent_id:
            del file_map[abs_filepath]
            log_audit(agent_id, "release_file", {"filepath": abs_filepath})
            return [types.TextContent(
                type="text",
                text=f"File '{filepath}' has been released."
            )]
        else:
            return [types.TextContent(
                type="text",
                text=f"File '{filepath}' was not registered to you or doesn't exist in the file map."
            )]
    else:
        file_map[abs_filepath] = {
            "agent_id": agent_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "status": status
        }
        
        log_audit(agent_id, f"claim_file_{status}", {"filepath": abs_filepath})
        
        return [types.TextContent(
            type="text",
            text=f"File '{filepath}' is now registered to agent '{agent_id}' with status '{status}'."
        )]

async def get_system_prompt_tool(token):
    """Get the system prompt for the current agent"""
    agent_id = get_agent_id(token)
    if not agent_id:
        return [types.TextContent(
            type="text",
            text="Unauthorized: Valid token required"
        )]
    
    # Get appropriate token
    agent_token = None
    is_admin = False
    
    for t, data in active_agents.items():
        if data["agent_id"] == agent_id:
            agent_token = t
            break
    
    is_admin = agent_id.lower().startswith("admin")
    
    # Generate system prompt
    system_prompt = generate_system_prompt(
        agent_id, 
        agent_token, 
        admin_token if is_admin else None
    )
    
    log_audit(agent_id, "get_system_prompt", {})
    
    return [types.TextContent(
        type="text",
        text=f"System Prompt for {agent_id}:\n\n{system_prompt}"
    )]

async def view_audit_log_tool(token, agent_id=None, action=None, limit=50):
    """View the audit log, optionally filtered by agent ID or action"""
    if not verify_token(token, "admin"):
        return [types.TextContent(
            type="text",
            text="Unauthorized: Admin token required"
        )]
    
    # Filter the audit log
    filtered_log = audit_log
    
    if agent_id:
        filtered_log = [entry for entry in filtered_log if entry["agent_id"] == agent_id]
    
    if action:
        filtered_log = [entry for entry in filtered_log if entry["action"] == action]
    
    # Get the most recent entries up to the limit
    limited_log = filtered_log[-limit:] if limit else filtered_log
    
    log_audit("admin", "view_audit_log", {"agent_id": agent_id, "action": action, "limit": limit})
    
    return [types.TextContent(
        type="text",
        text=f"Audit Log ({len(limited_log)} entries):\n\n{json.dumps(limited_log, indent=2)}"
    )]

# --- New Project Context Tools ---

async def view_project_context_tool(token, context_key: Optional[str] = None, search_query: Optional[str] = None):
    """View project context. Provide context_key for specific lookup OR search_query for keyword search."""
    agent_id = get_agent_id(token)
    if not agent_id:
        return [types.TextContent(type="text", text="Unauthorized: Valid token required")]

    log_audit(agent_id, "view_project_context", {"context_key": context_key, "search_query": search_query})
    
    conn = get_db_connection()
    cursor = conn.cursor()
    results = []
    response_text = ""

    try:
        if context_key:
            cursor.execute("SELECT value, description, updated_by, last_updated FROM project_context WHERE context_key = ?", (context_key,))
            row = cursor.fetchone()
            if row:
                value = json.loads(row["value"]) # Parse JSON string value
                results.append({
                    "key": context_key,
                    "value": value,
                    "description": row["description"],
                    "updated_by": row["updated_by"],
                    "last_updated": row["last_updated"]
                })
                response_text = f"Project Context for key '{context_key}':\n\n{json.dumps(results[0], indent=2)}"
            else:
                response_text = f"Project context key '{context_key}' not found."
        elif search_query:
            like_query = f'%{search_query}%'
            cursor.execute("""
                SELECT context_key, value, description, updated_by, last_updated 
                FROM project_context 
                WHERE context_key LIKE ? OR description LIKE ? OR value LIKE ?
                LIMIT 50
            """, (like_query, like_query, like_query))
            rows = cursor.fetchall()
            if rows:
                for row in rows:
                     results.append({
                        "key": row["context_key"],
                        "value": json.loads(row["value"]),
                        "description": row["description"],
                        "updated_by": row["updated_by"],
                        "last_updated": row["last_updated"]
                    })
                response_text = f"Found {len(results)} project context entries matching '{search_query}':\n\n{json.dumps(results, indent=2)}"
            else:
                response_text = f"No project context entries found matching '{search_query}'."
        else:
            # Return all context (potentially large! Consider limiting or warning)
            cursor.execute("SELECT context_key, value, description, updated_by, last_updated FROM project_context LIMIT 200")
            rows = cursor.fetchall()
            if rows:
                 for row in rows:
                     results.append({
                        "key": row["context_key"],
                        "value": json.loads(row["value"]),
                        "description": row["description"],
                        "updated_by": row["updated_by"],
                        "last_updated": row["last_updated"]
                    })
                 response_text = f"Full Project Context ({len(results)} entries - potentially truncated):\n\n{json.dumps(results, indent=2)}"
            else:
                 response_text = "Project context is empty."

    except sqlite3.Error as e:
        logger.error(f"Database error viewing project context: {e}")
        response_text = f"Database error viewing project context: {e}"
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from project_context table: {e}")
        response_text = f"Error decoding stored project context value."
    finally:
        conn.close()

    return [types.TextContent(type="text", text=response_text)]

async def update_project_context_tool(token, context_key: str, context_value: Any, description: Optional[str] = None):
    """Update the project context at a specific key (dot-notation support removed, use full key). Admin only."""
    # Note: Removed dot-notation handling for simplicity with direct DB storage.
    # User must provide the full intended key.
    if not verify_token(token, "admin"):
        return [types.TextContent(type="text", text="Unauthorized: Admin token required")]

    agent_id = get_agent_id(token) # Should be 'admin'
    log_audit(agent_id, "update_project_context", {"context_key": context_key, "value_type": str(type(context_value)), "description": description})

    # --- DB Interaction --- 
    conn = get_db_connection()
    cursor = conn.cursor()
    updated_at = datetime.datetime.now().isoformat()
    try:
        # Ensure value is JSON serializable before storing
        value_json = json.dumps(context_value)
    except TypeError as e:
        logger.error(f"Value provided for project context key '{context_key}' is not JSON serializable: {e}")
        return [types.TextContent(type="text", text=f"Error: Provided value is not JSON serializable.")]

    try:
        # Use INSERT OR REPLACE (UPSERT) to handle both insert and update
        cursor.execute("""
            INSERT OR REPLACE INTO project_context (context_key, value, last_updated, updated_by, description)
            VALUES (?, ?, ?, ?, ?)
        """, (context_key, value_json, updated_at, agent_id, description))
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Database error updating project context for key '{context_key}': {e}")
        return [types.TextContent(type="text", text=f"Database error updating project context: {e}")]
    finally:
        conn.close()

    return [types.TextContent(
        type="text",
        text=f"Project context updated successfully for key '{context_key}'."
    )]

# --- End Project Context Tools ---


# --- File Metadata Tools ---

async def view_file_metadata_tool(token, filepath: str):
    """View stored metadata for a specific file path."""
    agent_id = get_agent_id(token)
    if not agent_id:
        return [types.TextContent(type="text", text="Unauthorized: Valid token required")]

    # Resolve the filepath relative to agent's working dir if not absolute
    if not os.path.isabs(filepath):
        working_dir = agent_working_dirs.get(agent_id, os.getcwd())
        resolved_filepath = os.path.abspath(os.path.join(working_dir, filepath))
    else:
        resolved_filepath = os.path.abspath(filepath)
        
    # Normalize path for consistent storage/lookup
    normalized_filepath = str(Path(resolved_filepath).as_posix()) 

    log_audit(agent_id, "view_file_metadata", {"filepath": normalized_filepath})

    conn = get_db_connection()
    cursor = conn.cursor()
    response_text = ""
    try:
        cursor.execute("SELECT metadata, updated_by, last_updated FROM file_metadata WHERE filepath = ?", (normalized_filepath,))
        row = cursor.fetchone()
        if row:
            metadata = json.loads(row["metadata"]) # Parse JSON string
            response_text = f"Metadata for file '{normalized_filepath}':\n\n{json.dumps(metadata, indent=2)}\n(Last updated by {row['updated_by']} at {row['last_updated']})"
        else:
            response_text = f"No metadata found for file '{normalized_filepath}'."
    except sqlite3.Error as e:
        logger.error(f"Database error viewing file metadata for '{normalized_filepath}': {e}")
        response_text = f"Database error viewing file metadata: {e}"
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from file_metadata table for '{normalized_filepath}': {e}")
        response_text = f"Error decoding stored file metadata."
    finally:
        conn.close()

    return [types.TextContent(type="text", text=response_text)]

async def update_file_metadata_tool(token, filepath: str, metadata: Dict[str, Any]):
    """Add or replace the entire metadata object for a specific file path. Admin only for now."""
    # Could be refined to allow updating specific keys within the metadata JSON.
    if not verify_token(token, "admin"): # Restrict to admin initially
        return [types.TextContent(type="text", text="Unauthorized: Admin token required")]

    agent_id = get_agent_id(token)

    # Resolve and normalize path
    if not os.path.isabs(filepath):
        working_dir = agent_working_dirs.get(agent_id, os.getcwd())
        resolved_filepath = os.path.abspath(os.path.join(working_dir, filepath))
    else:
        resolved_filepath = os.path.abspath(filepath)
    normalized_filepath = str(Path(resolved_filepath).as_posix())

    log_audit(agent_id, "update_file_metadata", {"filepath": normalized_filepath, "metadata_keys": list(metadata.keys())})

    conn = get_db_connection()
    cursor = conn.cursor()
    updated_at = datetime.datetime.now().isoformat()
    try:
        metadata_json = json.dumps(metadata) # Store entire object as JSON
    except TypeError as e:
        logger.error(f"Metadata provided for file '{normalized_filepath}' is not JSON serializable: {e}")
        return [types.TextContent(type="text", text=f"Error: Provided metadata is not JSON serializable.")]

    try:
        cursor.execute("""
            INSERT OR REPLACE INTO file_metadata (filepath, metadata, last_updated, updated_by)
            VALUES (?, ?, ?, ?)
        """, (normalized_filepath, metadata_json, updated_at, agent_id))
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        logger.error(f"Database error updating file metadata for '{normalized_filepath}': {e}")
        return [types.TextContent(type="text", text=f"Database error updating file metadata: {e}")]
    finally:
        conn.close()

    return [types.TextContent(
        type="text",
        text=f"File metadata updated successfully for '{normalized_filepath}'."
    )]

# --- End File Metadata Tools ---


# --- RAG Tools (Implementation) ---

async def ask_project_rag_tool(token, query: str):
    """Ask a natural language question about the project using RAG."""
    agent_id = get_agent_id(token)
    if not agent_id:
        return [types.TextContent(type="text", text="Unauthorized: Valid token required")]

    log_audit(agent_id, "ask_project_rag", {"query": query})
    
    client = get_openai_client()
    if not client:
         return [types.TextContent(type="text", text="RAG Error: OpenAI client not available.")]

    conn = get_db_connection()
    cursor = conn.cursor()
    combined_context = ""
    live_context_results = []
    live_task_results = []
    vector_search_results = []
    
    try:
        # --- 1. Fetch Live Context (Recently Updated) ---
        try:
            cursor.execute("SELECT meta_value FROM rag_meta WHERE meta_key = ?", ('last_indexed_context',))
            last_indexed_context_row = cursor.fetchone()
            last_indexed_context_time = last_indexed_context_row[0] if last_indexed_context_row else '1970-01-01T00:00:00Z'
            
            cursor.execute("""
                SELECT context_key, value, description 
                FROM project_context 
                WHERE last_updated > ? 
                ORDER BY last_updated DESC 
                LIMIT 5 
            """, (last_indexed_context_time,))
            live_context_results = cursor.fetchall()
        except Exception as e:
            logger.warning(f"Failed to fetch live project context: {e}")
            
        # --- 2. Fetch Live Tasks (Keyword Search) ---
        try:
            # Basic keyword extraction (split query into words)
            keywords = [f'%{word}%' for word in query.lower().split() if len(word) > 2] # Simple keyword extraction
            if keywords:
                # Build LIKE clauses for title and description
                title_clauses = " OR ".join(["title LIKE ?"] * len(keywords))
                desc_clauses = " OR ".join(["description LIKE ?"] * len(keywords))
                sql_params = keywords + keywords # Duplicate keywords for both title and desc
                
                task_query_sql = f"""
                    SELECT task_id, title, status, description 
                    FROM tasks 
                    WHERE ({title_clauses}) OR ({desc_clauses})
                    ORDER BY updated_at DESC
                    LIMIT 5 
                """
                cursor.execute(task_query_sql, sql_params)
                live_task_results = cursor.fetchall()
        except Exception as e:
            logger.warning(f"Failed to fetch live tasks based on query keywords: {e}")

        # --- 3. Perform Vector Search (Indexed Knowledge) ---
        try:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='rag_embeddings'")
            vec_table_exists = cursor.fetchone() is not None
        except sqlite3.Error as e:
            vec_table_exists = False 
            logger.warning(f"Database error checking for rag_embeddings table: {e}. Assuming not available.")

        if vec_table_exists:
            try:
                # Embed the query
                response = client.embeddings.create(
                    input=[query], 
                    model=EMBEDDING_MODEL,
                    dimensions=EMBEDDING_DIMENSION # Added dimensions parameter
                )
                query_embedding = response.data[0].embedding
                query_embedding_json = json.dumps(query_embedding)

                # Search Vector Table
                k = 5 # Number of results to retrieve
                cursor.execute("""
                    SELECT c.chunk_text, c.source_type, c.source_ref, r.distance
                    FROM rag_embeddings r
                    JOIN rag_chunks c ON r.rowid = c.chunk_id
                    WHERE r.embedding MATCH ?1 AND k = ?2 -- Specify k directly for the MATCH
                    ORDER BY r.distance
                """, (query_embedding_json, k))
                vector_search_results = cursor.fetchall()
            except sqlite3.Error as e:
                # Handle specific VSS errors gracefully if needed
                 logger.error(f"Error during vector search: {e}")
            except Exception as e:
                logger.error(f"Unexpected error during vector search part: {e}")
        else:
            logger.warning("ask_project_rag called but vector table 'rag_embeddings' is not available. Skipping vector search.")
            
        conn.close() # Close connection after all DB queries

        # --- 4. Combine Contexts for LLM --- 
        context_parts = []
        token_count = 0
        max_total_context_tokens = MAX_CONTEXT_TOKENS # Use the global max

        # Add Live Context
        if live_context_results:
            context_parts.append("--- Recently Updated Context (Live) ---")
            for row in live_context_results:
                entry_text = f"Key: {row['context_key']}\nValue: {row['value']}\nDescription: {row['description'] or 'N/A'}\n"
                entry_tokens = len(entry_text.split()) # Approx tokens
                if token_count + entry_tokens < max_total_context_tokens:
                    context_parts.append(entry_text)
                    token_count += entry_tokens
                else: break
            context_parts.append("---------------------------------------")

        # Add Live Tasks
        if live_task_results:
            context_parts.append("--- Relevant Tasks (Live) ---")
            for row in live_task_results:
                entry_text = f"Task ID: {row['task_id']}\nTitle: {row['title']}\nStatus: {row['status']}\nDescription: {row['description'] or 'N/A'}\n"
                entry_tokens = len(entry_text.split()) # Approx tokens
                if token_count + entry_tokens < max_total_context_tokens:
                    context_parts.append(entry_text)
                    token_count += entry_tokens
                else: break
            context_parts.append("-----------------------------")

        # Add Indexed Knowledge (Vector Search Results)
        if vector_search_results:
            context_parts.append("--- Indexed Knowledge Base (Vector Search) ---")
            for i, row in enumerate(vector_search_results):
                chunk_text = row['chunk_text']
                source_info = f"Source: {row['source_type']} - {row['source_ref']}"
                distance = row['distance']
                chunk_tokens = len(chunk_text.split()) # Approx tokens
                
                if token_count + chunk_tokens < max_total_context_tokens:
                    context_parts.append(f"Chunk {i+1} ({source_info}, distance: {distance:.4f})\n{chunk_text}\n")
                    token_count += chunk_tokens
                else:
                    context_parts.append("--- [Indexed knowledge truncated due to token limit] ---")
                    break
            context_parts.append("-------------------------------------------")

        # Check if any context was found
        if not context_parts:
             return [types.TextContent(type="text", text="No relevant information found in the project knowledge base or live data for your query.")]

        combined_context = "\n".join(context_parts)

        # --- 5. Call Chat Completion API --- 
        system_prompt = """You are an AI assistant answering questions about a software project. 
Use the provided context, which may include recently updated live data (context keys, tasks) and information retrieved from an indexed knowledge base (like documentation), to answer the user's query. 
Prioritize information from the 'Live' sections if available and relevant. 
Answer using *only* the information given in the context. If the context doesn't contain the answer, say so explicitly."""
        user_message = f"Context:\n{combined_context}\n\nQuery: {query}"
        
        chat_response = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]
        )
        answer = chat_response.choices[0].message.content

    except openai.APIError as e:
        logger.error(f"OpenAI API error during RAG query: {e}", exc_info=True)
        answer = f"Error communicating with OpenAI: {e}"
        if conn and conn.is_connected: conn.close() # Check if connection exists and is usable
    except sqlite3.Error as e:
        logger.error(f"Database error during RAG query: {e}", exc_info=True)
        answer = f"Error querying RAG database: {e}"
        if conn and conn.is_connected: conn.close()
    except Exception as e:
        logger.error(f"Unexpected error during RAG query: {e}", exc_info=True)
        answer = f"An unexpected error occurred during the RAG query."
        if conn and conn.is_connected: conn.close()

    return [types.TextContent(type="text", text=answer)]

# --- End RAG Tools ---


# --- Original Tools ... ---
# ... (check_file_status, update_file_status, get_system_prompt, view_audit_log) ...

# --- Dashboard API Functions ---

# Wrapper for the graph data endpoint to pass necessary globals
async def graph_data_endpoint(request):
    # Pass the function to get a DB connection and the live file_map
    # Note: Assuming get_db_connection and file_map are accessible globals in main.py context
    return await get_graph_data_impl(get_db_connection, file_map)

# Wrapper for the task tree data endpoint
async def task_tree_data_endpoint(request):
    return await get_task_tree_data_impl(get_db_connection)

# Endpoint to fetch details for a specific node
async def get_node_details(request):
    node_id = request.query_params.get('node_id')
    if not node_id:
        return JSONResponse({'error': 'Missing node_id parameter'}, status_code=400)

    details = {'id': node_id, 'type': 'unknown', 'data': {}}
    conn = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        parts = node_id.split('_', 1)
        node_type = parts[0]
        actual_id = parts[1] if len(parts) > 1 else node_id # Handle admin_node

        details['type'] = node_type

        if node_type == 'agent':
            cursor.execute("SELECT * FROM agents WHERE agent_id = ?", (actual_id,))
            row = cursor.fetchone()
            if row: details['data'] = dict(row)
            # Fetch recent actions for this agent
            cursor.execute("SELECT timestamp, action_type, task_id, details FROM agent_actions WHERE agent_id = ? ORDER BY timestamp DESC LIMIT 10", (actual_id,))
            details['actions'] = [dict(r) for r in cursor.fetchall()]
            # Fetch assigned tasks for this agent
            cursor.execute("SELECT task_id, title, status, priority FROM tasks WHERE assigned_to = ? ORDER BY created_at DESC", (actual_id,))
            details['assigned_tasks'] = [dict(r) for r in cursor.fetchall()]

        elif node_type == 'task':
            cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (actual_id,))
            row = cursor.fetchone()
            if row: details['data'] = dict(row)
            # Fetch recent actions for this task
            cursor.execute("SELECT timestamp, agent_id, action_type, details FROM agent_actions WHERE task_id = ? ORDER BY timestamp DESC LIMIT 10", (actual_id,))
            details['actions'] = [dict(r) for r in cursor.fetchall()]

        elif node_type == 'context':
            cursor.execute("SELECT * FROM project_context WHERE context_key = ?", (actual_id,))
            row = cursor.fetchone()
            if row: details['data'] = dict(row)
            # Fetch recent actions related to this context (if logged)
            cursor.execute("SELECT timestamp, agent_id, action_type FROM agent_actions WHERE action_type = 'updated_context' AND details LIKE ? ORDER BY timestamp DESC LIMIT 5", (f'%{actual_id}%',))
            details['actions'] = [dict(r) for r in cursor.fetchall()]

        elif node_type == 'file':
            # File nodes represent live state, details are in the title
            # Fetch recent actions related to this file
            details['data'] = {'filepath': actual_id}
            cursor.execute("SELECT timestamp, agent_id, action_type, details FROM agent_actions WHERE action_type LIKE '%_file' AND details LIKE ? ORDER BY timestamp DESC LIMIT 5", (f'%{actual_id}%',))
            details['actions'] = [dict(r) for r in cursor.fetchall()]

        elif node_type == 'admin':
             details['data'] = {'name': 'Admin User'}
             # Fetch recent admin actions
             cursor.execute("SELECT timestamp, action_type, task_id, details FROM agent_actions WHERE agent_id = 'admin' ORDER BY timestamp DESC LIMIT 10",)
             details['actions'] = [dict(r) for r in cursor.fetchall()]

        conn.close()

    except Exception as e:
        logger.error(f"Error fetching details for node {node_id}: {e}", exc_info=True)
        if conn:
            try: conn.close()
            except: pass
        return JSONResponse({'error': f'Failed to fetch details: {e}'}, status_code=500)

    if not details.get('data'):
        return JSONResponse({'error': 'Node not found or no data available'}, status_code=404)

    return JSONResponse(details)

# Endpoint to fetch list of all agents
async def get_agents_list(request):
    agents_list = []
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Add static Admin entry first
        agents_list.append({
            'agent_id': 'Admin',
            'status': 'system',
            # 'color': get_node_style('admin').get('color', '#607D8B'), # Cannot call helper from other module easily
            'color': '#607D8B', # Hardcoded admin color
            'created_at': 'N/A',
            'current_task': 'N/A'
        })
        
        # Fetch all agents, including terminated, order by creation
        cursor.execute("SELECT agent_id, status, color, created_at, current_task FROM agents ORDER BY created_at DESC")
        for row in cursor.fetchall():
            agents_list.append(dict(row))
        conn.close()
    except Exception as e:
        logger.error(f"Error fetching agents list: {e}", exc_info=True)
        if conn:
            try: conn.close()
            except: pass
        return JSONResponse({'error': f'Failed to fetch agents list: {e}'}, status_code=500)
    
    return JSONResponse(agents_list)

# --- End Dashboard API Functions ---

@click.command()
@click.option("--port", default=8080, help="Port to listen on for SSE")
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse"]),
    default="sse",
    help="Transport type",
)
@click.option(
    "--project-dir",
    type=click.Path(file_okay=False, dir_okay=True, resolve_path=True), # Ensure it's a directory
    default=".", # Default to current directory
    help="Project directory containing the .agent folder. Defaults to current directory.",
)
@click.option(
    "--admin-token-param",
    type=str,
    default=None,
    help="Admin token for authentication (generates random if not provided)",
)
def main(port: int, transport: str, project_dir: str = None, admin_token_param: str = None) -> int:
    global connections
    global active_agents
    global admin_token
    global tasks # Added tasks global reference
    global agent_working_dirs # Added agent_working_dirs global reference
    global server_running
    global rag_index_task # Added global for background task handle
    
    # Set up admin token
    admin_token = admin_token_param if admin_token_param else generate_token()
    print(f"{'Using provided' if admin_token_param else 'Generated'} admin token: {admin_token}")
    
    # Handle project directory (no longer creates temp dir)
    project_path = Path(project_dir).resolve() # project_dir defaults to '.' via click
    
    # Create project directory if it doesn't exist? Or require it? Let's require it for now.
    if not project_path.exists():
         print(f"Error: Project directory '{project_path}' does not exist. Please create it or specify an existing directory.")
         # Optionally, create it:
         # print(f"Project directory '{project_path}' does not exist. Creating it.")
         # project_path.mkdir(parents=True, exist_ok=True)
         return 1
    elif not project_path.is_dir():
         print(f"Error: Project path '{project_path}' is not a directory.")
         return 1

    print(f"Using project directory: {project_path}")
    os.environ["MCP_PROJECT_DIR"] = str(project_path)
    
    # Initialize .agent directory structure (creates structure if needed)
    agent_dir = init_agent_directory(str(project_path))
    if agent_dir is None:
        # init_agent_directory might return None if user aborts MCP dir warning
        return 1
        
    print(f"Initialized .agent directory structure in {agent_dir}")

    # Initialize SQLite Database (creates DB file and tables if they don't exist)
    try:
        init_database()
    except Exception as e:
        logger.error(f"Failed to initialize database at {agent_dir / DB_FILE_NAME}: {e}")
        print(f"Error: Failed to initialize database. Check logs and permissions.")
        return 1

    # --- Handle Admin Token Persistence ---
    admin_token_key = "config_admin_token"
    conn = get_db_connection()
    cursor = conn.cursor()
    effective_admin_token = None
    token_source = ""

    try:
        if admin_token_param:
            effective_admin_token = admin_token_param
            token_source = "command-line parameter"
            # Store/Update the provided token in DB
            cursor.execute("""
                INSERT OR REPLACE INTO project_context (context_key, value, last_updated, updated_by, description)
                VALUES (?, ?, ?, ?, ?)
            """, (admin_token_key, json.dumps(effective_admin_token), datetime.datetime.now().isoformat(), "server_startup", "Persistent MCP Admin Token"))
            conn.commit()
            logger.info(f"Using admin token provided via {token_source}.")
        else:
            # Try to load from DB
            cursor.execute("SELECT value FROM project_context WHERE context_key = ?", (admin_token_key,))
            row = cursor.fetchone()
            if row:
                try:
                    effective_admin_token = json.loads(row["value"]) 
                    token_source = "stored configuration"
                    logger.info(f"Loaded admin token from {token_source}.")
                except json.JSONDecodeError:
                    logger.warning("Failed to decode stored admin token. Generating a new one.")
            
            # If not loaded or decode failed, generate and store
            if not effective_admin_token:
                effective_admin_token = generate_token()
                token_source = "newly generated"
                cursor.execute("""
                    INSERT OR REPLACE INTO project_context (context_key, value, last_updated, updated_by, description)
                    VALUES (?, ?, ?, ?, ?)
                """, (admin_token_key, json.dumps(effective_admin_token), datetime.datetime.now().isoformat(), "server_startup", "Persistent MCP Admin Token"))
                conn.commit()
                logger.info(f"Generated and stored new admin token.")

    except sqlite3.Error as e:
        logger.error(f"Database error handling admin token persistence: {e}. Falling back to temporary token.")
        # Fallback to ensure server starts even if DB fails here
        effective_admin_token = admin_token_param if admin_token_param else generate_token()
        token_source = "temporary fallback"
    finally:
        conn.close()

    admin_token = effective_admin_token # Assign to the global variable
    print(f"Using Admin Token ({token_source}): {admin_token}")
    # --- End Handle Admin Token Persistence ---

    # --- Load existing state from Database ---
    print("Loading existing state from database...")
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Load Agents
        active_agents_count = 0
        cursor.execute("SELECT token, agent_id, capabilities, created_at, status, current_task, working_directory FROM agents WHERE status != ?", ("terminated",))
        for row in cursor.fetchall():
            agent_token = row["token"]
            agent_id = row["agent_id"]
            active_agents[agent_token] = {
                "agent_id": agent_id,
                "capabilities": json.loads(row["capabilities"] or '[]'),
                "created_at": row["created_at"],
                "status": row["status"],
                "current_task": row["current_task"],
                # working_directory loaded separately below
            }
            agent_working_dirs[agent_id] = row["working_directory"]
            active_agents_count += 1
        print(f"Loaded {active_agents_count} active agents.")

        # Load Tasks
        task_count = 0
        cursor.execute("SELECT * FROM tasks")
        for row in cursor.fetchall():
            tasks[row["task_id"]] = dict(row) # Convert Row object to dict
            task_count += 1
        print(f"Loaded {task_count} tasks.")
        
        # Project Context & File Metadata are not typically loaded into memory unless needed by specific tools.
        # RAG index loading would happen here or on demand later.

        conn.close()
    except sqlite3.Error as e:
        logger.error(f"Database error during state loading: {e}")
        print(f"Error: Failed to load state from database. Check logs.")
        # Decide whether to proceed with empty state or exit
        # For now, let's proceed with potentially partial state and log the error
        active_agents = {}
        tasks = {}
        agent_working_dirs = {}
    except Exception as e:
        logger.error(f"Unexpected error during state loading: {e}")
        print(f"Error: Unexpected error loading state. Check logs.")
        # Exit might be safer here
        return 1

    # File map and audit log are transient and start empty
    global file_map, audit_log
    file_map = {}
    audit_log = []
    # Load persistent audit log? No, the file agent_audit.log is the persistent store.
    
    print("State loading complete.")
    # --- End Load existing state ---

    # --- Start Background Tasks ---
    # Use a task group to manage background tasks cleanly? Or just launch directly?
    # For simplicity now, launch directly. Requires anyio context.
    # This needs to be done within the async context where the server runs.
    # We will launch it within the 'arun' function for stdio or before uvicorn.run for sse.
    print("Background RAG indexer will be started with the server.")
    # --- End Start Background Tasks ---

    # Create MCP server
    app = Server("mcp-server")
    
    # Set up templates directory for dashboard
    templates_dir = Path(__file__).parent / "templates"
    if not templates_dir.exists():
        templates_dir.mkdir(parents=True)
        # Create basic index.html template
        with open(templates_dir / "index.html", "w") as f:
            f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>MCP Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
        .header { background-color: #333; color: white; padding: 10px 20px; }
        .container { display: flex; }
        .sidebar { width: 250px; background-color: #f0f0f0; padding: 10px; }
        .main { flex-grow: 1; padding: 10px; }
        .card { border: 1px solid #ddd; border-radius: 4px; padding: 10px; margin-bottom: 10px; }
        .agent-card { margin-bottom: 10px; padding: 10px; border-radius: 4px; }
        .agent-active { background-color: #dff0d8; border: 1px solid #d6e9c6; }
        .agent-terminated { background-color: #f2dede; border: 1px solid #ebccd1; }
        #status-panel { margin-top: 20px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>MCP Dashboard</h1>
    </div>
    <div class="container">
        <div class="sidebar">
            <h3>Server Info</h3>
            <div class="card">
                <p>Connections: <span id="connection-count">0</span></p>
                <p>Active Agents: <span id="agent-count">0</span></p>
                <p>Project: <span id="project-name">Loading...</span></p>
            </div>
            <h3>Actions</h3>
            <div class="card">
                <button id="refresh-btn">Refresh</button>
                <button id="create-agent-btn">Create Agent</button>
            </div>
        </div>
        <div class="main">
            <h2>Agents</h2>
            <div id="agent-list">Loading agents...</div>
            <h2>Status</h2>
            <div id="status-panel" class="card">
                <pre id="status-json">Loading status...</pre>
            </div>
        </div>
    </div>
    <script>
        // Simple dashboard JavaScript
        document.addEventListener('DOMContentLoaded', function() {
            // Refresh data periodically
            fetchData();
            setInterval(fetchData, 5000);
            
            // Set up button handlers
            document.getElementById('refresh-btn').addEventListener('click', fetchData);
            document.getElementById('create-agent-btn').addEventListener('click', createAgent);
        });
        
        function fetchData() {
            // Fetch dashboard data
            fetch('/api/dashboard')
                .then(response => response.json())
                .then(data => {
                    document.getElementById('connection-count').textContent = data.connections;
                    document.getElementById('agent-count').textContent = data.agents.length;
                    document.getElementById('project-name').textContent = data.project_name;
                    document.getElementById('status-json').textContent = JSON.stringify(data, null, 2);
                    
                    // Render agent list
                    const agentList = document.getElementById('agent-list');
                    agentList.innerHTML = '';
                    
                    data.agents.forEach(agent => {
                        const agentCard = document.createElement('div');
                        agentCard.className = `agent-card agent-${agent.status}`;
                        agentCard.innerHTML = `
                            <h3>${agent.agent_id}</h3>
                            <p>Status: ${agent.status}</p>
                            <p>Task: ${agent.current_task || 'None'}</p>
                            <button onclick="terminateAgent('${agent.agent_id}')">Terminate</button>
                        `;
                        agentList.appendChild(agentCard);
                    });
                })
                .catch(error => {
                    console.error('Error fetching dashboard data:', error);
                });
        }
        
        function createAgent() {
            const agentId = prompt('Enter agent ID:');
            if (!agentId) return;
            
            const adminToken = prompt('Enter admin token:');
            if (!adminToken) return;
            
            fetch('/api/create-agent', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    token: adminToken,
                    agent_id: agentId,
                }),
            })
            .then(response => response.json())
            .then(data => {
                alert(data.message);
                fetchData();
            })
            .catch(error => {
                console.error('Error creating agent:', error);
            });
        }
        
        function terminateAgent(agentId) {
            const adminToken = prompt('Enter admin token:');
            if (!adminToken) return;
            
            fetch('/api/terminate-agent', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    token: adminToken,
                    agent_id: agentId,
                }),
            })
            .then(response => response.json())
            .then(data => {
                alert(data.message);
                fetchData();
            })
            .catch(error => {
                console.error('Error terminating agent:', error);
            });
        }
    </script>
</body>
</html>
            """)
    
    templates = Jinja2Templates(directory=str(templates_dir))
    
    # Register tools
    @app.list_tools()
    async def list_tools() -> list[types.Tool]:
        return [
            # Admin tools
            types.Tool(
                name="create_agent",
                description="Create a new agent with the specified ID and capabilities",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "token": {
                            "type": "string",
                            "description": "Admin authentication token"
                        },
                        "agent_id": {
                            "type": "string",
                            "description": "Unique identifier for the agent"
                        },
                        "capabilities": {
                            "type": "array",
                            "description": "List of agent capabilities",
                            "items": {
                                "type": "string"
                            }
                        }
                    },
                    "required": ["token", "agent_id"],
                    "additionalProperties": False
                }
            ),
            types.Tool(
                name="view_status",
                description="View the status of all agents and the MCP server",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "token": {
                            "type": "string",
                            "description": "Admin authentication token"
                        }
                    },
                    "required": ["token"],
                    "additionalProperties": False
                }
            ),
            types.Tool(
                name="terminate_agent",
                description="Terminate an agent with the given ID",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "token": {
                            "type": "string",
                            "description": "Admin authentication token"
                        },
                        "agent_id": {
                            "type": "string",
                            "description": "Unique identifier for the agent to terminate"
                        }
                    },
                    "required": ["token", "agent_id"],
                    "additionalProperties": False
                }
            ),
            # Task management tools
            types.Tool(
                name="assign_task",
                description="Admin tool to assign a task to an agent, optionally specifying dependencies.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "token": {
                            "type": "string",
                            "description": "Admin authentication token"
                        },
                        "agent_id": {
                            "type": "string",
                            "description": "Agent to assign task to"
                        },
                        "task_title": {
                            "type": "string",
                            "description": "Title of the task"
                        },
                        "task_description": {
                            "type": "string",
                            "description": "Detailed description of the task"
                        },
                        "priority": {
                            "type": "string",
                            "description": "Task priority (low, medium, high)",
                            "enum": ["low", "medium", "high"]
                        },
                        "depends_on_tasks": { # Added
                            "type": "array",
                            "description": "List of task IDs this task depends on (optional)",
                            "items": { "type": "string" }
                        }
                    },
                    "required": ["token", "agent_id", "task_title", "task_description"],
                    "additionalProperties": False
                }
            ),
            types.Tool(
                name="create_self_task",
                description="Agent tool to create a task for themselves, optionally specifying dependencies.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "token": {
                            "type": "string",
                            "description": "Agent authentication token"
                        },
                        "task_title": {
                            "type": "string",
                            "description": "Title of the task"
                        },
                        "task_description": {
                            "type": "string",
                            "description": "Detailed description of the task"
                        },
                        "priority": {
                            "type": "string",
                            "description": "Task priority (low, medium, high)",
                            "enum": ["low", "medium", "high"]
                        },
                        "depends_on_tasks": { # Added
                            "type": "array",
                            "description": "List of task IDs this task depends on (optional)",
                            "items": { "type": "string" }
                        }
                    },
                    "required": ["token", "task_title", "task_description"],
                    "additionalProperties": False
                }
            ),
            types.Tool(
                name="update_task_status",
                description="Update the status and optionally other fields (admin only) of a task.", # Updated description
                inputSchema={
                    "type": "object",
                    "properties": {
                        "token": {
                            "type": "string",
                            "description": "Authentication token"
                        },
                        "task_id": {
                            "type": "string",
                            "description": "ID of the task to update"
                        },
                        "status": {
                            "type": "string",
                            "description": "New status for the task",
                            "enum": ["pending", "in_progress", "completed", "cancelled"]
                        },
                        "notes": {
                            "type": "string",
                            "description": "Optional notes about the status update"
                        },
                        # --- Admin Only Optional Fields ---
                        "title": {
                            "type": "string",
                            "description": "(Admin Only) New title for the task"
                        },
                        "description": {
                            "type": "string",
                            "description": "(Admin Only) New description for the task"
                        },
                        "priority": {
                            "type": "string",
                            "description": "(Admin Only) New priority for the task",
                            "enum": ["low", "medium", "high"]
                        },
                        "assigned_to": {
                            "type": "string",
                            "description": "(Admin Only) New agent ID to assign the task to"
                        },
                        "depends_on_tasks": {
                            "type": "array",
                            "description": "(Admin Only) New list of task IDs this task depends on",
                            "items": { "type": "string" }
                        }
                    },
                    "required": ["token", "task_id", "status"],
                    "additionalProperties": False
                }
            ),
            types.Tool(
                name="view_tasks",
                description="View tasks, optionally filtered by agent ID or status",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "token": {
                            "type": "string",
                            "description": "Authentication token"
                        },
                        "agent_id": {
                            "type": "string",
                            "description": "Filter tasks by agent ID (optional)"
                        },
                        "status": {
                            "type": "string",
                            "description": "Filter tasks by status (optional)",
                            "enum": ["pending", "in_progress", "completed", "cancelled"]
                        }
                    },
                    "required": ["token"],
                    "additionalProperties": False
                }
            ),
            types.Tool(
                name="request_assistance",
                description="Request assistance with a task, creating a child task",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "token": {
                            "type": "string",
                            "description": "Agent authentication token"
                        },
                        "task_id": {
                            "type": "string",
                            "description": "ID of the task needing assistance"
                        },
                        "description": {
                            "type": "string",
                            "description": "Description of the assistance needed"
                        }
                    },
                    "required": ["token", "task_id", "description"],
                    "additionalProperties": False
                }
            ),
            types.Tool(
                name="check_file_status",
                description="Check if a file is currently being used by another agent",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "token": {
                            "type": "string",
                            "description": "Agent authentication token"
                        },
                        "filepath": {
                            "type": "string",
                            "description": "Path to the file to check"
                        }
                    },
                    "required": ["token", "filepath"],
                    "additionalProperties": False
                }
            ),
            types.Tool(
                name="update_file_status",
                description="Update the status of a file",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "token": {
                            "type": "string",
                            "description": "Agent authentication token"
                        },
                        "filepath": {
                            "type": "string",
                            "description": "Path to the file to update"
                        },
                        "status": {
                            "type": "string",
                            "description": "New status for the file",
                            "enum": ["editing", "reading", "reviewing", "released"]
                        }
                    },
                    "required": ["token", "filepath", "status"],
                    "additionalProperties": False
                }
            ),
            types.Tool(
                name="get_system_prompt",
                description="Get the system prompt for the current agent",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "token": {
                            "type": "string",
                            "description": "Agent authentication token"
                        }
                    },
                    "required": ["token"],
                    "additionalProperties": False
                }
            ),
            types.Tool(
                name="view_audit_log",
                description="View the audit log",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "token": {
                            "type": "string",
                            "description": "Admin authentication token"
                        },
                        "agent_id": {
                            "type": "string",
                            "description": "Filter audit log by agent ID (optional)"
                        },
                        "action": {
                            "type": "string",
                            "description": "Filter audit log by action (optional)"
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of entries to return (default 50)",
                            "minimum": 1,
                            "maximum": 100
                        }
                    },
                    "required": ["token"],
                    "additionalProperties": False
                }
            ),
            # --- Project Context Tools ---
            types.Tool(
                name="view_project_context",
                description="View project context. Provide context_key for specific lookup OR search_query for keyword search.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "token": {"type": "string", "description": "Authentication token"},
                        "context_key": {"type": "string", "description": "Exact key to view (optional)"},
                        "search_query": {"type": "string", "description": "Keyword search query (optional)"}
                    },
                    "required": ["token"],
                    "additionalProperties": False
                }
            ),
            types.Tool(
                name="update_project_context",
                description="Add or update a project context entry with a specific key. Admin only.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "token": {"type": "string", "description": "Admin authentication token"},
                        "context_key": {"type": "string", "description": "The exact key for the context entry"},
                        "context_value": {"type": "object", "description": "The JSON-serializable value to set"},
                        "description": {"type": "string", "description": "Optional description of the context entry."}
                    },
                    "required": ["token", "context_key", "context_value"],
                    "additionalProperties": False
                }
            ),
            # File Metadata Tools
             types.Tool(
                name="view_file_metadata",
                description="View stored metadata for a specific file path.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "token": {"type": "string", "description": "Authentication token"},
                        "filepath": {"type": "string", "description": "Path to the file"}
                    },
                    "required": ["token", "filepath"],
                    "additionalProperties": False
                }
            ),
            types.Tool(
                name="update_file_metadata",
                description="Add or replace metadata for a specific file path. Admin only.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "token": {"type": "string", "description": "Admin authentication token"},
                        "filepath": {"type": "string", "description": "Path to the file"},
                        "metadata": {"type": "object", "description": "A JSON object containing the metadata"}
                    },
                    "required": ["token", "filepath", "metadata"],
                    "additionalProperties": False
                }
            ),
            # RAG Tool
            types.Tool(
                name="ask_project_rag",
                description="Ask a natural language question about the project (uses RAG).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "token": {"type": "string", "description": "Authentication token"},
                        "query": {"type": "string", "description": "The question to ask about the project"}
                    },
                    "required": ["token", "query"],
                    "additionalProperties": False
                }
            ),
            # Other existing tools (check_file_status, update_file_status, get_system_prompt, view_audit_log, test)
            # ... (Ensure these schemas are correct) ...
        ]

    @app.call_tool()
    async def handle_tool(name: str, arguments: dict) -> list[types.TextContent]:
        # Sanitize arguments input to handle Unicode issues
        try:
            # Accept both a single dict or a list of dicts for arguments
            if isinstance(arguments, list):
                sanitized_args = []
                for arg in arguments:
                    try:
                        sanitized_args.append(sanitize_json_input(arg))
                    except Exception as e:
                        return [types.TextContent(type="text", text=f"Error sanitizing input: {e}")]
                results = []
                for arg in sanitized_args:
                    try:
                        res = await handle_tool(name, arg)
                        results.extend(res)
                    except Exception as e:
                        results.append(types.TextContent(type="text", text=f"Error processing item: {e}"))
                return results
            elif not isinstance(arguments, dict):
                # Try to sanitize and parse if not a dict
                try:
                    arguments = sanitize_json_input(arguments)
                except ValueError as e:
                    return [types.TextContent(type="text", text=f"Invalid input: {str(e)}")]
            
            # Continue with sanitized arguments
            if name == "test":
                return await test_tool()
            elif name == "create_agent":
                return await create_agent_tool(
                    arguments.get("token"),
                    arguments.get("agent_id"),
                    arguments.get("capabilities"),
                    arguments.get("working_directory")
                )
            elif name == "view_status":
                return await view_status_tool(arguments.get("token"))
            elif name == "terminate_agent":
                return await terminate_agent_tool(
                    arguments.get("token"),
                    arguments.get("agent_id")
                )
            elif name == "assign_task":
                return await assign_task_tool(
                    arguments.get("token"),
                    arguments.get("agent_id"),
                    arguments.get("task_title"),
                    arguments.get("task_description"),
                    arguments.get("priority", "medium"),
                    arguments.get("depends_on_tasks"),
                    arguments.get("parent_task_id")
                )
            elif name == "create_self_task":
                return await create_self_task_tool(
                    arguments.get("token"),
                    arguments.get("task_title"),
                    arguments.get("task_description"),
                    arguments.get("priority", "medium"),
                    arguments.get("depends_on_tasks"),
                    arguments.get("parent_task_id")
                )
            elif name == "update_task_status":
                return await update_task_status_tool(
                    arguments.get("token"),
                    arguments.get("task_id"),
                    arguments.get("status"),
                    arguments.get("notes"),
                    # Pass admin-only fields
                    title=arguments.get("title"),
                    description=arguments.get("description"),
                    priority=arguments.get("priority"),
                    assigned_to=arguments.get("assigned_to"),
                    depends_on_tasks=arguments.get("depends_on_tasks")
                )
            elif name == "view_tasks":
                return await view_tasks_tool(
                    arguments.get("token"),
                    arguments.get("agent_id"),
                    arguments.get("status")
                )
            elif name == "request_assistance":
                return await request_assistance_tool(
                    arguments.get("token"),
                    arguments.get("task_id"),
                    arguments.get("description")
                )
            elif name == "check_file_status":
                return await check_file_status_tool(
                    arguments.get("token"),
                    arguments.get("filepath")
                )
            elif name == "update_file_status":
                return await update_file_status_tool(
                    arguments.get("token"),
                    arguments.get("filepath"),
                    arguments.get("status")
                )
            elif name == "get_system_prompt":
                return await get_system_prompt_tool(arguments.get("token"))
            elif name == "view_audit_log":
                return await view_audit_log_tool(
                    arguments.get("token"),
                    arguments.get("agent_id"),
                    arguments.get("action"),
                    arguments.get("limit")
                )
            # --- Handle Project Context Tools ---
            elif name == "view_project_context":
                 return await view_project_context_tool(
                     arguments.get("token"),
                     arguments.get("context_key"),
                     arguments.get("search_query") # Added search query
                 )
            elif name == "update_project_context":
                 return await update_project_context_tool(
                     arguments.get("token"),
                     arguments.get("context_key"),
                     arguments.get("context_value"),
                     arguments.get("description")
                 )
            # --- End Handle Project Context Tools ---
            # --- Handle File Metadata Tools ---
            elif name == "view_file_metadata":
                return await view_file_metadata_tool(
                    arguments.get("token"),
                    arguments.get("filepath")
                )
            elif name == "update_file_metadata":
                return await update_file_metadata_tool(
                    arguments.get("token"),
                    arguments.get("filepath"),
                    arguments.get("metadata")
                )
            # --- End Handle File Metadata Tools ---
             # --- Handle RAG Tool ---
            elif name == "ask_project_rag":
                return await ask_project_rag_tool(
                    arguments.get("token"),
                    arguments.get("query")
                )
            # --- End Handle RAG Tool ---
            else:
                raise ValueError(f"Unknown tool: {name}")
        except Exception as e:
            return [types.TextContent(type="text", text=f"Internal error in tool handler: {e}")]

    async def test_tool() -> list[types.TextContent]:
        """Simple test tool that returns a success message"""
        return [types.TextContent(
            type="text",
            text="Tool is working! 🎉"
        )]

    # Handle different transport types
    if transport == "sse":
        # Set up SSE transport
        sse = SseServerTransport("/messages/")

        async def handle_sse(request):
            try:
                client_id = str(uuid.uuid4())[:8]
                logger.info(f"SSE connection request from {request.client.host} (ID: {client_id})")
                print(f"[{datetime.datetime.now().isoformat()}] SSE connection request from {request.client.host} (ID: {client_id})")
                
                async with sse.connect_sse(
                    request.scope, request.receive, request._send
                ) as streams:
                    logger.info(f"SSE client connected: {client_id}")
                    print(f"[{datetime.datetime.now().isoformat()}] SSE client connected: {client_id}")
                    
                    try:
                        await app.run(
                            streams[0], 
                            streams[1], 
                            app.create_initialization_options()
                        )
                    finally:
                        logger.info(f"SSE client disconnected: {client_id}")
                        print(f"[{datetime.datetime.now().isoformat()}] SSE client disconnected: {client_id}")
            except Exception as e:
                logger.error(f"Error in SSE connection: {str(e)}")
                print(f"[{datetime.datetime.now().isoformat()}] Error in SSE connection: {str(e)}")
                raise

        # Dashboard routes
        async def dashboard_home(request):
            return templates.TemplateResponse("index.html", {"request": request})
        
        # API endpoints for dashboard
        async def dashboard_api(request):
            try:
                # Convert active_agents to list for JSON
                agents_list = [
                    {
                        "agent_id": data["agent_id"],
                        "status": data["status"],
                        "current_task": data["current_task"],
                        "capabilities": data["capabilities"]
                    } for token, data in active_agents.items()
                ]
                
                project_name = Path(os.environ.get("MCP_PROJECT_DIR", ".")).name
                
                return JSONResponse({
                    "connections": 0,  # Simplified - no longer tracking connections
                    "agents": agents_list,
                    "project_name": project_name
                })
            except Exception as e:
                logger.error(f"Error in dashboard API: {str(e)}")
                return JSONResponse({"error": f"Dashboard API error: {str(e)}"}, status_code=500)
        
        async def get_tokens(request):
            """API endpoint to retrieve admin and agent tokens for the dashboard"""
            try:
                # We don't check for token authentication here as this endpoint is only used 
                # on the client side for displaying tokens in the dashboard
                
                # Get agent tokens
                agent_tokens = []
                for token, data in active_agents.items():
                    if data["status"] != "terminated":
                        agent_tokens.append({
                            "agent_id": data["agent_id"],
                            "token": token
                        })
                
                return JSONResponse({
                    "admin_token": admin_token,
                    "agent_tokens": agent_tokens
                })
            except Exception as e:
                logger.error(f"Error retrieving tokens: {str(e)}")
                return JSONResponse({"error": f"Error retrieving tokens: {str(e)}"}, status_code=500)
        
        async def create_agent_api(request):
            global active_agents
            try:
                data = await get_sanitized_json_body(request)
                token = data.get("token")
                agent_id = data.get("agent_id")
                
                if not token or token != admin_token:
                    return JSONResponse({"message": "Unauthorized: Invalid admin token"}, status_code=401)
                
                if not agent_id:
                    return JSONResponse({"message": "Agent ID is required"}, status_code=400)
                
                # Create agent
                agent_token = generate_token()
                active_agents[agent_token] = {
                    "agent_id": agent_id,
                    "capabilities": [],
                    "created_at": datetime.datetime.now().isoformat(),
                    "status": "active",
                    "current_task": None
                }
                
                # Create agent file
                project_dir = os.environ.get("MCP_PROJECT_DIR", ".")
                agent_file = Path(project_dir) / ".agent" / "agents" / f"{agent_id}.json"
                agent_data = active_agents[agent_token].copy()
                agent_data["token"] = agent_token
                
                with open(agent_file, "w") as f:
                    json.dump(agent_data, f, indent=2)
                
                return JSONResponse({
                    "message": f"Agent '{agent_id}' created successfully",
                    "agent_token": agent_token
                })
            except ValueError as e:
                return JSONResponse({"message": str(e)}, status_code=400)
            except Exception as e:
                logger.error(f"Error creating agent: {str(e)}")
                return JSONResponse({"message": f"Error creating agent: {str(e)}"}, status_code=500)
        
        async def terminate_agent_api(request):
            try:
                data = await get_sanitized_json_body(request)
                token = data.get("token")
                agent_id = data.get("agent_id")
                
                if not token or token != admin_token:
                    return JSONResponse({"message": "Unauthorized: Invalid admin token"}, status_code=401)
                
                if not agent_id:
                    return JSONResponse({"message": "Agent ID is required"}, status_code=400)
                
                # Find agent token
                agent_token = None
                for token, data in active_agents.items():
                    if data["agent_id"] == agent_id:
                        agent_token = token
                        break
                
                if not agent_token:
                    return JSONResponse({"message": f"Agent '{agent_id}' not found"}, status_code=404)
                
                # Update agent file
                project_dir = os.environ.get("MCP_PROJECT_DIR", ".")
                agent_file = Path(project_dir) / ".agent" / "agents" / f"{agent_id}.json"
                
                if agent_file.exists():
                    with open(agent_file, "r") as f:
                        agent_data = json.load(f)
                
                    agent_data["status"] = "terminated"
                    agent_data["terminated_at"] = datetime.datetime.now().isoformat()
                    
                    with open(agent_file, "w") as f:
                        json.dump(agent_data, f, indent=2)
                
                # Remove from active agents
                del active_agents[agent_token]
                
                return JSONResponse({
                    "message": f"Agent '{agent_id}' terminated"
                })
            except ValueError as e:
                return JSONResponse({"message": str(e)}, status_code=400)
            except Exception as e:
                logger.error(f"Error terminating agent: {str(e)}")
                return JSONResponse({"message": f"Error terminating agent: {str(e)}"}, status_code=500)

        async def update_task_details_api(request):
            """API endpoint to update task details from the dashboard"""
            if request.method != 'POST':
                return JSONResponse({"error": "Method not allowed"}, status_code=405)
            
            try:
                data = await get_sanitized_json_body(request)
                
                # Validate required fields
                required_fields = ['token', 'task_id', 'status']
                for field in required_fields:
                    if field not in data:
                        return JSONResponse({"error": f"Missing required field: {field}"}, status=400)
                
                # Verify token as admin
                try:
                    if not verify_token(data['token'], required_role='admin'):
                        return JSONResponse({"error": "Invalid admin token"}, status_code=403)
                except Exception as e:
                    return JSONResponse({"error": f"Token verification error: {str(e)}"}, status_code=403)
                
                # Get database connection
                conn = get_db_connection()
                cursor = conn.cursor()
                
                # Check if task exists
                cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (data['task_id'],))
                task = cursor.fetchone()
                if not task:
                    conn.close()
                    return JSONResponse({"error": "Task not found"}, status_code=404)
                
                # Update the task fields
                update_fields = []
                params = []
                
                # Always update status and updated_at
                update_fields.append("status = ?")
                params.append(data['status'])
                
                update_fields.append("updated_at = ?")
                params.append(datetime.datetime.now().isoformat())
                
                # Optional fields
                if 'title' in data and data['title']:
                    update_fields.append("title = ?")
                    params.append(data['title'])
                
                if 'description' in data and data['description']:
                    update_fields.append("description = ?")
                    params.append(data['description'])
                
                if 'priority' in data and data['priority']:
                    update_fields.append("priority = ?")
                    params.append(data['priority'])
                
                # Append notes if provided
                if 'notes' in data and data['notes']:
                    cursor.execute("SELECT notes FROM tasks WHERE task_id = ?", (data['task_id'],))
                    existing_notes = cursor.fetchone()[0] or ""
                    
                    # Format the new note with timestamp
                    timestamp = datetime.datetime.now().isoformat()
                    new_note = f"\n[{timestamp}] {data['notes']}"
                    
                    # Append to existing notes
                    if existing_notes:
                        updated_notes = existing_notes + new_note
                    else:
                        updated_notes = new_note.lstrip()
                    
                    update_fields.append("notes = ?")
                    params.append(updated_notes)
                
                # Finalize query params
                params.append(data['task_id'])
                
                # Execute the update
                query = f"UPDATE tasks SET {', '.join(update_fields)} WHERE task_id = ?"
                cursor.execute(query, params)
                
                # Log the action
                agent_id = get_agent_id(data['token']) or "admin"
                _log_agent_action(
                    cursor, 
                    agent_id, 
                    "update_task", 
                    task_id=data['task_id'], 
                    details=json.dumps({"status": data['status']})
                )
                
                conn.commit()
                conn.close()
                
                return JSONResponse({"success": True, "message": "Task updated successfully"})
            
            except ValueError as e:
                return JSONResponse({"error": str(e)}, status_code=400)    
            except Exception as e:
                logger.error(f"Error updating task: {str(e)}")
                return JSONResponse({"error": f"Failed to update task: {str(e)}"}, status=500)

        # Create a separate Starlette application for the web dashboard
        templates = Jinja2Templates(directory=str(templates_dir))
        web_app = Starlette()
        
        # Register routes on the web app
        web_app.add_route('/', dashboard_home)
        web_app.add_route('/api/dashboard', dashboard_api)
        web_app.add_route('/api/create-agent', create_agent_api)
        web_app.add_route('/api/terminate-agent', terminate_agent_api)
        web_app.add_route('/api/graph-data', graph_data_endpoint)
        web_app.add_route('/api/task-tree-data', task_tree_data_endpoint)
        web_app.add_route('/api/details', get_node_details)
        web_app.add_route('/api/agents', get_agents_list)
        web_app.add_route('/api/tokens', get_tokens)
        web_app.add_route('/api/update-task-details', update_task_details_api)
        
        # Add the SSE endpoints that Cursor requires
        web_app.add_route('/sse', handle_sse)
        web_app.mount('/messages', sse.handle_post_message)
        
        # Configure static files
        static_dir = os.path.join(os.path.dirname(__file__), 'static')
        web_app.mount('/static', StaticFiles(directory=static_dir))

        print(f"MCP Server started with admin token: {admin_token}")
        print(f"Dashboard available at http://localhost:{port}")
        print(f"Project directory: {project_path}") # Updated message
        print("Press Ctrl+C to shut down the server gracefully")

        # Run server with graceful shutdown support
        async def run_server_with_background_tasks():
             async with anyio.create_task_group() as tg:
                 global rag_index_task
                 logger.info("Starting background RAG indexer task...")
                 rag_index_task = tg.start_soon(run_rag_indexing_periodically)
                 # Start the server
                 # Pass log_config=None to prevent uvicorn from overriding root logger setup
                 config = uvicorn.Config(web_app, host="0.0.0.0", port=port, log_config=None)
                 server = uvicorn.Server(config)
                 await server.serve()
                 logger.info("Server stopped. Waiting for RAG indexer to finish current cycle...")

        try:
            anyio.run(run_server_with_background_tasks)
        except KeyboardInterrupt:
             logger.info("Keyboard interrupt received, shutting down...")
        finally:
             pass # No temp dir cleanup needed
    else:
        # Handle stdio transport with background task
        async def arun():
            async with anyio.create_task_group() as tg:
                global rag_index_task
                logger.info("Starting background RAG indexer task...")
                rag_index_task = tg.start_soon(run_rag_indexing_periodically)
                
                # Run stdio server part
                try:
                    from mcp.server.stdio import stdio_server
                    async with stdio_server() as streams:
                        await app.run(
                            streams[0], 
                            streams[1], 
                            app.create_initialization_options()
                        )
                except KeyboardInterrupt:
                    print("Keyboard interrupt received during stdio run, shutting down...")
                    # await tg.cancel_scope.cancel() # Cancel background task
                finally:
                     pass # No temp dir cleanup needed
            logger.info("Stdio server and background tasks finished.")
        try:
            anyio.run(arun)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")
            
    return 0

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except Exception as e:
        logger.exception(f"Unexpected error in main: {e}")
        print(f"Unexpected error: {e}")