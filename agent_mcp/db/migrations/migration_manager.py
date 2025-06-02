#!/usr/bin/env python3
"""
Database Migration Manager for Agent MCP

Automatically detects database version and applies necessary migrations
to bring it up to the current version.
"""

import sqlite3
import json
import asyncio
import sys
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from ..connection import get_db_connection
from ...core.config import logger, get_agent_dir
from .migration_config import migration_config


class MigrationManager:
    """Manages database schema versions and migrations"""
    
    # Current schema version
    CURRENT_VERSION = "2.0.0"
    
    # Migration history
    MIGRATIONS = {
        "1.0.0": "Initial schema - flat task structure",
        "1.1.0": "Added code support fields",
        "2.0.0": "Multi-root task architecture with phases and workstreams"
    }
    
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.migration_log = []  # Store detailed migration log
    
    async def check_and_migrate(self) -> bool:
        """Check database version and run migrations if needed"""
        try:
            # Check if auto-migration is enabled
            if not migration_config.get('auto_migrate', True):
                logger.info("Auto-migration is disabled in configuration")
                return True
            
            self.conn = get_db_connection()
            self.cursor = self.conn.cursor()
            
            # Ensure migration tracking table exists
            self._ensure_migration_table()
            
            # Get current database version
            current_version = self._get_current_version()
            
            if current_version == self.CURRENT_VERSION:
                logger.info(f"✅ Database is up to date (version {self.CURRENT_VERSION})")
                self._cleanup_old_backups()  # Clean old backups
                return True
            
            logger.info(f"📊 Database version: {current_version or 'unknown'}")
            logger.info(f"🎯 Target version: {self.CURRENT_VERSION}")
            
            # Determine which migrations to run
            migrations_to_run = self._get_pending_migrations(current_version)
            
            if not migrations_to_run:
                logger.info("✅ No migrations needed")
                return True
            
            # Ask for confirmation if interactive mode
            if migration_config.get('interactive', True) and sys.stdin.isatty():
                if not await self._confirm_migration(current_version, migrations_to_run):
                    logger.info("❌ Migration cancelled by user")
                    return False
            
            # Create backup if enabled
            backup_path = None
            if migration_config.get('auto_backup', True):
                backup_path = await self._create_backup()
                logger.info(f"💾 Created backup at: {backup_path}")
            
            # Run migrations
            for version, migration_func in migrations_to_run:
                logger.info(f"🔧 Running migration to version {version}...")
                self._log_migration(f"Starting migration to {version}")
                try:
                    # Run migration with detailed logging
                    await self._run_migration_with_logging(version, migration_func)
                    self._record_migration(version)
                    logger.info(f"✅ Successfully migrated to version {version}")
                    self._log_migration(f"Migration to {version} completed successfully")
                except Exception as e:
                    logger.error(f"❌ Migration to {version} failed: {e}", exc_info=True)
                    self._log_migration(f"Migration to {version} failed: {str(e)}")
                    if backup_path:
                        logger.info(f"🔄 Backup available at: {backup_path}")
                        # Ask if user wants to restore
                        if await self._ask_restore_backup(backup_path):
                            await self._restore_backup(backup_path)
                            logger.info("✅ Database restored from backup")
                    return False
            
            self.conn.commit()
            logger.info(f"✅ Database successfully migrated to version {self.CURRENT_VERSION}")
            
            # Save migration log
            await self._save_migration_log()
            
            # Clean up old backups
            self._cleanup_old_backups()
            
            return True
            
        except Exception as e:
            logger.error(f"Error during migration check: {e}")
            return False
        finally:
            if self.conn:
                self.conn.close()
    
    def _ensure_migration_table(self):
        """Ensure migration tracking table exists"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL,
                description TEXT
            )
        """)
        self.conn.commit()
    
    def _get_current_version(self) -> Optional[str]:
        """Get current database version"""
        self.cursor.execute("""
            SELECT version FROM schema_migrations 
            ORDER BY applied_at DESC 
            LIMIT 1
        """)
        result = self.cursor.fetchone()
        
        if result:
            return result['version']
        
        # Check for legacy indicators
        if self._is_legacy_v1():
            return "1.0.0"
        
        return None
    
    def _is_legacy_v1(self) -> bool:
        """Check if this is a legacy v1 database"""
        # Check for phase tasks
        self.cursor.execute("""
            SELECT COUNT(*) as count 
            FROM tasks 
            WHERE task_id LIKE 'phase_%'
        """)
        phase_count = self.cursor.fetchone()['count']
        
        # Check for code_language field (v1.1.0)
        self.cursor.execute("PRAGMA table_info(tasks)")
        columns = [col['name'] for col in self.cursor.fetchall()]
        has_code_support = 'code_language' in columns
        
        if phase_count == 0 and has_code_support:
            return True  # v1.1.0
        elif phase_count == 0:
            return True  # v1.0.0
        
        return False
    
    def _get_pending_migrations(self, current_version: Optional[str]) -> List[tuple]:
        """Get list of migrations to run"""
        migrations = []
        
        # Map versions to migration functions
        version_migrations = {
            "1.1.0": self._migrate_to_1_1_0,
            "2.0.0": self._migrate_to_2_0_0
        }
        
        # Determine which versions to apply
        if not current_version:
            # Fresh database, apply all
            migrations = [(v, version_migrations[v]) for v in ["1.1.0", "2.0.0"]]
        elif current_version == "1.0.0":
            # Apply 1.1.0 and 2.0.0
            migrations = [(v, version_migrations[v]) for v in ["1.1.0", "2.0.0"]]
        elif current_version == "1.1.0":
            # Only apply 2.0.0
            migrations = [("2.0.0", version_migrations["2.0.0"])]
        
        return migrations
    
    async def _confirm_migration(self, current_version: str, migrations: List[tuple]) -> bool:
        """Ask user for confirmation before migrating"""
        print(f"\n{'='*60}")
        print("DATABASE MIGRATION REQUIRED")
        print("="*60)
        print(f"Current version: {current_version or 'unknown'}")
        print(f"Target version: {self.CURRENT_VERSION}")
        print(f"\nMigrations to apply:")
        for version, _ in migrations:
            print(f"  • {version}: {self.MIGRATIONS.get(version, 'Unknown')}")
        
        print("\n⚠️  This will modify your database structure.")
        if migration_config.get('auto_backup', True):
            print("A backup will be created automatically.")
        
        print("\nDo you want to proceed? (y/N): ", end='', flush=True)
        
        try:
            response = input().strip().lower()
            return response in ('y', 'yes')
        except (EOFError, KeyboardInterrupt):
            print("\nMigration cancelled.")
            return False
    
    async def _create_backup(self) -> Path:
        """Create a backup of the database"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        db_path = Path(self.conn.execute("PRAGMA database_list").fetchone()['file'])
        backup_path = db_path.parent / f"{db_path.stem}_backup_{timestamp}.db"
        
        # Use SQLite backup API
        backup_conn = sqlite3.connect(str(backup_path))
        with backup_conn:
            self.conn.backup(backup_conn)
        backup_conn.close()
        
        return backup_path
    
    async def _migrate_to_1_1_0(self):
        """Migrate to version 1.1.0 (add code support)"""
        # This migration is already handled by add_code_support.py
        from .add_code_support import migrate_database
        migrate_database()
    
    async def _migrate_to_2_0_0(self):
        """Migrate to version 2.0.0 (multi-root task architecture)"""
        # Use our granular migration system
        from ...core.granular_migration import run_granular_migration
        success = await run_granular_migration()
        if not success:
            raise Exception("Granular migration failed")
    
    def _record_migration(self, version: str):
        """Record that a migration was applied"""
        self.cursor.execute("""
            INSERT INTO schema_migrations (version, applied_at, description)
            VALUES (?, ?, ?)
        """, (version, datetime.now().isoformat(), self.MIGRATIONS.get(version, "")))
    
    def _cleanup_old_backups(self):
        """Clean up database backups older than retention period"""
        try:
            retention_days = migration_config.get('backup_retention_days', 7)
            if retention_days <= 0:
                return  # Don't clean up if retention is disabled
            
            db_path = Path(self.conn.execute("PRAGMA database_list").fetchone()['file'])
            backup_pattern = f"{db_path.stem}_backup_*.db"
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            for backup_file in db_path.parent.glob(backup_pattern):
                # Parse timestamp from filename
                try:
                    timestamp_str = backup_file.stem.split('_backup_')[1]
                    backup_date = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                    
                    if backup_date < cutoff_date:
                        backup_file.unlink()
                        logger.info(f"🗑️  Deleted old backup: {backup_file.name}")
                except Exception:
                    pass  # Skip files we can't parse
                    
        except Exception as e:
            logger.warning(f"Error cleaning up old backups: {e}")
    
    def _log_migration(self, message: str):
        """Add message to migration log"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.migration_log.append(f"[{timestamp}] {message}")
        
    def get_migration_log(self) -> List[str]:
        """Get the complete migration log"""
        return self.migration_log.copy()
    
    async def _run_migration_with_logging(self, version: str, migration_func):
        """Run migration with detailed logging"""
        self._log_migration(f"Pre-migration check for {version}...")
        
        # Log current database state
        tables = self._get_all_tables()
        self._log_migration(f"Current tables: {', '.join(tables)}")
        
        # Run the migration
        self._log_migration(f"Executing migration function for {version}...")
        await migration_func()
        
        # Log post-migration state
        new_tables = self._get_all_tables()
        self._log_migration(f"Post-migration tables: {', '.join(new_tables)}")
        
        # Check if migration was recorded
        if self._is_migration_recorded(version):
            self._log_migration(f"Migration {version} recorded in schema_migrations")
        else:
            self._log_migration(f"WARNING: Migration {version} not found in schema_migrations")
    
    def _get_all_tables(self) -> List[str]:
        """Get list of all tables in database"""
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        return [row['name'] for row in self.cursor.fetchall()]
    
    def _is_migration_recorded(self, version: str) -> bool:
        """Check if a migration version is recorded"""
        self.cursor.execute("SELECT 1 FROM schema_migrations WHERE version = ?", (version,))
        return self.cursor.fetchone() is not None
    
    async def _ask_restore_backup(self, backup_path: Path) -> bool:
        """Ask user if they want to restore from backup"""
        print(f"\n{'='*60}")
        print("MIGRATION FAILED")
        print("="*60)
        print(f"\nA backup is available at: {backup_path}")
        print("\nWould you like to restore from this backup? (y/N): ", end='', flush=True)
        
        try:
            response = input().strip().lower()
            return response in ('y', 'yes')
        except (EOFError, KeyboardInterrupt):
            print("\nRestore cancelled.")
            return False
    
    async def _restore_backup(self, backup_path: Path):
        """Restore database from backup"""
        db_path = Path(self.conn.execute("PRAGMA database_list").fetchone()['file'])
        
        # Close current connection
        self.conn.close()
        
        # Copy backup over current database
        shutil.copy2(str(backup_path), str(db_path))
        
        # Reopen connection
        self.conn = get_db_connection()
        self.cursor = self.conn.cursor()
        self._log_migration(f"Database restored from {backup_path}")
    
    async def _save_migration_log(self):
        """Save migration log to file"""
        try:
            log_dir = get_agent_dir() / "migration_logs"
            log_dir.mkdir(exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = log_dir / f"migration_{timestamp}.log"
            
            with open(log_file, 'w') as f:
                f.write("\n".join(self.migration_log))
            
            logger.info(f"📝 Migration log saved to: {log_file}")
            self._log_migration(f"Log saved to {log_file}")
        except Exception as e:
            logger.error(f"Failed to save migration log: {e}")


async def ensure_database_current() -> bool:
    """Ensure database is at current version, migrating if necessary"""
    manager = MigrationManager()
    return await manager.check_and_migrate()


# Version check decorator for critical operations
def requires_current_db(func):
    """Decorator to ensure database is current before operation"""
    async def wrapper(*args, **kwargs):
        if not await ensure_database_current():
            raise Exception("Database migration required but failed")
        return await func(*args, **kwargs)
    return wrapper