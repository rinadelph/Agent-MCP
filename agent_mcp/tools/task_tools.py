# Agent-MCP/mcp_template/mcp_server_src/tools/task_tools.py
import json
import datetime
import secrets # For task_id generation
import os # For request_assistance (notifications path)
from pathlib import Path # For request_assistance
from typing import List, Dict, Any, Optional

import mcp.types as mcp_types

from .registry import register_tool
from ..core.config import logger, ENABLE_TASK_PLACEMENT_RAG, ALLOW_RAG_OVERRIDE
from ..core import globals as g
from ..core.auth import verify_token, get_agent_id
from ..utils.audit_utils import log_audit
from ..db.connection import get_db_connection
from ..db.actions.agent_actions_db import log_agent_action_to_db
from ..features.task_placement.validator import validate_task_placement
from ..features.task_placement.suggestions import (
    format_suggestions_for_agent, 
    format_override_reason,
    should_escalate_to_admin
)
from ..features.rag.indexing import index_task_data
# For request_assistance, generate_id was used. Let's use secrets.token_hex for consistency.
# from main.py:1191 (generate_id - not present, assuming secrets.token_hex was intended)

def _generate_task_id() -> str:
    """Generates a unique task ID."""
    return f"task_{secrets.token_hex(6)}"

def _generate_notification_id() -> str:
    """Generates a unique notification ID."""
    return f"notification_{secrets.token_hex(8)}"


