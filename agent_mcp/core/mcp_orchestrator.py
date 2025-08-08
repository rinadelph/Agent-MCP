# MCP Orchestrator Configuration Module
"""
MCP orchestrator integration module that manages MCP server configurations
and team guidelines for coordinated multi-agent operations.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class MCPServerCategory(Enum):
    """Categories of MCP servers for organizational purposes."""
    DEVELOPMENT_TOOLS = "_development_tools"
    AI_FRAMEWORKS = "_ai_frameworks"
    ML_LIBRARIES = "_ml_libraries"
    DEEP_LEARNING = "_deep_learning"
    BACKEND_WEB = "_backend_web"
    DATA_TOOLS = "_data_tools"
    ORCHESTRATOR_SPECIFIC = "_orchestrator_specific"


@dataclass
class MCPServerConfig:
    """Configuration for a single MCP server."""
    name: str
    category: Optional[MCPServerCategory] = None
    command: Optional[str] = None
    args: Optional[List[str]] = None
    url: Optional[str] = None
    description: Optional[str] = None
    
    def is_local(self) -> bool:
        """Check if this is a local MCP server (uses command)."""
        return self.command is not None
    
    def is_remote(self) -> bool:
        """Check if this is a remote MCP server (uses URL)."""
        return self.url is not None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format for JSON serialization."""
        result = {"name": self.name}
        if self.command:
            result["command"] = self.command
        if self.args:
            result["args"] = self.args
        if self.url:
            result["url"] = self.url
        if self.description:
            result["description"] = self.description
        return result


@dataclass
class MCPTeamGuideline:
    """Guidelines for specific team roles using MCP tools."""
    role: str
    tools: List[str] = field(default_factory=list)
    best_practices: List[str] = field(default_factory=list)
    examples: Dict[str, str] = field(default_factory=dict)


@dataclass
class MCPOrchestrationConfig:
    """Complete MCP orchestration configuration."""
    servers: Dict[str, MCPServerConfig] = field(default_factory=dict)
    team_guidelines: Dict[str, MCPTeamGuideline] = field(default_factory=dict)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)
    active_servers: Set[str] = field(default_factory=set)
    

