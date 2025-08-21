// Session persistence utilities for MCP session recovery
// Handles connection drops and long-running agent state preservation

import { getDbConnection } from '../db/connection.js';
import { MCP_DEBUG } from '../core/config.js';
import type { StreamableHTTPServerTransport } from '@modelcontextprotocol/sdk/server/streamableHttp.js';

// Session recovery grace period (10 minutes)
const SESSION_RECOVERY_GRACE_PERIOD_MS = 10 * 60 * 1000;

// Session heartbeat interval (30 seconds)
const SESSION_HEARTBEAT_INTERVAL_MS = 30 * 1000;

// Active heartbeat timers
const heartbeatTimers = new Map<string, NodeJS.Timeout>();

export interface SessionState {
  mcpSessionId: string;
  transportState: any;
  agentContext?: any;
  conversationState?: any;
  workingDirectory?: string;
  metadata?: any;
}

export interface AgentSessionState {
  agentId: string;
  mcpSessionId: string;
  stateKey: string;
  stateValue: any;
  expiresAt?: string;
}

/**
 * Initialize session persistence for a new MCP session
 */
export async function initializeSessionPersistence(
  sessionId: string,
  transport: StreamableHTTPServerTransport,
  workingDirectory?: string
): Promise<void> {
  try {
    const db = getDbConnection();
    const now = new Date().toISOString();
    const gracePeriodExpires = new Date(Date.now() + SESSION_RECOVERY_GRACE_PERIOD_MS).toISOString();
    
    // Serialize minimal transport state (just what we need for recovery)
    const transportState = JSON.stringify({
      sessionId: sessionId,
      created: now,
      // Add other recoverable transport properties as needed
    });
    
    const metadata = JSON.stringify({
      initialized_at: now,
      recovery_enabled: true,
      node_process_pid: process.pid
    });
    
    // Insert session persistence record
    const stmt = db.prepare(`
      INSERT OR REPLACE INTO mcp_session_persistence 
      (mcp_session_id, transport_state, created_at, last_heartbeat, status, 
       grace_period_expires, working_directory, metadata)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `);
    
    stmt.run(
      sessionId,
      transportState,
      now,
      now,
      'active',
      gracePeriodExpires,
      workingDirectory || process.cwd(),
      metadata
    );
    
    // Start heartbeat for this session
    startSessionHeartbeat(sessionId);
    
    if (MCP_DEBUG) {
      console.log(`🔄 Session persistence initialized for: ${sessionId}`);
    }
  } catch (error) {
    console.error(`Error initializing session persistence for ${sessionId}:`, error);
  }
}

/**
 * Update session heartbeat to indicate active connection
 */
export async function updateSessionHeartbeat(sessionId: string): Promise<void> {
  try {
    const db = getDbConnection();
    const now = new Date().toISOString();
    
    const stmt = db.prepare(`
      UPDATE mcp_session_persistence 
      SET last_heartbeat = ?, status = 'active'
      WHERE mcp_session_id = ?
    `);
    
    const result = stmt.run(now, sessionId);
    
    if (MCP_DEBUG && result.changes === 0) {
      console.log(`⚠️ Heartbeat update failed for session: ${sessionId} (session not found)`);
    }
  } catch (error) {
    console.error(`Error updating heartbeat for session ${sessionId}:`, error);
  }
}

/**
 * Mark session as disconnected and start recovery grace period
 */
export async function markSessionDisconnected(sessionId: string): Promise<void> {
  try {
    const db = getDbConnection();
    const now = new Date().toISOString();
    const gracePeriodExpires = new Date(Date.now() + SESSION_RECOVERY_GRACE_PERIOD_MS).toISOString();
    
    const stmt = db.prepare(`
      UPDATE mcp_session_persistence 
      SET status = 'disconnected', disconnected_at = ?, grace_period_expires = ?
      WHERE mcp_session_id = ? AND status != 'expired'
    `);
    
    const result = stmt.run(now, gracePeriodExpires, sessionId);
    
    // Stop heartbeat for disconnected session
    stopSessionHeartbeat(sessionId);
    
    if (result.changes > 0) {
      console.log(`🔌 Session marked as disconnected: ${sessionId} (recovery window: 10 minutes)`);
    }
  } catch (error) {
    console.error(`Error marking session as disconnected ${sessionId}:`, error);
  }
}

