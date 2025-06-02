#!/usr/bin/env python3
"""
Main CLI entry point for agent-mcp with subcommands

This provides a more organized command structure:
- agent-mcp server    (run the server)
- agent-mcp migrate   (database migration)
- agent-mcp index     (run RAG indexing)
- agent-mcp version   (show version)
"""

import click
import sys
import os
from pathlib import Path
from typing import Optional
import logging
import traceback

# Add parent to path for imports when running as script
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_mcp import __version__
from agent_mcp.cli import main_cli

# Set up enhanced logging for CLI routing
cli_logger = logging.getLogger('agent_mcp.cli_main')
cli_logger.setLevel(logging.DEBUG)

# Add file handler for CLI-specific logs
cli_log_file = 'agent_mcp_cli.log'
cli_file_handler = logging.FileHandler(cli_log_file, mode='a')
cli_file_handler.setLevel(logging.DEBUG)
cli_formatter = logging.Formatter(
    '%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s - %(funcName)s:%(lineno)d - %(message)s',
    datefmt='%H:%M:%S'
)
cli_file_handler.setFormatter(cli_formatter)
cli_logger.addHandler(cli_file_handler)

cli_logger.info("=" * 80)
cli_logger.info("CLI MAIN MODULE LOADED")
cli_logger.info("=" * 80)


@click.group(invoke_without_command=True, context_settings=dict(help_option_names=['-h', '--help']))
@click.version_option(version=__version__, prog_name="agent-mcp")
@click.pass_context
def cli(ctx):
    """
    Agent MCP - Multi-Agent Collaboration Platform
    
    A powerful framework for building and managing multi-agent systems
    with intelligent task distribution and RAG capabilities.
    
    Run without arguments to launch the interactive control center.
    
    For detailed documentation, visit: https://github.com/your-org/agent-mcp
    """
    cli_logger.info(f"CLI invoked with args: {sys.argv}")
    cli_logger.info(f"Invoked subcommand: {ctx.invoked_subcommand}")
    
    # If no command is provided, launch the unified interface
    if ctx.invoked_subcommand is None:
        cli_logger.info("No subcommand provided - launching unified interface")
        
        # Disable console logging for UI mode (but keep file logging)
        import logging
        root_logger = logging.getLogger()
        # Remove console handlers to prevent debug logs from showing in UI
        for handler in root_logger.handlers[:]:
            if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
                root_logger.removeHandler(handler)
                cli_logger.info("Removed console handler for UI mode")
        
        from .cli_commands.unified_interface_v2 import run_enhanced_interface
        run_enhanced_interface()
    else:
        cli_logger.info(f"Subcommand '{ctx.invoked_subcommand}' will be invoked")


