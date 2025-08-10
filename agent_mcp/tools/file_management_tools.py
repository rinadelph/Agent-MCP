# Agent-MCP/mcp_template/mcp_server_src/tools/file_management_tools.py
import os
import datetime
from typing import List, Dict, Any

import mcp.types as mcp_types # Assuming this is your mcp.types path

from .registry import register_tool
from ..core.config import logger
from ..core import globals as g
from ..core.auth import get_agent_id # verify_token not strictly needed here if get_agent_id implies valid token
from ..utils.audit_utils import log_audit
# No DB interactions for these specific tools as they manage in-memory state (g.file_map)

# --- check_file_status tool ---
# Original logic from main.py: lines 1774-1801 (check_file_status_tool function)
async def check_file_status_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    agent_auth_token = arguments.get("token")
    filepath_arg = arguments.get("filepath")

    requesting_agent_id = get_agent_id(agent_auth_token) # main.py:1777
    if not requesting_agent_id:
        return [mcp_types.TextContent(type="text", text="Unauthorized: Valid token required")]

    if not filepath_arg or not isinstance(filepath_arg, str):
        return [mcp_types.TextContent(type="text", text="Error: filepath is required and must be a string.")]

    # Resolve the filepath to absolute path (main.py:1781-1785)
    # This uses the agent's working directory from g.agent_working_dirs
    if not os.path.isabs(filepath_arg):
        agent_wd = g.agent_working_dirs.get(requesting_agent_id)
        if not agent_wd:
            # This case should ideally not happen if agent is properly initialized
            logger.warning(f"Agent '{requesting_agent_id}' has no working directory set in g.agent_working_dirs. Using current server CWD as fallback for path resolution.")
            agent_wd = os.getcwd() 
        resolved_abs_filepath = os.path.abspath(os.path.join(agent_wd, filepath_arg))
    else:
        resolved_abs_filepath = os.path.abspath(filepath_arg)
    
    # Log the file status check (main.py:1788)
    log_audit(requesting_agent_id, "check_file_status", {"filepath": resolved_abs_filepath, "original_path": filepath_arg})
    
    # Check if file is in the file map (main.py:1791-1799)
    if resolved_abs_filepath in g.file_map:
        file_info = g.file_map[resolved_abs_filepath]
        status_message: str
        if file_info.get("agent_id") == requesting_agent_id:
            status_message = (
                f"File '{filepath_arg}' (resolved: {resolved_abs_filepath}) is currently "
                f"being used by YOU ({requesting_agent_id}) since {file_info.get('timestamp', 'N/A')}. "
                f"Status: {file_info.get('status', 'unknown')}"
            )
        else:
            status_message = (
                f"File '{filepath_arg}' (resolved: {resolved_abs_filepath}) is currently "
                f"being used by agent '{file_info.get('agent_id', 'unknown')}' "
                f"since {file_info.get('timestamp', 'N/A')}. Status: {file_info.get('status', 'unknown')}"
            )
        return [mcp_types.TextContent(type="text", text=status_message)]
    else:
        return [mcp_types.TextContent(
            type="text",
            text=f"File '{filepath_arg}' (resolved: {resolved_abs_filepath}) is not currently being used by any agent according to the file map."
        )]

