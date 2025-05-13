import os
import sys
import json
import logging
import asyncio
import argparse
import uuid
from functools import partial
import httpx
import time
import re
from urllib.parse import urljoin
from typing import Dict, Any, Optional, List, Tuple
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get API key from environment variables
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logger.error("OPENAI_API_KEY not found in environment variables. Please set it in your .env file.")
    print("ERROR: OPENAI_API_KEY not found in environment variables. Please set it in your .env file.")
    sys.exit(1)

# OpenAI client setup - using direct API calls
from openai import OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)


class MCPClient:
    """Client for interacting with MCP server using SSE protocol"""
    
    def __init__(self, url, admin_token):
        # Convert messages URL to SSE URL if needed
        self.url = url.replace('/messages/', '/sse/') if '/messages/' in url else url
        if not self.url.endswith('/sse'):
            self.url = urljoin(self.url, '/sse')
        
        self.admin_token = admin_token
        self.tools_cache = None
        self.client_id = f"rag_agent_{uuid.uuid4().hex[:8]}"
        self.pending_requests = {}
        self.sse_client = None
        self.sse_task = None
        logger.info(f"Created MCP client with client ID: {self.client_id}")
    
    async def connect_sse(self):
        """Establish connection to SSE endpoint"""
        if self.sse_client:
            return

        self.sse_client = httpx.AsyncClient(timeout=None)  # No timeout for SSE connection
        
        # Start SSE listener task
        self.sse_task = asyncio.create_task(self._listen_sse())
        
        # Give the task a moment to start
        await asyncio.sleep(0.5)
    
    async def _listen_sse(self):
        """Listen for SSE events from the server"""
        logger.info(f"Connecting to SSE endpoint: {self.url}?clientId={self.client_id}")
        
        try:
            async with self.sse_client.stream(
                "GET", 
                f"{self.url}?clientId={self.client_id}",
                headers={"Accept": "text/event-stream"}
            ) as response:
                if response.status_code != 200:
                    logger.error(f"Failed to connect to SSE: {response.status_code}")
                    return
                
                # Buffer for SSE messages
                buffer = ""
                event_data = {}
                
                # Process stream
                async for chunk in response.aiter_text():
                    if not chunk:
                        continue
                    
                    buffer += chunk
                    
                    # Process complete events (separated by double newlines)
                    while '\n\n' in buffer:
                        event_text, buffer = buffer.split('\n\n', 1)
                        
                        # Parse event
                        await self._parse_sse_event(event_text)
                        
        except Exception as e:
            logger.error(f"SSE connection error: {str(e)}")
            # Allow reconnection by clearing client
            self.sse_client = None
    
    async def _parse_sse_event(self, event_text):
        """Parse an SSE event and handle it appropriately"""
        event_data = {}
        event_type = "message"  # Default event type
        
        # Parse the event lines
        for line in event_text.split('\n'):
            if line.startswith('event:'):
                event_type = line[6:].strip()
            elif line.startswith('data:'):
                data_content = line[5:].strip()
                # Try to parse as JSON
                try:
                    event_data = json.loads(data_content)
                except json.JSONDecodeError:
                    event_data = {"text": data_content}
            elif line.startswith('id:'):
                event_data["id"] = line[3:].strip()
        
        # Handle different event types
        if event_type == "message":
            logger.debug(f"Received message event: {event_data}")
        elif event_type == "tool_response":
            # Process tool response
            if "id" in event_data and event_data["id"] in self.pending_requests:
                request_id = event_data["id"]
                result = event_data.get("result", {})
                # Resolve the pending request
                if not self.pending_requests[request_id].done():
                    self.pending_requests[request_id].set_result(result)
                # Clean up
                del self.pending_requests[request_id]
        elif event_type == "error":
            logger.error(f"Received error event: {event_data}")
            # If this is for a pending request, resolve it with the error
            if "id" in event_data and event_data["id"] in self.pending_requests:
                request_id = event_data["id"]
                if not self.pending_requests[request_id].done():
                    self.pending_requests[request_id].set_exception(
                        Exception(event_data.get("error", "Unknown SSE error"))
                    )
                # Clean up
                del self.pending_requests[request_id]
        elif event_type == "tools":
            # Process tools list
            if "tools" in event_data:
                self.tools_cache = event_data["tools"]
                logger.info(f"Received tools from SSE: {len(self.tools_cache)} tools")
            
    async def list_tools(self):
        """Get list of available tools from MCP server via SSE"""
        if self.tools_cache:
            return self.tools_cache
            
        logger.info("Fetching available tools from MCP server...")
        
        # Ensure SSE connection is established
        await self.connect_sse()
        
        # Wait for tools to be received via SSE (with timeout)
        timeout = 5  # seconds
        start_time = time.time()
        
        while not self.tools_cache and (time.time() - start_time) < timeout:
            await asyncio.sleep(0.5)
        
        if not self.tools_cache:
            logger.warning("Timed out waiting for tools from SSE, using hardcoded tools")
            return self._get_hardcoded_tools()
            
        return self.tools_cache
    
    def _get_hardcoded_tools(self):
        """Return a hardcoded list of known MCP tools"""
        tools = [
            {
                "name": "ask_project_rag",
                "description": "Ask a natural language question about the project (uses RAG).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "token": {
                            "type": "string",
                            "description": "Authentication token"
                        },
                        "query": {
                            "type": "string",
                            "description": "The question to ask about the project"
                        }
                    },
                    "required": ["token", "query"]
                }
            },
            {
                "name": "view_project_context",
                "description": "View project context. Provide context_key for specific lookup OR search_query for keyword search.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "token": {
                            "type": "string",
                            "description": "Authentication token"
                        },
                        "context_key": {
                            "type": "string",
                            "description": "Exact key to view (optional)"
                        },
                        "search_query": {
                            "type": "string",
                            "description": "Keyword search query (optional)"
                        }
                    },
                    "required": ["token"]
                }
            },
            {
                "name": "view_tasks",
                "description": "View tasks, optionally filtered by agent ID or status",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "token": {
                            "type": "string",
                            "description": "Authentication token"
                        },
                        "agent_id": {
                            "type": "string",
                            "description": "Filter tasks by agent ID (optional)"
                        },
                        "status": {
                            "type": "string",
                            "description": "Filter tasks by status (optional)",
                            "enum": ["pending", "in_progress", "completed", "cancelled"]
                        }
                    },
                    "required": ["token"]
                }
            }
        ]
        
        self.tools_cache = tools
        return tools
    
    async def _send_sse_message(self, message_type, payload):
        """Send a message to the SSE connection and get a response"""
        if not self.sse_client or (self.sse_task and self.sse_task.done()):
            await self.connect_sse()
        
        # Generate a unique request ID
        request_id = str(uuid.uuid4())
        
        # Create a future to wait for the response
        response_future = asyncio.Future()
        self.pending_requests[request_id] = response_future
        
        # Create message with the request ID
        message = {
            "type": message_type,
            "id": request_id,
            "clientId": self.client_id,
            **payload
        }
        
        # Send message using a separate HTTP request (not the SSE stream)
        dashboard_base = self.url.split('/sse')[0]
        message_url = f"{dashboard_base}/sse/message"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    message_url,
                    json=message,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.admin_token}"
                    },
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    logger.error(f"Failed to send SSE message: {response.status_code}")
                    # Clean up the pending request
                    if request_id in self.pending_requests:
                        del self.pending_requests[request_id]
                    return None
                
            except Exception as e:
                logger.error(f"Error sending SSE message: {str(e)}")
                # Clean up the pending request
                if request_id in self.pending_requests:
                    del self.pending_requests[request_id]
                return None
        
        # Wait for the response with timeout
        try:
            return await asyncio.wait_for(response_future, timeout=60.0)
        except asyncio.TimeoutError:
            logger.error(f"Timeout waiting for response to {message_type} request")
            # Clean up the pending request
            if request_id in self.pending_requests:
                del self.pending_requests[request_id]
            return None
        
    async def call_tool(self, tool_name, parameters):
        """Call a tool on the MCP server using the SSE protocol"""
        # Clone parameters to avoid modifying the original
        tool_params = parameters.copy()
        
        # Ensure token is included and set to admin_token
        tool_params["token"] = self.admin_token
            
        logger.info(f"Calling tool: {tool_name} with parameters: {tool_params}")
        
        # Format the tool call for SSE
        tool_payload = {
            "tool": tool_name,
            "arguments": tool_params
        }
        
        # Send the tool request via SSE
        result = await self._send_sse_message("tool_call", tool_payload)
        
        if result is None:
            # If SSE failed, try the direct API approach as fallback
            logger.warning("SSE tool call failed, trying fallback API methods")
            return await self._call_tool_api_fallback(tool_name, tool_params)
        
        # Parse the result
        try:
            # Check for content field in response
            if isinstance(result, dict):
                if "error" in result:
                    return f"Error from server: {result['error']}"
                elif "content" in result:
                    return result["content"]
                elif "text" in result:
                    return result["text"]
                elif "result" in result:
                    return str(result["result"])
            
            # Handle list responses
            if isinstance(result, list) and len(result) > 0:
                # Extract content from list of objects
                content_items = []
                for item in result:
                    if isinstance(item, dict):
                        for key in ["text", "content", "result"]:
                            if key in item:
                                content_items.append(item[key])
                                break
                        else:
                            # If no recognized field found, use the whole item
                            content_items.append(str(item))
                    else:
                        content_items.append(str(item))
                
                if content_items:
                    return "\n".join(content_items)
            
            # Fall back to returning the raw result
            return str(result)
        except Exception as e:
            logger.error(f"Error parsing tool result: {str(e)}")
            return f"Error parsing result: {str(e)}"
    
    async def _call_tool_api_fallback(self, tool_name, parameters):
        """Fallback method to call tools using API endpoints"""
        logger.info(f"Using fallback API methods for tool: {tool_name}")
        
        dashboard_base = self.url.split('/sse')[0]
        
        # Try multiple API endpoints as fallbacks
        endpoints = [
            # Direct tool API endpoint
            {
                "url": f"{dashboard_base}/api/tool-call",
                "method": "POST",
                "headers": {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.admin_token}"
                },
                "json": {
                    "name": tool_name,
                    "arguments": parameters
                }
            },
            # Dashboard API endpoint
            {
                "url": f"{dashboard_base}/dashboard/api/tool-call",
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
                "json": {
                    "admin_token": self.admin_token,
                    "tool": tool_name,
                    "arguments": parameters
                }
            },
            # Direct tool endpoint
            {
                "url": f"{dashboard_base}/api/{tool_name.replace('_', '-')}",
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
                "params": {"token": self.admin_token},
                "json": parameters
            }
        ]
        
        async with httpx.AsyncClient() as client:
            for endpoint in endpoints:
                try:
                    response = await client.request(
                        endpoint["method"],
                        endpoint["url"],
                        headers=endpoint.get("headers", {}),
                        params=endpoint.get("params", {}),
                        json=endpoint.get("json", {}),
                        timeout=60.0
                    )
                    
                    if response.status_code == 200:
                        # Successfully called the API
                        try:
                            result = response.json()
                            
                            # Handle different response formats
                            if isinstance(result, dict):
                                if "error" in result:
                                    logger.warning(f"API error response: {result['error']}")
                                    continue  # Try next endpoint
                                elif "content" in result:
                                    return result["content"]
                                elif "result" in result:
                                    return str(result["result"])
                            
                            # Handle list responses
                            if isinstance(result, list) and len(result) > 0:
                                content_items = []
                                for item in result:
                                    if isinstance(item, dict) and "text" in item:
                                        content_items.append(item["text"])
                                if content_items:
                                    return "\n".join(content_items)
                            
                            # Return the raw result
                            return str(result)
                            
                        except json.JSONDecodeError:
                            # Return the raw text if not JSON
                            return response.text
                    
                except Exception as e:
                    logger.error(f"Error with API endpoint {endpoint['url']}: {str(e)}")
                    continue  # Try next endpoint
        
        # If all endpoints failed
        return f"Error: Failed to call tool {tool_name}. All API endpoints failed."
    
    async def close(self):
        """Close the SSE connection and clean up"""
        if self.sse_task:
            self.sse_task.cancel()
            try:
                await self.sse_task
            except asyncio.CancelledError:
                pass
            
        if self.sse_client:
            await self.sse_client.aclose()
            self.sse_client = None


