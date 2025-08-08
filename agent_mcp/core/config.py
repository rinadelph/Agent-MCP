# Agent-MCP Configuration Management System
"""
Comprehensive configuration management system with schema validation,
environment variable validation, hot-reloading, and consolidated settings.
"""

import logging
import os
import sys
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from enum import Enum
import threading
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import jsonschema
from jsonschema import validate

# Version information
VERSION = "2.0"
GITHUB_REPO = "rinadelph/Agent-MCP"
AUTHOR = "Luis Alejandro Rincon"
GITHUB_URL = "https://github.com/rinadelph"

# --- TUI Colors (ANSI Escape Codes) ---
class TUIColors:
    HEADER = "\033[95m"  # Light Magenta
    OKBLUE = "\033[94m"  # Light Blue
    OKCYAN = "\033[96m"  # Light Cyan
    OKGREEN = "\033[92m"  # Light Green
    WARNING = "\033[93m"  # Yellow
    FAIL = "\033[91m"  # Red
    ENDC = "\033[0m"  # Reset to default
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"
    DIM = "\033[2m"

    # Specific log level colors
    DEBUG = OKCYAN
    INFO = OKGREEN
    WARNING = WARNING
    ERROR = FAIL
    CRITICAL = BOLD + FAIL


class ColorfulFormatter(logging.Formatter):
    """Custom formatter to add colors to log messages for console output."""

    LOG_LEVEL_COLORS = {
        logging.DEBUG: TUIColors.DEBUG,
        logging.INFO: TUIColors.INFO,
        logging.WARNING: TUIColors.WARNING,
        logging.ERROR: TUIColors.ERROR,
        logging.CRITICAL: TUIColors.CRITICAL,
    }

    def format(self, record):
        color = self.LOG_LEVEL_COLORS.get(record.levelno, TUIColors.ENDC)
        record.levelname = (
            f"{color}{record.levelname:<8}{TUIColors.ENDC}"  # Pad levelname
        )
        record.name = f"{TUIColors.OKBLUE}{record.name}{TUIColors.ENDC}"
        return super().format(record)