/**
 * Check if a session can be recovered (within grace period)
 */
export async function canRecoverSession(sessionId: string): Promise<boolean> {
  try {
    const db = getDbConnection();
    const now = new Date().toISOString();
    
    const result = db.prepare(`
      SELECT status, grace_period_expires, recovery_attempts
      FROM mcp_session_persistence 
      WHERE mcp_session_id = ?
    `).get(sessionId) as any;
    
    if (!result) {
      if (MCP_DEBUG) {
        console.log(`❌ Session not found for recovery: ${sessionId}`);
      }
      return false;
    }
    
    // Check if within grace period
    const gracePeriodExpires = new Date(result.grace_period_expires);
    const isWithinGracePeriod = gracePeriodExpires > new Date();
    
    // Check if not too many recovery attempts
    const hasAttemptsLeft = result.recovery_attempts < 3;
    
    // Must be disconnected or active status
    const canRecover = ['disconnected', 'active'].includes(result.status) && 
                      isWithinGracePeriod && 
                      hasAttemptsLeft;
    
    if (MCP_DEBUG) {
      console.log(`🔍 Recovery check for ${sessionId}: status=${result.status}, ` +
                 `withinGrace=${isWithinGracePeriod}, attempts=${result.recovery_attempts}, ` +
                 `canRecover=${canRecover}`);
    }
    
    return canRecover;
  } catch (error) {
    console.error(`Error checking session recovery for ${sessionId}:`, error);
    return false;
  }
}

/**
 * Recover session state and mark as recovered
 */
export async function recoverSession(sessionId: string): Promise<SessionState | null> {
  try {
    const db = getDbConnection();
    const now = new Date().toISOString();
    
    // Get session data
    const session = db.prepare(`
      SELECT * FROM mcp_session_persistence 
      WHERE mcp_session_id = ?
    `).get(sessionId) as any;
    
    if (!session) {
      return null;
    }
    
    // Increment recovery attempts
    const updateStmt = db.prepare(`
      UPDATE mcp_session_persistence 
      SET status = 'recovered', recovery_attempts = recovery_attempts + 1, last_heartbeat = ?
      WHERE mcp_session_id = ?
    `);
    
    updateStmt.run(now, sessionId);
    
    // Restart heartbeat for recovered session
    startSessionHeartbeat(sessionId);
    
    const sessionState: SessionState = {
      mcpSessionId: sessionId,
      transportState: JSON.parse(session.transport_state),
      agentContext: session.agent_context ? JSON.parse(session.agent_context) : undefined,
      conversationState: session.conversation_state ? JSON.parse(session.conversation_state) : undefined,
      workingDirectory: session.working_directory,
      metadata: session.metadata ? JSON.parse(session.metadata) : undefined
    };
    
    console.log(`✅ Session recovered successfully: ${sessionId} (attempt ${session.recovery_attempts + 1})`);
    
    return sessionState;
  } catch (error) {
    console.error(`Error recovering session ${sessionId}:`, error);
    return null;
  }
}

/**
 * Save agent state for a session
 */
export async function saveAgentSessionState(
  agentId: string,
  sessionId: string,
  stateKey: string,
  stateValue: any,
  expiresAt?: string
): Promise<void> {
  try {
    const db = getDbConnection();
    const now = new Date().toISOString();
    
    const stmt = db.prepare(`
      INSERT OR REPLACE INTO agent_session_state 
      (agent_id, mcp_session_id, state_key, state_value, last_updated, expires_at)
      VALUES (?, ?, ?, ?, ?, ?)
    `);
    
    stmt.run(
      agentId,
      sessionId,
      stateKey,
      JSON.stringify(stateValue),
      now,
      expiresAt
    );
    
    if (MCP_DEBUG) {
      console.log(`💾 Saved agent state: ${agentId}/${sessionId}/${stateKey}`);
    }
  } catch (error) {
    console.error(`Error saving agent session state:`, error);
  }
}

