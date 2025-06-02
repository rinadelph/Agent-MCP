# Agent-MCP/mcp_template/mcp_server_src/tools/phase_management_tools.py

import json
import datetime
import sqlite3
from typing import List, Dict, Any, Optional

import mcp.types as mcp_types

from .registry import register_tool
from ..core.config import logger
from ..core import globals as g
from ..core.auth import get_agent_id, verify_token
from ..utils.audit_utils import log_audit
from ..db.connection import get_db_connection
from ..db.actions.agent_actions_db import log_agent_action_to_db

def _get_phase_hierarchy() -> Dict[str, Any]:
    """Define the linear phase hierarchy for Agent MCP"""
    return {
        "phases": [
            {
                "phase_id": "phase_1_foundation",
                "name": "Phase 1: Foundation",
                "description": "Core system architecture, database, authentication, and basic APIs",
                "order": 1,
                "prerequisites": [],
                "theory_focus": "System foundation and core data structures"
            },
            {
                "phase_id": "phase_2_intelligence", 
                "name": "Phase 2: Intelligence",
                "description": "RAG system, embeddings, context management, and AI integration",
                "order": 2,
                "prerequisites": ["phase_1_foundation"],
                "theory_focus": "Knowledge systems and AI intelligence integration"
            },
            {
                "phase_id": "phase_3_coordination",
                "name": "Phase 3: Coordination", 
                "description": "Multi-agent workflows, task orchestration, and system integration",
                "order": 3,
                "prerequisites": ["phase_2_intelligence"],
                "theory_focus": "Agent coordination and workflow orchestration"
            },
            {
                "phase_id": "phase_4_optimization",
                "name": "Phase 4: Optimization",
                "description": "Performance tuning, scaling, monitoring, and production readiness",
                "order": 4,
                "prerequisites": ["phase_3_coordination"],
                "theory_focus": "System optimization and production deployment"
            }
        ],
        "linear_enforcement": True,
        "agent_termination_required": True,
        "completion_threshold": 100  # 100% completion required before next phase
    }

def _analyze_phase_completion(cursor, phase_id: str) -> Dict[str, Any]:
    """Analyze completion status of a phase based on root task workstreams"""
    
    # Get all ROOT tasks for this phase (direct children of phase)
    cursor.execute("""
        SELECT task_id, title, status, priority, assigned_to, created_at, updated_at
        FROM tasks 
        WHERE parent_task = ? AND status != 'cancelled'
        ORDER BY priority DESC, created_at ASC
    """, (phase_id,))
    
    root_tasks = [dict(row) for row in cursor.fetchall()]
    
    if not root_tasks:
        return {
            "phase_id": phase_id,
            "total_root_tasks": 0,
            "completed_root_tasks": 0,
            "completion_percentage": 0,
            "can_advance": False,
            "blocking_root_tasks": [],
            "root_task_details": [],
            "status": "empty"
        }
    
    # Analyze each root task's completion (including its subtasks)
    root_task_details = []
    completed_root_tasks = 0
    
    for root_task in root_tasks:
        root_task_analysis = _analyze_root_task_completion(cursor, root_task['task_id'])
        root_task_details.append({
            "task_id": root_task['task_id'],
            "title": root_task['title'],
            "status": root_task['status'],
            "assigned_to": root_task['assigned_to'],
            "completion_percentage": root_task_analysis['completion_percentage'],
            "total_subtasks": root_task_analysis['total_subtasks'],
            "completed_subtasks": root_task_analysis['completed_subtasks'],
            "can_complete": root_task_analysis['can_complete'],
            "blocking_subtasks": root_task_analysis['blocking_subtasks']
        })
        
        # Root task is considered complete if ALL its subtasks are complete AND root task is marked complete
        if root_task_analysis['can_complete'] and root_task['status'] == 'completed':
            completed_root_tasks += 1
    
    total_root_tasks = len(root_tasks)
    completion_percentage = (completed_root_tasks / total_root_tasks) * 100 if total_root_tasks > 0 else 0
    
    # Find blocking root tasks (not fully completed)
    blocking_root_tasks = [
        {
            "task_id": detail["task_id"],
            "title": detail["title"],
            "status": detail["status"],
            "assigned_to": detail["assigned_to"],
            "completion_percentage": detail["completion_percentage"],
            "blocking_subtasks_count": len(detail["blocking_subtasks"])
        }
        for detail in root_task_details 
        if not (detail['can_complete'] and detail['task_id'] in [t['task_id'] for t in root_tasks if t['status'] == 'completed'])
    ]
    
    # Determine phase status based on root task completion
    if completion_percentage == 100:
        status = "completed"
    elif completion_percentage >= 80:
        status = "near_completion"
    elif any(detail['completion_percentage'] > 0 for detail in root_task_details):
        status = "in_progress"
    elif any(detail['status'] == 'failed' for detail in root_task_details):
        status = "blocked"
    else:
        status = "pending"
    
    return {
        "phase_id": phase_id,
        "total_root_tasks": total_root_tasks,
        "completed_root_tasks": completed_root_tasks,
        "completion_percentage": round(completion_percentage, 1),
        "can_advance": completion_percentage == 100,
        "blocking_root_tasks": blocking_root_tasks,
        "root_task_details": root_task_details,
        "status": status
    }

