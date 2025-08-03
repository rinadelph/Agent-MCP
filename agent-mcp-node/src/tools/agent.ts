// Agent management tools for Agent-MCP Node.js
// Ported from Python admin_tools.py

import { z } from 'zod';
import { randomUUID } from 'crypto';
import { registerTool } from './registry.js';
import { getDbConnection } from '../db/connection.js';
import { getDatabaseStats } from '../db/schema.js';
import { VERSION, AGENT_COLORS, getProjectDir, MCP_DEBUG } from '../core/config.js';
import { verifyToken, getAgentId, generateToken as authGenerateToken, registerActiveAgent } from '../core/auth.js';
import { globalState as coreGlobalState } from '../core/globals.js';
import { 
  isTmuxAvailable, 
  createTmuxSession, 
  sendCommandToSession, 
  generateAgentSessionName,
  sendPromptAsync,
  sendPromptToSession,
  killTmuxSession,
  sessionExists
} from '../utils/tmux.js';
import { buildAgentPrompt, TemplateType } from '../utils/promptTemplates.js';
import path from 'path';
import { promises as fs } from 'fs';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

// Types for agent management
export interface Agent {
  token: string;
  agent_id: string;
  capabilities: string[];
  status: 'created' | 'active' | 'terminated' | 'failed' | 'completed';
  current_task?: string;
  working_directory: string;
  color: string;
  created_at: string;
  updated_at: string;
  terminated_at?: string;
}

// Global state tracking (similar to Python globals)
const globalState = {
  activeAgents: new Map<string, Agent>(),
  agentWorkingDirs: new Map<string, string>(),
  agentTmuxSessions: new Map<string, string>(), // agent_id -> tmux_session_name
  agentColorIndex: 0,
  serverStartTime: new Date().toISOString()
};

// Helper functions
function generateAgentToken(): string {
  return randomUUID().replace(/-/g, '');
}

function getNextAgentColor(): string {
  const color = AGENT_COLORS[globalState.agentColorIndex % AGENT_COLORS.length] || 'blue';
  globalState.agentColorIndex++;
  return color;
}

function logAgentAction(agentId: string, action: string, details: any = {}) {
  const db = getDbConnection();
  const timestamp = new Date().toISOString();
  
  try {
    const stmt = db.prepare(`
      INSERT INTO agent_actions (agent_id, action_type, timestamp, details)
      VALUES (?, ?, ?, ?)
    `);
    
    stmt.run(agentId, action, timestamp, JSON.stringify(details));
    
    if (MCP_DEBUG) {
      console.log(`📝 Logged action: ${action} for agent ${agentId}`);
    }
  } catch (error) {
    console.error(`Failed to log agent action: ${error}`);
  }
}