/**
 * Load agent state for a session
 */
export async function loadAgentSessionState(
  agentId: string,
  sessionId: string,
  stateKey: string
): Promise<any | null> {
  try {
    const db = getDbConnection();
    const now = new Date().toISOString();
    
    const result = db.prepare(`
      SELECT state_value FROM agent_session_state 
      WHERE agent_id = ? AND mcp_session_id = ? AND state_key = ?
      AND (expires_at IS NULL OR expires_at > ?)
    `).get(agentId, sessionId, stateKey, now) as any;
    
    if (result) {
      return JSON.parse(result.state_value);
    }
    
    return null;
  } catch (error) {
    console.error(`Error loading agent session state:`, error);
    return null;
  }
}

/**
 * Clean up expired sessions and session state
 */
export async function cleanupExpiredSessions(): Promise<void> {
  try {
    const db = getDbConnection();
    const now = new Date().toISOString();
    
    // Mark expired sessions
    const expireStmt = db.prepare(`
      UPDATE mcp_session_persistence 
      SET status = 'expired'
      WHERE status IN ('disconnected', 'active') AND grace_period_expires < ?
    `);
    
    const expiredResult = expireStmt.run(now);
    
    // Clean up expired agent session state
    const cleanupStmt = db.prepare(`
      DELETE FROM agent_session_state 
      WHERE expires_at IS NOT NULL AND expires_at < ?
    `);
    
    const cleanupResult = cleanupStmt.run(now);
    
    if (MCP_DEBUG && (expiredResult.changes > 0 || cleanupResult.changes > 0)) {
      console.log(`🧹 Cleanup: ${expiredResult.changes} sessions expired, ${cleanupResult.changes} state entries cleaned`);
    }
  } catch (error) {
    console.error('Error during session cleanup:', error);
  }
}

/**
 * Start heartbeat timer for a session
 */
function startSessionHeartbeat(sessionId: string): void {
  // Clear existing timer if any
  stopSessionHeartbeat(sessionId);
  
  const timer = setInterval(async () => {
    await updateSessionHeartbeat(sessionId);
  }, SESSION_HEARTBEAT_INTERVAL_MS);
  
  heartbeatTimers.set(sessionId, timer);
  
  if (MCP_DEBUG) {
    console.log(`💓 Started heartbeat for session: ${sessionId}`);
  }
}

/**
 * Stop heartbeat timer for a session
 */
function stopSessionHeartbeat(sessionId: string): void {
  const timer = heartbeatTimers.get(sessionId);
  if (timer) {
    clearInterval(timer);
    heartbeatTimers.delete(sessionId);
    
    if (MCP_DEBUG) {
      console.log(`💔 Stopped heartbeat for session: ${sessionId}`);
    }
  }
}

/**
 * Get all active sessions with their status
 */
export async function getActiveSessions(): Promise<any[]> {
  try {
    const db = getDbConnection();
    
    const sessions = db.prepare(`
      SELECT mcp_session_id, status, last_heartbeat, disconnected_at, 
             recovery_attempts, grace_period_expires, working_directory
      FROM mcp_session_persistence 
      WHERE status IN ('active', 'disconnected', 'recovered')
      ORDER BY last_heartbeat DESC
    `).all();
    
    return sessions;
  } catch (error) {
    console.error('Error getting active sessions:', error);
    return [];
  }
}

// Start periodic cleanup (every 5 minutes)
setInterval(cleanupExpiredSessions, 5 * 60 * 1000);

console.log('✅ Session persistence utilities loaded');