# Agent MCP Template

A template for creating multi-agent systems using the MCP (Multi-Agent Collaboration Protocol) for coordinated, efficient AI collaboration.

## Features

- Multi-agent collaboration framework
- Task management and coordination
- Context and knowledge sharing between agents
- Graph visualization of agent interactions
- Support for embedding and RAG capabilities
- Interactive dashboard

## Project Planning with the Main Context Document (MCD)

Before starting development, it's essential to use deep research to create a **Main Context Document (MCD)** - the single source of truth for your application. This document provides a granular plan detailing:

- System architecture and component relationships
- UI/UX design for all screens and components
- API routes and endpoints
- Data structures and models
- Implementation units and tasks
- Dependencies and technology stack

**The MCD is critical because:**
1. It enables agents to understand the overall system before working on individual components
2. It allows linear, coordinated building (like constructing a house from blueprints)
3. It reduces token usage by providing structured, relevant context
4. It prevents conflicting implementations between agents

**Review the `MCD.md` file** in this repository to understand the structure and level of detail required. The MCD should contain:

- Overview and goals
- Context and architecture diagrams
- Functional requirements
- Design specifications (UI/UX, API, data models)
- Implementation details
- Task breakdown for agents

With a comprehensive MCD, agents can implement your application part-by-part with a clear understanding of how each piece fits into the whole.

## Installation

### Prerequisites

- Python 3.8+
- [uv](https://github.com/astral-sh/uv) (recommended for faster package installation)

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/agent-mcp.git
   cd agent-mcp
   ```

2. Set up environment variables by copying the example file:
   ```bash
   cp .env.example .env
   ```

3. Edit the `.env` file and add your OpenAI API key:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

4. Install using uv:
   ```bash
   uv venv
   uv pip install -e .
   ```

   Or with pip:
   ```bash
   pip install -e .
   ```

## Multi-Agent Workflow

### Architecture Overview

The MCP system uses a hierarchical structure with:
- **Admin Agent**: Coordinates other agents, assigns tasks, and maintains overall project direction
- **Worker Agents**: Specialized agents that execute specific tasks (frontend, backend, data modeling, etc.)

### Agent Setup and Operation

#### 1. Starting the MCP Server

```bash
uv run -m mcp_template.main --port 8080 --project-dir /path/to/your/project
```

Options:
- `--port`: Port to run the server on (default: 8080)
- `--project-dir`: Base directory for the project

#### 2. Configure Admin Token

The admin token provides privileged access to the MCP server. You can set it in your `.env` file:

```
MCP_ADMIN_TOKEN=your_custom_admin_token
```

If not set, a random token will be generated at server startup and printed to the console. Make note of this token as it's required for admin operations.

#### 3. Launching Agents

1. **Admin Agent**: Start the admin agent using:
   ```bash
   python -m mcp_template.mcp_client_runner --admin
   ```

2. **Worker Agents**: Start worker agents using:
   ```bash
   python -m mcp_template.mcp_client_runner --agent-id worker1 --capabilities "frontend,react"
   python -m mcp_template.mcp_client_runner --agent-id worker2 --capabilities "backend,api"
   ```

#### 4. Using AUTO Mode with Worker Agents

Once your environment is set up and agents are connected, you can activate AUTO mode with specialized worker capabilities:

```
AUTO --worker --memory
```

This commands the agent to:
- Operate autonomously without user intervention
- Follow the worker protocol with task status tracking
- Utilize memory for context retention across interactions

### Dashboard

Access the dashboard at `http://localhost:8080` to:
- Monitor agent activities in real-time
- View task status and dependencies
- Observe agent relationships and coordination
- Track file operations and context sharing

## Token System and Resource Management

### Understanding Tokens

Tokens serve multiple purposes in the MCP system:
1. **Authentication Tokens**: Used for agent identification and admin access
2. **RAG Tokens**: Used for embedding and retrieving context from the knowledge base
3. **OpenAI Tokens**: Consumed during agent operations (model usage)

### Token Management

To monitor and manage token usage:
1. Install SQLite Viewer plugin or use the command line:
   ```bash
   sqlite3 /path/to/project/.agent/mcp_state.db
   ```

2. Query token usage:
   ```sql
   SELECT * FROM token_usage;
   ```

3. Monitor in the dashboard under the "Resources" tab

### Resource Optimization

For large projects:
1. Use specialized agents with focused capabilities to reduce context size
2. Break tasks into smaller units with clear dependencies
3. Utilize the RAG system for efficient context retrieval
4. Store shared information in the project context rather than repeating in messages

## Project RAG and Knowledge Base

### Setting Up the Project RAG

The Retrieval-Augmented Generation (RAG) system allows agents to access relevant project knowledge efficiently:

1. Index project files:
   ```bash
   python -m mcp_template.rag_indexer --project-dir /path/to/project
   ```

2. Add documentation to the knowledge base:
   ```bash
   python -m mcp_template.rag_indexer --add-doc /path/to/document.md
   ```

### Using RAG in Agent Workflows

Agents can query the knowledge base using:
```python
response = await client.ask_project_rag("How does the authentication system work?")
```

This returns relevant context without loading entire files, saving tokens and improving response quality.

## Agent Task Assignment Strategy

For optimal performance, follow these guidelines:

1. **Task Granularity**: Break down large tasks into atomic units with clear inputs/outputs
2. **Dependency Tracking**: Explicitly define task dependencies in assignment
3. **Capability Matching**: Assign tasks to agents with relevant capabilities
4. **Progress Monitoring**: Use explicit status updates to track task progress
5. **Context Sharing**: Provide necessary context at assignment time to reduce later lookups

Example task assignment from admin to worker:
```
@worker1 Please implement the login form component based on the MCD section 6.1. 
Dependencies: None
Artifacts: src/components/LoginForm.tsx
Context: Uses FormKit, requires email validation
```

## Components

- `main.py`: MCP server implementation
- `mcp_client.py`: Client library for connecting agents to MCP
- `dashboard_api.py`: API endpoints for visualization
- `rag_agent_test.py`: Example of a RAG-capable agent
- `INSTRUCTIONS.md`: Operational guidelines for agents

## Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key
- `MCP_SERVER_URL`: URL of the MCP server
- `MCP_ADMIN_TOKEN`: (Optional) Admin token for direct access
- `MCP_PROJECT_DIR`: Path to the project directory

## License

MIT License