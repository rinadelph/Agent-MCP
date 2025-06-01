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
    
    # Support both single and bulk operations
    context_key_to_update = arguments.get("context_key")
    context_value_to_set = arguments.get("context_value")
    description_for_context = arguments.get("description")
    updates_list = arguments.get("updates")  # For bulk operations
    
    requesting_agent_id = get_agent_id(auth_token)
    if not requesting_agent_id:
        return [mcp_types.TextContent(type="text", text="Unauthorized: Valid token required")]
    
    # Determine operation mode
    is_bulk_operation = updates_list is not None
    
    if is_bulk_operation:
        if not isinstance(updates_list, list) or len(updates_list) == 0:
            return [mcp_types.TextContent(type="text", text="Error: updates must be a non-empty list for bulk operations.")]
        return await _handle_bulk_context_update(requesting_agent_id, updates_list)
    else:
        # Single operation (backward compatibility)
        if not context_key_to_update or context_value_to_set is None:
            return [mcp_types.TextContent(type="text", text="Error: context_key and context_value are required for single updates.")]
        return await _handle_single_context_update(requesting_agent_id, context_key_to_update, context_value_to_set, description_for_context)

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
        """, (context_key_to_update, value_json_str, updated_at_iso, requesting_agent_id, description_for_context))
        
        # Log to agent_actions table
        log_agent_action_to_db(cursor, requesting_agent_id, "updated_context", 
                               details={'context_key': context_key_to_update, 'action': 'set/update'})
        conn.commit()
        
        logger.info(f"Project context for key '{context_key_to_update}' updated by '{requesting_agent_id}'.")
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


# --- bulk_update_project_context tool ---
async def bulk_update_project_context_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    auth_token = arguments.get("token")
    updates = arguments.get("updates", [])  # List of update operations

    requesting_agent_id = get_agent_id(auth_token)
    if not requesting_agent_id:
        return [mcp_types.TextContent(type="text", text="Unauthorized: Valid token required")]
        
    if not updates or not isinstance(updates, list):
        return [mcp_types.TextContent(type="text", text="Error: updates array is required.")]

    # Validate each update operation
    for i, update in enumerate(updates):
        if not isinstance(update, dict):
            return [mcp_types.TextContent(type="text", text=f"Error: Update {i} must be an object.")]
        if "context_key" not in update:
            return [mcp_types.TextContent(type="text", text=f"Error: Update {i} missing required 'context_key'.")]
        if "context_value" not in update:
            return [mcp_types.TextContent(type="text", text=f"Error: Update {i} missing required 'context_value'.")]

    # Log audit
    log_audit(requesting_agent_id, "bulk_update_project_context", 
              {"update_count": len(updates)})

    conn = None
    results = []
    failed_updates = []
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        updated_at_iso = datetime.datetime.now().isoformat()

        # Process each update atomically
        for i, update in enumerate(updates):
            try:
                context_key = update["context_key"]
                context_value = update["context_value"]
                description = update.get("description", f"Bulk update operation {i+1}")
                
                # Validate JSON serialization
                value_json_str = json.dumps(context_value)
                
                # Execute update
                cursor.execute("""
                    INSERT OR REPLACE INTO project_context (context_key, value, last_updated, updated_by, description)
                    VALUES (?, ?, ?, ?, ?)
                """, (context_key, value_json_str, updated_at_iso, requesting_agent_id, description))
                
                results.append(f"✓ Updated '{context_key}'")
                
                # Log individual action
                log_agent_action_to_db(cursor, requesting_agent_id, "bulk_updated_context", 
                                       details={'context_key': context_key, 'operation': f'bulk_update_{i+1}'})
                
            except (TypeError, json.JSONEncodeError) as e_json:
                failed_updates.append(f"✗ Failed '{update.get('context_key', 'unknown')}': Invalid JSON - {e_json}")
            except Exception as e_update:
                failed_updates.append(f"✗ Failed '{update.get('context_key', 'unknown')}': {str(e_update)}")

        conn.commit()
        
        # Build response
        response_parts = [f"Bulk update completed: {len(results)} successful, {len(failed_updates)} failed"]
        
        if results:
            response_parts.append("\nSuccessful updates:")
            response_parts.extend(results)
            
        if failed_updates:
            response_parts.append("\nFailed updates:")
            response_parts.extend(failed_updates)
        
        logger.info(f"Bulk context update by '{requesting_agent_id}': {len(results)} successful, {len(failed_updates)} failed.")
        return [mcp_types.TextContent(type="text", text="\n".join(response_parts))]

    except sqlite3.Error as e_sql:
        if conn: conn.rollback()
        logger.error(f"Database error in bulk context update: {e_sql}", exc_info=True)
        return [mcp_types.TextContent(type="text", text=f"Database error in bulk update: {e_sql}")]
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Unexpected error in bulk context update: {e}", exc_info=True)
        return [mcp_types.TextContent(type="text", text=f"Unexpected error in bulk update: {e}")]
    finally:
        if conn:
            conn.close()


# --- validate_context_consistency tool ---
async def validate_context_consistency_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    auth_token = arguments.get("token")

    requesting_agent_id = get_agent_id(auth_token)
    if not requesting_agent_id:
        return [mcp_types.TextContent(type="text", text="Unauthorized: Valid token required")]

    # Log audit
    log_audit(requesting_agent_id, "validate_context_consistency", {})

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        issues = []
        warnings = []
        
        # Get all context entries
        cursor.execute("SELECT context_key, value, description, updated_by, last_updated FROM project_context ORDER BY context_key")
        all_entries = [dict(row) for row in cursor.fetchall()]
        
        if not all_entries:
            return [mcp_types.TextContent(type="text", text="No project context entries found.")]

        # Check 1: Invalid JSON values
        for entry in all_entries:
            try:
                json.loads(entry["value"])
            except json.JSONDecodeError as e:
                issues.append(f"Invalid JSON in '{entry['context_key']}': {e}")

        # Check 2: Duplicate or conflicting keys (case-insensitive)
        key_map = {}
        for entry in all_entries:
            key_lower = entry["context_key"].lower()
            if key_lower in key_map:
                issues.append(f"Potential duplicate keys: '{key_map[key_lower]}' and '{entry['context_key']}'")
            else:
                key_map[key_lower] = entry["context_key"]

        # Check 3: Missing descriptions
        missing_desc = [entry["context_key"] for entry in all_entries if not entry.get("description")]
        if missing_desc:
            warnings.extend([f"Missing description: '{key}'" for key in missing_desc[:10]])
            if len(missing_desc) > 10:
                warnings.append(f"... and {len(missing_desc) - 10} more missing descriptions")

        # Check 4: Very old entries (potential staleness)
        import datetime as dt
        cutoff_date = (dt.datetime.now() - dt.timedelta(days=30)).isoformat()
        old_entries = [entry["context_key"] for entry in all_entries 
                      if entry["last_updated"] < cutoff_date]
        if old_entries:
            warnings.extend([f"Old entry (>30 days): '{key}'" for key in old_entries[:5]])
            if len(old_entries) > 5:
                warnings.append(f"... and {len(old_entries) - 5} more old entries")

        # Check 5: Unusually large values (potential bloat)
        large_entries = []
        for entry in all_entries:
            if len(entry["value"]) > 10000:  # 10KB threshold
                large_entries.append(f"{entry['context_key']} ({len(entry['value'])} chars)")
        if large_entries:
            warnings.extend([f"Large entry: {entry}" for entry in large_entries[:5]])
            if len(large_entries) > 5:
                warnings.append(f"... and {len(large_entries) - 5} more large entries")

        # Build response
        response_parts = [f"Context Consistency Validation Results"]
        response_parts.append(f"Total entries: {len(all_entries)}")
        
        if not issues and not warnings:
            response_parts.append("\n✅ No issues found! Context appears consistent.")
        else:
            if issues:
                response_parts.append(f"\n🚨 Critical Issues ({len(issues)}):")
                response_parts.extend([f"  {issue}" for issue in issues])
            
            if warnings:
                response_parts.append(f"\n⚠️  Warnings ({len(warnings)}):")
                response_parts.extend([f"  {warning}" for warning in warnings])
                
            response_parts.append("\nRecommendations:")
            if issues:
                response_parts.append("- Fix critical issues immediately")
                response_parts.append("- Use bulk_update_project_context for corrections")
            if warnings:
                response_parts.append("- Review warnings for potential cleanup")
                response_parts.append("- Consider using delete_project_context for unused entries")

        return [mcp_types.TextContent(type="text", text="\n".join(response_parts))]

    except sqlite3.Error as e_sql:
        logger.error(f"Database error validating context consistency: {e_sql}", exc_info=True)
        return [mcp_types.TextContent(type="text", text=f"Database error validating context: {e_sql}")]
    except Exception as e:
        logger.error(f"Unexpected error validating context consistency: {e}", exc_info=True)
        return [mcp_types.TextContent(type="text", text=f"Unexpected error validating context: {e}")]
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

    register_tool(
        name="bulk_update_project_context",
        description="Update multiple project context entries atomically. Essential for large-scale context corrections.",
        input_schema={
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "Authentication token"},
                "updates": {
                    "type": "array",
                    "description": "Array of update operations",
                    "items": {
                        "type": "object",
                        "properties": {
                            "context_key": {"type": "string", "description": "The context key to update"},
                            "context_value": {"description": "The new value (any JSON-serializable type)"},
                            "description": {"type": "string", "description": "Optional description for this update"}
                        },
                        "required": ["context_key", "context_value"],
                        "additionalProperties": False
                    }
                }
            },
            "required": ["token", "updates"],
            "additionalProperties": False
        },
        implementation=bulk_update_project_context_tool_impl
    )

    register_tool(
        name="validate_context_consistency",
        description="Check for inconsistencies, conflicts, and quality issues in project context. Critical for preventing context poisoning.",
        input_schema={
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "Authentication token"}
            },
            "required": ["token"],
            "additionalProperties": False
        },
        implementation=validate_context_consistency_tool_impl
    )

# Call registration when this module is imported
register_project_context_tools()