// Agent communication tools for Agent-MCP Node.js
// Ported from Python agent_communication_tools.py

import { z } from 'zod';
import { randomBytes } from 'crypto';
import { registerTool } from './registry.js';
import { getDbConnection } from '../db/connection.js';
import { getAgentId, verifyToken } from '../core/auth.js';
import { globalState } from '../core/globals.js';
import { 
  sessionExists, 
  sanitizeSessionName, 
  sendCommandToSession,
  sendPromptToSession 
} from '../utils/tmux.js';
import { MCP_DEBUG } from '../core/config.js';

/**
 * Generate a unique message ID
 */
function generateMessageId(): string {
  return `msg_${randomBytes(8).toString('hex')}`;
}

/**
 * Check if two agents are allowed to communicate
 */
function canAgentsCommunicate(senderId: string, recipientId: string, isAdmin: boolean): [boolean, string] {
  // Admin can always communicate
  if (isAdmin) {
    return [true, "Admin privileges"];
  }
  
  // Check if both agents are active
  if (globalState.activeAgents.has(senderId) && globalState.activeAgents.has(recipientId)) {
    return [true, "Both agents are active"];
  }
  
  // Could be extended with more sophisticated permission system
  return [false, "Communication not permitted between these agents"];
}

/**
 * Tool for sending messages between agents
 */
