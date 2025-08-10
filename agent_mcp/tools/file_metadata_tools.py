# Agent-MCP/mcp_template/mcp_server_src/tools/file_metadata_tools.py
import json
import datetime
import sqlite3
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

import mcp.types as mcp_types

from .registry import register_tool
from ..core.config import logger
from ..core import globals as g  # For agent_working_dirs
from ..core.auth import get_agent_id, verify_token
from ..utils.audit_utils import log_audit
from ..db.connection import get_db_connection
from ..db.actions.agent_actions_db import log_agent_action_to_db


def _normalize_filepath(filepath_arg: str, agent_id_for_wd: Optional[str]) -> str:
    """
    Resolves a filepath to an absolute, normalized POSIX path.
    Uses the agent's working directory if the path is relative.
    """
    if not os.path.isabs(filepath_arg):
        working_dir = os.getcwd()  # Default to CWD if no agent context
        if agent_id_for_wd and agent_id_for_wd in g.agent_working_dirs:
            working_dir = g.agent_working_dirs[agent_id_for_wd]
        elif agent_id_for_wd:  # Agent ID provided but not in map
            logger.warning(
                f"Agent '{agent_id_for_wd}' not found in agent_working_dirs for path resolution. Using CWD."
            )

        resolved_path = Path(working_dir) / filepath_arg
    else:
        resolved_path = Path(filepath_arg)

    return (
        resolved_path.resolve().as_posix()
    )  # Resolve to absolute and normalize to POSIX


# --- view_file_metadata tool ---
# Original logic from main.py: lines 1503-1533 (view_file_metadata_tool function)
async def view_file_metadata_tool_impl(
    arguments: Dict[str, Any],
) -> List[mcp_types.TextContent]:
    agent_auth_token = arguments.get("token")
    filepath_arg = arguments.get("filepath")

    requesting_agent_id = get_agent_id(agent_auth_token)  # main.py:1506
    if not requesting_agent_id:
        return [
            mcp_types.TextContent(
                type="text", text="Unauthorized: Valid token required"
            )
        ]

    if not filepath_arg or not isinstance(filepath_arg, str):
        return [
            mcp_types.TextContent(
                type="text", text="Error: filepath is required and must be a string."
            )
        ]

    # Resolve and normalize path (main.py:1509-1515)
    normalized_filepath_str = _normalize_filepath(filepath_arg, requesting_agent_id)

    # Log audit (main.py:1517)
    log_audit(
        requesting_agent_id,
        "view_file_metadata",
        {"filepath_normalized": normalized_filepath_str, "original_path": filepath_arg},
    )

    conn = None
    response_message: str = ""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # main.py:1521
        cursor.execute(
            "SELECT metadata, updated_by, last_updated, content_hash FROM file_metadata WHERE filepath = ?",
            (normalized_filepath_str,),
        )
        row = cursor.fetchone()
        if row:  # main.py:1523-1525
            try:
                metadata_parsed = json.loads(
                    row["metadata"]
                )  # Metadata is stored as JSON string
            except json.JSONDecodeError:
                logger.warning(
                    f"Failed to parse JSON metadata for file '{normalized_filepath_str}'. Raw: {row['metadata']}"
                )
                metadata_parsed = {
                    "error": "Could not parse stored metadata string.",
                    "raw_value": row["metadata"],
                }

            response_data = {
                "filepath": normalized_filepath_str,
                "metadata": metadata_parsed,
                "last_updated_by": row["updated_by"],
                "last_updated_at": row["last_updated"],
                "content_hash": (
                    row["content_hash"] if "content_hash" in row.keys() else "N/A"
                ),  # content_hash was added later
            }
            response_message = f"Metadata for file '{filepath_arg}' (normalized: {normalized_filepath_str}):\n\n{json.dumps(response_data, indent=2, ensure_ascii=False)}"
        else:  # main.py:1527
            response_message = f"No metadata found for file '{filepath_arg}' (normalized: {normalized_filepath_str})."

    except sqlite3.Error as e_sql:  # main.py:1529
        logger.error(
            f"Database error viewing file metadata for '{normalized_filepath_str}': {e_sql}",
            exc_info=True,
        )
        response_message = f"Database error viewing file metadata: {e_sql}"
    except (
        json.JSONDecodeError
    ) as e_json:  # Should be caught per-item, but as fallback (main.py:1532)
        logger.error(
            f"Error decoding JSON from file_metadata table for '{normalized_filepath_str}': {e_json}",
            exc_info=True,
        )
        response_message = f"Error decoding stored file metadata."
    except Exception as e:
        logger.error(
            f"Unexpected error viewing file metadata for '{normalized_filepath_str}': {e}",
            exc_info=True,
        )
        response_message = f"An unexpected error occurred: {e}"
    finally:
        if conn:
            conn.close()

    return [mcp_types.TextContent(type="text", text=response_message)]


