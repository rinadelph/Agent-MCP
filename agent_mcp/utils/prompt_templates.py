# Agent-MCP/agent_mcp/utils/prompt_templates.py
from typing import Dict, Optional, Any
from ..core.config import logger


# Predefined prompt templates for different agent types
PROMPT_TEMPLATES = {
    "worker_with_rag": """This is your agent token: {agent_token} Ask the project RAG agent at least 5-7 questions to understand what you need to do. I want you to critically think when asking a question, then criticize yourself before asking that question. How you criticize yourself is by proposing an idea, criticizing it, and based on that criticism you pull through with that idea. It's better to add too much context versus too little. Add all these context entries to the agent mcp. ACT AUTO --worker --memory""",
    "basic_worker": """You are {agent_id} worker agent.
Your Agent Token: {agent_token}

Query the project knowledge graph to understand:
1. Overall system architecture
2. Your specific responsibilities
3. Integration points with other components
4. Coding standards and patterns to follow
5. Current implementation status

Begin implementation following the established patterns.

AUTO --worker --memory""",
    "frontend_worker": """You are {agent_id} frontend worker agent.
Your Admin Token: {agent_token}

Query the project knowledge graph to understand:
1. UI/UX requirements and design system
2. Frontend architecture and component structure
3. State management patterns
4. Integration with backend APIs
5. Testing and validation requirements

Focus on component-based development with visual validation.

AUTO --worker --playwright""",
    "admin_agent": """You are the admin agent.
Admin Token: {admin_token}

Your role is to:
- Coordinate all development work
- Create and manage worker agents
- Maintain project context
- Assign tasks based on agent specializations

Query the project RAG for current status and begin coordination.""",
    "custom": "{custom_prompt}",
}


def get_prompt_template(template_name: str) -> Optional[str]:
    """Get a prompt template by name."""
    return PROMPT_TEMPLATES.get(template_name)


def format_prompt(template_name: str, **kwargs) -> Optional[str]:
    """
    Format a prompt template with the provided variables.

    Args:
        template_name: Name of the template to use
        **kwargs: Variables to substitute in the template

    Returns:
        Formatted prompt string or None if template not found
    """
    template = get_prompt_template(template_name)
    if not template:
        logger.error(f"Prompt template '{template_name}' not found")
        return None

    try:
        return template.format(**kwargs)
    except KeyError as e:
        logger.error(f"Missing required variable {e} for template '{template_name}'")
        return None
    except Exception as e:
        logger.error(f"Error formatting template '{template_name}': {e}")
        return None


def create_custom_prompt(prompt_text: str, **kwargs) -> str:
    """
    Create a custom prompt with variable substitution.

    Args:
        prompt_text: The custom prompt text
        **kwargs: Variables to substitute

    Returns:
        Formatted custom prompt
    """
    try:
        return prompt_text.format(**kwargs)
    except Exception as e:
        logger.warning(f"Error formatting custom prompt: {e}, returning as-is")
        return prompt_text


def get_available_templates() -> Dict[str, str]:
    """Get all available prompt templates with descriptions."""
    descriptions = {
        "worker_with_rag": "Worker agent with RAG querying and critical thinking instructions",
        "basic_worker": "Standard worker agent with basic project querying",
        "frontend_worker": "Frontend-focused worker with UI/UX emphasis",
        "admin_agent": "Admin agent for coordination and management",
        "custom": "Custom prompt template (requires custom_prompt parameter)",
    }
    return descriptions


def validate_template_variables(template_name: str, variables: Dict[str, Any]) -> bool:
    """
    Validate that all required variables are provided for a template.

    Args:
        template_name: Name of the template to validate
        variables: Dictionary of variables to check

    Returns:
        True if all required variables are present, False otherwise
    """
    template = get_prompt_template(template_name)
    if not template:
        return False

    # Extract variable names from template
    import re

    required_vars = set(re.findall(r"\{(\w+)\}", template))
    provided_vars = set(variables.keys())

    missing_vars = required_vars - provided_vars
    if missing_vars:
        logger.error(
            f"Missing required variables for template '{template_name}': {missing_vars}"
        )
        return False

    return True


def build_agent_prompt(
    agent_id: str,
    agent_token: str,
    admin_token: str,
    template_name: str = "basic_worker",
    custom_prompt: str = None,
    **extra_vars,
) -> Optional[str]:
    """
    Build a complete agent prompt with all necessary information.

    Args:
        agent_id: The agent's ID
        agent_token: The agent's token
        admin_token: The admin token
        template_name: Name of the template to use
        custom_prompt: Custom prompt text (for custom template)
        **extra_vars: Additional variables for template substitution

    Returns:
        Complete formatted prompt or None if error
    """
    # Prepare base variables
    variables = {
        "agent_id": agent_id,
        "agent_token": agent_token,
        "admin_token": admin_token,
        **extra_vars,
    }

    # Handle custom template
    if template_name == "custom" and custom_prompt:
        variables["custom_prompt"] = custom_prompt

    # Validate and format
    if not validate_template_variables(template_name, variables):
        return None

    return format_prompt(template_name, **variables)
