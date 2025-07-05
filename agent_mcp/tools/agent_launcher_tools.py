# Agent-MCP/agent_mcp/tools/agent_launcher_tools.py
from typing import List, Dict, Any
import mcp.types as mcp_types

from .registry import register_tool
from ..core.auth import verify_token
from ..utils.audit_utils import log_audit
from ..utils.prompt_templates import get_available_templates
from .admin_tools import create_agent_tool_impl  # Reuse the main create_agent function


async def create_worker_agent_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    """
    Quick helper to create a worker agent with the specific RAG prompt template.
    This is a convenience wrapper around create_agent with predefined settings.
    """
    token = arguments.get("token")
    agent_id = arguments.get("agent_id")
    working_directory = arguments.get("working_directory")
    
    if not verify_token(token, "admin"):
        return [mcp_types.TextContent(type="text", text="Unauthorized: Admin token required")]
    
    if not agent_id:
        return [mcp_types.TextContent(type="text", text="Error: agent_id is required")]
    
    # Build the create_agent arguments with the specific template
    create_args = {
        "token": token,
        "agent_id": agent_id,
        "capabilities": ["code_edit", "file_read", "task_management"],
        "prompt_template": "worker_with_rag",
        "send_prompt": True,
        "prompt_delay": 5  # Slightly longer delay for stability
    }
    
    if working_directory:
        create_args["working_directory"] = working_directory
    
    # Call the main create_agent function
    result = await create_agent_tool_impl(create_args)
    
    # Add audit log
    log_audit("admin", "create_worker_agent", {
        "agent_id": agent_id,
        "template": "worker_with_rag",
        "auto_prompt": True
    })
    
    return result


async def list_prompt_templates_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    """
    List all available prompt templates for agent creation.
    """
    token = arguments.get("token")
    
    if not verify_token(token, "admin"):
        return [mcp_types.TextContent(type="text", text="Unauthorized: Admin token required")]
    
    templates = get_available_templates()
    
    template_info = "Available Prompt Templates:\n\n"
    for template_name, description in templates.items():
        template_info += f"• **{template_name}**: {description}\n"
    
    template_info += "\nUse these template names with the 'prompt_template' parameter in create_agent."
    
    return [mcp_types.TextContent(type="text", text=template_info)]


def register_agent_launcher_tools():
    """Register the agent launcher convenience tools."""
    
    register_tool(
        name="create_worker_agent",
        description="Quick helper to create a worker agent with the RAG prompt template and auto-prompt sending.",
        input_schema={
            "type": "object",
            "properties": {
                "token": {
                    "type": "string", 
                    "description": "Admin authentication token"
                },
                "agent_id": {
                    "type": "string", 
                    "description": "Unique identifier for the worker agent"
                },
                "working_directory": {
                    "type": "string",
                    "description": "Optional working directory for the agent. Defaults to project root."
                }
            },
            "required": ["token", "agent_id"],
            "additionalProperties": False
        },
        implementation=create_worker_agent_tool_impl
    )
    
    register_tool(
        name="list_prompt_templates",
        description="List all available prompt templates for agent creation.",
        input_schema={
            "type": "object",
            "properties": {
                "token": {
                    "type": "string", 
                    "description": "Admin authentication token"
                }
            },
            "required": ["token"],
            "additionalProperties": False
        },
        implementation=list_prompt_templates_tool_impl
    )


# Auto-register when imported
register_agent_launcher_tools()