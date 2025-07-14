#!/bin/bash
# Setup script for Agent-MCP Claude Code hooks
# This configures the multi-agent file locking system for Claude Code

set -e

echo "🔧 Setting up Agent-MCP Claude Code hooks..."

# Create .claude directory if it doesn't exist
mkdir -p .claude

# Backup existing settings if they exist
if [ -f ".claude/settings.json" ]; then
    timestamp=$(date +%s)
    echo "📦 Backing up existing settings to settings.json.backup.$timestamp"
    cp .claude/settings.json ".claude/settings.json.backup.$timestamp"
fi

# Create proper hook configuration
cat > .claude/settings.json << 'EOF'
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          {
            "type": "command",
            "command": "node \"./agent_mcp/hooks/file-lock-manager.js\"",
            "timeout": 30
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit|Read|Glob|Grep",
        "hooks": [
          {
            "type": "command",
            "command": "node \"./agent_mcp/hooks/activity-broadcaster.js\"",
            "timeout": 15
          }
        ]
      }
    ]
  }
}
EOF

# Verify hook files exist and are executable
if [ ! -f "agent_mcp/hooks/file-lock-manager.js" ]; then
    echo "❌ Error: Hook file agent_mcp/hooks/file-lock-manager.js not found"
    exit 1
fi

if [ ! -f "agent_mcp/hooks/activity-broadcaster.js" ]; then
    echo "❌ Error: Hook file agent_mcp/hooks/activity-broadcaster.js not found"
    exit 1
fi

# Make sure hook files are executable
chmod +x agent_mcp/hooks/*.js

# Create directories that hooks might need
mkdir -p .agent-locks
mkdir -p .agent-activity

echo "✅ Claude Code hooks configured successfully!"
echo ""
echo "The following hooks are now active:"
echo "  • PreToolUse: File locking to prevent conflicts"
echo "  • PostToolUse: Activity logging and lock release"
echo ""
echo "This enables proper multi-agent collaboration with file-level conflict prevention."
echo ""
echo "To verify the setup, try editing a file with Claude Code - you should see"
echo "no hook errors in the console."