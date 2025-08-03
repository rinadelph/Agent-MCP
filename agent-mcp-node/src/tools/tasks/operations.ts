// Task operations tools for Agent-MCP Node.js
// Ported from Python task_tools.py (search, bulk operations, delete functions)

import { z } from 'zod';
import { registerTool } from '../registry.js';
import { getDbConnection } from '../../db/connection.js';
import { MCP_DEBUG } from '../../core/config.js';
import { verifyToken } from '../../core/auth.js';
import { 
  formatTaskSummary,
  logTaskAction,
  validateTaskStatus,
  estimateTokens 
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

// Search Tasks Tool
registerTool(
  'search_tasks',
  'Advanced task search with fuzzy matching, semantic search, and intelligent filtering.',
  z.object({
    token: z.string().describe('Agent or admin authentication token'),
    query: z.string().describe('Search query for titles, descriptions, and notes'),
    
    // Search options
    search_mode: z.enum(['fuzzy', 'exact', 'semantic']).default('fuzzy').describe('Search matching mode'),
    search_fields: z.array(z.enum(['title', 'description', 'notes', 'task_id'])).default(['title', 'description']).describe('Fields to search in'),
    case_sensitive: z.boolean().default(false).describe('Case sensitive search'),
    
    // Content analysis
    min_relevance_score: z.number().min(0).max(1).default(0.3).describe('Minimum relevance score (0-1)'),
    max_token_length: z.number().min(100).max(10000).default(1000).describe('Maximum content length to analyze'),
    
    // Filtering (same as view_tasks but focused on search results)
    filter_status: z.enum(['pending', 'in_progress', 'completed', 'cancelled', 'failed']).optional(),
    filter_priority: z.enum(['low', 'medium', 'high']).optional(),
    filter_agent_id: z.string().optional(),
    filter_created_after: z.string().optional(),
    
    // Display and pagination
    limit: z.number().min(1).max(100).default(20).describe('Maximum results to return'),
    include_context: z.boolean().default(true).describe('Include matching context snippets'),
    highlight_matches: z.boolean().default(true).describe('Highlight matching terms'),
    
    // Smart suggestions
    suggest_related: z.boolean().default(true).describe('Suggest related tasks'),
    include_analytics: z.boolean().default(false).describe('Include search analytics')
  }),
  async (args, context) => {
    const {
      token,
      query,
      search_mode = 'fuzzy',
      search_fields = ['title', 'description'],
      case_sensitive = false,
      min_relevance_score = 0.3,
      max_token_length = 1000,
      filter_status,
      filter_priority,
      filter_agent_id,
      filter_created_after,
      limit = 20,
      include_context = true,
      highlight_matches = true,
      suggest_related = true,
      include_analytics = false
    } = args;
    
    // Authentication
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
    
    if (!query || query.trim().length === 0) {
      return {
        content: [{
          type: 'text' as const,
          text: '❌ Error: Search query is required'
        }],
        isError: true
      };
    }
    
    const db = getDbConnection();
    
    try {
      // Build base query with permission filtering
      let baseQuery = 'SELECT * FROM tasks WHERE 1=1';
      const params: any[] = [];
      
      // Apply permission filtering
      if (!isAdmin && requestingAgentId) {
        baseQuery += ' AND (assigned_to = ? OR assigned_to IS NULL OR created_by = ?)';
        params.push(requestingAgentId, requestingAgentId);
      }
      
      // Apply additional filters
      if (filter_status) {
        baseQuery += ' AND status = ?';
        params.push(filter_status);
      }
      
      if (filter_priority) {
        baseQuery += ' AND priority = ?';
        params.push(filter_priority);
      }
      
      if (filter_agent_id) {
        baseQuery += ' AND assigned_to = ?';
        params.push(filter_agent_id);
      }
      
      if (filter_created_after) {
        baseQuery += ' AND created_at >= ?';
        params.push(filter_created_after);
      }
      
      // Execute base query to get candidate tasks
      const candidateTasks = db.prepare(baseQuery).all(...params);
      
      if (candidateTasks.length === 0) {
        return {
          content: [{
            type: 'text' as const,
            text: '🔍 No tasks found matching the filters. Try adjusting your search criteria.'
          }]
        };
      }
      
      // Prepare search terms
      const searchTerms = case_sensitive ? query : query.toLowerCase();
      const queryWords = searchTerms.split(/\s+/).filter((word: string) => word.length > 2);
      
      // Search and score tasks
      const searchResults: Array<{
        task: any;
        score: number;
        matches: Array<{ field: string; context: string; position: number }>;
      }> = [];
      
      for (const task of candidateTasks) {
        const taskScore = calculateTaskRelevanceScore(task, queryWords, search_fields, case_sensitive, max_token_length);
        
        if (taskScore.score >= min_relevance_score) {
          searchResults.push({
            task,
            score: taskScore.score,
            matches: taskScore.matches
          });
        }
      }
      
      // Sort by relevance score
      searchResults.sort((a, b) => b.score - a.score);
      
      // Limit results
      const limitedResults = searchResults.slice(0, limit);
      
      // Format response
      const response: string[] = [];
      
      if (include_analytics) {
        response.push('📊 **Search Analytics**');
        response.push('');
        response.push(`- Query: "${query}"`);
        response.push(`- Search Mode: ${search_mode}`);
        response.push(`- Fields: ${search_fields.join(', ')}`);
        response.push(`- Candidates Analyzed: ${candidateTasks.length}`);
        response.push(`- Results Found: ${searchResults.length}`);
        response.push(`- Results Shown: ${limitedResults.length}`);
        response.push(`- Min Relevance: ${min_relevance_score}`);
        response.push('');
        response.push('─'.repeat(50));
        response.push('');
      }
      
      response.push(`🔍 **Search Results** (${limitedResults.length} found)`);
      response.push('');
      
      if (limitedResults.length === 0) {
        response.push(`No tasks found matching "${query}" with relevance score >= ${min_relevance_score}`);
        response.push('');
        response.push('💡 **Try:**');
        response.push('- Using different search terms');
        response.push('- Lowering min_relevance_score');
        response.push('- Expanding search_fields');
        response.push('- Using semantic search mode (if available)');
      } else {
        limitedResults.forEach((result, index) => {
          response.push(`**${index + 1}. ${result.task.task_id}** (Relevance: ${(result.score * 100).toFixed(1)}%)`);
          response.push(formatTaskSummary(result.task));
          
          if (include_context && result.matches.length > 0) {
            response.push('');
            response.push('**Matching Context:**');
            result.matches.slice(0, 3).forEach(match => {
              let context = match.context;
              if (highlight_matches && !case_sensitive) {
                // Simple highlighting for display
                queryWords.forEach((word: string) => {
                  const regex = new RegExp(`(${word})`, 'gi');
                  context = context.replace(regex, '**$1**');
                });
              }
              response.push(`- ${match.field}: "${context}"`);
            });
          }
          
          response.push('');
        });
        
        if (searchResults.length > limit) {
          response.push(`📄 **Pagination:** Showing top ${limit} of ${searchResults.length} results`);
          response.push('💡 Increase limit parameter to see more results');
          response.push('');
        }
      }
      
      // Related task suggestions
      if (suggest_related && limitedResults.length > 0) {
        const relatedTasks = findRelatedTasks(db, query, limitedResults.map(r => r.task.task_id), requestingAgentId, isAdmin);
        
        if (relatedTasks.length > 0) {
          response.push('🔗 **Related Tasks:**');
          relatedTasks.slice(0, 3).forEach(task => {
            response.push(`- ${task.task_id}: ${task.title} (${task.status})`);
          });
          response.push('');
        }
      }
      
      // Log search activity
      if (MCP_DEBUG) {
        console.log(`🔍 ${requestingAgentId || 'admin'} searched for "${query}" - ${limitedResults.length} results`);
      }
      
      logTaskAction(requestingAgentId || 'admin', 'searched_tasks', undefined, {
        query,
        results_count: limitedResults.length,
        search_mode,
        fields: search_fields
      });
      
      return {
        content: [{
          type: 'text' as const,
          text: response.join('\n')
        }]
      };
      
    } catch (error) {
      console.error('Error searching tasks:', error);
      return {
        content: [{
          type: 'text' as const,
          text: `❌ Error searching tasks: ${error instanceof Error ? error.message : String(error)}`
        }],
        isError: true
      };
    }
  }
);

// Delete Task Tool (Admin only)
registerTool(
  'delete_task',
  'Delete one or more tasks. Admin only operation with safety checks and cascade options.',
  z.object({
    token: z.string().describe('Admin authentication token'),
    task_id: z.string().optional().describe('Single task ID to delete'),
    task_ids: z.array(z.string()).optional().describe('Multiple task IDs to delete'),
    
    // Safety options
    force_delete: z.boolean().default(false).describe('Force delete even if task has dependencies'),
    cascade_children: z.boolean().default(false).describe('Also delete child tasks'),
    unassign_only: z.boolean().default(false).describe('Unassign instead of deleting'),
    
    // Confirmation
    confirmation_phrase: z.string().optional().describe('Type "DELETE TASKS" to confirm deletion'),
    reason: z.string().optional().describe('Reason for deletion (for audit log)')
  }),
  async (args, context) => {
    const {
      token,
      task_id,
      task_ids,
      force_delete = false,
      cascade_children = false,
      unassign_only = false,
      confirmation_phrase,
      reason
    } = args;
    
    // Verify admin authentication
    if (!verifyAdminToken(token)) {
      return {
        content: [{
          type: 'text' as const,
          text: '❌ Unauthorized: Admin token required for task deletion'
        }],
        isError: true
      };
    }
    
    // Determine task IDs to delete
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
    
    // Safety confirmation for multiple deletes or force operations
    if ((targetTaskIds.length > 1 || force_delete || cascade_children) && confirmation_phrase !== 'DELETE TASKS') {
      return {
        content: [{
          type: 'text' as const,
          text: `⚠️ **DELETION CONFIRMATION REQUIRED**\n\nYou are about to delete ${targetTaskIds.length} task(s).\n${force_delete ? 'Force delete is enabled.\n' : ''}${cascade_children ? 'Cascade children is enabled.\n' : ''}\nTo confirm, add: confirmation_phrase: "DELETE TASKS"`
        }]
      };
    }
    
    const db = getDbConnection();
    const results: string[] = [];
    
    try {
      const transaction = db.transaction(() => {
        for (const taskId of targetTaskIds) {
          // Get task data
          const task = db.prepare('SELECT * FROM tasks WHERE task_id = ?').get(taskId);
          
          if (!task) {
            results.push(`❌ Task '${taskId}' not found`);
            continue;
          }
          
          const taskData = task as any;
          
          // Check for dependencies if not forcing
          if (!force_delete) {
            const dependentTasks = db.prepare(`
              SELECT task_id, title FROM tasks 
              WHERE depends_on_tasks LIKE ? AND task_id != ?
            `).all(`%${taskId}%`, taskId);
            
            if (dependentTasks.length > 0) {
              results.push(`❌ Cannot delete '${taskId}': ${dependentTasks.length} tasks depend on it`);
              results.push(`   Dependent tasks: ${dependentTasks.map((t: any) => t.task_id).join(', ')}`);
              results.push(`   Use force_delete=true to override`);
              continue;
            }
          }
          
          if (unassign_only) {
            // Just unassign the task
            const updateResult = db.prepare(`
              UPDATE tasks SET assigned_to = NULL, status = 'pending', updated_at = ? 
              WHERE task_id = ?
            `).run(new Date().toISOString(), taskId);
            
            if (updateResult.changes > 0) {
              results.push(`✅ Unassigned '${taskId}': ${taskData.title}`);
            }
          } else {
            // Handle child tasks
            const childTasks = JSON.parse(taskData.child_tasks || '[]');
            if (childTasks.length > 0) {
              if (cascade_children) {
                // Delete child tasks recursively
                for (const childId of childTasks) {
                  const deleteChild = db.prepare('DELETE FROM tasks WHERE task_id = ?').run(childId);
                  if (deleteChild.changes > 0) {
                    results.push(`  🗑️ Deleted child task: ${childId}`);
                  }
                }
              } else {
                // Orphan child tasks by removing parent reference
                for (const childId of childTasks) {
                  db.prepare('UPDATE tasks SET parent_task = NULL WHERE task_id = ?').run(childId);
                  results.push(`  ⚠️ Orphaned child task: ${childId}`);
                }
              }
            }
            
            // Update parent task to remove this as child
            if (taskData.parent_task) {
              const parent = db.prepare('SELECT child_tasks FROM tasks WHERE task_id = ?').get(taskData.parent_task);
              if (parent) {
                const siblings = JSON.parse((parent as any).child_tasks || '[]').filter((id: string) => id !== taskId);
                db.prepare('UPDATE tasks SET child_tasks = ? WHERE task_id = ?').run(
                  JSON.stringify(siblings), 
                  taskData.parent_task
                );
              }
            }
            
            // Remove from dependencies of other tasks
            const dependentTasks = db.prepare(`
              SELECT task_id, depends_on_tasks FROM tasks 
              WHERE depends_on_tasks LIKE ?
            `).all(`%${taskId}%`);
            
            for (const depTask of dependentTasks) {
              const deps = JSON.parse((depTask as any).depends_on_tasks || '[]').filter((id: string) => id !== taskId);
              db.prepare('UPDATE tasks SET depends_on_tasks = ? WHERE task_id = ?').run(
                JSON.stringify(deps),
                (depTask as any).task_id
              );
            }
            
            // Finally delete the task
            const deleteResult = db.prepare('DELETE FROM tasks WHERE task_id = ?').run(taskId);
            
            if (deleteResult.changes > 0) {
              results.push(`✅ Deleted '${taskId}': ${taskData.title}`);
              
              // Log deletion
              logTaskAction('admin', 'deleted_task', taskId, {
                title: taskData.title,
                reason,
                force_delete,
                cascade_children,
                child_count: childTasks.length
              });
            } else {
              results.push(`❌ Failed to delete '${taskId}'`);
            }
          }
        }
      });
      
      transaction();
      
      const response = [
        `🗑️ **Task ${unassign_only ? 'Unassignment' : 'Deletion'} Results**`,
        '',
        ...results
      ];
      
      if (targetTaskIds.length > 1) {
        const successCount = results.filter(r => r.startsWith('✅')).length;
        response.push('');
        response.push(`📊 **Summary:** ${successCount}/${targetTaskIds.length} tasks processed successfully`);
      }
      
      if (reason) {
        response.push('');
        response.push(`📝 **Reason:** ${reason}`);
      }
      
      return {
        content: [{
          type: 'text' as const,
          text: response.join('\n')
        }]
      };
      
    } catch (error) {
      console.error('Error deleting tasks:', error);
      return {
        content: [{
          type: 'text' as const,
          text: `❌ Error deleting tasks: ${error instanceof Error ? error.message : String(error)}`
        }],
        isError: true
      };
    }
  }
);

// Helper function to calculate task relevance score
function calculateTaskRelevanceScore(
  task: any, 
  queryWords: string[], 
  searchFields: string[], 
  caseSensitive: boolean,
  maxTokenLength: number
): { score: number; matches: Array<{ field: string; context: string; position: number }> } {
  let totalScore = 0;
  const matches: Array<{ field: string; context: string; position: number }> = [];
  
  for (const field of searchFields) {
    let fieldContent = '';
    let fieldWeight = 1;
    
    switch (field) {
      case 'title':
        fieldContent = task.title || '';
        fieldWeight = 2; // Title matches are more important
        break;
      case 'description':
        fieldContent = task.description || '';
        fieldWeight = 1.5;
        break;
      case 'notes':
        const notes = JSON.parse(task.notes || '[]');
        fieldContent = notes.map((note: any) => note.content).join(' ');
        fieldWeight = 1;
        break;
      case 'task_id':
        fieldContent = task.task_id || '';
        fieldWeight = 3; // Exact ID matches are very important
        break;
    }
    
    if (!fieldContent) continue;
    
    // Limit content length for performance
    if (fieldContent.length > maxTokenLength) {
      fieldContent = fieldContent.substring(0, maxTokenLength);
    }
    
    const searchContent = caseSensitive ? fieldContent : fieldContent.toLowerCase();
    
    // Calculate field score
    let fieldScore = 0;
    
    for (const word of queryWords) {
      const wordIndex = searchContent.indexOf(word);
      if (wordIndex !== -1) {
        // Base score for match
        fieldScore += 0.3;
        
        // Bonus for exact word boundaries
        const isWholeWord = (wordIndex === 0 || !/\w/.test(searchContent.charAt(wordIndex - 1))) &&
                          (wordIndex + word.length === searchContent.length || !/\w/.test(searchContent.charAt(wordIndex + word.length)));
        if (isWholeWord) {
          fieldScore += 0.2;
        }
        
        // Bonus for position (earlier matches score higher)
        const positionBonus = 1 - (wordIndex / searchContent.length) * 0.3;
        fieldScore += positionBonus * 0.1;
        
        // Record match for context
        const contextStart = Math.max(0, wordIndex - 50);
        const contextEnd = Math.min(searchContent.length, wordIndex + word.length + 50);
        const context = fieldContent.substring(contextStart, contextEnd);
        
        matches.push({
          field,
          context: context.trim(),
          position: wordIndex
        });
      }
    }
    
    totalScore += fieldScore * fieldWeight;
  }
  
  // Normalize score to 0-1 range
  const normalizedScore = Math.min(1, totalScore / queryWords.length);
  
  return { score: normalizedScore, matches };
}

// Helper function to find related tasks
function findRelatedTasks(
  db: any, 
  query: string, 
  excludeIds: string[], 
  requestingAgentId: string | null, 
  isAdmin: boolean
): any[] {
  try {
    const queryWords = query.toLowerCase().split(/\s+/).filter(word => word.length > 2);
    
    let relatedQuery = `
      SELECT task_id, title, status FROM tasks 
      WHERE task_id NOT IN (${excludeIds.map(() => '?').join(',')})
    `;
    const params = [...excludeIds];
    
    // Apply permission filtering
    if (!isAdmin && requestingAgentId) {
      relatedQuery += ' AND (assigned_to = ? OR assigned_to IS NULL OR created_by = ?)';
      params.push(requestingAgentId, requestingAgentId);
    }
    
    // Simple related task finding based on common words
    if (queryWords.length > 0) {
      const likeConditions = queryWords.map(() => '(title LIKE ? OR description LIKE ?)').join(' OR ');
      relatedQuery += ` AND (${likeConditions})`;
      
      for (const word of queryWords) {
        const pattern = `%${word}%`;
        params.push(pattern, pattern);
      }
    }
    
    relatedQuery += ' LIMIT 5';
    
    return db.prepare(relatedQuery).all(...params);
  } catch (error) {
    console.error('Error finding related tasks:', error);
    return [];
  }
}

// Bulk Task Operations Tool
registerTool(
  'bulk_task_operations',
  'Perform multiple task operations in a single atomic transaction. Supports update_status, update_priority, add_note, and reassign (admin only) operations. Critical for efficient batch task management.',
  z.object({
    token: z.string().optional().describe('Authentication token (agent or admin)'),
    operations: z.array(z.object({
      type: z.enum(['update_status', 'update_priority', 'add_note', 'reassign']).describe('Operation type'),
      task_id: z.string().describe('Task ID to operate on'),
      status: z.enum(['pending', 'in_progress', 'completed', 'cancelled', 'failed']).optional().describe('New status for update_status operation'),
      priority: z.enum(['low', 'medium', 'high']).optional().describe('New priority for update_priority operation'),
      content: z.string().optional().describe('Note content for add_note operation'),
      notes: z.string().optional().describe('Notes for update_status operation'),
      assigned_to: z.string().optional().describe('New assignee for reassign operation (admin only)')
    })).min(1).describe('List of operations to perform')
  }),
  async (args, context) => {
    const { token, operations } = args;
    
    // Get requesting agent ID from token or context
    let requestingAgentId: string | null = null;
    
    if (token) {
      requestingAgentId = getAgentIdFromToken(token);
    } else {
      // For MCP connections, use session-based authentication
      requestingAgentId = context.agentId || 'admin';
    }
    
    if (!requestingAgentId) {
      return {
        content: [{
          type: 'text' as const,
          text: '❌ Unauthorized: Valid token required'
        }],
        isError: true
      };
    }
    
    const isAdminRequest = verifyAdminToken(token);
    
    if (!operations || !Array.isArray(operations) || operations.length === 0) {
      return {
        content: [{
          type: 'text' as const,
          text: '❌ Error: operations list is required and must be a non-empty array'
        }],
        isError: true
      };
    }
    
    const db = getDbConnection();
    const results: string[] = [];
    const updatedAt = new Date().toISOString();
    
    try {
      // Process all operations in a single atomic transaction
      const transaction = db.transaction(() => {
        for (let i = 0; i < operations.length; i++) {
          const op = operations[i];
          const operationIndex = i + 1;
          
          if (!op || typeof op !== 'object') {
            results.push(`Operation ${operationIndex}: Invalid operation format (must be object)`);
            continue;
          }
          
          const { type: operationType, task_id, status, priority, content, notes, assigned_to } = op;
          
          if (!task_id || !operationType) {
            results.push(`Operation ${operationIndex}: Missing required fields 'type' and 'task_id'`);
            continue;
          }
          
          // Verify task exists and get task data
          const task = db.prepare('SELECT * FROM tasks WHERE task_id = ?').get(task_id);
          if (!task) {
            results.push(`Operation ${operationIndex}: Task '${task_id}' not found`);
            continue;
          }
          
          const taskData = task as any;
          
          // Permission check - agents can only modify their own tasks
          if (taskData.assigned_to !== requestingAgentId && !isAdminRequest) {
            results.push(`Operation ${operationIndex}: Unauthorized - can only modify own tasks`);
            continue;
          }
          
          try {
            // Process each operation type
            if (operationType === 'update_status') {
              if (!status) {
                results.push(`Operation ${operationIndex}: Missing 'status' for update_status operation`);
                continue;
              }
              
              const validStatuses = ['pending', 'in_progress', 'completed', 'cancelled', 'failed'];
              if (!validStatuses.includes(status)) {
                results.push(`Operation ${operationIndex}: Invalid status '${status}'`);
                continue;
              }
              
              // Update status and handle notes
              let currentNotes = JSON.parse(taskData.notes || '[]');
              if (notes) {
                currentNotes.push({
                  timestamp: updatedAt,
                  author: requestingAgentId,
                  content: notes
                });
              }
              
              const updateResult = db.prepare(`
                UPDATE tasks SET status = ?, notes = ?, updated_at = ? WHERE task_id = ?
              `).run(status, JSON.stringify(currentNotes), updatedAt, task_id);
              
              if (updateResult.changes > 0) {
                results.push(`Operation ${operationIndex}: Task '${task_id}' status updated to '${status}'`);
              } else {
                results.push(`Operation ${operationIndex}: Failed to update status for task '${task_id}'`);
              }
              
            } else if (operationType === 'update_priority') {
              if (!priority || !['low', 'medium', 'high'].includes(priority)) {
                results.push(`Operation ${operationIndex}: Invalid priority '${priority}'`);
                continue;
              }
              
              const updateResult = db.prepare(`
                UPDATE tasks SET priority = ?, updated_at = ? WHERE task_id = ?
              `).run(priority, updatedAt, task_id);
              
              if (updateResult.changes > 0) {
                results.push(`Operation ${operationIndex}: Task '${task_id}' priority updated to '${priority}'`);
              } else {
                results.push(`Operation ${operationIndex}: Failed to update priority for task '${task_id}'`);
              }
              
            } else if (operationType === 'add_note') {
              if (!content) {
                results.push(`Operation ${operationIndex}: Missing 'content' for add_note operation`);
                continue;
              }
              
              let currentNotes = JSON.parse(taskData.notes || '[]');
              currentNotes.push({
                timestamp: updatedAt,
                author: requestingAgentId,
                content: content
              });
              
              const updateResult = db.prepare(`
                UPDATE tasks SET notes = ?, updated_at = ? WHERE task_id = ?
              `).run(JSON.stringify(currentNotes), updatedAt, task_id);
              
              if (updateResult.changes > 0) {
                results.push(`Operation ${operationIndex}: Note added to task '${task_id}'`);
              } else {
                results.push(`Operation ${operationIndex}: Failed to add note to task '${task_id}'`);
              }
              
            } else if (operationType === 'reassign') {
              if (!isAdminRequest) {
                results.push(`Operation ${operationIndex}: Reassign operation requires admin privileges`);
                continue;
              }
              
              if (!assigned_to) {
                results.push(`Operation ${operationIndex}: Missing 'assigned_to' for reassign operation`);
                continue;
              }
              
              const updateResult = db.prepare(`
                UPDATE tasks SET assigned_to = ?, updated_at = ? WHERE task_id = ?
              `).run(assigned_to, updatedAt, task_id);
              
              if (updateResult.changes > 0) {
                results.push(`Operation ${operationIndex}: Task '${task_id}' reassigned to '${assigned_to}'`);
              } else {
                results.push(`Operation ${operationIndex}: Failed to reassign task '${task_id}'`);
              }
              
            } else {
              results.push(`Operation ${operationIndex}: Unknown operation type '${operationType}'`);
            }
            
          } catch (operationError) {
            results.push(`Operation ${operationIndex}: Error processing - ${operationError instanceof Error ? operationError.message : String(operationError)}`);
            console.error(`Error in bulk operation ${operationIndex}:`, operationError);
          }
        }
      });
      
      // Execute the transaction
      transaction();
      
      // Log the bulk operation
      logTaskAction(requestingAgentId, 'bulk_task_operations', undefined, {
        operations_count: operations.length,
        success_count: results.filter(r => !r.includes('Error') && !r.includes('Failed') && !r.includes('Missing') && !r.includes('Invalid') && !r.includes('Unauthorized') && !r.includes('Unknown')).length,
        operation_types: operations.map(op => op.type)
      });
      
      // Build response
      const successCount = results.filter(r => r.includes('✅') || (!r.includes('❌') && !r.includes('Error') && !r.includes('Failed'))).length;
      const response = [
        `📝 **Bulk Task Operations Results** (${operations.length} operations)`,
        '',
        ...results.map(r => r.startsWith('Operation') ? `• ${r}` : r),
        '',
        `📊 **Summary:** ${successCount}/${operations.length} operations completed successfully`
      ];
      
      if (MCP_DEBUG) {
        console.log(`📝 ${requestingAgentId} performed bulk operations on ${operations.length} tasks - ${successCount} successful`);
      }
      
      return {
        content: [{
          type: 'text' as const,
          text: response.join('\n')
        }]
      };
      
    } catch (error) {
      console.error('Error in bulk task operations:', error);
      return {
        content: [{
          type: 'text' as const,
          text: `❌ Database error in bulk operations: ${error instanceof Error ? error.message : String(error)}`
        }],
        isError: true
      };
    }
  }
);

console.log('✅ Task operations tools registered successfully');