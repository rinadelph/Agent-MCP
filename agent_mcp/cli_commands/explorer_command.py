"""Interactive CLI Explorer for Agent MCP"""

import os
import sys
import click
import pyperclip
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
import json
import logging
import traceback

# For interactive UI
import curses
from curses import wrapper
import textwrap

# Project imports
from ..db.connection import get_db_connection
from ..db.actions.agent_db import get_all_active_agents_from_db
from ..db.actions.task_db import get_all_tasks_from_db, get_task_by_id
from ..db.actions.context_db import get_all_context_from_db
from ..core.config import logger

# Set up enhanced logging for the explorer
explorer_logger = logging.getLogger('agent_mcp.cli.explorer')
explorer_logger.setLevel(logging.DEBUG)

# Add file handler for explorer-specific logs
explorer_log_file = 'agent_mcp_explorer.log'
explorer_file_handler = logging.FileHandler(explorer_log_file, mode='a')
explorer_file_handler.setLevel(logging.DEBUG)
explorer_formatter = logging.Formatter(
    '%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s - %(funcName)s:%(lineno)d - %(message)s',
    datefmt='%H:%M:%S'
)
explorer_file_handler.setFormatter(explorer_formatter)
explorer_logger.addHandler(explorer_file_handler)

explorer_logger.info("=" * 80)
explorer_logger.info("EXPLORER COMMAND MODULE LOADED")
explorer_logger.info("=" * 80)


