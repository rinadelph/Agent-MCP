# Agent-MCP/mcp_template/mcp_server_src/tools/admin_tools.py
import json
import datetime
import subprocess # For launching Cursor (will be commented out)
import os
import sqlite3
from typing import List, Dict, Any, Optional

import mcp.types as mcp_types # Assuming this is your mcp.types path

from .registry import register_tool
from ..core.config import logger, AGENT_COLORS # AGENT_COLORS for create_agent
from ..core import globals as g
from ..core.auth import verify_token, generate_token # For create_agent, terminate_agent
from ..utils.audit_utils import log_audit
from ..utils.project_utils import generate_system_prompt # For create_agent
from ..db.connection import get_db_connection
from ..db.actions.agent_actions_db import log_agent_action_to_db # For DB logging

# --- create_agent tool ---
# Original logic from main.py: lines 1060-1203 (create_agent_tool function)
async def create_agent_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    token = arguments.get("token")
    agent_id = arguments.get("agent_id")
    capabilities = arguments.get("capabilities") # This was List[str]
    working_directory_arg = arguments.get("working_directory") # This was str

    if not verify_token(token, "admin"): # main.py:1066
        return [mcp_types.TextContent(type="text", text="Unauthorized: Admin token required")]

    if not agent_id or not isinstance(agent_id, str):
        return [mcp_types.TextContent(type="text", text="Error: agent_id is required and must be a string.")]

    # Check in-memory map first (main.py:1072)
    if agent_id in g.agent_working_dirs:
        return [mcp_types.TextContent(type="text", text=f"Agent '{agent_id}' already exists (in active memory).")]

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Double check in DB (main.py:1077-1081)
        cursor.execute("SELECT agent_id FROM agents WHERE agent_id = ?", (agent_id,))
        if cursor.fetchone():
            return [mcp_types.TextContent(type="text", text=f"Agent '{agent_id}' already exists (in database).")]

        # Generate token and prepare data (main.py:1089-1092)
        new_agent_token = generate_token()
        created_at_iso = datetime.datetime.now().isoformat()
        capabilities_json = json.dumps(capabilities or [])
        status = "created" # Or "active" immediately? Original used "created".

        # Assign a color (main.py:1095-1097)
        agent_color = AGENT_COLORS[g.agent_color_index % len(AGENT_COLORS)]
        g.agent_color_index += 1

        # Determine working directory (main.py:1100-1104)
        # MCP_PROJECT_DIR is set by cli.py or server startup.
        project_dir_env = os.environ.get("MCP_PROJECT_DIR")
        if not project_dir_env:
            logger.error("MCP_PROJECT_DIR environment variable not set. Cannot determine agent working directory.")
            return [mcp_types.TextContent(type="text", text="Server configuration error: MCP_PROJECT_DIR not set.")]
        
        base_project_dir = os.path.abspath(project_dir_env)
        if working_directory_arg and isinstance(working_directory_arg, str):
            # Ensure working_directory_arg is treated as relative to project_dir if not absolute
            if not os.path.isabs(working_directory_arg):
                agent_working_dir_abs = os.path.abspath(os.path.join(base_project_dir, working_directory_arg))
            else:
                agent_working_dir_abs = os.path.abspath(working_directory_arg)
            # Security check: ensure the working directory is within the project_dir or a configured allowed path
            # For now, we assume any absolute path provided is acceptable if admin provides it.
        else:
            agent_working_dir_abs = base_project_dir
        
        # Ensure the working directory exists
        try:
            os.makedirs(agent_working_dir_abs, exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create working directory {agent_working_dir_abs} for agent {agent_id}: {e}")
            return [mcp_types.TextContent(type="text", text=f"Error creating working directory: {e}")]


        # Insert into Database (main.py:1107-1117)
        cursor.execute("""
            INSERT INTO agents (token, agent_id, capabilities, created_at, status, working_directory, color, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            new_agent_token, agent_id, capabilities_json, created_at_iso, status,
            agent_working_dir_abs, agent_color,
            created_at_iso # updated_at initially same as created_at
        ))
        
        # Log action to agent_actions table (main.py:1119)
        log_agent_action_to_db(cursor, "admin", "created_agent", details={'agent_id': agent_id, 'color': agent_color, 'wd': agent_working_dir_abs})
        conn.commit()

        # Update in-memory state (main.py:1126-1133)
        g.active_agents[new_agent_token] = {
            "agent_id": agent_id,
            "capabilities": capabilities or [],
            "created_at": created_at_iso,
            "status": status,
            "current_task": None,
            "color": agent_color
        }
        g.agent_working_dirs[agent_id] = agent_working_dir_abs

        # Log to audit log file (main.py:1136-1144)
        log_audit(
            "admin",
            "create_agent",
            {
                "agent_id": agent_id,
                "capabilities": capabilities or [],
                "working_directory": agent_working_dir_abs,
                "assigned_color": agent_color
            }
        )

        # Generate system prompt (main.py:1147)
        # The original passed `token` (admin token) if agent_id started with "admin".
        # `generate_system_prompt` now takes `admin_token_runtime`.
        system_prompt_str = generate_system_prompt(agent_id, new_agent_token, g.admin_token)

        # Launch Cursor window (main.py:1150-1166) - COMMENTED OUT AS REQUESTED
        launch_status = "Cursor window launch functionality is currently disabled in the refactored code."
        # try:
        #     profile_num = g.agent_profile_counter
        #     g.agent_profile_counter -= 1
        #     if g.agent_profile_counter < 1: g.agent_profile_counter = 20
        #
        #     cursor_exe_path = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Programs", "Cursor", "Cursor.exe")
        #     if not os.path.exists(cursor_exe_path):
        #         # Try common alternative paths or log error
        #         # For now, assume it might not be found and report that.
        #         logger.warning(f"Cursor.exe not found at default path: {cursor_exe_path}")
        #         raise FileNotFoundError(f"Cursor.exe not found at {cursor_exe_path}")
        #
        #     env_vars = os.environ.copy()
        #     env_vars["CURSOR_AGENT_ID"] = agent_id
        #     env_vars["CURSOR_MCP_URL"] = f"http://localhost:{os.environ.get('PORT', '8080')}" # Should use configured URL
        #     env_vars["CURSOR_WORKING_DIR"] = agent_working_dir_abs
        #     if agent_id.lower().startswith("admin") and new_agent_token == g.admin_token: # Check if this agent IS the admin
        #         env_vars["CURSOR_ADMIN_TOKEN"] = g.admin_token
        #     else:
        #         env_vars["CURSOR_AGENT_TOKEN"] = new_agent_token
        #
        #     # Using subprocess.Popen for non-blocking start
        #     subprocess.Popen([
        #         "cmd", "/c", "start", f"Cursor Agent - {agent_id}", cursor_exe_path,
        #         f"--user-data-dir={profile_num}", "--max-memory=16384" # Consider making memory configurable
        #     ], env=env_vars, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=subprocess.CREATE_NO_WINDOW) # CREATE_NO_WINDOW for Windows
        #     launch_status = f"✅ Cursor window for agent '{agent_id}' launched with profile {profile_num}."
        #     logger.info(launch_status)
        # except FileNotFoundError as e_fnf:
        #     launch_status = f"❌ Failed to launch Cursor: {str(e_fnf)}. Ensure Cursor is installed at the expected location."
        #     logger.error(launch_status)
        # except Exception as e_launch:
        #     launch_status = f"❌ Failed to launch Cursor window: {str(e_launch)}"
        #     logger.error(launch_status, exc_info=True)

        # Log to console (main.py:1169-1174)
        console_output = (
            f"\n=== Agent '{agent_id}' Created ===\n"
            f"Token: {new_agent_token}\n"
            f"Assigned Color: {agent_color}\n"
            f"Working Directory: {agent_working_dir_abs}\n"
            f"{launch_status}\n"
            f"=========================\n"
            f"=== System Prompt for {agent_id} ===\n{system_prompt_str}\n"
            f"========================="
        )
        logger.info(f"Agent '{agent_id}' created. Token: {new_agent_token}, Color: {agent_color}, WD: {agent_working_dir_abs}")
        print(console_output) # For direct CLI feedback

        return [mcp_types.TextContent(
            type="text",
            text=f"Agent '{agent_id}' created successfully.\n"
                 f"Token: {new_agent_token}\n"
                 f"Assigned Color: {agent_color}\n"
                 f"Working Directory: {agent_working_dir_abs}\n"
                 f"{launch_status}\n\n"
                 f"System Prompt:\n{system_prompt_str}"
        )]

    except sqlite3.Error as e_sql:
        if conn: conn.rollback()
        logger.error(f"Database error creating agent {agent_id}: {e_sql}", exc_info=True)
        return [mcp_types.TextContent(type="text", text=f"Database error creating agent: {e_sql}")]
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Unexpected error creating agent {agent_id}: {e}", exc_info=True)
        return [mcp_types.TextContent(type="text", text=f"Unexpected error creating agent: {e}")]
    finally:
        if conn:
            conn.close()

# --- view_status tool ---
# Original logic from main.py: lines 1242-1268 (view_status_tool function)
async def view_status_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    token = arguments.get("token")

    if not verify_token(token, "admin"): # main.py:1244
        return [mcp_types.TextContent(type="text", text="Unauthorized: Admin token required")]

    log_audit("admin", "view_status", {}) # main.py:1249

    # Build agent status from g.active_agents and g.agent_working_dirs (main.py:1251-1259)
    agent_status_dict = {}
    for agent_tkn, agent_data in g.active_agents.items():
        agent_id = agent_data.get("agent_id")
        if agent_id: # Should always be present if agent_data is valid
            agent_status_dict[agent_id] = {
                "status": agent_data.get("status", "unknown"),
                "current_task": agent_data.get("current_task"),
                "capabilities": agent_data.get("capabilities", []),
                "working_directory": g.agent_working_dirs.get(agent_id, "N/A"),
                "color": agent_data.get("color", "N/A") # Added color from active_agents
            }
    
    # Server uptime was N/A in original (main.py:1264)
    # We need a server start time global to calculate this, or pass it from app lifecycle.
    # For now, keeping it N/A for 1-to-1.
    server_start_time_iso = g.server_start_time if hasattr(g, 'server_start_time') else None
    uptime_str = "N/A"
    if server_start_time_iso:
        uptime_delta = datetime.datetime.now() - datetime.datetime.fromisoformat(server_start_time_iso)
        uptime_str = str(uptime_delta)


    status_payload = { # main.py:1260-1266
        "active_connections": len(g.connections), # g.connections might be managed by SSE transport layer
        "active_agents_count": len(g.active_agents),
        "agents_details": agent_status_dict,
        "server_uptime": uptime_str,
        "file_map_size": len(g.file_map),
        "file_map_preview": {k: v for i, (k, v) in enumerate(g.file_map.items()) if i < 5} # Preview first 5
        # Consider adding task counts, DB status, RAG index status etc.
    }

    try:
        status_json = json.dumps(status_payload, indent=2)
    except TypeError as e:
        logger.error(f"Error serializing server status to JSON: {e}")
        status_json = f"Error creating status JSON: {e}"

    return [mcp_types.TextContent(type="text", text=f"MCP Server Status:\n{status_json}")]

# --- terminate_agent tool ---
# Original logic from main.py: lines 1270-1316 (terminate_agent_tool function)
async def terminate_agent_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    token = arguments.get("token")
    agent_id_to_terminate = arguments.get("agent_id")

    if not verify_token(token, "admin"): # main.py:1274
        return [mcp_types.TextContent(type="text", text="Unauthorized: Admin token required")]

    if not agent_id_to_terminate or not isinstance(agent_id_to_terminate, str):
        return [mcp_types.TextContent(type="text", text="Error: agent_id to terminate is required.")]

    # Find agent token from in-memory map (main.py:1279-1283)
    found_agent_token: Optional[str] = None
    for tkn, data in g.active_agents.items():
        if data.get("agent_id") == agent_id_to_terminate:
            found_agent_token = tkn
            break
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if not found_agent_token:
            # Check DB if not found in memory (main.py:1285-1290)
            cursor.execute("SELECT token FROM agents WHERE agent_id = ? AND status != ?", (agent_id_to_terminate, "terminated"))
            row = cursor.fetchone()
            if row:
                # Agent exists in DB but not active memory. Proceed to terminate in DB.
                logger.warning(f"Agent {agent_id_to_terminate} found in DB (token: {row['token']}) but not in active memory. Proceeding with DB termination.")
                # We don't have its token to remove from g.active_agents if it's not there.
            else:
                return [mcp_types.TextContent(type="text", text=f"Agent '{agent_id_to_terminate}' not found or already terminated.")]
        
        # Update agent status in Database (main.py:1295-1302)
        terminated_at_iso = datetime.datetime.now().isoformat()
        cursor.execute("""
            UPDATE agents SET status = ?, terminated_at = ?, updated_at = ?, current_task = NULL
            WHERE agent_id = ? AND status != ? 
        """, ("terminated", terminated_at_iso, terminated_at_iso, agent_id_to_terminate, "terminated"))
        # Set current_task to NULL as well.
        
        if cursor.rowcount == 0 and not found_agent_token: # If DB check didn't find it initially and update affected 0 rows
             return [mcp_types.TextContent(type="text", text=f"Agent '{agent_id_to_terminate}' not found in DB or already terminated.")]

        log_agent_action_to_db(cursor, "admin", "terminated_agent", details={'agent_id': agent_id_to_terminate})
        conn.commit()

        # Remove from active in-memory state if present (main.py:1309-1311)
        if found_agent_token and found_agent_token in g.active_agents:
            del g.active_agents[found_agent_token]
        if agent_id_to_terminate in g.agent_working_dirs:
            del g.agent_working_dirs[agent_id_to_terminate]
        
        # Release any files held by this agent from g.file_map
        files_released_count = 0
        for filepath, info in list(g.file_map.items()): # Iterate over a copy
            if info.get("agent_id") == agent_id_to_terminate:
                del g.file_map[filepath]
                files_released_count +=1
        if files_released_count > 0:
            logger.info(f"Released {files_released_count} files held by terminated agent {agent_id_to_terminate}.")


        log_audit("admin", "terminate_agent", {"agent_id": agent_id_to_terminate}) # main.py:1313
        logger.info(f"Agent '{agent_id_to_terminate}' terminated successfully.")
        return [mcp_types.TextContent(type="text", text=f"Agent '{agent_id_to_terminate}' terminated.")]

    except sqlite3.Error as e_sql:
        if conn: conn.rollback()
        logger.error(f"Database error terminating agent {agent_id_to_terminate}: {e_sql}", exc_info=True)
        return [mcp_types.TextContent(type="text", text=f"Database error terminating agent: {e_sql}")]
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Unexpected error terminating agent {agent_id_to_terminate}: {e}", exc_info=True)
        return [mcp_types.TextContent(type="text", text=f"Unexpected error terminating agent: {e}")]
    finally:
        if conn:
            conn.close()

# --- view_audit_log tool ---
# Original logic from main.py: lines 1387-1408 (view_audit_log_tool function)
async def view_audit_log_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    token = arguments.get("token")
    filter_agent_id = arguments.get("agent_id") # Optional filter
    filter_action = arguments.get("action")     # Optional filter
    limit = arguments.get("limit", 50)          # Default limit 50

    if not verify_token(token, "admin"): # main.py:1389
        return [mcp_types.TextContent(type="text", text="Unauthorized: Admin token required")]

    # Validate limit
    try:
        limit = int(limit)
        if not (1 <= limit <= 200): # Max 200 for safety
            limit = 50 
    except ValueError:
        limit = 50

    # Filter the in-memory audit log (g.audit_log) (main.py:1394-1400)
    # For a more complete audit log, one might query the agent_actions table from DB.
    # The original tool only viewed the in-memory `audit_log`.
    
    # The original `audit_log` was a global list.
    # The `log_audit` function in `utils/audit_utils.py` appends to `g.audit_log`.
    # So, we read from `g.audit_log`.
    
    # Create a working copy for filtering
    current_audit_log_snapshot = list(g.audit_log) # Filter from a snapshot
    
    filtered_log_entries = current_audit_log_snapshot
    if filter_agent_id:
        filtered_log_entries = [entry for entry in filtered_log_entries if entry.get("agent_id") == filter_agent_id]
    if filter_action:
        filtered_log_entries = [entry for entry in filtered_log_entries if entry.get("action") == filter_action]

    # Get the most recent entries up to the limit (main.py:1403)
    # Slicing from the end gives recent entries.
    limited_log_entries = filtered_log_entries[-limit:]

    # Log this action itself (main.py:1405)
    log_audit("admin", "view_audit_log", {"filter_agent_id": filter_agent_id, "filter_action": filter_action, "limit": limit})

    try:
        log_json = json.dumps(limited_log_entries, indent=2)
    except TypeError as e:
        logger.error(f"Error serializing audit log to JSON: {e}")
        log_json = f"Error creating audit log JSON: {e}"

    return [mcp_types.TextContent(
        type="text",
        text=f"Audit Log ({len(limited_log_entries)} entries displayed, filtered by agent: {filter_agent_id or 'Any'}, action: {filter_action or 'Any'}):\n{log_json}"
    )]

# --- get_agent_tokens tool ---
async def get_agent_tokens_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    """
    Retrieve agent tokens with advanced filtering capabilities.
    Supports filtering by status, agent_id pattern, creation date range, and more.
    """
    token = arguments.get("token")
    
    # Authentication
    if not verify_token(token, "admin"):
        return [mcp_types.TextContent(type="text", text="Unauthorized: Admin token required")]
    
    # Extract and validate filter parameters
    filter_status = arguments.get("filter_status")  # e.g., "active", "terminated", "created"
    filter_agent_id_pattern = arguments.get("filter_agent_id_pattern")  # SQL LIKE pattern
    filter_created_after = arguments.get("filter_created_after")  # ISO format date
    filter_created_before = arguments.get("filter_created_before")  # ISO format date
    include_terminated = arguments.get("include_terminated", False)  # Boolean
    include_sensitive_data = arguments.get("include_sensitive_data", True)  # Boolean
    limit = arguments.get("limit", 50)  # Default limit
    offset = arguments.get("offset", 0)  # Pagination offset
    sort_by = arguments.get("sort_by", "created_at")  # Sort field
    sort_order = arguments.get("sort_order", "DESC")  # ASC or DESC
    
    # Validate parameters
    try:
        limit = int(limit)
        if not (1 <= limit <= 500):  # Max 500 for safety
            limit = 50
    except (ValueError, TypeError):
        limit = 50
    
    try:
        offset = int(offset)
        if offset < 0:
            offset = 0
    except (ValueError, TypeError):
        offset = 0
    
    # Validate sort parameters
    allowed_sort_fields = ["created_at", "updated_at", "agent_id", "status"]
    if sort_by not in allowed_sort_fields:
        sort_by = "created_at"
    
    if sort_order.upper() not in ["ASC", "DESC"]:
        sort_order = "DESC"
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Build dynamic query
        base_query = """
            SELECT token, agent_id, status, created_at
            FROM agents
            WHERE 1=1
        """
        
        query_params = []
        
        # Apply filters
        if filter_status:
            base_query += " AND status = ?"
            query_params.append(filter_status)
        
        if filter_agent_id_pattern:
            base_query += " AND agent_id LIKE ?"
            query_params.append(filter_agent_id_pattern)
        
        if not include_terminated:
            base_query += " AND status != ?"
            query_params.append("terminated")
        
        if filter_created_after:
            base_query += " AND created_at >= ?"
            query_params.append(filter_created_after)
        
        if filter_created_before:
            base_query += " AND created_at <= ?"
            query_params.append(filter_created_before)
        
        # Add sorting and pagination
        base_query += f" ORDER BY {sort_by} {sort_order}"
        base_query += " LIMIT ? OFFSET ?"
        query_params.extend([limit, offset])
        
        # Execute query
        cursor.execute(base_query, query_params)
        rows = cursor.fetchall()
        
        # Process results
        agents_data = []
        for row in rows:
            agent_data = dict(row)
            
            # Handle sensitive data
            if not include_sensitive_data:
                # Mask the token for security
                if 'token' in agent_data:
                    token_value = agent_data['token']
                    if token_value and len(token_value) > 8:
                        agent_data['token'] = token_value[:4] + "..." + token_value[-4:]
                    else:
                        agent_data['token'] = "***"
            
            agents_data.append(agent_data)
        
        # Get total count for pagination info
        count_query = """
            SELECT COUNT(*) as total
            FROM agents
            WHERE 1=1
        """
        
        count_params = []
        if filter_status:
            count_query += " AND status = ?"
            count_params.append(filter_status)
        
        if filter_agent_id_pattern:
            count_query += " AND agent_id LIKE ?"
            count_params.append(filter_agent_id_pattern)
        
        if not include_terminated:
            count_query += " AND status != ?"
            count_params.append("terminated")
        
        if filter_created_after:
            count_query += " AND created_at >= ?"
            count_params.append(filter_created_after)
        
        if filter_created_before:
            count_query += " AND created_at <= ?"
            count_params.append(filter_created_before)
        
        cursor.execute(count_query, count_params)
        total_count = cursor.fetchone()[0]
        
        # Log this access
        log_audit("admin", "get_agent_tokens", {
            "filter_status": filter_status,
            "filter_agent_id_pattern": filter_agent_id_pattern,
            "agents_returned": len(agents_data),
            "total_matching": total_count,
            "include_sensitive_data": include_sensitive_data
        })
        
        # Build response
        response_data = {
            "agents": agents_data,
            "pagination": {
                "offset": offset,
                "limit": limit,
                "total_count": total_count,
                "returned_count": len(agents_data),
                "has_more": offset + len(agents_data) < total_count
            },
            "filters_applied": {
                "filter_status": filter_status,
                "filter_agent_id_pattern": filter_agent_id_pattern,
                "filter_created_after": filter_created_after,
                "filter_created_before": filter_created_before,
                "include_terminated": include_terminated,
                "include_sensitive_data": include_sensitive_data
            },
            "sort": {
                "sort_by": sort_by,
                "sort_order": sort_order
            }
        }
        
        try:
            response_json = json.dumps(response_data, indent=2)
        except TypeError as e:
            logger.error(f"Error serializing agent tokens response to JSON: {e}")
            response_json = f"Error creating response JSON: {e}"
        
        return [mcp_types.TextContent(
            type="text",
            text=f"Agent Tokens ({len(agents_data)} of {total_count} total):\n{response_json}"
        )]
    
    except sqlite3.Error as e_sql:
        logger.error(f"Database error retrieving agent tokens: {e_sql}", exc_info=True)
        return [mcp_types.TextContent(type="text", text=f"Database error retrieving agent tokens: {e_sql}")]
    except Exception as e:
        logger.error(f"Unexpected error retrieving agent tokens: {e}", exc_info=True)
        return [mcp_types.TextContent(type="text", text=f"Unexpected error retrieving agent tokens: {e}")]
    finally:
        if conn:
            conn.close()


# --- Register all admin tools ---
def register_admin_tools():
    register_tool(
        name="create_agent",
        description="Create a new agent with the specified ID, capabilities, and optional working directory.",
        input_schema={ # From main.py:1641-1661, added working_directory
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "Admin authentication token"},
                "agent_id": {"type": "string", "description": "Unique identifier for the agent"},
                "capabilities": {
                    "type": "array",
                    "description": "List of agent capabilities (e.g., 'code_edit', 'file_read')",
                    "items": {"type": "string"},
                    "default": []
                },
                "working_directory": {
                    "type": "string",
                    "description": "Optional working directory for the agent. If relative, it's based on the project root. Defaults to project root."
                }
            },
            "required": ["token", "agent_id"],
            "additionalProperties": False # As per original
        },
        implementation=create_agent_tool_impl
    )

    register_tool(
        name="view_status",
        description="View the status of all agents, connections, and the MCP server.",
        input_schema={ # From main.py:1663-1674
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "Admin authentication token"}
            },
            "required": ["token"],
            "additionalProperties": False
        },
        implementation=view_status_tool_impl
    )

    register_tool(
        name="terminate_agent",
        description="Terminate an active agent with the given ID.",
        input_schema={ # From main.py:1676-1689
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "Admin authentication token"},
                "agent_id": {"type": "string", "description": "Unique identifier for the agent to terminate"}
            },
            "required": ["token", "agent_id"],
            "additionalProperties": False
        },
        implementation=terminate_agent_tool_impl
    )

    register_tool(
        name="view_audit_log",
        description="View the in-memory audit log, optionally filtered by agent ID or action, with a limit.",
        input_schema={ # From main.py:1788-1810
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "Admin authentication token"},
                "agent_id": {"type": "string", "description": "Filter audit log by agent ID (optional)"},
                "action": {"type": "string", "description": "Filter audit log by action (e.g., 'create_agent') (optional)"},
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of entries to return (default 50, max 200)",
                    "default": 50,
                    "minimum": 1,
                    "maximum": 200
                }
            },
            "required": ["token"],
            "additionalProperties": False
        },
        implementation=view_audit_log_tool_impl
    )

    register_tool(
        name="get_agent_tokens",
        description="Retrieve agent tokens with advanced filtering capabilities. Supports filtering by status, agent_id pattern, creation date range, and more.",
        input_schema={
            "type": "object",
            "properties": {
                "token": {
                    "type": "string", 
                    "description": "Admin authentication token"
                },
                "filter_status": {
                    "type": "string",
                    "description": "Filter by agent status (e.g., 'active', 'terminated', 'created')"
                },
                "filter_agent_id_pattern": {
                    "type": "string",
                    "description": "Filter by agent ID using SQL LIKE pattern (e.g., 'test_%', '%prod%')"
                },
                "filter_created_after": {
                    "type": "string",
                    "description": "Filter agents created after this date (ISO format: YYYY-MM-DDTHH:MM:SS)"
                },
                "filter_created_before": {
                    "type": "string",
                    "description": "Filter agents created before this date (ISO format: YYYY-MM-DDTHH:MM:SS)"
                },
                "include_terminated": {
                    "type": "boolean",
                    "description": "Include terminated agents in results (default: false)",
                    "default": False
                },
                "include_sensitive_data": {
                    "type": "boolean",
                    "description": "Include full tokens in response (default: true). If false, tokens will be masked for security.",
                    "default": True
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of agents to return (default: 50, max: 500)",
                    "default": 50,
                    "minimum": 1,
                    "maximum": 500
                },
                "offset": {
                    "type": "integer",
                    "description": "Number of agents to skip for pagination (default: 0)",
                    "default": 0,
                    "minimum": 0
                },
                "sort_by": {
                    "type": "string",
                    "description": "Field to sort by (default: 'created_at')",
                    "enum": ["created_at", "updated_at", "agent_id", "status"],
                    "default": "created_at"
                },
                "sort_order": {
                    "type": "string",
                    "description": "Sort order (default: 'DESC')",
                    "enum": ["ASC", "DESC"],
                    "default": "DESC"
                }
            },
            "required": ["token"],
            "additionalProperties": False
        },
        implementation=get_agent_tokens_tool_impl
    )

# Call registration when this module is imported
register_admin_tools()