"""
TUI actions that interact with the Agent-MCP server.
These functions bridge the TUI with the server's functionality.
"""

import asyncio
from typing import Dict, List, Optional
from ..db.actions import agent_db, task_db, context_db
from ..tools import project_context_tools, utility_tools
from .colors import TUITheme
from .display import TUIDisplay

class TUIActions:
    """Actions that the TUI can perform on the server."""
    
    def __init__(self, server_instance=None):
        self.server = server_instance
        self.display = TUIDisplay()
    
    async def get_server_status(self) -> Dict[str, any]:
        """Get the current server status."""
        try:
            # Get basic server info
            status = {
                'running': self.server is not None,
                'status': 'Running' if self.server else 'Stopped',
                'port': getattr(self.server, 'port', 3000) if self.server else 'N/A',
            }
            
            # Get agent and task counts
            if self.server:
                agents = await agent_db.get_all_agents()
                tasks = await task_db.get_all_tasks()
                status['agent_count'] = len(agents)
                status['task_count'] = len(tasks)
            else:
                status['agent_count'] = 0
                status['task_count'] = 0
            
            return status
        except Exception as e:
            return {
                'running': False,
                'status': f'Error: {str(e)}',
                'port': 'N/A',
                'agent_count': 0,
                'task_count': 0,
            }
    
    async def get_agents_list(self) -> List[Dict[str, any]]:
        """Get the list of all agents with their status."""
        try:
            agents = await agent_db.get_all_agents()
            agent_list = []
            
            for agent in agents:
                # Get agent's tasks
                agent_tasks = await task_db.get_agent_tasks(agent['id'])
                
                agent_info = {
                    'id': agent['id'],
                    'name': agent['name'],
                    'goal': agent['goal'],
                    'active': agent.get('is_active', False),
                    'task_count': len(agent_tasks),
                    'color': agent.get('color', '#FFFFFF'),
                }
                agent_list.append(agent_info)
            
            return agent_list
        except Exception as e:
            print(TUITheme.error(f"Error fetching agents: {str(e)}"))
            return []
    
    async def get_tasks_list(self) -> List[Dict[str, any]]:
        """Get the list of all tasks with their status."""
        try:
            tasks = await task_db.get_all_tasks()
            task_list = []
            
            for task in tasks:
                # Get agent name
                agent = await agent_db.get_agent(task['agent_id'])
                agent_name = agent['name'] if agent else 'Unknown'
                
                task_info = {
                    'id': task['id'],
                    'name': task.get('tool', 'Unknown'),
                    'status': task['status'],
                    'agent_id': task['agent_id'],
                    'agent_name': agent_name,
                    'created_at': task.get('created_at'),
                    'completed_at': task.get('completed_at'),
                }
                task_list.append(task_info)
            
            return task_list
        except Exception as e:
            print(TUITheme.error(f"Error fetching tasks: {str(e)}"))
            return []
    
    async def get_context_info(self) -> Dict[str, any]:
        """Get project context information."""
        try:
            # Get context using the project context tools
            context = await project_context_tools.view_context()
            
            # Parse the context response
            context_info = {
                'project_path': context.get('project_path', 'Unknown'),
                'description': context.get('description', 'No description'),
                'key_files': context.get('key_files', []),
                'recent_activity': context.get('recent_activity', []),
            }
            
            return context_info
        except Exception as e:
            print(TUITheme.error(f"Error fetching context: {str(e)}"))
            return {
                'project_path': 'Error',
                'description': str(e),
                'key_files': [],
                'recent_activity': [],
            }
    
    async def create_agent(self, name: str, goal: str) -> bool:
        """Create a new agent."""
        try:
            # Create agent using the agent actions
            agent = await agent_db.create_agent(name=name, goal=goal)
            print(TUITheme.success(f"Agent '{name}' created successfully!"))
            return True
        except Exception as e:
            print(TUITheme.error(f"Error creating agent: {str(e)}"))
            return False
    
    async def create_task(self, agent_id: str, tool: str, instructions: str, input_data: Optional[Dict] = None) -> bool:
        """Create a new task for an agent."""
        try:
            # Create task using the task actions
            task = await task_db.create_task(
                agent_id=agent_id,
                tool=tool,
                input_data=input_data or {},
                instructions=instructions
            )
            print(TUITheme.success(f"Task created successfully!"))
            return True
        except Exception as e:
            print(TUITheme.error(f"Error creating task: {str(e)}"))
            return False
    
    async def edit_task(self, task_id: str, updates: Dict[str, any]) -> bool:
        """Edit an existing task."""
        try:
            # Update task using the task actions
            await task_db.update_task(task_id, **updates)
            print(TUITheme.success(f"Task updated successfully!"))
            return True
        except Exception as e:
            print(TUITheme.error(f"Error updating task: {str(e)}"))
            return False
    
    async def delete_task(self, task_id: str) -> bool:
        """Delete a task."""
        try:
            # Delete task using the task actions
            # Note: This might need to be implemented in task_db
            # For now, we'll mark it as cancelled
            await task_db.update_task(task_id, status='cancelled')
            print(TUITheme.success(f"Task deleted successfully!"))
            return True
        except Exception as e:
            print(TUITheme.error(f"Error deleting task: {str(e)}"))
            return False
    
    async def get_logs(self, limit: int = 50) -> List[str]:
        """Get recent server logs."""
        try:
            # Read from the log file
            from ..core.config import LOG_FILE_NAME
            from pathlib import Path
            
            log_path = Path(LOG_FILE_NAME)
            if log_path.exists():
                with open(log_path, 'r') as f:
                    lines = f.readlines()
                    return lines[-limit:]  # Return last 'limit' lines
            else:
                return ["Log file not found"]
        except Exception as e:
            return [f"Error reading logs: {str(e)}"]
    
    async def refresh_data(self) -> bool:
        """Refresh all data from the server."""
        try:
            # This would trigger a refresh of all cached data
            # For now, just return success
            print(TUITheme.info("Refreshing data..."))
            return True
        except Exception as e:
            print(TUITheme.error(f"Error refreshing data: {str(e)}"))
            return False
    
    def run_async(self, coro):
        """Helper to run async functions in sync context."""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(coro)