// Create Agent Tool
registerTool(
  'create_agent',
  'Admin-only tool to create a new agent with specified capabilities and task assignments. Agents MUST have at least one task assigned. Workflow: 1) Create unassigned tasks first, 2) Create agent with those task IDs.',
  z.object({
    agent_id: z.string().describe('Unique identifier for the agent'),
    capabilities: z.array(z.string()).optional().describe('List of agent capabilities'),
    task_ids: z.array(z.string()).optional().describe('List of task IDs to assign to the agent (required - must have at least one task)'),
    admin_token: z.string().describe('Admin authentication token (required)')
  }),
  async (args, context) => {
    const { agent_id, capabilities = [], task_ids = [], admin_token } = args;
    
    // Verify admin authentication - REQUIRED
    if (!admin_token || !verifyToken(admin_token, 'admin')) {
      return {
        content: [{
          type: 'text' as const,
          text: '❌ Unauthorized: Admin privileges required to create agents'
        }],
        isError: true
      };
    }
    
    // Basic validation
    if (!agent_id) {
      return {
        content: [{
          type: 'text' as const,
          text: '❌ Error: agent_id is required. Please provide a unique identifier for the agent.'
        }],
        isError: true
      };
    }
    
    // Agents must have at least one task assigned
    if (!task_ids || task_ids.length === 0) {
      return {
        content: [{
          type: 'text' as const,
          text: '❌ Error: Agents must be created with at least one task assigned. Please provide task_ids.\n\n💡 **Workflow:**\n1. First create unassigned tasks using assign_task (without agent_token)\n2. Then create agent with those task IDs using create_agent'
        }],
        isError: true
      };
    }
    
    // Check if agent already exists
    if (globalState.activeAgents.has(agent_id)) {
      return {
        content: [{
          type: 'text' as const,
          text: `❌ Agent '${agent_id}' already exists in active memory`
        }],
        isError: true
      };
    }
    
    const db = getDbConnection();
    
    try {
      // Check database for existing agent
      const existingAgent = db.prepare('SELECT agent_id FROM agents WHERE agent_id = ?').get(agent_id);
      if (existingAgent) {
        return {
          content: [{
            type: 'text' as const,
            text: `❌ Agent '${agent_id}' already exists in database`
          }],
          isError: true
        };
      }
      
      // Validate tasks if provided
      for (const taskId of task_ids) {
        const task = db.prepare('SELECT task_id, assigned_to, status FROM tasks WHERE task_id = ?').get(taskId);
        if (!task) {
          return {
            content: [{
              type: 'text' as const,
              text: `❌ Task '${taskId}' not found in database`
            }],
            isError: true
          };
        }
        
        if ((task as any).assigned_to) {
          return {
            content: [{
              type: 'text' as const,
              text: `❌ Task '${taskId}' is already assigned to agent '${(task as any).assigned_to}'`
            }],
            isError: true
          };
        }
      }
      
      // Generate agent data
      const newToken = generateAgentToken();
      const createdAt = new Date().toISOString();
      const agentColor = getNextAgentColor();
      const workingDir = getProjectDir();
      const status = 'created';
      
      // Begin transaction
      const transaction = db.transaction(() => {
        // Insert agent
        const insertAgent = db.prepare(`
          INSERT INTO agents (
            token, agent_id, capabilities, created_at, status, 
            working_directory, color, updated_at
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        `);
        
        insertAgent.run(
          newToken,
          agent_id,
          JSON.stringify(capabilities),
          createdAt,
          status,
          workingDir,
          agentColor,
          createdAt
        );
        
        // Assign tasks
        const assignedTasks: string[] = [];
        for (const taskId of task_ids) {
          const updateTask = db.prepare(`
            UPDATE tasks 
            SET assigned_to = ?, status = 'pending', updated_at = ? 
            WHERE task_id = ?
          `);
          
          const result = updateTask.run(agent_id, createdAt, taskId);
          if (result.changes > 0) {
            assignedTasks.push(taskId);
          }
        }
        
        // Set current task to first assigned task
        if (assignedTasks.length > 0) {
          const updateCurrentTask = db.prepare(`
            UPDATE agents SET current_task = ? WHERE agent_id = ?
          `);
          updateCurrentTask.run(assignedTasks[0], agent_id);
        }
        
        // Log agent creation
        logAgentAction('admin', 'created_agent', {
          agent_id,
          color: agentColor,
          working_directory: workingDir,
          assigned_tasks: assignedTasks
        });
        
        return assignedTasks;
      });
      
      const assignedTasks = transaction();
      
      // Update global state
      const agentData: Agent = {
        token: newToken,
        agent_id,
        capabilities,
        status: 'created',
        current_task: assignedTasks[0] || undefined,
        working_directory: workingDir,
        color: agentColor,
        created_at: createdAt,
        updated_at: createdAt
      };
      
      globalState.activeAgents.set(agent_id, agentData);
      globalState.agentWorkingDirs.set(agent_id, workingDir);
      
      // Launch tmux session for the agent
      let launchStatus = '';
      if (await isTmuxAvailable()) {
        try {
          // Create sanitized session name
          const tmuxSessionName = generateAgentSessionName(agent_id, admin_token);
          
          // Create the tmux session (without immediate command, no environment variables)
          if (await createTmuxSession(tmuxSessionName, workingDir, undefined, undefined)) {
            // Track the tmux session in globals
            globalState.agentTmuxSessions.set(agent_id, tmuxSessionName);
            
            // Initial setup commands for visibility in tmux session
            const welcomeMessage = `echo '=== Agent ${agent_id} initialization starting ==='`;
            if (await sendCommandToSession(tmuxSessionName, welcomeMessage)) {
              if (MCP_DEBUG) {
                console.log(`✅ Sent welcome message to agent '${agent_id}'`);
              }
            }
            
            // Add setup delay to ensure commands execute properly
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            
            // Verify we're in the correct working directory
            const verifyCommand = `echo 'Working directory:' && pwd`;
            await sendCommandToSession(tmuxSessionName, verifyCommand);
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            // Get server port for MCP registration
            const serverPort = process.env.PORT || '3001';
            const mcpServerUrl = `http://localhost:${serverPort}/mcp`;
            
            // Log MCP server info
            const mcpInfoCommand = `echo 'MCP Server URL: ${mcpServerUrl}'`;
            await sendCommandToSession(tmuxSessionName, mcpInfoCommand);
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            // Register MCP server connection
            const mcpAddCommand = `claude mcp add -t sse AgentMCP-Node ${mcpServerUrl}`;
            if (MCP_DEBUG) {
              console.log(`Registering MCP server for agent '${agent_id}': ${mcpAddCommand}`);
            }
            
            if (!await sendCommandToSession(tmuxSessionName, mcpAddCommand)) {
              console.error(`Failed to register MCP server for agent '${agent_id}'`);
              launchStatus = `❌ Failed to register MCP server for agent '${agent_id}'.`;
            } else {
              // Add delay to ensure MCP registration completes
              await new Promise(resolve => setTimeout(resolve, 1000));
              
              // Verify MCP registration
              const verifyMcpCommand = 'claude mcp list';
              if (MCP_DEBUG) {
                console.log(`Verifying MCP registration for agent '${agent_id}'`);
              }
              await sendCommandToSession(tmuxSessionName, verifyMcpCommand);
              await new Promise(resolve => setTimeout(resolve, 1000));
              
              // Start Claude
              const startClaudeMessage = "echo '--- Starting Claude with MCP ---'";
              await sendCommandToSession(tmuxSessionName, startClaudeMessage);
              await new Promise(resolve => setTimeout(resolve, 1000));
              
              const claudeCommand = 'claude --dangerously-skip-permissions';
              if (MCP_DEBUG) {
                console.log(`Starting Claude for agent '${agent_id}': ${claudeCommand}`);
              }
              
              if (!await sendCommandToSession(tmuxSessionName, claudeCommand)) {
                console.error(`Failed to start Claude for agent '${agent_id}'`);
                launchStatus = `❌ Failed to start Claude for agent '${agent_id}' after MCP registration.`;
              } else {
                launchStatus = `✅ tmux session '${tmuxSessionName}' created for agent '${agent_id}' with MCP registration and Claude.`;
                
                // Log completion message to tmux session
                const completionMessage = `echo '=== Agent ${agent_id} setup complete - Claude starting ==='`;
                await sendCommandToSession(tmuxSessionName, completionMessage);
                
                // Send the exact prompt from Python Agent-MCP (worker_with_rag template)
                console.log(`🔥 SCHEDULING TIMEOUT for agent '${agent_id}' with session '${tmuxSessionName}'`);
                const timeoutId = setTimeout(async () => {
                  console.log(`🎯 TIMEOUT CALLBACK EXECUTING for agent '${agent_id}'`);
                  const prompt = `This is your agent token: ${newToken} Ask the project RAG agent at least 5-7 questions to understand what you need to do. I want you to critically think when asking a question, then criticize yourself before asking that question. How you criticize yourself is by proposing an idea, criticizing it, and based on that criticism you pull through with that idea. It's better to add too much context versus too little. Add all these context entries to the agent mcp. ACT AUTO --worker --memory`;

                  try {
                    console.log(`🔧 About to send keys to session: ${tmuxSessionName}`);
                    // Step 1: Type the message
                    await execAsync(`tmux send-keys -t "${tmuxSessionName}" "${prompt}"`);
                    console.log(`📝 Typed prompt to agent '${agent_id}'`);
                    
                    // Step 2: Wait 0.5 seconds
                    await new Promise(resolve => setTimeout(resolve, 500));
                    
                    // Step 3: Hit Enter
                    await execAsync(`tmux send-keys -t "${tmuxSessionName}" Enter`);
                    console.log(`✅ Sent prompt to agent '${agent_id}' with token: ${newToken}`);
                  } catch (error) {
                    console.error(`❌ Failed to send prompt to agent '${agent_id}':`, error);
                  }
                  console.log(`🏁 TIMEOUT CALLBACK COMPLETED for agent '${agent_id}'`);
                }, 4000); // Wait 4 seconds for Claude to fully start
                console.log(`⏰ Timeout scheduled with ID: ${timeoutId} for agent '${agent_id}'`);
              }
            }
            
            if (MCP_DEBUG) {
              console.log(`tmux session '${tmuxSessionName}' launched for agent '${agent_id}'`);
            }
          } else {
            launchStatus = `❌ Failed to create tmux session for agent '${agent_id}'.`;
            console.error(launchStatus);
          }
        } catch (error) {
          launchStatus = `❌ Failed to launch tmux session: ${error instanceof Error ? error.message : String(error)}`;
          console.error(launchStatus);
        }
      } else {
        console.warn('tmux is not available - agent session cannot be launched automatically');
        launchStatus = '⚠️ tmux not available - manual agent setup required.';
      }
      
      const response = [
        `✅ **Agent '${agent_id}' Created Successfully**`,
        '',
        `**Details:**`,
        `- Token: ${newToken}`,
        `- Color: ${agentColor}`,
        `- Working Directory: ${workingDir}`,
        `- Status: ${status}`,
        `- Capabilities: ${capabilities.join(', ') || 'None'}`,
        ''
      ];
      
      if (assignedTasks.length > 0) {
        response.push(`**Assigned Tasks:**`);
        assignedTasks.forEach(taskId => {
          response.push(`- ${taskId}`);
        });
        response.push(`**Current Task:** ${assignedTasks[0]}`);
        response.push('');
      } else {
        response.push(`**Tasks:** No tasks assigned`);
        response.push('');
      }
      
      // Add tmux launch status
      if (launchStatus) {
        response.push(`**Launch Status:**`);
        response.push(launchStatus);
        response.push('');
      }
      
      // Add tmux session info if available
      const sessionName = globalState.agentTmuxSessions.get(agent_id);
      if (sessionName) {
        response.push(`**Tmux Session:** ${sessionName}`);
        response.push(`**Connect Command:** \`tmux attach-session -t ${sessionName}\``);
        response.push('');
      }
      
      response.push('🤖 Agent is ready for activation');
      
      return {
        content: [{
          type: 'text' as const,
          text: response.join('\n')
        }]
      };
      
    } catch (error) {
      console.error(`Error creating agent ${agent_id}:`, error);
      return {
        content: [{
          type: 'text' as const,
          text: `❌ Error creating agent: ${error instanceof Error ? error.message : String(error)}`
        }],
        isError: true
      };
    }
  }
);

