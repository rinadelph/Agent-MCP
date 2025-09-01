// MCP Resources for Agent-MCP Node.js
// Provides agent data as MCP resources for @ mentions

import { getDbConnection } from '../db/connection.js';
import { MCP_DEBUG } from '../core/config.js';
import { createColoredResource, ColoredResource } from '../core/resourceColors.js';

// Use the enhanced colored resource interface
export interface AgentResource extends ColoredResource {}

export interface AgentResourceContent {
  uri: string;
  mimeType: string;
  text: string;
}

/**
 * Get all active agents as resources
 */
export async function getAgentResources(): Promise<AgentResource[]> {
  const db = getDbConnection();
  
  try {
    const stmt = db.prepare(`
      SELECT 
        a.agent_id, 
        a.status, 
        a.created_at, 
        a.current_task,
        t.status as task_status,
        t.title as task_title,
        (SELECT COUNT(*) FROM tasks WHERE assigned_to = a.agent_id AND status = 'completed') as completed_tasks,
        (SELECT COUNT(*) FROM tasks WHERE assigned_to = a.agent_id AND status = 'in_progress') as active_tasks,
        (SELECT COUNT(*) FROM tasks WHERE assigned_to = a.agent_id AND status = 'pending') as pending_tasks
      FROM agents a
      LEFT JOIN tasks t ON a.current_task = t.task_id
      WHERE a.status IN ('created', 'active')
      ORDER BY a.created_at DESC
    `);
    
    const agents = stmt.all();
    
    return agents.map((agent: any) => {
      // Semantic status and color mapping
      let color = 'blue';
      let status = 'ready';
      let description = 'agent';
      
      if (agent.current_task && agent.task_status === 'in_progress') {
        color = 'yellow';
        status = 'working';
        description = `🔄 ${agent.task_title || 'working'}`;
      } else if (agent.completed_tasks > 0 && !agent.current_task) {
        color = 'green';
        status = 'completed';
        description = `✅ ${agent.completed_tasks} done`;
      } else if (agent.pending_tasks > 0) {
        color = 'cyan';
        status = 'pending';
        description = `📋 ${agent.pending_tasks} pending`;
      } else if (agent.status === 'active') {
        color = 'green';
        status = 'active';
        description = '🟢 ready';
      }
      
      // Get ANSI color code for the name - using RGB orange for working agents
      const ansiCode = color === 'yellow' ? '\x1b[1;38;2;255;165;0m' : // Bold orange for working
                      color === 'green' ? '\x1b[1;92m' :   // Bold bright green for ready
                      color === 'cyan' ? '\x1b[1;96m' :    // Bold bright cyan for pending
                      color === 'blue' ? '\x1b[1;94m' : '\x1b[1;97m'; // Bold bright colors
      
      return {
        uri: `agent://${agent.agent_id}`,
        name: `${ansiCode}@${agent.agent_id}\x1b[0m`,
        description: `${ansiCode}${description}\x1b[0m`,
        mimeType: 'application/json',
        annotations: {
          color,
          type: 'agent',
          status,
          priority: color === 'yellow' ? 'high' : 'normal',
          category: 'automation'
        }
      };
    });
  } catch (error) {
    console.error('Error fetching agent resources:', error);
    return [];
  }
}

/**
 * Get detailed agent information as resource content
 */
export async function getAgentResourceContent(agentId: string): Promise<AgentResourceContent | null> {
  const db = getDbConnection();
  
  try {
    // Get agent basic info
    const agentStmt = db.prepare(`
      SELECT a.*, t.title as current_task_title, t.description as current_task_description, t.status as current_task_status
      FROM agents a
      LEFT JOIN tasks t ON a.current_task = t.task_id
      WHERE a.agent_id = ?
    `);
    
    const agent = agentStmt.get(agentId) as any;
    
    if (!agent) {
      return null;
    }
    
    // Get all tasks for this agent
    const tasksStmt = db.prepare(`
      SELECT task_id, title, description, status, priority, created_at, updated_at
      FROM tasks 
      WHERE assigned_to = ? 
      ORDER BY 
        CASE status 
          WHEN 'in_progress' THEN 1
          WHEN 'pending' THEN 2  
          WHEN 'completed' THEN 3
          WHEN 'failed' THEN 4
          WHEN 'cancelled' THEN 5
        END,
        updated_at DESC
    `);
    
    const tasks = tasksStmt.all(agentId);
    
    // Get recent actions
    const actionsStmt = db.prepare(`
      SELECT action_type, timestamp, details
      FROM agent_actions 
      WHERE agent_id = ? 
      ORDER BY timestamp DESC 
      LIMIT 5
    `);
    
    const recentActions = actionsStmt.all(agentId);
    
    const tmuxSessionName = `${agent.agent_id}-148f`;
    
    const agentSummary = {
      "\x1b[96m🤖 Agent\x1b[0m (cyan)": `@${agent.agent_id}`,
      "\x1b[92m📊 Status\x1b[0m (green)": agent.status,
      "\x1b[93m🎯 Capabilities\x1b[0m (yellow)": agent.capabilities ? JSON.parse(agent.capabilities) : [],
      "\x1b[94m📁 Working Directory\x1b[0m (blue)": agent.working_directory,
      "\x1b[95m🕒 Created\x1b[0m (magenta)": new Date(agent.created_at).toLocaleString(),
      "─────────────────": "─────────────────",
      "\x1b[97m🔧 TMUX SESSION\x1b[0m (white)": "─────────────────",
      "Session Name": tmuxSessionName,
      "Connect Command": `tmux attach-session -t ${tmuxSessionName}`,
      "View Logs": `tmux capture-pane -t ${tmuxSessionName} -p`,
      "─────────────────1": "─────────────────",
      "\x1b[91m📋 CURRENT TASK\x1b[0m (red)": agent.current_task ? {
        "Task ID": agent.current_task,
        "Title": agent.current_task_title ? `\x1b[93m${agent.current_task_title}\x1b[0m (yellow)` : "No title",
        "Status": agent.current_task_status,
        "Description": agent.current_task_description
      } : "No current task assigned",
      "─────────────────2": "─────────────────",
      "\x1b[94m📝 ALL TASKS\x1b[0m (blue)": tasks.length > 0 ? tasks.map((task: any) => ({
        "ID": task.task_id,
        "Title": `\x1b[92m${task.title}\x1b[0m (green)`,
        "Status": `${getStatusEmoji(task.status)} ${task.status}`,
        "Priority": task.priority,
        "Updated": new Date(task.updated_at).toLocaleString()
      })) : "No tasks assigned",
      "─────────────────3": "─────────────────",
      "\x1b[95m🕐 RECENT ACTIVITY\x1b[0m (magenta)": recentActions.length > 0 ? recentActions.map((action: any) => ({
        "Action": action.action_type,
        "Time": new Date(action.timestamp).toLocaleString(),
        "Details": action.details || "No details"
      })) : "No recent activity"
    };
    
    return {
      uri: `agent://agent-mcp/${agentId}`,
      mimeType: 'application/json',
      text: JSON.stringify(agentSummary, null, 2)
    };
  } catch (error) {
    console.error(`Error fetching agent resource content for ${agentId}:`, error);
    return null;
  }
}

function getStatusEmoji(status: string): string {
  switch (status) {
    case 'in_progress': return '🔄';
    case 'completed': return '✅';
    case 'pending': return '📋';
    case 'failed': return '❌';
    case 'cancelled': return '🚫';
    default: return '❓';
  }
}

if (MCP_DEBUG) {
  console.log('✅ Agent resources module loaded');
}