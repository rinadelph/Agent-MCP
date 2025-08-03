// Project Context Tools for Agent-MCP Node.js
// Ported from Python project_context_tools.py to match API exactly

import { z } from 'zod';
import { registerTool } from './registry.js';
import { getDbConnection } from '../db/connection.js';
import { MCP_DEBUG } from '../core/config.js';
import { verifyToken, getAgentId } from '../core/auth.js';

// Schemas matching Python implementation
const ViewProjectContextSchema = z.object({
  token: z.string().describe("Authentication token"),
  context_key: z.string().optional().describe("Exact key to view (optional). If provided, search_query is ignored."),
  search_query: z.string().optional().describe("Keyword search query (optional). Searches keys, descriptions, and values."),
  show_health_analysis: z.boolean().optional().default(false).describe("Include comprehensive health metrics and analysis"),
  show_stale_entries: z.boolean().optional().default(false).describe("Show only entries older than 30 days needing review"),
  include_backup_info: z.boolean().optional().default(false).describe("Include backup recommendations and info"),
  max_results: z.number().int().min(1).max(200).optional().default(50).describe("Maximum number of entries to return"),
  sort_by: z.enum(['key', 'last_updated', 'size']).optional().default('last_updated').describe("Sort entries by specified field")
});

const UpdateProjectContextSchema = z.object({
  token: z.string().describe("Authentication token"),
  context_key: z.string().describe("Key for the context entry"),
  context_value: z.any().describe("Value to store (will be JSON stringified)"),
  description: z.string().optional().describe("Optional description of what this context represents")
});

const BulkUpdateProjectContextSchema = z.object({
  token: z.string().describe("Authentication token"),
  updates: z.array(z.object({
    context_key: z.string(),
    context_value: z.any(),
    description: z.string().optional()
  })).describe("Array of context updates to perform")
});

const DeleteProjectContextSchema = z.object({
  token: z.string().describe("Authentication token"),
  context_key: z.string().describe("Context key to delete")
});

const BackupProjectContextSchema = z.object({
  token: z.string().describe("Authentication token"),
  backup_name: z.string().optional().describe("Custom name for the backup")
});

const ValidateContextConsistencySchema = z.object({
  token: z.string().describe("Authentication token"),
  fix_issues: z.boolean().optional().default(false).describe("Automatically fix found issues")
});

/**
 * Analyze context health - ported from Python _analyze_context_health
 */
function analyzeContextHealth(contextEntries: any[]) {
  if (!contextEntries || contextEntries.length === 0) {
    return { status: "no_data", total: 0 };
  }

  const total = contextEntries.length;
  const issues: string[] = [];
  const warnings: string[] = [];
  let staleCount = 0;
  let jsonErrors = 0;
  let largeEntries = 0;
  const currentTime = new Date();

  for (const entry of contextEntries) {
    const contextKey = entry.context_key || "unknown";
    const value = entry.value || "";
    const lastUpdated = entry.last_updated;

    // Check for JSON parsing issues
    try {
      if (typeof value === 'string') {
        JSON.parse(value);
      }
    } catch {
      jsonErrors += 1;
      issues.push(`JSON parse error in '${contextKey}'`);
    }

    // Check for stale entries (30+ days old)
    if (lastUpdated) {
      try {
        const updatedTime = new Date(lastUpdated);
        const daysOld = Math.floor((currentTime.getTime() - updatedTime.getTime()) / (1000 * 60 * 60 * 24));
        if (daysOld > 30) {
          staleCount += 1;
          if (daysOld > 90) {
            warnings.push(`'${contextKey}' is ${daysOld} days old`);
          }
        }
      } catch {
        warnings.push(`Invalid timestamp for '${contextKey}'`);
      }
    }

    // Check for oversized entries (>10KB)
    const entrySize = String(value).length;
    if (entrySize > 10240) { // 10KB
      largeEntries += 1;
      warnings.push(`'${contextKey}' is large (${Math.floor(entrySize/1024)}KB)`);
    }
  }

  // Calculate health score
  const staleRatio = staleCount / total;
  const errorRatio = jsonErrors / total;
  const largeRatio = largeEntries / total;

  const healthScore = Math.max(
    0, Math.min(100, 100 - (staleRatio * 40) - (errorRatio * 50) - (largeRatio * 10))
  );

  const healthStatus = healthScore >= 90 ? "excellent" :
                      healthScore >= 70 ? "good" :
                      healthScore >= 50 ? "needs_attention" : "critical";

  return {
    status: healthStatus,
    health_score: Math.round(healthScore * 10) / 10,
    total,
    stale_entries: staleCount,
    json_errors: jsonErrors,
    large_entries: largeEntries,
    issues: issues.slice(0, 5), // Limit to first 5
    warnings: warnings.slice(0, 5), // Limit to first 5
    recommendations: generateContextRecommendations(staleCount, jsonErrors, largeEntries, total)
  };
}

