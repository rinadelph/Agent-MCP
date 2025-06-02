"""
Automatic migration utility for Agent MCP
"""
import asyncio
import os
from pathlib import Path
from ..core.config import logger
from ..db.migrations.migration_manager import MigrationManager


def run_auto_migration(project_dir: str = None) -> bool:
    """
    Run automatic migration for a project
    Returns True if successful or no migration needed
    """
    try:
        # Set project directory if provided
        if project_dir:
            old_dir = os.environ.get("MCP_PROJECT_DIR")
            os.environ["MCP_PROJECT_DIR"] = str(project_dir)
        
        # Create migration manager
        mm = MigrationManager()
        
        # Run async migration check
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Check current version
            current_version = mm.get_current_version()
            latest_version = mm.get_latest_version()
            
            if current_version == latest_version:
                logger.info(f"Database already at latest version: {latest_version}")
                return True
            
            logger.info(f"Migrating database from {current_version} to {latest_version}")
            
            # Run migration
            result = loop.run_until_complete(mm.check_and_migrate())
            
            if result:
                logger.info("Migration completed successfully")
            else:
                logger.warning("Migration completed with warnings")
                
            return True
            
        finally:
            loop.close()
            
            # Restore old directory
            if project_dir and old_dir:
                os.environ["MCP_PROJECT_DIR"] = old_dir
                
    except Exception as e:
        logger.error(f"Auto-migration failed: {e}")
        # Don't fail initialization if migration fails
        return True


def ensure_database_ready(project_dir: str) -> bool:
    """
    Ensure database is ready for use (exists and is migrated)
    """
    try:
        agent_dir = Path(project_dir) / ".agent"
        db_path = agent_dir / "agent_data.db"
        
        if not db_path.exists():
            logger.info("Database doesn't exist yet, will be created on first use")
            return True
            
        # Run auto migration
        return run_auto_migration(project_dir)
        
    except Exception as e:
        logger.error(f"Error ensuring database ready: {e}")
        # Don't fail, let the app continue
        return True