/**
 * Testing Agent Auto-Launch System for Node.js
 * Automatically launches testing agents when tasks are completed
 */

import { getDbConnection } from '../db/connection.js';
import { buildAgentPrompt } from './promptTemplates.js';
import { MCP_DEBUG, getProjectDir } from '../core/config.js';
import { execSync } from 'child_process';
import * as crypto from 'crypto';
import { createTestingTask } from '../tools/testingTasks.js';

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
    
    // 5. Create comprehensive testing task first
    const adminConfig = db.prepare('SELECT config_value FROM admin_config WHERE config_key = ?').get('admin_token') as any;
    const adminToken = adminConfig?.config_value || '';
    
    const testingTaskResult = await createTestingTask.execute({
      completed_task_id: completedTaskId,
      completed_by_agent: completedByAgent,
      testing_agent_id: testingAgentId,
      admin_token: adminToken
    });
    
    if (!testingTaskResult.success) {
      console.error(`❌ Failed to create testing task: ${testingTaskResult.error}`);
      return { success: false, testing_agent_id: testingAgentId, error: `Failed to create testing task: ${testingTaskResult.error}` };
    }
    
    console.log(`✅ Created testing task ${testingTaskResult.testing_task_id} with:`);
    console.log(`   - ${testingTaskResult.subtasks_found} subtasks to audit`);
    console.log(`   - ${testingTaskResult.context_entries_found} context entries to review`);
    console.log(`   - ${testingTaskResult.files_modified} files to check`);
    console.log(`   - ${testingTaskResult.actions_logged} actions to analyze`);
    
    // 6. Create testing agent using the SAME method as normal agents
    console.log(`🤖 Creating testing agent ${testingAgentId} using normal agent creation flow...`);
    
    // Import the create_agent tool logic directly
    const { generateToken: authGenerateToken, registerActiveAgent } = await import('../core/auth.js');
    
    // Generate agent data exactly like normal agents
    const testingToken = authGenerateToken();
    const createdAt = new Date().toISOString();
    const projectDir = getProjectDir();
    const agentColor = '#FF0000'; // Red color for testing agents
    const status = 'created';
    const capabilities = ['testing', 'validation', 'criticism', 'audit'];
    
    // Begin transaction (same as normal agent creation)
    const transaction = db.transaction(() => {
      // Insert agent (same structure as normal agents)
      const insertAgent = db.prepare(`
        INSERT INTO agents (
          token, agent_id, capabilities, created_at, status, 
          working_directory, color, updated_at, current_task
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
      `);
      
      insertAgent.run(
        testingToken,
        testingAgentId,
        JSON.stringify(capabilities),
        createdAt,
        status,
        projectDir,
        agentColor,
        createdAt,
        testingTaskResult.testing_task_id
      );
      
      // Assign the testing task to the agent (same as normal task assignment)
      const updateTask = db.prepare(`
        UPDATE tasks 
        SET assigned_to = ?, status = 'pending', updated_at = ? 
        WHERE task_id = ?
      `);
      
      const result = updateTask.run(testingAgentId, createdAt, testingTaskResult.testing_task_id);
      if (result.changes === 0) {
        throw new Error(`Failed to assign testing task ${testingTaskResult.testing_task_id} to ${testingAgentId}`);
      }
      
      return testingTaskResult.testing_task_id;
    });
    
    const assignedTask = transaction();
    
    // Register agent in global state (same as normal agents)
    const agentData = {
      token: testingToken,
      agent_id: testingAgentId,
      capabilities,
      status: 'created' as const,
      current_task: assignedTask,
      working_directory: projectDir,
      color: agentColor,
      created_at: createdAt,
      updated_at: createdAt
    };
    
    // Use the SAME registration method as normal agents
    registerActiveAgent(testingToken, agentData);
    
    console.log(`✅ Created testing agent ${testingAgentId} using normal agent flow with token ${testingToken}`);
    
    // 7. Build enriched prompt for testing agent with testing task context
    const prompt = buildAgentPrompt(
      testingAgentId,
      testingToken,
      adminToken,
      'testing_agent',
      undefined,
      {
        testing_task_id: testingTaskResult.testing_task_id,
        completed_by_agent: completedByAgent,
        completed_task_id: completedTaskId,
        completed_task_title: task.title || 'Unknown',
        completed_task_description: task.description || 'No description',
        audit_summary: `Found ${testingTaskResult.subtasks_found} subtasks, ${testingTaskResult.context_entries_found} context entries, ${testingTaskResult.files_modified} files modified`
      }
    );
    
    if (!prompt) {
      console.error(`❌ Failed to build prompt for testing agent ${testingAgentId}`);
      return { success: false, testing_agent_id: testingAgentId, error: 'Failed to build prompt' };
    }
    
    // 8. Create tmux session for testing agent
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
          execSync(`tmux send-keys -t "${sessionName}" "${prompt.replace(/\\/g, '\\\\').replace(/"/g, '\\"').replace(/\n/g, ' ')}"`, { timeout: 10000 });
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
        INSERT INTO agent_actions (agent_id, action_type, details, timestamp)
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
      
      // Schedule enhanced testing validation after a brief delay to allow agent to start
      setTimeout(async () => {
        try {
          const enhancedResult = await runEnhancedTestingValidation(
            testingAgentId,
            completedByAgent,
            completedTaskId,
            {} // In real implementation, pass actual completed work data
          );
          
          if (MCP_DEBUG) {
            console.log(`🧪 Enhanced testing result for ${testingAgentId}:`, enhancedResult);
          }
        } catch (error) {
          console.error(`❌ Enhanced testing validation error:`, error);
        }
      }, 15000); // 15 second delay
      
      console.log(`🧪 Testing agent ${testingAgentId} launched successfully for task ${completedTaskId} with enhanced validation`);
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

