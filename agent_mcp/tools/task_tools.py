# Agent-MCP/mcp_template/mcp_server_src/tools/task_tools.py
import json
import datetime
import secrets  # For task_id generation
import os  # For request_assistance (notifications path)
import sqlite3  # For database operations
from pathlib import Path  # For request_assistance
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
    should_escalate_to_admin,
)
from ..features.rag.indexing import index_task_data

# For request_assistance, generate_id was used. Let's use secrets.token_hex for consistency.
# from main.py:1191 (generate_id - not present, assuming secrets.token_hex was intended)
from .agent_communication_tools import send_agent_message_tool_impl


def estimate_tokens(text: str) -> int:
    """Accurate token estimation using tiktoken for GPT-4"""
    try:
        import tiktoken

        encoding = tiktoken.encoding_for_model("gpt-4")
        return len(encoding.encode(text))
    except ImportError:
        # Fallback to rough estimation if tiktoken not available
        return len(text) // 4
    except Exception:
        # Fallback for any other tiktoken errors
        return len(text) // 4


def _generate_task_id() -> str:
    """Generates a unique task ID."""
    return f"task_{secrets.token_hex(6)}"


def _generate_notification_id() -> str:
    """Generates a unique notification ID."""
    return f"notification_{secrets.token_hex(8)}"


