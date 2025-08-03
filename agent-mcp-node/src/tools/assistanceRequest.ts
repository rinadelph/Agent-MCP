// Intelligent assistance request system
// Routes agent help requests to admin's current Claude Code session

import { z } from 'zod';
import { randomBytes } from 'crypto';
import { registerTool } from './registry.js';
import { getDbConnection } from '../db/connection.js';
import { getAgentId } from '../core/auth.js';
import { sendMessageToAdminSession } from '../utils/sessionDetection.js';
import { MCP_DEBUG } from '../core/config.js';

/**
 * Generate unique assistance request ID
 */
function generateAssistanceId(): string {
  return `assist_${randomBytes(6).toString('hex')}`;
}

/**
 * Tool for agents to request assistance from admin
 */
registerTool(
  'request_assistance',
  'Request assistance from admin when stuck or needing guidance. Routes to admin\'s current Claude Code session.',
  z.object({
    token: z.string().describe('Agent\'s authentication token'),
    task_id: z.string().optional().describe('Task ID related to the assistance request'),
    description: z.string().min(10).max(2000).describe('Description of what help is needed (10-2000 characters)'),
    urgency: z.enum(['low', 'normal', 'high', 'urgent']).optional().default('normal').describe('Urgency level of the request'),
    context: z.string().optional().describe('Additional context about current work state'),
    suggested_actions: z.array(z.string()).optional().describe('Possible solutions the agent has considered'),
    blocking: z.boolean().optional().default(false).describe('Whether this issue is blocking all progress')
  }),
  async (args, context) => {
    try {
      const { 
        token, 
        task_id, 
        description, 
        urgency = 'normal', 
        context: additionalContext, 
        suggested_actions = [], 
        blocking = false 
      } = args;

      // Authentication
      const agentId = getAgentId(token);
      if (!agentId) {
        return {
          content: [{ type: 'text' as const, text: 'Unauthorized: Valid agent token required' }],
          isError: true
        };
      }

      // Validation
      if (!description.trim()) {
        return {
          content: [{ type: 'text' as const, text: 'Error: Description is required and cannot be empty' }],
          isError: true
        };
      }

      const db = getDbConnection();
      const assistanceId = generateAssistanceId();
      const timestamp = new Date().toISOString();

      // Get agent info for context
      const agent = db.prepare('SELECT agent_id, current_task, working_directory FROM agents WHERE agent_id = ?').get(agentId) as any;
      
      // Get task info if provided
      let taskInfo = null;
      if (task_id) {
        taskInfo = db.prepare('SELECT task_id, title, description as task_description, status, priority FROM tasks WHERE task_id = ?').get(task_id) as any;
      }

      // Store assistance request in database
      const requestData = {
        assistance_id: assistanceId,
        agent_id: agentId,
        task_id: task_id || null,
        description,
        urgency,
        additional_context: additionalContext || null,
        suggested_actions: JSON.stringify(suggested_actions),
        blocking,
        status: 'pending',
        created_at: timestamp,
        agent_working_directory: agent?.working_directory || null,
        agent_current_task: agent?.current_task || null
      };

      // Store in agent_actions for audit trail
      const stmt = db.prepare(`
        INSERT INTO agent_actions (agent_id, action_type, task_id, timestamp, details)
        VALUES (?, ?, ?, ?, ?)
      `);
      
      stmt.run(agentId, 'request_assistance', task_id || null, timestamp, JSON.stringify(requestData));

      // Build comprehensive assistance message for admin
      const messageParts = [
        `🤖 **Agent ${agentId} requests assistance**`,
        `Request ID: ${assistanceId}`,
        `${blocking ? '🚫 **BLOCKING ISSUE**' : ''}`,
        '',
        `**Problem Description:**`,
        description,
        ''
      ];

      if (taskInfo) {
        messageParts.push(
          `**Related Task:**`,
          `- ID: ${taskInfo.task_id}`,
          `- Title: ${taskInfo.title}`,
          `- Status: ${taskInfo.status}`,
          `- Priority: ${taskInfo.priority}`,
          ''
        );
      }

      if (agent?.working_directory) {
        messageParts.push(
          `**Agent Context:**`,
          `- Working Directory: ${agent.working_directory}`,
          `- Current Task: ${agent.current_task || 'None'}`,
          ''
        );
      }

      if (additionalContext) {
        messageParts.push(
          `**Additional Context:**`,
          additionalContext,
          ''
        );
      }

      if (suggested_actions.length > 0) {
        messageParts.push(
          `**Agent's Suggested Actions:**`,
          ...suggested_actions.map((action: string) => `- ${action}`),
          ''
        );
      }

      messageParts.push(
        `**Admin Actions:**`,
        `- Send guidance: send_agent_message with recipient_id="${agentId}"`,
        `- Broadcast update: broadcast_admin_message`,
        `- View agent: tmux attach-session -t [agent-session]`,
        `- Check tasks: view_tasks`,
        ''
      );

      const fullMessage = messageParts.join('\n');

      // Try to deliver to admin's current session
      let deliveryStatus = 'stored';
      const delivered = await sendMessageToAdminSession(fullMessage, urgency);
      
      if (delivered) {
        deliveryStatus = 'delivered_to_admin_session';
        
        // Update delivery status in database
        const updateStmt = db.prepare(`
          UPDATE agent_actions 
          SET details = json_set(details, '$.delivery_status', ?) 
          WHERE agent_id = ? AND action_type = 'request_assistance' AND timestamp = ?
        `);
        updateStmt.run('delivered_to_admin_session', agentId, timestamp);
      }

      // Also send as agent message for persistent storage
      const messageStmt = db.prepare(`
        INSERT INTO agent_messages (message_id, sender_id, recipient_id, message_content, 
                                  message_type, priority, timestamp, delivered, read)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
      `);
      
      messageStmt.run(
        `msg_${assistanceId}`, 
        agentId, 
        'admin', 
        fullMessage, 
        'assistance_request', 
        urgency, 
        timestamp, 
        delivered ? 1 : 0, 
        0
      );

      if (MCP_DEBUG) {
        console.log(`🆘 Assistance request from ${agentId}: ${assistanceId} (${deliveryStatus})`);
      }

      return {
        content: [{
          type: 'text' as const,
          text: `✅ **Assistance Request Submitted**

Request ID: ${assistanceId}
Urgency: ${urgency.toUpperCase()}
Delivery: ${deliveryStatus === 'delivered_to_admin_session' ? '📨 Sent to admin\'s current session' : '📝 Stored for admin review'}
${blocking ? '\n🚫 **BLOCKING**: This issue prevents further progress' : ''}

Your request has been ${delivered ? 'immediately delivered to the admin' : 'stored and will be seen by the admin'}. 
${blocking ? 'Since this is blocking, consider pausing current work until resolved.' : 'You can continue with other tasks while waiting for assistance.'}

💡 **While waiting:**
- Document any additional findings
- Try alternative approaches if possible  
- Update task status if needed`
        }],
        isError: false
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error('Error processing assistance request:', error);
      return {
        content: [{ type: 'text' as const, text: `❌ Failed to request assistance: ${errorMessage}` }],
        isError: true
      };
    }
  }
);

console.log('✅ Intelligent assistance request system loaded');