// File Management Tools for Agent-MCP Node.js
// Prevents conflicts when multiple agents work on the same files

import { z } from 'zod';
import { registerTool } from './registry.js';
import { getDbConnection } from '../db/connection.js';
import { MCP_DEBUG } from '../core/config.js';
import path from 'path';
import fs from 'fs';

// Schemas for file management tools
const CheckFileStatusSchema = z.object({
  filepath: z.string().describe("Path to the file to check status for"),
  agent_id: z.string().optional().describe("Agent ID requesting the check (for context)")
});

const UpdateFileStatusSchema = z.object({
  filepath: z.string().describe("Path to the file to update status for"),
  status: z.enum(['in_use', 'released']).describe("New status for the file"),
  agent_id: z.string().describe("Agent ID making the update"),
  notes: z.string().optional().describe("Optional notes about the file work")
});

interface FileStatus {
  filepath: string;
  status: 'in_use' | 'released';
  agent_id: string;
  locked_at: string;
  released_at?: string;
  notes?: string;
  last_modified?: string;
}

/**
 * Normalize file path to absolute path
 */
function normalizeFilePath(filepath: string, agentId?: string): string {
  // If already absolute, return as-is
  if (path.isAbsolute(filepath)) {
    return path.normalize(filepath);
  }
  
  // If we have an agent ID, get their working directory
  if (agentId) {
    const db = getDbConnection();
    try {
      const stmt = db.prepare('SELECT working_directory FROM agents WHERE agent_id = ?');
      const agent = stmt.get(agentId) as any;
      if (agent && agent.working_directory) {
        return path.normalize(path.join(agent.working_directory, filepath));
      }
    } catch (error) {
      console.error(`Error getting agent working directory for ${agentId}:`, error);
    }
  }
  
  // Default to current working directory
  return path.normalize(path.resolve(filepath));
}

/**
 * Get file system stats if file exists
 */
function getFileStats(filepath: string) {
  try {
    const stats = fs.statSync(filepath);
    return {
      exists: true,
      size: stats.size,
      lastModified: stats.mtime.toISOString(),
      isDirectory: stats.isDirectory()
    };
  } catch (error) {
    return {
      exists: false,
      size: 0,
      lastModified: null,
      isDirectory: false
    };
  }
}

/**
 * Check file status - see if file is being worked on by another agent
 */
async function checkFileStatus(args: Record<string, any>) {
  const { filepath, agent_id } = args;
  const db = getDbConnection();
  
  try {
    const normalizedPath = normalizeFilePath(filepath, agent_id);
    const fileStats = getFileStats(normalizedPath);
    
    // Check current file locks
    const stmt = db.prepare(`
      SELECT fs.*, a.agent_id as agent_name, a.status as agent_status
      FROM file_status fs
      LEFT JOIN agents a ON fs.agent_id = a.agent_id
      WHERE fs.filepath = ? AND fs.status = 'in_use'
      ORDER BY fs.locked_at DESC
      LIMIT 1
    `);
    
    const currentLock = stmt.get(normalizedPath) as any;
    
    // Get file history
    const historyStmt = db.prepare(`
      SELECT fs.*, a.agent_id as agent_name
      FROM file_status fs
      LEFT JOIN agents a ON fs.agent_id = a.agent_id  
      WHERE fs.filepath = ?
      ORDER BY fs.locked_at DESC
      LIMIT 5
    `);
    
    const history = historyStmt.all(normalizedPath);
    
    const result = {
      filepath: normalizedPath,
      file_exists: fileStats.exists,
      file_size: fileStats.size,
      last_modified: fileStats.lastModified,
      is_directory: fileStats.isDirectory,
      status: currentLock ? 'locked' : 'available',
      locked_by: currentLock ? {
        agent_id: currentLock.agent_id,
        agent_status: currentLock.agent_status,
        locked_at: currentLock.locked_at,
        notes: currentLock.notes
      } : null,
      can_edit: !currentLock || currentLock.agent_id === agent_id,
      recent_history: history.map((h: any) => ({
        agent_id: h.agent_id,
        status: h.status,
        locked_at: h.locked_at,
        released_at: h.released_at,
        notes: h.notes
      }))
    };
    
    if (MCP_DEBUG) {
      console.log('📁 File status check:', {
        file: normalizedPath,
        status: result.status,
        locked_by: currentLock?.agent_id
      });
    }
    
    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify(result, null, 2)
      }]
    };
    
  } catch (error) {
    console.error('Error checking file status:', error);
    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify({
          error: 'Failed to check file status',
          details: error instanceof Error ? error.message : String(error)
        }, null, 2)
      }],
      isError: true
    };
  }
}