async def run_agent_chat(query, mcp_server_url, admin_token):
    """Run the RAG agent with a single query and return the response"""
    
    # Initialize MCP client
    mcp_client = MCPClient(mcp_server_url, admin_token)
    
    try:
        # Get available tools
        tools = await mcp_client.list_tools()
        
        # Initialize conversation with system message
        messages = [
            {"role": "system", "content": """You are a knowledgeable agent that provides information about the project.
            You use the available MCP tools to retrieve relevant information.
            When asked a question, use the 'ask_project_rag' tool to find information in the project.
            For specific context lookups, use the 'view_project_context' tool.
            For tasks information, use the 'view_tasks' tool.
            Always provide helpful, accurate information based on the project's actual content."""},
            {"role": "user", "content": query}
        ]
        
        # Run the conversation loop
        max_iterations = 5
        for i in range(max_iterations):
            # Call the OpenAI API
            response = client.chat.completions.create(
                model="gpt-4.1-2025-04-14",
                messages=messages,
                tools=[{"type": "function", "function": tool} for tool in tools],
                tool_choice="auto",
            )
            
            # Get the response content
            response_message = response.choices[0].message
            
            # Add the assistant's message to the conversation
            messages.append(response_message.model_dump())
            
            # Check if the assistant wants to use a tool
            if response_message.tool_calls:
                # Process each tool call
                for tool_call in response_message.tool_calls:
                    # Extract the tool call details
                    tool_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)
                    
                    print(f"\n[Using tool: {tool_name}...]", flush=True)
                    
                    # Call the tool
                    tool_result = await mcp_client.call_tool(tool_name, arguments)
                    
                    # Add the tool result to the conversation
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": tool_name,
                        "content": str(tool_result),
                    })
                    
                    print()  # Newline after tool call
            else:
                # If no tool calls, we're done
                await mcp_client.close()
                return response_message.content
                
        # If we've reached the maximum number of iterations, return the last response
        await mcp_client.close()
        return "Reached maximum number of iterations. Here's what I know so far: " + response_message.content
    finally:
        # Ensure client is closed even if an error occurs
        await mcp_client.close()


