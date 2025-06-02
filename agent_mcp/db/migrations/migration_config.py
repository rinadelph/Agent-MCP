#!/usr/bin/env python3
"""
Migration Configuration for Agent MCP

Allows users to control migration behavior through environment variables
or configuration files.
"""

import os
from typing import Dict, Any
from pathlib import Path


class MigrationConfig:
    """Migration configuration settings"""
    
    # Environment variable prefix
    ENV_PREFIX = "AGENT_MCP_MIGRATION_"
    
    # Default settings
    DEFAULTS = {
        "auto_migrate": True,           # Automatically run migrations on startup
        "auto_backup": True,            # Create backup before migration
        "interactive": True,            # Ask for confirmation (if TTY available)
        "backup_retention_days": 7,     # Keep backups for N days
        "preserve_hierarchies": True,   # Preserve task hierarchies during migration
        "consolidate_workstreams": True,# Consolidate small workstreams
        "min_tasks_per_workstream": 5,  # Minimum tasks for standalone workstream
        "max_workstreams_per_phase": 7, # Maximum workstreams per phase
    }
    
    def __init__(self):
        self.settings = self.DEFAULTS.copy()
        self._load_from_environment()
        self._load_from_config_file()
    
    def _load_from_environment(self):
        """Load settings from environment variables"""
        for key, default_value in self.DEFAULTS.items():
            env_key = f"{self.ENV_PREFIX}{key.upper()}"
            env_value = os.environ.get(env_key)
            
            if env_value is not None:
                # Convert to appropriate type
                if isinstance(default_value, bool):
                    self.settings[key] = env_value.lower() in ('true', '1', 'yes', 'on')
                elif isinstance(default_value, int):
                    try:
                        self.settings[key] = int(env_value)
                    except ValueError:
                        pass  # Keep default
                else:
                    self.settings[key] = env_value
    
    def _load_from_config_file(self):
        """Load settings from .agent/migration.conf if it exists"""
        project_dir = os.environ.get("MCP_PROJECT_DIR")
        if not project_dir:
            return
        
        config_path = Path(project_dir) / ".agent" / "migration.conf"
        if not config_path.exists():
            return
        
        try:
            with open(config_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip().lower()
                        value = value.strip()
                        
                        if key in self.settings:
                            # Convert to appropriate type
                            if isinstance(self.settings[key], bool):
                                self.settings[key] = value.lower() in ('true', '1', 'yes', 'on')
                            elif isinstance(self.settings[key], int):
                                try:
                                    self.settings[key] = int(value)
                                except ValueError:
                                    pass
                            else:
                                self.settings[key] = value
        except Exception:
            pass  # Ignore config file errors
    
    def get(self, key: str, default=None):
        """Get a configuration value"""
        return self.settings.get(key, default)
    
    def set(self, key: str, value: Any):
        """Set a configuration value"""
        self.settings[key] = value
    
    def as_dict(self) -> Dict[str, Any]:
        """Get all settings as a dictionary"""
        return self.settings.copy()
    
    def save_to_file(self):
        """Save current settings to config file"""
        project_dir = os.environ.get("MCP_PROJECT_DIR")
        if not project_dir:
            return
        
        config_path = Path(project_dir) / ".agent" / "migration.conf"
        
        try:
            with open(config_path, 'w') as f:
                f.write("# Agent MCP Migration Configuration\n")
                f.write("# Generated automatically - modify as needed\n\n")
                
                for key, value in sorted(self.settings.items()):
                    if isinstance(value, bool):
                        value_str = "true" if value else "false"
                    else:
                        value_str = str(value)
                    
                    f.write(f"{key} = {value_str}\n")
                    
                    # Add helpful comments
                    if key == "auto_migrate":
                        f.write("# auto_migrate: Automatically run migrations on startup\n")
                    elif key == "interactive":
                        f.write("# interactive: Ask for confirmation before migrating\n")
                    elif key == "min_tasks_per_workstream":
                        f.write("# min_tasks_per_workstream: Minimum tasks for a standalone workstream\n")
                    f.write("\n")
        except Exception:
            pass  # Ignore save errors


# Global config instance
migration_config = MigrationConfig()