/**
 * Generate context recommendations - ported from Python
 */
function generateContextRecommendations(staleCount: number, jsonErrors: number, largeEntries: number, total: number): string[] {
  const recommendations: string[] = [];
  
  if (staleCount > 0) {
    recommendations.push(`Review ${staleCount} stale entries that haven't been updated in 30+ days`);
  }
  
  if (jsonErrors > 0) {
    recommendations.push(`Fix ${jsonErrors} entries with JSON parsing errors`);
  }
  
  if (largeEntries > 0) {
    recommendations.push(`Consider splitting ${largeEntries} large entries (>10KB) into smaller pieces`);
  }
  
  if (total > 100) {
    recommendations.push("Consider creating context backups due to large number of entries");
  }
  
  return recommendations;
}

/**
 * View project context - ported from Python view_project_context_tool_impl
 */
async function viewProjectContext(args: Record<string, any>) {
  const { 
    token, 
    context_key, 
    search_query, 
    show_health_analysis = false,
    show_stale_entries = false,
    include_backup_info = false,
    max_results = 50,
    sort_by = 'last_updated'
  } = args;

  // Authenticate
  const agentId = getAgentId(token);
  if (!agentId) {
    return {
      content: [{
        type: 'text' as const,
        text: "Unauthorized: Valid token required"
      }],
      isError: true
    };
  }

  const db = getDbConnection();

  try {
    // Build query based on filters
    const whereConditions: string[] = [];
    const queryParams: any[] = [];

    if (context_key) {
      whereConditions.push("context_key = ?");
      queryParams.push(context_key);
    } else if (search_query) {
      const likePattern = `%${search_query}%`;
      whereConditions.push("(context_key LIKE ? OR description LIKE ? OR value LIKE ?)");
      queryParams.push(likePattern, likePattern, likePattern);
    }

    if (show_stale_entries) {
      // Show entries older than 30 days
      const thirtyDaysAgo = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString();
      whereConditions.push("last_updated < ?");
      queryParams.push(thirtyDaysAgo);
    }

    // Build query with smart sorting
    let baseQuery = "SELECT context_key, value, description, updated_by, last_updated, LENGTH(value) as value_size FROM project_context";

    if (whereConditions.length > 0) {
      baseQuery += " WHERE " + whereConditions.join(" AND ");
    }

    // Smart sorting
    if (sort_by === "size") {
      baseQuery += " ORDER BY LENGTH(value) DESC";
    } else if (sort_by === "key") {
      baseQuery += " ORDER BY context_key ASC";
    } else { // last_updated (default)
      baseQuery += " ORDER BY last_updated DESC";
    }

    baseQuery += ` LIMIT ${max_results}`;

    const stmt = db.prepare(baseQuery);
    const rows = stmt.all(...queryParams);

    if (rows.length === 0) {
      const message = context_key ? 
        `Context key '${context_key}' not found` : 
        'No project context entries found';
      
      return {
        content: [{
          type: 'text' as const,
          text: JSON.stringify({ message, total_entries: 0 }, null, 2)
        }]
      };
    }

    // Process results with enhanced information
    const processedResults = [];
    
    for (const row of rows as any[]) {
      try {
        let valueParsed;
        let jsonValid = true;
        
        try {
          valueParsed = JSON.parse(row.value);
        } catch {
          valueParsed = row.value;
          jsonValid = false;
        }

        // Calculate additional metadata
        const entrySize = String(row.value).length;
        const lastUpdated = row.last_updated;
        
        let daysOld = null;
        if (lastUpdated) {
          try {
            const updatedTime = new Date(lastUpdated);
            daysOld = Math.floor((Date.now() - updatedTime.getTime()) / (1000 * 60 * 60 * 24));
          } catch {
            // Invalid date
          }
        }

        processedResults.push({
          context_key: row.context_key,
          value: valueParsed,
          description: row.description,
          updated_by: row.updated_by,
          last_updated: lastUpdated,
          metadata: {
            size_bytes: entrySize,
            size_kb: Math.round(entrySize / 1024 * 10) / 10,
            json_valid: jsonValid,
            days_old: daysOld,
            is_stale: daysOld !== null && daysOld > 30
          }
        });
      } catch (error) {
        // Skip problematic entries but log
        if (MCP_DEBUG) {
          console.error(`Error processing context entry ${row.context_key}:`, error);
        }
      }
    }

    // Build response
    const response: any = {
      total_entries: processedResults.length,
      max_results_limit: max_results,
      sort_by,
      entries: processedResults
    };

    // Add health analysis if requested
    if (show_health_analysis) {
      response.health_analysis = analyzeContextHealth(rows);
    }

    // Add backup info if requested
    if (include_backup_info) {
      // Check for existing backups
      const backupStmt = db.prepare("SELECT context_key, last_updated FROM project_context WHERE context_key LIKE '__backup__%' ORDER BY last_updated DESC LIMIT 5");
      const backups = backupStmt.all();
      
      response.backup_info = {
        recent_backups: backups,
        recommendation: backups.length === 0 ? 
          "No backups found - consider creating one" : 
          `${backups.length} backups available`
      };
    }

    // Log action
    const actionStmt = db.prepare(`
      INSERT INTO agent_actions (agent_id, action_type, timestamp, details)
      VALUES (?, ?, ?, ?)
    `);
    
    actionStmt.run(agentId, 'view_project_context', new Date().toISOString(), JSON.stringify({
      context_key,
      search_query,
      results_count: processedResults.length
    }));

    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify(response, null, 2)
      }]
    };

  } catch (error) {
    console.error('Error viewing project context:', error);
    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify({
          error: 'Failed to view project context',
          details: error instanceof Error ? error.message : String(error)
        }, null, 2)
      }],
      isError: true
    };
  }
}

