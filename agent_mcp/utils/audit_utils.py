# Agent-MCP/mcp_template/mcp_server_src/utils/audit_utils.py
import datetime
import json
from typing import Dict, Any

# Import logger from the central config
from ..core.config import logger
# Import the global audit_log list
from ..core import globals as g # Corrected import alias

# The name of the audit log file, consistent with the original.
# This file will be created in the directory where the server is run.
# (Original main.py line 868: with open("agent_audit.log", "a"))
AUDIT_LOG_FILE_NAME = "agent_audit.log"

# Original location: main.py lines 838-850 (Note: line numbers in your prompt were for auth.py)
# The actual function `log_audit` in `main.py` starts around line 838.
def log_audit(agent_id: str, action: str, details: Dict[str, Any]) -> None:
    """
    Log an audit entry for agent actions to both in-memory list (g.audit_log)
    and a persistent file (agent_audit.log).

    Original main.py lines: approximately 838-850.
    """
    timestamp = datetime.datetime.now().isoformat()
    entry = {
        "timestamp": timestamp,
        "agent_id": agent_id,
        "action": action,
        "details": details  # details is expected to be a dictionary
    }

    # Append to the in-memory global audit log
    # (Original main.py line 844: audit_log.append(entry))
    if g.audit_log is not None: # Defensive check, though it's initialized
        g.audit_log.append(entry)
    else:
        logger.warning("Global audit_log list is None. Cannot append in-memory audit entry.")

    # Log to the main server logger (console and mcp_server.log)
    # (Original main.py line 845: logger.info(f"AUDIT: {agent_id} - {action} - {json.dumps(details)}"))
    try:
        # Attempt to serialize details for logging; use str() as a fallback.
        details_for_logging = json.dumps(details)
    except TypeError:
        details_for_logging = str(details)
    logger.info(f"AUDIT: {agent_id} - {action} - {details_for_logging}")

    # Write to the persistent audit log file (agent_audit.log) - only in debug mode
    # (Original main.py lines 847-849: with open("agent_audit.log", "a") as f: ...)
    import os
    debug_mode = os.environ.get("MCP_DEBUG", "false").lower() == "true"
    if debug_mode:
        try:
            with open(AUDIT_LOG_FILE_NAME, "a", encoding='utf-8') as f:
                # Each line in the file should be a self-contained JSON object.
                json.dump(entry, f)
                f.write("\n")  # Newline after each JSON entry for better readability and parsing
        except IOError as e:
            logger.error(f"IOError writing to audit log file '{AUDIT_LOG_FILE_NAME}': {e}")
        except Exception as e: # Catch any other unexpected errors during file write
            logger.error(f"Unexpected error writing to audit log file '{AUDIT_LOG_FILE_NAME}': {e}", exc_info=True)