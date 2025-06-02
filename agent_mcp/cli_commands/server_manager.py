"""
Agent MCP Server Manager - A tmux-like interface for managing multiple MCP servers
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
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import curses
from curses import wrapper
import pyperclip
import click
import logging
import traceback

from ..core.config import logger
from ..db.connection import get_db_connection
from ..utils.project_utils import init_agent_directory

# Set up enhanced logging for the server manager
manager_logger = logging.getLogger('agent_mcp.cli.server_manager')
manager_logger.setLevel(logging.DEBUG)

# Add file handler for manager-specific logs
manager_log_file = 'agent_mcp_manager.log'
manager_file_handler = logging.FileHandler(manager_log_file, mode='a')
manager_file_handler.setLevel(logging.DEBUG)
manager_formatter = logging.Formatter(
    '%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s - %(funcName)s:%(lineno)d - %(message)s',
    datefmt='%H:%M:%S'
)
manager_file_handler.setFormatter(manager_formatter)
manager_logger.addHandler(manager_file_handler)

manager_logger.info("=" * 80)
manager_logger.info("SERVER MANAGER MODULE LOADED")
manager_logger.info("=" * 80)


class ServerProcess:
    """Represents a running MCP server"""
    def __init__(self, project_dir: str, port: int, process: subprocess.Popen):
        manager_logger.info(f"Creating ServerProcess: project_dir={project_dir}, port={port}, PID={process.pid}")
        self.project_dir = project_dir
        self.port = port
        self.process = process
        self.name = Path(project_dir).name
        self.start_time = datetime.now()
        self.admin_token = None
        self.logs = []
        self.max_logs = 1000
        manager_logger.debug(f"ServerProcess initialized: name={self.name}, start_time={self.start_time}")
        
    def is_running(self):
        """Check if server is still running"""
        status = self.process.poll() is None
        manager_logger.debug(f"Server {self.name} on port {self.port} is_running: {status}")
        return status
        
    def get_uptime(self):
        """Get server uptime"""
        if self.is_running():
            delta = datetime.now() - self.start_time
            hours, remainder = divmod(delta.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return "Stopped"
        
    def add_log(self, line: str):
        """Add log line"""
        self.logs.append((datetime.now(), line))
        if len(self.logs) > self.max_logs:
            self.logs.pop(0)
            
    def stop(self):
        """Stop the server"""
        if self.is_running():
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()


class ServerManager:
    """Main server manager application"""
    
    def __init__(self, stdscr):
        manager_logger.info("Initializing ServerManager")
        self.stdscr = stdscr
        self.servers: Dict[int, ServerProcess] = {}  # port -> ServerProcess
        self.current_mode = "dashboard"  # dashboard, browser, server_view, launch
        self.selected_index = 0
        self.scroll_offset = 0
        self.current_server_port = None
        self.browser_path = Path.home()
        self.browser_items = []
        self.launch_config = {
            "project_dir": None,
            "port": 8080,
            "init_project": False
        }
        self.message = ""
        self.message_type = "info"
        
        manager_logger.debug("Setting up color pairs")
        # Initialize colors
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)   # Success/Header
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Selected
        curses.init_pair(3, curses.COLOR_CYAN, curses.COLOR_BLACK)    # Info
        curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)     # Error
        curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK) # Keys
        curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_BLACK)   # Normal
        curses.init_pair(7, curses.COLOR_BLUE, curses.COLOR_BLACK)    # Directory
        
        # Hide cursor
        curses.curs_set(0)
        manager_logger.debug(f"Terminal size: {curses.LINES}x{curses.COLS}")
        
        # Start log reader threads
        self.running = True
        manager_logger.info("Starting log reader threads")
        self.start_log_readers()
        
        manager_logger.info("ServerManager initialization complete")
        
    def start_log_readers(self):
        """Start threads to read server logs"""
        def read_logs():
            while self.running:
                for port, server in list(self.servers.items()):
                    if server.is_running():
                        try:
                            line = server.process.stdout.readline()
                            if line:
                                server.add_log(line.decode('utf-8').strip())
                                # Extract admin token if present
                                if "MCP Admin Token" in line.decode('utf-8'):
                                    parts = line.decode('utf-8').split(":")
                                    if len(parts) > 1:
                                        server.admin_token = parts[-1].strip()
                        except:
                            pass
                time.sleep(0.1)
                
        thread = threading.Thread(target=read_logs, daemon=True)
        thread.start()
        
    def run(self):
        """Main loop"""
        try:
            while True:
                self.refresh_screen()
                key = self.stdscr.getch()
                
                if key == ord('q') or key == ord('Q'):
                    if self.current_mode == "dashboard":
                        if self.confirm_quit():
                            break
                    else:
                        self.current_mode = "dashboard"
                        self.selected_index = 0
                        self.scroll_offset = 0
                elif key == curses.KEY_UP or key == ord('k'):
                    self.move_selection(-1)
                elif key == curses.KEY_DOWN or key == ord('j'):
                    self.move_selection(1)
                elif key == curses.KEY_LEFT or key == ord('h'):
                    self.handle_back()
                elif key == curses.KEY_RIGHT or key == ord('l') or key == 10:  # Enter
                    self.handle_selection()
                elif key == ord('n') or key == ord('N'):
                    if self.current_mode == "dashboard":
                        self.current_mode = "browser"
                        self.browser_path = Path.home()
                        self.load_browser_items()
                elif key == ord('s') or key == ord('S'):
                    if self.current_mode == "dashboard" and self.servers:
                        self.stop_selected_server()
                elif key == ord('r') or key == ord('R'):
                    if self.current_mode == "dashboard" and self.servers:
                        self.restart_selected_server()
                elif key == ord('c') or key == ord('C'):
                    self.copy_to_clipboard()
                elif key == ord('i') or key == ord('I'):
                    if self.current_mode == "launch":
                        self.launch_config["init_project"] = not self.launch_config["init_project"]
                elif key == ord('p') or key == ord('P'):
                    if self.current_mode == "launch":
                        self.enter_port_selection()
                elif key == ord('L'):
                    if self.current_mode == "launch":
                        self.launch_server()
                elif key == ord('\t'):  # Tab to switch servers
                    if self.current_mode == "server_view":
                        self.switch_to_next_server()
                        
        finally:
            self.running = False
            self.cleanup()
            
    def refresh_screen(self):
        """Refresh the display"""
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()
        
        # Draw header
        self.draw_header(width)
        
        # Draw main content
        if self.current_mode == "dashboard":
            self.draw_dashboard(height, width)
        elif self.current_mode == "browser":
            self.draw_browser(height, width)
        elif self.current_mode == "server_view":
            self.draw_server_view(height, width)
        elif self.current_mode == "launch":
            self.draw_launch_config(height, width)
            
        # Draw footer
        self.draw_footer(height - 1, width)
        
        # Draw message if any
        if self.message:
            self.draw_message(height - 2, width)
            
        self.stdscr.refresh()
        
    def draw_header(self, width: int):
        """Draw header"""
        header = "🚀 Agent MCP Server Manager"
        mode_text = f" [{self.current_mode.replace('_', ' ').title()}]"
        
        self.stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
        self.stdscr.addstr(0, (width - len(header) - len(mode_text)) // 2, header)
        self.stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
        
        self.stdscr.attron(curses.color_pair(3))
        self.stdscr.addstr(0, (width - len(header) - len(mode_text)) // 2 + len(header), mode_text)
        self.stdscr.attroff(curses.color_pair(3))
        
    def draw_dashboard(self, height: int, width: int):
        """Draw main dashboard"""
        y = 2
        
        # Welcome box
        if not self.servers:
            # Draw welcome screen
            welcome_lines = [
                "╔═══════════════════════════════════════════════════╗",
                "║       Welcome to Agent MCP Server Manager!        ║",
                "║                                                   ║",
                "║   Manage multiple MCP servers from one place     ║",
                "║                                                   ║",
                "║   Press 'n' to launch your first server          ║",
                "╚═══════════════════════════════════════════════════╝"
            ]
            
            start_y = (height - len(welcome_lines)) // 2
            for i, line in enumerate(welcome_lines):
                x = (width - len(line)) // 2
                if i == 0 or i == len(welcome_lines) - 1:
                    self.stdscr.attron(curses.color_pair(3))
                    self.stdscr.addstr(start_y + i, x, line)
                    self.stdscr.attroff(curses.color_pair(3))
                elif "Press 'n'" in line:
                    self.stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
                    self.stdscr.addstr(start_y + i, x, line)
                    self.stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
                else:
                    self.stdscr.addstr(start_y + i, x, line)
            return
            
        # Running servers section with better formatting
        self.stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
        self.stdscr.addstr(y, 2, "📊 Running Servers")
        self.stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)
        
        # Draw separator line
        y += 1
        self.stdscr.addstr(y, 2, "─" * (width - 4), curses.color_pair(6) | curses.A_DIM)
        y += 2
        
        server_list = list(self.servers.items())
        for i, (port, server) in enumerate(server_list):
            if y >= height - 8:
                break
                
            # Draw box for each server
            is_selected = i == self.selected_index
            box_color = curses.color_pair(2) if is_selected else curses.color_pair(6)
            
            # Server box
            if is_selected:
                self.stdscr.attron(box_color)
                self.stdscr.addstr(y, 2, "┌" + "─" * (width - 6) + "┐")
                self.stdscr.addstr(y + 1, 2, "│")
                self.stdscr.addstr(y + 1, width - 3, "│")
                self.stdscr.addstr(y + 2, 2, "│")
                self.stdscr.addstr(y + 2, width - 3, "│")
                self.stdscr.addstr(y + 3, 2, "└" + "─" * (width - 6) + "┘")
                self.stdscr.attroff(box_color)
                
            # Status indicator
            status = "●" if server.is_running() else "○"
            status_color = curses.color_pair(1) if server.is_running() else curses.color_pair(4)
            
            self.stdscr.attron(status_color | curses.A_BOLD)
            self.stdscr.addstr(y + 1, 5, status)
            self.stdscr.attroff(status_color | curses.A_BOLD)
            
            # Server name and port
            self.stdscr.attron(curses.A_BOLD)
            self.stdscr.addstr(y + 1, 8, f"{server.name}")
            self.stdscr.attroff(curses.A_BOLD)
            self.stdscr.addstr(y + 1, 8 + len(server.name) + 1, f"(port {port})")
            
            # Uptime
            uptime_x = width - 20
            self.stdscr.addstr(y + 1, uptime_x, f"⏱ {server.get_uptime()}")
            
            # Admin token on second line
            if server.admin_token:
                self.stdscr.attron(curses.color_pair(3))
                self.stdscr.addstr(y + 2, 8, f"🔑 Token: {server.admin_token}")
                self.stdscr.attroff(curses.color_pair(3))
            else:
                self.stdscr.addstr(y + 2, 8, "⏳ Waiting for token...", curses.A_DIM)
                
            y += 4
                
        # Quick stats
        y += 2
        self.stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
        self.stdscr.addstr(y, 2, "System Status:")
        self.stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)
        y += 1
        
        # CPU and Memory usage
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        
        self.stdscr.addstr(y, 4, f"CPU: {cpu_percent}% | Memory: {memory.percent}%")
        
    def draw_browser(self, height: int, width: int):
        """Draw file browser"""
        y = 2
        
        # Title
        self.stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
        self.stdscr.addstr(y, 2, "📂 Select Project Directory")
        self.stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)
        y += 1
        
        # Current path with better formatting
        path_str = str(self.browser_path)
        if len(path_str) > width - 10:
            # Show beginning and end
            path_parts = path_str.split('/')
            if len(path_parts) > 3:
                path_str = f"/{path_parts[1]}/.../{path_parts[-1]}"
                
        self.stdscr.attron(curses.color_pair(6))
        self.stdscr.addstr(y, 2, f"📍 {path_str}")
        self.stdscr.attroff(curses.color_pair(6))
        y += 1
        
        # Separator
        self.stdscr.addstr(y, 2, "─" * (width - 4), curses.color_pair(6) | curses.A_DIM)
        y += 2
        
        # Instructions
        if not self.browser_items:
            self.stdscr.addstr(y, 4, "Empty directory", curses.A_DIM)
            return
            
        # Directory listing with better layout
        visible_items = min(height - 10, len(self.browser_items))
        
        for i in range(visible_items):
            item_idx = self.scroll_offset + i
            if item_idx >= len(self.browser_items):
                break
                
            item = self.browser_items[item_idx]
            is_dir = item.is_dir()
            has_agent = (item / ".agent").exists() if is_dir else False
            is_selected = item_idx == self.selected_index
            
            # Selection indicator with box
            if is_selected:
                self.stdscr.attron(curses.color_pair(2))
                self.stdscr.addstr(y + i, 2, "▶")
                self.stdscr.attroff(curses.color_pair(2))
                
            # Icon and name
            x_offset = 5
            if item == self.browser_path.parent and self.browser_path.parent != self.browser_path:
                # Parent directory
                self.stdscr.attron(curses.color_pair(6) | curses.A_DIM)
                self.stdscr.addstr(y + i, x_offset, "⬆️  ..")
                self.stdscr.attroff(curses.color_pair(6) | curses.A_DIM)
            elif is_dir:
                if has_agent:
                    # MCP Project - highlight it
                    self.stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
                    self.stdscr.addstr(y + i, x_offset, "🚀 ")
                    self.stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
                    
                    name_color = curses.color_pair(1)
                    if is_selected:
                        name_color |= curses.A_BOLD
                    self.stdscr.attron(name_color)
                    self.stdscr.addstr(y + i, x_offset + 3, item.name)
                    self.stdscr.attroff(name_color)
                    
                    # Badge
                    self.stdscr.attron(curses.color_pair(1))
                    self.stdscr.addstr(y + i, x_offset + 3 + len(item.name) + 2, "● MCP Project")
                    self.stdscr.attroff(curses.color_pair(1))
                else:
                    # Regular directory
                    self.stdscr.attron(curses.color_pair(7))
                    self.stdscr.addstr(y + i, x_offset, "📁 ")
                    self.stdscr.addstr(y + i, x_offset + 3, item.name)
                    self.stdscr.attroff(curses.color_pair(7))
                    
        # Scroll indicator
        if len(self.browser_items) > visible_items:
            scroll_height = height - 10
            scroll_pos = int((self.scroll_offset / (len(self.browser_items) - visible_items)) * (scroll_height - 1))
            for sy in range(scroll_height):
                if sy == scroll_pos:
                    self.stdscr.addstr(y + sy, width - 3, "█", curses.color_pair(3))
                else:
                    self.stdscr.addstr(y + sy, width - 3, "│", curses.color_pair(6) | curses.A_DIM)
                
    def draw_server_view(self, height: int, width: int):
        """Draw detailed server view"""
        if self.current_server_port not in self.servers:
            self.current_mode = "dashboard"
            return
            
        server = self.servers[self.current_server_port]
        y = 2
        
        # Server info
        self.stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
        self.stdscr.addstr(y, 2, f"Server: {server.name} (Port {self.current_server_port})")
        self.stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)
        y += 1
        
        self.stdscr.addstr(y, 2, f"Project: {server.project_dir}")
        y += 1
        self.stdscr.addstr(y, 2, f"Status: {'Running' if server.is_running() else 'Stopped'}")
        y += 1
        self.stdscr.addstr(y, 2, f"Uptime: {server.get_uptime()}")
        y += 1
        
        if server.admin_token:
            self.stdscr.addstr(y, 2, f"Admin Token: {server.admin_token}")
            y += 1
            
        y += 1
        
        # Logs
        self.stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
        self.stdscr.addstr(y, 2, "Recent Logs:")
        self.stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)
        y += 1
        
        # Show last logs that fit
        log_height = height - y - 3
        start_idx = max(0, len(server.logs) - log_height)
        
        for i, (timestamp, log_line) in enumerate(server.logs[start_idx:]):
            if y + i >= height - 3:
                break
                
            time_str = timestamp.strftime("%H:%M:%S")
            
            # Color based on log content
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
                
            self.stdscr.addstr(y + i, 2, f"{time_str} ", curses.A_DIM)
            self.stdscr.attron(color)
            self.stdscr.addstr(y + i, 11, log_line)
            self.stdscr.attroff(color)
            
    def draw_launch_config(self, height: int, width: int):
        """Draw launch configuration screen"""
        # Center the configuration box
        box_width = min(70, width - 10)
        box_height = 20
        start_x = (width - box_width) // 2
        start_y = (height - box_height) // 2
        
        # Draw box border
        self.stdscr.attron(curses.color_pair(3))
        # Top border
        self.stdscr.addstr(start_y, start_x, "╔" + "═" * (box_width - 2) + "╗")
        # Side borders
        for i in range(1, box_height - 1):
            self.stdscr.addstr(start_y + i, start_x, "║")
            self.stdscr.addstr(start_y + i, start_x + box_width - 1, "║")
        # Bottom border
        self.stdscr.addstr(start_y + box_height - 1, start_x, "╚" + "═" * (box_width - 2) + "╝")
        self.stdscr.attroff(curses.color_pair(3))
        
        # Title
        title = " 🚀 Launch New Server "
        title_x = start_x + (box_width - len(title)) // 2
        self.stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
        self.stdscr.addstr(start_y, title_x, title)
        self.stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)
        
        y = start_y + 3
        x = start_x + 4
        
        # Project directory section
        self.stdscr.attron(curses.A_BOLD)
        self.stdscr.addstr(y, x, "Project Directory")
        self.stdscr.attroff(curses.A_BOLD)
        y += 1
        
        project_str = str(self.launch_config["project_dir"]) if self.launch_config["project_dir"] else "Not selected"
        max_path_width = box_width - 10
        if len(project_str) > max_path_width:
            project_str = "..." + project_str[-(max_path_width - 3):]
            
        if self.launch_config["project_dir"]:
            # Check if it's already an MCP project
            is_mcp = (self.launch_config["project_dir"] / ".agent").exists()
            
            self.stdscr.attron(curses.color_pair(1))
            self.stdscr.addstr(y, x + 2, f"📁 {project_str}")
            self.stdscr.attroff(curses.color_pair(1))
            
            if is_mcp:
                self.stdscr.attron(curses.color_pair(1))
                self.stdscr.addstr(y + 1, x + 2, "✓ Existing MCP project")
                self.stdscr.attroff(curses.color_pair(1))
        else:
            self.stdscr.attron(curses.color_pair(4))
            self.stdscr.addstr(y, x + 2, "⚠️  No directory selected")
            self.stdscr.attroff(curses.color_pair(4))
        
        y += 3
        
        # Port section
        self.stdscr.attron(curses.A_BOLD)
        self.stdscr.addstr(y, x, "Server Port")
        self.stdscr.attroff(curses.A_BOLD)
        y += 1
        
        port_display = f":{self.launch_config['port']}"
        if self.launch_config["port"] in self.servers:
            self.stdscr.attron(curses.color_pair(4))
            self.stdscr.addstr(y, x + 2, f"🔴 {port_display} (Already in use!)")
            self.stdscr.attroff(curses.color_pair(4))
        else:
            self.stdscr.attron(curses.color_pair(1))
            self.stdscr.addstr(y, x + 2, f"🟢 {port_display}")
            self.stdscr.attroff(curses.color_pair(1))
            
        self.stdscr.addstr(y, x + 15, "Press 'p' to change", curses.A_DIM)
        y += 3
        
        # Options section
        self.stdscr.attron(curses.A_BOLD)
        self.stdscr.addstr(y, x, "Options")
        self.stdscr.attroff(curses.A_BOLD)
        y += 1
        
        # Initialize checkbox
        if self.launch_config["init_project"]:
            self.stdscr.attron(curses.color_pair(1))
            self.stdscr.addstr(y, x + 2, "☑")
            self.stdscr.attroff(curses.color_pair(1))
        else:
            self.stdscr.addstr(y, x + 2, "☐")
            
        self.stdscr.addstr(y, x + 4, "Initialize project if needed")
        self.stdscr.addstr(y, x + 35, "Press 'i'", curses.A_DIM)
        y += 3
        
        # Action buttons
        can_launch = (self.launch_config["project_dir"] and 
                     self.launch_config["port"] not in self.servers)
        
        if can_launch:
            # Draw launch button
            button_text = " Press 'L' to Launch "
            button_x = start_x + (box_width - len(button_text)) // 2
            self.stdscr.attron(curses.color_pair(1) | curses.A_BOLD | curses.A_REVERSE)
            self.stdscr.addstr(y, button_x, button_text)
            self.stdscr.attroff(curses.color_pair(1) | curses.A_BOLD | curses.A_REVERSE)
        else:
            # Show what's needed
            if not self.launch_config["project_dir"]:
                msg = "Select a project directory first"
            else:
                msg = "Port is already in use"
            msg_x = start_x + (box_width - len(msg)) // 2
            self.stdscr.attron(curses.color_pair(4) | curses.A_DIM)
            self.stdscr.addstr(y, msg_x, msg)
            self.stdscr.attroff(curses.color_pair(4) | curses.A_DIM)
            
    def draw_footer(self, y: int, width: int):
        """Draw footer with controls"""
        controls = []
        
        if self.current_mode == "dashboard":
            controls = ["n: New Server", "Enter: View", "s: Stop", "r: Restart", "c: Copy Token", "q: Quit"]
        elif self.current_mode == "browser":
            controls = ["Enter: Select/Open", "←: Back", "q: Cancel"]
        elif self.current_mode == "server_view":
            controls = ["Tab: Switch Server", "c: Copy Token", "←/q: Back"]
        elif self.current_mode == "launch":
            controls = ["p: Change Port", "i: Toggle Init", "L: Launch", "q: Cancel"]
            
        footer_text = " | ".join(controls)
        if len(footer_text) > width - 2:
            footer_text = footer_text[:width - 5] + "..."
            
        self.stdscr.attron(curses.color_pair(5))
        self.stdscr.addstr(y, (width - len(footer_text)) // 2, footer_text)
        self.stdscr.attroff(curses.color_pair(5))
        
    def draw_message(self, y: int, width: int):
        """Draw temporary message"""
        color = curses.color_pair(1) if self.message_type == "success" else curses.color_pair(4)
        
        self.stdscr.attron(color | curses.A_BOLD)
        self.stdscr.addstr(y, (width - len(self.message)) // 2, self.message)
        self.stdscr.attroff(color | curses.A_BOLD)
        
    def move_selection(self, delta: int):
        """Move selection up/down"""
        if self.current_mode == "dashboard":
            max_items = len(self.servers)
        elif self.current_mode == "browser":
            max_items = len(self.browser_items)
        else:
            return
            
        if max_items == 0:
            return
            
        self.selected_index = max(0, min(self.selected_index + delta, max_items - 1))
        
        # Adjust scroll offset
        height, _ = self.stdscr.getmaxyx()
        visible_items = height - 10
        
        if self.selected_index < self.scroll_offset:
            self.scroll_offset = self.selected_index
        elif self.selected_index >= self.scroll_offset + visible_items:
            self.scroll_offset = self.selected_index - visible_items + 1
            
    def handle_selection(self):
        """Handle enter key"""
        if self.current_mode == "dashboard" and self.servers:
            # View selected server
            ports = list(self.servers.keys())
            if 0 <= self.selected_index < len(ports):
                self.current_server_port = ports[self.selected_index]
                self.current_mode = "server_view"
        elif self.current_mode == "browser":
            # Select directory or navigate
            if 0 <= self.selected_index < len(self.browser_items):
                item = self.browser_items[self.selected_index]
                if item.is_dir():
                    # Check if it's a project directory
                    if (item / ".agent").exists() or item == self.browser_path:
                        # Select as project
                        self.launch_config["project_dir"] = item
                        self.current_mode = "launch"
                    else:
                        # Navigate into directory
                        self.browser_path = item
                        self.load_browser_items()
                        self.selected_index = 0
                        self.scroll_offset = 0
                        
    def handle_back(self):
        """Handle back navigation"""
        if self.current_mode == "browser":
            # Go up directory
            parent = self.browser_path.parent
            if parent != self.browser_path:
                self.browser_path = parent
                self.load_browser_items()
                self.selected_index = 0
                self.scroll_offset = 0
                
    def load_browser_items(self):
        """Load items for file browser"""
        try:
            items = []
            
            # Add parent directory if not at root
            if self.browser_path.parent != self.browser_path:
                items.append(self.browser_path.parent)
                
            # Add directories first, then files
            for item in sorted(self.browser_path.iterdir()):
                if item.is_dir() and not item.name.startswith('.'):
                    items.append(item)
                    
            self.browser_items = items
        except PermissionError:
            self.browser_items = []
            self.show_message("Permission denied", "error")
            
    def enter_port_selection(self):
        """Enter port selection mode"""
        curses.echo()
        curses.curs_set(1)
        
        height, width = self.stdscr.getmaxyx()
        self.stdscr.addstr(height // 2, 2, "Enter port (1024-65535): ")
        self.stdscr.refresh()
        
        port_str = self.stdscr.getstr(height // 2, 27, 5).decode('utf-8')
        
        curses.noecho()
        curses.curs_set(0)
        
        try:
            port = int(port_str)
            if 1024 <= port <= 65535:
                self.launch_config["port"] = port
            else:
                self.show_message("Port must be between 1024 and 65535", "error")
        except ValueError:
            self.show_message("Invalid port number", "error")
            
    def launch_server(self):
        """Launch a new server"""
        project_dir = self.launch_config["project_dir"]
        port = self.launch_config["port"]
        
        if not project_dir:
            self.show_message("No project directory selected", "error")
            return
            
        if port in self.servers:
            self.show_message(f"Port {port} is already in use", "error")
            return
            
        # Initialize project if needed
        if self.launch_config["init_project"] and not (project_dir / ".agent").exists():
            self.show_message("Initializing project...", "info")
            self.stdscr.refresh()
            
            try:
                init_agent_directory(str(project_dir))
            except Exception as e:
                self.show_message(f"Failed to initialize: {str(e)}", "error")
                return
                
        # Launch server
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
            self.current_mode = "dashboard"
            
            # Select the new server
            self.selected_index = len(self.servers) - 1
            
        except Exception as e:
            self.show_message(f"Failed to launch: {str(e)}", "error")
            
    def stop_selected_server(self):
        """Stop the selected server"""
        if not self.servers:
            return
            
        ports = list(self.servers.keys())
        if 0 <= self.selected_index < len(ports):
            port = ports[self.selected_index]
            server = self.servers[port]
            
            if server.is_running():
                server.stop()
                self.show_message(f"Stopped server on port {port}", "success")
            else:
                self.show_message("Server is not running", "error")
                
    def restart_selected_server(self):
        """Restart the selected server"""
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
            cmd = [
                sys.executable, "-m", "agent_mcp.cli_main", "server",
                "--port", str(port),
                "--project-dir", server.project_dir,
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
                
                new_server = ServerProcess(server.project_dir, port, process)
                self.servers[port] = new_server
                
                self.show_message(f"Restarted server on port {port}", "success")
                
            except Exception as e:
                self.show_message(f"Failed to restart: {str(e)}", "error")
                
    def switch_to_next_server(self):
        """Switch to next server in server view"""
        if len(self.servers) <= 1:
            return
            
        ports = sorted(self.servers.keys())
        current_idx = ports.index(self.current_server_port)
        next_idx = (current_idx + 1) % len(ports)
        self.current_server_port = ports[next_idx]
        
    def copy_to_clipboard(self):
        """Copy relevant info to clipboard"""
        try:
            if self.current_mode == "dashboard" and self.servers:
                ports = list(self.servers.keys())
                if 0 <= self.selected_index < len(ports):
                    server = self.servers[ports[self.selected_index]]
                    if server.admin_token:
                        pyperclip.copy(server.admin_token)
                        self.show_message("Admin token copied to clipboard", "success")
                    else:
                        self.show_message("No admin token available yet", "error")
            elif self.current_mode == "server_view":
                server = self.servers.get(self.current_server_port)
                if server and server.admin_token:
                    pyperclip.copy(server.admin_token)
                    self.show_message("Admin token copied to clipboard", "success")
        except Exception as e:
            self.show_message(f"Copy failed: {str(e)}", "error")
            
    def show_message(self, message: str, msg_type: str = "info"):
        """Show a temporary message"""
        self.message = message
        self.message_type = msg_type
        
        # Clear message after 3 seconds
        def clear_message():
            time.sleep(3)
            self.message = ""
            
        threading.Thread(target=clear_message, daemon=True).start()
        
    def confirm_quit(self):
        """Confirm before quitting"""
        if not any(s.is_running() for s in self.servers.values()):
            return True
            
        # Show confirmation
        height, width = self.stdscr.getmaxyx()
        y = height // 2
        
        self.stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
        msg = "Servers are still running. Really quit? (y/n)"
        self.stdscr.addstr(y, (width - len(msg)) // 2, msg)
        self.stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)
        self.stdscr.refresh()
        
        key = self.stdscr.getch()
        return key in [ord('y'), ord('Y')]
        
    def cleanup(self):
        """Cleanup on exit"""
        for server in self.servers.values():
            if server.is_running():
                server.stop()


def run_server_manager():
    """Entry point for server manager"""
    manager_logger.info("=" * 80)
    manager_logger.info("STARTING SERVER MANAGER")
    manager_logger.info("=" * 80)
    manager_logger.info(f"Terminal: {os.environ.get('TERM', 'unknown')}")
    
    try:
        manager_logger.info("Initializing curses wrapper")
        wrapper(lambda stdscr: ServerManager(stdscr).run())
        manager_logger.info("Server manager closed normally")
    except KeyboardInterrupt:
        manager_logger.info("Server manager closed by user (Ctrl+C)")
        pass
    except Exception as e:
        logger.error(f"Server manager error: {e}", exc_info=True)
        manager_logger.error(f"Server manager error: {e}")
        manager_logger.debug(f"Error traceback: {traceback.format_exc()}")
        click.echo(f"Error: {str(e)}")
        sys.exit(1)
    finally:
        manager_logger.info("Server manager shutdown complete")
        manager_logger.info("=" * 80)