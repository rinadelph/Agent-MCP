# Agent-MCP Node.js Implementation

A TypeScript/Node.js port of the Agent-MCP (Multi-Agent Collaboration Protocol) system with backwards compatibility support.

## Architecture

This implementation uses a **backwards compatible MCP server** that supports both:
- **Streamable HTTP** (protocol version 2025-03-26) - Primary transport
- **HTTP+SSE** (protocol version 2024-11-05) - Fallback transport for legacy clients

## Features

- ✅ Backwards compatibility with existing MCP clients
- ✅ Session management and resumability
- ✅ Multi-transport support (Streamable HTTP + SSE)
- ✅ Real-time notifications via Server-Sent Events
- ✅ Tool registration and execution system
- ✅ CORS support for web clients
- ✅ Graceful error handling and shutdown

## Quick Start

### Install Dependencies

```bash
cd agent-mcp-node
npm install
```

### Run the Server

```bash
# Development mode with auto-restart
npm run dev

# Or run directly
npm run server

# Or with custom port and project directory
npm run server -- --port 4000 --project-dir /path/to/project
```

### Global Installation (Optional)

After building the project, you can create a global command:

```bash
npm run build
npm link

# Now you can run from anywhere
agent-mcp --port 4000 --project-dir /path/to/any/project
```

#### CLI Options

The server supports the following command line options:

- `-p, --port <number>`: Port to run the server on (default: 3001)
- `--project-dir <path>`: Project directory to operate in (default: current working directory)
- `-V, --version`: Display version number
- `-h, --help`: Display help information

**Note:** You can also set the port using environment variables:
```bash
PORT=4000 npm run server
```
CLI options take precedence over environment variables.

**Examples:**

```bash
# Start on port 4000
npm run server -- --port 4000

# Start with custom project directory
npm run server -- --project-dir /home/user/my-project

# Start on port 5000 in specific directory
npm run server -- --port 5000 --project-dir /path/to/project

# Show help
npm run server -- --help
```

The server will start on the specified port (default: `http://localhost:3001`) with these endpoints:

- **MCP Endpoint**: `http://localhost:3001/mcp` (GET/POST/DELETE)
- **Health Check**: `http://localhost:3001/health` (GET)
- **Statistics**: `http://localhost:3001/stats` (GET)

### Test with Client

In another terminal:

```bash
npm run test-client
```

The client will automatically detect the best transport method and connect.

## Server Endpoints

### Streamable HTTP (Recommended)
- **Endpoint**: `/mcp`
- **Methods**: GET, POST, DELETE
- **Headers**: `mcp-session-id`
- **Protocol**: 2025-03-26

### HTTP+SSE (Legacy)
- **SSE Stream**: `/sse` (GET)
- **Messages**: `/messages` (POST)
- **Headers**: `x-session-id`
- **Protocol**: 2024-11-05

## Development

### Build TypeScript

```bash
npm run build
```

### Run Production Build

```bash
npm run start
```

### Clean Build Files

```bash
npm run clean
```

## Next Steps

This foundation provides:

1. **Transport Layer**: Backwards compatible MCP server
2. **Session Management**: Multi-session support with proper isolation
3. **Tool System**: Framework for registering and executing tools
4. **Notifications**: Real-time event streaming

Ready for extending with Agent-MCP specific features:
- Multi-agent coordination tools
- Project context management
- File locking and state management
- RAG/vector search integration
- Database persistence layer

## Architecture Decisions

- **Primary Transport**: Streamable HTTP for modern clients
- **Fallback Transport**: SSE for legacy compatibility
- **Session Isolation**: Prevents mixing transport types per session
- **Scalability**: Foundation ready for distributed message routing
- **IDE Integration**: Compatible with Claude Code and other MCP clients