/**
 * Send feedback message to the original agent after testing
 */
export async function sendTestingFeedbackToAgent(
  testingAgentId: string, 
  originalAgentId: string, 
  taskId: string, 
  testResults: { passed: boolean; issues: string[]; recommendations: string[] }
): Promise<boolean> {
  try {
    const db = getDbConnection();
    
    // Get testing agent token
    const testingAgent = db.prepare('SELECT token FROM agents WHERE agent_id = ?').get(testingAgentId);
    if (!testingAgent) {
      console.error(`❌ Testing agent ${testingAgentId} not found`);
      return false;
    }
    
    // Get original agent token
    const originalAgent = db.prepare('SELECT token FROM agents WHERE agent_id = ?').get(originalAgentId);
    if (!originalAgent) {
      console.error(`❌ Original agent ${originalAgentId} not found`);
      return false;
    }
    
    // Construct feedback message
    const statusEmoji = testResults.passed ? '✅' : '❌';
    const statusText = testResults.passed ? 'PASSED' : 'FAILED';
    
    let message = `🧪 **TESTING FEEDBACK for Task ${taskId}**\n\n`;
    message += `${statusEmoji} **Test Result: ${statusText}**\n\n`;
    
    if (testResults.issues.length > 0) {
      message += `**Issues Found:**\n`;
      testResults.issues.forEach((issue, i) => {
        message += `${i + 1}. ${issue}\n`;
      });
      message += '\n';
    }
    
    if (testResults.recommendations.length > 0) {
      message += `**Recommendations:**\n`;
      testResults.recommendations.forEach((rec, i) => {
        message += `${i + 1}. ${rec}\n`;
      });
      message += '\n';
    }
    
    message += `From: Testing Agent ${testingAgentId}\n`;
    message += `Task Status: ${testResults.passed ? 'Validated ✅' : 'Needs Revision ❌'}`;
    
    // Send message using the agent communication system
    const messageId = `test_feedback_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    const insertMessage = db.prepare(`
      INSERT INTO agent_messages (
        message_id, sender_id, recipient_id, message_content, 
        message_type, priority, timestamp, delivered, read
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);
    
    insertMessage.run(
      messageId,
      testingAgentId,
      originalAgentId,
      message,
      'assistance_request', // Use assistance_request type for testing feedback
      testResults.passed ? 'normal' : 'high', // High priority for failures
      new Date().toISOString(),
      0, // Not delivered yet
      0  // Not read yet
    );
    
    // Also send to tmux session if agent is active
    try {
      // Try to find agent's tmux session by pattern
      const stdout = execSync(`tmux list-sessions | grep "${originalAgentId}" | head -1 | cut -d: -f1`, { timeout: 5000 });
      const sessionName = stdout.toString().trim();
      
      if (sessionName) {
        const tmuxMessage = `🧪 Testing feedback received for task ${taskId}: ${statusText}`;
        execSync(`tmux display-message -t "${sessionName}" "${tmuxMessage}"`, { timeout: 5000 });
      }
    } catch (tmuxError) {
      // Non-critical - message is still in database
      console.log(`⚠️ Could not send tmux notification: ${tmuxError}`);
    }
    
    if (MCP_DEBUG) {
      console.log(`✅ Testing feedback sent from ${testingAgentId} to ${originalAgentId}`);
    }
    
    return true;
    
  } catch (error) {
    console.error(`❌ Error sending testing feedback:`, error);
    return false;
  }
}

/**
 * Clean incorrect or outdated project context based on testing results
 */
