# Agent-MCP/mcp_template/mcp_server_src/utils/json_utils.py
import json
import re
from typing import Any, Union, Dict, List

# Import the centrally configured logger
from ..core.config import logger
# For Starlette Request type hint, if you want to be very specific,
# you'd import it, but 'Any' is fine for now if Starlette isn't a direct dependency here.
# from starlette.requests import Request # Example

# --- JSON Sanitization Utility ---
# Original location: main.py lines 52-123
def sanitize_json_input(input_data: Union[str, bytes, Dict, List, Any]) -> Union[Dict, List, Any]: # Added bytes to input_data
    """
    Sanitize JSON input aggressively to handle hidden Unicode characters,
    misplaced whitespace, and line breaks.

    Args:
        input_data: Can be a string, bytes (from request.body()),
                    or a Python object (dict, list).

    Returns:
        Properly parsed Python object (dict, list, etc.)
    """
    # If already a Python object (dict/list), just return it
    if isinstance(input_data, (dict, list)):
        return input_data

    # If bytes, decode to string first
    if isinstance(input_data, bytes):
        try:
            input_data_str = input_data.decode('utf-8')
        except UnicodeDecodeError:
            logger.warning("Failed to decode input data as UTF-8, trying latin-1.")
            try:
                input_data_str = input_data.decode('latin-1')
            except UnicodeDecodeError as ude:
                logger.error(f"Could not decode input bytes: {ude}")
                raise ValueError(f"Invalid input bytes encoding: {ude}")
    elif isinstance(input_data, str):
        input_data_str = input_data
    else:
        # If not string or bytes, try to convert to string
        try:
            input_data_str = str(input_data)
        except Exception as e:
            logger.error(f"Failed to convert input to string: {e}")
            raise ValueError(f"Input must be a JSON string, bytes, or Python object, got {type(input_data)}")

    # Step 1: Initial direct parse attempt
    try:
        return json.loads(input_data_str)
    except json.JSONDecodeError:
        pass # Continue cleaning if direct parse fails

    # Step 2: Aggressive Whitespace Removal (Handles CR/LF/Spaces between elements)
    # Remove whitespace after opening braces/brackets
    cleaned = re.sub(r'([\{\[])\s+', r'\1', input_data_str)
    # Remove whitespace before closing braces/brackets
    cleaned = re.sub(r'\s+([\}\]])', r'\1', cleaned)
    # Remove whitespace after commas and colons
    cleaned = re.sub(r'([:,])\s+', r'\1', cleaned)
    # Remove whitespace before commas
    cleaned = re.sub(r'\s+(,)', r'\1', cleaned)
    # Remove line breaks that might be separating elements
    cleaned = cleaned.replace('\r\n', '').replace('\n', '').replace('\r', '')

    # Step 3: Remove Control Characters (excluding tab \t)
    # Using repr() to make them visible for regex, then stripping quotes.
    cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', cleaned)

    # Step 4: Remove problematic Unicode (Zero-width spaces, BOM, line/paragraph separators)
    cleaned = re.sub(r'[\u200B-\u200F\uFEFF\u2028\u2029]', '', cleaned)

    # Step 5: Try parsing the aggressively cleaned string
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e_cleaned:
        # Step 6: Fallback for potentially nested/escaped JSON or other oddities
        try:
            # Try to find the main JSON object/array within the string
            match = re.search(r'^\s*(\{.*\}|\[.*\])\s*$', cleaned, re.DOTALL)
            if match:
                return json.loads(match.group(1))
        except json.JSONDecodeError:
             pass # If even the extracted part fails, fall through
        except Exception as inner_e:
             logger.warning(f"Inner regex/parse fallback failed during sanitization: {inner_e}")
             pass

        # Log the final failure state for debugging
        error_excerpt = cleaned[:100] + ('...' if len(cleaned) > 100 else '')
        logger.error(f"Aggressive JSON parsing failed: {e_cleaned}, cleaned data (excerpt): {error_excerpt}")
        raise ValueError(f"Failed to parse JSON even after aggressive sanitization: {e_cleaned}")

# Helper function for API request handling
# Original location: main.py lines 126-143
async def get_sanitized_json_body(request: Any) -> Union[Dict, List, Any]: # 'request: Request' if Starlette is imported
    """
    Helper function to safely get and sanitize a JSON request body.
    Assumes 'request' is a Starlette Request object or similar with an awaitable .body() method.

    Args:
        request: The Starlette request object (or any object with awaitable .body())

    Returns:
        The sanitized JSON data as a Python object

    Raises:
        ValueError: If the request body is not valid JSON or cannot be processed.
    """
    try:
        # Get the raw body data
        raw_body = await request.body() # This is usually bytes

        # Sanitize and parse it (sanitize_json_input now handles bytes decoding)
        return sanitize_json_input(raw_body)
    except ValueError as ve: # Catch ValueError from sanitize_json_input or body decoding
        logger.error(f"Failed to get/sanitize request body: {ve}")
        raise ValueError(f"Invalid request body: {ve}") # Re-raise with context
    except Exception as e:
        # Catching other potential exceptions from request.body() or unexpected issues
        logger.error(f"Unexpected error processing request body: {e}", exc_info=True)
        raise ValueError(f"Error processing request body: {e}")

# --- End JSON Sanitization Utility ---