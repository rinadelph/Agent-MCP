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
import { Command } from 'commander';
import { resolve } from 'path';

// Import Agent-MCP components
import { checkVssLoadability } from "../../db/connection.js";
import { initDatabase, getDatabaseStats } from "../../db/schema.js";
import { toolRegistry } from "../../tools/registry.js";
import { initializeAdminToken } from "../../core/auth.js";
import { 
  initializeSessionPersistence, 
  markSessionDisconnected, 
  canRecoverSession, 
  recoverSession,
  getActiveSessions 
} from "../../utils/sessionPersistence.js";
import "../../tools/basic.js"; // Register basic tools
import "../../tools/agent.js"; // Register agent management tools  
import "../../tools/agentCommunication.js"; // Register agent communication tools
import "../../tools/assistanceRequest.js"; // Register intelligent assistance request
import "../../tools/tasks/index.js"; // Register task management tools
import "../../tools/rag.js"; // Register RAG tools
import "../../tools/file_management.js"; // Register file management tools
import "../../tools/project_context.js"; // Register project context tools
import "../../tools/sessionState.js"; // Register session state management tools
// Resources will be handled directly in server setup
import { MCP_DEBUG, VERSION, TUIColors, AUTHOR, GITHUB_URL } from "../../core/config.js";

// Parse command line arguments
const program = new Command();
program
  .name('agent-mcp-server')
  .description('Agent-MCP Node.js Server with Multi-Agent Collaboration Protocol')
  .version(VERSION)
  .option('-p, --port <number>', 'port to run the server on', '3001')
  .option('-h, --host <host>', 'host to bind the server to', '0.0.0.0')
  .option('--project-dir <path>', 'project directory to operate in', process.cwd())
  .parse();

const options = program.opts();
const PORT = parseInt(options.port);
const HOST = options.host;
const PROJECT_DIR = resolve(options.projectDir);

// Change to project directory if specified
if (options.projectDir !== process.cwd()) {
  try {
    process.chdir(PROJECT_DIR);
    console.log(`📁 Changed to project directory: ${PROJECT_DIR}`);
  } catch (error) {
    console.error(`❌ Failed to change to project directory: ${PROJECT_DIR}`);
    console.error(error);
    process.exit(1);
  }
}

