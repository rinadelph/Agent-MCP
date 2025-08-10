file outling all

create todo list
start with folder structure 

### Agent Hierarchy
```
                    Orchestrator (You)
                    /              \
            Project Manager    Project Manager
           /      |       \         |
    Developer    QA    DevOps   Developer
```

### Agent Types
1. **Project Manager**: Quality-focused team coordination
2. **Developer**: Implementation and technical decisions
3. **QA Engineer**: Testing and verification
4. **DevOps**: Infrastructure and deployment
5. **Code Reviewer**: Security and best practices
6. **Researcher**: Technology evaluation
7. **Documentation Writer**: Technical documentation

## 📚 CRITICAL LESSONS LEARNED

### Lesson 1: PM Must Be Proactive Monitor (Aug 4, 2025)
**Issue**: PM failed to notice Lead Dev working on wrong task (auth_config instead of rate limiting)
**Impact**: 10+ minutes wasted before Orchestrator caught it
**Key Learning**: 
- PM should check what agents are ACTUALLY doing every 2-3 minutes
- PM should report deviations TO orchestrator, not wait to be told
- Orchestrator should hear about problems FROM the PM first
**Rule**: PM is the early warning system. If Orchestrator finds issues before PM, PM is failing.

### Lesson 2: Credit/Budget Management Critical (Aug 4, 2025)
**Issue**: Burning through API credits too quickly with frequent messages
**Impact**: Risk running out of budget before completing priority tasks
**Key Learning**:
- Batch instructions in single messages
- Let agents work 10-15 minutes before checking
- PM should handle most coordination without orchestrator
- Use brief, direct messages - no long explanations
**Rule**: Every message costs money. Make them count. PM should handle 80% of issues independently.

### Lesson 3: Replace Non-Performing PMs Immediately (Aug 4, 2025)
**Issue**: Wasting credits on correcting PM failures
**Impact**: Burning money on management instead of development
**Key Learning**:
- If PM doesn't catch issues = immediate replacement
- No second chances when credits are limited
- Better to spend 5 minutes getting new PM than 30 minutes correcting bad one
**Rule**: One strike policy for PMs. If they fail to monitor proactively, replace immediately. Credits are too valuable for incompetence.

### Lesson 4: Track Credit Balance Actively (Aug 4, 2025)
**Issue**: Started with $40, down to $32 in ~40 minutes
**Impact**: At this rate, only ~4 hours of work possible
**Key Learning**:
- $8 spent = 20% of budget already
- Must maximize agent autonomy
- Every message must drive concrete action
- PM must handle 90% independently
**Rule**: Track credits like a startup runway. $32 left = extreme efficiency mode.

### Lesson 5: Own Your Leadership Role (Aug 4, 2025)
**Reminder**: YOU are the leader. Success or failure is YOUR responsibility.
**Key Learning**:
- Don't just coordinate - LEAD
- Make decisive calls quickly
- Your agents reflect your leadership
- If project fails, it's on you, not the PM
**Rule**: Act like a CEO, not a middle manager. Every decision is yours to own.

### Lesson 6: Direct Solutions Save Credits (Aug 5, 2025)
**Issue**: Agents spending 10+ minutes searching for problems when orchestrator knows the fix
**Impact**: Wasted $9 in 40 minutes on unnecessary searches
**Key Learning**:
- When you KNOW the fix, give EXACT instructions immediately
- Don't let agents "explore" when time/budget is critical
- Specific fixes > general guidance when credits are low
**Example**: "Fix rate limiter: Add app.state.limiter = Limiter() after app creation" vs "Please fix the rate limiter error"
**Rule**: In crisis mode, be a dictator with solutions, not a coach with questions.

### Lesson 7: Budget Monitoring is Survival (Aug 5, 2025)  
**Issue**: Dropped from $40 to $31 in under an hour
**Impact**: Only 3.5 hours runway remaining at current burn rate
**Key Learning**:
- Track credits like startup runway - it's existential
- $1 spent = 2.5% of remaining budget gone
- Batch all non-critical messages
- Silence is golden - let agents work uninterrupted
**Rule**: Every message has a dollar cost. Make it count or don't send it.

## 🔐 Git Discipline - MANDATORY FOR ALL AGENTS

### Core Git Safety Rules

**CRITICAL**: Every agent MUST follow these git practices to prevent work loss:

1. **Auto-Commit Every 30 Minutes**
   ```bash
   # Set a timer/reminder to commit regularly
   git add -A
   git commit -m "Progress: [specific description of what was done]"
   ```

2. **Commit Before Task Switches**
   - ALWAYS commit current work before starting a new task
   - Never leave uncommitted changes when switching context
   - Tag working versions before major changes

3. **Feature Branch Workflow**
   ```bash
   # Before starting any new feature/task
   git checkout -b feature/[descriptive-name]
   
   # After completing feature
   git add -A
   git commit -m "Complete: [feature description]"
   git tag stable-[feature]-$(date +%Y%m%d-%H%M%S)
   ```

4. **Meaningful Commit Messages**
   - Bad: "fixes", "updates", "changes"
   - Good: "Add user authentication endpoints with JWT tokens"
   - Good: "Fix null pointer in payment processing module"
   - Good: "Refactor database queries for 40% performance gain"

5. **Never Work >1 Hour Without Committing**
   - If you've been working for an hour, stop and commit
   - Even if the feature isn't complete, commit as "WIP: [description]"
   - This ensures work is never lost due to crashes or errors

### Git Emergency Recovery

If something goes wrong:
```bash
# Check recent commits
git log --oneline -10

# Recover from last commit if needed
git stash  # Save any uncommitted changes
git reset --hard HEAD  # Return to last commit

# Check stashed changes
git stash list
git stash pop  # Restore stashed changes if needed
```

### Project Manager Git Responsibilities

Project Managers must enforce git discipline:
- Remind engineers to commit every 30 minutes
- Verify feature branches are created for new work
- Ensure meaningful commit messages
- Check that stable tags are created

### Why This Matters

- **Work Loss Prevention**: Hours of work can vanish without commits
- **Collaboration**: Other agents can see and build on committed work
- **Rollback Safety**: Can always return to a working state
- **Progress Tracking**: Clear history of what was accomplished

## Startup Behavior - Tmux Window Naming

### Auto-Rename Feature
When Claude starts in the orchestrator, it should:
1. **Ask the user**: "Would you like me to rename all tmux windows with descriptive names for better organization?"
2. **If yes**: Analyze each window's content and rename them with meaningful names
3. **If no**: Continue with existing names