async def _update_single_task(
    cursor,
    task_id: str,
    new_status: str,
    requesting_agent_id: str,
    is_admin_request: bool,
    notes_content: Optional[str] = None,
    new_title: Optional[str] = None,
    new_description: Optional[str] = None,
    new_priority: Optional[str] = None,
    new_assigned_to: Optional[str] = None,
    new_depends_on_tasks: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Helper function to update a single task with smart features"""

    # Fetch task current data
    cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
    task_db_row = cursor.fetchone()
    if not task_db_row:
        return {"success": False, "error": f"Task '{task_id}' not found"}

    task_current_data = dict(task_db_row)

    # Verify permissions
    if (
        task_current_data.get("assigned_to") != requesting_agent_id
        and not is_admin_request
    ):
        return {
            "success": False,
            "error": f"Unauthorized: Cannot update task '{task_id}' assigned to {task_current_data.get('assigned_to')}",
        }

    updated_at_iso = datetime.datetime.now().isoformat()

    # Build update query
    update_fields_sql = ["status = ?", "updated_at = ?"]
    update_params = [new_status, updated_at_iso]

    # Handle notes
    current_notes_list = json.loads(task_current_data.get("notes") or "[]")
    if notes_content:
        current_notes_list.append(
            {
                "timestamp": updated_at_iso,
                "author": requesting_agent_id,
                "content": notes_content,
            }
        )
    update_fields_sql.append("notes = ?")
    update_params.append(json.dumps(current_notes_list))

    # Admin-only field updates
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
        if new_assigned_to is not None:
            update_fields_sql.append("assigned_to = ?")
            update_params.append(new_assigned_to)
        if new_depends_on_tasks is not None:
            update_fields_sql.append("depends_on_tasks = ?")
            update_params.append(json.dumps(new_depends_on_tasks))

    update_params.append(task_id)

    # Execute update with validated field assignments
    if update_fields_sql:
        # Validate all field assignments are safe (contain only expected patterns)
        allowed_field_patterns = [
            "status = ?",
            "updated_at = ?",
            "notes = ?",
            "title = ?",
            "description = ?",
            "priority = ?",
            "assigned_to = ?",
            "depends_on_tasks = ?",
        ]

        safe_fields = []
        for field in update_fields_sql:
            if field in allowed_field_patterns:
                safe_fields.append(field)
            else:
                logger.warning(
                    f"Task update: Skipping unsafe field assignment: {field}"
                )

        if safe_fields:
            set_clause = ", ".join(safe_fields)
            update_sql = f"UPDATE tasks SET {set_clause} WHERE task_id = ?"
            cursor.execute(update_sql, tuple(update_params))

    # Update in-memory cache
    if task_id in g.tasks:
        g.tasks[task_id]["status"] = new_status
        g.tasks[task_id]["updated_at"] = updated_at_iso
        g.tasks[task_id]["notes"] = current_notes_list
        if is_admin_request:
            if new_title is not None:
                g.tasks[task_id]["title"] = new_title
            if new_description is not None:
                g.tasks[task_id]["description"] = new_description
            if new_priority is not None:
                g.tasks[task_id]["priority"] = new_priority
            if new_assigned_to is not None:
                g.tasks[task_id]["assigned_to"] = new_assigned_to
            if new_depends_on_tasks is not None:
                g.tasks[task_id]["depends_on_tasks"] = new_depends_on_tasks

    # Handle parent task notifications
    if new_status in ["completed", "cancelled", "failed"] and task_current_data.get(
        "parent_task"
    ):
        parent_task_id = task_current_data["parent_task"]
        cursor.execute("SELECT notes FROM tasks WHERE task_id = ?", (parent_task_id,))
        parent_row = cursor.fetchone()
        if parent_row:
            parent_notes_list = json.loads(parent_row["notes"] or "[]")
            parent_notes_list.append(
                {
                    "timestamp": updated_at_iso,
                    "author": "system",
                    "content": f"Subtask '{task_id}' ({task_current_data.get('title', '')}) status changed to: {new_status}",
                }
            )
            cursor.execute(
                "UPDATE tasks SET notes = ?, updated_at = ? WHERE task_id = ?",
                (json.dumps(parent_notes_list), updated_at_iso, parent_task_id),
            )
            if parent_task_id in g.tasks:
                g.tasks[parent_task_id]["notes"] = parent_notes_list
                g.tasks[parent_task_id]["updated_at"] = updated_at_iso

    return {
        "success": True,
        "task_id": task_id,
        "old_status": task_current_data.get("status"),
        "new_status": new_status,
        "child_tasks": json.loads(task_current_data.get("child_tasks") or "[]"),
        "depends_on_tasks": json.loads(
            task_current_data.get("depends_on_tasks") or "[]"
        ),
    }


def _analyze_task_dependencies(
    task: Dict[str, Any], all_tasks: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """Analyze task dependencies and blocking conditions"""
    task_id = task.get("task_id")
    status = task.get("status")
    depends_on = task.get("depends_on_tasks", [])

    if isinstance(depends_on, str):
        try:
            depends_on = json.loads(depends_on)
        except:
            depends_on = []

    analysis = {
        "is_blocked": False,
        "blocking_dependencies": [],
        "completed_dependencies": [],
        "missing_dependencies": [],
        "can_start": True,
        "blocks_tasks": [],
        "dependency_health": "healthy",
    }

    # Check dependencies
    for dep_id in depends_on:
        if dep_id in all_tasks:
            dep_task = all_tasks[dep_id]
            dep_status = dep_task.get("status")

            if dep_status == "completed":
                analysis["completed_dependencies"].append(dep_id)
            elif dep_status in ["failed", "cancelled"]:
                analysis["blocking_dependencies"].append(dep_id)
                analysis["is_blocked"] = True
                analysis["can_start"] = False
            elif dep_status in ["pending", "in_progress"]:
                analysis["blocking_dependencies"].append(dep_id)
                if status == "pending":
                    analysis["can_start"] = False
        else:
            analysis["missing_dependencies"].append(dep_id)
            analysis["is_blocked"] = True
            analysis["can_start"] = False

    # Find tasks that depend on this one
    for other_id, other_task in all_tasks.items():
        other_deps = other_task.get("depends_on_tasks", [])
        if isinstance(other_deps, str):
            try:
                other_deps = json.loads(other_deps)
            except:
                other_deps = []

        if task_id in other_deps:
            analysis["blocks_tasks"].append(other_id)

    # Determine health
    if analysis["missing_dependencies"]:
        analysis["dependency_health"] = "critical"
    elif analysis["is_blocked"] and status == "in_progress":
        analysis["dependency_health"] = "warning"
    elif not analysis["can_start"] and status == "pending":
        analysis["dependency_health"] = "waiting"

    return analysis


def _calculate_task_health_metrics(tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate overall task health metrics"""
    if not tasks:
        return {"total": 0, "status": "no_data"}

    total = len(tasks)
    status_counts = {}
    priority_counts = {}
    blocked_count = 0
    overdue_count = 0
    stale_count = 0

    current_time = datetime.datetime.now()

    for task in tasks:
        # Status distribution
        status = task.get("status", "unknown")
        status_counts[status] = status_counts.get(status, 0) + 1

        # Priority distribution
        priority = task.get("priority", "medium")
        priority_counts[priority] = priority_counts.get(priority, 0) + 1

        # Check for blocked tasks (has dependencies but can't proceed)
        deps = task.get("depends_on_tasks", [])
        if isinstance(deps, str):
            try:
                deps = json.loads(deps)
            except:
                deps = []

        if deps and status == "pending":
            blocked_count += 1

        # Check for stale tasks (no updates in 7+ days)
        updated_at = task.get("updated_at")
        if updated_at:
            try:
                updated_time = datetime.datetime.fromisoformat(
                    updated_at.replace("Z", "+00:00").replace("+00:00", "")
                )
                days_since_update = (current_time - updated_time).days
                if days_since_update > 7 and status in ["in_progress", "pending"]:
                    stale_count += 1
            except:
                pass

    # Calculate health score (0-100)
    completed_ratio = status_counts.get("completed", 0) / total
    active_ratio = (
        status_counts.get("in_progress", 0) + status_counts.get("pending", 0)
    ) / total
    blocked_ratio = blocked_count / total if total > 0 else 0
    stale_ratio = stale_count / total if total > 0 else 0

    health_score = max(
        0,
        min(
            100,
            completed_ratio * 30  # 30% weight for completion
            + active_ratio * 40  # 40% weight for active work
            + (1 - blocked_ratio) * 20  # 20% penalty for blocked tasks
            + (1 - stale_ratio) * 10,  # 10% penalty for stale tasks
        ),
    )

    return {
        "total": total,
        "status_distribution": status_counts,
        "priority_distribution": priority_counts,
        "blocked_tasks": blocked_count,
        "stale_tasks": stale_count,
        "health_score": round(health_score, 1),
        "health_status": (
            "excellent"
            if health_score >= 80
            else (
                "good"
                if health_score >= 60
                else "needs_attention" if health_score >= 40 else "critical"
            )
        ),
    }


# --- Helper functions for assign_task modes ---


async def _create_unassigned_tasks(
    arguments: Dict[str, Any],
) -> List[mcp_types.TextContent]:
    """Mode 0: Create unassigned tasks (assigned_to = NULL)"""
    task_title = arguments.get("task_title")
    task_description = arguments.get("task_description")
    tasks = arguments.get("tasks")
    priority = arguments.get("priority", "medium")
    parent_task_id_arg = arguments.get("parent_task_id")

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        created_tasks = []
        created_at = datetime.datetime.now().isoformat()

        if tasks:
            # Multiple unassigned task creation
            for i, task in enumerate(tasks):
                task_id = f"task_{int(datetime.datetime.now().timestamp() * 1000)}_{i}"
                title = task["title"]
                description = task["description"]
                task_priority = task.get("priority", "medium")
                parent_task = task.get("parent_task_id")

                # Create unassigned task
                task_data = {
                    "task_id": task_id,
                    "title": title,
                    "description": description,
                    "assigned_to": None,  # UNASSIGNED
                    "created_by": "admin",
                    "status": "unassigned",
                    "priority": task_priority,
                    "created_at": created_at,
                    "updated_at": created_at,
                    "parent_task": parent_task,
                    "child_tasks": json.dumps([]),
                    "depends_on_tasks": json.dumps([]),
                    "notes": json.dumps([]),
                }

                cursor.execute(
                    """
                    INSERT INTO tasks (task_id, title, description, assigned_to, created_by, status, priority, 
                                       created_at, updated_at, parent_task, child_tasks, depends_on_tasks, notes)
                    VALUES (:task_id, :title, :description, :assigned_to, :created_by, :status, :priority, 
                            :created_at, :updated_at, :parent_task, :child_tasks, :depends_on_tasks, :notes)
                """,
                    task_data,
                )

                log_agent_action_to_db(
                    cursor,
                    "admin",
                    "created_unassigned_task",
                    task_id=task_id,
                    details={"title": title, "mode": "unassigned_multiple"},
                )

                created_tasks.append(
                    {"task_id": task_id, "title": title, "priority": task_priority}
                )

        elif task_title and task_description:
            # Single unassigned task creation
            task_id = f"task_{int(datetime.datetime.now().timestamp() * 1000)}"

            task_data = {
                "task_id": task_id,
                "title": task_title,
                "description": task_description,
                "assigned_to": None,  # UNASSIGNED
                "created_by": "admin",
                "status": "unassigned",
                "priority": priority,
                "created_at": created_at,
                "updated_at": created_at,
                "parent_task": parent_task_id_arg,
                "child_tasks": json.dumps([]),
                "depends_on_tasks": json.dumps([]),
                "notes": json.dumps([]),
            }

            cursor.execute(
                """
                INSERT INTO tasks (task_id, title, description, assigned_to, created_by, status, priority, 
                                   created_at, updated_at, parent_task, child_tasks, depends_on_tasks, notes)
                VALUES (:task_id, :title, :description, :assigned_to, :created_by, :status, :priority, 
                        :created_at, :updated_at, :parent_task, :child_tasks, :depends_on_tasks, :notes)
            """,
                task_data,
            )

            log_agent_action_to_db(
                cursor,
                "admin",
                "created_unassigned_task",
                task_id=task_id,
                details={"title": task_title, "mode": "unassigned_single"},
            )

            created_tasks.append(
                {"task_id": task_id, "title": task_title, "priority": priority}
            )

        else:
            return [
                mcp_types.TextContent(
                    type="text",
                    text="Error: Provide either 'task_title' and 'task_description' for single task, or 'tasks' array for multiple tasks.",
                )
            ]

        conn.commit()

        # Build response
        response_parts = [
            f"✅ **Unassigned Tasks Created**",
            f"   Tasks Created: {len(created_tasks)}",
            f"   Status: Pending assignment",
            "",
        ]

        for i, task in enumerate(created_tasks, 1):
            response_parts.append(
                f"   {i}. {task['task_id']}: {task['title']} (Priority: {task['priority']})"
            )

        response_parts.append(
            "\n💡 Use assign_task with task_ids parameter to assign these tasks to agents."
        )

        return [mcp_types.TextContent(type="text", text="\n".join(response_parts))]

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error creating unassigned tasks: {e}", exc_info=True)
        return [
            mcp_types.TextContent(
                type="text", text=f"Error creating unassigned tasks: {e}"
            )
        ]
    finally:
        if conn:
            conn.close()


async def _assign_to_existing_tasks(
    arguments: Dict[str, Any],
    target_agent_id: str,
    task_ids: List[str],
    validate_agent_workload: bool,
    coordination_notes: str,
) -> List[mcp_types.TextContent]:
    """Mode 3: Assign agent to existing unassigned tasks"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Validate that all tasks exist and are unassigned
        placeholders = ",".join(["?" for _ in task_ids])
        cursor.execute(
            f"SELECT task_id, title, assigned_to FROM tasks WHERE task_id IN ({placeholders})",
            task_ids,
        )
        found_tasks = cursor.fetchall()

        if len(found_tasks) != len(task_ids):
            found_ids = [task["task_id"] for task in found_tasks]
            missing_ids = [tid for tid in task_ids if tid not in found_ids]
            return [
                mcp_types.TextContent(
                    type="text",
                    text=f"Error: Tasks not found: {', '.join(missing_ids)}",
                )
            ]

        # Check for already assigned tasks
        assigned_tasks = [
            task for task in found_tasks if task["assigned_to"] is not None
        ]
        if assigned_tasks:
            assigned_list = [
                f"{task['task_id']} (assigned to {task['assigned_to']})"
                for task in assigned_tasks
            ]
            return [
                mcp_types.TextContent(
                    type="text",
                    text=f"Error: Some tasks are already assigned: {', '.join(assigned_list)}",
                )
            ]

        # Validate agent exists
        cursor.execute(
            "SELECT agent_id FROM agents WHERE agent_id = ?", (target_agent_id,)
        )
        if not cursor.fetchone():
            return [
                mcp_types.TextContent(
                    type="text", text=f"Error: Agent '{target_agent_id}' not found."
                )
            ]

        # Assign all tasks to the agent
        updated_at = datetime.datetime.now().isoformat()
        for task_id in task_ids:
            cursor.execute(
                "UPDATE tasks SET assigned_to = ?, updated_at = ? WHERE task_id = ?",
                (target_agent_id, updated_at, task_id),
            )

            # Log the assignment
            log_agent_action_to_db(
                cursor,
                "admin",
                "assigned_task",
                task_id=task_id,
                details={
                    "agent_id": target_agent_id,
                    "mode": "existing_task_assignment",
                },
            )

        # Update agent's current task if they don't have one (use first task)
        cursor.execute(
            "SELECT current_task FROM agents WHERE agent_id = ?", (target_agent_id,)
        )
        agent_row = cursor.fetchone()
        if agent_row and agent_row["current_task"] is None:
            cursor.execute(
                "UPDATE agents SET current_task = ?, updated_at = ? WHERE agent_id = ?",
                (task_ids[0], updated_at, target_agent_id),
            )

        conn.commit()

        # Build response
        task_titles = [task["title"] for task in found_tasks]
        response_parts = [
            f"✅ **Tasks Assigned Successfully**",
            f"   Agent: {target_agent_id}",
            f"   Tasks Assigned: {len(task_ids)}",
            "",
        ]

        for i, (task_id, title) in enumerate(zip(task_ids, task_titles), 1):
            response_parts.append(f"   {i}. {task_id}: {title}")

        if coordination_notes:
            response_parts.append(f"\n📋 **Coordination Notes:** {coordination_notes}")

        return [mcp_types.TextContent(type="text", text="\n".join(response_parts))]

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error assigning existing tasks: {e}", exc_info=True)
        return [mcp_types.TextContent(type="text", text=f"Error assigning tasks: {e}")]
    finally:
        if conn:
            conn.close()


async def _create_and_assign_multiple_tasks(
    arguments: Dict[str, Any],
    target_agent_id: str,
    tasks: List[Dict[str, Any]],
    auto_suggest_parent: bool,
    validate_agent_workload: bool,
    coordination_notes: str,
) -> List[mcp_types.TextContent]:
    """Mode 2: Create multiple tasks and assign to agent"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Validate agent exists
        cursor.execute(
            "SELECT agent_id FROM agents WHERE agent_id = ?", (target_agent_id,)
        )
        if not cursor.fetchone():
            return [
                mcp_types.TextContent(
                    type="text", text=f"Error: Agent '{target_agent_id}' not found."
                )
            ]

        created_tasks = []
        created_at = datetime.datetime.now().isoformat()

        # Create each task
        for i, task in enumerate(tasks):
            task_id = f"task_{int(datetime.datetime.now().timestamp() * 1000)}_{i}"
            title = task["title"]
            description = task["description"]
            priority = task.get("priority", "medium")
            parent_task = task.get("parent_task_id")

            # Create task data
            task_data = {
                "task_id": task_id,
                "title": title,
                "description": description,
                "assigned_to": target_agent_id,
                "created_by": "admin",
                "status": "pending",
                "priority": priority,
                "created_at": created_at,
                "updated_at": created_at,
                "parent_task": parent_task,
                "child_tasks": json.dumps([]),
                "depends_on_tasks": json.dumps([]),
                "notes": json.dumps([]),
            }

            # Insert task
            cursor.execute(
                """
                INSERT INTO tasks (task_id, title, description, assigned_to, created_by, status, priority, 
                                   created_at, updated_at, parent_task, child_tasks, depends_on_tasks, notes)
                VALUES (:task_id, :title, :description, :assigned_to, :created_by, :status, :priority, 
                        :created_at, :updated_at, :parent_task, :child_tasks, :depends_on_tasks, :notes)
            """,
                task_data,
            )

            # Log the creation
            log_agent_action_to_db(
                cursor,
                "admin",
                "assigned_task",
                task_id=task_id,
                details={
                    "agent_id": target_agent_id,
                    "title": title,
                    "mode": "multiple_task_creation",
                },
            )

            created_tasks.append(
                {"task_id": task_id, "title": title, "priority": priority}
            )

        # Update agent's current task if they don't have one (use first task)
        cursor.execute(
            "SELECT current_task FROM agents WHERE agent_id = ?", (target_agent_id,)
        )
        agent_row = cursor.fetchone()
        if agent_row and agent_row["current_task"] is None and created_tasks:
            cursor.execute(
                "UPDATE agents SET current_task = ?, updated_at = ? WHERE agent_id = ?",
                (created_tasks[0]["task_id"], created_at, target_agent_id),
            )

        conn.commit()

        # Build response
        response_parts = [
            f"✅ **Multiple Tasks Created and Assigned**",
            f"   Agent: {target_agent_id}",
            f"   Tasks Created: {len(created_tasks)}",
            "",
        ]

        for i, task in enumerate(created_tasks, 1):
            response_parts.append(
                f"   {i}. {task['task_id']}: {task['title']} (Priority: {task['priority']})"
            )

        if coordination_notes:
            response_parts.append(f"\n📋 **Coordination Notes:** {coordination_notes}")

        return [mcp_types.TextContent(type="text", text="\n".join(response_parts))]

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error creating multiple tasks: {e}", exc_info=True)
        return [
            mcp_types.TextContent(
                type="text", text=f"Error creating multiple tasks: {e}"
            )
        ]
    finally:
        if conn:
            conn.close()


# --- assign_task tool ---
# Original logic from main.py: lines 1319-1384 (assign_task_tool function)
async def assign_task_tool_impl(
    arguments: Dict[str, Any],
) -> List[mcp_types.TextContent]:
    admin_auth_token = arguments.get("token")
    target_agent_token = arguments.get("agent_token")

    # Mode 1: Single task creation (existing behavior)
    task_title = arguments.get("task_title")
    task_description = arguments.get("task_description")
    priority = arguments.get("priority", "medium")  # Default from schema
    depends_on_tasks_list = arguments.get("depends_on_tasks")  # List[str] or None
    parent_task_id_arg = arguments.get("parent_task_id")  # Optional str

    # Mode 2: Multiple task creation (new)
    tasks = arguments.get("tasks")  # List[Dict] with task details

    # Mode 3: Existing task assignment (new)
    task_ids = arguments.get("task_ids")  # List[str] of existing task IDs

    # Smart coordination features
    auto_suggest_parent = arguments.get(
        "auto_suggest_parent", True
    )  # Auto-suggest parent tasks
    validate_agent_workload = arguments.get(
        "validate_agent_workload", True
    )  # Check agent capacity
    auto_schedule = arguments.get(
        "auto_schedule", False
    )  # Auto-schedule based on dependencies
    coordination_notes = arguments.get(
        "coordination_notes"
    )  # Optional coordination context
    estimated_hours = arguments.get("estimated_hours")  # Optional workload estimation

    if not verify_token(admin_auth_token, "admin"):  # main.py:1326
        return [
            mcp_types.TextContent(
                type="text", text="Unauthorized: Admin token required"
            )
        ]

    # Handle unassigned task creation (agent_token is optional)
    if not target_agent_token:
        # Mode 0: Create unassigned tasks
        return await _create_unassigned_tasks(arguments)

    # Convert agent_token to agent_id and validate agent
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Find agent by token
        cursor.execute(
            "SELECT agent_id FROM agents WHERE token = ?", (target_agent_token,)
        )
        agent_row = cursor.fetchone()
        if not agent_row:
            conn.close()
            return [
                mcp_types.TextContent(
                    type="text",
                    text="Error: Agent token not found. Agent may not exist or token is invalid.",
                )
            ]

        target_agent_id = agent_row["agent_id"]

        # Prevent admin agents from being assigned tasks
        if target_agent_id.lower().startswith("admin"):
            conn.close()
            return [
                mcp_types.TextContent(
                    type="text",
                    text="Error: Admin agents cannot be assigned tasks. Admin agents are for coordination and management only.",
                )
            ]

    except Exception as e:
        conn.close()
        logger.error(f"Error validating agent token: {e}", exc_info=True)
        return [mcp_types.TextContent(type="text", text=f"Error validating agent: {e}")]
    finally:
        conn.close()

    # Determine operation mode and validate parameters (when agent_token provided)
    if task_ids:
        # Mode 3: Assign to existing tasks
        operation_mode = "existing"
        if not isinstance(task_ids, list) or not task_ids:
            return [
                mcp_types.TextContent(
                    type="text",
                    text="Error: task_ids must be a non-empty list of task IDs.",
                )
            ]
    elif tasks:
        # Mode 2: Create multiple tasks + assign
        operation_mode = "multiple"
        if not isinstance(tasks, list) or not tasks:
            return [
                mcp_types.TextContent(
                    type="text",
                    text="Error: tasks must be a non-empty list of task objects.",
                )
            ]
        # Validate each task object
        for i, task in enumerate(tasks):
            if not isinstance(task, dict) or not all(
                [task.get("title"), task.get("description")]
            ):
                return [
                    mcp_types.TextContent(
                        type="text",
                        text=f"Error: Task {i+1} must have 'title' and 'description' fields.",
                    )
                ]
    else:
        # Mode 1: Single task creation (existing behavior)
        operation_mode = "single"
        if not all([task_title, task_description]):
            return [
                mcp_types.TextContent(
                    type="text",
                    text="Error: task_title and task_description are required for single task creation, or provide 'tasks' array for multiple tasks, or 'task_ids' for existing task assignment.",
                )
            ]

    # Route to appropriate handler based on operation mode
    if operation_mode == "existing":
        return await _assign_to_existing_tasks(
            arguments,
            target_agent_id,
            task_ids,
            validate_agent_workload,
            coordination_notes,
        )
    elif operation_mode == "multiple":
        return await _create_and_assign_multiple_tasks(
            arguments,
            target_agent_id,
            tasks,
            auto_suggest_parent,
            validate_agent_workload,
            coordination_notes,
        )
    else:
        # operation_mode == "single" - continue with existing logic
        pass

    # Enforce single root task rule BEFORE any processing (Mode 1: Single task)
    if parent_task_id_arg is None:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) as count, GROUP_CONCAT(task_id) as root_ids FROM tasks WHERE parent_task IS NULL"
        )
        result = cursor.fetchone()
        root_count = result["count"]
        root_ids = result["root_ids"]

        if root_count > 0:
            if auto_suggest_parent:
                # Use smart parent suggestion
                parent_suggestions = _suggest_optimal_parent_task(
                    cursor, target_agent_id, task_description
                )

                suggestion_text = "\n🧠 **Smart Parent Suggestions:**\n"
                if parent_suggestions["has_suggestions"]:
                    for i, suggestion in enumerate(
                        parent_suggestions["suggestions"], 1
                    ):
                        suggestion_text += (
                            f"  {i}. {suggestion['task_id']}: {suggestion['title']}\n"
                        )
                        suggestion_text += f"     Status: {suggestion['status']} | Priority: {suggestion['priority']} | {suggestion['reason']}\n"
                else:
                    # Fallback to basic suggestions
                    cursor.execute(
                        """
                        SELECT task_id, title, status 
                        FROM tasks 
                        WHERE status IN ('pending', 'in_progress') AND assigned_to = ?
                        ORDER BY updated_at DESC
                        LIMIT 3
                    """,
                        (target_agent_id,),
                    )

                    basic_suggestions = cursor.fetchall()
                    if basic_suggestions:
                        suggestion_text += "  Based on agent's recent tasks:\n"
                        for task in basic_suggestions:
                            suggestion_text += f"  - {task['task_id']}: {task['title']} (status: {task['status']})\n"
                    else:
                        suggestion_text += (
                            "  No suitable parent tasks found for this agent.\n"
                        )
                        suggestion_text += "  Consider assigning to a different agent with active tasks.\n"
            else:
                # Basic suggestion fallback
                cursor.execute(
                    """
                    SELECT task_id, title, status 
                    FROM tasks 
                    WHERE status IN ('pending', 'in_progress')
                    ORDER BY 
                        CASE WHEN assigned_to = ? THEN 0 ELSE 1 END,
                        created_at DESC
                    LIMIT 5
                """,
                    (target_agent_id,),
                )

                suggestions = cursor.fetchall()
                suggestion_text = "\nSuggested parent tasks:\n"
                for task in suggestions:
                    suggestion_text += f"  - {task['task_id']}: {task['title']} (status: {task['status']})\n"

            conn.close()

            return [
                mcp_types.TextContent(
                    type="text",
                    text=f"ERROR: Cannot create task without parent. {root_count} root task(s) already exist: {root_ids}\n\n"
                    f"You MUST specify a parent_task_id. Every task except the first must have a parent.\n"
                    f"{suggestion_text}\n"
                    f"💡 Use auto_suggest_parent=true for smarter suggestions based on task content.\n"
                    f"Use 'view_tasks' for complete task list, or use one of the suggestions above.",
                )
            ]

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
            cursor.execute(
                "SELECT token FROM agents WHERE agent_id = ? AND status != ?",
                (target_agent_id, "terminated"),
            )
            row = cursor.fetchone()
            if not row:
                return [
                    mcp_types.TextContent(
                        type="text",
                        text=f"Agent '{target_agent_id}' not found or is terminated.",
                    )
                ]
            # Agent exists in DB but not memory, can still assign task.
            logger.warning(
                f"Assigning task to agent {target_agent_id} found in DB but not active memory."
            )
            # assigned_agent_active_token remains None if not in active_agents

        # Generate task ID and timestamps first
        new_task_id = _generate_task_id()
        created_at_iso = datetime.datetime.now().isoformat()
        status = "pending"

        # Check single root task rule
        if parent_task_id_arg is None:
            cursor.execute(
                "SELECT COUNT(*) as count, MIN(task_id) as root_id FROM tasks WHERE parent_task IS NULL"
            )
            result = cursor.fetchone()
            root_count = result["count"]
            existing_root_id = result["root_id"]

            if root_count > 0:
                logger.error(
                    f"Attempt to create second root task. Existing root: {existing_root_id}"
                )
                return [
                    mcp_types.TextContent(
                        type="text",
                        text=f"ERROR: Cannot create root task. A root task already exists ({existing_root_id}). All new tasks must have a parent.",
                    )
                ]

        # Smart workload validation
        workload_analysis = None
        workload_warnings = []

        if validate_agent_workload:
            workload_analysis = _analyze_agent_workload(cursor, target_agent_id)

            if not workload_analysis["can_take_new_task"]:
                warning_msg = (
                    f"⚠️ Agent workload warning: {workload_analysis['capacity_status']} "
                )
                warning_msg += (
                    f"({workload_analysis['total_active_tasks']} active tasks, "
                )
                warning_msg += (
                    f"{workload_analysis['high_priority_tasks']} high priority)"
                )
                workload_warnings.append(warning_msg)

                if workload_analysis["recommendations"]:
                    workload_warnings.extend(
                        [
                            f"   💡 {rec}"
                            for rec in workload_analysis["recommendations"][:2]
                        ]
                    )

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
                auth_token=admin_auth_token,
            )

            suggestion_message = format_suggestions_for_agent(
                validation_result, parent_task_id_arg, depends_on_tasks_list
            )

            # For denied status, block creation unless override is allowed
            if validation_result["status"] == "denied" and not ALLOW_RAG_OVERRIDE:
                return [
                    mcp_types.TextContent(
                        type="text",
                        text=f"Task creation BLOCKED by RAG validation:\n{suggestion_message}",
                    )
                ]

            # Process suggestions - always apply them unless explicitly overridden
            if validation_result["status"] != "approved":
                validation_message = f"\nRAG Validation ({validation_result['status']}):\n{suggestion_message}\n"

                # Apply suggestions by default (agent should see this behavior)
                suggestions = validation_result["suggestions"]
                if suggestions.get("parent_task") is not None:
                    final_parent_task_id = suggestions["parent_task"]
                    validation_message += (
                        f"✓ Applied suggested parent: {final_parent_task_id}\n"
                    )
                if suggestions.get("dependencies"):
                    final_depends_on_tasks = suggestions["dependencies"]
                    validation_message += (
                        f"✓ Applied suggested dependencies: {final_depends_on_tasks}\n"
                    )

                logger.info(
                    f"RAG suggestions automatically applied for task {new_task_id}"
                )
            else:
                validation_message = "\n✓ RAG validation approved placement\n"

        # Build initial notes with coordination information
        initial_notes = []

        # Add coordination notes if provided
        if coordination_notes:
            initial_notes.append(
                {
                    "timestamp": created_at_iso,
                    "author": "admin",
                    "content": f"📋 Coordination: {coordination_notes}",
                }
            )

        # Add workload information
        if workload_analysis:
            workload_note = (
                f"👤 Agent workload: {workload_analysis['capacity_status']} "
            )
            workload_note += f"({workload_analysis['total_active_tasks']} active tasks)"
            if estimated_hours:
                workload_note += f" | Estimated: {estimated_hours}h"
            initial_notes.append(
                {
                    "timestamp": created_at_iso,
                    "author": "system",
                    "content": workload_note,
                }
            )

        # Add smart parent suggestion note if used
        if auto_suggest_parent and final_parent_task_id:
            initial_notes.append(
                {
                    "timestamp": created_at_iso,
                    "author": "system",
                    "content": f"🧠 Smart assignment: Parent task suggested based on content similarity",
                }
            )

        task_data_for_db = {  # main.py:1354-1367
            "task_id": new_task_id,
            "title": task_title,
            "description": task_description,
            "assigned_to": target_agent_id,
            "created_by": "admin",  # Admin is assigning
            "status": status,
            "priority": priority,
            "created_at": created_at_iso,
            "updated_at": created_at_iso,
            "parent_task": final_parent_task_id,  # Use validated value
            "child_tasks": json.dumps([]),
            "depends_on_tasks": json.dumps(
                final_depends_on_tasks or []
            ),  # Use validated value
            "notes": json.dumps(initial_notes),
        }

        # Save task to database (main.py:1370-1373)
        cursor.execute(
            """
            INSERT INTO tasks (task_id, title, description, assigned_to, created_by, status, priority, 
                               created_at, updated_at, parent_task, child_tasks, depends_on_tasks, notes)
            VALUES (:task_id, :title, :description, :assigned_to, :created_by, :status, :priority, 
                    :created_at, :updated_at, :parent_task, :child_tasks, :depends_on_tasks, :notes)
        """,
            task_data_for_db,
        )

        # Update agent's current task in DB if they don't have one (main.py:1376-1387)
        should_update_agent_current_task = False
        if (
            assigned_agent_active_token
            and assigned_agent_active_token in g.active_agents
        ):
            if g.active_agents[assigned_agent_active_token].get("current_task") is None:
                should_update_agent_current_task = True
        else:  # Agent not in active memory, check DB
            cursor.execute(
                "SELECT current_task FROM agents WHERE agent_id = ?", (target_agent_id,)
            )
            agent_row = cursor.fetchone()
            if agent_row and agent_row["current_task"] is None:
                should_update_agent_current_task = True

        if should_update_agent_current_task:
            cursor.execute(
                "UPDATE agents SET current_task = ?, updated_at = ? WHERE agent_id = ?",
                (new_task_id, created_at_iso, target_agent_id),
            )

        log_agent_action_to_db(
            cursor,
            "admin",
            "assigned_task",
            task_id=new_task_id,
            details={"agent_id": target_agent_id, "title": task_title},
        )
        conn.commit()

        # Update agent's current task in memory if needed (main.py:1390-1391)
        if (
            should_update_agent_current_task
            and assigned_agent_active_token
            and assigned_agent_active_token in g.active_agents
        ):
            g.active_agents[assigned_agent_active_token]["current_task"] = new_task_id

        # Add task to in-memory tasks dictionary (main.py:1394-1398)
        # Convert JSON strings back for in-memory representation
        task_data_for_memory = task_data_for_db.copy()
        task_data_for_memory["child_tasks"] = []
        task_data_for_memory["depends_on_tasks"] = (
            final_depends_on_tasks or []
        )  # Use validated value
        task_data_for_memory["notes"] = []
        g.tasks[new_task_id] = task_data_for_memory

        # System 8: Index the new task for RAG
        # Convert database format to the format expected by indexing
        index_data = task_data_for_memory.copy()
        index_data["depends_on_tasks"] = final_depends_on_tasks or []
        # Start indexing asynchronously (fire and forget)
        import asyncio

        asyncio.create_task(index_task_data(new_task_id, index_data))

        log_audit(
            "admin",
            "assign_task",
            {"task_id": new_task_id, "agent_id": target_agent_id, "title": task_title},
        )  # main.py:1404
        logger.info(
            f"Task '{new_task_id}' ({task_title}) assigned to agent '{target_agent_id}'."
        )

        # Build comprehensive response
        response_parts = [f"✅ **Task Assigned Successfully**"]
        response_parts.append(f"   Task ID: {new_task_id}")
        response_parts.append(f"   Title: {task_title}")
        response_parts.append(f"   Agent: {target_agent_id}")
        response_parts.append(f"   Priority: {priority}")

        if final_parent_task_id:
            response_parts.append(f"   Parent: {final_parent_task_id}")

        if final_depends_on_tasks:
            response_parts.append(
                f"   Dependencies: {', '.join(final_depends_on_tasks)}"
            )

        if estimated_hours:
            response_parts.append(f"   Estimated: {estimated_hours} hours")

        # Add workload analysis
        if workload_analysis:
            response_parts.append("")
            capacity_icon = (
                "🟢"
                if workload_analysis["capacity_status"] == "available"
                else "🟡" if workload_analysis["capacity_status"] == "busy" else "🔴"
            )
            response_parts.append(
                f"👤 **Agent Workload:** {capacity_icon} {workload_analysis['capacity_status'].title()}"
            )
            response_parts.append(
                f"   Active Tasks: {workload_analysis['total_active_tasks']} ({workload_analysis['high_priority_tasks']} high priority)"
            )

            if workload_warnings:
                response_parts.extend(workload_warnings)

        # Add RAG validation info
        if validation_performed and validation_message:
            response_parts.append(validation_message)

        # Add coordination info
        if coordination_notes:
            response_parts.append(f"\n📋 **Coordination Notes:** {coordination_notes}")

        # Add smart feature usage tips
        response_parts.append("\n💡 **Smart Features Used:**")
        if auto_suggest_parent:
            response_parts.append(
                "• Smart parent suggestion based on content similarity"
            )
        if validate_agent_workload:
            response_parts.append("• Agent workload analysis and capacity checking")
        if coordination_notes:
            response_parts.append("• Coordination context captured for team awareness")

        return [mcp_types.TextContent(type="text", text="\n".join(response_parts))]

    except sqlite3.Error as e_sql:
        if conn:
            conn.rollback()
        logger.error(
            f"Database error assigning task to agent {target_agent_id}: {e_sql}",
            exc_info=True,
        )
        return [
            mcp_types.TextContent(
                type="text", text=f"Database error assigning task: {e_sql}"
            )
        ]
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(
            f"Unexpected error assigning task to agent {target_agent_id}: {e}",
            exc_info=True,
        )
        return [
            mcp_types.TextContent(
                type="text", text=f"Unexpected error assigning task: {e}"
            )
        ]
    finally:
        if conn:
            conn.close()


