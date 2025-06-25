# Agent-MCP

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/rinadelph/Agent-MCP)

Multi-Agent Collaboration Protocol for coordinated AI software development.

![Agent Network Visualization](assets/images/Screenshot%20from%202025-06-25%2011-29-43.png)

Think **Obsidian for your AI agents** - a knowledge graph where agents coordinate through shared context, task management, and real-time collaboration.

## What it does

Agent-MCP lets multiple AI agents work on your codebase simultaneously without conflicts. Agents coordinate through shared memory, file-level locking, and a visual dashboard that shows everything happening in real-time.

## Quick Start

```bash
# Clone and setup
git clone https://github.com/rinadelph/Agent-MCP.git
cd Agent-MCP
cp .env.example .env  # Add your OpenAI API key
uv venv && uv pip install -e .

# Start the server
uv run -m agent_mcp.cli --project-dir /path/to/your/project

# Launch dashboard (recommended)
cd agent_mcp/dashboard && npm install && npm run dev
```

## Essential Prompts

Copy these prompts directly into your AI assistant:

### 1. Initialize Admin Agent
```
You are the admin agent.
Admin Token: "your_admin_token_from_server"

Your role is to coordinate work and manage other agents.
```

### 2. Add Project Context
```
Add this MCD (Main Context Document) to project context:

[paste your MCD here - see docs/mcd-guide.md for structure]

Store every detail, don't summarize anything.
```

### 3. Create Worker Agents
```
Create specialized agents for implementation:
- backend-worker: API and database tasks
- frontend-worker: UI and client-side logic
- test-worker: Testing and validation
```

### 4. Initialize Workers
```
# In new window for each worker:
You are [worker-name] agent.
Your Admin Token: "worker_token_from_admin"

Ask the project RAG 5-7 questions to understand requirements.
Then begin implementation.

AUTO --worker --memory
```

### 5. Monitor Progress
Use the dashboard at `http://localhost:3847` to:
- View real-time agent collaboration network
- Track task completion
- Manage project memory
- Debug agent interactions

## Visual Dashboard

### Multi-Agent Collaboration Network
![Dashboard Overview](assets/images/Screenshot%20from%202025-06-25%2012-07-32.png)
Real-time visualization of agents and tasks - see how your AI team works together.

### Memory Bank
![Memory Management](assets/images/Screenshot%20from%202025-06-25%2012-08-39.png)
Persistent context that never gets lost - your project's knowledge graph.

### Agent Fleet Management
![Agent Fleet](assets/images/Screenshot%20from%202025-06-25%2012-07-55.png)
Monitor all agents, their tasks, and activity in one place.

## How it Works

1. **Write an MCD** - A detailed blueprint of your project (like a comprehensive README)
2. **Admin agent loads it** - Creates shared context all agents can access
3. **Deploy specialized workers** - Each handles specific parts of your project
4. **Agents coordinate automatically** - Through file locking and shared memory
5. **Monitor everything visually** - See the entire process in real-time

## Why Agent-MCP?

Traditional AI assistants are like having one developer who gets overwhelmed. Agent-MCP is like having a coordinated team where:
- Each agent specializes in what they do best
- Knowledge is shared across the entire team
- Work happens in parallel without conflicts
- You can see everything happening in real-time

## Documentation

- [Getting Started](./docs/getting-started.md) - Detailed setup walkthrough
- [MCD Guide](./docs/mcd-guide.md) - Creating project blueprints
- [Theory](./docs/chapter-1-cognitive-empathy.md) - Understanding the approach

## Requirements

- Python 3.8+
- Node.js 18+ (for dashboard)
- OpenAI API key
- AI coding assistant (Claude Code or Cursor)

## Common Issues

**Can't find admin token**: Check server startup logs  
**Worker can't access tasks**: Use worker token, not admin token  
**Agents overwriting each other**: Ensure using --worker flag  
**Dashboard won't load**: Check Node version, reinstall dependencies

## Community

- [Discord](https://discord.gg/7Jm7nrhjGn)
- [Issues](https://github.com/rinadelph/Agent-MCP/issues)
- [Discussions](https://github.com/rinadelph/Agent-MCP/discussions)

## License

MIT