# --- assign_task tool ---
# Original logic from main.py: lines 1319-1384 (assign_task_tool function)
async def assign_task_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    admin_auth_token = arguments.get("token")
    target_agent_id = arguments.get("agent_id")
    task_title = arguments.get("task_title")
    task_description = arguments.get("task_description")
    priority = arguments.get("priority", "medium") # Default from schema
    depends_on_tasks_list = arguments.get("depends_on_tasks") # List[str] or None
    parent_task_id_arg = arguments.get("parent_task_id") # Optional str

    if not verify_token(admin_auth_token, "admin"): # main.py:1326
        return [mcp_types.TextContent(type="text", text="Unauthorized: Admin token required")]

    if not all([target_agent_id, task_title, task_description]):
        return [mcp_types.TextContent(type="text", text="Error: agent_id, task_title, and task_description are required.")]
    
    # Enforce single root task rule BEFORE any processing
    if parent_task_id_arg is None:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count, GROUP_CONCAT(task_id) as root_ids FROM tasks WHERE parent_task IS NULL")
        result = cursor.fetchone()
        root_count = result['count']
        root_ids = result['root_ids']
        
        if root_count > 0:
            # Find some suggested parent tasks to help the admin
            cursor.execute("""
                SELECT task_id, title, status 
                FROM tasks 
                WHERE status IN ('pending', 'in_progress')
                ORDER BY 
                    CASE WHEN assigned_to = ? THEN 0 ELSE 1 END,
                    created_at DESC
                LIMIT 5
            """, (target_agent_id,))
            
            suggestions = cursor.fetchall()
            suggestion_text = "\nSuggested parent tasks:\n"
            for task in suggestions:
                suggestion_text += f"  - {task['task_id']}: {task['title']} (status: {task['status']})\n"
            
            conn.close()
            
            return [mcp_types.TextContent(
                type="text",
                text=f"ERROR: Cannot create task without parent. {root_count} root task(s) already exist: {root_ids}\n\n"
                     f"You MUST specify a parent_task_id. Every task except the first must have a parent.\n"
                     f"{suggestion_text}\n"
                     f"Use 'view_tasks' for complete task list, or use one of the suggestions above."
            )]
        
        conn.close()

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if agent exists (in memory or DB) - main.py:1331-1346
        agent_exists_in_memory = target_agent_id in g.agent_working_dirs
        assigned_agent_active_token: Optional[str] = None
        if agent_exists_in_memory:
            for tkn, data in g.active_agents.items():
                if data.get("agent_id") == target_agent_id:
                    assigned_agent_active_token = tkn
                    break
        
        if not agent_exists_in_memory:
            cursor.execute("SELECT token FROM agents WHERE agent_id = ? AND status != ?", (target_agent_id, "terminated"))
            row = cursor.fetchone()
            if not row:
                return [mcp_types.TextContent(type="text", text=f"Agent '{target_agent_id}' not found or is terminated.")]
            # Agent exists in DB but not memory, can still assign task.
            logger.warning(f"Assigning task to agent {target_agent_id} found in DB but not active memory.")
            # assigned_agent_active_token remains None if not in active_agents

        # Generate task ID and timestamps first
        new_task_id = _generate_task_id()
        created_at_iso = datetime.datetime.now().isoformat()
        status = "pending"
        
        # Check single root task rule
        if parent_task_id_arg is None:
            cursor.execute("SELECT COUNT(*) as count, MIN(task_id) as root_id FROM tasks WHERE parent_task IS NULL")
            result = cursor.fetchone()
            root_count = result['count']
            existing_root_id = result['root_id']
            
            if root_count > 0:
                logger.error(f"Attempt to create second root task. Existing root: {existing_root_id}")
                return [mcp_types.TextContent(
                    type="text",
                    text=f"ERROR: Cannot create root task. A root task already exists ({existing_root_id}). All new tasks must have a parent."
                )]
        
        # System 8: RAG Pre-Check for Task Placement
        final_parent_task_id = parent_task_id_arg
        final_depends_on_tasks = depends_on_tasks_list
        validation_performed = False
        validation_message = ""
        
        if ENABLE_TASK_PLACEMENT_RAG:
            validation_performed = True
            validation_result = await validate_task_placement(
                title=task_title,
                description=task_description,
                parent_task_id=parent_task_id_arg,
                depends_on_tasks=depends_on_tasks_list,
                created_by="admin",
                auth_token=admin_auth_token
            )
            
            suggestion_message = format_suggestions_for_agent(
                validation_result,
                parent_task_id_arg,
                depends_on_tasks_list
            )
            
            # For denied status, block creation unless override is allowed
            if validation_result["status"] == "denied" and not ALLOW_RAG_OVERRIDE:
                return [mcp_types.TextContent(
                    type="text", 
                    text=f"Task creation BLOCKED by RAG validation:\n{suggestion_message}"
                )]
            
            # Process suggestions - always apply them unless explicitly overridden
            if validation_result["status"] != "approved":
                validation_message = f"\nRAG Validation ({validation_result['status']}):\n{suggestion_message}\n"
                
                # Apply suggestions by default (agent should see this behavior)
                suggestions = validation_result["suggestions"]
                if suggestions.get("parent_task") is not None:
                    final_parent_task_id = suggestions["parent_task"]
                    validation_message += f"✓ Applied suggested parent: {final_parent_task_id}\n"
                if suggestions.get("dependencies"):
                    final_depends_on_tasks = suggestions["dependencies"]
                    validation_message += f"✓ Applied suggested dependencies: {final_depends_on_tasks}\n"
                
                logger.info(f"RAG suggestions automatically applied for task {new_task_id}")
            else:
                validation_message = "\n✓ RAG validation approved placement\n"

        task_data_for_db = { # main.py:1354-1367
            "task_id": new_task_id,
            "title": task_title,
            "description": task_description,
            "assigned_to": target_agent_id,
            "created_by": "admin", # Admin is assigning
            "status": status,
            "priority": priority,
            "created_at": created_at_iso,
            "updated_at": created_at_iso,
            "parent_task": final_parent_task_id,  # Use validated value
            "child_tasks": json.dumps([]),
            "depends_on_tasks": json.dumps(final_depends_on_tasks or []),  # Use validated value
            "notes": json.dumps([])
        }

        # Save task to database (main.py:1370-1373)
        cursor.execute("""
            INSERT INTO tasks (task_id, title, description, assigned_to, created_by, status, priority, 
                               created_at, updated_at, parent_task, child_tasks, depends_on_tasks, notes)
            VALUES (:task_id, :title, :description, :assigned_to, :created_by, :status, :priority, 
                    :created_at, :updated_at, :parent_task, :child_tasks, :depends_on_tasks, :notes)
        """, task_data_for_db)

        # Update agent's current task in DB if they don't have one (main.py:1376-1387)
        should_update_agent_current_task = False
        if assigned_agent_active_token and assigned_agent_active_token in g.active_agents:
            if g.active_agents[assigned_agent_active_token].get("current_task") is None:
                should_update_agent_current_task = True
        else: # Agent not in active memory, check DB
            cursor.execute("SELECT current_task FROM agents WHERE agent_id = ?", (target_agent_id,))
            agent_row = cursor.fetchone()
            if agent_row and agent_row["current_task"] is None:
                should_update_agent_current_task = True
        
        if should_update_agent_current_task:
            cursor.execute("UPDATE agents SET current_task = ?, updated_at = ? WHERE agent_id = ?", 
                           (new_task_id, created_at_iso, target_agent_id))

        log_agent_action_to_db(cursor, "admin", "assigned_task", task_id=new_task_id, 
                               details={'agent_id': target_agent_id, 'title': task_title})
        conn.commit()

        # Update agent's current task in memory if needed (main.py:1390-1391)
        if should_update_agent_current_task and assigned_agent_active_token and assigned_agent_active_token in g.active_agents:
            g.active_agents[assigned_agent_active_token]["current_task"] = new_task_id
            
        # Add task to in-memory tasks dictionary (main.py:1394-1398)
        # Convert JSON strings back for in-memory representation
        task_data_for_memory = task_data_for_db.copy()
        task_data_for_memory["child_tasks"] = []
        task_data_for_memory["depends_on_tasks"] = final_depends_on_tasks or []  # Use validated value
        task_data_for_memory["notes"] = []
        g.tasks[new_task_id] = task_data_for_memory
        
        # System 8: Index the new task for RAG
        # Convert database format to the format expected by indexing
        index_data = task_data_for_memory.copy()
        index_data["depends_on_tasks"] = final_depends_on_tasks or []
        # Start indexing asynchronously (fire and forget)
        import asyncio
        asyncio.create_task(index_task_data(new_task_id, index_data))
            
        log_audit("admin", "assign_task", {"task_id": new_task_id, "agent_id": target_agent_id, "title": task_title}) # main.py:1404
        logger.info(f"Task '{new_task_id}' ({task_title}) assigned to agent '{target_agent_id}'.")
        response_text = f"Task '{new_task_id}' assigned to agent '{target_agent_id}'.\nTitle: {task_title}"
        if validation_performed and validation_message:
            response_text += validation_message
        
        return [mcp_types.TextContent(type="text", text=response_text)]

    except sqlite3.Error as e_sql:
        if conn: conn.rollback()
        logger.error(f"Database error assigning task to agent {target_agent_id}: {e_sql}", exc_info=True)
        return [mcp_types.TextContent(type="text", text=f"Database error assigning task: {e_sql}")]
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Unexpected error assigning task to agent {target_agent_id}: {e}", exc_info=True)
        return [mcp_types.TextContent(type="text", text=f"Unexpected error assigning task: {e}")]
    finally:
        if conn:
            conn.close()


