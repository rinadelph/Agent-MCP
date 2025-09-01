// Background Agent Management - Standalone mode without hierarchical tasks
// Works alongside existing task system for flexible agent deployment

import { z } from 'zod';
import { randomUUID } from 'crypto';
import { registerTool } from './registry.js';
import { getDbConnection } from '../db/connection.js';
import { VERSION, AGENT_COLORS, getProjectDir, MCP_DEBUG } from '../core/config.js';
import { getCLIAgents, getDefaultCLI } from '../core/extendedConfig.js';
import { verifyToken, getAgentId, generateToken as authGenerateToken } from '../core/auth.js';
import { globalState as coreGlobalState } from '../core/globals.js';
import { 
  isTmuxAvailable, 
  createTmuxSession, 
  sendCommandToSession, 
  generateAgentSessionName,
  sendPromptToSession,
  killTmuxSession,
  sessionExists
} from '../utils/tmux.js';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

// Types for background agents
export interface BackgroundAgent {
  token: string;
  agent_id: string;
  mode: 'background' | 'service' | 'monitoring' | 'general';
  objectives: string[];
  capabilities: string[];
  status: 'created' | 'active' | 'terminated' | 'failed' | 'paused';
  working_directory: string;
  color: string;
  created_at: string;
  updated_at: string;
  terminated_at?: string;
  last_activity?: string;
}

// Global state for background agents (separate from task-based agents)
const backgroundGlobalState = {
  backgroundAgents: new Map<string, BackgroundAgent>(),
  backgroundTmuxSessions: new Map<string, string>(),
  agentColorIndex: 0,
  serverStartTime: new Date().toISOString()
};

// Helper functions
function generateAgentToken(): string {
  return randomUUID().replace(/-/g, '');
}

function getNextBackgroundAgentColor(): string {
  const color = AGENT_COLORS[backgroundGlobalState.agentColorIndex % AGENT_COLORS.length] || 'purple';
  backgroundGlobalState.agentColorIndex++;
  return color;
}

function logBackgroundAgentAction(agentId: string, action: string, details: any = {}) {
  const db = getDbConnection();
  const timestamp = new Date().toISOString();
  
  try {
    const stmt = db.prepare(`
      INSERT INTO agent_actions (agent_id, action_type, timestamp, details)
      VALUES (?, ?, ?, ?)
    `);
    
    stmt.run(agentId, action, timestamp, JSON.stringify(details));
    
    if (MCP_DEBUG) {
      console.log(`🎯 Background agent action: ${action} for ${agentId}`);
    }
  } catch (error) {
    console.error(`Failed to log background agent action: ${error}`);
  }
}