// Display colorful ASCII art banner (matching Python version)
function displayBanner() {
  // Clear terminal
  console.clear();
  
  // RGB to ANSI escape code helper
  const rgb = (r: number, g: number, b: number) => `\x1b[38;2;${r};${g};${b}m`;
  const reset = '\x1b[0m';
  
  // Gradient colors (pink to cyan like Python version)
  const gradientColors = {
    pink_start: [255, 182, 255] as [number, number, number],
    purple_mid: [182, 144, 255] as [number, number, number],
    blue_mid: [144, 182, 255] as [number, number, number],
    cyan_end: [144, 255, 255] as [number, number, number]
  };
  
  // ASCII art for AGENT MCP (full banner)
  const logoLines = [
    " █████╗  ██████╗ ███████╗███╗   ██╗████████╗    ███╗   ███╗ ██████╗██████╗ ",
    "██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝    ████╗ ████║██╔════╝██╔══██╗",
    "███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║       ██╔████╔██║██║     ██████╔╝",
    "██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║       ██║╚██╔╝██║██║     ██╔═══╝ ",
    "██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║       ██║ ╚═╝ ██║╚██████╗██║     ",
    "╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝       ╚═╝     ╚═╝ ╚═════╝╚═╝     "
  ];
  
  // Apply gradient colors
  logoLines.forEach((line, i) => {
    const progress = i / (logoLines.length - 1);
    let r, g, b;
    
    if (progress < 0.33) {
      // Pink to purple
      const localProgress = progress / 0.33;
      r = Math.round(gradientColors.pink_start[0] + (gradientColors.purple_mid[0] - gradientColors.pink_start[0]) * localProgress);
      g = Math.round(gradientColors.pink_start[1] + (gradientColors.purple_mid[1] - gradientColors.pink_start[1]) * localProgress);
      b = Math.round(gradientColors.pink_start[2] + (gradientColors.purple_mid[2] - gradientColors.pink_start[2]) * localProgress);
    } else if (progress < 0.66) {
      // Purple to blue
      const localProgress = (progress - 0.33) / 0.33;
      r = Math.round(gradientColors.purple_mid[0] + (gradientColors.blue_mid[0] - gradientColors.purple_mid[0]) * localProgress);
      g = Math.round(gradientColors.purple_mid[1] + (gradientColors.blue_mid[1] - gradientColors.purple_mid[1]) * localProgress);
      b = Math.round(gradientColors.purple_mid[2] + (gradientColors.blue_mid[2] - gradientColors.purple_mid[2]) * localProgress);
    } else {
      // Blue to cyan
      const localProgress = (progress - 0.66) / 0.34;
      r = Math.round(gradientColors.blue_mid[0] + (gradientColors.cyan_end[0] - gradientColors.blue_mid[0]) * localProgress);
      g = Math.round(gradientColors.blue_mid[1] + (gradientColors.cyan_end[1] - gradientColors.blue_mid[1]) * localProgress);
      b = Math.round(gradientColors.blue_mid[2] + (gradientColors.cyan_end[2] - gradientColors.blue_mid[2]) * localProgress);
    }
    
    // Center the line
    const terminalWidth = process.stdout.columns || 80;
    const padding = Math.max(0, Math.floor((terminalWidth - line.length) / 2));
    console.log(' '.repeat(padding) + rgb(r, g, b) + line + reset);
  });
  
  console.log('');
  
  // Credits and version info (centered, matching Python style)
  const creditsText = `Created by ${AUTHOR} (${GITHUB_URL})`;
  const versionText = `Version ${VERSION}`;
  const terminalWidth = process.stdout.columns || 80;
  
  const creditsPadding = Math.max(0, Math.floor((terminalWidth - creditsText.length) / 2));
  const versionPadding = Math.max(0, Math.floor((terminalWidth - versionText.length) / 2));
  
  console.log(' '.repeat(creditsPadding) + TUIColors.DIM + creditsText + reset);
  console.log(' '.repeat(versionPadding) + TUIColors.OKBLUE + versionText + reset);
  console.log(TUIColors.OKBLUE + '─'.repeat(terminalWidth) + reset);
  console.log('');
}

// Display the banner
displayBanner();

// Initialize database and check VSS on startup
console.log("🚀 Starting Agent-MCP Node.js Server...");
console.log(`📁 Project Directory: ${PROJECT_DIR}`);
console.log(`🌐 Server Host: ${HOST}`);
console.log(`🌐 Server Port: ${PORT}`);
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

// Store transports by session ID with recovery metadata
const transports: { [sessionId: string]: {
  transport: StreamableHTTPServerTransport;
  createdAt: Date;
  lastActivity: Date;
  isRecovered: boolean;
} } = {};

