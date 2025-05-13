import asyncio
import argparse
import logging
import traceback
from mcp_client import interactive_chat

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="MCP RAG Agent using OpenAI API")
    parser.add_argument("--url", default="http://localhost:8038/sse/",
                      help="MCP server URL (default: http://localhost:8038/sse/)")
    parser.add_argument("--token", help="Admin token for MCP server")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        
    # Use provided admin token or prompt for it
    admin_token = args.token
    if not admin_token:
        admin_token = input("Enter your MCP admin token: ")
    
    print(f"Connecting to MCP server at {args.url}")
    try:
        asyncio.run(interactive_chat(args.url, admin_token))
    except KeyboardInterrupt:
        print("\nApplication terminated by user")
    except Exception as e:
        logging.error(f"Application error: {e}")
        if args.debug:
            traceback.print_exc() 