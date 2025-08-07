#!/bin/bash
# Agent-MCP Agent Startup Script Template
# Enhanced with TMUX Bible rules and lessons learned
# This script implements critical lessons from multi-agent orchestration experience

# Environment variables should be set by the tmux session creation:
# - MCP_AGENT_ID: The agent's unique identifier
# - MCP_AGENT_TOKEN: The agent's authentication token
# - MCP_SERVER_URL: The MCP server URL
# - MCP_WORKING_DIR: The agent's working directory
# - MCP_ADMIN_TOKEN: Admin token (if this is an admin agent)
# - MCP_AGENT_ROLE: Agent role (developer, pm, qa, devops, etc.)

echo "🚀 === Agent-MCP Agent Startup (Enhanced) ==="
echo "Agent ID: ${MCP_AGENT_ID:-not-set}"
echo "Agent Role: ${MCP_AGENT_ROLE:-general}"
echo "Working Dir: ${MCP_WORKING_DIR:-not-set}"
echo "Server URL: ${MCP_SERVER_URL:-not-set}"
echo "Token: ${MCP_AGENT_TOKEN:0:8}... (truncated)"
echo "TMUX Bible Integration: ACTIVE"
echo "=============================================="

# Change to working directory
if [ -n "$MCP_WORKING_DIR" ]; then
    cd "$MCP_WORKING_DIR" || {
        echo "❌ ERROR: Failed to change to working directory: $MCP_WORKING_DIR"
        exit 1
    }
    echo "✅ Changed to working directory: $MCP_WORKING_DIR"
else
    echo "⚠️  WARNING: No working directory specified, using current directory"
fi

# Verify we're in a git repository (Git Discipline - TMUX Bible)
if [ -d ".git" ]; then
    echo "✅ Git repository detected - git discipline will be enforced"
    
    # Show current git status for context
    echo "📊 Current git status:"
    git status --porcelain | head -5
    
    # Remind about git discipline rules
    echo ""
    echo "🔐 GIT DISCIPLINE RULES (MANDATORY):"
    echo "   • Commit every 30 minutes maximum"
    echo "   • Never work >1 hour without committing"
    echo "   • Use meaningful commit messages"
    echo "   • Command: git add -A && git commit -m 'Progress: [description]'"
else
    echo "⚠️  WARNING: Not in a git repository - git discipline cannot be enforced"
fi

# Check if Claude CLI is available
if ! command -v claude &> /dev/null; then
    echo "❌ ERROR: Claude CLI not found. Please install Claude Code CLI."
    echo "Visit: https://claude.ai/code for installation instructions"
    exit 1
fi

# Pre-launch checks and setup
echo ""
echo "🔍 Pre-launch checks:"

# Check for virtual environment if Python project
if [ -f "requirements.txt" ] || [ -f "pyproject.toml" ]; then
    if [ -n "$VIRTUAL_ENV" ]; then
        echo "✅ Python virtual environment active: $VIRTUAL_ENV"
    else
        echo "⚠️  Python project detected but no virtual environment active"
        if [ -d "venv" ]; then
            echo "   Found venv directory. Activate with: source venv/bin/activate"
        elif [ -d ".venv" ]; then
            echo "   Found .venv directory. Activate with: source .venv/bin/activate"
        fi
    fi
fi

# Check for Node.js project
if [ -f "package.json" ]; then
    echo "✅ Node.js project detected"
    if [ ! -d "node_modules" ]; then
        echo "⚠️  node_modules not found. Run 'npm install' if needed"
    fi
fi

# Set up auto-commit reminder (background process)
if [ -d ".git" ]; then
    (
        # Wait 30 minutes (1800 seconds), then remind about committing
        sleep 1800
        echo ""
        echo "⏰ AUTO-COMMIT REMINDER: It's been 30 minutes!"
        echo "   Time to commit your work: git add -A && git commit -m 'Progress: [description]'"
        echo ""
    ) &
    echo "✅ Auto-commit reminder set for 30 minutes"
fi

# Display agent-specific instructions based on role
echo ""
echo "📋 AGENT ROLE INSTRUCTIONS:"
case "${MCP_AGENT_ROLE:-general}" in
    "developer"|"dev")
        echo "   🔧 DEVELOPER AGENT RULES:"
        echo "   • Focus on implementation, not planning"
        echo "   • Use MCP tools exclusively when available"
        echo "   • Commit every 30 minutes with descriptive messages"
        echo "   • Test your code before marking tasks complete"
        echo "   • Ask for help after 10 minutes if stuck"
        ;;
    "pm"|"manager"|"project-manager")
        echo "   📊 PROJECT MANAGER RULES:"
        echo "   • Monitor ALL agents every 2-3 minutes"
        echo "   • Report issues TO orchestrator, don't wait to be asked"
        echo "   • Handle 80% of coordination independently"
        echo "   • Enforce git discipline across all agents"
        echo "   • YOU are the early warning system"
        ;;
    "qa"|"test")
        echo "   🧪 QA ENGINEER RULES:"
        echo "   • Verify EVERYTHING - no trust without verification"
        echo "   • Maintain >80% test coverage"
        echo "   • Create test plans for every feature"
        echo "   • Report quality issues immediately"
        ;;
    "devops"|"ops")
        echo "   ⚙️  DEVOPS ENGINEER RULES:"
        echo "   • Monitor service health continuously"
        echo "   • Automate everything possible"
        echo "   • Document all infrastructure changes"
        echo "   • Implement proper logging and monitoring"
        ;;
    *)
        echo "   📝 GENERAL AGENT RULES:"
        echo "   • Follow the 'Services First' principle"
        echo "   • One task at a time, complete before moving on"
        echo "   • Communicate status clearly and frequently"
        echo "   • Use descriptive commit messages"
        ;;
esac

# TMUX Bible Critical Rules
echo ""
echo "🔑 CRITICAL TMUX BIBLE RULES:"
echo "   1. 'Services First, Everything Else Second'"
echo "   2. 'One Agent, One Job, One Command'"
echo "   3. '5 Minutes to Compliance or Replacement'"
echo "   4. 'Git Commit Every 15 Minutes, No Exceptions'"
echo "   5. 'Running Badly Beats Not Running'"
echo "   6. 'Use What Exists, Create Nothing'"
echo "   7. 'MCP Tools Always, Basic Tools Never'"

# Budget discipline reminder (from TMUX Bible lessons)
echo ""
echo "💰 BUDGET DISCIPLINE:"
echo "   • Every message costs money - make them count"
echo "   • Work 10-15 minutes before asking for help"
echo "   • Be brief and direct - no long explanations"
echo "   • Handle 80% of issues independently"

echo ""
echo "🎯 Ready to launch Claude with --dangerously-skip-permissions"
echo "   Remember: YOU are responsible for maintaining discipline and quality"
echo ""

# Launch Claude with the specified options
echo "🚀 Launching Claude Code CLI..."
exec claude --dangerously-skip-permissions