# TMUX Bible Integration

Agent-MCP has been enhanced with critical lessons learned from multi-agent orchestration, documented in `tmux-bible.md`. This integration brings battle-tested protocols and safety measures to prevent the common failure modes that plague multi-agent development systems.

## 🔑 Key Integration Areas

### 0. Claude Command Standardization

**All Agent Launches**: Every agent in the system now uses the exact command:
```bash
claude --dangerously-skip-permissions
```

This standardization ensures:
- Consistent permissions across all agents
- No variation in Claude CLI behavior
- Simplified documentation and troubleshooting
- Compliance with TMUX Bible protocols

### 1. Enhanced TMUX Utilities (`agent_mcp/utils/tmux_utils.py`)

**New Functions Added:**
- `send_claude_message()` - Proper timing protocols for Claude agents
- `create_project_session_structure()` - TMUX Bible session setup
- `create_project_manager_window()` - Hub-and-spoke communication setup
- `rename_session_windows_intelligently()` - Auto-rename based on content
- `enforce_git_discipline()` - Mandatory 30-minute commit cycles
- `check_agent_compliance()` - Real-time compliance monitoring
- `create_monitoring_summary()` - Comprehensive agent status reports
- `activate_plan_mode()` - Claude plan mode activation (Shift+Tab+Tab)
- `emergency_stop_agent()` - Escalation protocol (Escape key)

### 2. MCP Tools (`agent_mcp/tools/tmux_orchestration_tools.py`)

**11 New MCP Tools:**
- `tmux_create_project_session` - Project startup sequence automation
- `tmux_send_message_to_agent` - Proper message timing protocols
- `tmux_request_status_update` - Structured status reporting
- `tmux_assign_task` - TMUX Bible task assignment format
- `tmux_check_compliance` - Agent compliance verification
- `tmux_create_monitoring_report` - System-wide monitoring
- `tmux_activate_plan_mode` - Plan mode for complex tasks
- `tmux_emergency_stop` - Emergency intervention capability
- `tmux_enforce_budget_discipline` - Credit conservation reminders
- `tmux_enforce_git_discipline` - Git safety across all agents
- `tmux_intelligent_window_rename` - Auto-naming conventions

### 3. Enhanced Agent Startup (`agent_mcp/templates/agent_startup.sh`)

**TMUX Bible Enhancements:**
- **Standardized Claude Command**: Uses `claude --dangerously-skip-permissions` exclusively
- Role-specific instructions (developer, PM, QA, devops)
- Git discipline enforcement at startup
- Auto-commit reminders (30-minute intervals)
- Budget discipline warnings
- Project type detection (Python, Node.js, etc.)
- Critical rules reminder display

### 4. Configuration (`agent_mcp/core/config.py`)

**New TMUX Bible Settings:**
```python
# Git discipline (mandatory)
TMUX_GIT_COMMIT_INTERVAL = 1800  # 30 minutes maximum
TMUX_AUTO_COMMIT_ENABLED = True

# Resource limits (prevent exhaustion)
TMUX_MAX_ACTIVE_AGENTS = 10  # Hard limit
TMUX_AGENT_IDLE_TIMEOUT = 3600  # 1 hour

# Credit conservation (budget discipline)
TMUX_CREDIT_CONSERVATION_MODE = True
TMUX_PM_AUTONOMY_TARGET = 0.8  # 80% independent handling

# Compliance enforcement (strike system)
TMUX_STRIKE_SYSTEM_ENABLED = True
TMUX_MAX_STRIKES_PER_AGENT = 3
```

## 💡 Critical Lessons Implemented

### Lesson 1: PM Must Be Proactive Monitor
- **Problem**: PM failed to notice agents working on wrong tasks
- **Solution**: 2-3 minute check intervals, proactive reporting to orchestrator
- **Implementation**: Compliance monitoring tools with automated alerting

### Lesson 2: Credit/Budget Management Critical  
- **Problem**: Burning through API credits too quickly
- **Solution**: Batch instructions, 10-15 minute work intervals, brief messages
- **Implementation**: Budget discipline enforcement and conservation mode

### Lesson 3: Replace Non-Performing Agents Immediately
- **Problem**: Wasting credits on correcting PM failures
- **Solution**: One-strike policy for critical failures
- **Implementation**: Strike system with automatic replacement triggers

### Lesson 4: Git Discipline is Survival
- **Problem**: Lost hours of work due to lack of commits
- **Solution**: Mandatory 30-minute commit cycles, auto-reminders
- **Implementation**: Automatic git enforcement across all agents

### Lesson 5: Direct Solutions Save Credits
- **Problem**: Agents spending time exploring when fix is known
- **Solution**: Direct, specific instructions when orchestrator knows solution
- **Implementation**: Structured task assignments with exact commands

## 🚀 Usage Examples

### Create a Project Session
```python
# Uses TMUX Bible project startup sequence
await tmux_create_project_session({
    "project_name": "my-app",
    "project_path": "/path/to/project"
})
```

### Send Message with Proper Timing
```python
# Replaces manual tmux send-keys with proper timing
await tmux_send_message_to_agent({
    "session_target": "my-app:0",
    "message": "STATUS UPDATE: What's your current progress?"
})
```

### Monitor Agent Compliance
```python
# Real-time compliance checking
await tmux_check_compliance({
    "session_name": "my-app",
    "window": "0"
})
```

### Emergency Intervention
```python
# When agent goes off-track
await tmux_emergency_stop({
    "session_name": "my-app",
    "window": "0"
})
```

## 📊 Monitoring and Alerts

The system now provides comprehensive monitoring based on TMUX Bible protocols:

- **Compliance Scoring**: Real-time agent performance metrics
- **Git Discipline Tracking**: Commit frequency monitoring
- **Credit Usage Alerts**: Budget conservation warnings
- **Strike System**: Automated non-compliance tracking
- **Performance Monitoring**: Task completion and response times

## 🔧 Window Naming Conventions

Automatic window renaming based on content:
- `Claude-Agent` for Claude instances
- `NextJS-Dev`, `Uvicorn-API` for development servers
- `Project-Shell` for command line interfaces
- `TEMP-Purpose` for temporary agents

## ⚡ Performance Benefits

**Before TMUX Bible Integration:**
- Frequent work loss due to lack of commits
- Credit burn from inefficient communication
- Agent confusion and task switching
- Manual intervention required constantly

**After TMUX Bible Integration:**
- Mandatory git safety prevents work loss
- Structured communication reduces API costs
- Compliance monitoring catches issues early
- Automated protocols reduce manual oversight

## 🚨 Emergency Protocols

**Escalation Levels:**
1. **Level 1** (1-2 min): Direct messages with specific commands
2. **Level 2** (30 sec): Emergency stop + force specific execution
3. **Level 3** (Continuous): Direct control, agent replacement

**Emergency Commands:**
- Escape key interrupt for immediate stop
- Strike system for persistent non-compliance
- Automatic cleanup of orphaned sessions

## 🔒 Safety Features

- **Resource Limits**: Maximum 10 active agents
- **Auto-Cleanup**: Orphaned session detection and removal
- **Git Safety**: Mandatory commit cycles prevent work loss
- **Budget Protection**: Credit conservation protocols
- **Compliance Enforcement**: Strike system for accountability

## 📈 Future Enhancements

The TMUX Bible integration provides a foundation for:
- Machine learning-based agent performance prediction
- Advanced compliance scoring algorithms
- Integration with external project management tools
- Real-time collaboration metrics and optimization

---

This integration transforms Agent-MCP from a basic multi-agent system into a production-ready orchestration platform that learns from real-world failures and implements proven protocols for success.