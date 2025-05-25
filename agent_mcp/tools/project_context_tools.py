# Agent-MCP/mcp_template/mcp_server_src/tools/project_context_tools.py
import json
import datetime
import sqlite3
from typing import List, Dict, Any, Optional

import mcp.types as mcp_types

from .registry import register_tool
from ..core.config import logger
from ..core import globals as g # Not directly used here, but auth uses it
from ..core.auth import get_agent_id, verify_token
from ..utils.audit_utils import log_audit
from ..db.connection import get_db_connection
from ..db.actions.agent_actions_db import log_agent_action_to_db


# --- view_project_context tool ---
# Original logic from main.py: lines 1411-1465 (view_project_context_tool function)
async def view_project_context_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    agent_auth_token = arguments.get("token")
    context_key_filter = arguments.get("context_key") # Optional specific key
    search_query_filter = arguments.get("search_query") # Optional search query

    requesting_agent_id = get_agent_id(agent_auth_token) # main.py:1414
    if not requesting_agent_id:
        return [mcp_types.TextContent(type="text", text="Unauthorized: Valid token required")]

    # Log audit (main.py:1417)
    log_audit(requesting_agent_id, "view_project_context", 
              {"context_key": context_key_filter, "search_query": search_query_filter})
    
    conn = None
    results_list: List[Dict[str, Any]] = []
    response_message: str = ""

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        if context_key_filter: # main.py:1422-1433
            cursor.execute("SELECT value, description, updated_by, last_updated FROM project_context WHERE context_key = ?", 
                           (context_key_filter,))
            row = cursor.fetchone()
            if row:
                try:
                    value_parsed = json.loads(row["value"]) # Value is stored as JSON string
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse JSON value for context_key '{context_key_filter}'. Raw value: {row['value']}")
                    value_parsed = row["value"] # Return raw string if not parsable JSON

                results_list.append({
                    "key": context_key_filter,
                    "value": value_parsed,
                    "description": row["description"],
                    "updated_by": row["updated_by"],
                    "last_updated": row["last_updated"]
                })
                # Use json.dumps for consistent formatting in the output message
                response_message = f"Project Context for key '{context_key_filter}':\n\n{json.dumps(results_list[0], indent=2)}"
            else:
                response_message = f"Project context key '{context_key_filter}' not found."
        elif search_query_filter: # main.py:1434-1448
            like_pattern = f'%{search_query_filter}%'
            # Search in key, description, and the raw JSON value string
            cursor.execute("""
                SELECT context_key, value, description, updated_by, last_updated 
                FROM project_context 
                WHERE context_key LIKE ? OR description LIKE ? OR value LIKE ?
                ORDER BY last_updated DESC 
                LIMIT 50 
            """, (like_pattern, like_pattern, like_pattern)) # Limit results for broad searches
            
            rows = cursor.fetchall()
            if rows:
                for row_data in rows:
                    try:
                        value_parsed = json.loads(row_data["value"])
                    except json.JSONDecodeError:
                        value_parsed = row_data["value"]
                    results_list.append({
                        "key": row_data["context_key"],
                        "value": value_parsed,
                        "description": row_data["description"],
                        "updated_by": row_data["updated_by"],
                        "last_updated": row_data["last_updated"]
                    })
                response_message = f"Found {len(results_list)} project context entries matching '{search_query_filter}':\n\n{json.dumps(results_list, indent=2, ensure_ascii=False)}"
            else:
                response_message = f"No project context entries found matching search query '{search_query_filter}'."
        else: # Return all context (main.py:1450-1460) - limited for safety
            cursor.execute("SELECT context_key, value, description, updated_by, last_updated FROM project_context ORDER BY last_updated DESC LIMIT 200")
            rows = cursor.fetchall()
            if rows:
                for row_data in rows:
                    try:
                        value_parsed = json.loads(row_data["value"])
                    except json.JSONDecodeError:
                        value_parsed = row_data["value"]
                    results_list.append({
                        "key": row_data["context_key"],
                        "value": value_parsed,
                        "description": row_data["description"],
                        "updated_by": row_data["updated_by"],
                        "last_updated": row_data["last_updated"]
                    })
                response_message = f"Full Project Context ({len(results_list)} entries - potentially truncated at 200):\n\n{json.dumps(results_list, indent=2, ensure_ascii=False)}"
            else:
                response_message = "Project context is currently empty."

    except sqlite3.Error as e_sql:
        logger.error(f"Database error viewing project context: {e_sql}", exc_info=True) # main.py:1462
        response_message = f"Database error viewing project context: {e_sql}"
    except json.JSONDecodeError as e_json: # Should be caught per-item, but as a fallback
        logger.error(f"Error decoding JSON from project_context table during bulk view: {e_json}", exc_info=True) # main.py:1465
        response_message = f"Error decoding stored project context value(s)."
    except Exception as e:
        logger.error(f"Unexpected error viewing project context: {e}", exc_info=True)
        response_message = f"An unexpected error occurred: {e}"
    finally:
        if conn:
            conn.close()

    return [mcp_types.TextContent(type="text", text=response_message)]


