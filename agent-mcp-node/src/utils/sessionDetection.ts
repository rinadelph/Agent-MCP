// Session detection utilities for intelligent admin routing
// Detects admin's current Claude Code session for assistance request routing

import { exec } from 'child_process';
import { promisify } from 'util';
import { getDbConnection } from '../db/connection.js';
import { MCP_DEBUG } from '../core/config.js';

const execAsync = promisify(exec);

/**
 * Detect the admin's active Claude Code tmux session by looking for admin token usage
 */
export async function detectCallingTmuxSession(): Promise<string | null> {
  // This is a placeholder - the real detection happens in detectAdminSessionByToken
  // which is called with the actual admin token from the tool registry
  return await getAdminActiveSession();
}

/**
 * Detect admin session by looking for admin token in tmux session output
 */
export async function detectAdminSessionByToken(adminToken: string): Promise<string | null> {
  try {
    if (!adminToken || adminToken.length < 10) {
      if (MCP_DEBUG) {
        console.log('🔍 Invalid or missing admin token for session detection');
      }
      return null;
    }

    // Get all tmux sessions with their attachment status
    const { stdout } = await execAsync('tmux list-sessions -F "#{session_name}:#{session_attached}"');
    const sessions = stdout.split('\n').filter(line => line.trim());
    
    const sessionCandidates: { 
      name: string; 
      attached: boolean; 
      tokenCount: number; 
      score: number;
      lastTokenSeen?: string;
    }[] = [];
    
    for (const sessionLine of sessions) {
      const [name, attachedStr] = sessionLine.split(':');
      if (!name) continue;
      
      const attached = attachedStr === '1';
      
      try {
        // Capture the session output and count admin token occurrences
        const { stdout: sessionOutput } = await execAsync(`tmux capture-pane -t "${name}" -p`);
        
        // Count occurrences of the admin token (escape regex special characters)
        const escapedToken = adminToken.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const tokenMatches = sessionOutput.match(new RegExp(escapedToken, 'g'));
        const tokenCount = tokenMatches ? tokenMatches.length : 0;
        
        // Calculate score based on token usage and session status
        let score = tokenCount * 100; // Base score from token usage
        
        if (attached) score += 50; // Boost for attached sessions
        if (tokenCount > 0) score += 25; // Boost for any token presence
        
        // Extra boost for sessions with admin-related names
        if (name.toLowerCase().includes('agent')) score += 10;
        if (name.toLowerCase().includes('claude')) score += 10;
        if (name.toLowerCase().includes('mcp')) score += 5;
        
        // Get timestamp of most recent token usage (rough approximation)
        let lastTokenSeen;
        if (tokenCount > 0) {
          lastTokenSeen = new Date().toISOString(); // Recent usage assumed
        }
        
        sessionCandidates.push({
          name,
          attached,
          tokenCount,
          score,
          lastTokenSeen
        });
        
        if (MCP_DEBUG && tokenCount > 0) {
          console.log(`🔍 Session "${name}": ${tokenCount} token occurrences, attached: ${attached}, score: ${score}`);
        }
        
      } catch (error) {
        if (MCP_DEBUG) {
          console.log(`⚠️ Could not inspect session "${name}": ${error instanceof Error ? error.message : String(error)}`);
        }
        // Still add to candidates with zero score - no boost for attachment without token
        sessionCandidates.push({
          name,
          attached,
          tokenCount: 0,
          score: 0 // No score boost for sessions without valid token usage
        });
      }
    }
    
    // Sort by score (highest first), then by attachment status
    sessionCandidates.sort((a, b) => {
      if (b.score !== a.score) return b.score - a.score;
      if (a.attached !== b.attached) return a.attached ? -1 : 1;
      return 0;
    });
    
    if (MCP_DEBUG) {
      console.log(`📊 Session detection results:`, 
        sessionCandidates
          .filter(s => s.score > 0)
          .map(s => `${s.name}(tokens:${s.tokenCount}, score:${s.score}, attached:${s.attached})`)
          .join(', ')
      );
    }
    
    // Return the best candidate if it has valid token usage
    const bestCandidate = sessionCandidates[0];
    if (bestCandidate && bestCandidate.tokenCount > 0) {
      if (MCP_DEBUG) {
        console.log(`🎯 Selected admin session: "${bestCandidate.name}" (${bestCandidate.tokenCount} token uses, attached: ${bestCandidate.attached})`);
      }
      return bestCandidate.name;
    }
    
    if (MCP_DEBUG) {
      console.log('🔍 No suitable admin session found - no token usage detected');
    }
    return null;
    
  } catch (error) {
    if (MCP_DEBUG) {
      console.error('Error detecting admin session by token:', error);
    }
    return null;
  }
}

/**
 * Detect agent session by scanning tmux sessions for agent token usage
 * Similar to admin detection but with agent-specific scoring
 */
