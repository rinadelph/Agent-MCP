# Agent-MCP/agent_mcp/tools/agent_communication_tools.py
import json
import datetime
import secrets
import sqlite3
from typing import List, Dict, Any, Optional
from pathlib import Path
import os

import mcp.types as mcp_types

from .registry import register_tool
from ..core.config import logger
from ..core import globals as g
from ..core.auth import verify_token, get_agent_id
from ..utils.audit_utils import log_audit
from ..db.connection import get_db_connection
from ..db.actions.agent_actions_db import log_agent_action_to_db
from ..utils.tmux_utils import send_prompt_async, session_exists, sanitize_session_name, send_command_to_session


def _generate_message_id() -> str:
    """Generate a unique message ID."""
    return f"msg_{secrets.token_hex(8)}"


def _can_agents_communicate(sender_id: str, recipient_id: str, is_admin: bool) -> tuple[bool, str]:
    """
    Check if two agents are allowed to communicate.
    
    Args:
        sender_id: ID of the sending agent
        recipient_id: ID of the receiving agent  
        is_admin: Whether the sender has admin privileges
    
    Returns:
        Tuple of (allowed: bool, reason: str)
    """
    # Admin can always communicate with anyone
    if is_admin:
        return True, "Admin privileges"
    
    # Self-communication not allowed (use internal methods)
    if sender_id == recipient_id:
        return False, "Self-communication not allowed"
    
    # Admin agent can always be contacted
    if recipient_id == "admin" or recipient_id.lower().startswith("admin"):
        return True, "Admin agent always contactable"
    
    # Check if recipient allows communication from sender
    # This could be extended with a permission system in the database
    # For now, we'll use a simple rule: agents can communicate if they're both active
    if sender_id in g.active_agents and recipient_id in g.active_agents:
        return True, "Both agents are active"
    
    # Check if either agent is in the same task context
    # (This would require additional task relationship checking)
    
    return False, "Communication not permitted between these agents"