def _analyze_root_task_completion(cursor, root_task_id: str) -> Dict[str, Any]:
    """Analyze completion of a root task including all its subtasks recursively"""
    
    # Get all subtasks under this root task (recursive)
    cursor.execute("""
        WITH RECURSIVE task_tree AS (
            SELECT task_id, title, status, assigned_to
            FROM tasks 
            WHERE parent_task = ? AND status != 'cancelled'
            
            UNION ALL
            
            SELECT t.task_id, t.title, t.status, t.assigned_to
            FROM tasks t
            INNER JOIN task_tree tt ON t.parent_task = tt.task_id
            WHERE t.status != 'cancelled'
        )
        SELECT * FROM task_tree
    """, (root_task_id,))
    
    subtasks = [dict(row) for row in cursor.fetchall()]
    
    if not subtasks:
        # Root task has no subtasks - completion based on root task status only
        return {
            "total_subtasks": 0,
            "completed_subtasks": 0,
            "completion_percentage": 100,  # No subtasks means root task itself determines completion
            "can_complete": True,
            "blocking_subtasks": []
        }
    
    # Calculate subtask completion
    total_subtasks = len(subtasks)
    completed_subtasks = len([t for t in subtasks if t['status'] == 'completed'])
    failed_subtasks = len([t for t in subtasks if t['status'] == 'failed'])
    
    completion_percentage = (completed_subtasks / total_subtasks) * 100 if total_subtasks > 0 else 100
    
    # Root task can complete if ALL subtasks are completed
    can_complete = completion_percentage == 100
    
    # Find blocking subtasks
    blocking_subtasks = [
        {
            "task_id": t["task_id"],
            "title": t["title"],
            "status": t["status"],
            "assigned_to": t["assigned_to"]
        }
        for t in subtasks if t['status'] not in ['completed', 'cancelled']
    ]
    
    return {
        "total_subtasks": total_subtasks,
        "completed_subtasks": completed_subtasks,
        "failed_subtasks": failed_subtasks,
        "completion_percentage": round(completion_percentage, 1),
        "can_complete": can_complete,
        "blocking_subtasks": blocking_subtasks
    }

def _get_active_agents_for_phase(cursor, phase_id: str) -> List[Dict[str, Any]]:
    """Get all agents currently working on tasks in this phase (including all subtasks)"""
    
    # Get agents working on root tasks and all their subtasks
    cursor.execute("""
        WITH RECURSIVE phase_tasks AS (
            -- Root tasks directly under phase
            SELECT task_id, assigned_to FROM tasks WHERE parent_task = ?
            
            UNION ALL
            
            -- All subtasks under root tasks
            SELECT t.task_id, t.assigned_to
            FROM tasks t
            INNER JOIN phase_tasks pt ON t.parent_task = pt.task_id
        )
        SELECT DISTINCT assigned_to, COUNT(*) as task_count
        FROM phase_tasks pt
        INNER JOIN tasks t ON pt.task_id = t.task_id
        WHERE t.status IN ('pending', 'in_progress') AND assigned_to IS NOT NULL
        GROUP BY assigned_to
    """, (phase_id,))
    
    agents = []
    for row in cursor.fetchall():
        agents.append({
            "agent_id": row["assigned_to"],
            "active_tasks": row["task_count"]
        })
    
    return agents

