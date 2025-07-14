# Agent-MCP/mcp_template/mcp_server_src/app/server_lifecycle.py
import os
import json
import datetime
import sqlite3
import anyio  # For managing background tasks
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Project-specific imports
from ..core.config import logger, get_project_dir
from ..core import globals as g
from ..core.auth import generate_token  # For admin token generation
from ..utils.project_utils import init_agent_directory
from ..db.schema import init_database as initialize_database_schema
from ..db.connection import get_db_connection, check_vss_loadability
from ..external.openai_service import initialize_openai_client
from ..features.rag.indexing import run_rag_indexing_periodically

from ..features.claude_session_monitor import run_claude_session_monitoring
from ..utils.signal_utils import register_signal_handlers  # For graceful shutdown
from ..db.write_queue import get_write_queue


# This function encapsulates the logic originally in main() before server run.
async def application_startup(
    project_dir_path_str: str, admin_token_param: Optional[str] = None
):
    """
    Handles all application startup procedures:
    - Sets project directory environment variable.
    - Initializes .agent directory.
    - Initializes database schema.
    - Handles admin token persistence (load or generate).
    - Loads existing state (agents, tasks) from DB.
    - Initializes external services (OpenAI client).
    - Performs VSS loadability check.
    - Registers signal handlers.
    """
    # Load environment variables from .env file
    load_dotenv()

    logger.info("MCP Server application starting up...")
    g.server_start_time = datetime.datetime.now().isoformat()  # For uptime calculation

    # 1. Handle Project Directory (Original main.py:1950-1959)
    project_path = Path(project_dir_path_str).resolve()
    if not project_path.exists():
        logger.info(f"Project directory '{project_path}' does not exist. Creating it.")
        try:
            project_path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(
                f"CRITICAL: Failed to create project directory '{project_path}': {e}. Exiting."
            )
            raise SystemExit(f"Failed to create project directory: {e}") from e
    elif not project_path.is_dir():
        logger.error(
            f"CRITICAL: Project path '{project_path}' is not a directory. Exiting."
        )
        raise SystemExit(f"Project path '{project_path}' is not a directory.")

    os.environ["MCP_PROJECT_DIR"] = str(
        project_path
    )  # Critical for other modules using get_project_dir()
    logger.info(f"Using project directory: {project_path}")

    # 2. Initialize .agent directory (Original main.py:1962-1966)
    agent_dir = init_agent_directory(
        str(project_path)
    )  # project_utils.init_agent_directory
    if agent_dir is None:  # init_agent_directory returns None on critical failure
        logger.error(
            "CRITICAL: Failed to initialize .agent directory structure. Exiting."
        )
        raise SystemExit("Failed to initialize .agent directory.")
    logger.info(f".agent directory initialized at {agent_dir}")

    # 3. Initialize Database Schema (Original main.py:1969-1974)
    try:
        initialize_database_schema()  # db.schema.init_database
    except Exception as e:
        logger.error(
            f"CRITICAL: Failed to initialize database: {e}. Exiting.", exc_info=True
        )
        # DB_FILE_NAME is in core.config, get_db_path uses it.
        from ..core.config import get_db_path as get_db_path_for_error

        db_path_err = get_db_path_for_error()  # Get path for error message
        raise SystemExit(
            f"Error: Failed to initialize database at {db_path_err}. Check logs and permissions."
        ) from e

    # 4. Handle Admin Token Persistence (Original main.py:1977-2012)
    # This logic ensures g.admin_token is set.
    admin_token_key_in_db = "config_admin_token"  # As used in original
    conn_admin_token = None
    effective_admin_token: Optional[str] = None
    token_source_description: str = ""

    try:
        conn_admin_token = get_db_connection()
        cursor = conn_admin_token.cursor()
        if admin_token_param:
            effective_admin_token = admin_token_param
            token_source_description = "command-line parameter"
            cursor.execute(
                """
                INSERT OR REPLACE INTO project_context (context_key, value, last_updated, updated_by, description)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    admin_token_key_in_db,
                    json.dumps(effective_admin_token),
                    datetime.datetime.now().isoformat(),
                    "server_startup",
                    "Persistent MCP Admin Token",
                ),
            )
            conn_admin_token.commit()
            logger.info(f"Using admin token provided via {token_source_description}.")
        else:
            cursor.execute(
                "SELECT value FROM project_context WHERE context_key = ?",
                (admin_token_key_in_db,),
            )
            row = cursor.fetchone()
            if row and row["value"]:
                try:
                    loaded_token = json.loads(row["value"])
                    if isinstance(loaded_token, str) and loaded_token:
                        effective_admin_token = loaded_token
                        token_source_description = "stored configuration in database"
                        logger.info(
                            f"Loaded admin token from {token_source_description}."
                        )
                    else:
                        logger.warning(
                            "Stored admin token in DB is invalid. Generating a new one."
                        )
                except json.JSONDecodeError:
                    logger.warning(
                        "Failed to decode stored admin token from DB. Generating a new one."
                    )

            if not effective_admin_token:  # If not loaded or invalid
                effective_admin_token = generate_token()
                token_source_description = "newly generated"
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO project_context (context_key, value, last_updated, updated_by, description)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        admin_token_key_in_db,
                        json.dumps(effective_admin_token),
                        datetime.datetime.now().isoformat(),
                        "server_startup",
                        "Persistent MCP Admin Token",
                    ),
                )
                conn_admin_token.commit()
                logger.info(f"Generated and stored new admin token.")

        g.admin_token = effective_admin_token  # Set the global admin token
        logger.info(f"MCP Admin Token ({token_source_description}): {g.admin_token}")

    except sqlite3.Error as e_sql_admin:
        logger.error(
            f"Database error during admin token persistence: {e_sql_admin}. Falling back to temporary token.",
            exc_info=True,
        )
        g.admin_token = admin_token_param if admin_token_param else generate_token()
        logger.warning(f"Using temporary admin token due to DB error: {g.admin_token}")
    except Exception as e_admin:
        logger.error(
            f"Unexpected error during admin token persistence: {e_admin}. Falling back to temporary token.",
            exc_info=True,
        )
        g.admin_token = admin_token_param if admin_token_param else generate_token()
        logger.warning(
            f"Using temporary admin token due to unexpected error: {g.admin_token}"
        )
    finally:
        if conn_admin_token:
            conn_admin_token.close()

    if not g.admin_token:  # Should not happen if logic above is correct
        logger.error("CRITICAL: Admin token could not be set. Exiting.")
        raise SystemExit("Admin token initialization failed.")

    # 5. Load existing state from Database (Original main.py:2015-2045)
    logger.info("Loading existing state from database...")
    conn_load_state = None
    try:
        conn_load_state = get_db_connection()
        cursor = conn_load_state.cursor()

        # Load Active Agents (status != 'terminated')
        active_agents_count = 0
        cursor.execute(
            """
            SELECT token, agent_id, capabilities, created_at, status, current_task, working_directory, color 
            FROM agents WHERE status != ?
        """,
            ("terminated",),
        )
        for row in cursor.fetchall():
            agent_token_val = row["token"]
            agent_id_val = row["agent_id"]
            g.active_agents[agent_token_val] = {
                "agent_id": agent_id_val,
                "capabilities": json.loads(row["capabilities"] or "[]"),
                "created_at": row["created_at"],
                "status": row["status"],
                "current_task": row["current_task"],
                "color": row["color"],  # Added color loading
            }
            g.agent_working_dirs[agent_id_val] = row["working_directory"]
            active_agents_count += 1
        logger.info(f"Loaded {active_agents_count} active agents from database.")

        # Load All Tasks into g.tasks
        task_count = 0
        cursor.execute("SELECT * FROM tasks")  # Load all tasks
        for row_dict in (dict(row) for row in cursor.fetchall()):
            task_id_val = row_dict["task_id"]
            # Ensure complex fields are Python lists/dicts in memory
            for field_key in ["child_tasks", "depends_on_tasks", "notes"]:
                if isinstance(row_dict.get(field_key), str):
                    try:
                        row_dict[field_key] = json.loads(row_dict[field_key] or "[]")
                    except json.JSONDecodeError:
                        logger.warning(
                            f"Failed to parse JSON for field '{field_key}' in task '{task_id_val}'. Defaulting to empty list."
                        )
                        row_dict[field_key] = []
            g.tasks[task_id_val] = row_dict
            task_count += 1
        logger.info(f"Loaded {task_count} tasks into memory cache.")

        # File map (g.file_map) and audit log (g.audit_log) are transient and start empty.
        g.file_map.clear()
        g.audit_log.clear()
        logger.info(
            "In-memory file map and audit log initialized as empty for this session."
        )

    except sqlite3.Error as e_sql_load:
        logger.error(
            f"Database error during state loading: {e_sql_load}. Server might operate with incomplete state.",
            exc_info=True,
        )
        # Decide if this is critical. Original proceeded with empty state.
        g.active_agents.clear()
        g.tasks.clear()
        g.agent_working_dirs.clear()
    except Exception as e_load:
        logger.error(
            f"Unexpected error during state loading: {e_load}. Exiting.", exc_info=True
        )
        raise SystemExit(f"Unexpected error loading state: {e_load}") from e_load
    finally:
        if conn_load_state:
            conn_load_state.close()
    logger.info("State loading from database complete.")

    # 6. Initialize OpenAI Client (Original main.py: part of get_openai_client, called by RAG indexer)
    # We explicitly initialize it at startup now.
    if (
        not initialize_openai_client()
    ):  # external.openai_service.initialize_openai_client
        logger.warning(
            "OpenAI client failed to initialize. OpenAI-dependent features (like RAG) will be unavailable."
        )
        # Server can continue, but RAG won't work.

    # 6.5. Initialize Database Write Queue
    # This prevents SQLite lock contention during concurrent write operations
    write_queue = get_write_queue()
    await write_queue.start()
    logger.info("Database write queue initialized and started.")

    # 7. Perform VSS Loadability Check (Original main.py: called by init_database)
    # This ensures g.global_vss_load_successful is set.
    check_vss_loadability()  # db.connection.check_vss_loadability
    if g.global_vss_load_successful:
        logger.info("sqlite-vec (VSS) extension confirmed loadable.")
    else:
        logger.warning(
            "sqlite-vec (VSS) extension is NOT loadable. RAG search functionality will be impaired."
        )

    # 8. Register Signal Handlers (Original main.py: 839-840, called before server run)
    register_signal_handlers()  # utils.signal_utils.register_signal_handlers

    logger.info("MCP Server application startup sequence finished.")


async def start_background_tasks(task_group: anyio.abc.TaskGroup):
    """Starts long-running background tasks like the RAG indexer."""
    logger.info("Starting background tasks...")
    # Start RAG Indexer (Original main.py: 2625-2627)
    # The interval can be made configurable if needed.
    rag_interval = int(os.environ.get("MCP_RAG_INDEX_INTERVAL_SECONDS", "300"))
    g.rag_index_task_scope = await task_group.start(
        run_rag_indexing_periodically, rag_interval
    )
    logger.info(f"RAG indexing task started with interval {rag_interval}s.")

    # Start Claude Code Session Monitor - DISABLED
    # claude_session_interval = int(
    #     os.environ.get("MCP_CLAUDE_SESSION_MONITOR_INTERVAL", "5")
    # )
    # g.claude_session_task_scope = await task_group.start(
    #     run_claude_session_monitoring, claude_session_interval
    # )
    # logger.info(
    #     f"Claude Code session monitor started with interval {claude_session_interval}s."
    # )
    logger.info(
        "Claude Code session monitor disabled - hook functionality temporarily disabled"
    )


async def application_shutdown():
    """Handles graceful shutdown of application resources and tasks."""
    logger.info("MCP Server application shutting down...")
    g.server_running = False  # Ensure flag is set for all components

    # Cancel background tasks
    if g.rag_index_task_scope and not g.rag_index_task_scope.cancel_called:
        logger.info("Attempting to cancel RAG indexing task...")
        g.rag_index_task_scope.cancel()

    if g.claude_session_task_scope and not g.claude_session_task_scope.cancel_called:
        logger.info("Attempting to cancel Claude session monitoring task...")
        g.claude_session_task_scope.cancel()
        # Note: Actual waiting for task completion is usually handled by the AnyIO TaskGroup context manager.

    # Stop database write queue
    write_queue = get_write_queue()
    await write_queue.stop()
    logger.info("Database write queue stopped.")

    # Add any other cleanup (e.g., closing persistent connections if not managed by context)
    # For SQLite, connections are typically short-lived per request/operation.

    logger.info("MCP Server application shutdown sequence complete.")


# These functions will be used by the Starlette app's `on_startup` and `on_shutdown` events,
# or by the CLI runner.
