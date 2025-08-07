# Agent-MCP/agent_mcp/utils/tmux_utils.py
import subprocess
import re
import shlex
import time
import threading
from typing import List, Dict, Optional, Any
from pathlib import Path

from ..core.config import logger

# TMUX Bible Integration - Critical Rules and Lessons
# Based on lessons learned from multi-agent orchestration

# Git discipline constants (Lesson 6 from TMUX Bible)
AUTO_COMMIT_INTERVAL = 1800  # 30 minutes in seconds
MAX_WORK_WITHOUT_COMMIT = 3600  # 1 hour max

# Communication protocol constants
CLAUDE_STARTUP_DELAY = 5  # seconds
MESSAGE_SEND_DELAY = 0.5  # delay between typing and Enter
STATUS_CHECK_INTERVAL = 300  # 5 minutes for regular checks

# Window naming conventions from TMUX Bible
WINDOW_NAMING_CONVENTIONS = {
    'agent': 'Claude-{role}',
    'server': '{framework}-{purpose}',
    'shell': '{project}-Shell',
    'service': '{service}-Server',
    'temp': 'TEMP-{purpose}'
}


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


def send_claude_message(session_name: str, message: str, delay_seconds: float = 0.5) -> bool:
    """
    Send a message to Claude using proper TMUX Bible protocol.
    
    Based on critical lesson: Always use proper timing and separation
    between message text and Enter key for Claude agents.
    
    Args:
        session_name: Target tmux session/window (format: session:window or session:window.pane)
        message: Message text to send
        delay_seconds: Delay between typing message and pressing Enter
        
    Returns:
        True if message was sent successfully, False otherwise
    """
    if not is_tmux_available():
        logger.error("tmux is not available")
        return False
    
    if not message.strip():
        logger.warning("Attempted to send empty message")
        return False
        
    try:
        # Parse target (could be session:window or session:window.pane)
        target = session_name
        
        # Type the message first (without Enter)
        logger.debug(f"Sending message to {target}: {message[:50]}...")
        result = subprocess.run(['tmux', 'send-keys', '-t', target, message], 
                              capture_output=True, 
                              text=True, 
                              timeout=10)
        
        if result.returncode != 0:
            logger.error(f"Failed to send message to {target}: {result.stderr}")
            return False
        
        # Critical delay - prevents Enter being sent too quickly
        time.sleep(delay_seconds)
        
        # Send Enter to execute
        result = subprocess.run(['tmux', 'send-keys', '-t', target, 'Enter'], 
                              capture_output=True, 
                              text=True, 
                              timeout=5)
        
        if result.returncode == 0:
            logger.info(f"Successfully sent message to {target}")
            return True
        else:
            logger.error(f"Failed to send Enter to {target}: {result.stderr}")
            return False
            
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout sending message to {target}")
        return False
    except Exception as e:
        logger.error(f"Error sending message to {target}: {e}")
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
    def _send_prompt():
        send_prompt_to_session(session_name, prompt, delay_seconds)
    
    thread = threading.Thread(target=_send_prompt, daemon=True)
    thread.start()


