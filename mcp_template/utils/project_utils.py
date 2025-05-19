# Agent-MCP/mcp_template/mcp_server_src/utils/project_utils.py
import os
import json
import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from ..core import globals as g
from ..core.config import logger, get_project_dir # Import get_project_dir for MCP_VERSION if needed

# __version__ was in mcp_template/__init__.py.
# If MCP_VERSION is needed here, it should ideally be sourced from a single place.
# For now, let's assume it might come from the main package's __init__ or a dedicated version file.
# We can hardcode it temporarily or make it configurable.
try:
    # Attempt to get version from the root __init__.py of mcp_template
    from mcp_template import __version__ as MCP_VERSION
except ImportError:
    logger.warning("Could not import __version__ from mcp_template. Using default '0.1.0'.")
    MCP_VERSION = "0.1.0" # Fallback, matches original main.py:1041

# Original location: main.py lines 876-929 (init_agent_directory)
def init_agent_directory(project_dir_str: str) -> Optional[Path]:
    """
    Initialize the .agent directory structure in the specified project directory.
    If the directory structure already exists, it verifies it.
    Original main.py: lines 876-929
    """
    try:
        project_path = Path(project_dir_str).resolve()
    except Exception as e:
        logger.error(f"Invalid project directory string '{project_dir_str}': {e}")
        return None

    # Validate that the project directory is not the MCP directory itself
    # This logic needs to correctly identify the MCP codebase root.
    # Assuming this file is at: Agent-MCP/mcp_template/mcp_server_src/utils/project_utils.py
    # Then, __file__.resolve() gives the path to this file.
    # .parent -> .../utils
    # .parent.parent -> .../mcp_server_src
    # .parent.parent.parent -> .../mcp_template (This is the root of the agent code package)
    # .parent.parent.parent.parent -> .../Agent-MCP (This is the repository root)
    # The original check was against `Path(__file__).resolve().parent.parent` from `main.py`
    # which would be `mcp_template`.
    mcp_codebase_root_for_check = Path(__file__).resolve().parent.parent.parent # This should point to mcp_template

    # Original main.py line 880-884
    if project_path == mcp_codebase_root_for_check or project_path in mcp_codebase_root_for_check.parents:
        # This warning matches the original behavior.
        logger.warning(f"WARNING: Initializing .agent in the MCP directory itself ({project_path}) or its parent is not recommended!")
        logger.warning(f"Please specify a project directory that is NOT the MCP codebase.")
        # Original code proceeded with a warning, so we do the same.

    agent_dir = project_path / ".agent"

    # Original main.py lines 887-899 (directory list)
    directories_to_create = [
        "",  # Ensures .agent itself is created
        "logs",
        "diffs",
        "notifications",
        "notifications/pending",
        "notifications/acknowledged",
    ]

    try:
        for directory_suffix in directories_to_create:
            (agent_dir / directory_suffix).mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create .agent directory structure in {agent_dir}: {e}")
        return None # Indicate failure

    # Create initial config file if it doesn't exist
    # Original main.py lines 902-914
    config_path = agent_dir / "config.json"
    if not config_path.exists():
        # g.admin_token might not be initialized when this function is first called
        # during server startup before admin token persistence logic.
        # The original code in main.py:1040 used `admin_token` which was set earlier.
        # We should pass the admin_token to this function if it's needed at this stage,
        # or ensure g.admin_token is reliably set before this.
        # For now, let's assume g.admin_token will be set by the time this is called in a meaningful way,
        # or it will be None if called very early (e.g. initial setup).
        current_admin_token = g.admin_token # Get current global admin token

        config_data = {
            "project_name": project_path.name,
            "created_at": datetime.datetime.now().isoformat(),
            "admin_token": current_admin_token, # Use the admin token available at call time
            "mcp_version": MCP_VERSION
        }
        try:
            with open(config_path, "w", encoding='utf-8') as f:
                json.dump(config_data, f, indent=2)
        except IOError as e:
            logger.error(f"Failed to write initial config.json to {config_path}: {e}")
            return None # Indicate failure
        except Exception as e:
            logger.error(f"Unexpected error writing initial config.json: {e}", exc_info=True)
            return None

    # Create initial daily logs file if it doesn't exist
    # Original main.py lines 917-926
    log_file_dir = agent_dir / "logs"
    # log_file_dir.mkdir(parents=True, exist_ok=True) # Ensured by directories_to_create
    log_file_path = log_file_dir / f"{datetime.date.today().isoformat()}.json"
    if not log_file_path.exists():
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "event": "agent_directory_initialized",
            "details": "Initial setup of .agent directory"
        }
        try:
            with open(log_file_path, "w", encoding='utf-8') as f:
                json.dump([log_entry], f, indent=2) # Original stored a list with one entry
        except IOError as e:
            logger.error(f"Failed to write initial daily log file to {log_file_path}: {e}")
            # Continue, as this is less critical than config.json, matching original behavior.
        except Exception as e:
            logger.error(f"Unexpected error writing initial daily log file: {e}", exc_info=True)


    logger.info(f".agent directory structure initialized/verified in {agent_dir}")
    return agent_dir

