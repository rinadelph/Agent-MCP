# Agent MCP

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/rinadelph/Agent-MCP)

![Agent Workflow](assets/images/agent-workflow_resized.png)

A modern framework for creating collaborative multi-agent systems. Build, manage, and monitor AI agents that work together on complex projects through an intuitive dashboard interface.

## ⚡ Quick Start (3 Steps)

### 1. Setup & Installation
```bash
git clone https://github.com/rinadelph/Agent-MCP.git
cd Agent-MCP
cp .env.example .env
# Add your OpenAI API key to .env
uv venv && uv pip install -e .
```

### 2. Start MCP Server
```bash
uv run -m agent_mcp.cli --project-dir /path/to/your/project
```
The server will show you instructions to start the dashboard.

### 3. Launch Dashboard
Open a new terminal and run:
```bash
cd agent_mcp/dashboard
npm install  # First time only
npm run dev
```
Open **http://localhost:3847** in your browser.

That's it! 🎉 You now have a powerful multi-agent system running with a modern dashboard interface.

## ✨ What You Get

**🚀 Intuitive Dashboard**: Modern React interface for managing agents, tasks, and project context

**🤖 Multi-Agent Coordination**: Create specialized agents that collaborate automatically

**📊 Real-time Monitoring**: Watch your agents work through interactive charts and graphs

**🧠 Centralized Memory**: Agents share knowledge through a unified context system

**📖 Prompt Library**: Pre-built prompts for common workflows, plus custom prompt creation

**🔍 Task Visualization**: Track progress with detailed task trees and dependency graphs

## 🎯 Core Concepts

### The Dashboard
Your central command center for:
- **Agents**: Monitor active agents and their current tasks
- **Tasks**: Track progress with real-time status updates  
- **Memory**: Manage shared context and knowledge
- **Prompts**: Use standardized workflows or create custom ones
- **System**: Monitor performance and resource usage

### Agent Types
- **Admin Agent**: Orchestrates the overall project and creates other agents
- **Worker Agents**: Specialized agents for specific tasks (frontend, backend, analysis, etc.)

### Workflow
1. Start with a **Main Context Document** (MCD) describing your project
2. **Admin agent** loads the MCD and creates worker agents
3. **Worker agents** automatically find and execute their assigned tasks
4. **Dashboard** provides real-time visibility into all activities

## 📋 Creating Your First Project

### 1. Create a Main Context Document (MCD)
Create an `MCD.md` file in your project with:
- Project overview and goals
- Architecture and components
- API endpoints and data models
- Task breakdown and requirements

See the [MCD-EXAMPLE](./MCD-EXAMPLE) folder for templates.

### 2. Initialize Admin Agent
In your AI assistant (Claude Code, Cursor, etc.):
```
Initialize as an admin agent and add the MCD.md file to project context.
```
The dashboard will provide the exact token and commands to use.

### 3. Create Worker Agents
Tell your admin agent:
```
Create a worker agent with ID "frontend-worker" to implement the login page.
```

### 4. Initialize Workers
Open new AI assistant windows for each worker and use the initialization prompts from the **Prompt Book** in your dashboard.

## 🎨 Dashboard Features

### Agents View
- Monitor all active agents and their status
- View current tasks and completion progress
- Quick access to agent tokens and configuration

### Tasks View  
- Real-time task status updates
- Interactive task trees showing dependencies
- Detailed task information and history

### Memory Management
- Browse and search project context
- Add new memories with intuitive forms
- Edit existing context with smart value editors

### Prompt Book
- Pre-built prompts for common Agent-MCP workflows
- Custom prompt creation with variable templating
- Copy-paste ready prompts for immediate use
- Interactive tutorial for new users

### System Monitoring
- Resource usage and performance metrics
- Server status and connection health
- Activity logs and debugging information

## 🔧 Advanced Usage

### Multiple Projects
Each project gets its own MCP server instance and dashboard:
```bash
# Terminal 1: Project A
uv run -m agent_mcp.cli --project-dir /path/to/project-a --port 8081

# Terminal 2: Project B  
uv run -m agent_mcp.cli --project-dir /path/to/project-b --port 8082
```

### Custom Prompts
Use the dashboard's Prompt Book to:
- Create reusable prompt templates
- Add variable placeholders with `{{VARIABLE_NAME}}`
- Organize prompts by category and tags
- Share prompts across team members

### Integration with AI Assistants
Agent-MCP works with any AI coding assistant:
- **Claude Code**: Native MCP protocol support
- **Cursor**: Use via copy-paste workflow
- **VS Code Extensions**: Compatible with MCP-enabled extensions
- **Custom Integrations**: REST API available for custom tools

## 🛠 Configuration

### Environment Variables
```bash
OPENAI_API_KEY=your_key_here
MCP_DEBUG=false                # Enable debug logging
PORT=8080                      # Default MCP server port
```

### Dashboard Settings
The dashboard automatically:
- Runs on port **3847** (bookmarkable URL)
- Detects and connects to your MCP server
- Saves your preferences locally  
- Updates in real-time with seamless CORS

## 📚 Learning Resources

### Video Tutorials
- [How to add MCD context to Agent MCP](https://www.loom.com/share/16407661b19b477185fe9570c3a6aa3b)

### Example Projects
See the `MCD-EXAMPLE` folder for:
- Web application templates
- API service examples  
- Full-stack project structures

### Prompt Library
The dashboard includes ready-to-use prompts for:
- Admin agent initialization
- Worker agent creation
- Task coordination
- Debugging and troubleshooting

## 🌟 Why Agent-MCP?

**Traditional AI Workflow**: One agent, one conversation, limited context
```
You ↔ AI Assistant → Code
```

**Agent-MCP Workflow**: Coordinated team, shared memory, specialized roles
```
You ↔ Admin Agent ↔ Worker Agents → Coordinated Development
              ↕
        Shared Context & Memory
```

### Benefits
- **Scale Beyond Single Conversations**: No token limits or context loss
- **Specialized Expertise**: Each agent focuses on what it does best  
- **Persistent Memory**: Knowledge accumulates across all interactions
- **Visual Management**: See everything happening in real-time
- **Team Collaboration**: Multiple people can work with the same agent system

## 🤝 Community

<div align="center">
  <a href="https://discord.gg/7Jm7nrhjGn">
    <img src="https://img.shields.io/badge/Discord-Join%20Our%20Community-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Join our Discord community" width="300"/>
  </a>
</div>

Join our Discord to:
- Get help with setup and usage
- Share your projects and workflows
- Discuss multi-agent architectures
- Connect with other developers

<div align="center">
  <h3><a href="https://discord.gg/7Jm7nrhjGn">👉 Join the Discord Server 👈</a></h3>
</div>

[![Verified on MseeP](https://mseep.ai/badge.svg)](https://mseep.ai/app/3350e4c1-32fb-4492-8848-0ae1e87f969b)

---

**Ready to supercharge your development workflow?** Start with the Quick Start guide above and join thousands of developers building the future of AI collaboration.