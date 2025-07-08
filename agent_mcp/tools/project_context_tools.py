# Agent-MCP/mcp_template/mcp_server_src/tools/project_context_tools.py
import json
import datetime
import sqlite3
from typing import List, Dict, Any, Optional

import mcp.types as mcp_types

from .registry import register_tool
from ..core.config import logger
from ..core import globals as g  # Not directly used here, but auth uses it
from ..core.auth import get_agent_id, verify_token
from ..utils.audit_utils import log_audit
from ..db.connection import get_db_connection, execute_db_write
from ..db.actions.agent_actions_db import log_agent_action_to_db


def _analyze_context_health(context_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze project context health and identify issues"""
    if not context_entries:
        return {"status": "no_data", "total": 0}

    total = len(context_entries)
    issues = []
    warnings = []
    stale_count = 0
    json_errors = 0
    large_entries = 0
    current_time = datetime.datetime.now()

    for entry in context_entries:
        context_key = entry.get("context_key", "unknown")
        value = entry.get("value", "")
        last_updated = entry.get("last_updated")

        # Check for JSON parsing issues
        try:
            if isinstance(value, str):
                json.loads(value)
        except json.JSONDecodeError:
            json_errors += 1
            issues.append(f"JSON parse error in '{context_key}'")

        # Check for stale entries (30+ days old)
        if last_updated:
            try:
                updated_time = datetime.datetime.fromisoformat(
                    last_updated.replace("Z", "+00:00").replace("+00:00", "")
                )
                days_old = (current_time - updated_time).days
                if days_old > 30:
                    stale_count += 1
                    if days_old > 90:
                        warnings.append(f"'{context_key}' is {days_old} days old")
            except:
                warnings.append(f"Invalid timestamp for '{context_key}'")

        # Check for oversized entries (>10KB)
        entry_size = len(str(value))
        if entry_size > 10240:  # 10KB
            large_entries += 1
            warnings.append(f"'{context_key}' is large ({entry_size//1024}KB)")

    # Calculate health score
    stale_ratio = stale_count / total
    error_ratio = json_errors / total
    large_ratio = large_entries / total

    health_score = max(
        0, min(100, 100 - (stale_ratio * 40) - (error_ratio * 50) - (large_ratio * 10))
    )

    health_status = (
        "excellent"
        if health_score >= 90
        else (
            "good"
            if health_score >= 70
            else "needs_attention" if health_score >= 50 else "critical"
        )
    )

    return {
        "status": health_status,
        "health_score": round(health_score, 1),
        "total": total,
        "stale_entries": stale_count,
        "json_errors": json_errors,
        "large_entries": large_entries,
        "issues": issues[:5],  # Limit to first 5
        "warnings": warnings[:5],  # Limit to first 5
        "recommendations": _generate_context_recommendations(
            stale_count, json_errors, large_entries, total
        ),
    }


def _generate_context_recommendations(
    stale_count: int, json_errors: int, large_entries: int, total: int
) -> List[str]:
    """Generate actionable recommendations based on context health"""
    recommendations = []

    if json_errors > 0:
        recommendations.append(
            f"Fix {json_errors} JSON parsing errors using validate_context_consistency"
        )

    if stale_count > total * 0.3:  # More than 30% stale
        recommendations.append(
            f"Review and update {stale_count} stale entries (30+ days old)"
        )

    if large_entries > 0:
        recommendations.append(
            f"Consider breaking down {large_entries} large entries into smaller components"
        )

    if total > 100:
        recommendations.append(
            "Consider archiving old context entries to improve performance"
        )

    if not recommendations:
        recommendations.append(
            "Context health is excellent - no immediate action required"
        )

    return recommendations


def _create_context_backup(cursor, backup_name: str = None) -> Dict[str, Any]:
    """Create a backup of all project context data"""
    if not backup_name:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"context_backup_{timestamp}"

    # Fetch all context data
    cursor.execute("SELECT * FROM project_context ORDER BY context_key")
    all_entries = cursor.fetchall()

    backup_data = {
        "backup_name": backup_name,
        "created_at": datetime.datetime.now().isoformat(),
        "total_entries": len(all_entries),
        "entries": [dict(row) for row in all_entries],
    }

    return backup_data


# --- view_project_context tool ---
# Original logic from main.py: lines 1411-1465 (view_project_context_tool function)
async def view_project_context_tool_impl(
    arguments: Dict[str, Any],
) -> List[mcp_types.TextContent]:
    agent_auth_token = arguments.get("token")
    context_key_filter = arguments.get("context_key")  # Optional specific key
    search_query_filter = arguments.get("search_query")  # Optional search query

    # Smart features
    show_health_analysis = arguments.get("show_health_analysis", False)
    show_stale_entries = arguments.get(
        "show_stale_entries", False
    )  # Show entries older than 30 days
    include_backup_info = arguments.get(
        "include_backup_info", False
    )  # Include backup status
    max_results = arguments.get("max_results", 50)  # Limit results
    sort_by = arguments.get(
        "sort_by", "last_updated"
    )  # Sort by: key, last_updated, size

    requesting_agent_id = get_agent_id(agent_auth_token)  # main.py:1414
    if not requesting_agent_id:
        return [
            mcp_types.TextContent(
                type="text", text="Unauthorized: Valid token required"
            )
        ]

    # Log audit (main.py:1417)
    log_audit(
        requesting_agent_id,
        "view_project_context",
        {"context_key": context_key_filter, "search_query": search_query_filter},
    )

    conn = None
    results_list: List[Dict[str, Any]] = []
    response_message: str = ""

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Build smart query based on filters
        where_conditions = []
        query_params = []

        if context_key_filter:
            where_conditions.append("context_key = ?")
            query_params.append(context_key_filter)
        elif search_query_filter:
            like_pattern = f"%{search_query_filter}%"
            where_conditions.append(
                "(context_key LIKE ? OR description LIKE ? OR value LIKE ?)"
            )
            query_params.extend([like_pattern, like_pattern, like_pattern])

        if show_stale_entries:
            # Show entries older than 30 days
            thirty_days_ago = (
                datetime.datetime.now() - datetime.timedelta(days=30)
            ).isoformat()
            where_conditions.append("last_updated < ?")
            query_params.append(thirty_days_ago)

        # Build query with smart sorting
        base_query = "SELECT context_key, value, description, updated_by, last_updated, LENGTH(value) as value_size FROM project_context"

        if where_conditions:
            base_query += " WHERE " + " AND ".join(where_conditions)

        # Smart sorting
        if sort_by == "size":
            base_query += " ORDER BY LENGTH(value) DESC"
        elif sort_by == "key":
            base_query += " ORDER BY context_key ASC"
        else:  # last_updated (default)
            base_query += " ORDER BY last_updated DESC"

        base_query += f" LIMIT {max_results}"

        cursor.execute(base_query, query_params)
        rows = cursor.fetchall()

        # Process results with enhanced information
        for row_data in rows:
            try:
                value_parsed = json.loads(row_data["value"])
                json_valid = True
            except json.JSONDecodeError:
                value_parsed = row_data["value"]
                json_valid = False

            # Calculate additional metadata
            entry_size = len(str(row_data["value"]))
            last_updated = row_data["last_updated"]
            days_old = None

            if last_updated:
                try:
                    updated_time = datetime.datetime.fromisoformat(
                        last_updated.replace("Z", "+00:00").replace("+00:00", "")
                    )
                    days_old = (datetime.datetime.now() - updated_time).days
                except:
                    pass

            entry_data = {
                "key": row_data["context_key"],
                "value": value_parsed,
                "description": row_data["description"],
                "updated_by": row_data["updated_by"],
                "last_updated": last_updated,
                "_metadata": {
                    "size_bytes": entry_size,
                    "size_kb": round(entry_size / 1024, 2),
                    "json_valid": json_valid,
                    "days_old": days_old,
                    "is_stale": days_old and days_old > 30,
                    "is_large": entry_size > 10240,  # >10KB
                },
            }
            results_list.append(entry_data)

        # Generate smart response
        if not results_list:
            response_message = "No project context entries found matching the criteria."
        else:
            # Build header with filter information
            filter_info = []
            if context_key_filter:
                filter_info.append(f"key='{context_key_filter}'")
            if search_query_filter:
                filter_info.append(f"search='{search_query_filter}'")
            if show_stale_entries:
                filter_info.append("stale_only=true")

            header = f"Project Context ({len(results_list)} entries"
            if filter_info:
                header += f", filtered by: {', '.join(filter_info)}"
            header += f", sorted by: {sort_by})"

            response_parts = [header + "\n"]

            # Add health analysis if requested
            if show_health_analysis:
                # Fetch all entries for comprehensive health analysis
                cursor.execute(
                    "SELECT context_key, value, last_updated FROM project_context"
                )
                all_entries = [dict(row) for row in cursor.fetchall()]
                health_analysis = _analyze_context_health(all_entries)

                health_status = health_analysis["status"]
                health_score = health_analysis["health_score"]

                health_icon = (
                    "🟢"
                    if health_status == "excellent"
                    else (
                        "🟡"
                        if health_status == "good"
                        else "🟠" if health_status == "needs_attention" else "🔴"
                    )
                )

                response_parts.append(
                    f"📊 **Context Health:** {health_icon} {health_status.title()} ({health_score}/100)"
                )
                response_parts.append(f"   Total: {health_analysis['total']} entries")
                response_parts.append(
                    f"   Issues: {health_analysis['json_errors']} JSON errors, {health_analysis['stale_entries']} stale, {health_analysis['large_entries']} large"
                )

                if health_analysis["recommendations"]:
                    response_parts.append(
                        f"   💡 {health_analysis['recommendations'][0]}"
                    )
                response_parts.append("")

            # Add backup info if requested
            if include_backup_info:
                response_parts.append(
                    "💾 **Backup Info:** Use bulk_update_project_context for backups"
                )
                response_parts.append("")

            # Format entries
            for i, entry in enumerate(results_list[:20]):  # Limit display to 20 entries
                metadata = entry.get("_metadata", {})

                # Entry header with smart indicators
                indicators = []
                if not metadata.get("json_valid", True):
                    indicators.append("❌ JSON_ERROR")
                if metadata.get("is_stale", False):
                    indicators.append(f"⏰ STALE({metadata.get('days_old')}d)")
                if metadata.get("is_large", False):
                    indicators.append(f"📦 LARGE({metadata.get('size_kb')}KB)")

                indicator_text = " " + " ".join(indicators) if indicators else ""

                response_parts.append(f"**{entry['key']}**{indicator_text}")
                response_parts.append(
                    f"  Description: {entry.get('description', 'No description')}"
                )
                response_parts.append(
                    f"  Updated: {entry.get('last_updated', 'Unknown')} by {entry.get('updated_by', 'Unknown')}"
                )

                # Show value preview (truncated for large values)
                value_str = (
                    json.dumps(entry["value"], indent=2)
                    if isinstance(entry["value"], (dict, list))
                    else str(entry["value"])
                )
                if len(value_str) > 500:
                    value_str = value_str[:500] + "... [TRUNCATED]"
                response_parts.append(f"  Value: {value_str}")
                response_parts.append("")

            if len(results_list) > 20:
                response_parts.append(f"... and {len(results_list) - 20} more entries")
                response_parts.append(
                    "Use max_results parameter to see more, or add filters to narrow results"
                )

            # Add smart usage tips
            response_parts.append("\n💡 Smart Tips:")
            if not show_health_analysis:
                response_parts.append(
                    "• Add show_health_analysis=true for context health metrics"
                )
            if not show_stale_entries:
                response_parts.append(
                    "• Add show_stale_entries=true to see entries needing updates"
                )
            response_parts.append(
                "• Use sort_by=[key|size|last_updated] for different sorting"
            )
            response_parts.append(
                "• Use validate_context_consistency to fix JSON errors"
            )

            response_message = "\n".join(response_parts)

    except sqlite3.Error as e_sql:
        logger.error(
            f"Database error viewing project context: {e_sql}", exc_info=True
        )  # main.py:1462
        response_message = f"Database error viewing project context: {e_sql}"
    except (
        json.JSONDecodeError
    ) as e_json:  # Should be caught per-item, but as a fallback
        logger.error(
            f"Error decoding JSON from project_context table during bulk view: {e_json}",
            exc_info=True,
        )  # main.py:1465
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
async def _handle_single_context_update(
    requesting_agent_id: str,
    context_key_to_update: str,
    context_value_to_set: Any,
    description_for_context: Optional[str] = None,
) -> List[mcp_types.TextContent]:
    """Handle single context update operation"""
    # Log audit
    log_audit(
        requesting_agent_id,
        "update_project_context",
        {
            "context_key": context_key_to_update,
            "value_type": str(type(context_value_to_set)),
            "description": description_for_context,
        },
    )

    conn = None
    try:
        # Ensure value is JSON serializable before storing
        value_json_str = json.dumps(context_value_to_set)
    except TypeError as e_type:
        logger.error(
            f"Value provided for project context key '{context_key_to_update}' is not JSON serializable: {e_type}"
        )
        return [
            mcp_types.TextContent(
                type="text",
                text=f"Error: Provided context_value is not JSON serializable: {e_type}",
            )
        ]

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        updated_at_iso = datetime.datetime.now().isoformat()

        # Use INSERT OR REPLACE (UPSERT)
        cursor.execute(
            """
            INSERT OR REPLACE INTO project_context (context_key, value, last_updated, updated_by, description)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                context_key_to_update,
                value_json_str,
                updated_at_iso,
                requesting_agent_id,
                description_for_context,
            ),
        )

        # Log to agent_actions table
        log_agent_action_to_db(
            cursor,
            requesting_agent_id,
            "updated_context",
            details={"context_key": context_key_to_update, "action": "set/update"},
        )
        conn.commit()

        logger.info(
            f"Project context for key '{context_key_to_update}' updated by '{requesting_agent_id}'."
        )
        return [
            mcp_types.TextContent(
                type="text",
                text=f"Project context updated successfully for key '{context_key_to_update}'.",
            )
        ]

    except sqlite3.Error as e_sql:
        if conn:
            conn.rollback()
        logger.error(
            f"Database error updating project context for key '{context_key_to_update}': {e_sql}",
            exc_info=True,
        )
        return [
            mcp_types.TextContent(
                type="text", text=f"Database error updating project context: {e_sql}"
            )
        ]
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(
            f"Unexpected error updating project context for key '{context_key_to_update}': {e}",
            exc_info=True,
        )
        return [
            mcp_types.TextContent(
                type="text", text=f"Unexpected error updating project context: {e}"
            )
        ]
    finally:
        if conn:
            conn.close()