def create_project_session_structure(project_name: str, project_path: str, admin_token: str) -> Dict[str, Any]:
    """
    Create a complete tmux session structure for a project following TMUX Bible protocols.
    
    Based on Project Startup Sequence from TMUX Bible.
    
    Args:
        project_name: Name of the project (will be sanitized)
        project_path: Full path to project directory
        admin_token: Admin token for session naming
        
    Returns:
        Dictionary with session info and window mapping
    """
    clean_project_name = sanitize_session_name(project_name)
    
    if session_exists(clean_project_name):
        logger.warning(f"Project session '{clean_project_name}' already exists")
        return {'success': False, 'error': 'Session exists'}
    
    try:
        # Create main session
        logger.info(f"Creating project session structure for '{project_name}'")
        
        # Window 0: Claude Agent (orchestrator/main agent)
        if not create_tmux_session(clean_project_name, project_path):
            return {'success': False, 'error': 'Failed to create main session'}
        
        # Rename first window following naming convention
        subprocess.run(['tmux', 'rename-window', '-t', f'{clean_project_name}:0', 'Claude-Agent'], 
                      capture_output=True, timeout=5)
        
        # Window 1: Project Shell
        subprocess.run(['tmux', 'new-window', '-t', clean_project_name, '-n', 'Project-Shell', '-c', project_path], 
                      capture_output=True, timeout=5)
        
        # Window 2: Dev Server
        subprocess.run(['tmux', 'new-window', '-t', clean_project_name, '-n', 'Dev-Server', '-c', project_path], 
                      capture_output=True, timeout=5)
        
        # Window 3: Available for Project Manager (created on demand)
        # Following hub-and-spoke communication model
        
        session_info = {
            'success': True,
            'session_name': clean_project_name,
            'project_path': project_path,
            'windows': {
                0: {'name': 'Claude-Agent', 'purpose': 'Main orchestrator/developer agent'},
                1: {'name': 'Project-Shell', 'purpose': 'Command line operations'},
                2: {'name': 'Dev-Server', 'purpose': 'Development server'}
            },
            'next_window_id': 3
        }
        
        logger.info(f"Successfully created project session structure: {clean_project_name}")
        return session_info
        
    except Exception as e:
        logger.error(f"Error creating project session structure: {e}")
        return {'success': False, 'error': str(e)}