/**
 * Update project context - ported from Python update_project_context_tool_impl
 */
async function updateProjectContext(args: Record<string, any>) {
  const { token, context_key, context_value, description } = args;

  // Authenticate
  const agentId = getAgentId(token);
  if (!agentId) {
    return {
      content: [{
        type: 'text' as const,
        text: "Unauthorized: Valid token required"
      }],
      isError: true
    };
  }

  const db = getDbConnection();

  try {
    // Ensure value is JSON serializable
    let valueJsonStr: string;
    try {
      valueJsonStr = JSON.stringify(context_value);
    } catch (error) {
      return {
        content: [{
          type: 'text' as const,
          text: `Error: Provided context_value is not JSON serializable: ${error}`
        }],
        isError: true
      };
    }

    const timestamp = new Date().toISOString();

    // Use INSERT OR REPLACE (UPSERT)
    const upsertStmt = db.prepare(`
      INSERT OR REPLACE INTO project_context (context_key, value, last_updated, updated_by, description)
      VALUES (?, ?, ?, ?, ?)
    `);

    upsertStmt.run(context_key, valueJsonStr, timestamp, agentId, description || null);

    // Log action
    const actionStmt = db.prepare(`
      INSERT INTO agent_actions (agent_id, action_type, timestamp, details)
      VALUES (?, ?, ?, ?)
    `);

    actionStmt.run(agentId, 'updated_context', timestamp, JSON.stringify({
      context_key,
      action: 'set/update'
    }));

    if (MCP_DEBUG) {
      console.log(`📝 Project context '${context_key}' updated by '${agentId}'`);
    }

    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify({
          success: true,
          context_key,
          updated_by: agentId,
          timestamp,
          value_size_bytes: valueJsonStr.length,
          description
        }, null, 2)
      }]
    };

  } catch (error) {
    console.error('Error updating project context:', error);
    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify({
          error: 'Failed to update project context',
          details: error instanceof Error ? error.message : String(error)
        }, null, 2)
      }],
      isError: true
    };
  }
}