async def _handle_bulk_context_update(
    requesting_agent_id: str, updates_list: List[Dict[str, Any]]
) -> List[mcp_types.TextContent]:
    """Handle bulk context update operations"""
    # Log audit
    log_audit(
        requesting_agent_id,
        "bulk_update_project_context",
        {"update_count": len(updates_list)},
    )

    conn = None
    results = []
    failed_updates = []

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        updated_at_iso = datetime.datetime.now().isoformat()

        # Process each update atomically
        for i, update in enumerate(updates_list):
            try:
                context_key = update["context_key"]
                context_value = update["context_value"]
                description = update.get("description", f"Bulk update operation {i+1}")

                # Validate JSON serialization
                value_json_str = json.dumps(context_value)

                # Execute update
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO project_context (context_key, value, last_updated, updated_by, description)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        context_key,
                        value_json_str,
                        updated_at_iso,
                        requesting_agent_id,
                        description,
                    ),
                )

                results.append(f"✓ Updated '{context_key}'")

                # Log individual action
                log_agent_action_to_db(
                    cursor,
                    requesting_agent_id,
                    "bulk_updated_context",
                    details={
                        "context_key": context_key,
                        "operation": f"bulk_update_{i+1}",
                    },
                )

            except (TypeError, json.JSONEncodeError) as e_json:
                failed_updates.append(
                    f"✗ Failed '{update.get('context_key', 'unknown')}': Invalid JSON - {e_json}"
                )
            except Exception as e_update:
                failed_updates.append(
                    f"✗ Failed '{update.get('context_key', 'unknown')}': {str(e_update)}"
                )

        conn.commit()

        # Build response
        response_parts = [
            f"Bulk update completed: {len(results)} successful, {len(failed_updates)} failed"
        ]

        if results:
            response_parts.append("\nSuccessful updates:")
            response_parts.extend(results)

        if failed_updates:
            response_parts.append("\nFailed updates:")
            response_parts.extend(failed_updates)

        logger.info(
            f"Bulk context update by '{requesting_agent_id}': {len(results)} successful, {len(failed_updates)} failed."
        )
        return [mcp_types.TextContent(type="text", text="\n".join(response_parts))]

    except sqlite3.Error as e_sql:
        if conn:
            conn.rollback()
        logger.error(f"Database error in bulk context update: {e_sql}", exc_info=True)
        return [
            mcp_types.TextContent(
                type="text", text=f"Database error in bulk update: {e_sql}"
            )
        ]
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Unexpected error in bulk context update: {e}", exc_info=True)
        return [
            mcp_types.TextContent(
                type="text", text=f"Unexpected error in bulk update: {e}"
            )
        ]
    finally:
        if conn:
            conn.close()


