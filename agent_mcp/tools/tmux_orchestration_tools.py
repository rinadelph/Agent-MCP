# Agent-MCP/agent_mcp/tools/tmux_orchestration_tools.py
"""
TMUX Bible-enhanced orchestration tools for Agent-MCP.

These tools implement the critical lessons learned from multi-agent orchestration
as documented in the TMUX Bible.
"""

import asyncio
from typing import List, Dict, Any, Optional
import json
import time

import mcp.types as mcp_types
from ..core.config import logger
from ..core import globals as g
from ..utils.tmux_utils import (
    is_tmux_available,
    create_project_session_structure,
    create_project_manager_window,
    send_claude_message,
    send_status_update_request,
    send_task_assignment,
    check_agent_compliance,
    create_monitoring_summary,
    activate_plan_mode,
    emergency_stop_agent,
    enforce_credit_budget_discipline,
    enforce_git_discipline,
    rename_session_windows_intelligently,
    discover_active_agents_from_tmux
)


async def tmux_create_project_session(name: str, arguments: dict) -> List[mcp_types.TextContent]:
    """
    Create a complete project session structure following TMUX Bible protocols.
    
    This implements the Project Startup Sequence from TMUX Bible.
    """
    try:
        project_name = arguments.get('project_name', '').strip()
        project_path = arguments.get('project_path', '').strip()
        admin_token = arguments.get('admin_token', g.admin_token)
        
        if not project_name:
            return [mcp_types.TextContent(
                type="text",
                text="ERROR: project_name is required"
            )]
        
        if not project_path:
            return [mcp_types.TextContent(
                type="text",
                text="ERROR: project_path is required"
            )]
        
        if not is_tmux_available():
            return [mcp_types.TextContent(
                type="text",
                text="ERROR: tmux is not available on this system"
            )]
        
        # Create the project session structure
        result = create_project_session_structure(project_name, project_path, admin_token)
        
        if result['success']:
            # Log the session creation
            logger.info(f"Created project session '{project_name}' with TMUX Bible structure")
            
            response = f"""✅ Project session created successfully!

**Session Details:**
- Name: {result['session_name']}
- Path: {result['project_path']}
- Windows created: {len(result['windows'])}

**Window Structure:**
"""
            for window_id, window_info in result['windows'].items():
                response += f"- Window {window_id}: {window_info['name']} ({window_info['purpose']})\n"
            
            response += f"""
**Next Steps (TMUX Bible Protocol):**
1. Brief the Claude agent in window 0
2. Set up development server in window 2
3. Create Project Manager when needed (window 3+)
4. Enforce git discipline across all windows

**Ready for agent deployment!**"""
            
            return [mcp_types.TextContent(type="text", text=response)]
        else:
            error_msg = f"❌ Failed to create project session: {result.get('error', 'Unknown error')}"
            logger.error(error_msg)
            return [mcp_types.TextContent(type="text", text=error_msg)]
            
    except Exception as e:
        error_msg = f"Error creating project session: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return [mcp_types.TextContent(type="text", text=error_msg)]


async def tmux_send_message_to_agent(name: str, arguments: dict) -> List[mcp_types.TextContent]:
    """
    Send a message to a Claude agent using proper TMUX Bible timing protocols.
    
    This replaces manual tmux send-keys with proper timing and error handling.
    """
    try:
        session_target = arguments.get('session_target', '').strip()
        message = arguments.get('message', '').strip()
        
        if not session_target:
            return [mcp_types.TextContent(
                type="text",
                text="ERROR: session_target is required (format: session:window or session:window.pane)"
            )]
        
        if not message:
            return [mcp_types.TextContent(
                type="text",
                text="ERROR: message is required"
            )]
        
        # Send the message using proper TMUX Bible protocol
        success = send_claude_message(session_target, message)
        
        if success:
            logger.info(f"Message sent to {session_target}: {message[:50]}...")
            return [mcp_types.TextContent(
                type="text",
                text=f"✅ Message sent successfully to {session_target}"
            )]
        else:
            return [mcp_types.TextContent(
                type="text",
                text=f"❌ Failed to send message to {session_target}"
            )]
            
    except Exception as e:
        error_msg = f"Error sending message: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return [mcp_types.TextContent(type="text", text=error_msg)]