export async function detectAgentSessionByToken(agentToken: string, agentId?: string): Promise<string | null> {
  try {
    if (!agentToken || agentToken.length < 10) {
      if (MCP_DEBUG) {
        console.log('🤖 Invalid or missing agent token for session detection');
      }
      return null;
    }

    // Get all tmux sessions with their attachment status
    const { stdout } = await execAsync('tmux list-sessions -F "#{session_name}:#{session_attached}"');
    const sessions = stdout.split('\n').filter(line => line.trim());
    
    const sessionCandidates: { 
      name: string; 
      attached: boolean; 
      tokenCount: number; 
      score: number;
      lastTokenSeen?: string;
    }[] = [];
    
    for (const sessionLine of sessions) {
      const [name, attachedStr] = sessionLine.split(':');
      if (!name) continue;
      
      const attached = attachedStr === '1';
      
      try {
        // Capture the session output and count agent token occurrences
        const { stdout: sessionOutput } = await execAsync(`tmux capture-pane -t "${name}" -p`);
        
        // Count occurrences of the agent token
        const tokenMatches = sessionOutput.match(new RegExp(agentToken, 'g'));
        const tokenCount = tokenMatches ? tokenMatches.length : 0;
        
        // Calculate score based on token usage and session characteristics
        let score = tokenCount * 100; // Base score from token usage
        
        if (attached) score += 50; // Boost for attached sessions
        if (tokenCount > 0) score += 25; // Boost for any token presence
        
        // Strong bonus for sessions matching agent ID
        if (agentId && name.includes(agentId)) {
          score += 200; // High bonus for exact agent session match
        }
        
        // Bonus for agent-like session names
        if (name.includes('agent') || name.includes('148f')) {
          score += 25;
        }
        
        // Penalty for admin-like sessions (avoid false positives during agent creation)
        if (name.toLowerCase().includes('admin') || 
            (name.toLowerCase().includes('claude') && !name.includes('agent'))) {
          score -= 100; // This is likely agent creation in admin session, not agent working
        }
        
        // Get timestamp of most recent token usage
        let lastTokenSeen;
        if (tokenCount > 0) {
          lastTokenSeen = new Date().toISOString(); // Recent usage assumed
        }
        
        sessionCandidates.push({
          name,
          attached,
          tokenCount,
          score,
          lastTokenSeen
        });
        
        if (MCP_DEBUG && tokenCount > 0) {
          console.log(`🤖 Agent session "${name}": ${tokenCount} token occurrences, attached: ${attached}, score: ${score}`);
        }
        
      } catch (error) {
        if (MCP_DEBUG) {
          console.log(`⚠️ Could not inspect session "${name}": ${error instanceof Error ? error.message : String(error)}`);
        }
        // Still add to candidates with zero score
        sessionCandidates.push({
          name,
          attached,
          tokenCount: 0,
          score: 0
        });
      }
    }
    
    // Sort by score (highest first), then by attachment status
    sessionCandidates.sort((a, b) => {
      if (b.score !== a.score) return b.score - a.score;
      if (a.attached !== b.attached) return a.attached ? -1 : 1;
      return 0;
    });
    
    if (MCP_DEBUG) {
      console.log(`🤖 Agent session detection results:`, 
        sessionCandidates
          .filter(s => s.score > 0)
          .map(s => `${s.name}(tokens:${s.tokenCount}, score:${s.score}, attached:${s.attached})`)
          .join(', ')
      );
    }
    
    // Return the best candidate if it has positive score (token usage or agent name match)
    const bestCandidate = sessionCandidates[0];
    if (bestCandidate && bestCandidate.score > 0) {
      if (MCP_DEBUG) {
        console.log(`🎯 Selected agent session: "${bestCandidate.name}" (${bestCandidate.tokenCount} token uses, attached: ${bestCandidate.attached})`);
      }
      return bestCandidate.name;
    }
    
    if (MCP_DEBUG) {
      console.log('🤖 No suitable agent session found - no token usage detected');
    }
    return null;
    
  } catch (error) {
    if (MCP_DEBUG) {
      console.error('Error detecting agent session by token:', error);
    }
    return null;
  }
}

/**
 * Check if a process is in the ancestry of another process
 */
function isProcessInTree(targetPid: number, rootPid: number, processLines: string[]): boolean {
  const processMap = new Map<number, number>(); // pid -> ppid
  
  for (const line of processLines) {
    const parts = line.trim().split(/\s+/);
    if (parts.length >= 2 && parts[0] && parts[1]) {
      const pid = parseInt(parts[0]);
      const ppid = parseInt(parts[1]);
      if (!isNaN(pid) && !isNaN(ppid)) {
        processMap.set(pid, ppid);
      }
    }
  }
  
  // Walk up the process tree from targetPid
  let currentPid = targetPid;
  const visited = new Set<number>();
  
  while (currentPid && currentPid !== 1 && !visited.has(currentPid)) {
    if (currentPid === rootPid) {
      return true;
    }
    
    visited.add(currentPid);
    const parentPid = processMap.get(currentPid);
    if (!parentPid) break;
    currentPid = parentPid;
  }
  
  return false;
}

/**
 * Update admin's current session in the database
 */