# --- create_phase tool ---
async def create_phase_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    admin_auth_token = arguments.get("token")
    phase_type = arguments.get("phase_type")  # foundation, intelligence, coordination, optimization
    custom_name = arguments.get("custom_name")  # Optional custom phase name
    custom_description = arguments.get("custom_description")  # Optional custom description
    
    if not verify_token(admin_auth_token, "admin"):
        return [mcp_types.TextContent(type="text", text="Unauthorized: Admin token required")]
    
    if not phase_type:
        return [mcp_types.TextContent(type="text", text="Error: phase_type is required")]
    
    requesting_agent_id = get_agent_id(admin_auth_token)
    log_audit(requesting_agent_id, "create_phase", {"phase_type": phase_type})
    
    phase_hierarchy = _get_phase_hierarchy()
    
    # Find the phase definition
    phase_def = None
    for phase in phase_hierarchy["phases"]:
        if phase_type in phase["phase_id"]:
            phase_def = phase
            break
    
    if not phase_def:
        valid_types = [p["phase_id"].split("_")[1] + "_" + p["phase_id"].split("_")[2] for p in phase_hierarchy["phases"]]
        return [mcp_types.TextContent(type="text", text=f"Invalid phase_type. Valid options: {', '.join(valid_types)}")]
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if phase already exists
        cursor.execute("SELECT task_id FROM tasks WHERE task_id = ?", (phase_def["phase_id"],))
        if cursor.fetchone():
            return [mcp_types.TextContent(type="text", text=f"Phase '{phase_def['phase_id']}' already exists")]
        
        # Validate linear progression - check if prerequisites are completed
        if phase_def["prerequisites"]:
            for prereq in phase_def["prerequisites"]:
                completion = _analyze_phase_completion(cursor, prereq)
                if not completion["can_advance"]:
                    return [mcp_types.TextContent(
                        type="text",
                        text=f"Cannot create phase '{phase_def['phase_id']}'. Prerequisite phase '{prereq}' is only {completion['completion_percentage']}% complete.\n"
                             f"Linear phase progression requires 100% completion of previous phases.\n"
                             f"Blocking tasks in {prereq}: {len(completion['blocking_tasks'])}"
                    )]
        
        # Create phase as a special root task
        created_at_iso = datetime.datetime.now().isoformat()
        
        phase_title = custom_name or phase_def["name"]
        phase_description = custom_description or phase_def["description"]
        
        # Add theory focus to description
        phase_description += f"\n\n🧠 Theory Focus: {phase_def['theory_focus']}"
        
        phase_data = {
            "task_id": phase_def["phase_id"],
            "title": phase_title,
            "description": phase_description,
            "assigned_to": None,  # Phases are not assigned to specific agents
            "created_by": "admin",
            "status": "pending",
            "priority": "high",
            "created_at": created_at_iso,
            "updated_at": created_at_iso,
            "parent_task": None,  # Phases are root tasks
            "child_tasks": json.dumps([]),
            "depends_on_tasks": json.dumps(phase_def["prerequisites"]),
            "notes": json.dumps([{
                "timestamp": created_at_iso,
                "author": "system",
                "content": f"📊 Phase {phase_def['order']} created in linear progression. Prerequisites: {', '.join(phase_def['prerequisites']) if phase_def['prerequisites'] else 'None'}"
            }])
        }
        
        cursor.execute("""
            INSERT INTO tasks (task_id, title, description, assigned_to, created_by, status, priority,
                             created_at, updated_at, parent_task, child_tasks, depends_on_tasks, notes)
            VALUES (:task_id, :title, :description, :assigned_to, :created_by, :status, :priority,
                    :created_at, :updated_at, :parent_task, :child_tasks, :depends_on_tasks, :notes)
        """, phase_data)
        
        # Update in-memory cache
        phase_data_for_memory = phase_data.copy()
        phase_data_for_memory["child_tasks"] = []
        phase_data_for_memory["depends_on_tasks"] = phase_def["prerequisites"]
        phase_data_for_memory["notes"] = json.loads(phase_data["notes"])
        g.tasks[phase_def["phase_id"]] = phase_data_for_memory
        
        log_agent_action_to_db(cursor, requesting_agent_id, "create_phase", 
                             phase_def["phase_id"], {"phase_order": phase_def["order"]})
        conn.commit()
        
        response_parts = [
            f"✅ **{phase_title} Created**",
            f"   Phase ID: {phase_def['phase_id']}",
            f"   Order: {phase_def['order']} of {len(phase_hierarchy['phases'])}",
            f"   Theory Focus: {phase_def['theory_focus']}",
            ""
        ]
        
        if phase_def["prerequisites"]:
            response_parts.append(f"✓ Prerequisites verified: {', '.join(phase_def['prerequisites'])}")
        else:
            response_parts.append("✓ No prerequisites (root phase)")
        
        response_parts.extend([
            "",
            "📋 **Next Steps:**",
            f"• Use assign_task with parent_task_id='{phase_def['phase_id']}' to add tasks to this phase",
            "• All root tasks must be 100% complete before advancing to next phase", 
            "• Agents will be terminated between phases for knowledge crystallization"
        ])
        
        return [mcp_types.TextContent(type="text", text="\n".join(response_parts))]
        
    except sqlite3.Error as e_sql:
        if conn: conn.rollback()
        logger.error(f"Database error creating phase: {e_sql}", exc_info=True)
        return [mcp_types.TextContent(type="text", text=f"Database error creating phase: {e_sql}")]
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Unexpected error creating phase: {e}", exc_info=True)
        return [mcp_types.TextContent(type="text", text=f"Unexpected error creating phase: {e}")]
    finally:
        if conn:
            conn.close()