async def tmux_request_status_update(name: str, arguments: dict) -> List[mcp_types.TextContent]:
    """
    Request a structured status update from an agent following TMUX Bible protocols.
    """
    try:
        session_name = arguments.get('session_name', '').strip()
        window = arguments.get('window', '0')
        
        if not session_name:
            return [mcp_types.TextContent(
                type="text",
                text="ERROR: session_name is required"
            )]
        
        success = send_status_update_request(session_name, window)
        
        if success:
            return [mcp_types.TextContent(
                type="text",
                text=f"✅ Status update request sent to {session_name}:{window}"
            )]
        else:
            return [mcp_types.TextContent(
                type="text",
                text=f"❌ Failed to send status update request to {session_name}:{window}"
            )]
            
    except Exception as e:
        error_msg = f"Error requesting status update: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return [mcp_types.TextContent(type="text", text=error_msg)]


async def tmux_assign_task(name: str, arguments: dict) -> List[mcp_types.TextContent]:
    """
    Assign a structured task to an agent following TMUX Bible protocols.
    """
    try:
        session_name = arguments.get('session_name', '').strip()
        window = arguments.get('window', '0')
        task_info = arguments.get('task_info', {})
        
        if not session_name:
            return [mcp_types.TextContent(
                type="text",
                text="ERROR: session_name is required"
            )]
        
        # Ensure task_info has required fields
        if not isinstance(task_info, dict):
            return [mcp_types.TextContent(
                type="text",
                text="ERROR: task_info must be a dictionary with task details"
            )]
        
        success = send_task_assignment(session_name, task_info, window)
        
        if success:
            task_title = task_info.get('title', 'Untitled Task')
            return [mcp_types.TextContent(
                type="text",
                text=f"✅ Task '{task_title}' assigned to {session_name}:{window}"
            )]
        else:
            return [mcp_types.TextContent(
                type="text",
                text=f"❌ Failed to assign task to {session_name}:{window}"
            )]
            
    except Exception as e:
        error_msg = f"Error assigning task: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return [mcp_types.TextContent(type="text", text=error_msg)]


async def tmux_check_compliance(name: str, arguments: dict) -> List[mcp_types.TextContent]:
    """
    Check agent compliance based on TMUX Bible monitoring rules.
    """
    try:
        session_name = arguments.get('session_name', '').strip()
        window = arguments.get('window', '0')
        
        if not session_name:
            return [mcp_types.TextContent(
                type="text",
                text="ERROR: session_name is required"
            )]
        
        compliance = check_agent_compliance(session_name, window)
        
        status_icon = "✅" if compliance['compliant'] else "❌"
        response = f"{status_icon} **Agent Compliance Check: {session_name}:{window}**\n\n"
        
        response += f"**Compliance Status:** {'COMPLIANT' if compliance['compliant'] else 'NON-COMPLIANT'}\n"
        response += f"**Compliance Score:** {compliance['compliance_score']}\n\n"
        
        if compliance['positive_indicators']:
            response += "**Positive Indicators:**\n"
            for indicator in compliance['positive_indicators']:
                response += f"✅ {indicator}\n"
            response += "\n"
        
        if compliance['negative_indicators']:
            response += "**Issues Found:**\n"
            for indicator in compliance['negative_indicators']:
                response += f"❌ {indicator}\n"
            response += "\n"
        
        if compliance.get('content_sample'):
            response += f"**Recent Activity Sample:**\n```\n{compliance['content_sample']}\n```\n"
        
        # Add recommendations based on compliance
        if not compliance['compliant']:
            response += "\n**Recommended Actions:**\n"
            response += "1. Send direct intervention message\n"
            response += "2. Consider 2-minute check interval\n"
            response += "3. If no improvement, escalate to replacement\n"
        
        return [mcp_types.TextContent(type="text", text=response)]
        
    except Exception as e:
        error_msg = f"Error checking compliance: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return [mcp_types.TextContent(type="text", text=error_msg)]


