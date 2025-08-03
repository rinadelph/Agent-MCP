#!/bin/bash

# Test Environment Variables in Tmux Agent Sessions
# Tests that environment variables are properly set in agent tmux sessions

set -e  # Exit on any error

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

# Function to check if tmux session exists
session_exists() {
    tmux has-session -t "$1" 2>/dev/null
}

# Function to create test session with environment variables
create_test_session() {
    local session_name="$1"
    local test_env_vars="$2"
    
    # Kill existing session if it exists
    if session_exists "$session_name"; then
        log_info "Cleaning up existing session: $session_name"
        tmux kill-session -t "$session_name" 2>/dev/null || true
        sleep 1
    fi
    
    log_info "Creating test session: $session_name"
    
    # Create session first, then set environment variables
    tmux new-session -d -s "$session_name"
    
    # Set environment variables in the session
    if [[ -n "$test_env_vars" ]]; then
        while IFS= read -r line; do
            if [[ -n "$line" && "$line" == *"="* ]]; then
                local key="${line%%=*}"
                local value="${line#*=}"
                tmux send-keys -t "$session_name" "export $key='$value'" Enter
                sleep 0.1
            fi
        done <<< "$test_env_vars"
    fi
    
    # Wait for session to be ready
    sleep 1
    
    return 0
}