// Create Background Agent Tool
registerTool(
  'create_background_agent',
  'Create a standalone background agent that operates independently without hierarchical task requirements. Perfect for monitoring, services, and general assistance. No admin token required - designed to be lightweight and accessible!',
  z.object({
    agent_id: z.string().describe('Unique identifier for the background agent'),
    mode: z.enum(['background', 'service', 'monitoring', 'general']).default('background').describe('Operating mode for the agent'),
    objectives: z.array(z.string()).describe('List of high-level objectives (not hierarchical tasks)'),
    cli_agent: z.enum(['claude', 'gemini', 'llxprt', 'swarmcode']).optional().describe('CLI agent to use (claude, gemini, llxprt, swarmcode). Uses default if not specified'),
    capabilities: z.array(z.string()).optional().describe('List of agent capabilities')
  }),
  async (args, context) => {
    const { agent_id, mode = 'background', objectives, cli_agent, capabilities = [] } = args;
    
    // Determine which CLI agent to use
    const availableCLIAgents = getCLIAgents();
    const selectedCLI = cli_agent || getDefaultCLI();
    
    // Validate CLI agent selection
    if (!availableCLIAgents.includes(selectedCLI)) {
      return {
        content: [{
          type: 'text' as const,
          text: `❌ Error: CLI agent '${selectedCLI}' is not configured. Available agents: ${availableCLIAgents.join(', ')}`
        }],
        isError: true
      };
    }
    
    // Basic validation
    if (!agent_id || !objectives || objectives.length === 0) {
      return {
        content: [{
          type: 'text' as const,
          text: '❌ Error: agent_id and at least one objective are required'
        }],
        isError: true
      };
    }
    
    // Check if background agent already exists
    if (backgroundGlobalState.backgroundAgents.has(agent_id)) {
      return {
        content: [{
          type: 'text' as const,
          text: `❌ Background agent '${agent_id}' already exists in active memory`
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
            text: `❌ Agent '${agent_id}' already exists in database (use different ID for background agent)`
          }],
          isError: true
        };
      }
      
      // Generate agent data
      const newToken = generateAgentToken();
      const createdAt = new Date().toISOString();
      const agentColor = getNextBackgroundAgentColor();
      const workingDir = getProjectDir();
      const status = 'created';
      
      // Store in database with special background agent markers
      const insertAgent = db.prepare(`
        INSERT INTO agents (
          token, agent_id, capabilities, created_at, status, 
          working_directory, color, updated_at, current_task
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
      `);
      
      // Use special marker to indicate this is a background agent
      const backgroundCapabilities = [...capabilities, `mode:${mode}`, 'background-agent'];
      const objectivesAsTask = `BACKGROUND_OBJECTIVES:${JSON.stringify(objectives)}`;
      
      insertAgent.run(
        newToken,
        agent_id,
        JSON.stringify(backgroundCapabilities),
        createdAt,
        status,
        workingDir,
        agentColor,
        createdAt,
        objectivesAsTask // Store objectives in current_task field with special prefix
      );
      
      // Log background agent creation
      logBackgroundAgentAction('system', 'created_background_agent', {
        agent_id,
        mode,
        objectives,
        color: agentColor,
        working_directory: workingDir
      });
      
      // Update global state
      const agentData: BackgroundAgent = {
        token: newToken,
        agent_id,
        mode,
        objectives,
        capabilities: backgroundCapabilities,
        status: 'created',
        working_directory: workingDir,
        color: agentColor,
        created_at: createdAt,
        updated_at: createdAt
      };
      
      backgroundGlobalState.backgroundAgents.set(agent_id, agentData);
      
      // Launch tmux session for the background agent
      let launchStatus = '';
      if (await isTmuxAvailable()) {
        try {
          const tmuxSessionName = generateAgentSessionName(agent_id, newToken);
          
          if (await createTmuxSession(tmuxSessionName, workingDir, undefined, undefined)) {
            backgroundGlobalState.backgroundTmuxSessions.set(agent_id, tmuxSessionName);
            
            // Setup commands for background agent
            const welcomeMessage = `echo '🎯 Background Agent ${agent_id} (${mode} mode) initialization starting'`;
            await sendCommandToSession(tmuxSessionName, welcomeMessage);
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            // Show objectives
            const objectivesMessage = `echo 'Objectives: ${objectives.join(', ')}'`;
            await sendCommandToSession(tmuxSessionName, objectivesMessage);
            await new Promise(resolve => setTimeout(resolve, 1000));
            
            // Get server port for MCP registration
            const serverPort = process.env.PORT || '3001';
            const mcpServerUrl = `http://localhost:${serverPort}/mcp`;
            
            // Generate CLI-specific commands
            let mcpAddCommand = '';
            let cliStartCommand = '';
            let hasMCPSupport = true;
            
            switch (selectedCLI) {
              case 'claude':
                mcpAddCommand = `claude mcp add -t sse AgentMCP-Background ${mcpServerUrl}`;
                cliStartCommand = 'claude --dangerously-skip-permissions';
                break;
              case 'gemini':
                // Gemini uses settings.json for MCP config, no need to register
                mcpAddCommand = `echo 'Using Gemini MCP via ~/.gemini/settings.json'`;
                cliStartCommand = 'gemini --enable-mcp';
                break;
              case 'llxprt':
                mcpAddCommand = `llxprt mcp add AgentMCP-Background ${mcpServerUrl}`;
                cliStartCommand = 'llxprt --mcp';
                break;
              case 'swarmcode':
                mcpAddCommand = `swarmcode mcp add AgentMCP-Background ${mcpServerUrl}`;
                cliStartCommand = 'swarmcode --mcp';
                break;
              default:
                mcpAddCommand = `echo 'Unknown CLI agent: ${selectedCLI}'`;
                cliStartCommand = 'echo "CLI agent not supported"';
                hasMCPSupport = false;
            }
            
            if (MCP_DEBUG) {
              console.log(`Setting up ${selectedCLI} for background agent '${agent_id}': ${mcpAddCommand}`);
            }
            
            // Register MCP server (if supported)
            if (!await sendCommandToSession(tmuxSessionName, mcpAddCommand)) {
              console.error(`Failed to register MCP server for background agent '${agent_id}' with ${selectedCLI}`);
              launchStatus = `❌ Failed to register MCP server for background agent '${agent_id}' with ${selectedCLI}.`;
            } else {
              await new Promise(resolve => setTimeout(resolve, 1000));
              
              // Start selected CLI agent
              const startMessage = `echo '--- Starting ${selectedCLI} for Background Agent ---'`;
              await sendCommandToSession(tmuxSessionName, startMessage);
              await new Promise(resolve => setTimeout(resolve, 1000));
              
              if (MCP_DEBUG) {
                console.log(`Starting ${selectedCLI} for background agent '${agent_id}': ${cliStartCommand}`);
              }
              
              if (!await sendCommandToSession(tmuxSessionName, cliStartCommand)) {
                console.error(`Failed to start ${selectedCLI} for background agent '${agent_id}'`);
                launchStatus = `❌ Failed to start ${selectedCLI} for background agent '${agent_id}' after MCP setup.`;
              } else {
                const mcpStatus = hasMCPSupport ? 'with MCP integration' : 'standalone mode';
                launchStatus = `✅ tmux session '${tmuxSessionName}' created for background agent '${agent_id}' using ${selectedCLI} (${mcpStatus}).`;
                
                // Send background agent prompt after delay
                console.log(`🔥 SCHEDULING BACKGROUND PROMPT for agent '${agent_id}' with session '${tmuxSessionName}'`);
                const timeoutId = setTimeout(async () => {
                  console.log(`🎯 BACKGROUND PROMPT CALLBACK EXECUTING for agent '${agent_id}'`);
                  const prompt = buildBackgroundAgentPrompt(agent_id, mode, objectives);

                  try {
                    console.log(`🔧 About to send background prompt to session: ${tmuxSessionName}`);
                    await execAsync(`tmux send-keys -t "${tmuxSessionName}" "${prompt}"`);
                    console.log(`📝 Typed background prompt to agent '${agent_id}'`);
                    
                    await new Promise(resolve => setTimeout(resolve, 500));
                    
                    await execAsync(`tmux send-keys -t "${tmuxSessionName}" Enter`);
                    console.log(`✅ Sent background prompt to agent '${agent_id}' with token: ${newToken}`);
                  } catch (error) {
                    console.error(`❌ Failed to send background prompt to agent '${agent_id}':`, error);
                  }
                  console.log(`🏁 BACKGROUND PROMPT CALLBACK COMPLETED for agent '${agent_id}'`);
                }, 4000);
                console.log(`⏰ Background timeout scheduled with ID: ${timeoutId} for agent '${agent_id}'`);
              }
            }
            
            if (MCP_DEBUG) {
              console.log(`Background tmux session '${tmuxSessionName}' launched for agent '${agent_id}'`);
            }
          } else {
            launchStatus = `❌ Failed to create tmux session for background agent '${agent_id}'.`;
            console.error(launchStatus);
          }
        } catch (error) {
          launchStatus = `❌ Failed to launch tmux session: ${error instanceof Error ? error.message : String(error)}`;
          console.error(launchStatus);
        }
      } else {
        console.warn('tmux is not available - background agent session cannot be launched automatically');
        launchStatus = '⚠️ tmux not available - manual background agent setup required.';
      }
      
      const response = [
        `✅ **Background Agent '${agent_id}' Created Successfully**`,
        '',
        `**Details:**`,
        `- Mode: ${mode}`,
        `- CLI Agent: ${selectedCLI}${selectedCLI !== 'swarmcode' ? ' (MCP enabled)' : ' (standalone)'}`,
        `- Color: ${agentColor}`,
        `- Working Directory: ${workingDir}`,
        `- Status: ${status}`,
        `- Capabilities: ${backgroundCapabilities.join(', ')}`,
        '',
        `**Objectives:**`
      ];
      
      objectives.forEach((objective: string) => {
        response.push(`- ${objective}`);
      });
      
      response.push('');
      
      // Add tmux launch status
      if (launchStatus) {
        response.push(`**Launch Status:**`);
        response.push(launchStatus);
        response.push('');
      }
      
      // Add tmux session info if available
      const sessionName = backgroundGlobalState.backgroundTmuxSessions.get(agent_id);
      if (sessionName) {
        response.push(`**Tmux Session:** ${sessionName}`);
        response.push(`**Connect Command:** \`tmux attach-session -t ${sessionName}\``);
        response.push('');
      }
      
      response.push('🎯 Background Agent is ready for independent operation');
      
      return {
        content: [{
          type: 'text' as const,
          text: response.join('\n')
        }]
      };
      
    } catch (error) {
      console.error(`Error creating background agent ${agent_id}:`, error);
      return {
        content: [{
          type: 'text' as const,
          text: `❌ Error creating background agent: ${error instanceof Error ? error.message : String(error)}`
        }],
        isError: true
      };
    }
  }
);