# --- create_self_task tool ---
# Original logic from main.py: lines 1409-1474 (create_self_task_tool function)
async def create_self_task_tool_impl(
    arguments: Dict[str, Any],
) -> List[mcp_types.TextContent]:
    agent_auth_token = arguments.get("token")
    task_title = arguments.get("task_title")
    task_description = arguments.get("task_description")
    priority = arguments.get("priority", "medium")
    depends_on_tasks_list = arguments.get("depends_on_tasks")
    parent_task_id_arg = arguments.get("parent_task_id")

    requesting_agent_id = get_agent_id(agent_auth_token)  # main.py:1415
    if not requesting_agent_id:
        return [
            mcp_types.TextContent(
                type="text", text="Unauthorized: Valid token required"
            )
        ]

    if not all([task_title, task_description]):
        return [
            mcp_types.TextContent(
                type="text", text="Error: task_title and task_description are required."
            )
        ]

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
            logger.error(
                f"Agent '{requesting_agent_id}' attempted to create a root task"
            )

            # Find a suitable parent task for the agent
            cursor.execute(
                """
                SELECT task_id, title FROM tasks 
                WHERE assigned_to = ? OR created_by = ?
                ORDER BY created_at DESC LIMIT 1
            """,
                (requesting_agent_id, requesting_agent_id),
            )

            suggested_parent = cursor.fetchone()
            suggestion_text = ""
            if suggested_parent:
                suggestion_text = f"\nSuggested parent: {suggested_parent['task_id']} ({suggested_parent['title']})"

            return [
                mcp_types.TextContent(
                    type="text",
                    text=f"ERROR: Agents cannot create root tasks. Every task must have a parent.{suggestion_text}\nPlease specify a parent_task_id.",
                )
            ]

        # Additional check for single root rule even for admin
        if actual_parent_task_id is None:
            cursor.execute(
                "SELECT COUNT(*) as count, MIN(task_id) as root_id FROM tasks WHERE parent_task IS NULL"
            )
            result = cursor.fetchone()
            root_count = result["count"]
            existing_root_id = result["root_id"]

            if root_count > 0:
                logger.error(
                    f"Attempt to create second root task. Existing root: {existing_root_id}"
                )
                return [
                    mcp_types.TextContent(
                        type="text",
                        text=f"ERROR: Cannot create root task. A root task already exists ({existing_root_id}). All new tasks must have a parent.",
                    )
                ]

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
                auth_token=agent_auth_token,
            )

            suggestion_message = format_suggestions_for_agent(
                validation_result, actual_parent_task_id, depends_on_tasks_list
            )

            # Check for denial
            if validation_result["status"] == "denied":
                return [
                    mcp_types.TextContent(
                        type="text",
                        text=f"Task creation BLOCKED by RAG validation:\n{suggestion_message}",
                    )
                ]

            # Process validation results
            if validation_result["status"] != "approved":
                validation_message = f"\nRAG Validation ({validation_result['status']}):\n{suggestion_message}\n"

                # For agents, always accept suggestions automatically
                suggestions = validation_result["suggestions"]
                if suggestions.get("parent_task") is not None:
                    final_parent_task_id = suggestions["parent_task"]
                    validation_message += (
                        f"✓ Applied suggested parent: {final_parent_task_id}\n"
                    )
                if suggestions.get("dependencies"):
                    final_depends_on_tasks = suggestions["dependencies"]
                    validation_message += (
                        f"✓ Applied suggested dependencies: {final_depends_on_tasks}\n"
                    )

                logger.info(
                    f"Agent {requesting_agent_id} automatically accepted RAG suggestions"
                )

                # Check if escalation is needed
                if should_escalate_to_admin(validation_result, requesting_agent_id):
                    logger.warning(
                        f"Task {new_task_id} flagged for admin review: {validation_result.get('message')}"
                    )
                    validation_message += "⚠️ Task flagged for admin review\n"
            else:
                validation_message = "\n✓ RAG validation approved placement\n"

        task_data_for_db = {  # main.py:1439-1452
            "task_id": new_task_id,
            "title": task_title,
            "description": task_description,
            "assigned_to": requesting_agent_id,
            "created_by": requesting_agent_id,  # Agent creates for self
            "status": status,
            "priority": priority,
            "created_at": created_at_iso,
            "updated_at": created_at_iso,
            "parent_task": final_parent_task_id,  # Use validated value
            "child_tasks": json.dumps([]),
            "depends_on_tasks": json.dumps(
                final_depends_on_tasks or []
            ),  # Use validated value
            "notes": json.dumps([]),
        }

        cursor.execute(
            """
            INSERT INTO tasks (task_id, title, description, assigned_to, created_by, status, priority, 
                               created_at, updated_at, parent_task, child_tasks, depends_on_tasks, notes)
            VALUES (:task_id, :title, :description, :assigned_to, :created_by, :status, :priority, 
                    :created_at, :updated_at, :parent_task, :child_tasks, :depends_on_tasks, :notes)
        """,
            task_data_for_db,
        )

        # Update agent's current task in DB if they don't have one (main.py:1455-1469)
        should_update_agent_current_task = False
        if agent_auth_token in g.active_agents:  # Check memory first
            if g.active_agents[agent_auth_token].get("current_task") is None:
                should_update_agent_current_task = True
        elif (
            requesting_agent_id != "admin"
        ):  # If not admin and not in active_agents (e.g. loaded from DB only)
            cursor.execute(
                "SELECT current_task FROM agents WHERE agent_id = ?",
                (requesting_agent_id,),
            )
            agent_row = cursor.fetchone()
            if agent_row and agent_row["current_task"] is None:
                should_update_agent_current_task = True
        # Admin agents don't have a persistent 'current_task' in the agents table.

        if should_update_agent_current_task and requesting_agent_id != "admin":
            cursor.execute(
                "UPDATE agents SET current_task = ?, updated_at = ? WHERE agent_id = ?",
                (new_task_id, created_at_iso, requesting_agent_id),
            )

        log_agent_action_to_db(
            cursor,
            requesting_agent_id,
            "created_self_task",
            task_id=new_task_id,
            details={"title": task_title},
        )
        conn.commit()

        if should_update_agent_current_task and agent_auth_token in g.active_agents:
            g.active_agents[agent_auth_token]["current_task"] = new_task_id

        task_data_for_memory = task_data_for_db.copy()
        task_data_for_memory["child_tasks"] = []
        task_data_for_memory["depends_on_tasks"] = (
            final_depends_on_tasks or []
        )  # Use validated value
        task_data_for_memory["notes"] = []
        g.tasks[new_task_id] = task_data_for_memory

        # System 8: Index the new task for RAG
        # Convert database format to the format expected by indexing
        index_data = task_data_for_memory.copy()
        # No need to override depends_on_tasks again, it's already the validated value
        # Start indexing asynchronously (fire and forget)
        import asyncio

        asyncio.create_task(index_task_data(new_task_id, index_data))

        log_audit(
            requesting_agent_id,
            "create_self_task",
            {"task_id": new_task_id, "title": task_title},
        )  # main.py:1485
        logger.info(
            f"Agent '{requesting_agent_id}' created self-task '{new_task_id}' ({task_title})."
        )

        response_text = (
            f"Self-assigned task '{new_task_id}' created.\nTitle: {task_title}"
        )
        if validation_message:
            response_text += validation_message

        return [mcp_types.TextContent(type="text", text=response_text)]

    except sqlite3.Error as e_sql:
        if conn:
            conn.rollback()
        logger.error(
            f"Database error creating self task for agent {requesting_agent_id}: {e_sql}",
            exc_info=True,
        )
        return [
            mcp_types.TextContent(
                type="text", text=f"Database error creating self task: {e_sql}"
            )
        ]
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(
            f"Unexpected error creating self task for agent {requesting_agent_id}: {e}",
            exc_info=True,
        )
        return [
            mcp_types.TextContent(
                type="text", text=f"Unexpected error creating self task: {e}"
            )
        ]
    finally:
        if conn:
            conn.close()


