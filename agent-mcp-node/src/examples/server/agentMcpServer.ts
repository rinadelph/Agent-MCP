#!/usr/bin/env node

import dotenv from 'dotenv';
// Load environment variables first
dotenv.config();

import express from "express";
import { randomUUID } from "node:crypto";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";
import { isInitializeRequest } from "@modelcontextprotocol/sdk/types.js";
import { InMemoryEventStore } from "@modelcontextprotocol/sdk/examples/shared/inMemoryEventStore.js";
import cors from "cors";
import { z } from "zod";

// Import Agent-MCP components
import { checkVssLoadability } from "../../db/connection.js";
import { initDatabase, getDatabaseStats } from "../../db/schema.js";
import { toolRegistry } from "../../tools/registry.js";
import { initializeAdminToken } from "../../core/auth.js";
import "../../tools/basic.js"; // Register basic tools
import "../../tools/agent.js"; // Register agent management tools  
import "../../tools/agentCommunication.js"; // Register agent communication tools
import "../../tools/assistanceRequest.js"; // Register intelligent assistance request
import "../../tools/tasks/index.js"; // Register task management tools
import "../../tools/rag.js"; // Register RAG tools
import "../../tools/file_management.js"; // Register file management tools
import "../../tools/project_context.js"; // Register project context tools
// Resources will be handled directly in server setup
import { MCP_DEBUG, VERSION } from "../../core/config.js";

const PORT = process.env.PORT ? parseInt(process.env.PORT) : 3001;

// Initialize database and check VSS on startup
console.log("🚀 Starting Agent-MCP Node.js Server...");
console.log(`📊 Checking database extensions...`);

const vssAvailable = checkVssLoadability();
if (vssAvailable) {
  console.log("✅ sqlite-vec extension loaded successfully");
} else {
  console.log("⚠️  sqlite-vec extension not available - RAG functionality disabled");
}

console.log("🗄️  Initializing database...");
try {
  initDatabase();
  const stats = getDatabaseStats();
  console.log("📈 Database statistics:", stats);
} catch (error) {
  console.error("❌ Database initialization failed:", error);
  process.exit(1);
}

console.log("🔐 Initializing authentication system...");
let SERVER_ADMIN_TOKEN: string;
try {
  SERVER_ADMIN_TOKEN = initializeAdminToken();
  console.log("✅ Authentication system ready");
} catch (error) {
  console.error("❌ Authentication initialization failed:", error);
  process.exit(1);
}

console.log("🤖 Initializing OpenAI service...");
try {
  const { initializeOpenAIClient } = await import("../../external/openai_service.js");
  const openaiClient = initializeOpenAIClient();
  if (openaiClient) {
    console.log("✅ OpenAI service ready");
  } else {
    console.log("⚠️  OpenAI service not available - check OPENAI_API_KEY");
  }
} catch (error) {
  console.error("❌ OpenAI service initialization failed:", error);
  console.log("⚠️  Continuing without OpenAI (RAG functionality will be limited)");
}