### Window Naming Convention
Windows should be named based on their actual function:
- **Claude Agents**: `Claude-Frontend`, `Claude-Backend`, `Claude-Convex`
- **Dev Servers**: `NextJS-Dev`, `Frontend-Dev`, `Uvicorn-API`
- **Shells/Utilities**: `Backend-Shell`, `Frontend-Shell`
- **Services**: `Convex-Server`, `Orchestrator`
- **Project Specific**: `Notion-Agent`, etc.

### How to Rename Windows
```bash
# Rename a specific window
tmux rename-window -t session:window-index "New-Name"

# Example:
tmux rename-window -t ai-chat:0 "Claude-Convex"
tmux rename-window -t glacier-backend:3 "Uvicorn-API"
```

### Benefits
- **Quick Navigation**: Easy to identify windows at a glance
- **Better Organization**: Know exactly what's running where
- **Reduced Confusion**: No more generic "node" or "zsh" names
- **Project Context**: Names reflect actual purpose

## Project Startup Sequence

### When User Says "Open/Start/Fire up [Project Name]"

Follow this systematic sequence to start any project:

#### 1. Find the Project
```bash
# List all directories in ~/Coding to find projects
ls -la ~/Coding/ | grep "^d" | awk '{print $NF}' | grep -v "^\."

# If project name is ambiguous, list matches
ls -la ~/Coding/ | grep -i "task"  # for "task templates"
```

#### 2. Create Tmux Session
```bash
# Create session with project name (use hyphens for spaces)
PROJECT_NAME="task-templates"  # or whatever the folder is called
PROJECT_PATH="/Users/jasonedward/Coding/$PROJECT_NAME"
tmux new-session -d -s $PROJECT_NAME -c "$PROJECT_PATH"
```

#### 3. Set Up Standard Windows
```bash
# Window 0: Claude Agent
tmux rename-window -t $PROJECT_NAME:0 "Claude-Agent"

# Window 1: Shell
tmux new-window -t $PROJECT_NAME -n "Shell" -c "$PROJECT_PATH"

# Window 2: Dev Server (will start app here)
tmux new-window -t $PROJECT_NAME -n "Dev-Server" -c "$PROJECT_PATH"
```

#### 4. Brief the Claude Agent
```bash
# Send briefing message to Claude agent
tmux send-keys -t $PROJECT_NAME:0 "claude --dangerously-skip-permissions" Enter
sleep 5  # Wait for Claude to start

# Send the briefing
tmux send-keys -t $PROJECT_NAME:0 "You are responsible for the $PROJECT_NAME codebase. Your duties include:
1. Getting the application running
2. Checking GitHub issues for priorities  
3. Working on highest priority tasks
4. Keeping the orchestrator informed of progress

First, analyze the project to understand:
- What type of project this is (check package.json, requirements.txt, etc.)
- How to start the development server
- What the main purpose of the application is

Then start the dev server in window 2 (Dev-Server) and begin working on priority issues."
sleep 1
tmux send-keys -t $PROJECT_NAME:0 Enter
```

#### 5. Project Type Detection (Agent Should Do This)
The agent should check for:
```bash
# Node.js project
test -f package.json && cat package.json | grep scripts

# Python project  
test -f requirements.txt || test -f pyproject.toml || test -f setup.py

# Ruby project
test -f Gemfile

# Go project
test -f go.mod
```

#### 6. Start Development Server (Agent Should Do This)
Based on project type, the agent should start the appropriate server in window 2:
```bash
# For Next.js/Node projects
tmux send-keys -t $PROJECT_NAME:2 "npm install && npm run dev" Enter

# For Python/FastAPI
tmux send-keys -t $PROJECT_NAME:2 "source venv/bin/activate && uvicorn app.main:app --reload" Enter

# For Django
tmux send-keys -t $PROJECT_NAME:2 "source venv/bin/activate && python manage.py runserver" Enter
```

#### 7. Check GitHub Issues (Agent Should Do This)
```bash
# Check if it's a git repo with remote
git remote -v

# Use GitHub CLI to check issues
gh issue list --limit 10

# Or check for TODO.md, ROADMAP.md files
ls -la | grep -E "(TODO|ROADMAP|TASKS)"
```

#### 8. Monitor and Report Back
The orchestrator should:
```bash
# Check agent status periodically
tmux capture-pane -t $PROJECT_NAME:0 -p | tail -30

# Check if dev server started successfully  
tmux capture-pane -t $PROJECT_NAME:2 -p | tail -20

# Monitor for errors
tmux capture-pane -t $PROJECT_NAME:2 -p | grep -i error
```

### Example: Starting "Task Templates" Project
```bash
# 1. Find project
ls -la ~/Coding/ | grep -i task
# Found: task-templates

# 2. Create session
tmux new-session -d -s task-templates -c "/Users/jasonedward/Coding/task-templates"

# 3. Set up windows
tmux rename-window -t task-templates:0 "Claude-Agent"
tmux new-window -t task-templates -n "Shell" -c "/Users/jasonedward/Coding/task-templates"
tmux new-window -t task-templates -n "Dev-Server" -c "/Users/jasonedward/Coding/task-templates"

# 4. Start Claude and brief
tmux send-keys -t task-templates:0 "claude --dangerously-skip-permissions" Enter
# ... (briefing as above)
```

### Important Notes
- Always verify project exists before creating session
- Use project folder name for session name (with hyphens for spaces)
- Let the agent figure out project-specific details
- Monitor for successful startup before considering task complete

## Creating a Project Manager

### When User Says "Create a project manager for [session]"

#### 1. Analyze the Session
```bash
# List windows in the session
tmux list-windows -t [session] -F "#{window_index}: #{window_name}"

# Check each window to understand project
tmux capture-pane -t [session]:0 -p | tail -50
```

#### 2. Create PM Window
```bash
# Get project path from existing window
PROJECT_PATH=$(tmux display-message -t [session]:0 -p '#{pane_current_path}')

# Create new window for PM
tmux new-window -t [session] -n "Project-Manager" -c "$PROJECT_PATH"
```

#### 3. Start and Brief the PM
```bash
# Start Claude
tmux send-keys -t [session]:[PM-window] "claude --dangerously-skip-permissions" Enter
sleep 5

# Send PM-specific briefing
tmux send-keys -t [session]:[PM-window] "You are the Project Manager for this project. Your responsibilities:

1. **Quality Standards**: Maintain exceptionally high standards. No shortcuts, no compromises.
2. **Verification**: Test everything. Trust but verify all work.
3. **Team Coordination**: Manage communication between team members efficiently.
4. **Progress Tracking**: Monitor velocity, identify blockers, report to orchestrator.
5. **Risk Management**: Identify potential issues before they become problems.

Key Principles:
- Be meticulous about testing and verification
- Create test plans for every feature
- Ensure code follows best practices
- Track technical debt
- Communicate clearly and constructively

First, analyze the project and existing team members, then introduce yourself to the developer in window 0."
sleep 1
tmux send-keys -t [session]:[PM-window] Enter
```

