// Task creation tools for Agent-MCP Node.js
// Ported from Python task_tools.py (assign_task and create_self_task functions)

import { z } from 'zod';
import { registerTool } from '../registry.js';
import { getDbConnection } from '../../db/connection.js';
import { MCP_DEBUG } from '../../core/config.js';
import { verifyToken, getAgentId, validateAgentToken } from '../../core/auth.js';
import { globalState } from '../../core/globals.js';
import { 
  generateTaskId, 
  logTaskAction, 
  validateTaskStatus, 
  validateTaskPriority,
  analyzeAgentWorkload 
} from './core.js';

// Create Self Task Tool (for agents to create subtasks)
registerTool(
  'create_self_task',
  'Create a subtask under current assignment. Agents can only create child tasks, never root tasks.',
  z.object({
    token: z.string().optional().describe('Agent authentication token (optional - uses session context)'),
    task_title: z.string().describe('Title of the task'),
    task_description: z.string().describe('Detailed description of the task'),
    priority: z.enum(['low', 'medium', 'high']).default('medium').describe('Task priority'),
    depends_on_tasks: z.array(z.string()).optional().describe('List of task IDs this task depends on'),
    parent_task_id: z.string().optional().describe('ID of the parent task (if not provided, uses current task)')
  }),
  async (args, context) => {
    const { token, task_title, task_description, priority, depends_on_tasks = [], parent_task_id } = args;
    
    // Get requesting agent ID from token or context
    let requestingAgentId: string | null = null;
    
    if (token) {
      requestingAgentId = getAgentId(token);
    } else {
      // For MCP connections, use session-based authentication
      // For now, default to 'admin' for testing - in production this would come from session context
      requestingAgentId = context.agentId || 'admin';
    }
    
    if (!requestingAgentId) {
      return {
        content: [{
          type: 'text' as const,
          text: '❌ Unauthorized: Valid agent token required or session not authenticated'
        }],
        isError: true
      };
    }
    
    // Validate required fields
    if (!task_title || !task_description) {
      return {
        content: [{
          type: 'text' as const,
          text: '❌ Error: task_title and task_description are required'
        }],
        isError: true
      };
    }
    
    const db = getDbConnection();
    
    try {
      // Determine parent task ID
      let actualParentTaskId = parent_task_id;
      
      if (!actualParentTaskId) {
        // Get agent's current task
        const agent = db.prepare('SELECT current_task FROM agents WHERE agent_id = ?').get(requestingAgentId);
        if (agent && (agent as any).current_task) {
          actualParentTaskId = (agent as any).current_task;
        }
      }
      
      // Agents can NEVER create root tasks
      if (requestingAgentId !== 'admin' && !actualParentTaskId) {
        // Find a suitable parent task suggestion
        const suggestedParent = db.prepare(`
          SELECT task_id, title FROM tasks 
          WHERE assigned_to = ? OR created_by = ?
          ORDER BY created_at DESC LIMIT 1
        `).get(requestingAgentId, requestingAgentId);
        
        let suggestionText = '';
        if (suggestedParent) {
          suggestionText = `\nSuggested parent: ${(suggestedParent as any).task_id} (${(suggestedParent as any).title})`;
        }
        
        return {
          content: [{
            type: 'text' as const,
            text: `❌ ERROR: Agents cannot create root tasks. Every task must have a parent.${suggestionText}\nPlease specify a parent_task_id.`
          }],
          isError: true
        };
      }
      
      // Phase-based task management: Only one active phase (root task) at a time
      if (!actualParentTaskId) {
        const rootCheck = db.prepare('SELECT task_id, title, status FROM tasks WHERE parent_task IS NULL ORDER BY created_at DESC LIMIT 1').get();
        
        if (rootCheck) {
          const existingPhase = rootCheck as any;
          
          // Check if current phase is complete using helper function
          if (!isPhaseComplete(db, existingPhase.task_id)) {
            // Get available parent tasks for suggestions
            const availableParents = getAvailableParentTasks(db, existingPhase.task_id);
            
            let suggestionText = '';
            if (availableParents.length > 0) {
              suggestionText = `\n\n💡 **Available Parent Tasks:**\n${availableParents.map((p: any) => `- ${p.task_id}: ${p.title}`).join('\n')}`;
            } else {
              suggestionText = `\n\n💡 **Create a parent task first:** Add a task with parent_task_id="${existingPhase.task_id}"`;
            }
            
            return {
              content: [{
                type: 'text' as const,
                text: `❌ **Cannot Start New Phase**\n\nPhase "${existingPhase.title}" (${existingPhase.task_id}) is still active with incomplete tasks.\n\n🎯 **Agent-MCP enforces focused work:** Complete the current phase before starting a new one.\n\n**To add work to current phase:** Specify a parent_task_id pointing to an existing task.${suggestionText}\n\n**To start new phase:** Complete all tasks in "${existingPhase.title}" first.`
              }],
              isError: true
            };
          } else {
            // Current phase is complete, allow new phase
            console.log(`✅ Phase "${existingPhase.title}" completed. Allowing new phase creation.`);
          }
        }
      }
      
      // Validate dependencies if provided
      for (const depTaskId of depends_on_tasks) {
        const depTask = db.prepare('SELECT task_id FROM tasks WHERE task_id = ?').get(depTaskId);
        if (!depTask) {
          return {
            content: [{
              type: 'text' as const,
              text: `❌ Error: Dependency task '${depTaskId}' not found`
            }],
            isError: true
          };
        }
      }
      
      // Generate task data
      const newTaskId = generateTaskId();
      const createdAt = new Date().toISOString();
      const status = 'pending';
      
      // Begin transaction
      const transaction = db.transaction(() => {
        // Insert new task
        const insertTask = db.prepare(`
          INSERT INTO tasks (
            task_id, title, description, assigned_to, created_by, status, priority,
            created_at, updated_at, parent_task, child_tasks, depends_on_tasks, notes
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        `);
        
        insertTask.run(
          newTaskId,
          task_title,
          task_description,
          requestingAgentId, // Self-assigned
          requestingAgentId,
          status,
          priority,
          createdAt,
          createdAt,
          actualParentTaskId,
          JSON.stringify([]), // Empty child tasks initially
          JSON.stringify(depends_on_tasks),
          JSON.stringify([])   // Empty notes initially
        );
        
        // Update parent task's child_tasks if parent exists
        if (actualParentTaskId) {
          const parentTask = db.prepare('SELECT child_tasks FROM tasks WHERE task_id = ?').get(actualParentTaskId);
          if (parentTask) {
            const childTasks = JSON.parse((parentTask as any).child_tasks || '[]');
            childTasks.push(newTaskId);
            
            const updateParent = db.prepare('UPDATE tasks SET child_tasks = ?, updated_at = ? WHERE task_id = ?');
            updateParent.run(JSON.stringify(childTasks), createdAt, actualParentTaskId);
          }
        }
        
        // Log task creation
        logTaskAction(requestingAgentId, 'created_self_task', newTaskId, {
          title: task_title,
          priority,
          parent_task: actualParentTaskId,
          depends_on_count: depends_on_tasks.length
        });
        
        return newTaskId;
      });
      
      const taskId = transaction();
      
      const response = [
        `✅ **Task '${taskId}' Created Successfully**`,
        '',
        `**Details:**`,
        `- Title: ${task_title}`,
        `- Priority: ${priority}`,
        `- Status: ${status}`,
        `- Assigned to: ${requestingAgentId} (self)`,
        `- Created by: ${requestingAgentId}`,
        ''
      ];
      
      if (actualParentTaskId) {
        response.push(`**Parent Task:** ${actualParentTaskId}`);
      }
      
      if (depends_on_tasks.length > 0) {
        response.push(`**Dependencies:** ${depends_on_tasks.join(', ')}`);
      }
      
      response.push('', '🎯 Task is ready for work');
      
      if (MCP_DEBUG) {
        console.log(`📝 Agent ${requestingAgentId} created self-task: ${taskId}`);
      }
      
      return {
        content: [{
          type: 'text' as const,
          text: response.join('\n')
        }]
      };
      
    } catch (error) {
      console.error(`Error creating self-task for agent ${requestingAgentId}:`, error);
      return {
        content: [{
          type: 'text' as const,
          text: `❌ Error creating task: ${error instanceof Error ? error.message : String(error)}`
        }],
        isError: true
      };
    }
  }
);

