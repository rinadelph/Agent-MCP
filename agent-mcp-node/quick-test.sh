#!/bin/bash

# Quick test script for Agent-MCP Node.js server
# Tests the server endpoints manually

set -e

PORT=3001
SERVER_URL="http://localhost:$PORT"

echo "🧪 Testing Agent-MCP Node.js Server on $SERVER_URL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Test 1: Check if server is running
echo "1️⃣  Testing server availability..."
if curl -s --fail --max-time 5 "$SERVER_URL/mcp" > /dev/null; then
    echo "✅ Server is responding"
else
    echo "❌ Server is not responding. Make sure to run: npm run test-server"
    exit 1
fi

# Test 2: Test HTTP MCP endpoint with initialize
echo ""
echo "2️⃣  Testing HTTP MCP initialize..."
INIT_RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
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
    "$SERVER_URL/mcp")

if echo "$INIT_RESPONSE" | grep -q '"result"'; then
    echo "✅ Initialize request successful"
    echo "📄 Response preview: $(echo "$INIT_RESPONSE" | head -c 150)..."
else
    echo "❌ Initialize request failed"
    echo "📄 Response: $INIT_RESPONSE"
fi

# Test 3: Test SSE endpoint
echo ""
echo "3️⃣  Testing SSE endpoint..."
SSE_RESPONSE=$(curl -s --max-time 3 \
    -H "Accept: text/event-stream" \
    -H "x-session-id: test-session-123" \
    "$SERVER_URL/sse" || echo "timeout")

if [[ "$SSE_RESPONSE" != "timeout" && -n "$SSE_RESPONSE" ]]; then
    echo "✅ SSE endpoint responding"
    echo "📄 Response preview: $(echo "$SSE_RESPONSE" | head -c 100)..."
else
    echo "⚠️  SSE endpoint timeout (expected for testing)"
fi

# Test 4: Test tools listing (requires session)
echo ""
echo "4️⃣  Testing tools listing..."
TOOLS_RESPONSE=$(curl -s -X POST \
    -H "Content-Type: application/json" \
    -H "mcp-session-id: test-session-456" \
    -d '{
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list"
    }' \
    "$SERVER_URL/mcp")

if echo "$TOOLS_RESPONSE" | grep -q '"tools"'; then
    echo "✅ Tools listing successful"
    
    # Extract tool names
    if command -v jq &> /dev/null; then
        echo "🔧 Available tools:"
        echo "$TOOLS_RESPONSE" | jq -r '.result.tools[].name' | sed 's/^/  - /'
    else
        echo "📄 Tools response: $(echo "$TOOLS_RESPONSE" | head -c 200)..."
    fi
else
    echo "❌ Tools listing failed"
    echo "📄 Response: $TOOLS_RESPONSE"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎉 Manual testing complete!"
echo ""
echo "📋 Next steps:"
echo "  1. Run the full test suite: ./test-suite.sh"
echo "  2. Add server to Claude: claude mcp add --transport http AgentMCP-Node $SERVER_URL/mcp"
echo "  3. Test in Claude: /mcp and try the 'start-notification-stream' tool"
echo ""