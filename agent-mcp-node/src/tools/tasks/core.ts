// Core task utilities and helpers for Agent-MCP Node.js
// Ported from Python task_tools.py

import { randomBytes } from 'crypto';
import { getDbConnection } from '../../db/connection.js';

// Types for task management
export interface Task {
  task_id: string;
  title: string;
  description: string;
  assigned_to?: string;
  created_by: string;
  status: 'pending' | 'in_progress' | 'completed' | 'cancelled' | 'failed';
  priority: 'low' | 'medium' | 'high';
  created_at: string;
  updated_at: string;
  parent_task?: string;
  child_tasks: string[];
  depends_on_tasks: string[];
  notes: Array<{
    content: string;
    timestamp: string;
    agent_id: string;
  }>;
}

export interface TaskHealthMetrics {
  totalTasks: number;
  byStatus: Record<string, number>;
  byPriority: Record<string, number>;
  avgCompletionTime?: number;
  overdueCount: number;
  recentActivity: number;
}

// Task ID generation
export function generateTaskId(): string {
  return `task_${randomBytes(6).toString('hex')}`;
}

// Notification ID generation  
export function generateNotificationId(): string {
  return `notification_${randomBytes(8).toString('hex')}`;
}

// Token estimation for text (simplified version of Python tiktoken)
export function estimateTokens(text: string): number {
  // Rough estimation: ~4 characters per token
  return Math.ceil(text.length / 4);
}

// Task formatting helpers
export function formatTaskSummary(task: any): string {
  const status = task.status || 'unknown';
  const priority = task.priority || 'medium';
  const assignedTo = task.assigned_to || 'unassigned';
  
  return `**${task.task_id}** (${status}/${priority}) - ${task.title}\n` +
         `  Assigned: ${assignedTo}\n` +
         `  Created: ${new Date(task.created_at).toLocaleDateString()}`;
}

export function formatTaskDetailed(task: any): string {
  const notes = JSON.parse(task.notes || '[]');
  const childTasks = JSON.parse(task.child_tasks || '[]');
  const dependsOn = JSON.parse(task.depends_on_tasks || '[]');
  
  let formatted = `**${task.task_id}** - ${task.title}\n\n`;
  formatted += `**Status:** ${task.status} | **Priority:** ${task.priority}\n`;
  formatted += `**Assigned to:** ${task.assigned_to || 'Unassigned'}\n`;
  formatted += `**Created by:** ${task.created_by}\n`;
  formatted += `**Created:** ${new Date(task.created_at).toLocaleString()}\n`;
  formatted += `**Updated:** ${new Date(task.updated_at).toLocaleString()}\n\n`;
  
  if (task.description) {
    formatted += `**Description:**\n${task.description}\n\n`;
  }
  
  if (task.parent_task) {
    formatted += `**Parent Task:** ${task.parent_task}\n`;
  }
  
  if (childTasks.length > 0) {
    formatted += `**Child Tasks:** ${childTasks.join(', ')}\n`;
  }
  
  if (dependsOn.length > 0) {
    formatted += `**Depends On:** ${dependsOn.join(', ')}\n`;
  }
  
  if (notes.length > 0) {
    formatted += `\n**Notes:**\n`;
    notes.slice(-3).forEach((note: any) => {
      formatted += `- [${new Date(note.timestamp).toLocaleString()}] ${note.agent_id}: ${note.content}\n`;
    });
  }
  
  return formatted;
}

export function formatTaskWithDependencies(task: any): string {
  const db = getDbConnection();
  let formatted = formatTaskDetailed(task);
  
  try {
    const dependsOn = JSON.parse(task.depends_on_tasks || '[]');
    if (dependsOn.length > 0) {
      formatted += `\n**Dependency Details:**\n`;
      
      for (const depTaskId of dependsOn) {
        const depTask = db.prepare('SELECT task_id, title, status FROM tasks WHERE task_id = ?').get(depTaskId);
        if (depTask) {
          formatted += `- ${depTaskId}: ${(depTask as any).title} (${(depTask as any).status})\n`;
        } else {
          formatted += `- ${depTaskId}: [Task not found]\n`;
        }
      }
    }
    
    const childTasks = JSON.parse(task.child_tasks || '[]');
    if (childTasks.length > 0) {
      formatted += `\n**Child Task Details:**\n`;
      
      for (const childTaskId of childTasks) {
        const childTask = db.prepare('SELECT task_id, title, status FROM tasks WHERE task_id = ?').get(childTaskId);
        if (childTask) {
          formatted += `- ${childTaskId}: ${(childTask as any).title} (${(childTask as any).status})\n`;
        } else {
          formatted += `- ${childTaskId}: [Task not found]\n`;
        }
      }
    }
  } catch (error) {
    console.error('Error formatting task dependencies:', error);
  }
  
  return formatted;
}

