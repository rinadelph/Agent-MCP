# CHANGELOG - Agent-MCP Node.js

## [4.0.1] - 2025-09-01

### 🎨 Major Resource System Overhaul - Visual Enhancement & Security

#### 🔒 Security Fixes
- **CRITICAL**: Removed environment token exposure that was leaking API keys
  - Eliminated `getEnvironmentTokens()` function that exposed sensitive environment variables
  - Removed support for displaying OPENAI_API_KEY, GEMINI_API_KEY, ANTHROPIC_API_KEY, etc.
  - API keys and secrets are now NEVER exposed through MCP resources

#### 🎨 Visual Enhancements - Resource Coloring System

##### Color Implementation Discovery
- Discovered Claude Code's coloring system through systematic testing
- Found that ANSI escape codes in descriptions are rendered as colors
- Implemented bold + colored descriptions for all resource types
- Color system uses: `\x1b[1;COLOR_CODEm` format for bold bright colors

##### Resource Colors by Type

**Agent Resources** (`src/resources/agents.ts`)
- 🟡 **Orange** (`\x1b[1;38;2;255;165;0m`) - Working agents (like Claude Code's agent status)
- 🟢 **Green** (`\x1b[1;92m`) - Ready/active agents
- 🔵 **Cyan** (`\x1b[1;96m`) - Agents with pending tasks
- ⚪ **White** (`\x1b[1;97m`) - Default/idle agents

**Tmux Resources** (`src/resources/tmux.ts`)
- 🟢 **Green** (`\x1b[1;92m`) - Attached/active sessions
- ⚪ **White** (`\x1b[1;37m`) - Detached/inactive sessions
- Removed individual pane resources (too granular)
- Now shows session activity: what's running, windows count, last activity time

**Token Resources** (`src/resources/tokens.ts`)
- 🟠 **Orange** (`\x1b[1;38;2;255;165;0m`) - Admin tokens (matching Claude Code style)
- 🟣 **Magenta** (`\x1b[1;95m`) - Agent tokens
- 🟡 **Yellow** (`\x1b[1;93m`) - Monitor tokens
- 🔵 **Cyan** (`\x1b[1;96m`) - Service tokens
- Added emoji indicators: 🔑 Admin, 🤖 Agent, 👁️ Monitor, ⚙️ Service

#### 📋 New Resource Types

##### Task Resources (`src/resources/tasks.ts`) - NEW
- View active tasks with `@task-{id}`
- Create tasks with `@create-task`
- Color-coded by priority and status:
  - **In Progress**: Red (high), Yellow (medium), Green (low)
  - **Pending**: Magenta (high), Cyan (medium), White (low)
- Shows: Status, Priority, Assignee, Subtask count
- Task details include: Description, Dependencies, Parent task, Subtasks, Notes

##### Create Agent Resources (`src/resources/createAgent.ts`) - NEW
Simplified to 3 focused agent types:
1. **`@create-agent`** - Normal task-based agents
   - Works through hierarchical tasks
   - Progress tracking
   - Task dependencies
   
2. **`@create-background`** - Autonomous agents
   - No task structure needed
   - Continuous operation
   - General assistance
   
3. **`@create-monitor`** - Rule-based monitors
   - IF-THEN rule format
   - Event-driven actions
   - Condition monitoring

#### 🔧 Resource Description Improvements

##### Compact, Informative Descriptions
- **Before**: `agent - agent token - Background agent token for file-monitor-agent (terminated)`
- **After**: `🤖 agent` or `🔄 working on: task-name` or `✅ 5 done`

##### Tmux Session Descriptions
- **Before**: `tmux session - 2 windows, 80x24`
- **After**: `🟢 npm run dev • 2w • active 3m` (shows what's running, window count, activity)

##### Token Descriptions
- **Before**: `admin token - Primary admin token for Agent-MCP system`
- **After**: `🔑 admin` (simple emoji + role)

#### 🏗️ Architecture Changes

##### Removed Test Resources
- Deleted `src/resources/testResources.ts` 
- Removed test resource registration from server
- Production-ready, focused on real resources only

##### URI Structure Standardization
- Agents: `agent://{agent-id}`
- Tasks: `task://{task-id}`
- Tmux: `tmux://{session-name}`
- Tokens: `token://{token-name}`
- Create templates: `create://{template-type}`

##### Server Registration Updates (`src/examples/server/agentMcpServer.ts`)
- Added task resource registration
- Added create agent template registration
- Fixed URI parsing for new format
- Improved logging with emojis for each resource type

#### 🐛 Bug Fixes
- Fixed agent URI parsing to handle new simplified format
- Fixed tmux session activity time calculation
- Removed buggy pane-level resources (kept session info only)
- Fixed token retrieval for agent tokens

#### 📝 Documentation
- Added comprehensive examples in create templates
- Clear command templates for each agent type
- Tips and best practices for agent creation
- IF-THEN rule format documentation for monitors

#### 🎯 Key Improvements Summary
1. **Security**: No more API key exposure
2. **Visual**: Bold, colored resource descriptions
3. **Organization**: Clear separation between viewing and creating
4. **Simplicity**: 3 focused agent types instead of vague categories
5. **Functionality**: Tasks as browsable and creatable resources
6. **Compactness**: Shorter, more informative descriptions
7. **Activity**: Shows what's actually running in tmux sessions

### Technical Details

#### ANSI Color Codes Used
```
Bold Bright Red:     \x1b[1;91m
Bold Bright Green:   \x1b[1;92m  
Bold Bright Yellow:  \x1b[1;93m
Bold Bright Blue:    \x1b[1;94m
Bold Bright Magenta: \x1b[1;95m
Bold Bright Cyan:    \x1b[1;96m
Bold White:          \x1b[1;37m
Bold Orange (RGB):   \x1b[1;38;2;255;165;0m
Reset:               \x1b[0m
```

#### Files Modified
- `src/resources/agents.ts` - Color implementation, compact descriptions
- `src/resources/tmux.ts` - Session focus, activity monitoring
- `src/resources/tokens.ts` - Security fix, emoji indicators
- `src/resources/tasks.ts` - NEW: Task viewing and creation
- `src/resources/createAgent.ts` - NEW: Agent creation templates
- `src/examples/server/agentMcpServer.ts` - Resource registration
- Removed: `src/resources/testResources.ts`

#### Dependencies
No new dependencies added. Uses existing:
- Better SQLite3 for database
- Node.js child_process for tmux interaction
- Built-in ANSI escape sequences for coloring

---

## Previous Versions

### [4.0.0] - 2025-09-01
- Initial Agent-MCP implementation
- Multi-agent collaboration protocol
- Task management system
- RAG integration
- Tmux session management