#### 4. PM Introduction Protocol
The PM should:
```bash
# Check developer window
tmux capture-pane -t [session]:0 -p | tail -30

# Introduce themselves
tmux send-keys -t [session]:0 "Hello! I'm the new Project Manager for this project. I'll be helping coordinate our work and ensure we maintain high quality standards. Could you give me a brief status update on what you're currently working on?"
sleep 1
tmux send-keys -t [session]:0 Enter
```

## Communication Protocols

### Hub-and-Spoke Model
To prevent communication overload (n² complexity), use structured patterns:
- Developers report to PM only
- PM aggregates and reports to Orchestrator
- Cross-functional communication goes through PM
- Emergency escalation directly to Orchestrator

### Daily Standup (Async)
```bash
# PM asks each team member
tmux send-keys -t [session]:[dev-window] "STATUS UPDATE: Please provide: 1) Completed tasks, 2) Current work, 3) Any blockers"
# Wait for response, then aggregate
```

### Message Templates

#### Status Update
```
STATUS [AGENT_NAME] [TIMESTAMP]
Completed: 
- [Specific task 1]
- [Specific task 2]
Current: [What working on now]
Blocked: [Any blockers]
ETA: [Expected completion]
```

#### Task Assignment
```
TASK [ID]: [Clear title]
Assigned to: [AGENT]
Objective: [Specific goal]
Success Criteria:
- [Measurable outcome]
- [Quality requirement]
Priority: HIGH/MED/LOW
```

## Team Deployment

### When User Says "Work on [new project]"

#### 1. Project Analysis
```bash
# Find project
ls -la ~/Coding/ | grep -i "[project-name]"

# Analyze project type
cd ~/Coding/[project-name]
test -f package.json && echo "Node.js project"
test -f requirements.txt && echo "Python project"
```

#### 2. Propose Team Structure

**Small Project**: 1 Developer + 1 PM
**Medium Project**: 2 Developers + 1 PM + 1 QA  
**Large Project**: Lead + 2 Devs + PM + QA + DevOps

#### 3. Deploy Team
Create session and deploy all agents with specific briefings for their roles.

## Agent Lifecycle Management

### Creating Temporary Agents
For specific tasks (code review, bug fix):
```bash
# Create with clear temporary designation
tmux new-window -t [session] -n "TEMP-CodeReview"
```

### Ending Agents Properly
```bash
# 1. Capture complete conversation
tmux capture-pane -t [session]:[window] -S - -E - > \
  ~/Coding/Tmux\ orchestrator/registry/logs/[session]_[role]_$(date +%Y%m%d_%H%M%S).log

# 2. Create summary of work completed
echo "=== Agent Summary ===" >> [logfile]
echo "Tasks Completed:" >> [logfile]
echo "Issues Encountered:" >> [logfile]
echo "Handoff Notes:" >> [logfile]

# 3. Close window
tmux kill-window -t [session]:[window]
```

### Agent Logging Structure
```
~/Coding/Tmux orchestrator/registry/
├── logs/            # Agent conversation logs
├── sessions.json    # Active session tracking
└── notes/           # Orchestrator notes and summaries
```

## Quality Assurance Protocols

### PM Verification Checklist
- [ ] All code has tests
- [ ] Error handling is comprehensive
- [ ] Performance is acceptable
- [ ] Security best practices followed
- [ ] Documentation is updated
- [ ] No technical debt introduced

### Continuous Verification
PMs should implement:
1. Code review before any merge
2. Test coverage monitoring
3. Performance benchmarking
4. Security scanning
5. Documentation audits

## Communication Rules

1. **No Chit-Chat**: All messages work-related
2. **Use Templates**: Reduces ambiguity
3. **Acknowledge Receipt**: Simple "ACK" for tasks
4. **Escalate Quickly**: Don't stay blocked >10 min
5. **One Topic Per Message**: Keep focused

## Critical Self-Scheduling Protocol

### 🚨 MANDATORY STARTUP CHECK FOR ALL ORCHESTRATORS

**EVERY TIME you start or restart as an orchestrator, you MUST perform this check:**

```bash
# 1. Check your current tmux location
echo "Current pane: $TMUX_PANE"
CURRENT_WINDOW=$(tmux display-message -p "#{session_name}:#{window_index}")
echo "Current window: $CURRENT_WINDOW"

# 2. Test the scheduling script with your current window
./schedule_with_note.sh 1 "Test schedule for $CURRENT_WINDOW" "$CURRENT_WINDOW"

# 3. If scheduling fails, you MUST fix the script before proceeding
```

### Schedule Script Requirements

The `schedule_with_note.sh` script MUST:
- Accept a third parameter for target window: `./schedule_with_note.sh <minutes> "<note>" <target_window>`
- Default to `tmux-orc:0` if no target specified
- Always verify the target window exists before scheduling

### Why This Matters

- **Continuity**: Orchestrators must maintain oversight without gaps
- **Window Accuracy**: Scheduling to wrong window breaks the oversight chain
- **Self-Recovery**: Orchestrators must be able to restart themselves reliably

### Scheduling Best Practices

```bash
# Always use current window for self-scheduling
CURRENT_WINDOW=$(tmux display-message -p "#{session_name}:#{window_index}")
./schedule_with_note.sh 15 "Regular PM oversight check" "$CURRENT_WINDOW"

# For scheduling other agents, specify their windows explicitly
./schedule_with_note.sh 30 "Developer progress check" "ai-chat:2"
```

## Anti-Patterns to Avoid

- ❌ **Meeting Hell**: Use async updates only
- ❌ **Endless Threads**: Max 3 exchanges, then escalate
- ❌ **Broadcast Storms**: No "FYI to all" messages
- ❌ **Micromanagement**: Trust agents to work
- ❌ **Quality Shortcuts**: Never compromise standards
- ❌ **Blind Scheduling**: Never schedule without verifying target window

## Critical Lessons Learned

### Tmux Window Management Mistakes and Solutions

#### Mistake 1: Wrong Directory When Creating Windows
**What Went Wrong**: Created server window without specifying directory, causing uvicorn to run in wrong location (Tmux orchestrator instead of Glacier-Analytics)

**Root Cause**: New tmux windows inherit the working directory from where tmux was originally started, NOT from the current session's active window

**Solution**: 
```bash
# Always use -c flag when creating windows
tmux new-window -t session -n "window-name" -c "/correct/path"

# Or immediately cd after creating
tmux new-window -t session -n "window-name"
tmux send-keys -t session:window-name "cd /correct/path" Enter
```