async def tmux_create_monitoring_report(name: str, arguments: dict) -> List[mcp_types.TextContent]:
    """
    Create a comprehensive monitoring report of all agents.
    """
    try:
        admin_token = arguments.get('admin_token', g.admin_token)
        
        summary = create_monitoring_summary(admin_token)
        
        response = f"📊 **Agent Monitoring Report**\n"
        response += f"**Generated:** {summary['timestamp']}\n"
        response += f"**Total Agents:** {summary['total_agents']}\n\n"
        
        if summary.get('error'):
            response += f"❌ **Error:** {summary['error']}\n"
            return [mcp_types.TextContent(type="text", text=response)]
        
        # Agent status table
        if summary['agent_status']:
            response += "**Agent Status:**\n"
            for agent in summary['agent_status']:
                status_icon = "✅" if agent['compliance'] else "❌"
                attached_icon = "🔗" if agent['session_attached'] else "📱"
                response += f"{status_icon} {attached_icon} **{agent['agent_id']}** "
                response += f"(Session: {agent['session_name']}, Score: {agent['compliance_score']})\n"
                
                if agent['issues']:
                    for issue in agent['issues']:
                        response += f"   ⚠️ {issue}\n"
            response += "\n"
        
        # Compliance issues
        if summary['compliance_issues']:
            response += "**🚨 Compliance Issues:**\n"
            for issue in summary['compliance_issues']:
                response += f"❌ **{issue['agent_id']}:** {', '.join(issue['issues'])}\n"
                response += f"   Recommendation: {issue['recommendation']}\n"
            response += "\n"
        
        # Recommendations
        if summary['recommendations']:
            response += "**💡 System Recommendations:**\n"
            for rec in summary['recommendations']:
                response += f"• {rec}\n"
        
        return [mcp_types.TextContent(type="text", text=response)]
        
    except Exception as e:
        error_msg = f"Error creating monitoring report: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return [mcp_types.TextContent(type="text", text=error_msg)]


async def tmux_activate_plan_mode(name: str, arguments: dict) -> List[mcp_types.TextContent]:
    """
    Activate Claude's plan mode using TMUX Bible key sequence.
    """
    try:
        session_name = arguments.get('session_name', '').strip()
        window = arguments.get('window', '0')
        
        if not session_name:
            return [mcp_types.TextContent(
                type="text",
                text="ERROR: session_name is required"
            )]
        
        success = activate_plan_mode(session_name, window)
        
        if success:
            return [mcp_types.TextContent(
                type="text",
                text=f"✅ Plan mode activation attempted for {session_name}:{window}\n"
                     "Check the agent window to verify '⏸ plan mode on' appears."
            )]
        else:
            return [mcp_types.TextContent(
                type="text",
                text=f"❌ Failed to activate plan mode for {session_name}:{window}"
            )]
            
    except Exception as e:
        error_msg = f"Error activating plan mode: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return [mcp_types.TextContent(type="text", text=error_msg)]


async def tmux_emergency_stop(name: str, arguments: dict) -> List[mcp_types.TextContent]:
    """
    Send emergency stop signal to an agent (escalation protocol).
    """
    try:
        session_name = arguments.get('session_name', '').strip()
        window = arguments.get('window', '0')
        
        if not session_name:
            return [mcp_types.TextContent(
                type="text",
                text="ERROR: session_name is required"
            )]
        
        success = emergency_stop_agent(session_name, window)
        
        if success:
            logger.warning(f"Emergency stop executed for {session_name}:{window}")
            return [mcp_types.TextContent(
                type="text",
                text=f"🛑 Emergency stop signal sent to {session_name}:{window}\n"
                     "Agent has been instructed to cease current activity and await instructions."
            )]
        else:
            return [mcp_types.TextContent(
                type="text",
                text=f"❌ Failed to send emergency stop to {session_name}:{window}"
            )]
            
    except Exception as e:
        error_msg = f"Error sending emergency stop: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return [mcp_types.TextContent(type="text", text=error_msg)]


async def tmux_enforce_budget_discipline(name: str, arguments: dict) -> List[mcp_types.TextContent]:
    """
    Enforce credit budget discipline across all agents in a session.
    """
    try:
        session_name = arguments.get('session_name', '').strip()
        
        if not session_name:
            return [mcp_types.TextContent(
                type="text",
                text="ERROR: session_name is required"
            )]
        
        success = enforce_credit_budget_discipline(session_name)
        
        if success:
            return [mcp_types.TextContent(
                type="text",
                text=f"✅ Budget discipline reminder sent to {session_name}\n"
                     "All agents have been reminded about credit conservation."
            )]
        else:
            return [mcp_types.TextContent(
                type="text",
                text=f"❌ Failed to send budget discipline reminder to {session_name}"
            )]
            
    except Exception as e:
        error_msg = f"Error enforcing budget discipline: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return [mcp_types.TextContent(type="text", text=error_msg)]