async def update_project_context_tool_impl(
    arguments: Dict[str, Any],
) -> List[mcp_types.TextContent]:
    auth_token = arguments.get("token")

    # Support both single and bulk operations
    context_key_to_update = arguments.get("context_key")
    context_value_to_set = arguments.get("context_value")
    description_for_context = arguments.get("description")
    updates_list = arguments.get("updates")  # For bulk operations

    requesting_agent_id = get_agent_id(auth_token)
    if not requesting_agent_id:
        return [
            mcp_types.TextContent(
                type="text", text="Unauthorized: Valid token required"
            )
        ]

    # Determine operation mode
    is_bulk_operation = updates_list is not None

    if is_bulk_operation:
        if not isinstance(updates_list, list) or len(updates_list) == 0:
            return [
                mcp_types.TextContent(
                    type="text",
                    text="Error: updates must be a non-empty list for bulk operations.",
                )
            ]
        return await _handle_bulk_context_update(requesting_agent_id, updates_list)
    else:
        # Single operation (backward compatibility)
        if not context_key_to_update or context_value_to_set is None:
            return [
                mcp_types.TextContent(
                    type="text",
                    text="Error: context_key and context_value are required for single updates.",
                )
            ]
        return await _handle_single_context_update(
            requesting_agent_id,
            context_key_to_update,
            context_value_to_set,
            description_for_context,
        )


