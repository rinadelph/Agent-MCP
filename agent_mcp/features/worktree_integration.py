# Agent-MCP/agent_mcp/features/worktree_integration.py
"""
Worktree integration for Agent-MCP.

This module provides the integration layer between the core agent system
and Git worktrees for isolated parallel development.
"""

import os
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from ..utils.worktree_utils import (
    is_git_repository,
    validate_worktree_requirements,
    create_git_worktree,
    cleanup_git_worktree,
    detect_project_setup_commands,
    run_setup_commands,
    generate_worktree_path,
    generate_branch_name
)

logger = logging.getLogger(__name__)


@dataclass
class WorktreeConfig:
    """Configuration for agent worktree setup."""
    enabled: bool = False
    branch_name: Optional[str] = None
    base_branch: str = "main"
    auto_setup: bool = True
    setup_commands: Optional[List[str]] = None
    cleanup_strategy: str = "on_terminate"  # "manual", "on_terminate", "smart"


class WorktreeManager:
    """
    Manager for agent worktree operations.
    
    This class handles the creation, tracking, and cleanup of Git worktrees
    for agent isolation.
    """
    
    def __init__(self):
        self.enabled = False
        self.agent_worktrees: Dict[str, Dict[str, Any]] = {}
    
    def enable(self) -> bool:
        """
        Enable worktree support if requirements are met.
        
        Returns:
            True if worktree support is enabled, False otherwise
        """
        if not is_git_repository():
            logger.warning("Worktree support requires a Git repository")
            return False
        
        validation = validate_worktree_requirements()
        if not validation["valid"]:
            logger.error(f"Worktree requirements not met: {validation['issues']}")
            return False
        
        self.enabled = True
        logger.info("✅ Worktree support enabled")
        return True
    
    def is_enabled(self) -> bool:
        """Check if worktree support is enabled."""
        return self.enabled
    
    def create_agent_worktree(
        self,
        agent_id: str,
        admin_token_suffix: str,
        config: WorktreeConfig
    ) -> Dict[str, Any]:
        """
        Create a worktree for an agent.
        
        Args:
            agent_id: Agent identifier
            admin_token_suffix: Last 4 characters of admin token
            config: Worktree configuration
            
        Returns:
            Result dictionary with worktree details
        """
        if not self.enabled:
            return {
                "success": False,
                "error": "Worktree support not enabled"
            }
        
        try:
            # Generate paths and names
            worktree_path = generate_worktree_path(agent_id, admin_token_suffix)
            branch_name = generate_branch_name(agent_id, config.branch_name)
            
            logger.info(f"Creating worktree for agent {agent_id}: {worktree_path}")
            
            # Create the worktree
            create_result = create_git_worktree(
                path=worktree_path,
                branch=branch_name,
                base_branch=config.base_branch
            )
            
            if not create_result["success"]:
                return create_result
            
            # Set up the environment if requested
            setup_result = None
            if config.auto_setup:
                setup_commands = config.setup_commands or detect_project_setup_commands(worktree_path)
                
                if setup_commands:
                    logger.info(f"Running setup commands for {agent_id}: {setup_commands}")
                    setup_result = run_setup_commands(worktree_path, setup_commands)
                    
                    if not setup_result["success"]:
                        logger.warning(f"Setup failed for {agent_id}, but continuing: {setup_result}")
            
            # Track the worktree
            worktree_info = {
                "path": worktree_path,
                "branch": branch_name,
                "base_branch": config.base_branch,
                "cleanup_strategy": config.cleanup_strategy,
                "setup_commands": config.setup_commands or detect_project_setup_commands(worktree_path),
                "created_at": create_result.get("created_at"),
                "setup_result": setup_result
            }
            
            self.agent_worktrees[agent_id] = worktree_info
            
            logger.info(f"✅ Worktree created for agent {agent_id}")
            
            return {
                "success": True,
                "worktree_path": worktree_path,
                "branch": branch_name,
                "worktree_info": worktree_info,
                "create_result": create_result,
                "setup_result": setup_result
            }
            
        except Exception as e:
            logger.error(f"Failed to create worktree for agent {agent_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def cleanup_agent_worktree(
        self,
        agent_id: str,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Clean up an agent's worktree.
        
        Args:
            agent_id: Agent identifier
            force: Force cleanup even with uncommitted changes
            
        Returns:
            Cleanup result dictionary
        """
        if agent_id not in self.agent_worktrees:
            return {
                "success": True,  # Nothing to clean up
                "message": f"No worktree found for agent {agent_id}"
            }
        
        worktree_info = self.agent_worktrees[agent_id]
        worktree_path = worktree_info["path"]
        
        logger.info(f"Cleaning up worktree for agent {agent_id}: {worktree_path}")
        
        try:
            cleanup_result = cleanup_git_worktree(worktree_path, force=force)
            
            if cleanup_result["success"]:
                # Remove from tracking
                del self.agent_worktrees[agent_id]
                logger.info(f"✅ Worktree cleaned up for agent {agent_id}")
            else:
                logger.error(f"Failed to cleanup worktree for agent {agent_id}: {cleanup_result['error']}")
            
            return cleanup_result
            
        except Exception as e:
            logger.error(f"Exception cleaning up worktree for agent {agent_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_agent_worktree_info(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        Get worktree information for an agent.
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            Worktree information or None if not found
        """
        return self.agent_worktrees.get(agent_id)
    
    def list_agent_worktrees(self) -> Dict[str, Dict[str, Any]]:
        """
        List all tracked agent worktrees.
        
        Returns:
            Dictionary of agent_id -> worktree_info
        """
        return self.agent_worktrees.copy()
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get overall worktree manager status.
        
        Returns:
            Status dictionary with worktree information
        """
        return {
            "enabled": self.enabled,
            "tracked_worktrees": len(self.agent_worktrees),
            "agent_worktrees": {
                agent_id: {
                    "path": info["path"],
                    "branch": info["branch"],
                    "exists": os.path.exists(info["path"])
                }
                for agent_id, info in self.agent_worktrees.items()
            }
        }


# Global worktree manager instance
worktree_manager = WorktreeManager()


def enable_worktree_support() -> bool:
    """
    Enable worktree support globally.
    
    Returns:
        True if enabled successfully, False otherwise
    """
    return worktree_manager.enable()


def is_worktree_enabled() -> bool:
    """Check if worktree support is enabled globally."""
    return worktree_manager.is_enabled()


def create_agent_worktree(
    agent_id: str,
    admin_token_suffix: str,
    config: WorktreeConfig
) -> Dict[str, Any]:
    """
    Create a worktree for an agent using the global manager.
    
    Args:
        agent_id: Agent identifier
        admin_token_suffix: Last 4 characters of admin token
        config: Worktree configuration
        
    Returns:
        Result dictionary with worktree details
    """
    return worktree_manager.create_agent_worktree(agent_id, admin_token_suffix, config)


def cleanup_agent_worktree(agent_id: str, force: bool = False) -> Dict[str, Any]:
    """
    Clean up an agent's worktree using the global manager.
    
    Args:
        agent_id: Agent identifier
        force: Force cleanup even with uncommitted changes
        
    Returns:
        Cleanup result dictionary
    """
    return worktree_manager.cleanup_agent_worktree(agent_id, force)


def get_worktree_status() -> Dict[str, Any]:
    """Get overall worktree status."""
    return worktree_manager.get_status()


def get_agent_worktree_path(agent_id: str) -> Optional[str]:
    """
    Get the worktree path for an agent.
    
    Args:
        agent_id: Agent identifier
        
    Returns:
        Worktree path or None if not found
    """
    info = worktree_manager.get_agent_worktree_info(agent_id)
    return info["path"] if info else None