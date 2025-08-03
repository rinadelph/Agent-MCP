#!/bin/bash

# Agent-MCP Node.js Testing Suite
# This script tests the MCP server setup and tool availability with Claude Code

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_DIR="$SCRIPT_DIR/tests/test-1"
DEFAULT_PORT=3000

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to find available port
find_available_port() {
    local port=$DEFAULT_PORT
    while netstat -tuln | grep -q ":$port "; do
        ((port++))
    done
    echo $port
}

# Function to check if tmux session exists
session_exists() {
    tmux has-session -t "$1" 2>/dev/null
}

# Function to cleanup on exit
cleanup() {
    local exit_code=$?
    log_info "Cleaning up..."
    
    # Kill tmux sessions if they exist
    if session_exists "agentmcp-node-test"; then
        log_info "Terminating MCP Node.js server session"
        tmux kill-session -t "agentmcp-node-test" 2>/dev/null || true
    fi
    
    if session_exists "claude-mcp-test"; then
        log_info "Terminating Claude session"
        tmux kill-session -t "claude-mcp-test" 2>/dev/null || true
    fi
    
    exit $exit_code
}

# Function to restart server and Claude (for testing iterations)
restart_server_and_claude() {
    local port=$1
    local project_dir=$2
    
    log_info "Restarting MCP server and Claude for fresh connection..."
    
    # Kill existing sessions
    if session_exists "agentmcp-node-test"; then
        log_info "Stopping existing MCP server..."
        tmux kill-session -t "agentmcp-node-test" 2>/dev/null || true
        sleep 2
    fi
    
    if session_exists "claude-mcp-test"; then
        log_info "Stopping existing Claude session..."
        tmux kill-session -t "claude-mcp-test" 2>/dev/null || true
        sleep 2
    fi
    
    # Restart MCP server
    log_info "Starting fresh MCP Node.js server on port $port..."
    tmux new-session -d -s "agentmcp-node-test" -c "$SCRIPT_DIR"
    local mcp_command="PORT=$port npm run test-server"
    tmux send-keys -t "agentmcp-node-test" "$mcp_command" Enter
    
    # Wait for server to start
    if ! wait_for_server "$port"; then
        log_error "Failed to restart MCP server"
        return 1
    fi
    
    # Restart Claude with fresh MCP configuration
    log_info "Starting fresh Claude session..."
    tmux new-session -d -s "claude-mcp-test" -c "$project_dir"
    sleep 2
    
    # Reconfigure MCP server
    tmux send-keys -t "claude-mcp-test" "claude mcp remove AgentMCP-Node 2>/dev/null || true" Enter
    sleep 2
    tmux send-keys -t "claude-mcp-test" "claude mcp add --transport http AgentMCP-Node http://localhost:$port/mcp" Enter
    sleep 3
    
    # Start Claude
    tmux send-keys -t "claude-mcp-test" "claude" Enter
    sleep 8
    
    log_success "Server and Claude restarted successfully!"
    return 0
}

# Set up cleanup trap
trap cleanup EXIT INT TERM

# Function to wait for server startup
wait_for_server() {
    local port=$1
    local max_attempts=15
    local attempt=0
    
    log_info "Waiting for MCP Node.js server to start on port $port..."
    
    while [[ $attempt -lt $max_attempts ]]; do
        # Check if port is listening
        if netstat -tuln | grep -q ":$port "; then
            log_success "MCP Node.js server is listening on port $port!"
            return 0
        fi
        
        ((attempt++))
        sleep 2
        echo -n "."
    done
    
    log_error "MCP Node.js server failed to start after $max_attempts attempts"
    return 1
}

