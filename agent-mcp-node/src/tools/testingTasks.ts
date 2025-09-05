// Testing Tasks - Proper task creation and access for testing agents
// Ensures testing agents can audit all work done by the original agent

import { z } from 'zod';
import { getDbConnection } from '../db/connection.js';
import { MCP_DEBUG } from '../core/config.js';

/**
 * Create a comprehensive testing task when an agent completes work
 * This gives the testing agent full visibility into what was done
 */
export const createTestingTask = {
  name: 'create_testing_task',
  description: 'Create a testing task with full access to original work',
  inputSchema: z.object({
    completed_task_id: z.string().describe('The task that was just completed'),
    completed_by_agent: z.string().describe('Agent who completed the task'),
    testing_agent_id: z.string().describe('Testing agent who will audit the work'),
    admin_token: z.string().describe('Admin token for task creation')
  }),
  async execute(args: any) {
    const { completed_task_id, completed_by_agent, testing_agent_id, admin_token } = args;
    const db = getDbConnection();
    
    try {
      // 1. Get the completed task details
      const completedTask = db.prepare(`
        SELECT * FROM tasks WHERE task_id = ?
      `).get(completed_task_id) as any;
      
      if (!completedTask) {
        throw new Error(`Completed task ${completed_task_id} not found`);
      }
      
      // 2. Get all subtasks created by the original agent
      const subtasks = db.prepare(`
        SELECT task_id, title, description, status, created_at, updated_at
        FROM tasks 
        WHERE parent_task = ? OR created_by = ?
        ORDER BY created_at DESC
      `).all(completed_task_id, completed_by_agent);
      
      // 3. Get all context entries created/modified by the original agent
      const contextEntries = db.prepare(`
        SELECT context_key, value as context_value, description, last_updated
        FROM project_context
        WHERE JSON_EXTRACT(value, '$.created_by') = ? 
           OR JSON_EXTRACT(value, '$.modified_by') = ?
           OR context_key LIKE ?
        ORDER BY last_updated DESC
        LIMIT 50
      `).all(completed_by_agent, completed_by_agent, `%${completed_task_id}%`);
      
      // 4. Get all files modified (from file_status if tracked)
      const modifiedFiles = db.prepare(`
        SELECT filepath, status, notes, updated_at
        FROM file_status
        WHERE agent_id = ? AND updated_at > datetime('now', '-1 hour')
        ORDER BY updated_at DESC
      `).all(completed_by_agent);
      
      // 5. Get agent actions/logs
      const agentActions = db.prepare(`
        SELECT action_type, timestamp, details
        FROM agent_actions
        WHERE agent_id = ? 
          AND timestamp > datetime('now', '-1 hour')
        ORDER BY timestamp DESC
        LIMIT 100
      `).all(completed_by_agent);
      
      // 6. Create comprehensive testing task
      const testingTaskId = `test-${completed_task_id}`;
      const testingTaskTitle = `Test: ${completedTask.title}`;
      const testingTaskDescription = `
## Testing Task for ${completed_task_id}

### Original Task
- **Title**: ${completedTask.title}
- **Description**: ${completedTask.description}
- **Completed By**: ${completed_by_agent}
- **Status**: ${completedTask.status}

### Work Done by ${completed_by_agent}

#### Subtasks Created (${subtasks.length})
${subtasks.map((st: any) => `- ${st.task_id}: ${st.title} (${st.status})`).join('\n')}

#### Context Entries Modified (${contextEntries.length})
${contextEntries.slice(0, 10).map((ce: any) => `- ${ce.context_key}: ${ce.description || 'No description'}`).join('\n')}
${contextEntries.length > 10 ? `... and ${contextEntries.length - 10} more` : ''}

#### Files Modified (${modifiedFiles.length})
${modifiedFiles.map((f: any) => `- ${f.filepath}: ${f.notes || 'No notes'}`).join('\n')}

#### Recent Actions (${agentActions.length})
${agentActions.slice(0, 20).map((a: any) => `- ${a.action_type}: ${a.details || 'No details'}`).join('\n')}
${agentActions.length > 20 ? `... and ${agentActions.length - 20} more` : ''}

### Testing Requirements
1. **Verify Implementation**: Check that all requirements from original task are met
2. **Test Functionality**: Ensure all features work as expected
3. **Check Integration**: Verify integration with existing code
4. **Review Code Quality**: Check for best practices, error handling
5. **Validate Context**: Ensure project context is accurate and complete
6. **Edge Cases**: Test edge cases and error conditions

### Access Information
- You have full access to all tasks, context, and files
- Use \`view_tasks\` to see all related tasks
- Use \`view_project_context\` to audit context entries
- Use \`check_file_status\` to see what files were modified
- Use \`ask_project_rag\` to understand the implementation

### Response Protocol
- ✅ If tests pass: Update this task to 'completed' with notes
- ❌ If tests fail: 
  1. Update original task ${completed_task_id} to 'in_progress'
  2. Create subtasks for fixes needed
  3. Send detailed feedback to ${completed_by_agent}
`;
      
      // Check if testing task already exists
      const existingTestTask = db.prepare('SELECT task_id FROM tasks WHERE task_id = ?').get(testingTaskId);
      
      if (existingTestTask) {
        // Update existing test task
        db.prepare(`
          UPDATE tasks 
          SET description = ?, status = 'pending', updated_at = CURRENT_TIMESTAMP
          WHERE task_id = ?
        `).run(testingTaskDescription, testingTaskId);
      } else {
        // Create new testing task
        db.prepare(`
          INSERT INTO tasks (
            task_id, title, description, assigned_to, created_by,
            status, priority, parent_task, created_at, updated_at
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        `).run(
          testingTaskId,
          testingTaskTitle,
          testingTaskDescription,
          testing_agent_id,
          'system',
          'pending',
          'high',
          completed_task_id
        );
      }
      
      // 7. Grant testing agent access to all related context
      const accessGrant = {
        testing_agent: testing_agent_id,
        original_agent: completed_by_agent,
        completed_task: completed_task_id,
        access_granted: new Date().toISOString(),
        permissions: ['read_all_tasks', 'read_all_context', 'modify_task_status', 'create_tasks']
      };
      
      db.prepare(`
        INSERT OR REPLACE INTO project_context (context_key, value, description, last_updated, updated_by)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?)
      `).run(
        `testing_access_${testing_agent_id}`,
        JSON.stringify(accessGrant),
        `Testing access grant for ${testing_agent_id} to audit ${completed_by_agent}'s work`,
        'testing_system'
      );
      
      console.log(`✅ Created comprehensive testing task ${testingTaskId} for ${testing_agent_id}`);
      
      return {
        success: true,
        testing_task_id: testingTaskId,
        subtasks_found: subtasks.length,
        context_entries_found: contextEntries.length,
        files_modified: modifiedFiles.length,
        actions_logged: agentActions.length
      };
      
    } catch (error) {
      console.error('Error creating testing task:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : String(error)
      };
    }
  }
};