@cli.command()
@click.option(
    "--port",
    type=int,
    default=8080,
    help="Port to bind the server to (SSE mode only)"
)
@click.option(
    "--transport",
    type=click.Choice(["stdio", "sse"], case_sensitive=False),
    default="sse",
    help="Transport type: stdio for MCP protocol, sse for web dashboard"
)
@click.option(
    "--project-dir",
    type=click.Path(exists=False, file_okay=False, dir_okay=True, path_type=Path),
    default=".",
    help="Project directory path (will be created if it doesn't exist)"
)
@click.option(
    "--admin-token",
    type=str,
    help="Admin token for authentication (generated if not provided)"
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug logging"
)
@click.option(
    "--no-tui",
    is_flag=True,
    help="Disable Terminal UI (show raw logs)"
)
def server(port: int, transport: str, project_dir: Path, admin_token: Optional[str], 
          debug: bool, no_tui: bool):
    """Run the Agent MCP server
    
    Examples:
    
        # Run with web dashboard on default port
        agent-mcp server
        
        # Run on custom port with specific project
        agent-mcp server --port 9000 --project-dir ./my-project
        
        # Run in stdio mode for MCP protocol
        agent-mcp server --transport stdio
    """
    cli_logger.info("=" * 80)
    cli_logger.info("SERVER COMMAND INVOKED")
    cli_logger.info("=" * 80)
    cli_logger.info(f"Parameters:")
    cli_logger.info(f"  port: {port}")
    cli_logger.info(f"  transport: {transport}")
    cli_logger.info(f"  project_dir: {project_dir}")
    cli_logger.info(f"  admin_token: {'[PROVIDED]' if admin_token else 'None'}")
    cli_logger.info(f"  debug: {debug}")
    cli_logger.info(f"  no_tui: {no_tui}")
    
    # Convert Path to string for compatibility
    project_dir_str = str(project_dir)
    
    # Import the actual server running logic
    import asyncio
    import uvicorn
    import anyio
    from agent_mcp.app.main_app import create_app
    from agent_mcp.app.server_lifecycle import start_background_tasks
    from agent_mcp.core.config import logger, CONSOLE_LOGGING_ENABLED
    from agent_mcp.core import globals as g
    from agent_mcp.tui.display import TUIDisplay
    
    # Debug is always on for CLI logging, but respect the flag for Starlette
    if debug:
        os.environ["MCP_DEBUG"] = "true"  # For Starlette debug mode
        cli_logger.info("Debug flag passed - enabling Starlette debug mode")
    else:
        os.environ["MCP_DEBUG"] = "false"
    
    # Console logging is always enabled for CLI
    tui_active = False  # Never use TUI for CLI
    
    logger.info("Standard console logging is enabled.")
    print("MCP Server starting with console logging...")
    
    logger.info(f"Attempting to start MCP Server: Port={port}, Transport={transport}, ProjectDir='{project_dir_str}'")
    
    if transport == "sse":
        # Create the Starlette application instance
        starlette_app = create_app(project_dir=project_dir_str, admin_token_cli=admin_token)
        
        # Uvicorn configuration
        uvicorn_config = uvicorn.Config(
            starlette_app,
            host="0.0.0.0",
            port=port,
            log_config=None,
            access_log=False,
            lifespan="on"
        )
        server = uvicorn.Server(uvicorn_config)
        
        async def run_sse_server_with_bg_tasks():
            try:
                async with anyio.create_task_group() as tg:
                    # Start background tasks
                    await start_background_tasks(tg)
                    
                    # Start the Uvicorn server
                    logger.info(f"Starting Uvicorn server for SSE transport on http://0.0.0.0:{port}")
                    logger.info(f"Dashboard available at http://localhost:{port}")
                    
                    if not tui_active:
                        print(f"MCP Server running on http://0.0.0.0:{port} (SSE Transport)")
                        print(f"Dashboard: http://localhost:{port}")
                        print(f"Admin Token: {g.admin_token}")
                        print("Press Ctrl+C to quit.")
                    
                    await server.serve()
                    
                    logger.info("Uvicorn server has stopped.")
            except Exception as e:
                logger.critical(f"Fatal error during SSE server execution: {e}", exc_info=True)
                g.server_running = False
            finally:
                logger.info("SSE server and background task group scope exited.")
        
        try:
            anyio.run(run_sse_server_with_bg_tasks)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received. Server shutting down.")
        except SystemExit as e:
            logger.error(f"SystemExit caught: {e}. Server will not start.")
            if tui_active:
                tui = TUIDisplay()
                tui.clear_screen()
            sys.exit(e.code if isinstance(e.code, int) else 1)
    else:
        print(f"Transport type '{transport}' not implemented in this simplified version")


@cli.command()
@click.option('--check', is_flag=True, help='Check current database version')
@click.option('--force', is_flag=True, help='Force migration without confirmation')
@click.option('--no-backup', is_flag=True, help='Skip backup creation')
@click.option('--config', is_flag=True, help='Show migration configuration')
@click.option('--set', 'config_set', help='Set configuration value (KEY=VALUE)')
@click.option('--list-backups', is_flag=True, help='List available database backups')
@click.option('--restore', 'backup_name', help='Restore database from backup')
@click.option('--logs', is_flag=True, help='Show migration logs')
@click.option('--project-dir', type=click.Path(), default=".", 
              help='Project directory containing .agent folder')
def migrate(check: bool, force: bool, no_backup: bool, config: bool, 
           config_set: Optional[str], list_backups: bool, backup_name: Optional[str],
           logs: bool, project_dir: str):
    """Manage database migrations
    
    Examples:
    
        # Check current version
        agent-mcp migrate --check
        
        # Run migration interactively
        agent-mcp migrate
        
        # Force migration without prompts
        agent-mcp migrate --force
        
        # Configure migration settings
        agent-mcp migrate --set auto_migrate=false
        
        # List available backups
        agent-mcp migrate --list-backups
        
        # Restore from backup
        agent-mcp migrate --restore
        agent-mcp migrate --restore mcp_state_backup_20250602.db
        
        # Show migration logs
        agent-mcp migrate --logs
    """
    # Set project directory
    os.environ["MCP_PROJECT_DIR"] = str(Path(project_dir).resolve())
    
    # Import here to avoid circular imports
    import asyncio
    from agent_mcp.cli_commands.migrate_command import (
        check_version, run_migration, show_config, set_config,
        list_backups as list_backups_func, restore_backup, show_migration_logs
    )
    
    if check:
        asyncio.run(check_version())
    elif config:
        show_config()
    elif config_set:
        set_config(config_set)
    elif list_backups:
        asyncio.run(list_backups_func())
    elif backup_name is not None:
        asyncio.run(restore_backup(backup_name))
    elif logs:
        asyncio.run(show_migration_logs())
    else:
        asyncio.run(run_migration(force=force, no_backup=no_backup))


# Legacy commands - kept for compatibility but redirect to unified interface
@cli.command(hidden=True)  # Hide from help
def manager():
    """(Deprecated) Use 'agent-mcp' without arguments instead"""
    click.echo("Note: 'manager' command is deprecated. Launching control center...")
    from .cli_commands.unified_interface import run_unified_interface
    run_unified_interface()