# --- create_self_task tool ---
# Original logic from main.py: lines 1409-1474 (create_self_task_tool function)
async def create_self_task_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    agent_auth_token = arguments.get("token")
    task_title = arguments.get("task_title")
    task_description = arguments.get("task_description")
    priority = arguments.get("priority", "medium")
    depends_on_tasks_list = arguments.get("depends_on_tasks")
    parent_task_id_arg = arguments.get("parent_task_id")

    requesting_agent_id = get_agent_id(agent_auth_token) # main.py:1415
    if not requesting_agent_id:
        return [mcp_types.TextContent(type="text", text="Unauthorized: Valid token required")]

    if not all([task_title, task_description]):
        return [mcp_types.TextContent(type="text", text="Error: task_title and task_description are required.")]

    # Determine actual parent task ID (main.py:1419-1423)
    actual_parent_task_id = parent_task_id_arg
    if actual_parent_task_id is None and agent_auth_token in g.active_agents:
        actual_parent_task_id = g.active_agents[agent_auth_token].get("current_task")
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Hierarchy Validation - Agents can NEVER create root tasks
        if requesting_agent_id != "admin" and actual_parent_task_id is None:
            logger.error(f"Agent '{requesting_agent_id}' attempted to create a root task")
            
            # Find a suitable parent task for the agent
            cursor.execute("""
                SELECT task_id, title FROM tasks 
                WHERE assigned_to = ? OR created_by = ?
                ORDER BY created_at DESC LIMIT 1
            """, (requesting_agent_id, requesting_agent_id))
            
            suggested_parent = cursor.fetchone()
            suggestion_text = ""
            if suggested_parent:
                suggestion_text = f"\nSuggested parent: {suggested_parent['task_id']} ({suggested_parent['title']})"
            
            return [mcp_types.TextContent(
                type="text",
                text=f"ERROR: Agents cannot create root tasks. Every task must have a parent.{suggestion_text}\nPlease specify a parent_task_id."
            )]
        
        # Additional check for single root rule even for admin
        if actual_parent_task_id is None:
            cursor.execute("SELECT COUNT(*) as count, MIN(task_id) as root_id FROM tasks WHERE parent_task IS NULL")
            result = cursor.fetchone()
            root_count = result['count']
            existing_root_id = result['root_id']
            
            if root_count > 0:
                logger.error(f"Attempt to create second root task. Existing root: {existing_root_id}")
                return [mcp_types.TextContent(
                    type="text",
                    text=f"ERROR: Cannot create root task. A root task already exists ({existing_root_id}). All new tasks must have a parent."
                )]

        # Generate task ID and timestamps first
        new_task_id = _generate_task_id()
        created_at_iso = datetime.datetime.now().isoformat()
        status = "pending"
        
        # System 8: RAG Pre-Check for Task Placement
        final_parent_task_id = actual_parent_task_id
        final_depends_on_tasks = depends_on_tasks_list
        validation_message = ""
        
        if ENABLE_TASK_PLACEMENT_RAG:
            validation_result = await validate_task_placement(
                title=task_title,
                description=task_description,
                parent_task_id=actual_parent_task_id,
                depends_on_tasks=depends_on_tasks_list,
                created_by=requesting_agent_id,
                auth_token=agent_auth_token
            )
            
            suggestion_message = format_suggestions_for_agent(
                validation_result,
                actual_parent_task_id,
                depends_on_tasks_list
            )
            
            # Check for denial
            if validation_result["status"] == "denied":
                return [mcp_types.TextContent(
                    type="text", 
                    text=f"Task creation BLOCKED by RAG validation:\n{suggestion_message}"
                )]
            
            # Process validation results
            if validation_result["status"] != "approved":
                validation_message = f"\nRAG Validation ({validation_result['status']}):\n{suggestion_message}\n"
                
                # For agents, always accept suggestions automatically
                suggestions = validation_result["suggestions"]
                if suggestions.get("parent_task") is not None:
                    final_parent_task_id = suggestions["parent_task"]
                    validation_message += f"✓ Applied suggested parent: {final_parent_task_id}\n"
                if suggestions.get("dependencies"):
                    final_depends_on_tasks = suggestions["dependencies"]
                    validation_message += f"✓ Applied suggested dependencies: {final_depends_on_tasks}\n"
                
                logger.info(f"Agent {requesting_agent_id} automatically accepted RAG suggestions")
                
                # Check if escalation is needed
                if should_escalate_to_admin(validation_result, requesting_agent_id):
                    logger.warning(f"Task {new_task_id} flagged for admin review: {validation_result.get('message')}")
                    validation_message += "⚠️ Task flagged for admin review\n"
            else:
                validation_message = "\n✓ RAG validation approved placement\n"

        task_data_for_db = { # main.py:1439-1452
            "task_id": new_task_id,
            "title": task_title,
            "description": task_description,
            "assigned_to": requesting_agent_id,
            "created_by": requesting_agent_id, # Agent creates for self
            "status": status,
            "priority": priority,
            "created_at": created_at_iso,
            "updated_at": created_at_iso,
            "parent_task": final_parent_task_id,  # Use validated value
            "child_tasks": json.dumps([]),
            "depends_on_tasks": json.dumps(final_depends_on_tasks or []),  # Use validated value
            "notes": json.dumps([])
        }
        
        cursor.execute("""
            INSERT INTO tasks (task_id, title, description, assigned_to, created_by, status, priority, 
                               created_at, updated_at, parent_task, child_tasks, depends_on_tasks, notes)
            VALUES (:task_id, :title, :description, :assigned_to, :created_by, :status, :priority, 
                    :created_at, :updated_at, :parent_task, :child_tasks, :depends_on_tasks, :notes)
        """, task_data_for_db)

        # Update agent's current task in DB if they don't have one (main.py:1455-1469)
        should_update_agent_current_task = False
        if agent_auth_token in g.active_agents: # Check memory first
            if g.active_agents[agent_auth_token].get("current_task") is None:
                should_update_agent_current_task = True
        elif requesting_agent_id != "admin": # If not admin and not in active_agents (e.g. loaded from DB only)
            cursor.execute("SELECT current_task FROM agents WHERE agent_id = ?", (requesting_agent_id,))
            agent_row = cursor.fetchone()
            if agent_row and agent_row["current_task"] is None:
                should_update_agent_current_task = True
        # Admin agents don't have a persistent 'current_task' in the agents table.

        if should_update_agent_current_task and requesting_agent_id != "admin":
            cursor.execute("UPDATE agents SET current_task = ?, updated_at = ? WHERE agent_id = ?",
                           (new_task_id, created_at_iso, requesting_agent_id))

        log_agent_action_to_db(cursor, requesting_agent_id, "created_self_task", task_id=new_task_id,
                               details={'title': task_title})
        conn.commit()

        if should_update_agent_current_task and agent_auth_token in g.active_agents:
            g.active_agents[agent_auth_token]["current_task"] = new_task_id
            
        task_data_for_memory = task_data_for_db.copy()
        task_data_for_memory["child_tasks"] = []
        task_data_for_memory["depends_on_tasks"] = final_depends_on_tasks or []  # Use validated value
        task_data_for_memory["notes"] = []
        g.tasks[new_task_id] = task_data_for_memory
        
        # System 8: Index the new task for RAG
        # Convert database format to the format expected by indexing
        index_data = task_data_for_memory.copy()
        # No need to override depends_on_tasks again, it's already the validated value
        # Start indexing asynchronously (fire and forget)
        import asyncio
        asyncio.create_task(index_task_data(new_task_id, index_data))

        log_audit(requesting_agent_id, "create_self_task", {"task_id": new_task_id, "title": task_title}) # main.py:1485
        logger.info(f"Agent '{requesting_agent_id}' created self-task '{new_task_id}' ({task_title}).")
        
        response_text = f"Self-assigned task '{new_task_id}' created.\nTitle: {task_title}"
        if validation_message:
            response_text += validation_message
            
        return [mcp_types.TextContent(type="text", text=response_text)]

    except sqlite3.Error as e_sql:
        if conn: conn.rollback()
        logger.error(f"Database error creating self task for agent {requesting_agent_id}: {e_sql}", exc_info=True)
        return [mcp_types.TextContent(type="text", text=f"Database error creating self task: {e_sql}")]
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Unexpected error creating self task for agent {requesting_agent_id}: {e}", exc_info=True)
        return [mcp_types.TextContent(type="text", text=f"Unexpected error creating self task: {e}")]
    finally:
        if conn:
            conn.close()