/**
 * Bulk update project context - ported from Python bulk_update_project_context_tool_impl
 */
async function bulkUpdateProjectContext(args: Record<string, any>) {
  const { token, updates } = args;

  // Authenticate
  const agentId = getAgentId(token);
  if (!agentId) {
    return {
      content: [{
        type: 'text' as const,
        text: "Unauthorized: Valid token required"
      }],
      isError: true
    };
  }

  const db = getDbConnection();

  try {
    const timestamp = new Date().toISOString();
    const results: any[] = [];

    // Use transaction for bulk update
    const transaction = db.transaction(() => {
      for (const update of updates) {
        const { context_key, context_value, description } = update;

        // Ensure value is JSON serializable
        let valueJsonStr: string;
        try {
          valueJsonStr = JSON.stringify(context_value);
        } catch (error) {
          results.push({
            context_key,
            success: false,
            error: `Value not JSON serializable: ${error}`
          });
          continue;
        }

        // Insert or update
        const upsertStmt = db.prepare(`
          INSERT OR REPLACE INTO project_context (context_key, value, last_updated, updated_by, description)
          VALUES (?, ?, ?, ?, ?)
        `);

        upsertStmt.run(context_key, valueJsonStr, timestamp, agentId, description || null);

        results.push({
          context_key,
          success: true,
          value_size_bytes: valueJsonStr.length
        });
      }

      // Log bulk action
      const actionStmt = db.prepare(`
        INSERT INTO agent_actions (agent_id, action_type, timestamp, details)
        VALUES (?, ?, ?, ?)
      `);

      actionStmt.run(agentId, 'bulk_update_context', timestamp, JSON.stringify({
        updates_count: updates.length
      }));
    });

    transaction();

    if (MCP_DEBUG) {
      console.log(`📝 Bulk context update: ${updates.length} entries by ${agentId}`);
    }

    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify({
          success: true,
          updates_processed: results.length,
          updated_by: agentId,
          timestamp,
          results
        }, null, 2)
      }]
    };

  } catch (error) {
    console.error('Error bulk updating project context:', error);
    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify({
          error: 'Failed to bulk update project context',
          details: error instanceof Error ? error.message : String(error)
        }, null, 2)
      }],
      isError: true
    };
  }
}

/**
 * Delete project context - ported from Python delete_project_context_tool_impl
 */
async function deleteProjectContext(args: Record<string, any>) {
  const { token, context_key } = args;

  // Authenticate
  const agentId = getAgentId(token);
  if (!agentId) {
    return {
      content: [{
        type: 'text' as const,
        text: "Unauthorized: Valid token required"
      }],
      isError: true
    };
  }

  const db = getDbConnection();

  try {
    // Check if entry exists
    const existingStmt = db.prepare('SELECT context_key, value FROM project_context WHERE context_key = ?');
    const existing = existingStmt.get(context_key);

    if (!existing) {
      return {
        content: [{
          type: 'text' as const,
          text: JSON.stringify({
            success: false,
            error: `Context key '${context_key}' not found`
          }, null, 2)
        }],
        isError: true
      };
    }

    // Delete the entry
    const deleteStmt = db.prepare('DELETE FROM project_context WHERE context_key = ?');
    const result = deleteStmt.run(context_key);

    // Log action
    const timestamp = new Date().toISOString();
    const actionStmt = db.prepare(`
      INSERT INTO agent_actions (agent_id, action_type, timestamp, details)
      VALUES (?, ?, ?, ?)
    `);

    actionStmt.run(agentId, 'delete_context', timestamp, JSON.stringify({
      context_key,
      deleted_value_size: String((existing as any).value).length
    }));

    if (MCP_DEBUG) {
      console.log(`🗑️ Context deleted: ${context_key} by ${agentId}`);
    }

    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify({
          success: true,
          context_key,
          deleted_by: agentId,
          timestamp,
          deleted: result.changes > 0
        }, null, 2)
      }]
    };

  } catch (error) {
    console.error('Error deleting project context:', error);
    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify({
          error: 'Failed to delete project context',
          details: error instanceof Error ? error.message : String(error)
        }, null, 2)
      }],
      isError: true
    };
  }
}

