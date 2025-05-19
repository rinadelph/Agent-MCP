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
    HEADER = '\033[95m'    # Light Magenta
    OKBLUE = '\033[94m'    # Light Blue
    OKCYAN = '\033[96m'    # Light Cyan
    OKGREEN = '\033[92m'   # Light Green
    WARNING = '\033[93m'   # Yellow
    FAIL = '\033[91m'      # Red
    ENDC = '\033[0m'       # Reset to default
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    DIM = '\033[2m'

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
        record.levelname = f"{color}{record.levelname:<8}{TUIColors.ENDC}"  # Pad levelname
        record.name = f"{TUIColors.OKBLUE}{record.name}{TUIColors.ENDC}"
        return super().format(record)

# --- General Configuration ---
DB_FILE_NAME: str = "mcp_state.db"  # From main.py:39

# --- Logging Configuration ---
LOG_FILE_NAME: str = "mcp_server.log" # Based on main.py:46
LOG_LEVEL: int = logging.INFO        # From main.py:43
LOG_FORMAT_FILE: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
LOG_FORMAT_CONSOLE: str = f'%(asctime)s - %(name)s - %(levelname)s - {TUIColors.DIM}%(message)s{TUIColors.ENDC}'  # Dim message text

CONSOLE_LOGGING_ENABLED = False  # New flag to control console logging globally

def setup_logging():
    """Configures global logging for the application."""
    
    root_logger = logging.getLogger()  # Get the root logger
    root_logger.setLevel(LOG_LEVEL)    # Set level on the root logger

    # Clear any existing handlers on the root logger to avoid duplication
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 1. File Handler (always add this, no colors)
    file_formatter = logging.Formatter(LOG_FORMAT_FILE)
    file_handler = logging.FileHandler(LOG_FILE_NAME, mode='a', encoding='utf-8')  # Append mode
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # 2. Console Handler (with colors, conditional)
    if CONSOLE_LOGGING_ENABLED:
        console_formatter = ColorfulFormatter(LOG_FORMAT_CONSOLE, datefmt='%H:%M:%S')  # Simpler datefmt for console
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
    logging.getLogger("mcp.server.lowlevel.server").propagate = False  # Prevent duplication if it logs directly

# Initialize logging when this module is imported
setup_logging()
logger = logging.getLogger("mcp_server")  # Main application logger

# --- Agent Appearance ---
AGENT_COLORS: List[str] = [ # From main.py:160-164 (Note: original had 160-165, but list ends on 164)
    "#FF5733", "#33FF57", "#3357FF", "#FF33A1", "#A133FF", "#33FFA1",
    "#FFBD33", "#33FFBD", "#BD33FF", "#FF3333", "#33FF33", "#3333FF",
    "#FF8C00", "#00CED1", "#9400D3", "#FF1493", "#7FFF00", "#1E90FF"
]

# --- OpenAI Model Configuration ---
EMBEDDING_MODEL: str = "text-embedding-3-large" # From main.py:178
CHAT_MODEL: str = "gpt-4.1-2025-04-14" # From main.py:179 (Ensure this matches your desired model)
TASK_ANALYSIS_MODEL: str = "gpt-3.5-turbo-16k" # Cheaper model for task placement analysis
EMBEDDING_DIMENSION: int = 1024 # From main.py:180
MAX_EMBEDDING_BATCH_SIZE: int = 100 # From main.py:181
MAX_CONTEXT_TOKENS: int = 12000 # From main.py:182
TASK_ANALYSIS_MAX_TOKENS: int = 16000 # Context window for task analysis model

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
OPENAI_API_KEY_ENV: Optional[str] = os.environ.get("OPENAI_API_KEY") # From main.py:174
# Debug print statement removed for clean console output
if not OPENAI_API_KEY_ENV:
    logger.error("CRITICAL: OPENAI_API_KEY not found in environment variables. Please set it in your .env file or environment.")
    # Depending on strictness, you might want to raise an exception or sys.exit(1) here
    # For now, just logging, as the openai_service.py will handle the client init failure.

# --- Task Placement Configuration (System 8) ---
ENABLE_TASK_PLACEMENT_RAG: bool = os.getenv("ENABLE_TASK_PLACEMENT_RAG", "true").lower() == "true"
TASK_DUPLICATION_THRESHOLD: float = float(os.getenv("TASK_DUPLICATION_THRESHOLD", "0.8"))
ALLOW_RAG_OVERRIDE: bool = os.getenv("ALLOW_RAG_OVERRIDE", "true").lower() == "true"
TASK_PLACEMENT_RAG_TIMEOUT: int = int(os.getenv("TASK_PLACEMENT_RAG_TIMEOUT", "5"))  # seconds

# Log that configuration is loaded (optional)
logger.info("Core configuration loaded (with colorful logging setup).")
# Example of how other modules will use this logger:
# from mcp_server_src.core.config import logger
# logger.info("This is a log message from another module.")