// Assign Task Tool (admin tool for creating and assigning tasks)
registerTool(
  'assign_task',
  'Admin tool to create and assign tasks to agents. Supports single task, multiple tasks, or assigning existing tasks.',
  z.object({
    token: z.string().describe('Admin authentication token'),
    agent_token: z.string().optional().describe('Agent token to assign task(s) to (if not provided, creates unassigned tasks)'),
    
    // Mode 1: Single task creation
    task_title: z.string().optional().describe('Title of the task (for single task creation)'),
    task_description: z.string().optional().describe('Description of the task (for single task creation)'),
    priority: z.enum(['low', 'medium', 'high']).default('medium').describe('Task priority (for single task)'),
    depends_on_tasks: z.array(z.string()).optional().describe('List of task IDs this task depends on'),
    parent_task_id: z.string().optional().describe('ID of the parent task'),
    
    // Mode 2: Multiple task creation
    tasks: z.array(z.object({
      title: z.string().describe('Task title'),
      description: z.string().describe('Task description'),
      priority: z.enum(['low', 'medium', 'high']).default('medium').describe('Task priority'),
      depends_on_tasks: z.array(z.string()).optional().describe('Dependencies for this task'),
      parent_task_id: z.string().optional().describe('Parent task for this task')
    })).optional().describe('Array of tasks to create and assign'),
    
    // Mode 3: Existing task assignment
    task_ids: z.array(z.string()).optional().describe('List of existing task IDs to assign to agent'),
    
    // Options
    validate_agent_workload: z.boolean().default(true).describe('Check agent capacity before assignment'),
    coordination_notes: z.string().optional().describe('Optional coordination context'),
    estimated_hours: z.number().optional().describe('Estimated hours for workload calculation')
  }),
  async (args, context) => {
    const { 
      token, 
      agent_token, 
      task_title, 
      task_description, 
      priority = 'medium',
      depends_on_tasks = [],
      parent_task_id,
      tasks,
      task_ids,
      validate_agent_workload = true,
      coordination_notes,
      estimated_hours
    } = args;
    
    // Verify admin authentication
    if (!verifyToken(token || '', 'admin')) {
      return {
        content: [{
          type: 'text' as const,
          text: '❌ Unauthorized: Admin token required'
        }],
        isError: true
      };
    }
    
    // Handle unassigned task creation
    if (!agent_token) {
      return createUnassignedTasks(args);
    }
    
    // Validate agent
    const targetAgentId = getAgentId(agent_token);
    if (!targetAgentId) {
      return {
        content: [{
          type: 'text' as const,
          text: '❌ Error: Agent token not found. Agent may not exist or token is invalid.'
        }],
        isError: true
      };
    }
    
    // Prevent admin agents from being assigned tasks
    if (targetAgentId.toLowerCase().startsWith('admin')) {
      return {
        content: [{
          type: 'text' as const,
          text: '❌ Error: Admin agents cannot be assigned tasks. Admin agents are for coordination and management only.'
        }],
        isError: true
      };
    }
    
    // Determine operation mode
    let operationMode: 'single' | 'multiple' | 'existing';
    
    if (task_ids && task_ids.length > 0) {
      operationMode = 'existing';
    } else if (tasks && tasks.length > 0) {
      operationMode = 'multiple';
    } else if (task_title && task_description) {
      operationMode = 'single';
    } else {
      return {
        content: [{
          type: 'text' as const,
          text: '❌ Error: Must provide either task_title & task_description (single), tasks array (multiple), or task_ids (existing assignment)'
        }],
        isError: true
      };
    }
    
    // Validate agent workload if requested
    if (validate_agent_workload) {
      const workload = analyzeAgentWorkload(targetAgentId);
      if (workload.workloadScore > 15) {
        return {
          content: [{
            type: 'text' as const,
            text: `⚠️ Warning: Agent ${targetAgentId} has high workload (score: ${workload.workloadScore}). Consider redistributing tasks or assign to different agent.\n\nWorkload Details:\n- Active tasks: ${(workload.tasksByStatus.pending || 0) + (workload.tasksByStatus.in_progress || 0)}\n- High priority tasks: ${workload.tasksByPriority.high || 0}\n\nRecommendations:\n${workload.recommendations.join('\n')}`
          }]
        };
      }
    }
    
    // Route to appropriate handler
    switch (operationMode) {
      case 'existing':
        return assignExistingTasks(targetAgentId, task_ids!, coordination_notes);
      case 'multiple':
        return createMultipleTasks(targetAgentId, tasks!, coordination_notes);
      case 'single':
        return createSingleTask(targetAgentId, {
          title: task_title!,
          description: task_description!,
          priority,
          depends_on_tasks,
          parent_task_id
        }, coordination_notes);
    }
  }
);

