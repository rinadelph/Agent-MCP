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

def initialize_openai_client() -> Optional[openai.OpenAI]:
    """
    Initializes and returns the OpenAI API client.
    Sets the global `g.openai_client_instance`.
    If initialization fails, `g.openai_client_instance` remains None and this function returns None.
    This function should be called once at application startup.
    """
    if g.openai_client_instance is not None:
        logger.info("OpenAI client already initialized.")
        return g.openai_client_instance

    if openai is None: # Check if the library import failed
        logger.error("OpenAI library failed to import. Cannot initialize client.")
        return None

    if not OPENAI_API_KEY_ENV: # Check from config.py, which got it from os.environ
        logger.error("OPENAI_API_KEY not found in environment variables. Cannot initialize OpenAI client.")
        # The original main.py:177 did a sys.exit(1).
        # We can replicate this critical failure or allow the server to start without OpenAI features.
        # For now, let's log and return None, features using OpenAI should check client availability.
        # If strict: sys.exit("CRITICAL: OPENAI_API_KEY is not set. Exiting.")
        return None

    logger.info("Initializing OpenAI client...")
    try:
        # Create the OpenAI client instance
        # Original main.py:191
        client = openai.OpenAI(api_key=OPENAI_API_KEY_ENV)

        # Test the connection by making a simple, low-cost API call
        # Original main.py:193 (client.models.list())
        client.models.list() # This call verifies API key and connectivity.

        logger.info("OpenAI client initialized and connection tested successfully.")
        g.openai_client_instance = client # Store the initialized client in globals
        return client
    except openai.AuthenticationError as e:
        logger.error(f"OpenAI Authentication Error: Invalid API key or organization ID. Please check your credentials. Details: {e}")
        g.openai_client_instance = None
    except openai.APIConnectionError as e:
        logger.error(f"OpenAI API Connection Error: Could not connect to OpenAI. Check your network settings and OpenAI's status page. Details: {e}")
        g.openai_client_instance = None
    except openai.RateLimitError as e:
        logger.error(f"OpenAI Rate Limit Error: You have exceeded your API quota or rate limit. Details: {e}")
        g.openai_client_instance = None
    except openai.APIError as e: # Catch other OpenAI API specific errors
        logger.error(f"OpenAI API Error during client initialization: {e}", exc_info=True)
        g.openai_client_instance = None
    except Exception as e: # Catch any other unexpected errors
        logger.error(f"Failed to initialize OpenAI client due to an unexpected error: {e}", exc_info=True)
        g.openai_client_instance = None

    return None # Return None if initialization failed

def get_openai_client() -> Optional[openai.OpenAI]:
    """
    Returns the globally initialized OpenAI client instance.
    If the client is not initialized, it attempts to initialize it.
    """
    if g.openai_client_instance is None:
        logger.info("OpenAI client not yet initialized. Attempting initialization now.")
        initialize_openai_client() # Attempt to initialize if not already done.

    if g.openai_client_instance is None:
        logger.warning("OpenAI client is not available (initialization might have failed).")

    return g.openai_client_instance

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