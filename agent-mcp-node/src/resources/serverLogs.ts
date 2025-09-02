// Server Logs Resource - Only available in debug mode
// Provides access to server terminal output for debugging

import { MCP_DEBUG } from '../core/config.js';
import { execSync } from 'child_process';

export interface ServerLogResource {
  uri: string;
  name: string;
  description: string;
  mimeType: string;
}

/**
 * Get server log resources (only in debug mode)
 */
export async function getServerLogResources(): Promise<ServerLogResource[]> {
  if (!MCP_DEBUG) {
    return []; // Don't expose in production
  }
  
  return [{
    uri: 'logs://server',
    name: '\x1b[1;91m@server-logs\x1b[0m', // Red for debug/critical
    description: '\x1b[1;91m🔴 Live server terminal output (DEBUG MODE)\x1b[0m',
    mimeType: 'text/plain'
  }];
}

/**
 * Get server log content from tmux pane
 */
export async function getServerLogContent(uri: string): Promise<{ uri: string; mimeType: string; text: string }> {
  if (!MCP_DEBUG) {
    throw new Error('Server logs only available in debug mode');
  }
  
  if (uri !== 'logs://server') {
    throw new Error(`Unknown server log resource: ${uri}`);
  }
  
  try {
    // Try to capture the Agent-MCP server pane (session 1, window Agent-MCP, pane 1)
    // This captures the last 500 lines from the server pane
    let serverOutput = '';
    
    try {
      // Try different possible pane locations
      const paneLocations = [
        '1:Agent-MCP.1',      // Session 1, Window Agent-MCP, Pane 1 (second pane)
        ':Agent-MCP.1',        // Current session, Window Agent-MCP, Pane 1
        '1:0.1',               // Session 1, Window 0, Pane 1
        '0:0.1',               // Session 0, Window 0, Pane 1
      ];
      
      for (const pane of paneLocations) {
        try {
          serverOutput = execSync(`tmux capture-pane -t '${pane}' -p -S -500 2>/dev/null || true`, 
            { encoding: 'utf-8', timeout: 5000 }).toString();
          if (serverOutput && serverOutput.length > 100) {
            console.log(`📋 Captured server logs from pane ${pane}`);
            break;
          }
        } catch (e) {
          // Try next pane
        }
      }
      
      if (!serverOutput) {
        // Fallback: Try to find any pane running agentMcpServer
        const sessions = execSync('tmux list-panes -a -F "#{session_name}:#{window_index}.#{pane_index} #{pane_current_command}"', 
          { encoding: 'utf-8' }).toString();
        
        const serverPane = sessions.split('\n').find(line => 
          line.includes('node') || line.includes('tsx') || line.includes('agentMcpServer')
        );
        
        if (serverPane) {
          const paneId = serverPane.split(' ')[0];
          serverOutput = execSync(`tmux capture-pane -t '${paneId}' -p -S -500`, 
            { encoding: 'utf-8' }).toString();
        }
      }
    } catch (error) {
      serverOutput = `Error capturing tmux pane: ${error}\n\nMake sure the server is running in a tmux pane.`;
    }
    
    if (!serverOutput) {
      serverOutput = 'No server output found. Make sure the Agent-MCP server is running in tmux.';
    }
    
    const content = [
      '='.repeat(80),
      '📋 AGENT-MCP SERVER LOGS (Last 500 lines)',
      '='.repeat(80),
      '',
      serverOutput,
      '',
      '='.repeat(80),
      '💡 Tips:',
      '- This shows the last 500 lines from the server terminal',
      '- Look for error messages, stack traces, or unusual output',
      '- Check for "Error", "SqliteError", "TypeError" patterns',
      '- Review recent agent launches and task completions',
      '='.repeat(80)
    ].join('\n');
    
    return {
      uri,
      mimeType: 'text/plain',
      text: content
    };
    
  } catch (error) {
    return {
      uri,
      mimeType: 'text/plain',
      text: `Error retrieving server logs: ${error}\n\nEnsure the server is running in tmux.`
    };
  }
}

console.log('✅ Server logs resource module loaded (DEBUG MODE ONLY)');