# --- update_task_status tool ---
# Original logic from main.py: lines 1477-1583 (update_task_status_tool function)
async def update_task_status_tool_impl(
    arguments: Dict[str, Any],
) -> List[mcp_types.TextContent]:
    agent_auth_token = arguments.get("token")
    task_id_to_update = arguments.get("task_id")
    task_ids_bulk = arguments.get(
        "task_ids"
    )  # NEW: List of task IDs for bulk operations
    new_status = arguments.get("status")
    notes_content = arguments.get("notes")  # Optional string for new note

    # Admin-only fields for full task update
    new_title = arguments.get("title")
    new_description = arguments.get("description")
    new_priority = arguments.get("priority")
    new_assigned_to = arguments.get("assigned_to")
    new_depends_on_tasks = arguments.get("depends_on_tasks")  # List[str] or None

    # Smart features
    auto_update_dependencies = arguments.get(
        "auto_update_dependencies", True
    )  # Auto-update dependent tasks
    cascade_to_children = arguments.get(
        "cascade_to_children", False
    )  # Cascade status to child tasks
    validate_dependencies = arguments.get(
        "validate_dependencies", True
    )  # Validate dependency constraints

    requesting_agent_id = get_agent_id(agent_auth_token)
    if not requesting_agent_id:
        return [
            mcp_types.TextContent(
                type="text", text="Unauthorized: Valid token required"
            )
        ]

    # Determine if this is bulk or single operation
    task_ids_to_process = []
    if task_ids_bulk:
        task_ids_to_process = task_ids_bulk
    elif task_id_to_update:
        task_ids_to_process = [task_id_to_update]
    else:
        return [
            mcp_types.TextContent(
                type="text", text="Error: Either task_id or task_ids is required."
            )
        ]

    if not new_status:
        return [mcp_types.TextContent(type="text", text="Error: status is required.")]

    valid_statuses = ["pending", "in_progress", "completed", "cancelled", "failed"]
    if new_status not in valid_statuses:
        return [
            mcp_types.TextContent(
                type="text",
                text=f"Invalid status: {new_status}. Valid: {', '.join(valid_statuses)}",
            )
        ]

    is_admin_request = verify_token(agent_auth_token, "admin")

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Process tasks (bulk or single)
        results = []
        tasks_to_cascade = []

        # Phase 1: Update primary tasks
        for task_id in task_ids_to_process:
            result = await _update_single_task(
                cursor,
                task_id,
                new_status,
                requesting_agent_id,
                is_admin_request,
                notes_content,
                new_title,
                new_description,
                new_priority,
                new_assigned_to,
                new_depends_on_tasks,
            )
            results.append(result)

            if result["success"] and cascade_to_children:
                tasks_to_cascade.extend(result["child_tasks"])

            # Log individual task action
            if result["success"]:
                log_details = {"status": new_status, "old_status": result["old_status"]}
                if notes_content:
                    log_details["notes_added"] = True
                log_agent_action_to_db(
                    cursor,
                    requesting_agent_id,
                    "update_task_status",
                    task_id=task_id,
                    details=log_details,
                )

        # Phase 2: Smart cascade to children if requested
        cascade_results = []
        if cascade_to_children and tasks_to_cascade:
            for child_task_id in tasks_to_cascade:
                # Only cascade certain status changes to avoid breaking workflows
                if new_status in ["cancelled", "failed"]:  # Cascade blocking states
                    child_result = await _update_single_task(
                        cursor,
                        child_task_id,
                        new_status,
                        requesting_agent_id,
                        is_admin_request,
                        f"Auto-cascaded from parent task status change",
                        None,
                        None,
                        None,
                        None,
                        None,
                    )
                    cascade_results.append(child_result)

        # Phase 3: Smart dependency updates if requested
        dependency_updates = []
        if auto_update_dependencies:
            for result in results:
                if result["success"] and new_status == "completed":
                    # Find tasks that depend on this completed task
                    cursor.execute("SELECT task_id, depends_on_tasks FROM tasks")
                    all_tasks = cursor.fetchall()

                    for task_row in all_tasks:
                        task_deps = json.loads(task_row["depends_on_tasks"] or "[]")
                        if result["task_id"] in task_deps:
                            # Check if all dependencies are now completed
                            all_deps_completed = True
                            for dep_id in task_deps:
                                if (
                                    dep_id != result["task_id"]
                                ):  # Skip the one we just completed
                                    cursor.execute(
                                        "SELECT status FROM tasks WHERE task_id = ?",
                                        (dep_id,),
                                    )
                                    dep_row = cursor.fetchone()
                                    if not dep_row or dep_row["status"] != "completed":
                                        all_deps_completed = False
                                        break

                            if all_deps_completed:
                                # Auto-update dependent task to in_progress if it's pending
                                cursor.execute(
                                    "SELECT status FROM tasks WHERE task_id = ?",
                                    (task_row["task_id"],),
                                )
                                dependent_task = cursor.fetchone()
                                if (
                                    dependent_task
                                    and dependent_task["status"] == "pending"
                                ):
                                    dep_result = await _update_single_task(
                                        cursor,
                                        task_row["task_id"],
                                        "in_progress",
                                        requesting_agent_id,
                                        is_admin_request,
                                        f"Auto-advanced: all dependencies completed",
                                        None,
                                        None,
                                        None,
                                        None,
                                        None,
                                    )
                                    dependency_updates.append(dep_result)

        # Commit all changes
        conn.commit()

        # Phase 4: Re-index updated tasks
        import asyncio

        for result in results + cascade_results + dependency_updates:
            if result.get("success"):
                task_id = result["task_id"]
                if task_id in g.tasks:
                    asyncio.create_task(
                        index_task_data(task_id, g.tasks[task_id].copy())
                    )

        # Build comprehensive response
        successful_updates = [r for r in results if r.get("success")]
        failed_updates = [r for r in results if not r.get("success")]

        response_parts = []

        if len(task_ids_to_process) == 1:
            # Single task response
            if successful_updates:
                response_parts.append(
                    f"Task {successful_updates[0]['task_id']} status updated to {new_status}."
                )
            else:
                response_parts.append(
                    f"Failed to update task: {failed_updates[0]['error']}"
                )
        else:
            # Bulk operation response
            response_parts.append(
                f"Bulk update completed: {len(successful_updates)}/{len(task_ids_to_process)} tasks updated."
            )

            if failed_updates:
                response_parts.append(f"Failed updates:")
                for fail in failed_updates[:3]:  # Limit to first 3 failures
                    response_parts.append(f"  - {fail['error']}")
                if len(failed_updates) > 3:
                    response_parts.append(
                        f"  ... and {len(failed_updates) - 3} more failures"
                    )

        # Add smart feature results
        if cascade_results:
            successful_cascades = [r for r in cascade_results if r.get("success")]
            response_parts.append(
                f"Cascaded to {len(successful_cascades)} child tasks."
            )

        if dependency_updates:
            successful_deps = [r for r in dependency_updates if r.get("success")]
            response_parts.append(
                f"Auto-advanced {len(successful_deps)} dependent tasks."
            )

        log_audit(
            requesting_agent_id,
            "update_task_status",
            {
                "task_count": len(task_ids_to_process),
                "successful": len(successful_updates),
                "failed": len(failed_updates),
                "status": new_status,
                "cascade_count": len(cascade_results),
                "dependency_updates": len(dependency_updates),
            },
        )

        return [mcp_types.TextContent(type="text", text="\n".join(response_parts))]

    except sqlite3.Error as e_sql:
        if conn:
            conn.rollback()
        logger.error(f"Database error updating tasks: {e_sql}", exc_info=True)
        return [
            mcp_types.TextContent(
                type="text", text=f"Database error updating tasks: {e_sql}"
            )
        ]
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Unexpected error updating tasks: {e}", exc_info=True)
        return [
            mcp_types.TextContent(
                type="text", text=f"Unexpected error updating tasks: {e}"
            )
        ]
    finally:
        if conn:
            conn.close()


