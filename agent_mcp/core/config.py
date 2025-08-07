# Agent-MCP/mcp_template/mcp_server_src/core/config.py
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

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


# --- General Configuration ---
DB_FILE_NAME: str = "mcp_state.db"  # From main.py:39

# --- Logging Configuration ---
LOG_FILE_NAME: str = "mcp_server.log"  # Based on main.py:46
LOG_LEVEL: int = logging.INFO  # From main.py:43
LOG_FORMAT_FILE: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FORMAT_CONSOLE: str = (
    f"%(asctime)s - %(name)s - %(levelname)s - {TUIColors.DIM}%(message)s{TUIColors.ENDC}"  # Dim message text
)

CONSOLE_LOGGING_ENABLED = (
    os.environ.get("MCP_DEBUG", "false").lower() == "true"
)  # Enable console logging in debug mode


def setup_logging():
    """Configures global logging for the application."""

    root_logger = logging.getLogger()  # Get the root logger
    root_logger.setLevel(LOG_LEVEL)  # Set level on the root logger

    # Clear any existing handlers on the root logger to avoid duplication
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 1. File Handler (only in debug mode)
    debug_mode = os.environ.get("MCP_DEBUG", "false").lower() == "true"
    if debug_mode:
        file_formatter = logging.Formatter(LOG_FORMAT_FILE)
        file_handler = logging.FileHandler(
            LOG_FILE_NAME, mode="a", encoding="utf-8"
        )  # Append mode
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

    # 2. Console Handler (with colors, conditional)
    if CONSOLE_LOGGING_ENABLED:
        console_formatter = ColorfulFormatter(
            LOG_FORMAT_CONSOLE, datefmt="%H:%M:%S"
        )  # Simpler datefmt for console
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        # Filter out less important messages for console if desired
        # console_handler.setLevel(logging.INFO)  # Example: only INFO and above for console
        root_logger.addHandler(console_handler)

    # Suppress overly verbose logs from specific libraries for both file and console
    logging.getLogger("watchfiles").setLevel(logging.WARNING)
    # Uvicorn access logs are handled by Uvicorn's config (access_log=False in cli.py)
    # but we can also try to manage its error logger if needed.
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.WARNING)  # General uvicorn logger
    logging.getLogger("mcp.server.lowlevel.server").propagate = (
        False  # Prevent duplication if it logs directly
    )


def enable_console_logging():
    """Enable console logging dynamically (used when debug mode is enabled)."""
    global CONSOLE_LOGGING_ENABLED
    CONSOLE_LOGGING_ENABLED = True
    # Re-setup logging to add file handler when debug mode is enabled
    setup_logging()

    root_logger = logging.getLogger()

    # Check if console handler already exists
    has_console_handler = any(
        isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout
        for handler in root_logger.handlers
    )

    if not has_console_handler:
        console_formatter = ColorfulFormatter(LOG_FORMAT_CONSOLE, datefmt="%H:%M:%S")
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(console_formatter)
        # Set logging level to DEBUG for more verbose output
        console_handler.setLevel(logging.DEBUG)
        root_logger.addHandler(console_handler)

        # Also set root logger to DEBUG level
        root_logger.setLevel(logging.DEBUG)


# Initialize logging when this module is imported
setup_logging()
logger = logging.getLogger("mcp_server")  # Main application logger

# --- Agent Appearance ---
AGENT_COLORS: List[str] = (
    [  # From main.py:160-164 (Note: original had 160-165, but list ends on 164)
        "#FF5733",
        "#33FF57",
        "#3357FF",
        "#FF33A1",
        "#A133FF",
        "#33FFA1",
        "#FFBD33",
        "#33FFBD",
        "#BD33FF",
        "#FF3333",
        "#33FF33",
        "#3333FF",
        "#FF8C00",
        "#00CED1",
        "#9400D3",
        "#FF1493",
        "#7FFF00",
        "#1E90FF",
    ]
)

