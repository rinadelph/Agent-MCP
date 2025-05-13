import os
import sys
import json
import logging
import asyncio
import argparse
import uuid
from functools import partial
import httpx
from urllib.parse import urljoin
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get API key from environment variables
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logger.error("OPENAI_API_KEY not found in environment variables. Please set it in your .env file.")
    print("ERROR: OPENAI_API_KEY not found in environment variables. Please set it in your .env file.")
    sys.exit(1)

from openai import OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

class MCPClient:
    """Client for interacting with MCP-compliant servers using SSE protocol"""
    
    def __init__(self, server_url, admin_token):
        """Initialize the MCP client

        Args:
            server_url (str): URL of the MCP server
            admin_token (str): Admin token for authentication
        """
        # Ensure the URL is properly formatted for SSE
        self.server_url = server_url
        if not self.server_url.endswith('/sse'):
            self.server_url = urljoin(self.server_url, '/sse')
        
        self.admin_token = admin_token
        self.client_id = f"mcp_client_{uuid.uuid4().hex[:8]}"
        self.sse_client = None
        self.tools_cache = None
        self.event_queue = asyncio.Queue()
        logger.info(f"Created MCP client with ID: {self.client_id}")
    
    async def connect(self):
        """Establish connection to the MCP server via SSE"""
        if self.sse_client:
            return
        
        logger.info(f"Connecting to MCP server at {self.server_url}")
        
        # Create a client for SSE connection
        self.sse_client = httpx.AsyncClient(timeout=None)  # No timeout for persistent connection
        
        # Start listening for SSE events
        self.sse_task = asyncio.create_task(self._listen_for_events())
        
        # Wait briefly for connection to establish
        await asyncio.sleep(0.5)
    
    async def _listen_for_events(self):
        """Listen for Server-Sent Events"""
        try:
            url = f"{self.server_url}?clientId={self.client_id}"
            logger.debug(f"SSE connection URL: {url}")
            
            async with self.sse_client.stream(
                'GET',
                url,
                headers={'Accept': 'text/event-stream'}
            ) as response:
                if response.status_code != 200:
                    logger.error(f"Failed to connect to SSE endpoint: {response.status_code}")
                    return
                
                logger.info("SSE connection established")
                
                # Buffer for incoming SSE data
                buffer = ""
                
                async for chunk in response.aiter_text():
                    buffer += chunk
                    
                    # Process complete events (separated by double newlines)
                    while '\n\n' in buffer:
                        event_text, buffer = buffer.split('\n\n', 1)
                        await self._process_sse_event(event_text)
        
        except Exception as e:
            logger.error(f"SSE connection error: {str(e)}")
        finally:
            logger.info("SSE connection closed")
    
    async def _process_sse_event(self, event_text):
        """Process an SSE event"""
        event_type = "message"  # Default event type
        event_data = {}
        
        # Parse the event
        for line in event_text.split('\n'):
            line = line.strip()
            
            if not line:
                continue
                
            if line.startswith('event:'):
                event_type = line[6:].strip()
            elif line.startswith('data:'):
                data_text = line[5:].strip()
                try:
                    event_data = json.loads(data_text)
                except json.JSONDecodeError:
                    event_data = {"text": data_text}
            elif line.startswith('id:'):
                event_data["id"] = line[3:].strip()
        
        # Put the event into the queue
        await self.event_queue.put((event_type, event_data))
        
        # Handle specific event types immediately
        if event_type == "tools" and "tools" in event_data:
            logger.info(f"Received tools definition: {len(event_data['tools'])} tools")
            self.tools_cache = event_data["tools"]
    
    async def list_tools(self):
        """Get list of tools available from the MCP server"""
        # If we have cached tools, return them
        if self.tools_cache:
            return self.tools_cache
        
        # Ensure we're connected
        await self.connect()
        
        # Wait for tools to be received via SSE (with timeout)
        timeout = 5  # seconds
        try:
            start_time = asyncio.get_event_loop().time()
            while not self.tools_cache:
                if asyncio.get_event_loop().time() - start_time > timeout:
                    logger.warning("Timed out waiting for tools from SSE")
                    break
                    
                # Check for events with a short timeout
                try:
                    event_type, event_data = await asyncio.wait_for(
                        self.event_queue.get(), 
                        timeout=0.5
                    )
                    
                    if event_type == "tools" and "tools" in event_data:
                        self.tools_cache = event_data["tools"]
                        break
                except asyncio.TimeoutError:
                    # No event received within the timeout
                    pass
        
        except Exception as e:
            logger.error(f"Error waiting for tools: {str(e)}")
        
        # If we still don't have tools, use hardcoded defaults
        if not self.tools_cache:
            logger.info("Using hardcoded tools")
            self.tools_cache = self._get_default_tools()
            
        return self.tools_cache
    
    def _get_default_tools(self):
        """Return default tool definitions when server doesn't provide them"""
        return [
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
            },
            {
                "name": "assign_task_tool",
                "description": "Admin tool to assign a task to an agent, optionally specifying dependencies and a parent task.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "token": {"type": "string", "description": "Admin authentication token"},
                        "agent_id": {"type": "string", "description": "ID of the agent to assign the task to"},
                        "task_title": {"type": "string", "description": "Title of the task"},
                        "task_description": {"type": "string", "description": "Detailed description of the task"},
                        "priority": {"type": "string", "description": "Task priority (e.g., low, medium, high)", "default": "medium"},
                        "depends_on_tasks": {"type": "array", "items": {"type": "string"}, "description": "List of task IDs this task depends on (optional)"},
                        "parent_task_id": {"type": "string", "description": "ID of the parent task (optional)"}
                    },
                    "required": ["token", "agent_id", "task_title", "task_description"]
                }
            },
            {
                "name": "create_self_task_tool",
                "description": "Agent tool to create a task for themselves, optionally specifying dependencies and a parent task. Defaults parent to current task if none provided.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "token": {"type": "string", "description": "Agent authentication token"},
                        "task_title": {"type": "string", "description": "Title of the task"},
                        "task_description": {"type": "string", "description": "Detailed description of the task"},
                        "priority": {"type": "string", "description": "Task priority (e.g., low, medium, high)", "default": "medium"},
                        "depends_on_tasks": {"type": "array", "items": {"type": "string"}, "description": "List of task IDs this task depends on (optional)"},
                        "parent_task_id": {"type": "string", "description": "ID of the parent task (optional, defaults to agent's current task)"}
                    },
                    "required": ["token", "task_title", "task_description"]
                }
            }
        ]
    
    async def call_tool(self, tool_name, parameters):
        """Call a tool on the MCP server
        
        This uses the MCP protocol to invoke tools via SSE message passing.
        """
        # Ensure we're connected
        await self.connect()
        
        # Clone parameters to avoid modifying the original
        params = parameters.copy()
        
        # Add token to parameters if not present
        if "token" not in params:
            params["token"] = self.admin_token
        
        logger.info(f"Calling tool: {tool_name} with parameters: {params}")
        
        # Create a message ID for correlating the response
        message_id = str(uuid.uuid4())
        
        # Prepare the tool call message (format used by SSE)
        message = {
            "clientId": self.client_id,
            "id": message_id,
            "type": "tool_call",
            "tool": tool_name,
            "arguments": params
        }
        
        # Get the base URL (without /sse)
        base_url = self.server_url.rsplit('/sse', 1)[0]
        
        # Try multiple endpoints that might handle messages
        message_endpoints = [
            f"{base_url}/api/message",
            f"{base_url}/api/sse/message",
            f"{base_url}/sse/message",
            f"{base_url}/message",
            f"{base_url}/api/tool-call",
            f"{base_url}/dashboard/api/tool-call",
            f"{base_url}/api/{tool_name.replace('_', '-')}"
        ]
        
        success = False
        
        # Send the message to each endpoint until one succeeds
        for endpoint in message_endpoints:
            try:
                async with httpx.AsyncClient() as client:
                    logger.debug(f"Trying to send tool call to: {endpoint}")
                    
                    # Some endpoints need different formats
                    if "dashboard/api/tool-call" in endpoint:
                        # Format used by some dashboard endpoints
                        payload = {
                            "admin_token": self.admin_token,
                            "tool": tool_name,
                            "arguments": params
                        }
                    elif "api/tool-call" in endpoint:
                        # Format used by direct tool-call API
                        payload = {
                            "name": tool_name,
                            "arguments": params
                        }
                    else:
                        # Default SSE message format
                        payload = message
                    
                    response = await client.post(
                        endpoint,
                        json=payload,
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {self.admin_token}"
                        },
                        timeout=10.0
                    )
                    
                    if response.status_code == 200:
                        logger.info(f"Successfully sent tool call message to {endpoint}")
                        success = True
                        break
                    else:
                        logger.debug(f"Failed to send message to {endpoint}: {response.status_code}")
                
            except Exception as e:
                logger.debug(f"Error sending to {endpoint}: {str(e)}")
                continue
        
        if not success:
            # If all endpoints failed, try direct API approach
            return await self._call_direct_api(tool_name, params)
        
        # Wait for the tool response event with matching ID
        logger.debug("Tool call message sent, waiting for response")
        start_time = asyncio.get_event_loop().time()
        timeout = 60  # 60 seconds timeout for tool calls
        
        while asyncio.get_event_loop().time() - start_time < timeout:
            try:
                event_type, event_data = await asyncio.wait_for(
                    self.event_queue.get(),
                    timeout=1.0
                )
                
                # Check if this is our tool response
                if (event_type == "tool_response" and 
                    event_data.get("id") == message_id):
                    
                    logger.debug(f"Received tool response: {event_data}")
                    
                    # Extract and format the result
                    if "error" in event_data:
                        return f"Error: {event_data['error']}"
                    elif "result" in event_data:
                        result = event_data["result"]
                        
                        # Handle different result formats
                        if isinstance(result, dict):
                            if "content" in result:
                                return result["content"]
                            elif "text" in result:
                                return result["text"]
                        
                        # Return the raw result if no specific format
                        return str(result)
                    else:
                        return "Tool call completed but returned no result"
            
            except asyncio.TimeoutError:
                # No event within the wait time, continue waiting
                continue
        
        # If we get here, we timed out waiting for a response
        logger.error(f"Timeout waiting for tool response: {tool_name}")
        
        # As a last resort, try direct API approach
        return await self._call_direct_api(tool_name, params)
    
    async def _call_direct_api(self, tool_name, parameters):
        """Fallback method to call tools using direct API endpoints"""
        logger.info(f"Using direct API approach for tool: {tool_name}")
        
        # Get the base URL (without /sse)
        base_url = self.server_url.rsplit('/sse', 1)[0]
        
        # Define multiple possible API endpoints
        api_endpoints = [
            {
                "url": f"{base_url}/api/tool-call",
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
            {
                "url": f"{base_url}/dashboard/api/tool-call",
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
                "json": {
                    "admin_token": self.admin_token,
                    "tool": tool_name,
                    "arguments": parameters
                }
            },
            {
                "url": f"{base_url}/api/{tool_name.replace('_', '-')}",
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
                "params": {"token": self.admin_token},
                "json": parameters
            },
            {
                "url": f"{base_url}/api/{tool_name}",
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
                "params": {"token": self.admin_token},
                "json": parameters
            },
            {
                "url": f"{base_url}/{tool_name.replace('_', '-')}",
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
                "params": {"token": self.admin_token},
                "json": parameters
            }
        ]
        
        async with httpx.AsyncClient() as client:
            for endpoint in api_endpoints:
                try:
                    logger.debug(f"Trying API endpoint: {endpoint['url']}")
                    response = await client.request(
                        endpoint["method"],
                        endpoint["url"],
                        headers=endpoint.get("headers", {}),
                        params=endpoint.get("params", {}),
                        json=endpoint.get("json", {}),
                        timeout=60.0
                    )
                    
                    if response.status_code == 200:
                        logger.info(f"Successfully called API endpoint: {endpoint['url']}")
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
                                else:
                                    return str(result)
                            
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
                    else:
                        logger.debug(f"API endpoint {endpoint['url']} returned {response.status_code}")
                    
                except Exception as e:
                    logger.debug(f"Error with API endpoint {endpoint['url']}: {str(e)}")
                    continue  # Try next endpoint
        
        # If all endpoints failed
        return f"Error: Failed to call tool {tool_name}. All API endpoints failed."
    
    async def close(self):
        """Close the client connection"""
        if self.sse_task:
            self.sse_task.cancel()
            try:
                await self.sse_task
            except asyncio.CancelledError:
                pass
        
        if self.sse_client:
            await self.sse_client.aclose()
            self.sse_client = None
        
        logger.info("MCP client connection closed")


async def run_agent_chat(query, server_url, admin_token):
    """Run a chat with the RAG agent using the MCP client"""
    # Create and connect MCP client
    mcp_client = MCPClient(server_url, admin_token)
    
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
                    
                    # Make sure arguments contains the admin token
                    if "token" not in arguments or arguments["token"] == "user":
                        arguments["token"] = admin_token
                    
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
                return response_message.content
                
        # If we've reached the maximum number of iterations, return the last response
        return "Reached maximum number of iterations. Here's what I know so far: " + response_message.content
    
    finally:
        # Ensure client is closed
        await mcp_client.close()


async def interactive_chat(server_url, admin_token):
    """Run an interactive chat session with the RAG agent"""
    print(f"=== Project RAG Agent Chat ===")
    print(f"Connected to MCP server: {server_url}")
    print("Type 'exit' or 'quit' to end the session")
    print("Ask a question about your project:")
    
    # Create the MCP client once for the session
    mcp_client = MCPClient(server_url, admin_token)
    
    try:
        # Initialize the client
        await mcp_client.connect()
        
        while True:
            try:
                query = input("\nYou: ")
                if query.lower() in ['exit', 'quit']:
                    print("Ending session. Goodbye!")
                    break
                    
                print("\nAgent: ", end="", flush=True)
                result = await run_agent_chat(query, server_url, admin_token)
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
        logger.error(f"Application error: {e}")
        if args.debug:
            import traceback
            traceback.print_exc() 