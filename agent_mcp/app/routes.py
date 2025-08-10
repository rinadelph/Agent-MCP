# Agent-MCP/mcp_template/mcp_server_src/app/routes.py
import os
import json
import datetime
import sqlite3
from pathlib import Path
from typing import Callable, List, Dict, Any # Added List, Dict, Any

from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from starlette.responses import JSONResponse, Response, PlainTextResponse
from starlette.requests import Request

# Project-specific imports
from ..core.config import logger
from ..core import globals as g
from ..core.auth import verify_token, get_agent_id as auth_get_agent_id
from ..utils.json_utils import get_sanitized_json_body
from ..db.connection import get_db_connection
from ..db.actions.agent_actions_db import log_agent_action_to_db

from ..features.dashboard.api import (
    fetch_graph_data_logic,
    fetch_task_tree_data_logic,
    fetch_supply_chain_data_logic
)
from ..features.dashboard.styles import get_node_style

# Import tool implementations that these dashboard APIs will call
from ..tools.admin_tools import (
    create_agent_tool_impl,
    terminate_agent_tool_impl
)
import mcp.types as mcp_types # For handling the result from tool_impl

# --- Dashboard and API Endpoints ---

async def simple_status_api_route(request: Request) -> JSONResponse:
    # Handle OPTIONS for CORS preflight
    if request.method == 'OPTIONS':
        return await handle_options(request)
    
    try:
        # Get system status
        from ..db.actions.agent_db import get_all_active_agents_from_db
        from ..db.actions.task_db import get_all_tasks_from_db
        
        agents = get_all_active_agents_from_db()
        tasks = get_all_tasks_from_db()
        
        # Count task statuses
        pending_tasks = len([t for t in tasks if t.get('status') == 'pending'])
        completed_tasks = len([t for t in tasks if t.get('status') == 'completed'])
        
        return JSONResponse({
            "server_running": True,
            "total_agents": len(agents),
            "active_agents": len([a for a in agents if a.get('status') == 'active']),
            "total_tasks": len(tasks),
            "pending_tasks": pending_tasks,
            "completed_tasks": completed_tasks,
            "last_updated": datetime.datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error in simple_status_api_route: {e}", exc_info=True)
        return JSONResponse({"error": f"Failed to get simple status: {str(e)}"}, status_code=500)

async def graph_data_api_route(request: Request) -> JSONResponse:
    # // ... (implementation from previous response)
    try:
        data = await fetch_graph_data_logic(g.file_map.copy())
        return JSONResponse(data)
    except Exception as e:
        logger.error(f"Error serving graph data: {e}", exc_info=True)
        return JSONResponse({'nodes': [], 'edges': [], 'error': str(e)}, status_code=500)

async def task_tree_data_api_route(request: Request) -> JSONResponse:
    # // ... (implementation from previous response)
    try:
        data = await fetch_task_tree_data_logic()
        return JSONResponse(data)
    except Exception as e:
        logger.error(f"Error serving task tree data: {e}", exc_info=True)
        return JSONResponse({'nodes': [], 'edges': [], 'error': str(e)}, status_code=500)

async def node_details_api_route(request: Request) -> JSONResponse:
    # // ... (implementation from previous response)
    node_id = request.query_params.get('node_id')
    if not node_id:
        return JSONResponse({'error': 'Missing node_id parameter'}, status_code=400)
    details: Dict[str, Any] = {'id': node_id, 'type': 'unknown', 'data': {}, 'actions': [], 'related': {}}
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        parts = node_id.split('_', 1)
        node_type_from_id = parts[0] if len(parts) > 1 else node_id
        actual_id_from_node = parts[1] if len(parts) > 1 else (node_id if node_type_from_id != 'admin' else 'admin')
        details['type'] = node_type_from_id
        if node_type_from_id == 'agent':
            cursor.execute("SELECT * FROM agents WHERE agent_id = ?", (actual_id_from_node,))
            row = cursor.fetchone();
            if row: details['data'] = dict(row)
            cursor.execute("SELECT timestamp, action_type, task_id, details FROM agent_actions WHERE agent_id = ? ORDER BY timestamp DESC LIMIT 10", (actual_id_from_node,))
            details['actions'] = [dict(r) for r in cursor.fetchall()]
            cursor.execute("SELECT task_id, title, status, priority FROM tasks WHERE assigned_to = ? ORDER BY created_at DESC LIMIT 10", (actual_id_from_node,))
            details['related']['assigned_tasks'] = [dict(r) for r in cursor.fetchall()]
        elif node_type_from_id == 'task':
            cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (actual_id_from_node,))
            row = cursor.fetchone();
            if row: details['data'] = dict(row)
            cursor.execute("SELECT timestamp, agent_id, action_type, details FROM agent_actions WHERE task_id = ? ORDER BY timestamp DESC LIMIT 10", (actual_id_from_node,))
            details['actions'] = [dict(r) for r in cursor.fetchall()]
        elif node_type_from_id == 'context':
            cursor.execute("SELECT * FROM project_context WHERE context_key = ?", (actual_id_from_node,))
            row = cursor.fetchone();
            if row: details['data'] = dict(row)
            cursor.execute("SELECT timestamp, agent_id, action_type FROM agent_actions WHERE (action_type = 'updated_context' OR action_type = 'update_project_context') AND details LIKE ? ORDER BY timestamp DESC LIMIT 5", (f'%"{actual_id_from_node}"%',))
            details['actions'] = [dict(r) for r in cursor.fetchall()]
        elif node_type_from_id == 'file':
            details['data'] = {'filepath': actual_id_from_node, 'info': g.file_map.get(actual_id_from_node, {})}
            cursor.execute("SELECT timestamp, agent_id, action_type, details FROM agent_actions WHERE (action_type LIKE '%_file' OR action_type LIKE 'claim_file_%' OR action_type = 'release_file') AND details LIKE ? ORDER BY timestamp DESC LIMIT 5", (f'%"{actual_id_from_node}"%',))
            details['actions'] = [dict(r) for r in cursor.fetchall()]
        elif node_type_from_id == 'admin':
            details['data'] = {'name': 'Admin User / System'}
            cursor.execute("SELECT timestamp, action_type, task_id, details FROM agent_actions WHERE agent_id = 'admin' ORDER BY timestamp DESC LIMIT 10")
            details['actions'] = [dict(r) for r in cursor.fetchall()]
        if not details.get('data') and node_type_from_id not in ['admin']:
             return JSONResponse({'error': 'Node data not found or type unrecognized'}, status_code=404)
    except Exception as e:
        logger.error(f"Error fetching details for node {node_id}: {e}", exc_info=True)
        return JSONResponse({'error': f'Failed to fetch node details: {str(e)}'}, status_code=500)
    finally:
        if conn: conn.close()
    return JSONResponse(details)

async def agents_list_api_route(request: Request) -> JSONResponse:
    # // ... (implementation from previous response)
    agents_list_data: List[Dict[str, Any]] = []
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        admin_style = get_node_style('admin')
        agents_list_data.append({
            'agent_id': 'Admin', 'status': 'system', 'color': admin_style.get('color', '#607D8B'),
            'created_at': 'N/A', 'current_task': 'N/A'
        })
        cursor.execute("SELECT agent_id, status, color, created_at, current_task FROM agents ORDER BY created_at DESC")
        for row in cursor.fetchall(): agents_list_data.append(dict(row))
    except Exception as e:
        logger.error(f"Error fetching agents list: {e}", exc_info=True)
        return JSONResponse({'error': f'Failed to fetch agents list: {str(e)}'}, status_code=500)
    finally:
        if conn: conn.close()
    return JSONResponse(agents_list_data)

async def tokens_api_route(request: Request) -> JSONResponse:
    # // ... (implementation from previous response)
    try:
        agent_tokens_list = []
        for token, data in g.active_agents.items():
            if data.get("status") != "terminated":
                agent_tokens_list.append({"agent_id": data.get("agent_id"), "token": token})
        return JSONResponse({"admin_token": g.admin_token, "agent_tokens": agent_tokens_list})
    except Exception as e:
        logger.error(f"Error retrieving tokens for dashboard: {e}", exc_info=True)
        return JSONResponse({"error": f"Error retrieving tokens: {str(e)}"}, status_code=500)

async def all_tasks_api_route(request: Request) -> JSONResponse:
    # // ... (implementation from previous response)
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks ORDER BY created_at DESC")
        tasks_data = [dict(row) for row in cursor.fetchall()]
        return JSONResponse(tasks_data)
    except Exception as e:
        logger.error(f"Error fetching all tasks: {e}", exc_info=True)
        return JSONResponse({"error": f"Failed to fetch all tasks: {str(e)}"}, status_code=500)
    finally:
        if conn: conn.close()

async def update_task_details_api_route(request: Request) -> JSONResponse:
    # // ... (implementation from previous response)
    if request.method != 'POST': return JSONResponse({"error": "Method not allowed"}, status_code=405)
    conn = None
    try:
        data = await get_sanitized_json_body(request)
        admin_auth_token = data.get('token'); task_id_to_update = data.get('task_id'); new_status = data.get('status')
        if not task_id_to_update or not new_status: return JSONResponse({"error": "task_id and status are required fields."}, status_code=400)
        if not verify_token(admin_auth_token, required_role='admin'): return JSONResponse({"error": "Invalid admin token"}, status_code=403)
        requesting_admin_id = auth_get_agent_id(admin_auth_token)
        conn = get_db_connection(); cursor = conn.cursor()
        cursor.execute("SELECT notes FROM tasks WHERE task_id = ?", (task_id_to_update,)); task_row = cursor.fetchone()
        if not task_row: return JSONResponse({"error": "Task not found"}, status_code=404)
        existing_notes_str = task_row["notes"]
        update_fields: List[str] = []; params: List[Any] = []; log_details: Dict[str, Any] = {"status_updated_to": new_status}
        update_fields.append("status = ?"); params.append(new_status)
        update_fields.append("updated_at = ?"); params.append(datetime.datetime.now().isoformat())
        if 'title' in data and data['title'] is not None: update_fields.append("title = ?"); params.append(data['title']); log_details["title_changed"] = True
        if 'description' in data and data['description'] is not None: update_fields.append("description = ?"); params.append(data['description']); log_details["description_changed"] = True
        if 'priority' in data and data['priority']: update_fields.append("priority = ?"); params.append(data['priority']); log_details["priority_changed"] = True
        if 'notes' in data and data['notes'] and isinstance(data['notes'], str) and data['notes'].strip():
            try: current_notes_list = json.loads(existing_notes_str or "[]")
            except json.JSONDecodeError: current_notes_list = []
            new_note_entry = {"timestamp": datetime.datetime.now().isoformat(), "author": requesting_admin_id, "content": data['notes'].strip()}
            current_notes_list.append(new_note_entry); update_fields.append("notes = ?"); params.append(json.dumps(current_notes_list)); log_details["notes_added"] = True
        params.append(task_id_to_update)
        if update_fields:
            placeholders = ', '.join(update_fields)
            query = f"UPDATE tasks SET {placeholders} WHERE task_id = ?"
            cursor.execute(query, tuple(params))
        log_agent_action_to_db(cursor, requesting_admin_id, "updated_task_dashboard", task_id=task_id_to_update, details=log_details); conn.commit()
        if task_id_to_update in g.tasks:
            cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id_to_update,)); updated_task_for_cache = cursor.fetchone()
            if updated_task_for_cache:
                g.tasks[task_id_to_update] = dict(updated_task_for_cache)
                for field_key in ["child_tasks", "depends_on_tasks", "notes"]:
                    if isinstance(g.tasks[task_id_to_update].get(field_key), str):
                        try: g.tasks[task_id_to_update][field_key] = json.loads(g.tasks[task_id_to_update][field_key] or "[]")
                        except json.JSONDecodeError: g.tasks[task_id_to_update][field_key] = []
            else: del g.tasks[task_id_to_update]
        return JSONResponse({"success": True, "message": "Task updated successfully via dashboard."})
    except ValueError as e_val: return JSONResponse({"error": str(e_val)}, status_code=400)    
    except sqlite3.Error as e_sql:
        if conn: conn.rollback();
        logger.error(f"DB error updating task via dashboard: {e_sql}", exc_info=True)
        return JSONResponse({"error": f"Failed to update task (DB): {str(e_sql)}"}, status_code=500)
    except Exception as e:
        if conn: conn.rollback();
        logger.error(f"Error updating task via dashboard: {e}", exc_info=True)
        return JSONResponse({"error": f"Failed to update task: {str(e)}"}, status_code=500)
    finally:
        if conn: conn.close()


