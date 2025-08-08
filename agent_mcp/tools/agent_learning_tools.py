# Agent-MCP Agent Learning Tools
"""
Tools for integrating the agent learning and adaptation system with
learning, specialization training, collaboration protocols, and performance optimization.
"""

import json
from typing import List, Dict, Any, Optional
import mcp.types as mcp_types

from .registry import register_tool
from ..core.config import logger
from ..core import globals as g
from ..core.auth import verify_token, get_agent_id
from ..utils.audit_utils import log_audit
from ..features.agent_learning import (
    agent_learning_system,
    LearningType,
    SpecializationType,
    CollaborationProtocol
)


async def record_learning_experience_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    """
    Record a learning experience for an agent.
    
    Args:
        token: Authentication token
        agent_id: ID of the agent
        task_type: Type of task performed
        input_data: Input data for the task
        output_data: Output data from the task
        feedback_score: Feedback score (0.0 to 1.0)
        learning_type: Type of learning (supervised, reinforcement, unsupervised, transfer, meta)
        specialization: Optional specialization type
    """
    token = arguments.get("token")
    agent_id = arguments.get("agent_id")
    task_type = arguments.get("task_type")
    input_data = arguments.get("input_data", {})
    output_data = arguments.get("output_data", {})
    feedback_score = arguments.get("feedback_score", 0.8)
    learning_type_str = arguments.get("learning_type", "supervised")
    specialization_str = arguments.get("specialization")
    
    # Authentication
    requesting_agent_id = get_agent_id(token)
    if not requesting_agent_id:
        return [mcp_types.TextContent(type="text", text="Unauthorized: Valid token required")]
    
    # Validation
    if not agent_id or not task_type:
        return [mcp_types.TextContent(type="text", text="Error: agent_id and task_type are required")]
    
    if not 0.0 <= feedback_score <= 1.0:
        return [mcp_types.TextContent(type="text", text="Error: feedback_score must be between 0.0 and 1.0")]
    
    try:
        # Convert learning type string to enum
        learning_type = LearningType[learning_type_str.upper()]
    except KeyError:
        return [mcp_types.TextContent(type="text", text=f"Error: Invalid learning type '{learning_type_str}'")]
    
    # Convert specialization string to enum if provided
    specialization = None
    if specialization_str:
        try:
            specialization = SpecializationType[specialization_str.upper()]
        except KeyError:
            return [mcp_types.TextContent(type="text", text=f"Error: Invalid specialization type '{specialization_str}'")]
    
    try:
        # Record learning experience
        experience_id = await agent_learning_system.record_learning_experience(
            agent_id=agent_id,
            task_type=task_type,
            input_data=input_data,
            output_data=output_data,
            feedback_score=feedback_score,
            learning_type=learning_type,
            specialization=specialization
        )
        
        # Log audit
        log_audit(requesting_agent_id, "record_learning_experience", {
            "target_agent_id": agent_id,
            "task_type": task_type,
            "feedback_score": feedback_score,
            "learning_type": learning_type_str,
            "specialization": specialization_str,
            "experience_id": experience_id
        })
        
        return [mcp_types.TextContent(type="text", text=f"Learning experience recorded successfully. Experience ID: {experience_id}")]
        
    except Exception as e:
        logger.error(f"Error recording learning experience: {e}")
        return [mcp_types.TextContent(type="text", text=f"Error recording learning experience: {str(e)}")]


async def train_specialization_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    """
    Train an agent for a specific specialization.
    
    Args:
        token: Authentication token
        agent_id: ID of the agent to train
        specialization_type: Type of specialization to train
        training_data: Training data for the specialization
    """
    token = arguments.get("token")
    agent_id = arguments.get("agent_id")
    specialization_type_str = arguments.get("specialization_type")
    training_data = arguments.get("training_data", [])
    
    # Authentication
    requesting_agent_id = get_agent_id(token)
    if not requesting_agent_id:
        return [mcp_types.TextContent(type="text", text="Unauthorized: Valid token required")]
    
    # Validation
    if not agent_id or not specialization_type_str:
        return [mcp_types.TextContent(type="text", text="Error: agent_id and specialization_type are required")]
    
    try:
        # Convert specialization type string to enum
        specialization_type = SpecializationType[specialization_type_str.upper()]
    except KeyError:
        return [mcp_types.TextContent(type="text", text=f"Error: Invalid specialization type '{specialization_type_str}'")]
    
    try:
        # Train specialization
        success = await agent_learning_system.train_specialization(
            agent_id=agent_id,
            specialization_type=specialization_type,
            training_data=training_data
        )
        
        if success:
            # Log audit
            log_audit(requesting_agent_id, "train_specialization", {
                "target_agent_id": agent_id,
                "specialization_type": specialization_type_str,
                "training_data_count": len(training_data)
            })
            
            return [mcp_types.TextContent(type="text", text=f"Successfully trained agent {agent_id} for {specialization_type_str} specialization")]
        else:
            return [mcp_types.TextContent(type="text", text=f"Failed to train agent {agent_id} for {specialization_type_str} specialization")]
        
    except Exception as e:
        logger.error(f"Error training specialization: {e}")
        return [mcp_types.TextContent(type="text", text=f"Error training specialization: {str(e)}")]


