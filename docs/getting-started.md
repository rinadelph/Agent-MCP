# Getting Started with Agent-MCP

Welcome to Agent-MCP! This guide will take you from installation to your first successful multi-agent collaboration workflow.

## 📋 Prerequisites

### Required Knowledge
- **Basic programming experience** (any language)
- **Command line familiarity** (basic terminal commands)
- **Git basics** (clone, commit, push)
- **AI assistant experience** (Claude Code, Cursor, or similar)

### Required Software
- **Python 3.8+** with pip/uv
- **Node.js 18+** with npm
- **Git** for version control
- **AI Coding Assistant** (Claude Code recommended)

### Recommended Setup
- **VS Code** with SQLite Viewer extension
- **Terminal multiplexer** (tmux or similar)
- **OpenAI API key** for embeddings

---

## ⚡ Quick Install (5 Minutes)

### 1. Clone and Setup
```bash
# Clone the repository
git clone https://github.com/rinadelph/Agent-MCP.git
cd Agent-MCP

# Setup environment
cp .env.example .env
# Edit .env and add your OpenAI API key

# Install dependencies
uv venv && uv pip install -e .
```

### 2. Start MCP Server
```bash
# Start the MCP server (replace with your project path)
uv run -m agent_mcp.cli --project-dir /path/to/your/project

# You'll see output like:
# 🤖 Admin Token: abc123def456...
# 📡 Server running on http://localhost:8080
# 📊 Dashboard: Start with 'cd agent_mcp/dashboard && npm run dev'
```

### 3. Launch Dashboard (Optional but Recommended)
```bash
# In a new terminal
cd agent_mcp/dashboard
npm install  # First time only
npm run dev

# Dashboard available at http://localhost:3847
```

### 4. Connect AI Assistant
**For Claude Code**, add to your `mcp.json`:
```json
{
  "mcpServers": {
    "Agent-MCP": {
      "url": "http://localhost:8080/sse"
    }
  }
}
```

**🎉 You're ready!** The server is running and your AI assistant can connect.

---

## 🎯 Your First Multi-Agent Project

Let's build a simple task management system to demonstrate Agent-MCP's capabilities.

### Step 1: Create Your Project Directory
```bash
mkdir my-task-manager
cd my-task-manager

# Initialize basic structure
touch README.md
mkdir src docs tests
```

### Step 2: Create Your First MCD

Create `MCD.md` in your project root:

````markdown
# Task Manager MCD

## 🎯 Overview & Goals  
**Project Vision**: Build a simple task management web application where users can create, update, and delete tasks with a clean, responsive interface.

**Target Users**: Individual users who need a simple, distraction-free task tracker

**Core Features**: 
1. Create tasks with title and description
2. Mark tasks as complete/incomplete
3. Delete tasks
4. Responsive web interface
5. Local storage persistence

**Success Criteria**: 
- Users can add a task in under 5 seconds
- Task status updates are immediate
- Interface works on mobile and desktop
- No data loss on page refresh

## 🏗️ Technical Architecture
**Frontend**: 
- Vanilla JavaScript (no framework complexity)
- HTML5 with semantic structure
- CSS3 with Flexbox/Grid for responsive design
- LocalStorage for data persistence

**Backend**: 
- None required (client-side only for simplicity)
- Future: Node.js + Express for multi-user features

**APIs**: 
- LocalStorage API for data persistence
- Future: REST API for server features

**Technology Justification**: 
- Vanilla JS for simplicity and learning
- LocalStorage for immediate functionality without backend complexity
- Responsive design for universal accessibility

## 📋 Detailed Implementation

### Data Structure
```javascript
// Task object structure
interface Task {
  id: string;          // UUID for unique identification
  title: string;       // Required, max 100 characters
  description: string; // Optional, max 500 characters  
  completed: boolean;  // Task completion status
  createdAt: Date;     // Creation timestamp
  updatedAt: Date;     // Last modification timestamp
}

// Storage structure
const tasks = []; // Array of Task objects in localStorage
```