# --- OpenAI Model Configuration ---
# Advanced mode flag - set by CLI
ADVANCED_EMBEDDINGS: bool = False  # Default to simple mode

# Auto-indexing control - set by CLI
DISABLE_AUTO_INDEXING: bool = False  # Default to automatic indexing

# Original/Simple mode configuration (default) - restored to original values
SIMPLE_EMBEDDING_MODEL: str = (
    "text-embedding-3-large"  # Original embedding model (unchanged)
)
SIMPLE_EMBEDDING_DIMENSION: int = 1536  # Increased from 1024 for better performance

# Advanced mode configuration - new enhanced mode
ADVANCED_EMBEDDING_MODEL: str = "text-embedding-3-large"  # From main.py:178
ADVANCED_EMBEDDING_DIMENSION: int = (
    3072  # Full dimension for text-embedding-3-large for better code understanding
)

# Dynamic configuration based on mode
EMBEDDING_MODEL: str = (
    ADVANCED_EMBEDDING_MODEL if ADVANCED_EMBEDDINGS else SIMPLE_EMBEDDING_MODEL
)
EMBEDDING_DIMENSION: int = (
    ADVANCED_EMBEDDING_DIMENSION if ADVANCED_EMBEDDINGS else SIMPLE_EMBEDDING_DIMENSION
)

CHAT_MODEL: str = (
    "gpt-4.1-2025-04-14"  # From main.py:179 (Ensure this matches your desired model)
)
TASK_ANALYSIS_MODEL: str = (
    "gpt-4.1-2025-04-14"  # Same model for consistent task placement analysis
)
MAX_EMBEDDING_BATCH_SIZE: int = 100  # From main.py:181
MAX_CONTEXT_TOKENS: int = 1000000  # GPT-4.1 has 1M token context window
TASK_ANALYSIS_MAX_TOKENS: int = (
    1000000  # Same 1M token context window for task analysis
)

# --- Project Directory Helpers ---
# These rely on an environment variable "MCP_PROJECT_DIR" being set,
# typically by the CLI entry point (previously in main.py:1953, will be in cli.py).


def get_project_dir() -> Path:
    """Gets the resolved absolute path to the project directory."""
    project_dir_str = os.environ.get("MCP_PROJECT_DIR")
    if not project_dir_str:
        # This case should ideally be handled at startup by the CLI,
        # ensuring MCP_PROJECT_DIR is always set.
        logger.error("CRITICAL: MCP_PROJECT_DIR environment variable is not set.")
        # Fallback to current directory, but this is likely not intended for normal operation.
        return Path(".").resolve()
    return Path(project_dir_str).resolve()


def get_agent_dir() -> Path:
    """Gets the path to the .agent directory within the project directory."""
    return get_project_dir() / ".agent"


def get_db_path() -> Path:
    """Gets the full path to the SQLite database file."""
    return get_agent_dir() / DB_FILE_NAME


# --- Environment Variable Check (Optional but good practice) ---
OPENAI_API_KEY_ENV: Optional[str] = os.environ.get("OPENAI_API_KEY")  # From main.py:174
# Debug print statement removed for clean console output
if not OPENAI_API_KEY_ENV:
    logger.error(
        "CRITICAL: OPENAI_API_KEY not found in environment variables. Please set it in your .env file or environment."
    )
    # Depending on strictness, you might want to raise an exception or sys.exit(1) here
    # For now, just logging, as the openai_service.py will handle the client init failure.

# --- Task Placement Configuration (System 8) ---
ENABLE_TASK_PLACEMENT_RAG: bool = (
    os.getenv("ENABLE_TASK_PLACEMENT_RAG", "true").lower() == "true"
)
TASK_DUPLICATION_THRESHOLD: float = float(
    os.getenv("TASK_DUPLICATION_THRESHOLD", "0.8")
)
ALLOW_RAG_OVERRIDE: bool = os.getenv("ALLOW_RAG_OVERRIDE", "true").lower() == "true"
TASK_PLACEMENT_RAG_TIMEOUT: int = int(
    os.getenv("TASK_PLACEMENT_RAG_TIMEOUT", "5")
)  # seconds