# --- bulk_update_project_context tool ---
async def bulk_update_project_context_tool_impl(
    arguments: Dict[str, Any],
) -> List[mcp_types.TextContent]:
    auth_token = arguments.get("token")
    updates = arguments.get("updates", [])  # List of update operations

    requesting_agent_id = get_agent_id(auth_token)
    if not requesting_agent_id:
        return [
            mcp_types.TextContent(
                type="text", text="Unauthorized: Valid token required"
            )
        ]

    if not updates or not isinstance(updates, list):
        return [
            mcp_types.TextContent(type="text", text="Error: updates array is required.")
        ]

    # Validate each update operation
    for i, update in enumerate(updates):
        if not isinstance(update, dict):
            return [
                mcp_types.TextContent(
                    type="text", text=f"Error: Update {i} must be an object."
                )
            ]
        if "context_key" not in update:
            return [
                mcp_types.TextContent(
                    type="text",
                    text=f"Error: Update {i} missing required 'context_key'.",
                )
            ]
        if "context_value" not in update:
            return [
                mcp_types.TextContent(
                    type="text",
                    text=f"Error: Update {i} missing required 'context_value'.",
                )
            ]

    # Log audit
    log_audit(
        requesting_agent_id,
        "bulk_update_project_context",
        {"update_count": len(updates)},
    )

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
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO project_context (context_key, value, last_updated, updated_by, description)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        context_key,
                        value_json_str,
                        updated_at_iso,
                        requesting_agent_id,
                        description,
                    ),
                )

                results.append(f"✓ Updated '{context_key}'")

                # Log individual action
                log_agent_action_to_db(
                    cursor,
                    requesting_agent_id,
                    "bulk_updated_context",
                    details={
                        "context_key": context_key,
                        "operation": f"bulk_update_{i+1}",
                    },
                )

            except (TypeError, json.JSONEncodeError) as e_json:
                failed_updates.append(
                    f"✗ Failed '{update.get('context_key', 'unknown')}': Invalid JSON - {e_json}"
                )
            except Exception as e_update:
                failed_updates.append(
                    f"✗ Failed '{update.get('context_key', 'unknown')}': {str(e_update)}"
                )

        conn.commit()

        # Build response
        response_parts = [
            f"Bulk update completed: {len(results)} successful, {len(failed_updates)} failed"
        ]

        if results:
            response_parts.append("\nSuccessful updates:")
            response_parts.extend(results)

        if failed_updates:
            response_parts.append("\nFailed updates:")
            response_parts.extend(failed_updates)

        logger.info(
            f"Bulk context update by '{requesting_agent_id}': {len(results)} successful, {len(failed_updates)} failed."
        )
        return [mcp_types.TextContent(type="text", text="\n".join(response_parts))]

    except sqlite3.Error as e_sql:
        if conn:
            conn.rollback()
        logger.error(f"Database error in bulk context update: {e_sql}", exc_info=True)
        return [
            mcp_types.TextContent(
                type="text", text=f"Database error in bulk update: {e_sql}"
            )
        ]
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Unexpected error in bulk context update: {e}", exc_info=True)
        return [
            mcp_types.TextContent(
                type="text", text=f"Unexpected error in bulk update: {e}"
            )
        ]
    finally:
        if conn:
            conn.close()


