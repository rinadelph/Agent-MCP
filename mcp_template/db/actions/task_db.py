# Agent-MCP/mcp_template/mcp_server_src/db/actions/task_db.py
import sqlite3
import json
import datetime
from typing import Optional, Dict, List, Any

from mcp_server_src.core.config import logger
from mcp_server_src.db.connection import get_db_connection

# This module provides reusable database operations specifically for the 'tasks' table.

def _parse_task_json_fields(task_data: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to parse JSON string fields in a task dictionary."""
    if not task_data:
        return {}
    
    parsed_data = task_data.copy()
    for field_key in ["child_tasks", "depends_on_tasks", "notes"]:
        if field_key in parsed_data and isinstance(parsed_data[field_key], str):
            try:
                parsed_data[field_key] = json.loads(parsed_data[field_key] or "[]")
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON for field '{field_key}' in task '{parsed_data.get('task_id', 'Unknown')}'. Raw: {parsed_data[field_key]}")
                parsed_data[field_key] = [] # Default to empty list on parse error
    return parsed_data

def get_task_by_id(task_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetches a single task's details from the database by task_id.
    Parses JSON fields (child_tasks, depends_on_tasks, notes) into Python lists.
    Returns None if the task is not found.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()
        if row:
            return _parse_task_json_fields(dict(row))
        return None
    except sqlite3.Error as e:
        logger.error(f"Database error fetching task by ID '{task_id}': {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching task by ID '{task_id}': {e}", exc_info=True)
        return None
    finally:
        if conn:
            conn.close()

def get_all_tasks_from_db() -> List[Dict[str, Any]]:
    """
    Fetches all tasks from the database.
    Parses JSON fields for each task.
    This is used for populating g.tasks at startup and for dashboard views.
    """
    tasks_list: List[Dict[str, Any]] = []
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Query matches the one in server_lifecycle.application_startup and all_tasks_api_route
        cursor.execute("SELECT * FROM tasks ORDER BY created_at DESC") # Order for consistency
        for row in cursor.fetchall():
            tasks_list.append(_parse_task_json_fields(dict(row)))
        return tasks_list
    except sqlite3.Error as e:
        logger.error(f"Database error fetching all tasks: {e}", exc_info=True)
        return [] # Return empty list on error
    except Exception as e:
        logger.error(f"Unexpected error fetching all tasks: {e}", exc_info=True)
        return []
    finally:
        if conn:
            conn.close()

def get_tasks_by_agent_id(agent_id: str, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetches tasks assigned to a specific agent, optionally filtered by status.
    Parses JSON fields for each task.
    """
    tasks_list: List[Dict[str, Any]] = []
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM tasks WHERE assigned_to = ?"
        params: List[Any] = [agent_id]
        
        if status_filter:
            query += " AND status = ?"
            params.append(status_filter)
        
        query += " ORDER BY created_at DESC"
        
        cursor.execute(query, tuple(params))
        for row in cursor.fetchall():
            tasks_list.append(_parse_task_json_fields(dict(row)))
        return tasks_list
    except sqlite3.Error as e:
        logger.error(f"Database error fetching tasks for agent '{agent_id}': {e}", exc_info=True)
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching tasks for agent '{agent_id}': {e}", exc_info=True)
        return []
    finally:
        if conn:
            conn.close()

# Example of a more specific update function (not directly from original main.py as a separate function)
# Task updates are currently handled within task_tools.py, which is fine for 1-to-1.
# This is a conceptual example of how task updates could be further centralized if needed.
def update_task_fields_in_db(task_id: str, fields_to_update: Dict[str, Any]) -> bool:
    """
    Updates specified fields for a task in the database.
    Automatically updates the 'updated_at' timestamp.
    Handles JSON serialization for complex fields like 'notes', 'child_tasks', 'depends_on_tasks'.
    Returns True on success, False on failure.
    """
    if not task_id or not fields_to_update:
        logger.warning("update_task_fields_in_db called with no task_id or no fields to update.")
        return False

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        update_clauses: List[str] = []
        update_values: List[Any] = []

        for field, value in fields_to_update.items():
            # Basic validation against known task fields from schema.py
            # This list should match columns in the 'tasks' table.
            valid_fields = [
                "title", "description", "assigned_to", "status", "priority",
                "parent_task", "child_tasks", "depends_on_tasks", "notes"
            ]
            if field not in valid_fields:
                logger.warning(f"Attempted to update invalid task field: {field} for task {task_id}. Skipping.")
                continue

            update_clauses.append(f"{field} = ?")
            if field in ["child_tasks", "depends_on_tasks", "notes"]:
                update_values.append(json.dumps(value or [])) # Ensure JSON list for these
            else:
                update_values.append(value)
        
        if not update_clauses:
            logger.info(f"No valid fields to update for task {task_id}.")
            return False # Or True, as no actual update was needed/performed

        # Always update the 'updated_at' timestamp
        update_clauses.append("updated_at = ?")
        update_values.append(datetime.datetime.now().isoformat())

        update_values.append(task_id) # For the WHERE clause

        sql = f"UPDATE tasks SET {', '.join(update_clauses)} WHERE task_id = ?"
        
        cursor.execute(sql, tuple(update_values))
        conn.commit()

        if cursor.rowcount > 0:
            logger.info(f"Task '{task_id}' updated in DB with fields: {list(fields_to_update.keys())}.")
            return True
        else:
            logger.warning(f"Task '{task_id}' not found or update had no effect in DB.")
            return False # Task might not exist or values were the same

    except sqlite3.Error as e:
        if conn: conn.rollback()
        logger.error(f"Database error updating task '{task_id}': {e}", exc_info=True)
        return False
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Unexpected error updating task '{task_id}': {e}", exc_info=True)
        return False
    finally:
        if conn:
            conn.close()