# Agent-MCP/mcp_template/mcp_server_src/features/dashboard/api.py
import sqlite3
import json
from pathlib import Path # For Path().name in file map processing
from typing import List, Dict, Any, Callable, Set, Tuple # Added Set, Tuple

# Import from our project structure
from ...core.config import logger # Central logger
from ...db.connection import get_db_connection # To get DB connections
from .styles import get_node_style # Import the styling function from this package

# Note: The original dashboard_api.py had a logger instance:
# logger = logging.getLogger("mcp_dashboard_api")
# We will use the central logger from core.config for consistency.

# Original location: dashboard_api.py lines 46-173 (get_graph_data function)
async def fetch_graph_data_logic(
    # get_db_connection_func: Callable[[], sqlite3.Connection], # Replaced by direct import
    current_file_map_snapshot: Dict[str, Dict[str, Any]]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Fetches and formats data for graph visualization (Physics Layout).
    This is the core logic, separated from the Starlette JSONResponse.

    Args:
        current_file_map_snapshot: A snapshot of the current g.file_map.

    Returns:
        A dictionary with 'nodes' and 'edges' lists.
        Raises Exception on critical error.
    """
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    node_ids: Set[str] = set() # To keep track of added nodes and prevent duplicates
    agent_colors: Dict[str, str] = {} # To store agent colors for consistent edge coloring if needed

    conn = None
    try:
        conn = get_db_connection() # Use the imported function
        cursor = conn.cursor()

        # 1. Agents - Get colors first, only include non-terminated
        # Original dashboard_api.py: lines 53-68
        cursor.execute("SELECT agent_id, status, color, working_directory, current_task FROM agents WHERE status != 'terminated'")
        agent_rows = cursor.fetchall()
        for row in agent_rows:
            agent_id_val = row['agent_id']
            node_id_str = f"agent_{agent_id_val}"
            agent_colors[agent_id_val] = row['color'] # Store color for potential use

            if node_id_str not in node_ids:
                style = get_node_style('agent', row['status'], row['color'])
                nodes.append({
                    'id': node_id_str,
                    'label': agent_id_val, # Keep label simple for physics layout
                    'group': 'agent',
                    'title': (f"Agent: {agent_id_val}\nStatus: {row['status']}\n"
                              f"Color: {row['color'] or 'N/A'}\nTask: {row['current_task'] or 'None'}\n"
                              f"WD: {row['working_directory'] or 'N/A'}"),
                    'mass': 5, # Add mass for physics layout (agents as anchors)
                    **style # Spread the style dictionary (color, shape, size)
                })
                node_ids.add(node_id_str)

        # Add Admin node (Original dashboard_api.py: lines 71-75)
        admin_node_id_str = "admin_node" # Consistent ID
        if admin_node_id_str not in node_ids:
            style = get_node_style('admin')
            nodes.append({
                'id': admin_node_id_str,
                'label': 'Admin',
                'group': 'admin',
                'title': 'Admin User / System Actions',
                'mass': 8, # Higher mass for Admin (more central/stable)
                **style
            })
            node_ids.add(admin_node_id_str)

        # 2. Tasks (Original dashboard_api.py: lines 78-105)
        cursor.execute("SELECT task_id, title, status, assigned_to, created_by, parent_task, depends_on_tasks, description FROM tasks")
        task_rows = cursor.fetchall()
        # task_node_map: Dict[str, str] = {} # Not strictly needed if nodes are added to node_ids immediately
        for row in task_rows:
            task_id_val = row['task_id']
            node_id_str = f"task_{task_id_val}"
            parent_task_id_val = row['parent_task'] # Get parent_task ID

            if node_id_str not in node_ids:
                style = get_node_style('task', row['status'])
                short_title = row['title'][:20] + '...' if len(row['title']) > 20 else row['title']
                nodes.append({
                    'id': node_id_str,
                    'label': short_title, # Simpler label for physics layout
                    'group': 'task',
                    'title': (f"Task: {row['title']}\nID: {task_id_val}\nStatus: {row['status']}\n"
                              f"Assigned: {row['assigned_to'] or 'None'}\nCreated by: {row['created_by']}\n"
                              f"Parent: {parent_task_id_val or 'None'}\n"
                              f"Description: {row['description'][:100] + '...' if row['description'] and len(row['description']) > 100 else (row['description'] or 'N/A')}"),
                    'mass': 2, # Default mass for tasks
                    **style
                })
                node_ids.add(node_id_str)

            # Edge: Creator -> Task (Original dashboard_api.py: lines 93-98)
            creator_id = row['created_by']
            creator_node_id_str = admin_node_id_str # Default to admin
            if creator_id != 'admin':
                potential_agent_creator_node_id = f"agent_{creator_id}"
                if potential_agent_creator_node_id in node_ids: # Check if agent node exists
                    creator_node_id_str = potential_agent_creator_node_id
            
            if creator_node_id_str in node_ids: # Ensure creator node exists
                 edges.append({
                     'from': creator_node_id_str,
                     'to': node_id_str,
                     'title': f'Created by {creator_id}',
                     'color': {'color': '#555555', 'opacity': 0.3}, # Subtle grey
                     'width': 0.5,
                     'arrows': {'to': {'enabled': True, 'scaleFactor': 0.5}} # Small arrow
                 })

            # *** NEW: Add Parent-Child Edges for Tasks ***
            if parent_task_id_val:
                parent_node_id_str = f"task_{parent_task_id_val}"
                if parent_node_id_str in node_ids and node_id_str in node_ids: # Ensure both parent and child nodes exist
                    edges.append({
                        'from': parent_node_id_str,
                        'to': node_id_str,
                        'title': f'Parent of {task_id_val}',
                        'color': {'color': '#6AB04C', 'opacity': 0.9}, # Distinct color (e.g., green)
                        'width': 2, # Slightly thicker for hierarchy
                        'dashes': False, # Solid line
                        'smooth': {'type': 'cubicBezier', 'forceDirection': 'vertical', 'roundness': 0.4}, # Suggests hierarchy
                        'arrows': {'to': {'enabled': True, 'scaleFactor': 0.7, 'type': 'arrow'}},
                        # Physics properties for stronger hierarchical grouping
                        'length': 100, # Shorter preferred length for parent-child
                        # 'strength': 0.5 # (vis.js default is 0.1, higher is stiffer) - adjust as needed
                    })

            # Edges for Dependencies (Original dashboard_api.py: lines 100-105)
            try:
                depends_list_str = row['depends_on_tasks']
                if depends_list_str:
                    depends_task_ids = json.loads(depends_list_str)
                    for dep_task_id in depends_task_ids:
                        dep_node_id_str = f"task_{dep_task_id}"
                        if dep_node_id_str in node_ids and node_id_str in node_ids: # Ensure both nodes exist
                            edges.append({
                                'from': dep_node_id_str,
                                'to': node_id_str,
                                'title': f'{task_id_val} depends on {dep_task_id}',
                                'color': {'color': '#E84393', 'opacity': 0.7}, # Distinct color (e.g., pink/magenta)
                                'width': 1,
                                'dashes': [5, 5], # Dashed line for dependency
                                'smooth': {'type': 'curvedCW', 'roundness': 0.2}, # Different curve
                                'arrows': {'to': {'enabled': True, 'scaleFactor': 0.6, 'type': 'vee'}},
                                'length': 200, # Allow more length for dependencies
                                # 'strength': 0.05
                            })
            except json.JSONDecodeError:
                logger.warning(f"Could not parse depends_on_tasks JSON for task {task_id_val}: '{row['depends_on_tasks']}'")

        # 3. Agent Actions -> Link Agent to Task (Main interaction edges)
        # Original dashboard_api.py: lines 108-132
        agent_task_links: Dict[Tuple[str, str], str] = {} # (agent_node, task_node) -> latest_action_type
        # Fetch actions that link agents to tasks
        cursor.execute("""
            SELECT agent_id, task_id, action_type, timestamp 
            FROM agent_actions 
            WHERE task_id IS NOT NULL AND agent_id != 'admin' 
            ORDER BY timestamp ASC
        """)
        for action_row in cursor.fetchall():
            agent_node_str = f"agent_{action_row['agent_id']}"
            task_node_str = f"task_{action_row['task_id']}"
            if agent_node_str in node_ids and task_node_str in node_ids:
                link_key = (agent_node_str, task_node_str)
                # Store the latest action type for this agent-task pair
                agent_task_links[link_key] = action_row['action_type']

        for (agent_node_str, task_node_str), action_type in agent_task_links.items():
            edge_color_val = '#CCCCCC' # Default light grey
            edge_width_val = 1.0
            edge_dashes_val = False # Solid line by default
            # Customize edge style based on the latest action type
            if action_type == 'assigned_task': edge_color_val = '#FFC107'; edge_width_val = 1.2 # Yellow
            elif action_type == 'started_work' or action_type == 'in_progress': edge_color_val = '#2196F3'; edge_width_val = 1.5 # Blue
            elif action_type == 'completed_task': edge_color_val = '#4CAF50'; edge_width_val = 1.2 # Green
            elif action_type == 'cancelled_task' or action_type == 'failed_task': edge_color_val = '#FF9800' # Orange
            
            edges.append({
                'from': agent_node_str,
                'to': task_node_str,
                'title': f'Last action: {action_type}',
                'arrows': {'to': {'enabled': True, 'scaleFactor': 0.7}},
                'color': {'color': edge_color_val, 'opacity': 0.8},
                'width': edge_width_val,
                'dashes': edge_dashes_val,
                'length': 150 # Default length for agent-task interaction
            })

        # 4. Project Context (Original dashboard_api.py: lines 135-145)
        cursor.execute("SELECT context_key, description FROM project_context")
        for context_row in cursor.fetchall():
            key = context_row['context_key']
            node_id_str = f"context_{key}"
            if node_id_str not in node_ids:
                style = get_node_style('context')
                nodes.append({
                    'id': node_id_str,
                    'label': key[:20] + '...' if len(key) > 20 else key,
                    'group': 'context',
                    'title': f"Context Key: {key}\nDescription: {context_row['description'] or 'N/A'}",
                    'mass': 0.5, # Lower mass for peripheral nodes
                    **style
                })
                node_ids.add(node_id_str)
            # Subtle edge from Admin to context node
            if admin_node_id_str in node_ids:
                edges.append({
                    'from': admin_node_id_str,
                    'to': node_id_str,
                    'title': 'Manages context',
                    'color': {'color': '#666666', 'opacity': 0.4},
                    'width': 0.5,
                    'arrows': {'to': {'enabled': False}} # No arrow for this general link
                })

        # 5. File Map (Live from g.file_map snapshot)
        # Original dashboard_api.py: lines 148-162
        for filepath_str, info_dict in current_file_map_snapshot.items():
            agent_id_val = info_dict.get('agent_id')
            file_status = info_dict.get('status')
            
            # Use Path for robust name extraction
            short_path_str = Path(filepath_str).name 
            file_node_id_str = f"file_{filepath_str}" # Use full path for unique ID
            agent_node_id_str = f"agent_{agent_id_val}"

            if file_node_id_str not in node_ids:
                style = get_node_style('file') # Status not passed to style for file nodes
                nodes.append({
                    'id': file_node_id_str,
                    'label': short_path_str,
                    'group': 'file',
                    'title': f"File: {filepath_str}\nStatus: {file_status or 'N/A'}\nUser: {agent_id_val or 'N/A'}",
                    'mass': 0.5, # Lower mass for peripheral nodes
                    **style
                })
                node_ids.add(file_node_id_str)

            if agent_node_id_str in node_ids: # Ensure agent node exists
                edge_color_file = '#e67e22' if file_status == 'editing' else '#f1c40f' # Orange for editing, yellow for reading/other
                edges.append({
                    'from': agent_node_id_str,
                    'to': file_node_id_str,
                    'arrows': {'to': {'enabled': True, 'scaleFactor': 0.6}},
                    'label': file_status or "", # Edge label shows status
                    'title': f'{agent_id_val} is {file_status or "accessing"} {short_path_str}',
                    'font': {'size': 8, 'color': '#EEEEEE', 'strokeWidth': 0}, # Light font for edge label
                    'color': {'color': edge_color_file, 'opacity': 0.7}
                })
        
        return {'nodes': nodes, 'edges': edges}

    except Exception as e:
        logger.error(f"Error fetching graph data logic: {e}", exc_info=True)
        # Re-raise the exception to be handled by the calling API endpoint,
        # which will then return a JSONResponse with status 500.
        raise
    finally:
        if conn:
            conn.close()


# Original location: dashboard_api.py lines 175-214 (get_task_tree_data function)
async def fetch_task_tree_data_logic() -> Dict[str, List[Dict[str, Any]]]:
    """
    Fetches only task data formatted for a hierarchical tree view.
    This is the core logic, separated from the Starlette JSONResponse.

    Returns:
        A dictionary with 'nodes' and 'edges' lists.
        Raises Exception on critical error.
    """
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    node_ids: Set[str] = set() # To track added nodes

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # 1. Tasks (Original dashboard_api.py: lines 182-200)
        # Order by created_at for potential layout hints or consistent processing
        cursor.execute("SELECT task_id, title, status, parent_task, depends_on_tasks, description, created_at FROM tasks ORDER BY created_at ASC")
        task_rows = cursor.fetchall()
        # task_node_map: Dict[str, str] = {} # Not strictly needed if using node_ids set

        for row in task_rows:
            task_id_val = row['task_id']
            node_id_str = f"task_{task_id_val}"
            parent_task_id_val = row['parent_task'] # Get parent_task ID

            if node_id_str not in node_ids:
                style = get_node_style('task', row['status']) # Get task style
                short_title = row['title'][:20] + '...' if len(row['title']) > 20 else row['title']
                nodes.append({
                    'id': node_id_str,
                    'label': short_title,
                    'group': 'task', # Group for styling
                    'title': (f"Task: {row['title']}\nID: {task_id_val}\nStatus: {row['status']}\n"
                              f"Parent: {parent_task_id_val or 'None'}\n"
                              f"Desc: {row['description'][:100] + '...' if row['description'] and len(row['description']) > 100 else (row['description'] or 'N/A')}"),
                    **style # Spread style attributes
                })
                node_ids.add(node_id_str)

            # *** NEW: Add Parent-Child Edges for Task Tree View ***
            if parent_task_id_val:
                parent_node_id_str = f"task_{parent_task_id_val}"
                if parent_node_id_str in node_ids and node_id_str in node_ids:
                    edges.append({
                        'from': parent_node_id_str,
                        'to': node_id_str,
                        'arrows': {'to': {'enabled': True, 'scaleFactor': 0.9, 'type': 'arrow'}},
                        'color': {'color': '#27AE60', 'opacity': 1.0}, # Strong green for hierarchy
                        'width': 2.5,
                        'dashes': False, # Solid line
                        'smooth': {'enabled': True, 'type': 'cubicBezier', 'forceDirection': 'vertical', 'roundness': 0.4}, # For tree layout
                        'title': f'{task_id_val} is sub-task of {parent_task_id_val}'
                        # No 'length' or 'strength' here as hierarchical layout handles positioning
                    })
            
            # Edges for Dependencies (Original dashboard_api.py: lines 202-214)
            try:
                depends_list_str = row['depends_on_tasks']
                if depends_list_str:
                    depends_task_ids = json.loads(depends_list_str)
                    for dep_task_id in depends_task_ids:
                        dep_node_id_str = f"task_{dep_task_id}"
                        # Only add edge if dependent task node exists (was added to nodes list)
                        if dep_node_id_str in node_ids and node_id_str in node_ids:
                            edges.append({
                                'from': dep_node_id_str, 
                                'to': node_id_str, 
                                'arrows': {'to': {'enabled': True, 'scaleFactor': 0.7, 'type': 'vee'}}, 
                                'color': {'color': '#e74c3c', 'opacity': 0.7}, # Dependency color (red-ish)
                                'width': 1.5,
                                'dashes': [4, 4], # Dashed for dependency
                                'smooth': {'enabled': True, 'type': 'curvedCW', 'roundness': 0.15},
                                'title': f'{task_id_val} depends on {dep_task_id}'
                            })
            except json.JSONDecodeError:
                logger.warning(f"Could not parse depends_on_tasks JSON for task {task_id_val} in task tree: '{row['depends_on_tasks']}'")
        
        return {'nodes': nodes, 'edges': edges}

    except Exception as e:
        logger.error(f"Error fetching task tree data logic: {e}", exc_info=True)
        # Re-raise to be handled by the API endpoint wrapper
        raise
    finally:
        if conn:
            conn.close()

# The Starlette JSONResponse wrappers that were in main.py (graph_data_endpoint, task_tree_data_endpoint)
# will now be defined in `mcp_server_src/app/routes.py`. Those wrappers will call these `_logic` functions.