# Agent-MCP/agent_mcp/utils/tmux_utils.py
import subprocess
import re
import shlex
from typing import List, Dict, Optional, Any
from pathlib import Path

from ..core.config import logger


def is_tmux_available() -> bool:
    """Check if tmux is installed and available."""
    try:
        result = subprocess.run(['tmux', '-V'], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        return False


def sanitize_session_name(name: str) -> str:
    """
    Sanitize session name to be safe for tmux.
    Tmux session names cannot contain: . : [ ] space $ and other special chars
    """
    # Replace invalid characters with underscores
    sanitized = re.sub(r'[.:\[\]\s$\'"`\\]', '_', name)
    # Remove any consecutive underscores
    sanitized = re.sub(r'_+', '_', sanitized)
    # Remove leading/trailing underscores
    sanitized = sanitized.strip('_')
    # Ensure it starts with alphanumeric
    if sanitized and not sanitized[0].isalnum():
        sanitized = 'agent_' + sanitized
    return sanitized or 'agent_session'


def create_tmux_session(session_name: str, 
                       working_dir: str, 
                       command: str = None,
                       env_vars: Dict[str, str] = None) -> bool:
    """
    Create a new tmux session with the given name and working directory.
    
    Args:
        session_name: Name for the tmux session (will be sanitized)
        working_dir: Working directory for the session
        command: Optional command to run in the session
        env_vars: Optional environment variables to set
    
    Returns:
        True if session was created successfully, False otherwise
    """
    if not is_tmux_available():
        logger.error("tmux is not available on this system")
        return False
    
    # Sanitize session name
    clean_session_name = sanitize_session_name(session_name)
    
    # Check if session already exists
    if session_exists(clean_session_name):
        logger.warning(f"tmux session '{clean_session_name}' already exists")
        return False
    
    # Ensure working directory exists
    try:
        Path(working_dir).mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create working directory {working_dir}: {e}")
        return False
    
    try:
        # Build tmux command
        tmux_cmd = ['tmux', 'new-session', '-d', '-s', clean_session_name, '-c', working_dir]
        
        # Add environment variables if provided
        env = None
        if env_vars:
            import os
            env = os.environ.copy()
            env.update(env_vars)
        
        # Add the command to run if provided
        if command:
            tmux_cmd.append(command)
        
        # Execute tmux command
        result = subprocess.run(tmux_cmd, 
                              capture_output=True, 
                              text=True, 
                              timeout=10,
                              env=env)
        
        if result.returncode == 0:
            logger.info(f"Created tmux session '{clean_session_name}' in {working_dir}")
            return True
        else:
            logger.error(f"Failed to create tmux session: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout creating tmux session '{clean_session_name}'")
        return False
    except Exception as e:
        logger.error(f"Error creating tmux session '{clean_session_name}': {e}")
        return False


def session_exists(session_name: str) -> bool:
    """Check if a tmux session with the given name exists."""
    if not is_tmux_available():
        return False
    
    clean_session_name = sanitize_session_name(session_name)
    
    try:
        result = subprocess.run(['tmux', 'has-session', '-t', clean_session_name], 
                              capture_output=True, 
                              timeout=5)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, subprocess.SubprocessError):
        return False


def list_tmux_sessions() -> List[Dict[str, Any]]:
    """
    List all tmux sessions with detailed information.
    
    Returns:
        List of dictionaries containing session information
    """
    if not is_tmux_available():
        return []
    
    try:
        # Use tmux list-sessions with a specific format
        result = subprocess.run(['tmux', 'list-sessions', '-F', 
                               '#{session_name}|#{session_created}|#{session_attached}|#{session_windows}'], 
                              capture_output=True, 
                              text=True, 
                              timeout=10)
        
        if result.returncode != 0:
            if "no server running" in result.stderr:
                return []  # No tmux server running, no sessions
            logger.warning(f"Failed to list tmux sessions: {result.stderr}")
            return []
        
        sessions = []
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split('|')
                if len(parts) >= 4:
                    sessions.append({
                        'name': parts[0],
                        'created': parts[1],
                        'attached': parts[2] == '1',
                        'windows': int(parts[3])
                    })
        
        return sessions
        
    except subprocess.TimeoutExpired:
        logger.error("Timeout listing tmux sessions")
        return []
    except Exception as e:
        logger.error(f"Error listing tmux sessions: {e}")
        return []