// Helper function to build background agent prompt
function buildBackgroundAgentPrompt(agentId: string, mode: string, objectives: string[]): string {
  const objectivesList = objectives.map((obj, i) => `${i + 1}. ${obj}`).join('\\n');
  
  return `You are ${agentId}, a background agent operating in ${mode} mode.

BACKGROUND AGENT INSTRUCTIONS:
- You operate independently without hierarchical task constraints
- Your objectives: \\n${objectivesList}
- You can work on these objectives in any order or simultaneously
- No parent tasks required - you have full autonomy
- No admin authentication needed - you're lightweight and accessible
- Focus on continuous operation rather than discrete task completion
- Report on progress periodically but work continuously

Start working on your objectives now.`;
}

// List Background Agents Tool
registerTool(
  'list_background_agents',
  'List all background agents with their current status and objectives',
  z.object({
    mode_filter: z.enum(['background', 'service', 'monitoring', 'general']).optional().describe('Filter by agent mode'),
    status_filter: z.enum(['created', 'active', 'terminated', 'failed', 'paused']).optional().describe('Filter by status'),
    include_details: z.boolean().default(false).optional().describe('Include detailed information')
  }),
  async (args, context) => {
    const { mode_filter, status_filter, include_details = false } = args;
    
    try {
      const db = getDbConnection();
      
      // Get background agents from database (those with background-agent capability)
      let query = `
        SELECT * FROM agents 
        WHERE capabilities LIKE '%background-agent%'
      `;
      const params: any[] = [];
      
      if (status_filter) {
        query += ' AND status = ?';
        params.push(status_filter);
      }
      
      query += ' ORDER BY created_at DESC';
      
      const agents = db.prepare(query).all(...params);
      
      if (agents.length === 0) {
        return {
          content: [{
            type: 'text' as const,
            text: `🎯 No background agents found${status_filter ? ` with status '${status_filter}'` : ''}${mode_filter ? ` in mode '${mode_filter}'` : ''}`
          }]
        };
      }
      
      const response = [
        `🎯 **Background Agents** (${agents.length} found)`,
        ''
      ];
      
      agents.forEach((agent: any) => {
        const caps = JSON.parse(agent.capabilities || '[]');
        const mode = caps.find((cap: string) => cap.startsWith('mode:'))?.split(':')[1] || 'unknown';
        
        // Skip if mode filter doesn't match
        if (mode_filter && mode !== mode_filter) {
          return;
        }
        
        // Extract objectives from current_task field
        let objectives: string[] = [];
        if (agent.current_task && agent.current_task.startsWith('BACKGROUND_OBJECTIVES:')) {
          try {
            const objectivesJson = agent.current_task.replace('BACKGROUND_OBJECTIVES:', '');
            objectives = JSON.parse(objectivesJson);
          } catch (e) {
            objectives = ['Failed to parse objectives'];
          }
        }
        
        response.push(`**${agent.agent_id}** - ${agent.status} (${mode} mode) ${agent.color}`);
        
        if (include_details) {
          response.push(`  Created: ${agent.created_at}`);
          response.push(`  Working Dir: ${agent.working_directory}`);
          response.push(`  Objectives:`);
          objectives.forEach(obj => {
            response.push(`    • ${obj}`);
          });
          if (agent.terminated_at) {
            response.push(`  Terminated: ${agent.terminated_at}`);
          }
        } else {
          response.push(`  Objectives: ${objectives.slice(0, 2).join(', ')}${objectives.length > 2 ? '...' : ''}`);
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
          text: `❌ Error listing background agents: ${error instanceof Error ? error.message : String(error)}`
        }],
        isError: true
      };
    }
  }
);

