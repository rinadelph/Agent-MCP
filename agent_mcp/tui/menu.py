"""
Menu system for the TUI.
Handles keyboard input and menu navigation.
"""

import sys

# Conditionally import termios and tty for non-Windows systems
if sys.platform != 'win32':
    import termios
    import tty

from enum import Enum
from typing import List, Optional, Tuple, Callable
from .colors import TUITheme

class MenuAction(Enum):
    """Available menu actions."""
    VIEW_AGENTS = "View Agents"
    VIEW_TASKS = "View Tasks"
    VIEW_CONTEXT = "View Context"
    VIEW_LOGS = "View Logs"
    CREATE_AGENT = "Create Agent"
    CREATE_TASK = "Create Task"
    EDIT_TASK = "Edit Task"
    DELETE_TASK = "Delete Task"
    REFRESH = "Refresh"
    HELP = "Help"
    QUIT = "Quit"

class TUIMenu:
    """Handles menu navigation and user input."""
    
    def __init__(self):
        self.main_menu_items = [
            MenuAction.VIEW_AGENTS,
            MenuAction.VIEW_TASKS,
            MenuAction.VIEW_CONTEXT,
            MenuAction.VIEW_LOGS,
            MenuAction.CREATE_AGENT,
            MenuAction.CREATE_TASK,
            MenuAction.REFRESH,
            MenuAction.HELP,
            MenuAction.QUIT,
        ]
        self.current_index = 0
        self.is_windows = sys.platform.startswith('win')
    
    def get_key(self) -> str:
        """Get a single keypress from the user."""
        if self.is_windows:
            # Windows implementation using msvcrt
            try:
                import msvcrt
                key = msvcrt.getch()
                if key in [b'\x00', b'\xe0']:  # Special keys (arrows, etc.)
                    key = msvcrt.getch()
                    if key == b'H':  # Up arrow
                        return 'up'
                    elif key == b'P':  # Down arrow
                        return 'down'
                return key.decode('utf-8', errors='ignore').lower()
            except:
                return input()  # Fallback for Windows
        else:
            # Unix/Linux implementation
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            try:
                tty.setraw(sys.stdin.fileno())
                key = sys.stdin.read(1)
                
                # Handle escape sequences for arrow keys
                if key == '\x1b':  # ESC sequence
                    key += sys.stdin.read(2)
                    if key == '\x1b[A':  # Up arrow
                        return 'up'
                    elif key == '\x1b[B':  # Down arrow
                        return 'down'
                    elif key == '\x1b[C':  # Right arrow
                        return 'right'
                    elif key == '\x1b[D':  # Left arrow
                        return 'left'
                
                return key.lower()
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    
    def navigate_menu(self, menu_items: List[str], initial_index: int = 0) -> Optional[int]:
        """
        Navigate a menu and return the selected index.
        Returns None if the user cancels.
        """
        self.current_index = initial_index
        
        while True:
            key = self.get_key()
            
            if key in ['up', 'k']:  # Up arrow or 'k' (vim-style)
                self.current_index = (self.current_index - 1) % len(menu_items)
            elif key in ['down', 'j']:  # Down arrow or 'j' (vim-style)
                self.current_index = (self.current_index + 1) % len(menu_items)
            elif key in ['\r', '\n', ' ']:  # Enter or Space
                return self.current_index
            elif key in ['q', '\x1b']:  # 'q' or ESC
                return None
            elif key == '\x03':  # Ctrl+C
                raise KeyboardInterrupt()
    
    def show_main_menu(self) -> Optional[MenuAction]:
        """Show the main menu and return the selected action."""
        menu_strings = [action.value for action in self.main_menu_items]
        selected_index = self.navigate_menu(menu_strings)
        
        if selected_index is not None:
            return self.main_menu_items[selected_index]
        return None
    
    def show_context_menu(self, items: List[Tuple[str, Callable]], title: str = "Context Menu") -> bool:
        """
        Show a context menu with custom items.
        Each item is a tuple of (display_text, callback_function).
        Returns True if an action was selected, False if cancelled.
        """
        menu_strings = [item[0] for item in items]
        selected_index = self.navigate_menu(menu_strings)
        
        if selected_index is not None:
            # Execute the callback
            items[selected_index][1]()
            return True
        return False
    
    def get_text_input(self, prompt: str, default_value: str = "") -> Optional[str]:
        """Get text input from the user."""
        # Restore normal terminal mode for text input
        if not self.is_windows:
            # termios and tty are imported conditionally at the top
            # and self.is_windows already guards this block
            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        
        print(TUITheme.info(f"{prompt} "), end='')
        if default_value:
            print(TUITheme.dim(f"[{default_value}]: "), end='')
        else:
            print(": ", end='')
        
        try:
            user_input = input()
            if not user_input and default_value:
                return default_value
            return user_input if user_input else None
        except KeyboardInterrupt:
            return None
    
    def confirm_action(self, message: str) -> bool:
        """Show a confirmation dialog."""
        print(TUITheme.warning(f"\n{message} (y/n): "), end='', flush=True)
        
        while True:
            key = self.get_key()
            if key in ['y', 'yes']:
                return True
            elif key in ['n', 'no', '\x1b', 'q']:  # 'n', 'no', ESC, or 'q'
                return False
            elif key == '\x03':  # Ctrl+C
                raise KeyboardInterrupt()
    
    def select_from_list(self, items: List[str], title: str = "Select Item") -> Optional[int]:
        """
        Show a list selection menu.
        Returns the index of the selected item, or None if cancelled.
        """
        print(TUITheme.header(f"\n{title}"))
        print(TUITheme.colorize('─' * 40, TUITheme.BORDER))
        
        for i, item in enumerate(items):
            print(f"  {i + 1}. {item}")
        
        print(TUITheme.colorize('─' * 40, TUITheme.BORDER))
        
        return self.navigate_menu(items)
    
    def show_help(self):
        """Display help information."""
        help_text = """
        Agent-MCP TUI Help
        
        Navigation:
          ↑/k     - Move up
          ↓/j     - Move down
          Enter   - Select item
          Space   - Select item
          q/ESC   - Go back/Cancel
          Ctrl+C  - Exit application
        
        Main Menu Actions:
          View Agents   - List all agents and their status
          View Tasks    - List all tasks and their status
          View Context  - Show project context information
          View Logs     - Display server logs
          Create Agent  - Create a new agent
          Create Task   - Create a new task
          Refresh       - Refresh the display
          Help          - Show this help screen
          Quit          - Exit the application
        
        Press any key to continue...
        """
        
        print(TUITheme.info(help_text))
        self.get_key()  # Wait for any key