// View Status Tool
registerTool(
  'view_status',
  'View the status of all agents, connections, and the MCP server',
  z.object({
    admin_token: z.string().optional().describe('Admin authentication token (optional - uses session context)')
  }),
  async (args, context) => {
    // For MCP usage, default to admin access for system status
    // In production, this would check session context for proper authentication
    
    try {
      const db = getDbConnection();
      const stats = getDatabaseStats();
      
      // Get all agents from database
      const agents = db.prepare('SELECT * FROM agents ORDER BY created_at DESC').all();
      
      // Calculate uptime
      const startTime = new Date(globalState.serverStartTime);
      const uptime = Math.floor((Date.now() - startTime.getTime()) / 1000);
      const uptimeHours = Math.floor(uptime / 3600);
      const uptimeMinutes = Math.floor((uptime % 3600) / 60);
      const uptimeSeconds = uptime % 60;
      
      const statusInfo = {
        server: {
          version: VERSION,
          uptime: `${uptimeHours}h ${uptimeMinutes}m ${uptimeSeconds}s`,
          startTime: globalState.serverStartTime
        },
        agents: {
          total: agents.length,
          active: agents.filter((a: any) => a.status === 'active').length,
          created: agents.filter((a: any) => a.status === 'created').length,
          terminated: agents.filter((a: any) => a.status === 'terminated').length
        },
        database: stats,
        memory: {
          activeAgents: globalState.activeAgents.size,
          workingDirs: globalState.agentWorkingDirs.size
        }
      };
      
      const response = [
        `🏥 **Agent-MCP System Status**`,
        '',
        `**Server Info:**`,
        `- Version: ${statusInfo.server.version}`,
        `- Uptime: ${statusInfo.server.uptime}`,
        `- Started: ${statusInfo.server.startTime}`,
        '',
        `**Agent Summary:**`,
        `- Total Agents: ${statusInfo.agents.total}`,
        `- Active: ${statusInfo.agents.active}`,
        `- Created: ${statusInfo.agents.created}`,
        `- Terminated: ${statusInfo.agents.terminated}`,
        '',
        `**Database Tables:**`
      ];
      
      Object.entries(statusInfo.database).forEach(([table, count]) => {
        response.push(`- ${table}: ${count >= 0 ? count : 'N/A'} records`);
      });
      
      if (agents.length > 0) {
        response.push('', '**Agent Details:**');
        agents.slice(0, 10).forEach((agent: any) => {
          response.push(`- **${agent.agent_id}** (${agent.status}) - ${agent.color}`);
          if (agent.current_task) {
            response.push(`  Current Task: ${agent.current_task}`);
          }
        });
        
        if (agents.length > 10) {
          response.push(`... and ${agents.length - 10} more agents`);
        }
      }
      
      response.push('', '✅ System operational');
      
      return {
        content: [{
          type: 'text' as const,
          text: response.join('\n')
        }]
      };
      
    } catch (error) {
      return {
        content: [{
          type: 'text' as const,
          text: `❌ Error getting system status: ${error instanceof Error ? error.message : String(error)}`
        }],
        isError: true
      };
    }
  }
);

