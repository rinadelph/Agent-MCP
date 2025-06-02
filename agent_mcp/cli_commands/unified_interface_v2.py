"""
Enhanced Unified Agent MCP Interface - Version 2
With improved navigation, server management, and integrated viewers
"""

import os
import sys
import json
import asyncio
import subprocess
import signal
import time
import psutil
import threading
import curses
from curses import wrapper
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import pyperclip
import click
import logging
import traceback

from ..core.config import logger, get_project_dir
from ..db.connection import get_db_connection
from ..db.actions.agent_db import get_all_active_agents_from_db
from ..db.actions.task_db import get_all_tasks_from_db
from ..utils.project_utils import init_agent_directory
from ..db.migrations.migration_manager import MigrationManager
from .server_manager import ServerProcess

# Set up enhanced logging for the unified interface
ui_logger = logging.getLogger('agent_mcp.cli.unified_interface')
ui_logger.setLevel(logging.DEBUG)

# Add file handler for UI-specific logs
ui_log_file = 'agent_mcp_ui.log'
ui_file_handler = logging.FileHandler(ui_log_file, mode='a')
ui_file_handler.setLevel(logging.DEBUG)
ui_formatter = logging.Formatter(
    '%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s - %(funcName)s:%(lineno)d - %(message)s',
    datefmt='%H:%M:%S'
)
ui_file_handler.setFormatter(ui_formatter)
ui_logger.addHandler(ui_file_handler)

ui_logger.info("=" * 80)
ui_logger.info("UNIFIED INTERFACE V2 MODULE LOADED")
ui_logger.info("=" * 80)


class ServerControlPanel:
    """Enhanced server control panel with integrated viewers"""
    
    def __init__(self, server: ServerProcess, port: int):
        ui_logger.info(f"Initializing ServerControlPanel for server on port {port}")
        ui_logger.debug(f"Server details: project_dir={server.project_dir}")
        self.server = server
        self.port = port
        self.current_tab = "overview"  # overview, logs, agents, tasks, context
        self.agents = []
        self.tasks = []
        self.context = []
        self.selected_item = 0
        self.scroll_offset = 0
        self.data_loaded = False
        self.loading = False
        ui_logger.info(f"ServerControlPanel initialized successfully")
        
    def load_data(self):
        """Load data from server's database - only if not already loaded"""
        ui_logger.debug(f"load_data called - data_loaded={self.data_loaded}, loading={self.loading}, current_tab={self.current_tab}")
        if self.data_loaded or self.loading:
            ui_logger.debug("Data already loaded or loading in progress, skipping")
            return
            
        self.loading = True
        ui_logger.info(f"Loading data for tab: {self.current_tab}")
        try:
            # Set project directory for this server
            old_dir = os.environ.get("MCP_PROJECT_DIR")
            ui_logger.debug(f"Temporarily setting MCP_PROJECT_DIR to: {self.server.project_dir}")
            os.environ["MCP_PROJECT_DIR"] = self.server.project_dir
            
            # Only load data when needed
            if self.current_tab in ["agents", "overview"]:
                ui_logger.debug("Loading agents data...")
                self.agents = get_all_active_agents_from_db()
                ui_logger.info(f"Loaded {len(self.agents)} agents")
            
            if self.current_tab in ["tasks", "overview"]:
                ui_logger.debug("Loading tasks data...")
                self.tasks = get_all_tasks_from_db()
                ui_logger.info(f"Loaded {len(self.tasks)} tasks")
            
            if self.current_tab in ["context", "overview"]:
                ui_logger.debug("Loading context data...")
                self.context = self.get_context_entries()
                ui_logger.info(f"Loaded {len(self.context)} context entries")
            
            # Restore old directory
            if old_dir:
                os.environ["MCP_PROJECT_DIR"] = old_dir
                ui_logger.debug(f"Restored MCP_PROJECT_DIR to: {old_dir}")
                
            self.data_loaded = True
            ui_logger.info("Data loading completed successfully")
                
        except Exception as e:
            logger.error(f"Error loading server data: {e}")
            ui_logger.error(f"Error loading server data: {e}")
            ui_logger.debug(f"Traceback: {traceback.format_exc()}")
        finally:
            self.loading = False
            
    def get_context_entries(self):
        """Get context entries from database"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT context_key, value, description, last_updated, updated_by
                FROM project_context
                ORDER BY last_updated DESC
            """)
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    'context_key': row['context_key'],
                    'context_value': row['value'],
                    'description': row.get('description', ''),
                    'updated_at': row['last_updated'],
                    'updated_by': row['updated_by']
                })
            
            conn.close()
            return results
        except Exception as e:
            logger.error(f"Error fetching context: {e}")
            return []


