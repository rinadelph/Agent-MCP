#!/bin/bash

# Basic functionality test for Agent-MCP Node.js
set -e

echo "🧪 Testing Agent-MCP Node.js Basic Functionality"
echo "================================================"

PORT=3001
BASE_URL="http://localhost:$PORT"

# Test 1: Health check
echo "📊 Testing health endpoint..."
HEALTH=$(curl -s "$BASE_URL/health")
if echo "$HEALTH" | grep -q '"status":"healthy"'; then
    echo "✅ Health check passed"
else
    echo "❌ Health check failed"
    exit 1
fi

# Test 2: Statistics endpoint
echo "📈 Testing statistics endpoint..."
STATS=$(curl -s "$BASE_URL/stats")
if echo "$STATS" | grep -q '"database"'; then
    echo "✅ Statistics endpoint working"
    TOOL_COUNT=$(echo "$STATS" | grep -o '"tools":[0-9]*' | grep -o '[0-9]*')
    echo "📋 Available tools: $TOOL_COUNT"
else
    echo "❌ Statistics endpoint failed"
    exit 1
fi

# Test 3: MCP Initialize
echo "🔗 Testing MCP initialize..."
INIT_RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -H "Accept: application/json, text/event-stream" \
    -d '{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "test-client", "version": "1.0.0"}}}' \
    "$BASE_URL/mcp")

if echo "$INIT_RESPONSE" | grep -q '"result"'; then
    echo "✅ MCP initialize successful"
    
    # Extract session ID for further tests
    SESSION_ID=$(echo "$INIT_RESPONSE" | grep -o 'id: [^_]*' | head -1 | cut -d' ' -f2)
    echo "🔑 Session ID: ${SESSION_ID:0:20}..."
else
    echo "❌ MCP initialize failed"
    echo "Response: $INIT_RESPONSE"
    exit 1
fi

echo ""
echo "🎉 All basic functionality tests passed!"
echo "✅ Agent-MCP Node.js server is working correctly"
echo ""
echo "🔧 Next steps:"
echo "   - Test actual MCP tools with Claude Code"
echo "   - Implement remaining Agent-MCP Python tools"
echo "   - Add task management and agent coordination"
echo "   - Test multi-agent scenarios"