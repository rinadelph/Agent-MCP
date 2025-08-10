# Agent-MCP/agent_mcp/utils/worktree_utils.py
"""
Git worktree utilities for parallel agent development.

This module provides core functionality for creating, managing, and cleaning up
Git worktrees for isolated agent environments.
"""

import os
import subprocess
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


def is_git_repository(path: str = ".") -> bool:
    """
    Check if the given path is within a Git repository.
    
    Args:
        path: Directory path to check (defaults to current directory)
        
    Returns:
        True if path is in a Git repository, False otherwise
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        return False


def get_current_branch(path: str = ".") -> Optional[str]:
    """
    Get the current branch name.
    
    Args:
        path: Repository path
        
    Returns:
        Current branch name or None if not in a repository
    """
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=path,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
        return None
    except Exception as e:
        logger.error(f"Error getting current branch: {e}")
        return None


def branch_exists(branch_name: str, path: str = ".") -> bool:
    """
    Check if a branch exists in the repository.
    
    Args:
        branch_name: Name of the branch to check
        path: Repository path
        
    Returns:
        True if branch exists, False otherwise
    """
    try:
        result = subprocess.run(
            ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"],
            cwd=path,
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def create_git_worktree(
    path: str, 
    branch: str, 
    base_branch: str = "main",
    repo_path: str = "."
) -> Dict[str, Any]:
    """
    Create a new Git worktree.
    
    Args:
        path: Path where the worktree should be created
        branch: Branch name for the worktree
        base_branch: Base branch to create new branch from
        repo_path: Path to the main repository
        
    Returns:
        Dictionary with success status and details
    """
    try:
        # Ensure the path is absolute and doesn't exist
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            return {
                "success": False,
                "error": f"Path already exists: {abs_path}",
                "path": abs_path
            }
        
        # Create parent directory if it doesn't exist
        parent_dir = os.path.dirname(abs_path)
        os.makedirs(parent_dir, exist_ok=True)
        
        # Prepare Git command
        if branch_exists(branch, repo_path):
            # Use existing branch
            cmd = ["git", "worktree", "add", abs_path, branch]
            action = f"checkout existing branch '{branch}'"
        else:
            # Create new branch from base
            cmd = ["git", "worktree", "add", abs_path, "-b", branch, base_branch]
            action = f"create new branch '{branch}' from '{base_branch}'"
        
        # Execute Git worktree command
        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=60  # Worktree creation can be slow for large repos
        )
        
        if result.returncode == 0:
            logger.info(f"Created worktree at {abs_path} ({action})")
            return {
                "success": True,
                "path": abs_path,
                "branch": branch,
                "base_branch": base_branch,
                "action": action,
                "message": f"Worktree created at {abs_path}"
            }
        else:
            logger.error(f"Failed to create worktree: {result.stderr}")
            return {
                "success": False,
                "error": result.stderr.strip(),
                "command": " ".join(cmd),
                "path": abs_path
            }
            
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Timeout creating worktree (repository might be very large)",
            "path": path
        }
    except Exception as e:
        logger.error(f"Exception creating worktree: {e}")
        return {
            "success": False,
            "error": str(e),
            "path": path
        }


def list_git_worktrees(repo_path: str = ".") -> List[Dict[str, Any]]:
    """
    List all Git worktrees in the repository.
    
    Args:
        repo_path: Path to the repository
        
    Returns:
        List of worktree information dictionaries
    """
    try:
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            logger.error(f"Failed to list worktrees: {result.stderr}")
            return []
        
        worktrees = []
        current_worktree = {}
        
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
                
            if line.startswith('worktree '):
                # Start of new worktree entry
                if current_worktree:
                    worktrees.append(current_worktree)
                current_worktree = {"path": line[9:]}
            elif line.startswith('HEAD '):
                current_worktree["commit"] = line[5:]
            elif line.startswith('branch '):
                current_worktree["branch"] = line[7:]
            elif line == 'bare':
                current_worktree["bare"] = True
            elif line == 'detached':
                current_worktree["detached"] = True
            elif line == 'locked':
                current_worktree["locked"] = True
            elif line == 'prunable':
                current_worktree["prunable"] = True
        
        # Add the last worktree
        if current_worktree:
            worktrees.append(current_worktree)
        
        # Add existence check for each worktree
        for wt in worktrees:
            wt["exists"] = os.path.exists(wt["path"])
        
        logger.debug(f"Found {len(worktrees)} worktrees")
        return worktrees
        
    except subprocess.TimeoutExpired:
        logger.error("Timeout listing worktrees")
        return []
    except Exception as e:
        logger.error(f"Error listing worktrees: {e}")
        return []


def has_uncommitted_changes(worktree_path: str) -> bool:
    """
    Check if a worktree has uncommitted changes.
    
    Args:
        worktree_path: Path to the worktree
        
    Returns:
        True if there are uncommitted changes, False otherwise
    """
    try:
        # Check if directory exists
        if not os.path.exists(worktree_path):
            return False
        
        # Check for uncommitted changes (staged + unstaged)
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # If there's any output from --porcelain, there are changes
        return bool(result.stdout.strip()) if result.returncode == 0 else False
        
    except Exception as e:
        logger.error(f"Error checking for uncommitted changes in {worktree_path}: {e}")
        return True  # Assume there are changes if we can't check


def cleanup_git_worktree(
    path: str, 
    force: bool = False,
    repo_path: str = "."
) -> Dict[str, Any]:
    """
    Remove a Git worktree.
    
    Args:
        path: Path to the worktree to remove
        force: Force removal even if there are uncommitted changes
        repo_path: Path to the main repository
        
    Returns:
        Dictionary with success status and details
    """
    try:
        abs_path = os.path.abspath(path)
        
        # Check if the worktree exists
        if not os.path.exists(abs_path):
            return {
                "success": True,  # Already doesn't exist
                "message": f"Worktree at {abs_path} doesn't exist",
                "path": abs_path
            }
        
        # Check for uncommitted changes unless forced
        if not force and has_uncommitted_changes(abs_path):
            return {
                "success": False,
                "error": "Worktree has uncommitted changes. Use force=True to override.",
                "uncommitted_changes": True,
                "path": abs_path
            }
        
        # Prepare remove command
        cmd = ["git", "worktree", "remove", abs_path]
        if force:
            cmd.append("--force")
        
        # Execute removal
        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            logger.info(f"Removed worktree at {abs_path}")
            return {
                "success": True,
                "message": f"Worktree at {abs_path} removed successfully",
                "path": abs_path
            }
        else:
            logger.error(f"Failed to remove worktree: {result.stderr}")
            return {
                "success": False,
                "error": result.stderr.strip(),
                "command": " ".join(cmd),
                "path": abs_path
            }
            
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Timeout removing worktree",
            "path": path
        }
    except Exception as e:
        logger.error(f"Exception removing worktree: {e}")
        return {
            "success": False,
            "error": str(e),
            "path": path
        }


def detect_project_setup_commands(worktree_path: str) -> List[str]:
    """
    Auto-detect common setup commands for the project type.
    
    Args:
        worktree_path: Path to the worktree
        
    Returns:
        List of setup commands to run
    """
    setup_commands = []
    
    try:
        # Node.js projects
        if os.path.exists(os.path.join(worktree_path, "package.json")):
            if os.path.exists(os.path.join(worktree_path, "yarn.lock")):
                setup_commands.append("yarn install")
            elif os.path.exists(os.path.join(worktree_path, "pnpm-lock.yaml")):
                setup_commands.append("pnpm install")
            else:
                setup_commands.append("npm install")
        
        # Python projects
        if os.path.exists(os.path.join(worktree_path, "requirements.txt")):
            setup_commands.append("pip install -r requirements.txt")
        elif os.path.exists(os.path.join(worktree_path, "pyproject.toml")):
            setup_commands.append("pip install -e .")
        elif os.path.exists(os.path.join(worktree_path, "setup.py")):
            setup_commands.append("pip install -e .")
        
        # Rust projects
        if os.path.exists(os.path.join(worktree_path, "Cargo.toml")):
            setup_commands.append("cargo build")
        
        # Go projects
        if os.path.exists(os.path.join(worktree_path, "go.mod")):
            setup_commands.append("go mod download")
        
        # Maven projects
        if os.path.exists(os.path.join(worktree_path, "pom.xml")):
            setup_commands.append("mvn dependency:resolve")
        
        # Gradle projects
        if os.path.exists(os.path.join(worktree_path, "build.gradle")) or \
           os.path.exists(os.path.join(worktree_path, "build.gradle.kts")):
            setup_commands.append("./gradlew build")
        
        logger.debug(f"Detected setup commands for {worktree_path}: {setup_commands}")
        return setup_commands
        
    except Exception as e:
        logger.error(f"Error detecting setup commands: {e}")
        return []


def run_setup_commands(
    worktree_path: str, 
    commands: List[str],
    timeout: int = 300
) -> Dict[str, Any]:
    """
    Run setup commands in the worktree directory.
    
    Args:
        worktree_path: Path to the worktree
        commands: List of setup commands to run
        timeout: Timeout in seconds for each command
        
    Returns:
        Dictionary with results of running setup commands
    """
    results = []
    original_cwd = os.getcwd()
    
    try:
        if not os.path.exists(worktree_path):
            return {
                "success": False,
                "error": f"Worktree path doesn't exist: {worktree_path}",
                "results": []
            }
        
        os.chdir(worktree_path)
        logger.info(f"Running {len(commands)} setup commands in {worktree_path}")
        
        for cmd in commands:
            logger.debug(f"Running: {cmd}")
            try:
                result = subprocess.run(
                    cmd.split(),
                    cwd=worktree_path,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                
                cmd_result = {
                    "command": cmd,
                    "success": result.returncode == 0,
                    "returncode": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr
                }
                
                if result.returncode == 0:
                    logger.debug(f"✅ {cmd} completed successfully")
                else:
                    logger.warning(f"❌ {cmd} failed with code {result.returncode}")
                
                results.append(cmd_result)
                
            except subprocess.TimeoutExpired:
                cmd_result = {
                    "command": cmd,
                    "success": False,
                    "error": f"Command timed out after {timeout} seconds"
                }
                results.append(cmd_result)
                logger.error(f"⏰ {cmd} timed out")
                
            except Exception as e:
                cmd_result = {
                    "command": cmd,
                    "success": False,
                    "error": str(e)
                }
                results.append(cmd_result)
                logger.error(f"💥 {cmd} failed with exception: {e}")
        
        success_count = sum(1 for r in results if r["success"])
        overall_success = success_count == len(commands)
        
        logger.info(f"Setup complete: {success_count}/{len(commands)} commands succeeded")
        
        return {
            "success": overall_success,
            "results": results,
            "success_count": success_count,
            "total_commands": len(commands),
            "worktree_path": worktree_path
        }
        
    except Exception as e:
        logger.error(f"Error running setup commands: {e}")
        return {
            "success": False,
            "error": str(e),
            "results": results
        }
    finally:
        os.chdir(original_cwd)


def generate_worktree_path(agent_id: str, admin_token_suffix: str, base_path: str = "../agents") -> str:
    """
    Generate a standardized worktree path for an agent.
    
    Args:
        agent_id: Agent identifier
        admin_token_suffix: Last 4 characters of admin token
        base_path: Base directory for agent worktrees
        
    Returns:
        Absolute path for the agent's worktree
    """
    worktree_dir = f"{agent_id}-{admin_token_suffix}"
    return os.path.abspath(os.path.join(base_path, worktree_dir))


def generate_branch_name(agent_id: str, custom_branch: Optional[str] = None) -> str:
    """
    Generate a standardized branch name for an agent.
    
    Args:
        agent_id: Agent identifier
        custom_branch: Custom branch name if specified
        
    Returns:
        Branch name for the agent
    """
    if custom_branch:
        return custom_branch
    return f"agent/{agent_id}"


# Validation helpers

def validate_worktree_requirements(repo_path: str = ".") -> Dict[str, Any]:
    """
    Validate that worktree operations can be performed.
    
    Args:
        repo_path: Path to the repository
        
    Returns:
        Validation results with any issues found
    """
    issues = []
    
    # Check if it's a Git repository
    if not is_git_repository(repo_path):
        issues.append("Not a Git repository")
    
    # Check if Git is available
    try:
        result = subprocess.run(["git", "--version"], capture_output=True, timeout=5)
        if result.returncode != 0:
            issues.append("Git command not available")
    except Exception:
        issues.append("Git command not available")
    
    # Check if we can create worktrees (Git 2.5+)
    try:
        result = subprocess.run(["git", "worktree", "--help"], capture_output=True, timeout=5)
        if result.returncode != 0:
            issues.append("Git worktree command not available (requires Git 2.5+)")
    except Exception:
        issues.append("Git worktree command not available")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues
    }