# --- TMUX Bible Configuration ---
# Based on critical lessons learned from multi-agent orchestration
# These settings enforce the rules and protocols documented in tmux-bible.md

# Git discipline constants (mandatory for all agents)
TMUX_GIT_COMMIT_INTERVAL: int = 1800  # 30 minutes in seconds - never exceed this
TMUX_MAX_WORK_WITHOUT_COMMIT: int = 3600  # 1 hour absolute maximum
TMUX_AUTO_COMMIT_ENABLED: bool = True  # Enable automatic commit reminders

# Communication protocol timing
TMUX_CLAUDE_STARTUP_DELAY: int = 5  # seconds to wait for Claude to start
TMUX_MESSAGE_SEND_DELAY: float = 0.5  # delay between typing and Enter key
TMUX_STATUS_CHECK_INTERVAL: int = 300  # 5 minutes for regular agent checks
TMUX_COMPLIANCE_CHECK_INTERVAL: int = 120  # 2 minutes for non-compliant agents

# Agent limits and cleanup (enforce resource discipline)
TMUX_MAX_ACTIVE_AGENTS: int = 10  # Hard limit from TMUX Bible - prevents resource exhaustion
TMUX_AGENT_IDLE_TIMEOUT: int = 3600  # 1 hour - kill idle agents to free resources
TMUX_AUTO_CLEANUP_ENABLED: bool = True  # Enable automatic cleanup of orphaned sessions

# Budget discipline settings (critical for credit conservation)
TMUX_CREDIT_CONSERVATION_MODE: bool = os.environ.get("TMUX_CREDIT_CONSERVATION", "true").lower() == "true"
TMUX_BATCH_MESSAGES_ENABLED: bool = True  # Batch instructions to reduce API calls
TMUX_PM_AUTONOMY_TARGET: float = 0.8  # PM should handle 80% of issues independently

# Compliance enforcement (strike system from TMUX Bible)
TMUX_STRIKE_SYSTEM_ENABLED: bool = True
TMUX_MAX_STRIKES_PER_AGENT: int = 3  # Three strikes and agent is replaced
TMUX_COMPLIANCE_THRESHOLD: float = 0.7  # Minimum compliance score to avoid strikes

# Window naming conventions (auto-rename feature)
TMUX_AUTO_RENAME_WINDOWS: bool = True  # Automatically suggest descriptive window names
TMUX_WINDOW_NAMING_CONVENTIONS: Dict[str, str] = {
    'claude_agent': 'Claude-{role}',
    'dev_server': '{framework}-{purpose}',
    'shell': '{project}-Shell',
    'service': '{service}-Server',
    'temp_agent': 'TEMP-{purpose}'
}

# Emergency protocols (escalation and recovery)
TMUX_EMERGENCY_STOP_ENABLED: bool = True  # Enable Escape key emergency stop
TMUX_AUTO_RECOVERY_ENABLED: bool = True  # Attempt to recover from agent failures
TMUX_ESCALATION_TIMEOUT: int = 300  # 5 minutes before escalating to orchestrator

# Monitoring and alerting
TMUX_MONITORING_ENABLED: bool = True  # Enable comprehensive agent monitoring
TMUX_ALERT_ON_COMPLIANCE_ISSUES: bool = True  # Alert when compliance drops
TMUX_PERFORMANCE_MONITORING: bool = True  # Monitor response times and task completion

# Log that configuration is loaded (optional)
logger.info("Core configuration loaded (with colorful logging setup and TMUX Bible integration).")
logger.info(f"TMUX Bible features: Git discipline={TMUX_AUTO_COMMIT_ENABLED}, "
           f"Max agents={TMUX_MAX_ACTIVE_AGENTS}, Credit conservation={TMUX_CREDIT_CONSERVATION_MODE}")
# Example of how other modules will use this logger:
# from mcp_server_src.core.config import logger
# logger.info("This is a log message from another module.")