# --- ADDED: Dashboard-specific Agent Management API Endpoints ---

# Original: main.py lines 2022-2058 (create_agent_api function)
async def create_agent_dashboard_api_route(request: Request) -> JSONResponse:
    """Dashboard API endpoint to create an agent. Calls the admin tool internally."""
    if request.method != 'POST':
        return JSONResponse({"error": "Method not allowed"}, status_code=405)
    try:
        data = await get_sanitized_json_body(request)
        admin_auth_token = data.get("token")
        agent_id = data.get("agent_id")
        capabilities = data.get("capabilities", []) # Optional
        working_directory = data.get("working_directory") # Optional

        # This endpoint itself requires admin authentication
        if not verify_token(admin_auth_token, "admin"):
            return JSONResponse({"message": "Unauthorized: Invalid admin token for API call"}, status_code=401)

        if not agent_id:
            return JSONResponse({"message": "Agent ID is required"}, status_code=400)

        # Prepare arguments for the create_agent_tool_impl
        tool_args = {
            "token": admin_auth_token, # The tool_impl will verify this again
            "agent_id": agent_id,
            "capabilities": capabilities,
            "working_directory": working_directory
        }
        
        # Call the already refactored tool implementation
        result_list: List[mcp_types.TextContent] = await create_agent_tool_impl(tool_args)
        
        # Process the result from tool_impl to form a JSONResponse
        # The tool_impl returns a list of TextContent objects.
        # The original API returned a simple JSON message.
        if result_list and result_list[0].text.startswith(f"Agent '{agent_id}' created successfully."):
            # Extract token if possible for dashboard convenience (original API did this)
            # This is a bit fragile as it relies on string parsing of the tool's output.
            agent_token_from_result = None
            for line in result_list[0].text.split('\n'):
                if line.startswith("Token: "):
                    agent_token_from_result = line.split("Token: ", 1)[1]
                    break
            return JSONResponse({
                "message": f"Agent '{agent_id}' created successfully via dashboard API.",
                "agent_token": agent_token_from_result # May be None if not parsed
            })
        else:
            # Return the error message from the tool
            error_message = result_list[0].text if result_list else "Unknown error creating agent."
            # Determine appropriate status code based on error message
            status_code = 400 # Default bad request
            if "Unauthorized" in error_message: status_code = 401
            if "already exists" in error_message: status_code = 409 # Conflict
            return JSONResponse({"message": error_message}, status_code=status_code)

    except ValueError as e_val: # From get_sanitized_json_body
        return JSONResponse({"message": str(e_val)}, status_code=400)
    except Exception as e:
        logger.error(f"Error in create_agent_dashboard_api_route: {e}", exc_info=True)
        return JSONResponse({"message": f"Error creating agent via dashboard API: {str(e)}"}, status_code=500)