// Terminate Agent Tool
registerTool(
  'terminate_agent',
  'Admin-only tool to terminate an active agent with the given ID. Requires valid admin token.',
  z.object({
    agent_id: z.string().describe('Unique identifier for the agent to terminate'),
    admin_token: z.string().describe('Admin authentication token (required)')
  }),
  async (args, context) => {
    const { agent_id, admin_token } = args;
    
    // Verify admin authentication - REQUIRED
    if (!admin_token || !verifyToken(admin_token, 'admin')) {
      return {
        content: [{
          type: 'text' as const,
          text: '❌ Unauthorized: Admin privileges required to terminate agents'
        }],
        isError: true
      };
    }
    
    if (!agent_id) {
      return {
        content: [{
          type: 'text' as const,
          text: '❌ Error: agent_id is required'
        }],
        isError: true
      };
    }
    
    const db = getDbConnection();
    
    try {
      // Check if agent exists
      const agent = db.prepare('SELECT * FROM agents WHERE agent_id = ? AND status != ?').get(agent_id, 'terminated');
      
      if (!agent) {
        return {
          content: [{
            type: 'text' as const,
            text: `❌ Agent '${agent_id}' not found or already terminated`
          }],
          isError: true
        };
      }
      
      const terminatedAt = new Date().toISOString();
      
      // Begin transaction
      const transaction = db.transaction(() => {
        // Update agent status
        const updateAgent = db.prepare(`
          UPDATE agents 
          SET status = ?, terminated_at = ?, updated_at = ?, current_task = NULL
          WHERE agent_id = ? AND status != ?
        `);
        
        updateAgent.run('terminated', terminatedAt, terminatedAt, agent_id, 'terminated');
        
        // Unassign any assigned tasks
        const unassignTasks = db.prepare(`
          UPDATE tasks 
          SET assigned_to = NULL, status = 'pending', updated_at = ?
          WHERE assigned_to = ?
        `);
        
        const unassignResult = unassignTasks.run(terminatedAt, agent_id);
        
        // Log termination
        logAgentAction('admin', 'terminated_agent', {
          agent_id,
          tasks_unassigned: unassignResult.changes
        });
        
        return unassignResult.changes;
      });
      
      const tasksUnassigned = transaction();
      
      // Update global state
      globalState.activeAgents.delete(agent_id);
      globalState.agentWorkingDirs.delete(agent_id);
      
      const response = [
        `✅ **Agent '${agent_id}' Terminated Successfully**`,
        '',
        `- Terminated at: ${terminatedAt}`,
        `- Tasks unassigned: ${tasksUnassigned}`,
        '- Removed from active memory',
        '',
        '🔴 Agent is no longer active'
      ];
      
      return {
        content: [{
          type: 'text' as const,
          text: response.join('\n')
        }]
      };
      
    } catch (error) {
      console.error(`Error terminating agent ${agent_id}:`, error);
      return {
        content: [{
          type: 'text' as const,
          text: `❌ Error terminating agent: ${error instanceof Error ? error.message : String(error)}`
        }],
        isError: true
      };
    }
  }
);