async def tmux_enforce_git_discipline(name: str, arguments: dict) -> List[mcp_types.TextContent]:
    """
    Enforce git discipline rules across all windows in a session.
    """
    try:
        session_name = arguments.get('session_name', '').strip()
        auto_commit = arguments.get('auto_commit', True)
        
        if not session_name:
            return [mcp_types.TextContent(
                type="text",
                text="ERROR: session_name is required"
            )]
        
        result = enforce_git_discipline(session_name, auto_commit)
        
        if result['success']:
            response = f"✅ Git discipline enforced for {session_name}\n"
            response += f"Windows updated: {len(result['enforced_windows'])}\n"
            if result['auto_commit_enabled']:
                response += "Auto-commit reminders activated (every 30 minutes)\n"
            response += "\nAll agents reminded of mandatory git practices."
            
            return [mcp_types.TextContent(type="text", text=response)]
        else:
            return [mcp_types.TextContent(
                type="text",
                text=f"❌ Failed to enforce git discipline: {result.get('error', 'Unknown error')}"
            )]
            
    except Exception as e:
        error_msg = f"Error enforcing git discipline: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return [mcp_types.TextContent(type="text", text=error_msg)]


async def tmux_intelligent_window_rename(name: str, arguments: dict) -> List[mcp_types.TextContent]:
    """
    Intelligently rename windows based on their content following TMUX Bible conventions.
    """
    try:
        session_name = arguments.get('session_name', '').strip()
        
        if not session_name:
            return [mcp_types.TextContent(
                type="text",
                text="ERROR: session_name is required"
            )]
        
        result = rename_session_windows_intelligently(session_name)
        
        if result['success']:
            response = f"✅ Intelligent window renaming completed for {session_name}\n"
            response += f"Windows renamed: {result['renamed_count']}\n\n"
            
            if result['renamed_windows']:
                response += "**Rename Summary:**\n"
                for rename in result['renamed_windows']:
                    response += f"Window {rename['window_index']}: '{rename['old_name']}' → '{rename['new_name']}'\n"
                    response += f"   Based on command: {rename['command']}\n"
            else:
                response += "No windows needed renaming (already have descriptive names)."
            
            return [mcp_types.TextContent(type="text", text=response)]
        else:
            return [mcp_types.TextContent(
                type="text",
                text=f"❌ Failed to rename windows: {result.get('error', 'Unknown error')}"
            )]
            
    except Exception as e:
        error_msg = f"Error renaming windows: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return [mcp_types.TextContent(type="text", text=error_msg)]


# Registration function to be called from tools.__init__.py
def register_tmux_orchestration_tools():
    """
    Register all TMUX orchestration tools with the MCP registry.
    
    This function is called during tools package initialization to register
    all TMUX Bible enhanced tools for multi-agent orchestration.
    """
    from .registry import register_tool
    
    # Map tool names to their implementation functions
    tool_mapping = {
        "tmux_create_project_session": tmux_create_project_session,
        "tmux_send_message_to_agent": tmux_send_message_to_agent,
        "tmux_request_status_update": tmux_request_status_update,
        "tmux_assign_task": tmux_assign_task,
        "tmux_check_compliance": tmux_check_compliance,
        "tmux_create_monitoring_report": tmux_create_monitoring_report,
        "tmux_activate_plan_mode": tmux_activate_plan_mode,
        "tmux_emergency_stop": tmux_emergency_stop,
        "tmux_enforce_budget_discipline": tmux_enforce_budget_discipline,
        "tmux_enforce_git_discipline": tmux_enforce_git_discipline,
        "tmux_intelligent_window_rename": tmux_intelligent_window_rename
    }
    
    # Register each tool with its schema
    for tool_schema in TMUX_ORCHESTRATION_TOOLS:
        tool_name = tool_schema.name
        if tool_name in tool_mapping:
            register_tool(
                name=tool_name,
                description=tool_schema.description,
                input_schema=tool_schema.inputSchema,
                implementation=tool_mapping[tool_name]
            )
        else:
            logger.error(f"No implementation found for TMUX tool: {tool_name}")
    
    logger.info(f"Registered {len(TMUX_ORCHESTRATION_TOOLS)} TMUX orchestration tools")