# Original: main.py lines 2061-2099 (terminate_agent_api function)
async def terminate_agent_dashboard_api_route(request: Request) -> JSONResponse:
    """Dashboard API endpoint to terminate an agent. Calls the admin tool internally."""
    if request.method != 'POST':
        return JSONResponse({"error": "Method not allowed"}, status_code=405)
    try:
        data = await get_sanitized_json_body(request)
        admin_auth_token = data.get("token")
        agent_id_to_terminate = data.get("agent_id")

        if not verify_token(admin_auth_token, "admin"):
            return JSONResponse({"message": "Unauthorized: Invalid admin token for API call"}, status_code=401)

        if not agent_id_to_terminate:
            return JSONResponse({"message": "Agent ID to terminate is required"}, status_code=400)

        tool_args = {
            "token": admin_auth_token, # Tool impl will verify again
            "agent_id": agent_id_to_terminate
        }

        result_list: List[mcp_types.TextContent] = await terminate_agent_tool_impl(tool_args)

        if result_list and result_list[0].text.startswith(f"Agent '{agent_id_to_terminate}' terminated"):
            return JSONResponse({"message": f"Agent '{agent_id_to_terminate}' terminated successfully via dashboard API."})
        else:
            error_message = result_list[0].text if result_list else "Unknown error terminating agent."
            status_code = 400
            if "Unauthorized" in error_message: status_code = 401
            if "not found" in error_message: status_code = 404
            return JSONResponse({"message": error_message}, status_code=status_code)
            
    except ValueError as e_val: # From get_sanitized_json_body
        return JSONResponse({"message": str(e_val)}, status_code=400)
    except Exception as e:
        logger.error(f"Error in terminate_agent_dashboard_api_route: {e}", exc_info=True)
        return JSONResponse({"message": f"Error terminating agent via dashboard API: {str(e)}"}, status_code=500)


