#!/bin/bash

# Agent-MCP Testing Suite
# This script creates a single test environment and initializes the MCP server with Claude Code

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
TEST_DIR="$SCRIPT_DIR/tests/test-1"
DEFAULT_PORT=8002

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
    if session_exists "agentmcp-test"; then
        log_info "Terminating MCP server session"
        tmux kill-session -t "agentmcp-test" 2>/dev/null || true
    fi
    
    if session_exists "claude-test"; then
        log_info "Terminating Claude session"
        tmux kill-session -t "claude-test" 2>/dev/null || true
    fi
    
    exit $exit_code
}

# Set up cleanup trap
trap cleanup EXIT INT TERM

# Function to wait for server startup
wait_for_server() {
    local port=$1
    local max_attempts=15
    local attempt=0
    
    log_info "Waiting for MCP server to start on port $port..."
    
    while [[ $attempt -lt $max_attempts ]]; do
        # Check if port is listening instead of making HTTP requests
        if netstat -tuln | grep -q ":$port "; then
            log_success "MCP server is listening on port $port!"
            return 0
        fi
        
        ((attempt++))
        sleep 2
        echo -n "."
    done
    
    log_error "MCP server failed to start after $max_attempts attempts"
    return 1
}

# Function to extract admin token from tmux session
extract_admin_token() {
    local session=$1
    local max_attempts=20
    local attempt=0
    
    log_info "Extracting admin token from MCP server output..."
    
    while [[ $attempt -lt $max_attempts ]]; do
        # Capture the tmux session buffer and look for admin token
        local buffer=$(tmux capture-pane -t "$session" -p 2>/dev/null || echo "")
        
        # Look for patterns like "Admin Token: xxx" or "MCP Admin Token: xxx"
        local token=$(echo "$buffer" | grep -oE "(Admin Token|MCP Admin Token).*: [a-fA-F0-9]+" | tail -1 | grep -oE "[a-fA-F0-9]{8,}" || echo "")
        
        if [[ -n "$token" ]]; then
            echo "$token"
            return 0
        fi
        
        ((attempt++))
        sleep 1
    done
    
    log_error "Could not extract admin token from server output"
    return 1
}

# Main execution
main() {
    log_info "Starting Agent-MCP Testing Suite"
    
    # Check dependencies
    if ! command -v uv &> /dev/null; then
        log_error "uv is required but not installed. Please install uv first."
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
    
    # Create or use project directory (always delete old testing repo)
    if [[ -z "$project_dir" ]]; then
        project_dir="$TEST_DIR/project"
        log_info "Deleting old testing repo and creating fresh test directory: $TEST_DIR"
        rm -rf "$TEST_DIR" 2>/dev/null || true
        mkdir -p "$project_dir"
        
        # Initialize a basic project structure
        cat > "$project_dir/README.md" << EOF
# Test Project

This is a test project for Agent-MCP testing suite.

Created: $(date)
Port: $port
EOF
        
        # Create a simple Python project structure
        mkdir -p "$project_dir/src"
        cat > "$project_dir/src/__init__.py" << EOF
"""
Test project for Agent-MCP
"""
__version__ = "0.1.0"
EOF
        
        cat > "$project_dir/pyproject.toml" << EOF
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "test-project"
version = "0.1.0"
description = "Test project for Agent-MCP"
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
    
    # Create and start MCP server session
    log_info "Starting MCP server..."
    tmux new-session -d -s "agentmcp-test" -c "$REPO_ROOT"
    
    # Start the MCP server
    local mcp_command="uv run -m agent_mcp.cli --port $port --project-dir '$project_dir'"
    log_info "Running: $mcp_command"
    tmux send-keys -t "agentmcp-test" "$mcp_command" Enter
    
    # Wait for server to start
    if ! wait_for_server "$port"; then
        log_error "Failed to start MCP server"
        exit 1
    fi
    
    # Extract admin token
    log_info "Extracting admin token..."
    local admin_token
    if ! admin_token=$(extract_admin_token "agentmcp-test"); then
        log_error "Failed to extract admin token"
        exit 1
    fi
    
    log_success "Admin token extracted: $admin_token"
    
    # Create Claude session
    log_info "Setting up Claude Code session..."
    tmux new-session -d -s "claude-test" -c "$project_dir"
    
    # Wait a moment for session to initialize
    sleep 2
    
    # Add MCP server to Claude
    log_info "Adding MCP server to Claude Code..."
    tmux send-keys -t "claude-test" "claude mcp add -t sse AgentMCP http://localhost:$port/sse" Enter
    
    # Wait for MCP add to complete
    sleep 3
    
    # Start Claude Code
    log_info "Starting Claude Code..."
    tmux send-keys -t "claude-test" "claude" Enter
    
    # Wait for Claude to start
    sleep 5
    
    # Initialize admin agent
    log_info "Initializing admin agent..."
    local admin_init_message="You are the admin agent.
Admin Token: $admin_token

Your role is to:
- Coordinate all development work
- Create and manage worker agents  
- Maintain project context
- Assign tasks based on agent specializations

TESTING INSTRUCTIONS:
1. Create a task for building a super complex calculator in Python with features like:
   - Scientific functions (trigonometry, logarithms, powers)
   - Expression parsing and evaluation
   - Memory functions (store, recall, clear)
   - History of calculations
   - Error handling for invalid inputs
   - Unit conversions
   - Statistical functions

2. Create a worker agent and assign this complex calculator task

3. Monitor the agent completing the task and watch the testing agent auto-launch

Query the project RAG for current status and begin coordination."
    
    # Send initialization message to Claude (message and Enter separately)
    tmux send-keys -t "claude-test" "$admin_init_message"
    sleep 1
    tmux send-keys -t "claude-test" Enter
    
    # Create summary file
    cat > "$TEST_DIR/test-info.txt" << EOF
Agent-MCP Test Environment
Created: $(date)

Configuration:
- Port: $port
- Project Directory: $project_dir
- Admin Token: $admin_token

Tmux Sessions:
- MCP Server: agentmcp-test
- Claude Code: claude-test

Commands to access:
- MCP Server: tmux attach-session -t agentmcp-test
- Claude Code: tmux attach-session -t claude-test

Test Project Structure:
$(find "$project_dir" -type f | head -20)
EOF
    
    log_success "Test environment is ready!"
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${GREEN}Test Environment Summary${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo -e "${BLUE}Project Directory:${NC} $project_dir"
    echo -e "${BLUE}MCP Server Port:${NC} $port"
    echo -e "${BLUE}Admin Token:${NC} $admin_token"
    echo ""
    echo -e "${YELLOW}Tmux Sessions:${NC}"
    echo -e "  MCP Server: ${GREEN}tmux attach-session -t agentmcp-test${NC}"
    echo -e "  Claude Code: ${GREEN}tmux attach-session -t claude-test${NC}"
    echo ""
    echo -e "${YELLOW}Useful Commands:${NC}"
    echo -e "  View MCP logs: ${GREEN}tmux capture-pane -t agentmcp-test -p${NC}"
    echo -e "  Send to Claude: ${GREEN}tmux send-keys -t claude-test 'your message' Enter${NC}"
    echo -e "  Kill test: ${GREEN}tmux kill-session -t agentmcp-test && tmux kill-session -t claude-test${NC}"
    echo ""
    echo -e "${GREEN}Admin agent has been initialized and is ready for commands!${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Attach to Claude session by default
    log_info "Attaching to Claude Code session..."
    exec tmux attach-session -t "claude-test"
}

# Run main function with all arguments
main "$@"