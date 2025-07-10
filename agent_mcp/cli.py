# Agent-MCP/mcp_template/mcp_server_src/cli.py
import click
import uvicorn  # For running the Starlette app in SSE mode
import anyio  # For running async functions and task groups
import os
import sys
import json
import sqlite3
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv, dotenv_values

# Load environment variables before importing other modules
# Try explicit paths

# Get the directory of the current script
script_dir = Path(__file__).resolve().parent

# Try parent directories
for parent_level in range(3):  # Go up to 3 levels
    env_path = script_dir / (".." * parent_level) / ".env"
    env_path = env_path.resolve()
    print(f"Trying to load .env from: {env_path}")
    if env_path.exists():
        print(f"Found .env at: {env_path}")
        env_vars = dotenv_values(str(env_path))
        print(f"Loaded variables: {list(env_vars.keys())}")
        print(
            f"OPENAI_API_KEY from file: {env_vars.get('OPENAI_API_KEY', 'NOT FOUND')[:10]}..."
        )
        # Manually set the environment variables
        for key, value in env_vars.items():
            os.environ[key] = value
        print(
            f"Set OPENAI_API_KEY in environ: {os.environ.get('OPENAI_API_KEY', 'NOT FOUND')[:10]}..."
        )
        break

# Also try normal load_dotenv in case
load_dotenv()

# Project-specific imports
# Ensure core.config (and thus logging) is initialized early.
from .core.config import (
    logger,
    CONSOLE_LOGGING_ENABLED,
    enable_console_logging,
)  # Logger is initialized in config.py
from .core import globals as g  # For g.server_running and other globals

# Import app creation and lifecycle functions
from .app.main_app import create_app, mcp_app_instance  # mcp_app_instance for stdio
from .app.server_lifecycle import (
    start_background_tasks,
    application_startup,
    application_shutdown,
)  # application_startup is called by create_app's on_startup
from .tui.display import TUIDisplay  # Import TUI display


def get_admin_token_from_db(project_dir: str) -> Optional[str]:
    """Get the admin token from the SQLite database."""
    try:
        # Construct the path to the database
        db_path = Path(project_dir).resolve() / ".agent" / "mcp_state.db"

        if not db_path.exists():
            return None

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Get the admin token from project_context table
        cursor.execute(
            "SELECT value FROM project_context WHERE context_key = ?",
            ("config_admin_token",),
        )
        row = cursor.fetchone()

        if row and row["value"]:
            try:
                admin_token = json.loads(row["value"])
                if isinstance(admin_token, str) and admin_token:
                    return admin_token
            except json.JSONDecodeError:
                pass

        conn.close()
        return None
    except Exception as e:
        logger.error(f"Error reading admin token from database: {e}")
        return None