// Create server factory function
const getServer = async () => {
  const server = new McpServer({
    name: 'agent-mcp-node-server',
    version: VERSION,
  }, { 
    capabilities: { 
      logging: {},
      experimental: {},
      resources: {
        subscribe: true,
        listChanged: true
      }
    } 
  });

  // Register all tools from the registry
  const tools = toolRegistry.getTools();
  const toolDefinitions = toolRegistry.getAllToolDefinitions();
  
  for (const toolDef of toolDefinitions) {
    // Convert Zod object schema to plain object for MCP
    const inputSchema: Record<string, any> = {};
    if (toolDef.inputSchema instanceof z.ZodObject) {
      const shape = toolDef.inputSchema.shape;
      for (const [key, zodSchema] of Object.entries(shape)) {
        inputSchema[key] = zodSchema;
      }
    }
    
    server.registerTool(
      toolDef.name,
      {
        title: toolDef.name,
        description: toolDef.description || 'No description provided',
        inputSchema: inputSchema
      },
      async (args) => {
        try {
          const result = await toolRegistry.executeTool(toolDef.name, args, {
            sessionId: 'claude-code-session',
            agentId: 'claude-code-user',
            requestId: 'claude-code-request'
          });
          
          // Convert our ToolResult to proper MCP format
          return {
            content: result.content.map(item => {
              const mcpItem: any = {
                type: item.type,
                text: item.text
              };
              
              // Only add optional properties if they exist
              if (item.data) mcpItem.data = item.data;
              if (item.mimeType) mcpItem.mimeType = item.mimeType;
              if (item.uri) mcpItem.uri = item.uri;
              
              return mcpItem;
            }),
            isError: result.isError
          };
        } catch (error) {
          return {
            content: [{
              type: 'text',
              text: `Tool execution failed: ${error instanceof Error ? error.message : String(error)}`
            }],
            isError: true
          };
        }
      }
    );
  }

  // Register MCP resources for agent @ mentions
  const { getAgentResources, getAgentResourceContent } = await import('../../resources/agents.js');
  
  // Register each agent as a dynamic resource
  const agents = await getAgentResources();
  for (const agentResource of agents) {
    server.resource(agentResource.name, agentResource.uri, {
      description: agentResource.description,
      mimeType: agentResource.mimeType
    }, async () => {
      if (MCP_DEBUG) {
        console.log(`📖 Reading agent resource: ${agentResource.uri}`);
      }
      
      // Parse agent ID from URI
      const match = agentResource.uri.match(/^agent:\/\/agent-mcp\/(.+)$/);
      if (!match) {
        throw new Error(`Invalid agent resource URI: ${agentResource.uri}`);
      }
      
      const agentId = match[1]!;
      const content = await getAgentResourceContent(agentId);
      
      if (!content) {
        throw new Error(`Agent resource not found: ${agentId}`);
      }
      
      return {
        contents: [{
          uri: content.uri,
          mimeType: content.mimeType,
          text: content.text
        }]
      };
    });
  }

  // Register MCP resources for tmux sessions and panes @ mentions
  const { getTmuxResources, getTmuxResourceContent } = await import('../../resources/tmux.js');
  
  // Register each tmux session and pane as a dynamic resource
  const tmuxResources = await getTmuxResources();
  for (const tmuxResource of tmuxResources) {
    server.resource(tmuxResource.name, tmuxResource.uri, {
      description: tmuxResource.description,
      mimeType: tmuxResource.mimeType
    }, async () => {
      if (MCP_DEBUG) {
        console.log(`📖 Reading tmux resource: ${tmuxResource.uri}`);
      }
      
      // Parse session/pane identifier from URI
      let identifier = '';
      const sessionMatch = tmuxResource.uri.match(/^tmux:\/\/session\/(.+)$/);
      const paneMatch = tmuxResource.uri.match(/^tmux:\/\/pane\/(.+)$/);
      
      if (sessionMatch) {
        identifier = sessionMatch[1]!;
      } else if (paneMatch) {
        identifier = paneMatch[1]!;
      } else {
        throw new Error(`Invalid tmux resource URI: ${tmuxResource.uri}`);
      }
      
      const content = await getTmuxResourceContent(identifier);
      
      if (!content) {
        throw new Error(`Tmux resource not found: ${identifier}`);
      }
      
      return {
        contents: [{
          uri: content.uri,
          mimeType: content.mimeType,
          text: content.text
        }]
      };
    });
  }

  console.log(`✅ Registered ${tools.length} tools`);
  console.log(`✅ Registered ${agents.length} agent resources`);
  console.log(`✅ Registered ${tmuxResources.length} tmux resources`);
  if (MCP_DEBUG) {
    console.log("🔧 Available tools:", tools.map(t => t.name).join(', '));
  }

  return server;
};

// Create Express application
const app = express();
app.use(express.json());

// Configure CORS
app.use(cors({
  origin: '*',
  exposedHeaders: ['Mcp-Session-Id']
}));

// Store transports by session ID
const transports: { [sessionId: string]: StreamableHTTPServerTransport } = {};

