import sqlite3
import json
import logging
from pathlib import Path
from starlette.responses import JSONResponse

# Assuming get_db_connection is available or passed if needed
# For simplicity, let's assume get_db_connection is importable or handled elsewhere
# You might need to adjust imports based on your actual structure
# from .main import get_db_connection # Example if in same package

logger = logging.getLogger("mcp_dashboard_api")

# Helper to get node color/shape based on type/status and agent color
def get_node_style(node_type, status=None, agent_color=None):
    # Simplified shapes and size variation for physics layout
    base_size = 15
    shape = 'dot' # Default to dot
    color = agent_color # Use agent color if available

    if node_type == 'agent':
        size = base_size + 10
        shape = 'ellipse'
        if status == 'terminated': color = '#F44336' # Keep red for terminated
        elif not color: color = '#4CAF50' # Default green if no color assigned
    elif node_type == 'task':
        size = base_size + 5
        shape = 'square'
        color = '#FFC107' # Pending - Yellow
        if status == 'completed': color = '#9E9E9E' # Grey
        elif status == 'cancelled' or status == 'failed': color = '#FF9800' # Orange
        elif status == 'in_progress': color = '#2196F3' # Blue
    elif node_type == 'context':
        size = base_size
        shape = 'diamond'
        color = '#9C27B0' # Purple
    elif node_type == 'file':
        size = base_size
        shape = 'triangle'
        color = '#795548' # Brown
    elif node_type == 'admin':
        size = base_size + 10
        shape = 'star'
        color = '#607D8B' # Grey
    else: # Default
        size = base_size
        color = '#BDC3C7'
        shape = 'dot'

    return {'color': color, 'shape': shape, 'size': size}

async def get_graph_data(get_db_connection_func, current_file_map):
    """Fetches and formats data for graph visualization (Physics Layout)."""
    nodes = []
    edges = []
    node_ids = set()
    agent_colors = {}

    conn = None
    try:
        conn = get_db_connection_func()
        cursor = conn.cursor()

        # 1. Agents - Get colors first
        cursor.execute("SELECT agent_id, status, color, working_directory, current_task FROM agents WHERE status != 'terminated'")
        agent_rows = cursor.fetchall()
        for row in agent_rows:
            agent_id = row['agent_id']
            node_id = f"agent_{agent_id}"
            agent_colors[agent_id] = row['color'] # Store color
            if node_id not in node_ids:
                style = get_node_style('agent', row['status'], row['color'])
                nodes.append({
                    'id': node_id,
                    'label': agent_id,
                    'group': 'agent',
                    'title': f"Agent: {agent_id}\\nStatus: {row['status']}\\nColor: {row['color']}\\nTask: {row['current_task'] or 'None'}\\nWD: {row['working_directory']}",
                    **style
                })
                node_ids.add(node_id)

        # Add Admin node
        admin_node_id = "admin_node"
        if admin_node_id not in node_ids:
             style = get_node_style('admin')
             nodes.append({'id': admin_node_id, 'label': 'Admin', 'group': 'admin', 'title': 'Admin Actions', **style})
             node_ids.add(admin_node_id)

        # 2. Tasks
        cursor.execute("SELECT task_id, title, status, assigned_to, created_by, parent_task, depends_on_tasks, description FROM tasks")
        task_rows = cursor.fetchall()
        task_node_map = {}
        for row in task_rows:
            task_id = row['task_id']
            node_id = f"task_{task_id}"
            task_node_map[task_id] = node_id # For dependency linking
            if node_id not in node_ids:
                style = get_node_style('task', row['status'])
                short_title = row['title'][:20] # Shorter label for physics layout
                nodes.append({
                    'id': node_id,
                    'label': f"{short_title}", # Simpler label
                    'group': 'task',
                    'title': f"Task: {row['title']}", # Tooltip has full info
                    **style
                })
                node_ids.add(node_id)

            # Edge: Creator -> Task (Very subtle)
            creator = row['created_by']
            creator_node = admin_node_id
            if creator != 'admin' and f"agent_{creator}" in node_ids:
                creator_node = f"agent_{creator}"
            if creator_node in node_ids:
                 edges.append({'from': creator_node, 'to': node_id, 'color': {'color': '#555', 'opacity': 0.3}, 'width': 0.5})

            # Edges for Dependencies (Slightly more visible, dashed)
            try:
                depends_list = json.loads(row['depends_on_tasks'] or '[]')
                for dep_task_id in depends_list:
                    dep_node_id = f"task_{dep_task_id}"
                    if dep_node_id in node_ids: # Only add edge if dependent task node exists
                        edges.append({'from': dep_node_id, 'to': node_id, 'color': {'color': '#aaa', 'opacity': 0.5}, 'dashes': [3, 3]})
            except json.JSONDecodeError:
                logger.warning(f"Could not parse depends_on_tasks for {task_id}")

        # 3. Agent Actions -> Link Agent to Task (Main interaction edges)
        agent_task_links = {}
        cursor.execute("SELECT agent_id, task_id, action_type, timestamp FROM agent_actions WHERE task_id IS NOT NULL ORDER BY timestamp ASC")
        for row in cursor.fetchall():
            agent_node = f"agent_{row['agent_id']}"
            task_node = f"task_{row['task_id']}"
            if agent_node in node_ids and task_node in node_ids:
                link_key = (agent_node, task_node)
                # Store the latest action type for this agent-task pair
                agent_task_links[link_key] = row['action_type']

        for (agent_node, task_node), action_type in agent_task_links.items():
            edge_color = '#ccc' # Default white-ish
            width = 1
            dashes = False
            if action_type == 'assigned': edge_color = '#FFC107' # Yellow
            elif action_type == 'in_progress': edge_color = '#2196F3'; width=1.5 # Blue slightly thicker
            elif action_type == 'completed': edge_color = '#4CAF50' # Green
            elif action_type == 'cancelled' or action_type == 'failed': edge_color = '#FF9800' # Orange

            edges.append({
                'from': agent_node,
                'to': task_node,
                'arrows': 'to',
                'color': {'color': edge_color, 'opacity': 0.8},
                'width': width,
                'dashes': dashes
            })

        # 4. Project Context (Small nodes linked from Admin)
        cursor.execute("SELECT context_key FROM project_context")
        for row in cursor.fetchall():
            key = row['context_key']
            node_id = f"context_{key}"
            if node_id not in node_ids:
                style = get_node_style('context')
                nodes.append({'id': node_id, 'label': key, 'group': 'context', 'title': f"Context: {key}", **style})
                node_ids.add(node_id)
            # Subtle edge from Admin
            edges.append({'from': admin_node_id, 'to': node_id, 'color': {'color': '#666', 'opacity': 0.4}, 'width': 0.5})

        # 5. File Map (Live) - Link agent to file (Subtle links)
        for filepath, info in current_file_map.items():
            agent_id = info['agent_id']
            status = info['status']
            short_path = Path(filepath).name
            file_node_id = f"file_{filepath}"
            agent_node_id = f"agent_{agent_id}"

            if file_node_id not in node_ids:
                style = get_node_style('file')
                nodes.append({'id': file_node_id, 'label': short_path, 'group': 'file', 'title': f"File: {filepath}", **style})
                node_ids.add(file_node_id)

            if agent_node_id in node_ids:
                 edge_color = '#e67e22' if status == 'editing' else '#f1c40f'
                 edges.append({'from': agent_node_id, 'to': file_node_id, 'arrows': 'to', 'label': status, 'font': {'size': 8, 'color':'#eee'}, 'color': {'color': edge_color, 'opacity':0.7}})

        conn.close()

    except Exception as e:
        logger.error(f"Error fetching graph data: {e}", exc_info=True)
        if conn:
            try: conn.close()
            except: pass
        return JSONResponse({'nodes': [], 'edges': []}, status_code=500)

    return JSONResponse({'nodes': nodes, 'edges': edges})