# --- view_phase_status tool ---
async def view_phase_status_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    auth_token = arguments.get("token")
    phase_id = arguments.get("phase_id")  # Optional specific phase
    show_blocking_tasks = arguments.get("show_blocking_tasks", True)
    show_agent_assignments = arguments.get("show_agent_assignments", True)
    
    requesting_agent_id = get_agent_id(auth_token)
    if not requesting_agent_id:
        return [mcp_types.TextContent(type="text", text="Unauthorized: Valid token required")]
    
    log_audit(requesting_agent_id, "view_phase_status", {"phase_id": phase_id})
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        phase_hierarchy = _get_phase_hierarchy()
        
        if phase_id:
            # Show specific phase status
            phases_to_check = [p for p in phase_hierarchy["phases"] if p["phase_id"] == phase_id]
            if not phases_to_check:
                return [mcp_types.TextContent(type="text", text=f"Phase '{phase_id}' not found")]
        else:
            # Show all phases
            phases_to_check = phase_hierarchy["phases"]
        
        response_parts = ["📊 **Phase Status Overview**\n"]
        
        for phase_def in phases_to_check:
            completion = _analyze_phase_completion(cursor, phase_def["phase_id"])
            
            # Phase header with status icon
            status_icon = "✅" if completion["status"] == "completed" else \
                         "🟡" if completion["status"] == "in_progress" else \
                         "🔴" if completion["status"] == "blocked" else "⭐"
            
            response_parts.append(f"{status_icon} **{phase_def['name']}** ({completion['completion_percentage']}%)")
            response_parts.append(f"   ID: {phase_def['phase_id']} | Order: {phase_def['order']}")
            response_parts.append(f"   Root Tasks: {completion['completed_root_tasks']}/{completion['total_root_tasks']} completed")
            
            if completion["total_root_tasks"] > 0:
                response_parts.append(f"   Status: {completion['status']} | Can advance: {'Yes' if completion['can_advance'] else 'No'}")
            
            # Show blocking tasks if requested and exist
            if show_blocking_tasks and completion["blocking_root_tasks"]:
                response_parts.append(f"   🚫 Blocking root tasks ({len(completion['blocking_root_tasks'])}):")
                for root_task in completion["blocking_root_tasks"][:3]:  # Show first 3
                    response_parts.append(f"      - {root_task['task_id']}: {root_task['title']} ({root_task['completion_percentage']}%) → {root_task['assigned_to']}")
                    if root_task['blocking_subtasks_count'] > 0:
                        response_parts.append(f"        └── {root_task['blocking_subtasks_count']} incomplete subtasks")
                if len(completion["blocking_root_tasks"]) > 3:
                    response_parts.append(f"      ... and {len(completion['blocking_root_tasks']) - 3} more")
            
            # Show agent assignments if requested
            if show_agent_assignments and completion["total_root_tasks"] > 0:
                agents = _get_active_agents_for_phase(cursor, phase_def["phase_id"])
                if agents:
                    agent_list = ', '.join([f"{a['agent_id']}({a['active_tasks']})" for a in agents])
                    response_parts.append(f"   👥 Active agents: {agent_list}")
            
            response_parts.append("")
        
        # Add linear progression info
        response_parts.extend([
            "🔄 **Linear Progression Rules:**",
            "• Phases must be completed in order (1→2→3→4)",
            "• 100% root task completion required before phase advancement",
            "• All agents terminated between phases for knowledge crystallization",
            "• Next phase cannot begin until current phase is fully complete"
        ])
        
        return [mcp_types.TextContent(type="text", text="\n".join(response_parts))]
        
    except Exception as e:
        logger.error(f"Error viewing phase status: {e}", exc_info=True)
        return [mcp_types.TextContent(type="text", text=f"Error viewing phase status: {e}")]
    finally:
        if conn:
            conn.close()

