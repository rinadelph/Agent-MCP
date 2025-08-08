# MCP Orchestrator Utilities
"""
Utility functions for working with the MCP orchestrator and managing
MCP server configurations in the Agent-MCP system.
"""

import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from agent_mcp.core.config import config_manager, mcp_orchestrator
from agent_mcp.core.mcp_orchestrator import MCPServerCategory, MCPServerConfig

logger = logging.getLogger(__name__)


def get_mcp_orchestrator():
    """
    Get the global MCP orchestrator instance.
    
    Returns:
        The MCP orchestrator or None if not initialized
    """
    return mcp_orchestrator


def is_mcp_enabled() -> bool:
    """
    Check if MCP orchestration is enabled.
    
    Returns:
        True if MCP is enabled
    """
    return config_manager.mcp.enabled and mcp_orchestrator is not None


def get_active_mcp_servers() -> List[str]:
    """
    Get list of currently active MCP servers.
    
    Returns:
        List of active server names
    """
    if not is_mcp_enabled():
        return []
    return mcp_orchestrator.get_active_servers()


def get_available_mcp_servers() -> List[str]:
    """
    Get list of all available MCP servers.
    
    Returns:
        List of all configured server names
    """
    if not is_mcp_enabled():
        return []
    return mcp_orchestrator.get_all_servers()


def activate_mcp_server(server_name: str) -> bool:
    """
    Activate an MCP server.
    
    Args:
        server_name: Name of the server to activate
        
    Returns:
        True if activation successful
    """
    if not is_mcp_enabled():
        logger.warning("MCP orchestration is not enabled")
        return False
    
    return mcp_orchestrator.activate_server(server_name)


def deactivate_mcp_server(server_name: str) -> bool:
    """
    Deactivate an MCP server.
    
    Args:
        server_name: Name of the server to deactivate
        
    Returns:
        True if deactivation successful
    """
    if not is_mcp_enabled():
        logger.warning("MCP orchestration is not enabled")
        return False
    
    return mcp_orchestrator.deactivate_server(server_name)


def get_mcp_servers_by_category(category: str) -> List[Dict[str, Any]]:
    """
    Get MCP servers grouped by category.
    
    Args:
        category: Category name (e.g., "AI_FRAMEWORKS", "ML_LIBRARIES")
        
    Returns:
        List of server configurations in the category
    """
    if not is_mcp_enabled():
        return []
    
    try:
        category_enum = MCPServerCategory(f"_{category.lower()}")
        servers = mcp_orchestrator.get_servers_by_category(category_enum)
        return [server.to_dict() for server in servers]
    except ValueError:
        logger.warning(f"Invalid MCP category: {category}")
        return []


def get_team_recommendations(role: str) -> Dict[str, Any]:
    """
    Get MCP tool recommendations for a team role.
    
    Args:
        role: Team role (e.g., "Lead Developer", "ML Engineer")
        
    Returns:
        Dictionary with tools and best practices
    """
    if not is_mcp_enabled():
        return {"tools": [], "best_practices": []}
    
    return {
        "tools": mcp_orchestrator.get_team_tools(role),
        "best_practices": mcp_orchestrator.get_best_practices(role)
    }


def get_mcp_status() -> Dict[str, Any]:
    """
    Get comprehensive MCP orchestration status.
    
    Returns:
        Status information dictionary
    """
    if not is_mcp_enabled():
        return {
            "enabled": False,
            "message": "MCP orchestration is not enabled"
        }
    
    status = mcp_orchestrator.get_orchestration_status()
    status["enabled"] = True
    return status


def validate_mcp_configuration() -> Dict[str, Any]:
    """
    Validate the current MCP configuration.
    
    Returns:
        Validation results
    """
    if not is_mcp_enabled():
        return {
            "valid": False,
            "issues": ["MCP orchestration is not enabled"],
            "warnings": []
        }
    
    return mcp_orchestrator.validate_configuration()


def export_mcp_configuration(output_file: Path) -> bool:
    """
    Export MCP configuration to a file.
    
    Args:
        output_file: Path to output file
        
    Returns:
        True if export successful
    """
    if not is_mcp_enabled():
        logger.warning("MCP orchestration is not enabled")
        return False
    
    try:
        mcp_orchestrator.export_config(output_file)
        return True
    except Exception as e:
        logger.error(f"Failed to export MCP configuration: {e}")
        return False


def get_mcp_server_info(server_name: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a specific MCP server.
    
    Args:
        server_name: Name of the server
        
    Returns:
        Server configuration dictionary or None
    """
    if not is_mcp_enabled():
        return None
    
    server = mcp_orchestrator.get_server_config(server_name)
    if server:
        info = server.to_dict()
        info["active"] = mcp_orchestrator.is_server_active(server_name)
        return info
    return None


def suggest_mcp_servers_for_task(task_description: str) -> List[str]:
    """
    Suggest MCP servers based on task description.
    
    Args:
        task_description: Description of the task
        
    Returns:
        List of suggested server names
    """
    if not is_mcp_enabled():
        return []
    
    suggestions = []
    task_lower = task_description.lower()
    
    # Keyword-based suggestions
    keywords = {
        "file": ["filesystem"],
        "git": ["git"],
        "commit": ["git"],
        "database": ["postgres", "sqlite"],
        "sql": ["postgres", "sqlite"],
        "ml": ["scikit-learn", "pandas", "numpy"],
        "machine learning": ["scikit-learn", "huggingface-transformers"],
        "deep learning": ["tensorflow", "pytorch"],
        "api": ["fastapi"],
        "web": ["fastapi", "streamlit"],
        "browser": ["browser"],
        "fetch": ["fetch"],
        "memory": ["memory"],
        "knowledge": ["memory"]
    }
    
    for keyword, servers in keywords.items():
        if keyword in task_lower:
            suggestions.extend(servers)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_suggestions = []
    for server in suggestions:
        if server not in seen and server in mcp_orchestrator.config.servers:
            seen.add(server)
            unique_suggestions.append(server)
    
    return unique_suggestions


def get_mcp_performance_metrics() -> Dict[str, Any]:
    """
    Get MCP performance metrics.
    
    Returns:
        Performance metrics dictionary
    """
    if not is_mcp_enabled():
        return {}
    
    return mcp_orchestrator.config.performance_metrics


def reload_mcp_configuration() -> bool:
    """
    Reload MCP configuration from files.
    
    Returns:
        True if reload successful
    """
    if not config_manager.mcp.enabled:
        logger.warning("MCP orchestration is not enabled")
        return False
    
    try:
        from agent_mcp.core.config import setup_mcp_orchestrator
        global mcp_orchestrator
        mcp_orchestrator = setup_mcp_orchestrator()
        logger.info("MCP configuration reloaded successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to reload MCP configuration: {e}")
        return False