### Core Functions
```javascript
// Required functions to implement
function createTask(title, description) { }
function updateTask(id, updates) { }
function deleteTask(id) { }
function toggleTaskComplete(id) { }
function loadTasks() { }
function saveTasks() { }
function renderTasks() { }
```

### HTML Structure
```html
<!DOCTYPE html>
<html>
<head>
  <title>Task Manager</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
  <div class="container">
    <header>
      <h1>My Task Manager</h1>
    </header>
    
    <section class="task-form">
      <input type="text" id="task-title" placeholder="Task title...">
      <textarea id="task-description" placeholder="Description (optional)"></textarea>
      <button id="add-task">Add Task</button>
    </section>
    
    <section class="task-list">
      <div id="tasks-container">
        <!-- Tasks rendered here -->
      </div>
    </section>
  </div>
</body>
</html>
```

## 📁 File Structure & Organization
```
my-task-manager/
├── index.html           # Main HTML file
├── css/
│   └── styles.css      # All styling
├── js/
│   ├── app.js          # Main application logic
│   ├── storage.js      # LocalStorage utilities
│   └── utils.js        # Helper functions
├── tests/
│   └── app.test.html   # Simple HTML-based tests
└── docs/
    └── README.md       # Usage instructions
```

## ✅ Task Breakdown & Implementation Plan

### Phase 1: Core Structure (30 minutes)
**1.1 HTML Foundation**
- Create semantic HTML structure with proper accessibility
- Include meta tags for responsive design
- **Acceptance**: HTML validates and displays correctly

**1.2 CSS Styling**
- Implement responsive layout with Flexbox
- Create clean, modern styling with good contrast
- **Acceptance**: Interface looks good on mobile and desktop

### Phase 2: JavaScript Functionality (45 minutes)
**2.1 Data Management**
- Implement localStorage utilities for data persistence
- Create task CRUD operations
- **Acceptance**: Tasks persist across page refreshes

**2.2 User Interface**
- Implement task creation form handling
- Create dynamic task list rendering
- Add task completion toggle functionality
- **Acceptance**: All core features work without errors

### Phase 3: Polish (15 minutes)
**3.1 User Experience**
- Add form validation and user feedback
- Implement keyboard shortcuts (Enter to add task)
- **Acceptance**: Interface is intuitive and responsive

## 🔗 Integration & Dependencies
**Internal Dependencies**: 
- app.js depends on storage.js and utils.js
- All JS files depend on DOM structure in index.html

**External Dependencies**: 
- None (vanilla JavaScript only)

## 🧪 Testing & Validation Strategy
**Manual Testing**:
- Create task and verify it appears
- Mark task complete and verify status change
- Delete task and verify removal
- Refresh page and verify persistence
- Test on mobile device for responsiveness

**Acceptance Criteria**:
- All CRUD operations work correctly
- Data persists across browser sessions
- No JavaScript errors in console
- Interface is fully responsive
````

### Step 3: Initialize Admin Agent

In your AI assistant (Claude Code/Cursor), use your admin token:

```
You are the admin agent for the Task Manager project.
Admin Token: "your_admin_token_from_server_startup"

TASK: Add the entire MCD to project context - every detail, don't summarize anything.

[Paste your complete MCD here]

After adding context, create a worker agent to start implementation.
```

### Step 4: Create Worker Agent

When the admin agent creates a worker, initialize it in a new window:

```
You are frontend-worker agent.
Your Admin Token: "worker_token_from_admin_response"

Look at your assigned tasks and ask the project RAG agent 5-7 critical questions to understand:
- What exactly needs to be implemented
- What file structure to use  
- How the task management functionality should work

Think critically about each question before asking.

AUTO --worker --memory
```

### Step 5: Watch the Magic Happen