# --- Click Command Definition ---
# This replicates the @click.command and options from the original main.py (lines 1936-1950)
@click.command(context_settings=dict(help_option_names=["-h", "--help"]))
@click.option(
    "--port",
    type=int,
    default=os.environ.get("PORT", 8080),  # Read from env var PORT if set, else 8080
    show_default=True,
    help="Port to listen on for SSE and HTTP dashboard.",
)
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse"], case_sensitive=False),
    default="sse",
    show_default=True,
    help="Transport type for MCP communication (stdio or sse).",
)
@click.option(
    "--project-dir",
    type=click.Path(file_okay=False, dir_okay=True, resolve_path=True, writable=True),
    default=".",
    show_default=True,
    help="Project directory. The .agent folder will be created/used here. Defaults to current directory.",
)
@click.option(
    "--admin-token",  # Renamed from admin_token_param for clarity
    "admin_token_cli",  # Variable name for the parameter
    type=str,
    default=None,
    help="Admin token for authentication. If not provided, one will be loaded from DB or generated.",
)
@click.option(
    "--debug",
    is_flag=True,
    default=os.environ.get("MCP_DEBUG", "false").lower()
    == "true",  # Default from env var
    help="Enable debug mode for the server (more verbose logging, Starlette debug pages).",
)
@click.option(
    "--no-tui",
    is_flag=True,
    default=False,
    help="Disable the terminal UI display (logs will still go to file).",
)
@click.option(
    "--advanced",
    is_flag=True,
    default=False,
    help="Enable advanced embeddings mode with larger dimension (3072) and more sophisticated code analysis.",
)
@click.option(
    "--git",
    is_flag=True,
    default=False,
    help="Enable experimental Git worktree support for parallel agent development (advanced users only).",
)
@click.option(
    "--no-index",
    is_flag=True,
    default=False,
    help="Disable automatic markdown file indexing. Allows selective manual indexing of specific content into the RAG system.",
)
def main_cli(
    port: int,
    transport: str,
    project_dir: str,
    admin_token_cli: Optional[str],
    debug: bool,
    no_tui: bool,
    advanced: bool,
    git: bool,
    no_index: bool,
):
    """
    Main Command-Line Interface for starting the MCP Server.

    The server supports two embedding modes:
    - Simple mode (default): Uses text-embedding-3-large (1536 dimensions) - indexes only markdown files and context
    - Advanced mode (--advanced): Uses text-embedding-3-large (3072 dimensions) - includes code analysis, task indexing

    Note: Switching between modes will require re-indexing all content.
    """
    # Set advanced embeddings mode before other imports that might use it
    if advanced:
        from .core import config

        config.ADVANCED_EMBEDDINGS = True
        # Update the dynamic configs
        config.EMBEDDING_MODEL = config.ADVANCED_EMBEDDING_MODEL
        config.EMBEDDING_DIMENSION = config.ADVANCED_EMBEDDING_DIMENSION
        logger.info(
            "Advanced embeddings mode enabled (3072 dimensions, text-embedding-3-large, code & task indexing)"
        )
    else:
        from .core.config import SIMPLE_EMBEDDING_DIMENSION, SIMPLE_EMBEDDING_MODEL

        logger.info(
            f"Using simple embeddings mode ({SIMPLE_EMBEDDING_DIMENSION} dimensions, {SIMPLE_EMBEDDING_MODEL}, markdown & context only)"
        )

    # Initialize Git worktree support if enabled
    if git:
        try:
            from .features.worktree_integration import enable_worktree_support

            worktree_enabled = enable_worktree_support()
            if worktree_enabled:
                logger.info(
                    "🌿 Git worktree support enabled for parallel agent development"
                )
            else:
                logger.warning(
                    "❌ Git worktree support could not be enabled - check requirements"
                )
                logger.warning("   Continuing without worktree support...")
        except ImportError:
            logger.error(
                "❌ Git worktree features not available - missing dependencies"
            )
            logger.warning("   Continuing without worktree support...")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Git worktree support: {e}")
            logger.warning("   Continuing without worktree support...")
    else:
        logger.info("Git worktree support disabled (use --git to enable)")

    if debug:
        os.environ["MCP_DEBUG"] = (
            "true"  # Ensure env var is set for Starlette debug mode
        )
        enable_console_logging()  # Enable console logging for debug mode
        logger.info(
            "Debug mode enabled via CLI flag or MCP_DEBUG environment variable."
        )
        logger.info("Console logging enabled for debug mode.")
        # Logging level might need to be adjusted here if not already handled by config.py
        # For now, config.py sets the base level. Uvicorn also has its own log level.
    else:
        os.environ["MCP_DEBUG"] = "false"

    # Determine if the TUI should be active
    # TUI is active if console logging is disabled AND --no-tui is NOT passed AND not in debug mode
    from .core.config import (
        CONSOLE_LOGGING_ENABLED as current_console_logging,
    )  # Get updated value

    tui_active = not current_console_logging and not no_tui and not debug

    if tui_active:
        logger.info(
            "TUI display mode is active. Standard console logging is suppressed."
        )
    elif current_console_logging or debug:
        logger.info("Standard console logging is enabled (TUI display mode is off).")
        print("MCP Server starting with standard console logging...")
    else:  # Console logging is off, and TUI is also off
        logger.info(
            "Console logging and TUI display are both disabled. Check log file for server messages."
        )

    # Log the embedding mode being used
    embedding_mode_info = "advanced" if advanced else "simple"
    if advanced:
        embedding_model_info = (
            config.EMBEDDING_MODEL if "config" in locals() else "text-embedding-3-large"
        )
        embedding_dim_info = (
            config.EMBEDDING_DIMENSION if "config" in locals() else 3072
        )
    else:
        from .core.config import SIMPLE_EMBEDDING_DIMENSION, SIMPLE_EMBEDDING_MODEL

        embedding_model_info = SIMPLE_EMBEDDING_MODEL
        embedding_dim_info = SIMPLE_EMBEDDING_DIMENSION

    logger.info(
        f"Attempting to start MCP Server: Port={port}, Transport={transport}, ProjectDir='{project_dir}'"
    )
    logger.info(
        f"Embedding Mode: {embedding_mode_info} (Model: {embedding_model_info}, Dimensions: {embedding_dim_info})"
    )

    # --- TUI Display Loop (if not disabled) ---
    async def tui_display_loop(
        cli_port: int,
        cli_transport: str,
        cli_project_dir: str,
        *,
        task_status=anyio.TASK_STATUS_IGNORED,
    ):
        task_status.started()
        logger.info("TUI display loop started.")
        tui = TUIDisplay()
        initial_display = True

        # Import required modules
        from .core import globals as globals_module
        from .db.actions.agent_db import get_all_active_agents_from_db
        from .db.actions.task_db import (
            get_all_tasks_from_db,
            get_task_by_id,
            get_tasks_by_agent_id,
        )
        from datetime import datetime
        from .tui.colors import TUITheme

        # Simple tracking of server status for display
        async def get_server_status():
            try:
                return {
                    "running": globals_module.server_running,
                    "status": "Running" if globals_module.server_running else "Stopped",
                    "port": cli_port,
                }
            except Exception as e:
                logger.error(f"Error getting server status: {e}")
                return {
                    "running": globals_module.server_running,
                    "status": "Error",
                    "port": cli_port,
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
                current_row += 2

                # Display simplified server info
                tui.move_cursor(current_row, 1)
                tui.clear_line()
                print(TUITheme.header(" MCP Server Running"))
                current_row += 2

                tui.move_cursor(current_row, 1)
                tui.clear_line()
                print(f"Project Directory: {TUITheme.info(cli_project_dir)}")
                current_row += 1

                tui.move_cursor(current_row, 1)
                tui.clear_line()
                print(f"Transport: {TUITheme.info(cli_transport)}")
                current_row += 1

                tui.move_cursor(current_row, 1)
                tui.clear_line()
                print(f"MCP Port: {TUITheme.info(str(cli_port))}")
                current_row += 1

                # Display admin token
                admin_token = get_admin_token_from_db(cli_project_dir)
                if admin_token:
                    tui.move_cursor(current_row, 1)
                    tui.clear_line()
                    print(f"Admin Token: {TUITheme.info(admin_token)}")
                    current_row += 1

                current_row += 2

                # Display dashboard instructions
                tui.move_cursor(current_row, 1)
                tui.clear_line()
                print(TUITheme.header(" Next Steps"))
                current_row += 2

                tui.move_cursor(current_row, 1)
                tui.clear_line()
                print("1. Open a new terminal window")
                current_row += 1

                tui.move_cursor(current_row, 1)
                tui.clear_line()
                dashboard_path = (
                    f"{cli_project_dir}/agent_mcp/dashboard"
                    if cli_project_dir != "."
                    else "agent_mcp/dashboard"
                )
                print(f"2. Navigate to: {TUITheme.info(dashboard_path)}")
                current_row += 1

                tui.move_cursor(current_row, 1)
                tui.clear_line()
                print(f"3. Run: {TUITheme.bold('npm run dev')}")
                current_row += 1

                tui.move_cursor(current_row, 1)
                tui.clear_line()
                print(f"4. Open: {TUITheme.info('http://localhost:3847')}")
                current_row += 3

                tui.move_cursor(current_row, 1)
                tui.clear_line()
                print(
                    TUITheme.warning(
                        "Keep this MCP server running while using the dashboard"
                    )
                )
                current_row += 2

                tui.move_cursor(current_row, 1)
                tui.clear_line()
                print(TUITheme.info("Press Ctrl+C to stop the MCP server"))
                current_row += 1

                # Clear remaining lines to prevent artifacts
                for row in range(current_row, tui.terminal_height):
                    tui.move_cursor(row, 1)
                    tui.clear_line()

                if initial_display:
                    initial_display = False

                await anyio.sleep(5)  # Refresh less frequently since display is simpler
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
        starlette_app = create_app(
            project_dir=project_dir, admin_token_cli=admin_token_cli
        )

        # Uvicorn configuration
        # log_config=None prevents Uvicorn from overriding our logging setup from config.py
        # (Original main.py:2630)
        uvicorn_config = uvicorn.Config(
            starlette_app,
            host="0.0.0.0",  # Listen on all available interfaces
            port=port,
            log_config=None,  # Use our custom logging setup
            access_log=False,  # Disable access logs
            lifespan="on",  # Ensure Starlette's on_startup/on_shutdown are used
        )
        server = uvicorn.Server(uvicorn_config)

        # Run Uvicorn server with background tasks managed by an AnyIO task group
        # This replaces the original run_server_with_background_tasks (main.py:2624)
        async def run_sse_server_with_bg_tasks():
            nonlocal server  # Allow modification if server needs to be accessed (e.g. server.should_exit)
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
                    logger.info(
                        f"Starting Uvicorn server for SSE transport on http://0.0.0.0:{port}"
                    )
                    logger.info(f"Dashboard available at http://localhost:{port}")
                    logger.info(
                        f"Admin token will be displayed by server startup sequence if generated/loaded."
                    )
                    logger.info("Press Ctrl+C to shut down the server gracefully.")

                    # Show standard startup messages only if TUI is not active
                    if not tui_active:
                        # Show AGENT MCP banner
                        from .tui.colors import get_responsive_agent_mcp_banner

                        print()
                        print(get_responsive_agent_mcp_banner())
                        print()
                        print(f"🚀 MCP Server running on port {port}")
                        print(f"📁 Project: {project_dir}")

                        # Display admin token from database
                        admin_token = get_admin_token_from_db(project_dir)
                        if admin_token:
                            print(f"🔑 Admin Token: {admin_token}")

                        print()
                        print("Next steps:")
                        dashboard_path = (
                            f"{project_dir}/agent_mcp/dashboard"
                            if project_dir != "."
                            else "agent_mcp/dashboard"
                        )
                        print(f"1. Open new terminal → cd {dashboard_path}")
                        print("2. Run: npm run dev")
                        print("3. Open: http://localhost:3847")
                        print()
                        print("Keep this server running. Press Ctrl+C to quit.")

                    await server.serve()

                    # This part is reached after server.serve() finishes (e.g., on shutdown signal)
                    logger.info(
                        "Uvicorn server has stopped. Waiting for background tasks to finalize..."
                    )
            except Exception as e:  # Catch errors during server run or task group setup
                logger.critical(
                    f"Fatal error during SSE server execution: {e}", exc_info=True
                )
                # Ensure g.server_running is false so other parts know to stop
                g.server_running = False
                # Consider re-raising or exiting if this is a critical unrecoverable error
            finally:
                logger.info("SSE server and background task group scope exited.")
                # application_shutdown is called by Starlette's on_shutdown event.

        try:
            anyio.run(run_sse_server_with_bg_tasks)
        except (
            KeyboardInterrupt
        ):  # Should be handled by signal handlers and graceful shutdown
            logger.info(
                "Keyboard interrupt received by AnyIO runner. Server should be shutting down."
            )
        except SystemExit as e:  # Catch SystemExit from application_startup
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
                await application_startup(
                    project_dir_path_str=project_dir, admin_token_param=admin_token_cli
                )

                async with anyio.create_task_group() as tg:
                    await start_background_tasks(tg)  # Start RAG indexer etc.

                    # Start TUI display loop if enabled
                    if tui_active:
                        await tg.start(
                            tui_display_loop, 0, transport, project_dir
                        )  # Port is 0 for stdio

                    logger.info("Starting MCP server with stdio transport.")
                    logger.info("Press Ctrl+C to shut down.")

                    # Show standard startup messages only if TUI is not active
                    if not tui_active:
                        # Show AGENT MCP banner
                        from .tui.colors import get_responsive_agent_mcp_banner

                        print()
                        print(get_responsive_agent_mcp_banner())
                        print()
                        print("🚀 MCP Server running (stdio transport)")
                        print("Server is ready for AI assistant connections.")

                        # Display admin token from database
                        admin_token = get_admin_token_from_db(project_dir)
                        if admin_token:
                            print(f"🔑 Admin Token: {admin_token}")

                        print("Use Ctrl+C to quit.")

                    # Import stdio_server from mcp library
                    try:
                        from mcp.server.stdio import stdio_server
                    except ImportError:
                        logger.error(
                            "Failed to import mcp.server.stdio. Stdio transport is unavailable."
                        )
                        return

                    try:
                        async with stdio_server() as streams:
                            # mcp_app_instance is created in main_app.py and imported
                            await mcp_app_instance.run(
                                streams[0],  # input_stream
                                streams[1],  # output_stream
                                mcp_app_instance.create_initialization_options(),
                            )
                    except (
                        Exception
                    ) as e_mcp_run:  # Catch errors from mcp_app_instance.run
                        logger.error(
                            f"Error during MCP stdio server run: {e_mcp_run}",
                            exc_info=True,
                        )
                    finally:
                        logger.info("MCP stdio server run finished.")
                        # Ensure g.server_running is false to stop background tasks
                        g.server_running = False

            except Exception as e:  # Catch errors during stdio setup or task group
                logger.critical(
                    f"Fatal error during stdio server execution: {e}", exc_info=True
                )
                g.server_running = False
            finally:
                logger.info("Stdio server and background task group scope exited.")
                # Manually call application_shutdown for stdio mode
                await application_shutdown()

        try:
            anyio.run(run_stdio_server_with_bg_tasks)
        except KeyboardInterrupt:
            logger.info(
                "Keyboard interrupt received by AnyIO runner for stdio. Server should be shutting down."
            )
        except SystemExit as e:  # Catch SystemExit from application_startup
            logger.error(f"SystemExit caught: {e}. Server will not start.")
            if tui_active:
                tui = TUIDisplay()
                tui.clear_screen()
            sys.exit(e.code if isinstance(e.code, int) else 1)

    else:  # Should not happen due to click.Choice
        logger.error(f"Invalid transport type specified: {transport}")
        click.echo(
            f"Error: Invalid transport type '{transport}'. Choose 'stdio' or 'sse'.",
            err=True,
        )
        sys.exit(1)

    logger.info("MCP Server has shut down.")

    # Clear console one last time if TUI was active
    if tui_active:
        tui = TUIDisplay()
        tui.clear_screen()

    sys.exit(0)  # Explicitly exit after cleanup if not already exited by SystemExit


# This allows running `python -m mcp_server_src.cli --port ...`
if __name__ == "__main__":
    main_cli()
