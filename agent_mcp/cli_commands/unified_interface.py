"""
Unified Agent MCP Interface - Everything in one place
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

from ..core.config import logger, get_project_dir
from ..db.connection import get_db_connection
from ..db.actions.agent_db import get_all_active_agents_from_db
from ..db.actions.task_db import get_all_tasks_from_db
# Context will be retrieved directly from database
from ..utils.project_utils import init_agent_directory
from ..db.migrations.migration_manager import MigrationManager
from .server_manager import ServerProcess


def get_all_context_from_db():
    """Get all context entries from the database"""
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


class UnifiedMCPInterface:
    """Main unified interface for all Agent MCP operations"""
    
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.current_screen = "main_menu"
        self.previous_screen = None
        self.selected_index = 0
        self.scroll_offset = 0
        
        # Server management
        self.servers: Dict[int, ServerProcess] = {}
        self.current_server_port = None
        
        # File browser state
        self.browser_path = Path.home()
        self.browser_items = []
        
        # Data explorer state
        self.explorer_mode = None  # agents, tasks, context
        self.explorer_items = []
        self.explorer_filter = ""
        
        # Messages
        self.message = ""
        self.message_type = "info"
        self.message_timer = None
        
        # Initialize colors
        self.init_colors()
        
        # Hide cursor
        curses.curs_set(0)
        
        # Start background tasks
        self.running = True
        self.start_background_tasks()
        
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
        """Start background monitoring tasks"""
        def monitor_servers():
            while self.running:
                for port, server in list(self.servers.items()):
                    if server.is_running() and server.process.stdout:
                        try:
                            # Non-blocking read
                            line = server.process.stdout.readline()
                            if line:
                                decoded = line.decode('utf-8').strip()
                                server.add_log(decoded)
                                # Extract admin token
                                if "MCP Admin Token" in decoded and ":" in decoded:
                                    token = decoded.split(":")[-1].strip()
                                    server.admin_token = token
                        except:
                            pass
                time.sleep(0.1)
                
        thread = threading.Thread(target=monitor_servers, daemon=True)
        thread.start()
        
    def run(self):
        """Main event loop"""
        try:
            while True:
                self.draw_screen()
                key = self.stdscr.getch()
                
                if not self.handle_input(key):
                    break
        finally:
            self.cleanup()
            
    def draw_screen(self):
        """Draw the current screen"""
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()
        
        # Draw header
        self.draw_header(width)
        
        # Draw main content based on current screen
        content_start = 2
        content_height = height - 4
        
        if self.current_screen == "main_menu":
            self.draw_main_menu(content_start, content_height, width)
        elif self.current_screen == "server_dashboard":
            self.draw_server_dashboard(content_start, content_height, width)
        elif self.current_screen == "quick_launch":
            self.draw_quick_launch(content_start, content_height, width)
        elif self.current_screen == "project_browser":
            self.draw_project_browser(content_start, content_height, width)
        elif self.current_screen == "data_explorer":
            self.draw_data_explorer(content_start, content_height, width)
        elif self.current_screen == "database_tools":
            self.draw_database_tools(content_start, content_height, width)
        elif self.current_screen == "settings":
            self.draw_settings(content_start, content_height, width)
        elif self.current_screen == "help":
            self.draw_help(content_start, content_height, width)
        elif self.current_screen == "server_details":
            self.draw_server_details(content_start, content_height, width)
        elif self.current_screen == "launch_config":
            self.draw_launch_config(content_start, content_height, width)
            
        # Draw footer
        self.draw_footer(height - 1, width)
        
        # Draw message if any
        if self.message:
            self.draw_message(height - 2, width)
            
        self.stdscr.refresh()
        
    def draw_header(self, width: int):
        """Draw the header bar"""
        header = "🚀 Agent MCP Control Center"
        
        # Add breadcrumb
        breadcrumb = self.get_breadcrumb()
        if breadcrumb:
            header += f" > {breadcrumb}"
            
        # Center the header
        padding = (width - len(header)) // 2
        
        self.stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
        self.stdscr.addstr(0, padding, header)
        self.stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
        
        # Add server count on the right
        if self.servers:
            running = sum(1 for s in self.servers.values() if s.is_running())
            status = f"[{running} servers running]"
            self.stdscr.attron(curses.color_pair(3))
            self.stdscr.addstr(0, width - len(status) - 2, status)
            self.stdscr.attroff(curses.color_pair(3))
            
    def get_breadcrumb(self):
        """Get breadcrumb for current screen"""
        breadcrumbs = {
            "server_dashboard": "Server Dashboard",
            "quick_launch": "Quick Launch",
            "project_browser": "Project Browser",
            "data_explorer": "Data Explorer",
            "database_tools": "Database Tools",
            "settings": "Settings",
            "help": "Documentation",
            "server_details": "Server Details",
            "launch_config": "Launch Configuration"
        }
        return breadcrumbs.get(self.current_screen, "")
        
    def draw_main_menu(self, y: int, height: int, width: int):
        """Draw the main menu"""
        # Center the menu box
        box_width = min(70, width - 10)
        box_height = min(20, height - 4)
        start_x = (width - box_width) // 2
        start_y = y + (height - box_height) // 2
        
        # Draw box
        self.draw_box(start_x, start_y, box_width, box_height)
        
        # Title
        title = " 🚀 Agent MCP Control Center "
        title_x = start_x + (box_width - len(title)) // 2
        self.stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
        self.stdscr.addstr(start_y, title_x, title)
        self.stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
        
        # Menu items
        menu_items = [
            ("1", "📊 Server Dashboard", "Manage running servers"),
            ("2", "⚡ Quick Launch", "Start server in current directory"),
            ("3", "📁 Project Browser", "Browse & initialize projects"),
            ("4", "🔍 Data Explorer", "View agents, tasks, context"),
            ("5", "🗄️ Database Tools", "Migrations, backups, health"),
            ("6", "⚙️ Settings", "Configure MCP defaults"),
            ("7", "📚 Documentation", "View help & examples"),
            ("8", "🚪 Exit", "Close control center")
        ]
        
        item_y = start_y + 3
        for i, (num, title, desc) in enumerate(menu_items):
            if i == self.selected_index:
                # Highlight selected item
                self.stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
                self.stdscr.addstr(item_y, start_x + 3, f"[{num}] {title}")
                self.stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
                
                # Show description
                self.stdscr.attron(curses.color_pair(3))
                desc_x = start_x + 8
                self.stdscr.addstr(item_y, desc_x + len(f"[{num}] {title}"), f" - {desc}")
                self.stdscr.attroff(curses.color_pair(3))
            else:
                self.stdscr.addstr(item_y, start_x + 3, f"[{num}] {title}")
                self.stdscr.addstr(item_y, start_x + 8 + len(f"[{num}] {title}"), 
                                 f" - {desc}", curses.A_DIM)
            item_y += 1
            
        # Instructions
        inst_y = start_y + box_height - 2
        instructions = "Select option (1-8) or use ↑↓ + Enter"
        inst_x = start_x + (box_width - len(instructions)) // 2
        self.stdscr.attron(curses.color_pair(5))
        self.stdscr.addstr(inst_y, inst_x, instructions)
        self.stdscr.attroff(curses.color_pair(5))
        
    def draw_server_dashboard(self, y: int, height: int, width: int):
        """Draw server dashboard"""
        # Title
        self.stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
        self.stdscr.addstr(y, 2, "📊 Running Servers")
        self.stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)
        y += 1
        
        self.stdscr.addstr(y, 2, "─" * (width - 4), curses.color_pair(6) | curses.A_DIM)
        y += 2
        
        if not self.servers:
            # Empty state
            empty_msg = [
                "No servers currently running.",
                "",
                "Press 'n' to launch a new server",
                "or '2' for Quick Launch"
            ]
            
            msg_y = y + (height - y - len(empty_msg)) // 2
            for msg in empty_msg:
                msg_x = (width - len(msg)) // 2
                if "Press" in msg:
                    self.stdscr.attron(curses.color_pair(1))
                    self.stdscr.addstr(msg_y, msg_x, msg)
                    self.stdscr.attroff(curses.color_pair(1))
                else:
                    self.stdscr.addstr(msg_y, msg_x, msg, curses.A_DIM)
                msg_y += 1
        else:
            # Server list
            server_list = list(self.servers.items())
            visible = min(len(server_list), height - y - 4)
            
            for i in range(visible):
                idx = self.scroll_offset + i
                if idx >= len(server_list):
                    break
                    
                port, server = server_list[idx]
                is_selected = idx == self.selected_index
                
                # Draw server box
                if is_selected:
                    self.draw_server_item(y + i * 3, width, server, port, True)
                else:
                    self.draw_server_item(y + i * 3, width, server, port, False)
                    
    def draw_server_item(self, y: int, width: int, server: ServerProcess, 
                         port: int, selected: bool):
        """Draw a single server item"""
        box_color = curses.color_pair(2) if selected else curses.color_pair(6)
        
        # Status
        status = "●" if server.is_running() else "○"
        status_color = curses.color_pair(1) if server.is_running() else curses.color_pair(4)
        
        # Draw selection indicator
        if selected:
            self.stdscr.attron(curses.color_pair(2))
            self.stdscr.addstr(y, 2, "▶")
            self.stdscr.attroff(curses.color_pair(2))
            
        # Status dot
        self.stdscr.attron(status_color | curses.A_BOLD)
        self.stdscr.addstr(y, 5, status)
        self.stdscr.attroff(status_color | curses.A_BOLD)
        
        # Server info
        self.stdscr.attron(curses.A_BOLD)
        self.stdscr.addstr(y, 8, server.name)
        self.stdscr.attroff(curses.A_BOLD)
        
        info = f" (:{port}) - Uptime: {server.get_uptime()}"
        self.stdscr.addstr(y, 8 + len(server.name), info)
        
        # Token on next line
        if server.admin_token:
            self.stdscr.attron(curses.color_pair(3))
            token_display = f"🔑 {server.admin_token}"
            if len(token_display) > width - 10:
                token_display = f"🔑 {server.admin_token[:width-15]}..."
            self.stdscr.addstr(y + 1, 8, token_display)
            self.stdscr.attroff(curses.color_pair(3))
            
    def draw_quick_launch(self, y: int, height: int, width: int):
        """Draw quick launch screen"""
        # Get current directory info
        current_dir = Path.cwd()
        has_agent = (current_dir / ".agent").exists()
        
        # Center the content
        box_width = min(60, width - 10)
        box_height = 15
        start_x = (width - box_width) // 2
        start_y = y + (height - box_height) // 2
        
        # Draw box
        self.draw_box(start_x, start_y, box_width, box_height)
        
        # Title
        title = " ⚡ Quick Launch "
        self.stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
        self.stdscr.addstr(start_y, start_x + (box_width - len(title)) // 2, title)
        self.stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)
        
        y = start_y + 2
        x = start_x + 3
        
        # Current directory
        self.stdscr.attron(curses.A_BOLD)
        self.stdscr.addstr(y, x, "Current Directory:")
        self.stdscr.attroff(curses.A_BOLD)
        y += 1
        
        dir_str = str(current_dir)
        if len(dir_str) > box_width - 6:
            dir_str = "..." + dir_str[-(box_width - 9):]
        self.stdscr.addstr(y, x + 2, dir_str)
        y += 1
        
        # Status
        if has_agent:
            self.stdscr.attron(curses.color_pair(1))
            self.stdscr.addstr(y, x + 2, "✓ MCP Project Ready")
            self.stdscr.attroff(curses.color_pair(1))
        else:
            self.stdscr.attron(curses.color_pair(4))
            self.stdscr.addstr(y, x + 2, "⚠ Not an MCP project")
            self.stdscr.attroff(curses.color_pair(4))
        y += 2
        
        # Port selection
        self.stdscr.addstr(y, x, "Port: ")
        port = self.find_available_port()
        self.stdscr.attron(curses.color_pair(1))
        self.stdscr.addstr(y, x + 6, str(port))
        self.stdscr.attroff(curses.color_pair(1))
        y += 3
        
        # Actions
        actions = []
        if has_agent:
            actions.append(("[L]", "Launch Server", 0))
        else:
            actions.append(("[I]", "Initialize & Launch", 0))
            actions.append(("[B]", "Browse for Project", 1))
            
        for i, (key, desc, idx) in enumerate(actions):
            if idx == self.selected_index:
                self.stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
                self.stdscr.addstr(y + i, x, f"{key} {desc}")
                self.stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
            else:
                self.stdscr.attron(curses.color_pair(5))
                self.stdscr.addstr(y + i, x, key)
                self.stdscr.attroff(curses.color_pair(5))
                self.stdscr.addstr(y + i, x + len(key) + 1, desc)
                
    def draw_project_browser(self, y: int, height: int, width: int):
        """Draw project browser"""
        # Title and path
        self.stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
        self.stdscr.addstr(y, 2, "📁 Project Browser")
        self.stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)
        y += 1
        
        # Current path
        path_str = str(self.browser_path)
        if len(path_str) > width - 10:
            path_parts = path_str.split('/')
            if len(path_parts) > 3:
                path_str = f"/{path_parts[1]}/.../{path_parts[-1]}"
                
        self.stdscr.addstr(y, 2, f"📍 {path_str}", curses.color_pair(6))
        y += 1
        
        self.stdscr.addstr(y, 2, "─" * (width - 4), curses.color_pair(6) | curses.A_DIM)
        y += 2
        
        # Load items if needed
        if not self.browser_items:
            self.load_browser_items()
            
        # Directory listing
        visible = min(height - y - 2, len(self.browser_items))
        
        for i in range(visible):
            idx = self.scroll_offset + i
            if idx >= len(self.browser_items):
                break
                
            item = self.browser_items[idx]
            is_selected = idx == self.selected_index
            
            self.draw_browser_item(y + i, width, item, is_selected)
            
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
                
                # Get project info
                try:
                    # Count agents and tasks if possible
                    db_path = item / ".agent" / "agent_data.db"
                    if db_path.exists():
                        self.stdscr.attron(curses.color_pair(1))
                        self.stdscr.addstr(y, x + 3 + len(item.name) + 2, "[MCP Project]")
                        self.stdscr.attroff(curses.color_pair(1))
                except:
                    pass
            else:
                # Regular directory
                self.stdscr.attron(curses.color_pair(7))
                self.stdscr.addstr(y, x, "📁 ")
                self.stdscr.addstr(y, x + 3, item.name)
                self.stdscr.attroff(curses.color_pair(7))
                
    def draw_data_explorer(self, y: int, height: int, width: int):
        """Draw data explorer"""
        if not self.current_server_port:
            # Need to select a server first
            self.draw_server_selector(y, height, width)
        else:
            # Show data options
            self.draw_data_options(y, height, width)
            
    def draw_server_selector(self, y: int, height: int, width: int):
        """Draw server selection for data explorer"""
        self.stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
        self.stdscr.addstr(y, 2, "Select a server to explore:")
        self.stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)
        y += 2
        
        if not self.servers:
            self.stdscr.addstr(y, 4, "No servers running", curses.A_DIM)
            self.stdscr.addstr(y + 2, 4, "Launch a server first", curses.A_DIM)
        else:
            for i, (port, server) in enumerate(self.servers.items()):
                if not server.is_running():
                    continue
                    
                is_selected = i == self.selected_index
                
                if is_selected:
                    self.stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
                    self.stdscr.addstr(y + i, 2, f"▶ {server.name} (:{port})")
                    self.stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
                else:
                    self.stdscr.addstr(y + i, 4, f"{server.name} (:{port})")
                    
    def draw_data_options(self, y: int, height: int, width: int):
        """Draw data explorer options"""
        server = self.servers.get(self.current_server_port)
        if not server:
            self.current_server_port = None
            return
            
        # Header
        self.stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
        self.stdscr.addstr(y, 2, f"🔍 Data Explorer: {server.name}")
        self.stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)
        y += 2
        
        # Options
        options = [
            ("A", "👥 Agents", "View all agents & tokens"),
            ("T", "📋 Tasks", "Browse and filter tasks"),
            ("C", "🗂️ Context", "Explore context entries"),
            ("S", "🔍 Search", "Search across all data")
        ]
        
        for i, (key, title, desc) in enumerate(options):
            is_selected = i == self.selected_index
            
            if is_selected:
                self.stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
                self.stdscr.addstr(y + i * 2, 2, f"[{key}] {title}")
                self.stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
                self.stdscr.attron(curses.color_pair(3))
                self.stdscr.addstr(y + i * 2, 20, desc)
                self.stdscr.attroff(curses.color_pair(3))
            else:
                self.stdscr.attron(curses.color_pair(5))
                self.stdscr.addstr(y + i * 2, 2, f"[{key}]")
                self.stdscr.attroff(curses.color_pair(5))
                self.stdscr.addstr(y + i * 2, 6, f" {title}")
                self.stdscr.addstr(y + i * 2, 20, desc, curses.A_DIM)
                
    def draw_database_tools(self, y: int, height: int, width: int):
        """Draw database tools"""
        self.stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
        self.stdscr.addstr(y, 2, "🗄️ Database Tools")
        self.stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)
        y += 2
        
        # Get migration status
        try:
            mm = MigrationManager()
            current_version = mm.get_current_version()
            latest_version = mm.get_latest_version()
            needs_migration = current_version != latest_version
        except:
            current_version = "Unknown"
            latest_version = "Unknown"
            needs_migration = False
            
        # Status box
        status_lines = [
            f"Current Version: {current_version}",
            f"Latest Version: {latest_version}",
            f"Status: {'⚠️ Migration needed' if needs_migration else '✓ Up to date'}"
        ]
        
        for line in status_lines:
            if "⚠️" in line:
                self.stdscr.attron(curses.color_pair(4))
                self.stdscr.addstr(y, 4, line)
                self.stdscr.attroff(curses.color_pair(4))
            elif "✓" in line:
                self.stdscr.attron(curses.color_pair(1))
                self.stdscr.addstr(y, 4, line)
                self.stdscr.attroff(curses.color_pair(1))
            else:
                self.stdscr.addstr(y, 4, line)
            y += 1
        y += 2
        
        # Tools
        tools = [
            ("M", "Run Migrations", "Apply pending database migrations"),
            ("B", "Backup Database", "Create a backup of current data"),
            ("R", "Restore Backup", "Restore from a previous backup"),
            ("L", "View Logs", "See migration history"),
            ("C", "Check Health", "Verify database integrity")
        ]
        
        for i, (key, title, desc) in enumerate(tools):
            is_selected = i == self.selected_index
            
            if is_selected:
                self.stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
                self.stdscr.addstr(y + i * 2, 2, f"[{key}] {title}")
                self.stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
                self.stdscr.attron(curses.color_pair(3))
                self.stdscr.addstr(y + i * 2 + 1, 6, desc)
                self.stdscr.attroff(curses.color_pair(3))
            else:
                self.stdscr.attron(curses.color_pair(5))
                self.stdscr.addstr(y + i * 2, 2, f"[{key}]")
                self.stdscr.attroff(curses.color_pair(5))
                self.stdscr.addstr(y + i * 2, 6, title)
                self.stdscr.addstr(y + i * 2 + 1, 6, desc, curses.A_DIM)
                
    def draw_box(self, x: int, y: int, width: int, height: int, 
                 color: int = None):
        """Draw a box with unicode characters"""
        if color:
            self.stdscr.attron(color)
            
        # Corners
        self.stdscr.addstr(y, x, "╔")
        self.stdscr.addstr(y, x + width - 1, "╗")
        self.stdscr.addstr(y + height - 1, x, "╚")
        self.stdscr.addstr(y + height - 1, x + width - 1, "╝")
        
        # Horizontal lines
        for i in range(1, width - 1):
            self.stdscr.addstr(y, x + i, "═")
            self.stdscr.addstr(y + height - 1, x + i, "═")
            
        # Vertical lines
        for i in range(1, height - 1):
            self.stdscr.addstr(y + i, x, "║")
            self.stdscr.addstr(y + i, x + width - 1, "║")
            
        if color:
            self.stdscr.attroff(color)
            
    def draw_footer(self, y: int, width: int):
        """Draw footer with context-sensitive controls"""
        controls = self.get_controls()
        
        # Format controls
        if isinstance(controls, dict):
            control_str = " | ".join([f"{k}: {v}" for k, v in controls.items()])
            if len(control_str) > width - 4:
                # Show only essential controls
                essential = list(controls.items())[:3]
                control_str = " | ".join([f"{k}: {v}" for k, v in essential]) + " | ..."
        else:
            control_str = "Use arrow keys to navigate"
            
        # Center the controls
        x = max(0, (width - len(control_str)) // 2)
        
        try:
            self.stdscr.attron(curses.color_pair(5))
            self.stdscr.addstr(y, x, control_str[:width-1])
            self.stdscr.attroff(curses.color_pair(5))
        except curses.error:
            pass  # Ignore if we can't draw at this position
        
    def get_controls(self):
        """Get context-sensitive controls"""
        base_controls = {"q": "Back", "↑↓": "Navigate"}
        
        screen_controls = {
            "main_menu": {"Enter": "Select", "1-8": "Quick Select", "q": "Exit"},
            "server_dashboard": {"n": "New", "Enter": "View", "s": "Stop", "r": "Restart", 
                               "c": "Copy Token"},
            "quick_launch": {"l": "Launch", "i": "Initialize", "b": "Browse"},
            "project_browser": {"Enter": "Open/Select", "i": "Initialize", "l": "Launch"},
            "data_explorer": {"Enter": "Select", "a/t/c/s": "Quick Jump"},
            "database_tools": {"Enter": "Execute", "m": "Migrate", "b": "Backup"},
            "settings": {"Enter": "Edit", "s": "Save"},
            "help": {"↑↓": "Scroll", "PgUp/PgDn": "Page"}
        }
        
        return screen_controls.get(self.current_screen, base_controls)
        
    def handle_input(self, key: int) -> bool:
        """Handle keyboard input, return False to exit"""
        # Global keys
        if key == ord('q') or key == ord('Q'):
            if self.current_screen == "main_menu":
                return self.confirm_exit()
            else:
                self.go_back()
                return True
                
        # Navigation
        if key == curses.KEY_UP or key == ord('k'):
            self.move_selection(-1)
        elif key == curses.KEY_DOWN or key == ord('j'):
            self.move_selection(1)
        elif key == curses.KEY_LEFT or key == ord('h'):
            self.go_back()
        elif key == curses.KEY_RIGHT or key == ord('l') or key == 10:  # Enter
            self.handle_selection()
            
        # Screen-specific keys
        self.handle_screen_keys(key)
        
        return True
        
    def handle_screen_keys(self, key: int):
        """Handle screen-specific keyboard shortcuts"""
        if self.current_screen == "main_menu":
            # Number shortcuts
            if ord('1') <= key <= ord('8'):
                self.selected_index = key - ord('1')
                self.handle_selection()
                
        elif self.current_screen == "server_dashboard":
            if key == ord('n') or key == ord('N'):
                self.change_screen("project_browser")
            elif key == ord('s') or key == ord('S'):
                self.stop_selected_server()
            elif key == ord('r') or key == ord('R'):
                self.restart_selected_server()
            elif key == ord('c') or key == ord('C'):
                self.copy_admin_token()
                
        elif self.current_screen == "quick_launch":
            if key == ord('l') or key == ord('L'):
                self.quick_launch_server()
            elif key == ord('i') or key == ord('I'):
                self.initialize_and_launch()
            elif key == ord('b') or key == ord('B'):
                self.change_screen("project_browser")
                
        elif self.current_screen == "project_browser":
            if key == ord('i') or key == ord('I'):
                self.initialize_selected_project()
            elif key == ord('l') or key == ord('L'):
                self.launch_from_browser()
                
    def handle_selection(self):
        """Handle enter key press"""
        if self.current_screen == "main_menu":
            options = [
                "server_dashboard",
                "quick_launch", 
                "project_browser",
                "data_explorer",
                "database_tools",
                "settings",
                "help",
                None  # Exit
            ]
            
            if 0 <= self.selected_index < len(options):
                if options[self.selected_index]:
                    self.change_screen(options[self.selected_index])
                else:
                    return self.confirm_exit()
                    
        elif self.current_screen == "project_browser":
            if 0 <= self.selected_index < len(self.browser_items):
                item = self.browser_items[self.selected_index]
                if item.is_dir():
                    if (item / ".agent").exists():
                        # Launch from this project
                        self.launch_from_path(item)
                    else:
                        # Navigate into directory
                        self.browser_path = item
                        self.load_browser_items()
                        self.selected_index = 0
                        
    def change_screen(self, new_screen: str):
        """Change to a new screen"""
        self.previous_screen = self.current_screen
        self.current_screen = new_screen
        self.selected_index = 0
        self.scroll_offset = 0
        
        # Screen-specific initialization
        if new_screen == "project_browser":
            self.browser_path = Path.cwd()
            self.load_browser_items()
            
    def go_back(self):
        """Go back to previous screen"""
        if self.previous_screen:
            self.current_screen, self.previous_screen = self.previous_screen, self.current_screen
            self.selected_index = 0
        elif self.current_screen != "main_menu":
            self.change_screen("main_menu")
            
    def move_selection(self, delta: int):
        """Move selection up or down"""
        max_items = self.get_max_items()
        if max_items > 0:
            self.selected_index = max(0, min(self.selected_index + delta, max_items - 1))
            
    def get_max_items(self) -> int:
        """Get maximum number of items for current screen"""
        if self.current_screen == "main_menu":
            return 8
        elif self.current_screen == "server_dashboard":
            return len(self.servers)
        elif self.current_screen == "project_browser":
            return len(self.browser_items)
        elif self.current_screen == "data_explorer":
            return 4 if self.current_server_port else len(self.servers)
        elif self.current_screen == "database_tools":
            return 5
        return 0
        
    def find_available_port(self) -> int:
        """Find next available port"""
        port = 8080
        while port in self.servers:
            port += 1
        return port
        
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
            
    def quick_launch_server(self):
        """Quick launch in current directory"""
        current_dir = Path.cwd()
        if not (current_dir / ".agent").exists():
            self.show_message("Not an MCP project. Initialize first.", "error")
            return
            
        port = self.find_available_port()
        self.launch_server(current_dir, port)
        
    def initialize_and_launch(self):
        """Initialize project and launch"""
        current_dir = Path.cwd()
        
        self.show_message("Initializing project...", "info")
        self.stdscr.refresh()
        
        try:
            init_agent_directory(str(current_dir))
            self.show_message("Project initialized!", "success")
            
            # Now launch
            port = self.find_available_port()
            self.launch_server(current_dir, port)
        except Exception as e:
            self.show_message(f"Failed to initialize: {str(e)}", "error")
            
    def launch_from_path(self, path: Path):
        """Launch server from specific path"""
        port = self.find_available_port()
        self.launch_server(path, port)
        
    def launch_server(self, project_dir: Path, port: int):
        """Launch a new server"""
        cmd = [
            sys.executable, "-m", "agent_mcp.cli_main", "server",
            "--port", str(port),
            "--project-dir", str(project_dir),
            "--no-tui"
        ]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                universal_newlines=False,
                preexec_fn=os.setsid if sys.platform != 'win32' else None
            )
            
            server = ServerProcess(str(project_dir), port, process)
            self.servers[port] = server
            
            self.show_message(f"Server launched on port {port}", "success")
            self.change_screen("server_dashboard")
            
        except Exception as e:
            self.show_message(f"Failed to launch: {str(e)}", "error")
            
    def copy_admin_token(self):
        """Copy selected server's admin token"""
        if not self.servers:
            return
            
        ports = list(self.servers.keys())
        if 0 <= self.selected_index < len(ports):
            server = self.servers[ports[self.selected_index]]
            if server.admin_token:
                try:
                    pyperclip.copy(server.admin_token)
                    self.show_message("Admin token copied!", "success")
                except Exception as e:
                    self.show_message(f"Copy failed: {str(e)}", "error")
            else:
                self.show_message("No token available yet", "error")
                
    def show_message(self, message: str, msg_type: str = "info"):
        """Show a temporary message"""
        self.message = message
        self.message_type = msg_type
        
        # Clear after 3 seconds
        if self.message_timer:
            self.message_timer.cancel()
            
        def clear():
            self.message = ""
            
        self.message_timer = threading.Timer(3.0, clear)
        self.message_timer.daemon = True
        self.message_timer.start()
        
    def draw_message(self, y: int, width: int):
        """Draw message"""
        if not self.message:
            return
            
        color_map = {
            "success": curses.color_pair(1),
            "error": curses.color_pair(4),
            "info": curses.color_pair(3)
        }
        
        color = color_map.get(self.message_type, curses.color_pair(6))
        
        # Center the message
        x = (width - len(self.message)) // 2
        
        self.stdscr.attron(color | curses.A_BOLD)
        self.stdscr.addstr(y, x, self.message)
        self.stdscr.attroff(color | curses.A_BOLD)
        
    def confirm_exit(self) -> bool:
        """Confirm before exiting"""
        if any(s.is_running() for s in self.servers.values()):
            # Show confirmation
            height, width = self.stdscr.getmaxyx()
            y = height // 2
            
            msg = "Servers are still running. Really exit? (y/n)"
            x = (width - len(msg)) // 2
            
            self.stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
            self.stdscr.addstr(y, x, msg)
            self.stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
            self.stdscr.refresh()
            
            key = self.stdscr.getch()
            return key in [ord('y'), ord('Y')]
        return True
        
    def cleanup(self):
        """Cleanup on exit"""
        self.running = False
        for server in self.servers.values():
            if server.is_running():
                server.stop()
                
    def stop_selected_server(self):
        """Stop the selected server"""
        if not self.servers:
            return
            
        ports = list(self.servers.keys())
        if 0 <= self.selected_index < len(ports):
            server = self.servers[ports[self.selected_index]]
            if server.is_running():
                server.stop()
                self.show_message("Server stopped", "success")
                
    def restart_selected_server(self):
        """Restart selected server"""
        if not self.servers:
            return
            
        ports = list(self.servers.keys())
        if 0 <= self.selected_index < len(ports):
            port = ports[self.selected_index]
            server = self.servers[port]
            
            # Stop if running
            if server.is_running():
                server.stop()
                time.sleep(1)
                
            # Restart
            self.launch_server(Path(server.project_dir), port)
            self.show_message("Server restarted", "success")


def run_unified_interface():
    """Entry point for unified interface"""
    try:
        wrapper(lambda stdscr: UnifiedMCPInterface(stdscr).run())
    except KeyboardInterrupt:
        pass
    except curses.error as e:
        logger.error(f"Curses error: {e}", exc_info=True)
        click.echo(f"Terminal error: {str(e)}")
        click.echo("Try running in a different terminal or with --no-tui option")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unified interface error: {e}", exc_info=True)
        click.echo(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)