"""
String utility functions for the MCP server.

This module provides various string manipulation functions that can be used 
throughout the MCP server application.
"""


def camel_to_snake_case(camel_string: str) -> str:
    """
    Converts a camelCase string to snake_case.
    
    Args:
        camel_string: The camelCase string to convert.
        
    Returns:
        The converted snake_case string.
        
    Examples:
        >>> camel_to_snake_case("helloWorld")
        'hello_world'
        >>> camel_to_snake_case("HTTPResponse")
        'http_response'
    """
    import re
    # Insert underscore before uppercase letters and convert to lowercase
    snake_case = re.sub(r'(?<!^)(?=[A-Z])', '_', camel_string).lower()
    return snake_case


def snake_to_camel_case(snake_string: str, capitalize_first: bool = False) -> str:
    """
    Converts a snake_case string to camelCase.
    
    Args:
        snake_string: The snake_case string to convert.
        capitalize_first: Whether to capitalize the first letter (PascalCase).
        
    Returns:
        The converted camelCase string.
        
    Examples:
        >>> snake_to_camel_case("hello_world")
        'helloWorld'
        >>> snake_to_camel_case("http_response", capitalize_first=True)
        'HttpResponse'
    """
    # Split the string by underscores
    components = snake_string.split('_')
    
    # Capitalize each component except the first one (unless capitalize_first=True)
    if capitalize_first:
        return ''.join(x.title() for x in components)
    else:
        return components[0] + ''.join(x.title() for x in components[1:])


def truncate_string(text: str, max_length: int, ellipsis: str = '...') -> str:
    """
    Truncates a string to a specified length with optional ellipsis.
    
    Args:
        text: The string to truncate.
        max_length: The maximum length of the string.
        ellipsis: The string to append if truncation occurs. Defaults to '...'.
        
    Returns:
        The truncated string.
        
    Examples:
        >>> truncate_string("This is a long string", 10)
        'This is a...'
        >>> truncate_string("Short", 10)
        'Short'
    """
    if len(text) <= max_length:
        return text
    
    # Calculate truncation point to accommodate ellipsis
    truncate_at = max_length - len(ellipsis)
    return text[:truncate_at] + ellipsis 