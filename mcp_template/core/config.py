# Agent-MCP/mcp_template/mcp_server_src/core/config.py
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

# --- General Configuration ---
DB_FILE_NAME: str = "mcp_state.db"  # From main.py:39

# --- Logging Configuration ---
LOG_FILE_NAME: str = "mcp_server.log" # Based on main.py:46
LOG_LEVEL: int = logging.INFO        # From main.py:43
LOG_FORMAT: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s' # From main.py:44

def setup_logging():
    """Configures global logging for the application."""
    # Ensure project directory is available for log file path if needed,
    # though for now, log file is in the current working directory of the server.
    # If MCP_PROJECT_DIR is set and you want logs inside .agent/logs:
    # log_dir = get_agent_dir() / "logs"
    # log_dir.mkdir(parents=True, exist_ok=True)
    # log_file_path = log_dir / LOG_FILE_NAME
    # For simplicity, keeping it as mcp_server.log in the CWD of the server process for now.
    # This matches the original behavior of main.py:46 logging.FileHandler("mcp_server.log")

    logging.basicConfig(
        level=LOG_LEVEL,
        format=LOG_FORMAT,
        handlers=[
            logging.FileHandler(LOG_FILE_NAME), # From main.py:46
            logging.StreamHandler(sys.stdout)   # From main.py:47 (StreamHandler was to stdout by default)
        ]
    )
    # Example: Suppress overly verbose logs from specific libraries if needed in the future
    # logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    # logging.getLogger("httpx").setLevel(logging.WARNING)

# Initialize logging when this module is imported
setup_logging()
logger = logging.getLogger("mcp_server") # From main.py:50

# --- Agent Appearance ---
AGENT_COLORS: List[str] = [ # From main.py:160-164 (Note: original had 160-165, but list ends on 164)
    "#FF5733", "#33FF57", "#3357FF", "#FF33A1", "#A133FF", "#33FFA1",
    "#FFBD33", "#33FFBD", "#BD33FF", "#FF3333", "#33FF33", "#3333FF",
    "#FF8C00", "#00CED1", "#9400D3", "#FF1493", "#7FFF00", "#1E90FF"
]

# --- OpenAI Model Configuration ---
EMBEDDING_MODEL: str = "text-embedding-3-large" # From main.py:178
CHAT_MODEL: str = "gpt-4.1-2025-04-14" # From main.py:179 (Ensure this matches your desired model)
EMBEDDING_DIMENSION: int = 1024 # From main.py:180
MAX_EMBEDDING_BATCH_SIZE: int = 100 # From main.py:181
MAX_CONTEXT_TOKENS: int = 12000 # From main.py:182

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
if not OPENAI_API_KEY_ENV:
    logger.error("CRITICAL: OPENAI_API_KEY not found in environment variables. Please set it in your .env file or environment.")
    # Depending on strictness, you might want to raise an exception or sys.exit(1) here
    # For now, just logging, as the openai_service.py will handle the client init failure.

# Log that configuration is loaded (optional)
logger.info("Core configuration loaded.")
# Example of how other modules will use this logger:
# from mcp_server_src.core.config import logger
# logger.info("This is a log message from another module.")