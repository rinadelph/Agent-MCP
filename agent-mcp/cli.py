# Agent-MCP/mcp_template/mcp_server_src/cli.py
import click
import uvicorn # For running the Starlette app in SSE mode
import anyio # For running async functions and task groups
import os
import sys
from typing import Optional

# Project-specific imports
# Ensure core.config (and thus logging) is initialized early.
from .core.config import logger # Logger is initialized in config.py
from .core import globals as g # For g.server_running and other globals
# Import app creation and lifecycle functions
from .app.main_app import create_app, mcp_app_instance # mcp_app_instance for stdio
from .app.server_lifecycle import start_background_tasks, application_startup, application_shutdown # application_startup is called by create_app's on_startup

# --- Click Command Definition ---
# This replicates the @click.command and options from the original main.py (lines 1936-1950)
@click.command(context_settings=dict(help_option_names=['-h', '--help']))
@click.option(
    "--port",
    type=int,
    default=os.environ.get('PORT', 8080), # Read from env var PORT if set, else 8080
    show_default=True,
    help="Port to listen on for SSE and HTTP dashboard."
)
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse"], case_sensitive=False),
    default="sse",
    show_default=True,
    help="Transport type for MCP communication (stdio or sse)."
)
@click.option(
    "--project-dir",
    type=click.Path(file_okay=False, dir_okay=True, resolve_path=True, writable=True),
    default=".",
    show_default=True,
    help="Project directory. The .agent folder will be created/used here. Defaults to current directory."
)
@click.option(
    "--admin-token", # Renamed from admin_token_param for clarity
    "admin_token_cli", # Variable name for the parameter
    type=str,
    default=None,
    help="Admin token for authentication. If not provided, one will be loaded from DB or generated."
)
@click.option(
    "--debug",
    is_flag=True,
    default=os.environ.get("MCP_DEBUG", "false").lower() == "true", # Default from env var
    help="Enable debug mode for the server (more verbose logging, Starlette debug pages)."
)
def main_cli(port: int, transport: str, project_dir: str, admin_token_cli: Optional[str], debug: bool):
    """
    Main Command-Line Interface for starting the MCP Server.
    """
    if debug:
        logger.info("Debug mode enabled via CLI flag or MCP_DEBUG environment variable.")
        # Logging level might need to be adjusted here if not already handled by config.py
        # For now, config.py sets the base level. Uvicorn also has its own log level.
        os.environ["MCP_DEBUG"] = "true" # Ensure env var is set for Starlette debug mode
    else:
        os.environ["MCP_DEBUG"] = "false"

    logger.info(f"Attempting to start MCP Server: Port={port}, Transport={transport}, ProjectDir='{project_dir}'")

    # The application_startup logic (including setting MCP_PROJECT_DIR env var,
    # DB init, admin token handling, state loading, OpenAI init, VSS check, signal handlers)
    # is now part of the Starlette app's on_startup event, triggered by create_app.

    if transport == "sse":
        # Create the Starlette application instance.
        # `application_startup` will be called by Starlette during its startup phase.
        starlette_app = create_app(project_dir=project_dir, admin_token_cli=admin_token_cli)
        
        # Uvicorn configuration
        # log_config=None prevents Uvicorn from overriding our logging setup from config.py
        # (Original main.py:2630)
        uvicorn_config = uvicorn.Config(
            starlette_app,
            host="0.0.0.0", # Listen on all available interfaces
            port=port,
            log_config=None, # Use our custom logging setup
            lifespan="on" # Ensure Starlette's on_startup/on_shutdown are used
        )
        server = uvicorn.Server(uvicorn_config)

        # Run Uvicorn server with background tasks managed by an AnyIO task group
        # This replaces the original run_server_with_background_tasks (main.py:2624)
        async def run_sse_server_with_bg_tasks():
            nonlocal server # Allow modification if server needs to be accessed (e.g. server.should_exit)
            try:
                async with anyio.create_task_group() as tg:
                    # Start background tasks (e.g., RAG indexer)
                    # `application_startup` (called by Starlette) prepares everything.
                    # `start_background_tasks` actually launches them in the task group.
                    await start_background_tasks(tg)
                    
                    # Start the Uvicorn server
                    logger.info(f"Starting Uvicorn server for SSE transport on http://0.0.0.0:{port}")
                    logger.info(f"Dashboard available at http://localhost:{port}")
                    logger.info(f"Admin token will be displayed by server startup sequence if generated/loaded.")
                    logger.info("Press Ctrl+C to shut down the server gracefully.")
                    
                    await server.serve()
                    
                    # This part is reached after server.serve() finishes (e.g., on shutdown signal)
                    logger.info("Uvicorn server has stopped. Waiting for background tasks to finalize...")
            except Exception as e: # Catch errors during server run or task group setup
                logger.critical(f"Fatal error during SSE server execution: {e}", exc_info=True)
                # Ensure g.server_running is false so other parts know to stop
                g.server_running = False 
                # Consider re-raising or exiting if this is a critical unrecoverable error
            finally:
                logger.info("SSE server and background task group scope exited.")
                # application_shutdown is called by Starlette's on_shutdown event.

        try:
            anyio.run(run_sse_server_with_bg_tasks)
        except KeyboardInterrupt: # Should be handled by signal handlers and graceful shutdown
            logger.info("Keyboard interrupt received by AnyIO runner. Server should be shutting down.")
        except SystemExit as e: # Catch SystemExit from application_startup
            logger.error(f"SystemExit caught: {e}. Server will not start.")
            sys.exit(e.code if isinstance(e.code, int) else 1)


    elif transport == "stdio":
        # Handle stdio transport (Original main.py:2639-2656 - arun function)
        # For stdio, we don't use Uvicorn or Starlette's HTTP capabilities.
        # We directly run the MCPLowLevelServer with stdio streams.
        
        async def run_stdio_server_with_bg_tasks():
            try:
                # Perform application startup manually for stdio mode as Starlette lifecycle isn't used.
                await application_startup(project_dir_path_str=project_dir, admin_token_param=admin_token_cli)
                
                async with anyio.create_task_group() as tg:
                    await start_background_tasks(tg) # Start RAG indexer etc.
                    
                    logger.info("Starting MCP server with stdio transport.")
                    logger.info(f"Admin token: {g.admin_token}") # Display admin token for stdio mode
                    logger.info("Press Ctrl+C to shut down.")
                    
                    # Import stdio_server from mcp library
                    try:
                        from mcp.server.stdio import stdio_server
                    except ImportError:
                        logger.error("Failed to import mcp.server.stdio. Stdio transport is unavailable.")
                        return

                    try:
                        async with stdio_server() as streams:
                            # mcp_app_instance is created in main_app.py and imported
                            await mcp_app_instance.run(
                                streams[0], # input_stream
                                streams[1], # output_stream
                                mcp_app_instance.create_initialization_options()
                            )
                    except Exception as e_mcp_run: # Catch errors from mcp_app_instance.run
                        logger.error(f"Error during MCP stdio server run: {e_mcp_run}", exc_info=True)
                    finally:
                        logger.info("MCP stdio server run finished.")
                        # Ensure g.server_running is false to stop background tasks
                        g.server_running = False 
                
            except Exception as e: # Catch errors during stdio setup or task group
                logger.critical(f"Fatal error during stdio server execution: {e}", exc_info=True)
                g.server_running = False
            finally:
                logger.info("Stdio server and background task group scope exited.")
                # Manually call application_shutdown for stdio mode
                await application_shutdown()

        try:
            anyio.run(run_stdio_server_with_bg_tasks)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received by AnyIO runner for stdio. Server should be shutting down.")
        except SystemExit as e: # Catch SystemExit from application_startup
            logger.error(f"SystemExit caught: {e}. Server will not start.")
            sys.exit(e.code if isinstance(e.code, int) else 1)
            
    else: # Should not happen due to click.Choice
        logger.error(f"Invalid transport type specified: {transport}")
        click.echo(f"Error: Invalid transport type '{transport}'. Choose 'stdio' or 'sse'.", err=True)
        sys.exit(1)

    logger.info("MCP Server has shut down.")
    sys.exit(0) # Explicitly exit after cleanup if not already exited by SystemExit

# This allows running `python -m mcp_server_src.cli --port ...`
if __name__ == "__main__":
    main_cli()