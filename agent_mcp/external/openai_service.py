# Agent-MCP/mcp_template/mcp_server_src/external/openai_service.py
import os
import sys # For sys.exit in case of critical failure during initialization (optional)
from typing import Optional # Added import for Optional

# Import OpenAI library.
# It's good practice to handle potential ImportError if it's an optional dependency,
# though for this project, it seems to be a core requirement.
try:
    import openai
except ImportError:
    # If openai library is not installed, log an error and make client None.
    # The application might still run if RAG/OpenAI features are optional
    # and guarded by checks for a valid client.
    from ..core.config import logger as temp_logger # Use temp logger if config not fully up
    temp_logger.error("OpenAI Python library not found. Please install it using 'pip install openai'. OpenAI dependent features will be unavailable.")
    openai = None # Make openai None so subsequent checks fail gracefully

# Import configurations and global variables
from ..core.config import logger, OPENAI_API_KEY_ENV # OPENAI_API_KEY_ENV from config
from ..core import globals as g # To store the client instance if needed globally

# The openai_client instance will be stored in g.openai_client_instance
# g.openai_client_instance: Optional[openai.OpenAI] = None # This is defined in globals.py

# Original location: main.py lines 173-177 (API key check)
# Original location: main.py lines 187-197 (get_openai_client function)

def initialize_openai_client() -> bool:
    """
    Initializes the async OpenAI API client.
    Sets the global `g.openai_async_client_instance`.
    Since this is an async MCP server, we only need async clients.
    Returns True if successful, False otherwise.
    This function should be called once at application startup.
    """
    if g.openai_async_client_instance is not None:
        logger.info("OpenAI async client already initialized.")
        return True

    if openai is None: # Check if the library import failed
        logger.error("OpenAI library failed to import. Cannot initialize client.")
        return False

    if not OPENAI_API_KEY_ENV: # Check from config.py, which got it from os.environ
        logger.error("OPENAI_API_KEY not found in environment variables. Cannot initialize OpenAI client.")
        # Do not print to console - just log to file
        return False

    logger.info("Initializing OpenAI async client...")
    try:
        # Create the async OpenAI client instance
        async_client = openai.AsyncOpenAI(api_key=OPENAI_API_KEY_ENV)

        # We can't test the async client with a synchronous call here,
        # but we'll trust that if the API key is valid, it will work
        # The first actual API call will reveal any authentication issues

        logger.info("OpenAI async client initialized successfully.")
        g.openai_async_client_instance = async_client # Store the async client in globals
        
        # Clear the sync client to ensure it's not used
        g.openai_client_instance = None
        
        return True
    except Exception as e: # Catch any initialization errors
        logger.error(f"Failed to initialize OpenAI async client: {e}", exc_info=True)
        g.openai_async_client_instance = None
        g.openai_client_instance = None

    return False

def get_openai_client() -> Optional[openai.OpenAI]:
    """
    DEPRECATED: This function is kept for backward compatibility but should not be used.
    Use get_openai_async_client() instead for all OpenAI operations.
    Always returns None to prevent synchronous client usage in async contexts.
    """
    logger.warning("get_openai_client() is deprecated. Use get_openai_async_client() instead.")
    return None

def get_openai_async_client() -> Optional['openai.AsyncOpenAI']:
    """
    Returns the globally initialized async OpenAI client instance.
    If the client is not initialized, it attempts to initialize it.
    This should be used in async contexts to avoid blocking the event loop.
    """
    if g.openai_async_client_instance is None:
        logger.info("OpenAI async client not yet initialized. Attempting initialization now.")
        initialize_openai_client() # This will initialize both sync and async clients

    if g.openai_async_client_instance is None:
        logger.warning("OpenAI async client is not available (initialization might have failed).")

    return g.openai_async_client_instance

# Any other OpenAI specific helper functions that don't belong in RAG or tools
# could go here. For example, if you had a generic text generation or embedding
# function used by multiple parts of the system outside of the RAG context.
# For now, client initialization and access are the main concerns.

# Example of how this is intended to be used at startup:
# In server_lifecycle.py or cli.py:
# from mcp_server_src.external.openai_service import initialize_openai_client
# initialize_openai_client()
#
# Then, in other modules (e.g., RAG indexing, RAG tool):
# from mcp_server_src.external.openai_service import get_openai_client
# client = get_openai_client()
# if client:
#     # Use the client
# else:
#     # Handle OpenAI unavailability