# --- backup_project_context tool ---
async def backup_project_context_tool_impl(
    arguments: Dict[str, Any],
) -> List[mcp_types.TextContent]:
    auth_token = arguments.get("token")
    backup_name = arguments.get("backup_name")  # Optional custom backup name
    include_health_report = arguments.get(
        "include_health_report", True
    )  # Include health analysis in backup

    requesting_agent_id = get_agent_id(auth_token)
    if not requesting_agent_id:
        return [
            mcp_types.TextContent(
                type="text", text="Unauthorized: Valid token required"
            )
        ]

    # Admin only for security
    if not verify_token(auth_token, "admin"):
        return [
            mcp_types.TextContent(
                type="text",
                text="Unauthorized: Admin token required for backup operations",
            )
        ]

    log_audit(
        requesting_agent_id, "backup_project_context", {"backup_name": backup_name}
    )

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Create backup
        backup_data = _create_context_backup(cursor, backup_name)

        # Add health analysis if requested
        if include_health_report:
            all_entries = backup_data["entries"]
            health_analysis = _analyze_context_health(all_entries)
            backup_data["health_report"] = health_analysis

        # Save backup to a file in the project directory (optional - could be database too)
        import os

        project_dir = os.environ.get("MCP_PROJECT_DIR", ".")
        backup_dir = os.path.join(project_dir, ".agent", "backups", "context")
        os.makedirs(backup_dir, exist_ok=True)

        backup_filename = f"{backup_data['backup_name']}.json"
        backup_path = os.path.join(backup_dir, backup_filename)

        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)

        # Generate response
        response_parts = [
            f"✅ **Context Backup Created**",
            f"   Name: {backup_data['backup_name']}",
            f"   Entries: {backup_data['total_entries']}",
            f"   File: {backup_path}",
            f"   Created: {backup_data['created_at']}",
        ]

        if include_health_report and "health_report" in backup_data:
            health = backup_data["health_report"]
            health_icon = (
                "🟢"
                if health["status"] == "excellent"
                else (
                    "🟡"
                    if health["status"] == "good"
                    else "🟠" if health["status"] == "needs_attention" else "🔴"
                )
            )

            response_parts.extend(
                [
                    "",
                    f"📊 **Health Report:** {health_icon} {health['status'].title()} ({health['health_score']}/100)",
                    f"   Issues: {health['json_errors']} JSON errors, {health['stale_entries']} stale entries",
                    f"   Recommendations: {len(health['recommendations'])} items",
                ]
            )

        response_parts.extend(
            [
                "",
                "💡 **Backup Usage:**",
                "• Use this backup to restore context in case of corruption",
                "• Store backup files securely - they contain sensitive project data",
                "• Regular backups recommended before major context changes",
            ]
        )

        log_agent_action_to_db(
            cursor,
            requesting_agent_id,
            "backup_project_context",
            backup_name,
            {"total_entries": backup_data["total_entries"], "backup_path": backup_path},
        )

        return [mcp_types.TextContent(type="text", text="\n".join(response_parts))]

    except Exception as e:
        logger.error(f"Error creating context backup: {e}", exc_info=True)
        return [mcp_types.TextContent(type="text", text=f"Error creating backup: {e}")]
    finally:
        if conn:
            conn.close()