# Function to test HTTP endpoint
test_http_endpoint() {
    local port=$1
    local endpoint="http://localhost:$port/mcp"
    
    log_info "Testing HTTP endpoint: $endpoint"
    
    # Test with curl - try to POST an initialize request
    local response=$(curl -s -w "%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"test-client","version":"1.0.0"}}}' \
        "$endpoint" || echo "000")
    
    local http_code="${response: -3}"
    local body="${response%???}"
    
    if [[ "$http_code" == "200" ]]; then
        log_success "HTTP endpoint responding correctly (status: $http_code)"
        log_info "Response preview: ${body:0:200}..."
        return 0
    else
        log_warning "HTTP endpoint status: $http_code"
        log_info "Response: $body"
        return 1
    fi
}

# Function to test SSE endpoint (fallback)
test_sse_endpoint() {
    local port=$1
    local endpoint="http://localhost:$port/sse"
    
    log_info "Testing SSE endpoint: $endpoint"
    
    # Test SSE endpoint with curl
    local response=$(curl -s -w "%{http_code}" -X GET \
        -H "Accept: text/event-stream" \
        -H "x-session-id: test-session-123" \
        --max-time 5 \
        "$endpoint" || echo "000")
    
    local http_code="${response: -3}"
    
    if [[ "$http_code" == "200" ]]; then
        log_success "SSE endpoint responding correctly (status: $http_code)"
        return 0
    else
        log_warning "SSE endpoint status: $http_code"
        return 1
    fi
}

# Main execution
main() {
    log_info "Starting Agent-MCP Node.js Testing Suite"
    
    # Check dependencies
    if ! command -v node &> /dev/null; then
        log_error "Node.js is required but not installed. Please install Node.js first."
        exit 1
    fi
    
    if ! command -v npm &> /dev/null; then
        log_error "npm is required but not installed. Please install npm first."
        exit 1
    fi
    
    if ! command -v tmux &> /dev/null; then
        log_error "tmux is required but not installed. Please install tmux first."
        exit 1
    fi
    
    if ! command -v claude &> /dev/null; then
        log_error "claude CLI is required but not installed. Please install Claude Code CLI first."
        exit 1
    fi
    
    # Parse command line arguments
    local port=""
    local project_dir=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --port)
                port="$2"
                shift 2
                ;;
            --project-dir)
                project_dir="$2"
                shift 2
                ;;
            -h|--help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --port PORT         Specify MCP server port (default: auto-detect)"
                echo "  --project-dir DIR   Use existing project directory"
                echo "  -h, --help          Show this help message"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Determine port
    if [[ -z "$port" ]]; then
        port=$(find_available_port)
    fi
    
    # Create test project directory
    if [[ -z "$project_dir" ]]; then
        project_dir="$TEST_DIR/project"
        log_info "Creating fresh test directory: $TEST_DIR"
        rm -rf "$TEST_DIR" 2>/dev/null || true
        mkdir -p "$project_dir"
        
        # Initialize a basic project structure
        cat > "$project_dir/README.md" << EOF
# Agent-MCP Node.js Test Project

This is a test project for the Agent-MCP Node.js testing suite.

Created: $(date)
Port: $port
EOF
        
        # Create a simple TypeScript project structure
        mkdir -p "$project_dir/src"
        cat > "$project_dir/src/index.ts" << EOF
/**
 * Test project for Agent-MCP Node.js
 */
export const version = "0.1.0";