registerTool(
  'send_agent_message',
  'Send a message to another agent with permission checks and delivery options.',
  z.object({
    token: z.string().describe('Sender\'s authentication token'),
    recipient_id: z.string().describe('ID of the agent to send message to'),
    message: z.string().max(4000).describe('Message content (max 4000 characters)'),
    message_type: z.enum(['text', 'assistance_request', 'task_update', 'notification', 'stop_command'])
      .optional().default('text').describe('Type of message'),
    priority: z.enum(['low', 'normal', 'high', 'urgent'])
      .optional().default('normal').describe('Message priority'),
    deliver_method: z.enum(['tmux', 'store', 'both'])
      .optional().default('tmux').describe('How to deliver the message')
  }),
  async (args, context) => {
    try {
      const { token, recipient_id, message, message_type = 'text', priority = 'normal', deliver_method = 'tmux' } = args;

      // Authentication
      const senderId = getAgentId(token);
      if (!senderId) {
        return {
          content: [{ type: 'text' as const, text: 'Unauthorized: Valid token required' }],
          isError: true
        };
      }

      // Validation
      if (!recipient_id || !message) {
        return {
          content: [{ type: 'text' as const, text: 'Error: recipient_id and message are required' }],
          isError: true
        };
      }

      // Admin-only check for stop commands
      const isAdmin = verifyToken(token, 'admin');
      if (message_type === 'stop_command' && !isAdmin) {
        return {
          content: [{ type: 'text' as const, text: 'Error: Only admin can send stop commands' }],
          isError: true
        };
      }

      // Permission check
      const [canCommunicate, reason] = canAgentsCommunicate(senderId, recipient_id, isAdmin);
      if (!canCommunicate) {
        return {
          content: [{ type: 'text' as const, text: `Communication denied: ${reason}` }],
          isError: true
        };
      }

      // Create message data
      const messageId = generateMessageId();
      const timestamp = new Date().toISOString();

      const db = getDbConnection();
      
      // Store message in database
      const stmt = db.prepare(`
        INSERT INTO agent_messages (message_id, sender_id, recipient_id, message_content, 
                                  message_type, priority, timestamp, delivered, read)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
      `);
      
      stmt.run(messageId, senderId, recipient_id, message, message_type, priority, timestamp, 0, 0);

      let deliveryStatus = 'stored';

      // Attempt delivery based on method
      if (deliver_method === 'tmux' || deliver_method === 'both') {
        // Try to deliver to recipient's tmux session
        const recipientSession = globalState.agentTmuxSessions.get(recipient_id);
        
        if (recipientSession && await sessionExists(recipientSession)) {
          try {
            if (message_type === 'stop_command') {
              // Send escape sequences to interrupt current operation
              const cleanSession = sanitizeSessionName(recipientSession);
              for (let i = 0; i < 4; i++) {
                await sendCommandToSession(cleanSession, 'Escape');
                await new Promise(resolve => setTimeout(resolve, 1000));
              }
              deliveryStatus = 'delivered_via_tmux';
            } else {
              // Format and send the message
              const formattedMessage = `
📨 **Message from ${senderId}** (${priority.toUpperCase()})
Type: ${message_type}
Time: ${new Date(timestamp).toLocaleString()}

${message}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`;
              
              const success = await sendPromptToSession(recipientSession, formattedMessage, 3);
              if (success) {
                deliveryStatus = 'delivered_via_tmux';
                
                // Mark as delivered in database
                const updateStmt = db.prepare('UPDATE agent_messages SET delivered = 1 WHERE message_id = ?');
                updateStmt.run(messageId);
              }
            }
          } catch (error) {
            console.error(`Failed to deliver message to ${recipient_id}:`, error);
          }
        }
      }

      if (MCP_DEBUG) {
        console.log(`📨 Message sent: ${senderId} → ${recipient_id} (${message_type}, ${deliveryStatus})`);
      }

      return {
        content: [{
          type: 'text' as const,
          text: `✅ Message sent successfully to ${recipient_id}\n- Message ID: ${messageId}\n- Delivery: ${deliveryStatus}\n- Type: ${message_type}\n- Priority: ${priority}`
        }],
        isError: false
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error('Error sending agent message:', error);
      return {
        content: [{ type: 'text' as const, text: `❌ Failed to send message: ${errorMessage}` }],
        isError: true
      };
    }
  }
);

/**
 * Tool for retrieving agent messages
 */
registerTool(
  'get_agent_messages',
  'Retrieve messages for the current agent.',
  z.object({
    token: z.string().describe('Agent\'s authentication token'),
    include_sent: z.boolean().optional().default(false).describe('Include messages sent by this agent'),
    include_received: z.boolean().optional().default(true).describe('Include messages received by this agent'),
    mark_as_read: z.boolean().optional().default(true).describe('Mark retrieved messages as read'),
    limit: z.number().int().min(1).max(100).optional().default(20).describe('Maximum number of messages to retrieve'),
    message_type: z.enum(['text', 'assistance_request', 'task_update', 'notification', 'stop_command'])
      .optional().describe('Filter by message type'),
    unread_only: z.boolean().optional().default(false).describe('Only show unread messages')
  }),
  async (args, context) => {
    try {
      const { 
        token, 
        include_sent = false, 
        include_received = true, 
        mark_as_read = true, 
        limit = 20, 
        message_type, 
        unread_only = false 
      } = args;

      // Authentication
      const agentId = getAgentId(token);
      if (!agentId) {
        return {
          content: [{ type: 'text' as const, text: 'Unauthorized: Valid token required' }],
          isError: true
        };
      }

      const db = getDbConnection();
      
      // Build query conditions
      const conditions: string[] = [];
      const params: any[] = [];

      if (include_sent && include_received) {
        conditions.push('(sender_id = ? OR recipient_id = ?)');
        params.push(agentId, agentId);
      } else if (include_sent) {
        conditions.push('sender_id = ?');
        params.push(agentId);
      } else if (include_received) {
        conditions.push('recipient_id = ?');
        params.push(agentId);
      }

      if (message_type) {
        conditions.push('message_type = ?');
        params.push(message_type);
      }

      if (unread_only) {
        conditions.push('read = 0');
      }

      const whereClause = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';
      
      const query = `
        SELECT message_id, sender_id, recipient_id, message_content, message_type, 
               priority, timestamp, delivered, read
        FROM agent_messages 
        ${whereClause}
        ORDER BY timestamp DESC 
        LIMIT ?
      `;
      
      params.push(limit);
      
      const stmt = db.prepare(query);
      const messages = stmt.all(...params) as any[];

      // Mark messages as read if requested
      if (mark_as_read && messages.length > 0) {
        const messageIds = messages
          .filter(msg => msg.recipient_id === agentId && !msg.read)
          .map(msg => msg.message_id);
        
        if (messageIds.length > 0) {
          const placeholders = messageIds.map(() => '?').join(',');
          const updateStmt = db.prepare(`UPDATE agent_messages SET read = 1 WHERE message_id IN (${placeholders})`);
          updateStmt.run(...messageIds);
        }
      }

      // Format response
      if (messages.length === 0) {
        return {
          content: [{
            type: 'text' as const,
            text: '📭 No messages found matching your criteria.'
          }],
          isError: false
        };
      }

      const formattedMessages = messages.map((msg, index) => {
        const isReceived = msg.recipient_id === agentId;
        const direction = isReceived ? '📥 RECEIVED' : '📤 SENT';
        const otherParty = isReceived ? msg.sender_id : msg.recipient_id;
        const readStatus = msg.read ? '✓' : '●';
        const deliveryStatus = msg.delivered ? '✓ delivered' : '○ stored';
        
        return `${index + 1}. ${direction} ${readStatus}
${msg.message_type.toUpperCase()} | ${msg.priority.toUpperCase()} | ${deliveryStatus}
${isReceived ? 'From' : 'To'}: ${otherParty}
Time: ${new Date(msg.timestamp).toLocaleString()}
ID: ${msg.message_id}

${msg.message_content}`;
      }).join('\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n');

      return {
        content: [{
          type: 'text' as const,
          text: `📬 **Agent Messages for ${agentId}**\nShowing ${messages.length} message(s)\n\n${formattedMessages}`
        }],
        isError: false
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error('Error retrieving agent messages:', error);
      return {
        content: [{ type: 'text' as const, text: `❌ Failed to retrieve messages: ${errorMessage}` }],
        isError: true
      };
    }
  }
);

/**
 * Tool for admin to broadcast messages to all active agents
 */
registerTool(
  'broadcast_admin_message',
  'Admin-only tool to broadcast a message to all active agents.',
  z.object({
    token: z.string().describe('Admin authentication token'),
    message: z.string().max(4000).describe('Message content to broadcast'),
    message_type: z.enum(['broadcast', 'announcement', 'system_alert'])
      .optional().default('broadcast').describe('Type of broadcast message'),
    priority: z.enum(['low', 'normal', 'high', 'urgent'])
      .optional().default('high').describe('Message priority')
  }),
  async (args, context) => {
    try {
      const { token, message, message_type = 'broadcast', priority = 'high' } = args;

      // Admin authentication required
      if (!verifyToken(token, 'admin')) {
        return {
          content: [{ type: 'text' as const, text: 'Unauthorized: Admin privileges required' }],
          isError: true
        };
      }

      // Validation
      if (!message) {
        return {
          content: [{ type: 'text' as const, text: 'Error: message is required' }],
          isError: true
        };
      }

      const db = getDbConnection();
      const adminId = 'admin';
      const timestamp = new Date().toISOString();
      
      // Get all active agents
      const activeAgents = Array.from(globalState.activeAgents.keys());
      
      if (activeAgents.length === 0) {
        return {
          content: [{
            type: 'text' as const,
            text: '📭 No active agents to broadcast to.'
          }],
          isError: false
        };
      }

      let deliveredCount = 0;
      const results: string[] = [];

      // Send to each active agent
      for (const recipientId of activeAgents) {
        try {
          const messageId = generateMessageId();
          
          // Store in database
          const stmt = db.prepare(`
            INSERT INTO agent_messages (message_id, sender_id, recipient_id, message_content, 
                                      message_type, priority, timestamp, delivered, read)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
          `);
          
          stmt.run(messageId, adminId, recipientId, message, message_type, priority, timestamp, 0, 0);

          // Try to deliver via tmux
          const recipientSession = globalState.agentTmuxSessions.get(recipientId);
          
          if (recipientSession && await sessionExists(recipientSession)) {
            const formattedMessage = `
🔔 **ADMIN BROADCAST** (${priority.toUpperCase()})
Type: ${message_type.toUpperCase()}
Time: ${new Date(timestamp).toLocaleString()}

${message}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`;
            
            const success = await sendPromptToSession(recipientSession, formattedMessage, 3);
            if (success) {
              deliveredCount++;
              
              // Mark as delivered
              const updateStmt = db.prepare('UPDATE agent_messages SET delivered = 1 WHERE message_id = ?');
              updateStmt.run(messageId);
              
              results.push(`✓ ${recipientId}: delivered via tmux`);
            } else {
              results.push(`○ ${recipientId}: stored only (tmux delivery failed)`);
            }
          } else {
            results.push(`○ ${recipientId}: stored only (no tmux session)`);
          }
          
        } catch (error) {
          results.push(`✗ ${recipientId}: failed (${error instanceof Error ? error.message : String(error)})`);
        }
      }

      if (MCP_DEBUG) {
        console.log(`📢 Admin broadcast sent to ${activeAgents.length} agents, ${deliveredCount} delivered via tmux`);
      }

      return {
        content: [{
          type: 'text' as const,
          text: `📢 **Broadcast Complete**\n\nMessage sent to ${activeAgents.length} active agent(s)\nDelivered via tmux: ${deliveredCount}\n\n**Delivery Results:**\n${results.join('\n')}`
        }],
        isError: false
      };

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      console.error('Error broadcasting admin message:', error);
      return {
        content: [{ type: 'text' as const, text: `❌ Failed to broadcast message: ${errorMessage}` }],
        isError: true
      };
    }
  }
);

console.log('✅ Agent communication tools loaded');