# --- view_tasks tool ---
# Original logic from main.py: lines 1586-1655 (view_tasks_tool function)
async def view_tasks_tool_impl(
    arguments: Dict[str, Any],
) -> List[mcp_types.TextContent]:
    agent_auth_token = arguments.get("token")
    filter_agent_id = arguments.get("agent_id")  # Optional agent_id to filter by
    filter_status = arguments.get("status")  # Optional status to filter by
    max_tokens = arguments.get(
        "max_tokens", 25000
    )  # Maximum response tokens (default: 25k)
    start_after = arguments.get(
        "start_after"
    )  # Task ID to start after (for pagination)
    summary_mode = arguments.get(
        "summary_mode", False
    )  # If True, show only summary info

    # Smart filtering and analysis options
    show_dependencies = arguments.get(
        "show_dependencies", False
    )  # Show dependency graph info
    show_health_analysis = arguments.get(
        "show_health_analysis", False
    )  # Show task health metrics
    filter_priority = arguments.get("filter_priority")  # Filter by priority
    filter_parent_task = arguments.get("filter_parent_task")  # Filter by parent task
    show_blocked_tasks = arguments.get(
        "show_blocked_tasks", False
    )  # Show only blocked tasks
    sort_by = arguments.get(
        "sort_by", "created_at"
    )  # Sort by: created_at, updated_at, priority, status

    requesting_agent_id = get_agent_id(agent_auth_token)
    if not requesting_agent_id:
        return [
            mcp_types.TextContent(
                type="text", text="Unauthorized: Valid token required"
            )
        ]

    is_admin_request = verify_token(agent_auth_token, "admin")

    # Permission check
    target_agent_id_for_filter = filter_agent_id
    if not is_admin_request:
        if filter_agent_id is None:
            target_agent_id_for_filter = requesting_agent_id
        elif filter_agent_id != requesting_agent_id:
            return [
                mcp_types.TextContent(
                    type="text",
                    text="Unauthorized: Non-admin agents can only view their own tasks or all tasks assigned to them if no agent_id filter is specified.",
                )
            ]

    # Advanced filtering with dependency analysis
    tasks_to_display: List[Dict[str, Any]] = []

    # Pre-analyze all tasks for dependency checking
    all_tasks_dict = dict(g.tasks)

    for task_id, task_data in g.tasks.items():
        # Basic permission filtering
        matches_agent = True
        if (
            target_agent_id_for_filter
            and task_data.get("assigned_to") != target_agent_id_for_filter
        ):
            matches_agent = False

        # Status filtering
        matches_status = True
        if filter_status and task_data.get("status") != filter_status:
            matches_status = False

        # Priority filtering
        matches_priority = True
        if filter_priority and task_data.get("priority") != filter_priority:
            matches_priority = False

        # Parent task filtering
        matches_parent = True
        if filter_parent_task and task_data.get("parent_task") != filter_parent_task:
            matches_parent = False

        # Blocked tasks filtering
        matches_blocked = True
        if show_blocked_tasks:
            dependency_analysis = _analyze_task_dependencies(task_data, all_tasks_dict)
            matches_blocked = (
                dependency_analysis["is_blocked"]
                or not dependency_analysis["can_start"]
            )

        if (
            matches_agent
            and matches_status
            and matches_priority
            and matches_parent
            and matches_blocked
        ):
            # Add dependency analysis if requested
            if show_dependencies:
                task_data_copy = task_data.copy()
                task_data_copy["_dependency_analysis"] = _analyze_task_dependencies(
                    task_data, all_tasks_dict
                )
                tasks_to_display.append(task_data_copy)
            else:
                tasks_to_display.append(task_data)

    # Smart sorting
    def get_sort_key(task):
        if sort_by == "priority":
            priority_order = {"high": 3, "medium": 2, "low": 1}
            return priority_order.get(task.get("priority", "medium"), 2)
        elif sort_by == "status":
            status_order = {
                "failed": 5,
                "in_progress": 4,
                "pending": 3,
                "completed": 2,
                "cancelled": 1,
            }
            return status_order.get(task.get("status", "pending"), 3)
        elif sort_by == "updated_at":
            return task.get("updated_at", "")
        else:  # created_at (default)
            return task.get("created_at", "")

    reverse_sort = sort_by in ["created_at", "updated_at", "priority", "status"]
    tasks_to_display.sort(key=get_sort_key, reverse=reverse_sort)

    # Handle pagination with start_after
    if start_after:
        start_index = 0
        for i, task in enumerate(tasks_to_display):
            if task.get("task_id") == start_after:
                start_index = i + 1
                break
        tasks_to_display = tasks_to_display[start_index:]

    if not tasks_to_display:
        response_text = "No tasks found matching the criteria."
    else:
        # Generate health analysis if requested
        health_analysis = None
        if show_health_analysis:
            health_analysis = _calculate_task_health_metrics(tasks_to_display)

        # Build response with smart headers
        filter_info = []
        if filter_status:
            filter_info.append(f"status={filter_status}")
        if filter_priority:
            filter_info.append(f"priority={filter_priority}")
        if filter_agent_id:
            filter_info.append(f"agent={filter_agent_id}")
        if filter_parent_task:
            filter_info.append(f"parent={filter_parent_task}")
        if show_blocked_tasks:
            filter_info.append("blocked_only=true")

        header = f"Tasks ({len(tasks_to_display)} found"
        if filter_info:
            header += f", filtered by: {', '.join(filter_info)}"
        header += f", sorted by: {sort_by})"

        response_parts = [header + "\n"]

        # Add health analysis at the top if requested
        if health_analysis:
            health_status = health_analysis["health_status"]
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
                f"📊 **Health Analysis:** {health_icon} {health_status.title()} ({health_score}/100)"
            )
            response_parts.append(
                f"   Status: {health_analysis['status_distribution']}"
            )
            response_parts.append(
                f"   Issues: {health_analysis['blocked_tasks']} blocked, {health_analysis['stale_tasks']} stale"
            )
            response_parts.append("")

        current_tokens = estimate_tokens("\n".join(response_parts))
        tasks_included = 0
        last_task_id = None
        truncated = False

        for task in tasks_to_display:
            # Format task with dependency info if requested
            if show_dependencies and "_dependency_analysis" in task:
                task_text = _format_task_with_dependencies(task)
            elif summary_mode:
                task_text = _format_task_summary(task)
            else:
                task_text = _format_task_detailed(task)

            task_tokens = estimate_tokens(task_text)

            # Check token limit with safety buffer
            safety_buffer = 1000
            if (
                current_tokens + task_tokens > (max_tokens - safety_buffer)
                and tasks_included > 0
            ):
                truncated = True
                break

            response_parts.append(f"{task_text}\n")
            current_tokens += task_tokens
            tasks_included += 1
            last_task_id = task.get("task_id")

        # Add smart pagination and usage tips
        if truncated:
            remaining_count = len(tasks_to_display) - tasks_included
            response_parts.append(
                f"--- Response truncated to stay under {max_tokens} tokens ---"
            )
            response_parts.append(
                f"Showing {tasks_included} of {len(tasks_to_display)} tasks ({remaining_count} remaining)"
            )
            response_parts.append(
                f"Continue: view_tasks(start_after='{last_task_id}', max_tokens={max_tokens})"
            )
            if not summary_mode:
                response_parts.append(f"Overview: view_tasks(summary_mode=true)")
        else:
            response_parts.append(f"--- All {tasks_included} matching tasks shown ---")

        # Add smart usage tips
        response_parts.append("\n💡 Smart Tips:")
        if not show_dependencies:
            response_parts.append(
                "• Add show_dependencies=true to see dependency chains"
            )
        if not show_health_analysis:
            response_parts.append("• Add show_health_analysis=true for health metrics")
        if not show_blocked_tasks:
            response_parts.append(
                "• Add show_blocked_tasks=true to see only blocked tasks"
            )
        response_parts.append(
            "• Use sort_by=[priority|status|updated_at] for different sorting"
        )

        response_text = "\n".join(response_parts)

    log_audit(
        requesting_agent_id,
        "view_tasks",
        {"filter_agent_id": filter_agent_id, "filter_status": filter_status},
    )
    return [mcp_types.TextContent(type="text", text=response_text)]


def _format_task_summary(task: Dict[str, Any]) -> str:
    """Format task in summary mode (minimal tokens)"""
    task_id = task.get("task_id", "N/A")
    title = task.get("title", "N/A")
    status = task.get("status", "N/A")
    priority = task.get("priority", "medium")
    assigned_to = task.get("assigned_to", "Unassigned")

    # Truncate description
    description = task.get("description", "No description")
    if len(description) > 100:
        description = description[:100] + "..."

    return f"""ID: {task_id}
Title: {title}
Status: {status} | Priority: {priority}
Assigned to: {assigned_to}
Description: {description}"""


def _format_task_detailed(task: Dict[str, Any]) -> str:
    """Format task in detailed mode (includes notes, full description)"""
    parts = []
    parts.append(f"ID: {task.get('task_id', 'N/A')}")
    parts.append(f"Title: {task.get('title', 'N/A')}")
    parts.append(f"Description: {task.get('description', 'No description')}")
    parts.append(f"Status: {task.get('status', 'N/A')}")
    parts.append(f"Priority: {task.get('priority', 'medium')}")
    parts.append(f"Assigned to: {task.get('assigned_to', 'None')}")
    parts.append(f"Created by: {task.get('created_by', 'N/A')}")
    parts.append(f"Created: {task.get('created_at', 'N/A')}")
    parts.append(f"Updated: {task.get('updated_at', 'N/A')}")

    if task.get("parent_task"):
        parts.append(f"Parent task: {task['parent_task']}")

    child_tasks_val = task.get("child_tasks", [])
    if isinstance(child_tasks_val, str):
        try:
            child_tasks_val = json.loads(child_tasks_val or "[]")
        except:
            child_tasks_val = ["Error decoding child_tasks"]
    if child_tasks_val:
        parts.append(f"Child tasks: {', '.join(child_tasks_val)}")

    notes_val = task.get("notes", [])
    if isinstance(notes_val, str):
        try:
            notes_val = json.loads(notes_val or "[]")
        except:
            notes_val = [{"author": "System", "content": "Error decoding notes"}]
    if notes_val:
        parts.append("Notes:")
        # Limit notes to prevent token explosion
        recent_notes = notes_val[-5:] if len(notes_val) > 5 else notes_val
        for note in recent_notes:
            if isinstance(note, dict):
                ts = note.get("timestamp", "Unknown time")
                auth = note.get("author", "Unknown")
                cont = note.get("content", "No content")
                parts.append(f"  - [{ts}] {auth}: {cont}")
            else:
                parts.append(f"  - [Invalid Note Format: {str(note)}]")
        if len(notes_val) > 5:
            parts.append(f"  ... and {len(notes_val) - 5} more notes")

    return "\n".join(parts)


def _format_task_with_dependencies(task: Dict[str, Any]) -> str:
    """Format task with dependency analysis information"""
    # Start with detailed format
    task_text = _format_task_detailed(task)

    # Add dependency analysis
    dep_analysis = task.get("_dependency_analysis", {})
    if dep_analysis:
        dep_parts = ["\n🔗 Dependency Analysis:"]

        # Health status
        health = dep_analysis.get("dependency_health", "unknown")
        health_icon = (
            "🟢"
            if health == "healthy"
            else "🟡" if health == "waiting" else "🟠" if health == "warning" else "🔴"
        )
        dep_parts.append(f"   Status: {health_icon} {health}")

        # Blocking info
        if dep_analysis.get("is_blocked"):
            dep_parts.append("   ⚠️  BLOCKED - Cannot proceed")
        elif not dep_analysis.get("can_start"):
            dep_parts.append("   ⏳ WAITING - Dependencies not ready")
        else:
            dep_parts.append("   ✅ READY - Can proceed")

        # Dependencies details
        completed_deps = dep_analysis.get("completed_dependencies", [])
        blocking_deps = dep_analysis.get("blocking_dependencies", [])
        missing_deps = dep_analysis.get("missing_dependencies", [])

        if completed_deps:
            dep_parts.append(
                f"   ✅ Completed: {', '.join(completed_deps[:3])}"
                + (
                    f" (+{len(completed_deps)-3} more)"
                    if len(completed_deps) > 3
                    else ""
                )
            )

        if blocking_deps:
            dep_parts.append(
                f"   🔴 Blocking: {', '.join(blocking_deps[:3])}"
                + (f" (+{len(blocking_deps)-3} more)" if len(blocking_deps) > 3 else "")
            )

        if missing_deps:
            dep_parts.append(
                f"   ❌ Missing: {', '.join(missing_deps[:3])}"
                + (f" (+{len(missing_deps)-3} more)" if len(missing_deps) > 3 else "")
            )

        # What this task blocks
        blocks_tasks = dep_analysis.get("blocks_tasks", [])
        if blocks_tasks:
            dep_parts.append(
                f"   🔒 Blocks: {', '.join(blocks_tasks[:3])}"
                + (f" (+{len(blocks_tasks)-3} more)" if len(blocks_tasks) > 3 else "")
            )

        task_text += "\n".join(dep_parts)

    return task_text


def _analyze_agent_workload(cursor, agent_id: str) -> Dict[str, Any]:
    """Analyze agent's current workload and capacity"""

    # Get agent's current tasks
    cursor.execute(
        """
        SELECT task_id, title, status, priority, created_at, updated_at 
        FROM tasks 
        WHERE assigned_to = ? AND status IN ('pending', 'in_progress')
        ORDER BY priority DESC, created_at ASC
    """,
        (agent_id,),
    )

    active_tasks = [dict(row) for row in cursor.fetchall()]

    # Calculate workload metrics
    total_tasks = len(active_tasks)
    high_priority_tasks = len([t for t in active_tasks if t.get("priority") == "high"])
    in_progress_tasks = len(
        [t for t in active_tasks if t.get("status") == "in_progress"]
    )
    pending_tasks = len([t for t in active_tasks if t.get("status") == "pending"])

    # Calculate "staleness" - tasks not updated recently
    current_time = datetime.datetime.now()
    stale_tasks = 0
    for task in active_tasks:
        if task.get("updated_at"):
            try:
                updated_time = datetime.datetime.fromisoformat(
                    task["updated_at"].replace("Z", "+00:00").replace("+00:00", "")
                )
                days_stale = (current_time - updated_time).days
                if days_stale > 3:  # No update in 3+ days
                    stale_tasks += 1
            except:
                pass

    # Simple capacity assessment
    capacity_status = "available"
    if total_tasks >= 8:
        capacity_status = "overloaded"
    elif total_tasks >= 5:
        capacity_status = "busy"
    elif high_priority_tasks >= 3:
        capacity_status = "busy"

    return {
        "agent_id": agent_id,
        "total_active_tasks": total_tasks,
        "high_priority_tasks": high_priority_tasks,
        "in_progress_tasks": in_progress_tasks,
        "pending_tasks": pending_tasks,
        "stale_tasks": stale_tasks,
        "capacity_status": capacity_status,
        "workload_score": min(
            100, total_tasks * 10 + high_priority_tasks * 5
        ),  # 0-100+
        "can_take_new_task": capacity_status in ["available", "busy"]
        and high_priority_tasks < 4,
        "recommendations": _generate_workload_recommendations(
            capacity_status, total_tasks, stale_tasks
        ),
    }


