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
npm run test-server
```

The server will start on `http://localhost:3000` with these endpoints:

- **Streamable HTTP**: `http://localhost:3000/mcp` (GET/POST/DELETE)
- **SSE (deprecated)**: `http://localhost:3000/sse` (GET) and `http://localhost:3000/messages` (POST)

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