/**
 * Update file status - lock or release a file
 */
async function updateFileStatus(args: Record<string, any>) {
  const { filepath, status, agent_id, notes } = args;
  const db = getDbConnection();
  
  try {
    const normalizedPath = normalizeFilePath(filepath, agent_id);
    const timestamp = new Date().toISOString();
    
    // Check if agent exists
    const agentStmt = db.prepare('SELECT agent_id, status FROM agents WHERE agent_id = ?');
    const agent = agentStmt.get(agent_id) as any;
    
    if (!agent) {
      return {
        content: [{
          type: 'text' as const,
          text: JSON.stringify({
            success: false,
            error: `Agent ${agent_id} not found`
          }, null, 2)
        }],
        isError: true
      };
    }
    
    if (status === 'in_use') {
      // Check if file is already locked by another agent
      const lockStmt = db.prepare(`
        SELECT agent_id, locked_at, notes 
        FROM file_status 
        WHERE filepath = ? AND status = 'in_use' AND agent_id != ?
      `);
      
      const existingLock = lockStmt.get(normalizedPath, agent_id) as any;
      
      if (existingLock) {
        return {
          content: [{
            type: 'text' as const,
            text: JSON.stringify({
              success: false,
              error: `File is already locked by agent ${existingLock.agent_id}`,
              locked_at: existingLock.locked_at,
              lock_notes: existingLock.notes
            }, null, 2)
          }],
          isError: true
        };
      }
      
      // Release any previous lock by this agent first
      const releaseStmt = db.prepare(`
        UPDATE file_status 
        SET status = 'released', released_at = ?
        WHERE filepath = ? AND agent_id = ? AND status = 'in_use'
      `);
      releaseStmt.run(timestamp, normalizedPath, agent_id);
      
      // Create new lock
      const insertStmt = db.prepare(`
        INSERT INTO file_status (filepath, status, agent_id, locked_at, notes)
        VALUES (?, ?, ?, ?, ?)
      `);
      insertStmt.run(normalizedPath, 'in_use', agent_id, timestamp, notes || null);
      
      if (MCP_DEBUG) {
        console.log(`🔒 File locked: ${normalizedPath} by ${agent_id}`);
      }
      
    } else if (status === 'released') {
      // Release the file
      const updateStmt = db.prepare(`
        UPDATE file_status 
        SET status = 'released', released_at = ?, notes = COALESCE(?, notes)
        WHERE filepath = ? AND agent_id = ? AND status = 'in_use'
      `);
      
      const result = updateStmt.run(timestamp, notes || null, normalizedPath, agent_id);
      
      if (result.changes === 0) {
        return {
          content: [{
            type: 'text' as const,
            text: JSON.stringify({
              success: false,
              error: `No active lock found for ${normalizedPath} by agent ${agent_id}`
            }, null, 2)
          }],
          isError: true
        };
      }
      
      if (MCP_DEBUG) {
        console.log(`🔓 File released: ${normalizedPath} by ${agent_id}`);
      }
    }
    
    // Log the action
    const actionStmt = db.prepare(`
      INSERT INTO agent_actions (agent_id, action_type, timestamp, details)
      VALUES (?, ?, ?, ?)
    `);
    
    actionStmt.run(agent_id, `file_${status}`, timestamp, JSON.stringify({
      filepath: normalizedPath,
      notes: notes
    }));
    
    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify({
          success: true,
          filepath: normalizedPath,
          status: status,
          agent_id: agent_id,
          timestamp: timestamp,
          notes: notes
        }, null, 2)
      }]
    };
    
  } catch (error) {
    console.error('Error updating file status:', error);
    return {
      content: [{
        type: 'text' as const,
        text: JSON.stringify({
          success: false,
          error: 'Failed to update file status',
          details: error instanceof Error ? error.message : String(error)
        }, null, 2)
      }],
      isError: true
    };
  }
}

// Register the file management tools
registerTool(
  'check_file_status',
  'Check if a file is being worked on by another agent to prevent conflicts',
  CheckFileStatusSchema,
  checkFileStatus
);

registerTool(
  'update_file_status',
  'Lock or release a file to coordinate work between agents',
  UpdateFileStatusSchema,
  updateFileStatus
);

if (MCP_DEBUG) {
  console.log('✅ File management tools registered');
}

export { checkFileStatus, updateFileStatus };