# --- update_file_metadata tool ---
# Original logic from main.py: lines 1536-1569 (update_file_metadata_tool function)
async def update_file_metadata_tool_impl(
    arguments: Dict[str, Any],
) -> List[mcp_types.TextContent]:
    admin_auth_token = arguments.get("token")
    filepath_arg = arguments.get("filepath")
    metadata_to_set = arguments.get("metadata")  # This is a Dict[str, Any]

    if not verify_token(
        admin_auth_token, "admin"
    ):  # main.py:1539 (Restricted to admin)
        return [
            mcp_types.TextContent(
                type="text",
                text="Unauthorized: Admin token required for updating file metadata.",
            )
        ]

    requesting_admin_id = get_agent_id(admin_auth_token)  # main.py:1542
    if not requesting_admin_id:  # Should be "admin"
        logger.error(
            "Admin token verified but could not get admin_id. This is unexpected."
        )
        return [
            mcp_types.TextContent(type="text", text="Internal authorization error.")
        ]

    if (
        not filepath_arg
        or not isinstance(filepath_arg, str)
        or metadata_to_set is None
        or not isinstance(metadata_to_set, dict)
    ):
        return [
            mcp_types.TextContent(
                type="text",
                text="Error: filepath (string) and metadata (dictionary) are required.",
            )
        ]

    # Resolve and normalize path (main.py:1545-1549)
    normalized_filepath_str = _normalize_filepath(
        filepath_arg, requesting_admin_id
    )  # Use admin's context for WD if needed

    # Log audit (main.py:1551)
    log_audit(
        requesting_admin_id,
        "update_file_metadata",
        {
            "filepath_normalized": normalized_filepath_str,
            "original_path": filepath_arg,
            "metadata_keys": list(metadata_to_set.keys()),
        },
    )

    conn = None
    try:
        # Ensure metadata is JSON serializable (main.py:1555-1558)
        metadata_json_str = json.dumps(metadata_to_set)
    except TypeError as e_type:
        logger.error(
            f"Metadata provided for file '{normalized_filepath_str}' is not JSON serializable: {e_type}"
        )
        return [
            mcp_types.TextContent(
                type="text",
                text=f"Error: Provided metadata is not JSON serializable: {e_type}",
            )
        ]

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        updated_at_iso = datetime.datetime.now().isoformat()

        # The original did not explicitly handle content_hash here.
        # If metadata updates should also update/clear content_hash, that logic would be added.
        # For now, it only updates metadata, last_updated, updated_by.
        # (main.py:1561-1565)
        cursor.execute(
            """
            INSERT OR REPLACE INTO file_metadata (filepath, metadata, last_updated, updated_by)
            VALUES (?, ?, ?, ?)
        """,
            (
                normalized_filepath_str,
                metadata_json_str,
                updated_at_iso,
                requesting_admin_id,
            ),
        )

        log_agent_action_to_db(
            cursor,
            requesting_admin_id,
            "updated_file_metadata",
            details={"filepath": normalized_filepath_str, "action": "set/update"},
        )
        conn.commit()

        logger.info(
            f"File metadata for '{normalized_filepath_str}' updated by '{requesting_admin_id}'."
        )
        return [
            mcp_types.TextContent(
                type="text",
                text=f"File metadata updated successfully for '{filepath_arg}' (normalized: {normalized_filepath_str}).",
            )
        ]

    except sqlite3.Error as e_sql:  # main.py:1566
        if conn:
            conn.rollback()
        logger.error(
            f"Database error updating file metadata for '{normalized_filepath_str}': {e_sql}",
            exc_info=True,
        )
        return [
            mcp_types.TextContent(
                type="text", text=f"Database error updating file metadata: {e_sql}"
            )
        ]
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(
            f"Unexpected error updating file metadata for '{normalized_filepath_str}': {e}",
            exc_info=True,
        )
        return [
            mcp_types.TextContent(
                type="text", text=f"Unexpected error updating file metadata: {e}"
            )
        ]
    finally:
        if conn:
            conn.close()


# --- Register file metadata tools ---
def register_file_metadata_tools():
    register_tool(
        name="view_file_metadata",  # main.py:1841 (schema name)
        description="View stored metadata (e.g., purpose, components) for a specific file path.",
        input_schema={  # From main.py:1842-1852
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "Authentication token"},
                "filepath": {
                    "type": "string",
                    "description": "Path to the file (can be relative to agent's CWD or absolute)",
                },
            },
            "required": ["token", "filepath"],
            "additionalProperties": False,
        },
        implementation=view_file_metadata_tool_impl,
    )

    register_tool(
        name="update_file_metadata",  # main.py:1854 (schema name)
        description="Add or replace the entire metadata object for a specific file path. Admin only.",
        input_schema={  # From main.py:1855-1867
            "type": "object",
            "properties": {
                "token": {
                    "type": "string",
                    "description": "Admin authentication token",
                },
                "filepath": {
                    "type": "string",
                    "description": "Path to the file (can be relative or absolute)",
                },
                "metadata": {
                    "type": "object",
                    "description": "A JSON object containing the metadata to set for the file.",
                },
            },
            "required": ["token", "filepath", "metadata"],
            "additionalProperties": False,
        },
        implementation=update_file_metadata_tool_impl,
    )


# Call registration when this module is imported
register_file_metadata_tools()
