#!/bin/bash

# Universal Agent-MCP Node.js Test Suite
# This script tests all implemented features and can be run continuously during development

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_PORT=3001
DB_PATH="$SCRIPT_DIR/test.db"
LOG_FILE="$SCRIPT_DIR/test-results.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Test tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
    ((PASSED_TESTS++))
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    ((FAILED_TESTS++))
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

log_test() {
    echo -e "${PURPLE}[TEST]${NC} $1" | tee -a "$LOG_FILE"
    ((TOTAL_TESTS++))
}

log_section() {
    echo -e "\n${CYAN}========== $1 ==========${NC}" | tee -a "$LOG_FILE"
}

# Function to check if process is running on port
check_port() {
    local port=$1
    netstat -tuln | grep -q ":$port "
}

# Function to wait for server
wait_for_server() {
    local port=$1
    local max_attempts=10
    local attempt=0
    
    while [[ $attempt -lt $max_attempts ]]; do
        if check_port "$port"; then
            return 0
        fi
        ((attempt++))
        sleep 1
    done
    return 1
}

# Function to test HTTP endpoint
test_http_endpoint() {
    local url=$1
    local expected_status=${2:-200}
    local test_name=$3
    
    log_test "$test_name"
    
    local response=$(curl -s -w "%{http_code}" -X GET "$url" 2>/dev/null || echo "000")
    local status="${response: -3}"
    
    if [[ "$status" == "$expected_status" ]]; then
        log_success "$test_name - Status: $status"
        return 0
    else
        log_error "$test_name - Expected: $expected_status, Got: $status"
        return 1
    fi
}

# Function to test MCP initialize
test_mcp_initialize() {
    log_test "MCP Initialize Request"
    
    local response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        -d '{
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }' \
        "http://localhost:$TEST_PORT/mcp" 2>/dev/null || echo "")
    
    if echo "$response" | grep -q '"result"'; then
        log_success "MCP Initialize - Server responded correctly"
        return 0
    else
        log_error "MCP Initialize - Failed: $response"
        return 1
    fi
}

# Function to test database operations
test_database() {
    log_section "DATABASE TESTS"
    
    # Test 1: Database file creation
    log_test "Database File Creation"
    if [[ -f "$DB_PATH" ]]; then
        log_success "Database file exists: $DB_PATH"
    else
        log_warning "Database file not found (may not be implemented yet)"
    fi
    
    # Test 2: Database connection (when implemented)
    log_test "Database Connection Test"
    log_warning "Database connection test not implemented yet"
    
    # Test 3: Schema validation (when implemented)
    log_test "Database Schema Validation"
    log_warning "Schema validation not implemented yet"
}

# Function to test MCP tools
test_mcp_tools() {
    log_section "MCP TOOLS TESTS"
    
    # Test tools listing
    log_test "Tools Listing"
    local tools_response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        -H "mcp-session-id: test-session-tools" \
        -d '{
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        }' \
        "http://localhost:$TEST_PORT/mcp" 2>/dev/null || echo "")
    
    if echo "$tools_response" | grep -q '"tools"'; then
        log_success "Tools listing successful"
        
        # Count available tools
        if command -v jq &> /dev/null; then
            local tool_count=$(echo "$tools_response" | jq '.result.tools | length' 2>/dev/null || echo "0")
            log_info "Available tools: $tool_count"
            echo "$tools_response" | jq -r '.result.tools[].name' 2>/dev/null | while read tool; do
                log_info "  - $tool"
            done
        fi
    else
        log_error "Tools listing failed: $tools_response"
    fi
    
    # Test greet tool
    log_test "Greet Tool Execution"
    local greet_response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -H "Accept: application/json, text/event-stream" \
        -H "mcp-session-id: test-session-greet" \
        -d '{
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "greet",
                "arguments": {
                    "name": "Agent-MCP"
                }
            }
        }' \
        "http://localhost:$TEST_PORT/mcp" 2>/dev/null || echo "")
    
    if echo "$greet_response" | grep -q '"content"'; then
        log_success "Greet tool execution successful"
    else
        log_error "Greet tool execution failed: $greet_response"
    fi
}

# Function to test agent operations (when implemented)
test_agent_operations() {
    log_section "AGENT OPERATIONS TESTS"
    
    log_test "Agent Creation Test"
    log_warning "Agent creation not implemented yet"
    
    log_test "Agent Status Test"
    log_warning "Agent status not implemented yet"
    
    log_test "Agent Task Assignment Test"
    log_warning "Agent task assignment not implemented yet"
}

# Function to test task management (when implemented)
test_task_management() {
    log_section "TASK MANAGEMENT TESTS"
    
    log_test "Task Creation Test"
    log_warning "Task creation not implemented yet"
    
    log_test "Task Assignment Test"
    log_warning "Task assignment not implemented yet"
    
    log_test "Task Status Update Test"
    log_warning "Task status update not implemented yet"
}

# Function to test project context (when implemented)
test_project_context() {
    log_section "PROJECT CONTEXT TESTS"
    
    log_test "Context Storage Test"
    log_warning "Context storage not implemented yet"
    
    log_test "Context Retrieval Test"
    log_warning "Context retrieval not implemented yet"
    
    log_test "Context Search Test"
    log_warning "Context search not implemented yet"
}

