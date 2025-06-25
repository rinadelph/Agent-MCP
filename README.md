# 🤖 Agent-MCP: Multi-Agent Collaboration Protocol

[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/rinadelph/Agent-MCP)
[![Responsive Banner](https://img.shields.io/badge/Responsive-Banner%20System-pink)](.)
[![Multi-Agent](https://img.shields.io/badge/Multi--Agent-Coordination-cyan)](.)
[![Real-time](https://img.shields.io/badge/Real--time-Dashboard-blue)](.)

![Agent Workflow](assets/images/agent-workflow_resized.png)

> **"If you want to go fast, go alone. If you want to go far, go together."** 

**Agent-MCP** revolutionizes AI-assisted development by orchestrating multiple specialized AI agents that work together intelligently on complex software projects - **no more context loss, no more overwrites, no more confusion.**

---

## 🎯 What Makes Agent-MCP Different?

### **Traditional AI Development** 😵‍💫
```
Single AI → Gets confused on large codebases
           → Loses context over time  
           → Overwrites previous work
           → Limited by conversation length
```

### **Agent-MCP Approach** ✨
```
👑 Admin Agent    → Coordinates & assigns tasks
🛠️ Worker Agents  → Specialized implementations  
🧠 Shared Memory  → Persistent context across all agents
📊 Visual Dashboard → Real-time monitoring & control
🔒 File Protection → Prevents conflicts between agents
```

**Result**: *Build enterprise-level applications with coordinated AI intelligence*

---

## ⚡ Quick Start (3 Commands)

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
# 🎉 Server shows admin token and instructions
```

### 3. Launch Dashboard
```bash
cd agent_mcp/dashboard && npm install && npm run dev
# 📊 Dashboard available at http://localhost:3847
```

**That's it!** You now have an intelligent multi-agent system with a beautiful dashboard. 🚀

---

## 📖 Step-by-Step Workflow (The Secret Sauce)

> *Based on real user feedback and proven workflows from production teams*

### Phase 1: Create Your Master Context Document (MCD)

The MCD is your **"application blueprint"** - think of it as writing a detailed book about your app before building it.

**Create `MCD.md` in your project:**
```markdown
# My Project MCD

## 🎯 Overview & Goals  
**Project Vision**: [What you're building - be specific]
**Target Users**: [Who will use this]
**Core Features**: [Main functionality - prioritized list]
**Success Criteria**: [How you'll know it's working]

## 🏗️ Technical Architecture
**Backend**: [Framework, database, hosting]
**Frontend**: [Framework, state management, styling]  
**APIs**: [External services, authentication]
**Deployment**: [CI/CD, hosting platform]

## 📋 Detailed Implementation
**Database Schema**: [Tables, relationships, indexes]
**API Endpoints**: [Methods, routes, request/response]
**UI Components**: [Pages, components, user flows]
**File Structure**: [Directories, naming conventions]

## ✅ Task Breakdown
1. **Project Setup**: Initialize structure & dependencies
2. **Backend Core**: Database, auth, core APIs
3. **Frontend Foundation**: UI components, routing
4. **Feature Implementation**: Core features one by one
5. **Integration & Testing**: Connect everything
6. **Deployment**: Launch and monitor
```

> 💡 **Pro Tip**: Use **Gemini 2.0 Flash** or **Claude** for deep research. Ask them: *"Help me create a comprehensive MCD for [your project]. Research the latest best practices for [your tech stack] and break down implementation into granular, actionable tasks."*

### Phase 2: Initialize Admin Agent (The Conductor)

**In Claude Code/Cursor, paste your admin token:**
```
You are the admin agent for this project.
Admin Token: "your_admin_token_from_server_startup"

TASK: Add the entire MCD to project context - every detail, don't summarize anything.

[Paste your complete MCD here]

After adding context, create a worker agent to start implementation.
```

### Phase 3: Deploy Worker Agents (The Specialists)

**Admin creates workers:**
```
Create a worker agent with ID "backend-worker" to implement the API endpoints.
Create a worker agent with ID "frontend-worker" to build the UI components.
```

**Initialize each worker (new Claude Code/Cursor window):**
```
You are backend-worker agent.
Your Admin Token: "worker_token_from_admin_response"

Look at your assigned tasks and ask the project RAG agent 5-7 critical questions to understand:
- What exactly needs to be implemented
- What dependencies and architecture to use
- How this fits with the overall project vision

Think critically about each question before asking.

AUTO --worker --memory
```

### Phase 4: Agent Coordination (The Magic)

**Automatic workflow:**
1. **Worker queries RAG**: "What backend framework should I use?"
2. **Worker checks tasks**: Reviews assigned implementation tasks
3. **Worker checks files**: Ensures no other agent is editing same files
4. **Worker implements**: Creates code with intelligent precision
5. **Worker documents**: Adds detailed notes about implementation
6. **Worker reports**: Updates task status and notifies admin

**Result**: Multiple agents work simultaneously without conflicts! 🎯

---

## 🎨 Dashboard Features (Your Mission Control)

### 🤖 Agents View
- **Real-time status** of all active agents
- **Current tasks** each agent is working on
- **Quick access** to agent tokens and commands
- **Performance metrics** and activity history

### 📋 Tasks View  
- **Interactive task trees** showing dependencies
- **Real-time progress** updates as agents work
- **Detailed task history** and implementation notes
- **Visual workflow** from planning to completion

### 🧠 Memory Management
- **Browse project context** with smart search
- **Add new memories** with intuitive forms
- **Edit existing context** with rich text editors
- **RAG-powered retrieval** for intelligent context

### 📖 Prompt Book (Game Changer!)
- **Pre-built prompts** for every workflow step
- **Custom prompt creation** with variables
- **Copy-paste ready** commands for instant use
- **Interactive tutorial** for new users

### 📊 System Monitoring
- **Resource usage** and performance metrics
- **Connection health** and server status
- **Activity logs** and debugging tools
- **Beautiful visualizations** of agent coordination

---

## 🛠️ Advanced Power User Features

### 🎯 Specialized Agent Modes
```bash
AUTO --worker --memory      # Standard worker with memory tools
AUTO --worker --playwright  # Frontend worker with screenshot testing
AUTO --memory               # Research and context management mode
```

### 🔄 Multi-Project Management
```bash
# Terminal 1: E-commerce Platform
uv run -m agent_mcp.cli --project-dir /code/ecommerce --port 8081

# Terminal 2: Mobile App Backend  
uv run -m agent_mcp.cli --project-dir /code/mobile-api --port 8082

# Terminal 3: Analytics Dashboard
uv run -m agent_mcp.cli --project-dir /code/analytics --port 8083
```

### 🧠 Custom Prompt Templates
Create reusable workflows in the dashboard:
```
Template: "API Endpoint Implementation"
Variables: {{ENDPOINT_NAME}}, {{HTTP_METHOD}}, {{RESPONSE_FORMAT}}
Usage: Standardize API development across all workers
```

### 🔒 Team Collaboration
- **Shared agent systems** for team coordination
- **Real-time conflict prevention** between team members
- **Centralized project memory** accessible to all
- **Audit trails** of all agent activities

---

## 🚀 Real-World Success Stories

### 💼 **SaaS Platform (2 weeks → Production)**
*"Used Agent-MCP with 4 coordinated agents (backend, frontend, database, testing) to build our entire customer portal. What used to take 3 months took 2 weeks."*

### 🏢 **Enterprise Migration (Legacy → Modern)**
*"Migrated a 10-year-old monolith to microservices using 8 specialized agents. Each agent handled a different service migration with perfect coordination."*

### 🎯 **Feature Development (1 week → 1 day)**
*"New features now ship in days instead of weeks. Agents maintain perfect context across sprints and coordinate seamlessly."*

---

## 🔧 Troubleshooting (Common Issues Solved)

### ❌ **"Can't find admin token"**
**Solution**: Check server startup logs in terminal, or open `.agent/database.db` with SQLite Viewer extension in VS Code

### ❌ **"Worker agent can't access tasks"**  
**Solution**: You're using admin token instead of worker token. Copy the worker token from admin agent's response.

### ❌ **"Agents are overwriting each other's work"**
**Solution**: Ensure agents use `check_file_status` tool before editing. This is automatic with `--worker` mode.

### ❌ **"Context not found"**
**Solution**: Admin agent needs to add MCD to project context first. Don't summarize - paste the entire MCD.

### ❌ **"Dashboard won't load"**
**Solution**: 
```bash
# Check Node.js version (needs 18+)
node --version  

# Reinstall dependencies
cd agent_mcp/dashboard
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### ❌ **"Agents seem confused about project"**
**Solution**: Your MCD needs more detail. Add specific file structures, API schemas, and implementation steps.

---

## ✨ Beautiful Terminal Experience

Agent-MCP features an **intelligent responsive banner system** that adapts to any terminal size:

- **🖥️ Large terminals (80+ chars)**: Full ASCII art banner
- **💻 Medium terminals (50-79 chars)**: Split banner (AGENT / MCP)  
- **📱 Small terminals (35-49 chars)**: Compact design
- **⌚ Tiny terminals (<35 chars)**: Progressive miniaturization
- **📟 Minimal terminals (<15 chars)**: Clean text fallback

*Beautiful pink-to-cyan gradients maintained across all sizes with surgical precision!*

---

## 🎓 Learning Resources

### 📹 **Video Tutorials**
- [How to add MCD context to Agent MCP](https://www.loom.com/share/16407661b19b477185fe9570c3a6aa3b)
- [Multi-agent coordination walkthrough](https://github.com/rinadelph/Agent-MCP/discussions)

### 📚 **Example Projects**
- **E-commerce Platform**: Complete online store with payment processing
- **Task Management SaaS**: Team collaboration with real-time sync  
- **API Microservices**: Scalable backend with multiple services
- **React Dashboard**: Analytics platform with complex visualizations

### 🎯 **Prompt Library**
Ready-to-use prompts for:
- **Admin agent initialization** and MCD integration
- **Worker agent creation** and task assignment
- **Debugging workflows** and error resolution
- **Team coordination** and conflict resolution

---

## 🤝 Community & Support

<div align="center">
  <a href="https://discord.gg/7Jm7nrhjGn">
    <img src="https://img.shields.io/badge/Discord-Join%20Our%20Community-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Join our Discord community" width="300"/>
  </a>
</div>

**Join 1000+ developers** using Agent-MCP for:
- 🆘 **Setup help** and troubleshooting
- 🚀 **Project showcases** and workflow sharing  
- 🧠 **Architecture discussions** and best practices
- 🤝 **Team collaboration** and knowledge exchange

<div align="center">
  <h3><a href="https://discord.gg/7Jm7nrhjGn">👉 Join the Discord Server 👈</a></h3>
</div>

[![Verified on MseeP](https://mseep.ai/badge.svg)](https://mseep.ai/app/3350e4c1-32fb-4492-8848-0ae1e87f969b)

---

## 🌟 Why Developers Love Agent-MCP

### **Before Agent-MCP** 😤
- Single AI gets overwhelmed by large codebases
- Context gets lost after long conversations  
- No coordination between coding sessions
- Constant overwrites and conflicts
- Starting over every time

### **After Agent-MCP** 🤩
- **Specialized intelligence** for every part of your stack
- **Persistent memory** that never forgets project context
- **Automatic coordination** prevents all conflicts
- **Visual dashboard** shows everything happening
- **Team collaboration** that actually works

---

## 🚀 Ready to Transform Your Development?

**Agent-MCP isn't just another tool - it's the future of software development.**

Experience the power of coordinated AI intelligence working on your projects while you maintain full control and visibility.

### 🎯 **Next Steps:**
1. **[⚡ Quick Start](#-quick-start-3-commands)** - Get running in 5 minutes
2. **[📖 Follow the Workflow](#-step-by-step-workflow-the-secret-sauce)** - Build your first project  
3. **[🤝 Join the Community](#-community--support)** - Learn from other developers
4. **[🚀 Share Your Success](#-real-world-success-stories)** - Show what you built

---

<div align="center">

**Built with ❤️ for the future of intelligent software development**

*Coordinated AI • Shared Intelligence • Unlimited Potential*

[![GitHub stars](https://img.shields.io/github/stars/rinadelph/Agent-MCP?style=social)](https://github.com/rinadelph/Agent-MCP)
[![Follow on Twitter](https://img.shields.io/twitter/follow/rinadelph?style=social)](https://twitter.com/rinadelph)

</div>