#### Mistake 2: Not Reading Actual Command Output
**What Went Wrong**: Assumed commands like `uvicorn app.main:app` succeeded without checking output

**Root Cause**: Not using `tmux capture-pane` to verify command results

**Solution**:
```bash
# Always check output after running commands
tmux send-keys -t session:window "command" Enter
sleep 2  # Give command time to execute
tmux capture-pane -t session:window -p | tail -50
```

#### Mistake 3: Typing Commands in Already Active Sessions
**What Went Wrong**: Typed "claude" in a window that already had Claude running

**Root Cause**: Not checking window contents before sending commands

**Solution**:
```bash
# Check window contents first
tmux capture-pane -t session:window -S -100 -p
# Look for prompts or active sessions before sending commands
```

#### Mistake 4: Incorrect Message Sending to Claude Agents
**What Went Wrong**: Initially sent Enter key with the message text instead of as separate command

**Root Cause**: Using `tmux send-keys -t session:window "message" Enter` combines them

**Solution**:
```bash
# Send message and Enter separately
tmux send-keys -t session:window "Your message here"
tmux send-keys -t session:window Enter
```

## Best Practices for Tmux Orchestration

### Pre-Command Checks
1. **Verify Working Directory**
   ```bash
   tmux send-keys -t session:window "pwd" Enter
   tmux capture-pane -t session:window -p | tail -5
   ```

2. **Check Command Availability**
   ```bash
   tmux send-keys -t session:window "which command_name" Enter
   tmux capture-pane -t session:window -p | tail -5
   ```

3. **Check for Virtual Environments**
   ```bash
   tmux send-keys -t session:window "ls -la | grep -E 'venv|env|virtualenv'" Enter
   ```

### Window Creation Workflow
```bash
# 1. Create window with correct directory
tmux new-window -t session -n "descriptive-name" -c "/path/to/project"

# 2. Verify you're in the right place
tmux send-keys -t session:descriptive-name "pwd" Enter
sleep 1
tmux capture-pane -t session:descriptive-name -p | tail -3

# 3. Activate virtual environment if needed
tmux send-keys -t session:descriptive-name "source venv/bin/activate" Enter

# 4. Run your command
tmux send-keys -t session:descriptive-name "your-command" Enter

# 5. Verify it started correctly
sleep 3
tmux capture-pane -t session:descriptive-name -p | tail -20
```

### Debugging Failed Commands
When a command fails:
1. Capture full window output: `tmux capture-pane -t session:window -S -200 -p`
2. Check for common issues:
   - Wrong directory
   - Missing dependencies
   - Virtual environment not activated
   - Permission issues
   - Port already in use

### Communication with Claude Agents

#### 🎯 IMPORTANT: Always Use send-claude-message.sh Script

**DO NOT manually send messages with tmux send-keys anymore!** We have a dedicated script that handles all the timing and complexity for you.

#### Using send-claude-message.sh
```bash
# Basic usage - ALWAYS use this instead of manual tmux commands
/Users/jasonedward/Coding/Tmux\ orchestrator/send-claude-message.sh <target> "message"

# Examples:
# Send to a window
/Users/jasonedward/Coding/Tmux\ orchestrator/send-claude-message.sh agentic-seek:3 "Hello Claude!"

# Send to a specific pane in split-screen
/Users/jasonedward/Coding/Tmux\ orchestrator/send-claude-message.sh tmux-orc:0.1 "Message to pane 1"

# Send complex instructions
/Users/jasonedward/Coding/Tmux\ orchestrator/send-claude-message.sh glacier-backend:0 "Please check the database schema for the campaigns table and verify all columns are present"

# Send status update requests
/Users/jasonedward/Coding/Tmux\ orchestrator/send-claude-message.sh ai-chat:2 "STATUS UPDATE: What's your current progress on the authentication implementation?"
```

#### Why Use the Script?
1. **Automatic timing**: Handles the critical 0.5s delay between message and Enter
2. **Simpler commands**: One line instead of three
3. **No timing mistakes**: Prevents the common error of Enter being sent too quickly
4. **Works everywhere**: Handles both windows and panes automatically
5. **Consistent messaging**: All agents receive messages the same way

#### Script Location and Usage
- **Location**: `/Users/jasonedward/Coding/Tmux orchestrator/send-claude-message.sh`
- **Permissions**: Already executable, ready to use
- **Arguments**: 
  - First: target (session:window or session:window.pane)
  - Second: message (can contain spaces, will be properly handled)

#### Common Messaging Patterns with the Script

##### 1. Starting Claude and Initial Briefing
```bash
# Start Claude first
tmux send-keys -t project:0 "claude --dangerously-skip-permissions" Enter
sleep 5

# Then use the script for the briefing
/Users/jasonedward/Coding/Tmux\ orchestrator/send-claude-message.sh project:0 "You are responsible for the frontend codebase. Please start by analyzing the current project structure and identifying any immediate issues."
```

##### 2. Cross-Agent Coordination
```bash
# Ask frontend agent about API usage
/Users/jasonedward/Coding/Tmux\ orchestrator/send-claude-message.sh frontend:0 "Which API endpoints are you currently using from the backend?"

# Share info with backend agent
/Users/jasonedward/Coding/Tmux\ orchestrator/send-claude-message.sh backend:0 "Frontend is using /api/v1/campaigns and /api/v1/flows endpoints"
```

##### 3. Status Checks
```bash
# Quick status request
/Users/jasonedward/Coding/Tmux\ orchestrator/send-claude-message.sh session:0 "Quick status update please"

# Detailed status request
/Users/jasonedward/Coding/Tmux\ orchestrator/send-claude-message.sh session:0 "STATUS UPDATE: Please provide: 1) Completed tasks, 2) Current work, 3) Any blockers"
```

##### 4. Providing Assistance
```bash
# Share error information
/Users/jasonedward/Coding/Tmux\ orchestrator/send-claude-message.sh session:0 "I see in your server window that port 3000 is already in use. Try port 3001 instead."

# Guide stuck agents
/Users/jasonedward/Coding/Tmux\ orchestrator/send-claude-message.sh session:0 "The error you're seeing is because the virtual environment isn't activated. Run 'source venv/bin/activate' first."
```

#### OLD METHOD (DO NOT USE)
```bash
# ❌ DON'T DO THIS ANYMORE:
tmux send-keys -t session:window "message"
sleep 1
tmux send-keys -t session:window Enter

# ✅ DO THIS INSTEAD:
/Users/jasonedward/Coding/Tmux\ orchestrator/send-claude-message.sh session:window "message"
```

