# Agent-MCP/mcp_template/mcp_server_src/utils/signal_utils.py
import signal
import sys
from typing import Any

# Import the global state module
from ..core import globals as g
# Import the central logger
from ..core.config import logger


# Original location: main.py lines 830-836 (signal_handler function)
def mcp_signal_handler(sig: int, frame: Any) -> None:
    """
    Handles termination signals like SIGINT (Ctrl+C) and SIGTERM.
    Performs immediate exit without cleanup.
    """
    signal_name = signal.Signals(sig).name if sys.version_info >= (3,8) else f"Signal {sig}"
    
    # Immediate exit without logging
    # os._exit is more forceful than sys.exit
    import os
    os._exit(0)


# Original location: main.py lines 839-840 (signal.signal calls)
def register_signal_handlers() -> None:
    """Registers the application's signal handlers."""
    try:
        signal.signal(signal.SIGINT, mcp_signal_handler)  # Handles Ctrl+C
        signal.signal(signal.SIGTERM, mcp_signal_handler) # Handles termination signals (e.g., from `kill`)
        logger.info("Registered SIGINT and SIGTERM signal handlers.")
    except ValueError as e:
        # This can happen if trying to register signals in a non-main thread on some OSes
        logger.warning(f"Could not register signal handlers (may not be in main thread or unsupported OS feature): {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while registering signal handlers: {e}", exc_info=True)

# The call to register_signal_handlers() will be done once during application startup,
# typically from the main CLI entry point (`cli.py`) or server setup (`app/server_lifecycle.py`).