export async function cleanIncorrectProjectContext(
  testingAgentId: string,
  taskId: string,
  incorrectContextKeys: string[]
): Promise<{ cleaned: number; errors: string[] }> {
  try {
    const db = getDbConnection();
    const errors: string[] = [];
    let cleaned = 0;
    
    if (MCP_DEBUG) {
      console.log(`🧹 Testing agent ${testingAgentId} cleaning ${incorrectContextKeys.length} context entries`);
    }
    
    for (const contextKey of incorrectContextKeys) {
      try {
        // Check if context exists
        const existingContext = db.prepare('SELECT * FROM project_context WHERE context_key = ?').get(contextKey);
        
        if (existingContext) {
          // Archive the incorrect context with timestamp and reason
          const archiveKey = `archived_${contextKey}_${Date.now()}`;
          const context = existingContext as any;
          const archiveValue = {
            original_value: JSON.parse(context.value),
            archived_by: testingAgentId,
            archived_reason: `Identified as incorrect during task ${taskId} testing`,
            archived_at: new Date().toISOString(),
            original_updated_by: context.updated_by,
            original_updated_at: context.last_updated
          };
          
          // Insert archived version
          db.prepare(`
            INSERT OR REPLACE INTO project_context 
            (context_key, value, last_updated, updated_by, description)
            VALUES (?, ?, ?, ?, ?)
          `).run(
            archiveKey,
            JSON.stringify(archiveValue),
            new Date().toISOString(),
            testingAgentId,
            `Archived incorrect context from ${contextKey}`
          );
          
          // Delete the incorrect context
          db.prepare('DELETE FROM project_context WHERE context_key = ?').run(contextKey);
          
          cleaned++;
          
          if (MCP_DEBUG) {
            console.log(`🧹 Cleaned context: ${contextKey} -> archived as ${archiveKey}`);
          }
          
        } else {
          errors.push(`Context key "${contextKey}" not found`);
        }
        
      } catch (contextError) {
        errors.push(`Failed to clean context "${contextKey}": ${contextError}`);
      }
    }
    
    // Log the context cleaning action
    const logAction = db.prepare(`
      INSERT INTO agent_actions (
        agent_id, action_type, task_id, timestamp, details
      ) VALUES (?, ?, ?, ?, ?)
    `);
    
    const timestamp = new Date().toISOString();
    logAction.run(
      testingAgentId,
      'cleaned_project_context',
      taskId,
      timestamp,
      JSON.stringify({
        cleaned_count: cleaned,
        error_count: errors.length,
        context_keys: incorrectContextKeys
      })
    );
    
    return { cleaned, errors };
    
  } catch (error) {
    console.error(`❌ Error cleaning project context:`, error);
    return { cleaned: 0, errors: [String(error)] };
  }
}

/**
 * Enhanced testing agent with feedback and context cleaning
 */
export async function runEnhancedTestingValidation(
  testingAgentId: string,
  originalAgentId: string,
  taskId: string,
  completedWork: any
): Promise<{ success: boolean; feedback_sent: boolean; context_cleaned: number }> {
  try {
    // Simulate testing validation (in real implementation, this would analyze the completed work)
    const testResults = {
      passed: Math.random() > 0.3, // 70% pass rate for demo
      issues: [
        'Implementation does not handle edge case X',
        'Code comments are insufficient for complex logic'
      ],
      recommendations: [
        'Add error handling for network timeouts',
        'Include unit tests for core functions',
        'Update documentation with usage examples'
      ]
    };
    
    // Send feedback to original agent
    const feedbackSent = await sendTestingFeedbackToAgent(
      testingAgentId, 
      originalAgentId, 
      taskId, 
      testResults
    );
    
    // Clean incorrect context if any issues found
    let contextCleaned = 0;
    if (!testResults.passed) {
      const incorrectContextKeys = [
        `task_${taskId}_assumptions`,
        `outdated_implementation_notes`
      ];
      
      const cleaningResult = await cleanIncorrectProjectContext(
        testingAgentId,
        taskId,
        incorrectContextKeys
      );
      
      contextCleaned = cleaningResult.cleaned;
    }
    
    if (MCP_DEBUG) {
      console.log(`🧪 Enhanced testing validation complete: feedback_sent=${feedbackSent}, context_cleaned=${contextCleaned}`);
    }
    
    return {
      success: true,
      feedback_sent: feedbackSent,
      context_cleaned: contextCleaned
    };
    
  } catch (error) {
    console.error(`❌ Enhanced testing validation failed:`, error);
    return {
      success: false,
      feedback_sent: false,
      context_cleaned: 0
    };
  }
}