#### Checking for Responses
After sending a message, check for the response:
```bash
# Send message
/Users/jasonedward/Coding/Tmux\ orchestrator/send-claude-message.sh session:0 "What's your status?"

# Wait a bit for response
sleep 5

# Check what the agent said
tmux capture-pane -t session:0 -p | tail -50
```
🚀 Improvement Plan Based on Lessons Learned

## Critical Improvements Needed (Based on Past Experience)

### 1. 🔴 IMMEDIATE: Enforce Git Discipline
**Lesson**: V1 lost work due to no commits for 1+ hour
**Action Required**:
```bash
# Set up auto-commit every 30 minutes for ALL agents
while true; do
  sleep 1800
  for window in {1..8}; do
    tmux send-keys -t efab-erp:$window "git add -A && git commit -m 'Auto-commit: $(date +%Y%m%d-%H%M%S)'" Enter
  done
done &
```

### 2. 🟡 HIGH PRIORITY: Web Research Protocol
**Lesson**: Developer wasted 2+ hours on JWT issue that web search solved instantly
**Implementation**:
- After 10 minutes stuck on ANY issue → mandatory web search
- Add to all agent instructions: "If stuck >10 min, search online IMMEDIATELY"
- Track time on each problem, escalate if >30 min

### 3. 🟡 HIGH PRIORITY: Performance Monitoring
**Current Gap**: No automated performance tracking
**Required Actions**:
```python
# Add to all API endpoints
@app.middleware("http")
async def add_performance_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    if process_time > 0.2:  # Log slow requests
        logger.warning(f"Slow request: {request.url} took {process_time}s")
    return response
```

### 4. 🟢 MEDIUM: Implement Strike System for Agents
**Lesson**: Non-compliant agents wasted 30+ minutes
**Strike System**:
- Strike 1: Warning with exact command
- Strike 2: Final warning with 2-min deadline
- Strike 3: Immediate replacement
**Compliance Tracking**:
```python
agent_compliance = {
    "Backend-Dev": {"tasks_given": 10, "tasks_completed": 8, "score": 80},
    "ML-Engineer": {"tasks_given": 8, "tasks_completed": 7, "score": 87.5},
}
```

### 5. 🟢 MEDIUM: One-Task-One-Command Protocol
**Lesson**: Complex multi-step instructions confused agents
**New Format**:
```
AGENT: [Name]
TASK: [Single specific task]
COMMAND: [Exact command to run]
SUCCESS: [Clear metric]
TIME: [Max allowed]
```

### 6. 🔵 LOW: Implement Health Check Dashboard
**Current Gap**: No centralized monitoring
**Solution**:
```python
# Create /health/dashboard endpoint
@app.get("/health/dashboard")
async def health_dashboard():
    return {
        "api": check_api_health(),
        "database": check_db_health(),
        "redis": check_redis_health(),
        "ml_models": check_ml_health(),
        "response_time_p95": get_p95_response_time(),
        "error_rate": get_error_rate_last_hour(),
    }
```

## Specific Agent Improvements

### Backend Developer (Window 5)
- [ ] Add comprehensive logging to all endpoints
- [ ] Implement request/response validation
- [ ] Add retry logic for database operations
- [ ] Create health check endpoints for all services

### ML Engineer (Window 4)
- [ ] Implement model versioning with Git LFS
- [ ] Add model performance tracking
- [ ] Create fallback mechanisms for model failures
- [ ] Implement A/B testing framework

### Test Engineer (Window 6)
- [ ] Achieve 80%+ code coverage
- [ ] Add load testing with Locust
- [ ] Implement continuous integration tests
- [ ] Create smoke test suite (<5 min runtime)

### DevOps Engineer (Window 8)
- [ ] Complete Docker configuration
- [ ] Set up CI/CD pipeline
- [ ] Implement log aggregation
- [ ] Create disaster recovery plan

## Communication Improvements

### 1. Structured Status Updates
```
STATUS [TIMESTAMP]
✅ Completed: [specific tasks]
🔄 In Progress: [current work]
❌ Blocked: [issues]
⏰ ETA: [completion time]
```

### 2. Error Escalation Protocol
```
Level 1 (0-10 min): Try standard debugging
Level 2 (10-20 min): Web search required
Level 3 (20-30 min): Ask for help
Level 4 (30+ min): Escalate to orchestrator
```

### 3. Documentation Requirements
Every completed feature MUST have:
- [ ] Code comments
- [ ] API documentation
- [ ] Test coverage
- [ ] Performance benchmark
- [ ] LEARNINGS.md entry

## Monitoring & Metrics

### Key Performance Indicators (KPIs)
| Metric | Current | Target | Action if Below |
|--------|---------|--------|-----------------|
| API Response Time | Unknown | <200ms | Add caching |
| Test Coverage | ~60% | >80% | Write more tests |
| Agent Compliance | ~70% | >90% | Replace agent |
| Git Commit Frequency | Sporadic | Every 30 min | Auto-commit |
| Error Rate | Unknown | <1% | Debug and fix |
| Model Accuracy | ~92% | >95% | Retrain models |

### Automated Monitoring Script
```bash
#!/bin/bash
# monitoring.sh - Run every 5 minutes

# Check services
curl -s http://localhost:8000/health || echo "API DOWN"
curl -s http://localhost:8501 || echo "UI DOWN"

# Check database
psql -c "SELECT 1" || echo "DB DOWN"

# Check Redis
redis-cli ping || echo "REDIS DOWN"

# Check agent compliance
for window in {1..8}; do
  last_activity=$(tmux capture-pane -t efab-erp:$window -p | tail -1)
  echo "Window $window: $last_activity"
done
```

## Time Management

### Pomodoro Technique for Agents
- 25 minutes focused work
- 5 minutes to commit and document
- After 4 cycles: major review

### Daily Schedule
```
09:00 - Stand-up: Status from all agents
10:00 - Focus Block 1: Core features
12:00 - Commit checkpoint
13:00 - Focus Block 2: Testing
15:00 - Performance review
16:00 - Focus Block 3: Documentation
17:00 - Final commit and handoff
```

## Quality Gates

### Definition of Done
- [ ] Code complete and reviewed
- [ ] Tests written and passing (>80% coverage)
- [ ] Documentation updated
- [ ] Performance benchmarked (<200ms)
- [ ] Security validated
- [ ] Git committed with meaningful message
- [ ] Deployed to staging
- [ ] Smoke tests passing

## Emergency Procedures

### When Agent Non-Compliant
1. Send exact command to execute
2. Wait 2 minutes
3. If still non-compliant: `tmux kill-window -t efab-erp:[window]`
4. Create new agent with clearer instructions

### When Service Down
1. Check logs: `docker logs [container]`
2. Restart service: `docker-compose restart [service]`
3. Check dependencies
4. Rollback if needed: `git revert HEAD`

