// Session state management tools for preserving agent context across connections
// Allows agents to save and restore their working state during session recovery

import { z } from 'zod';
import { toolRegistry } from './registry.js';
import { saveAgentSessionState, loadAgentSessionState } from '../utils/sessionPersistence.js';
import { MCP_DEBUG } from '../core/config.js';

// Save agent session state
toolRegistry.registerTool({
  name: 'save_session_state',
  description: 'Save agent working state for session recovery. Use this to preserve important context, task progress, or conversation state that should survive connection drops.',
  inputSchema: z.object({
    state_key: z.string().describe('Unique key for this piece of state (e.g., "current_task", "conversation_context", "work_progress")'),
    state_data: z.any().describe('The state data to save (will be JSON serialized)'),
    expires_in_hours: z.number().optional().describe('Optional: Hours until this state expires (default: 24 hours)')
  }),
  handler: async (args, context) => {
    try {
      const { state_key, state_data, expires_in_hours = 24 } = args;
      
      // Calculate expiration time
      const expiresAt = new Date(Date.now() + (expires_in_hours * 60 * 60 * 1000)).toISOString();
      
      // Use context information to identify agent and session
      const agentId = context.agentId || 'unknown';
      const sessionId = context.sessionId || 'default';
      
      await saveAgentSessionState(agentId, sessionId, state_key, state_data, expiresAt);
      
      if (MCP_DEBUG) {
        console.log(`💾 Agent ${agentId} saved session state: ${state_key}`);
      }
      
      return {
        content: [{
          type: 'text',
          text: `✅ Session state saved successfully\n\nKey: ${state_key}\nAgent: ${agentId}\nSession: ${sessionId}\nExpires: ${new Date(expiresAt).toLocaleString()}\n\nThis state will be preserved across connection drops and can be restored when the session reconnects.`
        }],
        isError: false
      };
    } catch (error) {
      console.error('Error saving session state:', error);
      return {
        content: [{
          type: 'text',
          text: `❌ Failed to save session state: ${error instanceof Error ? error.message : String(error)}`
        }],
        isError: true
      };
    }
  }
});

// Load agent session state
toolRegistry.registerTool({
  name: 'load_session_state',
  description: 'Load previously saved agent working state. Use this after a connection recovery to restore your context and continue where you left off.',
  inputSchema: z.object({
    state_key: z.string().describe('The key for the state data to load'),
  }),
  handler: async (args, context) => {
    try {
      const { state_key } = args;
      
      // Use context information to identify agent and session
      const agentId = context.agentId || 'unknown';
      const sessionId = context.sessionId || 'default';
      
      const stateData = await loadAgentSessionState(agentId, sessionId, state_key);
      
      if (stateData === null) {
        return {
          content: [{
            type: 'text',
            text: `⚠️ No session state found for key: ${state_key}\n\nAgent: ${agentId}\nSession: ${sessionId}\n\nThis could mean:\n- The state was never saved\n- The state has expired\n- This is a new session\n- The key name doesn't match`
          }],
          isError: false
        };
      }
      
      if (MCP_DEBUG) {
        console.log(`📖 Agent ${agentId} loaded session state: ${state_key}`);
      }
      
      return {
        content: [{
          type: 'text',
          text: `✅ Session state loaded successfully\n\nKey: ${state_key}\nAgent: ${agentId}\nSession: ${sessionId}\n\nData:\n${JSON.stringify(stateData, null, 2)}\n\nYou can now use this data to continue your work from where you left off.`
        }],
        isError: false
      };
    } catch (error) {
      console.error('Error loading session state:', error);
      return {
        content: [{
          type: 'text',
          text: `❌ Failed to load session state: ${error instanceof Error ? error.message : String(error)}`
        }],
        isError: true
      };
    }
  }
});