# --- advance_phase tool ---
async def advance_phase_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    admin_auth_token = arguments.get("token")
    current_phase_id = arguments.get("current_phase_id")
    force_advance = arguments.get("force_advance", False)  # Override completion check
    terminate_agents = arguments.get("terminate_agents", True)  # Terminate agents between phases
    
    if not verify_token(admin_auth_token, "admin"):
        return [mcp_types.TextContent(type="text", text="Unauthorized: Admin token required")]
    
    if not current_phase_id:
        return [mcp_types.TextContent(type="text", text="Error: current_phase_id is required")]
    
    requesting_agent_id = get_agent_id(admin_auth_token)
    log_audit(requesting_agent_id, "advance_phase", {"current_phase_id": current_phase_id, "force": force_advance})
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Analyze current phase completion
        completion = _analyze_phase_completion(cursor, current_phase_id)
        
        if not force_advance and not completion["can_advance"]:
            response_parts = [
                f"❌ **Cannot Advance from {current_phase_id}**",
                f"   Completion: {completion['completion_percentage']}% (100% required)",
                f"   Blocking root tasks: {len(completion['blocking_root_tasks'])}",
                ""
            ]
            
            if completion["blocking_root_tasks"]:
                response_parts.append("🚫 **Blocking Root Tasks:**")
                for root_task in completion["blocking_root_tasks"][:5]:
                    response_parts.append(f"   - {root_task['task_id']}: {root_task['title']} ({root_task['completion_percentage']}%) → {root_task['assigned_to']}")
                    if root_task['blocking_subtasks_count'] > 0:
                        response_parts.append(f"     └── {root_task['blocking_subtasks_count']} incomplete subtasks blocking completion")
                if len(completion["blocking_root_tasks"]) > 5:
                    response_parts.append(f"   ... and {len(completion['blocking_root_tasks']) - 5} more root tasks")
            
            response_parts.extend([
                "",
                "💡 **To Advance:**",
                "• Complete all blocking root tasks",
                "• Use force_advance=true to override (not recommended)",
                "• Ensure proper knowledge crystallization documentation"
            ])
            
            return [mcp_types.TextContent(type="text", text="\n".join(response_parts))]
        
        # Mark current phase as completed
        updated_at_iso = datetime.datetime.now().isoformat()
        
        completion_note = {
            "timestamp": updated_at_iso,
            "author": "admin",
            "content": f"🎉 Phase completed! Completion: {completion['completion_percentage']}%. Ready for agent termination and knowledge crystallization."
        }
        
        cursor.execute("SELECT notes FROM tasks WHERE task_id = ?", (current_phase_id,))
        current_notes = json.loads(cursor.fetchone()["notes"] or "[]")
        current_notes.append(completion_note)
        
        cursor.execute("""
            UPDATE tasks SET status = 'completed', updated_at = ?, notes = ?
            WHERE task_id = ?
        """, (updated_at_iso, json.dumps(current_notes), current_phase_id))
        
        # Update in-memory cache
        if current_phase_id in g.tasks:
            g.tasks[current_phase_id]["status"] = "completed"
            g.tasks[current_phase_id]["updated_at"] = updated_at_iso
            g.tasks[current_phase_id]["notes"] = current_notes
        
        response_parts = [
            f"✅ **Phase {current_phase_id} Completed**",
            f"   Final completion: {completion['completion_percentage']}%",
            f"   Root tasks completed: {completion['completed_root_tasks']}/{completion['total_root_tasks']}",
            ""
        ]
        
        # Handle agent termination
        if terminate_agents:
            agents_to_terminate = _get_active_agents_for_phase(cursor, current_phase_id)
            response_parts.append(f"🔄 **Agent Termination Required:**")
            if agents_to_terminate:
                response_parts.append(f"   Agents to terminate: {', '.join([a['agent_id'] for a in agents_to_terminate])}")
                response_parts.append("   ⚠️ Use terminate_agent tool for each agent before creating next phase")
            else:
                response_parts.append("   ✓ No active agents found - ready for next phase")
            response_parts.append("")
        
        response_parts.extend([
            "📚 **Knowledge Crystallization:**",
            "• Document all phase learnings and decisions",
            "• Update project context with key findings", 
            "• Ensure comprehensive handoff documentation",
            "• All agents must be terminated before next phase creation",
            "",
            "🎯 **Next Steps:**",
            "1. Terminate all agents working on this phase",
            "2. Create comprehensive phase documentation",
            "3. Use create_phase to begin next phase",
            "4. Assign fresh agents to new phase tasks"
        ])
        
        log_agent_action_to_db(cursor, requesting_agent_id, "advance_phase", 
                             current_phase_id, {"completion_percentage": completion["completion_percentage"]})
        conn.commit()
        
        return [mcp_types.TextContent(type="text", text="\n".join(response_parts))]
        
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Error advancing phase: {e}", exc_info=True)
        return [mcp_types.TextContent(type="text", text=f"Error advancing phase: {e}")]
    finally:
        if conn:
            conn.close()

