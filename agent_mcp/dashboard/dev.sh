#!/bin/bash

echo "🚀 Starting Agent-MCP Dashboard..."
echo "📡 Dashboard URL: http://localhost:3000"
echo ""

# Set environment variables
export SKIP_ENV_VALIDATION=true
export NODE_ENV=development
export NEXT_TELEMETRY_DISABLED=1

# Check if TypeScript is installed globally
if ! command -v tsc &> /dev/null; then
    echo "Installing TypeScript globally..."
    npm install -g typescript
fi

# Start Next.js directly
exec next dev --port 3000 --hostname localhost