// List saved session states
toolRegistry.registerTool({
  name: 'list_session_states',
  description: 'List all saved session states for this agent and session. Useful for seeing what context is available after a connection recovery.',
  inputSchema: z.object({}),
  handler: async (args, context) => {
    try {
      // Use context information to identify agent and session
      const agentId = context.agentId || 'unknown';
      const sessionId = context.sessionId || 'default';
      
      // We need to query the database directly for this
      const { getDbConnection } = await import('../db/connection.js');
      const db = getDbConnection();
      const now = new Date().toISOString();
      
      const states = db.prepare(`
        SELECT state_key, last_updated, expires_at
        FROM agent_session_state 
        WHERE agent_id = ? AND mcp_session_id = ?
        AND (expires_at IS NULL OR expires_at > ?)
        ORDER BY last_updated DESC
      `).all(agentId, sessionId, now);
      
      if (states.length === 0) {
        return {
          content: [{
            type: 'text',
            text: `📋 No saved session states found\n\nAgent: ${agentId}\nSession: ${sessionId}\n\nThis could be a new session or all previous states have expired.`
          }],
          isError: false
        };
      }
      
      const stateList = states.map((state: any) => {
        const expiresText = state.expires_at 
          ? `Expires: ${new Date(state.expires_at).toLocaleString()}`
          : 'Never expires';
        
        return `• ${state.state_key}\n  Last updated: ${new Date(state.last_updated).toLocaleString()}\n  ${expiresText}`;
      }).join('\n\n');
      
      return {
        content: [{
          type: 'text',
          text: `📋 Saved session states (${states.length} found)\n\nAgent: ${agentId}\nSession: ${sessionId}\n\n${stateList}\n\nUse load_session_state with any of these keys to restore your context.`
        }],
        isError: false
      };
    } catch (error) {
      console.error('Error listing session states:', error);
      return {
        content: [{
          type: 'text',
          text: `❌ Failed to list session states: ${error instanceof Error ? error.message : String(error)}`
        }],
        isError: true
      };
    }
  }
});

// Clear session state
toolRegistry.registerTool({
  name: 'clear_session_state',
  description: 'Clear a specific saved session state or all states for this agent/session.',
  inputSchema: z.object({
    state_key: z.string().optional().describe('Specific state key to clear. If not provided, clears ALL states for this agent/session.'),
    confirm: z.boolean().default(false).describe('Must be true to actually perform the clear operation')
  }),
  handler: async (args, context) => {
    try {
      const { state_key, confirm } = args;
      
      if (!confirm) {
        return {
          content: [{
            type: 'text',
            text: `⚠️ Clear operation cancelled\n\nTo actually clear session state, set confirm: true\n\n${state_key ? `This would clear: ${state_key}` : 'This would clear ALL session states for this agent/session'}`
          }],
          isError: false
        };
      }
      
      // Use context information to identify agent and session
      const agentId = context.agentId || 'unknown';
      const sessionId = context.sessionId || 'default';
      
      const { getDbConnection } = await import('../db/connection.js');
      const db = getDbConnection();
      
      let result;
      if (state_key) {
        // Clear specific state
        result = db.prepare(`
          DELETE FROM agent_session_state 
          WHERE agent_id = ? AND mcp_session_id = ? AND state_key = ?
        `).run(agentId, sessionId, state_key);
      } else {
        // Clear all states for this agent/session
        result = db.prepare(`
          DELETE FROM agent_session_state 
          WHERE agent_id = ? AND mcp_session_id = ?
        `).run(agentId, sessionId);
      }
      
      const clearedCount = result.changes;
      const whatCleared = state_key ? `state "${state_key}"` : 'all session states';
      
      if (clearedCount === 0) {
        return {
          content: [{
            type: 'text',
            text: `⚠️ No session states were cleared\n\n${state_key ? `State "${state_key}" was not found` : 'No session states exist for this agent/session'}`
          }],
          isError: false
        };
      }
      
      return {
        content: [{
          type: 'text',
          text: `✅ Cleared ${whatCleared}\n\nAgent: ${agentId}\nSession: ${sessionId}\nStates cleared: ${clearedCount}`
        }],
        isError: false
      };
    } catch (error) {
      console.error('Error clearing session state:', error);
      return {
        content: [{
          type: 'text',
          text: `❌ Failed to clear session state: ${error instanceof Error ? error.message : String(error)}`
        }],
        isError: true
      };
    }
  }
});

console.log('✅ Session state management tools registered');