def kill_tmux_session(session_name: str) -> bool:
    """
    Kill a tmux session by name.
    
    Args:
        session_name: Name of the session to kill
    
    Returns:
        True if session was killed successfully, False otherwise
    """
    if not is_tmux_available():
        logger.error("tmux is not available on this system")
        return False
    
    clean_session_name = sanitize_session_name(session_name)
    
    if not session_exists(clean_session_name):
        logger.warning(f"tmux session '{clean_session_name}' does not exist")
        return True  # Consider it "successful" if it doesn't exist
    
    try:
        result = subprocess.run(['tmux', 'kill-session', '-t', clean_session_name], 
                              capture_output=True, 
                              text=True, 
                              timeout=10)
        
        if result.returncode == 0:
            logger.info(f"Killed tmux session '{clean_session_name}'")
            return True
        else:
            logger.error(f"Failed to kill tmux session '{clean_session_name}': {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout killing tmux session '{clean_session_name}'")
        return False
    except Exception as e:
        logger.error(f"Error killing tmux session '{clean_session_name}': {e}")
        return False


def get_session_status(session_name: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed status information for a specific tmux session.
    
    Args:
        session_name: Name of the session to check
    
    Returns:
        Dictionary with session status or None if session doesn't exist
    """
    if not is_tmux_available():
        return None
    
    clean_session_name = sanitize_session_name(session_name)
    
    if not session_exists(clean_session_name):
        return None
    
    try:
        # Get detailed session information
        result = subprocess.run(['tmux', 'display-message', '-t', clean_session_name, '-p',
                               '#{session_name}|#{session_created}|#{session_attached}|#{session_windows}|#{session_id}'], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        
        if result.returncode == 0:
            parts = result.stdout.strip().split('|')
            if len(parts) >= 5:
                return {
                    'name': parts[0],
                    'created': parts[1],
                    'attached': parts[2] == '1',
                    'windows': int(parts[3]),
                    'session_id': parts[4],
                    'exists': True
                }
        
        return None
        
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout getting status for tmux session '{clean_session_name}'")
        return None
    except Exception as e:
        logger.error(f"Error getting status for tmux session '{clean_session_name}': {e}")
        return None


def send_command_to_session(session_name: str, command: str) -> bool:
    """
    Send a command to a tmux session.
    
    Args:
        session_name: Name of the target session
        command: Command to send
    
    Returns:
        True if command was sent successfully, False otherwise
    """
    if not is_tmux_available():
        return False
    
    clean_session_name = sanitize_session_name(session_name)
    
    if not session_exists(clean_session_name):
        logger.warning(f"tmux session '{clean_session_name}' does not exist")
        return False
    
    try:
        # Send the command followed by Enter
        result = subprocess.run(['tmux', 'send-keys', '-t', clean_session_name, command, 'Enter'], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout sending command to tmux session '{clean_session_name}'")
        return False
    except Exception as e:
        logger.error(f"Error sending command to tmux session '{clean_session_name}': {e}")
        return False


def send_prompt_to_session(session_name: str, prompt: str, delay_seconds: int = 3) -> bool:
    """
    Send a prompt to a tmux session after a delay to allow Claude to start up.
    Uses proper tmux command separation: first type the text, then send Enter.
    
    Args:
        session_name: Name of the target session
        prompt: Prompt text to send
        delay_seconds: Seconds to wait before sending prompt
    
    Returns:
        True if prompt was sent successfully, False otherwise
    """
    import time
    
    if not is_tmux_available():
        return False
    
    clean_session_name = sanitize_session_name(session_name)
    
    if not session_exists(clean_session_name):
        logger.warning(f"tmux session '{clean_session_name}' does not exist")
        return False
    
    try:
        # Wait for Claude to start up
        logger.info(f"Waiting {delay_seconds} seconds for Claude to start up in session '{clean_session_name}'")
        time.sleep(delay_seconds)
        
        # First command: Type the prompt text (without Enter)
        logger.debug(f"Typing prompt to session '{clean_session_name}'")
        result = subprocess.run(['tmux', 'send-keys', '-t', clean_session_name, prompt], 
                              capture_output=True, 
                              text=True, 
                              timeout=10)
        
        if result.returncode != 0:
            logger.error(f"Failed to type prompt to session: {result.stderr}")
            return False
        
        # Small delay between typing and pressing Enter
        time.sleep(0.5)
        
        # Second command: Send Enter to execute
        logger.debug(f"Sending Enter to session '{clean_session_name}'")
        result = subprocess.run(['tmux', 'send-keys', '-t', clean_session_name, 'Enter'], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        
        if result.returncode == 0:
            logger.info(f"Successfully sent prompt to tmux session '{clean_session_name}'")
            return True
        else:
            logger.error(f"Failed to send Enter to session: {result.stderr}")
            return False
        
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout sending prompt to tmux session '{clean_session_name}'")
        return False
    except Exception as e:
        logger.error(f"Error sending prompt to tmux session '{clean_session_name}': {e}")
        return False


def send_prompt_async(session_name: str, prompt: str, delay_seconds: int = 3) -> None:
    """
    Send a prompt to a tmux session asynchronously in a background thread.
    
    Args:
        session_name: Name of the target session
        prompt: Prompt text to send
        delay_seconds: Seconds to wait before sending prompt
    """
    import threading
    
    def _send_prompt():
        send_prompt_to_session(session_name, prompt, delay_seconds)
    
    thread = threading.Thread(target=_send_prompt, daemon=True)
    thread.start()


def cleanup_agent_sessions(active_agent_ids: List[str]) -> int:
    """
    Clean up tmux sessions that don't correspond to active agents.
    
    Args:
        active_agent_ids: List of currently active agent IDs
    
    Returns:
        Number of sessions cleaned up
    """
    if not is_tmux_available():
        return 0
    
    sessions = list_tmux_sessions()
    cleaned_count = 0
    
    # Clean up sessions that start with 'agent_' but aren't in active_agent_ids
    for session in sessions:
        session_name = session['name']
        
        # Check if this looks like an agent session
        if session_name.startswith('agent_') or any(session_name == sanitize_session_name(agent_id) for agent_id in active_agent_ids):
            # Extract potential agent ID
            potential_agent_id = session_name.replace('agent_', '')
            clean_agent_ids = [sanitize_session_name(aid) for aid in active_agent_ids]
            
            if session_name not in clean_agent_ids and potential_agent_id not in active_agent_ids:
                logger.info(f"Cleaning up orphaned agent session: {session_name}")
                if kill_tmux_session(session_name):
                    cleaned_count += 1
    
    return cleaned_count


def get_admin_token_suffix(admin_token: str) -> str:
    """
    Get the last 4 characters of the admin token for session naming.
    
    Args:
        admin_token: The admin authentication token
        
    Returns:
        Last 4 characters of the token in lowercase
    """
    if not admin_token or len(admin_token) < 4:
        return "0000"  # Fallback for invalid tokens
    return admin_token[-4:].lower()


def generate_agent_session_name(agent_id: str, admin_token: str) -> str:
    """
    Generate a smart tmux session name in the format: agent-{suffix}
    where suffix is the last 4 characters of the admin token.
    
    Args:
        agent_id: The agent identifier
        admin_token: The admin authentication token
        
    Returns:
        Session name in format "agent-1234" where 1234 is from admin token
    """
    suffix = get_admin_token_suffix(admin_token)
    # Use agent_id prefix + suffix to make it unique per agent but identifiable
    clean_agent_id = sanitize_session_name(agent_id)
    return f"{clean_agent_id}-{suffix}"


def parse_agent_session_name(session_name: str, admin_token: str) -> Optional[str]:
    """
    Parse an agent session name to extract the agent ID.
    
    Args:
        session_name: The tmux session name to parse
        admin_token: The admin token to verify suffix
        
    Returns:
        Agent ID if the session matches the pattern, None otherwise
    """
    suffix = get_admin_token_suffix(admin_token)
    
    # Check if session name ends with the admin token suffix
    if not session_name.endswith(f"-{suffix}"):
        return None
    
    # Extract agent ID by removing the suffix
    agent_id = session_name[:-len(f"-{suffix}")]
    
    # Basic validation - agent ID should not be empty
    if not agent_id:
        return None
        
    return agent_id


def discover_active_agents_from_tmux(admin_token: str) -> List[Dict[str, Any]]:
    """
    Discover active agents by scanning tmux sessions for our naming pattern.
    
    Args:
        admin_token: The admin token to identify our sessions
        
    Returns:
        List of discovered agent info with agent_id, session_name, etc.
    """
    discovered_agents = []
    
    try:
        sessions = list_tmux_sessions()
        suffix = get_admin_token_suffix(admin_token)
        
        for session in sessions:
            session_name = session['name']
            
            # Check if this session matches our agent pattern
            agent_id = parse_agent_session_name(session_name, admin_token)
            
            if agent_id:
                discovered_agents.append({
                    'agent_id': agent_id,
                    'session_name': session_name,
                    'session_created': session.get('created'),
                    'session_attached': session.get('attached', False),
                    'session_windows': session.get('windows', 1),
                    'discovered_from_tmux': True
                })
                logger.info(f"Discovered agent '{agent_id}' in tmux session '{session_name}'")
        
        logger.info(f"Discovered {len(discovered_agents)} agents from tmux sessions with suffix '{suffix}'")
        
    except Exception as e:
        logger.error(f"Error discovering agents from tmux: {e}")
    
    return discovered_agents


def sync_agents_from_tmux(admin_token: str) -> Dict[str, Any]:
    """
    Synchronize agent tracking by discovering active agents from tmux sessions.
    
    Args:
        admin_token: The admin token to identify our sessions
        
    Returns:
        Summary of sync operation with discovered agents and stats
    """
    discovered_agents = discover_active_agents_from_tmux(admin_token)
    
    # Import here to avoid circular imports
    from ..core import globals as g
    
    sync_summary = {
        'discovered_count': len(discovered_agents),
        'discovered_agents': [],
        'already_tracked': [],
        'newly_tracked': []
    }
    
    for agent_info in discovered_agents:
        agent_id = agent_info['agent_id']
        session_name = agent_info['session_name']
        
        sync_summary['discovered_agents'].append({
            'agent_id': agent_id,
            'session_name': session_name,
            'session_attached': agent_info['session_attached']
        })
        
        # Check if we're already tracking this session
        if agent_id in g.agent_tmux_sessions:
            if g.agent_tmux_sessions[agent_id] == session_name:
                sync_summary['already_tracked'].append(agent_id)
            else:
                # Update session name if it changed
                g.agent_tmux_sessions[agent_id] = session_name
                sync_summary['newly_tracked'].append(agent_id)
                logger.info(f"Updated session tracking for agent '{agent_id}': {session_name}")
        else:
            # Start tracking this agent session
            g.agent_tmux_sessions[agent_id] = session_name
            sync_summary['newly_tracked'].append(agent_id)
            logger.info(f"Started tracking agent '{agent_id}' in session '{session_name}'")
    
    return sync_summary