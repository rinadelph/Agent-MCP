// Task management tools for Agent-MCP Node.js  
// Ported from Python task_tools.py (view_tasks, update_task_status functions)

import { z } from 'zod';
import { registerTool } from '../registry.js';
import { getDbConnection } from '../../db/connection.js';
import { MCP_DEBUG } from '../../core/config.js';
import { verifyToken, getAgentId } from '../../core/auth.js';
import { 
  formatTaskSummary, 
  formatTaskDetailed, 
  formatTaskWithDependencies,
  calculateTaskHealthMetrics,
  logTaskAction,
  validateTaskStatus 
} from './core.js';

// Helper function to get agent ID from token
function getAgentIdFromToken(token: string): string | null {
  const db = getDbConnection();
  
  try {
    const agent = db.prepare('SELECT agent_id FROM agents WHERE token = ?').get(token);
    return agent ? (agent as any).agent_id : null;
  } catch (error) {
    console.error('Error getting agent ID:', error);
    return null;
  }
}

// Helper function to verify admin access
function verifyAdminToken(token?: string): boolean {
  if (!token) return false;
  return verifyToken(token, 'admin');
}

// View Tasks Tool
registerTool(
  'view_tasks',
  'View tasks with filtering, sorting and detailed information. Supports multiple display formats.',
  z.object({
    token: z.string().optional().describe('Agent or admin authentication token (optional - uses session context)'),
    
    // Filtering options
    filter_agent_id: z.string().optional().describe('Filter tasks by assigned agent ID'),
    filter_status: z.enum(['pending', 'in_progress', 'completed', 'cancelled', 'failed']).optional().describe('Filter by task status'),
    filter_priority: z.enum(['low', 'medium', 'high']).optional().describe('Filter by task priority'),
    filter_created_by: z.string().optional().describe('Filter by task creator'),
    filter_parent_task: z.string().optional().describe('Filter by parent task ID'),
    filter_has_dependencies: z.boolean().optional().describe('Filter tasks that have dependencies'),
    
    // Date filtering
    filter_created_after: z.string().optional().describe('Filter tasks created after date (ISO format)'),
    filter_created_before: z.string().optional().describe('Filter tasks created before date (ISO format)'),
    filter_updated_after: z.string().optional().describe('Filter tasks updated after date (ISO format)'),
    
    // Text search
    search_text: z.string().optional().describe('Search in task titles and descriptions'),
    
    // Display options
    display_mode: z.enum(['summary', 'detailed', 'with_dependencies']).default('summary').describe('Display format'),
    include_completed: z.boolean().default(false).describe('Include completed tasks'),
    include_cancelled: z.boolean().default(false).describe('Include cancelled tasks'),
    
    // Sorting and pagination
    sort_by: z.enum(['created_at', 'updated_at', 'priority', 'status', 'title']).default('updated_at').describe('Sort field'),
    sort_order: z.enum(['asc', 'desc']).default('desc').describe('Sort order'),
    limit: z.number().min(1).max(200).default(50).describe('Maximum number of tasks to return'),
    offset: z.number().min(0).default(0).describe('Number of tasks to skip for pagination'),
    
    // Health metrics
    include_health_metrics: z.boolean().default(false).describe('Include overall task health metrics')
  }),
  async (args, context) => {
    const {
      token,
      filter_agent_id,
      filter_status,
      filter_priority,
      filter_created_by,
      filter_parent_task,
      filter_has_dependencies,
      filter_created_after,
      filter_created_before,
      filter_updated_after,
      search_text,
      display_mode = 'summary',
      include_completed = false,
      include_cancelled = false,
      sort_by = 'updated_at',
      sort_order = 'desc',
      limit = 50,
      offset = 0,
      include_health_metrics = false
    } = args;
    
    // Get requesting agent ID
    const requestingAgentId = getAgentIdFromToken(token);
    const isAdmin = verifyAdminToken(token);
    
    if (!requestingAgentId && !isAdmin) {
      return {
        content: [{
          type: 'text' as const,
          text: '❌ Unauthorized: Valid token required'
        }],
        isError: true
      };
    }
    
    const db = getDbConnection();
    
    try {
      // Build dynamic query
      let query = 'SELECT * FROM tasks WHERE 1=1';
      const params: any[] = [];
      
      // Apply permission filtering - non-admin agents can only see their own tasks or unassigned tasks
      if (!isAdmin && requestingAgentId) {
        query += ' AND (assigned_to = ? OR assigned_to IS NULL OR created_by = ?)';
        params.push(requestingAgentId, requestingAgentId);
      }
      
      // Apply filters
      if (filter_agent_id) {
        query += ' AND assigned_to = ?';
        params.push(filter_agent_id);
      }
      
      if (filter_status) {
        query += ' AND status = ?';
        params.push(filter_status);
      }
      
      if (filter_priority) {
        query += ' AND priority = ?';
        params.push(filter_priority);
      }
      
      if (filter_created_by) {
        query += ' AND created_by = ?';
        params.push(filter_created_by);
      }
      
      if (filter_parent_task) {
        query += ' AND parent_task = ?';
        params.push(filter_parent_task);
      }
      
      if (filter_has_dependencies !== undefined) {
        if (filter_has_dependencies) {
          query += " AND json_array_length(depends_on_tasks) > 0";
        } else {
          query += " AND (depends_on_tasks = '[]' OR depends_on_tasks IS NULL)";
        }
      }
      
      // Date filters
      if (filter_created_after) {
        query += ' AND created_at >= ?';
        params.push(filter_created_after);
      }
      
      if (filter_created_before) {
        query += ' AND created_at <= ?';
        params.push(filter_created_before);
      }
      
      if (filter_updated_after) {
        query += ' AND updated_at >= ?';
        params.push(filter_updated_after);
      }
      
      // Text search
      if (search_text) {
        query += ' AND (title LIKE ? OR description LIKE ?)';
        const searchPattern = `%${search_text}%`;
        params.push(searchPattern, searchPattern);
      }
      
      // Status exclusions
      if (!include_completed) {
        query += " AND status != 'completed'";
      }
      
      if (!include_cancelled) {
        query += " AND status NOT IN ('cancelled', 'failed')";
      }
      
      // Sorting
      const validSortFields = ['created_at', 'updated_at', 'priority', 'status', 'title'];
      const sortField = validSortFields.includes(sort_by) ? sort_by : 'updated_at';
      const sortDirection = sort_order === 'asc' ? 'ASC' : 'DESC';
      
      query += ` ORDER BY ${sortField} ${sortDirection}`;
      
      // Pagination
      query += ' LIMIT ? OFFSET ?';
      params.push(limit, offset);
      
      // Execute query
      const tasks = db.prepare(query).all(...params);
      
      // Get total count for pagination info
      let countQuery = query.replace(/SELECT \* FROM/, 'SELECT COUNT(*) as total FROM');
      countQuery = countQuery.replace(/ORDER BY.*$/, '');
      countQuery = countQuery.replace(/LIMIT.*$/, '');
      
      const countResult = db.prepare(countQuery).get(...params.slice(0, -2)); // Remove limit/offset params
      const totalCount = (countResult as any)?.total || 0;
      
      // Format response
      const response: string[] = [];
      
      if (include_health_metrics && isAdmin) {
        const allTasks = db.prepare('SELECT * FROM tasks').all();
        const healthMetrics = calculateTaskHealthMetrics(allTasks);
        
        response.push('📊 **Task Health Metrics**');
        response.push('');
        response.push(`**Overall Status:**`);
        response.push(`- Total Tasks: ${healthMetrics.totalTasks}`);
        response.push(`- Recent Activity: ${healthMetrics.recentActivity} tasks updated in last 24h`);
        response.push(`- Overdue Tasks: ${healthMetrics.overdueCount}`);
        response.push('');
        response.push(`**By Status:**`);
        Object.entries(healthMetrics.byStatus).forEach(([status, count]) => {
          response.push(`- ${status}: ${count}`);
        });
        response.push('');
        response.push(`**By Priority:**`);
        Object.entries(healthMetrics.byPriority).forEach(([priority, count]) => {
          response.push(`- ${priority}: ${count}`);
        });
        response.push('');
        response.push('─'.repeat(50));
        response.push('');
      }
      
      response.push(`🎯 **Task List** (${tasks.length} of ${totalCount} total)`);
      response.push('');
      
      if (tasks.length === 0) {
        response.push('No tasks found matching the specified criteria.');
        
        // Provide helpful suggestions
        if (filter_status || filter_priority || search_text) {
          response.push('');
          response.push('💡 **Suggestions:**');
          response.push('- Try removing some filters');
          response.push('- Check if tasks exist with different status/priority');
          response.push('- Use search_text for broader text matching');
        }
      } else {
        // Display tasks based on mode
        tasks.forEach((task: any, index: number) => {
          switch (display_mode) {
            case 'detailed':
              response.push(formatTaskDetailed(task));
              break;
            case 'with_dependencies':
              response.push(formatTaskWithDependencies(task));
              break;
            default: // summary
              response.push(formatTaskSummary(task));
              break;
          }
          
          if (index < tasks.length - 1) {
            response.push('');
          }
        });
        
        // Pagination info
        if (totalCount > limit) {
          response.push('');
          response.push('─'.repeat(30));
          response.push(`📄 **Pagination:** Showing ${offset + 1}-${Math.min(offset + limit, totalCount)} of ${totalCount}`);
          
          if (offset + limit < totalCount) {
            response.push(`💡 Use offset=${offset + limit} to see next ${limit} tasks`);
          }
        }
      }
      
      // Applied filters summary
      if (Object.keys(args).some(key => key.startsWith('filter_') && args[key] !== undefined)) {
        response.push('');
        response.push('🔍 **Active Filters:**');
        
        if (filter_agent_id) response.push(`- Agent: ${filter_agent_id}`);
        if (filter_status) response.push(`- Status: ${filter_status}`);
        if (filter_priority) response.push(`- Priority: ${filter_priority}`);
        if (filter_created_by) response.push(`- Created by: ${filter_created_by}`);
        if (filter_parent_task) response.push(`- Parent: ${filter_parent_task}`);
        if (search_text) response.push(`- Search: "${search_text}"`);
      }
      
      return {
        content: [{
          type: 'text' as const,
          text: response.join('\n')
        }]
      };
      
    } catch (error) {
      console.error('Error viewing tasks:', error);
      return {
        content: [{
          type: 'text' as const,
          text: `❌ Error retrieving tasks: ${error instanceof Error ? error.message : String(error)}`
        }],
        isError: true
      };
    }
  }
);