async def get_task_tree_data(get_db_connection_func):
    """Fetches only task data formatted for a hierarchical tree view."""
    nodes = []
    edges = []
    node_ids = set()

    conn = None
    try:
        conn = get_db_connection_func()
        cursor = conn.cursor()

        # 1. Tasks
        cursor.execute("SELECT task_id, title, status, depends_on_tasks, description FROM tasks ORDER BY created_at ASC") # Order by creation for potential layout hints
        task_rows = cursor.fetchall()
        task_node_map = {}
        for row in task_rows:
            task_id = row['task_id']
            node_id = f"task_{task_id}"
            task_node_map[task_id] = node_id
            if node_id not in node_ids:
                style = get_node_style('task', row['status']) # Get task style
                short_title = row['title'][:20]
                nodes.append({
                    'id': node_id,
                    'label': f"{short_title}",
                    'group': 'task',
                    'title': f"Task: {row['title']}\nID: {task_id}\\nStatus: {row['status']}\\nDesc: {row['description'] or 'N/A'}",
                    **style
                })
                node_ids.add(node_id)

            # Edges for Dependencies
            try:
                depends_list = json.loads(row['depends_on_tasks'] or '[]')
                for dep_task_id in depends_list:
                    dep_node_id = f"task_{dep_task_id}"
                    if dep_node_id in node_ids: # Only add edge if dependent task node exists
                        edges.append({
                            'from': dep_node_id, 
                            'to': node_id, 
                            'arrows': 'to', 
                            'color': {'color': '#e74c3c', 'opacity': 0.8}, # Dependency color (red-ish)
                            'width': 1.5 
                        })
            except json.JSONDecodeError:
                logger.warning(f"Could not parse depends_on_tasks for {task_id}")

        conn.close()

    except Exception as e:
        logger.error(f"Error fetching task tree data: {e}", exc_info=True)
        if conn:
            try: conn.close()
            except: pass
        return JSONResponse({'nodes': [], 'edges': []}, status_code=500)

    return JSONResponse({'nodes': nodes, 'edges': edges}) 