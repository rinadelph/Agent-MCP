"""
Agent MCP - Multi-Agent Collaboration Platform

A powerful framework for building and managing multi-agent systems
with intelligent task distribution and RAG capabilities.
"""

__version__ = "2.0.0"
__author__ = "AI CURSOR"
__email__ = "accounts@cursor.com"

# Export main components for easier imports
from .core.config import logger

__all__ = [
    "__version__",
    "logger",
]