def create_project_manager_window(session_name: str, project_path: str) -> bool:
    """
    Create a dedicated Project Manager window following TMUX Bible protocols.
    
    Based on "Creating a Project Manager" section from TMUX Bible.
    
    Args:
        session_name: Target session name
        project_path: Working directory for the PM
        
    Returns:
        True if PM window was created successfully
    """
    try:
        # Find next available window number
        result = subprocess.run(['tmux', 'list-windows', '-t', session_name, '-F', '#{window_index}'], 
                              capture_output=True, text=True, timeout=5)
        
        if result.returncode != 0:
            logger.error(f"Failed to list windows for session {session_name}")
            return False
            
        window_numbers = [int(line.strip()) for line in result.stdout.strip().split('\n') if line.strip().isdigit()]
        next_window = max(window_numbers) + 1 if window_numbers else 0
        
        # Create PM window
        result = subprocess.run(['tmux', 'new-window', '-t', session_name, '-n', 'Project-Manager', '-c', project_path], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            logger.info(f"Created Project Manager window in session '{session_name}'")
            return True
        else:
            logger.error(f"Failed to create PM window: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error creating Project Manager window: {e}")
        return False


def rename_session_windows_intelligently(session_name: str) -> Dict[str, Any]:
    """
    Analyze and rename tmux windows with descriptive names based on their content.
    
    Based on "Auto-Rename Feature" from TMUX Bible.
    
    Args:
        session_name: Target session name
        
    Returns:
        Dictionary with rename results
    """
    try:
        result = subprocess.run(['tmux', 'list-windows', '-t', session_name, '-F', 
                               '#{window_index}|#{window_name}|#{pane_current_command}'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode != 0:
            return {'success': False, 'error': 'Failed to list windows'}
        
        renamed_windows = []
        
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
                
            parts = line.split('|')
            if len(parts) >= 3:
                window_index = parts[0]
                current_name = parts[1]
                command = parts[2]
                
                # Determine new name based on command
                new_name = _suggest_window_name(command, current_name)
                
                if new_name != current_name:
                    # Rename the window
                    rename_result = subprocess.run(['tmux', 'rename-window', '-t', 
                                                   f'{session_name}:{window_index}', new_name], 
                                                  capture_output=True, timeout=5)
                    
                    if rename_result.returncode == 0:
                        renamed_windows.append({
                            'window_index': window_index,
                            'old_name': current_name,
                            'new_name': new_name,
                            'command': command
                        })
                        logger.info(f"Renamed window {window_index}: '{current_name}' -> '{new_name}'")
        
        return {
            'success': True,
            'renamed_count': len(renamed_windows),
            'renamed_windows': renamed_windows
        }
        
    except Exception as e:
        logger.error(f"Error renaming windows intelligently: {e}")
        return {'success': False, 'error': str(e)}


def _suggest_window_name(command: str, current_name: str) -> str:
    """
    Suggest a descriptive window name based on the running command.
    
    Based on Window Naming Convention from TMUX Bible.
    """
    command = command.lower()
    
    # Claude agents
    if 'claude' in command:
        return 'Claude-Agent'
    
    # Development servers
    if any(server in command for server in ['npm run dev', 'next dev', 'vite', 'webpack-dev-server']):
        return 'NextJS-Dev' if 'next' in command else 'Frontend-Dev'
    elif 'uvicorn' in command:
        return 'Uvicorn-API'
    elif 'django' in command and 'runserver' in command:
        return 'Django-Server'
    elif 'flask' in command:
        return 'Flask-API'
    elif 'streamlit' in command:
        return 'Streamlit-UI'
    
    # Shells and utilities
    elif command in ['zsh', 'bash', 'fish', 'sh']:
        return 'Shell'
    elif 'python' in command:
        return 'Python-Shell'
    elif 'node' in command:
        return 'Node-Shell'
    
    # Keep current name if no clear pattern
    return current_name


def enforce_git_discipline(session_name: str, auto_commit: bool = True) -> Dict[str, Any]:
    """
    Enforce git discipline rules from TMUX Bible across all windows in a session.
    
    Based on "Git Discipline - MANDATORY FOR ALL AGENTS" from TMUX Bible.
    
    Args:
        session_name: Target session name
        auto_commit: Whether to set up auto-commit for agents
        
    Returns:
        Dictionary with enforcement results
    """
    git_commands = [
        "echo 'Git discipline reminder: Commit every 30 minutes maximum'",
        "echo 'Use: git add -A && git commit -m \"Progress: [description]\"'",
        "echo 'Never work >1 hour without committing'"
    ]
    
    enforced_windows = []
    
    try:
        # Get all windows in the session
        result = subprocess.run(['tmux', 'list-windows', '-t', session_name, '-F', '#{window_index}'], 
                              capture_output=True, text=True, timeout=5)
        
        if result.returncode != 0:
            return {'success': False, 'error': 'Failed to list windows'}
        
        window_indices = [line.strip() for line in result.stdout.strip().split('\n') if line.strip()]
        
        for window_index in window_indices:
            target = f"{session_name}:{window_index}"
            
            # Send git discipline reminders to each window
            for cmd in git_commands:
                send_command_to_session(target, cmd)
                time.sleep(0.2)  # Small delay between commands
            
            enforced_windows.append(window_index)
        
        # Set up auto-commit if requested
        if auto_commit:
            _setup_auto_commit_for_session(session_name)
        
        return {
            'success': True,
            'enforced_windows': enforced_windows,
            'auto_commit_enabled': auto_commit
        }
        
    except Exception as e:
        logger.error(f"Error enforcing git discipline: {e}")
        return {'success': False, 'error': str(e)}


def _setup_auto_commit_for_session(session_name: str) -> None:
    """
    Set up automatic git commits for a session following TMUX Bible rules.
    
    Creates a background thread that commits work every 30 minutes.
    """
    def auto_commit_worker():
        while session_exists(session_name):
            time.sleep(AUTO_COMMIT_INTERVAL)  # 30 minutes
            
            if session_exists(session_name):
                commit_cmd = 'git add -A && git commit -m "Auto-commit: $(date +%Y%m%d-%H%M%S)"'
                
                # Send commit command to main agent window (usually window 0)
                if send_command_to_session(f"{session_name}:0", commit_cmd):
                    logger.info(f"Auto-commit executed for session {session_name}")
                else:
                    logger.warning(f"Failed to execute auto-commit for session {session_name}")
    
    # Start auto-commit worker thread
    commit_thread = threading.Thread(target=auto_commit_worker, daemon=True)
    commit_thread.start()
    logger.info(f"Started auto-commit worker for session {session_name}")


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


def send_status_update_request(session_name: str, target_window: str = "0") -> bool:
    """
    Send a structured status update request following TMUX Bible communication protocols.
    
    Based on "Message Templates" section from TMUX Bible.
    
    Args:
        session_name: Target session name
        target_window: Target window (default "0")
        
    Returns:
        True if status request was sent successfully
    """
    status_request = (
        "STATUS UPDATE: Please provide:\n"
        "1) Completed tasks in last check period\n"
        "2) Current work (be specific)\n"
        "3) Any blockers or issues\n"
        "4) ETA for current task completion"
    )
    
    target = f"{session_name}:{target_window}"
    return send_claude_message(target, status_request)


def send_task_assignment(session_name: str, task_info: Dict[str, Any], target_window: str = "0") -> bool:
    """
    Send a structured task assignment following TMUX Bible protocols.
    
    Args:
        session_name: Target session name
        task_info: Dictionary containing task details
        target_window: Target window
        
    Returns:
        True if task assignment was sent successfully
    """
    task_message = f"""TASK {task_info.get('id', 'UNKNOWN')}: {task_info.get('title', 'Untitled Task')}

Objective: {task_info.get('objective', 'Not specified')}

Success Criteria:
{chr(10).join(f'- {criteria}' for criteria in task_info.get('success_criteria', ['Complete task']))}

Priority: {task_info.get('priority', 'MEDIUM').upper()}
Max Time: {task_info.get('time_limit', '30 minutes')}

IMPORTANT: Commit your work every 30 minutes maximum. Use descriptive commit messages."""
    
    target = f"{session_name}:{target_window}"
    return send_claude_message(target, task_message)


def capture_window_content(session_name: str, window: str = "0", lines: int = 50) -> Optional[str]:
    """
    Capture content from a tmux window for monitoring purposes.
    
    Args:
        session_name: Target session name
        window: Target window
        lines: Number of lines to capture from bottom
        
    Returns:
        Window content as string or None if failed
    """
    try:
        target = f"{session_name}:{window}"
        result = subprocess.run(['tmux', 'capture-pane', '-t', target, '-p', '-S', f'-{lines}'], 
                              capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            return result.stdout
        else:
            logger.error(f"Failed to capture content from {target}: {result.stderr}")
            return None
            
    except Exception as e:
        logger.error(f"Error capturing window content: {e}")
        return None


def check_agent_compliance(session_name: str, window: str = "0") -> Dict[str, Any]:
    """
    Check agent compliance based on recent activity in their tmux window.
    
    Based on compliance monitoring from TMUX Bible.
    
    Args:
        session_name: Target session name
        window: Target window to check
        
    Returns:
        Dictionary with compliance assessment
    """
    content = capture_window_content(session_name, window, 100)
    
    if not content:
        return {
            'compliant': False,
            'reason': 'Unable to capture window content',
            'last_activity': None,
            'indicators': []
        }
    
    # Check for positive compliance indicators
    positive_indicators = []
    negative_indicators = []
    
    content_lower = content.lower()
    
    # Positive indicators
    if 'git commit' in content_lower or 'committed' in content_lower:
        positive_indicators.append('Recent git commits')
    
    if any(phrase in content_lower for phrase in ['completed', 'finished', 'done', 'success']):
        positive_indicators.append('Task completion indicators')
    
    if 'status' in content_lower and 'update' in content_lower:
        positive_indicators.append('Status reporting')
    
    # Negative indicators
    if any(phrase in content_lower for phrase in ['error', 'failed', 'exception', 'traceback']):
        negative_indicators.append('Error messages present')
    
    if 'stuck' in content_lower or 'help' in content_lower:
        negative_indicators.append('Agent requesting help')
    
    # Calculate compliance score
    compliance_score = len(positive_indicators) - len(negative_indicators)
    is_compliant = compliance_score >= 0 and len(negative_indicators) == 0
    
    return {
        'compliant': is_compliant,
        'compliance_score': compliance_score,
        'positive_indicators': positive_indicators,
        'negative_indicators': negative_indicators,
        'content_sample': content[-200:] if content else None  # Last 200 chars for context
    }


def enforce_credit_budget_discipline(session_name: str) -> bool:
    """
    Send budget discipline reminders based on TMUX Bible lessons about credit management.
    
    Based on "Credit/Budget Management Critical" lessons.
    
    Args:
        session_name: Target session name
        
    Returns:
        True if reminders were sent successfully
    """
    budget_reminder = """🚨 CREDIT BUDGET DISCIPLINE REMINDER:

1. Every message costs money - make them count
2. Work 10-15 minutes before asking for help
3. Batch instructions in single messages  
4. Be brief and direct - no long explanations
5. Handle 80% of issues independently

Current Priority: EFFICIENCY MODE
Let PM handle coordination, you focus on implementation."""
    
    return send_claude_message(f"{session_name}:0", budget_reminder)


def create_monitoring_summary(admin_token: str) -> Dict[str, Any]:
    """
    Create a comprehensive monitoring summary of all agent sessions.
    
    Based on monitoring practices from TMUX Bible.
    
    Args:
        admin_token: Admin token to identify relevant sessions
        
    Returns:
        Comprehensive monitoring summary
    """
    try:
        discovered_agents = discover_active_agents_from_tmux(admin_token)
        
        summary = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'total_agents': len(discovered_agents),
            'agent_status': [],
            'compliance_issues': [],
            'recommendations': []
        }
        
        for agent in discovered_agents:
            agent_id = agent['agent_id']
            session_name = agent['session_name']
            
            # Check compliance for this agent
            compliance = check_agent_compliance(session_name)
            
            agent_status = {
                'agent_id': agent_id,
                'session_name': session_name,
                'session_attached': agent.get('session_attached', False),
                'compliance': compliance['compliant'],
                'compliance_score': compliance['compliance_score'],
                'issues': compliance['negative_indicators']
            }
            
            summary['agent_status'].append(agent_status)
            
            # Track compliance issues
            if not compliance['compliant']:
                summary['compliance_issues'].append({
                    'agent_id': agent_id,
                    'issues': compliance['negative_indicators'],
                    'recommendation': 'Immediate intervention required'
                })
        
        # Generate recommendations
        if len(summary['compliance_issues']) > len(discovered_agents) * 0.5:
            summary['recommendations'].append('High non-compliance rate - review agent instructions')
        
        if summary['total_agents'] > 10:
            summary['recommendations'].append('Approaching maximum agent limit (10) - consider cleanup')
        
        return summary
        
    except Exception as e:
        logger.error(f"Error creating monitoring summary: {e}")
        return {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'error': str(e),
            'total_agents': 0,
            'agent_status': [],
            'compliance_issues': [],
            'recommendations': ['Monitoring system failure - check tmux availability']
        }


def activate_plan_mode(session_name: str, window: str = "0") -> bool:
    """
    Activate Claude's plan mode using the key sequence from TMUX Bible.
    
    Based on "Claude Plan Mode Discovery" section.
    
    Args:
        session_name: Target session name
        window: Target window
        
    Returns:
        True if plan mode activation was attempted
    """
    try:
        target = f"{session_name}:{window}"
        
        # Send the Shift+Tab+Tab sequence
        # In tmux, this is represented as S-Tab S-Tab
        result = subprocess.run(['tmux', 'send-keys', '-t', target, 'S-Tab', 'S-Tab'], 
                              capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            logger.info(f"Sent plan mode activation sequence to {target}")
            
            # Wait a moment, then verify activation
            time.sleep(2)
            
            content = capture_window_content(session_name, window, 5)
            if content and "plan mode on" in content.lower():
                logger.info(f"Plan mode successfully activated for {target}")
                return True
            else:
                logger.warning(f"Plan mode activation not confirmed for {target}")
                # Try sending the sequence again
                subprocess.run(['tmux', 'send-keys', '-t', target, 'S-Tab'], 
                             capture_output=True, timeout=5)
                return True
        else:
            logger.error(f"Failed to send plan mode sequence to {target}: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error activating plan mode: {e}")
        return False


def emergency_stop_agent(session_name: str, window: str = "0") -> bool:
    """
    Send emergency stop signal to an agent (Escape key).
    
    Based on escalation protocols from TMUX Bible.
    
    Args:
        session_name: Target session name
        window: Target window
        
    Returns:
        True if stop signal was sent
    """
    try:
        target = f"{session_name}:{window}"
        
        # Send Escape key to interrupt current action
        result = subprocess.run(['tmux', 'send-keys', '-t', target, 'Escape'], 
                              capture_output=True, text=True, timeout=5)
        
        if result.returncode == 0:
            logger.warning(f"Emergency stop signal sent to {target}")
            
            # Follow up with clear stop instruction
            stop_message = "🛑 STOP: Cease current activity and await new instructions."
            return send_claude_message(target, stop_message)
        else:
            logger.error(f"Failed to send emergency stop to {target}: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending emergency stop: {e}")
        return False