# Agent-MCP

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/rinadelph/Agent-MCP)

Multi-Agent Collaboration Protocol for coordinated AI software development.

## What it does

Agent-MCP lets multiple AI agents work on your codebase simultaneously without conflicts. Think of it as git for AI collaboration - agents coordinate through shared context and file-level locking.

## Quick Start

```bash
# Clone and setup
git clone https://github.com/rinadelph/Agent-MCP.git
cd Agent-MCP
cp .env.example .env  # Add your OpenAI API key
uv venv && uv pip install -e .

# Start the server
uv run -m agent_mcp.cli --project-dir /path/to/your/project

# Optional: Launch dashboard
cd agent_mcp/dashboard && npm install && npm run dev
```

## How it works

1. **Write an MCD** (Main Context Document) - a detailed blueprint of what you want to build
2. **Initialize an admin agent** with the MCD to coordinate the work
3. **Deploy worker agents** that implement specific features
4. **Monitor progress** through the dashboard or terminal

## Basic Workflow

### 1. Create an MCD

See [docs/mcd-guide.md](./docs/mcd-guide.md) for the complete guide. Basic structure:

```markdown
# Project MCD

## Overview & Goals
What you're building and why

## Technical Architecture  
Tech stack and infrastructure

## Detailed Implementation
Database schemas, API endpoints, UI components

## Task Breakdown
Ordered list of implementation tasks
```

### 2. Setup Admin Agent

In your AI assistant (Claude Code/Cursor):
```
You are the admin agent.
Admin Token: "your_admin_token_from_server"

Add this MCD to project context:
[paste your MCD]

Then create worker agents for implementation.
```

### 3. Initialize Workers

New window for each worker:
```
You are backend-worker agent.
Your Admin Token: "worker_token_from_admin"

Review your tasks and ask the project RAG 5-7 questions to understand the requirements.

AUTO --worker --memory
```

## Documentation

- [Getting Started](./docs/getting-started.md) - Detailed setup and first project
- [MCD Guide](./docs/mcd-guide.md) - Creating effective project blueprints
- [Theory](./docs/chapter-1-cognitive-empathy.md) - Why this approach works

## Key Features

- **Parallel Development**: Multiple agents work simultaneously
- **Conflict Prevention**: File-level locking prevents overwrites
- **Persistent Context**: Shared memory across all sessions
- **Real-time Monitoring**: Dashboard shows all agent activity
- **Deterministic Results**: Detailed MCDs produce consistent outcomes

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