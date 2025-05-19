# Agent-MCP/mcp_template/mcp_server_src/db/actions/agent_db.py
import sqlite3
import json
from typing import Optional, Dict, List, Any

from mcp_server_src.core.config import logger
from mcp_server_src.db.connection import get_db_connection

# This module provides reusable database operations specifically for the 'agents' table.

def get_agent_by_id(agent_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetches a single agent's details from the database by agent_id.
    Returns None if the agent is not found.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM agents WHERE agent_id = ?", (agent_id,))
        row = cursor.fetchone()
        if row:
            agent_data = dict(row)
            # Parse JSON fields if necessary (e.g., capabilities)
            if 'capabilities' in agent_data and isinstance(agent_data['capabilities'], str):
                try:
                    agent_data['capabilities'] = json.loads(agent_data['capabilities'])
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse capabilities JSON for agent {agent_id}. Raw: {agent_data['capabilities']}")
                    agent_data['capabilities'] = [] # Default to empty list on parse error
            return agent_data
        return None
    except sqlite3.Error as e:
        logger.error(f"Database error fetching agent by ID '{agent_id}': {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching agent by ID '{agent_id}': {e}", exc_info=True)
        return None
    finally:
        if conn:
            conn.close()

def get_agent_by_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Fetches a single agent's details from the database by their token.
    Returns None if the agent is not found.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM agents WHERE token = ?", (token,))
        row = cursor.fetchone()
        if row:
            agent_data = dict(row)
            if 'capabilities' in agent_data and isinstance(agent_data['capabilities'], str):
                try:
                    agent_data['capabilities'] = json.loads(agent_data['capabilities'])
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse capabilities JSON for agent with token. Raw: {agent_data['capabilities']}")
                    agent_data['capabilities'] = []
            return agent_data
        return None
    except sqlite3.Error as e:
        logger.error(f"Database error fetching agent by token: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching agent by token: {e}", exc_info=True)
        return None
    finally:
        if conn:
            conn.close()

def get_all_active_agents_from_db() -> List[Dict[str, Any]]:
    """
    Fetches all agents from the database that are not 'terminated'.
    This is used for populating g.active_agents at startup.
    """
    agents_list: List[Dict[str, Any]] = []
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Query matches the one in server_lifecycle.application_startup
        cursor.execute("""
            SELECT token, agent_id, capabilities, created_at, status, current_task, working_directory, color 
            FROM agents WHERE status != ?
        """, ("terminated",))
        for row in cursor.fetchall():
            agent_data = dict(row)
            if 'capabilities' in agent_data and isinstance(agent_data['capabilities'], str):
                try:
                    agent_data['capabilities'] = json.loads(agent_data['capabilities'] or '[]')
                except json.JSONDecodeError:
                    agent_data['capabilities'] = []
            agents_list.append(agent_data)
        return agents_list
    except sqlite3.Error as e:
        logger.error(f"Database error fetching all active agents: {e}", exc_info=True)
        return [] # Return empty list on error
    except Exception as e:
        logger.error(f"Unexpected error fetching all active agents: {e}", exc_info=True)
        return []
    finally:
        if conn:
            conn.close()

# Add other agent-specific DB operations here if needed, e.g.:
# - update_agent_status(agent_id, new_status, new_current_task=None)
# - update_agent_capabilities(agent_id, new_capabilities)
# These are currently handled within the tool implementations (admin_tools.py, task_tools.py)
# For a strict 1-to-1 of original main.py, these more granular functions weren't separate.
# However, having them here improves modularity if these operations become more complex or reused.

# Example: A more specific update function (not directly from original main.py as a separate function)
def update_agent_db_field(agent_id: str, field_name: str, new_value: Any) -> bool:
    """
    Updates a specific field for an agent in the database.
    Handles JSON serialization for fields like 'capabilities'.
    Returns True on success, False on failure.
    """
    if field_name not in ['status', 'current_task', 'working_directory', 'color', 'capabilities', 'updated_at']:
        logger.error(f"Attempted to update an invalid or unsupported agent field: {field_name}")
        return False

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        value_to_set = new_value
        if field_name == 'capabilities':
            value_to_set = json.dumps(new_value or [])
        elif field_name == 'updated_at' and new_value is None: # Auto-set updated_at if not provided
            value_to_set = datetime.datetime.now().isoformat()
        
        # Always update 'updated_at' timestamp
        sql = f"UPDATE agents SET {field_name} = ?, updated_at = ? WHERE agent_id = ?"
        current_time = datetime.datetime.now().isoformat()
        
        cursor.execute(sql, (value_to_set, current_time, agent_id))
        conn.commit()
        
        if cursor.rowcount > 0:
            logger.info(f"Agent '{agent_id}' field '{field_name}' updated in DB.")
            return True
        else:
            logger.warning(f"Agent '{agent_id}' not found or field '{field_name}' update had no effect in DB.")
            return False
            
    except sqlite3.Error as e:
        if conn: conn.rollback()
        logger.error(f"Database error updating agent '{agent_id}' field '{field_name}': {e}", exc_info=True)
        return False
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Unexpected error updating agent '{agent_id}' field '{field_name}': {e}", exc_info=True)
        return False
    finally:
        if conn:
            conn.close()