# --- Configuration Schema ---
CONFIG_SCHEMA = {
    "type": "object",
    "properties": {
        "database": {
            "type": "object",
            "properties": {
                "file_name": {"type": "string"},
                "timeout": {"type": "integer", "minimum": 1},
                "check_same_thread": {"type": "boolean"},
                "enable_foreign_keys": {"type": "boolean"}
            },
            "required": ["file_name"]
        },
        "logging": {
            "type": "object",
            "properties": {
                "level": {"type": "string", "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]},
                "file_name": {"type": "string"},
                "format_file": {"type": "string"},
                "format_console": {"type": "string"},
                "console_enabled": {"type": "boolean"}
            },
            "required": ["level", "file_name"]
        },
        "openai": {
            "type": "object",
            "properties": {
                "api_key": {"type": "string"},
                "embedding_model": {"type": "string"},
                "embedding_dimension": {"type": "integer", "minimum": 1},
                "chat_model": {"type": "string"},
                "task_analysis_model": {"type": "string"},
                "max_tokens": {"type": "integer", "minimum": 1},
                "temperature": {"type": "number", "minimum": 0, "maximum": 2},
                "max_retries": {"type": "integer", "minimum": 0},
                "timeout": {"type": "integer", "minimum": 1}
            },
            "required": ["api_key", "embedding_model", "chat_model"]
        },
        "agent": {
            "type": "object",
            "properties": {
                "max_active_agents": {"type": "integer", "minimum": 1},
                "agent_idle_timeout": {"type": "integer", "minimum": 1},
                "auto_cleanup_enabled": {"type": "boolean"},
                "git_commit_interval": {"type": "integer", "minimum": 1},
                "max_work_without_commit": {"type": "integer", "minimum": 1},
                "colors": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["max_active_agents", "agent_idle_timeout"]
        },
        "rag": {
            "type": "object",
            "properties": {
                "max_context_tokens": {"type": "integer", "minimum": 1},
                "chunk_size": {"type": "integer", "minimum": 1},
                "overlap_size": {"type": "integer", "minimum": 0},
                "max_results": {"type": "integer", "minimum": 1},
                "similarity_threshold": {"type": "number", "minimum": 0, "maximum": 1},
                "auto_indexing_enabled": {"type": "boolean"},
                "advanced_embeddings": {"type": "boolean"},
                "disable_auto_indexing": {"type": "boolean"}
            },
            "required": ["max_context_tokens", "chunk_size"]
        },
        "server": {
            "type": "object",
            "properties": {
                "host": {"type": "string"},
                "port": {"type": "integer", "minimum": 1, "maximum": 65535},
                "debug": {"type": "boolean"},
                "log_level": {"type": "string"},
                "cors_enabled": {"type": "boolean"},
                "max_request_size": {"type": "integer", "minimum": 1}
            },
            "required": ["host", "port"]
        },
        "tmux": {
            "type": "object",
            "properties": {
                "git_commit_interval": {"type": "integer", "minimum": 1},
                "max_work_without_commit": {"type": "integer", "minimum": 1},
                "auto_commit_enabled": {"type": "boolean"},
                "claude_startup_delay": {"type": "integer", "minimum": 0},
                "message_send_delay": {"type": "number", "minimum": 0},
                "status_check_interval": {"type": "integer", "minimum": 1},
                "compliance_check_interval": {"type": "integer", "minimum": 1},
                "max_active_agents": {"type": "integer", "minimum": 1},
                "agent_idle_timeout": {"type": "integer", "minimum": 1},
                "auto_cleanup_enabled": {"type": "boolean"},
                "credit_conservation_mode": {"type": "boolean"},
                "batch_messages_enabled": {"type": "boolean"},
                "pm_autonomy_target": {"type": "number", "minimum": 0, "maximum": 1},
                "strike_system_enabled": {"type": "boolean"},
                "max_strikes_per_agent": {"type": "integer", "minimum": 1},
                "compliance_threshold": {"type": "number", "minimum": 0, "maximum": 1},
                "auto_rename_windows": {"type": "boolean"},
                "window_naming_conventions": {"type": "object"},
                "emergency_stop_enabled": {"type": "boolean"},
                "auto_recovery_enabled": {"type": "boolean"},
                "escalation_timeout": {"type": "integer", "minimum": 1},
                "monitoring_enabled": {"type": "boolean"},
                "alert_on_compliance_issues": {"type": "boolean"},
                "performance_monitoring": {"type": "boolean"}
            }
        },
        "task_placement": {
            "type": "object",
            "properties": {
                "enable_rag": {"type": "boolean"},
                "duplication_threshold": {"type": "number", "minimum": 0, "maximum": 1},
                "allow_rag_override": {"type": "boolean"},
                "rag_timeout": {"type": "integer", "minimum": 1}
            }
        }
    }
}


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
class LoggingConfig:
    """Logging configuration settings."""
    level: str = "INFO"
    file_name: str = "mcp_server.log"
    format_file: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    format_console: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    console_enabled: bool = False


@dataclass
class OpenAIConfig:
    """OpenAI API configuration settings."""
    api_key: Optional[str] = None
    embedding_model: str = "text-embedding-3-large"
    embedding_dimension: int = 1536
    chat_model: str = "gpt-4.1-2025-04-14"
    task_analysis_model: str = "gpt-4.1-2025-04-14"
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
    colors: List[str] = field(default_factory=lambda: [
        "#FF5733", "#33FF57", "#3357FF", "#FF33A1", "#A133FF", "#33FFA1",
        "#FFBD33", "#33FFBD", "#BD33FF", "#FF3333", "#33FF33", "#3333FF",
        "#FF8C00", "#00CED1", "#9400D3", "#FF1493", "#7FFF00", "#1E90FF"
    ])


@dataclass
class RAGConfig:
    """RAG system configuration settings."""
    max_context_tokens: int = 1000000
    chunk_size: int = 2000
    overlap_size: int = 200
    max_results: int = 10
    similarity_threshold: float = 0.7
    auto_indexing_enabled: bool = True
    advanced_embeddings: bool = False
    disable_auto_indexing: bool = False


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
class TMUXConfig:
    """TMUX Bible configuration settings."""
    git_commit_interval: int = 1800
    max_work_without_commit: int = 3600
    auto_commit_enabled: bool = True
    claude_startup_delay: int = 5
    message_send_delay: float = 0.5
    status_check_interval: int = 300
    compliance_check_interval: int = 120
    max_active_agents: int = 10
    agent_idle_timeout: int = 3600
    auto_cleanup_enabled: bool = True
    credit_conservation_mode: bool = True
    batch_messages_enabled: bool = True
    pm_autonomy_target: float = 0.8
    strike_system_enabled: bool = True
    max_strikes_per_agent: int = 3
    compliance_threshold: float = 0.7
    auto_rename_windows: bool = True
    window_naming_conventions: Dict[str, str] = field(default_factory=lambda: {
        'claude_agent': 'Claude-{role}',
        'dev_server': '{framework}-{purpose}',
        'shell': '{project}-Shell',
        'service': '{service}-Server',
        'temp_agent': 'TEMP-{purpose}'
    })
    emergency_stop_enabled: bool = True
    auto_recovery_enabled: bool = True
    escalation_timeout: int = 300
    monitoring_enabled: bool = True
    alert_on_compliance_issues: bool = True
    performance_monitoring: bool = True


@dataclass
class TaskPlacementConfig:
    """Task placement configuration settings."""
    enable_rag: bool = True
    duplication_threshold: float = 0.8
    allow_rag_override: bool = True
    rag_timeout: int = 5


@dataclass
class SystemConfig:
    """System-wide configuration settings."""
    environment: EnvironmentType = EnvironmentType.DEVELOPMENT
    project_dir: Optional[Path] = None
    data_dir: Optional[Path] = None
    log_dir: Optional[Path] = None
    temp_dir: Optional[Path] = None


class ConfigFileHandler(FileSystemEventHandler):
    """Handles configuration file changes for hot-reloading."""
    
    def __init__(self, config_manager: 'ConfigurationManager'):
        self.config_manager = config_manager
        self.last_modified = 0
    
    def on_modified(self, event):
        if event.is_directory:
            return
        
        if event.src_path.endswith(('.json', '.yaml', '.yml')):
            current_time = time.time()
            if current_time - self.last_modified > 1:  # Debounce
                self.last_modified = current_time
                try:
                    self.config_manager.reload_config()
                except Exception as e:
                    logging.error(f"Error reloading configuration: {e}")


class ConfigurationManager:
    """Comprehensive configuration management system."""
    
    def __init__(self, config_file: Optional[Path] = None):
        self.config_file = config_file
        self.database = DatabaseConfig()
        self.logging = LoggingConfig()
        self.openai = OpenAIConfig()
        self.agent = AgentConfig()
        self.rag = RAGConfig()
        self.server = ServerConfig()
        self.tmux = TMUXConfig()
        self.task_placement = TaskPlacementConfig()
        self.system = SystemConfig()
        
        self._loaded = False
        self._observer = None
        self._lock = threading.RLock()
        self._callbacks = []
        
        # Load initial configuration
        self.load_configuration()
    
    def load_configuration(self) -> None:
        """Load configuration from all sources."""
        with self._lock:
            # Load from environment variables first
            self._load_from_environment()
            
            # Load from configuration file if provided
            if self.config_file and self.config_file.exists():
                self._load_from_file(self.config_file)
            
            # Validate configuration
            self._validate_configuration()
            
            # Setup logging
            self._setup_logging()
            
            self._loaded = True
    
    def _load_from_environment(self) -> None:
        """Load configuration from environment variables."""
        # Database configuration
        self.database.file_name = os.getenv("DB_FILE_NAME", self.database.file_name)
        self.database.timeout = int(os.getenv("DB_TIMEOUT", self.database.timeout))
        self.database.check_same_thread = os.getenv("DB_CHECK_SAME_THREAD", "false").lower() == "true"
        self.database.enable_foreign_keys = os.getenv("DB_ENABLE_FOREIGN_KEYS", "true").lower() == "true"
        
        # Logging configuration
        self.logging.level = os.getenv("LOG_LEVEL", self.logging.level)
        self.logging.file_name = os.getenv("LOG_FILE_NAME", self.logging.file_name)
        self.logging.console_enabled = os.getenv("MCP_DEBUG", "false").lower() == "true"
        
        # OpenAI configuration
        self.openai.api_key = os.getenv("OPENAI_API_KEY")
        self.openai.embedding_model = os.getenv("OPENAI_EMBEDDING_MODEL", self.openai.embedding_model)
        self.openai.embedding_dimension = int(os.getenv("OPENAI_EMBEDDING_DIMENSION", self.openai.embedding_dimension))
        self.openai.chat_model = os.getenv("OPENAI_CHAT_MODEL", self.openai.chat_model)
        self.openai.task_analysis_model = os.getenv("OPENAI_TASK_ANALYSIS_MODEL", self.openai.task_analysis_model)
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
        self.rag.advanced_embeddings = os.getenv("ADVANCED_EMBEDDINGS", "false").lower() == "true"
        self.rag.disable_auto_indexing = os.getenv("DISABLE_AUTO_INDEXING", "false").lower() == "true"
        
        # Server configuration
        self.server.host = os.getenv("SERVER_HOST", self.server.host)
        self.server.port = int(os.getenv("SERVER_PORT", self.server.port))
        self.server.debug = os.getenv("DEBUG", "false").lower() == "true"
        self.server.log_level = os.getenv("LOG_LEVEL", self.server.log_level)
        self.server.cors_enabled = os.getenv("CORS_ENABLED", "true").lower() == "true"
        self.server.max_request_size = int(os.getenv("MAX_REQUEST_SIZE", self.server.max_request_size))
        
        # TMUX configuration
        self.tmux.git_commit_interval = int(os.getenv("TMUX_GIT_COMMIT_INTERVAL", self.tmux.git_commit_interval))
        self.tmux.max_work_without_commit = int(os.getenv("TMUX_MAX_WORK_WITHOUT_COMMIT", self.tmux.max_work_without_commit))
        self.tmux.auto_commit_enabled = os.getenv("TMUX_AUTO_COMMIT_ENABLED", "true").lower() == "true"
        self.tmux.claude_startup_delay = int(os.getenv("TMUX_CLAUDE_STARTUP_DELAY", self.tmux.claude_startup_delay))
        self.tmux.message_send_delay = float(os.getenv("TMUX_MESSAGE_SEND_DELAY", self.tmux.message_send_delay))
        self.tmux.status_check_interval = int(os.getenv("TMUX_STATUS_CHECK_INTERVAL", self.tmux.status_check_interval))
        self.tmux.compliance_check_interval = int(os.getenv("TMUX_COMPLIANCE_CHECK_INTERVAL", self.tmux.compliance_check_interval))
        self.tmux.max_active_agents = int(os.getenv("TMUX_MAX_ACTIVE_AGENTS", self.tmux.max_active_agents))
        self.tmux.agent_idle_timeout = int(os.getenv("TMUX_AGENT_IDLE_TIMEOUT", self.tmux.agent_idle_timeout))
        self.tmux.auto_cleanup_enabled = os.getenv("TMUX_AUTO_CLEANUP_ENABLED", "true").lower() == "true"
        self.tmux.credit_conservation_mode = os.getenv("TMUX_CREDIT_CONSERVATION", "true").lower() == "true"
        self.tmux.batch_messages_enabled = os.getenv("TMUX_BATCH_MESSAGES_ENABLED", "true").lower() == "true"
        self.tmux.pm_autonomy_target = float(os.getenv("TMUX_PM_AUTONOMY_TARGET", self.tmux.pm_autonomy_target))
        self.tmux.strike_system_enabled = os.getenv("TMUX_STRIKE_SYSTEM_ENABLED", "true").lower() == "true"
        self.tmux.max_strikes_per_agent = int(os.getenv("TMUX_MAX_STRIKES_PER_AGENT", self.tmux.max_strikes_per_agent))
        self.tmux.compliance_threshold = float(os.getenv("TMUX_COMPLIANCE_THRESHOLD", self.tmux.compliance_threshold))
        self.tmux.auto_rename_windows = os.getenv("TMUX_AUTO_RENAME_WINDOWS", "true").lower() == "true"
        self.tmux.emergency_stop_enabled = os.getenv("TMUX_EMERGENCY_STOP_ENABLED", "true").lower() == "true"
        self.tmux.auto_recovery_enabled = os.getenv("TMUX_AUTO_RECOVERY_ENABLED", "true").lower() == "true"
        self.tmux.escalation_timeout = int(os.getenv("TMUX_ESCALATION_TIMEOUT", self.tmux.escalation_timeout))
        self.tmux.monitoring_enabled = os.getenv("TMUX_MONITORING_ENABLED", "true").lower() == "true"
        self.tmux.alert_on_compliance_issues = os.getenv("TMUX_ALERT_ON_COMPLIANCE_ISSUES", "true").lower() == "true"
        self.tmux.performance_monitoring = os.getenv("TMUX_PERFORMANCE_MONITORING", "true").lower() == "true"
        
        # Task placement configuration
        self.task_placement.enable_rag = os.getenv("ENABLE_TASK_PLACEMENT_RAG", "true").lower() == "true"
        self.task_placement.duplication_threshold = float(os.getenv("TASK_DUPLICATION_THRESHOLD", self.task_placement.duplication_threshold))
        self.task_placement.allow_rag_override = os.getenv("ALLOW_RAG_OVERRIDE", "true").lower() == "true"
        self.task_placement.rag_timeout = int(os.getenv("TASK_PLACEMENT_RAG_TIMEOUT", self.task_placement.rag_timeout))
        
        # System configuration
        env_str = os.getenv("ENVIRONMENT", "development").lower()
        try:
            self.system.environment = EnvironmentType(env_str)
        except ValueError:
            self.system.environment = EnvironmentType.DEVELOPMENT
        
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
    
    def _load_from_file(self, config_file: Path) -> None:
        """Load configuration from a file (JSON or YAML)."""
        try:
            with open(config_file, 'r') as f:
                if config_file.suffix.lower() in ['.yaml', '.yml']:
                    config_data = yaml.safe_load(f)
                else:
                    config_data = json.load(f)
            
            # Update configuration sections
            self._update_dataclass_from_dict(self.database, config_data.get('database', {}))
            self._update_dataclass_from_dict(self.logging, config_data.get('logging', {}))
            self._update_dataclass_from_dict(self.openai, config_data.get('openai', {}))
            self._update_dataclass_from_dict(self.agent, config_data.get('agent', {}))
            self._update_dataclass_from_dict(self.rag, config_data.get('rag', {}))
            self._update_dataclass_from_dict(self.server, config_data.get('server', {}))
            self._update_dataclass_from_dict(self.tmux, config_data.get('tmux', {}))
            self._update_dataclass_from_dict(self.task_placement, config_data.get('task_placement', {}))
            self._update_dataclass_from_dict(self.system, config_data.get('system', {}))
            
        except Exception as e:
            raise ConfigError(f"Error loading configuration file {config_file}: {e}")
    
    def _update_dataclass_from_dict(self, dataclass_instance: Any, data: Dict[str, Any]) -> None:
        """Update a dataclass instance with new data."""
        for key, value in data.items():
            if hasattr(dataclass_instance, key):
                # Handle special cases
                if key == 'environment' and isinstance(value, str):
                    try:
                        value = EnvironmentType(value)
                    except ValueError:
                        value = EnvironmentType.DEVELOPMENT
                elif key == 'project_dir' and isinstance(value, str):
                    value = Path(value).resolve()
                elif key == 'data_dir' and isinstance(value, str):
                    value = Path(value).resolve()
                elif key == 'log_dir' and isinstance(value, str):
                    value = Path(value).resolve()
                elif key == 'temp_dir' and isinstance(value, str):
                    value = Path(value).resolve()
                
                setattr(dataclass_instance, key, value)
    
    def _validate_configuration(self) -> None:
        """Validate the current configuration against schema."""
        try:
            config_dict = self.to_dict()
            validate(instance=config_dict, schema=CONFIG_SCHEMA)
        except jsonschema.exceptions.ValidationError as e:
            raise ConfigError(f"Configuration validation failed: {e}")
        except Exception as e:
            raise ConfigError(f"Configuration validation error: {e}")
    
    def _setup_logging(self) -> None:
        """Setup logging based on configuration."""
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.logging.level.upper()))
        
        # Clear existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # File handler
        if self.system.log_dir:
            log_file = self.system.log_dir / self.logging.file_name
        elif self.system.project_dir:
            log_file = self.system.project_dir / ".agent" / self.logging.file_name
        else:
            log_file = Path(self.logging.file_name)
        
        # Ensure log directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_formatter = logging.Formatter(self.logging.format_file)
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
        
        # Console handler (if enabled)
        if self.logging.console_enabled:
            console_formatter = ColorfulFormatter(self.logging.format_console, datefmt="%H:%M:%S")
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(console_formatter)
            root_logger.addHandler(console_handler)
        
        # Suppress verbose logs
        logging.getLogger("watchfiles").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
        logging.getLogger("uvicorn").setLevel(logging.WARNING)
        logging.getLogger("mcp.server.lowlevel.server").propagate = False
    
    def reload_config(self) -> None:
        """Reload configuration from all sources."""
        with self._lock:
            old_config = self.to_dict()
            self.load_configuration()
            new_config = self.to_dict()
            
            # Notify callbacks of configuration changes
            if old_config != new_config:
                self._notify_callbacks(old_config, new_config)
    
    def enable_hot_reloading(self, config_dir: Optional[Path] = None) -> None:
        """Enable hot-reloading of configuration files."""
        if self._observer:
            self._observer.stop()
            self._observer = None
        
        if config_dir is None:
            config_dir = self.config_file.parent if self.config_file else Path.cwd()
        
        self._observer = Observer()
        event_handler = ConfigFileHandler(self)
        self._observer.schedule(event_handler, str(config_dir), recursive=False)
        self._observer.start()
    
    def disable_hot_reloading(self) -> None:
        """Disable hot-reloading of configuration files."""
        if self._observer:
            self._observer.stop()
            self._observer = None
    
    def add_config_change_callback(self, callback) -> None:
        """Add a callback to be called when configuration changes."""
        self._callbacks.append(callback)
    
    def _notify_callbacks(self, old_config: Dict[str, Any], new_config: Dict[str, Any]) -> None:
        """Notify all callbacks of configuration changes."""
        for callback in self._callbacks:
            try:
                callback(old_config, new_config)
            except Exception as e:
                logging.error(f"Error in configuration change callback: {e}")
    
    def get_database_path(self) -> Path:
        """Get the database file path."""
        if self.system.project_dir:
            return self.system.project_dir / ".agent" / self.database.file_name
        else:
            return Path(self.database.file_name)
    
    def get_log_path(self) -> Path:
        """Get the log file path."""
        if self.system.log_dir:
            return self.system.log_dir / self.logging.file_name
        elif self.system.project_dir:
            return self.system.project_dir / ".agent" / self.logging.file_name
        else:
            return Path(self.logging.file_name)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        def dataclass_to_dict(obj):
            if hasattr(obj, '__dataclass_fields__'):
                result = {}
                for field_name in obj.__dataclass_fields__:
                    value = getattr(obj, field_name)
                    if isinstance(value, Path):
                        result[field_name] = str(value)
                    elif isinstance(value, EnvironmentType):
                        result[field_name] = value.value
                    elif hasattr(value, '__dataclass_fields__'):
                        result[field_name] = dataclass_to_dict(value)
                    else:
                        result[field_name] = value
                return result
            return obj
        
        return {
            'database': dataclass_to_dict(self.database),
            'logging': dataclass_to_dict(self.logging),
            'openai': dataclass_to_dict(self.openai),
            'agent': dataclass_to_dict(self.agent),
            'rag': dataclass_to_dict(self.rag),
            'server': dataclass_to_dict(self.server),
            'tmux': dataclass_to_dict(self.tmux),
            'task_placement': dataclass_to_dict(self.task_placement),
            'system': dataclass_to_dict(self.system)
        }
    
    def save_to_file(self, config_file: Optional[Path] = None) -> None:
        """Save configuration to a file."""
        if config_file is None:
            config_file = self.config_file
        
        if config_file is None:
            raise ConfigError("No configuration file specified")
        
        try:
            config_data = self.to_dict()
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_file, 'w') as f:
                if config_file.suffix.lower() in ['.yaml', '.yml']:
                    yaml.dump(config_data, f, default_flow_style=False, indent=2)
                else:
                    json.dump(config_data, f, indent=2)
        except Exception as e:
            raise ConfigError(f"Error saving configuration file: {e}")
    
    def validate_environment_variables(self) -> List[str]:
        """Validate required environment variables and return any missing ones."""
        missing_vars = []
        
        # Check required environment variables
        if not self.openai.api_key:
            missing_vars.append("OPENAI_API_KEY")
        
        if not self.system.project_dir:
            missing_vars.append("MCP_PROJECT_DIR")
        
        return missing_vars


