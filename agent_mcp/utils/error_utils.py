# Agent-MCP Error Handling Utilities
"""
Standardized error handling utilities for the Agent-MCP system.
Provides consistent error handling patterns across all modules.
"""

import logging
import traceback
from typing import Any, Dict, List, Optional, Union
from functools import wraps

from ..core.config import logger
import mcp.types as mcp_types

# Error types for categorization
class AgentMCPError(Exception):
    """Base exception for Agent-MCP specific errors."""
    pass

class AuthenticationError(AgentMCPError):
    """Raised when authentication fails."""
    pass

class DatabaseError(AgentMCPError):
    """Raised when database operations fail."""
    pass

class OpenAIError(AgentMCPError):
    """Raised when OpenAI API operations fail."""
    pass

class ToolExecutionError(AgentMCPError):
    """Raised when tool execution fails."""
    pass

class ValidationError(AgentMCPError):
    """Raised when input validation fails."""
    pass

def handle_tool_errors(func):
    """
    Decorator to standardize error handling in tool implementations.
    
    Usage:
        @handle_tool_errors
        async def my_tool_impl(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
            # Tool implementation
            pass
    """
    @wraps(func)
    async def wrapper(arguments: Dict[str, Any]) -> List[mcp_types.TextContent]:
        try:
            return await func(arguments)
        except AuthenticationError as e:
            logger.warning(f"Authentication error in {func.__name__}: {e}")
            return [mcp_types.TextContent(type="text", text=f"Authentication error: {e}")]
        except ValidationError as e:
            logger.warning(f"Validation error in {func.__name__}: {e}")
            return [mcp_types.TextContent(type="text", text=f"Validation error: {e}")]
        except DatabaseError as e:
            logger.error(f"Database error in {func.__name__}: {e}", exc_info=True)
            return [mcp_types.TextContent(type="text", text=f"Database error: {e}")]
        except OpenAIError as e:
            logger.error(f"OpenAI API error in {func.__name__}: {e}", exc_info=True)
            return [mcp_types.TextContent(type="text", text=f"OpenAI API error: {e}")]
        except ToolExecutionError as e:
            logger.error(f"Tool execution error in {func.__name__}: {e}", exc_info=True)
            return [mcp_types.TextContent(type="text", text=f"Tool execution error: {e}")]
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}", exc_info=True)
            return [mcp_types.TextContent(type="text", text=f"Unexpected error: {e}")]
    
    return wrapper

def validate_required_fields(arguments: Dict[str, Any], required_fields: List[str]) -> None:
    """
    Validate that required fields are present in arguments.
    
    Args:
        arguments: The arguments dictionary to validate
        required_fields: List of required field names
        
    Raises:
        ValidationError: If any required field is missing
    """
    missing_fields = []
    for field in required_fields:
        if field not in arguments or arguments[field] is None:
            missing_fields.append(field)
    
    if missing_fields:
        raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}")

def validate_field_types(arguments: Dict[str, Any], field_types: Dict[str, type]) -> None:
    """
    Validate that fields have the correct types.
    
    Args:
        arguments: The arguments dictionary to validate
        field_types: Dictionary mapping field names to expected types
        
    Raises:
        ValidationError: If any field has incorrect type
    """
    for field, expected_type in field_types.items():
        if field in arguments and arguments[field] is not None:
            if not isinstance(arguments[field], expected_type):
                raise ValidationError(
                    f"Field '{field}' must be of type {expected_type.__name__}, "
                    f"got {type(arguments[field]).__name__}"
                )

def safe_database_operation(operation_name: str):
    """
    Decorator for safe database operations with proper error handling.
    
    Args:
        operation_name: Name of the operation for logging
        
    Returns:
        Decorated function that handles database errors gracefully
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Database operation '{operation_name}' failed: {e}", exc_info=True)
                raise DatabaseError(f"Database operation '{operation_name}' failed: {e}")
        return wrapper
    return decorator

def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """
    Decorator to retry operations on failure.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds
        
    Returns:
        Decorated function with retry logic
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay} seconds..."
                        )
                        import asyncio
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_retries + 1} attempts failed for {func.__name__}: {e}",
                            exc_info=True
                        )
            
            raise last_exception
        
        return wrapper
    return decorator

def log_operation(operation_name: str, include_args: bool = False):
    """
    Decorator to log operation execution.
    
    Args:
        operation_name: Name of the operation to log
        include_args: Whether to include arguments in the log
        
    Returns:
        Decorated function with logging
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            logger.info(f"Starting operation: {operation_name}")
            if include_args and args:
                logger.debug(f"Operation {operation_name} args: {args}")
            
            try:
                result = await func(*args, **kwargs)
                logger.info(f"Completed operation: {operation_name}")
                return result
            except Exception as e:
                logger.error(f"Operation {operation_name} failed: {e}", exc_info=True)
                raise
        return wrapper
    return decorator

def format_error_response(error: Exception, context: str = "") -> str:
    """
    Format an error into a user-friendly response.
    
    Args:
        error: The exception that occurred
        context: Additional context about where the error occurred
        
    Returns:
        Formatted error message
    """
    if isinstance(error, AuthenticationError):
        return f"Authentication failed: {error}"
    elif isinstance(error, ValidationError):
        return f"Invalid input: {error}"
    elif isinstance(error, DatabaseError):
        return f"Database error: {error}"
    elif isinstance(error, OpenAIError):
        return f"OpenAI API error: {error}"
    elif isinstance(error, ToolExecutionError):
        return f"Tool execution error: {error}"
    else:
        return f"Unexpected error: {error}"

def create_error_content(error: Exception, context: str = "") -> List[mcp_types.TextContent]:
    """
    Create a standardized error response for MCP tools.
    
    Args:
        error: The exception that occurred
        context: Additional context about where the error occurred
        
    Returns:
        List containing error message as TextContent
    """
    error_message = format_error_response(error, context)
    return [mcp_types.TextContent(type="text", text=error_message)]
