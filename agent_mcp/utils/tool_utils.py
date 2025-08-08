# Agent-MCP Tool Utilities
"""
Shared utility functions for tool implementations to eliminate code duplication
and standardize common patterns across all tools.
"""

import json
import datetime
import secrets
from typing import List, Dict, Any, Optional, Callable, Awaitable
from functools import wraps
import mcp.types as mcp_types

from ..core.config import logger
from ..core.auth import verify_token, get_agent_id
from ..utils.audit_utils import log_audit
from ..utils.db_utils import execute_query, execute_update, safe_query
from ..db.connection import execute_db_write


class ToolError(Exception):
    """Base exception for tool-related errors."""
    pass


class ToolValidationError(ToolError):
    """Exception for tool validation errors."""
    pass


class ToolPermissionError(ToolError):
    """Exception for tool permission errors."""
    pass


def generate_unique_id(prefix: str = "id") -> str:
    """Generate a unique ID with optional prefix."""
    return f"{prefix}_{secrets.token_hex(6)}"


def validate_required_params(arguments: Dict[str, Any], required_params: List[str]) -> None:
    """Validate that required parameters are present in arguments."""
    missing_params = [param for param in required_params if param not in arguments or arguments[param] is None]
    if missing_params:
        raise ToolValidationError(f"Missing required parameters: {', '.join(missing_params)}")


def validate_token_permission(token: str, required_permission: str = "admin") -> bool:
    """Validate token and check permission level."""
    if not token:
        raise ToolPermissionError("Token is required")
    
    if not verify_token(token, required_permission):
        raise ToolPermissionError(f"Unauthorized: {required_permission} permission required")
    
    return True


def get_current_agent_id(token: str) -> Optional[str]:
    """Get current agent ID from token."""
    try:
        return get_agent_id(token)
    except Exception as e:
        logger.warning(f"Could not extract agent ID from token: {e}")
        return None


def format_success_response(message: str, data: Optional[Dict[str, Any]] = None) -> List[mcp_types.TextContent]:
    """Format a successful tool response."""
    response_text = f"✅ {message}"
    if data:
        response_text += f"\n\nData: {json.dumps(data, indent=2, default=str)}"
    
    return [mcp_types.TextContent(type="text", text=response_text)]


def format_error_response(error_message: str, error_type: str = "Error") -> List[mcp_types.TextContent]:
    """Format an error tool response."""
    return [mcp_types.TextContent(type="text", text=f"❌ {error_type}: {error_message}")]


