# Load environment variables as the very first thing
import os
from pathlib import Path
from dotenv import load_dotenv

# Find and load .env file from project root
current_file = Path(__file__).resolve()
project_root = current_file.parent.parent  # Go up to Agent-MCP directory
env_file = project_root / '.env'

print(f"Looking for .env at: {env_file}")
if env_file.exists():
    print(f"Loading .env from: {env_file}")
    load_dotenv(dotenv_path=str(env_file))
    print(f"OPENAI_API_KEY in environment: {os.environ.get('OPENAI_API_KEY', 'NOT FOUND')[:20]}...")
else:
    print(f"No .env file found at {env_file}")
    load_dotenv()  # Try default locations

# Now import and run the CLI
from .cli import main_cli

if __name__ == "__main__":
    main_cli()