# --- update_task_status tool ---
# Original logic from main.py: lines 1477-1583 (update_task_status_tool function)
async def update_task_status_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    agent_auth_token = arguments.get("token")
    task_id_to_update = arguments.get("task_id")
    new_status = arguments.get("status")
    notes_content = arguments.get("notes") # Optional string for new note

    # Admin-only fields for full task update
    new_title = arguments.get("title")
    new_description = arguments.get("description")
    new_priority = arguments.get("priority")
    new_assigned_to = arguments.get("assigned_to")
    new_depends_on_tasks = arguments.get("depends_on_tasks") # List[str] or None

    requesting_agent_id = get_agent_id(agent_auth_token)
    if not requesting_agent_id: # main.py:1485 (token verification)
        return [mcp_types.TextContent(type="text", text="Unauthorized: Valid token required")]

    if not task_id_to_update or not new_status:
        return [mcp_types.TextContent(type="text", text="Error: task_id and status are required.")]

    valid_statuses = ["pending", "in_progress", "completed", "cancelled", "failed"] # Added "failed"
    if new_status not in valid_statuses: # main.py:1515
        return [mcp_types.TextContent(type="text", text=f"Invalid status: {new_status}. Valid: {', '.join(valid_statuses)}")]

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch task from DB to verify ownership and get current data (main.py:1494-1508 for loading if not in memory)
        # For simplicity here, we always fetch from DB to ensure latest state.
        cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id_to_update,))
        task_db_row = cursor.fetchone()
        if not task_db_row:
            return [mcp_types.TextContent(type="text", text=f"Task '{task_id_to_update}' not found.")]
        
        task_current_data = dict(task_db_row)

        # Verify permissions (main.py:1511-1514)
        is_admin_request = verify_token(agent_auth_token, "admin")
        if task_current_data.get("assigned_to") != requesting_agent_id and not is_admin_request:
            return [mcp_types.TextContent(type="text", text="Unauthorized: You can only update tasks assigned to you, or use an admin token.")]

        updated_at_iso = datetime.datetime.now().isoformat()
        
        update_fields_sql: List[str] = ["status = ?", "updated_at = ?"]
        update_params: List[Any] = [new_status, updated_at_iso]

        current_notes_list = json.loads(task_current_data.get("notes") or "[]")
        if notes_content: # main.py:1520-1535 (notes handling)
            current_notes_list.append({
                "timestamp": updated_at_iso,
                "author": requesting_agent_id,
                "content": notes_content
            })
        update_fields_sql.append("notes = ?")
        update_params.append(json.dumps(current_notes_list))

        # Admin-only field updates (main.py:1477 - args were in signature)
        if is_admin_request:
            if new_title is not None:
                update_fields_sql.append("title = ?")
                update_params.append(new_title)
            if new_description is not None:
                update_fields_sql.append("description = ?")
                update_params.append(new_description)
            if new_priority is not None:
                update_fields_sql.append("priority = ?")
                update_params.append(new_priority)
            if new_assigned_to is not None: # Admin can re-assign
                update_fields_sql.append("assigned_to = ?")
                update_params.append(new_assigned_to)
            if new_depends_on_tasks is not None: # Admin can change dependencies
                update_fields_sql.append("depends_on_tasks = ?")
                update_params.append(json.dumps(new_depends_on_tasks))
        
        update_params.append(task_id_to_update)
        
        cursor.execute(f"UPDATE tasks SET {', '.join(update_fields_sql)} WHERE task_id = ?", tuple(update_params))

        # Log action (main.py:1548-1555)
        log_details = {"status": new_status}
        if notes_content: log_details["notes_added"] = True
        if is_admin_request: # Log admin changes
            if new_title: log_details["title_changed"] = True
            # ... add other admin changes to log_details if needed
        log_agent_action_to_db(cursor, requesting_agent_id, "update_task_status", task_id=task_id_to_update, details=log_details)
        conn.commit()

        # Update in-memory cache (g.tasks)
        if task_id_to_update in g.tasks:
            g.tasks[task_id_to_update]["status"] = new_status
            g.tasks[task_id_to_update]["updated_at"] = updated_at_iso
            g.tasks[task_id_to_update]["notes"] = current_notes_list # Already a list
            if is_admin_request:
                if new_title is not None: g.tasks[task_id_to_update]["title"] = new_title
                if new_description is not None: g.tasks[task_id_to_update]["description"] = new_description
                if new_priority is not None: g.tasks[task_id_to_update]["priority"] = new_priority
                if new_assigned_to is not None: g.tasks[task_id_to_update]["assigned_to"] = new_assigned_to
                if new_depends_on_tasks is not None: g.tasks[task_id_to_update]["depends_on_tasks"] = new_depends_on_tasks
        else: # If not in memory, fetch updated from DB to populate cache (less likely path)
            cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id_to_update,))
            updated_row_for_cache = cursor.fetchone()
            if updated_row_for_cache:
                g.tasks[task_id_to_update] = dict(updated_row_for_cache)
                # Ensure list types for relevant fields in cache
                for field_key in ["child_tasks", "depends_on_tasks", "notes"]:
                    if isinstance(g.tasks[task_id_to_update].get(field_key), str):
                        try:
                            g.tasks[task_id_to_update][field_key] = json.loads(g.tasks[task_id_to_update][field_key] or "[]")
                        except json.JSONDecodeError:
                            g.tasks[task_id_to_update][field_key] = []


        # Parent task update logic (main.py:1559-1580) - This was complex and file-based.
        # Replicating the DB update for parent task notes.
        if new_status in ["completed", "cancelled", "failed"] and task_current_data.get("parent_task"):
            parent_task_id_for_note = task_current_data["parent_task"]
            cursor.execute("SELECT notes FROM tasks WHERE task_id = ?", (parent_task_id_for_note,))
            parent_row = cursor.fetchone()
            if parent_row:
                parent_notes_list = json.loads(parent_row["notes"] or "[]")
                parent_notes_list.append({
                    "timestamp": updated_at_iso,
                    "author": "system", # System notification
                    "content": f"Subtask '{task_id_to_update}' ({task_current_data.get('title', '')}) status changed to: {new_status}"
                })
                cursor.execute("UPDATE tasks SET notes = ?, updated_at = ? WHERE task_id = ?",
                               (json.dumps(parent_notes_list), updated_at_iso, parent_task_id_for_note))
                conn.commit()
                if parent_task_id_for_note in g.tasks: # Update parent in memory cache too
                    g.tasks[parent_task_id_for_note]["notes"] = parent_notes_list
                    g.tasks[parent_task_id_for_note]["updated_at"] = updated_at_iso

        # System 8: Re-index the task after update
        # Get the updated task data from cache or DB
        task_data_for_index = None
        if task_id_to_update in g.tasks:
            task_data_for_index = g.tasks[task_id_to_update].copy()
        else:
            cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id_to_update,))
            task_row = cursor.fetchone()
            if task_row:
                task_data_for_index = dict(task_row)
                # Convert JSON fields for indexing
                for field in ["depends_on_tasks", "child_tasks", "notes"]:
                    if isinstance(task_data_for_index.get(field), str):
                        try:
                            task_data_for_index[field] = json.loads(task_data_for_index[field] or "[]")
                        except json.JSONDecodeError:
                            task_data_for_index[field] = []
        
        if task_data_for_index:
            # Start indexing asynchronously
            import asyncio
            asyncio.create_task(index_task_data(task_id_to_update, task_data_for_index))

        log_audit(requesting_agent_id, "update_task_status", {"task_id": task_id_to_update, "new_status": new_status})
        logger.info(f"Task '{task_id_to_update}' status updated to '{new_status}' by agent '{requesting_agent_id}'.")
        return [mcp_types.TextContent(type="text", text=f"Task {task_id_to_update} status updated to {new_status}.")]

    except sqlite3.Error as e_sql:
        if conn: conn.rollback()
        logger.error(f"Database error updating task {task_id_to_update}: {e_sql}", exc_info=True)
        return [mcp_types.TextContent(type="text", text=f"Database error updating task: {e_sql}")]
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Unexpected error updating task {task_id_to_update}: {e}", exc_info=True)
        return [mcp_types.TextContent(type="text", text=f"Unexpected error updating task: {e}")]
    finally:
        if conn:
            conn.close()


