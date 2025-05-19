# Agent-MCP/mcp_template/mcp_server_src/tools/rag_tools.py
from typing import List, Dict, Any

import mcp.types as mcp_types # Assuming this is your mcp.types path

from .registry import register_tool
from ..core.config import logger
# No direct use of g (globals) here, auth and RAG core logic handle that.
from ..core.auth import get_agent_id # Corrected
from ..utils.audit_utils import log_audit # Corrected
# Import the core RAG querying logic
from ..features.rag.query import query_rag_system # Corrected

# --- ask_project_rag tool ---
# Original logic for the tool part from main.py: lines 1572-1578 (ask_project_rag_tool function shell)
# The core RAG execution is in features/rag/query.py's query_rag_system.
async def ask_project_rag_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    agent_auth_token = arguments.get("token")
    query_text = arguments.get("query")

    requesting_agent_id = get_agent_id(agent_auth_token) # main.py:1575
    if not requesting_agent_id:
        return [mcp_types.TextContent(type="text", text="Unauthorized: Valid agent token required")]

    if not query_text or not isinstance(query_text, str):
        return [mcp_types.TextContent(type="text", text="Error: query text is required and must be a string.")]

    # Log audit (main.py:1578)
    log_audit(requesting_agent_id, "ask_project_rag", {"query": query_text})
    
    logger.info(f"Agent '{requesting_agent_id}' is asking project RAG: '{query_text[:100]}...'")

    try:
        # Call the core RAG system function from features/rag/query.py
        # This function (query_rag_system) handles all the complex RAG logic.
        answer_text = await query_rag_system(query_text)
        
        # The query_rag_system already handles internal errors and returns a string.
        return [mcp_types.TextContent(type="text", text=answer_text)]
        
    except Exception as e:
        # This catch block is for unexpected errors specifically within this tool_impl wrapper,
        # not for errors within query_rag_system itself, as those are handled internally by it.
        logger.error(f"Unexpected error in ask_project_rag_tool_impl for agent '{requesting_agent_id}': {e}", exc_info=True)
        return [mcp_types.TextContent(type="text", text=f"An unexpected error occurred while processing your RAG query: {str(e)}")]


# --- Register RAG tools ---
def register_rag_tools():
    register_tool(
        name="ask_project_rag", # main.py:1869 (schema name)
        description="Ask a natural language question about the project. The system uses RAG (Retrieval Augmented Generation) to find relevant information from indexed documentation, context, and metadata to synthesize an answer.",
        input_schema={ # From main.py:1870-1881
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "Authentication token for the agent making the query."},
                "query": {"type": "string", "description": "The natural language question to ask about the project."}
            },
            "required": ["token", "query"],
            "additionalProperties": False
        },
        implementation=ask_project_rag_tool_impl
    )

# Call registration when this module is imported
register_rag_tools()