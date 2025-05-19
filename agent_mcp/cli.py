# Agent-MCP/mcp_template/mcp_server_src/cli.py
import click
import uvicorn # For running the Starlette app in SSE mode
import anyio # For running async functions and task groups
import os
import sys
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv, dotenv_values

# Load environment variables before importing other modules
# Try explicit paths

# Get the directory of the current script
script_dir = Path(__file__).resolve().parent

# Try parent directories
for parent_level in range(3):  # Go up to 3 levels
    env_path = script_dir / ('..' * parent_level) / '.env'
    env_path = env_path.resolve()
    print(f"Trying to load .env from: {env_path}")
    if env_path.exists():
        print(f"Found .env at: {env_path}")
        env_vars = dotenv_values(str(env_path))
        print(f"Loaded variables: {list(env_vars.keys())}")
        print(f"OPENAI_API_KEY from file: {env_vars.get('OPENAI_API_KEY', 'NOT FOUND')[:10]}...")
        # Manually set the environment variables
        for key, value in env_vars.items():
            os.environ[key] = value
        print(f"Set OPENAI_API_KEY in environ: {os.environ.get('OPENAI_API_KEY', 'NOT FOUND')[:10]}...")
        break

# Also try normal load_dotenv in case
load_dotenv()

# Project-specific imports
# Ensure core.config (and thus logging) is initialized early.
from .core.config import logger, CONSOLE_LOGGING_ENABLED # Logger is initialized in config.py
from .core import globals as g # For g.server_running and other globals
# Import app creation and lifecycle functions
from .app.main_app import create_app, mcp_app_instance # mcp_app_instance for stdio
from .app.server_lifecycle import start_background_tasks, application_startup, application_shutdown # application_startup is called by create_app's on_startup
from .tui.display import TUIDisplay # Import TUI display

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
@click.option(
    "--no-tui",
    is_flag=True,
    default=False,
    help="Disable the terminal UI display (logs will still go to file)."
)
def main_cli(port: int, transport: str, project_dir: str, admin_token_cli: Optional[str], debug: bool, no_tui: bool):
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

    # Determine if the TUI should be active
    # TUI is active if console logging is generally disabled by config AND --no-tui is NOT passed
    tui_active = not CONSOLE_LOGGING_ENABLED and not no_tui
    
    if tui_active:
        logger.info("TUI display mode is active. Standard console logging is suppressed.")
    elif CONSOLE_LOGGING_ENABLED:
        logger.info("Standard console logging is enabled (TUI display mode is off).")
        print("MCP Server starting with standard console logging...")
    else:  # Console logging is off, and TUI is also off
        logger.info("Console logging and TUI display are both disabled. Check log file for server messages.")

    logger.info(f"Attempting to start MCP Server: Port={port}, Transport={transport}, ProjectDir='{project_dir}'")

    # --- TUI Display Loop (if not disabled) ---
    async def tui_display_loop(cli_port: int, cli_transport: str, cli_project_dir: str, *, task_status=anyio.TASK_STATUS_IGNORED):
        task_status.started()
        logger.info("TUI display loop started.")
        tui = TUIDisplay()
        initial_display = True
        
        # Import required modules
        from .core import globals as globals_module
        from .db.actions.agent_db import get_all_active_agents_from_db
        from .db.actions.task_db import get_all_tasks_from_db, get_task_by_id, get_tasks_by_agent_id
        from datetime import datetime
        from .tui.colors import TUITheme
        
        # Simple tracking of server status for display
        async def get_server_status():
            try:
                agents = get_all_active_agents_from_db()
                tasks = get_all_tasks_from_db()
                return {
                    'running': globals_module.server_running,
                    'status': 'Running' if globals_module.server_running else 'Stopped',
                    'port': cli_port,
                    'agent_count': len(agents),
                    'task_count': len(tasks)
                }
            except Exception as e:
                logger.error(f"Error getting server status: {e}")
                return {
                    'running': globals_module.server_running,
                    'status': 'Error',
                    'port': cli_port,
                    'agent_count': 0,
                    'task_count': 0
                }
        
        try:
            # Wait a moment for server initialization to complete
            await anyio.sleep(2)
            
            # Setup alternate screen and hide cursor for smoother display
            tui.enable_alternate_screen()
            tui.hide_cursor()
            
            first_draw = True
            
            while globals_module.server_running:
                server_status = await get_server_status()
                
                # Clear screen only on first draw
                if first_draw:
                    tui.clear_screen()
                    first_draw = False
                
                # Move to top and redraw
                tui.move_cursor(1, 1)
                current_row = tui.draw_header(clear_first=False)
                
                # Position cursor for status bar
                tui.move_cursor(current_row, 1)
                tui.draw_status_bar(server_status)
                current_row += 1
                
                # Display basic info
                tui.move_cursor(current_row, 1)
                tui.clear_line()
                print(TUITheme.header(" Server Information"))
                current_row += 1
                
                tui.move_cursor(current_row, 1)
                tui.clear_line()
                print(f"Transport: {cli_transport}")
                current_row += 1
                
                tui.move_cursor(current_row, 1)
                tui.clear_line()
                print(f"Project Directory: {cli_project_dir}")
                current_row += 1
                
                # Display full dashboard URL
                dashboard_url = f"http://localhost:{cli_port}"
                tui.move_cursor(current_row, 1)
                tui.clear_line()
                print(f"Dashboard URL: {TUITheme.info(dashboard_url)}")
                current_row += 1
                
                # Display full admin token in bold
                tui.move_cursor(current_row, 1)
                tui.clear_line()
                print(f"Admin Token: {TUITheme.bold(globals_module.admin_token)}" if globals_module.admin_token else "Admin Token: N/A")
                current_row += 1
                
                # Display agents section
                current_row += 1
                tui.move_cursor(current_row, 1)
                tui.clear_line()
                print(TUITheme.header(" Agents"))
                current_row += 1
                if server_status['agent_count'] > 0:
                    agents = get_all_active_agents_from_db()
                    for i, agent in enumerate(agents):
                        agent_color = agent.get('color', '#FFFFFF')
                        agent_status_db = agent.get('status', 'idle')
                        agent_token = agent.get('token', 'Unknown')
                        current_task = agent.get('current_task')
                        
                        # Determine actual status based on tasks
                        actual_status = agent_status_db
                        status_color = TUITheme.success
                        
                        if current_task:
                            task = get_task_by_id(current_task)
                            if task:
                                task_status = task.get('status', 'unknown')
                                if task_status == 'completed':
                                    # Check if there's a next task
                                    pending_tasks = get_tasks_by_agent_id(agent['agent_id'], status_filter='pending')
                                    next_tasks = [t for t in pending_tasks if t['task_id'] != current_task]
                                    if not next_tasks:
                                        actual_status = 'inactive'
                                        status_color = TUITheme.dim
                                    else:
                                        actual_status = 'ready'
                                        status_color = TUITheme.info
                                elif task_status in ['in_progress', 'working']:
                                    actual_status = 'working...'
                                    status_color = TUITheme.warning
                                else:
                                    actual_status = task_status
                        else:
                            # No current task, check for pending tasks
                            pending_tasks = get_tasks_by_agent_id(agent['agent_id'], status_filter='pending')
                            if pending_tasks:
                                actual_status = 'ready'
                                status_color = TUITheme.info
                            else:
                                actual_status = 'inactive'
                                status_color = TUITheme.dim
                        
                        # Convert color to ANSI codes
                        color_code = agent_color.replace('#', '')
                        try:
                            r = int(color_code[0:2], 16)
                            g = int(color_code[2:4], 16) 
                            b = int(color_code[4:6], 16)
                            color_start = f"\033[38;2;{r};{g};{b}m"
                            color_end = "\033[0m"
                        except:
                            color_start = ""
                            color_end = ""
                        
                        # Agent header with colored bullet
                        tui.move_cursor(current_row, 1)
                        tui.clear_line()
                        print(f"{color_start}● {agent['agent_id']}{color_end}")
                        current_row += 1
                        
                        tui.move_cursor(current_row, 1)
                        tui.clear_line()
                        print(f"  Status: {status_color(actual_status.capitalize())}")
                        current_row += 1
                        
                        tui.move_cursor(current_row, 1)
                        tui.clear_line()
                        print(f"  Token: {TUITheme.dim(agent_token)}")
                        current_row += 1
                        
                        # Current task info
                        if current_task:
                            task = get_task_by_id(current_task)
                            if task:
                                task_title = task.get('title', 'Unknown Task')
                                task_status = task.get('status', 'unknown')
                                
                                tui.move_cursor(current_row, 1)
                                tui.clear_line()
                                print(f"  Current Task: {TUITheme.info(task_title)}")
                                current_row += 1
                                
                                tui.move_cursor(current_row, 1)
                                tui.clear_line()
                                print(f"  Task Status: {task_status}")
                                current_row += 1
                                
                                # Calculate how long they've been working on it
                                if task.get('assigned_at'):
                                    started = datetime.fromisoformat(task['assigned_at'])
                                    duration = datetime.now() - started
                                    total_minutes = duration.total_seconds() / 60
                                    hours = int(total_minutes // 60)
                                    minutes = int(total_minutes % 60)
                                    
                                    if hours > 0:
                                        time_str = f"{hours}h {minutes}m"
                                    else:
                                        time_str = f"{minutes}m"
                                    
                                    tui.move_cursor(current_row, 1)
                                    tui.clear_line()
                                    print(f"  Working for: {TUITheme.warning(time_str)}")
                                    current_row += 1
                        else:
                            tui.move_cursor(current_row, 1)
                            tui.clear_line()
                            print(f"  Current Task: {TUITheme.dim('None')}")
                            current_row += 1
                        
                        # Show next task if available
                        pending_tasks = get_tasks_by_agent_id(agent['agent_id'], status_filter='pending')
                        if pending_tasks:
                            # Filter out current task from pending tasks
                            next_tasks = [t for t in pending_tasks if t['task_id'] != current_task]
                            if next_tasks:
                                next_task = next_tasks[0]
                                tui.move_cursor(current_row, 1)
                                tui.clear_line()
                                print(f"  Next Task: {TUITheme.dim(next_task.get('title', 'Unknown Task'))}")
                                current_row += 1
                        
                        # Add spacing between agents
                        if i < len(agents) - 1:
                            current_row += 1
                else:
                    tui.move_cursor(current_row, 1)
                    tui.clear_line()
                    print(TUITheme.dim("No active agents"))
                    current_row += 1
                
                current_row += 1
                tui.move_cursor(current_row, 1)
                tui.clear_line()
                print(TUITheme.info("Press Ctrl+C to quit"))
                current_row += 1
                
                # Clear remaining lines to prevent artifacts
                for row in range(current_row, tui.terminal_height):
                    tui.move_cursor(row, 1)
                    tui.clear_line()
                
                if initial_display:
                    initial_display = False
                
                await anyio.sleep(2)  # Refresh TUI display every 2 seconds
        except anyio.get_cancelled_exc_class():
            logger.info("TUI display loop cancelled.")
        finally:
            # Cleanup the terminal
            tui.show_cursor()
            tui.disable_alternate_screen()
            tui.clear_screen()
            print("MCP Server TUI has exited.")
            logger.info("TUI display loop finished.")

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
            access_log=False,  # Disable access logs
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
                    
                    # Start TUI display loop if enabled
                    if tui_active:
                        await tg.start(tui_display_loop, port, transport, project_dir)
                    
                    # Start the Uvicorn server
                    logger.info(f"Starting Uvicorn server for SSE transport on http://0.0.0.0:{port}")
                    logger.info(f"Dashboard available at http://localhost:{port}")
                    logger.info(f"Admin token will be displayed by server startup sequence if generated/loaded.")
                    logger.info("Press Ctrl+C to shut down the server gracefully.")
                    
                    # Show standard startup messages only if TUI is not active
                    if not tui_active:
                        print(f"MCP Server running on http://0.0.0.0:{port} (SSE Transport)")
                        print(f"Dashboard: http://localhost:{port}")
                        print("Press Ctrl+C to quit.")
                    
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
            if tui_active:
                tui = TUIDisplay()
                tui.clear_screen()
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
                    
                    # Start TUI display loop if enabled
                    if tui_active:
                        await tg.start(tui_display_loop, 0, transport, project_dir)  # Port is 0 for stdio
                    
                    logger.info("Starting MCP server with stdio transport.")
                    logger.info(f"Admin token: {g.admin_token}") # Display admin token for stdio mode
                    logger.info("Press Ctrl+C to shut down.")
                    
                    # Show standard startup messages only if TUI is not active
                    if not tui_active:
                        print(f"MCP Server running (stdio Transport). Admin Token: {g.admin_token}")
                        print("Use Ctrl+C to quit.")
                    
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
            if tui_active:
                tui = TUIDisplay()
                tui.clear_screen()
            sys.exit(e.code if isinstance(e.code, int) else 1)
            
    else: # Should not happen due to click.Choice
        logger.error(f"Invalid transport type specified: {transport}")
        click.echo(f"Error: Invalid transport type '{transport}'. Choose 'stdio' or 'sse'.", err=True)
        sys.exit(1)

    logger.info("MCP Server has shut down.")
    
    # Clear console one last time if TUI was active
    if tui_active:
        tui = TUIDisplay()
        tui.clear_screen()
        
    sys.exit(0) # Explicitly exit after cleanup if not already exited by SystemExit

# This allows running `python -m mcp_server_src.cli --port ...`
if __name__ == "__main__":
    main_cli()