# --- update_file_status tool ---
# Original logic from main.py: lines 1804-1849 (update_file_status_tool function)
async def update_file_status_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    agent_auth_token = arguments.get("token")
    filepath_arg = arguments.get("filepath")
    new_status = arguments.get("status") # e.g., "editing", "reading", "released"

    requesting_agent_id = get_agent_id(agent_auth_token) # main.py:1808
    if not requesting_agent_id:
        return [mcp_types.TextContent(type="text", text="Unauthorized: Valid token required")]

    if not filepath_arg or not isinstance(filepath_arg, str) or \
       not new_status or not isinstance(new_status, str):
        return [mcp_types.TextContent(type="text", text="Error: filepath and status are required and must be strings.")]

    # Resolve the filepath to absolute path (main.py:1812-1816)
    if not os.path.isabs(filepath_arg):
        agent_wd = g.agent_working_dirs.get(requesting_agent_id)
        if not agent_wd:
            logger.warning(f"Agent '{requesting_agent_id}' has no working directory set. Using CWD for path resolution.")
            agent_wd = os.getcwd()
        resolved_abs_filepath = os.path.abspath(os.path.join(agent_wd, filepath_arg))
    else:
        resolved_abs_filepath = os.path.abspath(filepath_arg)

    # Validate status (main.py:1819-1823)
    valid_statuses = ["editing", "reading", "reviewing", "released"]
    if new_status not in valid_statuses:
        return [mcp_types.TextContent(
            type="text",
            text=f"Invalid status: '{new_status}'. Must be one of: {', '.join(valid_statuses)}"
        )]

    # Check if file is already in use by another agent (main.py:1826-1831)
    if resolved_abs_filepath in g.file_map and \
       g.file_map[resolved_abs_filepath].get("agent_id") != requesting_agent_id and \
       new_status != "released": # Can always release, even if map is out of sync.
        current_holder_agent_id = g.file_map[resolved_abs_filepath].get("agent_id", "another agent")
        return [mcp_types.TextContent(
            type="text",
            text=f"File '{filepath_arg}' (resolved: {resolved_abs_filepath}) is already being used by agent '{current_holder_agent_id}'. Cannot claim it with status '{new_status}'."
        )]

    # Update the file map (g.file_map)
    if new_status == "released": # main.py:1834-1841
        if resolved_abs_filepath in g.file_map:
            # Only the agent holding the file or an admin should ideally release it.
            # The original code allowed any agent to release if they knew the path and it was in file_map.
            # For 1-to-1, we keep this behavior. A stricter check would be:
            # if g.file_map[resolved_abs_filepath].get("agent_id") == requesting_agent_id or verify_token(agent_auth_token, "admin"):
            del g.file_map[resolved_abs_filepath]
            log_audit(requesting_agent_id, "release_file", {"filepath": resolved_abs_filepath, "original_path": filepath_arg})
            logger.info(f"Agent '{requesting_agent_id}' released file '{resolved_abs_filepath}'.")
            return [mcp_types.TextContent(type="text", text=f"File '{filepath_arg}' (resolved: {resolved_abs_filepath}) has been released.")]
        else:
            # File was not in map, so it's already considered released from map's perspective.
            log_audit(requesting_agent_id, "attempt_release_unmapped_file", {"filepath": resolved_abs_filepath, "original_path": filepath_arg})
            return [mcp_types.TextContent(
                type="text",
                text=f"File '{filepath_arg}' (resolved: {resolved_abs_filepath}) was not found in the active file map (already considered released or never tracked)."
            )]
    else: # For "editing", "reading", "reviewing" (main.py:1842-1847)
        g.file_map[resolved_abs_filepath] = {
            "agent_id": requesting_agent_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "status": new_status
        }
        log_audit(requesting_agent_id, f"claim_file_{new_status}", {"filepath": resolved_abs_filepath, "original_path": filepath_arg})
        logger.info(f"Agent '{requesting_agent_id}' updated file '{resolved_abs_filepath}' status to '{new_status}'.")
        return [mcp_types.TextContent(
            type="text",
            text=f"File '{filepath_arg}' (resolved: {resolved_abs_filepath}) is now registered to agent '{requesting_agent_id}' with status '{new_status}'."
        )]

# --- Register file management tools ---
def register_file_management_tools():
    register_tool(
        name="check_file_status", # main.py:1825
        description="Check if a file is currently being used by another agent, based on the server's in-memory file map.",
        input_schema={ # From main.py:1826-1839
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "Agent authentication token"},
                "filepath": {"type": "string", "description": "Path to the file to check (can be relative to agent's CWD or absolute)"}
            },
            "required": ["token", "filepath"],
            "additionalProperties": False
        },
        implementation=check_file_status_tool_impl
    )

    register_tool(
        name="update_file_status", # main.py:1841
        description="Update the status of a file in the server's in-memory map (e.g., claim for editing, reading, or release it).",
        input_schema={ # From main.py:1842-1858
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "Agent authentication token"},
                "filepath": {"type": "string", "description": "Path to the file to update (can be relative or absolute)"},
                "status": {
                    "type": "string",
                    "description": "New status for the file.",
                    "enum": ["editing", "reading", "reviewing", "released"]
                }
            },
            "required": ["token", "filepath", "status"],
            "additionalProperties": False
        },
        implementation=update_file_status_tool_impl
    )

# Call registration when this module is imported
register_file_management_tools()