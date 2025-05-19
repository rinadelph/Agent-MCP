# Agent-MCP/mcp_template/mcp_server_src/utils/signal_utils.py
import signal
import sys
from typing import Any

# Import the global state module
from ..core import globals as g
# Import the central logger
from ..core.config import logger


# Original location: main.py lines 830-836 (signal_handler function)
def mcp_signal_handler(sig: int, frame: Any) -> None: # Added type hints, frame can be 'Any' or more specific if needed
    """
    Handles termination signals like SIGINT (Ctrl+C) and SIGTERM.
    Sets the global `g.server_running` flag to False to initiate graceful shutdown.
    """
    signal_name = signal.Signals(sig).name if sys.version_info >= (3,8) else f"Signal {sig}"
    
    logger.info(f"Received {signal_name}. Initiating graceful shutdown of MCP server...")
    # Matching original print statement (main.py:832)
    print(f"\nShutting down MCP server gracefully... (Received {signal_name})")

    g.server_running = False # Update the global flag (main.py:833)

    # The original code (main.py:835) had `print("Server shutdown complete")`
    # and `sys.exit(0)` (main.py:836).
    # In a more robust componentized server, the actual shutdown (closing sockets,
    # joining threads/tasks) happens in the main server loop after `g.server_running`
    # becomes False. The `sys.exit(0)` here is abrupt.
    # We will rely on the main server loop (e.g., Uvicorn or AnyIO task group)
    # to terminate cleanly when `g.server_running` is false or when it catches
    # the KeyboardInterrupt/SystemExit that the signal might re-raise.
    # For now, we are just setting the flag. The application entry point will handle the exit.
    logger.info("g.server_running flag set to False. Server should stop accepting new work and clean up.")
    # The print("Server shutdown complete") will now likely come from the main server teardown logic.


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