def _generate_workload_recommendations(
    capacity_status: str, total_tasks: int, stale_tasks: int
) -> List[str]:
    """Generate workload management recommendations"""
    recommendations = []

    if capacity_status == "overloaded":
        recommendations.append("Consider redistributing some tasks to other agents")
        recommendations.append("Focus on completing high-priority tasks first")

    if stale_tasks > 0:
        recommendations.append(
            f"Review {stale_tasks} stale tasks that haven't been updated recently"
        )

    if total_tasks > 6:
        recommendations.append(
            "Consider breaking down large tasks into smaller subtasks"
        )

    if not recommendations:
        recommendations.append("Workload appears manageable")

    return recommendations


def _suggest_optimal_parent_task(
    cursor, agent_id: str, task_description: str
) -> Dict[str, Any]:
    """Suggest optimal parent task based on context and agent workload"""

    # Get agent's current tasks that could be parents
    cursor.execute(
        """
        SELECT task_id, title, description, status, priority 
        FROM tasks 
        WHERE assigned_to = ? AND status IN ('pending', 'in_progress')
        ORDER BY 
            CASE WHEN status = 'in_progress' THEN 1 ELSE 2 END,
            CASE priority WHEN 'high' THEN 3 WHEN 'medium' THEN 2 ELSE 1 END DESC,
            updated_at DESC
        LIMIT 10
    """,
        (agent_id,),
    )

    agent_tasks = [dict(row) for row in cursor.fetchall()]

    # Simple text similarity scoring (could be enhanced with embeddings)
    def similarity_score(text1: str, text2: str) -> float:
        text1_words = set(text1.lower().split())
        text2_words = set(text2.lower().split())
        if not text1_words or not text2_words:
            return 0.0
        intersection = text1_words.intersection(text2_words)
        union = text1_words.union(text2_words)
        return len(intersection) / len(union) if union else 0.0

    suggestions = []
    for task in agent_tasks:
        # Score based on title and description similarity
        title_sim = similarity_score(task_description, task.get("title", ""))
        desc_sim = similarity_score(task_description, task.get("description", ""))
        combined_score = (title_sim * 0.6) + (desc_sim * 0.4)

        # Boost score for in-progress tasks (more likely to be good parents)
        if task.get("status") == "in_progress":
            combined_score *= 1.2

        if combined_score > 0.1:  # Only suggest if there's some relevance
            suggestions.append(
                {
                    "task_id": task["task_id"],
                    "title": task["title"],
                    "status": task["status"],
                    "priority": task["priority"],
                    "similarity_score": round(combined_score, 3),
                    "reason": f"Similar content ({int(combined_score*100)}% match)",
                }
            )

    # Sort by score and take top 3
    suggestions.sort(key=lambda x: x["similarity_score"], reverse=True)

    return {
        "agent_id": agent_id,
        "suggestions": suggestions[:3],
        "has_suggestions": len(suggestions) > 0,
    }


# --- request_assistance tool ---
# Original logic from main.py: lines 1658-1763 (request_assistance_tool function)
# This tool had file-based notification system. We'll replicate that for 1-to-1.
async def request_assistance_tool_impl(
    arguments: Dict[str, Any],
) -> List[mcp_types.TextContent]:
    agent_auth_token = arguments.get("token")
    parent_task_id = arguments.get("task_id")  # Task ID needing assistance
    assistance_description = arguments.get("description")

    requesting_agent_id = get_agent_id(agent_auth_token)  # main.py:1666
    if not requesting_agent_id:
        return [
            mcp_types.TextContent(
                type="text", text="Unauthorized: Valid token required"
            )
        ]

    if not parent_task_id or not assistance_description:
        return [
            mcp_types.TextContent(
                type="text",
                text="Error: task_id (for parent) and description are required.",
            )
        ]

    # Fetch parent task data (original used in-memory g.tasks, main.py:1674)
    # For robustness, let's fetch from DB, then update g.tasks.
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (parent_task_id,))
        parent_task_db_row = cursor.fetchone()
        if not parent_task_db_row:
            return [
                mcp_types.TextContent(
                    type="text", text=f"Parent task '{parent_task_id}' not found."
                )
            ]

        parent_task_current_data = dict(parent_task_db_row)

        # Verify ownership or admin (main.py:1688-1691)
        is_admin_request = verify_token(agent_auth_token, "admin")
        if (
            parent_task_current_data.get("assigned_to") != requesting_agent_id
            and not is_admin_request
        ):
            return [
                mcp_types.TextContent(
                    type="text",
                    text="Unauthorized: You can only request assistance for tasks assigned to you, or use an admin token.",
                )
            ]

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
            "task_id": parent_task_id,  # Parent task
            "child_task_id": child_task_id,  # The new assistance task
            "timestamp": timestamp_iso,
            "description": assistance_description,
            "status": "pending",  # Notification status
        }

        # Save notification file (main.py:1713-1718)
        project_dir_env = os.environ.get("MCP_PROJECT_DIR")
        if not project_dir_env:
            logger.error(
                "MCP_PROJECT_DIR not set. Cannot save assistance notification file."
            )
            # Decide if this is critical enough to stop. Original didn't explicitly stop.
        else:
            try:
                notifications_pending_dir = (
                    Path(project_dir_env) / ".agent" / "notifications" / "pending"
                )
                notifications_pending_dir.mkdir(parents=True, exist_ok=True)
                notification_file_path = (
                    notifications_pending_dir / f"{notification_id}.json"
                )
                with open(notification_file_path, "w", encoding="utf-8") as f:
                    json.dump(notification_data, f, indent=2)
                logger.info(
                    f"Assistance request notification saved to {notification_file_path}"
                )
            except Exception as e_notify:
                logger.error(
                    f"Failed to save assistance notification file: {e_notify}",
                    exc_info=True,
                )

        # Insert the child (assistance) task into DB (main.py:1722-1734)
        child_task_db_data = {
            "task_id": child_task_id,
            "title": child_task_title,
            "description": assistance_description,
            "status": "pending",
            "assigned_to": None,
            "priority": "high",  # Assistance tasks are high priority
            "created_at": timestamp_iso,
            "updated_at": timestamp_iso,
            "parent_task": parent_task_id,
            "depends_on_tasks": json.dumps([]),
            "created_by": requesting_agent_id,  # The agent who requested assistance
            "child_tasks": json.dumps([]),
            "notes": json.dumps([]),
        }
        cursor.execute(
            """
            INSERT INTO tasks (task_id, title, description, status, assigned_to, priority, created_at, 
                               updated_at, parent_task, depends_on_tasks, created_by, child_tasks, notes)
            VALUES (:task_id, :title, :description, :status, :assigned_to, :priority, :created_at, 
                    :updated_at, :parent_task, :depends_on_tasks, :created_by, :child_tasks, :notes)
        """,
            child_task_db_data,
        )

        # Update parent task's child_tasks field and notes (main.py:1737-1764)
        parent_child_tasks_list = json.loads(
            parent_task_current_data.get("child_tasks") or "[]"
        )
        parent_child_tasks_list.append(child_task_id)

        parent_notes_list = json.loads(parent_task_current_data.get("notes") or "[]")
        parent_notes_list.append(
            {
                "timestamp": timestamp_iso,
                "author": requesting_agent_id,
                "content": f"Requested assistance: {assistance_description}. Assistance task created: {child_task_id}",
            }
        )

        cursor.execute(
            "UPDATE tasks SET child_tasks = ?, notes = ?, updated_at = ? WHERE task_id = ?",
            (
                json.dumps(parent_child_tasks_list),
                json.dumps(parent_notes_list),
                timestamp_iso,
                parent_task_id,
            ),
        )

        log_agent_action_to_db(
            cursor,
            requesting_agent_id,
            "request_assistance",
            task_id=parent_task_id,
            details={
                "description": assistance_description,
                "child_task_id": child_task_id,
            },
        )
        conn.commit()

        # Update in-memory caches (g.tasks)
        # Parent task
        if parent_task_id in g.tasks:
            g.tasks[parent_task_id]["child_tasks"] = parent_child_tasks_list
            g.tasks[parent_task_id]["notes"] = parent_notes_list
            g.tasks[parent_task_id]["updated_at"] = timestamp_iso
        # New child task
        child_task_mem_data = child_task_db_data.copy()
        child_task_mem_data["depends_on_tasks"] = []  # from json.dumps([])
        child_task_mem_data["child_tasks"] = []
        child_task_mem_data["notes"] = []
        g.tasks[child_task_id] = child_task_mem_data

        # Send direct message to admin via new communication system
        try:
            admin_message = (
                f"🚨 Assistance Request from {requesting_agent_id}\n\n"
                f"Task: {parent_task_id} - {parent_task_current_data.get('title', 'Untitled Task')}\n"
                f"Description: {assistance_description}\n\n"
                f"Child assistance task created: {child_task_id}\n"
                f"Notification ID: {notification_id}"
            )

            # Send message to admin using the new communication system
            message_result = await send_agent_message_tool_impl(
                {
                    "token": agent_auth_token,
                    "recipient_id": "admin",
                    "message": admin_message,
                    "message_type": "assistance_request",
                    "priority": "high",
                    "deliver_method": "both",
                }
            )
            logger.info(f"Assistance request message sent to admin: {message_result}")
        except Exception as e_msg:
            logger.error(
                f"Failed to send assistance request message to admin: {e_msg}",
                exc_info=True,
            )
            # Don't fail the entire operation if messaging fails

        # Original code also wrote parent and child task JSON files (main.py:1766-1771)
        # This was part of an older file-based task system. We are now DB-centric.
        # For 1-to-1, if those files are still used by something, they'd need to be written.
        # However, the primary task store is now the DB.
        # We will skip writing these individual task JSON files as they are redundant with the DB.
        # If get_task_file_path was used elsewhere, that system needs re-evaluation.

        log_audit(
            requesting_agent_id,
            "request_assistance",
            {
                "parent_task_id": parent_task_id,
                "child_task_id": child_task_id,
                "description": assistance_description,
            },
        )
        logger.info(
            f"Agent '{requesting_agent_id}' requested assistance for task '{parent_task_id}'. Child task '{child_task_id}' created."
        )
        return [
            mcp_types.TextContent(
                type="text",
                text=f"Assistance requested for task {parent_task_id}. Child assistance task {child_task_id} created. Admin notified via file notification and direct message.",
            )
        ]

    except sqlite3.Error as e_sql:
        if conn:
            conn.rollback()
        logger.error(
            f"Database error requesting assistance for task {parent_task_id}: {e_sql}",
            exc_info=True,
        )
        return [
            mcp_types.TextContent(
                type="text", text=f"Database error requesting assistance: {e_sql}"
            )
        ]
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(
            f"Unexpected error requesting assistance for task {parent_task_id}: {e}",
            exc_info=True,
        )
        return [
            mcp_types.TextContent(
                type="text", text=f"Unexpected error requesting assistance: {e}"
            )
        ]
    finally:
        if conn:
            conn.close()