// Helper functions for different assignment modes
function createUnassignedTasks(args: any) {
  const { 
    task_title, 
    task_description, 
    priority = 'medium',
    depends_on_tasks = [],
    parent_task_id,
    tasks
  } = args;
  
  const db = getDbConnection();
  const results: string[] = [];
  const createdTasks: string[] = [];
  
  try {
    const transaction = db.transaction(() => {
      // Handle single task creation
      if (task_title && task_description) {
        const taskId = createSingleUnassignedTask({
          title: task_title,
          description: task_description,
          priority,
          depends_on_tasks,
          parent_task_id
        });
        
        if (taskId) {
          createdTasks.push(taskId);
          results.push(`✅ Created unassigned task '${taskId}': ${task_title}`);
        } else {
          results.push(`❌ Failed to create task: ${task_title} (check server logs for details)`);
        }
      }
      
      // Handle multiple task creation
      if (tasks && Array.isArray(tasks)) {
        for (const task of tasks) {
          const taskId = createSingleUnassignedTask({
            title: task.title,
            description: task.description,
            priority: task.priority || 'medium',
            depends_on_tasks: task.depends_on_tasks || [],
            parent_task_id: task.parent_task_id
          });
          
          if (taskId) {
            createdTasks.push(taskId);
            results.push(`✅ Created unassigned task '${taskId}': ${task.title}`);
          } else {
            results.push(`❌ Failed to create task: ${task.title} (check server logs for details)`);
          }
        }
      }
    });
    
    transaction();
    
    const response = [
      `📝 **Unassigned Task Creation Results**`,
      '',
      ...results,
      '',
      `📊 **Summary:** ${createdTasks.length} task(s) created successfully`,
      '',
      '💡 **Next Steps:**',
      '1. Create agents using create_agent tool',
      '2. Assign tasks to agents using assign_task with task_ids parameter',
      '',
      `**Created Task IDs:** ${createdTasks.join(', ')}`
    ];
    
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
        text: `❌ Error creating unassigned tasks: ${error instanceof Error ? error.message : String(error)}`
      }],
      isError: true
    };
  }
}