# --- Comprehensive Data Endpoint ---
async def all_data_api_route(request: Request) -> JSONResponse:
    """Get all data in one call for caching on frontend"""
    if request.method == 'OPTIONS':
        return await handle_options(request)
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all agents with their tokens
        cursor.execute("SELECT * FROM agents ORDER BY created_at DESC")
        agents_data = []
        for row in cursor.fetchall():
            agent_dict = dict(row)
            agent_id = agent_dict['agent_id']
            
            # Find token for this agent from active_agents
            agent_token = None
            for token, data in g.active_agents.items():
                if data.get("agent_id") == agent_id and data.get("status") != "terminated":
                    agent_token = token
                    break
            
            agent_dict['auth_token'] = agent_token
            agents_data.append(agent_dict)
        
        # Add admin as special agent
        agents_data.insert(0, {
            'agent_id': 'Admin',
            'status': 'system',
            'auth_token': g.admin_token,
            'created_at': 'N/A',
            'current_task': 'N/A'
        })
        
        # Get all tasks
        cursor.execute("SELECT * FROM tasks ORDER BY created_at DESC")
        tasks_data = [dict(row) for row in cursor.fetchall()]
        
        # Get all context entries
        cursor.execute("SELECT * FROM project_context ORDER BY last_updated DESC")
        context_data = [dict(row) for row in cursor.fetchall()]
        
        # Get recent agent actions (last 100)
        cursor.execute("""
            SELECT * FROM agent_actions 
            ORDER BY timestamp DESC 
            LIMIT 100
        """)
        actions_data = [dict(row) for row in cursor.fetchall()]
        
        # Get file metadata
        cursor.execute("SELECT * FROM file_metadata")
        file_metadata = [dict(row) for row in cursor.fetchall()]
        
        response_data = {
            "agents": agents_data,
            "tasks": tasks_data,
            "context": context_data,
            "actions": actions_data,
            "file_metadata": file_metadata,
            "file_map": g.file_map,
            "admin_token": g.admin_token,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        return JSONResponse(
            response_data,
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            }
        )
        
    except Exception as e:
        logger.error(f"Error fetching all data: {e}", exc_info=True)
        return JSONResponse({"error": f"Failed to fetch all data: {str(e)}"}, status_code=500)
    finally:
        if conn:
            conn.close()

async def context_data_api_route(request: Request) -> JSONResponse:
    """Get only context data"""
    if request.method == 'OPTIONS':
        return await handle_options(request)
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all context entries
        cursor.execute("SELECT * FROM project_context ORDER BY last_updated DESC")
        context_data = [dict(row) for row in cursor.fetchall()]
        
        return JSONResponse(
            context_data,
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            }
        )
        
    except Exception as e:
        logger.error(f"Error fetching context data: {e}", exc_info=True)
        return JSONResponse({"error": f"Failed to fetch context data: {str(e)}"}, status_code=500)
    finally:
        if conn:
            conn.close()

# --- CORS Preflight Handler ---
async def handle_options(request: Request) -> Response:
    """Handle OPTIONS requests for CORS preflight"""
    return PlainTextResponse(
        '',
        headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': '*',
            'Access-Control-Max-Age': '86400',
        }
    )

# --- Route Definitions List ---
routes = [
    Route('/api/all-data', endpoint=all_data_api_route, name="all_data_api", methods=['GET', 'OPTIONS']),
    Route('/api/status', endpoint=simple_status_api_route, name="simple_status_api", methods=['GET', 'OPTIONS']),
    Route('/api/graph-data', endpoint=graph_data_api_route, name="graph_data_api", methods=['GET', 'OPTIONS']),
    Route('/api/task-tree-data', endpoint=task_tree_data_api_route, name="task_tree_data_api", methods=['GET', 'OPTIONS']),
    Route('/api/node-details', endpoint=node_details_api_route, name="node_details_api", methods=['GET', 'OPTIONS']),
    Route('/api/agents', endpoint=agents_list_api_route, name="agents_list_api", methods=['GET', 'OPTIONS']),
    Route('/api/agents-list', endpoint=agents_list_api_route, name="agents_list_api_legacy", methods=['GET', 'OPTIONS']),
    Route('/api/tokens', endpoint=tokens_api_route, name="tokens_api", methods=['GET', 'OPTIONS']),
    Route('/api/tasks', endpoint=all_tasks_api_route, name="all_tasks_api", methods=['GET', 'OPTIONS']),
    Route('/api/tasks-all', endpoint=all_tasks_api_route, name="all_tasks_api_legacy", methods=['GET', 'OPTIONS']),
    Route('/api/update-task-dashboard', endpoint=update_task_details_api_route, name="update_task_dashboard_api", methods=['POST', 'OPTIONS']),
    
    # Added back for 1-to-1 dashboard compatibility
    Route('/api/create-agent', endpoint=create_agent_dashboard_api_route, name="create_agent_dashboard_api", methods=['POST', 'OPTIONS']),
    Route('/api/terminate-agent', endpoint=terminate_agent_dashboard_api_route, name="terminate_agent_dashboard_api", methods=['POST', 'OPTIONS']),
    
    # Catch-all OPTIONS handler for any API route
    Route('/api/{path:path}', endpoint=handle_options, methods=['OPTIONS']),
]