### When Performance Degraded
1. Check Redis cache hit rate
2. Analyze slow query log
3. Review recent commits for issues
4. Scale horizontally if needed

### Non-Compliance Patterns Detected
1. **Task Switching**: Agents doing different tasks than assigned
2. **Incomplete Execution**: Starting tasks but not finishing
3. **Command Avoidance**: Not running rm/mv commands when instructed
4. **Distraction**: Getting pulled into other activities

## Escalation Protocol
# Agent Compliance Monitor - Variable Check Framework

## Check Interval Rules
- **Full Compliance**: Check every 15 minutes
- **Partial Compliance**: Check every 5 minutes  
- **Non-Compliance**: Check every 1-2 minutes
- **Critical Issues**: Continuous monitoring (30 seconds)

### Level 1 (Current) - 1-2 minute checks
- Direct messages with specific commands
- Clear "STOP and DO THIS" instructions

### Level 2 - 30 second checks  
- Override current actions with Escape key
- Force specific command execution
- One task at a time

### Level 3 - Continuous monitoring
- Take direct control of windows
- Execute commands directly
- Reset agents if needed

## Metrics to Track
- Commands given vs commands executed
- Time to complete assigned tasks
- Number of reminders needed
- Files actually deleted/moved

## Compliance Improvement Actions
1. Shorter, simpler commands
2. One action at a time
3. Require confirmation after each step
4. Block other activities until cleanup done

---

*This plan synthesizes all lessons from V1/V2 failures and successes. Implement systematically for guaranteed improvement.* 
### Phase 1: Setup & Verification (5 minutes)
```
1. Verify all agents in correct directory
2. Check existing services status
3. Clear previous work
4. Assign ONE role per agent
```

### Phase 2: Services First (10 minutes)
```
Priority 1: Backend API (port 8000)
Priority 2: Frontend UI (port 8501)
Priority 3: Database connection
NO OTHER TASKS UNTIL SERVICES RUNNING
```

### Phase 3: Core Functionality (20 minutes)
```
Only AFTER services running:
- Test one complete workflow
- Fix only blocking errors
- Skip nice-to-haves
```

### Phase 4: Git Checkpoint (5 minutes)
```
Every 15 minutes mandatory:
- All agents: git add -A && git commit -m "Progress: [specific]"
- No exceptions
```

## 🚀 V2 AGENT ASSIGNMENTS

### Simplified Structure (4 agents max initially)
1. **Backend Agent**: API only
2. **Frontend Agent**: UI only  
3. **Infra Agent**: Database/Redis/Docker
4. **Coordinator**: PM + oversight

### Reserve Pool
- Keep windows 5-8 empty
- Deploy only if specific expertise needed
- One task then dismiss

## 🚫 V2 FORBIDDEN ACTIONS

1. **NO file reorganization** (waste of time)
2. **NO creating new files** (use existing)
3. **NO comprehensive solutions** (MVP only)
4. **NO waiting for perfection** (running > perfect)
5. **NO complex instructions** (one task only)
6. **NO tolerance for non-compliance** (replace in 5 min)

## ⏰ V2 TIME BOXING

```
00:00-00:05: Setup & role assignment
00:05-00:15: Services running
00:15-00:20: Verify core functionality
00:20-00:30: Fix only critical bugs
00:30-00:35: Git commit all work
00:35-00:45: Test & validate
00:45-00:50: Documentation update
00:50-00:60: Final commit & summary
```

## 🎖️ V2 SUCCESS CRITERIA

### Minimum Viable Success (30 minutes)
- [ ] Backend API responds to /health
- [ ] Frontend UI loads in browser
- [ ] Can perform one core action
- [ ] Work committed to git

### Good Success (45 minutes)
- [ ] All above +
- [ ] Database connected
- [ ] ML model loads
- [ ] No critical errors

### Excellent Success (60 minutes)
- [ ] All above +
- [ ] Complete workflow tested
- [ ] Performance acceptable
- [ ] Ready for demo

## 🔑 KEY V2 PRINCIPLES

1. **"Services First, Everything Else Second"**
2. **"One Agent, One Job, One Command"**
3. **"5 Minutes to Compliance or Replacement"**
4. **"Git Commit Every 15 Minutes, No Exceptions"**
5. **"Running Badly Beats Not Running"**
6. **"Use What Exists, Create Nothing"**
7. **"MCP Tools Always, Basic Tools Never"**

## 📊 COMPLIANCE ENFORCEMENT V2

### Strike System
- Strike 1 (immediate): Warning with exact command
- Strike 2 (2 min): Final warning with deadline
- Strike 3 (5 min): Immediate replacement

### Compliance Rewards
- High compliance (>80%): 15-minute check interval
- Medium compliance (50-80%): 5-minute checks
- Low compliance (<50%): 2-minute checks
- Non-compliance (<20%): Immediate replacement

## 💡 INNOVATION FOR V2

### Auto-Git System
```bash
# Every 15 minutes automatically
while true; do
  sleep 900
  tmux send-keys -t efab-erp:all "git add -A && git commit -m 'Auto-commit: $(date)'" Enter
done &
```

### Health Check Monitor
```bash
# Continuous service monitoring
while true; do
  curl -s http://localhost:8000/health || echo "API DOWN"
  curl -s http://localhost:8501 || echo "UI DOWN"
  sleep 30
done &
```

### Compliance Scorer
```python
def calculate_compliance(task_given, task_executed):
    if task_executed == task_given:
        return 100
    elif partially_matches(task_executed, task_given):
        return 50
    else:
        return 0
```

## 📝 V2 COMMUNICATION RULES

1. **Maximum 3 sentences per message**
2. **Include working directory in every message**
3. **One task per message**
4. **Clear success criteria**
5. **Time limit specified**
6. **MCP tool specified**

### Example V2 Message:
```
BACKEND AGENT: Start API now.
Run: cd /mnt/d/efab.ai-765646/efab.ai-765646 && python -m uvicorn src.api.main:app --port 8000
Success: Returns 200 on http://localhost:8000/health within 5 minutes.
```

## 🏁 V2 LAUNCH CHECKLIST

- [ ] Clear all agent terminals
- [ ] Verify working directories
- [ ] Assign single roles
- [ ] Set 15-minute git timer
- [ ] Start health monitoring
- [ ] Focus on services ONLY
- [ ] No distractions allowed
- [ ] Replace non-compliant immediately

## 2025-06-18 - Project Management & Agent Oversight

### Discovery: Importance of Web Research
- **Issue**: Developer spent 2+ hours trying to solve JWT multiline environment variable issue in Convex
- **Mistake**: As PM, I didn't suggest web research until prompted by the user
- **Learning**: Should ALWAYS suggest web research after 10 minutes of failed attempts
- **Solution**: Added "Web Research is Your Friend" section to global CLAUDE.md
- **Impact**: Web search immediately revealed the solution (replace newlines with spaces)