// Terminate Background Agent Tool  
registerTool(
  'terminate_background_agent',
  'Terminate a background agent by ID. No admin token required - background agents are lightweight and accessible!',
  z.object({
    agent_id: z.string().describe('ID of the background agent to terminate')
  }),
  async (args, context) => {
    const { agent_id } = args;
    
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
      // Check if background agent exists
      const agent = db.prepare(`
        SELECT * FROM agents 
        WHERE agent_id = ? AND capabilities LIKE '%background-agent%' AND status != ?
      `).get(agent_id, 'terminated');
      
      if (!agent) {
        return {
          content: [{
            type: 'text' as const,
            text: `❌ Background agent '${agent_id}' not found or already terminated`
          }],
          isError: true
        };
      }
      
      const terminatedAt = new Date().toISOString();
      
      // Update agent status
      const updateAgent = db.prepare(`
        UPDATE agents 
        SET status = ?, terminated_at = ?, updated_at = ?
        WHERE agent_id = ? AND capabilities LIKE '%background-agent%'
      `);
      
      updateAgent.run('terminated', terminatedAt, terminatedAt, agent_id);
      
      // Kill tmux session if it exists
      const tmuxSessionName = backgroundGlobalState.backgroundTmuxSessions.get(agent_id);
      let tmuxStatus = '';
      
      if (tmuxSessionName) {
        try {
          if (await sessionExists(tmuxSessionName)) {
            const killed = await killTmuxSession(tmuxSessionName);
            if (killed) {
              tmuxStatus = `- Tmux session '${tmuxSessionName}' killed`;
              if (MCP_DEBUG) {
                console.log(`✅ Killed tmux session for background agent '${agent_id}': ${tmuxSessionName}`);
              }
            } else {
              tmuxStatus = `- ⚠️ Failed to kill tmux session '${tmuxSessionName}'`;
            }
          } else {
            tmuxStatus = `- Tmux session '${tmuxSessionName}' already stopped`;
          }
        } catch (error) {
          tmuxStatus = `- ⚠️ Error killing tmux session: ${error instanceof Error ? error.message : String(error)}`;
        }
        
        backgroundGlobalState.backgroundTmuxSessions.delete(agent_id);
      } else {
        tmuxStatus = '- No tmux session found';
      }
      
      // Update global state
      backgroundGlobalState.backgroundAgents.delete(agent_id);
      
      // Log termination
      logBackgroundAgentAction('system', 'terminated_background_agent', {
        agent_id,
        terminated_at: terminatedAt
      });
      
      const response = [
        `✅ **Background Agent '${agent_id}' Terminated Successfully**`,
        '',
        `- Terminated at: ${terminatedAt}`,
        tmuxStatus,
        '- Removed from active memory',
        '',
        '🔴 Background agent is fully stopped'
      ];
      
      return {
        content: [{
          type: 'text' as const,
          text: response.join('\n')
        }]
      };
      
    } catch (error) {
      console.error(`Error terminating background agent ${agent_id}:`, error);
      return {
        content: [{
          type: 'text' as const,
          text: `❌ Error terminating background agent: ${error instanceof Error ? error.message : String(error)}`
        }],
        isError: true
      };
    }
  }
);

console.log('✅ Background agent management tools registered successfully');