# Original location: main.py lines 1206-1239 (generate_system_prompt)
def generate_system_prompt(agent_id: str, agent_token_for_prompt: str, admin_token_runtime: Optional[str]) -> str:
    """
    Generate a system prompt for an agent.
    Original main.py: lines 1206-1239.
    Uses g.agent_working_dirs.
    """
    # Determine working directory for the prompt
    # Fallback to CWD if agent_id not in g.agent_working_dirs, though it should be by the time this is called.
    # (Original main.py line 1226: agent_working_dirs.get(agent_id, os.getcwd()))
    working_dir = g.agent_working_dirs.get(agent_id, os.getcwd())

    # Base prompt content from original main.py lines 1208-1224
    base_prompt = f"""You are an AI agent running in Cursor, connected to a Multi-Agent Collaboration Protocol (MCP) server.

Your goal is to complete tasks efficiently and collaboratively using a shared, persistent knowledge base.

**Core Responsibilities & Tools:**
*   **File Safety:** Before modifying any file, use `check_file_status` to see if another agent is using it. Use `update_file_status` to claim files ('editing', 'reading', 'reviewing') before you start and 'released' when done.
*   **Task Management:** Use `view_tasks` to see your assigned tasks (filter by agent ID or status). Update progress with `update_task_status`. If a task is complex, use `request_assistance` or `create_self_task`.
*   **Project Context (Key-Value):** 
    *   Use `view_project_context` with `context_key` for specific values (e.g., API endpoints, configuration) or `search_query` to find relevant keys via keywords.
    *   (Admin) Use `update_project_context` to add/modify precise key-value context.
*   **File Metadata:** 
    *   Use `view_file_metadata` (with `filepath`) to understand a file's purpose, components, etc.
    *   (Admin) Use `update_file_metadata` to add/update structured information about specific files.
*   **RAG Querying:** Use `ask_project_rag` with a natural language `query` to ask broader questions about the project. The system will search across documentation, context, and metadata to synthesize an answer. (Index updates automatically in the background).
*   **Parallelization:** Analyze tasks for opportunities to work in parallel. Break down large tasks into smaller sub-tasks. Clearly define dependencies.
*   **Auditability:** Log all significant actions for tracking and debugging.

Your working directory is: {working_dir}
"""
    
    # Determine agent type for the prompt
    # (Original main.py line 1227: agent_details, and line 1210 for admin_token check)
    agent_type = "Worker"
    # The original logic in create_agent_tool (main.py:1134) passed `token` (which was the calling admin_token)
    # as the third argument to generate_system_prompt if the agent_id started with "admin".
    # So, `admin_token_runtime` here corresponds to that third argument.
    # An agent is "Admin" type in the prompt if its own token IS the admin token.
    if agent_id.lower().startswith("admin") and agent_token_for_prompt == admin_token_runtime:
        agent_type = "Admin"
    # A simpler check might be if the agent_token_for_prompt itself is the known g.admin_token
    # However, the original call structure was a bit specific.
    # Let's refine: the prompt should reflect if this *specific agent instance* is an admin.
    # This happens if its `agent_token_for_prompt` is the same as the system's `admin_token_runtime`.
    # The `agent_id.lower().startswith("admin")` is a secondary check.
    if agent_token_for_prompt == admin_token_runtime: # Primary check: is this agent's token THE admin token?
         agent_type = "Admin"


    agent_details_str = f"""Agent ID: {agent_id}
Agent Type: {agent_type}
"""
    
    # Connection code snippet for the agent to use
    # (Original main.py lines 1229-1237 for connection code structure)
    # The MCP_SERVER_URL should come from a config or be dynamically determined.
    # The original used os.environ.get('PORT', '8080') which implies it's for the SSE server.
    # The client connection example in the prompt should use the /messages/ endpoint for tool calls if that's the design.
    # Let's assume the agent's env var MCP_SERVER_URL points to the correct base for /messages/
    mcp_server_url_for_client = os.environ.get("MCP_SERVER_URL", f"http://localhost:{os.environ.get('PORT', '8080')}/messages/")
    
    # The original connection code snippet in main.py was quite extensive and specific.
    # For 1-to-1, we should replicate that structure.
    # It assumed the agent would use 'requests' and provided a `call_mcp_tool` like function.
    # The token used in HEADERS should be `agent_token_for_prompt`.
    connection_code_lines = [
        f"MCP_SERVER_URL = \"{mcp_server_url_for_client}\"  # Adjust if your server's tool endpoint is different",
        f"AGENT_TOKEN = \"{agent_token_for_prompt}\" # This is your unique agent token",
        "",
        "HEADERS = {",
        "    \"Content-Type\": \"application/json\",",
        # The original prompt had a complex way of deciding which token to use in Authorization.
        # It should always be the AGENT_TOKEN for the agent's own calls.
        "    \"Authorization\": f\"Bearer {{AGENT_TOKEN}}\"",
        "}",
        "",
        "def call_mcp_tool(tool_name: str, arguments: dict) -> dict:",
        "    payload = {",
        "        \"id\": f\"call_{{requests.compat.urlencode(arguments)[:10]}}\", # Example unique ID",
        "        \"type\": \"tool_call\",",
        "        \"tool\": tool_name,",
        "        \"arguments\": arguments",
        "    }",
        "    print(f\"Calling tool: {{tool_name}} with args: {{arguments}}\") # Debug print",
        "    try:",
        "        response = requests.post(MCP_SERVER_URL, headers=HEADERS, json=payload, timeout=60)",
        "        response.raise_for_status()  # Raise an HTTPError for bad responses (4XX or 5XX)",
        "        # The MCP server is expected to return a list of content blocks.",
        "        # We need to parse the 'text' from the first TextContent block.",
        "        response_data = response.json()",
        "        if isinstance(response_data, list) and len(response_data) > 0:",
        "            first_item = response_data[0]",
        "            if isinstance(first_item, dict) and first_item.get('type') == 'text':",
        "                return {{'text_response': first_item.get('text', '')}}",
        "        return {{'raw_response': response_data}} # Fallback",
        "    except requests.exceptions.Timeout:",
        "        print(f\"Timeout calling MCP tool {{tool_name}}\")",
        "        return {{'error': 'Timeout'}}"
        "    except requests.exceptions.RequestException as e:",
        "        print(f\"Error calling MCP tool {{tool_name}}: {{e}}\")",
        "        if e.response is not None:",
        "            print(f\"Response content: {{e.response.text}}\")",
        "            return {{'error': str(e), 'response_text': e.response.text}}",
        "        return {{'error': str(e)}}",
        "",
        "# Example usage:",
        "# result = call_mcp_tool(\"view_tasks\", {{\"token\": AGENT_TOKEN}})",
        "# if result and 'error' not in result: print(json.dumps(result, indent=2))"
    ]
    connection_code_str = "\n".join(connection_code_lines)
    
    # Construct full prompt (Original main.py line 1238)
    full_prompt = (
        base_prompt +
        agent_details_str +
        "\nCopy-paste this Python code into your environment to connect and interact with the MCP server:\n" +
        "```python\nimport requests\nimport json\n\n" +
        connection_code_str +
        "\n```\n\n" +
        "Use the available tools (the server will list them or consult documentation) via `call_mcp_tool` to manage your work."
    )
    return full_prompt