function createSingleUnassignedTask(taskData: {
  title: string;
  description: string;
  priority: string;
  depends_on_tasks: string[];
  parent_task_id?: string;
}): string | null {
  const db = getDbConnection();
  
  try {
    // Validate dependencies if provided
    for (const depTaskId of taskData.depends_on_tasks) {
      const depTask = db.prepare('SELECT task_id FROM tasks WHERE task_id = ?').get(depTaskId);
      if (!depTask) {
        throw new Error(`Dependency task '${depTaskId}' not found`);
      }
    }
    
    // Phase-based task management: Only one active phase (root task) at a time
    if (!taskData.parent_task_id) {
      const rootCheck = db.prepare('SELECT task_id, title, status FROM tasks WHERE parent_task IS NULL ORDER BY created_at DESC LIMIT 1').get();
      
      if (rootCheck) {
        const existingPhase = rootCheck as any;
        
        // Check if current phase is complete using helper function
        if (!isPhaseComplete(db, existingPhase.task_id)) {
          const availableParents = getAvailableParentTasks(db, existingPhase.task_id);
          const suggestions = availableParents.length > 0 
            ? `Available parents: ${availableParents.map(p => p.task_id).join(', ')}`
            : `Use parent_task_id="${existingPhase.task_id}" to add to current phase`;
          
          throw new Error(`Cannot start new phase. Phase "${existingPhase.title}" (${existingPhase.task_id}) has incomplete tasks. ${suggestions}`);
        } else {
          console.log(`✅ Phase "${existingPhase.title}" completed. Allowing new phase creation.`);
        }
      }
    }
    
    // Generate task data
    const newTaskId = generateTaskId();
    const createdAt = new Date().toISOString();
    const status = 'unassigned';
    
    // Insert new task (unassigned - assigned_to is NULL)
    const insertTask = db.prepare(`
      INSERT INTO tasks (
        task_id, title, description, assigned_to, created_by, status, priority,
        created_at, updated_at, parent_task, child_tasks, depends_on_tasks, notes
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);
    
    insertTask.run(
      newTaskId,
      taskData.title,
      taskData.description,
      null, // Unassigned
      'admin',
      status,
      taskData.priority,
      createdAt,
      createdAt,
      taskData.parent_task_id || null,
      JSON.stringify([]), // Empty child tasks initially
      JSON.stringify(taskData.depends_on_tasks),
      JSON.stringify([])   // Empty notes initially
    );
    
    // Update parent task's child_tasks if parent exists
    if (taskData.parent_task_id) {
      const parentTask = db.prepare('SELECT child_tasks FROM tasks WHERE task_id = ?').get(taskData.parent_task_id);
      if (parentTask) {
        const childTasks = JSON.parse((parentTask as any).child_tasks || '[]');
        childTasks.push(newTaskId);
        
        const updateParent = db.prepare('UPDATE tasks SET child_tasks = ?, updated_at = ? WHERE task_id = ?');
        updateParent.run(JSON.stringify(childTasks), createdAt, taskData.parent_task_id);
      }
    }
    
    // Log task creation
    logTaskAction('admin', 'created_unassigned_task', newTaskId, {
      title: taskData.title,
      priority: taskData.priority,
      parent_task: taskData.parent_task_id,
      depends_on_count: taskData.depends_on_tasks.length
    });
    
    return newTaskId;
    
  } catch (error) {
    console.error(`Error creating unassigned task "${taskData.title}":`, error);
    // Log more details for debugging
    if (error instanceof Error) {
      console.error(`Task creation failed: ${error.message}`);
    }
    return null;
  }
}

function assignExistingTasks(agentId: string, taskIds: string[], notes?: string) {
  const db = getDbConnection();
  
  try {
    const results: string[] = [];
    const timestamp = new Date().toISOString();
    
    const transaction = db.transaction(() => {
      for (const taskId of taskIds) {
        // Check if task exists and is unassigned
        const task = db.prepare('SELECT task_id, title, assigned_to, status FROM tasks WHERE task_id = ?').get(taskId);
        
        if (!task) {
          results.push(`❌ Task '${taskId}' not found`);
          continue;
        }
        
        if ((task as any).assigned_to) {
          results.push(`⚠️ Task '${taskId}' already assigned to ${(task as any).assigned_to}`);
          continue;
        }
        
        // Assign task
        const updateTask = db.prepare('UPDATE tasks SET assigned_to = ?, status = ?, updated_at = ? WHERE task_id = ?');
        updateTask.run(agentId, 'pending', timestamp, taskId);
        
        results.push(`✅ Assigned '${taskId}': ${(task as any).title}`);
        
        // Log assignment
        logTaskAction(agentId, 'assigned_existing_task', taskId, { notes });
      }
    });
    
    transaction();
    
    return {
      content: [{
        type: 'text' as const,
        text: `**Task Assignment Results:**\n\n${results.join('\n')}\n\n📋 Assignment completed for agent: ${agentId}`
      }]
    };
    
  } catch (error) {
    return {
      content: [{
        type: 'text' as const,
        text: `❌ Error assigning tasks: ${error instanceof Error ? error.message : String(error)}`
      }],
      isError: true
    };
  }
}

function createMultipleTasks(agentId: string, tasks: any[], notes?: string) {
  // Implementation for creating multiple tasks
  return {
    content: [{
      type: 'text' as const,
      text: '⚠️ Multiple task creation not yet implemented'
    }]
  };
}

function createSingleTask(agentId: string, taskData: any, notes?: string) {
  const db = getDbConnection();
  
  try {
    const taskId = generateTaskId();
    const timestamp = new Date().toISOString();
    
    const transaction = db.transaction(() => {
      // Insert task
      const insertTask = db.prepare(`
        INSERT INTO tasks (
          task_id, title, description, assigned_to, created_by, status, priority,
          created_at, updated_at, parent_task, child_tasks, depends_on_tasks, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `);
      
      const initialNotes = notes ? [{
        content: notes,
        timestamp,
        agent_id: 'admin'
      }] : [];
      
      insertTask.run(
        taskId,
        taskData.title,
        taskData.description,
        agentId,
        'admin',
        'pending',
        taskData.priority,
        timestamp,
        timestamp,
        taskData.parent_task_id || null,
        JSON.stringify([]),
        JSON.stringify(taskData.depends_on_tasks || []),
        JSON.stringify(initialNotes)
      );
      
      // Update parent if specified
      if (taskData.parent_task_id) {
        const parent = db.prepare('SELECT child_tasks FROM tasks WHERE task_id = ?').get(taskData.parent_task_id);
        if (parent) {
          const childTasks = JSON.parse((parent as any).child_tasks || '[]');
          childTasks.push(taskId);
          
          const updateParent = db.prepare('UPDATE tasks SET child_tasks = ?, updated_at = ? WHERE task_id = ?');
          updateParent.run(JSON.stringify(childTasks), timestamp, taskData.parent_task_id);
        }
      }
      
      // Log assignment
      logTaskAction(agentId, 'assigned_new_task', taskId, { 
        title: taskData.title, 
        priority: taskData.priority,
        notes 
      });
      
      return taskId;
    });
    
    const newTaskId = transaction();
    
    return {
      content: [{
        type: 'text' as const,
        text: `✅ **Task '${newTaskId}' Created and Assigned**\n\n**Details:**\n- Title: ${taskData.title}\n- Priority: ${taskData.priority}\n- Assigned to: ${agentId}\n- Status: pending\n\n🎯 Task is ready for work`
      }]
    };
    
  } catch (error) {
    return {
      content: [{
        type: 'text' as const,
        text: `❌ Error creating task: ${error instanceof Error ? error.message : String(error)}`
      }],
      isError: true
    };
  }
}

// Helper function to get available parent tasks for suggestions
function getAvailableParentTasks(db: any, phaseTaskId: string): Array<{task_id: string, title: string}> {
  try {
    const availableParents = db.prepare(`
      WITH RECURSIVE task_tree AS (
        SELECT task_id, title, status FROM tasks WHERE task_id = ?
        UNION ALL
        SELECT t.task_id, t.title, t.status
        FROM tasks t
        INNER JOIN task_tree tt ON t.parent_task = tt.task_id
      )
      SELECT task_id, title FROM task_tree 
      WHERE status IN ('pending', 'in_progress', 'unassigned')
      ORDER BY title
      LIMIT 10
    `).all(phaseTaskId);
    
    return availableParents || [];
  } catch (error) {
    console.error('Error getting available parent tasks:', error);
    return [];
  }
}

// Helper function to check if phase is complete
function isPhaseComplete(db: any, phaseTaskId: string): boolean {
  try {
    const incompleteTasksQuery = db.prepare(`
      WITH RECURSIVE task_tree AS (
        SELECT task_id, title, status, parent_task FROM tasks WHERE task_id = ?
        UNION ALL
        SELECT t.task_id, t.title, t.status, t.parent_task 
        FROM tasks t
        INNER JOIN task_tree tt ON t.parent_task = tt.task_id
      )
      SELECT COUNT(*) as count FROM task_tree 
      WHERE status NOT IN ('completed', 'cancelled')
    `).get(phaseTaskId);
    
    return (incompleteTasksQuery as any).count === 0;
  } catch (error) {
    console.error('Error checking phase completion:', error);
    return false;
  }
}

console.log('✅ Task creation tools registered successfully');