/**
 * Testing Agent Auto-Launch System for Node.js
 * Automatically launches testing agents when tasks are completed
 */

import { getDbConnection } from '../db/connection.js';
import { buildAgentPrompt } from './promptTemplates.js';
import { MCP_DEBUG, getProjectDir } from '../core/config.js';
import { execSync } from 'child_process';
import * as crypto from 'crypto';

export interface TestingAgentLaunchResult {
  success: boolean;
  testing_agent_id: string;
  error?: string;
}

/**
 * Send escape sequences to pause an agent's tmux session
 */
export async function sendEscapeToAgent(agentId: string): Promise<boolean> {
  try {
    console.log(`🛑 Pausing agent ${agentId} with escape sequences`);
    
    // Get agent's tmux session from database
    const db = getDbConnection();
    const agent = db.prepare('SELECT * FROM agents WHERE agent_id = ?').get(agentId) as any;
    
    if (!agent) {
      console.warn(`⚠️ Agent ${agentId} not found in database`);
      return false;
    }
    
    // Calculate session name (agent-id with last 4 chars of admin token)
    const adminConfig = db.prepare('SELECT config_value FROM admin_config WHERE config_key = ?').get('admin_token') as any;
    const adminToken = adminConfig?.config_value;
    
    if (!adminToken) {
      console.error('❌ Admin token not found');
      return false;
    }
    
    const suffix = adminToken.slice(-4).toLowerCase();
    const sessionName = `${agentId.replace(/[^a-zA-Z0-9_-]/g, '_')}-${suffix}`;
    
    // Send 4 escape sequences with 1 second intervals
    for (let i = 0; i < 4; i++) {
      try {
        execSync(`tmux send-keys -t "${sessionName}" Escape`, { timeout: 5000 });
        console.log(`✅ Sent Escape ${i + 1}/4 to agent ${agentId}`);
        if (i < 3) {
          await new Promise(resolve => setTimeout(resolve, 1000));
        }
      } catch (error) {
        console.error(`❌ Failed to send Escape ${i + 1}/4 to agent ${agentId}:`, error);
        return false;
      }
    }
    
    console.log(`✅ Successfully paused agent ${agentId}`);
    return true;
  } catch (error) {
    console.error(`❌ Error pausing agent ${agentId}:`, error);
    return false;
  }
}

/**
 * Generate a unique token for testing agent
 */
function generateTestingAgentToken(): string {
  return crypto.randomBytes(16).toString('hex');
}

/**
 * Launch testing agent for a completed task
 */
