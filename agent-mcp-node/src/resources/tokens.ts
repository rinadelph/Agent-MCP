// MCP Resources for Tokens 
// Provides token data as MCP resources for @ mentions and easy access

import { getDbConnection } from '../db/connection.js';
import { MCP_DEBUG } from '../core/config.js';
import { createColoredResource, ColoredResource } from '../core/resourceColors.js';

// Use the enhanced colored resource interface
export interface TokenResource extends ColoredResource {}

export interface TokenResourceContent {
  uri: string;
  mimeType: string;
  text: string;
}

export interface TokenInfo {
  name: string;
  token: string;
  role: string;
  description: string;
  created_at: string;
  expires_at?: string;
  usage_count?: number;
  last_used?: string;
}

/**
 * Get all available tokens as resources
 */
export async function getTokenResources(): Promise<TokenResource[]> {
  const tokens = await getAvailableTokens();
  
  return tokens.map(token => {
    // Semantic color mapping based on token role
    let color = 'white';
    let status = 'available';
    
    switch (token.role.toLowerCase()) {
      case 'admin':
        color = 'red';
        status = 'critical';
        break;
      case 'agent':
        color = 'magenta';
        status = 'active';
        break;
      case 'monitor':
        color = 'yellow';
        status = 'monitoring';
        break;
      case 'service':
        color = 'cyan';
        status = 'service';
        break;
      case 'api':
        color = 'blue';
        status = 'external';
        break;
      default:
        color = 'white';
        status = 'unknown';
    }
    
    // Try Claude Code-style resource naming patterns
    let resourceName = token.name;
    
    // Try patterns that might trigger Claude Code's coloring
    switch (token.role.toLowerCase()) {
      case 'admin':
        resourceName = `admin-${token.name}`;
        break;
      case 'agent':
        resourceName = `agent-${token.name}`;
        break;
      case 'monitor':
        resourceName = `monitor-${token.name}`;
        break;
      case 'service':
        resourceName = `service-${token.name}`;
        break;
      default:
        resourceName = `token-${token.name}`;
    }
    
    // Get ANSI color code for the name - using orange for admin tokens like Claude Code
    const ansiCode = color === 'red' ? '\x1b[1;38;2;255;165;0m' : // Bold orange for admin (like Claude Code)
                    color === 'magenta' ? '\x1b[1;95m' :   // Bold bright magenta for agents
                    color === 'yellow' ? '\x1b[1;93m' :    // Bold bright yellow for monitors
                    color === 'cyan' ? '\x1b[1;96m' :      // Bold bright cyan for services
                    color === 'blue' ? '\x1b[1;94m' : '\x1b[1;97m'; // Bold bright colors
    
    return {
      uri: `token://${token.name}`,
      name: `${ansiCode}@${token.name}\x1b[0m`,
      description: `${ansiCode}${getRoleEmoji(token.role)} ${token.role}\x1b[0m`,
      mimeType: 'text/plain',
      annotations: {
        color,
        type: 'token',
        status,
        priority: color === 'red' ? 'critical' : 'normal',
        category: 'authentication'
      }
    };
  });
}

/**
 * Get content for a specific token resource
 */
export async function getTokenResourceContent(uri: string): Promise<TokenResourceContent> {
  const tokenName = uri.replace('token://', '');
  const tokens = await getAvailableTokens();
  const token = tokens.find(t => t.name === tokenName);
  
  if (!token) {
    throw new Error(`Token '${tokenName}' not found`);
  }
  
  const content = [
    `Token Name: ${token.name}`,
    `Role: ${token.role}`,
    `Description: ${token.description}`,
    `Token Value: ${token.token}`,
    `Created: ${token.created_at}`,
    token.expires_at ? `Expires: ${token.expires_at}` : 'Expires: Never',
    token.usage_count !== undefined ? `Usage Count: ${token.usage_count}` : '',
    token.last_used ? `Last Used: ${token.last_used}` : 'Last Used: Never',
    '',
    `🔑 Use this token for authentication in MCP tools that require admin privileges.`,
    `📋 Copy the token value above to use with tools like create_background_agent.`,
    '',
    `Example usage:`,
    `create_background_agent({`,
    `  agent_id: "my-agent",`,
    `  mode: "monitoring", `,
    `  objectives: ["system monitoring"],`,
    `  token: "${token.token}"`,
    `})`
  ].filter(Boolean).join('\n');
  
  return {
    uri,
    mimeType: 'text/plain',
    text: content
  };
}

/**
 * Get all available tokens from various sources
 */
async function getAvailableTokens(): Promise<TokenInfo[]> {
  const tokens: TokenInfo[] = [];
  
  try {
    // Get admin token from database
    const db = getDbConnection();
    const adminConfig = db.prepare('SELECT * FROM admin_config LIMIT 1').get() as any;
    
    if (adminConfig?.admin_token) {
      tokens.push({
        name: 'admin',
        token: adminConfig.admin_token,
        role: 'admin',
        description: 'Primary admin token for Agent-MCP system',
        created_at: adminConfig.created_at || new Date().toISOString(),
        usage_count: 0 // Could be tracked in future
      });
    }
    
    // Get agent tokens from agents table
    const agentStmt = db.prepare(`
      SELECT agent_id, token, created_at, status, capabilities 
      FROM agents 
      WHERE status IN ('created', 'active', 'terminated')
      ORDER BY created_at DESC
    `);
    
    const agents = agentStmt.all();
    agents.forEach((agent: any) => {
      if (agent.token) {
        const capabilities = JSON.parse(agent.capabilities || '[]');
        const isBackgroundAgent = capabilities.includes('background-agent');
        
        tokens.push({
          name: `agent-${agent.agent_id}`,
          token: agent.token,
          role: 'agent',
          description: `${isBackgroundAgent ? 'Background' : 'Regular'} agent token for ${agent.agent_id} (${agent.status})`,
          created_at: agent.created_at,
          usage_count: 0 // Could be tracked from agent_actions table
        });
      }
    });
    
    // Environment tokens removed for security - API keys should never be exposed
    
    if (MCP_DEBUG) {
      console.log(`📋 Found ${tokens.length} tokens for resources`);
    }
    
  } catch (error) {
    console.error('Error fetching tokens for resources:', error);
  }
  
  return tokens;
}

// Environment token function removed for security
// API keys and secrets should NEVER be exposed through MCP resources

/**
 * Helper function to get a specific token by name
 */
export async function getTokenByName(name: string): Promise<string | null> {
  const tokens = await getAvailableTokens();
  const token = tokens.find(t => t.name === name || t.name === `agent-${name}`);
  return token?.token || null;
}

/**
 * Helper function to validate if a token exists
 */
export async function validateTokenExists(name: string): Promise<boolean> {
  const token = await getTokenByName(name);
  return token !== null;
}

/**
 * Get token info for display (with masked token)
 */
export async function getTokenInfo(name: string): Promise<TokenInfo | null> {
  const tokens = await getAvailableTokens();
  const token = tokens.find(t => t.name === name);
  
  if (!token) return null;
  
  // Return copy with masked token for display
  return {
    ...token,
    token: `${token.token.substring(0, 8)}...${token.token.substring(token.token.length - 4)}`
  };
}

function getRoleEmoji(role: string): string {
  switch (role.toLowerCase()) {
    case 'admin': return '🔑';
    case 'agent': return '🤖';
    case 'monitor': return '👁️';
    case 'service': return '⚙️';
    case 'api': return '🔌';
    default: return '🎫';
  }
}

console.log('✅ Token resources module loaded');