# --- view_tasks tool ---
# Original logic from main.py: lines 1586-1655 (view_tasks_tool function)
async def view_tasks_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    agent_auth_token = arguments.get("token")
    filter_agent_id = arguments.get("agent_id") # Optional agent_id to filter by
    filter_status = arguments.get("status")     # Optional status to filter by

    requesting_agent_id = get_agent_id(agent_auth_token) # main.py:1590
    if not requesting_agent_id:
        return [mcp_types.TextContent(type="text", text="Unauthorized: Valid token required")]

    is_admin_request = verify_token(agent_auth_token, "admin") # main.py:1596

    # Permission check (main.py:1599-1604)
    target_agent_id_for_filter = filter_agent_id
    if not is_admin_request: # If not admin
        if filter_agent_id is None: # Non-admin viewing tasks, defaults to their own
            target_agent_id_for_filter = requesting_agent_id
        elif filter_agent_id != requesting_agent_id: # Non-admin trying to view someone else's tasks
            return [mcp_types.TextContent(type="text", text="Unauthorized: Non-admin agents can only view their own tasks or all tasks assigned to them if no agent_id filter is specified.")]

    # Build query dynamically based on filters
    # The original code filtered from the in-memory `tasks` dictionary (g.tasks).
    # For consistency and to ensure up-to-date data, querying the DB is better.
    # However, for 1-to-1, we can replicate the in-memory filtering if g.tasks is reliably populated at startup.
    # Let's assume g.tasks is the source of truth for viewing, as per original.
    # (Original main.py:1607-1616 filters g.tasks)
    
    tasks_to_display: List[Dict[str, Any]] = []
    for task_id, task_data in g.tasks.items():
        matches_agent = True
        if target_agent_id_for_filter and task_data.get("assigned_to") != target_agent_id_for_filter:
            matches_agent = False
        
        matches_status = True
        if filter_status and task_data.get("status") != filter_status:
            matches_status = False
            
        if matches_agent and matches_status:
            tasks_to_display.append(task_data)
            
    # Sort tasks, e.g., by creation date descending (optional improvement)
    tasks_to_display.sort(key=lambda t: t.get("created_at", ""), reverse=True)

    if not tasks_to_display: # main.py:1619
        response_text = "No tasks found matching the criteria."
    else: # main.py:1621-1651 (response formatting)
        response_parts = ["Tasks:\n"]
        for task in tasks_to_display:
            response_parts.append(f"\nID: {task.get('task_id', 'N/A')}")
            response_parts.append(f"Title: {task.get('title', 'N/A')}")
            response_parts.append(f"Description: {task.get('description', 'No description')}")
            response_parts.append(f"Status: {task.get('status', 'N/A')}")
            response_parts.append(f"Priority: {task.get('priority', 'medium')}")
            response_parts.append(f"Assigned to: {task.get('assigned_to', 'None')}")
            response_parts.append(f"Created by: {task.get('created_by', 'N/A')}")
            response_parts.append(f"Created: {task.get('created_at', 'N/A')}")
            response_parts.append(f"Updated: {task.get('updated_at', 'N/A')}")
            if task.get('parent_task'):
                response_parts.append(f"Parent task: {task['parent_task']}")
            
            child_tasks_val = task.get('child_tasks', []) # Expect list from g.tasks
            if isinstance(child_tasks_val, str): # Should not happen if g.tasks is well-maintained
                try: child_tasks_val = json.loads(child_tasks_val or "[]")
                except: child_tasks_val = ["Error decoding child_tasks"]
            if child_tasks_val:
                response_parts.append(f"Child tasks: {', '.join(child_tasks_val)}")

            notes_val = task.get('notes', []) # Expect list from g.tasks
            if isinstance(notes_val, str): # Should not happen
                try: notes_val = json.loads(notes_val or "[]")
                except: notes_val = [{"author": "System", "content": "Error decoding notes"}]
            if notes_val:
                response_parts.append("Notes:")
                for note in notes_val:
                    if isinstance(note, dict):
                        ts = note.get("timestamp", "Unknown time")
                        auth = note.get("author", "Unknown")
                        cont = note.get("content", "No content")
                        response_parts.append(f"  - [{ts}] {auth}: {cont}")
                    else:
                        response_parts.append(f"  - [Invalid Note Format: {str(note)}]")
        response_text = "\n".join(response_parts)

    log_audit(requesting_agent_id, "view_tasks", {"filter_agent_id": filter_agent_id, "filter_status": filter_status}) # main.py:1653
    return [mcp_types.TextContent(type="text", text=response_text)]


