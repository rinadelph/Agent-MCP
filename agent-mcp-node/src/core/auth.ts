// Authentication system for Agent-MCP Node.js
// Ported from Python core/auth.py

import { randomBytes } from 'crypto';
import { globalState } from './globals.js';
import { getDbConnection } from '../db/connection.js';

/**
 * Generate a secure random token
 * Ported from Python auth.py generate_token()
 */
export function generateToken(): string {
  return randomBytes(16).toString('hex');
}

/**
 * Verify if a token is valid and has the required role
 * Enhanced with database fallback for better agent recognition
 * 
 * @param token - The token to verify
 * @param requiredRole - Required role: "admin" or "agent" 
 * @returns true if token is valid for the required role
 */
export function verifyToken(token: string, requiredRole: 'admin' | 'agent' = 'agent'): boolean {
  if (!token) {
    return false;
  }
  
  // Check admin token
  if (requiredRole === 'admin' && token === globalState.adminToken) {
    return true;
  }
  
  // For agent role verification
  if (requiredRole === 'agent') {
    // Allow admin token to be used for agent roles
    if (token === globalState.adminToken) {
      return true; // Admins can act as agents
    }
    
    // Check active agents (runtime tracking)
    if (globalState.activeAgents.has(token)) {
      return true;
    }
    
    // Fallback: Check database for agent token
    try {
      const db = getDbConnection();
      const agent = db.prepare('SELECT agent_id FROM agents WHERE token = ?').get(token) as any;
      if (agent) {
        return true; // Agent exists in database
      }
    } catch (error) {
      // Database error, continue to false
    }
  }
  
  return false;
}

/**
 * Get agent ID from token
 * Enhanced with database fallback for better agent recognition
 * 
 * @param token - The token to look up
 * @returns agent_id if token is valid, null otherwise
 */
export function getAgentId(token: string): string | null {
  if (!token) {
    return null;
  }
  
  // Admin token returns special 'admin' agent_id
  if (token === globalState.adminToken) {
    return 'admin';
  }
  
  // Check active agents first (runtime tracking)
  const agentData = globalState.activeAgents.get(token);
  if (agentData && agentData.agent_id) {
    return agentData.agent_id;
  }
  
  // Fallback: Check database for agent token
  try {
    const db = getDbConnection();
    const agent = db.prepare('SELECT agent_id FROM agents WHERE token = ?').get(token) as any;
    if (agent) {
      return agent.agent_id;
    }
  } catch (error) {
    // Database error, continue to null
  }
  
  return null;
}

/**
 * Initialize admin token - load from database or generate and store new one
 * This should be called during server startup
 */
export function initializeAdminToken(): string {
  // First check if admin token is provided via environment (for override)
  const envAdminToken = process.env.MCP_ADMIN_TOKEN;
  
  if (envAdminToken) {
    globalState.adminToken = envAdminToken;
    console.log('🔑 Admin token loaded from environment (override)');
    return globalState.adminToken;
  }
  
  // Try to load existing admin token from database
  try {
    const db = getDbConnection();
    const existingToken = db.prepare(`
      SELECT config_value FROM admin_config 
      WHERE config_key = 'admin_token' 
      LIMIT 1
    `).get();
    
    if (existingToken && (existingToken as any).config_value) {
      globalState.adminToken = (existingToken as any).config_value;
      console.log('🔑 Admin token loaded from database');
      return (existingToken as any).config_value;
    }
  } catch (error) {
    // Database might not be initialized yet, fallback to generation
    console.log('🔑 No existing admin token found, generating new one');
  }
  
  // Generate new admin token and store in database
  globalState.adminToken = generateToken();
  
  try {
    const db = getDbConnection();
    const timestamp = new Date().toISOString();
    
    // Store in admin_config table for persistence
    db.prepare(`
      INSERT OR REPLACE INTO admin_config (config_key, config_value, created_at, updated_at, description)
      VALUES (?, ?, ?, ?, ?)
    `).run(
      'admin_token',
      globalState.adminToken,
      timestamp,
      timestamp,
      'Primary admin token for Agent-MCP server'
    );
    
    console.log('🔑 Generated and stored new admin token:', globalState.adminToken);
  } catch (error) {
    console.error('⚠️ Could not store admin token in database:', error);
    console.log('🔑 Generated admin token (not persisted):', globalState.adminToken);
  }
  
  return globalState.adminToken;
}

/**
 * Validate agent token and get agent data
 * @param token - Agent token to validate
 * @returns Agent data if valid, null if invalid
 */
export function validateAgentToken(token: string): any | null {
  if (!token) {
    return null;
  }
  
  // Admin token is always valid
  if (token === globalState.adminToken) {
    return {
      agent_id: 'admin',
      token: globalState.adminToken,
      capabilities: ['admin'],
      status: 'active',
      isAdmin: true
    };
  }
  
  // Check active agents
  const agentData = globalState.activeAgents.get(token);
  if (agentData) {
    return {
      ...agentData,
      isAdmin: false
    };
  }
  
  return null;
}

/**
 * Check if a token has admin privileges
 * @param token - Token to check
 * @returns true if token has admin privileges
 */
export function isAdminToken(token: string): boolean {
  return token === globalState.adminToken;
}

/**
 * Register an active agent in the global state
 * @param token - Agent's authentication token
 * @param agentData - Agent data object
 */
export function registerActiveAgent(token: string, agentData: any): void {
  globalState.activeAgents.set(token, agentData);
  
  if (agentData.agent_id && agentData.working_directory) {
    globalState.agentWorkingDirs.set(agentData.agent_id, agentData.working_directory);
  }
}

/**
 * Unregister an active agent from global state
 * @param token - Agent's authentication token
 */
export function unregisterActiveAgent(token: string): void {
  const agentData = globalState.activeAgents.get(token);
  
  if (agentData && agentData.agent_id) {
    globalState.agentWorkingDirs.delete(agentData.agent_id);
  }
  
  globalState.activeAgents.delete(token);
}

/**
 * Get all active agent tokens
 * @returns Array of active agent tokens
 */
export function getActiveAgentTokens(): string[] {
  return Array.from(globalState.activeAgents.keys());
}

/**
 * Get agent data by agent_id
 * @param agentId - The agent ID to look up
 * @returns Agent data if found, null otherwise
 */
export function getAgentDataById(agentId: string): any | null {
  // Check for admin
  if (agentId === 'admin') {
    return {
      agent_id: 'admin',
      token: globalState.adminToken,
      capabilities: ['admin'],
      status: 'active',
      isAdmin: true
    };
  }
  
  // Search through active agents
  for (const [token, agentData] of globalState.activeAgents) {
    if (agentData.agent_id === agentId) {
      return { ...agentData, token, isAdmin: false };
    }
  }
  
  return null;
}

console.log('✅ Authentication system loaded');