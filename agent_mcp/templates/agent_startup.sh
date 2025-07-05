#!/bin/bash
# Agent-MCP Agent Startup Script Template
# This script can be customized for specific agent initialization

# Environment variables should be set by the tmux session creation:
# - MCP_AGENT_ID: The agent's unique identifier
# - MCP_AGENT_TOKEN: The agent's authentication token
# - MCP_SERVER_URL: The MCP server URL
# - MCP_WORKING_DIR: The agent's working directory
# - MCP_ADMIN_TOKEN: Admin token (if this is an admin agent)

echo "=== Agent-MCP Agent Startup ==="
echo "Agent ID: ${MCP_AGENT_ID:-not-set}"
echo "Working Dir: ${MCP_WORKING_DIR:-not-set}"
echo "Server URL: ${MCP_SERVER_URL:-not-set}"
echo "Token: ${MCP_AGENT_TOKEN:0:8}... (truncated)"
echo "================================"

# Change to working directory
if [ -n "$MCP_WORKING_DIR" ]; then
    cd "$MCP_WORKING_DIR" || {
        echo "ERROR: Failed to change to working directory: $MCP_WORKING_DIR"
        exit 1
    }
fi

# Check if Claude CLI is available
if ! command -v claude &> /dev/null; then
    echo "ERROR: Claude CLI not found. Please install Claude Code CLI."
    echo "Visit: https://claude.ai/code for installation instructions"
    exit 1
fi

# Launch Claude with the specified options
echo "Launching Claude Code CLI..."
exec claude --dangerously-skip-permissions