# --- update_project_context tool ---
# Original logic from main.py: lines 1468-1500 (update_project_context_tool function)
async def update_project_context_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    auth_token = arguments.get("token")
    context_key_to_update = arguments.get("context_key")
    context_value_to_set = arguments.get("context_value") # This is Any, will be JSON serialized
    description_for_context = arguments.get("description") # Optional string

    # Modified: Allow any agent with a valid token, not just admin
    requesting_agent_id = get_agent_id(auth_token)
    if not requesting_agent_id:
        return [mcp_types.TextContent(type="text", text="Unauthorized: Valid token required")]
        
    if not context_key_to_update or context_value_to_set is None: # Value can be null, but not missing
        return [mcp_types.TextContent(type="text", text="Error: context_key and context_value are required.")]

    # Log audit (main.py:1477)
    log_audit(requesting_agent_id, "update_project_context", 
              {"context_key": context_key_to_update, "value_type": str(type(context_value_to_set)), "description": description_for_context})

    conn = None
    try:
        # Ensure value is JSON serializable before storing (main.py:1483-1486)
        value_json_str = json.dumps(context_value_to_set)
    except TypeError as e_type:
        logger.error(f"Value provided for project context key '{context_key_to_update}' is not JSON serializable: {e_type}")
        return [mcp_types.TextContent(type="text", text=f"Error: Provided context_value is not JSON serializable: {e_type}")]

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        updated_at_iso = datetime.datetime.now().isoformat()

        # Use INSERT OR REPLACE (UPSERT) (main.py:1489-1494)
        cursor.execute("""
            INSERT OR REPLACE INTO project_context (context_key, value, last_updated, updated_by, description)
            VALUES (?, ?, ?, ?, ?)
        """, (context_key_to_update, value_json_str, updated_at_iso, requesting_admin_id, description_for_context))
        
        # Log to agent_actions table
        log_agent_action_to_db(cursor, requesting_admin_id, "updated_context", 
                               details={'context_key': context_key_to_update, 'action': 'set/update'})
        conn.commit()
        
        logger.info(f"Project context for key '{context_key_to_update}' updated by '{requesting_admin_id}'.")
        return [mcp_types.TextContent(
            type="text",
            text=f"Project context updated successfully for key '{context_key_to_update}'."
        )]

    except sqlite3.Error as e_sql: # main.py:1495
        if conn: conn.rollback()
        logger.error(f"Database error updating project context for key '{context_key_to_update}': {e_sql}", exc_info=True)
        return [mcp_types.TextContent(type="text", text=f"Database error updating project context: {e_sql}")]
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Unexpected error updating project context for key '{context_key_to_update}': {e}", exc_info=True)
        return [mcp_types.TextContent(type="text", text=f"Unexpected error updating project context: {e}")]
    finally:
        if conn:
            conn.close()


# --- Register project context tools ---
def register_project_context_tools():
    register_tool(
        name="view_project_context", # main.py:1812
        description="View project context. Provide context_key for specific lookup OR search_query for keyword search across keys, descriptions, and values.",
        input_schema={ # From main.py:1813-1823
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "Authentication token"},
                "context_key": {"type": "string", "description": "Exact key to view (optional). If provided, search_query is ignored."},
                "search_query": {"type": "string", "description": "Keyword search query (optional). Searches keys, descriptions, and values."}
            },
            "required": ["token"], # Only token is required, filters are optional
            "additionalProperties": False
        },
        implementation=view_project_context_tool_impl
    )

    register_tool(
        name="update_project_context", # main.py:1825
        description="Add or update a project context entry with a specific key. The value can be any JSON-serializable type.",
        input_schema={ # From main.py:1826-1839
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "Authentication token (agent or admin)"},
                "context_key": {"type": "string", "description": "The exact key for the context entry (e.g., 'api.service_x.url')."},
                "context_value": {"type": "object", "description": "The JSON-serializable value to set (e.g., string, number, list, dict).", "additionalProperties": True}, # Allow any valid JSON as value
                "description": {"type": "string", "description": "Optional description of this context entry."}
            },
            "required": ["token", "context_key", "context_value"],
            "additionalProperties": False
        },
        implementation=update_project_context_tool_impl
    )

# Call registration when this module is imported
register_project_context_tools()