async def send_agent_message_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    """
    Send a message from one agent to another with permission checks.
    Messages can be delivered via tmux session or stored for later retrieval.
    """
    sender_token = arguments.get("token")
    recipient_id = arguments.get("recipient_id")
    message_content = arguments.get("message")
    message_type = arguments.get("message_type", "text")  # text, assistance_request, task_update
    priority = arguments.get("priority", "normal")  # low, normal, high, urgent
    deliver_method = arguments.get("deliver_method", "tmux")  # tmux, store, both
    
    # Authentication
    sender_id = get_agent_id(sender_token)
    if not sender_id:
        return [mcp_types.TextContent(type="text", text="Unauthorized: Valid token required")]
    
    # Validation
    if not recipient_id or not message_content:
        return [mcp_types.TextContent(type="text", text="Error: recipient_id and message are required")]
    
    if len(message_content) > 4000:  # Reasonable message size limit
        return [mcp_types.TextContent(type="text", text="Error: Message too long (max 4000 characters)")]
    
    # Admin-only check for stop commands
    is_admin = verify_token(sender_token, "admin")
    if message_type == "stop_command" and not is_admin:
        return [mcp_types.TextContent(type="text", text="Error: Only admin can send stop commands")]
    
    # Permission check
    can_communicate, reason = _can_agents_communicate(sender_id, recipient_id, is_admin)
    
    if not can_communicate:
        return [mcp_types.TextContent(type="text", text=f"Communication denied: {reason}")]
    
    # Create message data
    message_id = _generate_message_id()
    timestamp = datetime.datetime.now().isoformat()
    
    message_data = {
        "message_id": message_id,
        "sender_id": sender_id,
        "recipient_id": recipient_id,
        "message_content": message_content,
        "message_type": message_type,
        "priority": priority,
        "timestamp": timestamp,
        "delivered": False,
        "read": False
    }
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Store message in database
        cursor.execute("""
            INSERT INTO agent_messages (message_id, sender_id, recipient_id, message_content, 
                                      message_type, priority, timestamp, delivered, read)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (message_id, sender_id, recipient_id, message_content, message_type, 
              priority, timestamp, False, False))
        
        # Attempt delivery based on method
        delivery_status = "stored"
        
        if deliver_method in ["tmux", "both"]:
            # Try to deliver to recipient's tmux session
            if recipient_id in g.agent_tmux_sessions:
                session_name = g.agent_tmux_sessions[recipient_id]
                if session_exists(session_name):
                    # Handle stop commands differently
                    if message_type == "stop_command":
                        # Send control sequence to interrupt the agent
                        try:
                            import subprocess
                            clean_session_name = sanitize_session_name(session_name)
                            
                            # Send Escape 4 times with 1 second intervals to stop current operation
                            import time
                            success = True
                            for i in range(4):
                                result = subprocess.run(['tmux', 'send-keys', '-t', clean_session_name, 'Escape'], 
                                                      capture_output=True, text=True, timeout=5)
                                if result.returncode != 0:
                                    success = False
                                    break
                                logger.debug(f"Sent Escape {i+1}/4 to agent {recipient_id}")
                                if i < 3:  # Don't sleep after the last one
                                    time.sleep(1)
                            
                            if success:
                                delivery_status = "delivered_stop_command"
                                logger.info(f"Stop command (4x Escape) sent to agent {recipient_id} in session {session_name}")
                            else:
                                delivery_status = "stop_command_failed"
                                logger.error(f"Failed to send stop command: {result.stderr}")
                            
                            # Mark as delivered in database
                            cursor.execute("UPDATE agent_messages SET delivered = ? WHERE message_id = ?", 
                                         (success, message_id))
                                         
                        except Exception as e:
                            logger.error(f"Failed to send stop command to tmux session '{session_name}': {e}")
                            delivery_status = "stop_command_failed"
                    else:
                        # Format regular message for delivery
                        formatted_message = f"\n💬 Message from {sender_id} ({priority}): {message_content}\n"
                        
                        # Send message to tmux session
                        try:
                            send_prompt_async(session_name, formatted_message, delay_seconds=1)
                            delivery_status = "delivered_tmux"
                            
                            # Mark as delivered in database
                            cursor.execute("UPDATE agent_messages SET delivered = ? WHERE message_id = ?", 
                                         (True, message_id))
                            
                        except Exception as e:
                            logger.error(f"Failed to deliver message to tmux session '{session_name}': {e}")
                            delivery_status = "delivery_failed"
                else:
                    delivery_status = "session_not_found"
            else:
                delivery_status = "no_session"
        
        # Log the communication
        log_agent_action_to_db(cursor, sender_id, "send_message", 
                               details={
                                   "recipient": recipient_id,
                                   "message_type": message_type,
                                   "priority": priority,
                                   "delivery_status": delivery_status
                               })
        
        conn.commit()
        
        # Audit log
        log_audit(sender_id, "send_agent_message", {
            "recipient": recipient_id,
            "message_type": message_type,
            "priority": priority,
            "delivery_status": delivery_status,
            "message_id": message_id
        })
        
        # Build response
        status_messages = {
            "stored": "Message stored for recipient",
            "delivered_tmux": "Message delivered to recipient's session",
            "delivery_failed": "Message stored but delivery failed",
            "session_not_found": "Message stored; recipient session not active",
            "no_session": "Message stored; recipient has no active session",
            "delivered_stop_command": "Stop command sent to recipient's session",
            "stop_command_failed": "Stop command failed to send"
        }
        
        response_text = f"Message sent to {recipient_id}. {status_messages.get(delivery_status, 'Unknown status')}"
        
        if delivery_status not in ["delivered_tmux", "delivered_stop_command"]:
            response_text += f" (Message ID: {message_id})"
        
        return [mcp_types.TextContent(type="text", text=response_text)]
        
    except sqlite3.Error as e:
        if conn: conn.rollback()
        logger.error(f"Database error sending message: {e}", exc_info=True)
        return [mcp_types.TextContent(type="text", text=f"Database error sending message: {e}")]
    except Exception as e:
        if conn: conn.rollback()
        logger.error(f"Unexpected error sending message: {e}", exc_info=True)
        return [mcp_types.TextContent(type="text", text=f"Unexpected error sending message: {e}")]
    finally:
        if conn:
            conn.close()


async def get_agent_messages_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    """
    Retrieve messages for an agent.
    """
    agent_token = arguments.get("token")
    include_sent = arguments.get("include_sent", False)
    include_received = arguments.get("include_received", True)
    mark_as_read = arguments.get("mark_as_read", True)
    limit = arguments.get("limit", 20)
    message_type_filter = arguments.get("message_type")
    unread_only = arguments.get("unread_only", False)
    
    # Authentication
    agent_id = get_agent_id(agent_token)
    if not agent_id:
        return [mcp_types.TextContent(type="text", text="Unauthorized: Valid token required")]
    
    # Validation
    try:
        limit = int(limit)
        if not (1 <= limit <= 100):
            limit = 20
    except (ValueError, TypeError):
        limit = 20
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Build query
        query_conditions = []
        query_params = []
        
        if include_received and include_sent:
            query_conditions.append("(recipient_id = ? OR sender_id = ?)")
            query_params.extend([agent_id, agent_id])
        elif include_received:
            query_conditions.append("recipient_id = ?")
            query_params.append(agent_id)
        elif include_sent:
            query_conditions.append("sender_id = ?")
            query_params.append(agent_id)
        else:
            return [mcp_types.TextContent(type="text", text="Error: Must include sent or received messages")]
        
        if message_type_filter:
            query_conditions.append("message_type = ?")
            query_params.append(message_type_filter)
        
        if unread_only:
            query_conditions.append("read = ?")
            query_params.append(False)
        
        where_clause = " AND ".join(query_conditions)
        
        query = f"""
            SELECT message_id, sender_id, recipient_id, message_content, message_type, 
                   priority, timestamp, delivered, read
            FROM agent_messages 
            WHERE {where_clause}
            ORDER BY timestamp DESC 
            LIMIT ?
        """
        query_params.append(limit)
        
        cursor.execute(query, query_params)
        messages = cursor.fetchall()
        
        # Mark received messages as read if requested
        if mark_as_read and include_received:
            message_ids_to_mark = [msg["message_id"] for msg in messages 
                                 if msg["recipient_id"] == agent_id and not msg["read"]]
            if message_ids_to_mark:
                placeholders = ",".join("?" * len(message_ids_to_mark))
                cursor.execute(f"UPDATE agent_messages SET read = ? WHERE message_id IN ({placeholders})", 
                             [True] + message_ids_to_mark)
                conn.commit()
        
        # Format response
        if not messages:
            return [mcp_types.TextContent(type="text", text="No messages found")]
        
        response_lines = [f"Messages for {agent_id} (showing {len(messages)} of max {limit}):"]
        response_lines.append("")
        
        for msg in messages:
            direction = "➡️" if msg["sender_id"] == agent_id else "⬅️"
            other_agent = msg["recipient_id"] if msg["sender_id"] == agent_id else msg["sender_id"]
            read_status = "📖" if msg["read"] else "📩"
            priority_icon = {"low": "🔵", "normal": "⚪", "high": "🟡", "urgent": "🔴"}.get(msg["priority"], "⚪")
            
            response_lines.append(f"{direction} {read_status} {priority_icon} [{msg['message_type']}] {other_agent}")
            response_lines.append(f"   {msg['timestamp']}")
            response_lines.append(f"   {msg['message_content']}")
            response_lines.append("")
        
        log_audit(agent_id, "get_agent_messages", {
            "messages_retrieved": len(messages),
            "include_sent": include_sent,
            "include_received": include_received
        })
        
        return [mcp_types.TextContent(type="text", text="\n".join(response_lines))]
        
    except sqlite3.Error as e:
        logger.error(f"Database error retrieving messages: {e}", exc_info=True)
        return [mcp_types.TextContent(type="text", text=f"Database error retrieving messages: {e}")]
    except Exception as e:
        logger.error(f"Unexpected error retrieving messages: {e}", exc_info=True)
        return [mcp_types.TextContent(type="text", text=f"Unexpected error retrieving messages: {e}")]
    finally:
        if conn:
            conn.close()


async def broadcast_admin_message_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    """
    Admin-only tool to broadcast a message to all active agents.
    """
    admin_token = arguments.get("token")
    message_content = arguments.get("message")
    message_type = arguments.get("message_type", "broadcast")
    priority = arguments.get("priority", "high")
    
    # Authentication (admin only)
    if not verify_token(admin_token, "admin"):
        return [mcp_types.TextContent(type="text", text="Unauthorized: Admin token required")]
    
    if not message_content:
        return [mcp_types.TextContent(type="text", text="Error: message is required")]
    
    # Get all active agents
    active_agents = list(g.active_agents.keys())
    if not active_agents:
        return [mcp_types.TextContent(type="text", text="No active agents to broadcast to")]
    
    # Send to each agent
    sent_count = 0
    failed_count = 0
    
    for agent_token in active_agents:
        agent_data = g.active_agents[agent_token]
        recipient_id = agent_data.get("agent_id")
        
        if recipient_id and recipient_id != "admin":  # Don't send to admin itself
            try:
                # Use the send message function
                result = await send_agent_message_tool_impl({
                    "token": admin_token,
                    "recipient_id": recipient_id,
                    "message": message_content,
                    "message_type": message_type,
                    "priority": priority,
                    "deliver_method": "both"
                })
                sent_count += 1
            except Exception as e:
                logger.error(f"Failed to send broadcast to {recipient_id}: {e}")
                failed_count += 1
    
    log_audit("admin", "broadcast_message", {
        "message_type": message_type,
        "priority": priority,
        "sent_count": sent_count,
        "failed_count": failed_count
    })
    
    return [mcp_types.TextContent(
        type="text", 
        text=f"Broadcast sent to {sent_count} agents. {failed_count} failed."
    )]


def register_agent_communication_tools():
    """Register agent communication tools."""
    
    register_tool(
        name="send_agent_message",
        description="Send a message to another agent with permission checks and delivery options.",
        input_schema={
            "type": "object",
            "properties": {
                "token": {
                    "type": "string",
                    "description": "Sender's authentication token"
                },
                "recipient_id": {
                    "type": "string",
                    "description": "ID of the agent to send message to"
                },
                "message": {
                    "type": "string",
                    "description": "Message content (max 4000 characters)"
                },
                "message_type": {
                    "type": "string",
                    "description": "Type of message",
                    "enum": ["text", "assistance_request", "task_update", "notification", "stop_command"],
                    "default": "text"
                },
                "priority": {
                    "type": "string",
                    "description": "Message priority",
                    "enum": ["low", "normal", "high", "urgent"],
                    "default": "normal"
                },
                "deliver_method": {
                    "type": "string",
                    "description": "How to deliver the message",
                    "enum": ["tmux", "store", "both"],
                    "default": "tmux"
                }
            },
            "required": ["token", "recipient_id", "message"],
            "additionalProperties": False
        },
        implementation=send_agent_message_tool_impl
    )
    
    register_tool(
        name="get_agent_messages",
        description="Retrieve messages for the current agent.",
        input_schema={
            "type": "object",
            "properties": {
                "token": {
                    "type": "string",
                    "description": "Agent's authentication token"
                },
                "include_sent": {
                    "type": "boolean",
                    "description": "Include messages sent by this agent",
                    "default": False
                },
                "include_received": {
                    "type": "boolean",
                    "description": "Include messages received by this agent",
                    "default": True
                },
                "mark_as_read": {
                    "type": "boolean",
                    "description": "Mark retrieved messages as read",
                    "default": True
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of messages to retrieve",
                    "default": 20,
                    "minimum": 1,
                    "maximum": 100
                },
                "message_type": {
                    "type": "string",
                    "description": "Filter by message type",
                    "enum": ["text", "assistance_request", "task_update", "notification", "stop_command"]
                },
                "unread_only": {
                    "type": "boolean",
                    "description": "Only show unread messages",
                    "default": False
                }
            },
            "required": ["token"],
            "additionalProperties": False
        },
        implementation=get_agent_messages_tool_impl
    )
    
    register_tool(
        name="broadcast_admin_message",
        description="Admin-only tool to broadcast a message to all active agents.",
        input_schema={
            "type": "object",
            "properties": {
                "token": {
                    "type": "string",
                    "description": "Admin authentication token"
                },
                "message": {
                    "type": "string",
                    "description": "Message content to broadcast"
                },
                "message_type": {
                    "type": "string",
                    "description": "Type of broadcast message",
                    "enum": ["broadcast", "announcement", "system_alert"],
                    "default": "broadcast"
                },
                "priority": {
                    "type": "string",
                    "description": "Message priority",
                    "enum": ["low", "normal", "high", "urgent"],
                    "default": "high"
                }
            },
            "required": ["token", "message"],
            "additionalProperties": False
        },
        implementation=broadcast_admin_message_tool_impl
    )


# Auto-register when imported
register_agent_communication_tools()