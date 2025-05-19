"""
Display components for the TUI.
Handles rendering of various UI elements like headers, status bars, and data tables.
"""

import os
import shutil
from datetime import datetime
from typing import List, Dict, Optional, Tuple
try:
    import requests
except ImportError:
    requests = None
from .colors import TUITheme, AGENT_MCP_LOGO, STATUS_SYMBOLS
from ..core.config import VERSION, AUTHOR, GITHUB_URL, GITHUB_REPO

class TUIDisplay:
    """Handles all display-related functionality for the TUI."""
    
    def __init__(self):
        self.terminal_width = shutil.get_terminal_size().columns
        self.terminal_height = shutil.get_terminal_size().lines
        self._update_available = None  # Cache update status
        self._last_update_check = None  # Time of last check
    
    def clear_screen(self):
        """Clear the terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')
    
    def move_cursor(self, row: int, col: int):
        """Move cursor to specific position."""
        print(f"\033[{row};{col}H", end='')
    
    def clear_line(self):
        """Clear current line."""
        print("\033[2K", end='')
    
    def save_cursor(self):
        """Save cursor position."""
        print("\033[s", end='')
    
    def restore_cursor(self):
        """Restore cursor position."""
        print("\033[u", end='')
    
    def hide_cursor(self):
        """Hide cursor to reduce flicker."""
        print("\033[?25l", end='')
    
    def show_cursor(self):
        """Show cursor."""
        print("\033[?25h", end='')
        
    def enable_alternate_screen(self):
        """Enable alternate screen buffer."""
        print("\033[?1049h", end='')
        
    def disable_alternate_screen(self):
        """Disable alternate screen buffer and return to normal screen."""
        print("\033[?1049l", end='')
    
    def refresh_terminal_size(self):
        """Update terminal dimensions."""
        self.terminal_width = shutil.get_terminal_size().columns
        self.terminal_height = shutil.get_terminal_size().lines
    
    def draw_header(self, clear_first: bool = True):
        """Draw the application header with logo, credits, and version info."""
        if clear_first:
            self.clear_screen()
        else:
            self.move_cursor(1, 1)
        
        # Check for updates in the background
        update_available = self._check_for_updates()
        
        current_row = 1
        
        # If update available, show a notification at the top
        if update_available:
            update_msg = " NEW VERSION AVAILABLE - Please update "
            padding = (self.terminal_width - len(update_msg)) // 2
            self.move_cursor(current_row, 1)
            self.clear_line()
            print(' ' * padding + TUITheme.error(update_msg))
            current_row += 2
        
        # Center the logo
        logo_lines = AGENT_MCP_LOGO.strip().split('\n')
        for line in logo_lines:
            self.move_cursor(current_row, 1)
            self.clear_line()
            padding = (self.terminal_width - len(line)) // 2
            print(' ' * padding + TUITheme.header(line))
            current_row += 1
        
        # Add credits and version info
        credits_text = f"Created by {AUTHOR} ({GITHUB_URL})"
        version_text = f"Version {VERSION}"
        
        # Center the credits
        self.move_cursor(current_row, 1)
        self.clear_line()
        credits_padding = (self.terminal_width - len(credits_text)) // 2
        print(' ' * credits_padding + TUITheme.dim(credits_text))
        current_row += 1
        
        # Center the version
        self.move_cursor(current_row, 1)
        self.clear_line()
        version_padding = (self.terminal_width - len(version_text)) // 2
        print(' ' * version_padding + TUITheme.info(version_text))
        current_row += 1
        
        self.move_cursor(current_row, 1)
        self.clear_line()
        print(TUITheme.colorize('─' * self.terminal_width, TUITheme.BORDER))
        
        return current_row + 1
    
    def _check_for_updates(self) -> bool:
        """Check if a newer version is available on GitHub."""
        # If requests isn't available, don't check for updates
        if requests is None:
            return False
            
        # Only check once per session or every 5 minutes
        if self._update_available is not None:
            if self._last_update_check:
                time_since_check = datetime.now() - self._last_update_check
                if time_since_check.total_seconds() < 300:  # 5 minutes
                    return self._update_available
        
        try:
            # Try to get the latest release from GitHub API
            response = requests.get(
                f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest",
                timeout=2  # Quick timeout to not block the UI
            )
            if response.status_code == 200:
                latest_version = response.json().get('tag_name', '').lstrip('v')
                if latest_version and latest_version != VERSION:
                    self._update_available = True
                else:
                    self._update_available = False
            else:
                self._update_available = False
        except:
            # Silently fail if we can't check for updates
            self._update_available = False
        
        self._last_update_check = datetime.now()
        return self._update_available
    
    def draw_status_bar(self, server_status: Dict[str, any]):
        """Draw the status bar showing server information."""
        self.clear_line()
        
        status_color = TUITheme.SUCCESS if server_status.get('running') else TUITheme.ERROR
        status_symbol = STATUS_SYMBOLS['running'] if server_status.get('running') else STATUS_SYMBOLS['stopped']
        
        status_text = f"{status_symbol} Server: {server_status.get('status', 'Unknown')}"
        status_text += f" | Port: {server_status.get('port', 'N/A')}"
        status_text += f" | Agents: {server_status.get('agent_count', 0)}"
        status_text += f" | Tasks: {server_status.get('task_count', 0)}"
        
        # Right-align the time
        current_time = datetime.now().strftime("%H:%M:%S")
        time_text = f"Time: {current_time}"
        
        # Calculate padding
        total_status_length = len(status_text) + len(time_text)
        if total_status_length < self.terminal_width:
            padding = self.terminal_width - total_status_length - 2
            full_status = f" {status_text}{' ' * padding}{time_text} "
        else:
            full_status = f" {status_text} "
        
        print(TUITheme.colorize(full_status, status_color, TUITheme.BG_BLACK))
    
    def draw_agent_list(self, agents: List[Dict[str, any]], selected_index: int = -1):
        """Draw the list of agents with their status."""
        print(TUITheme.header("\n Agents"))
        print(TUITheme.colorize('─' * self.terminal_width, TUITheme.BORDER))
        
        if not agents:
            print(TUITheme.dim("  No agents available"))
        else:
            for i, agent in enumerate(agents):
                is_selected = i == selected_index
                
                # Agent status
                if agent.get('active'):
                    status_symbol = STATUS_SYMBOLS['running']
                    status_color = TUITheme.AGENT_ACTIVE
                else:
                    status_symbol = STATUS_SYMBOLS['stopped']
                    status_color = TUITheme.AGENT_INACTIVE
                
                # Format agent line
                agent_line = f"  {status_symbol} {agent.get('name', 'Unknown')} (ID: {agent.get('id', 'N/A')})"
                agent_line += f" - Tasks: {agent.get('task_count', 0)}"
                
                # Apply selection highlighting
                if is_selected:
                    print(TUITheme.colorize(agent_line, TUITheme.MENU_SELECTED))
                else:
                    print(TUITheme.colorize(agent_line, status_color))
    
    def draw_task_list(self, tasks: List[Dict[str, any]], selected_index: int = -1):
        """Draw the list of tasks with their status."""
        print(TUITheme.header("\n Tasks"))
        print(TUITheme.colorize('─' * self.terminal_width, TUITheme.BORDER))
        
        if not tasks:
            print(TUITheme.dim("  No tasks available"))
        else:
            for i, task in enumerate(tasks):
                is_selected = i == selected_index
                
                # Task status
                status = task.get('status', 'unknown').lower()
                if status == 'running':
                    status_symbol = STATUS_SYMBOLS['running']
                    status_color = TUITheme.TASK_RUNNING
                elif status == 'completed':
                    status_symbol = STATUS_SYMBOLS['success']
                    status_color = TUITheme.SUCCESS
                elif status == 'error' or status == 'failed':
                    status_symbol = STATUS_SYMBOLS['error']
                    status_color = TUITheme.TASK_ERROR
                else:
                    status_symbol = STATUS_SYMBOLS['stopped']
                    status_color = TUITheme.TASK_STOPPED
                
                # Format task line
                task_line = f"  {status_symbol} {task.get('name', 'Unknown')} ({status})"
                task_line += f" - Agent: {task.get('agent_name', 'N/A')}"
                
                # Apply selection highlighting
                if is_selected:
                    print(TUITheme.colorize(task_line, TUITheme.MENU_SELECTED))
                else:
                    print(TUITheme.colorize(task_line, status_color))
    
    def draw_menu(self, menu_items: List[str], selected_index: int):
        """Draw a menu with selectable items."""
        print(TUITheme.header("\n Menu"))
        print(TUITheme.colorize('─' * self.terminal_width, TUITheme.BORDER))
        
        for i, item in enumerate(menu_items):
            is_selected = i == selected_index
            
            if is_selected:
                print(TUITheme.colorize(f"  {STATUS_SYMBOLS['arrow_right']} {item}", TUITheme.MENU_SELECTED))
            else:
                print(f"  {item}")
    
    def draw_help_footer(self):
        """Draw the help footer with keyboard shortcuts."""
        help_text = " ↑/↓: Navigate | Enter: Select | q: Quit | h: Help "
        padding = (self.terminal_width - len(help_text)) // 2
        
        print(TUITheme.colorize('\n' + '─' * self.terminal_width, TUITheme.BORDER))
        print(' ' * padding + TUITheme.dim(help_text))
    
    def draw_text_box(self, title: str, content: str, width: Optional[int] = None):
        """Draw a box with text content."""
        if width is None:
            width = min(80, self.terminal_width - 4)
        
        # Draw top border
        print(TUITheme.colorize('┌' + '─' * (width - 2) + '┐', TUITheme.BORDER))
        
        # Draw title if provided
        if title:
            title_line = f"│ {TUITheme.bold(title):<{width-3}}│"
            print(TUITheme.colorize(title_line, TUITheme.BORDER))
            print(TUITheme.colorize('├' + '─' * (width - 2) + '┤', TUITheme.BORDER))
        
        # Draw content
        lines = content.split('\n')
        for line in lines:
            # Wrap long lines
            while len(line) > width - 4:
                print(TUITheme.colorize(f"│ {line[:width-4]} │", TUITheme.BORDER))
                line = line[width-4:]
            print(TUITheme.colorize(f"│ {line:<{width-3}}│", TUITheme.BORDER))
        
        # Draw bottom border
        print(TUITheme.colorize('└' + '─' * (width - 2) + '┘', TUITheme.BORDER))
    
    def draw_progress_bar(self, progress: float, width: int = 40, label: str = ""):
        """Draw a progress bar."""
        filled = int(width * progress)
        empty = width - filled
        
        bar = f"[{'█' * filled}{'░' * empty}]"
        percentage = f"{progress * 100:.1f}%"
        
        if label:
            print(f"{label}: {bar} {percentage}")
        else:
            print(f"{bar} {percentage}")
    
    def draw_spinner(self, message: str, frame: int = 0):
        """Draw a spinning loader animation."""
        spinner_frames = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        spinner = spinner_frames[frame % len(spinner_frames)]
        
        print(f"\r{TUITheme.colorize(spinner, TUITheme.PRIMARY)} {message}", end='', flush=True)
    
    def draw_confirmation_dialog(self, message: str) -> bool:
        """Draw a confirmation dialog and get user response."""
        self.draw_text_box("Confirmation", message)
        print(TUITheme.warning("\nPress 'y' to confirm, 'n' to cancel: "), end='', flush=True)
        
        # Note: Actual input handling would be done by the caller
        # This is just the display component
        return True
    
    def draw_input_dialog(self, prompt: str, default_value: str = "") -> str:
        """Draw an input dialog for user text entry."""
        self.draw_text_box("Input", prompt)
        
        if default_value:
            print(TUITheme.dim(f"Default: {default_value}"))
        
        print(TUITheme.info("Enter value: "), end='', flush=True)
        
        # Note: Actual input handling would be done by the caller
        # This is just the display component
        return ""