# Tool definitions for MCP registration
TMUX_ORCHESTRATION_TOOLS = [
    mcp_types.Tool(
        name="tmux_create_project_session",
        description="Create a complete project session structure following TMUX Bible protocols",
        inputSchema={
            "type": "object",
            "properties": {
                "project_name": {
                    "type": "string",
                    "description": "Name of the project (will be sanitized for tmux)"
                },
                "project_path": {
                    "type": "string",
                    "description": "Full path to the project directory"
                },
                "admin_token": {
                    "type": "string",
                    "description": "Admin token for session naming (optional, uses global if not provided)"
                }
            },
            "required": ["project_name", "project_path"]
        }
    ),
    
    mcp_types.Tool(
        name="tmux_send_message_to_agent",
        description="Send a message to Claude agent using proper TMUX Bible timing protocols",
        inputSchema={
            "type": "object",
            "properties": {
                "session_target": {
                    "type": "string",
                    "description": "Target in format session:window or session:window.pane"
                },
                "message": {
                    "type": "string",
                    "description": "Message to send to the agent"
                }
            },
            "required": ["session_target", "message"]
        }
    ),
    
    mcp_types.Tool(
        name="tmux_request_status_update",
        description="Request structured status update from an agent",
        inputSchema={
            "type": "object",
            "properties": {
                "session_name": {
                    "type": "string",
                    "description": "Name of the tmux session"
                },
                "window": {
                    "type": "string",
                    "description": "Window number (default: '0')"
                }
            },
            "required": ["session_name"]
        }
    ),
    
    mcp_types.Tool(
        name="tmux_assign_task",
        description="Assign a structured task to an agent following TMUX Bible protocols",
        inputSchema={
            "type": "object",
            "properties": {
                "session_name": {
                    "type": "string",
                    "description": "Name of the tmux session"
                },
                "window": {
                    "type": "string",
                    "description": "Window number (default: '0')"
                },
                "task_info": {
                    "type": "object",
                    "description": "Task information dictionary",
                    "properties": {
                        "id": {"type": "string", "description": "Task ID"},
                        "title": {"type": "string", "description": "Task title"},
                        "objective": {"type": "string", "description": "Clear objective"},
                        "success_criteria": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of success criteria"
                        },
                        "priority": {
                            "type": "string",
                            "enum": ["HIGH", "MEDIUM", "LOW"],
                            "description": "Task priority"
                        },
                        "time_limit": {
                            "type": "string",
                            "description": "Maximum time allowed (e.g., '30 minutes')"
                        }
                    },
                    "required": ["title", "objective"]
                }
            },
            "required": ["session_name", "task_info"]
        }
    ),
    
    mcp_types.Tool(
        name="tmux_check_compliance",
        description="Check agent compliance based on TMUX Bible monitoring rules",
        inputSchema={
            "type": "object",
            "properties": {
                "session_name": {
                    "type": "string",
                    "description": "Name of the tmux session"
                },
                "window": {
                    "type": "string",
                    "description": "Window number (default: '0')"
                }
            },
            "required": ["session_name"]
        }
    ),
    
    mcp_types.Tool(
        name="tmux_create_monitoring_report",
        description="Create comprehensive monitoring report of all agents",
        inputSchema={
            "type": "object",
            "properties": {
                "admin_token": {
                    "type": "string",
                    "description": "Admin token to identify relevant sessions (optional)"
                }
            }
        }
    ),
    
    mcp_types.Tool(
        name="tmux_activate_plan_mode",
        description="Activate Claude's plan mode using TMUX Bible key sequence",
        inputSchema={
            "type": "object",
            "properties": {
                "session_name": {
                    "type": "string",
                    "description": "Name of the tmux session"
                },
                "window": {
                    "type": "string",
                    "description": "Window number (default: '0')"
                }
            },
            "required": ["session_name"]
        }
    ),
    
    mcp_types.Tool(
        name="tmux_emergency_stop",
        description="Send emergency stop signal to an agent (escalation protocol)",
        inputSchema={
            "type": "object",
            "properties": {
                "session_name": {
                    "type": "string",
                    "description": "Name of the tmux session"
                },
                "window": {
                    "type": "string",
                    "description": "Window number (default: '0')"
                }
            },
            "required": ["session_name"]
        }
    ),
    
    mcp_types.Tool(
        name="tmux_enforce_budget_discipline",
        description="Enforce credit budget discipline across agents in a session",
        inputSchema={
            "type": "object",
            "properties": {
                "session_name": {
                    "type": "string",
                    "description": "Name of the tmux session"
                }
            },
            "required": ["session_name"]
        }
    ),
    
    mcp_types.Tool(
        name="tmux_enforce_git_discipline",
        description="Enforce git discipline rules across all windows in a session",
        inputSchema={
            "type": "object",
            "properties": {
                "session_name": {
                    "type": "string",
                    "description": "Name of the tmux session"
                },
                "auto_commit": {
                    "type": "boolean",
                    "description": "Enable automatic commit reminders (default: true)"
                }
            },
            "required": ["session_name"]
        }
    ),
    
    mcp_types.Tool(
        name="tmux_intelligent_window_rename",
        description="Intelligently rename windows based on content following TMUX Bible conventions",
        inputSchema={
            "type": "object",
            "properties": {
                "session_name": {
                    "type": "string",
                    "description": "Name of the tmux session"
                }
            },
            "required": ["session_name"]
        }
    )
]


# Call registration when this module is imported
register_tmux_orchestration_tools()