/**
 * Create backup of project context - ported from Python backup_project_context_tool_impl
 */
async function backupProjectContext(args: Record<string, any>) {
  const { token, backup_name } = args;

  // Authenticate
  const agentId = getAgentId(token);
  if (!agentId) {
    return {
      content: [{
        type: 'text' as const,
        text: "Unauthorized: Valid token required"
      }],
      isError: true
    };
  }

  const db = getDbConnection();

  try {
    const timestamp = new Date().toISOString();
    const backupId = backup_name || `backup_${timestamp.replace(/[:.]/g, '-')}`;

    // Get all context entries
    const stmt = db.prepare('SELECT * FROM project_context WHERE context_key NOT LIKE "__backup__%" ORDER BY context_key');
    const entries = stmt.all();

    const backup = {
      backup_id: backupId,
      created_at: timestamp,
      created_by: agentId,
      entry_count: entries.length,
      entries: entries.map((entry: any) => ({
        context_key: entry.context_key,
        value: JSON.parse(entry.value),
        description: entry.description,
        last_updated: entry.last_updated,
        updated_by: entry.updated_by
      }))
    };

    // Store backup as a special context entry
    const backupKey = `__backup__${backupId}`;
    const backupJson = JSON.stringify(backup);

    const insertStmt = db.prepare(`
      INSERT INTO project_context (context_key, value, last_updated, updated_by, description)
      VALUES (?, ?, ?, ?, ?)
    `);

    insertStmt.run(backupKey, backupJson, timestamp, agentId, `Backup created by ${agentId}`);

    // Log action
    const actionStmt = db.prepare(`
      INSERT INTO agent_actions (agent_id, action_type, timestamp, details)
      VALUES (?, ?, ?, ?)
    `);

    actionStmt.run(agentId, 'backup_context', timestamp, JSON.stringify({
      backup_id: backupId,
      entry_count: entries.length
    }));

    if (MCP_DEBUG) {
      console.log(`💾 Context backup created: ${backupId} by ${agentId}`);
    }

    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify({
          success: true,
          backup_id: backupId,
          backup_key: backupKey,
          entry_count: entries.length,
          backup_size_bytes: backupJson.length,
          created_by: agentId,
          timestamp
        }, null, 2)
      }]
    };

  } catch (error) {
    console.error('Error creating context backup:', error);
    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify({
          error: 'Failed to create context backup',
          details: error instanceof Error ? error.message : String(error)
        }, null, 2)
      }],
      isError: true
    };
  }
}

/**
 * Validate context consistency - ported from Python validate_context_consistency_tool_impl
 */