// Update Task Status Tool
registerTool(
  'update_task_status',
  'Update the status of one or more tasks. Agents can update their own tasks, admins can update any task.',
  z.object({
    token: z.string().describe('Agent or admin authentication token'),
    task_id: z.string().optional().describe('Single task ID to update'),
    task_ids: z.array(z.string()).optional().describe('Multiple task IDs to update'),
    new_status: z.enum(['pending', 'in_progress', 'completed', 'cancelled', 'failed']).describe('New status for the task(s)'),
    notes: z.string().optional().describe('Optional notes about the status change'),
    
    // Additional update fields (optional)
    new_title: z.string().optional().describe('New title for the task'),
    new_description: z.string().optional().describe('New description for the task'),
    new_priority: z.enum(['low', 'medium', 'high']).optional().describe('New priority for the task'),
    new_assigned_to: z.string().optional().describe('New agent assignment (admin only)'),
    
    // Completion metadata
    completion_notes: z.string().optional().describe('Notes for completed tasks'),
    estimated_hours: z.number().optional().describe('Actual hours worked (for analytics)')
  }),
  async (args, context) => {
    const {
      token,
      task_id,
      task_ids,
      new_status,
      notes,
      new_title,
      new_description,
      new_priority,
      new_assigned_to,
      completion_notes,
      estimated_hours
    } = args;
    
    // Get requesting agent ID
    const requestingAgentId = getAgentIdFromToken(token);
    const isAdmin = verifyAdminToken(token);
    
    if (!requestingAgentId && !isAdmin) {
      return {
        content: [{
          type: 'text' as const,
          text: '❌ Unauthorized: Valid token required'
        }],
        isError: true
      };
    }
    
    // Validate status
    if (!validateTaskStatus(new_status)) {
      return {
        content: [{
          type: 'text' as const,
          text: '❌ Error: Invalid status. Must be one of: pending, in_progress, completed, cancelled, failed'
        }],
        isError: true
      };
    }
    
    // Determine task IDs to update
    let targetTaskIds: string[];
    if (task_id) {
      targetTaskIds = [task_id];
    } else if (task_ids && task_ids.length > 0) {
      targetTaskIds = task_ids;
    } else {
      return {
        content: [{
          type: 'text' as const,
          text: '❌ Error: Must provide either task_id or task_ids'
        }],
        isError: true
      };
    }
    
    const db = getDbConnection();
    const results: string[] = [];
    const timestamp = new Date().toISOString();
    
    try {
      const transaction = db.transaction(() => {
        for (const taskId of targetTaskIds) {
          // Get current task data
          const task = db.prepare('SELECT * FROM tasks WHERE task_id = ?').get(taskId);
          
          if (!task) {
            results.push(`❌ Task '${taskId}' not found`);
            continue;
          }
          
          const taskData = task as any;
          
          // Check permissions
          if (!isAdmin && taskData.assigned_to !== requestingAgentId) {
            results.push(`❌ Unauthorized: Cannot update task '${taskId}' assigned to ${taskData.assigned_to}`);
            continue;
          }
          
          // Build update query
          const updateFields = ['status = ?', 'updated_at = ?'];
          const updateParams = [new_status, timestamp];
          
          // Handle notes
          const currentNotes = JSON.parse(taskData.notes || '[]');
          if (notes || completion_notes) {
            const noteContent = notes || completion_notes || '';
            currentNotes.push({
              content: noteContent,
              timestamp,
              agent_id: requestingAgentId || 'admin'
            });
            updateFields.push('notes = ?');
            updateParams.push(JSON.stringify(currentNotes));
          }
          
          // Handle optional field updates
          if (new_title) {
            updateFields.push('title = ?');
            updateParams.push(new_title);
          }
          
          if (new_description) {
            updateFields.push('description = ?');
            updateParams.push(new_description);
          }
          
          if (new_priority) {
            updateFields.push('priority = ?');
            updateParams.push(new_priority);
          }
          
          if (new_assigned_to && isAdmin) {
            updateFields.push('assigned_to = ?');
            updateParams.push(new_assigned_to);
          }
          
          // Execute update
          const updateQuery = `UPDATE tasks SET ${updateFields.join(', ')} WHERE task_id = ?`;
          updateParams.push(taskId);
          
          const updateResult = db.prepare(updateQuery).run(...updateParams);
          
          if (updateResult.changes > 0) {
            results.push(`✅ Updated '${taskId}': ${taskData.title} → ${new_status}`);
            
            // Log the action
            logTaskAction(requestingAgentId || 'admin', 'updated_task_status', taskId, {
              old_status: taskData.status,
              new_status,
              notes: notes || completion_notes,
              estimated_hours
            });
            
            // Special handling for completion
            if (new_status === 'completed') {
              results.push(`  🎉 Task completed! ${completion_notes ? `Notes: ${completion_notes}` : ''}`);
            }
          } else {
            results.push(`⚠️ No changes made to task '${taskId}'`);
          }
        }
      });
      
      transaction();
      
      const response = [
        `📝 **Task Status Update Results**`,
        '',
        ...results
      ];
      
      if (targetTaskIds.length > 1) {
        const successCount = results.filter(r => r.startsWith('✅')).length;
        response.push('');
        response.push(`📊 **Summary:** ${successCount}/${targetTaskIds.length} tasks updated successfully`);
      }
      
      if (MCP_DEBUG) {
        console.log(`📝 ${requestingAgentId || 'admin'} updated ${targetTaskIds.length} task(s) to ${new_status}`);
      }
      
      return {
        content: [{
          type: 'text' as const,
          text: response.join('\n')
        }]
      };
      
    } catch (error) {
      console.error('Error updating task status:', error);
      return {
        content: [{
          type: 'text' as const,
          text: `❌ Error updating task status: ${error instanceof Error ? error.message : String(error)}`
        }],
        isError: true
      };
    }
  }
);

console.log('✅ Task management tools registered successfully');