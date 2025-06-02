#!/usr/bin/env python3
"""
CLI command for database migration management

Usage:
    agent-mcp migrate [options]
    
Options:
    --check         Check current database version without migrating
    --force         Force migration without confirmation
    --no-backup     Skip backup creation
    --config        Show current migration configuration
    --set KEY=VAL   Set a migration configuration value
"""

import asyncio
import sys
import os
import argparse
from pathlib import Path
from typing import Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agent_mcp.db.migrations.migration_manager import MigrationManager, ensure_database_current
from agent_mcp.db.migrations.migration_config import migration_config
from agent_mcp.core.config import logger, get_agent_dir


async def check_version():
    """Check and display current database version"""
    manager = MigrationManager()
    
    try:
        from agent_mcp.db.connection import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Ensure migration table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL,
                description TEXT
            )
        """)
        
        # Get migration history
        cursor.execute("""
            SELECT version, applied_at, description 
            FROM schema_migrations 
            ORDER BY applied_at DESC
        """)
        migrations = cursor.fetchall()
        
        print(f"\n{'='*60}")
        print("DATABASE VERSION INFORMATION")
        print("="*60)
        print(f"Current Schema Version: {MigrationManager.CURRENT_VERSION}")
        
        if migrations:
            print(f"\nMigration History:")
            for version, applied_at, description in migrations:
                print(f"  • {version}: {description}")
                print(f"    Applied: {applied_at}")
        else:
            print("\nNo migration history found (legacy database)")
        
        conn.close()
        
    except Exception as e:
        print(f"Error checking version: {e}")
        return False
    
    return True


async def run_migration(force: bool = False, no_backup: bool = False):
    """Run database migration"""
    # Override config for this run
    original_interactive = migration_config.get('interactive')
    original_backup = migration_config.get('auto_backup')
    
    try:
        if force:
            migration_config.set('interactive', False)
        if no_backup:
            migration_config.set('auto_backup', False)
        
        success = await ensure_database_current()
        
        if success:
            print("\n✅ Migration completed successfully!")
        else:
            print("\n❌ Migration failed or was cancelled.")
            sys.exit(1)
            
    finally:
        # Restore original settings
        migration_config.set('interactive', original_interactive)
        migration_config.set('auto_backup', original_backup)


def show_config():
    """Display current migration configuration"""
    print(f"\n{'='*60}")
    print("MIGRATION CONFIGURATION")
    print("="*60)
    
    config_dict = migration_config.as_dict()
    
    for key, value in sorted(config_dict.items()):
        print(f"{key:.<30} {value}")
    
    print(f"\nConfiguration sources:")
    print(f"  1. Environment variables (AGENT_MCP_MIGRATION_*)")
    print(f"  2. Config file (.agent/migration.conf)")
    print(f"  3. Default values")


def set_config(key_value: str):
    """Set a configuration value"""
    if '=' not in key_value:
        print(f"Error: Invalid format. Use KEY=VALUE")
        return
    
    key, value = key_value.split('=', 1)
    key = key.strip().lower()
    value = value.strip()
    
    # Check if key exists
    if key not in migration_config.settings:
        print(f"Error: Unknown configuration key '{key}'")
        print(f"Valid keys: {', '.join(sorted(migration_config.settings.keys()))}")
        return
    
    # Convert value to appropriate type
    current_value = migration_config.settings[key]
    if isinstance(current_value, bool):
        value = value.lower() in ('true', '1', 'yes', 'on')
    elif isinstance(current_value, int):
        try:
            value = int(value)
        except ValueError:
            print(f"Error: '{key}' requires an integer value")
            return
    
    migration_config.set(key, value)
    migration_config.save_to_file()
    
    print(f"✅ Set {key} = {value}")
    print(f"Configuration saved to .agent/migration.conf")


async def list_backups():
    """List available database backups"""
    try:
        db_dir = get_agent_dir()
        backups = list(db_dir.glob("mcp_state_backup_*.db"))
        
        if not backups:
            print("\nNo backups found.")
            return
        
        print(f"\n{'='*60}")
        print("AVAILABLE BACKUPS")
        print("="*60)
        
        backups.sort(reverse=True)  # Most recent first
        for i, backup in enumerate(backups, 1):
            stat = backup.stat()
            size_mb = stat.st_size / 1024 / 1024
            mod_time = datetime.fromtimestamp(stat.st_mtime)
            print(f"  {i}. {backup.name}")
            print(f"     Size: {size_mb:.1f} MB")
            print(f"     Created: {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print()
    
    except Exception as e:
        print(f"Error listing backups: {e}")


async def restore_backup(backup_name: Optional[str] = None):
    """Restore database from a backup"""
    try:
        db_dir = get_agent_dir()
        
        if backup_name:
            backup_path = db_dir / backup_name
            if not backup_path.exists():
                print(f"Error: Backup '{backup_name}' not found")
                return False
        else:
            # List available backups and let user choose
            backups = sorted(db_dir.glob("mcp_state_backup_*.db"), reverse=True)
            if not backups:
                print("No backups found.")
                return False
            
            print("\nAvailable backups:")
            for i, backup in enumerate(backups, 1):
                stat = backup.stat()
                mod_time = datetime.fromtimestamp(stat.st_mtime)
                print(f"  {i}. {backup.name} - {mod_time.strftime('%Y-%m-%d %H:%M:%S')}")
            
            print("\nEnter backup number to restore (or 0 to cancel): ", end='', flush=True)
            try:
                choice = int(input().strip())
                if choice == 0:
                    print("Restore cancelled.")
                    return False
                if 1 <= choice <= len(backups):
                    backup_path = backups[choice - 1]
                else:
                    print("Invalid choice.")
                    return False
            except (ValueError, EOFError, KeyboardInterrupt):
                print("\nRestore cancelled.")
                return False
        
        # Confirm restore
        print(f"\n⚠️  This will replace the current database with: {backup_path.name}")
        print("Are you sure? (y/N): ", end='', flush=True)
        
        try:
            response = input().strip().lower()
            if response not in ('y', 'yes'):
                print("Restore cancelled.")
                return False
        except (EOFError, KeyboardInterrupt):
            print("\nRestore cancelled.")
            return False
        
        # Perform restore
        import shutil
        db_path = db_dir / "mcp_state.db"
        
        # Create a backup of current state before restoring
        current_backup = db_dir / f"mcp_state_before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2(str(db_path), str(current_backup))
        print(f"\n💾 Created backup of current state: {current_backup.name}")
        
        # Restore the selected backup
        shutil.copy2(str(backup_path), str(db_path))
        print(f"✅ Database restored from: {backup_path.name}")
        
        return True
        
    except Exception as e:
        print(f"Error restoring backup: {e}")
        return False


async def show_migration_logs():
    """Show recent migration logs"""
    try:
        log_dir = get_agent_dir() / "migration_logs"
        if not log_dir.exists():
            print("\nNo migration logs found.")
            return
        
        logs = sorted(log_dir.glob("migration_*.log"), reverse=True)
        if not logs:
            print("\nNo migration logs found.")
            return
        
        # Show the most recent log
        latest_log = logs[0]
        print(f"\n{'='*60}")
        print(f"MIGRATION LOG: {latest_log.name}")
        print("="*60)
        
        with open(latest_log, 'r') as f:
            print(f.read())
        
        if len(logs) > 1:
            print(f"\n({len(logs)-1} more log files available in {log_dir})")
    
    except Exception as e:
        print(f"Error reading migration logs: {e}")


async def main():
    """Main entry point for migration CLI"""
    parser = argparse.ArgumentParser(
        description='Agent MCP Database Migration Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  agent-mcp migrate --check           # Check current version
  agent-mcp migrate                   # Run migration interactively
  agent-mcp migrate --force           # Run migration without confirmation
  agent-mcp migrate --config          # Show configuration
  agent-mcp migrate --set auto_migrate=false  # Disable auto-migration
  agent-mcp migrate --list-backups    # List available backups
  agent-mcp migrate --restore         # Restore from backup
  agent-mcp migrate --logs            # Show migration logs
        """
    )
    
    parser.add_argument('--check', action='store_true', 
                       help='Check current database version without migrating')
    parser.add_argument('--force', action='store_true',
                       help='Force migration without confirmation')
    parser.add_argument('--no-backup', action='store_true',
                       help='Skip backup creation')
    parser.add_argument('--config', action='store_true',
                       help='Show current migration configuration')
    parser.add_argument('--set', metavar='KEY=VALUE',
                       help='Set a migration configuration value')
    parser.add_argument('--list-backups', action='store_true',
                       help='List available database backups')
    parser.add_argument('--restore', nargs='?', const=True, metavar='BACKUP_NAME',
                       help='Restore database from backup (interactive if no name given)')
    parser.add_argument('--logs', action='store_true',
                       help='Show recent migration logs')
    
    args = parser.parse_args()
    
    # Ensure project directory is set
    if 'MCP_PROJECT_DIR' not in os.environ:
        print("Error: MCP_PROJECT_DIR not set. Run from agent-mcp context.")
        sys.exit(1)
    
    if args.check:
        await check_version()
    elif args.config:
        show_config()
    elif args.set:
        set_config(args.set)
    elif args.list_backups:
        await list_backups()
    elif args.restore is not None:
        backup_name = args.restore if args.restore is not True else None
        await restore_backup(backup_name)
    elif args.logs:
        await show_migration_logs()
    else:
        await run_migration(force=args.force, no_backup=args.no_backup)


if __name__ == '__main__':
    asyncio.run(main())