class InteractiveExplorer:
    """Interactive explorer for Agent MCP with arrow key navigation"""
    
    def __init__(self, stdscr):
        explorer_logger.info("Initializing InteractiveExplorer")
        self.stdscr = stdscr
        self.current_mode = "main"  # main, agents, tasks, context
        self.current_selection = 0
        self.scroll_offset = 0
        self.items = []
        self.detail_view = False
        self.selected_item = None
        self.search_query = ""
        self.search_mode = False
        
        explorer_logger.debug("Setting up color pairs")
        # Color pairs
        curses.init_pair(1, curses.COLOR_GREEN, curses.COLOR_BLACK)  # Header
        curses.init_pair(2, curses.COLOR_YELLOW, curses.COLOR_BLACK)  # Selected
        curses.init_pair(3, curses.COLOR_CYAN, curses.COLOR_BLACK)   # Info
        curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)    # Error
        curses.init_pair(5, curses.COLOR_MAGENTA, curses.COLOR_BLACK) # Keys
        curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_BLACK)  # Normal
        
        # Hide cursor
        curses.curs_set(0)
        explorer_logger.debug(f"Terminal size: {curses.LINES}x{curses.COLS}")
        explorer_logger.info("InteractiveExplorer initialization complete")
        
    def run(self):
        """Main loop"""
        explorer_logger.info("Starting explorer main loop")
        try:
            while True:
                self.refresh_screen()
                key = self.stdscr.getch()
                
                if key != -1:  # Key pressed
                    explorer_logger.debug(f"Key pressed: {key} (char: {chr(key) if 32 <= key <= 126 else 'special'})")
            
            if self.search_mode:
                if key == 27:  # ESC
                    self.search_mode = False
                    self.search_query = ""
                    self.refresh_items()
                elif key == 10:  # Enter
                    self.search_mode = False
                    self.refresh_items()
                elif key == curses.KEY_BACKSPACE or key == 127:
                    self.search_query = self.search_query[:-1]
                    self.refresh_items()
                elif 32 <= key <= 126:  # Printable characters
                    self.search_query += chr(key)
                    self.refresh_items()
            else:
                if key == ord('q') or key == ord('Q'):
                    if self.detail_view:
                        self.detail_view = False
                        self.selected_item = None
                    elif self.current_mode != "main":
                        self.current_mode = "main"
                        self.current_selection = 0
                        self.scroll_offset = 0
                        self.items = []
                    else:
                        break
                elif key == curses.KEY_UP or key == ord('k'):
                    self.move_selection(-1)
                elif key == curses.KEY_DOWN or key == ord('j'):
                    self.move_selection(1)
                elif key == curses.KEY_PPAGE:  # Page Up
                    self.move_selection(-10)
                elif key == curses.KEY_NPAGE:  # Page Down
                    self.move_selection(10)
                elif key == 10 or key == curses.KEY_RIGHT or key == ord('l'):  # Enter or Right
                    self.handle_selection()
                elif key == curses.KEY_LEFT or key == ord('h'):  # Left
                    if self.detail_view:
                        self.detail_view = False
                        self.selected_item = None
                    elif self.current_mode != "main":
                        self.current_mode = "main"
                        self.current_selection = 0
                        self.scroll_offset = 0
                        self.items = []
                elif key == ord('c') or key == ord('C'):
                    self.copy_to_clipboard()
                elif key == ord('/'):
                    if self.current_mode != "main":
                        self.search_mode = True
                        self.search_query = ""
                elif key == ord('r') or key == ord('R'):
                    self.refresh_items()
                    
    def refresh_screen(self):
        """Refresh the screen display"""
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()
        
        # Header
        header = "🚀 Agent MCP Explorer"
        if self.current_mode != "main":
            header += f" - {self.current_mode.title()}"
        if self.search_mode:
            header += f" - Search: {self.search_query}"
        elif self.search_query:
            header += f" - Filter: {self.search_query}"
            
        self.stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
        self.stdscr.addstr(0, (width - len(header)) // 2, header)
        self.stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
        
        # Main content area
        content_start = 2
        content_height = height - 5  # Leave room for header and footer
        
        if self.detail_view and self.selected_item:
            self.draw_detail_view(content_start, content_height, width)
        elif self.current_mode == "main":
            self.draw_main_menu(content_start, content_height, width)
        else:
            self.draw_list_view(content_start, content_height, width)
            
        # Footer with controls
        self.draw_footer(height - 2, width)
        
        self.stdscr.refresh()
        
    def draw_main_menu(self, start_y: int, height: int, width: int):
        """Draw the main menu"""
        menu_items = [
            ("👥 Agents", "View and manage agents with their tokens"),
            ("📋 Tasks", "Browse tasks and their assignments"),
            ("🗂️ Context", "Explore project context entries"),
            ("🚪 Quit", "Exit the explorer")
        ]
        
        for i, (title, desc) in enumerate(menu_items):
            y_pos = start_y + i * 3
            if y_pos + 2 > start_y + height:
                break
                
            if i == self.current_selection:
                self.stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
                self.stdscr.addstr(y_pos, 2, f"> {title}")
                self.stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
                self.stdscr.attron(curses.color_pair(3))
                self.stdscr.addstr(y_pos + 1, 4, desc)
                self.stdscr.attroff(curses.color_pair(3))
            else:
                self.stdscr.addstr(y_pos, 4, title)
                self.stdscr.addstr(y_pos + 1, 4, desc, curses.color_pair(6) | curses.A_DIM)
                
    def draw_list_view(self, start_y: int, height: int, width: int):
        """Draw list view for agents/tasks/context"""
        if not self.items:
            self.load_items()
            
        # Calculate visible range
        visible_items = min(height - 1, len(self.items))
        
        # Adjust scroll offset if needed
        if self.current_selection < self.scroll_offset:
            self.scroll_offset = self.current_selection
        elif self.current_selection >= self.scroll_offset + visible_items:
            self.scroll_offset = self.current_selection - visible_items + 1
            
        # Draw items
        for i in range(visible_items):
            item_idx = self.scroll_offset + i
            if item_idx >= len(self.items):
                break
                
            y_pos = start_y + i
            item = self.items[item_idx]
            
            # Format item display
            if self.current_mode == "agents":
                display_text = f"{item['agent_id']} ({item['status']}) - Tasks: {item['active_tasks']}"
            elif self.current_mode == "tasks":
                display_text = f"[{item['status']}] {item['title'][:50]}... - {item['assigned_to'] or 'Unassigned'}"
            elif self.current_mode == "context":
                display_text = f"{item['context_key']}: {str(item['context_value'])[:60]}..."
                
            # Truncate if too long
            max_width = width - 4
            if len(display_text) > max_width:
                display_text = display_text[:max_width - 3] + "..."
                
            if item_idx == self.current_selection:
                self.stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
                self.stdscr.addstr(y_pos, 2, f"> {display_text}")
                self.stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
            else:
                self.stdscr.addstr(y_pos, 4, display_text)
                
        # Scroll indicator
        if len(self.items) > visible_items:
            scroll_pos = int((self.scroll_offset / (len(self.items) - visible_items)) * (height - 3))
            self.stdscr.addstr(start_y + scroll_pos, width - 2, "█", curses.color_pair(3))
            
    def draw_detail_view(self, start_y: int, height: int, width: int):
        """Draw detailed view of selected item"""
        if not self.selected_item:
            return
            
        y_pos = start_y
        max_width = width - 4
        
        if self.current_mode == "agents":
            details = [
                ("Agent ID", self.selected_item['agent_id']),
                ("Status", self.selected_item['status']),
                ("Active Tasks", str(self.selected_item['active_tasks'])),
                ("Token", self.selected_item['token']),
                ("Created", self.selected_item['created_at']),
                ("", ""),
                ("Press 'c' to copy token to clipboard", "")
            ]
        elif self.current_mode == "tasks":
            details = [
                ("Task ID", self.selected_item['task_id']),
                ("Title", self.selected_item['title']),
                ("Description", self.selected_item.get('description', 'N/A')),
                ("Status", self.selected_item['status']),
                ("Assigned To", self.selected_item.get('assigned_to', 'Unassigned')),
                ("Priority", self.selected_item.get('priority', 'medium')),
                ("Created", self.selected_item['created_at']),
                ("Updated", self.selected_item['updated_at']),
                ("", ""),
                ("Press 'c' to copy task details to clipboard", "")
            ]
        elif self.current_mode == "context":
            details = [
                ("Key", self.selected_item['context_key']),
                ("Value", json.dumps(self.selected_item['context_value'], indent=2)),
                ("Metadata", json.dumps(self.selected_item.get('metadata', {}), indent=2)),
                ("Created", self.selected_item['created_at']),
                ("Updated", self.selected_item['updated_at']),
                ("", ""),
                ("Press 'c' to copy value to clipboard", "")
            ]
            
        for label, value in details:
            if y_pos - start_y >= height - 1:
                break
                
            if label:
                self.stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
                self.stdscr.addstr(y_pos, 2, f"{label}:")
                self.stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)
                
                # Handle multi-line values
                if isinstance(value, str) and len(value) > max_width - len(label) - 4:
                    # Wrap text
                    wrapped = textwrap.wrap(value, width=max_width - 4)
                    self.stdscr.addstr(y_pos, len(label) + 4, wrapped[0])
                    y_pos += 1
                    for line in wrapped[1:]:
                        if y_pos - start_y >= height - 1:
                            break
                        self.stdscr.addstr(y_pos, 4, line)
                        y_pos += 1
                else:
                    self.stdscr.addstr(y_pos, len(label) + 4, str(value))
                    y_pos += 1
            else:
                y_pos += 1
                
    def draw_footer(self, y: int, width: int):
        """Draw footer with controls"""
        controls = []
        
        if self.search_mode:
            controls = ["ESC: Cancel", "Enter: Apply"]
        elif self.detail_view:
            controls = ["q/←: Back", "c: Copy", "↑↓: Scroll"]
        elif self.current_mode == "main":
            controls = ["↑↓/jk: Navigate", "Enter/→: Select", "q: Quit"]
        else:
            controls = ["↑↓/jk: Navigate", "Enter/→: Details", "c: Copy", "/: Search", "q: Back"]
            
        footer_text = " | ".join(controls)
        self.stdscr.attron(curses.color_pair(5))
        self.stdscr.addstr(y, (width - len(footer_text)) // 2, footer_text)
        self.stdscr.attroff(curses.color_pair(5))
        
    def move_selection(self, delta: int):
        """Move selection up or down"""
        if self.current_mode == "main":
            max_items = 4  # Number of main menu items
        else:
            max_items = len(self.items)
            
        self.current_selection = max(0, min(self.current_selection + delta, max_items - 1))
        
    def handle_selection(self):
        """Handle item selection"""
        if self.current_mode == "main":
            if self.current_selection == 0:  # Agents
                self.current_mode = "agents"
                self.current_selection = 0
                self.scroll_offset = 0
                self.load_items()
            elif self.current_selection == 1:  # Tasks
                self.current_mode = "tasks"
                self.current_selection = 0
                self.scroll_offset = 0
                self.load_items()
            elif self.current_selection == 2:  # Context
                self.current_mode = "context"
                self.current_selection = 0
                self.scroll_offset = 0
                self.load_items()
            elif self.current_selection == 3:  # Quit
                sys.exit(0)
        else:
            # Show detail view
            if self.items and 0 <= self.current_selection < len(self.items):
                self.selected_item = self.items[self.current_selection]
                self.detail_view = True
                
    def load_items(self):
        """Load items based on current mode"""
        try:
            if self.current_mode == "agents":
                all_agents = get_all_active_agents_from_db()
                self.items = all_agents
            elif self.current_mode == "tasks":
                all_tasks = get_all_tasks_from_db()
                self.items = all_tasks
            elif self.current_mode == "context":
                all_context = get_all_context_from_db()
                self.items = all_context
                
            self.apply_search_filter()
        except Exception as e:
            logger.error(f"Error loading items: {e}")
            self.items = []
            
    def refresh_items(self):
        """Refresh current items"""
        self.load_items()
        
    def apply_search_filter(self):
        """Apply search filter to items"""
        if not self.search_query:
            return
            
        query = self.search_query.lower()
        
        if self.current_mode == "agents":
            self.items = [a for a in self.items if query in a['agent_id'].lower()]
        elif self.current_mode == "tasks":
            self.items = [t for t in self.items if 
                         query in t.get('title', '').lower() or 
                         query in t.get('description', '').lower() or
                         query in t.get('assigned_to', '').lower()]
        elif self.current_mode == "context":
            self.items = [c for c in self.items if 
                         query in c['context_key'].lower() or 
                         query in str(c['context_value']).lower()]
                         
    def copy_to_clipboard(self):
        """Copy relevant data to clipboard"""
        try:
            if self.detail_view and self.selected_item:
                if self.current_mode == "agents":
                    pyperclip.copy(self.selected_item['token'])
                    self.show_message("Token copied to clipboard!")
                elif self.current_mode == "tasks":
                    task_data = {
                        'task_id': self.selected_item['task_id'],
                        'title': self.selected_item['title'],
                        'description': self.selected_item.get('description', ''),
                        'status': self.selected_item['status'],
                        'assigned_to': self.selected_item.get('assigned_to', '')
                    }
                    pyperclip.copy(json.dumps(task_data, indent=2))
                    self.show_message("Task details copied to clipboard!")
                elif self.current_mode == "context":
                    pyperclip.copy(json.dumps(self.selected_item['context_value'], indent=2))
                    self.show_message("Context value copied to clipboard!")
            elif self.items and 0 <= self.current_selection < len(self.items):
                item = self.items[self.current_selection]
                if self.current_mode == "agents":
                    pyperclip.copy(item['token'])
                    self.show_message("Token copied to clipboard!")
                elif self.current_mode == "tasks":
                    pyperclip.copy(item['task_id'])
                    self.show_message("Task ID copied to clipboard!")
                elif self.current_mode == "context":
                    pyperclip.copy(item['context_key'])
                    self.show_message("Context key copied to clipboard!")
        except Exception as e:
            self.show_message(f"Error copying: {str(e)}", error=True)
            
    def show_message(self, message: str, error: bool = False):
        """Show a temporary message"""
        height, width = self.stdscr.getmaxyx()
        color = curses.color_pair(4) if error else curses.color_pair(1)
        
        # Clear message area
        self.stdscr.move(height - 3, 0)
        self.stdscr.clrtoeol()
        
        # Show message
        self.stdscr.attron(color | curses.A_BOLD)
        self.stdscr.addstr(height - 3, (width - len(message)) // 2, message)
        self.stdscr.attroff(color | curses.A_BOLD)
        self.stdscr.refresh()
        
        # Message will be cleared on next refresh


def run_interactive_explorer():
    """Entry point for interactive explorer"""
    explorer_logger.info("=" * 80)
    explorer_logger.info("STARTING INTERACTIVE EXPLORER")
    explorer_logger.info("=" * 80)
    
    # Check if we have a project directory set
    project_dir = os.environ.get("MCP_PROJECT_DIR")
    explorer_logger.info(f"Project directory: {project_dir}")
    
    if not project_dir:
        explorer_logger.error("No project directory set")
        click.echo("Error: No project directory set. Please run from a project directory or set MCP_PROJECT_DIR.")
        sys.exit(1)
        
    # Run the explorer
    try:
        explorer_logger.info("Initializing curses wrapper")
        wrapper(lambda stdscr: InteractiveExplorer(stdscr).run())
        explorer_logger.info("Explorer closed normally")
    except KeyboardInterrupt:
        explorer_logger.info("Explorer closed by user (Ctrl+C)")
        pass
    except Exception as e:
        logger.error(f"Explorer error: {e}", exc_info=True)
        explorer_logger.error(f"Explorer error: {e}")
        explorer_logger.debug(f"Error traceback: {traceback.format_exc()}")
        click.echo(f"Error: {str(e)}")
        sys.exit(1)
    finally:
        explorer_logger.info("Explorer shutdown complete")
        explorer_logger.info("=" * 80)