# --- request_assistance tool ---
# Original logic from main.py: lines 1658-1763 (request_assistance_tool function)
# This tool had file-based notification system. We'll replicate that for 1-to-1.
async def request_assistance_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    agent_auth_token = arguments.get("token")
    parent_task_id = arguments.get("task_id") # Task ID needing assistance
    assistance_description = arguments.get("description")

    requesting_agent_id = get_agent_id(agent_auth_token) # main.py:1666
    if not requesting_agent_id:
        return [mcp_types.TextContent(type="text", text="Unauthorized: Valid token required")]

    if not parent_task_id or not assistance_description:
        return [mcp_types.TextContent(type="text", text="Error: task_id (for parent) and description are required.")]

    # Fetch parent task data (original used in-memory g.tasks, main.py:1674)
    # For robustness, let's fetch from DB, then update g.tasks.
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (parent_task_id,))
        parent_task_db_row = cursor.fetchone()
        if not parent_task_db_row:
            return [mcp_types.TextContent(type="text", text=f"Parent task '{parent_task_id}' not found.")]
        
        parent_task_current_data = dict(parent_task_db_row)

        # Verify ownership or admin (main.py:1688-1691)
        is_admin_request = verify_token(agent_auth_token, "admin")
        if parent_task_current_data.get("assigned_to") != requesting_agent_id and not is_admin_request:
            return [mcp_types.TextContent(type="text", text="Unauthorized: You can only request assistance for tasks assigned to you, or use an admin token.")]

        # Create child assistance task (main.py:1694-1696)
        child_task_id = _generate_task_id()
        child_task_title = f"Assistance for {parent_task_id}: {parent_task_current_data.get('title', 'Untitled Task')}"
        timestamp_iso = datetime.datetime.now().isoformat()

        # Create notification for admin (main.py:1699-1710)
        # This part used file system notifications.
        notification_id = _generate_notification_id()
        notification_data = {
            "id": notification_id,
            "type": "assistance_request",
            "source_agent_id": requesting_agent_id,
            "task_id": parent_task_id, # Parent task
            "child_task_id": child_task_id, # The new assistance task
            "timestamp": timestamp_iso,
            "description": assistance_description,
            "status": "pending" # Notification status
        }
        
        # Save notification file (main.py:1713-1718)
        project_dir_env = os.environ.get("MCP_PROJECT_DIR")
        if not project_dir_env:
            logger.error("MCP_PROJECT_DIR not set. Cannot save assistance notification file.")
            # Decide if this is critical enough to stop. Original didn't explicitly stop.
        else:
            try:
                notifications_pending_dir = Path(project_dir_env) / ".agent" / "notifications" / "pending"
                notifications_pending_dir.mkdir(parents=True, exist_ok=True)
                notification_file_path = notifications_pending_dir / f"{notification_id}.json"
                with open(notification_file_path, "w", encoding='utf-8') as f:
                    json.dump(notification_data, f, indent=2)
                logger.info(f"Assistance request notification saved to {notification_file_path}")
            except Exception as e_notify:
                logger.error(f"Failed to save assistance notification file: {e_notify}", exc_info=True)

        # Insert the child (assistance) task into DB (main.py:1722-1734)
        child_task_db_data = {
            "task_id": child_task_id, "title": child_task_title, "description": assistance_description,
            "status": "pending", "assigned_to": None, "priority": "high", # Assistance tasks are high priority
            "created_at": timestamp_iso, "updated_at": timestamp_iso,
            "parent_task": parent_task_id, "depends_on_tasks": json.dumps([]),
            "created_by": requesting_agent_id, # The agent who requested assistance
            "child_tasks": json.dumps([]), "notes": json.dumps([])
        }
        cursor.execute("""
            INSERT INTO tasks (task_id, title, description, status, assigned_to, priority, created_at, 
                               updated_at, parent_task, depends_on_tasks, created_by, child_tasks, notes)
            VALUES (:task_id, :title, :description, :status, :assigned_to, :priority, :created_at, 
                    :updated_at, :parent_task, :depends_on_tasks, :created_by, :child_tasks, :notes)
        """, child_task_db_data)

        # Update parent task's child_tasks field and notes (main.py:1737-1764)
        parent_child_tasks_list = json.loads(parent_task_current_data.get("child_tasks") or "[]")
        parent_child_tasks_list.append(child_task_id)
        
        parent_notes_list = json.loads(parent_task_current_data.get("notes") or "[]")
        parent_notes_list.append({
            "timestamp": timestamp_iso,
            "author": requesting_agent_id,
            "content": f"Requested assistance: {assistance_description}. Assistance task created: {child_task_id}"
        })
        
        cursor.execute("UPDATE tasks SET child_tasks = ?, notes = ?, updated_at = ? WHERE task_id = ?",
                       (json.dumps(parent_child_tasks_list), json.dumps(parent_notes_list), timestamp_iso, parent_task_id))

        log_agent_action_to_db(cursor, requesting_agent_id, "request_assistance", task_id=parent_task_id,
                               details={"description": assistance_description, "child_task_id": child_task_id})
        conn.commit()

        # Update in-memory caches (g.tasks)
        # Parent task
        if parent_task_id in g.tasks:
            g.tasks[parent_task_id]["child_tasks"] = parent_child_tasks_list
            g.tasks[parent_task_id]["notes"] = parent_notes_list
            g.tasks[parent_task_id]["updated_at"] = timestamp_iso
        # New child task
        child_task_mem_data = child_task_db_data.copy()
        child_task_mem_data["depends_on_tasks"] = [] # from json.dumps([])
        child_task_mem_data["child_tasks"] = []
        child_task_mem_data["notes"] = []
        g.tasks[child_task_id] = child_task_mem_data
        
        # Original code also wrote parent and child task JSON files (main.py:1766-1771)
        # This was part of an older file-based task system. We are now DB-centric.
        # For 1-to-1, if those files are still used by something, they'd need to be written.
        # However, the primary task store is now the DB.
        # We will skip writing these individual task JSON files as they are redundant with the DB.
        # If get_task_file_path was used elsewhere, that system needs re-evaluation.

        log_audit(requesting_agent_id, "request_assistance", 
                  {"parent_task_id": parent_task_id, "child_task_id": child_task_id, "description": assistance_description})
        logger.info(f"Agent '{requesting_agent_id}' requested assistance for task '{parent_task_id}'. Child task '{child_task_id}' created.")
        return [mcp_types.TextContent(
            type="text",
            text=f"Assistance requested for task {parent_task_id}. Child assistance task {child_task_id} created and admin notified."
        )]

    except sqlite3.Error as e_sql:
        if conn: conn.rollback()
        logger.error(f"Database error requesting assistance for task {parent_task_id}: {e_sql}", exc_info=True)
        return [mcp_types.TextContent(type="text", text=f"Database error requesting assistance: {e_sql}")]
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Unexpected error requesting assistance for task {parent_task_id}: {e}", exc_info=True)
        return [mcp_types.TextContent(type="text", text=f"Unexpected error requesting assistance: {e}")]
    finally:
        if conn:
            conn.close()