class ConfigError(Exception):
    """Raised when configuration validation fails."""
    pass


# Global configuration manager instance
config_manager = ConfigurationManager()

def setup_logging():
    """Configures global logging for the application."""
    config_manager._setup_logging()

def enable_console_logging():
    """Enable console logging dynamically."""
    config_manager.logging.console_enabled = True
    config_manager._setup_logging()

# Initialize logging when this module is imported
setup_logging()
logger = logging.getLogger("mcp_server")

# Project directory helpers
def get_project_dir() -> Path:
    """Gets the resolved absolute path to the project directory."""
    return config_manager.system.project_dir or Path(".").resolve()

def get_agent_dir() -> Path:
    """Gets the path to the .agent directory within the project directory."""
    return get_project_dir() / ".agent"

def get_db_path() -> Path:
    """Gets the full path to the SQLite database file."""
    return config_manager.get_database_path()

# Environment variable validation
def validate_startup_environment() -> None:
    """Validate environment variables at startup."""
    missing_vars = config_manager.validate_environment_variables()
    
    if missing_vars:
        error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
        logger.error(error_msg)
        raise ConfigError(error_msg)
    
    if not config_manager.openai.api_key:
        logger.error("CRITICAL: OPENAI_API_KEY not found in environment variables.")
        logger.error("Please set it in your .env file or environment.")

# Initialize environment validation
validate_startup_environment()

# Log that configuration is loaded
logger.info("Core configuration loaded with comprehensive management system.")
logger.info(f"TMUX Bible features: Git discipline={config_manager.tmux.auto_commit_enabled}, "
           f"Max agents={config_manager.tmux.max_active_agents}, Credit conservation={config_manager.tmux.credit_conservation_mode}")