# --- validate_context_consistency tool ---
async def validate_context_consistency_tool_impl(
    arguments: Dict[str, Any],
) -> List[mcp_types.TextContent]:
    auth_token = arguments.get("token")

    requesting_agent_id = get_agent_id(auth_token)
    if not requesting_agent_id:
        return [
            mcp_types.TextContent(
                type="text", text="Unauthorized: Valid token required"
            )
        ]

    # Log audit
    log_audit(requesting_agent_id, "validate_context_consistency", {})

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        issues = []
        warnings = []

        # Get all context entries
        cursor.execute(
            "SELECT context_key, value, description, updated_by, last_updated FROM project_context ORDER BY context_key"
        )
        all_entries = [dict(row) for row in cursor.fetchall()]

        if not all_entries:
            return [
                mcp_types.TextContent(
                    type="text", text="No project context entries found."
                )
            ]

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
                issues.append(
                    f"Potential duplicate keys: '{key_map[key_lower]}' and '{entry['context_key']}'"
                )
            else:
                key_map[key_lower] = entry["context_key"]

        # Check 3: Missing descriptions
        missing_desc = [
            entry["context_key"]
            for entry in all_entries
            if not entry.get("description")
        ]
        if missing_desc:
            warnings.extend(
                [f"Missing description: '{key}'" for key in missing_desc[:10]]
            )
            if len(missing_desc) > 10:
                warnings.append(
                    f"... and {len(missing_desc) - 10} more missing descriptions"
                )

        # Check 4: Very old entries (potential staleness)
        import datetime as dt

        cutoff_date = (dt.datetime.now() - dt.timedelta(days=30)).isoformat()
        old_entries = [
            entry["context_key"]
            for entry in all_entries
            if entry["last_updated"] < cutoff_date
        ]
        if old_entries:
            warnings.extend(
                [f"Old entry (>30 days): '{key}'" for key in old_entries[:5]]
            )
            if len(old_entries) > 5:
                warnings.append(f"... and {len(old_entries) - 5} more old entries")

        # Check 5: Unusually large values (potential bloat)
        large_entries = []
        for entry in all_entries:
            if len(entry["value"]) > 10000:  # 10KB threshold
                large_entries.append(
                    f"{entry['context_key']} ({len(entry['value'])} chars)"
                )
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
                response_parts.append(
                    "- Use bulk_update_project_context for corrections"
                )
            if warnings:
                response_parts.append("- Review warnings for potential cleanup")
                response_parts.append(
                    "- Consider using delete_project_context for unused entries"
                )

        return [mcp_types.TextContent(type="text", text="\n".join(response_parts))]

    except sqlite3.Error as e_sql:
        logger.error(
            f"Database error validating context consistency: {e_sql}", exc_info=True
        )
        return [
            mcp_types.TextContent(
                type="text", text=f"Database error validating context: {e_sql}"
            )
        ]
    except Exception as e:
        logger.error(
            f"Unexpected error validating context consistency: {e}", exc_info=True
        )
        return [
            mcp_types.TextContent(
                type="text", text=f"Unexpected error validating context: {e}"
            )
        ]
    finally:
        if conn:
            conn.close()


