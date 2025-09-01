// MCP Resources for Tasks
// Provides task data as MCP resources for @ mentions

import { getDbConnection } from '../db/connection.js';
import { MCP_DEBUG } from '../core/config.js';

export interface TaskResource {
  uri: string;
  name: string;
  description: string;
  mimeType: string;
  annotations?: any;
}

export interface TaskResourceContent {
  uri: string;
  mimeType: string;
  text: string;
}

/**
 * Get all tasks as resources (including create-task template)
 */
export async function getTaskResources(): Promise<TaskResource[]> {
  const db = getDbConnection();
  const resources: TaskResource[] = [];
  
  // Add create-task resource first
  resources.push({
    uri: 'create://task',
    name: '\x1b[1;92m@create-task\x1b[0m',
    description: '\x1b[1;92m➕ Create new task/todo\x1b[0m',
    mimeType: 'text/markdown',
    annotations: {
      type: 'create-task',
      category: 'tasks'
    }
  });
  
  try {
    // Get active tasks from database
    const stmt = db.prepare(`
      SELECT 
        t.task_id,
        t.title,
        t.status,
        t.priority,
        t.assigned_to,
        t.parent_task,
        (SELECT COUNT(*) FROM tasks WHERE parent_task = t.task_id) as subtask_count
      FROM tasks t
      WHERE t.status IN ('pending', 'in_progress')
      ORDER BY 
        CASE t.status 
          WHEN 'in_progress' THEN 1
          WHEN 'pending' THEN 2
        END,
        CASE t.priority
          WHEN 'high' THEN 1
          WHEN 'medium' THEN 2
          WHEN 'low' THEN 3
        END,
        t.created_at DESC
      LIMIT 50
    `);
    
    const tasks = stmt.all();
    
    tasks.forEach((task: any) => {
      // Color based on status and priority
      let color = 'white';
      let emoji = '📋';
      
      if (task.status === 'in_progress') {
        color = task.priority === 'high' ? '\x1b[1;91m' : // Red for high priority in progress
                task.priority === 'medium' ? '\x1b[1;93m' : // Yellow for medium
                '\x1b[1;92m'; // Green for low
        emoji = '🔄';
      } else { // pending
        color = task.priority === 'high' ? '\x1b[1;95m' : // Magenta for high priority pending
                task.priority === 'medium' ? '\x1b[1;96m' : // Cyan for medium
                '\x1b[1;37m'; // White for low
        emoji = '⏳';
      }
      
      // Compact description
      const assignee = task.assigned_to ? `@${task.assigned_to}` : 'unassigned';
      const subtasks = task.subtask_count > 0 ? ` • ${task.subtask_count} subtasks` : '';
      const description = `${color}${emoji} ${task.status} • ${task.priority} • ${assignee}${subtasks}\x1b[0m`;
      
      resources.push({
        uri: `task://${task.task_id}`,
        name: `${color}@task-${task.task_id}\x1b[0m`,
        description,
        mimeType: 'application/json',
        annotations: {
          type: 'task',
          status: task.status,
          priority: task.priority,
          category: 'tasks'
        }
      });
    });
  } catch (error) {
    console.error('Error fetching task resources:', error);
  }
  
  return resources;
}

/**
 * Get detailed task information as resource content
 */
export async function getTaskResourceContent(uri: string): Promise<TaskResourceContent | null> {
  // Handle create-task template
  if (uri === 'create://task') {
    return {
      uri,
      mimeType: 'text/markdown',
      text: `# ➕ Create New Task

## Quick Create:
Just describe what needs to be done!

## Examples:
"Fix the login bug where users can't reset passwords"
"Add dark mode support to the settings page"
"Write tests for the new API endpoints"
"Review and refactor the database queries"

## Command:
\`\`\`javascript
assign_task({
  token: "@admin",
  task_title: "Your task title",
  task_description: "Detailed description",
  priority: "high", // high, medium, low
  agent_token: "@agent-name" // optional
})
\`\`\`

## For Subtasks:
\`\`\`javascript
create_self_task({
  token: "@agent-token",
  parent_task_id: "parent-id",
  task_title: "Subtask title",
  task_description: "Details"
})
\`\`\`

## Tips:
- Be specific about acceptance criteria
- Include any relevant context or links
- Set appropriate priority
- Assign to agent if ready to work
`
    };
  }
  
  // Handle regular task viewing
  const taskId = uri.replace('task://', '');
  const db = getDbConnection();
  
  try {
    const taskStmt = db.prepare(`
      SELECT 
        t.*,
        p.title as parent_title,
        a.agent_id as assigned_agent
      FROM tasks t
      LEFT JOIN tasks p ON t.parent_task = p.task_id
      LEFT JOIN agents a ON t.assigned_to = a.agent_id
      WHERE t.task_id = ?
    `);
    
    const task = taskStmt.get(taskId) as any;
    
    if (!task) {
      return null;
    }
    
    // Get subtasks
    const subtasksStmt = db.prepare(`
      SELECT task_id, title, status, priority
      FROM tasks
      WHERE parent_task = ?
      ORDER BY created_at
    `);
    
    const subtasks = subtasksStmt.all(taskId);
    
    // Get task dependencies
    const depsStmt = db.prepare(`
      SELECT dt.task_id, dt.title, dt.status
      FROM task_dependencies td
      JOIN tasks dt ON td.depends_on_task_id = dt.task_id
      WHERE td.task_id = ?
    `);
    
    const dependencies = depsStmt.all(taskId);
    
    // Build task summary
    const taskSummary = {
      "📋 Task": task.task_id,
      "📌 Title": task.title,
      "📝 Description": task.description,
      "─────────────────": "─────────────────",
      "📊 Status": getStatusEmoji(task.status) + ' ' + task.status,
      "🎯 Priority": task.priority,
      "👤 Assigned To": task.assigned_to || 'Unassigned',
      "🏷️ Created By": task.created_by || 'System',
      "📅 Created": new Date(task.created_at).toLocaleString(),
      "🔄 Updated": new Date(task.updated_at).toLocaleString(),
      "─────────────────1": "─────────────────",
      "🔗 Parent Task": task.parent_title ? `${task.parent_task}: ${task.parent_title}` : 'None (Root Task)',
      "📦 Subtasks": subtasks.length > 0 ? subtasks.map((st: any) => ({
        "ID": st.task_id,
        "Title": st.title,
        "Status": getStatusEmoji(st.status) + ' ' + st.status
      })) : 'No subtasks',
      "🔒 Dependencies": dependencies.length > 0 ? dependencies.map((dep: any) => ({
        "ID": dep.task_id,
        "Title": dep.title,
        "Status": getStatusEmoji(dep.status) + ' ' + dep.status
      })) : 'No dependencies',
      "─────────────────2": "─────────────────",
      "💡 Notes": task.notes || 'No notes'
    };
    
    return {
      uri,
      mimeType: 'application/json',
      text: JSON.stringify(taskSummary, null, 2)
    };
  } catch (error) {
    console.error(`Error fetching task resource content for ${taskId}:`, error);
    return null;
  }
}

function getStatusEmoji(status: string): string {
  switch (status) {
    case 'in_progress': return '🔄';
    case 'completed': return '✅';
    case 'pending': return '⏳';
    case 'failed': return '❌';
    case 'cancelled': return '🚫';
    default: return '❓';
  }
}

if (MCP_DEBUG) {
  console.log('✅ Task resources module loaded');
}