The worker agent will:
1. ✅ Query the project RAG for context
2. ✅ Review its assigned tasks  
3. ✅ Create the HTML structure
4. ✅ Implement CSS styling
5. ✅ Build JavaScript functionality
6. ✅ Test the implementation
7. ✅ Update task status and document progress

### Step 6: Review and Iterate

Use the dashboard to:
- 📊 Monitor agent progress in real-time
- 📋 Track task completion
- 🧠 View project context and agent communications
- 🔍 Debug any issues that arise

---

## 🎓 Learning Path

### After Your First Project
1. **Study the MCD** - Review how it guided the agent's work
2. **Explore the Dashboard** - Understand the visualizations
3. **Try Variations** - Modify the MCD and see how agents adapt
4. **Join Community** - Share your experience and learn from others

### Next Steps
1. **[The Complete MCD Guide](./mcd-guide.md)** - Master MCD creation
2. **[Agent Coordination Patterns](./agent-patterns.md)** - Learn advanced workflows
3. **[Example MCDs](./example-mcds/README.md)** - Study real-world examples

---

## 🔧 Troubleshooting Common Issues

### ❌ "Cannot find admin token"
**Solution**: Check the MCP server startup logs in your terminal. The token is displayed when the server starts.

### ❌ "Agent can't access project context"  
**Solution**: Make sure the admin agent successfully added the MCD to project context. Check the dashboard's Memory section.

### ❌ "Worker agent doesn't understand tasks"
**Solution**: Your MCD might be too vague. Add more specific implementation details and acceptance criteria.

### ❌ "Agents are not coordinating"
**Solution**: Ensure you're using the correct tokens (admin vs worker) and that the --worker flag is included in worker initialization.

### ❌ "Dashboard won't load"
**Solution**: 
```bash
# Check Node.js version (needs 18+)
node --version  

# Reinstall dependencies in dashboard directory
cd agent_mcp/dashboard
rm -rf node_modules package-lock.json
npm install
npm run dev
```

### ❌ "MCP server connection failed"
**Solution**: Verify the server is running on the correct port and that your AI assistant can reach `http://localhost:8080/sse`.

---

## 💡 Pro Tips for Success

### 1. Start Simple
- Begin with small, focused projects
- Master the basic workflow before attempting complex systems
- Use the provided examples as templates

### 2. Write Detailed MCDs
- The more specific your MCD, the better your results
- Include exact file names, function signatures, and acceptance criteria
- Don't assume the AI knows your preferences

### 3. Use the Dashboard
- Monitor agent activity in real-time
- Review project context to ensure it's complete
- Watch for patterns in agent coordination

### 4. Iterate and Improve
- Start with a basic MCD and refine it
- Learn from agent questions and confusion
- Update MCDs based on implementation experience

### 5. Join the Community
- Share your MCDs and get feedback
- Learn from other developers' experiences
- Contribute improvements and patterns

---

## 🚀 What's Next?

### Expand Your Skills
1. **Create More Complex Projects** - Try building APIs, databases, or full-stack applications
2. **Experiment with Agent Specialization** - Create frontend-only, backend-only, or testing-focused agents
3. **Explore Advanced Patterns** - Use multiple coordinated agents for larger projects

### Contribute to Agent-MCP
1. **Share Your MCDs** - Help others learn from your examples
2. **Report Issues** - Help improve the platform
3. **Suggest Features** - Shape the future of AI collaboration

### Stay Connected
- **[Discord Community](https://discord.gg/7Jm7nrhjGn)** - Daily discussions and support
- **[GitHub](https://github.com/rinadelph/Agent-MCP)** - Source code and issue tracking
- **[Documentation](./README.md)** - Comprehensive guides and references

---

**Congratulations! You've successfully set up Agent-MCP and completed your first multi-agent project. You're now ready to build amazing things with coordinated AI intelligence.**

**[Continue with The Complete MCD Guide →](./mcd-guide.md)**