// List Agents Tool
registerTool(
  'list_agents',
  'List all agents with filtering options',
  z.object({
    status: z.enum(['created', 'active', 'terminated', 'failed', 'completed']).optional().describe('Filter by agent status'),
    limit: z.number().min(1).max(100).default(50).optional().describe('Maximum number of agents to return'),
    include_details: z.boolean().default(false).optional().describe('Include detailed agent information')
  }),
  async (args, context) => {
    const { status, limit = 50, include_details = false } = args;
    
    try {
      const db = getDbConnection();
      
      let query = 'SELECT * FROM agents';
      const params: any[] = [];
      
      if (status) {
        query += ' WHERE status = ?';
        params.push(status);
      }
      
      query += ' ORDER BY created_at DESC LIMIT ?';
      params.push(limit);
      
      const agents = db.prepare(query).all(...params);
      
      if (agents.length === 0) {
        return {
          content: [{
            type: 'text' as const,
            text: `No agents found${status ? ` with status '${status}'` : ''}`
          }]
        };
      }
      
      const response = [
        `🤖 **Agent List** (${agents.length} found)`,
        ''
      ];
      
      agents.forEach((agent: any) => {
        const caps = JSON.parse(agent.capabilities || '[]');
        response.push(`**${agent.agent_id}** - ${agent.status} ${agent.color}`);
        
        if (include_details) {
          response.push(`  Token: ${agent.token.substring(0, 8)}...`);
          response.push(`  Created: ${agent.created_at}`);
          response.push(`  Working Dir: ${agent.working_directory}`);
          if (agent.current_task) {
            response.push(`  Current Task: ${agent.current_task}`);
          }
          if (caps.length > 0) {
            response.push(`  Capabilities: ${caps.join(', ')}`);
          }
          if (agent.terminated_at) {
            response.push(`  Terminated: ${agent.terminated_at}`);
          }
        } else {
          if (agent.current_task) {
            response.push(`  Task: ${agent.current_task}`);
          }
          response.push(`  Created: ${new Date(agent.created_at).toLocaleDateString()}`);
        }
        
        response.push('');
      });
      
      return {
        content: [{
          type: 'text' as const,
          text: response.join('\n')
        }]
      };
      
    } catch (error) {
      return {
        content: [{
          type: 'text' as const,
          text: `❌ Error listing agents: ${error instanceof Error ? error.message : String(error)}`
        }],
        isError: true
      };
    }
  }
);

console.log('✅ Agent management tools registered successfully');