/**
 * Get audit report for testing agent
 * Shows all changes made by an agent for a specific task
 */
export const getAuditReport = {
  name: 'get_audit_report',
  description: 'Get comprehensive audit report of agent work',
  inputSchema: z.object({
    agent_id: z.string().describe('Agent whose work to audit'),
    task_id: z.string().optional().describe('Specific task to audit'),
    hours_back: z.number().default(1).describe('How many hours back to look')
  }),
  async execute(args: any) {
    const { agent_id, task_id, hours_back = 1 } = args;
    const db = getDbConnection();
    
    try {
      const report: any = {
        agent: agent_id,
        task: task_id || 'all',
        period: `Last ${hours_back} hour(s)`,
        timestamp: new Date().toISOString()
      };
      
      // Get tasks worked on
      const tasksQuery = task_id ? 
        `SELECT * FROM tasks WHERE (assigned_to = ? OR created_by = ?) AND task_id = ?` :
        `SELECT * FROM tasks WHERE (assigned_to = ? OR created_by = ?) AND updated_at > datetime('now', '-${hours_back} hours')`;
      
      const tasks = task_id ?
        db.prepare(tasksQuery).all(agent_id, agent_id, task_id) :
        db.prepare(tasksQuery).all(agent_id, agent_id);
      
      report.tasks = {
        total: tasks.length,
        by_status: {},
        details: tasks.map((t: any) => ({
          id: t.task_id,
          title: t.title,
          status: t.status,
          updated: t.updated_at
        }))
      };
      
      // Count by status
      tasks.forEach((t: any) => {
        report.tasks.by_status[t.status] = (report.tasks.by_status[t.status] || 0) + 1;
      });
      
      // Get context changes
      const contextChanges = db.prepare(`
        SELECT context_key, value as context_value, description, last_updated
        FROM project_context
        WHERE (JSON_EXTRACT(value, '$.created_by') = ? 
           OR JSON_EXTRACT(value, '$.modified_by') = ?
           OR JSON_EXTRACT(value, '$.agent_id') = ?)
          AND last_updated > datetime('now', '-${hours_back} hours')
        ORDER BY last_updated DESC
      `).all(agent_id, agent_id, agent_id);
      
      report.context_changes = {
        total: contextChanges.length,
        entries: contextChanges.map((c: any) => ({
          key: c.context_key,
          description: c.description,
          updated: c.last_updated,
          size: c.context_value ? c.context_value.length : 0
        }))
      };
      
      // Get file modifications
      const fileChanges = db.prepare(`
        SELECT filepath, status, notes, updated_at
        FROM file_status
        WHERE agent_id = ? 
          AND updated_at > datetime('now', '-${hours_back} hours')
        ORDER BY updated_at DESC
      `).all(agent_id);
      
      report.file_changes = {
        total: fileChanges.length,
        files: fileChanges.map((f: any) => ({
          path: f.filepath,
          status: f.status,
          notes: f.notes,
          updated: f.updated_at
        }))
      };
      
      // Get agent actions
      const actions = db.prepare(`
        SELECT action_type, timestamp, details
        FROM agent_actions
        WHERE agent_id = ? 
          AND timestamp > datetime('now', '-${hours_back} hours')
        ORDER BY timestamp DESC
      `).all(agent_id);
      
      report.actions = {
        total: actions.length,
        by_type: {},
        recent: actions.slice(0, 50).map((a: any) => ({
          type: a.action_type,
          time: a.timestamp,
          details: a.details
        }))
      };
      
      // Count by action type
      actions.forEach((a: any) => {
        report.actions.by_type[a.action_type] = (report.actions.by_type[a.action_type] || 0) + 1;
      });
      
      // Generate summary
      report.summary = {
        total_changes: report.tasks.total + report.context_changes.total + report.file_changes.total,
        completed_tasks: report.tasks.by_status.completed || 0,
        pending_tasks: report.tasks.by_status.pending || 0,
        in_progress_tasks: report.tasks.by_status.in_progress || 0,
        recommendation: report.tasks.by_status.completed > 0 ? 'Ready for testing' : 'Work in progress'
      };
      
      if (MCP_DEBUG) {
        console.log(`📊 Generated audit report for ${agent_id}:`, report.summary);
      }
      
      return {
        success: true,
        report
      };
      
    } catch (error) {
      console.error('Error generating audit report:', error);
      return {
        success: false,
        error: error instanceof Error ? error.message : String(error)
      };
    }
  }
};

export const testingTaskTools = [createTestingTask, getAuditReport];