# Function to test RAG functionality (when implemented)
test_rag_functionality() {
    log_section "RAG/VECTOR SEARCH TESTS"
    
    log_test "Document Indexing Test"
    log_warning "Document indexing not implemented yet"
    
    log_test "Vector Search Test"
    log_warning "Vector search not implemented yet"
    
    log_test "RAG Query Test"
    log_warning "RAG query not implemented yet"
}

# Function to test performance under load
test_performance() {
    log_section "PERFORMANCE TESTS"
    
    log_test "Concurrent Connections Test"
    local concurrent_requests=5
    local pids=()
    
    for i in $(seq 1 $concurrent_requests); do
        (curl -s "http://localhost:$TEST_PORT/health" > /dev/null) &
        pids+=($!)
    done
    
    # Wait for all requests to complete
    local failed=0
    for pid in "${pids[@]}"; do
        if ! wait "$pid"; then
            ((failed++))
        fi
    done
    
    if [[ $failed -eq 0 ]]; then
        log_success "Concurrent connections test - $concurrent_requests requests succeeded"
    else
        log_error "Concurrent connections test - $failed requests failed"
    fi
    
    log_test "Response Time Test"
    local start_time=$(date +%s%N)
    curl -s "http://localhost:$TEST_PORT/health" > /dev/null
    local end_time=$(date +%s%N)
    local response_time=$(( (end_time - start_time) / 1000000 )) # Convert to milliseconds
    
    if [[ $response_time -lt 100 ]]; then
        log_success "Response time test - ${response_time}ms (excellent)"
    elif [[ $response_time -lt 500 ]]; then
        log_success "Response time test - ${response_time}ms (good)"
    else
        log_warning "Response time test - ${response_time}ms (slow)"
    fi
}

# Function to cleanup
cleanup() {
    log_info "Cleaning up test environment..."
    
    # Kill tmux sessions
    tmux kill-session -t "agentmcp-test-server" 2>/dev/null || true
    
    # Remove test database
    rm -f "$DB_PATH" 2>/dev/null || true
}

# Function to generate test report
generate_report() {
    log_section "TEST SUMMARY"
    
    local success_rate=0
    if [[ $TOTAL_TESTS -gt 0 ]]; then
        success_rate=$(( (PASSED_TESTS * 100) / TOTAL_TESTS ))
    fi
    
    echo -e "\n${CYAN}================================${NC}"
    echo -e "${CYAN}        TEST RESULTS SUMMARY     ${NC}"
    echo -e "${CYAN}================================${NC}"
    echo -e "Total Tests:    ${TOTAL_TESTS}"
    echo -e "Passed Tests:   ${GREEN}${PASSED_TESTS}${NC}"
    echo -e "Failed Tests:   ${RED}${FAILED_TESTS}${NC}"
    echo -e "Success Rate:   ${success_rate}%"
    echo -e "Log File:       ${LOG_FILE}"
    echo -e "${CYAN}================================${NC}\n"
    
    if [[ $success_rate -ge 80 ]]; then
        echo -e "${GREEN}🎉 Great job! Most tests are passing.${NC}"
    elif [[ $success_rate -ge 50 ]]; then
        echo -e "${YELLOW}⚠️  Good progress, but some tests need attention.${NC}"
    else
        echo -e "${RED}❌ Many tests are failing, needs work.${NC}"
    fi
}

# Main execution
main() {
    # Initialize log file
    echo "Agent-MCP Node.js Test Suite - $(date)" > "$LOG_FILE"
    
    log_section "AGENT-MCP NODE.JS UNIVERSAL TEST SUITE"
    log_info "Starting comprehensive feature testing..."
    log_info "Test Port: $TEST_PORT"
    log_info "Script Directory: $SCRIPT_DIR"
    
    # Check dependencies
    log_section "DEPENDENCY CHECKS"
    
    log_test "Node.js Installation"
    if command -v node &> /dev/null; then
        local node_version=$(node --version)
        log_success "Node.js found: $node_version"
    else
        log_error "Node.js not installed"
        exit 1
    fi
    
    log_test "npm Installation"
    if command -v npm &> /dev/null; then
        local npm_version=$(npm --version)
        log_success "npm found: $npm_version"
    else
        log_error "npm not installed"
        exit 1
    fi
    
    # Start the MCP server
    log_section "SERVER STARTUP"
    
    log_info "Starting MCP server on port $TEST_PORT..."
    tmux new-session -d -s "agentmcp-test-server" -c "$SCRIPT_DIR"
    tmux send-keys -t "agentmcp-test-server" "PORT=$TEST_PORT npm run test-server" Enter
    
    if wait_for_server "$TEST_PORT"; then
        log_success "MCP server started successfully on port $TEST_PORT"
    else
        log_error "Failed to start MCP server"
        cleanup
        exit 1
    fi
    
    # Run all test suites
    log_section "BASIC CONNECTIVITY TESTS"
    
    test_http_endpoint "http://localhost:$TEST_PORT/health" 200 "Health Endpoint"
    test_mcp_initialize
    
    # Core functionality tests
    test_database
    test_mcp_tools
    test_agent_operations
    test_task_management
    test_project_context
    test_rag_functionality
    
    # Performance tests
    test_performance
    
    # Generate final report
    generate_report
    
    # Cleanup
    cleanup
    
    # Exit with appropriate code
    if [[ $FAILED_TESTS -eq 0 ]]; then
        log_success "All tests completed successfully!"
        exit 0
    else
        log_error "Some tests failed. Check the log for details."
        exit 1
    fi
}

# Set up cleanup trap
trap cleanup EXIT INT TERM

# Run main function
main "$@"