async function validateContextConsistency(args: Record<string, any>) {
  const { token, fix_issues = false } = args;

  // Authenticate
  const agentId = getAgentId(token);
  if (!agentId) {
    return {
      content: [{
        type: 'text' as const,
        text: "Unauthorized: Valid token required"
      }],
      isError: true
    };
  }

  const db = getDbConnection();

  try {
    const issues: any[] = [];
    const fixes: any[] = [];

    // Get all context entries
    const stmt = db.prepare('SELECT * FROM project_context ORDER BY context_key');
    const entries = stmt.all();

    // Check for JSON parsing issues
    for (const entry of entries as any[]) {
      try {
        JSON.parse(entry.value);
      } catch {
        issues.push({
          type: 'invalid_json',
          context_key: entry.context_key,
          error: 'Value is not valid JSON'
        });

        if (fix_issues) {
          // Try to fix by re-stringifying
          try {
            const fixedValue = JSON.stringify(entry.value);
            const updateStmt = db.prepare('UPDATE project_context SET value = ? WHERE context_key = ?');
            updateStmt.run(fixedValue, entry.context_key);
            fixes.push({
              type: 'fixed_json',
              context_key: entry.context_key,
              action: 'Re-stringified value'
            });
          } catch {
            issues.push({
              type: 'unfixable_json',
              context_key: entry.context_key,
              error: 'Could not fix JSON'
            });
          }
        }
      }
    }

    // Check for orphaned references (agents that no longer exist)
    const agentStmt = db.prepare('SELECT DISTINCT updated_by FROM project_context');
    const contextAgents = agentStmt.all() as { updated_by: string }[];

    for (const contextAgent of contextAgents) {
      if (contextAgent.updated_by === 'admin' || contextAgent.updated_by === 'server_startup') {
        continue; // Skip system entries
      }

      const checkAgentStmt = db.prepare('SELECT agent_id FROM agents WHERE agent_id = ?');
      const agentExists = checkAgentStmt.get(contextAgent.updated_by);

      if (!agentExists) {
        issues.push({
          type: 'orphaned_agent_reference',
          agent_id: contextAgent.updated_by,
          error: 'Context references non-existent agent'
        });
      }
    }

    // Analyze context health
    const health = analyzeContextHealth(entries);

    // Log validation
    const timestamp = new Date().toISOString();
    const actionStmt = db.prepare(`
      INSERT INTO agent_actions (agent_id, action_type, timestamp, details)
      VALUES (?, ?, ?, ?)
    `);

    actionStmt.run(agentId, 'validate_context', timestamp, JSON.stringify({
      issues_found: issues.length,
      fixes_applied: fixes.length,
      fix_issues
    }));

    if (MCP_DEBUG) {
      console.log(`🔍 Context validation: ${issues.length} issues, ${fixes.length} fixes by ${agentId}`);
    }

    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify({
          validation_summary: {
            total_entries: entries.length,
            issues_found: issues.length,
            fixes_applied: fixes.length,
            validation_date: timestamp,
            validated_by: agentId
          },
          context_health: health,
          issues,
          fixes,
          recommendations: health.recommendations
        }, null, 2)
      }]
    };

  } catch (error) {
    console.error('Error validating context consistency:', error);
    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify({
          error: 'Failed to validate context consistency',
          details: error instanceof Error ? error.message : String(error)
        }, null, 2)
      }],
      isError: true
    };
  }
}

// Register all project context tools
registerTool(
  'view_project_context',
  'Smart project context viewer with health analysis, stale entry detection, and advanced filtering. Provides comprehensive insights into context quality and usage.',
  ViewProjectContextSchema,
  viewProjectContext
);

registerTool(
  'update_project_context',
  'Store project context information that all agents can access. Context is stored as JSON and can be retrieved by any authenticated agent.',
  UpdateProjectContextSchema,
  updateProjectContext
);

registerTool(
  'bulk_update_project_context',
  'Update multiple project context entries in a single transaction for efficiency and consistency.',
  BulkUpdateProjectContextSchema,
  bulkUpdateProjectContext
);

registerTool(
  'delete_project_context',
  'Delete a specific project context entry. This action cannot be undone, so use with caution.',
  DeleteProjectContextSchema,
  deleteProjectContext
);

registerTool(
  'backup_project_context',
  'Create a backup snapshot of all project context entries for disaster recovery and version control.',
  BackupProjectContextSchema,
  backupProjectContext
);

registerTool(
  'validate_context_consistency',
  'Validate project context integrity, check for issues like invalid JSON or orphaned references, and optionally fix problems automatically.',
  ValidateContextConsistencySchema,
  validateContextConsistency
);

if (MCP_DEBUG) {
  console.log('✅ Project context tools registered');
}

export { 
  viewProjectContext, 
  updateProjectContext, 
  bulkUpdateProjectContext,
  deleteProjectContext,
  backupProjectContext,
  validateContextConsistency
};