# --- Register phase management tools ---
def register_phase_management_tools():
    register_tool(
        name="create_phase",
        description="Create a new linear phase in the Agent MCP progression. Enforces linear phase dependencies and theory building structure.",
        input_schema={
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "Admin authentication token"},
                "phase_type": {
                    "type": "string", 
                    "description": "Type of phase to create",
                    "enum": ["foundation", "intelligence", "coordination", "optimization"]
                },
                "custom_name": {"type": "string", "description": "Optional custom phase name (overrides default)"},
                "custom_description": {"type": "string", "description": "Optional custom phase description (appends to default)"}
            },
            "required": ["token", "phase_type"],
            "additionalProperties": False
        },
        implementation=create_phase_tool_impl
    )
    
    register_tool(
        name="view_phase_status", 
        description="View linear phase progression status with completion metrics, blocking tasks, and agent assignments.",
        input_schema={
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "Authentication token"},
                "phase_id": {"type": "string", "description": "Optional specific phase ID to view (shows all phases if not provided)"},
                "show_blocking_tasks": {"type": "boolean", "description": "Show tasks blocking phase completion (default: true)", "default": True},
                "show_agent_assignments": {"type": "boolean", "description": "Show active agent assignments per phase (default: true)", "default": True}
            },
            "required": ["token"],
            "additionalProperties": False
        },
        implementation=view_phase_status_tool_impl
    )
    
    register_tool(
        name="advance_phase",
        description="Complete current phase and prepare for next phase. Enforces 100% completion and agent termination requirements.",
        input_schema={
            "type": "object", 
            "properties": {
                "token": {"type": "string", "description": "Admin authentication token"},
                "current_phase_id": {"type": "string", "description": "ID of phase to complete and advance from"},
                "force_advance": {"type": "boolean", "description": "Force advancement even if not 100% complete (not recommended)", "default": False},
                "terminate_agents": {"type": "boolean", "description": "Require agent termination between phases (default: true)", "default": True}
            },
            "required": ["token", "current_phase_id"],
            "additionalProperties": False
        },
        implementation=advance_phase_tool_impl
    )

# Call registration when this module is imported
register_phase_management_tools()