# Function to test environment variables in session
test_env_vars_in_session() {
    local session_name="$1"
    local expected_vars="$2"
    local test_results=()
    local all_passed=true
    
    if ! session_exists "$session_name"; then
        log_error "Session $session_name does not exist"
        return 1
    fi
    
    log_info "Testing environment variables in session: $session_name"
    
    # Test each expected variable
    while IFS= read -r line; do
        if [[ -z "$line" || "$line" != *"="* ]]; then
            continue
        fi
        
        local key="${line%%=*}"
        local expected_value="${line#*=}"
        
        # Get actual value from session - use a more reliable method
        tmux send-keys -t "$session_name" "echo \"ENV_VAR_${key}=\$${key}\"" Enter
        sleep 0.5
        local actual_value=$(tmux capture-pane -t "$session_name" -p | grep "ENV_VAR_${key}=" | tail -1 2>/dev/null || echo "")
        
        # Extract the value after the equals sign
        if [[ "$actual_value" =~ ENV_VAR_${key}=(.*) ]]; then
            actual_value="${BASH_REMATCH[1]}"
        else
            actual_value=""
        fi
        
        # Clean up the captured output
        actual_value=$(echo "$actual_value" | tr -d '\r\n' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        
        if [[ "$actual_value" == "$expected_value" ]]; then
            log_success "✓ $key = '$actual_value' (matches expected)"
            test_results+=("PASS: $key")
        else
            log_error "✗ $key = '$actual_value' (expected: '$expected_value')"
            test_results+=("FAIL: $key")
            all_passed=false
        fi
        
        sleep 0.5  # Small delay between tests
    done <<< "$expected_vars"
    
    return $([ "$all_passed" = true ] && echo 0 || echo 1)
}

# Function to test common agent environment variables
test_agent_env_vars() {
    local session_name="env-test-agent-$$"
    
    # Define test environment variables for agent
    local test_env_vars="MCP_AGENT_ID=test-agent-123
MCP_AGENT_TOKEN=test-token-456
MCP_SERVER_URL=http://localhost:3000
NODE_ENV=test
AGENT_WORKDIR=/tmp/agent-test"
    
    log_info "Testing Agent Environment Variables"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Create test session with environment variables
    if ! create_test_session "$session_name" "$test_env_vars"; then
        log_error "Failed to create test session"
        return 1
    fi
    
    # Test the environment variables
    if test_env_vars_in_session "$session_name" "$test_env_vars"; then
        log_success "All agent environment variables passed!"
        local test_passed=true
    else
        log_error "Some agent environment variables failed!"
        local test_passed=false
    fi
    
    # Cleanup
    if session_exists "$session_name"; then
        log_info "Cleaning up test session: $session_name"
        tmux kill-session -t "$session_name" 2>/dev/null || true
    fi
    
    return $([ "$test_passed" = true ] && echo 0 || echo 1)
}

# Function to test existing agent sessions
test_existing_agent_sessions() {
    log_info "Testing Existing Agent Sessions"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Find existing agent sessions
    local agent_sessions=($(tmux list-sessions -F "#{session_name}" 2>/dev/null | grep -E "(agent|test)" || true))
    
    if [[ ${#agent_sessions[@]} -eq 0 ]]; then
        log_warning "No existing agent sessions found to test"
        return 0
    fi
    
    local sessions_tested=0
    local sessions_passed=0
    
    for session in "${agent_sessions[@]}"; do
        if ! session_exists "$session"; then
            continue
        fi
        
        log_info "Testing session: $session"
        sessions_tested=$((sessions_tested + 1))
        
        # Test basic environment variables that should be present
        local basic_tests="PATH=$PATH
HOME=$HOME
USER=$USER"
        
        # Send a test command to capture environment
        tmux send-keys -t "$session" "env | grep -E '^(MCP_|AGENT_|NODE_|PATH|HOME|USER)' | head -10" Enter
        sleep 2
        
        # Capture the output
        local env_output=$(tmux capture-pane -t "$session" -p | tail -10)
        
        if [[ -n "$env_output" && "$env_output" != *"command not found"* ]]; then
            log_success "✓ Session $session has accessible environment"
            sessions_passed=$((sessions_passed + 1))
            
            # Show relevant environment variables
            echo "$env_output" | grep -E '^(MCP_|AGENT_|NODE_)' | head -3 | while read line; do
                log_info "  Found: $line"
            done
        else
            log_error "✗ Session $session environment test failed"
        fi
        
        echo ""
    done
    
    log_info "Tested $sessions_tested existing sessions, $sessions_passed passed"
    return $([ $sessions_passed -eq $sessions_tested ] && echo 0 || echo 1)
}

# Function to run comprehensive environment variable tests
run_comprehensive_tests() {
    log_info "Starting Comprehensive Environment Variable Tests"
    echo "════════════════════════════════════════════════════════════════════"
    
    local total_tests=0
    local passed_tests=0
    
    # Test 1: Agent Environment Variables
    total_tests=$((total_tests + 1))
    if test_agent_env_vars; then
        passed_tests=$((passed_tests + 1))
    fi
    
    echo ""
    
    # Test 2: Existing Agent Sessions
    total_tests=$((total_tests + 1))
    if test_existing_agent_sessions; then
        passed_tests=$((passed_tests + 1))
    fi
    
    echo ""
    echo "════════════════════════════════════════════════════════════════════"
    log_info "Test Summary: $passed_tests/$total_tests tests passed"
    
    if [[ $passed_tests -eq $total_tests ]]; then
        log_success "🎉 All environment variable tests passed!"
        return 0
    else
        log_error "❌ Some environment variable tests failed!"
        return 1
    fi
}

# Main execution
main() {
    echo -e "${BLUE}🧪 Agent-MCP Environment Variable Test Suite${NC}"
    echo "Testing tmux agent session environment variable handling"
    echo ""
    
    # Check dependencies
    if ! command -v tmux &> /dev/null; then
        log_error "tmux is required but not installed. Please install tmux first."
        exit 1
    fi
    
    # Parse command line arguments
    local test_type="comprehensive"
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --agent-vars)
                test_type="agent"
                shift
                ;;
            --existing)
                test_type="existing"
                shift
                ;;
            --comprehensive)
                test_type="comprehensive"
                shift
                ;;
            -h|--help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --agent-vars     Test only agent environment variables"
                echo "  --existing       Test only existing sessions"
                echo "  --comprehensive  Run all tests (default)"
                echo "  -h, --help       Show this help message"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done
    
    # Run the specified tests
    case $test_type in
        agent)
            test_agent_env_vars
            ;;
        existing)
            test_existing_agent_sessions
            ;;
        comprehensive)
            run_comprehensive_tests
            ;;
        *)
            log_error "Invalid test type: $test_type"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"