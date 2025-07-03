# Agent-MCP/mcp_template/mcp_server_src/app/main_app.py
import uuid
import datetime # For SSE connection logging
from pathlib import Path
from typing import List, Optional # Added List and Optional
import os # Added os import

from starlette.applications import Starlette
from starlette.routing import Mount, Route # Added Route
from starlette.middleware import Middleware # If any middleware is needed
from starlette.middleware.cors import CORSMiddleware # Example if CORS is needed

# MCP Server specific imports
from mcp.server.lowlevel import Server as MCPLowLevelServer # Renamed to avoid conflict
from mcp.server.sse import SseServerTransport
import mcp.types as mcp_types # For MCP tool types

# Project-specific imports
from ..core.config import logger
from ..core import globals as g # For g.connections (if still used for SSE tracking)
from .routes import routes as http_routes # Import defined HTTP routes
from .server_lifecycle import application_startup, application_shutdown, start_background_tasks
from ..tools.registry import list_available_tools, dispatch_tool_call

# --- MCP Server Setup (mimicking original main.py:2055) ---
mcp_app_instance = MCPLowLevelServer("mcp-server") # Name from original main.py:2055

# Register MCP tool handlers with the low-level server instance
# Original main.py: lines 1636-1938 (@app.list_tools, @app.call_tool)
@mcp_app_instance.list_tools()
async def mcp_list_tools_handler() -> List[mcp_types.Tool]:
    """MCP endpoint to list available tools."""
    # Check if server is initialized before handling requests
    if not g.server_initialized:
        logger.warning("Received list_tools request before server initialization was complete")
        # Return empty tools list during initialization to prevent errors
        return []
    
    return await list_available_tools() # Calls the function from tools.registry

@mcp_app_instance.call_tool()
async def mcp_call_tool_handler(name: str, arguments: dict) -> List[mcp_types.TextContent]:
    """MCP endpoint to call a specific tool."""
    # Check if server is initialized before handling requests
    if not g.server_initialized:
        logger.warning(f"Received call_tool request for '{name}' before server initialization was complete")
        # Return error message during initialization
        return [mcp_types.TextContent(
            type="text",
            text="Server is still initializing. Please wait a moment and try again."
        )]
    
    # `dispatch_tool_call` from tools.registry handles sanitization and routing
    return await dispatch_tool_call(name, arguments)


# --- SSE Transport Setup (mimicking original main.py:1943-1969 for SSE part) ---
# The SseServerTransport handles /messages/ (POST for tool calls) and /sse (GET for connections)
sse_transport = SseServerTransport("/messages/") # Path from original main.py:1943


# --- Starlette Application Creation ---
def create_app(project_dir: str, admin_token_cli: Optional[str] = None) -> Starlette:
    """
    Creates and configures the main Starlette application.
    """
    # Define lifecycle events
    async def on_app_startup():
        # Call the centralized application startup logic
        await application_startup(project_dir_path_str=project_dir, admin_token_param=admin_token_cli)
        # Start background tasks within a task group managed by Uvicorn/Hypercorn or AnyIO runner
        # This requires the server runner to manage the task group.
        # For now, we assume the main CLI runner will handle the task group.
        # If Uvicorn is run programmatically, its 'lifespan' can manage this.
        logger.info("Starlette app startup complete. Background tasks should be started by the server runner.")

    async def on_app_shutdown():
        # Call the centralized application shutdown logic
        await application_shutdown()
        logger.info("Starlette app shutdown complete.")

    # Define middleware (if any)
    # Enable CORS for dashboard integration - comprehensive CORS config
    middleware_stack = [
        Middleware(
            CORSMiddleware,
            allow_origins=[
                'http://localhost:3847',  # Primary dashboard port
                'http://127.0.0.1:3847',  # Alternative localhost
                'http://localhost:3000',  # Next.js default
                'http://localhost:3001',  # Common alternative
                '*'  # Fallback for any other ports during development
            ],
            allow_credentials=True,
            allow_methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'HEAD', 'PATCH'],
            allow_headers=['*'],
            expose_headers=['*'],
            max_age=3600,  # Cache preflight for 1 hour
        )
    ]

    # Create the Starlette app
    # The original main.py:2100 created `web_app = Starlette()`
    # It then added routes.
    
    # The routes list from app.routes.py already contains most HTTP routes.
    # We need to add the SSE specific routes here.
    all_routes = list(http_routes) # Start with routes from app/routes.py

    # Add SSE routes (Original main.py:2113-2114)
    # Create an ASGI app that handles both SSE and messages
    async def mcp_asgi_app(scope, receive, send):
        """ASGI app that routes MCP requests."""
        if scope["type"] == "http":
            if scope["path"] == "/sse" and scope["method"] == "GET":
                # Handle SSE connections
                client_id = str(uuid.uuid4())[:8]
                client_host = scope.get('client', ['unknown', None])[0]
                logger.info(f"SSE connection request from {client_host} (Log ID: {client_id})")
                
                async with sse_transport.connect_sse(scope, receive, send) as streams:
                    logger.info(f"SSE client connected: {client_id}")
                    try:
                        await mcp_app_instance.run(
                            streams[0],
                            streams[1],
                            mcp_app_instance.create_initialization_options()
                        )
                    finally:
                        logger.info(f"SSE client disconnected: {client_id}")
            elif scope["path"].startswith("/messages") and scope["method"] == "POST":
                # Handle POST messages
                await sse_transport.handle_post_message(scope, receive, send)
            else:
                # Not found
                await send({
                    "type": "http.response.start",
                    "status": 404,
                    "headers": [[b"content-type", b"text/plain"]],
                })
                await send({
                    "type": "http.response.body",
                    "body": b"Not Found",
                })
    
    # Mount the MCP ASGI app
    all_routes.append(Mount('/', app=mcp_asgi_app, name="mcp_transport"))

    # Note: Static file serving removed - dashboard is now served separately via npm run dev
    
    # Create the Starlette application instance
    app = Starlette(
        routes=all_routes,
        on_startup=[on_app_startup], # List of startup handlers
        on_shutdown=[on_app_shutdown], # List of shutdown handlers
        middleware=middleware_stack,
        debug=os.environ.get("MCP_DEBUG", "false").lower() == "true" # Optional debug mode
    )

    logger.info("Starlette application instance created with routes and lifecycle events.")
    return app

# The actual running of the app (e.g., with uvicorn) will be handled by cli.py