# Load environment variables as the very first thing
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Enable verbose logging from the start
import logging
# Check if we're running without arguments (UI mode)
ui_mode = len(sys.argv) == 1 or (len(sys.argv) == 2 and sys.argv[1] in ['--help', '-h'])
handlers = [logging.FileHandler('agent_mcp_debug.log', mode='a')]
if not ui_mode:
    # Only add console handler if not in UI mode
    handlers.append(logging.StreamHandler(sys.stdout))

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s - %(filename)s:%(lineno)d - %(funcName)s() - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=handlers
)

logger = logging.getLogger(__name__)
logger.info("=" * 80)
logger.info("AGENT-MCP STARTING - VERBOSE LOGGING ENABLED")
logger.info("=" * 80)
logger.info(f"Python version: {sys.version}")
logger.info(f"Current working directory: {os.getcwd()}")
logger.info(f"__file__: {__file__}")

# Find and load .env file from project root
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent  # Go up to Agent-MCP directory
env_file = project_root / '.env'

if not ui_mode:
    print(f"Looking for .env at: {env_file}")
logger.info(f"Looking for .env at: {env_file}")
if env_file.exists():
    if not ui_mode:
        print(f"Loading .env from: {env_file}")
    logger.info(f"Loading .env from: {env_file}")
    load_dotenv(dotenv_path=str(env_file))
    api_key = os.environ.get('OPENAI_API_KEY', 'NOT FOUND')
    if not ui_mode:
        print(f"OPENAI_API_KEY in environment: {api_key[:20]}...")
    logger.info(f"OPENAI_API_KEY in environment: {api_key[:20]}..." if api_key != 'NOT FOUND' else "OPENAI_API_KEY not found in environment")
else:
    if not ui_mode:
        print(f"No .env file found at {env_file}")
    logger.warning(f"No .env file found at {env_file}")
    load_dotenv()  # Try default locations
    logger.info("Loaded .env from default locations")

# Log all environment variables (be careful with sensitive data)
logger.debug("Environment variables related to MCP:")
for key, value in os.environ.items():
    if 'MCP' in key or 'OPENAI' in key:
        if 'KEY' in key or 'TOKEN' in key:
            logger.debug(f"  {key}: {value[:10]}..." if value else f"  {key}: None")
        else:
            logger.debug(f"  {key}: {value}")

# Now import and run the CLI
logger.info("Importing CLI module...")
from .cli_main import main

if __name__ == "__main__":
    logger.info("Running main() from cli_main")
    try:
        main()
    except Exception as e:
        logger.exception(f"Fatal error in main: {e}")
        raise