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

# Add parent to path for imports when running as script
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent))

from agent_mcp import __version__
from agent_mcp.cli import main_cli


@click.group(context_settings=dict(help_option_names=['-h', '--help']))
@click.version_option(version=__version__, prog_name="agent-mcp")
def cli():
    """
    Agent MCP - Multi-Agent Collaboration Platform
    
    A powerful framework for building and managing multi-agent systems
    with intelligent task distribution and RAG capabilities.
    
    For detailed documentation, visit: https://github.com/your-org/agent-mcp
    """
    pass


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
    # Convert Path to string for compatibility
    project_dir_str = str(project_dir)
    
    # Import and run the main CLI directly
    # This avoids the click command decorator issues
    import sys
    
    # Save original argv
    original_argv = sys.argv.copy()
    
    try:
        # Build new argv
        sys.argv = ['agent-mcp']
        sys.argv.extend(['--port', str(port)])
        sys.argv.extend(['--transport', transport])
        sys.argv.extend(['--project-dir', project_dir_str])
        if admin_token:
            sys.argv.extend(['--admin-token', admin_token])
        if debug:
            sys.argv.append('--debug')
        if no_tui:
            sys.argv.append('--no-tui')
        
        # Import and call the main function from cli module
        from agent_mcp.cli import main
        main()
    except SystemExit:
        pass  # Don't propagate SystemExit
    finally:
        # Restore original argv
        sys.argv = original_argv


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
    os.environ["MCP_PROJECT_DIR"] = str(Path(project_dir).resolve())
    
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
    cli()


if __name__ == "__main__":
    main()