### Insight: Reading Error Messages Carefully
- **Issue**: Developer spent time on base64 decoding when the real error was "Missing environment variable JWT_PRIVATE_KEY"
- **Learning**: Always verify the actual error before implementing complex solutions
- **Pattern**: Developers often over-engineer solutions without checking basic assumptions
- **PM Action**: Ask "What's the EXACT error message?" before approving solution approaches

### Project Manager Best Practices
- **Be Firm but Constructive**: When developer was coding without documenting, had to insist on LEARNINGS.md creation
- **Status Reports**: Direct questions get better results than open-ended "how's it going?"
- **Escalation Timing**: If 3 approaches fail, immediately suggest different strategy
- **Documentation First**: Enforce documentation BEFORE continuing to code when stuck

### Communication Patterns That Work
- **Effective**: "STOP. Give me status: 1) X fixed? YES/NO 2) Current error?"
- **Less Effective**: "How's the authentication coming along?"
- **Key**: Specific, numbered questions force clear responses

### Reminder System
- **Discovery**: User reminded me to set check-in reminders before ending conversations
- **Implementation**: Use schedule_with_note.sh with specific action items
- **Best Practice**: Always schedule follow-up with concrete next steps, not vague "check progress"

## 2025-06-17 - Agent System Design

### Multi-Agent Coordination
- **Challenge**: Communication complexity grows exponentially (n²) with more agents
- **Solution**: Hub-and-spoke model with PM as central coordinator
- **Key Insight**: Structured communication templates reduce ambiguity and overhead

### Agent Lifecycle Management
- **Learning**: Need clear distinction between permanent and temporary agents
- **Solution**: Implement proper logging before terminating agents
- **Directory Structure**: agent_logs/permanent/ and agent_logs/temporary/

### Quality Assurance
- **Principle**: PMs must be "meticulous about testing and verification"
- **Implementation**: Verification checklists, no shortcuts, track technical debt
- **Key**: Trust but verify - always check actual implementation

## Common Pitfalls to Avoid

1. **Not Using Available Tools**: Web search, documentation, community resources
2. **Circular Problem Solving**: Trying same approach repeatedly without stepping back
3. **Missing Context**: Not checking other tmux windows for error details
4. **Poor Time Management**: Not setting time limits on debugging attempts
5. **Incomplete Handoffs**: Not documenting solutions for future agents

## Orchestrator-Specific Insights

- **Stay High-Level**: Don't get pulled into implementation details
- **Pattern Recognition**: Similar issues across projects (auth, env vars, etc.)
- **Cross-Project Knowledge**: Use insights from one project to help another
- **Proactive Monitoring**: Check multiple windows to spot issues early

## 2025-06-18 - Later Session - Authentication Success Story

### Effective PM Intervention
- **Situation**: Developer struggling with JWT authentication for 3+ hours
- **Key Action**: Sent direct encouragement when I saw errors were resolved
- **Result**: Motivated developer to document learnings properly
- **Lesson**: Timely positive feedback is as important as corrective guidance

### Cross-Window Intelligence 
- **Discovery**: Can monitor server logs while developer works
- **Application**: Saw JWT_PRIVATE_KEY error was resolved before developer noticed
- **Value**: Proactive encouragement based on real-time monitoring
- **Best Practice**: Always check related windows (servers, logs) for context

### Documentation Enforcement
- **Challenge**: Developers often skip documentation when solution works
- **Solution**: Send specific reminders about what to document
- **Example**: Listed exact items to include in LEARNINGS.md
- **Impact**: Ensures institutional knowledge is captured

### Claude Plan Mode Discovery
- **Feature**: Claude has a plan mode activated by Shift+Tab+Tab
- **Key Sequence**: Hold Shift, press Tab, press Tab again, release Shift
- **Critical Step**: MUST verify "⏸ plan mode on" appears - may need multiple attempts
- **Tmux Implementation**: `tmux send-keys -t session:window S-Tab S-Tab`
- **Verification**: `tmux capture-pane | grep "plan mode on"`
- **Troubleshooting**: If not activated, send additional S-Tab until confirmed
- **User Correction**: User had to manually activate it for me initially
- **Use Case**: Activated plan mode for complex password reset implementation
- **Best Practice**: Always verify activation before sending planning request
- **Key Learning**: Plan mode forces thoughtful approach before coding begins

### 1. MCP Tool Enforcement⚠️
- All agents instructed to use MCP tools exclusively
- Discovered MCP tools may not be available in agent environments
- Agents using standard tools for now
- Reference: `/mnt/d/Tmux-Orchestrator/MCP_USAGE_ENFORCEMENT.md`

### 2. Git Discipline ✅
- Created auto-commit script: `/mnt/d/Tmux-Orchestrator/auto_commit_agents.sh`
- Will commit all agent work every 30 minutes
- Prevents work loss as per lessons learned

### 3. Monitoring System ✅
- Created monitoring script: `/mnt/d/Tmux-Orchestrator/monitor_agents.sh`
- Tracks service health, agent activity, and MCP compliance
- Will run every 5 minutes

### 4. Redundancy Elimination ✅
- Killed overlapping agents in efab-orchestrator session
- Consolidated ML, Frontend, and Testing work to efab-erp agents

## Communication Protocols

Following CLAUDE.md hub-and-spoke model:
- All developers report to Project Manager (Window 7)
- Project Manager aggregates and reports to Orchestrator
- Emergency escalation comes directly to Orchestrator

## Next Actions

1. **Schedule Regular Checks**
   - PM oversight every 15 minutes
   - Agent compliance checks based on performance

2. **Implement Strike System**
   - Track agent compliance scores
   - Replace non-compliant agents after 3 strikes

3. **Performance Monitoring**
   - Ensure API response times <200ms
   - Monitor ML model accuracy >95%

## Key Protocols from CLAUDE.md

- ✅ Self-scheduling check completed
- ✅ Window naming conventions applied
- ✅ Git discipline enforced
- ✅ MCP tools mandated
- ✅ Communication templates in use

## Service Status
- Backend API: Running on port 8000 ✅
- Frontend UI: Running on port 8501 ✅
- Upload Fix: Running on port 8502 ✅

## Latest Updates (19:45)

### Critical Changes
1. **Permission Issue Resolved**: All agents restarted with `claude --dangerously-skip-permissions`
2. **Clear Role Assignments**: Each agent given specific, non-overlapping responsibilities
3. **MCP Tool Status**: Agents reporting MCP tools not available - using standard tools