# --- Register project context tools ---
def register_project_context_tools():
    register_tool(
        name="view_project_context",
        description="Smart project context viewer with health analysis, stale entry detection, and advanced filtering. Provides comprehensive insights into context quality and usage.",
        input_schema={
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "Authentication token"},
                "context_key": {
                    "type": "string",
                    "description": "Exact key to view (optional). If provided, search_query is ignored.",
                },
                "search_query": {
                    "type": "string",
                    "description": "Keyword search query (optional). Searches keys, descriptions, and values.",
                },
                # Smart analysis features
                "show_health_analysis": {
                    "type": "boolean",
                    "description": "Include comprehensive health metrics and analysis (default: false)",
                },
                "show_stale_entries": {
                    "type": "boolean",
                    "description": "Show only entries older than 30 days needing review (default: false)",
                },
                "include_backup_info": {
                    "type": "boolean",
                    "description": "Include backup recommendations and info (default: false)",
                },
                # Display and sorting options
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of entries to return (default: 50)",
                    "minimum": 1,
                    "maximum": 200,
                },
                "sort_by": {
                    "type": "string",
                    "description": "Sort entries by specified field (default: last_updated)",
                    "enum": ["key", "last_updated", "size"],
                    "default": "last_updated",
                },
            },
            "required": ["token"],
            "additionalProperties": False,
        },
        implementation=view_project_context_tool_impl,
    )

    register_tool(
        name="update_project_context",  # main.py:1825
        description="Add or update a project context entry with a specific key. The value can be any JSON-serializable type.",
        input_schema={  # From main.py:1826-1839
            "type": "object",
            "properties": {
                "token": {
                    "type": "string",
                    "description": "Authentication token (agent or admin)",
                },
                "context_key": {
                    "type": "string",
                    "description": "The exact key for the context entry (e.g., 'api.service_x.url').",
                },
                "context_value": {
                    "type": "object",
                    "description": "The JSON-serializable value to set (e.g., string, number, list, dict).",
                    "additionalProperties": True,
                },  # Allow any valid JSON as value
                "description": {
                    "type": "string",
                    "description": "Optional description of this context entry.",
                },
            },
            "required": ["token", "context_key", "context_value"],
            "additionalProperties": False,
        },
        implementation=update_project_context_tool_impl,
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
                            "context_key": {
                                "type": "string",
                                "description": "The context key to update",
                            },
                            "context_value": {
                                "description": "The new value (any JSON-serializable type)"
                            },
                            "description": {
                                "type": "string",
                                "description": "Optional description for this update",
                            },
                        },
                        "required": ["context_key", "context_value"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["token", "updates"],
            "additionalProperties": False,
        },
        implementation=bulk_update_project_context_tool_impl,
    )

    register_tool(
        name="backup_project_context",
        description="Create comprehensive backup of all project context with health analysis. Admin-only operation for data safety and recovery.",
        input_schema={
            "type": "object",
            "properties": {
                "token": {
                    "type": "string",
                    "description": "Admin authentication token",
                },
                "backup_name": {
                    "type": "string",
                    "description": "Optional custom backup name (auto-generated if not provided)",
                },
                "include_health_report": {
                    "type": "boolean",
                    "description": "Include health analysis in backup (default: true)",
                    "default": True,
                },
            },
            "required": ["token"],
            "additionalProperties": False,
        },
        implementation=backup_project_context_tool_impl,
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
            "additionalProperties": False,
        },
        implementation=validate_context_consistency_tool_impl,
    )

    register_tool(
        name="delete_project_context",
        description="Delete project context entries permanently. Admin-only operation with safety checks for critical system keys.",
        input_schema={
            "type": "object",
            "properties": {
                "token": {
                    "type": "string",
                    "description": "Admin authentication token",
                },
                "context_key": {
                    "type": "string",
                    "description": "Single context key to delete (alternative to context_keys)",
                },
                "context_keys": {
                    "type": "array",
                    "description": "List of context keys to delete",
                    "items": {"type": "string"},
                    "minItems": 1,
                },
                "force_delete": {
                    "type": "boolean",
                    "description": "Force deletion even for critical system keys (default: false)",
                    "default": False,
                },
            },
            "required": ["token"],
            "additionalProperties": False,
        },
        implementation=delete_project_context_tool_impl,
    )


