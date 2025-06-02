# Agent MCP 🚀

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/rinadelph/Agent-MCP)

![Agent Workflow](assets/images/agent-workflow_resized.png)

A framework for creating multi-agent systems using the MCP (Model Context Protocol) for coordinated, efficient AI collaboration.

## 🎯 Quick Install

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Installation
```bash
# Clone the repository
git clone https://github.com/rinadelph/Agent-MCP.git
cd Agent-MCP

# Upgrade pip and setuptools (if needed)
pip install --upgrade pip setuptools>=64

# Install with pip (creates the agent-mcp command)
pip install -e .

# Verify installation
agent-mcp --version
```

That's it! You can now use `agent-mcp` from anywhere.

## 🚀 Quick Start Guide

> **Note**: I recommend using [MultipleCursor](https://github.com/rinadelph/MultipleCursor) to launch different chat windows on the same codebase as shown in the screenshot above.

### 1. Set Up Environment
Copy `.env.example` to `.env` and add your OpenAI API key:
```bash
cp .env.example .env
# Edit .env and add: OPENAI_API_KEY=your-key-here
```

### 2. Start the Server
```bash
# Run from any directory after installation
agent-mcp server --project-dir /path/to/your/project

# Or if running from the Agent-MCP directory:
agent-mcp server --project-dir .
```

Visit http://localhost:8080 to see your dashboard!

### 3. Create Main Context Document (MCD)
- Create a detailed `MCD.md` file in your project with architecture, API routes, data models, etc.
- This can be a single file or multiple files (for complex projects)
- See the [MCD-EXAMPLE](./MCD-EXAMPLE) folder for templates

### 4. Find Your Admin Token
The admin token is stored in your project's database:
1. Install a SQLite viewer extension in your code editor
2. Open `.agent/mcp_state.db` in your project directory
3. Check the `project_context` table for the admin token

### 5. Launch Admin Agent
1. Open your AI coding assistant (Claude Code, Cursor, etc.) in your project folder
2. Ask the AI to "Initialize as an admin agent with this token: [your-token]"
3. Tell the admin agent to add your MCD to the project context:
   ```
   Please add the MCD.md file to the project context. Don't summarize it.
   ```

### 6. Create and Manage Worker Agents
1. Ask your admin agent to create a worker agent:
   ```
   Create a worker agent with ID "frontend-worker" to implement the login page.
   ```
2. Open a new window/session in your AI assistant (same codebase)
3. Initialize the worker with this exact prompt:
   ```
   You are [worker-id] agent, your Admin Token: "[admin-token]"

   Look at your tasks and ask the project RAG agent at least 5-7 questions to understand what you need to do. I want you to critically think when asking a question, then criticize yourself before asking that question. How you criticize yourself is by proposing an idea, criticizing it, and based on that criticism you pull through with that idea.

   AUTO --worker --memory
   ```
4. The worker will automatically find its assigned tasks and start working

## 🎨 Features

- **Multi-agent Orchestration**: Deploy multiple AI agents that work together
- **Intelligent Task Distribution**: Automatically assigns tasks to the right agents  
- **RAG System Built-in**: Index and search your codebase with AI
- **Visual Dashboard**: Monitor and control agents from a beautiful web interface
- **Phase-based Workflows**: Organize work into Foundation → Intelligence → Coordination → Optimization
- **Context Sharing**: Agents share knowledge through the MCP protocol
- **Graph Visualization**: See agent interactions in real-time

## 📸 Dashboard

![Agent MCP Dashboard](assets/images/dashboard_resized.png)

## 🛠️ Commands

```bash
# Server Commands
agent-mcp server                    # Start with web dashboard
agent-mcp server --transport stdio  # Start in MCP mode
agent-mcp server --port 9000        # Use custom port
agent-mcp server --no-tui           # Disable terminal UI

# Project Management
agent-mcp init <project-name>       # Create new project
agent-mcp index                     # Index codebase for RAG

# Database Management  
agent-mcp migrate --check           # Check database version
agent-mcp migrate                   # Run migrations
agent-mcp migrate --config          # Show migration settings

# Other
agent-mcp version                   # Show version info
agent-mcp --help                    # Show all commands
```

## 🔧 Configuration

### Environment Variables
Create a `.env` file in your project:
```env
# Required
OPENAI_API_KEY=sk-...

# Optional
AGENT_MCP_MIGRATION_AUTO_MIGRATE=true
AGENT_MCP_MIGRATION_INTERACTIVE=true
USE_ADVANCED_EMBEDDINGS=true
MCP_RAG_INDEX_INTERVAL_SECONDS=300
```

### Migration Settings
Control database migrations:
```bash
# Show current settings
agent-mcp migrate --config

# Change settings
agent-mcp migrate --set auto_migrate=false
agent-mcp migrate --set min_tasks_per_workstream=5
```

## 📚 Project Planning with MCD

> **Watch the video tutorial:** [How to add MCD context to Agent MCP](https://www.loom.com/share/16407661b19b477185fe9570c3a6aa3b)

Before starting development, create a **Main Context Document (MCD)** - the single source of truth for your application. This document provides:

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

See the `MCD.md` file in this repository for structure and detail level required.

## 🌈 Installation Options

<details>
<summary>Advanced installation methods</summary>

### Using Homebrew (macOS/Linux)
```bash
brew tap agent-mcp/tap
brew install agent-mcp
```

### Using Python pip
```bash
pip install agent-mcp
```

### Build from Source
```bash
git clone https://github.com/rinadelph/Agent-MCP.git
cd Agent-MCP
pip install -e .
```

### Download Binary Directly
Visit [Releases](https://github.com/rinadelph/Agent-MCP/releases) for platform-specific binaries.
</details>

## 🐛 Troubleshooting

<details>
<summary>Common issues and solutions</summary>

### "command not found: agent-mcp"
- Restart your terminal
- Check installation: `which agent-mcp` or `where agent-mcp` (Windows)
- Reinstall: `npm install -g @agent-mcp/cli`

### "OpenAI API key not found"
- Create `.env` file in project directory
- Add: `OPENAI_API_KEY=your-key-here`
- Restart the server

### Port already in use
- Use different port: `agent-mcp server --port 9000`
- Find process: `lsof -i :8080` (Unix) or `netstat -ano | findstr :8080` (Windows)

### Database issues
- Check version: `agent-mcp migrate --check`
- Force migration: `agent-mcp migrate --force`
- Restore from backup in `.agent/` directory
</details>

## 🚀 Advanced Features

### Multi-Root Task Architecture
Agent MCP 2.0 uses an intelligent task organization system:
- **Phases**: Linear progression through Foundation → Intelligence → Coordination → Optimization
- **Workstreams**: Parallel task groups within each phase
- **Hierarchy Preservation**: Maintains parent-child task relationships
- **No Orphans**: Every task belongs to a workstream

### RAG System
- Automatically indexes your codebase
- Supports both standard and advanced embeddings
- SQLite-vec powered for fast searches
- Context-aware responses

### Migration System
- Automatic database upgrades
- Backup creation before migrations
- Configurable behavior
- Version tracking

## 📖 Documentation

- [Getting Started Guide](docs/getting-started.md)
- [Database Migration](docs/DATABASE_MIGRATION.md)
- [API Reference](docs/api-reference.md)
- [Contributing](CONTRIBUTING.md)

## 🤝 Contributing

We love contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📄 License

MIT License - see [LICENSE](LICENSE) file.

---

<p align="center">
  Made with ❤️ by the Agent MCP team
  <br>
  <a href="https://github.com/rinadelph/Agent-MCP">GitHub</a> •
  <a href="https://discord.gg/7Jm7nrhjGn">Discord</a>
</p>