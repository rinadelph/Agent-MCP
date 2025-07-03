# Agent-MCP/mcp_template/mcp_server_src/core/globals.py
"""
Centralized mutable global state for the MCP server.
To use:
from mcp_server_src.core import globals as g
g.admin_token = "new_token"
"""
import anyio # For rag_index_task type hint
from typing import Dict, List, Optional, Any

# --- Core Server State ---
# From main.py:147
# Client ID -> Connection data (Note: original usage of 'connections' might be simplified
# or its management moved if it's purely for SSE connection tracking by the transport layer)
connections: Dict[str, Any] = {}

# From main.py:148
active_agents: Dict[str, Dict[str, Any]] = {}  # Agent Token -> Agent data

# From main.py:149
# This is the runtime admin_token.
# Initialization logic (generate/load) will be handled during server startup.
admin_token: Optional[str] = None

# From main.py:150
tasks: Dict[str, Dict[str, Any]] = {}  # Task ID -> Task data (in-memory cache of tasks)

# --- File and Directory State ---
# From main.py:153
file_map: Dict[str, Dict[str, Any]] = {}  # filepath -> {"agent_id": ..., "timestamp": ..., "status": ...}

# From main.py:154
agent_working_dirs: Dict[str, str] = {}  # agent_id -> absolute_working_directory_path

# --- Auditing and Agent Management ---
# From main.py:155
# In-memory audit log for the current session. Persistent log is 'agent_audit.log'.
audit_log: List[Dict[str, Any]] = []

# From main.py:158
agent_profile_counter: int = 20 # For cycling Cursor profile numbers

# From main.py:166
agent_color_index: int = 0 # For cycling through AGENT_COLORS from config.py

# --- Server Lifecycle ---
# From main.py:169
server_running: bool = True # Flag to control main server loop and background tasks, handled by signal_utils.py

# Flag to track if server initialization is complete
# This prevents handling requests before critical components are ready
server_initialized: bool = False

# Timestamp when server initialization completed
server_start_time: Optional[float] = None

# --- External Service Clients (Placeholders) ---
# From main.py:185
# The actual OpenAI client instance will be initialized and managed by external/openai_service.py.
# This global variable can serve as a reference if truly global access is needed,
# though passing the client explicitly or using a getter from openai_service is cleaner.
# For now, we'll keep it as a placeholder reflecting the original structure.
# Type hint can be refined to `openai.OpenAI` once that module is structured.
openai_client_instance: Optional[Any] = None

# Async OpenAI client instance for use in async contexts
# This avoids blocking the event loop when making OpenAI API calls
openai_async_client_instance: Optional[Any] = None

# --- Database/VSS State ---
# From main.py:200
# Flag to check if sqlite-vec extension loadability has been tested.
global_vss_load_tested: bool = False

# From main.py:201
# Flag indicating if sqlite-vec extension was successfully loaded during the initial test.
global_vss_load_successful: bool = False

# --- Background Task Handles ---
# From main.py:510 (and used in main.py:1943, 2627, 2641)
# Handle for the RAG indexing background task, typically managed by an anyio.TaskGroup.
# The type hint `anyio.abc.CancelScope` is a common way to hold a reference that allows cancellation.
rag_index_task_scope: Optional[anyio.abc.CancelScope] = None

# Note: The original `main.py` also had `openai_client = None` at line 185.
# I've named it `openai_client_instance` here to avoid confusion with the module name
# if we later have `import openai_client from ...`.
# The actual OpenAI client will be initialized and managed in `external/openai_service.py`.