# --- Test/Demo Data Endpoint ---
async def create_sample_memories_route(request: Request) -> JSONResponse:
    """Create sample memory entries for testing"""
    if request.method == 'OPTIONS':
        return await handle_options(request)
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Sample memory entries
        sample_memories = [
            {
                'context_key': 'api.config.base_url',
                'value': json.dumps('https://api.example.com'),
                'description': 'Main API base URL for external services',
                'updated_by': 'system'
            },
            {
                'context_key': 'app.settings.theme',
                'value': json.dumps({'theme': 'dark', 'accent': 'blue'}),
                'description': 'Application theme preferences',
                'updated_by': 'admin'
            },
            {
                'context_key': 'database.connection.timeout',
                'value': json.dumps(30),
                'description': 'Database connection timeout in seconds',
                'updated_by': 'system'
            },
            {
                'context_key': 'cache.redis.config',
                'value': json.dumps({
                    'host': 'localhost',
                    'port': 6379,
                    'ttl': 3600
                }),
                'description': 'Redis cache configuration',
                'updated_by': 'admin'
            }
        ]
        
        current_time = datetime.datetime.now().isoformat()
        created_count = 0
        
        for memory in sample_memories:
            cursor.execute("""
                INSERT OR REPLACE INTO project_context (context_key, value, last_updated, updated_by, description)
                VALUES (?, ?, ?, ?, ?)
            """, (
                memory['context_key'],
                memory['value'],
                current_time,
                memory['updated_by'],
                memory['description']
            ))
            created_count += 1
        
        conn.commit()
        
        return JSONResponse({
            "success": True,
            "message": f"Created {created_count} sample memory entries",
            "created_count": created_count
        })
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error creating sample memories: {e}", exc_info=True)
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)
    finally:
        if conn:
            conn.close()

# Memory CRUD API endpoints
async def create_memory_api_route(request: Request) -> JSONResponse:
    """Create a new memory entry"""
    if request.method == 'OPTIONS':
        return await handle_options(request)
    
    if request.method != 'POST':
        return JSONResponse({"error": "Method not allowed"}, status_code=405)
    
    conn = None
    try:
        data = await get_sanitized_json_body(request)
        admin_token = data.get('token')
        context_key = data.get('context_key')
        context_value = data.get('context_value')
        description = data.get('description')
        
        if not verify_token(admin_token, required_role='admin'):
            return JSONResponse({"error": "Invalid admin token"}, status_code=403)
        
        if not context_key:
            return JSONResponse({"error": "context_key is required"}, status_code=400)
        
        requesting_admin_id = auth_get_agent_id(admin_token)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if key already exists
        cursor.execute("SELECT context_key FROM project_context WHERE context_key = ?", (context_key,))
        if cursor.fetchone():
            return JSONResponse({"error": "Memory with this key already exists"}, status_code=409)
        
        current_time = datetime.datetime.now().isoformat()
        
        cursor.execute("""
            INSERT INTO project_context (context_key, value, last_updated, updated_by, description)
            VALUES (?, ?, ?, ?, ?)
        """, (
            context_key,
            json.dumps(context_value),
            current_time,
            requesting_admin_id,
            description
        ))
        
        # Log the action
        log_agent_action_to_db(cursor, requesting_admin_id, "created_memory", details={"context_key": context_key})
        conn.commit()
        
        return JSONResponse({
            "success": True,
            "message": f"Memory '{context_key}' created successfully"
        })
        
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error creating memory: {e}", exc_info=True)
        return JSONResponse({"error": f"Failed to create memory: {str(e)}"}, status_code=500)
    finally:
        if conn:
            conn.close()

async def update_memory_api_route(request: Request) -> JSONResponse:
    """Update an existing memory entry"""
    if request.method == 'OPTIONS':
        return await handle_options(request)
    
    if request.method != 'PUT':
        return JSONResponse({"error": "Method not allowed"}, status_code=405)
    
    # Extract context_key from URL path
    path_parts = request.url.path.split('/')
    if len(path_parts) < 4 or not path_parts[-1]:
        return JSONResponse({"error": "context_key is required in URL"}, status_code=400)
    
    context_key = path_parts[-1]
    
    conn = None
    try:
        data = await get_sanitized_json_body(request)
        admin_token = data.get('token')
        context_value = data.get('context_value')
        description = data.get('description')
        
        if not verify_token(admin_token, required_role='admin'):
            return JSONResponse({"error": "Invalid admin token"}, status_code=403)
        
        requesting_admin_id = auth_get_agent_id(admin_token)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if memory exists
        cursor.execute("SELECT context_key FROM project_context WHERE context_key = ?", (context_key,))
        if not cursor.fetchone():
            return JSONResponse({"error": "Memory not found"}, status_code=404)
        
        current_time = datetime.datetime.now().isoformat()
        
        # Build update query dynamically
        update_fields = ["last_updated = ?", "updated_by = ?"]
        params = [current_time, requesting_admin_id]
        
        if context_value is not None:
            update_fields.append("value = ?")
            params.append(json.dumps(context_value))
        
        if description is not None:
            update_fields.append("description = ?")
            params.append(description)
        
        params.append(context_key)
        
        query = f"UPDATE project_context SET {', '.join(update_fields)} WHERE context_key = ?"
        cursor.execute(query, params)
        
        # Log the action
        log_agent_action_to_db(cursor, requesting_admin_id, "updated_memory", details={"context_key": context_key})
        conn.commit()
        
        return JSONResponse({
            "success": True,
            "message": f"Memory '{context_key}' updated successfully"
        })
        
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error updating memory: {e}", exc_info=True)
        return JSONResponse({"error": f"Failed to update memory: {str(e)}"}, status_code=500)
    finally:
        if conn:
            conn.close()

