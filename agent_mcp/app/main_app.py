# Agent-MCP/mcp_template/mcp_server_src/app/main_app.py
import uuid
import datetime # For SSE connection logging
from pathlib import Path
from typing import List, Optional # Added List and Optional
import os # Added os import

from starlette.applications import Starlette
from starlette.routing import Mount, Route # Added Route
from starlette.staticfiles import StaticFiles # For serving static files
from starlette.middleware import Middleware # If any middleware is needed
from starlette.middleware.cors import CORSMiddleware # Example if CORS is needed

# MCP Server specific imports
from mcp.server.lowlevel import Server as MCPLowLevelServer # Renamed to avoid conflict
from mcp.server.sse import SseServerTransport
import mcp.types as mcp_types # For MCP tool types

# Project-specific imports
from ..core.config import logger
from ..core import globals as g # For g.connections (if still used for SSE tracking)
from .routes import routes as http_routes, STATIC_DIR # Import defined HTTP routes and STATIC_DIR
from .server_lifecycle import application_startup, application_shutdown, start_background_tasks
from ..tools.registry import list_available_tools, dispatch_tool_call

# --- MCP Server Setup (mimicking original main.py:2055) ---
mcp_app_instance = MCPLowLevelServer("mcp-server") # Name from original main.py:2055

# Register MCP tool handlers with the low-level server instance
# Original main.py: lines 1636-1938 (@app.list_tools, @app.call_tool)
@mcp_app_instance.list_tools()
async def mcp_list_tools_handler() -> List[mcp_types.Tool]:
    """MCP endpoint to list available tools."""
    return await list_available_tools() # Calls the function from tools.registry

@mcp_app_instance.call_tool()
async def mcp_call_tool_handler(name: str, arguments: dict) -> List[mcp_types.TextContent]:
    """MCP endpoint to call a specific tool."""
    # `dispatch_tool_call` from tools.registry handles sanitization and routing
    return await dispatch_tool_call(name, arguments)


# --- SSE Transport Setup (mimicking original main.py:1943-1969 for SSE part) ---
# The SseServerTransport handles /messages/ (POST for tool calls) and /sse (GET for connections)
sse_transport = SseServerTransport("/messages/") # Path from original main.py:1943

async def sse_connection_handler(request): # Matches original handle_sse in main.py:1945
    """Handles new SSE client connections."""
    try:
        # Client ID generation (original main.py:1947)
        # While SseServerTransport might manage its own client IDs, logging this is useful.
        client_id_log = str(uuid.uuid4())[:8] # For logging this specific connection attempt
        logger.info(f"SSE connection request from {request.client.host} (Log ID: {client_id_log})")
        # The original also printed to console, which logger now handles.
        # print(f"[{datetime.datetime.now().isoformat()}] SSE connection request from {request.client.host} (ID: {client_id_log})")

        # `connect_sse` is a context manager from SseServerTransport
        async with sse_transport.connect_sse(
            request.scope, request.receive, request._send # Starlette's low-level ASGI send
        ) as streams:
            # streams[0] is input_stream, streams[1] is output_stream
            actual_client_id = streams[2] if len(streams) > 2 else client_id_log # Get actual client ID if provided by transport
            logger.info(f"SSE client connected: {actual_client_id}")
            # print(f"[{datetime.datetime.now().isoformat()}] SSE client connected: {actual_client_id}")
            
            # Store connection if g.connections is still used for tracking (original main.py:147)
            # g.connections[actual_client_id] = {"connected_at": datetime.datetime.now().isoformat()}

            try:
                # Run the MCP low-level server for this connection
                # (Original main.py:1957-1961)
                await mcp_app_instance.run(
                    streams[0], # input_stream
                    streams[1], # output_stream
                    mcp_app_instance.create_initialization_options() # As per original
                )
            finally:
                logger.info(f"SSE client disconnected: {actual_client_id}")
                # print(f"[{datetime.datetime.now().isoformat()}] SSE client disconnected: {actual_client_id}")
                # if actual_client_id in g.connections:
                #     del g.connections[actual_client_id]
    except Exception as e:
        # Log errors during SSE connection handling (original main.py:1964-1966)
        logger.error(f"Error in SSE connection handler: {str(e)}", exc_info=True)
        # print(f"[{datetime.datetime.now().isoformat()}] Error in SSE connection: {str(e)}")
        # Starlette will handle sending an error response if one isn't already sent.
        raise # Re-raise to let Starlette handle it if appropriate


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
    # Enable CORS for dashboard integration
    middleware_stack = [
        Middleware(
            CORSMiddleware,
            allow_origins=['http://localhost:3000'],  # Next.js dev server
            allow_credentials=True,
            allow_methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
            allow_headers=['*'],
        )
    ]

    # Create the Starlette app
    # The original main.py:2100 created `web_app = Starlette()`
    # It then added routes.
    
    # The routes list from app.routes.py already contains most HTTP routes.
    # We need to add the SSE specific routes here.
    all_routes = list(http_routes) # Start with routes from app/routes.py

    # Add SSE routes (Original main.py:2113-2114)
    all_routes.append(Route('/sse', endpoint=sse_connection_handler, name="sse_connect"))
    # Mount the SseServerTransport's POST message handler
    all_routes.append(Mount('/messages', app=sse_transport.handle_post_message, name="mcp_post_message"))

    # Mount static files (Original main.py:2120)
    # Ensure STATIC_DIR is an absolute path string for StaticFiles
    all_routes.append(Mount('/static', app=StaticFiles(directory=str(STATIC_DIR)), name="static_files"))
    
    # Mount Next.js static files at the expected /_next path
    next_static_dir = STATIC_DIR / "_next"
    if next_static_dir.exists():
        all_routes.append(Mount('/_next', app=StaticFiles(directory=str(next_static_dir)), name="next_static_files"))
    
    # Add routes for root-level static assets (favicon, etc.)
    from starlette.responses import FileResponse, JSONResponse
    
    async def favicon_route(request):
        favicon_path = STATIC_DIR / "favicon.ico"
        if favicon_path.exists():
            return FileResponse(str(favicon_path))
        return JSONResponse({"error": "Not found"}, status_code=404)
    
    all_routes.append(Route('/favicon.ico', endpoint=favicon_route, name="favicon"))
    
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