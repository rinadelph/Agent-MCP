// Authentication system for Agent-MCP Node.js
// Ported from Python core/auth.py
import { randomBytes } from 'crypto';
import { globalState } from './globals.js';
/**
 * Generate a secure random token
 * Ported from Python auth.py generate_token()
 */
export function generateToken() {
    return randomBytes(16).toString('hex');
}
/**
 * Verify if a token is valid and has the required role
 * Ported from Python auth.py verify_token()
 *
 * @param token - The token to verify
 * @param requiredRole - Required role: "admin" or "agent"
 * @returns true if token is valid for the required role
 */
export function verifyToken(token, requiredRole = 'agent') {
    if (!token) {
        return false;
    }
    // Check admin token
    if (requiredRole === 'admin' && token === globalState.adminToken) {
        return true;
    }
    // Check active agents (for agent role)
    if (requiredRole === 'agent' && globalState.activeAgents.has(token)) {
        return true;
    }
    // Allow admin token to be used for agent roles as well
    if (requiredRole === 'agent' && token === globalState.adminToken) {
        return true; // Admins can act as agents
    }
    return false;
}
/**
 * Get agent ID from token
 * Ported from Python auth.py get_agent_id()
 *
 * @param token - The token to look up
 * @returns agent_id if token is valid, null otherwise
 */
export function getAgentId(token) {
    if (!token) {
        return null;
    }
    // Admin token returns special 'admin' agent_id
    if (token === globalState.adminToken) {
        return 'admin';
    }
    // Check active agents
    const agentData = globalState.activeAgents.get(token);
    if (agentData && agentData.agent_id) {
        return agentData.agent_id;
    }
    return null;
}
/**
 * Initialize admin token - generate or load from environment
 * This should be called during server startup
 */
export function initializeAdminToken() {
    // Check if admin token is provided via environment
    const envAdminToken = process.env.MCP_ADMIN_TOKEN;
    if (envAdminToken) {
        globalState.adminToken = envAdminToken;
        console.log('🔑 Admin token loaded from environment');
    }
    else {
        // Generate new admin token
        globalState.adminToken = generateToken();
        console.log('🔑 Generated new admin token:', globalState.adminToken);
        console.log('💡 Set MCP_ADMIN_TOKEN environment variable to persist this token');
    }
    return globalState.adminToken;
}
/**
 * Validate agent token and get agent data
 * @param token - Agent token to validate
 * @returns Agent data if valid, null if invalid
 */
export function validateAgentToken(token) {
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
export function isAdminToken(token) {
    return token === globalState.adminToken;
}
/**
 * Register an active agent in the global state
 * @param token - Agent's authentication token
 * @param agentData - Agent data object
 */
export function registerActiveAgent(token, agentData) {
    globalState.activeAgents.set(token, agentData);
    if (agentData.agent_id && agentData.working_directory) {
        globalState.agentWorkingDirs.set(agentData.agent_id, agentData.working_directory);
    }
}
/**
 * Unregister an active agent from global state
 * @param token - Agent's authentication token
 */
export function unregisterActiveAgent(token) {
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
export function getActiveAgentTokens() {
    return Array.from(globalState.activeAgents.keys());
}
/**
 * Get agent data by agent_id
 * @param agentId - The agent ID to look up
 * @returns Agent data if found, null otherwise
 */
export function getAgentDataById(agentId) {
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