# --- Register all task tools ---
def register_task_tools():
    register_tool(
        name="assign_task", # main.py:1700
        description="Admin tool to assign a task to an agent. IMPORTANT: parent_task_id is REQUIRED if any tasks already exist.",
        input_schema={ # From main.py:1701-1724
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "Admin authentication token"},
                "agent_id": {"type": "string", "description": "Agent ID to assign the task to"},
                "task_title": {"type": "string", "description": "Title of the task"},
                "task_description": {"type": "string", "description": "Detailed description of the task"},
                "priority": {
                    "type": "string", "description": "Task priority (low, medium, high)",
                    "enum": ["low", "medium", "high"], "default": "medium"
                },
                "depends_on_tasks": {
                    "type": "array", "description": "List of task IDs this task depends on (optional)",
                    "items": {"type": "string"}
                },
                "parent_task_id": {
                    "type": "string", 
                    "description": "ID of the parent task (REQUIRED if any tasks exist - only one root task allowed)"
                },
                "override_rag": {
                    "type": "boolean", 
                    "description": "Override RAG validation suggestions (optional, defaults to false - accepts suggestions)",
                    "default": False
                },
                "override_reason": {
                    "type": "string",
                    "description": "Reason for overriding RAG validation (required if override_rag is true)"
                }
            },
            "required": ["token", "agent_id", "task_title", "task_description"],
            "additionalProperties": False
        },
        implementation=assign_task_tool_impl
    )

    register_tool(
        name="create_self_task", # main.py:1726
        description="Agent tool to create a task for themselves. IMPORTANT: parent_task_id is REQUIRED - agents cannot create root tasks.",
        input_schema={ # From main.py:1727-1750
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "Agent authentication token"},
                "task_title": {"type": "string", "description": "Title of the task"},
                "task_description": {"type": "string", "description": "Detailed description of the task"},
                "priority": {
                    "type": "string", "description": "Task priority (low, medium, high)",
                    "enum": ["low", "medium", "high"], "default": "medium"
                },
                "depends_on_tasks": {
                    "type": "array", "description": "List of task IDs this task depends on (optional)",
                    "items": {"type": "string"}
                },
                "parent_task_id": {
                    "type": "string", 
                    "description": "ID of the parent task (defaults to agent's current task if not specified, but MUST have a parent)"
                }
            },
            "required": ["token", "task_title", "task_description"],
            "additionalProperties": False
        },
        implementation=create_self_task_tool_impl
    )

    register_tool(
        name="update_task_status", # main.py:1752
        description="Update the status and optionally other fields (admin only) of a task. Add notes about the update.",
        input_schema={ # From main.py:1753-1786
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "Authentication token (agent or admin)"},
                "task_id": {"type": "string", "description": "ID of the task to update"},
                "status": {
                    "type": "string", "description": "New status for the task",
                    "enum": ["pending", "in_progress", "completed", "cancelled", "failed"] # Added failed
                },
                "notes": {"type": "string", "description": "Optional notes about the status update to be appended."},
                # Admin Only Optional Fields
                "title": {"type": "string", "description": "(Admin Only) New title for the task"},
                "description": {"type": "string", "description": "(Admin Only) New description for the task"},
                "priority": {
                    "type": "string", "description": "(Admin Only) New priority",
                    "enum": ["low", "medium", "high"]
                },
                "assigned_to": {"type": "string", "description": "(Admin Only) New agent ID to assign the task to"},
                "depends_on_tasks": {
                    "type": "array", "description": "(Admin Only) New list of task IDs this task depends on",
                    "items": {"type": "string"}
                }
            },
            "required": ["token", "task_id", "status"],
            "additionalProperties": False
        },
        implementation=update_task_status_tool_impl
    )

    register_tool(
        name="view_tasks", # main.py:1788
        description="View tasks. Can be filtered by agent ID and/or status. Non-admins can only view their own tasks if agent_id is specified.",
        input_schema={ # From main.py:1789-1806
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "Authentication token"},
                "agent_id": {"type": "string", "description": "Filter tasks by agent ID (optional). If non-admin, can only be self."},
                "status": {
                    "type": "string", "description": "Filter tasks by status (optional)",
                    "enum": ["pending", "in_progress", "completed", "cancelled", "failed"] # Added failed
                }
            },
            "required": ["token"],
            "additionalProperties": False
        },
        implementation=view_tasks_tool_impl
    )

    register_tool(
        name="request_assistance", # main.py:1808
        description="Request assistance with a task. This creates a child task assigned to 'None' and notifies admin.",
        input_schema={ # From main.py:1809-1823
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "Agent authentication token"},
                "task_id": {"type": "string", "description": "ID of the task for which assistance is needed (parent task)."},
                "description": {"type": "string", "description": "Description of the assistance required."}
            },
            "required": ["token", "task_id", "description"],
            "additionalProperties": False
        },
        implementation=request_assistance_tool_impl
    )

# Call registration when this module is imported
register_task_tools()