export async function updateAdminSession(sessionName: string): Promise<void> {
  try {
    const db = getDbConnection();
    const timestamp = new Date().toISOString();
    
    // Update or insert admin session record
    const stmt = db.prepare(`
      INSERT OR REPLACE INTO claude_code_sessions 
      (session_id, pid, parent_pid, first_detected, last_activity, working_directory, agent_id, status, metadata)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);
    
    const metadata = JSON.stringify({
      type: 'admin_session',
      detected_via: 'tool_call',
      updated_by: 'session_detection'
    });
    
    stmt.run(
      `admin_${sessionName}`,
      process.pid,
      process.ppid || 0,
      timestamp,
      timestamp,
      process.cwd(),
      'admin',
      'active',
      metadata
    );
    
    if (MCP_DEBUG) {
      console.log(`📋 Updated admin session: ${sessionName}`);
    }
  } catch (error) {
    console.error('Error updating admin session:', error);
  }
}

/**
 * Get the admin's current active session
 */
export async function getAdminActiveSession(): Promise<string | null> {
  try {
    const db = getDbConnection();
    
    const result = db.prepare(`
      SELECT session_id, last_activity 
      FROM claude_code_sessions 
      WHERE agent_id = 'admin' AND status = 'active'
      ORDER BY last_activity DESC 
      LIMIT 1
    `).get() as any;
    
    if (result) {
      // Extract session name from session_id (format: admin_sessionName)
      const sessionName = result.session_id.replace('admin_', '');
      
      // Check if session is still active (within last 10 minutes)
      const lastActivity = new Date(result.last_activity);
      const now = new Date();
      const minutesAgo = (now.getTime() - lastActivity.getTime()) / (1000 * 60);
      
      if (minutesAgo < 10) {
        return sessionName;
      } else {
        if (MCP_DEBUG) {
          console.log(`🕒 Admin session ${sessionName} is stale (${minutesAgo.toFixed(1)} minutes old)`);
        }
      }
    }
    
    return null;
  } catch (error) {
    console.error('Error getting admin active session:', error);
    return null;
  }
}

/**
 * Send a message to the admin's current tmux session
 */
export async function sendMessageToAdminSession(message: string, priority: 'low' | 'normal' | 'high' | 'urgent' = 'high'): Promise<boolean> {
  let sessionName = await getAdminActiveSession();
  
  // If no session found in database, try to detect using token scan
  if (!sessionName) {
    if (MCP_DEBUG) {
      console.log('📭 No active admin session in database, attempting token-based detection...');
    }
    
    // Try to get admin token from environment or recent activity
    const adminToken = process.env.SERVER_ADMIN_TOKEN;
    if (adminToken) {
      sessionName = await detectAdminSessionByToken(adminToken);
      
      if (sessionName) {
        // Update database with discovered session
        await updateAdminSession(sessionName);
        if (MCP_DEBUG) {
          console.log(`🔍 Detected admin session via token scan: ${sessionName}`);
        }
      }
    }
  }
  
  if (!sessionName) {
    if (MCP_DEBUG) {
      console.log('📭 No active admin session found for message delivery');
    }
    return false;
  }
  
  try {
    // Format the message with priority styling
    const priorityIcon = {
      low: '📘',
      normal: '📨', 
      high: '🔔',
      urgent: '🚨'
    }[priority];
    
    const formattedMessage = `
${priorityIcon} **ASSISTANCE REQUEST** (${priority.toUpperCase()})
Time: ${new Date().toLocaleString()}

${message}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
`;
    
    // Use both display-message (for immediate notification) and send-keys (for chat history)
    
    // 1. First show an immediate notification that works regardless of tmux mode
    const shortNotification = `${priorityIcon} ASSISTANCE REQUEST from agent - check chat for details`;
    await execAsync(`tmux display-message -t "${sessionName}" "${shortNotification}"`);
    
    // 2. Then try to send to chat, handling different tmux modes
    try {
      // Check if session is in copy mode
      const { stdout: sessionInfo } = await execAsync(`tmux display-message -t "${sessionName}" -p "#{pane_in_mode}"`);
      const inMode = sessionInfo.trim() === '1';
      
      if (inMode) {
        // Exit copy mode first
        await execAsync(`tmux send-keys -t "${sessionName}" Escape`);
        await new Promise(resolve => setTimeout(resolve, 100));
      }
      
      // Send the full message to chat using two separate commands
      const escapedMessage = formattedMessage.replace(/\\/g, '\\\\').replace(/"/g, '\\"');
      await execAsync(`tmux send-keys -t "${sessionName}" "${escapedMessage}"`);
      await execAsync(`tmux send-keys -t "${sessionName}" Enter`);
      
    } catch (error) {
      // Fallback: just send without mode checking using two separate commands
      const escapedMessage = formattedMessage.replace(/\\/g, '\\\\').replace(/"/g, '\\"');
      await execAsync(`tmux send-keys -t "${sessionName}" "${escapedMessage}"`);
      await execAsync(`tmux send-keys -t "${sessionName}" Enter`);
    }
    
    if (MCP_DEBUG) {
      console.log(`✅ Sent assistance request to admin session: ${sessionName}`);
    }
    
    return true;
  } catch (error) {
    console.error(`Error sending message to admin session ${sessionName}:`, error);
    return false;
  }
}

console.log('✅ Session detection utilities loaded');