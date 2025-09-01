// Token Helper Tools for Agent-MCP
// Provides easy token lookup and validation

import { z } from 'zod';
import { registerTool } from './registry.js';
import { getTokenByName, getTokenInfo, validateTokenExists, getTokenResources } from '../resources/tokens.js';

// List all available tokens
registerTool(
  'list_tokens',
  'List all available tokens with their names, roles, and descriptions. Use this to see what tokens you can @ mention.',
  z.object({
    include_masked: z.boolean().optional().default(true).describe('Include masked token values for reference')
  }),
  async (args, context) => {
    try {
      const tokenResources = await getTokenResources();
      
      if (tokenResources.length === 0) {
        return {
          content: [{
            type: 'text' as const,
            text: '🔑 No tokens found. Make sure the server is properly configured with admin tokens or environment variables.'
          }]
        };
      }
      
      const response = [
        `🔑 **Available Tokens** (${tokenResources.length} found)`,
        '',
        'You can @ mention these tokens in your messages to reference them:',
        ''
      ];
      
      for (const resource of tokenResources) {
        const tokenName = resource.name.replace('@', '');
        const tokenInfo = await getTokenInfo(tokenName);
        
        if (tokenInfo) {
          response.push(`**${resource.name}** - ${tokenInfo.role}`);
          response.push(`  ${tokenInfo.description}`);
          if (args.include_masked) {
            response.push(`  Token: ${tokenInfo.token}`);
          }
          response.push(`  Created: ${new Date(tokenInfo.created_at).toLocaleDateString()}`);
          response.push('');
        }
      }
      
      response.push('💡 **Usage Examples:**');
      response.push('- Type "@admin" to see the admin token details');
      response.push('- Use the token value in tools that require authentication');
      response.push('- Reference environment tokens like "@env-openai" for API keys');
      
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
          text: `❌ Error listing tokens: ${error instanceof Error ? error.message : String(error)}`
        }],
        isError: true
      };
    }
  }
);

// Get a specific token value by name
registerTool(
  'get_token',
  'Get the actual token value for use in other tools. Be careful with token security!',
  z.object({
    name: z.string().describe('Token name (without @ prefix, e.g., "admin", "agent-monitor-01")'),
    show_full: z.boolean().optional().default(false).describe('Show full token value (security risk - use carefully)')
  }),
  async (args, context) => {
    try {
      const { name, show_full } = args;
      
      const tokenValue = await getTokenByName(name);
      const tokenInfo = await getTokenInfo(name);
      
      if (!tokenValue || !tokenInfo) {
        return {
          content: [{
            type: 'text' as const,
            text: `❌ Token '${name}' not found. Use list_tokens to see available tokens.`
          }],
          isError: true
        };
      }
      
      const response = [
        `🔑 **Token: ${name}**`,
        '',
        `**Role:** ${tokenInfo.role}`,
        `**Description:** ${tokenInfo.description}`,
        `**Created:** ${new Date(tokenInfo.created_at).toLocaleDateString()}`,
        ''
      ];
      
      if (show_full) {
        response.push(`**⚠️ FULL TOKEN VALUE:**`);
        response.push(`\`${tokenValue}\``);
        response.push('');
        response.push('🔐 **SECURITY WARNING:** The full token is shown above. Use it carefully and never share it publicly!');
      } else {
        response.push(`**Token (masked):** ${tokenInfo.token}`);
        response.push('');
        response.push('💡 Use `show_full: true` to see the complete token value.');
      }
      
      response.push('');
      response.push('📋 **Copy-paste ready for tools:**');
      response.push(`token: "${tokenValue}"`);
      
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
          text: `❌ Error getting token: ${error instanceof Error ? error.message : String(error)}`
        }],
        isError: true
      };
    }
  }
);

// Validate if a token exists and is accessible
registerTool(
  'validate_token',
  'Check if a token exists and get basic info without exposing the token value.',
  z.object({
    name: z.string().describe('Token name to validate (without @ prefix)')
  }),
  async (args, context) => {
    try {
      const { name } = args;
      
      const exists = await validateTokenExists(name);
      const tokenInfo = await getTokenInfo(name);
      
      if (!exists || !tokenInfo) {
        return {
          content: [{
            type: 'text' as const,
            text: `❌ Token '${name}' not found or inaccessible.\n\nUse list_tokens to see available tokens.`
          }],
          isError: true
        };
      }
      
      const response = [
        `✅ **Token '${name}' is valid**`,
        '',
        `**Role:** ${tokenInfo.role}`,
        `**Description:** ${tokenInfo.description}`,
        `**Token:** ${tokenInfo.token} (masked)`,
        `**Created:** ${new Date(tokenInfo.created_at).toLocaleDateString()}`,
        '',
        '🔑 This token can be used for authentication in MCP tools.'
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
          text: `❌ Error validating token: ${error instanceof Error ? error.message : String(error)}`
        }],
        isError: true
      };
    }
  }
);

console.log('✅ Token helper tools registered');