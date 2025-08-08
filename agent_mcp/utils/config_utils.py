# Agent-MCP Configuration Utilities
"""
Configuration management utilities for the Agent-MCP system.
Provides validation, loading, and management of configuration settings.
"""

import os
import json
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

from ..core.config import logger

class ConfigError(Exception):
    """Raised when configuration validation fails."""
    pass

class EnvironmentType(Enum):
    """Environment types for configuration."""
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"

@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    file_name: str = "mcp_state.db"
    timeout: int = 30
    check_same_thread: bool = False
    enable_foreign_keys: bool = True

@dataclass
class OpenAIConfig:
    """OpenAI API configuration settings."""
    api_key: Optional[str] = None
    embedding_model: str = "text-embedding-3-large"
    embedding_dimension: int = 1536
    chat_model: str = "gpt-4.1-2025-04-14"
    max_tokens: int = 1000000
    temperature: float = 0.4
    max_retries: int = 3
    timeout: int = 30

@dataclass
class AgentConfig:
    """Agent system configuration settings."""
    max_active_agents: int = 10
    agent_idle_timeout: int = 3600
    auto_cleanup_enabled: bool = True
    git_commit_interval: int = 1800
    max_work_without_commit: int = 3600

@dataclass
class RAGConfig:
    """RAG system configuration settings."""
    max_context_tokens: int = 1000000
    chunk_size: int = 2000
    overlap_size: int = 200
    max_results: int = 10
    similarity_threshold: float = 0.7
    auto_indexing_enabled: bool = True

@dataclass
class ServerConfig:
    """Server configuration settings."""
    host: str = "localhost"
    port: int = 8080
    debug: bool = False
    log_level: str = "INFO"
    cors_enabled: bool = True
    max_request_size: int = 10 * 1024 * 1024  # 10MB

@dataclass
class SystemConfig:
    """System-wide configuration settings."""
    environment: EnvironmentType = EnvironmentType.DEVELOPMENT
    project_dir: Optional[Path] = None
    data_dir: Optional[Path] = None
    log_dir: Optional[Path] = None
    temp_dir: Optional[Path] = None