async def delete_memory_api_route(request: Request) -> JSONResponse:
    """Delete a memory entry"""
    if request.method == 'OPTIONS':
        return await handle_options(request)
    
    if request.method != 'DELETE':
        return JSONResponse({"error": "Method not allowed"}, status_code=405)
    
    # Extract context_key from URL path
    path_parts = request.url.path.split('/')
    if len(path_parts) < 4 or not path_parts[-1]:
        return JSONResponse({"error": "context_key is required in URL"}, status_code=400)
    
    context_key = path_parts[-1]
    
    conn = None
    try:
        data = await get_sanitized_json_body(request)
        admin_token = data.get('token')
        
        if not verify_token(admin_token, required_role='admin'):
            return JSONResponse({"error": "Invalid admin token"}, status_code=403)
        
        requesting_admin_id = auth_get_agent_id(admin_token)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if memory exists
        cursor.execute("SELECT context_key FROM project_context WHERE context_key = ?", (context_key,))
        if not cursor.fetchone():
            return JSONResponse({"error": "Memory not found"}, status_code=404)
        
        # Delete the memory
        cursor.execute("DELETE FROM project_context WHERE context_key = ?", (context_key,))
        
        # Log the action
        log_agent_action_to_db(cursor, requesting_admin_id, "deleted_memory", details={"context_key": context_key})
        conn.commit()
        
        return JSONResponse({
            "success": True,
            "message": f"Memory '{context_key}' deleted successfully"
        })
        
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error deleting memory: {e}", exc_info=True)
        return JSONResponse({"error": f"Failed to delete memory: {str(e)}"}, status_code=500)
    finally:
        if conn:
            conn.close()

# Add the memory CRUD routes
routes.extend([
    Route('/api/memories', endpoint=create_memory_api_route, name="create_memory_api", methods=['POST', 'OPTIONS']),
    Route('/api/memories/{context_key}', endpoint=update_memory_api_route, name="update_memory_api", methods=['PUT', 'OPTIONS']),
    Route('/api/memories/{context_key}', endpoint=delete_memory_api_route, name="delete_memory_api", methods=['DELETE', 'OPTIONS']),
    Route('/api/context-data', endpoint=context_data_api_route, name="context_data_api", methods=['GET', 'OPTIONS']),
])

# Add the sample data route
routes.append(Route('/api/create-sample-memories', endpoint=create_sample_memories_route, name="create_sample_memories", methods=['POST', 'OPTIONS']))

# --- Celery Task Queue Monitoring Endpoints ---

