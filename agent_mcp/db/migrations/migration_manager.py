# Migration Manager
"""
Migration manager for handling database migrations in Agent-MCP.
"""

import sqlite3
import importlib
import inspect
from typing import List, Dict, Any, Optional, Type
from datetime import datetime
from pathlib import Path

from ...core.config import logger
from .base_migration import BaseMigration


class MigrationManager:
    """Manages database migrations."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.migrations_table = "schema_migrations"
        self._ensure_migrations_table()
    
    def _ensure_migrations_table(self) -> None:
        """Ensure the migrations tracking table exists."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.migrations_table} (
                    version TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    execution_time_ms INTEGER,
                    status TEXT DEFAULT 'success'
                )
            """)
            conn.commit()
        finally:
            conn.close()
    
    def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration versions."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(f"SELECT version FROM {self.migrations_table} ORDER BY applied_at")
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def record_migration(self, migration: BaseMigration, execution_time_ms: int, 
                        status: str = "success") -> None:
        """Record a migration in the tracking table."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(f"""
                INSERT OR REPLACE INTO {self.migrations_table} 
                (version, description, execution_time_ms, status)
                VALUES (?, ?, ?, ?)
            """, (migration.version, migration.description, execution_time_ms, status))
            conn.commit()
        finally:
            conn.close()
    
    def remove_migration_record(self, version: str) -> None:
        """Remove a migration record from tracking table."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {self.migrations_table} WHERE version = ?", (version,))
            conn.commit()
        finally:
            conn.close()
    
    def discover_migrations(self, migrations_dir: str = "agent_mcp/db/migrations") -> List[Type[BaseMigration]]:
        """Discover all migration classes in the migrations directory."""
        migrations = []
        migrations_path = Path(migrations_dir)
        
        if not migrations_path.exists():
            logger.warning(f"Migrations directory not found: {migrations_path}")
            return migrations
        
        for file_path in migrations_path.glob("*.py"):
            if file_path.name.startswith("__"):
                continue
            
            module_name = f"{migrations_dir.replace('/', '.')}.{file_path.stem}"
            try:
                module = importlib.import_module(module_name)
                
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, BaseMigration) and 
                        obj != BaseMigration):
                        migrations.append(obj)
                        
            except ImportError as e:
                logger.warning(f"Could not import migration module {module_name}: {e}")
        
        # Sort migrations by version
        migrations.sort(key=lambda m: m().get_version())
        return migrations
    
    def get_pending_migrations(self) -> List[BaseMigration]:
        """Get list of migrations that haven't been applied yet."""
        applied_versions = set(self.get_applied_migrations())
        all_migrations = [migration_class() for migration_class in self.discover_migrations()]
        
        pending = []
        for migration in all_migrations:
            if migration.version not in applied_versions:
                pending.append(migration)
        
        return pending
    
    def migrate(self, target_version: Optional[str] = None) -> Dict[str, Any]:
        """Run pending migrations up to target version."""
        pending_migrations = self.get_pending_migrations()
        
        if not pending_migrations:
            logger.info("No pending migrations to apply")
            return {"status": "success", "applied": 0, "migrations": []}
        
        applied_migrations = []
        start_time = datetime.now()
        
        try:
            conn = sqlite3.connect(self.db_path)
            
            for migration in pending_migrations:
                if target_version and migration.version > target_version:
                    break
                
                logger.info(f"Applying migration {migration.version}: {migration.description}")
                migration_start = datetime.now()
                
                try:
                    # Validate migration before applying
                    if not migration.validate_migration(conn):
                        raise Exception(f"Migration {migration.version} validation failed")
                    
                    # Apply migration
                    migration.up(conn)
                    
                    # Record successful migration
                    execution_time = (datetime.now() - migration_start).total_seconds() * 1000
                    self.record_migration(migration, int(execution_time))
                    
                    applied_migrations.append({
                        "version": migration.version,
                        "description": migration.description,
                        "execution_time_ms": int(execution_time)
                    })
                    
                    logger.info(f"Successfully applied migration {migration.version}")
                    
                except Exception as e:
                    logger.error(f"Failed to apply migration {migration.version}: {e}")
                    self.record_migration(migration, 0, "failed")
                    raise
            
            conn.close()
            
            total_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(f"Migration completed: {len(applied_migrations)} migrations applied in {total_time:.2f}ms")
            
            return {
                "status": "success",
                "applied": len(applied_migrations),
                "migrations": applied_migrations,
                "total_time_ms": int(total_time)
            }
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "applied": len(applied_migrations),
                "migrations": applied_migrations
            }
    
    def rollback(self, target_version: Optional[str] = None) -> Dict[str, Any]:
        """Rollback migrations to target version."""
        applied_versions = self.get_applied_migrations()
        
        if not applied_versions:
            logger.info("No migrations to rollback")
            return {"status": "success", "rolled_back": 0, "migrations": []}
        
        # If no target version specified, rollback last migration
        if target_version is None:
            target_version = applied_versions[-2] if len(applied_versions) > 1 else None
        
        if target_version is None:
            logger.info("No migrations to rollback")
            return {"status": "success", "rolled_back": 0, "migrations": []}
        
        # Get migrations to rollback (in reverse order)
        migrations_to_rollback = []
        for version in reversed(applied_versions):
            if version <= target_version:
                break
            migration_class = self._find_migration_class(version)
            if migration_class:
                migrations_to_rollback.append(migration_class())
        
        rolled_back_migrations = []
        start_time = datetime.now()
        
        try:
            conn = sqlite3.connect(self.db_path)
            
            for migration in migrations_to_rollback:
                logger.info(f"Rolling back migration {migration.version}: {migration.description}")
                migration_start = datetime.now()
                
                try:
                    migration.down(conn)
                    
                    # Remove migration record
                    self.remove_migration_record(migration.version)
                    
                    execution_time = (datetime.now() - migration_start).total_seconds() * 1000
                    rolled_back_migrations.append({
                        "version": migration.version,
                        "description": migration.description,
                        "execution_time_ms": int(execution_time)
                    })
                    
                    logger.info(f"Successfully rolled back migration {migration.version}")
                    
                except Exception as e:
                    logger.error(f"Failed to rollback migration {migration.version}: {e}")
                    raise
            
            conn.close()
            
            total_time = (datetime.now() - start_time).total_seconds() * 1000
            logger.info(f"Rollback completed: {len(rolled_back_migrations)} migrations rolled back in {total_time:.2f}ms")
            
            return {
                "status": "success",
                "rolled_back": len(rolled_back_migrations),
                "migrations": rolled_back_migrations,
                "total_time_ms": int(total_time)
            }
            
        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "rolled_back": len(rolled_back_migrations),
                "migrations": rolled_back_migrations
            }
    
    def _find_migration_class(self, version: str) -> Optional[Type[BaseMigration]]:
        """Find migration class by version."""
        for migration_class in self.discover_migrations():
            if migration_class().get_version() == version:
                return migration_class
        return None
    
    def status(self) -> Dict[str, Any]:
        """Get migration status."""
        applied_versions = self.get_applied_migrations()
        pending_migrations = self.get_pending_migrations()
        
        return {
            "applied_count": len(applied_versions),
            "pending_count": len(pending_migrations),
            "applied_versions": applied_versions,
            "pending_versions": [m.version for m in pending_migrations],
            "latest_applied": applied_versions[-1] if applied_versions else None,
            "next_pending": pending_migrations[0].version if pending_migrations else None
        }
    
    def create_migration(self, version: str, description: str) -> str:
        """Create a new migration file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{version}.py"
        
        template = f'''# Migration: {version}
"""
{description}
"""

from .base_migration import BaseMigration
import sqlite3


class Migration{version.replace('.', '_')}(BaseMigration):
    """{description}"""
    
    def get_version(self) -> str:
        return "{version}"
    
    def get_description(self) -> str:
        return "{description}"
    
    def up(self, conn: sqlite3.Connection) -> None:
        """Apply the migration."""
        # TODO: Implement migration logic
        pass
    
    def down(self, conn: sqlite3.Connection) -> None:
        """Rollback the migration."""
        # TODO: Implement rollback logic
        pass
'''
        
        migrations_dir = Path("agent_mcp/db/migrations")
        migrations_dir.mkdir(exist_ok=True)
        
        file_path = migrations_dir / filename
        with open(file_path, 'w') as f:
            f.write(template)
        
        logger.info(f"Created migration file: {file_path}")
        return str(file_path)