class EnhancedUnifiedInterface:
    """Enhanced unified interface with better navigation and features"""
    
    def __init__(self, stdscr):
        ui_logger.info("=" * 80)
        ui_logger.info("Initializing EnhancedUnifiedInterface")
        ui_logger.info("=" * 80)
        
        self.stdscr = stdscr
        self.screen_stack = ["main_menu"]  # Navigation stack
        self.selected_index = 0
        self.scroll_offset = 0
        
        ui_logger.debug("Setting up screen properties")
        ui_logger.debug(f"Terminal size: {curses.LINES}x{curses.COLS}")
        
        # Server management
        self.servers: Dict[int, ServerProcess] = {}
        self.current_server_panel: Optional[ServerControlPanel] = None
        ui_logger.debug("Server management initialized")
        
        # Launch configuration
        self.launch_mode = "quick"  # quick, advanced
        self.launch_config = {
            "project_dir": None,
            "port": 8080,
            "auto_increment_port": True,
            "init_if_needed": True,
            "name": None
        }
        ui_logger.debug(f"Launch config: {self.launch_config}")
        
        # File browser
        self.browser_path = Path.cwd()
        self.browser_items = []
        ui_logger.debug(f"Browser path set to: {self.browser_path}")
        
        # Messages
        self.message = ""
        self.message_type = "info"
        
        # Quick actions
        self.quick_actions_open = False
        
        # Key handling
        self.last_key_time = 0
        self.key_repeat_delay = 0.05  # 50ms debounce
        
        # Initialize
        ui_logger.info("Initializing colors and curses settings")
        self.init_colors()
        curses.curs_set(0)
        self.stdscr.nodelay(1)  # Non-blocking input
        self.stdscr.timeout(50)  # 50ms timeout for getch
        self.running = True
        
        ui_logger.info("Starting background tasks")
        self.start_background_tasks()
        
        ui_logger.info("EnhancedUnifiedInterface initialization complete")
        
    def safe_addstr(self, y: int, x: int, text: str, attr=0):
        """Safely add string to screen with boundary checking"""
        height, width = self.stdscr.getmaxyx()
        
        # Check if position is within bounds
        if y < 0 or y >= height or x < 0 or x >= width:
            return
            
        # Truncate text if it would go past the right edge
        max_len = width - x
        if max_len <= 0:
            return
            
        if len(text) > max_len:
            text = text[:max_len-1]  # Leave room for cursor
            
        try:
            if attr:
                self.stdscr.attron(attr)
                self.stdscr.addstr(y, x, text)
                self.stdscr.attroff(attr)
            else:
                self.stdscr.addstr(y, x, text)
        except curses.error:
            # Ignore errors when writing at screen edges
            pass
            
    def init_colors(self):
        """Initialize color pairs"""
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)   # Success
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Selected
        curses.init_pair(3, curses.COLOR_CYAN, curses.COLOR_BLACK)    # Info
        curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)     # Error
        curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK) # Keys
        curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_BLACK)   # Normal
        curses.init_pair(7, curses.COLOR_BLUE, curses.COLOR_BLACK)    # Directory
        
    def start_background_tasks(self):
        """Start background monitoring"""
        def monitor_servers():
            while self.running:
                for port, server in list(self.servers.items()):
                    if server.is_running() and server.process.stdout:
                        try:
                            line = server.process.stdout.readline()
                            if line:
                                decoded = line.decode('utf-8').strip()
                                server.add_log(decoded)
                                if "MCP Admin Token" in decoded and ":" in decoded:
                                    token = decoded.split(":")[-1].strip()
                                    server.admin_token = token
                        except:
                            pass
                time.sleep(0.1)
                
        thread = threading.Thread(target=monitor_servers, daemon=True)
        thread.start()
        
    @property
    def current_screen(self):
        """Get current screen from stack"""
        return self.screen_stack[-1] if self.screen_stack else "main_menu"
        
    def push_screen(self, screen: str):
        """Navigate to a new screen"""
        logger.info(f"Pushing screen: {screen}, current stack: {self.screen_stack}")
        self.screen_stack.append(screen)
        self.selected_index = 0
        self.scroll_offset = 0
        logger.info(f"New stack: {self.screen_stack}, current: {self.current_screen}")
        
    def pop_screen(self):
        """Go back to previous screen"""
        logger.info(f"Popping screen, current stack: {self.screen_stack}")
        if len(self.screen_stack) > 1:
            popped = self.screen_stack.pop()
            self.selected_index = 0
            self.scroll_offset = 0
            logger.info(f"Popped {popped}, new current: {self.current_screen}")
            return True
        logger.info("Cannot pop - at root screen")
        return False
        
    def run(self):
        """Main event loop"""
        ui_logger.info("Starting main event loop")
        try:
            # Force initial draw
            self._needs_redraw = True
            ui_logger.debug("Initial draw requested")
            
            while self.running:
                # Only redraw if needed
                if getattr(self, '_needs_redraw', True):
                    ui_logger.debug(f"Redrawing screen: {self.current_screen}")
                    self.draw_screen()
                    self._needs_redraw = False
                    
                key = self.stdscr.getch()
                
                # Skip if no key pressed (timeout)
                if key == -1:
                    # Check if we need to update (e.g., for logs)
                    if self.current_screen == "server_control" and self.current_server_panel:
                        if self.current_server_panel.current_tab == "logs":
                            self._needs_redraw = True
                    continue
                    
                # Log key press
                if key != -1:
                    ui_logger.debug(f"Key pressed: {key} (char: {chr(key) if 32 <= key <= 126 else 'special'})")
                    
                # Simple debounce for navigation keys
                current_time = time.time()
                if key in [curses.KEY_UP, curses.KEY_DOWN, ord('j'), ord('k')]:
                    if current_time - self.last_key_time < self.key_repeat_delay:
                        ui_logger.debug("Key debounced")
                        continue
                    self.last_key_time = current_time
                
                # Mark for redraw after input
                self._needs_redraw = True
                
                if not self.handle_input(key):
                    break
        finally:
            self.cleanup()
            
    def draw_screen(self):
        """Draw the current screen"""
        try:
            self.stdscr.clear()
            height, width = self.stdscr.getmaxyx()
            
            # Log current screen for debugging
            logger.debug(f"Drawing screen: {self.current_screen}, stack: {self.screen_stack}, size: {width}x{height}")
            
            # Check minimum terminal size
            if height < 10 or width < 30:
                self.safe_addstr(1, 1, "Terminal too small!", curses.color_pair(4) | curses.A_BOLD)
                self.safe_addstr(2, 1, f"Size: {width}x{height}")
                self.safe_addstr(3, 1, "Need: 30x10 minimum")
                self.safe_addstr(5, 1, "Resize terminal or")
                self.safe_addstr(6, 1, "press 'q' to quit")
                self.stdscr.refresh()
                return
            
            # Draw header with breadcrumb
            self.draw_header(width)
            
            # Draw quick actions if open
            if self.quick_actions_open:
                self.draw_quick_actions(height, width)
                self.stdscr.refresh()
                return
                
            # Draw main content
            content_start = 3
            content_height = height - 5
            
            try:
                if self.current_screen == "main_menu":
                    self.draw_main_menu(content_start, content_height, width)
                elif self.current_screen == "server_hub":
                    self.draw_server_hub(content_start, content_height, width)
                elif self.current_screen == "server_control":
                    self.draw_server_control(content_start, content_height, width)
                elif self.current_screen == "launch_wizard":
                    self.draw_launch_wizard(content_start, content_height, width)
                elif self.current_screen == "project_browser":
                    self.draw_project_browser(content_start, content_height, width)
                elif self.current_screen == "port_selector":
                    self.draw_port_selector(content_start, content_height, width)
                elif self.current_screen == "database_tools":
                    self.draw_database_tools(content_start, content_height, width)
                elif self.current_screen == "settings":
                    self.draw_settings(content_start, content_height, width)
                elif self.current_screen == "help":
                    self.draw_help(content_start, content_height, width)
                else:
                    # Unknown screen - show error
                    self.safe_addstr(content_start + 2, 4, f"Unknown screen: {self.current_screen}", curses.color_pair(4))
                    logger.error(f"Unknown screen: {self.current_screen}")
            except curses.error as e:
                # Curses drawing error - likely terminal size issue
                logger.warning(f"Curses error drawing {self.current_screen}: {e}")
                self.safe_addstr(content_start + 2, 4, "Display error - resize terminal", curses.color_pair(4))
            except Exception as e:
                logger.error(f"Error drawing screen {self.current_screen}: {e}", exc_info=True)
                self.safe_addstr(content_start + 2, 4, f"Error: {str(e)}", curses.color_pair(4))
                
            # Draw footer
            if height > 6:  # Only draw footer if there's room
                self.draw_footer(height - 1, width)
            
            # Draw message
            if self.message and height > 7:
                self.draw_message(height - 2, width)
                
            self.stdscr.refresh()
        except curses.error:
            # Ignore any final refresh errors
            pass
        
    def draw_project_browser(self, y: int, height: int, width: int):
        """Draw project browser"""
        # Title with shortcuts
        self.stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
        self.stdscr.addstr(y, 2, "📁 Project Browser")
        self.stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)
        
        # Quick shortcuts on the right
        shortcuts = "[H]ome [U]p [G]o to"
        self.stdscr.attron(curses.color_pair(5))
        self.stdscr.addstr(y, width - len(shortcuts) - 2, shortcuts)
        self.stdscr.attroff(curses.color_pair(5))
        y += 1
        
        # Current path with better truncation
        path_str = str(self.browser_path)
        home_str = str(Path.home())
        if path_str.startswith(home_str):
            path_str = "~" + path_str[len(home_str):]
            
        if len(path_str) > width - 15:
            # Smart truncation
            parts = path_str.split('/')
            if len(parts) > 4:
                path_str = f"{'/'.join(parts[:2])}/.../{'/'.join(parts[-2:])}"
                
        self.stdscr.addstr(y, 2, f"📍 {path_str}", curses.color_pair(6))
        y += 2
        
        # Load items if needed
        if not self.browser_items:
            self.load_browser_items()
            
        # Show item count
        total_items = len(self.browser_items)
        if self.browser_path.parent != self.browser_path:
            total_items -= 1  # Don't count parent
            
        self.stdscr.addstr(y - 1, width - 20, f"[{total_items} items]", curses.A_DIM)
        
        # Directory listing with better visibility
        visible = min(height - y - 3, len(self.browser_items))
        
        # Adjust scroll offset if needed
        if self.selected_index >= self.scroll_offset + visible:
            self.scroll_offset = self.selected_index - visible + 1
        elif self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        
        for i in range(visible):
            idx = self.scroll_offset + i
            if idx >= len(self.browser_items):
                break
                
            item = self.browser_items[idx]
            is_selected = idx == self.selected_index
            
            self.draw_browser_item(y + i, width, item, is_selected)
            
        # Show scrollbar if needed
        if len(self.browser_items) > visible:
            self.draw_scrollbar(y, visible, len(self.browser_items), self.scroll_offset, width - 1)
            
    def draw_browser_item(self, y: int, width: int, item: Path, selected: bool):
        """Draw a browser item"""
        is_dir = item.is_dir()
        has_agent = (item / ".agent").exists() if is_dir else False
        
        # Selection indicator
        if selected:
            self.stdscr.attron(curses.color_pair(2))
            self.stdscr.addstr(y, 2, "▶")
            self.stdscr.attroff(curses.color_pair(2))
            
        x = 5
        
        # Special case for parent directory
        if item == self.browser_path.parent and item != self.browser_path:
            self.stdscr.addstr(y, x, "⬆️  ..", curses.color_pair(6) | curses.A_DIM)
        elif is_dir:
            if has_agent:
                # MCP Project
                self.stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
                self.stdscr.addstr(y, x, "🚀 ")
                self.stdscr.addstr(y, x + 3, item.name)
                self.stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
                
                # Badge
                self.stdscr.attron(curses.color_pair(1))
                self.stdscr.addstr(y, x + 3 + len(item.name) + 2, "[MCP Project]")
                self.stdscr.attroff(curses.color_pair(1))
            else:
                # Regular directory
                self.stdscr.attron(curses.color_pair(7))
                self.stdscr.addstr(y, x, "📁 ")
                self.stdscr.addstr(y, x + 3, item.name)
                self.stdscr.attroff(curses.color_pair(7))
                
    def load_browser_items(self):
        """Load items for file browser"""
        try:
            items = []
            
            # Add parent directory
            if self.browser_path.parent != self.browser_path:
                items.append(self.browser_path.parent)
                
            # Add directories
            for item in sorted(self.browser_path.iterdir()):
                if item.is_dir() and not item.name.startswith('.'):
                    items.append(item)
                    
            self.browser_items = items
        except PermissionError:
            self.browser_items = []
            self.show_message("Permission denied", "error")
            
    def draw_port_selector(self, y: int, height: int, width: int):
        """Draw port selector"""
        # Title
        self.stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
        self.stdscr.addstr(y, 2, "🔌 Port Selection")
        self.stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)
        y += 2
        
        # Current port with inline editing
        current_port = self.launch_config.get("port", 8080)
        self.stdscr.addstr(y, 4, "Current Port: ")
        
        # Highlight current port for editing
        self.stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
        self.stdscr.addstr(y, 18, str(current_port))
        self.stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
        
        # Port adjustment hints
        self.stdscr.addstr(y, 25, "[+/-] to adjust, [0-9] to type", curses.color_pair(5))
        y += 2
        
        # Check if port is available
        if current_port in self.servers:
            self.stdscr.attron(curses.color_pair(4))
            self.stdscr.addstr(y, 4, "⚠️  Port is already in use by another server!")
            self.stdscr.attroff(curses.color_pair(4))
        else:
            self.stdscr.attron(curses.color_pair(1))
            self.stdscr.addstr(y, 4, "✓ Port is available")
            self.stdscr.attroff(curses.color_pair(1))
        y += 2
        
        # Quick port options - show more ports
        self.stdscr.attron(curses.A_BOLD)
        self.stdscr.addstr(y, 4, "Quick Select (press number):")
        self.stdscr.attroff(curses.A_BOLD)
        y += 1
        
        # Show 9 ports in a 3x3 grid
        common_ports = [8080, 8081, 8082, 3000, 3001, 3002, 5000, 5001, 9000]
        for i in range(0, len(common_ports), 3):
            row_y = y + (i // 3)
            for j in range(3):
                if i + j < len(common_ports):
                    port = common_ports[i + j]
                    x = 4 + j * 20
                    num = i + j + 1
                    
                    # Color based on availability
                    if port in self.servers:
                        self.stdscr.attron(curses.color_pair(4))
                        status = " [IN USE]"
                    else:
                        self.stdscr.attron(curses.color_pair(1))
                        status = ""
                        
                    self.stdscr.addstr(row_y, x, f"[{num}] {port}{status}")
                    self.stdscr.attroff(curses.color_pair(4))
                    self.stdscr.attroff(curses.color_pair(1))
        
        y += 4
        self.stdscr.addstr(y, 4, "Actions:", curses.A_BOLD)
        y += 1
        self.stdscr.addstr(y, 6, "[Enter] Use current port", curses.color_pair(5))
        y += 1
        self.stdscr.addstr(y, 6, "[A] Auto-find next available", curses.color_pair(5))
        y += 1
        self.stdscr.addstr(y, 6, "[R] Random available port", curses.color_pair(5))
        y += 1
        self.stdscr.addstr(y, 6, "[ESC] Go back", curses.color_pair(5))
        
    def draw_server_logs(self, y: int, height: int, width: int, panel):
        """Draw server logs tab"""
        server = panel.server
        
        if not server.logs:
            self.stdscr.addstr(y + 2, 4, "No logs yet...", curses.A_DIM)
            return
            
        # Show recent logs
        visible = min(len(server.logs), height - 2)
        start_idx = max(0, len(server.logs) - visible)
        
        for i, (timestamp, log_line) in enumerate(server.logs[start_idx:]):
            if y + i >= y + height - 2:
                break
                
            time_str = timestamp.strftime("%H:%M:%S")
            
            # Color based on content
            if "ERROR" in log_line or "CRITICAL" in log_line:
                color = curses.color_pair(4)
            elif "WARNING" in log_line:
                color = curses.color_pair(2)
            elif "INFO" in log_line:
                color = curses.color_pair(6)
            else:
                color = curses.A_NORMAL
                
            # Truncate if needed
            max_width = width - 15
            if len(log_line) > max_width:
                log_line = log_line[:max_width - 3] + "..."
                
            self.stdscr.addstr(y + i, 2, time_str, curses.A_DIM)
            self.stdscr.attron(color)
            self.stdscr.addstr(y + i, 11, log_line)
            self.stdscr.attroff(color)
            
    def draw_server_tasks(self, y: int, height: int, width: int, panel):
        """Draw tasks tab"""
        if panel.loading:
            self.stdscr.addstr(y + 2, 4, "⏳ Loading tasks...", curses.color_pair(3))
            return
            
        if not panel.tasks:
            self.stdscr.addstr(y + 2, 4, "No tasks found", curses.A_DIM)
            return
            
        # Column headers
        headers = ["ID", "Title", "Status", "Assigned To"]
        col_widths = [15, 30, 12, 20]
        
        x = 4
        for i, header in enumerate(headers):
            self.stdscr.attron(curses.A_BOLD | curses.A_UNDERLINE)
            self.stdscr.addstr(y, x, header)
            self.stdscr.attroff(curses.A_BOLD | curses.A_UNDERLINE)
            x += col_widths[i]
            
        y += 2
        
        # Task list
        visible = min(len(panel.tasks), height - 4)
        for i in range(visible):
            idx = panel.scroll_offset + i
            if idx >= len(panel.tasks):
                break
                
            task = panel.tasks[idx]
            is_selected = idx == panel.selected_item
            
            if is_selected:
                self.stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
                
            x = 4
            # ID
            task_id = task.get('task_id', '')[:col_widths[0]-1]
            self.stdscr.addstr(y + i, x, task_id)
            x += col_widths[0]
            
            # Title
            title = task.get('title', '')[:col_widths[1]-1]
            self.stdscr.addstr(y + i, x, title)
            x += col_widths[1]
            
            # Status
            status = task.get('status', 'unknown')
            status_color = curses.color_pair(1) if status == 'completed' else curses.color_pair(6)
            self.stdscr.attron(status_color)
            self.stdscr.addstr(y + i, x, status)
            self.stdscr.attroff(status_color)
            x += col_widths[2]
            
            # Assigned to
            assigned = task.get('assigned_to', 'Unassigned')[:col_widths[3]-1]
            self.stdscr.addstr(y + i, x, assigned)
            
            if is_selected:
                self.stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
                
    def draw_server_context(self, y: int, height: int, width: int, panel):
        """Draw context tab"""
        if panel.loading:
            self.stdscr.addstr(y + 2, 4, "⏳ Loading context...", curses.color_pair(3))
            return
            
        if not panel.context:
            self.stdscr.addstr(y + 2, 4, "No context entries found", curses.A_DIM)
            return
            
        # Column headers
        headers = ["Key", "Value", "Updated"]
        col_widths = [25, 40, 20]
        
        x = 4
        for i, header in enumerate(headers):
            self.stdscr.attron(curses.A_BOLD | curses.A_UNDERLINE)
            self.stdscr.addstr(y, x, header)
            self.stdscr.attroff(curses.A_BOLD | curses.A_UNDERLINE)
            x += col_widths[i]
            
        y += 2
        
        # Context list
        visible = min(len(panel.context), height - 4)
        for i in range(visible):
            idx = panel.scroll_offset + i
            if idx >= len(panel.context):
                break
                
            ctx = panel.context[idx]
            is_selected = idx == panel.selected_item
            
            if is_selected:
                self.stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
                
            x = 4
            # Key
            key = ctx.get('context_key', '')[:col_widths[0]-1]
            self.stdscr.addstr(y + i, x, key)
            x += col_widths[0]
            
            # Value (truncated)
            value = str(ctx.get('context_value', ''))[:col_widths[1]-1]
            self.stdscr.addstr(y + i, x, value)
            x += col_widths[1]
            
            # Updated
            updated = ctx.get('updated_at', '')[:col_widths[2]-1]
            self.stdscr.addstr(y + i, x, updated)
            
            if is_selected:
                self.stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
        
    def draw_header(self, width: int):
        """Draw header with breadcrumb navigation"""
        # Title
        title = "🚀 Agent MCP Control Center"
        self.safe_addstr(0, 2, title, curses.color_pair(1) | curses.A_BOLD)
        
        # Breadcrumb
        breadcrumb = self.get_breadcrumb()
        if breadcrumb:
            self.safe_addstr(1, 2, f"📍 {breadcrumb}", curses.color_pair(3))
            
        # Server count
        if self.servers:
            running = sum(1 for s in self.servers.values() if s.is_running())
            status = f"[{running}/{len(self.servers)} servers]"
            status_x = max(0, width - len(status) - 2)
            self.safe_addstr(0, status_x, status, curses.color_pair(3))
            
        # Separator
        sep_line = "─" * min(width, 200)  # Limit separator length
        self.safe_addstr(2, 0, sep_line, curses.color_pair(6) | curses.A_DIM)
        
    def get_breadcrumb(self):
        """Get navigation breadcrumb"""
        screen_names = {
            "main_menu": "Home",
            "server_hub": "Server Hub",
            "server_control": "Server Control",
            "launch_wizard": "Launch Wizard",
            "project_browser": "Browse Projects",
            "port_selector": "Select Port"
        }
        
        parts = []
        for screen in self.screen_stack[1:]:  # Skip main_menu
            name = screen_names.get(screen, screen)
            parts.append(name)
            
        return " > ".join(parts)
        
    def draw_main_menu(self, y: int, height: int, width: int):
        """Draw enhanced main menu"""
        # Check minimum size
        if height < 15 or width < 40:
            # Show compact menu for small terminals
            self.safe_addstr(y + 1, 2, "Agent MCP", curses.color_pair(1) | curses.A_BOLD)
            self.safe_addstr(y + 3, 2, "Terminal too small!", curses.color_pair(4))
            self.safe_addstr(y + 4, 2, f"Need 40x15, have {width}x{height}")
            self.safe_addstr(y + 6, 2, "Please resize terminal")
            self.safe_addstr(y + 7, 2, "or press 'q' to quit")
            return
            
        # Center the menu
        menu_items = [
            ("1", "🎛️  Server Hub", "Manage all servers in one place"),
            ("2", "⚡ Quick Launch", "Launch server in current directory"),
            ("3", "🚀 Launch Wizard", "Step-by-step server setup"),
            ("4", "📁 Browse Projects", "Find and manage projects"),
            ("5", "🗄️  Database Tools", "Migrations and maintenance"),
            ("6", "⚙️  Settings", "Configure defaults"),
            ("7", "📚 Help", "Documentation and tips"),
            ("8", "🚪 Exit", "Close control center")
        ]
        
        # Calculate layout
        box_width = min(70, width - 10)
        box_height = len(menu_items) * 2 + 6
        
        # Check if menu fits
        if box_height > height - y - 2:
            # Show simple list for very small terminals
            self.safe_addstr(y, 2, "Agent MCP Menu", curses.color_pair(1) | curses.A_BOLD)
            for i, (num, title, _) in enumerate(menu_items[:min(len(menu_items), (height-y-3)//2)]):
                is_selected = i == self.selected_index
                line_y = y + 2 + i * 2
                if line_y >= height - 2:
                    break
                if is_selected:
                    self.safe_addstr(line_y, 2, f"▶ [{num}] {title}", curses.color_pair(2) | curses.A_BOLD)
                else:
                    self.safe_addstr(line_y, 2, f"  [{num}] {title}")
            return
            
        start_x = max(0, (width - box_width) // 2)
        start_y = max(y, min(y + (height - box_height) // 2, height - box_height - 2))
        
        # Draw box
        self.draw_box(start_x, start_y, box_width, box_height, curses.color_pair(3))
        
        # Title
        title = " Welcome to Agent MCP "
        title_x = start_x + (box_width - len(title)) // 2
        if title_x > 0 and start_y < height:
            self.safe_addstr(start_y, title_x, title, curses.color_pair(1) | curses.A_BOLD)
        
        # Menu items
        item_y = start_y + 2
        for i, (num, title, desc) in enumerate(menu_items):
            if item_y + 1 >= height - 2:
                break  # Stop if we're near the bottom
                
            is_selected = i == self.selected_index
            
            if is_selected:
                # Highlight box
                self.safe_addstr(item_y, start_x + 2, "▶", curses.color_pair(2))
                
            # Number and title
            attr = curses.A_BOLD if is_selected else curses.A_NORMAL
            self.safe_addstr(item_y, start_x + 4, f"[{num}] {title}", attr)
            
            # Description (if there's room)
            if item_y + 1 < height - 2:
                desc_color = curses.color_pair(3) if is_selected else curses.A_DIM
                self.safe_addstr(item_y + 1, start_x + 8, desc, desc_color)
            
            item_y += 2
            
    def draw_server_hub(self, y: int, height: int, width: int):
        """Draw comprehensive server hub"""
        # Title
        self.stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
        self.stdscr.addstr(y, 2, "🎛️  Server Hub - All Servers at a Glance")
        self.stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)
        y += 2
        
        if not self.servers:
            # Empty state with quick actions
            empty_box_height = 12
            empty_box_width = 65
            start_x = (width - empty_box_width) // 2
            start_y = y + (height - y - empty_box_height) // 2
            
            self.draw_box(start_x, start_y, empty_box_width, empty_box_height, curses.color_pair(3))
            
            # Title
            title = " 🚀 No Servers Running "
            self.stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
            self.stdscr.addstr(start_y, start_x + (empty_box_width - len(title)) // 2, title)
            self.stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)
            
            # Quick actions with better formatting
            actions = [
                ("N", "New Server", "Launch with wizard"),
                ("Q", "Quick Launch", "Start in current directory"),
                ("B", "Browse Projects", "Find and launch projects"),
                ("", "", ""),
                ("Tip:", "Press F2 for quick actions from anywhere", "")
            ]
            
            y_offset = 3
            for key, action, desc in actions:
                msg_y = start_y + y_offset
                
                if key == "Tip:":
                    # Special formatting for tip
                    self.stdscr.attron(curses.color_pair(5) | curses.A_DIM)
                    self.stdscr.addstr(msg_y, start_x + 4, f"{key} {action}")
                    self.stdscr.attroff(curses.color_pair(5) | curses.A_DIM)
                elif key:
                    # Action formatting
                    self.stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
                    self.stdscr.addstr(msg_y, start_x + 4, f"[{key}]")
                    self.stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
                    
                    self.stdscr.addstr(msg_y, start_x + 8, action)
                    
                    if desc:
                        self.stdscr.attron(curses.A_DIM)
                        self.stdscr.addstr(msg_y, start_x + 25, f"- {desc}")
                        self.stdscr.attroff(curses.A_DIM)
                        
                y_offset += 1
        else:
            # Server grid view
            self.draw_server_grid(y, height, width)
            
    def draw_server_grid(self, y: int, height: int, width: int):
        """Draw servers in a grid layout"""
        servers = list(self.servers.items())
        
        # Calculate grid dimensions
        card_width = min(40, (width - 6) // 2)
        card_height = 6
        cols = 2 if width > 80 else 1
        
        visible_rows = (height - y - 2) // (card_height + 1)
        visible_servers = visible_rows * cols
        
        # Adjust scroll
        if self.selected_index >= self.scroll_offset + visible_servers:
            self.scroll_offset = self.selected_index - visible_servers + 1
        elif self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
            
        # Draw server cards
        for i in range(visible_servers):
            server_idx = self.scroll_offset + i
            if server_idx >= len(servers):
                break
                
            port, server = servers[server_idx]
            is_selected = server_idx == self.selected_index
            
            # Calculate position
            row = i // cols
            col = i % cols
            card_x = 2 + col * (card_width + 2)
            card_y = y + row * (card_height + 1)
            
            # Draw card
            self.draw_server_card(card_x, card_y, card_width, card_height, 
                                server, port, is_selected)
                                
    def draw_server_card(self, x: int, y: int, w: int, h: int, 
                        server: ServerProcess, port: int, selected: bool):
        """Draw a server card"""
        # Border
        border_color = curses.color_pair(2) if selected else curses.color_pair(6)
        self.draw_box(x, y, w, h, border_color)
        
        # Status indicator
        status = "●" if server.is_running() else "○"
        status_color = curses.color_pair(1) if server.is_running() else curses.color_pair(4)
        self.stdscr.attron(status_color | curses.A_BOLD)
        self.stdscr.addstr(y + 1, x + 2, status)
        self.stdscr.attroff(status_color | curses.A_BOLD)
        
        # Server name
        name = server.name[:w-8]
        self.stdscr.attron(curses.A_BOLD)
        self.stdscr.addstr(y + 1, x + 4, name)
        self.stdscr.attroff(curses.A_BOLD)
        
        # Port
        self.stdscr.addstr(y + 2, x + 2, f"Port: {port}")
        
        # Uptime
        self.stdscr.addstr(y + 3, x + 2, f"⏱ {server.get_uptime()}")
        
        # Token status
        if server.admin_token:
            self.stdscr.attron(curses.color_pair(1))
            self.stdscr.addstr(y + 4, x + 2, "🔑 Token ready")
            self.stdscr.attroff(curses.color_pair(1))
        else:
            self.stdscr.addstr(y + 4, x + 2, "⏳ Starting...", curses.A_DIM)
            
    def draw_server_control(self, y: int, height: int, width: int):
        """Draw server control panel with tabs"""
        if not self.current_server_panel:
            self.pop_screen()
            return
            
        panel = self.current_server_panel
        server = panel.server
        
        # Load data for current tab if needed
        if panel.current_tab in ["agents", "tasks", "context"] and not panel.data_loaded:
            panel.load_data()
        
        # Header with server info
        self.stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
        self.stdscr.addstr(y, 2, f"🎛️  {server.name} Control Panel")
        self.stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)
        
        # Status line
        status = "● Running" if server.is_running() else "○ Stopped"
        status_color = curses.color_pair(1) if server.is_running() else curses.color_pair(4)
        self.stdscr.attron(status_color)
        self.stdscr.addstr(y, width - 15, status)
        self.stdscr.attroff(status_color)
        y += 2
        
        # Tabs
        tabs = [
            ("Overview", "overview"),
            ("Logs", "logs"),
            ("Agents", "agents"),
            ("Tasks", "tasks"),
            ("Context", "context")
        ]
        
        tab_x = 2
        for tab_name, tab_id in tabs:
            is_active = panel.current_tab == tab_id
            
            if is_active:
                self.stdscr.attron(curses.color_pair(2) | curses.A_BOLD | curses.A_REVERSE)
            else:
                self.stdscr.attron(curses.color_pair(6))
                
            self.stdscr.addstr(y, tab_x, f" {tab_name} ")
            
            if is_active:
                self.stdscr.attroff(curses.color_pair(2) | curses.A_BOLD | curses.A_REVERSE)
            else:
                self.stdscr.attroff(curses.color_pair(6))
                
            tab_x += len(tab_name) + 3
            
        y += 2
        
        # Tab content
        content_height = height - y - 2
        
        if panel.current_tab == "overview":
            self.draw_server_overview(y, content_height, width, panel)
        elif panel.current_tab == "logs":
            self.draw_server_logs(y, content_height, width, panel)
        elif panel.current_tab == "agents":
            self.draw_server_agents(y, content_height, width, panel)
        elif panel.current_tab == "tasks":
            self.draw_server_tasks(y, content_height, width, panel)
        elif panel.current_tab == "context":
            self.draw_server_context(y, content_height, width, panel)
            
    def draw_server_overview(self, y: int, height: int, width: int, panel):
        """Draw server overview tab"""
        server = panel.server
        
        # Info grid
        info = [
            ("Project", server.name),
            ("Directory", server.project_dir),
            ("Port", str(panel.port)),
            ("Uptime", server.get_uptime()),
            ("Admin Token", server.admin_token or "Not available"),
            ("Process ID", str(server.process.pid) if server.process else "N/A")
        ]
        
        # Draw info in two columns
        col_width = (width - 6) // 2
        for i, (label, value) in enumerate(info):
            col = i % 2
            row = i // 2
            x = 4 + col * col_width
            info_y = y + row * 2
            
            self.stdscr.attron(curses.A_BOLD)
            self.stdscr.addstr(info_y, x, f"{label}:")
            self.stdscr.attroff(curses.A_BOLD)
            
            # Truncate value if needed
            max_val_width = col_width - len(label) - 4
            if len(value) > max_val_width:
                value = value[:max_val_width-3] + "..."
                
            self.stdscr.addstr(info_y + 1, x + 2, value)
            
        # Quick actions
        y += 8
        self.stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
        self.stdscr.addstr(y, 4, "Quick Actions:")
        self.stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)
        y += 2
        
        actions = [
            ("C", "Copy admin token"),
            ("R", "Restart server"),
            ("S", "Stop server"),
            ("O", "Open in browser"),
            ("E", "Export config")
        ]
        
        for key, desc in actions:
            self.stdscr.attron(curses.color_pair(5))
            self.stdscr.addstr(y, 6, f"[{key}]")
            self.stdscr.attroff(curses.color_pair(5))
            self.stdscr.addstr(y, 10, desc)
            y += 1
            
    def draw_server_agents(self, y: int, height: int, width: int, panel):
        """Draw agents tab"""
        if panel.loading:
            self.stdscr.addstr(y + 2, 4, "⏳ Loading agents...", curses.color_pair(3))
            return
            
        if not panel.agents:
            self.stdscr.addstr(y + 2, 4, "No agents found", curses.A_DIM)
            return
            
        # Column headers
        headers = ["ID", "Status", "Tasks", "Token"]
        col_widths = [20, 10, 8, 30]
        
        x = 4
        for i, header in enumerate(headers):
            self.stdscr.attron(curses.A_BOLD | curses.A_UNDERLINE)
            self.stdscr.addstr(y, x, header)
            self.stdscr.attroff(curses.A_BOLD | curses.A_UNDERLINE)
            x += col_widths[i]
            
        y += 2
        
        # Agent list
        visible = min(len(panel.agents), height - 2)
        for i in range(visible):
            idx = panel.scroll_offset + i
            if idx >= len(panel.agents):
                break
                
            agent = panel.agents[idx]
            is_selected = idx == panel.selected_item
            
            if is_selected:
                self.stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
                
            x = 4
            # ID
            self.stdscr.addstr(y + i, x, agent['agent_id'][:col_widths[0]-1])
            x += col_widths[0]
            
            # Status
            status_color = curses.color_pair(1) if agent['status'] == 'active' else curses.color_pair(4)
            self.stdscr.attron(status_color)
            self.stdscr.addstr(y + i, x, agent['status'])
            self.stdscr.attroff(status_color)
            x += col_widths[1]
            
            # Tasks
            self.stdscr.addstr(y + i, x, str(agent.get('active_tasks', 0)))
            x += col_widths[2]
            
            # Token (truncated)
            token = agent.get('token', '')[:col_widths[3]-1]
            self.stdscr.addstr(y + i, x, token)
            
            if is_selected:
                self.stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
                
    def draw_launch_wizard(self, y: int, height: int, width: int):
        """Draw step-by-step launch wizard"""
        # Calculate layout
        wizard_width = min(70, width - 10)
        wizard_height = height - 4
        start_x = (width - wizard_width) // 2
        
        # Draw wizard box
        self.draw_box(start_x, y, wizard_width, wizard_height)
        
        # Title
        title = " 🚀 Server Launch Wizard "
        self.stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
        self.stdscr.addstr(y, start_x + (wizard_width - len(title)) // 2, title)
        self.stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)
        
        # Steps
        steps = [
            ("1", "Select Project", self.launch_config["project_dir"] is not None),
            ("2", "Choose Port", True),  # Always can choose port
            ("3", "Configure Options", True),
            ("4", "Launch Server", self.launch_config["project_dir"] is not None)
        ]
        
        step_y = y + 3
        for i, (num, label, completed) in enumerate(steps):
            is_current = i == self.selected_index
            
            # Step indicator
            if completed:
                self.stdscr.attron(curses.color_pair(1))
                indicator = "✓"
            else:
                self.stdscr.attron(curses.color_pair(6))
                indicator = "○"
                
            if is_current:
                self.stdscr.attron(curses.A_BOLD)
                self.stdscr.addstr(step_y, start_x + 3, "▶")
                
            self.stdscr.addstr(step_y, start_x + 5, f"{indicator} {num}. {label}")
            
            if completed:
                self.stdscr.attroff(curses.color_pair(1))
            else:
                self.stdscr.attroff(curses.color_pair(6))
                
            if is_current:
                self.stdscr.attroff(curses.A_BOLD)
                
            step_y += 2
            
        # Current step details
        detail_y = y + 12
        self.draw_wizard_step_details(start_x + 2, detail_y, wizard_width - 4)
        
    def draw_wizard_step_details(self, x: int, y: int, width: int):
        """Draw details for current wizard step"""
        if self.selected_index == 0:  # Select Project
            self.stdscr.attron(curses.A_BOLD)
            self.stdscr.addstr(y, x, "Select Project Directory:")
            self.stdscr.attroff(curses.A_BOLD)
            
            if self.launch_config["project_dir"]:
                self.stdscr.attron(curses.color_pair(1))
                self.stdscr.addstr(y + 2, x + 2, f"✓ {self.launch_config['project_dir']}")
                self.stdscr.attroff(curses.color_pair(1))
                
                # Check if initialized
                path = Path(self.launch_config["project_dir"])
                if (path / ".agent").exists():
                    self.stdscr.addstr(y + 3, x + 2, "Project is initialized", curses.color_pair(1))
                else:
                    self.stdscr.addstr(y + 3, x + 2, "Project needs initialization", curses.color_pair(4))
            else:
                self.stdscr.addstr(y + 2, x + 2, "Press [B] to browse for project", curses.A_DIM)
                self.stdscr.addstr(y + 3, x + 2, "Press [C] to use current directory", curses.A_DIM)
                
        elif self.selected_index == 1:  # Choose Port
            self.stdscr.attron(curses.A_BOLD)
            self.stdscr.addstr(y, x, "Select Server Port:")
            self.stdscr.attroff(curses.A_BOLD)
            
            # Port options
            port = self.launch_config["port"]
            self.stdscr.addstr(y + 2, x + 2, f"Current: {port}")
            
            # Check availability
            if port in self.servers:
                self.stdscr.attron(curses.color_pair(4))
                self.stdscr.addstr(y + 3, x + 2, "⚠ Port is already in use!")
                self.stdscr.attroff(curses.color_pair(4))
            else:
                self.stdscr.attron(curses.color_pair(1))
                self.stdscr.addstr(y + 3, x + 2, "✓ Port is available")
                self.stdscr.attroff(curses.color_pair(1))
                
            self.stdscr.addstr(y + 5, x + 2, "[P] Manual port entry", curses.color_pair(5))
            self.stdscr.addstr(y + 6, x + 2, "[+/-] Increment/decrement", curses.color_pair(5))
            self.stdscr.addstr(y + 7, x + 2, "[A] Find next available", curses.color_pair(5))
            
        elif self.selected_index == 2:  # Configure Options
            self.stdscr.attron(curses.A_BOLD)
            self.stdscr.addstr(y, x, "Launch Options:")
            self.stdscr.attroff(curses.A_BOLD)
            
            # Options with checkboxes
            options = [
                ("Auto-increment port if taken", self.launch_config["auto_increment_port"]),
                ("Initialize project if needed", self.launch_config["init_if_needed"]),
            ]
            
            opt_y = y + 2
            for i, (label, enabled) in enumerate(options):
                checkbox = "☑" if enabled else "☐"
                color = curses.color_pair(1) if enabled else curses.color_pair(6)
                
                self.stdscr.attron(color)
                self.stdscr.addstr(opt_y + i, x + 2, f"{checkbox} {label}")
                self.stdscr.attroff(color)
                
            self.stdscr.addstr(opt_y + 3, x + 2, "Press [Space] to toggle options", curses.color_pair(5))
            
        elif self.selected_index == 3:  # Launch
            self.stdscr.attron(curses.A_BOLD)
            self.stdscr.addstr(y, x, "Ready to Launch!")
            self.stdscr.attroff(curses.A_BOLD)
            
            if self.launch_config["project_dir"]:
                self.stdscr.addstr(y + 2, x + 2, f"Project: {self.launch_config['project_dir']}")
                self.stdscr.addstr(y + 3, x + 2, f"Port: {self.launch_config['port']}")
                
                self.stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
                self.stdscr.addstr(y + 5, x + 10, "Press [L] to Launch Server")
                self.stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
            else:
                self.stdscr.attron(curses.color_pair(4))
                self.stdscr.addstr(y + 2, x + 2, "Please select a project first!")
                self.stdscr.attroff(curses.color_pair(4))
                
    def draw_quick_actions(self, height: int, width: int):
        """Draw quick actions overlay"""
        # Semi-transparent overlay effect
        overlay_height = 15
        overlay_width = 50
        start_y = (height - overlay_height) // 2
        start_x = (width - overlay_width) // 2
        
        # Draw box with shadow effect
        self.draw_box(start_x, start_y, overlay_width, overlay_height, curses.color_pair(2))
        
        # Title
        title = " ⚡ Quick Actions "
        self.stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
        self.stdscr.addstr(start_y, start_x + (overlay_width - len(title)) // 2, title)
        self.stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
        
        # Actions
        actions = [
            ("N", "New Server", "Launch a new server"),
            ("S", "Stop All", "Stop all running servers"),
            ("R", "Restart All", "Restart all servers"),
            ("C", "Copy All Tokens", "Copy all admin tokens"),
            ("E", "Export Config", "Export server configs"),
            ("", "", ""),
            ("ESC", "Close", "Close this menu")
        ]
        
        y = start_y + 2
        for key, action, desc in actions:
            if not key:  # Separator
                y += 1
                continue
                
            # Key
            if key == "ESC":
                self.stdscr.attron(curses.color_pair(4))
            else:
                self.stdscr.attron(curses.color_pair(5) | curses.A_BOLD)
                
            self.stdscr.addstr(y, start_x + 3, f"[{key}]")
            
            if key == "ESC":
                self.stdscr.attroff(curses.color_pair(4))
            else:
                self.stdscr.attroff(curses.color_pair(5) | curses.A_BOLD)
                
            # Action and description
            self.stdscr.addstr(y, start_x + 8, f"{action}")
            self.stdscr.addstr(y, start_x + 20, f"- {desc}", curses.A_DIM)
            y += 1
            
    def draw_footer(self, y: int, width: int):
        """Draw context-sensitive footer"""
        controls = self.get_controls()
        
        # Global shortcuts on the left
        global_controls = "[F1] Help | [F2] Quick Actions"
        self.safe_addstr(y, 2, global_controls, curses.color_pair(5))
        
        # Context controls on the right
        if controls:
            control_str = " | ".join([f"{k}: {v}" for k, v in controls.items()])
            if len(control_str) > width // 2:
                control_str = control_str[:width//2 - 3] + "..."
                
            x = max(0, width - len(control_str) - 2)
            self.safe_addstr(y, x, control_str, curses.color_pair(5))
            
    def get_controls(self) -> Dict[str, str]:
        """Get context-sensitive controls"""
        screen = self.current_screen
        
        base = {"ESC": "Back"} if len(self.screen_stack) > 1 else {"q": "Quit"}
        
        if screen == "main_menu":
            return {**base, "↑↓": "Navigate", "Enter": "Select", "1-8": "Quick"}
        elif screen == "server_hub":
            return {**base, "Enter": "View", "n": "New", "s": "Stop", "r": "Restart"}
        elif screen == "server_control":
            if self.current_server_panel:
                return {**base, "Tab": "Switch Tab", "c": "Copy", "r": "Restart"}
            return base
        elif screen == "launch_wizard":
            return {**base, "↑↓": "Steps", "Enter": "Select", "b": "Browse"}
            
        return base
        
    def draw_box(self, x: int, y: int, w: int, h: int, color=None):
        """Draw a box with unicode characters"""
        height, width = self.stdscr.getmaxyx()
        
        # Check if box fits in terminal
        if x < 0 or y < 0 or x + w > width or y + h > height:
            return  # Don't draw if box doesn't fit
            
        if color:
            self.stdscr.attron(color)
            
        try:
            # Corners
            if y < height and x < width:
                self.stdscr.addstr(y, x, "╔")
            if y < height and x + w - 1 < width:
                self.stdscr.addstr(y, x + w - 1, "╗")
            if y + h - 1 < height and x < width:
                self.stdscr.addstr(y + h - 1, x, "╚")
            if y + h - 1 < height and x + w - 1 < width:
                self.stdscr.addstr(y + h - 1, x + w - 1, "╝")
            
            # Horizontal lines
            for i in range(1, w - 1):
                if y < height and x + i < width:
                    self.stdscr.addstr(y, x + i, "═")
                if y + h - 1 < height and x + i < width:
                    self.stdscr.addstr(y + h - 1, x + i, "═")
                
            # Vertical lines
            for i in range(1, h - 1):
                if y + i < height and x < width:
                    self.stdscr.addstr(y + i, x, "║")
                if y + i < height and x + w - 1 < width:
                    self.stdscr.addstr(y + i, x + w - 1, "║")
        except curses.error:
            pass  # Ignore curses errors when writing at screen edges
            
        if color:
            self.stdscr.attroff(color)
            
    def draw_scrollbar(self, y: int, visible_height: int, total_items: int, scroll_offset: int, x: int):
        """Draw a vertical scrollbar"""
        if total_items <= visible_height:
            return
            
        # Calculate scrollbar position and size
        scrollbar_height = max(1, int(visible_height * visible_height / total_items))
        scrollbar_pos = int(scroll_offset * (visible_height - scrollbar_height) / (total_items - visible_height))
        
        # Draw scrollbar track
        for i in range(visible_height):
            self.stdscr.addstr(y + i, x, "│", curses.A_DIM)
            
        # Draw scrollbar thumb
        for i in range(scrollbar_height):
            if y + scrollbar_pos + i < y + visible_height:
                self.stdscr.addstr(y + scrollbar_pos + i, x, "█", curses.color_pair(3))
            
    def handle_input(self, key: int) -> bool:
        """Handle keyboard input"""
        # Skip if still processing
        if key == -1:
            return True
            
        ui_logger.debug(f"handle_input called with key: {key}")
        
        # ESC key handling - IMMEDIATE with debounce
        if key == 27:  # ESC
            ui_logger.info("ESC key pressed")
            current_time = time.time()
            # Debounce ESC to prevent accidental exits
            if hasattr(self, '_last_esc_time') and current_time - self._last_esc_time < 0.3:
                ui_logger.debug("ESC key debounced")
                return True  # Ignore rapid ESC presses
            self._last_esc_time = current_time
            
            if self.quick_actions_open:
                ui_logger.info("Closing quick actions menu")
                self.quick_actions_open = False
                return True
            elif self.pop_screen():
                ui_logger.info(f"Popped screen, now at: {self.current_screen}")
                return True
            else:
                # Only exit if at main menu
                if self.current_screen == "main_menu":
                    ui_logger.info("ESC at main menu - confirming exit")
                    return self.confirm_exit()
                return True
                
        # Log other key presses for debugging
        key_str = chr(key) if 32 <= key < 127 else f"special({key})"
        ui_logger.debug(f"Key pressed: {key_str} ({key}) on screen: {self.current_screen}")
        
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Key pressed: {key_str} ({key}) on screen: {self.current_screen}")
        
        if key == curses.KEY_F2:
            self.quick_actions_open = not self.quick_actions_open
            return True
            
        # Quick actions handling
        if self.quick_actions_open:
            return self.handle_quick_action(key)
            
        # Handle resize event
        if key == curses.KEY_RESIZE or key == 410:
            # Terminal was resized, just redraw
            return True
            
        # Navigation - always handle these
        if key == curses.KEY_UP or key == ord('k'):
            self.move_selection(-1)
            return True
        elif key == curses.KEY_DOWN or key == ord('j'):
            self.move_selection(1)
            return True
        elif key == 10:  # Enter
            self.handle_selection()
            return True
            
        # Always allow 'q' to quit (especially for small terminals)
        if key == ord('q') or key == ord('Q'):
            if self.current_screen == "main_menu":
                return self.confirm_exit()
            else:
                self.pop_screen()
            return True
            
        # Screen-specific handling
        if self.current_screen == "main_menu":
            if ord('1') <= key <= ord('8'):
                self.selected_index = key - ord('1')
                self.handle_selection()
        elif self.current_screen == "server_hub":
            if key == ord('n') or key == ord('N'):
                self.push_screen("launch_wizard")
            elif key == ord('b') or key == ord('B'):
                self.push_screen("project_browser")
        elif self.current_screen == "server_control":
            if key == 9:  # Tab
                self.switch_server_tab()
            elif key == ord('c') or key == ord('C'):
                self.copy_current_item()
        elif self.current_screen == "launch_wizard":
            # Always pass keys to wizard handler
            self.handle_wizard_input(key)
        elif self.current_screen == "project_browser":
            self.handle_project_browser_input(key)
        elif self.current_screen == "port_selector":
            self.handle_port_selector_input(key)
            
        return True
        
    def handle_project_browser_input(self, key: int):
        """Handle project browser input"""
        if key == ord('l') or key == ord('L'):
            # Launch server from selected project
            if 0 <= self.selected_index < len(self.browser_items):
                item = self.browser_items[self.selected_index]
                if item.is_dir() and (item / ".agent").exists():
                    self.launch_server(item, self.find_available_port())
                    # Switch to server hub after launch
                    self.screen_stack = ["main_menu", "server_hub"]
        elif key == ord('i') or key == ord('I'):
            # Initialize selected directory
            if 0 <= self.selected_index < len(self.browser_items):
                item = self.browser_items[self.selected_index]
                if item.is_dir() and not (item / ".agent").exists():
                    self.show_message("Initializing project...", "info")
                    self.stdscr.refresh()
                    try:
                        init_agent_directory(str(item))
                        self.show_message("Project initialized!", "success")
                        self.browser_items = []  # Force reload
                    except Exception as e:
                        self.show_message(f"Init failed: {str(e)}", "error")
        elif key == ord('h') or key == ord('H'):
            # Go to home directory
            self.browser_path = Path.home()
            self.browser_items = []
            self.selected_index = 0
            self.scroll_offset = 0
        elif key == ord('u') or key == ord('U'):
            # Go up one directory
            if self.browser_path.parent != self.browser_path:
                self.browser_path = self.browser_path.parent
                self.browser_items = []
                self.selected_index = 0
                self.scroll_offset = 0
        elif key == ord('g') or key == ord('G'):
            # Go to specific directory - for now just go to /tmp
            self.browser_path = Path("/tmp")
            self.browser_items = []
            self.selected_index = 0
            self.scroll_offset = 0
        elif key == ord('r') or key == ord('R'):
            # Refresh current directory
            self.browser_items = []
            self.show_message("Directory refreshed", "info")
    
    def handle_port_selector_input(self, key: int):
        """Handle port selector input"""
        current_port = self.launch_config.get("port", 8080)
        
        if key == 10:  # Enter - use current port
            self.pop_screen()
        elif key == ord('+') or key == ord('='):
            # Increment port
            self.launch_config["port"] = min(65535, current_port + 1)
        elif key == ord('-') or key == ord('_'):
            # Decrement port
            self.launch_config["port"] = max(1024, current_port - 1)
        elif ord('1') <= key <= ord('9'):
            # Quick select
            common_ports = [8080, 8081, 8082, 3000, 3001, 3002, 5000, 5001, 9000]
            idx = key - ord('1')
            if idx < len(common_ports):
                self.launch_config["port"] = common_ports[idx]
                self.show_message(f"Selected port {common_ports[idx]}", "success")
        elif ord('0') <= key <= ord('9'):
            # Direct number entry - start with this digit
            if not hasattr(self, '_port_entry'):
                self._port_entry = ""
            self._port_entry += chr(key)
            
            # Limit to 5 digits
            if len(self._port_entry) > 5:
                self._port_entry = self._port_entry[-5:]
                
            try:
                port = int(self._port_entry)
                if 1024 <= port <= 65535:
                    self.launch_config["port"] = port
            except ValueError:
                pass
        elif key == ord('a') or key == ord('A'):
            # Auto-find next available
            self.launch_config["port"] = self.find_available_port()
            self.show_message(f"Auto-selected port {self.launch_config['port']}", "success")
        elif key == ord('r') or key == ord('R'):
            # Random available port
            import random
            available = [p for p in range(8000, 9000) if p not in self.servers]
            if available:
                self.launch_config["port"] = random.choice(available)
                self.show_message(f"Random port {self.launch_config['port']}", "success")
        elif key == 127 or key == curses.KEY_BACKSPACE:  # Backspace
            # Clear port entry
            if hasattr(self, '_port_entry'):
                self._port_entry = ""
    
    def handle_wizard_input(self, key: int):
        """Handle launch wizard input"""
        logger.debug(f"Wizard input - step: {self.selected_index}, key: {key}, chr: {chr(key) if 32 <= key < 127 else 'special'}")
        
        if self.selected_index == 0:  # Project selection
            if key == ord('b') or key == ord('B'):
                logger.info("Opening project browser from wizard")
                self.push_screen("project_browser")
            elif key == ord('c') or key == ord('C'):
                self.launch_config["project_dir"] = str(Path.cwd())
                logger.info(f"Set project dir to current: {self.launch_config['project_dir']}")
        elif self.selected_index == 1:  # Port selection
            if key == ord('+') or key == ord('='):
                self.launch_config["port"] = min(65535, self.launch_config["port"] + 1)
            elif key == ord('-'):
                self.launch_config["port"] = max(1024, self.launch_config["port"] - 1)
            elif key == ord('a') or key == ord('A'):
                self.launch_config["port"] = self.find_available_port()
            elif key == ord('p') or key == ord('P'):
                self.push_screen("port_selector")
        elif self.selected_index == 2:  # Options
            if key == ord(' '):
                # Toggle current option
                pass
        elif self.selected_index == 3:  # Launch
            if key == ord('l') or key == ord('L'):
                if self.launch_config["project_dir"]:
                    self.launch_server_from_wizard()
                    
    def handle_selection(self):
        """Handle enter key press"""
        if self.current_screen == "main_menu":
            options = [
                "server_hub",
                self.quick_launch,  # Function to call
                "launch_wizard",
                "project_browser",
                "database_tools",
                "settings",
                "help",
                self.confirm_exit  # Function to call
            ]
            
            if 0 <= self.selected_index < len(options):
                option = options[self.selected_index]
                if callable(option):
                    option()
                else:
                    self.push_screen(option)
                    
        elif self.current_screen == "server_hub":
            # Open server control panel
            if self.servers and 0 <= self.selected_index < len(self.servers):
                ports = list(self.servers.keys())
                port = ports[self.selected_index]
                server = self.servers[port]
                
                # Create control panel WITHOUT loading data yet
                self.current_server_panel = ServerControlPanel(server, port)
                # Data will be loaded on-demand when tab is displayed
                self.push_screen("server_control")
                
        elif self.current_screen == "project_browser":
            # Handle project browser selection
            if 0 <= self.selected_index < len(self.browser_items):
                item = self.browser_items[self.selected_index]
                
                # Special case for parent directory
                if item == self.browser_path.parent and item != self.browser_path:
                    self.browser_path = item
                    self.browser_items = []
                    self.selected_index = 0
                    self.scroll_offset = 0
                elif item.is_dir():
                    if (item / ".agent").exists():
                        # This is an MCP project - select it for launch
                        self.launch_config["project_dir"] = str(item)
                        if len(self.screen_stack) > 1 and self.screen_stack[-2] == "launch_wizard":
                            # Go back to launch wizard
                            self.pop_screen()
                        else:
                            # Ask what to do with this project
                            self.show_message(f"Selected: {item.name}. Press L to launch.", "success")
                    else:
                        # Navigate into directory
                        self.browser_path = item
                        self.browser_items = []
                        self.selected_index = 0
                        self.scroll_offset = 0
                
    def switch_server_tab(self):
        """Switch between server control tabs"""
        if not self.current_server_panel:
            return
            
        tabs = ["overview", "logs", "agents", "tasks", "context"]
        current_idx = tabs.index(self.current_server_panel.current_tab)
        next_idx = (current_idx + 1) % len(tabs)
        old_tab = self.current_server_panel.current_tab
        self.current_server_panel.current_tab = tabs[next_idx]
        
        # Mark data as not loaded when switching tabs
        if old_tab != tabs[next_idx]:
            self.current_server_panel.data_loaded = False
            self.current_server_panel.selected_item = 0
            self.current_server_panel.scroll_offset = 0
            
    def quick_launch(self):
        """Quick launch in current directory"""
        current_dir = Path.cwd()
        
        # Check if already initialized
        if not (current_dir / ".agent").exists():
            # Ask to initialize
            self.show_message("Initializing project...", "info")
            self.stdscr.refresh()
            try:
                init_agent_directory(str(current_dir))
                self.show_message("Project initialized!", "success")
            except Exception as e:
                self.show_message(f"Init failed: {str(e)}", "error")
                return False
                
        # Find available port
        port = self.find_available_port()
        
        # Launch (migration will happen automatically)
        if self.launch_server(current_dir, port):
            # Switch to server hub to see the new server
            self.screen_stack = ["main_menu", "server_hub"]
            
        return True
        
    def launch_server_from_wizard(self):
        """Launch server from wizard config"""
        project_dir = Path(self.launch_config["project_dir"])
        port = self.launch_config["port"]
        
        # Check if port is taken and auto-increment
        if port in self.servers and self.launch_config["auto_increment_port"]:
            port = self.find_available_port()
            
        # Initialize if needed
        if self.launch_config["init_if_needed"] and not (project_dir / ".agent").exists():
            self.show_message("Initializing project...", "info")
            try:
                init_agent_directory(str(project_dir))
            except Exception as e:
                self.show_message(f"Init failed: {str(e)}", "error")
                return
                
        # Launch
        if self.launch_server(project_dir, port):
            # Go to server hub
            self.screen_stack = ["main_menu", "server_hub"]
            
    def launch_server(self, project_dir: Path, port: int) -> bool:
        """Launch a new server"""
        ui_logger.info(f"Launching server: project_dir={project_dir}, port={port}")
        
        if port in self.servers:
            ui_logger.warning(f"Port {port} already in use")
            self.show_message(f"Port {port} already in use", "error")
            return False
        
        # Run auto-migration before launching
        self.show_message("Checking database...", "info")
        self.stdscr.refresh()
        ui_logger.info("Running database migration check")
        
        try:
            from ..utils.auto_migrate import ensure_database_ready
            ui_logger.debug(f"Calling ensure_database_ready for {project_dir}")
            if not ensure_database_ready(str(project_dir)):
                ui_logger.warning("Database check returned False, continuing anyway")
                self.show_message("Database check failed, continuing anyway", "warning")
        except Exception as e:
            logger.warning(f"Migration check failed: {e}")
            ui_logger.error(f"Migration check failed: {e}")
            ui_logger.debug(f"Migration error traceback: {traceback.format_exc()}")
            
        cmd = [
            sys.executable, "-m", "agent_mcp.cli_main", "server",
            "--port", str(port),
            "--project-dir", str(project_dir),
            "--no-tui"
        ]
        ui_logger.info(f"Launch command: {' '.join(cmd)}")
        
        try:
            ui_logger.debug("Starting subprocess...")
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                universal_newlines=False,
                preexec_fn=os.setsid if sys.platform != 'win32' else None
            )
            ui_logger.info(f"Process started with PID: {process.pid}")
            
            server = ServerProcess(str(project_dir), port, process)
            self.servers[port] = server
            ui_logger.info(f"Server object created and registered for port {port}")
            
            self.show_message(f"Server launched on port {port}!", "success")
            ui_logger.info(f"Server successfully launched on port {port}")
            return True
            
        except Exception as e:
            ui_logger.error(f"Launch failed: {str(e)}")
            ui_logger.debug(f"Launch error traceback: {traceback.format_exc()}")
            self.show_message(f"Launch failed: {str(e)}", "error")
            return False
            
    def find_available_port(self) -> int:
        """Find next available port"""
        port = 8080
        while port in self.servers:
            port += 1
        return port
        
    def copy_current_item(self):
        """Copy current item to clipboard"""
        if self.current_screen == "server_control" and self.current_server_panel:
            panel = self.current_server_panel
            
            if panel.current_tab == "overview" and panel.server.admin_token:
                try:
                    pyperclip.copy(panel.server.admin_token)
                    self.show_message("Token copied!", "success")
                except Exception as e:
                    self.show_message(f"Copy failed: {str(e)}", "error")
            elif panel.current_tab == "agents" and panel.agents:
                if 0 <= panel.selected_item < len(panel.agents):
                    agent = panel.agents[panel.selected_item]
                    pyperclip.copy(agent.get('token', ''))
                    self.show_message("Agent token copied!", "success")
                    
    def move_selection(self, delta: int):
        """Move selection up or down"""
        if self.current_screen == "main_menu":
            max_items = 8
        elif self.current_screen == "server_hub":
            max_items = len(self.servers) if self.servers else 0
        elif self.current_screen == "launch_wizard":
            max_items = 4
        elif self.current_screen == "project_browser":
            max_items = len(self.browser_items)
        elif self.current_screen == "port_selector":
            # Available ports shown
            common_ports = [8080, 8081, 8082, 3000, 3001, 5000, 5001, 9000]
            available_ports = [p for p in common_ports if p not in self.servers]
            max_items = min(len(available_ports), 5)
        elif self.current_screen == "database_tools":
            max_items = 5  # Number of tool options
        elif self.current_screen == "server_control" and self.current_server_panel:
            panel = self.current_server_panel
            if panel.current_tab == "agents":
                max_items = len(panel.agents)
            elif panel.current_tab == "tasks":
                max_items = len(panel.tasks)
            elif panel.current_tab == "context":
                max_items = len(panel.context)
            else:
                return
        else:
            max_items = 0
            
        if max_items > 0:
            self.selected_index = max(0, min(self.selected_index + delta, max_items - 1))
            logger.debug(f"Selection moved to {self.selected_index} of {max_items} items")
            
    def show_message(self, message: str, msg_type: str = "info"):
        """Show a temporary message"""
        self.message = message
        self.message_type = msg_type
        self._needs_redraw = True
        
        # Auto-clear after 2 seconds
        def clear():
            time.sleep(2)
            self.message = ""
            self._needs_redraw = True
            
        threading.Thread(target=clear, daemon=True).start()
        
    def draw_message(self, y: int, width: int):
        """Draw message"""
        if not self.message:
            return
            
        colors = {
            "success": curses.color_pair(1),
            "error": curses.color_pair(4),
            "info": curses.color_pair(3)
        }
        
        color = colors.get(self.message_type, curses.color_pair(6))
        x = max(0, (width - len(self.message)) // 2)
        
        self.safe_addstr(y, x, self.message, color | curses.A_BOLD)
        
    def confirm_exit(self) -> bool:
        """Confirm before exit"""
        if any(s.is_running() for s in self.servers.values()):
            # Show confirmation in message area
            self.show_message("Press 'y' to exit with servers running", "error")
            key = self.stdscr.getch()
            return key in [ord('y'), ord('Y')]
        return False
        
    def draw_database_tools(self, y: int, height: int, width: int):
        """Draw database tools screen"""
        self.stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
        self.stdscr.addstr(y, 2, "🗄️ Database Tools")
        self.stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)
        y += 2
        
        self.stdscr.addstr(y, 4, "Database tools coming soon...", curses.A_DIM)
        
    def draw_settings(self, y: int, height: int, width: int):
        """Draw settings screen"""
        self.stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
        self.stdscr.addstr(y, 2, "⚙️ Settings")
        self.stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)
        y += 2
        
        self.stdscr.addstr(y, 4, "Settings coming soon...", curses.A_DIM)
        
    def draw_help(self, y: int, height: int, width: int):
        """Draw help screen"""
        self.stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
        self.stdscr.addstr(y, 2, "📚 Help & Documentation")
        self.stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)
        y += 2
        
        help_text = [
            "Navigation:",
            "  ESC     - Go back",
            "  ↑↓/jk   - Move selection",
            "  Enter   - Select/Confirm",
            "  Tab     - Switch tabs",
            "  F2      - Quick actions",
            "",
            "Server Management:",
            "  n       - New server",
            "  s       - Stop server",
            "  r       - Restart server",
            "  c       - Copy token",
            "",
            "Tips:",
            "  - Use breadcrumbs to see where you are",
            "  - ESC always takes you back",
            "  - F2 opens quick actions from anywhere"
        ]
        
        for i, line in enumerate(help_text):
            if y + i < height - 2:
                if line.endswith(":"):
                    self.stdscr.attron(curses.A_BOLD)
                    self.stdscr.addstr(y + i, 4, line)
                    self.stdscr.attroff(curses.A_BOLD)
                else:
                    self.stdscr.addstr(y + i, 4, line)
                    
    def handle_quick_action(self, key: int):
        """Handle quick action menu input"""
        if key == ord('n') or key == ord('N'):
            self.quick_actions_open = False
            self.push_screen("launch_wizard")
        elif key == ord('s') or key == ord('S'):
            # Stop all servers
            for server in self.servers.values():
                if server.is_running():
                    server.stop()
            self.show_message("All servers stopped", "success")
            self.quick_actions_open = False
        elif key == ord('r') or key == ord('R'):
            # Restart all servers
            count = 0
            for port, server in list(self.servers.items()):
                if server.is_running():
                    server.stop()
                    time.sleep(0.5)
                    self.launch_server(Path(server.project_dir), port)
                    count += 1
            self.show_message(f"Restarted {count} servers", "success")
            self.quick_actions_open = False
        elif key == ord('c') or key == ord('C'):
            # Copy all tokens
            tokens = []
            for server in self.servers.values():
                if server.admin_token:
                    tokens.append(f"{server.name}: {server.admin_token}")
            if tokens:
                pyperclip.copy("\n".join(tokens))
                self.show_message("All tokens copied!", "success")
            else:
                self.show_message("No tokens available", "error")
            self.quick_actions_open = False
        elif key == 27:  # ESC
            self.quick_actions_open = False
            
        return True
        
    def cleanup(self):
        """Cleanup on exit"""
        self.running = False
        for server in self.servers.values():
            if server.is_running():
                server.stop()


def run_enhanced_interface():
    """Run the enhanced unified interface"""
    ui_logger.info("=" * 80)
    ui_logger.info("STARTING ENHANCED UNIFIED INTERFACE")
    ui_logger.info("=" * 80)
    ui_logger.info(f"Terminal: {os.environ.get('TERM', 'unknown')}")
    try:
        ui_logger.info(f"Terminal size: {os.get_terminal_size()}")
    except OSError as e:
        ui_logger.info(f"Terminal size: Unable to determine (error: {e})")
    
    logger.info("Starting enhanced interface")
    try:
        logger.info("Initializing curses wrapper")
        ui_logger.info("Initializing curses...")
        wrapper(lambda stdscr: EnhancedUnifiedInterface(stdscr).run())
        logger.info("Interface closed normally")
        ui_logger.info("Interface closed normally")
    except KeyboardInterrupt:
        logger.info("Interface closed by user (Ctrl+C)")
        ui_logger.info("Interface closed by user (Ctrl+C)")
    except curses.error as e:
        logger.error(f"Curses error: {e}")
        ui_logger.error(f"Curses error: {e}")
        ui_logger.debug(f"Curses error traceback: {traceback.format_exc()}")
        click.echo("Terminal error. Try a different terminal.")
    except Exception as e:
        logger.error(f"Interface error: {e}", exc_info=True)
        ui_logger.error(f"Interface error: {e}")
        ui_logger.debug(f"Error traceback: {traceback.format_exc()}")
        click.echo(f"Error: {str(e)}")
    finally:
        ui_logger.info("Enhanced interface shutdown complete")
        ui_logger.info("=" * 80)