async def delete_project_context_tool_impl(
    arguments: Dict[str, Any],
) -> List[mcp_types.TextContent]:
    """
    Delete project context entries permanently.
    Admin-only operation with safety checks for critical system keys.
    """
    admin_token = arguments.get("token")
    context_keys = arguments.get("context_keys", [])
    context_key = arguments.get("context_key")
    force_delete = arguments.get("force_delete", False)

    # Verify admin permissions
    if not verify_token(admin_token, "admin"):
        return [
            mcp_types.TextContent(
                type="text", text="Unauthorized: Admin token required"
            )
        ]

    # Prepare list of keys to delete
    keys_to_delete = []
    if context_key:
        keys_to_delete.append(context_key)
    if context_keys:
        keys_to_delete.extend(context_keys)

    if not keys_to_delete:
        return [
            mcp_types.TextContent(
                type="text", text="Error: No context keys specified for deletion"
            )
        ]

    # Critical system keys that require force_delete
    critical_keys = [
        "config_admin_token",
        "server_startup",
        "database_version",
        "system_config",
        "mcp_server_url",
    ]

    # Check for critical keys
    critical_keys_found = []
    for key in keys_to_delete:
        for critical_pattern in critical_keys:
            if (
                key.startswith(critical_pattern.split("_")[0] + "_")
                or key == critical_pattern
            ):
                critical_keys_found.append(key)
                break

    if critical_keys_found and not force_delete:
        return [
            mcp_types.TextContent(
                type="text",
                text=f"Error: Cannot delete critical system keys without force_delete=true: {critical_keys_found}",
            )
        ]

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check which keys exist
        existing_keys = []
        for key in keys_to_delete:
            cursor.execute(
                "SELECT context_key FROM project_context WHERE context_key = ?", (key,)
            )
            if cursor.fetchone():
                existing_keys.append(key)

        if not existing_keys:
            return [
                mcp_types.TextContent(
                    type="text",
                    text=f"Error: None of the specified keys exist in project context: {keys_to_delete}",
                )
            ]

        # Delete the keys
        deleted_count = 0
        deletion_details = []

        for key in existing_keys:
            # Get current value for logging
            cursor.execute(
                "SELECT value, description FROM project_context WHERE context_key = ?",
                (key,),
            )
            row = cursor.fetchone()

            if row:
                cursor.execute(
                    "DELETE FROM project_context WHERE context_key = ?", (key,)
                )
                if cursor.rowcount > 0:
                    deleted_count += 1
                    deletion_details.append(
                        {
                            "key": key,
                            "description": (
                                row["description"] if row["description"] else ""
                            ),
                            "was_critical": key in critical_keys_found,
                        }
                    )

        # Log the deletion action
        log_agent_action_to_db(
            cursor=cursor,
            agent_id="admin",
            action_type="deleted_context",
            details={
                "deleted_keys": [d["key"] for d in deletion_details],
                "critical_keys_deleted": critical_keys_found,
                "force_delete": force_delete,
                "total_deleted": deleted_count,
            },
        )

        conn.commit()

        # Prepare response
        response_parts = [
            f"Deleted {deleted_count} project context entries successfully:"
        ]

        for detail in deletion_details:
            key_info = f"  • {detail['key']}"
            if detail["description"]:
                key_info += f" ({detail['description']})"
            if detail["was_critical"]:
                key_info += " [CRITICAL]"
            response_parts.append(key_info)

        if critical_keys_found:
            response_parts.append(
                f"\n⚠️  WARNING: {len(critical_keys_found)} critical system keys were deleted!"
            )
            response_parts.append(
                "System functionality may be affected. Consider backing up before restart."
            )

        response_parts.append(
            f"\nDeletion completed at: {datetime.datetime.now().isoformat()}"
        )

        return [mcp_types.TextContent(type="text", text="\n".join(response_parts))]

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error in delete_project_context_tool_impl: {e}", exc_info=True)
        return [
            mcp_types.TextContent(
                type="text", text=f"Error deleting project context: {str(e)}"
            )
        ]
    finally:
        if conn:
            conn.close()


# Call registration when this module is imported
register_project_context_tools()