// Handle all MCP Streamable HTTP requests
app.all('/mcp', async (req, res) => {
  if (MCP_DEBUG) {
    console.log(`📡 Received ${req.method} request to /mcp`);
  }
  
  try {
    // Check for existing session ID
    const sessionId = req.headers['mcp-session-id'] as string;
    let transport: StreamableHTTPServerTransport;

    if (sessionId && transports[sessionId]) {
      // Reuse existing transport
      transport = transports[sessionId];
      if (MCP_DEBUG) {
        console.log(`♻️  Reusing transport for session: ${sessionId}`);
      }
    } else if (req.method === 'POST' && (isInitializeRequest(req.body) || !sessionId)) {
      // Create new transport for initialize request
      const eventStore = new InMemoryEventStore();
      transport = new StreamableHTTPServerTransport({
        sessionIdGenerator: () => randomUUID(),
        eventStore,
        onsessioninitialized: (newSessionId) => {
          console.log(`🔗 New session initialized: ${newSessionId}`);
          transports[newSessionId] = transport;
        }
      });

      // Set up cleanup
      transport.onclose = () => {
        const sid = transport.sessionId;
        if (sid && transports[sid]) {
          console.log(`🔌 Session ${sid} disconnected`);
          delete transports[sid];
        }
      };

      // Connect the transport to the MCP server
      const server = await getServer();
      await server.connect(transport);
    } else {
      // Invalid request
      res.status(400).json({
        jsonrpc: '2.0',
        error: {
          code: -32000,
          message: 'Bad Request: No valid session ID provided or not an initialize request',
        },
        id: null,
      });
      return;
    }

    // Handle the request with the transport
    await transport.handleRequest(req, res, req.body);
  } catch (error) {
    console.error('❌ Error handling MCP request:', error);
    if (!res.headersSent) {
      res.status(500).json({
        jsonrpc: '2.0',
        error: {
          code: -32603,
          message: 'Internal server error',
        },
        id: null,
      });
    }
  }
});

// Health check endpoint with enhanced information
app.get('/health', (req, res) => {
  const stats = getDatabaseStats();
  
  res.json({
    status: 'healthy',
    server: 'agent-mcp-node',
    version: VERSION,
    port: PORT,
    timestamp: new Date().toISOString(),
    sessions: Object.keys(transports).length,
    database: {
      vssSupported: vssAvailable,
      tables: stats
    },
    tools: toolRegistry.getTools().map(t => t.name)
  });
});

// Database stats endpoint
app.get('/stats', (req, res) => {
  try {
    const stats = getDatabaseStats();
    res.json({
      database: stats,
      sessions: Object.keys(transports).length,
      tools: toolRegistry.getTools().length,
      vssSupported: vssAvailable,
      uptime: Math.floor(process.uptime()),
      memory: process.memoryUsage()
    });
  } catch (error) {
    res.status(500).json({
      error: 'Failed to get statistics',
      details: error instanceof Error ? error.message : String(error)
    });
  }
});

// Start the server
const httpServer = app.listen(PORT, () => {
  console.log("\n🎉 Agent-MCP Node.js Server is ready!");
  console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
  console.log(`🌐 Server URL: http://localhost:${PORT}`);
  console.log(`📡 MCP Endpoint: http://localhost:${PORT}/mcp`);
  console.log(`❤️  Health Check: http://localhost:${PORT}/health`);
  console.log(`📊 Statistics: http://localhost:${PORT}/stats`);
  console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
  console.log(`🔧 Available Tools: ${toolRegistry.getTools().length}`);
  console.log(`🗄️  Vector Search: ${vssAvailable ? 'Enabled' : 'Disabled'}`);
  console.log(`📝 Debug Mode: ${MCP_DEBUG ? 'On' : 'Off'}`);
  console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
  console.log("✅ Ready for Claude Code connections!");
  console.log("");
  console.log("🔑 **ADMIN TOKEN** (copy this for agent creation):");
  console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
  console.log(`   ${SERVER_ADMIN_TOKEN}`);
  console.log("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
  console.log("");
  console.log("💡 Use this token with create_agent tool:");
  console.log(`   admin_token: ${SERVER_ADMIN_TOKEN}`);
});

// Graceful shutdown
process.on('SIGINT', async () => {
  console.log('\n🛑 Shutting down Agent-MCP Node.js server...');
  
  // Close all active transports
  const sessionIds = Object.keys(transports);
  if (sessionIds.length > 0) {
    console.log(`🔌 Closing ${sessionIds.length} active sessions...`);
    for (const sessionId of sessionIds) {
      try {
        await transports[sessionId]?.close();
        delete transports[sessionId];
      } catch (error) {
        console.error(`Error closing session ${sessionId}:`, error);
      }
    }
  }
  
  httpServer.close(() => {
    console.log('✅ Agent-MCP Node.js server shutdown complete');
    process.exit(0);
  });
});

process.on('SIGTERM', async () => {
  console.log('\n🛑 Received SIGTERM, shutting down...');
  process.kill(process.pid, 'SIGINT');
});