class ConfigManager:
    """Manages configuration loading, validation, and access."""
    
    def __init__(self):
        self.database = DatabaseConfig()
        self.openai = OpenAIConfig()
        self.agent = AgentConfig()
        self.rag = RAGConfig()
        self.server = ServerConfig()
        self.system = SystemConfig()
        self._loaded = False
    
    def load_from_environment(self) -> None:
        """Load configuration from environment variables."""
        # Database configuration
        self.database.file_name = os.getenv("DB_FILE_NAME", self.database.file_name)
        self.database.timeout = int(os.getenv("DB_TIMEOUT", self.database.timeout))
        
        # OpenAI configuration
        self.openai.api_key = os.getenv("OPENAI_API_KEY")
        self.openai.embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", self.openai.embedding_model)
        self.openai.embedding_dimension = int(os.getenv("OPENAI_EMBEDDING_DIMENSION", self.openai.embedding_dimension))
        self.openai.chat_model = os.getenv("OPENAI_CHAT_MODEL", self.openai.chat_model)
        self.openai.max_tokens = int(os.getenv("OPENAI_MAX_TOKENS", self.openai.max_tokens))
        self.openai.temperature = float(os.getenv("OPENAI_TEMPERATURE", self.openai.temperature))
        self.openai.max_retries = int(os.getenv("OPENAI_MAX_RETRIES", self.openai.max_retries))
        self.openai.timeout = int(os.getenv("OPENAI_TIMEOUT", self.openai.timeout))
        
        # Agent configuration
        self.agent.max_active_agents = int(os.getenv("MAX_ACTIVE_AGENTS", self.agent.max_active_agents))
        self.agent.agent_idle_timeout = int(os.getenv("AGENT_IDLE_TIMEOUT", self.agent.agent_idle_timeout))
        self.agent.auto_cleanup_enabled = os.getenv("AUTO_CLEANUP_ENABLED", "true").lower() == "true"
        self.agent.git_commit_interval = int(os.getenv("GIT_COMMIT_INTERVAL", self.agent.git_commit_interval))
        self.agent.max_work_without_commit = int(os.getenv("MAX_WORK_WITHOUT_COMMIT", self.agent.max_work_without_commit))
        
        # RAG configuration
        self.rag.max_context_tokens = int(os.getenv("MAX_CONTEXT_TOKENS", self.rag.max_context_tokens))
        self.rag.chunk_size = int(os.getenv("RAG_CHUNK_SIZE", self.rag.chunk_size))
        self.rag.overlap_size = int(os.getenv("RAG_OVERLAP_SIZE", self.rag.overlap_size))
        self.rag.max_results = int(os.getenv("RAG_MAX_RESULTS", self.rag.max_results))
        self.rag.similarity_threshold = float(os.getenv("RAG_SIMILARITY_THRESHOLD", self.rag.similarity_threshold))
        self.rag.auto_indexing_enabled = os.getenv("AUTO_INDEXING_ENABLED", "true").lower() == "true"
        
        # Server configuration
        self.server.host = os.getenv("SERVER_HOST", self.server.host)
        self.server.port = int(os.getenv("SERVER_PORT", self.server.port))
        self.server.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.server.log_level = os.getenv("LOG_LEVEL", self.server.log_level)
        self.server.cors_enabled = os.getenv("CORS_ENABLED", "true").lower() == "true"
        self.server.max_request_size = int(os.getenv("MAX_REQUEST_SIZE", self.server.max_request_size))
        
        # System configuration
        env_str = os.getenv("ENVIRONMENT", "development").lower()
        self.system.environment = EnvironmentType(env_str)
        
        project_dir_str = os.getenv("MCP_PROJECT_DIR")
        if project_dir_str:
            self.system.project_dir = Path(project_dir_str).resolve()
        
        data_dir_str = os.getenv("DATA_DIR")
        if data_dir_str:
            self.system.data_dir = Path(data_dir_str).resolve()
        
        log_dir_str = os.getenv("LOG_DIR")
        if log_dir_str:
            self.system.log_dir = Path(log_dir_str).resolve()
        
        temp_dir_str = os.getenv("TEMP_DIR")
        if temp_dir_str:
            self.system.temp_dir = Path(temp_dir_str).resolve()
        
        self._loaded = True
    
    def load_from_file(self, config_file: Path) -> None:
        """Load configuration from a JSON file."""
        if not config_file.exists():
            raise ConfigError(f"Configuration file not found: {config_file}")
        
        try:
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            
            # Update configuration sections
            if 'database' in config_data:
                self._update_dataclass(self.database, config_data['database'])
            if 'openai' in config_data:
                self._update_dataclass(self.openai, config_data['openai'])
            if 'agent' in config_data:
                self._update_dataclass(self.agent, config_data['agent'])
            if 'rag' in config_data:
                self._update_dataclass(self.rag, config_data['rag'])
            if 'server' in config_data:
                self._update_dataclass(self.server, config_data['server'])
            if 'system' in config_data:
                self._update_dataclass(self.system, config_data['system'])
            
            self._loaded = True
            
        except json.JSONDecodeError as e:
            raise ConfigError(f"Invalid JSON in configuration file: {e}")
        except Exception as e:
            raise ConfigError(f"Error loading configuration file: {e}")
    
    def _update_dataclass(self, dataclass_instance: Any, data: Dict[str, Any]) -> None:
        """Update a dataclass instance with new data."""
        for key, value in data.items():
            if hasattr(dataclass_instance, key):
                setattr(dataclass_instance, key, value)
    
    def validate(self) -> None:
        """Validate the current configuration."""
        errors = []
        
        # Validate OpenAI configuration
        if not self.openai.api_key:
            errors.append("OPENAI_API_KEY is required")
        
        if self.openai.embedding_dimension <= 0:
            errors.append("OPENAI_EMBEDDING_DIMENSION must be positive")
        
        if self.openai.max_tokens <= 0:
            errors.append("OPENAI_MAX_TOKENS must be positive")
        
        # Validate Agent configuration
        if self.agent.max_active_agents <= 0:
            errors.append("MAX_ACTIVE_AGENTS must be positive")
        
        if self.agent.agent_idle_timeout <= 0:
            errors.append("AGENT_IDLE_TIMEOUT must be positive")
        
        # Validate RAG configuration
        if self.rag.max_context_tokens <= 0:
            errors.append("MAX_CONTEXT_TOKENS must be positive")
        
        if self.rag.chunk_size <= 0:
            errors.append("RAG_CHUNK_SIZE must be positive")
        
        if self.rag.overlap_size < 0:
            errors.append("RAG_OVERLAP_SIZE must be non-negative")
        
        if not 0 <= self.rag.similarity_threshold <= 1:
            errors.append("RAG_SIMILARITY_THRESHOLD must be between 0 and 1")
        
        # Validate Server configuration
        if not 1 <= self.server.port <= 65535:
            errors.append("SERVER_PORT must be between 1 and 65535")
        
        if self.server.max_request_size <= 0:
            errors.append("MAX_REQUEST_SIZE must be positive")
        
        # Validate System configuration
        if self.system.project_dir and not self.system.project_dir.exists():
            errors.append(f"Project directory does not exist: {self.system.project_dir}")
        
        if errors:
            raise ConfigError(f"Configuration validation failed:\n" + "\n".join(f"- {error}" for error in errors))
    
    def get_database_path(self) -> Path:
        """Get the database file path."""
        if self.system.project_dir:
            return self.system.project_dir / ".agent" / self.database.file_name
        else:
            return Path(self.database.file_name)
    
    def get_log_path(self) -> Path:
        """Get the log file path."""
        if self.system.log_dir:
            return self.system.log_dir / "mcp_server.log"
        elif self.system.project_dir:
            return self.system.project_dir / ".agent" / "mcp_server.log"
        else:
            return Path("mcp_server.log")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            'database': self._dataclass_to_dict(self.database),
            'openai': self._dataclass_to_dict(self.openai),
            'agent': self._dataclass_to_dict(self.agent),
            'rag': self._dataclass_to_dict(self.rag),
            'server': self._dataclass_to_dict(self.server),
            'system': self._dataclass_to_dict(self.system)
        }
    
    def _dataclass_to_dict(self, dataclass_instance: Any) -> Dict[str, Any]:
        """Convert a dataclass instance to dictionary."""
        result = {}
        for field_name in dataclass_instance.__dataclass_fields__:
            value = getattr(dataclass_instance, field_name)
            if isinstance(value, Path):
                result[field_name] = str(value)
            elif isinstance(value, EnvironmentType):
                result[field_name] = value.value
            else:
                result[field_name] = value
        return result
    
    def save_to_file(self, config_file: Path) -> None:
        """Save configuration to a JSON file."""
        try:
            config_data = self.to_dict()
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
        except Exception as e:
            raise ConfigError(f"Error saving configuration file: {e}")

# Global configuration manager instance
config_manager = ConfigManager()

def load_configuration(config_file: Optional[Path] = None) -> ConfigManager:
    """
    Load and validate configuration.
    
    Args:
        config_file: Optional path to configuration file
        
    Returns:
        Configured ConfigManager instance
        
    Raises:
        ConfigError: If configuration validation fails
    """
    # Load from environment first
    config_manager.load_from_environment()
    
    # Load from file if provided
    if config_file:
        config_manager.load_from_file(config_file)
    
    # Validate configuration
    config_manager.validate()
    
    logger.info("Configuration loaded and validated successfully")
    return config_manager

def get_config() -> ConfigManager:
    """Get the global configuration manager instance."""
    if not config_manager._loaded:
        load_configuration()
    return config_manager
