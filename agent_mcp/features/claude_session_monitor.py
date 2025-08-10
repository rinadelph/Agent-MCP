# Agent-MCP/agent_mcp/features/claude_session_monitor.py
import os
import json
import asyncio
import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from ..core.config import logger, get_project_dir
from ..db.connection import get_db_connection
from ..db.actions.agent_actions_db import log_agent_action_to_db


class ClaudeSessionMonitor:
    """
    Monitors .agent/registry.json for Claude Code session activity.
    Integrates with git-agentmcp hook for multi-agent coordination.
    """

    def __init__(self):
        self.project_dir = get_project_dir()
        self.registry_path = Path(self.project_dir) / ".agent" / "registry.json"
        self.last_modified = None
        self.known_sessions = {}

    async def monitor_registry_file(self, interval: int = 5):
        """
        Periodically check .agent/registry.json for changes and process new sessions.
        """
        logger.info(f"Claude session monitor started (checking every {interval}s)")

        while True:
            try:
                await self.check_registry_changes()
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Error in Claude session monitor: {e}", exc_info=True)
                await asyncio.sleep(interval)  # Continue monitoring despite errors

    async def check_registry_changes(self):
        """Check if registry file has changed and process updates."""
        try:
            if not self.registry_path.exists():
                return

            # Check if file was modified
            current_modified = self.registry_path.stat().st_mtime
            if (
                self.last_modified is not None
                and current_modified <= self.last_modified
            ):
                return  # No changes

            self.last_modified = current_modified

            # Read and process registry
            with open(self.registry_path, "r") as f:
                registry = json.load(f)

            await self.process_registry_update(registry)

        except FileNotFoundError:
            # Registry file doesn't exist yet - normal for new projects
            pass
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in registry file: {self.registry_path}")
        except Exception as e:
            logger.error(f"Error checking registry changes: {e}", exc_info=True)

    async def process_registry_update(self, registry: Dict[str, Any]):
        """Process registry updates and sync with database."""
        try:
            sessions = registry.get("sessions", {})

            for session_id, session_data in sessions.items():
                if session_id not in self.known_sessions:
                    # New session detected
                    await self.register_new_session(session_id, session_data)
                    self.known_sessions[session_id] = session_data.copy()
                else:
                    # Update existing session
                    await self.update_session_activity(session_id, session_data)
                    self.known_sessions[session_id] = session_data.copy()

            # Clean up stale sessions from known_sessions
            current_session_ids = set(sessions.keys())
            stale_sessions = set(self.known_sessions.keys()) - current_session_ids
            for stale_id in stale_sessions:
                await self.mark_session_inactive(stale_id)
                del self.known_sessions[stale_id]

        except Exception as e:
            logger.error(f"Error processing registry update: {e}", exc_info=True)

    async def register_new_session(self, session_id: str, session_data: Dict[str, Any]):
        """Register a new Claude Code session in the database."""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            now = datetime.datetime.now().isoformat()

            # Insert new session
            cursor.execute(
                """
                INSERT OR REPLACE INTO claude_code_sessions 
                (session_id, pid, parent_pid, first_detected, last_activity, working_directory, status, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    session_id,
                    session_data.get("pid", 0),
                    session_data.get("parent_pid", 0),
                    now,
                    session_data.get("last_activity", now),
                    session_data.get("working_directory"),
                    "detected",
                    json.dumps(session_data),
                ),
            )

            conn.commit()
            conn.close()

            # Log detection activity
            log_agent_action_to_db(
                agent_id="system",
                action_type="claude_session_detected",
                task_id=None,
                details=json.dumps(
                    {
                        "session_id": session_id,
                        "pid": session_data.get("pid"),
                        "parent_pid": session_data.get("parent_pid"),
                        "working_directory": session_data.get("working_directory"),
                    }
                ),
            )

            logger.info(
                f"New Claude Code session detected: {session_id} (PID: {session_data.get('pid')})"
            )

        except Exception as e:
            logger.error(
                f"Error registering new session {session_id}: {e}", exc_info=True
            )

    async def update_session_activity(
        self, session_id: str, session_data: Dict[str, Any]
    ):
        """Update activity for existing session."""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE claude_code_sessions 
                SET last_activity = ?, metadata = ?, status = 'active'
                WHERE session_id = ?
            """,
                (
                    session_data.get(
                        "last_activity", datetime.datetime.now().isoformat()
                    ),
                    json.dumps(session_data),
                    session_id,
                ),
            )

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(
                f"Error updating session activity {session_id}: {e}", exc_info=True
            )

    async def mark_session_inactive(self, session_id: str):
        """Mark session as inactive (removed from registry)."""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE claude_code_sessions 
                SET status = 'inactive', last_activity = ?
                WHERE session_id = ?
            """,
                (datetime.datetime.now().isoformat(), session_id),
            )

            conn.commit()
            conn.close()

            logger.info(f"Claude Code session marked inactive: {session_id}")

        except Exception as e:
            logger.error(
                f"Error marking session inactive {session_id}: {e}", exc_info=True
            )

    async def get_active_sessions(self) -> Dict[str, Any]:
        """Get all active Claude Code sessions from database."""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT * FROM claude_code_sessions 
                WHERE status IN ('detected', 'active')
                ORDER BY last_activity DESC
            """
            )

            sessions = {}
            for row in cursor.fetchall():
                sessions[row["session_id"]] = dict(row)

            conn.close()
            return sessions

        except Exception as e:
            logger.error(f"Error getting active sessions: {e}", exc_info=True)
            return {}


# Global monitor instance
claude_session_monitor = ClaudeSessionMonitor()


async def run_claude_session_monitoring(interval: int = 5, *, task_status=None):
    """Background task for monitoring Claude Code sessions."""
    if task_status:
        task_status.started()
    await claude_session_monitor.monitor_registry_file(interval)
