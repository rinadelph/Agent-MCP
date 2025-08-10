# Integration Manager
"""
Integration manager for coordinating all refactoring improvements
and providing a unified interface for the Agent-MCP system.
"""

import asyncio
import time
from typing import Dict, List, Any, Optional
from pathlib import Path
import json

from ..core.config import logger
from .tool_utils import dependency_manager
from .memory_manager import memory_manager
from .file_operations import file_operations_manager
from ..db.migrations import MigrationManager


class IntegrationManager:
    """Manages integration of all refactoring improvements."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.migration_manager = MigrationManager(db_path)
        self.initialized = False
        self.startup_time = None
        
        # System health tracking
        self.health_metrics = {
            "startup_time": None,
            "last_health_check": None,
            "system_status": "initializing"
        }
    
    async def initialize_system(self) -> Dict[str, Any]:
        """Initialize all systems and run startup checks."""
        logger.info("Starting system initialization...")
        start_time = time.time()
        
        try:
            # Initialize database migrations
            migration_result = await self._initialize_database()
            
            # Initialize tool dependencies
            tool_result = await self._initialize_tool_system()
            
            # Initialize memory management
            memory_result = await self._initialize_memory_system()
            
            # Initialize file operations
            file_result = await self._initialize_file_system()
            
            # Run system health check
            health_result = await self._run_health_check()
            
            self.initialized = True
            self.startup_time = time.time()
            self.health_metrics["startup_time"] = self.startup_time
            self.health_metrics["system_status"] = "healthy"
            
            initialization_time = time.time() - start_time
            
            result = {
                "status": "success",
                "initialization_time": initialization_time,
                "migrations": migration_result,
                "tools": tool_result,
                "memory": memory_result,
                "files": file_result,
                "health": health_result
            }
            
            logger.info(f"System initialization completed in {initialization_time:.2f}s")
            return result
            
        except Exception as e:
            logger.error(f"System initialization failed: {e}")
            self.health_metrics["system_status"] = "failed"
            return {
                "status": "error",
                "error": str(e),
                "initialization_time": time.time() - start_time
            }
    
    async def _initialize_database(self) -> Dict[str, Any]:
        """Initialize database and run migrations."""
        try:
            # Run pending migrations
            migration_result = self.migration_manager.migrate()
            
            # Get migration status
            status = self.migration_manager.status()
            
            return {
                "status": "success",
                "migration_result": migration_result,
                "migration_status": status
            }
        except Exception as e:
            logger.error(f"Database initialization failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def _initialize_tool_system(self) -> Dict[str, Any]:
        """Initialize tool dependency management system."""
        try:
            # Register core tools with dependencies
            self._register_core_tools()
            
            # Check for circular dependencies
            circular_deps = dependency_manager.detect_circular_dependencies()
            
            return {
                "status": "success",
                "registered_tools": len(dependency_manager.tool_versions),
                "circular_dependencies": circular_deps
            }
        except Exception as e:
            logger.error(f"Tool system initialization failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _register_core_tools(self) -> None:
        """Register core tools with their dependencies."""
        # Register admin tools
        dependency_manager.register_tool("create_agent", "1.0.0")
        dependency_manager.register_tool("view_status", "1.0.0")
        dependency_manager.register_tool("terminate_agent", "1.0.0")
        
        # Register task tools
        dependency_manager.register_tool("assign_task", "1.0.0")
        dependency_manager.register_tool("update_task_status", "1.0.0")
        dependency_manager.register_tool("view_tasks", "1.0.0")
        
        # Register RAG tools
        dependency_manager.register_tool("ask_project_rag", "1.0.0")
        dependency_manager.register_tool("index_project_data", "1.0.0")
        
        logger.info("Core tools registered with dependency manager")
    
    async def _initialize_memory_system(self) -> Dict[str, Any]:
        """Initialize memory management system."""
        try:
            # Get initial memory statistics
            initial_stats = memory_manager.get_memory_statistics()
            
            # Set up memory alert callbacks
            memory_manager.add_alert_callback(self._handle_memory_alert)
            
            return {
                "status": "success",
                "initial_stats": initial_stats
            }
        except Exception as e:
            logger.error(f"Memory system initialization failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _handle_memory_alert(self, alert) -> None:
        """Handle memory alerts."""
        logger.warning(f"Memory alert: {alert.message} (Level: {alert.level.value})")
        
        # Trigger memory optimization if needed
        if alert.level.value in ["high", "critical"]:
            optimization_result = memory_manager.optimize_memory()
            logger.info(f"Memory optimization completed: {optimization_result}")
    
    async def _initialize_file_system(self) -> Dict[str, Any]:
        """Initialize file operations system."""
        try:
            # Set up file watching for important directories
            self._setup_file_watching()
            
            # Get initial file system metrics
            metrics = file_operations_manager.get_metrics()
            
            return {
                "status": "success",
                "metrics": metrics
            }
        except Exception as e:
            logger.error(f"File system initialization failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _setup_file_watching(self) -> None:
        """Set up file watching for important directories."""
        # Watch project directory for changes
        project_dir = Path.cwd()
        if project_dir.exists():
            file_operations_manager.watch_directory(
                str(project_dir),
                self._handle_file_change
            )
        
        # Watch database directory
        db_dir = Path(self.db_path).parent
        if db_dir.exists():
            file_operations_manager.watch_directory(
                str(db_dir),
                self._handle_file_change
            )
    
    def _handle_file_change(self, change_type: str, file_path: str) -> None:
        """Handle file system changes."""
        logger.debug(f"File change detected: {change_type} - {file_path}")
        
        # Update metrics
        file_operations_manager.metrics["change_events"] += 1
        
        # Handle specific file types
        if file_path.endswith('.py'):
            logger.info(f"Python file changed: {file_path}")
        elif file_path.endswith('.db'):
            logger.info(f"Database file changed: {file_path}")
    
    async def _run_health_check(self) -> Dict[str, Any]:
        """Run comprehensive system health check."""
        try:
            health_results = {
                "database": self._check_database_health(),
                "memory": self._check_memory_health(),
                "files": self._check_file_system_health(),
                "tools": self._check_tool_system_health()
            }
            
            # Determine overall health
            all_healthy = all(result.get("healthy", False) for result in health_results.values())
            
            self.health_metrics["last_health_check"] = time.time()
            self.health_metrics["system_status"] = "healthy" if all_healthy else "degraded"
            
            return {
                "overall_healthy": all_healthy,
                "components": health_results
            }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "overall_healthy": False,
                "error": str(e)
            }
    
    def _check_database_health(self) -> Dict[str, Any]:
        """Check database health."""
        try:
            status = self.migration_manager.status()
            return {
                "healthy": True,
                "applied_migrations": status["applied_count"],
                "pending_migrations": status["pending_count"]
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e)
            }
    
    def _check_memory_health(self) -> Dict[str, Any]:
        """Check memory system health."""
        try:
            stats = memory_manager.get_memory_statistics()
            current_usage = stats["current_usage"]["memory_percentage"]
            
            return {
                "healthy": current_usage < 0.9,  # 90% threshold
                "memory_usage": current_usage,
                "gc_stats": stats["garbage_collection"]
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e)
            }
    
    def _check_file_system_health(self) -> Dict[str, Any]:
        """Check file system health."""
        try:
            metrics = file_operations_manager.get_metrics()
            cache_stats = metrics["cache"]
            
            return {
                "healthy": True,
                "cache_hit_rate": cache_stats["hit_rate"],
                "pending_operations": metrics["history"]["pending_operations"]
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e)
            }
    
    def _check_tool_system_health(self) -> Dict[str, Any]:
        """Check tool system health."""
        try:
            circular_deps = dependency_manager.detect_circular_dependencies()
            
            return {
                "healthy": len(circular_deps) == 0,
                "registered_tools": len(dependency_manager.tool_versions),
                "circular_dependencies": circular_deps
            }
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e)
            }
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        if not self.initialized:
            return {
                "status": "not_initialized",
                "message": "System not yet initialized"
            }
        
        # Run health check
        health_result = await self._run_health_check()
        
        # Get metrics from all systems
        memory_stats = memory_manager.get_memory_statistics()
        file_metrics = file_operations_manager.get_metrics()
        tool_metrics = dependency_manager.get_all_metrics()
        
        return {
            "status": "initialized",
            "health": health_result,
            "uptime": time.time() - self.startup_time if self.startup_time else 0,
            "memory": memory_stats,
            "files": file_metrics,
            "tools": tool_metrics,
            "health_metrics": self.health_metrics
        }
    
    async def optimize_system(self) -> Dict[str, Any]:
        """Perform system-wide optimization."""
        logger.info("Starting system optimization...")
        
        optimization_results = {
            "memory": memory_manager.optimize_memory(),
            "files": {
                "cache_cleared": file_operations_manager.clear_cache(),
                "metrics": file_operations_manager.get_metrics()
            },
            "database": {
                "status": "optimized"
            }
        }
        
        logger.info("System optimization completed")
        return optimization_results
    
    async def export_system_report(self, file_path: str) -> None:
        """Export comprehensive system report."""
        status = await self.get_system_status()
        
        report = {
            "timestamp": time.time(),
            "system_status": status,
            "configuration": {
                "db_path": self.db_path,
                "initialized": self.initialized
            }
        }
        
        with open(file_path, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        
        logger.info(f"System report exported to {file_path}")
    
    async def shutdown(self) -> None:
        """Shutdown all systems gracefully."""
        logger.info("Starting system shutdown...")
        
        try:
            # Shutdown file operations
            file_operations_manager.shutdown()
            
            # Stop memory monitoring
            memory_manager.stop_monitoring()
            
            # Export final reports
            await self.export_system_report("system_shutdown_report.json")
            
            logger.info("System shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")


# Global integration manager instance
integration_manager = None


def get_integration_manager(db_path: str) -> IntegrationManager:
    """Get or create the global integration manager instance."""
    global integration_manager
    if integration_manager is None:
        integration_manager = IntegrationManager(db_path)
    return integration_manager