def log_tool_operation(operation: str, agent_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
    """Log tool operation for audit purposes."""
    log_data = {
        "operation": operation,
        "timestamp": datetime.datetime.now().isoformat(),
        "agent_id": agent_id,
    }
    if details:
        log_data.update(details)
    
    log_audit("tool_operation", log_data)


def safe_tool_operation(func: Callable[..., Awaitable[List[mcp_types.TextContent]]]):
    """Decorator for safe tool operations with error handling."""
    @wraps(func)
    async def wrapper(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
        try:
            return await func(arguments)
        except ToolValidationError as e:
            logger.warning(f"Tool validation error: {e}")
            return format_error_response(str(e), "Validation Error")
        except ToolPermissionError as e:
            logger.warning(f"Tool permission error: {e}")
            return format_error_response(str(e), "Permission Error")
        except Exception as e:
            logger.error(f"Tool operation failed: {e}", exc_info=True)
            return format_error_response(f"Internal error: {str(e)}", "System Error")
    
    return wrapper


def with_database_transaction(func: Callable[..., Awaitable[List[mcp_types.TextContent]]]):
    """Decorator for database operations with transaction support."""
    @wraps(func)
    async def wrapper(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
        async def db_operation():
            return await func(arguments)
        
        try:
            return await execute_db_write(db_operation)
        except Exception as e:
            logger.error(f"Database operation failed: {e}", exc_info=True)
            return format_error_response(f"Database error: {str(e)}", "Database Error")
    
    return wrapper


def validate_task_ids(task_ids: List[str]) -> None:
    """Validate that task IDs exist in the database."""
    if not task_ids:
        raise ToolValidationError("Task IDs list cannot be empty")
    
    # Check if tasks exist
    task_ids_str = "','".join(task_ids)
    query = f"SELECT COUNT(*) FROM tasks WHERE task_id IN ('{task_ids_str}')"
    result = execute_query(query)
    
    if not result or result[0]['COUNT(*)'] != len(task_ids):
        raise ToolValidationError(f"One or more task IDs not found: {task_ids}")


def validate_agent_id(agent_id: str) -> None:
    """Validate that agent ID exists and is active."""
    if not agent_id:
        raise ToolValidationError("Agent ID is required")
    
    query = "SELECT COUNT(*) FROM agents WHERE agent_id = ? AND status = 'active'"
    result = execute_query(query, (agent_id,))
    
    if not result or result[0]['COUNT(*)'] == 0:
        raise ToolValidationError(f"Agent '{agent_id}' not found or not active")


def get_agent_workload(agent_id: str) -> Dict[str, Any]:
    """Get current workload for an agent."""
    query = """
    SELECT 
        COUNT(*) as total_tasks,
        COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_tasks,
        COUNT(CASE WHEN status = 'in_progress' THEN 1 END) as active_tasks,
        COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_tasks
    FROM tasks 
    WHERE assigned_to = ?
    """
    result = execute_query(query, (agent_id,))
    return result[0] if result else {}


def format_task_summary(task: Dict[str, Any]) -> str:
    """Format a task for summary display."""
    priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}
    status_emoji = {
        "pending": "⏳", "in_progress": "🔄", "completed": "✅", 
        "cancelled": "❌", "blocked": "🚫"
    }
    
    priority = task.get('priority', 'medium')
    status = task.get('status', 'pending')
    
    return (
        f"{priority_emoji.get(priority, '⚪')} {status_emoji.get(status, '❓')} "
        f"**{task.get('title', 'Untitled')}** "
        f"({task.get('task_id', 'unknown')})"
    )


def format_detailed_task(task: Dict[str, Any]) -> str:
    """Format a task for detailed display."""
    summary = format_task_summary(task)
    description = task.get('description', 'No description')
    assigned_to = task.get('assigned_to', 'Unassigned')
    created_at = task.get('created_at', 'Unknown')
    
    notes = task.get('notes', '[]')
    try:
        notes_list = json.loads(notes) if notes else []
        notes_count = len(notes_list)
    except:
        notes_count = 0
    
    return (
        f"{summary}\n"
        f"📝 **Description:** {description}\n"
        f"👤 **Assigned to:** {assigned_to}\n"
        f"📅 **Created:** {created_at}\n"
        f"💬 **Notes:** {notes_count} note(s)\n"
        f"🔗 **Dependencies:** {task.get('depends_on_tasks', '[]')}"
    )


def estimate_tokens(text: str) -> int:
    """Accurate token estimation using tiktoken for GPT-4."""
    try:
        import tiktoken
        encoding = tiktoken.encoding_for_model("gpt-4")
        return len(encoding.encode(text))
    except ImportError:
        # Fallback to rough estimation if tiktoken not available
        return len(text) // 4
    except Exception:
        # Fallback for any other tiktoken errors
        return len(text) // 4


def sanitize_session_name(name: str) -> str:
    """Sanitize session name for TMUX compatibility."""
    import re
    # Remove or replace invalid characters
    sanitized = re.sub(r'[^a-zA-Z0-9\-_]', '_', name)
    # Ensure it starts with a letter or number
    if sanitized and not sanitized[0].isalnum():
        sanitized = 's' + sanitized
    # Limit length
    return sanitized[:50]


def create_agent_session_name(agent_id: str, admin_token: str) -> str:
    """Create agent session name in format: agent_id-suffix."""
    def get_admin_token_suffix(token: str) -> str:
        if not token or len(token) < 4:
            return "0000"
        return token[-4:].lower()
    
    suffix = get_admin_token_suffix(admin_token)
    clean_agent_id = sanitize_session_name(agent_id)
    return f"{clean_agent_id}-{suffix}"


# Common tool parameter schemas
COMMON_SCHEMAS = {
    "token": {
        "type": "string",
        "description": "Authentication token"
    },
    "agent_id": {
        "type": "string", 
        "description": "Agent identifier"
    },
    "task_ids": {
        "type": "array",
        "items": {"type": "string"},
        "description": "List of task IDs"
    },
    "admin_token": {
        "type": "string",
        "description": "Admin authentication token"
    }
}


def build_tool_schema(name: str, description: str, required_params: List[str], 
                     optional_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Build a standardized tool schema."""
    properties = {}
    required = []
    
    # Add common schemas
    for param in required_params:
        if param in COMMON_SCHEMAS:
            properties[param] = COMMON_SCHEMAS[param]
        else:
            properties[param] = {"type": "string", "description": f"{param} parameter"}
        required.append(param)
    
    # Add optional parameters
    if optional_params:
        properties.update(optional_params)
    
    return {
        "name": name,
        "description": description,
        "inputSchema": {
            "type": "object",
            "properties": properties,
            "required": required
        }
    }