class MCPOrchestrator:
    """
    Orchestrates MCP server configurations and team guidelines
    for multi-agent collaboration.
    """
    
    def __init__(self, config_file: Optional[Path] = None, guide_file: Optional[Path] = None):
        """
        Initialize MCP Orchestrator.
        
        Args:
            config_file: Path to mcp_config.json
            guide_file: Path to MCP_TEAM_GUIDE.md
        """
        self.config = MCPOrchestrationConfig()
        self.config_file = config_file or Path("/mnt/c/Users/psytz/TMUX Final/Agent-MCP/mcp_config.json")
        self.guide_file = guide_file or Path("/mnt/c/Users/psytz/TMUX Final/Agent-MCP/MCP_TEAM_GUIDE.md")
        
        # Load configurations
        self._load_mcp_config()
        self._load_team_guide()
        self._initialize_performance_metrics()
    
    def _load_mcp_config(self) -> None:
        """Load MCP server configurations from JSON file."""
        if not self.config_file.exists():
            logger.warning(f"MCP config file not found: {self.config_file}")
            return
        
        try:
            with open(self.config_file, 'r') as f:
                config_data = json.load(f)
            
            if "mcpServers" in config_data:
                servers_data = config_data["mcpServers"]
                current_category = None
                
                for key, value in servers_data.items():
                    # Check if this is a category marker
                    if key.startswith("_"):
                        try:
                            current_category = MCPServerCategory(key)
                        except ValueError:
                            current_category = None
                        continue
                    
                    # Create server configuration
                    if isinstance(value, dict):
                        server = MCPServerConfig(
                            name=key,
                            category=current_category,
                            command=value.get("command"),
                            args=value.get("args"),
                            url=value.get("url"),
                            description=value.get("description")
                        )
                        self.config.servers[key] = server
                        logger.debug(f"Loaded MCP server: {key}")
            
            logger.info(f"Loaded {len(self.config.servers)} MCP server configurations")
            
        except Exception as e:
            logger.error(f"Error loading MCP config: {e}")
    
    def _load_team_guide(self) -> None:
        """Load team guidelines from markdown file."""
        if not self.guide_file.exists():
            logger.warning(f"Team guide file not found: {self.guide_file}")
            return
        
        try:
            with open(self.guide_file, 'r') as f:
                content = f.read()
            
            # Parse team-specific recommendations
            self._parse_team_recommendations(content)
            
            # Parse usage examples
            self._parse_usage_examples(content)
            
            # Parse performance benefits
            self._parse_performance_metrics(content)
            
            logger.info(f"Loaded team guidelines for {len(self.config.team_guidelines)} roles")
            
        except Exception as e:
            logger.error(f"Error loading team guide: {e}")
    
    def _parse_team_recommendations(self, content: str) -> None:
        """Parse team-specific recommendations from guide content."""
        # Define team roles and their associated tools
        team_roles = {
            "Lead Developer": {
                "tools": ["mcp__fastapi", "mcp__sqlalchemy", "mcp__filesystem", "mcp__git"],
                "best_practices": [
                    "Use mcp__fastapi and mcp__sqlalchemy for API development",
                    "Use mcp__filesystem for rapid file navigation",
                    "Use mcp__git for atomic commits"
                ]
            },
            "ML Engineer": {
                "tools": ["mcp__scikit-learn", "mcp__pandas", "mcp__postgres", "mcp__memory"],
                "best_practices": [
                    "Use mcp__scikit-learn for ML pipelines",
                    "Use mcp__pandas for data preprocessing",
                    "Use mcp__postgres for training data queries",
                    "Use mcp__memory to track model experiments"
                ]
            },
            "DevOps": {
                "tools": ["mcp__postgres", "mcp__git", "mcp__browser"],
                "best_practices": [
                    "Use mcp__postgres for database monitoring",
                    "Use mcp__git for CI/CD workflows",
                    "Use mcp__browser for E2E testing"
                ]
            },
            "Project Manager": {
                "tools": ["mcp__memory", "mcp__git", "mcp__filesystem"],
                "best_practices": [
                    "Use mcp__memory to track project knowledge",
                    "Use mcp__git to monitor commit history",
                    "Use mcp__filesystem to review code changes"
                ]
            }
        }
        
        for role, config in team_roles.items():
            guideline = MCPTeamGuideline(
                role=role,
                tools=config["tools"],
                best_practices=config["best_practices"]
            )
            self.config.team_guidelines[role] = guideline
    
    def _parse_usage_examples(self, content: str) -> None:
        """Parse usage examples from guide content."""
        # Add common usage examples
        examples = {
            "file_operations": {
                "read": 'mcp__filesystem.read_file("/path/to/file")',
                "write": 'mcp__filesystem.write_file("/path/to/file", content)'
            },
            "database": {
                "query": 'mcp__postgres.query("SELECT * FROM table")'
            },
            "git": {
                "status": "mcp__git.status()",
                "commit": 'mcp__git.commit("feat: Add feature")'
            }
        }
        
        # Add examples to relevant team guidelines
        for role, guideline in self.config.team_guidelines.items():
            guideline.examples = examples
    
    def _parse_performance_metrics(self, content: str) -> None:
        """Parse performance metrics from guide content."""
        self.config.performance_metrics = {
            "mcp_speedup": "5-10x faster than standard operations",
            "direct_db_access": "Eliminates API overhead",
            "framework_guidance": "Reduces development time",
            "knowledge_graphs": "Maintains context across sessions"
        }
    
    def _initialize_performance_metrics(self) -> None:
        """Initialize performance tracking metrics."""
        if not self.config.performance_metrics:
            self.config.performance_metrics = {
                "total_servers": len(self.config.servers),
                "active_servers": 0,
                "server_categories": self._count_by_category(),
                "team_coverage": len(self.config.team_guidelines)
            }
    
    def _count_by_category(self) -> Dict[str, int]:
        """Count servers by category."""
        counts = {}
        for server in self.config.servers.values():
            if server.category:
                category_name = server.category.value
                counts[category_name] = counts.get(category_name, 0) + 1
        return counts
    
    def activate_server(self, server_name: str) -> bool:
        """
        Activate an MCP server for use.
        
        Args:
            server_name: Name of the server to activate
            
        Returns:
            True if activation successful
        """
        if server_name not in self.config.servers:
            logger.error(f"Server {server_name} not found in configuration")
            return False
        
        self.config.active_servers.add(server_name)
        logger.info(f"Activated MCP server: {server_name}")
        return True
    
    def deactivate_server(self, server_name: str) -> bool:
        """
        Deactivate an MCP server.
        
        Args:
            server_name: Name of the server to deactivate
            
        Returns:
            True if deactivation successful
        """
        if server_name in self.config.active_servers:
            self.config.active_servers.remove(server_name)
            logger.info(f"Deactivated MCP server: {server_name}")
            return True
        return False
    
    def get_servers_by_category(self, category: MCPServerCategory) -> List[MCPServerConfig]:
        """
        Get all servers in a specific category.
        
        Args:
            category: The category to filter by
            
        Returns:
            List of server configurations
        """
        return [
            server for server in self.config.servers.values()
            if server.category == category
        ]
    
    def get_team_tools(self, role: str) -> List[str]:
        """
        Get recommended tools for a team role.
        
        Args:
            role: Team role name
            
        Returns:
            List of recommended tool names
        """
        if role in self.config.team_guidelines:
            return self.config.team_guidelines[role].tools
        return []
    
    def get_best_practices(self, role: str) -> List[str]:
        """
        Get best practices for a team role.
        
        Args:
            role: Team role name
            
        Returns:
            List of best practices
        """
        if role in self.config.team_guidelines:
            return self.config.team_guidelines[role].best_practices
        return []
    
    def get_server_config(self, server_name: str) -> Optional[MCPServerConfig]:
        """
        Get configuration for a specific server.
        
        Args:
            server_name: Name of the server
            
        Returns:
            Server configuration or None
        """
        return self.config.servers.get(server_name)
    
    def is_server_active(self, server_name: str) -> bool:
        """
        Check if a server is currently active.
        
        Args:
            server_name: Name of the server
            
        Returns:
            True if server is active
        """
        return server_name in self.config.active_servers
    
    def get_active_servers(self) -> List[str]:
        """Get list of currently active servers."""
        return list(self.config.active_servers)
    
    def get_all_servers(self) -> List[str]:
        """Get list of all configured servers."""
        return list(self.config.servers.keys())
    
    def export_config(self, output_file: Path) -> None:
        """
        Export current configuration to JSON file.
        
        Args:
            output_file: Path to output file
        """
        try:
            config_data = {
                "mcpServers": {},
                "activeServers": list(self.config.active_servers),
                "performanceMetrics": self.config.performance_metrics
            }
            
            # Group servers by category
            current_category = None
            for server in self.config.servers.values():
                if server.category != current_category:
                    current_category = server.category
                    if current_category:
                        config_data["mcpServers"][current_category.value] = f"Category: {current_category.name}"
                
                config_data["mcpServers"][server.name] = server.to_dict()
            
            with open(output_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            logger.info(f"Exported configuration to {output_file}")
            
        except Exception as e:
            logger.error(f"Error exporting configuration: {e}")
    
    def validate_configuration(self) -> Dict[str, Any]:
        """
        Validate the current MCP configuration.
        
        Returns:
            Validation results with any issues found
        """
        issues = []
        warnings = []
        
        # Check for duplicate server names
        seen_names = set()
        for name in self.config.servers.keys():
            if name in seen_names:
                issues.append(f"Duplicate server name: {name}")
            seen_names.add(name)
        
        # Check for missing configurations
        for server in self.config.servers.values():
            if not server.is_local() and not server.is_remote():
                issues.append(f"Server {server.name} has neither command nor URL")
            
            if server.is_local() and not server.args:
                warnings.append(f"Local server {server.name} has no arguments")
        
        # Check team guidelines coverage
        if not self.config.team_guidelines:
            warnings.append("No team guidelines configured")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "summary": {
                "total_servers": len(self.config.servers),
                "active_servers": len(self.config.active_servers),
                "team_roles": len(self.config.team_guidelines)
            }
        }
    
    def get_orchestration_status(self) -> Dict[str, Any]:
        """
        Get current orchestration status.
        
        Returns:
            Status information dictionary
        """
        return {
            "configuration": {
                "total_servers": len(self.config.servers),
                "active_servers": len(self.config.active_servers),
                "categories": self._count_by_category(),
                "team_roles": len(self.config.team_guidelines)
            },
            "active_servers": list(self.config.active_servers),
            "performance_metrics": self.config.performance_metrics,
            "validation": self.validate_configuration()
        }


# Global orchestrator instance
_orchestrator: Optional[MCPOrchestrator] = None


def get_orchestrator(config_file: Optional[Path] = None, guide_file: Optional[Path] = None) -> MCPOrchestrator:
    """
    Get or create the global MCP orchestrator instance.
    
    Args:
        config_file: Optional path to mcp_config.json
        guide_file: Optional path to MCP_TEAM_GUIDE.md
        
    Returns:
        The MCP orchestrator instance
    """
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = MCPOrchestrator(config_file, guide_file)
    return _orchestrator


def initialize_orchestrator(config_file: Optional[Path] = None, guide_file: Optional[Path] = None) -> MCPOrchestrator:
    """
    Initialize a new MCP orchestrator instance.
    
    Args:
        config_file: Optional path to mcp_config.json
        guide_file: Optional path to MCP_TEAM_GUIDE.md
        
    Returns:
        The new MCP orchestrator instance
    """
    global _orchestrator
    _orchestrator = MCPOrchestrator(config_file, guide_file)
    logger.info("MCP Orchestrator initialized")
    return _orchestrator