@cli.command(hidden=True)  # Hide from help
def explorer():
    """(Deprecated) Use 'agent-mcp' without arguments instead"""
    click.echo("Note: 'explorer' command is deprecated. Launching control center...")
    from .cli_commands.unified_interface import run_unified_interface
    run_unified_interface()


@cli.command()
@click.option('--project-dir', type=click.Path(exists=True), default=".",
              help='Project directory to index')
@click.option('--force', is_flag=True, help='Force re-indexing of all files')
def index(project_dir: str, force: bool):
    """Run RAG indexing on project files
    
    Examples:
    
        # Index current directory
        agent-mcp index
        
        # Force re-index all files
        agent-mcp index --force
    """
    cli_logger.info("=" * 80)
    cli_logger.info("INDEX COMMAND INVOKED")
    cli_logger.info("=" * 80)
    cli_logger.info(f"Parameters:")
    cli_logger.info(f"  project_dir: {project_dir}")
    cli_logger.info(f"  force: {force}")
    
    os.environ["MCP_PROJECT_DIR"] = str(Path(project_dir).resolve())
    cli_logger.info(f"Set MCP_PROJECT_DIR to: {os.environ['MCP_PROJECT_DIR']}")
    
    # Import and run indexing
    import asyncio
    from agent_mcp.features.rag.indexing import index_project_files
    
    async def run_indexing():
        from agent_mcp.core.config import logger
        logger.info(f"Starting RAG indexing for: {project_dir}")
        
        try:
            stats = await index_project_files()
            
            print(f"\n✅ Indexing completed!")
            print(f"   Files processed: {stats.get('files_processed', 0)}")
            print(f"   Chunks created: {stats.get('chunks_created', 0)}")
            print(f"   Errors: {stats.get('errors', 0)}")
            
        except Exception as e:
            print(f"❌ Indexing failed: {e}")
            sys.exit(1)
    
    asyncio.run(run_indexing())


@cli.command()
def version():
    """Show version and system information"""
    cli_logger.info("VERSION COMMAND INVOKED")
    
    import platform
    
    print(f"Agent MCP v{__version__}")
    print(f"Python {platform.python_version()}")
    print(f"Platform: {platform.platform()}")
    
    # Check for optional dependencies
    try:
        import openai
        print(f"OpenAI SDK: v{openai.__version__}")
    except ImportError:
        print("OpenAI SDK: Not installed")
    
    try:
        import sqlite_vec
        print("SQLite-vec: Installed")
    except ImportError:
        print("SQLite-vec: Not installed")


@cli.command()
@click.argument('project_name')
@click.option('--template', type=click.Choice(['basic', 'advanced']), 
              default='basic', help='Project template to use')
def init(project_name: str, template: str):
    """Initialize a new Agent MCP project
    
    Examples:
    
        # Create basic project
        agent-mcp init my-project
        
        # Create advanced project with examples
        agent-mcp init my-project --template advanced
    """
    project_path = Path(project_name).resolve()
    
    if project_path.exists():
        print(f"❌ Directory '{project_name}' already exists")
        sys.exit(1)
    
    print(f"🚀 Creating new Agent MCP project: {project_name}")
    
    # Create project structure
    project_path.mkdir(parents=True)
    (project_path / ".agent").mkdir()
    
    # Create example .env file
    env_content = """# Agent MCP Configuration
OPENAI_API_KEY=your-api-key-here

# Optional configurations
# AGENT_MCP_MIGRATION_AUTO_MIGRATE=true
# AGENT_MCP_MIGRATION_INTERACTIVE=true
"""
    
    (project_path / ".env").write_text(env_content)
    
    # Create example configuration
    if template == 'advanced':
        # Add example files for advanced template
        (project_path / "README.md").write_text(f"# {project_name}\n\nAn Agent MCP project.\n")
        (project_path / "docs").mkdir()
        (project_path / "src").mkdir()
    
    print(f"✅ Project created at: {project_path}")
    print(f"\nNext steps:")
    print(f"1. cd {project_name}")
    print(f"2. Edit .env and add your OpenAI API key")
    print(f"3. Run: agent-mcp server")


def main():
    """Main entry point for agent-mcp command"""
    cli_logger.info("=" * 80)
    cli_logger.info("AGENT-MCP MAIN ENTRY POINT")
    cli_logger.info("=" * 80)
    cli_logger.info(f"Command line: {' '.join(sys.argv)}")
    cli_logger.info(f"Current directory: {os.getcwd()}")
    
    try:
        cli()
    except Exception as e:
        cli_logger.error(f"Unhandled exception in main: {e}")
        cli_logger.debug(f"Traceback: {traceback.format_exc()}")
        raise


if __name__ == "__main__":
    main()