export function greet(name: string): string {
    return \`Hello, \${name}! This is Agent-MCP Node.js.\`;
}
EOF
        
        cat > "$project_dir/package.json" << EOF
{
  "name": "agent-mcp-test-project",
  "version": "0.1.0",
  "description": "Test project for Agent-MCP Node.js",
  "main": "src/index.ts",
  "scripts": {
    "start": "node src/index.js"
  },
  "keywords": ["agent-mcp", "test"],
  "author": "Agent-MCP",
  "license": "MIT"
}
EOF
    else
        log_info "Using existing project directory: $project_dir"
        if [[ ! -d "$project_dir" ]]; then
            log_error "Project directory does not exist: $project_dir"
            exit 1
        fi
    fi
    
    # Convert to absolute path
    project_dir=$(realpath "$project_dir")
    
    log_info "Project Directory: $project_dir"
    log_info "Port: $port"
    
    # Check if dependencies are installed
    if [[ ! -d "$SCRIPT_DIR/node_modules" ]]; then
        log_info "Installing Node.js dependencies..."
        cd "$SCRIPT_DIR"
        npm install
    fi
    
    # Create and start MCP Node.js server session
    log_info "Starting MCP Node.js server..."
    tmux new-session -d -s "agentmcp-node-test" -c "$SCRIPT_DIR"
    
    # Start the MCP server with custom port
    local mcp_command="PORT=$port npm run test-server"
    
    log_info "Running: $mcp_command"
    tmux send-keys -t "agentmcp-node-test" "$mcp_command" Enter
    
    # Wait for server to start
    if ! wait_for_server "$port"; then
        log_error "Failed to start MCP Node.js server"
        exit 1
    fi
    
    # Test HTTP endpoint
    log_info "Testing MCP server endpoints..."
    if test_http_endpoint "$port"; then
        log_success "HTTP transport test passed"
    else
        log_warning "HTTP transport test failed"
    fi
    
    # Test SSE endpoint
    if test_sse_endpoint "$port"; then
        log_success "SSE transport test passed"
    else
        log_warning "SSE transport test failed"
    fi
    
    # Kill any existing Claude session to ensure clean restart
    if session_exists "claude-mcp-test"; then
        log_info "Cleaning up existing Claude session..."
        tmux kill-session -t "claude-mcp-test" 2>/dev/null || true
        sleep 1
    fi
    
    # Create Claude session
    log_info "Setting up Claude Code session..."
    tmux new-session -d -s "claude-mcp-test" -c "$project_dir"
    
    # Wait a moment for session to initialize
    sleep 2
    
    # Add MCP server to Claude (using HTTP transport) - remove existing first
    log_info "Configuring MCP Node.js server in Claude Code..."
    tmux send-keys -t "claude-mcp-test" "claude mcp remove AgentMCP-Node 2>/dev/null || true" Enter
    sleep 2
    tmux send-keys -t "claude-mcp-test" "claude mcp add --transport http AgentMCP-Node http://localhost:$port/mcp" Enter
    
    # Wait for MCP add to complete
    sleep 3
    
    # List MCP servers to verify
    log_info "Verifying MCP server configuration..."
    tmux send-keys -t "claude-mcp-test" "claude mcp list" Enter
    sleep 3
    
    # Start Claude Code (fresh instance to pick up new MCP server)
    log_info "Starting Claude Code with MCP server connection..."
    tmux send-keys -t "claude-mcp-test" "claude" Enter
    
    # Wait for Claude to start and establish MCP connections
    sleep 8
    
    # Test MCP connection and tools
    log_info "Testing MCP connection and available tools..."
    local test_message="Hello! I'm testing the Agent-MCP Node.js server connection.

Please help me test the MCP integration by:

1. Running /mcp to check the server connection status
2. List the available tools from the AgentMCP-Node server
3. Try calling the 'start-notification-stream' tool with parameters:
   - interval: 2 seconds
   - count: 3 notifications

This will test:
✅ MCP server connection
✅ Tool discovery
✅ Tool execution
✅ Real-time notifications

Let me know what tools are available and if the notification stream works!"
    
    # Send test message to Claude
    tmux send-keys -t "claude-mcp-test" "$test_message"
    sleep 1
    tmux send-keys -t "claude-mcp-test" Enter
    
    # Create summary file
    cat > "$TEST_DIR/test-info.txt" << EOF
Agent-MCP Node.js Test Environment
Created: $(date)

Configuration:
- Port: $port
- Project Directory: $project_dir
- Transport: HTTP (primary), SSE (fallback)

Tmux Sessions:
- MCP Node.js Server: agentmcp-node-test
- Claude Code: claude-mcp-test

Commands to access:
- MCP Server: tmux attach-session -t agentmcp-node-test
- Claude Code: tmux attach-session -t claude-mcp-test

MCP Server Endpoints:
- HTTP: http://localhost:$port/mcp
- SSE: http://localhost:$port/sse
- Messages: http://localhost:$port/messages

Test Commands in Claude:
- /mcp (check connection status)
- List tools and try 'start-notification-stream'

Test Project Structure:
$(find "$project_dir" -type f | head -10)
EOF
    
    log_success "MCP Node.js test environment is ready!"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${GREEN}Agent-MCP Node.js Test Environment Summary${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${BLUE}Project Directory:${NC} $project_dir"
    echo -e "${BLUE}MCP Server Port:${NC} $port"
    echo -e "${BLUE}Server URL:${NC} http://localhost:$port/mcp"
    echo ""
    echo -e "${YELLOW}Tmux Sessions:${NC}"
    echo -e "  MCP Node.js Server: ${GREEN}tmux attach-session -t agentmcp-node-test${NC}"
    echo -e "  Claude Code: ${GREEN}tmux attach-session -t claude-mcp-test${NC}"
    echo ""
    echo -e "${YELLOW}Testing Commands in Claude:${NC}"
    echo -e "  Check MCP status: ${GREEN}/mcp${NC}"
    echo -e "  Test tool: ${GREEN}Use the start-notification-stream tool${NC}"
    echo ""
    echo -e "${YELLOW}Useful Commands:${NC}"
    echo -e "  View server logs: ${GREEN}tmux capture-pane -t agentmcp-node-test -p${NC}"
    echo -e "  Send to Claude: ${GREEN}tmux send-keys -t claude-mcp-test 'your message' Enter${NC}"
    echo -e "  Kill tests: ${GREEN}tmux kill-session -t agentmcp-node-test && tmux kill-session -t claude-mcp-test${NC}"
    echo ""
    echo -e "${GREEN}Claude is ready to test the MCP Node.js server!${NC}"
    echo -e "${YELLOW}Testing instructions have been sent to Claude automatically.${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Attach to Claude session by default
    log_info "Attaching to Claude Code session..."
    exec tmux attach-session -t "claude-mcp-test"
}

# Run main function with all arguments
main "$@"