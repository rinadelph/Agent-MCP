# Agent-MCP/mcp_template/mcp_server_src/app/routes.py
import os
import json
import datetime
from pathlib import Path
from typing import Callable, List, Dict, Any # Added List, Dict, Any

from starlette.routing import Route, Mount
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from starlette.responses import JSONResponse, Response
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
    fetch_task_tree_data_logic
)
from ..features.dashboard.styles import get_node_style

# Import tool implementations that these dashboard APIs will call
from ..tools.admin_tools import (
    create_agent_tool_impl,
    terminate_agent_tool_impl
)
import mcp.types as mcp_types # For handling the result from tool_impl

# --- Template and Static Files Setup ---
TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


# --- Dashboard and API Endpoints ---

# ... (dashboard_home_route, simple_status_api_route, graph_data_api_route, task_tree_data_api_route, node_details_api_route, agents_list_api_route, tokens_api_route, all_tasks_api_route, update_task_details_api_route remain unchanged from the previous version) ...
# Ellipsis for brevity, these functions are the same as in the previous response.
async def dashboard_home_route(request: Request) -> Response:
    # // ... (implementation from previous response)
    return templates.TemplateResponse("index_componentized.html", {"request": request})

async def simple_status_api_route(request: Request) -> JSONResponse:
    # // ... (implementation from previous response)
    try:
        project_name = Path(os.environ.get("MCP_PROJECT_DIR", ".")).name
        active_agents_summary = [
            {"agent_id": data.get("agent_id"), "status": data.get("status")}
            for data in g.active_agents.values()
        ]
        return JSONResponse({
            "project_name": project_name,
            "active_agents_count": len(g.active_agents),
            "active_agents_summary": active_agents_summary,
            "server_status": "running"
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
        query = f"UPDATE tasks SET {', '.join(update_fields)} WHERE task_id = ?"; cursor.execute(query, tuple(params))
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


# --- Route Definitions List ---
routes = [
    Route('/', endpoint=dashboard_home_route, name="dashboard_home"),
    Route('/api/status', endpoint=simple_status_api_route, name="simple_status_api"),
    Route('/api/graph-data', endpoint=graph_data_api_route, name="graph_data_api"),
    Route('/api/task-tree-data', endpoint=task_tree_data_api_route, name="task_tree_data_api"),
    Route('/api/node-details', endpoint=node_details_api_route, name="node_details_api"),
    Route('/api/agents-list', endpoint=agents_list_api_route, name="agents_list_api"),
    Route('/api/tokens', endpoint=tokens_api_route, name="tokens_api"),
    Route('/api/tasks-all', endpoint=all_tasks_api_route, name="all_tasks_api"),
    Route('/api/update-task-dashboard', endpoint=update_task_details_api_route, name="update_task_dashboard_api"),
    
    # Added back for 1-to-1 dashboard compatibility
    Route('/api/create-agent', endpoint=create_agent_dashboard_api_route, name="create_agent_dashboard_api"),
    Route('/api/terminate-agent', endpoint=terminate_agent_dashboard_api_route, name="terminate_agent_dashboard_api"),
]