// Calculate task health metrics
export function calculateTaskHealthMetrics(tasks: any[]): TaskHealthMetrics {
  const metrics: TaskHealthMetrics = {
    totalTasks: tasks.length,
    byStatus: {},
    byPriority: {},
    overdueCount: 0,
    recentActivity: 0
  };
  
  const now = Date.now();
  const oneDayAgo = now - (24 * 60 * 60 * 1000);
  
  for (const task of tasks) {
    // Count by status
    const status = task.status || 'unknown';
    metrics.byStatus[status] = (metrics.byStatus[status] || 0) + 1;
    
    // Count by priority
    const priority = task.priority || 'medium';
    metrics.byPriority[priority] = (metrics.byPriority[priority] || 0) + 1;
    
    // Check for recent activity
    const updatedAt = new Date(task.updated_at).getTime();
    if (updatedAt > oneDayAgo) {
      metrics.recentActivity++;
    }
    
    // Check for overdue tasks (simplified logic)
    if (task.status === 'pending' || task.status === 'in_progress') {
      const createdAt = new Date(task.created_at).getTime();
      const daysSinceCreated = (now - createdAt) / (24 * 60 * 60 * 1000);
      
      // Consider overdue if pending for more than 7 days or in_progress for more than 14 days
      if ((task.status === 'pending' && daysSinceCreated > 7) ||
          (task.status === 'in_progress' && daysSinceCreated > 14)) {
        metrics.overdueCount++;
      }
    }
  }
  
  return metrics;
}

// Analyze agent workload
export function analyzeAgentWorkload(agentId: string): any {
  const db = getDbConnection();
  
  try {
    // Get all tasks assigned to agent
    const assignedTasks = db.prepare(`
      SELECT * FROM tasks 
      WHERE assigned_to = ? 
      ORDER BY created_at DESC
    `).all(agentId);
    
    // Get recent task actions
    const recentActions = db.prepare(`
      SELECT * FROM agent_actions 
      WHERE agent_id = ? AND timestamp > datetime('now', '-7 days')
      ORDER BY timestamp DESC
    `).all(agentId);
    
    const workload = {
      agentId,
      totalAssignedTasks: assignedTasks.length,
      tasksByStatus: {} as Record<string, number>,
      tasksByPriority: {} as Record<string, number>,
      recentActions: recentActions.length,
      workloadScore: 0,
      recommendations: [] as string[]
    };
    
    // Analyze assigned tasks
    for (const task of assignedTasks) {
      const status = (task as any).status;
      const priority = (task as any).priority;
      
      workload.tasksByStatus[status] = (workload.tasksByStatus[status] || 0) + 1;
      workload.tasksByPriority[priority] = (workload.tasksByPriority[priority] || 0) + 1;
    }
    
    // Calculate workload score (simplified)
    const activeTasks = (workload.tasksByStatus.pending || 0) + (workload.tasksByStatus.in_progress || 0);
    const highPriorityTasks = workload.tasksByPriority.high || 0;
    
    workload.workloadScore = activeTasks + (highPriorityTasks * 2);
    
    // Generate recommendations
    if (workload.workloadScore > 10) {
      workload.recommendations.push('High workload detected - consider redistributing tasks');
    }
    
    if (workload.tasksByStatus.pending && workload.tasksByStatus.pending > 5) {
      workload.recommendations.push('Many pending tasks - prioritize task assignment');
    }
    
    if (workload.recentActions < 5) {
      workload.recommendations.push('Low recent activity - check agent status');
    }
    
    return workload;
  } catch (error) {
    console.error(`Error analyzing workload for agent ${agentId}:`, error);
    return {
      agentId,
      error: error instanceof Error ? error.message : String(error)
    };
  }
}

// Validation helpers
export function validateTaskStatus(status: string): boolean {
  const validStatuses = ['pending', 'in_progress', 'completed', 'cancelled', 'failed'];
  return validStatuses.includes(status);
}

export function validateTaskPriority(priority: string): boolean {
  const validPriorities = ['low', 'medium', 'high'];
  return validPriorities.includes(priority);
}

// Database helpers
export function logTaskAction(agentId: string, actionType: string, taskId?: string, details: any = {}) {
  const db = getDbConnection();
  const timestamp = new Date().toISOString();
  
  try {
    const stmt = db.prepare(`
      INSERT INTO agent_actions (agent_id, action_type, task_id, timestamp, details)
      VALUES (?, ?, ?, ?, ?)
    `);
    
    stmt.run(agentId, actionType, taskId || null, timestamp, JSON.stringify(details));
  } catch (error) {
    console.error('Failed to log task action:', error);
  }
}

console.log('✅ Task core utilities loaded successfully');