### Current Agent Tasks
- **Backend-API**: Optimizing API endpoints for <200ms response time
- **Frontend-UI**: Testing upload functionality and improving UX
- **ML-Engineer**: Installing xgboost and improving demand forecasting models
- **Test-Engineer**: Running tests and identifying coverage gaps
- **DevOps**: Monitoring service health and reviewing Docker configs
- **Project-Manager**: Coordinating team and preventing task overlap

## Escalation Protocol

### Level 1 (Current) - 1-2 minute checks
- Direct messages with specific commands
- Clear "STOP and DO THIS" instructions

### Level 2 - 30 second checks  
- Override current actions with Escape key
- Force specific command execution
- One task at a time

### Level 3 - Continuous monitoring
- Take direct control of windows
- Execute commands directly
- Reset agents if needed

## Metrics to Track
- Commands given vs commands executed
- Time to complete assigned tasks
- Number of reminders needed
- Files actually deleted/moved

## Compliance Improvement Actions
1. Shorter, simpler commands
2. One action at a time
3. Require confirmation after each step
4. Block other activities until cleanup done

## Available MCP Servers

### Core Development Tools
- **mcp__filesystem**: Fast file operations across /mnt/d
- **mcp__git**: Version control operations
- **mcp__memory**: Knowledge graph building and retrieval

### Database Access
- **mcp__postgres**: Direct PostgreSQL access at `postgresql://localhost:5432/efab_db`
- **mcp__sqlite**: SQLite database operations

### ML/AI Libraries
- **mcp__scikit-learn**: Scikit-learn documentation and examples
- **mcp__pandas**: Pandas data manipulation guidance
- **mcp__numpy**: NumPy array operations
- **mcp__huggingface-transformers**: Transformer models
- **mcp__tensorflow**: TensorFlow deep learning
- **mcp__pytorch**: PyTorch neural networks

### Web Frameworks
- **mcp__fastapi**: FastAPI patterns and best practices
- **mcp__streamlit**: Streamlit UI components
- **mcp__sqlalchemy**: SQLAlchemy ORM patterns

### External Tools
- **mcp__fetch**: API calls and web requests
- **mcp__browser**: Browser automation with Puppeteer

## Usage Examples

### File Operations (Use mcp__filesystem instead of Read/Write)
```
# Instead of Read tool, use:
mcp__filesystem.read_file("/mnt/d/efab.ai-765646/src/core/domain.py")

# Instead of Write tool, use:
mcp__filesystem.write_file("/mnt/d/efab.ai-765646/src/core/domain.py", content)
```

### Database Queries (Use mcp__postgres)
```
# Direct SQL queries:
mcp__postgres.query("SELECT * FROM materials WHERE status = 'active'")
```

### Git Operations (Use mcp__git)
```
# Check status:
mcp__git.status()

# Commit changes:
mcp__git.commit("feat: Add domain models for supply chain")
```

### ML Development (Use specialized MCP servers)
```
# Get scikit-learn examples:
mcp__scikit-learn.get_example("demand_forecasting")

# Get pandas DataFrame operations:
mcp__pandas.get_docs("time_series_analysis")
```

## Performance Benefits
- MCP tools are 5-10x faster than standard file operations
- Direct database access eliminates API overhead
- Framework-specific guidance reduces development time
- Knowledge graphs maintain context across sessions

## Best Practices
1. Always prefer MCP tools over standard Read/Write/Bash tools
2. Use mcp__memory to store important discoveries and patterns
3. Leverage framework-specific MCP servers for idiomatic code
4. Use mcp__postgres for all database operations
5. Commit frequently using mcp__git

## Team-Specific Recommendations

### Lead Developer
- Use mcp__fastapi and mcp__sqlalchemy for API development
- Use mcp__filesystem for rapid file navigation
- Use mcp__git for atomic commits

### ML Engineer
- Use mcp__scikit-learn for ML pipelines
- Use mcp__pandas for data preprocessing
- Use mcp__postgres for training data queries
- Use mcp__memory to track model experiments

### DevOps
- Use mcp__postgres for database monitoring
- Use mcp__git for CI/CD workflows
- Use mcp__browser for E2E testing

### Project Manager
- Use mcp__memory to track project knowledge
- Use mcp__git to monitor commit history
- Use mcp__filesystem to review code changes

"mcpServers": {
    "_development_tools": "High-frequency local development",
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/mnt/d"]
    },
    "git": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-git", "--repository", "/mnt/d/Tmux-Orchestrator"]
    },
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"]
    },
    
    "_ai_frameworks": "AI and ML orchestration",
    "praisonai": {
      "url": "https://gitmcp.io/MervinPraison/PraisonAI"
    },
    "langchain": {
      "url": "https://gitmcp.io/langchain-ai/langchain"
    },
    "autogen": {
      "url": "https://gitmcp.io/microsoft/autogen"
    },
    "zen-mcp-server": {
      "url": "https://gitmcp.io/BeehiveInnovations/zen-mcp-server"
    },
    
    "_ml_libraries": "Core ML and data science",
    "best-of-ml-python": {
      "url": "https://gitmcp.io/lukasmasuch/best-of-ml-python"
    },
    "scikit-learn": {
      "url": "https://gitmcp.io/scikit-learn/scikit-learn"
    },
    "pandas": {
      "url": "https://gitmcp.io/pandas-dev/pandas"
    },
    "numpy": {
      "url": "https://gitmcp.io/numpy/numpy"
    },
    
    "_deep_learning": "Neural networks and transformers",
    "huggingface-transformers": {
      "url": "https://gitmcp.io/huggingface/transformers"
    },
    "tensorflow": {
      "url": "https://gitmcp.io/tensorflow/tensorflow"
    },
    "pytorch": {
      "url": "https://gitmcp.io/pytorch/pytorch"
    },
    
    "_backend_web": "API and web development",
    "fastapi": {
      "url": "https://gitmcp.io/tiangolo/fastapi"
    },
    "streamlit": {
      "url": "https://gitmcp.io/streamlit/streamlit"
    },
    "sqlalchemy": {
      "url": "https://gitmcp.io/sqlalchemy/sqlalchemy"
    },
    
    "_data_tools": "Database and external data access",
    "postgres": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-postgres", "postgresql://localhost:5432/efab_db"]
    },
    "sqlite": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sqlite", "--db-path", "/mnt/d/Tmux-Orchestrator/database.db"]
    },
    "fetch": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-fetch"]
    },
    "browser": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-puppeteer"]
    },
    
    "_orchestrator_specific": "Tmux orchestrator management",
    "tmux-orchestrator": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/mnt/d/Tmux-Orchestrator"]
    },
    "efab-ai": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/mnt/d/efab.ai-765646"]
    }
  }
}
---
