"""
Simple TUI display function for testing the basic TUI integration.
"""

from .display import TUIDisplay
from .colors import TUITheme

def test_tui_display():
    """Test the TUI display components."""
    display = TUIDisplay()
    
    # Clear screen and draw header
    display.draw_header()
    
    # Draw status bar
    server_status = {
        'running': True,
        'status': 'Running',
        'port': 8080,
        'agent_count': 3,
        'task_count': 5
    }
    display.draw_status_bar(server_status)
    
    # Draw some agents
    agents = [
        {'name': 'Agent 1', 'id': '001', 'active': True, 'task_count': 2},
        {'name': 'Agent 2', 'id': '002', 'active': False, 'task_count': 0},
        {'name': 'Agent 3', 'id': '003', 'active': True, 'task_count': 3},
    ]
    display.draw_agent_list(agents, selected_index=0)
    
    # Draw footer
    display.draw_help_footer()
    
    print(TUITheme.success("\nTUI Display Test Complete!"))