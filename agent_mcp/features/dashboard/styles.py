# Agent-MCP/mcp_template/mcp_server_src/features/dashboard/styles.py
from typing import Dict, Any, Optional

# No other project-specific imports are needed for this function.
# It's a pure utility based on its input arguments.

# Original location: dashboard_api.py lines 11-44 (get_node_style function)
def get_node_style(node_type: str, status: Optional[str] = None, agent_color: Optional[str] = None) -> Dict[str, Any]:
    """
    Helper to get node color, shape, and size for graph visualization based on node type,
    status, and assigned agent color. Designed for physics layout.

    Args:
        node_type: The type of the node (e.g., 'agent', 'task', 'context').
        status: The status of the node (e.g., 'completed', 'in_progress', 'terminated').
        agent_color: The pre-assigned color for an agent node.

    Returns:
        A dictionary containing 'color', 'shape', and 'size' for the node.
    """
    base_size: int = 15
    shape: str = 'dot'  # Default to dot
    color: Optional[str] = agent_color  # Use agent color if available and applicable

    node_style_properties: Dict[str, Any] = {}

    if node_type == 'agent':
        node_style_properties['size'] = base_size + 10
        node_style_properties['shape'] = 'ellipse' # Original: 'ellipse'
        if status == 'terminated':
            node_style_properties['color'] = '#F44336' # Red for terminated
        elif color: # If agent_color was provided and not terminated
            node_style_properties['color'] = color
        else: # Default color for active agent if no specific color assigned
            node_style_properties['color'] = '#4CAF50' # Default green
    elif node_type == 'task':
        node_style_properties['size'] = base_size + 5
        node_style_properties['shape'] = 'square' # Original: 'square'
        # Task color based on status
        if status == 'completed':
            node_style_properties['color'] = '#9E9E9E' # Grey
        elif status == 'cancelled' or status == 'failed': # Combined 'cancelled' and 'failed'
            node_style_properties['color'] = '#FF9800' # Orange
        elif status == 'in_progress':
            node_style_properties['color'] = '#2196F3' # Blue
        else: # Default for 'pending' or other statuses
            node_style_properties['color'] = '#FFC107' # Pending - Yellow
    elif node_type == 'context':
        node_style_properties['size'] = base_size
        node_style_properties['shape'] = 'diamond' # Original: 'diamond'
        node_style_properties['color'] = '#9C27B0' # Purple
    elif node_type == 'file':
        node_style_properties['size'] = base_size
        node_style_properties['shape'] = 'triangle' # Original: 'triangle'
        node_style_properties['color'] = '#795548' # Brown
    elif node_type == 'admin':
        node_style_properties['size'] = base_size + 10
        node_style_properties['shape'] = 'star' # Original: 'star'
        node_style_properties['color'] = '#607D8B' # Grey (original was also Grey)
    else:  # Default style for unknown node types
        node_style_properties['size'] = base_size
        node_style_properties['shape'] = 'dot'
        node_style_properties['color'] = '#BDC3C7' # Default light grey

    # Ensure all required keys are present even if not set by specific conditions
    if 'color' not in node_style_properties and color: # Fallback to agent_color if no specific color set
        node_style_properties['color'] = color
    elif 'color' not in node_style_properties: # Ultimate fallback color
        node_style_properties['color'] = '#BDC3C7'


    return {
        'color': node_style_properties.get('color'),
        'shape': node_style_properties.get('shape'),
        'size': node_style_properties.get('size')
    }