// Handle all MCP Streamable HTTP requests
app.all('/mcp', async (req, res) => {
  if (MCP_DEBUG) {
    console.log(`📡 Received ${req.method} request to /mcp`);
  }
  
  try {
    // Check for existing session ID
    const sessionId = req.headers['mcp-session-id'] as string;
    let transport: StreamableHTTPServerTransport | undefined;
    let isRecovered = false;

    if (sessionId && transports[sessionId]) {
      // Reuse existing transport
      const transportData = transports[sessionId];
      transport = transportData.transport;
      transportData.lastActivity = new Date();
      
      if (MCP_DEBUG) {
        console.log(`♻️  Reusing transport for session: ${sessionId} (recovered: ${transportData.isRecovered})`);
      }
    } else if (sessionId && await canRecoverSession(sessionId)) {
      // Attempt session recovery
      console.log(`🔄 Attempting to recover session: ${sessionId}`);
      
      const sessionState = await recoverSession(sessionId);
      if (sessionState) {
        // Create new transport for recovered session
        const eventStore = new InMemoryEventStore();
        transport = new StreamableHTTPServerTransport({
          sessionIdGenerator: () => sessionId, // Use existing session ID
          eventStore,
          onsessioninitialized: (recoveredSessionId) => {
            console.log(`✅ Session recovered and reinitialized: ${recoveredSessionId}`);
          }
        });

        // Set up enhanced cleanup with recovery support
        transport.onclose = async () => {
          const sid = transport!.sessionId;
          if (sid && transports[sid]) {
            console.log(`🔌 Session ${sid} disconnected - starting recovery grace period`);
            await markSessionDisconnected(sid);
            
            // Keep transport data for potential recovery but mark as disconnected
            transports[sid].transport = transport!; // Keep reference for potential reuse
            // Don't delete immediately - let grace period handle cleanup
            
            // Schedule cleanup after grace period
            setTimeout(async () => {
              const canStillRecover = await canRecoverSession(sid);
              if (!canStillRecover && transports[sid]) {
                console.log(`⏰ Grace period expired for session ${sid} - cleaning up`);
                delete transports[sid];
              }
            }, 10 * 60 * 1000); // 10 minute grace period
          }
        };

        // Store transport with recovery metadata
        const now = new Date();
        transports[sessionId] = {
          transport: transport!,
          createdAt: now,
          lastActivity: now,
          isRecovered: true
        };

        // Initialize persistence for recovered session
        await initializeSessionPersistence(sessionId, transport!, sessionState.workingDirectory);
        
        // Connect the transport to the MCP server
        const server = await getServer();
        await server.connect(transport!);
        
        isRecovered = true;
        console.log(`✅ Session successfully recovered: ${sessionId}`);
      } else {
        console.log(`❌ Failed to recover session state for: ${sessionId}`);
        // Fall through to create new session
      }
    }
    
    if (!transport && (req.method === 'POST' && (isInitializeRequest(req.body) || !sessionId))) {
      // Create new transport for initialize request
      const eventStore = new InMemoryEventStore();
      transport = new StreamableHTTPServerTransport({
        sessionIdGenerator: () => randomUUID(),
        eventStore,
        onsessioninitialized: async (newSessionId) => {
          console.log(`🔗 New session initialized: ${newSessionId}`);
          
          // Store transport with metadata
          const now = new Date();
          transports[newSessionId] = {
            transport: transport!,
            createdAt: now,
            lastActivity: now,
            isRecovered: false
          };
          
          // Initialize session persistence
          await initializeSessionPersistence(newSessionId, transport!, PROJECT_DIR);
        }
      });

      // Set up enhanced cleanup with recovery support
      transport.onclose = async () => {
        const sid = transport!.sessionId;
        if (sid && transports[sid]) {
          console.log(`🔌 Session ${sid} disconnected - starting recovery grace period`);
          await markSessionDisconnected(sid);
          
          // Keep transport data for potential recovery
          // Don't delete immediately - let grace period handle cleanup
          
          // Schedule cleanup after grace period
          setTimeout(async () => {
            const canStillRecover = await canRecoverSession(sid);
            if (!canStillRecover && transports[sid]) {
              console.log(`⏰ Grace period expired for session ${sid} - cleaning up`);
              delete transports[sid];
            }
          }, 10 * 60 * 1000); // 10 minute grace period
        }
      };

      // Connect the transport to the MCP server
      const server = await getServer();
      await server.connect(transport!);
    }
    
    if (!transport) {
      // Invalid request - no transport available
      res.status(400).json({
        jsonrpc: '2.0',
        error: {
          code: -32000,
          message: 'Bad Request: No valid session ID provided, session cannot be recovered, or not an initialize request',
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
app.get('/health', async (req, res) => {
  const stats = getDatabaseStats();
  const activeSessions = await getActiveSessions();
  const transportCount = Object.keys(transports).length;
  const recoveredSessions = Object.values(transports).filter(t => t.isRecovered).length;
  
  res.json({
    status: 'healthy',
    server: 'agent-mcp-node',
    version: VERSION,
    port: PORT,
    timestamp: new Date().toISOString(),
    sessions: {
      active_transports: transportCount,
      persistent_sessions: activeSessions.length,
      recovered_sessions: recoveredSessions
    },
    database: {
      vssSupported: vssAvailable,
      tables: stats
    },
    tools: toolRegistry.getTools().map(t => t.name),
    session_recovery: {
      enabled: true,
      grace_period_minutes: 10
    }
  });
});

// Database stats endpoint
app.get('/stats', async (req, res) => {
  try {
    const stats = getDatabaseStats();
    const activeSessions = await getActiveSessions();
    const transportCount = Object.keys(transports).length;
    const recoveredSessions = Object.values(transports).filter(t => t.isRecovered).length;
    
    res.json({
      database: stats,
      sessions: {
        active_transports: transportCount,
        persistent_sessions: activeSessions.length,
        recovered_sessions: recoveredSessions,
        session_details: activeSessions
      },
      tools: toolRegistry.getTools().length,
      vssSupported: vssAvailable,
      uptime: Math.floor(process.uptime()),
      memory: process.memoryUsage(),
      session_recovery: {
        enabled: true,
        grace_period_minutes: 10,
        active_sessions: activeSessions
      }
    });
  } catch (error) {
    res.status(500).json({
      error: 'Failed to get statistics',
      details: error instanceof Error ? error.message : String(error)
    });
  }
});

// Session management endpoint for debugging and testing
app.get('/sessions', async (req, res) => {
  try {
    const activeSessions = await getActiveSessions();
    const transportCount = Object.keys(transports).length;
    const recoveredSessions = Object.values(transports).filter(t => t.isRecovered).length;
    
    const transportDetails = Object.entries(transports).map(([sessionId, data]) => ({
      sessionId,
      createdAt: data.createdAt,
      lastActivity: data.lastActivity,
      isRecovered: data.isRecovered,
      ageMinutes: Math.floor((Date.now() - data.createdAt.getTime()) / (1000 * 60))
    }));
    
    res.json({
      summary: {
        active_transports: transportCount,
        persistent_sessions: activeSessions.length,
        recovered_sessions: recoveredSessions
      },
      active_transports: transportDetails,
      persistent_sessions: activeSessions,
      session_recovery: {
        enabled: true,
        grace_period_minutes: 10,
        cleanup_interval_minutes: 5
      }
    });
  } catch (error) {
    res.status(500).json({
      error: 'Failed to get session information',
      details: error instanceof Error ? error.message : String(error)
    });
  }
});

// Force session recovery endpoint for testing
app.post('/sessions/:sessionId/recover', async (req, res) => {
  try {
    const { sessionId } = req.params;
    
    const canRecover = await canRecoverSession(sessionId);
    if (!canRecover) {
      return res.status(400).json({
        error: 'Session cannot be recovered',
        sessionId,
        reason: 'Session not found, expired, or too many recovery attempts'
      });
    }
    
    const sessionState = await recoverSession(sessionId);
    if (!sessionState) {
      return res.status(500).json({
        error: 'Session recovery failed',
        sessionId
      });
    }
    
    res.json({
      message: 'Session recovery initiated',
      sessionId,
      sessionState: {
        workingDirectory: sessionState.workingDirectory,
        hasAgentContext: !!sessionState.agentContext,
        hasConversationState: !!sessionState.conversationState,
        metadata: sessionState.metadata
      }
    });
  } catch (error) {
    res.status(500).json({
      error: 'Failed to recover session',
      details: error instanceof Error ? error.message : String(error)
    });
  }
});

// Start the server
const httpServer = app.listen(PORT, HOST, () => {
  console.log("\n🎉 Agent-MCP Node.js Server is ready!");
  console.log(TUIColors.OKBLUE + "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" + TUIColors.ENDC);
  console.log(`🌐 Server URL: ${TUIColors.OKCYAN}http://${HOST}:${PORT}${TUIColors.ENDC}`);
  console.log(`📡 MCP Endpoint: ${TUIColors.OKCYAN}http://${HOST}:${PORT}/mcp${TUIColors.ENDC}`);
  console.log(`❤️  Health Check: ${TUIColors.OKCYAN}http://${HOST}:${PORT}/health${TUIColors.ENDC}`);
  console.log(`📊 Statistics: ${TUIColors.OKCYAN}http://${HOST}:${PORT}/stats${TUIColors.ENDC}`);
  console.log(TUIColors.OKBLUE + "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" + TUIColors.ENDC);
  console.log(`🔧 Available Tools: ${TUIColors.OKGREEN}${toolRegistry.getTools().length}${TUIColors.ENDC}`);
  console.log(`🗄️  Vector Search: ${vssAvailable ? TUIColors.OKGREEN + 'Enabled' : TUIColors.WARNING + 'Disabled'}${TUIColors.ENDC}`);
  console.log(`📝 Debug Mode: ${MCP_DEBUG ? TUIColors.OKGREEN + 'On' : TUIColors.DIM + 'Off'}${TUIColors.ENDC}`);
  console.log(TUIColors.OKBLUE + "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" + TUIColors.ENDC);
  console.log(TUIColors.OKGREEN + "✅ Ready for Claude Code connections!" + TUIColors.ENDC);
  console.log("");
  console.log(TUIColors.BOLD + TUIColors.WARNING + "🔑 **ADMIN TOKEN** (copy this for agent creation):" + TUIColors.ENDC);
  console.log(TUIColors.OKBLUE + "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" + TUIColors.ENDC);
  console.log(`   ${TUIColors.OKGREEN}${SERVER_ADMIN_TOKEN}${TUIColors.ENDC}`);
  console.log(TUIColors.OKBLUE + "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" + TUIColors.ENDC);
  console.log("");
  console.log(TUIColors.OKCYAN + "💡 Use this token with create_agent tool:" + TUIColors.ENDC);
  console.log(`   ${TUIColors.DIM}admin_token: ${TUIColors.OKGREEN}${SERVER_ADMIN_TOKEN}${TUIColors.ENDC}`);
});

// Graceful shutdown
process.on('SIGINT', async () => {
  console.log('\n🛑 Shutting down Agent-MCP Node.js server...');
  
  // Close all active transports with session persistence awareness
  const sessionIds = Object.keys(transports);
  if (sessionIds.length > 0) {
    console.log(`🔌 Closing ${sessionIds.length} active sessions (preserving for recovery)...`);
    for (const sessionId of sessionIds) {
      try {
        const transportData = transports[sessionId];
        if (transportData) {
          // Mark session as disconnected but don't expire immediately
          await markSessionDisconnected(sessionId);
          
          // Close the transport
          await transportData.transport?.close();
          
          console.log(`📦 Session ${sessionId} preserved for potential recovery`);
        }
        delete transports[sessionId];
      } catch (error) {
        console.error(`Error closing session ${sessionId}:`, error);
      }
    }
  }
  
  httpServer.close(() => {
    console.log('✅ Agent-MCP Node.js server shutdown complete');
    console.log('💾 Session states preserved in database for recovery');
    process.exit(0);
  });
});

process.on('SIGTERM', async () => {
  console.log('\n🛑 Received SIGTERM, shutting down...');
  process.kill(process.pid, 'SIGINT');
});