async def celery_status_api_route(request: Request) -> JSONResponse:
    """Get Celery system status and worker information."""
    if request.method == 'OPTIONS':
        return await handle_options(request)
    
    try:
        # Check if Celery is initialized
        if not g.celery_app_instance:
            return JSONResponse({
                "celery_initialized": False,
                "error": "Celery not initialized"
            }, status_code=503)
        
        # Get worker information
        worker_stats = {}
        try:
            inspect = g.celery_app_instance.control.inspect()
            worker_stats = {
                "active": inspect.active() or {},
                "scheduled": inspect.scheduled() or {},
                "reserved": inspect.reserved() or {},
                "stats": inspect.stats() or {},
                "registered": inspect.registered() or {}
            }
        except Exception as e:
            logger.warning(f"Could not get worker stats: {e}")
        
        # Get queue information from scheduler
        try:
            from ..tasks.scheduler import get_scheduler_status
            scheduler_stats = get_scheduler_status()
        except Exception as e:
            logger.warning(f"Could not get scheduler stats: {e}")
            scheduler_stats = {}
        
        return JSONResponse({
            "celery_initialized": True,
            "worker_stats": worker_stats,
            "scheduler_stats": scheduler_stats,
            "active_tasks": len(g.active_celery_tasks),
            "failed_tasks": len(g.failed_celery_tasks),
            "workers": g.celery_workers,
            "beat_running": g.celery_beat_running,
            "timestamp": datetime.datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting Celery status: {e}", exc_info=True)
        return JSONResponse({"error": f"Failed to get Celery status: {str(e)}"}, status_code=500)


async def celery_tasks_api_route(request: Request) -> JSONResponse:
    """Get information about running and completed Celery tasks."""
    if request.method == 'OPTIONS':
        return await handle_options(request)
    
    try:
        if not g.celery_app_instance:
            return JSONResponse({
                "error": "Celery not initialized"
            }, status_code=503)
        
        # Get task information from database
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Get recent Celery tasks from database (if we're storing them)
            cursor.execute("""
                SELECT task_id, task_name, status, created_at, updated_at, result, error_message
                FROM celery_task_log 
                ORDER BY created_at DESC 
                LIMIT 100
            """)
            db_tasks = [dict(row) for row in cursor.fetchall()]
            
        except sqlite3.OperationalError:
            # Table doesn't exist yet
            db_tasks = []
        except Exception as e:
            logger.warning(f"Could not get tasks from database: {e}")
            db_tasks = []
        finally:
            if conn:
                conn.close()
        
        # Combine with in-memory task tracking
        all_tasks = {
            "active_tasks": dict(g.active_celery_tasks),
            "failed_tasks": dict(g.failed_celery_tasks),
            "db_tasks": db_tasks,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        return JSONResponse(all_tasks)
        
    except Exception as e:
        logger.error(f"Error getting Celery tasks: {e}", exc_info=True)
        return JSONResponse({"error": f"Failed to get Celery tasks: {str(e)}"}, status_code=500)


async def schedule_task_api_route(request: Request) -> JSONResponse:
    """API endpoint to schedule a new Celery task."""
    if request.method == 'OPTIONS':
        return await handle_options(request)
    
    if request.method != 'POST':
        return JSONResponse({"error": "Method not allowed"}, status_code=405)
    
    try:
        data = await get_sanitized_json_body(request)
        admin_token = data.get('token')
        task_name = data.get('task_name')
        task_args = data.get('args', [])
        task_kwargs = data.get('kwargs', {})
        priority = data.get('priority', 'normal')
        queue = data.get('queue', 'default')
        
        if not verify_token(admin_token, required_role='admin'):
            return JSONResponse({"error": "Invalid admin token"}, status_code=403)
        
        if not task_name:
            return JSONResponse({"error": "task_name is required"}, status_code=400)
        
        if not g.celery_app_instance:
            return JSONResponse({"error": "Celery not initialized"}, status_code=503)
        
        # Schedule the task
        try:
            celery_task = g.celery_app_instance.send_task(
                task_name,
                args=task_args,
                kwargs=task_kwargs,
                queue=queue,
                retry=True,
                retry_policy={
                    'max_retries': 3,
                    'interval_start': 60,
                    'interval_step': 60,
                    'interval_max': 600
                }
            )
            
            # Track the task
            g.active_celery_tasks[celery_task.id] = {
                "task_name": task_name,
                "args": task_args,
                "kwargs": task_kwargs,
                "queue": queue,
                "priority": priority,
                "scheduled_at": datetime.datetime.now().isoformat(),
                "status": "pending"
            }
            
            return JSONResponse({
                "success": True,
                "task_id": celery_task.id,
                "task_name": task_name,
                "queue": queue,
                "message": f"Task '{task_name}' scheduled successfully"
            })
            
        except Exception as e:
            logger.error(f"Error scheduling task: {e}")
            return JSONResponse({
                "error": f"Failed to schedule task: {str(e)}"
            }, status_code=500)
        
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error(f"Error in schedule_task_api_route: {e}", exc_info=True)
        return JSONResponse({"error": f"Failed to schedule task: {str(e)}"}, status_code=500)


async def cancel_task_api_route(request: Request) -> JSONResponse:
    """API endpoint to cancel a Celery task."""
    if request.method == 'OPTIONS':
        return await handle_options(request)
    
    if request.method != 'POST':
        return JSONResponse({"error": "Method not allowed"}, status_code=405)
    
    try:
        data = await get_sanitized_json_body(request)
        admin_token = data.get('token')
        task_id = data.get('task_id')
        terminate = data.get('terminate', False)
        
        if not verify_token(admin_token, required_role='admin'):
            return JSONResponse({"error": "Invalid admin token"}, status_code=403)
        
        if not task_id:
            return JSONResponse({"error": "task_id is required"}, status_code=400)
        
        if not g.celery_app_instance:
            return JSONResponse({"error": "Celery not initialized"}, status_code=503)
        
        try:
            # Cancel/revoke the task
            g.celery_app_instance.control.revoke(task_id, terminate=terminate)
            
            # Update task tracking
            if task_id in g.active_celery_tasks:
                g.active_celery_tasks[task_id]["status"] = "revoked"
                g.active_celery_tasks[task_id]["cancelled_at"] = datetime.datetime.now().isoformat()
            
            return JSONResponse({
                "success": True,
                "task_id": task_id,
                "terminated": terminate,
                "message": f"Task {task_id} {'terminated' if terminate else 'cancelled'} successfully"
            })
            
        except Exception as e:
            logger.error(f"Error cancelling task: {e}")
            return JSONResponse({
                "error": f"Failed to cancel task: {str(e)}"
            }, status_code=500)
        
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error(f"Error in cancel_task_api_route: {e}", exc_info=True)
        return JSONResponse({"error": f"Failed to cancel task: {str(e)}"}, status_code=500)


async def scheduled_tasks_api_route(request: Request) -> JSONResponse:
    """Get information about scheduled tasks."""
    if request.method == 'OPTIONS':
        return await handle_options(request)
    
    try:
        from ..tasks.scheduler import list_all_scheduled_tasks
        scheduled_tasks = list_all_scheduled_tasks()
        
        return JSONResponse({
            "scheduled_tasks": scheduled_tasks,
            "total_count": len(scheduled_tasks),
            "timestamp": datetime.datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error getting scheduled tasks: {e}", exc_info=True)
        return JSONResponse({"error": f"Failed to get scheduled tasks: {str(e)}"}, status_code=500)


async def textile_erp_status_api_route(request: Request) -> JSONResponse:
    """Get textile ERP system status including sensor data, production, etc."""
    if request.method == 'OPTIONS':
        return await handle_options(request)
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get system overview
        status_data = {
            "timestamp": datetime.datetime.now().isoformat(),
            "celery_initialized": g.celery_app_instance is not None,
            "system_health": "healthy"
        }
        
        # Check if textile ERP tables exist and get basic stats
        try:
            # Production orders
            cursor.execute("SELECT COUNT(*) as total, COUNT(CASE WHEN status = 'active' THEN 1 END) as active FROM production_orders")
            production_stats = dict(cursor.fetchone())
            status_data["production_orders"] = production_stats
            
            # Machines
            cursor.execute("SELECT COUNT(*) as total, COUNT(CASE WHEN status = 'running' THEN 1 END) as running FROM machines")
            machine_stats = dict(cursor.fetchone())
            status_data["machines"] = machine_stats
            
            # Recent sensor data
            cursor.execute("SELECT COUNT(*) as count FROM sensor_readings WHERE timestamp >= datetime('now', '-1 hour')")
            sensor_count = cursor.fetchone()["count"]
            status_data["recent_sensor_readings"] = sensor_count
            
            # Quality alerts in last 24 hours
            cursor.execute("SELECT COUNT(*) as count FROM quality_alerts WHERE created_at >= datetime('now', '-1 day')")
            alert_count = cursor.fetchone()["count"]
            status_data["recent_quality_alerts"] = alert_count
            
            # Maintenance tasks
            cursor.execute("SELECT COUNT(*) as pending, COUNT(CASE WHEN status = 'in_progress' THEN 1 END) as in_progress FROM maintenance_orders WHERE status IN ('pending', 'in_progress')")
            maintenance_stats = dict(cursor.fetchone())
            status_data["maintenance"] = maintenance_stats
            
        except sqlite3.OperationalError as e:
            # Tables don't exist yet
            status_data["textile_erp_tables"] = "not_created"
            status_data["note"] = "Textile ERP tables not yet initialized"
        
        # Get recent Celery task statistics for textile ERP tasks
        try:
            from ..tasks.scheduler import get_scheduler_status
            scheduler_stats = get_scheduler_status()
            status_data["scheduler"] = scheduler_stats
        except Exception as e:
            logger.warning(f"Could not get scheduler stats: {e}")
        
        return JSONResponse(status_data)
        
    except Exception as e:
        logger.error(f"Error getting textile ERP status: {e}", exc_info=True)
        return JSONResponse({"error": f"Failed to get textile ERP status: {str(e)}"}, status_code=500)
    finally:
        if conn:
            conn.close()


async def worker_management_api_route(request: Request) -> JSONResponse:
    """API endpoint for managing Celery workers."""
    if request.method == 'OPTIONS':
        return await handle_options(request)
    
    if request.method != 'POST':
        return JSONResponse({"error": "Method not allowed"}, status_code=405)
    
    try:
        data = await get_sanitized_json_body(request)
        admin_token = data.get('token')
        action = data.get('action')  # 'start', 'stop', 'restart', 'status'
        worker_type = data.get('worker_type', 'all')
        
        if not verify_token(admin_token, required_role='admin'):
            return JSONResponse({"error": "Invalid admin token"}, status_code=403)
        
        if not action:
            return JSONResponse({"error": "action is required"}, status_code=400)
        
        if not g.celery_app_instance:
            return JSONResponse({"error": "Celery not initialized"}, status_code=503)
        
        # This is a simplified worker management endpoint
        # In production, you'd integrate with your process manager (supervisor, systemd, etc.)
        
        result = {
            "action": action,
            "worker_type": worker_type,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        if action == 'status':
            try:
                inspect = g.celery_app_instance.control.inspect()
                result["workers"] = {
                    "active": inspect.active() or {},
                    "stats": inspect.stats() or {},
                    "ping": inspect.ping() or {}
                }
                result["success"] = True
            except Exception as e:
                result["error"] = f"Failed to get worker status: {str(e)}"
                result["success"] = False
        
        elif action in ['start', 'stop', 'restart']:
            # In a real implementation, this would interact with process management
            result["message"] = f"Worker management action '{action}' for '{worker_type}' would be executed here"
            result["success"] = True
            result["note"] = "Worker management requires external process manager integration"
        
        else:
            return JSONResponse({"error": f"Unknown action: {action}"}, status_code=400)
        
        return JSONResponse(result)
        
    except ValueError as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    except Exception as e:
        logger.error(f"Error in worker_management_api_route: {e}", exc_info=True)
        return JSONResponse({"error": f"Failed to manage workers: {str(e)}"}, status_code=500)


# Add Celery monitoring routes
celery_routes = [
    Route('/api/celery/status', endpoint=celery_status_api_route, name="celery_status_api", methods=['GET', 'OPTIONS']),
    Route('/api/celery/tasks', endpoint=celery_tasks_api_route, name="celery_tasks_api", methods=['GET', 'OPTIONS']),
    Route('/api/celery/schedule-task', endpoint=schedule_task_api_route, name="schedule_task_api", methods=['POST', 'OPTIONS']),
    Route('/api/celery/cancel-task', endpoint=cancel_task_api_route, name="cancel_task_api", methods=['POST', 'OPTIONS']),
    Route('/api/celery/scheduled-tasks', endpoint=scheduled_tasks_api_route, name="scheduled_tasks_api", methods=['GET', 'OPTIONS']),
    Route('/api/celery/workers', endpoint=worker_management_api_route, name="worker_management_api", methods=['POST', 'OPTIONS']),
    Route('/api/textile-erp/status', endpoint=textile_erp_status_api_route, name="textile_erp_status_api", methods=['GET', 'OPTIONS']),
]

# Supply Chain API Route
async def supply_chain_data_api_route(request: Request) -> JSONResponse:
    """API endpoint for supply chain metrics and KPIs"""
    if request.method == 'OPTIONS':
        return await handle_options(request)
    
    try:
        data = await fetch_supply_chain_data_logic()
        return JSONResponse(
            data,
            headers={
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'GET, OPTIONS',
                'Access-Control-Allow-Headers': 'Content-Type'
            }
        )
    except Exception as e:
        logger.error(f"Error serving supply chain data: {e}", exc_info=True)
        return JSONResponse({'error': str(e)}, status_code=500)

routes.extend(celery_routes)

# Add supply chain route
routes.append(
    Route('/api/supply-chain-data', endpoint=supply_chain_data_api_route, name="supply_chain_data_api", methods=['GET', 'OPTIONS'])
)