export async function launchTestingAgentForCompletedTask(
  completedTaskId: string,
  completedByAgent: string
): Promise<TestingAgentLaunchResult> {
  
  const db = getDbConnection();
  
  try {
    console.log(`🧪 Launching testing agent for completed task: ${completedTaskId}`);
    
    // 1. Send Escape sequences to pause completing agent
    await sendEscapeToAgent(completedByAgent);
    
    // 2. Get task details for context
    const task = db.prepare('SELECT * FROM tasks WHERE task_id = ?').get(completedTaskId) as any;
    if (!task) {
      console.error(`❌ Cannot find completed task ${completedTaskId} for testing`);
      return { success: false, testing_agent_id: '', error: 'Task not found' };
    }
    
    // 3. Generate testing agent ID
    const testingAgentId = `test-${completedTaskId.slice(-6)}`;
    
    // 4. Clean up existing testing agent if it exists (task re-completed after fixes)
    const existingAgent = db.prepare('SELECT agent_id FROM agents WHERE agent_id = ?').get(testingAgentId);
    
    if (existingAgent) {
      console.log(`🧹 Task ${completedTaskId} re-completed - cleaning up existing testing agent ${testingAgentId}`);
      
      // Remove from database
      db.prepare('DELETE FROM agents WHERE agent_id = ?').run(testingAgentId);
      
      // Kill tmux session if it exists
      try {
        const adminConfig = db.prepare('SELECT config_value FROM admin_config WHERE config_key = ?').get('admin_token') as any;
        const adminToken = adminConfig?.config_value;
        const suffix = adminToken?.slice(-4).toLowerCase() || '0000';
        const sessionName = `${testingAgentId.replace(/[^a-zA-Z0-9_-]/g, '_')}-${suffix}`;
        
        execSync(`tmux kill-session -t "${sessionName}"`, { timeout: 5000 });
        console.log(`🧹 Killed existing tmux session for testing agent ${testingAgentId}`);
      } catch (error) {
        // Session might not exist, continue
        console.log(`ℹ️ No existing tmux session to kill for ${testingAgentId}`);
      }
    }
    
    // 5. Create testing agent token and database entry
    const testingToken = generateTestingAgentToken();
    const createdAt = new Date().toISOString();
    
    // Get project directory
    const projectDir = getProjectDir();
    
    // Insert testing agent into database
    const insertResult = db.prepare(`
      INSERT INTO agents (token, agent_id, capabilities, created_at, status, 
                        current_task, working_directory, color)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
      testingToken,
      testingAgentId,
      JSON.stringify(['testing', 'validation', 'criticism']),
      createdAt,
      'created',
      completedTaskId, // Set the completed task as current task
      projectDir,
      '#FF0000' // Red color for testing agents
    );
    
    if (insertResult.changes === 0) {
      console.error(`❌ Failed to create testing agent ${testingAgentId} in database`);
      return { success: false, testing_agent_id: testingAgentId, error: 'Failed to create agent in database' };
    }
    
    // 6. Build enriched prompt for testing agent
    const adminConfig = db.prepare('SELECT config_value FROM admin_config WHERE config_key = ?').get('admin_token') as any;
    const adminToken = adminConfig?.config_value || '';
    
    const prompt = buildAgentPrompt(
      testingAgentId,
      testingToken,
      adminToken,
      'testing_agent',
      undefined,
      {
        completed_by_agent: completedByAgent,
        completed_task_id: completedTaskId,
        completed_task_title: task.title || 'Unknown',
        completed_task_description: task.description || 'No description'
      }
    );
    
    if (!prompt) {
      console.error(`❌ Failed to build prompt for testing agent ${testingAgentId}`);
      return { success: false, testing_agent_id: testingAgentId, error: 'Failed to build prompt' };
    }
    
    // 7. Create tmux session for testing agent
    const suffix = adminToken.slice(-4).toLowerCase();
    const sessionName = `${testingAgentId.replace(/[^a-zA-Z0-9_-]/g, '_')}-${suffix}`;
    
    try {
      // Create tmux session
      execSync(`tmux new-session -d -s "${sessionName}" -c "${projectDir}"`, { timeout: 10000 });
      console.log(`✅ Created tmux session for testing agent: ${sessionName}`);
      
      // Set up environment variables
      const envCommands = [
        `export MCP_AGENT_ID="${testingAgentId}"`,
        `export MCP_AGENT_TOKEN="${testingToken}"`,
        `export MCP_SERVER_URL="http://localhost:3001"`,
        `export MCP_WORKING_DIR="${projectDir}"`
      ];
      
      for (const envCmd of envCommands) {
        execSync(`tmux send-keys -t "${sessionName}" "${envCmd}" Enter`, { timeout: 5000 });
        await new Promise(resolve => setTimeout(resolve, 500));
      }
      
      // Welcome message
      const welcomeMsg = `echo '=== Testing Agent ${testingAgentId} initialization starting ==='`;
      execSync(`tmux send-keys -t "${sessionName}" "${welcomeMsg}" Enter`, { timeout: 5000 });
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Register MCP server connection
      const mcpAddCommand = `claude mcp add -t sse AgentMCP http://localhost:3001/sse`;
      execSync(`tmux send-keys -t "${sessionName}" "${mcpAddCommand}" Enter`, { timeout: 5000 });
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Start Claude
      const claudeCommand = `claude --dangerously-skip-permissions`;
      execSync(`tmux send-keys -t "${sessionName}" "${claudeCommand}" Enter`, { timeout: 5000 });
      await new Promise(resolve => setTimeout(resolve, 3000));
      
      // Send enriched prompt after delay using two separate commands
      setTimeout(() => {
        try {
          // First command: type the prompt (without Enter)
          execSync(`tmux send-keys -t "${sessionName}" "${prompt.replace(/"/g, '\\"').replace(/\n/g, ' ')}"`, { timeout: 10000 });
          console.log(`✅ Typed prompt to testing agent ${testingAgentId}`);
          
          // Second command: press Enter to send the prompt
          setTimeout(() => {
            try {
              execSync(`tmux send-keys -t "${sessionName}" Enter`, { timeout: 5000 });
              console.log(`✅ Sent Enter to testing agent ${testingAgentId}`);
            } catch (error) {
              console.error(`❌ Failed to send Enter to testing agent ${testingAgentId}:`, error);
            }
          }, 1000);
        } catch (error) {
          console.error(`❌ Failed to send prompt to testing agent ${testingAgentId}:`, error);
        }
      }, 5000);
      
      // Log the testing agent creation
      db.prepare(`
        INSERT INTO agent_actions (agent_id, action_type, details, created_at)
        VALUES (?, ?, ?, ?)
      `).run(
        'admin',
        'create_testing_agent',
        JSON.stringify({
          testing_agent_id: testingAgentId,
          completed_task_id: completedTaskId,
          completed_by_agent: completedByAgent
        }),
        createdAt
      );
      
      console.log(`🧪 Testing agent ${testingAgentId} launched successfully for task ${completedTaskId}`);
      return { success: true, testing_agent_id: testingAgentId };
      
    } catch (error) {
      console.error(`❌ Failed to create tmux session for testing agent ${testingAgentId}:`, error);
      
      // Clean up database entry if session creation failed
      db.prepare('DELETE FROM agents WHERE agent_id = ?').run(testingAgentId);
      
      return { success: false, testing_agent_id: testingAgentId, error: `Failed to create tmux session: ${error}` };
    }
    
  } catch (error) {
    console.error(`❌ Error launching testing agent for task ${completedTaskId}:`, error);
    return { success: false, testing_agent_id: '', error: String(error) };
  }
}

/**
 * Auto-launch testing agents for multiple completed tasks
 */
export async function autoLaunchTestingAgents(
  completedTasks: Array<{ task_id: string; completed_by: string }>
): Promise<Array<{ task_id: string; testing_agent_launched: boolean; testing_agent_id?: string; error?: string }>> {
  
  const results = [];
  
  for (const { task_id, completed_by } of completedTasks) {
    try {
      const result = await launchTestingAgentForCompletedTask(task_id, completed_by);
      results.push({
        task_id,
        testing_agent_launched: result.success,
        testing_agent_id: result.testing_agent_id,
        error: result.error
      });
      
      if (MCP_DEBUG) {
        console.log(`🧪 Testing agent launch for task ${task_id}: ${result.success ? 'SUCCESS' : 'FAILED'}`);
      }
    } catch (error) {
      console.error(`❌ Failed to launch testing agent for task ${task_id}:`, error);
      results.push({
        task_id,
        testing_agent_launched: false,
        error: String(error)
      });
    }
  }
  
  return results;
}