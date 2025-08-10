"""
Agent-MCP Terminal User Interface (TUI) Package

This package provides an interactive terminal interface for the Agent-MCP server,
allowing users to monitor and control the server, agents, and tasks through
a colorful, menu-driven interface.
"""

from .main_loop import TUIMainLoop
from .display import TUIDisplay
from .menu import TUIMenu
from .actions import TUIActions

__all__ = ['TUIMainLoop', 'TUIDisplay', 'TUIMenu', 'TUIActions']