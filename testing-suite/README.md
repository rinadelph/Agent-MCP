# Agent-MCP Testing Suite

Automated testing environment for Agent-MCP with Claude Code integration.

## Quick Start

```bash
# Start test environment
./run-test.sh

# Clean up when done
./cleanup.sh
```

## What It Does

The testing suite automatically:

1. **Creates isolated test environment** in `tests/test-1/`
2. **Starts MCP server** on available port (default: 8002)
3. **Launches Claude Code** in separate tmux session
4. **Connects Claude to MCP** server via SSE
5. **Initializes admin agent** with extracted admin token
6. **Drops you into Claude session** ready to test

## Files Created

```
testing-suite/
├── tests/
│   └── test-1/
│       ├── project/          # Test project directory
│       │   ├── README.md
│       │   ├── pyproject.toml
│       │   └── src/
│       └── test-info.txt     # Test environment details
├── run-test.sh              # Main test script
├── cleanup.sh               # Cleanup script
└── README.md               # This file
```

## Usage

### Basic Usage
```bash
./run-test.sh
```

### With Custom Project Directory
```bash
./run-test.sh --project-dir /path/to/your/project
```

### With Custom Port
```bash
./run-test.sh --port 8003
```

## Tmux Sessions

The script creates two tmux sessions:

- **`agentmcp-test`** - MCP server running
- **`claude-test`** - Claude Code interface

### Accessing Sessions

```bash
# Attach to Claude (main testing interface)
tmux attach-session -t claude-test

# View MCP server logs
tmux attach-session -t agentmcp-test

# Send commands to Claude programmatically
tmux send-keys -t claude-test 'your message here' Enter
```

## Testing Workflow

1. **Start environment**: `./run-test.sh`
2. **Test features** in Claude session (auto-attached)
3. **View server logs** in MCP session if needed
4. **Clean up**: `./cleanup.sh` when done

## Admin Agent

The admin agent is automatically initialized with:

- **Admin token** extracted from server
- **Coordination role** for managing worker agents
- **RAG access** for project context
- **Task management** capabilities

Ready to:
- Create worker agents
- Assign tasks
- Coordinate development work
- Test the new testing agent auto-launch feature

## Cleanup Options

```bash
# Clean up sessions only (preserve files)
./cleanup.sh

# Clean up everything including test files
./cleanup.sh --remove-files
```

## Dependencies

- `uv` - Python package manager
- `tmux` - Terminal multiplexer
- `claude` - Claude Code CLI
- `curl` - For server health checks

## Troubleshooting

### Server Won't Start
- Check if port is already in use
- Verify `uv` and dependencies are installed
- Check MCP server logs: `tmux capture-pane -t agentmcp-test -p`

### Claude Connection Issues
- Ensure MCP server is running first
- Check Claude MCP configuration: `claude mcp list`
- Verify SSE endpoint: `curl http://localhost:8002/sse`

### Token Extraction Failed
- MCP server may not have started properly
- Check server output for admin token display
- Look in tmux session: `tmux capture-pane -t agentmcp-test -p`

## Testing the Testing Agent Feature

Once the environment is running, you can test the new auto-testing feature:

1. Create a task: `create_task`
2. Create a worker agent and assign the task
3. Have the worker complete the task (status → "completed")
4. Watch as a testing agent automatically launches
5. Observe the testing agent's critical validation process

The testing agent will:
- Pause the completing agent
- Launch in its own tmux session
- Get enriched context about what was completed
- Perform heavy criticism and real functionality tests
- Send pass/fail feedback to the original agent