# --- bulk_task_operations tool ---
async def bulk_task_operations_tool_impl(
    arguments: Dict[str, Any],
) -> List[mcp_types.TextContent]:
    agent_auth_token = arguments.get("token")
    operations = arguments.get("operations", [])  # List of operation objects

    requesting_agent_id = get_agent_id(agent_auth_token)
    if not requesting_agent_id:
        return [
            mcp_types.TextContent(
                type="text", text="Unauthorized: Valid token required"
            )
        ]

    if not operations or not isinstance(operations, list):
        return [
            mcp_types.TextContent(
                type="text",
                text="Error: operations list is required and must be a non-empty array",
            )
        ]

    is_admin_request = verify_token(agent_auth_token, "admin")

    # Process operations in a single transaction
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        results = []
        updated_at_iso = datetime.datetime.now().isoformat()

        for i, op in enumerate(operations):
            if not isinstance(op, dict):
                results.append(
                    f"Operation {i+1}: Invalid operation format (must be object)"
                )
                continue

            operation_type = op.get("type")
            task_id = op.get("task_id")

            if not task_id or not operation_type:
                results.append(
                    f"Operation {i+1}: Missing required fields 'type' and 'task_id'"
                )
                continue

            # Verify task exists and permissions
            cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
            task_row = cursor.fetchone()
            if not task_row:
                results.append(f"Operation {i+1}: Task '{task_id}' not found")
                continue

            task_data = dict(task_row)

            # Permission check
            if (
                task_data.get("assigned_to") != requesting_agent_id
                and not is_admin_request
            ):
                results.append(
                    f"Operation {i+1}: Unauthorized - can only modify own tasks"
                )
                continue

            try:
                if operation_type == "update_status":
                    new_status = op.get("status")
                    notes_content = op.get("notes")

                    if not new_status:
                        results.append(
                            f"Operation {i+1}: Missing 'status' for update_status operation"
                        )
                        continue

                    valid_statuses = [
                        "pending",
                        "in_progress",
                        "completed",
                        "cancelled",
                        "failed",
                    ]
                    if new_status not in valid_statuses:
                        results.append(
                            f"Operation {i+1}: Invalid status '{new_status}'"
                        )
                        continue

                    # Update status
                    update_fields = ["status = ?", "updated_at = ?"]
                    update_params = [new_status, updated_at_iso]

                    # Handle notes
                    current_notes = json.loads(task_data.get("notes") or "[]")
                    if notes_content:
                        current_notes.append(
                            {
                                "timestamp": updated_at_iso,
                                "author": requesting_agent_id,
                                "content": notes_content,
                            }
                        )
                    update_fields.append("notes = ?")
                    update_params.append(json.dumps(current_notes))

                    update_params.append(task_id)

                    # Validate field assignments for security
                    allowed_bulk_fields = ["status = ?", "updated_at = ?", "notes = ?"]
                    safe_fields = [
                        field for field in update_fields if field in allowed_bulk_fields
                    ]

                    if safe_fields:
                        set_clause = ", ".join(safe_fields)
                        bulk_update_sql = (
                            f"UPDATE tasks SET {set_clause} WHERE task_id = ?"
                        )
                        cursor.execute(bulk_update_sql, tuple(update_params))

                    # Update in-memory cache
                    if task_id in g.tasks:
                        g.tasks[task_id]["status"] = new_status
                        g.tasks[task_id]["updated_at"] = updated_at_iso
                        g.tasks[task_id]["notes"] = current_notes

                    results.append(
                        f"Operation {i+1}: Task '{task_id}' status updated to '{new_status}'"
                    )

                elif operation_type == "update_priority":
                    new_priority = op.get("priority")

                    if not new_priority or new_priority not in [
                        "low",
                        "medium",
                        "high",
                    ]:
                        results.append(
                            f"Operation {i+1}: Invalid priority '{new_priority}'"
                        )
                        continue

                    cursor.execute(
                        "UPDATE tasks SET priority = ?, updated_at = ? WHERE task_id = ?",
                        (new_priority, updated_at_iso, task_id),
                    )

                    if task_id in g.tasks:
                        g.tasks[task_id]["priority"] = new_priority
                        g.tasks[task_id]["updated_at"] = updated_at_iso

                    results.append(
                        f"Operation {i+1}: Task '{task_id}' priority updated to '{new_priority}'"
                    )

                elif operation_type == "add_note":
                    note_content = op.get("content")

                    if not note_content:
                        results.append(
                            f"Operation {i+1}: Missing 'content' for add_note operation"
                        )
                        continue

                    current_notes = json.loads(task_data.get("notes") or "[]")
                    current_notes.append(
                        {
                            "timestamp": updated_at_iso,
                            "author": requesting_agent_id,
                            "content": note_content,
                        }
                    )

                    cursor.execute(
                        "UPDATE tasks SET notes = ?, updated_at = ? WHERE task_id = ?",
                        (json.dumps(current_notes), updated_at_iso, task_id),
                    )

                    if task_id in g.tasks:
                        g.tasks[task_id]["notes"] = current_notes
                        g.tasks[task_id]["updated_at"] = updated_at_iso

                    results.append(f"Operation {i+1}: Note added to task '{task_id}'")

                elif operation_type == "reassign" and is_admin_request:
                    new_assigned_to = op.get("assigned_to")

                    if not new_assigned_to:
                        results.append(
                            f"Operation {i+1}: Missing 'assigned_to' for reassign operation"
                        )
                        continue

                    cursor.execute(
                        "UPDATE tasks SET assigned_to = ?, updated_at = ? WHERE task_id = ?",
                        (new_assigned_to, updated_at_iso, task_id),
                    )

                    if task_id in g.tasks:
                        g.tasks[task_id]["assigned_to"] = new_assigned_to
                        g.tasks[task_id]["updated_at"] = updated_at_iso

                    results.append(
                        f"Operation {i+1}: Task '{task_id}' reassigned to '{new_assigned_to}'"
                    )

                else:
                    if operation_type == "reassign" and not is_admin_request:
                        results.append(
                            f"Operation {i+1}: Reassign operation requires admin privileges"
                        )
                    else:
                        results.append(
                            f"Operation {i+1}: Unknown operation type '{operation_type}'"
                        )

            except Exception as e:
                results.append(f"Operation {i+1}: Error processing - {str(e)}")
                logger.error(f"Error in bulk operation {i+1}: {e}", exc_info=True)

        # Log the bulk operation
        log_agent_action_to_db(
            cursor,
            requesting_agent_id,
            "bulk_task_operations",
            details={
                "operations_count": len(operations),
                "success_count": len([r for r in results if "Error" not in r]),
            },
        )
        conn.commit()

        response_text = (
            f"Bulk Task Operations Results ({len(operations)} operations):\n\n"
            + "\n".join(results)
        )

        log_audit(
            requesting_agent_id,
            "bulk_task_operations",
            {"operations_count": len(operations)},
        )
        return [mcp_types.TextContent(type="text", text=response_text)]

    except sqlite3.Error as e_sql:
        if conn:
            conn.rollback()
        logger.error(f"Database error in bulk task operations: {e_sql}", exc_info=True)
        return [
            mcp_types.TextContent(
                type="text", text=f"Database error in bulk operations: {e_sql}"
            )
        ]
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Unexpected error in bulk task operations: {e}", exc_info=True)
        return [
            mcp_types.TextContent(
                type="text", text=f"Unexpected error in bulk operations: {e}"
            )
        ]
    finally:
        if conn:
            conn.close()


# --- search_tasks tool ---
async def search_tasks_tool_impl(
    arguments: Dict[str, Any],
) -> List[mcp_types.TextContent]:
    agent_auth_token = arguments.get("token")
    search_query = arguments.get("search_query")
    status_filter = arguments.get("status_filter")
    max_results = arguments.get("max_results", 20)
    include_notes = arguments.get("include_notes", True)

    requesting_agent_id = get_agent_id(agent_auth_token)
    if not requesting_agent_id:
        return [
            mcp_types.TextContent(
                type="text", text="Unauthorized: Valid token required"
            )
        ]

    if not search_query or not search_query.strip():
        return [
            mcp_types.TextContent(
                type="text", text="Error: search_query is required and cannot be empty."
            )
        ]

    is_admin_request = verify_token(agent_auth_token, "admin")

    # Prepare search terms
    search_terms = [
        term.strip().lower() for term in search_query.split() if len(term.strip()) > 2
    ]
    if not search_terms:
        return [
            mcp_types.TextContent(
                type="text",
                text="Error: Search query must contain terms longer than 2 characters.",
            )
        ]

    # Get tasks user can see
    candidate_tasks = []
    for task_id, task_data in g.tasks.items():
        # Permission check
        if not is_admin_request and task_data.get("assigned_to") != requesting_agent_id:
            continue

        # Status filter
        if status_filter and task_data.get("status") != status_filter:
            continue

        candidate_tasks.append(task_data)

    if not candidate_tasks:
        return [
            mcp_types.TextContent(
                type="text", text="No tasks found matching the criteria."
            )
        ]

    # Score tasks by relevance
    scored_results = []
    for task in candidate_tasks:
        score = 0.0
        matched_fields = []

        # Search in title (highest weight)
        title = (task.get("title") or "").lower()
        title_matches = sum(1 for term in search_terms if term in title)
        if title_matches > 0:
            score += title_matches * 3.0
            matched_fields.append(f"title ({title_matches} terms)")

        # Search in description (medium weight)
        description = (task.get("description") or "").lower()
        desc_matches = sum(1 for term in search_terms if term in description)
        if desc_matches > 0:
            score += desc_matches * 2.0
            matched_fields.append(f"description ({desc_matches} terms)")

        # Search in notes (lower weight)
        if include_notes:
            notes = task.get("notes", [])
            if isinstance(notes, str):
                try:
                    notes = json.loads(notes)
                except:
                    notes = []

            notes_content = " ".join(
                [note.get("content", "") for note in notes if isinstance(note, dict)]
            ).lower()
            notes_matches = sum(1 for term in search_terms if term in notes_content)
            if notes_matches > 0:
                score += notes_matches * 1.0
                matched_fields.append(f"notes ({notes_matches} terms)")

        # Exact phrase bonus
        full_text = f"{title} {description}".lower()
        if search_query.lower() in full_text:
            score += 2.0
            matched_fields.append("exact phrase")

        if score > 0:
            scored_results.append((task, score, matched_fields))

    if not scored_results:
        return [
            mcp_types.TextContent(
                type="text", text=f"No tasks found containing '{search_query}'."
            )
        ]

    # Sort by relevance (score descending, then by updated_at descending)
    scored_results.sort(key=lambda x: (x[1], x[0].get("updated_at", "")), reverse=True)

    # Limit results
    scored_results = scored_results[:max_results]

    # Format response with token awareness
    response_parts = [
        f"Search Results for '{search_query}' ({len(scored_results)} found):\n"
    ]
    current_tokens = len("\n".join(response_parts)) // 4  # Simple token estimation

    for i, (task, score, matched_fields) in enumerate(scored_results):
        if current_tokens >= 20000:  # Leave room for truncation message
            remaining = len(scored_results) - i
            response_parts.append(
                f"\n⚠️  Response truncated - {remaining} more results available"
            )
            response_parts.append(
                "Use max_results parameter or refine search to see more"
            )
            break

        # Format task result
        task_text = f"\n{i+1}. **{task.get('title', 'Untitled')}** (ID: {task.get('task_id', 'N/A')})"
        task_text += f"\n   Status: {task.get('status', 'N/A')} | Priority: {task.get('priority', 'medium')} | Assigned: {task.get('assigned_to', 'None')}"
        task_text += (
            f"\n   Relevance Score: {score:.1f} | Matched: {', '.join(matched_fields)}"
        )

        # Add truncated description
        desc = task.get("description", "No description")
        if len(desc) > 200:
            desc = desc[:200] + "..."
        task_text += f"\n   Description: {desc}"

        # Check token limit with safety buffer
        task_tokens = estimate_tokens(task_text)
        safety_buffer = 1000
        if current_tokens + task_tokens <= (20000 - safety_buffer):
            response_parts.append(task_text)
            current_tokens += task_tokens
        else:
            remaining = len(scored_results) - i
            response_parts.append(
                f"\n⚠️  Response truncated - {remaining} more results available"
            )
            break

    # Add usage tips
    response_parts.append(f"\n\n💡 Tips:")
    response_parts.append("• Use view_tasks(task_id='ID') for full task details")
    response_parts.append("• Add status_filter to narrow results")
    response_parts.append("• Use max_results to control response size")

    log_audit(
        requesting_agent_id,
        "search_tasks",
        {"query": search_query, "results": len(scored_results)},
    )
    return [mcp_types.TextContent(type="text", text="\n".join(response_parts))]


