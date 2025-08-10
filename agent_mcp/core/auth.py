# Agent-MCP/mcp_template/mcp_server_src/core/auth.py
import secrets
from typing import Optional

# Import globals that these functions will operate on
from . import globals as g
# No need to import config here as these functions don't directly use it.

# Original location: main.py, lines 852-854
def generate_token() -> str:
    """Generate a secure random token."""
    return secrets.token_hex(16)

# Original location: main.py, lines 856-866
def verify_token(token: str, required_role: str = "agent") -> bool:
    """
    Verify if a token is valid and has the required role.
    Uses global `g.admin_token` and `g.active_agents`.
    """
    if not token: # Added a check for empty/None token
        return False
    if required_role == "admin" and token == g.admin_token:
        return True
    # Check active_agents only if it's not None and token is a key
    if required_role == "agent" and g.active_agents and token in g.active_agents:
        return True
    # Allow admin token to be used for agent roles as well
    if required_role == "agent" and token == g.admin_token:
        return True  # Admins can act as agents
    return False

# Original location: main.py, lines 868-873
def get_agent_id(token: str) -> Optional[str]:
    """
    Get agent ID from token.
    Uses global `g.admin_token` and `g.active_agents`.
    """
    if not token: # Added a check for empty/None token
        return None
    if token == g.admin_token:
        return "admin" # 'admin' is a special agent_id for admin operations
    # Check active_agents only if it's not None and token is a key
    if g.active_agents and token in g.active_agents:
        # Ensure the agent data dictionary has 'agent_id'
        agent_data = g.active_agents[token]
        if isinstance(agent_data, dict) and "agent_id" in agent_data:
            return agent_data["agent_id"]
    return None