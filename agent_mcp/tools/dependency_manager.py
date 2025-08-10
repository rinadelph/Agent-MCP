# Tool Dependency Manager
"""
Tool dependency management system for Agent-MCP.
Handles tool dependencies, execution order, and compatibility checks.
"""

import asyncio
import time
from typing import Dict, List, Set, Optional, Any, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum
import json
import hashlib

from ..core.config import logger


class ToolStatus(Enum):
    """Tool execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ToolDependency:
    """Represents a tool dependency."""
    tool_name: str
    required_version: Optional[str] = None
    optional: bool = False
    timeout: Optional[float] = None


@dataclass
class ToolExecution:
    """Represents a tool execution."""
    tool_name: str
    arguments: Dict[str, Any]
    status: ToolStatus = ToolStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    execution_time: Optional[float] = None


class ToolDependencyManager:
    """Manages tool dependencies and execution order."""
    
    def __init__(self):
        self.tool_dependencies: Dict[str, List[ToolDependency]] = {}
        self.tool_versions: Dict[str, str] = {}
        self.execution_history: List[ToolExecution] = []
        self.running_executions: Dict[str, ToolExecution] = {}
        self.metrics: Dict[str, Dict[str, Any]] = {}
    
    def register_tool(self, tool_name: str, version: str = "1.0.0", 
                     dependencies: Optional[List[ToolDependency]] = None) -> None:
        """Register a tool with its dependencies."""
        self.tool_versions[tool_name] = version
        self.tool_dependencies[tool_name] = dependencies or []
        
        # Initialize metrics
        self.metrics[tool_name] = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "average_execution_time": 0.0,
            "last_execution": None,
            "dependencies": [dep.tool_name for dep in self.tool_dependencies[tool_name]]
        }
        
        logger.info(f"Registered tool: {tool_name} v{version}")
    
    def get_tool_dependencies(self, tool_name: str) -> List[ToolDependency]:
        """Get dependencies for a tool."""
        return self.tool_dependencies.get(tool_name, [])
    
    def check_dependencies(self, tool_name: str) -> Dict[str, Any]:
        """Check if all dependencies for a tool are satisfied."""
        dependencies = self.get_tool_dependencies(tool_name)
        results = {
            "satisfied": True,
            "missing": [],
            "version_mismatches": [],
            "optional_missing": []
        }
        
        for dep in dependencies:
            if dep.tool_name not in self.tool_versions:
                if dep.optional:
                    results["optional_missing"].append(dep.tool_name)
                else:
                    results["missing"].append(dep.tool_name)
                    results["satisfied"] = False
            elif dep.required_version:
                current_version = self.tool_versions[dep.tool_name]
                if not self._version_compatible(current_version, dep.required_version):
                    results["version_mismatches"].append({
                        "tool": dep.tool_name,
                        "required": dep.required_version,
                        "current": current_version
                    })
                    if not dep.optional:
                        results["satisfied"] = False
        
        return results
    
    def _version_compatible(self, current: str, required: str) -> bool:
        """Check if current version is compatible with required version."""
        try:
            current_parts = [int(x) for x in current.split('.')]
            required_parts = [int(x) for x in required.split('.')]
            
            # Simple version comparison (can be enhanced)
            for i in range(min(len(current_parts), len(required_parts))):
                if current_parts[i] < required_parts[i]:
                    return False
                elif current_parts[i] > required_parts[i]:
                    return True
            
            return len(current_parts) >= len(required_parts)
        except (ValueError, AttributeError):
            return current == required
    
    def get_execution_order(self, tool_names: List[str]) -> List[str]:
        """Get the optimal execution order for a list of tools."""
        # Topological sort for dependency resolution
        visited = set()
        temp_visited = set()
        order = []
        
        def visit(tool_name: str):
            if tool_name in temp_visited:
                raise ValueError(f"Circular dependency detected involving {tool_name}")
            if tool_name in visited:
                return
            
            temp_visited.add(tool_name)
            
            # Visit dependencies first
            dependencies = self.get_tool_dependencies(tool_name)
            for dep in dependencies:
                if not dep.optional:  # Only visit required dependencies
                    visit(dep.tool_name)
            
            temp_visited.remove(tool_name)
            visited.add(tool_name)
            order.append(tool_name)
        
        for tool_name in tool_names:
            if tool_name not in visited:
                visit(tool_name)
        
        return order
    
    async def execute_tool_with_dependencies(self, tool_name: str, arguments: Dict[str, Any],
                                           tool_implementation: Callable[[Dict[str, Any]], Awaitable[Any]],
                                           timeout: Optional[float] = None) -> ToolExecution:
        """Execute a tool with dependency checking and metrics tracking."""
        execution = ToolExecution(tool_name=tool_name, arguments=arguments)
        
        # Check dependencies
        dep_check = self.check_dependencies(tool_name)
        if not dep_check["satisfied"]:
            execution.status = ToolStatus.FAILED
            execution.error = f"Dependencies not satisfied: {dep_check}"
            return execution
        
        # Check for circular dependencies
        try:
            execution_order = self.get_execution_order([tool_name])
        except ValueError as e:
            execution.status = ToolStatus.FAILED
            execution.error = str(e)
            return execution
        
        # Execute tool
        execution.start_time = time.time()
        execution.status = ToolStatus.RUNNING
        self.running_executions[tool_name] = execution
        
        try:
            if timeout:
                result = await asyncio.wait_for(tool_implementation(arguments), timeout=timeout)
            else:
                result = await tool_implementation(arguments)
            
            execution.status = ToolStatus.COMPLETED
            execution.result = result
            
        except asyncio.TimeoutError:
            execution.status = ToolStatus.FAILED
            execution.error = f"Tool execution timed out after {timeout}s"
        except Exception as e:
            execution.status = ToolStatus.FAILED
            execution.error = str(e)
        finally:
            execution.end_time = time.time()
            execution.execution_time = execution.end_time - execution.start_time
            del self.running_executions[tool_name]
        
        # Update metrics
        self._update_metrics(execution)
        self.execution_history.append(execution)
        
        return execution
    
    def _update_metrics(self, execution: ToolExecution) -> None:
        """Update metrics for a tool execution."""
        tool_name = execution.tool_name
        if tool_name not in self.metrics:
            return
        
        metrics = self.metrics[tool_name]
        metrics["total_executions"] += 1
        metrics["last_execution"] = time.time()
        
        if execution.status == ToolStatus.COMPLETED:
            metrics["successful_executions"] += 1
        elif execution.status == ToolStatus.FAILED:
            metrics["failed_executions"] += 1
        
        # Update average execution time
        if execution.execution_time:
            current_avg = metrics["average_execution_time"]
            total_executions = metrics["total_executions"]
            new_avg = ((current_avg * (total_executions - 1)) + execution.execution_time) / total_executions
            metrics["average_execution_time"] = new_avg
    
    def get_tool_metrics(self, tool_name: str) -> Dict[str, Any]:
        """Get metrics for a specific tool."""
        return self.metrics.get(tool_name, {})
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all tools."""
        return self.metrics.copy()
    
    def get_execution_history(self, tool_name: Optional[str] = None, 
                            limit: Optional[int] = None) -> List[ToolExecution]:
        """Get execution history, optionally filtered by tool name."""
        history = self.execution_history
        
        if tool_name:
            history = [execution for execution in history if execution.tool_name == tool_name]
        
        if limit:
            history = history[-limit:]
        
        return history
    
    def get_running_executions(self) -> Dict[str, ToolExecution]:
        """Get currently running tool executions."""
        return self.running_executions.copy()
    
    def cancel_execution(self, tool_name: str) -> bool:
        """Cancel a running tool execution."""
        if tool_name in self.running_executions:
            execution = self.running_executions[tool_name]
            execution.status = ToolStatus.FAILED
            execution.error = "Execution cancelled"
            execution.end_time = time.time()
            execution.execution_time = execution.end_time - execution.start_time
            
            del self.running_executions[tool_name]
            self._update_metrics(execution)
            return True
        
        return False
    
    def get_dependency_graph(self) -> Dict[str, List[str]]:
        """Get the dependency graph for all tools."""
        graph = {}
        for tool_name in self.tool_versions:
            dependencies = self.get_tool_dependencies(tool_name)
            graph[tool_name] = [dep.tool_name for dep in dependencies if not dep.optional]
        
        return graph
    
    def detect_circular_dependencies(self) -> List[List[str]]:
        """Detect circular dependencies in the tool graph."""
        graph = self.get_dependency_graph()
        cycles = []
        visited = set()
        rec_stack = set()
        
        def dfs(node: str, path: List[str]):
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    dfs(neighbor, path.copy())
                elif neighbor in rec_stack:
                    # Found a cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
            
            rec_stack.remove(node)
        
        for node in graph:
            if node not in visited:
                dfs(node, [])
        
        return cycles
    
    def export_metrics(self, file_path: str) -> None:
        """Export metrics to a JSON file."""
        export_data = {
            "tool_versions": self.tool_versions,
            "tool_dependencies": {
                tool: [{"tool_name": dep.tool_name, "required_version": dep.required_version, 
                       "optional": dep.optional, "timeout": dep.timeout} 
                      for dep in deps]
                for tool, deps in self.tool_dependencies.items()
            },
            "metrics": self.metrics,
            "execution_history": [
                {
                    "tool_name": exec.tool_name,
                    "status": exec.status.value,
                    "execution_time": exec.execution_time,
                    "start_time": exec.start_time,
                    "end_time": exec.end_time,
                    "error": exec.error
                }
                for exec in self.execution_history
            ]
        }
        
        with open(file_path, 'w') as f:
            json.dump(export_data, f, indent=2, default=str)
        
        logger.info(f"Exported metrics to {file_path}")


# Global dependency manager instance
dependency_manager = ToolDependencyManager()