async def create_collaboration_session_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    """
    Create a collaboration session between agents.
    
    Args:
        token: Authentication token
        protocol: Collaboration protocol to use
        participants: List of agent IDs participating
        task_description: Description of the collaborative task
        roles: Optional role assignments for participants
    """
    token = arguments.get("token")
    protocol_str = arguments.get("protocol")
    participants = arguments.get("participants", [])
    task_description = arguments.get("task_description")
    roles = arguments.get("roles", {})
    
    # Authentication
    requesting_agent_id = get_agent_id(token)
    if not requesting_agent_id:
        return [mcp_types.TextContent(type="text", text="Unauthorized: Valid token required")]
    
    # Validation
    if not protocol_str or not participants or not task_description:
        return [mcp_types.TextContent(type="text", text="Error: protocol, participants, and task_description are required")]
    
    try:
        # Convert protocol string to enum
        protocol = CollaborationProtocol[protocol_str.upper()]
    except KeyError:
        return [mcp_types.TextContent(type="text", text=f"Error: Invalid protocol '{protocol_str}'")]
    
    try:
        # Create collaboration session
        session_id = await agent_learning_system.create_collaboration_session(
            protocol=protocol,
            participants=participants,
            task_description=task_description,
            roles=roles if roles else None
        )
        
        # Log audit
        log_audit(requesting_agent_id, "create_collaboration_session", {
            "protocol": protocol_str,
            "participants": participants,
            "task_description": task_description,
            "session_id": session_id
        })
        
        return [mcp_types.TextContent(type="text", text=f"Collaboration session created successfully. Session ID: {session_id}")]
        
    except Exception as e:
        logger.error(f"Error creating collaboration session: {e}")
        return [mcp_types.TextContent(type="text", text=f"Error creating collaboration session: {str(e)}")]


async def execute_collaboration_protocol_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    """
    Execute a collaboration protocol for a session.
    
    Args:
        token: Authentication token
        session_id: ID of the collaboration session
        task_data: Data for the collaborative task
    """
    token = arguments.get("token")
    session_id = arguments.get("session_id")
    task_data = arguments.get("task_data", {})
    
    # Authentication
    requesting_agent_id = get_agent_id(token)
    if not requesting_agent_id:
        return [mcp_types.TextContent(type="text", text="Unauthorized: Valid token required")]
    
    # Validation
    if not session_id:
        return [mcp_types.TextContent(type="text", text="Error: session_id is required")]
    
    try:
        # Execute collaboration protocol
        results = await agent_learning_system.execute_collaboration_protocol(
            session_id=session_id,
            task_data=task_data
        )
        
        # Log audit
        log_audit(requesting_agent_id, "execute_collaboration_protocol", {
            "session_id": session_id,
            "task_data_keys": list(task_data.keys()),
            "results_keys": list(results.keys())
        })
        
        # Return collaboration results
        return [mcp_types.TextContent(type="text", text=json.dumps(results, indent=2))]
        
    except Exception as e:
        logger.error(f"Error executing collaboration protocol: {e}")
        return [mcp_types.TextContent(type="text", text=f"Error executing collaboration protocol: {str(e)}")]


async def optimize_agent_performance_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    """
    Optimize agent performance based on learning data.
    
    Args:
        token: Authentication token
        agent_id: ID of the agent to optimize
    """
    token = arguments.get("token")
    agent_id = arguments.get("agent_id")
    
    # Authentication
    requesting_agent_id = get_agent_id(token)
    if not requesting_agent_id:
        return [mcp_types.TextContent(type="text", text="Unauthorized: Valid token required")]
    
    # Validation
    if not agent_id:
        return [mcp_types.TextContent(type="text", text="Error: agent_id is required")]
    
    try:
        # Optimize agent performance
        optimization_results = await agent_learning_system.optimize_agent_performance(agent_id)
        
        # Log audit
        log_audit(requesting_agent_id, "optimize_agent_performance", {
            "target_agent_id": agent_id,
            "optimization_keys": list(optimization_results.keys())
        })
        
        # Return optimization results
        return [mcp_types.TextContent(type="text", text=json.dumps(optimization_results, indent=2))]
        
    except Exception as e:
        logger.error(f"Error optimizing agent performance: {e}")
        return [mcp_types.TextContent(type="text", text=f"Error optimizing agent performance: {str(e)}")]


