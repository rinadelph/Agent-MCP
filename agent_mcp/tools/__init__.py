# Agent-MCP/mcp_template/mcp_server_src/tools/__init__.py

"""
Tools Package Initialization for MCP Server.

This __init__.py file serves to import all individual tool modules.
Importing these modules will trigger their respective registration functions
(e.g., `register_admin_tools()`, `register_task_tools()`, etc.), which in turn
call `register_tool()` from `mcp_server_src.tools.registry`. This populates
the central tool schemas and implementations in the registry.

The order of imports here generally doesn't matter for the registration itself,
as long as `mcp_server_src.tools.registry` is loaded before or during these imports.
"""

from ..core.config import logger

logger.info("Initializing and registering MCP tools...")

# Import each tool module to trigger its registration functions.
# The `register_tool` calls within these modules populate the
# `tool_schemas` and `tool_implementations` in `tools.registry`.

from . import admin_tools
from . import task_tools
from . import file_management_tools
from . import project_context_tools
from . import file_metadata_tools
from . import agent_tools
from . import rag_tools
from . import utility_tools
from . import agent_communication_tools

# Import and register TMUX Bible enhanced orchestration tools
from . import tmux_orchestration_tools

# After all imports, the tool registry in tools.registry should be populated.
# We can optionally add a log here to confirm, or check the registry's state.
from .registry import tool_schemas, tool_implementations

logger.info(f"MCP Tools initialization complete. {len(tool_schemas)} tool schemas registered.")
logger.debug(f"Registered tool names: {list(tool_implementations.keys())}")

# Expose key elements from the registry if needed directly from `tools` package
# For example, if other parts of the application need direct access to these:
# from .registry import list_available_tools, dispatch_tool_call
# This makes them available as `from mcp_server_src.tools import list_available_tools`

# For now, other modules will import directly from .registry if needed.