async def interactive_chat(mcp_server_url, admin_token):
    """Run an interactive chat session with the RAG agent"""
    print(f"=== Project RAG Agent Chat ===")
    print(f"Connected to MCP server: {mcp_server_url}")
    print("Type 'exit' or 'quit' to end the session")
    print("Ask a question about your project:")
    
    # Create a single MCP client for the whole session
    mcp_client = MCPClient(mcp_server_url, admin_token)
    
    try:
        # Establish SSE connection first
        await mcp_client.connect_sse()
        
        while True:
            try:
                query = input("\nYou: ")
                if query.lower() in ['exit', 'quit']:
                    print("Ending session. Goodbye!")
                    break
                    
                print("\nAgent: ", end="", flush=True)
                result = await run_agent_chat(query, mcp_server_url, admin_token)
                print(result)
                
            except KeyboardInterrupt:
                print("\nSession interrupted. Goodbye!")
                break
            except Exception as e:
                logger.error(f"Error in chat session: {e}")
                print(f"\nAn error occurred: {e}")
    finally:
        # Clean up
        await mcp_client.close()


if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="RAG Agent using OpenAI API with MCP")
    parser.add_argument("--token", help="Admin token for MCP server")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # --- Interactive MCP Server Details ---
    mcp_host = 'localhost'
    use_default_host = input("Connect to default MCP server (localhost)? (Y/n): ").lower().strip()
    if use_default_host == 'n':
        mcp_host = input("Enter MCP server IP or hostname: ").strip() or 'localhost' # Default to localhost if empty

    mcp_port = 8038
    while True:
        port_input = input(f"Enter MCP server port (default: {mcp_port}): ").strip()
        if not port_input:
            break # Use default
        try:
            mcp_port = int(port_input)
            if 1 <= mcp_port <= 65535:
                 break
            else:
                 print("Port must be between 1 and 65535.")
        except ValueError:
            print("Invalid port number. Please enter a numeric value.")

    mcp_server_url = f"http://{mcp_host}:{mcp_port}/sse/"
    # --- End Interactive MCP Server Details ---

    # Use provided admin token or prompt for it
    admin_token = args.token
    if not admin_token:
        admin_token = input("Enter your MCP admin token: ")
    
    print(f"Connecting to MCP server at {mcp_server_url}") # Use constructed URL
    try:
        asyncio.run(interactive_chat(mcp_server_url, admin_token)) # Use constructed URL
    except KeyboardInterrupt:
        print("\nApplication terminated by user")
    except Exception as e:
        logger.error(f"Application error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc() 