# --- Register all task tools ---
def register_task_tools():
    register_tool(
        name="assign_task",
        description="Multi-mode task assignment tool. Mode 1: Create single task + assign agent. Mode 2: Create multiple tasks + assign agent. Mode 3: Assign agent to existing unassigned tasks. Includes workload analysis, intelligent parent suggestions, and coordination features.",
        input_schema={
            "type": "object",
            "properties": {
                "token": {
                    "type": "string",
                    "description": "Admin authentication token",
                },
                "agent_token": {
                    "type": "string",
                    "description": "Agent token to assign the task(s) to (optional - if not provided, creates unassigned tasks)",
                },
                # Mode 1: Single task creation (existing behavior)
                "task_title": {
                    "type": "string",
                    "description": "Title of the task (Mode 1: single task creation)",
                },
                "task_description": {
                    "type": "string",
                    "description": "Detailed description of the task (Mode 1: single task creation)",
                },
                "priority": {
                    "type": "string",
                    "description": "Task priority (low, medium, high) - for single task mode",
                    "enum": ["low", "medium", "high"],
                    "default": "medium",
                },
                "depends_on_tasks": {
                    "type": "array",
                    "description": "List of task IDs this task depends on (Mode 1 only)",
                    "items": {"type": "string"},
                },
                "parent_task_id": {
                    "type": "string",
                    "description": "ID of the parent task (Mode 1 only)",
                },
                # Mode 2: Multiple task creation
                "tasks": {
                    "type": "array",
                    "description": "Array of tasks to create and assign (Mode 2: multiple task creation)",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Task title"},
                            "description": {
                                "type": "string",
                                "description": "Task description",
                            },
                            "priority": {
                                "type": "string",
                                "description": "Task priority",
                                "enum": ["low", "medium", "high"],
                                "default": "medium",
                            },
                            "parent_task_id": {
                                "type": "string",
                                "description": "Parent task ID for this task",
                            },
                        },
                        "required": ["title", "description"],
                        "additionalProperties": False,
                    },
                },
                # Mode 3: Existing task assignment
                "task_ids": {
                    "type": "array",
                    "description": "Array of existing task IDs to assign to agent (Mode 3: existing task assignment)",
                    "items": {"type": "string"},
                },
                # Smart coordination features (apply to all modes)
                "auto_suggest_parent": {
                    "type": "boolean",
                    "description": "Use AI to suggest optimal parent task based on content similarity (default: true)",
                    "default": True,
                },
                "validate_agent_workload": {
                    "type": "boolean",
                    "description": "Analyze agent capacity and provide workload warnings (default: true)",
                    "default": True,
                },
                "auto_schedule": {
                    "type": "boolean",
                    "description": "Auto-schedule task based on dependencies and agent availability (default: false)",
                    "default": False,
                },
                "coordination_notes": {
                    "type": "string",
                    "description": "Optional coordination context for team awareness and handoffs",
                },
                "estimated_hours": {
                    "type": "number",
                    "description": "Optional workload estimation in hours for capacity planning",
                },
                # RAG validation options
                "override_rag": {
                    "type": "boolean",
                    "description": "Override RAG validation suggestions (optional, defaults to false - accepts suggestions)",
                    "default": False,
                },
                "override_reason": {
                    "type": "string",
                    "description": "Reason for overriding RAG validation (required if override_rag is true)",
                },
            },
            "required": ["token"],
            "additionalProperties": False,
        },
        implementation=assign_task_tool_impl,
    )

    register_tool(
        name="create_self_task",  # main.py:1726
        description="Agent tool to create a task for themselves. IMPORTANT: parent_task_id is REQUIRED - agents cannot create root tasks.",
        input_schema={  # From main.py:1727-1750
            "type": "object",
            "properties": {
                "token": {
                    "type": "string",
                    "description": "Agent authentication token",
                },
                "task_title": {"type": "string", "description": "Title of the task"},
                "task_description": {
                    "type": "string",
                    "description": "Detailed description of the task",
                },
                "priority": {
                    "type": "string",
                    "description": "Task priority (low, medium, high)",
                    "enum": ["low", "medium", "high"],
                    "default": "medium",
                },
                "depends_on_tasks": {
                    "type": "array",
                    "description": "List of task IDs this task depends on (optional)",
                    "items": {"type": "string"},
                },
                "parent_task_id": {
                    "type": "string",
                    "description": "ID of the parent task (defaults to agent's current task if not specified, but MUST have a parent)",
                },
            },
            "required": ["token", "task_title", "task_description"],
            "additionalProperties": False,
        },
        implementation=create_self_task_tool_impl,
    )

    register_tool(
        name="update_task_status",
        description="Smart task status update tool with bulk operations, dependency management, and cascade features. Supports single task or bulk updates with intelligent automation.",
        input_schema={
            "type": "object",
            "properties": {
                "token": {
                    "type": "string",
                    "description": "Authentication token (agent or admin)",
                },
                "task_id": {
                    "type": "string",
                    "description": "ID of the task to update (for single task operations)",
                },
                "task_ids": {
                    "type": "array",
                    "description": "List of task IDs for bulk operations (alternative to task_id)",
                    "items": {"type": "string"},
                },
                "status": {
                    "type": "string",
                    "description": "New status for the task(s)",
                    "enum": [
                        "pending",
                        "in_progress",
                        "completed",
                        "cancelled",
                        "failed",
                    ],
                },
                "notes": {
                    "type": "string",
                    "description": "Optional notes about the status update to be appended.",
                },
                # Admin Only Optional Fields
                "title": {
                    "type": "string",
                    "description": "(Admin Only) New title for the task",
                },
                "description": {
                    "type": "string",
                    "description": "(Admin Only) New description for the task",
                },
                "priority": {
                    "type": "string",
                    "description": "(Admin Only) New priority",
                    "enum": ["low", "medium", "high"],
                },
                "assigned_to": {
                    "type": "string",
                    "description": "(Admin Only) New agent ID to assign the task to",
                },
                "depends_on_tasks": {
                    "type": "array",
                    "description": "(Admin Only) New list of task IDs this task depends on",
                    "items": {"type": "string"},
                },
                # Smart Features
                "auto_update_dependencies": {
                    "type": "boolean",
                    "description": "Automatically advance dependent tasks when their dependencies are completed (default: true)",
                    "default": True,
                },
                "cascade_to_children": {
                    "type": "boolean",
                    "description": "Cascade status changes to child tasks (only for failed/cancelled states, default: false)",
                    "default": False,
                },
                "validate_dependencies": {
                    "type": "boolean",
                    "description": "Validate dependency constraints before updating (default: true)",
                    "default": True,
                },
            },
            "required": ["token", "status"],
            "additionalProperties": False,
        },
        implementation=update_task_status_tool_impl,
    )

    register_tool(
        name="view_tasks",
        description="Smart task viewer with dependency analysis, health metrics, and advanced filtering. Provides comprehensive task insights with intelligent pagination.",
        input_schema={
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "Authentication token"},
                "agent_id": {
                    "type": "string",
                    "description": "Filter tasks by agent ID (optional). If non-admin, can only be self.",
                },
                "status": {
                    "type": "string",
                    "description": "Filter tasks by status (optional)",
                    "enum": [
                        "pending",
                        "in_progress",
                        "completed",
                        "cancelled",
                        "failed",
                    ],
                },
                "max_tokens": {
                    "type": "integer",
                    "description": "Maximum response tokens (default: 25000)",
                    "minimum": 1000,
                    "maximum": 25000,
                },
                "start_after": {
                    "type": "string",
                    "description": "Task ID to start after (for pagination)",
                },
                "summary_mode": {
                    "type": "boolean",
                    "description": "If true, show only summary info to fit more tasks (default: false)",
                },
                # Smart filtering options
                "filter_priority": {
                    "type": "string",
                    "description": "Filter by priority level",
                    "enum": ["low", "medium", "high"],
                },
                "filter_parent_task": {
                    "type": "string",
                    "description": "Filter by parent task ID",
                },
                "show_blocked_tasks": {
                    "type": "boolean",
                    "description": "Show only blocked/waiting tasks (default: false)",
                },
                # Analysis and insights
                "show_dependencies": {
                    "type": "boolean",
                    "description": "Include dependency chain analysis for each task (default: false)",
                },
                "show_health_analysis": {
                    "type": "boolean",
                    "description": "Include overall task health metrics and analysis (default: false)",
                },
                # Sorting options
                "sort_by": {
                    "type": "string",
                    "description": "Sort tasks by specified field (default: created_at)",
                    "enum": ["created_at", "updated_at", "priority", "status"],
                    "default": "created_at",
                },
            },
            "required": ["token"],
            "additionalProperties": False,
        },
        implementation=view_tasks_tool_impl,
    )

    register_tool(
        name="search_tasks",
        description="Full-text search across task titles, descriptions, and notes. Critical for finding related work and avoiding duplication.",
        input_schema={
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "Authentication token"},
                "search_query": {
                    "type": "string",
                    "description": "Search terms to find in tasks",
                },
                "status_filter": {
                    "type": "string",
                    "description": "Optional status filter",
                    "enum": [
                        "pending",
                        "in_progress",
                        "completed",
                        "cancelled",
                        "failed",
                    ],
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum results to return (default: 20)",
                    "minimum": 1,
                    "maximum": 100,
                },
                "include_notes": {
                    "type": "boolean",
                    "description": "Include notes content in search (default: true)",
                },
            },
            "required": ["token", "search_query"],
            "additionalProperties": False,
        },
        implementation=search_tasks_tool_impl,
    )

    register_tool(
        name="request_assistance",  # main.py:1808
        description="Request assistance with a task. This creates a child task assigned to 'None' and notifies admin.",
        input_schema={  # From main.py:1809-1823
            "type": "object",
            "properties": {
                "token": {
                    "type": "string",
                    "description": "Agent authentication token",
                },
                "task_id": {
                    "type": "string",
                    "description": "ID of the task for which assistance is needed (parent task).",
                },
                "description": {
                    "type": "string",
                    "description": "Description of the assistance required.",
                },
            },
            "required": ["token", "task_id", "description"],
            "additionalProperties": False,
        },
        implementation=request_assistance_tool_impl,
    )

    register_tool(
        name="bulk_task_operations",
        description="Perform multiple task operations in a single atomic transaction. Supports update_status, update_priority, add_note, and reassign (admin only) operations. Critical for efficient batch task management.",
        input_schema={
            "type": "object",
            "properties": {
                "token": {
                    "type": "string",
                    "description": "Authentication token (agent or admin)",
                },
                "operations": {
                    "type": "array",
                    "description": "List of operations to perform",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "description": "Operation type",
                                "enum": [
                                    "update_status",
                                    "update_priority",
                                    "add_note",
                                    "reassign",
                                ],
                            },
                            "task_id": {
                                "type": "string",
                                "description": "Task ID to operate on",
                            },
                            "status": {
                                "type": "string",
                                "description": "New status for update_status operation",
                                "enum": [
                                    "pending",
                                    "in_progress",
                                    "completed",
                                    "cancelled",
                                    "failed",
                                ],
                            },
                            "priority": {
                                "type": "string",
                                "description": "New priority for update_priority operation",
                                "enum": ["low", "medium", "high"],
                            },
                            "content": {
                                "type": "string",
                                "description": "Note content for add_note operation",
                            },
                            "notes": {
                                "type": "string",
                                "description": "Notes for update_status operation",
                            },
                            "assigned_to": {
                                "type": "string",
                                "description": "New assignee for reassign operation (admin only)",
                            },
                        },
                        "required": ["type", "task_id"],
                        "additionalProperties": False,
                    },
                    "minItems": 1,
                },
            },
            "required": ["token", "operations"],
            "additionalProperties": False,
        },
        implementation=bulk_task_operations_tool_impl,
    )

    register_tool(
        name="delete_task",
        description="Delete a task permanently with cascade handling for related tasks. Admin-only operation with comprehensive safety checks.",
        input_schema={
            "type": "object",
            "properties": {
                "token": {
                    "type": "string",
                    "description": "Admin authentication token",
                },
                "task_id": {
                    "type": "string",
                    "description": "ID of the task to delete",
                },
                "force_delete": {
                    "type": "boolean",
                    "description": "Force deletion even if task has children or dependencies (default: false)",
                    "default": False,
                },
            },
            "required": ["token", "task_id"],
            "additionalProperties": False,
        },
        implementation=delete_task_tool_impl,
    )


async def delete_task_tool_impl(
    arguments: Dict[str, Any],
) -> List[mcp_types.TextContent]:
    """
    Delete a task permanently with cascade handling for related tasks.
    Admin-only operation with comprehensive safety checks.
    """
    admin_token = arguments.get("token")
    task_id = arguments.get("task_id")
    force_delete = arguments.get("force_delete", False)

    # Verify admin permissions
    if not verify_token(admin_token, "admin"):
        return [
            mcp_types.TextContent(
                type="text", text="Unauthorized: Admin token required"
            )
        ]

    if not task_id:
        return [mcp_types.TextContent(type="text", text="Error: task_id is required")]

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if task exists
        cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        task_row = cursor.fetchone()

        if not task_row:
            return [
                mcp_types.TextContent(
                    type="text", text=f"Error: Task '{task_id}' not found"
                )
            ]

        task_data = dict(task_row)

        # Parse relationships
        child_tasks = json.loads(task_data.get("child_tasks", "[]"))
        depends_on_tasks = json.loads(task_data.get("depends_on_tasks", "[]"))

        # Check for child tasks
        if child_tasks and not force_delete:
            return [
                mcp_types.TextContent(
                    type="text",
                    text=f"Error: Task '{task_id}' has {len(child_tasks)} child tasks: {child_tasks}. Use force_delete=true to cascade delete.",
                )
            ]

        # Check for tasks that depend on this one
        cursor.execute(
            "SELECT task_id, title FROM tasks WHERE json_extract(depends_on_tasks, '$') LIKE ?",
            (f'%"{task_id}"%',),
        )
        dependent_tasks = cursor.fetchall()

        if dependent_tasks and not force_delete:
            dependent_list = [
                f"{row['task_id']} ({row['title']})" for row in dependent_tasks
            ]
            return [
                mcp_types.TextContent(
                    type="text",
                    text=f"Error: {len(dependent_tasks)} tasks depend on '{task_id}': {dependent_list}. Use force_delete=true to cascade delete.",
                )
            ]

        # Begin cascade deletion operations
        cascade_operations = []

        # Update parent task to remove this child
        if task_data.get("parent_task"):
            parent_id = task_data["parent_task"]
            cursor.execute(
                "SELECT child_tasks FROM tasks WHERE task_id = ?", (parent_id,)
            )
            parent_row = cursor.fetchone()

            if parent_row:
                parent_children = json.loads(parent_row["child_tasks"] or "[]")
                if task_id in parent_children:
                    parent_children.remove(task_id)
                    cursor.execute(
                        "UPDATE tasks SET child_tasks = ?, updated_at = ? WHERE task_id = ?",
                        (
                            json.dumps(parent_children),
                            datetime.datetime.now().isoformat(),
                            parent_id,
                        ),
                    )
                    cascade_operations.append(
                        f"Updated parent task '{parent_id}' to remove child reference"
                    )

        # Handle child tasks
        if child_tasks and force_delete:
            for child_id in child_tasks:
                cursor.execute("DELETE FROM tasks WHERE task_id = ?", (child_id,))
                if cursor.rowcount > 0:
                    cascade_operations.append(f"Deleted child task '{child_id}'")

        # Handle dependent tasks
        if dependent_tasks and force_delete:
            for dep_row in dependent_tasks:
                dep_id = dep_row["task_id"]
                cursor.execute(
                    "SELECT depends_on_tasks FROM tasks WHERE task_id = ?", (dep_id,)
                )
                dep_task_row = cursor.fetchone()

                if dep_task_row:
                    dep_dependencies = json.loads(
                        dep_task_row["depends_on_tasks"] or "[]"
                    )
                    if task_id in dep_dependencies:
                        dep_dependencies.remove(task_id)
                        cursor.execute(
                            "UPDATE tasks SET depends_on_tasks = ?, updated_at = ? WHERE task_id = ?",
                            (
                                json.dumps(dep_dependencies),
                                datetime.datetime.now().isoformat(),
                                dep_id,
                            ),
                        )
                        cascade_operations.append(
                            f"Updated task '{dep_id}' to remove dependency on '{task_id}'"
                        )

        # Delete the main task
        cursor.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))

        if cursor.rowcount == 0:
            return [
                mcp_types.TextContent(
                    type="text", text=f"Error: Failed to delete task '{task_id}'"
                )
            ]

        # Log the deletion action
        log_agent_action_to_db(
            cursor=cursor,
            agent_id="admin",
            action_type="deleted_task",
            task_id=task_id,
            details={
                "task_title": task_data.get("title"),
                "force_delete": force_delete,
                "cascade_operations": cascade_operations,
            },
        )

        conn.commit()

        # Prepare response
        response_parts = [
            f"Task '{task_id}' ({task_data.get('title', 'Untitled')}) deleted successfully."
        ]

        if cascade_operations:
            response_parts.append("\nCascade Operations:")
            for op in cascade_operations:
                response_parts.append(f"  • {op}")

        response_parts.append(
            f"\nDeletion completed at: {datetime.datetime.now().isoformat()}"
        )

        return [mcp_types.TextContent(type="text", text="\n".join(response_parts))]

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error in delete_task_tool_impl: {e}", exc_info=True)
        return [
            mcp_types.TextContent(type="text", text=f"Error deleting task: {str(e)}")
        ]
    finally:
        if conn:
            conn.close()


# Call registration when this module is imported
register_task_tools()