async def get_agent_learning_summary_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
    """
    Get a summary of agent's learning progress.
    
    Args:
        token: Authentication token
        agent_id: ID of the agent
    """
    token = arguments.get("token")
    agent_id = arguments.get("agent_id")
    
    # Authentication
    requesting_agent_id = get_agent_id(token)
    if not requesting_agent_id:
        return [mcp_types.TextContent(type="text", text="Unauthorized: Valid token required")]
    
    # Validation
    if not agent_id:
        return [mcp_types.TextContent(type="text", text="Error: agent_id is required")]
    
    try:
        # Get learning summary
        summary = agent_learning_system.get_agent_learning_summary(agent_id)
        
        # Log audit
        log_audit(requesting_agent_id, "get_agent_learning_summary", {
            "target_agent_id": agent_id,
            "summary_keys": list(summary.keys())
        })
        
        # Return learning summary
        return [mcp_types.TextContent(type="text", text=json.dumps(summary, indent=2))]
        
    except Exception as e:
        logger.error(f"Error getting agent learning summary: {e}")
        return [mcp_types.TextContent(type="text", text=f"Error getting learning summary: {str(e)}")]


def register_agent_learning_tools():
    """Register all agent learning tools."""
    
    # Record Learning Experience Tool
    register_tool(
        name="record_learning_experience",
        description="Record a learning experience for an agent with feedback and specialization tracking.",
        input_schema={
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "Authentication token"},
                "agent_id": {"type": "string", "description": "ID of the agent"},
                "task_type": {"type": "string", "description": "Type of task performed"},
                "input_data": {
                    "type": "object",
                    "description": "Input data for the task"
                },
                "output_data": {
                    "type": "object",
                    "description": "Output data from the task"
                },
                "feedback_score": {
                    "type": "number",
                    "description": "Feedback score (0.0 to 1.0)",
                    "default": 0.8
                },
                "learning_type": {
                    "type": "string",
                    "enum": ["supervised", "reinforcement", "unsupervised", "transfer", "meta"],
                    "description": "Type of learning",
                    "default": "supervised"
                },
                "specialization": {
                    "type": "string",
                    "enum": ["code_review", "debugging", "documentation", "testing", "architecture", "security", "performance", "ui_ux", "data_analysis", "general"],
                    "description": "Optional specialization type"
                }
            },
            "required": ["token", "agent_id", "task_type"],
            "additionalProperties": False
        },
        implementation=record_learning_experience_tool_impl
    )
    
    # Train Specialization Tool
    register_tool(
        name="train_specialization",
        description="Train an agent for a specific specialization using provided training data.",
        input_schema={
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "Authentication token"},
                "agent_id": {"type": "string", "description": "ID of the agent to train"},
                "specialization_type": {
                    "type": "string",
                    "enum": ["code_review", "debugging", "documentation", "testing", "architecture", "security", "performance", "ui_ux", "data_analysis", "general"],
                    "description": "Type of specialization to train"
                },
                "training_data": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Training data for the specialization"
                }
            },
            "required": ["token", "agent_id", "specialization_type"],
            "additionalProperties": False
        },
        implementation=train_specialization_tool_impl
    )
    
    # Create Collaboration Session Tool
    register_tool(
        name="create_collaboration_session",
        description="Create a collaboration session between agents with specified protocol and roles.",
        input_schema={
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "Authentication token"},
                "protocol": {
                    "type": "string",
                    "enum": ["hierarchical", "peer_to_peer", "swarm", "master_worker", "consensus"],
                    "description": "Collaboration protocol to use"
                },
                "participants": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of agent IDs participating"
                },
                "task_description": {
                    "type": "string",
                    "description": "Description of the collaborative task"
                },
                "roles": {
                    "type": "object",
                    "description": "Optional role assignments for participants"
                }
            },
            "required": ["token", "protocol", "participants", "task_description"],
            "additionalProperties": False
        },
        implementation=create_collaboration_session_tool_impl
    )
    
    # Execute Collaboration Protocol Tool
    register_tool(
        name="execute_collaboration_protocol",
        description="Execute a collaboration protocol for a session with task data.",
        input_schema={
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "Authentication token"},
                "session_id": {"type": "string", "description": "ID of the collaboration session"},
                "task_data": {
                    "type": "object",
                    "description": "Data for the collaborative task"
                }
            },
            "required": ["token", "session_id"],
            "additionalProperties": False
        },
        implementation=execute_collaboration_protocol_tool_impl
    )
    
    # Optimize Agent Performance Tool
    register_tool(
        name="optimize_agent_performance",
        description="Optimize agent performance based on learning data and provide recommendations.",
        input_schema={
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "Authentication token"},
                "agent_id": {"type": "string", "description": "ID of the agent to optimize"}
            },
            "required": ["token", "agent_id"],
            "additionalProperties": False
        },
        implementation=optimize_agent_performance_tool_impl
    )
    
    # Get Agent Learning Summary Tool
    register_tool(
        name="get_agent_learning_summary",
        description="Get a comprehensive summary of agent's learning progress, specializations, and collaboration history.",
        input_schema={
            "type": "object",
            "properties": {
                "token": {"type": "string", "description": "Authentication token"},
                "agent_id": {"type": "string", "description": "ID of the agent"}
            },
            "required": ["token", "agent_id"],
            "additionalProperties": False
        },
        implementation=get_agent_learning_summary_tool_impl
    )


# Register tools when module is imported
register_agent_learning_tools()
