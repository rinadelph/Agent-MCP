# Agent-MCP/mcp_template/mcp_server_src/tools/agent_tools.py
from typing import List, Dict, Any, Optional

import mcp.types as mcp_types # Assuming this is your mcp.types path

from .registry import register_tool
from ..core.config import logger
from ..core import globals as g
from ..core.auth import get_agent_id # verify_token not strictly needed here
from ..utils.audit_utils import log_audit
from ..utils.project_utils import generate_system_prompt # The core logic

# --- get_system_prompt tool ---
# Original logic from main.py: lines 1352-1384 (get_system_prompt_tool function)
async def get_system_prompt_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    agent_auth_token = arguments.get("token") # This is the agent's own token

    requesting_agent_id = get_agent_id(agent_auth_token) # main.py:1355
    if not requesting_agent_id:
        return [mcp_types.TextContent(type="text", text="Unauthorized: Valid agent token required")]

    # The original code (main.py:1359-1365) tried to find the agent_token again from active_agents
    # if it wasn't the admin token. This is redundant if `agent_auth_token` is already the agent's token.
    # `generate_system_prompt` needs the agent's specific token for the connection snippet.
    # It also needs the runtime admin_token to determine if the agent IS the admin.

    # The `generate_system_prompt` function from `project_utils` now takes:
    # (agent_id: str, agent_token_for_prompt: str, admin_token_runtime: Optional[str])
    # `agent_auth_token` is the `agent_token_for_prompt`.
    # `g.admin_token` is the `admin_token_runtime`.
    
    system_prompt_str = generate_system_prompt(
        agent_id=requesting_agent_id,
        agent_token_for_prompt=agent_auth_token, # Pass the agent's own token
        admin_token_runtime=g.admin_token # Pass the current global admin token
    ) # main.py:1368-1373 (call to generate_system_prompt)

    log_audit(requesting_agent_id, "get_system_prompt", {}) # main.py:1375
    
    logger.info(f"Provided system prompt for agent '{requesting_agent_id}'.")
    return [mcp_types.TextContent(
        type="text",
        text=f"System Prompt for Agent '{requesting_agent_id}':\n\n{system_prompt_str}"
    )] # main.py:1377-1381


# --- Register agent-specific tools ---
def register_agent_tools():
    register_tool(
        name="get_system_prompt", # main.py:1773 (schema name)
        description="Get the tailored system prompt for the currently authenticated agent, including connection instructions.",
        input_schema={ # From main.py:1774-1786
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "Agent authentication token (the agent's own token)"}
            },
            "required": ["token"],
            "additionalProperties": False
        },
        implementation=get_system_prompt_tool_impl
    )

# Call registration when this module is imported
register_agent_tools()