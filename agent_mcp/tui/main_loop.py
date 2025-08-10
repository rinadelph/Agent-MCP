"""
Main TUI loop that coordinates the display, menu, and actions.
"""

import sys
import time
import asyncio
import threading
from typing import Optional

from .display import TUIDisplay
from .menu import TUIMenu, MenuAction
from .actions import TUIActions
from .colors import TUITheme
from ..core.config import logger

class TUIMainLoop:
    """Main TUI application loop."""
    
    def __init__(self, server_instance=None):
        self.display = TUIDisplay()
        self.menu = TUIMenu()
        self.actions = TUIActions(server_instance)
        self.server = server_instance
        self.running = True
        self.current_view = "main"
        self.refresh_interval = 5  # seconds
        self.last_refresh = 0
        
        # Data cache
        self.server_status = {}
        self.agents_list = []
        self.tasks_list = []
        self.context_info = {}
        self.logs = []
    
    async def refresh_data(self):
        """Refresh all data from the server."""
        try:
            self.server_status = await self.actions.get_server_status()
            self.agents_list = await self.actions.get_agents_list()
            self.tasks_list = await self.actions.get_tasks_list()
            self.context_info = await self.actions.get_context_info()
            self.last_refresh = time.time()
        except Exception as e:
            logger.error(f"Error refreshing TUI data: {str(e)}")
    
    def auto_refresh_check(self):
        """Check if it's time to auto-refresh the data."""
        if time.time() - self.last_refresh > self.refresh_interval:
            self.actions.run_async(self.refresh_data())
    
    def run(self):
        """Main TUI loop."""
        try:
            # Initial data load
            self.actions.run_async(self.refresh_data())
            
            while self.running:
                self.auto_refresh_check()
                self.display.refresh_terminal_size()
                
                # Draw the current view
                if self.current_view == "main":
                    self.show_main_view()
                elif self.current_view == "agents":
                    self.show_agents_view()
                elif self.current_view == "tasks":
                    self.show_tasks_view()
                elif self.current_view == "context":
                    self.show_context_view()
                elif self.current_view == "logs":
                    self.show_logs_view()
                elif self.current_view == "help":
                    self.show_help_view()
                
        except KeyboardInterrupt:
            self.shutdown()
        except Exception as e:
            logger.error(f"TUI error: {str(e)}")
            print(TUITheme.error(f"\nError: {str(e)}"))
            self.shutdown()
    
    def show_main_view(self):
        """Show the main menu view."""
        self.display.draw_header()
        self.display.draw_status_bar(self.server_status)
        
        # Show summary information
        print(TUITheme.header("\n Summary"))
        print(TUITheme.colorize('─' * self.display.terminal_width, TUITheme.BORDER))
        print(f"  Active Agents: {len([a for a in self.agents_list if a.get('active')])}/{len(self.agents_list)}")
        print(f"  Running Tasks: {len([t for t in self.tasks_list if t.get('status') == 'running'])}/{len(self.tasks_list)}")
        print(f"  Project: {self.context_info.get('project_path', 'Unknown')}")
        
        # Show main menu
        action = self.menu.show_main_menu()
        
        if action == MenuAction.VIEW_AGENTS:
            self.current_view = "agents"
        elif action == MenuAction.VIEW_TASKS:
            self.current_view = "tasks"
        elif action == MenuAction.VIEW_CONTEXT:
            self.current_view = "context"
        elif action == MenuAction.VIEW_LOGS:
            self.current_view = "logs"
        elif action == MenuAction.CREATE_AGENT:
            self.create_agent_dialog()
        elif action == MenuAction.CREATE_TASK:
            self.create_task_dialog()
        elif action == MenuAction.REFRESH:
            self.actions.run_async(self.refresh_data())
        elif action == MenuAction.HELP:
            self.current_view = "help"
        elif action == MenuAction.QUIT:
            if self.menu.confirm_action("Are you sure you want to quit?"):
                self.shutdown()
        
        self.display.draw_help_footer()
    
    def show_agents_view(self):
        """Show the agents list view."""
        self.display.draw_header()
        self.display.draw_status_bar(self.server_status)
        
        # Display agents with selection
        selected_index = 0
        while True:
            self.display.clear_screen()
            self.display.draw_header()
            self.display.draw_status_bar(self.server_status)
            self.display.draw_agent_list(self.agents_list, selected_index)
            
            print(TUITheme.info("\nPress Enter to view details, 'b' to go back"))
            
            key = self.menu.get_key()
            if key in ['up', 'k']:
                selected_index = (selected_index - 1) % max(1, len(self.agents_list))
            elif key in ['down', 'j']:
                selected_index = (selected_index + 1) % max(1, len(self.agents_list))
            elif key in ['\r', '\n']:  # Enter
                if self.agents_list:
                    self.show_agent_details(self.agents_list[selected_index])
            elif key in ['b', 'q', '\x1b']:  # Back
                self.current_view = "main"
                break
    
    def show_tasks_view(self):
        """Show the tasks list view."""
        selected_index = 0
        
        while True:
            self.display.clear_screen()
            self.display.draw_header()
            self.display.draw_status_bar(self.server_status)
            self.display.draw_task_list(self.tasks_list, selected_index)
            
            print(TUITheme.info("\nPress Enter to view details, 'e' to edit, 'd' to delete, 'b' to go back"))
            
            key = self.menu.get_key()
            if key in ['up', 'k']:
                selected_index = (selected_index - 1) % max(1, len(self.tasks_list))
            elif key in ['down', 'j']:
                selected_index = (selected_index + 1) % max(1, len(self.tasks_list))
            elif key in ['\r', '\n']:  # Enter
                if self.tasks_list:
                    self.show_task_details(self.tasks_list[selected_index])
            elif key == 'e':  # Edit
                if self.tasks_list:
                    self.edit_task_dialog(self.tasks_list[selected_index])
            elif key == 'd':  # Delete
                if self.tasks_list and self.menu.confirm_action("Delete this task?"):
                    task_id = self.tasks_list[selected_index]['id']
                    self.actions.run_async(self.actions.delete_task(task_id))
                    self.actions.run_async(self.refresh_data())
            elif key in ['b', 'q', '\x1b']:  # Back
                self.current_view = "main"
                break
    
    def show_context_view(self):
        """Show the project context view."""
        self.display.clear_screen()
        self.display.draw_header()
        self.display.draw_status_bar(self.server_status)
        
        print(TUITheme.header("\n Project Context"))
        print(TUITheme.colorize('─' * self.display.terminal_width, TUITheme.BORDER))
        
        print(f"\nProject Path: {TUITheme.info(self.context_info.get('project_path', 'Unknown'))}")
        print(f"Description: {self.context_info.get('description', 'No description')}")
        
        if self.context_info.get('key_files'):
            print(TUITheme.header("\nKey Files:"))
            for file in self.context_info.get('key_files', []):
                print(f"  • {file}")
        
        if self.context_info.get('recent_activity'):
            print(TUITheme.header("\nRecent Activity:"))
            for activity in self.context_info.get('recent_activity', [])[:10]:
                print(f"  • {activity}")
        
        print(TUITheme.info("\nPress any key to go back"))
        self.menu.get_key()
        self.current_view = "main"
    
    def show_logs_view(self):
        """Show the server logs view."""
        self.logs = self.actions.run_async(self.actions.get_logs(limit=50))
        
        self.display.clear_screen()
        self.display.draw_header()
        self.display.draw_status_bar(self.server_status)
        
        print(TUITheme.header("\n Server Logs (Last 50 lines)"))
        print(TUITheme.colorize('─' * self.display.terminal_width, TUITheme.BORDER))
        
        for line in self.logs:
            # Color code based on log level
            if "ERROR" in line:
                print(TUITheme.error(line.strip()))
            elif "WARNING" in line:
                print(TUITheme.warning(line.strip()))
            elif "INFO" in line:
                print(TUITheme.info(line.strip()))
            else:
                print(TUITheme.dim(line.strip()))
        
        print(TUITheme.info("\nPress any key to go back"))
        self.menu.get_key()
        self.current_view = "main"
    
    def show_help_view(self):
        """Show the help view."""
        self.display.clear_screen()
        self.display.draw_header()
        self.menu.show_help()
        self.current_view = "main"
    
    def show_agent_details(self, agent: dict):
        """Show detailed information about an agent."""
        self.display.clear_screen()
        self.display.draw_header()
        
        content = f"Name: {agent['name']}\n"
        content += f"ID: {agent['id']}\n"
        content += f"Goal: {agent['goal']}\n"
        content += f"Status: {'Active' if agent['active'] else 'Inactive'}\n"
        content += f"Tasks: {agent['task_count']}\n"
        content += f"Color: {agent['color']}"
        
        self.display.draw_text_box(f"Agent: {agent['name']}", content)
        
        print(TUITheme.info("\nPress any key to go back"))
        self.menu.get_key()
    
    def show_task_details(self, task: dict):
        """Show detailed information about a task."""
        self.display.clear_screen()
        self.display.draw_header()
        
        content = f"ID: {task['id']}\n"
        content += f"Tool: {task['name']}\n"
        content += f"Status: {task['status']}\n"
        content += f"Agent: {task['agent_name']}\n"
        content += f"Created: {task.get('created_at', 'Unknown')}\n"
        content += f"Completed: {task.get('completed_at', 'N/A')}"
        
        self.display.draw_text_box(f"Task: {task['name']}", content)
        
        print(TUITheme.info("\nPress any key to go back"))
        self.menu.get_key()
    
    def create_agent_dialog(self):
        """Show dialog to create a new agent."""
        self.display.clear_screen()
        self.display.draw_header()
        
        print(TUITheme.header("\n Create New Agent"))
        print(TUITheme.colorize('─' * 40, TUITheme.BORDER))
        
        name = self.menu.get_text_input("Agent name")
        if name:
            goal = self.menu.get_text_input("Agent goal")
            if goal:
                self.actions.run_async(self.actions.create_agent(name, goal))
                self.actions.run_async(self.refresh_data())
    
    def create_task_dialog(self):
        """Show dialog to create a new task."""
        if not self.agents_list:
            print(TUITheme.error("No agents available. Create an agent first."))
            time.sleep(2)
            return
        
        self.display.clear_screen()
        self.display.draw_header()
        
        print(TUITheme.header("\n Create New Task"))
        print(TUITheme.colorize('─' * 40, TUITheme.BORDER))
        
        # Select agent
        agent_names = [f"{a['name']} (ID: {a['id']})" for a in self.agents_list]
        selected_agent_index = self.menu.select_from_list(agent_names, "Select Agent")
        
        if selected_agent_index is not None:
            agent_id = self.agents_list[selected_agent_index]['id']
            
            tool = self.menu.get_text_input("Tool name")
            if tool:
                instructions = self.menu.get_text_input("Instructions")
                if instructions:
                    self.actions.run_async(
                        self.actions.create_task(agent_id, tool, instructions)
                    )
                    self.actions.run_async(self.refresh_data())
    
    def edit_task_dialog(self, task: dict):
        """Show dialog to edit a task."""
        self.display.clear_screen()
        self.display.draw_header()
        
        print(TUITheme.header("\n Edit Task"))
        print(TUITheme.colorize('─' * 40, TUITheme.BORDER))
        
        print(f"Current tool: {task['name']}")
        new_tool = self.menu.get_text_input("New tool name (leave empty to keep current)")
        
        print(f"Current status: {task['status']}")
        new_status = self.menu.get_text_input("New status (leave empty to keep current)")
        
        updates = {}
        if new_tool:
            updates['tool'] = new_tool
        if new_status:
            updates['status'] = new_status
        
        if updates:
            self.actions.run_async(self.actions.edit_task(task['id'], updates))
            self.actions.run_async(self.refresh_data())
    
    def shutdown(self):
        """Gracefully shutdown the TUI."""
        self.running = False
        print(TUITheme.info("\nShutting down Agent-MCP TUI..."))
        # Additional cleanup if needed
        sys.exit(0)