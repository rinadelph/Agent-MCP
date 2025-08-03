// Tmux utilities for Agent-MCP Node.js
// Ported from Python utils/tmux_utils.py

import { spawn, exec, ChildProcess } from 'child_process';
import { promisify } from 'util';
import path from 'path';
import fs from 'fs';
import { MCP_DEBUG } from '../core/config.js';

const execAsync = promisify(exec);

/**
 * Check if tmux is installed and available
 */
export async function isTmuxAvailable(): Promise<boolean> {
  try {
    const { stdout } = await execAsync('tmux -V');
    return stdout.includes('tmux');
  } catch (error) {
    return false;
  }
}

/**
 * Sanitize session name to be safe for tmux
 * Tmux session names cannot contain: . : [ ] space $ and other special chars
 */
export function sanitizeSessionName(name: string): string {
  // Replace invalid characters with underscores
  let sanitized = name.replace(/[.:\[\]\s$'"`\\]/g, '_');
  // Remove any consecutive underscores
  sanitized = sanitized.replace(/_+/g, '_');
  // Remove leading/trailing underscores
  sanitized = sanitized.replace(/^_+|_+$/g, '');
  // Ensure it starts with alphanumeric
  if (sanitized && sanitized.length > 0 && !/^[a-zA-Z0-9]/.test(sanitized.charAt(0))) {
    sanitized = 'agent_' + sanitized;
  }
  return sanitized || 'agent_session';
}

/**
 * Create a new tmux session with the given name and working directory
 */
export async function createTmuxSession(
  sessionName: string,
  workingDir: string,
  command?: string,
  envVars?: Record<string, string>
): Promise<boolean> {
  if (!await isTmuxAvailable()) {
    console.error('tmux is not available on this system');
    return false;
  }

  // Sanitize session name
  const cleanSessionName = sanitizeSessionName(sessionName);

  // Check if session already exists
  if (await sessionExists(cleanSessionName)) {
    console.warn(`tmux session '${cleanSessionName}' already exists`);
    return false;
  }

  // Ensure working directory exists
  try {
    await fs.promises.mkdir(workingDir, { recursive: true });
  } catch (error) {
    console.error(`Failed to create working directory ${workingDir}:`, error);
    return false;
  }

  try {
    // Build tmux command
    const tmuxCmd = ['tmux', 'new-session', '-d', '-s', cleanSessionName, '-c', workingDir];

    // Add the command to run if provided
    if (command) {
      tmuxCmd.push(command);
    }

    // Build environment for spawn
    const env = envVars ? { ...process.env, ...envVars } : process.env;

    // Execute tmux command
    const result = await new Promise<{ code: number; stderr: string }>((resolve) => {
      const proc: ChildProcess = spawn(tmuxCmd[0]!, tmuxCmd.slice(1), {
        env,
        stdio: ['pipe', 'pipe', 'pipe']
      });

      let stderr = '';
      if (proc.stderr) {
        proc.stderr.on('data', (data: Buffer) => {
          stderr += data.toString();
        });
      }

      proc.on('close', (code: number | null) => {
        resolve({ code: code || 0, stderr });
      });

      proc.on('error', () => {
        resolve({ code: 1, stderr: 'Process error' });
      });

      // Set timeout
      setTimeout(() => {
        if (proc.kill) {
          proc.kill();
        }
        resolve({ code: 1, stderr: 'Timeout' });
      }, 10000);
    });

    if (result.code === 0) {
      if (MCP_DEBUG) {
        console.log(`Created tmux session '${cleanSessionName}' in ${workingDir}`);
      }
      return true;
    } else {
      console.error(`Failed to create tmux session: ${result.stderr}`);
      return false;
    }
  } catch (error) {
    console.error(`Error creating tmux session '${cleanSessionName}':`, error);
    return false;
  }
}

/**
 * Check if a tmux session with the given name exists
 */
export async function sessionExists(sessionName: string): Promise<boolean> {
  if (!await isTmuxAvailable()) {
    return false;
  }

  const cleanSessionName = sanitizeSessionName(sessionName);

  try {
    await execAsync(`tmux has-session -t "${cleanSessionName}"`);
    return true;
  } catch (error) {
    return false;
  }
}

/**
 * List all tmux sessions with detailed information
 */
export async function listTmuxSessions(): Promise<Array<{
  name: string;
  created: string;
  attached: boolean;
  windows: number;
}>> {
  if (!await isTmuxAvailable()) {
    return [];
  }

  try {
    const { stdout, stderr } = await execAsync(
      'tmux list-sessions -F "#{session_name}|#{session_created}|#{session_attached}|#{session_windows}"'
    );

    if (stderr && stderr.includes('no server running')) {
      return []; // No tmux server running, no sessions
    }

    const sessions = [];
    const lines = stdout.trim().split('\n');
    
    for (const line of lines) {
      if (line) {
        const parts = line.split('|');
        if (parts.length >= 4 && parts[0] && parts[1]) {
          sessions.push({
            name: parts[0]!,
            created: parts[1]!,
            attached: parts[2] === '1',
            windows: parseInt(parts[3]!, 10)
          });
        }
      }
    }

    return sessions;
  } catch (error) {
    if (MCP_DEBUG) {
      console.error('Error listing tmux sessions:', error);
    }
    return [];
  }
}

/**
 * Kill a tmux session by name
 */
export async function killTmuxSession(sessionName: string): Promise<boolean> {
  if (!await isTmuxAvailable()) {
    console.error('tmux is not available on this system');
    return false;
  }

  const cleanSessionName = sanitizeSessionName(sessionName);

  if (!await sessionExists(cleanSessionName)) {
    console.warn(`tmux session '${cleanSessionName}' does not exist`);
    return true; // Consider it "successful" if it doesn't exist
  }

  try {
    await execAsync(`tmux kill-session -t "${cleanSessionName}"`);
    if (MCP_DEBUG) {
      console.log(`Killed tmux session '${cleanSessionName}'`);
    }
    return true;
  } catch (error) {
    console.error(`Failed to kill tmux session '${cleanSessionName}':`, error);
    return false;
  }
}

/**
 * Get detailed status information for a specific tmux session
 */
export async function getSessionStatus(sessionName: string): Promise<{
  name: string;
  created: string;
  attached: boolean;
  windows: number;
  sessionId: string;
  exists: boolean;
} | null> {
  if (!await isTmuxAvailable()) {
    return null;
  }

  const cleanSessionName = sanitizeSessionName(sessionName);

  if (!await sessionExists(cleanSessionName)) {
    return null;
  }

  try {
    const { stdout } = await execAsync(
      `tmux display-message -t "${cleanSessionName}" -p "#{session_name}|#{session_created}|#{session_attached}|#{session_windows}|#{session_id}"`
    );

    const parts = stdout.trim().split('|');
    if (parts.length >= 5 && parts[0] && parts[1] && parts[4]) {
      return {
        name: parts[0]!,
        created: parts[1]!,
        attached: parts[2] === '1',
        windows: parseInt(parts[3]!, 10),
        sessionId: parts[4]!,
        exists: true
      };
    }

    return null;
  } catch (error) {
    if (MCP_DEBUG) {
      console.error(`Error getting status for tmux session '${cleanSessionName}':`, error);
    }
    return null;
  }
}

/**
 * Send a command to a tmux session
 */
export async function sendCommandToSession(sessionName: string, command: string): Promise<boolean> {
  if (!await isTmuxAvailable()) {
    return false;
  }

  const cleanSessionName = sanitizeSessionName(sessionName);

  if (!await sessionExists(cleanSessionName)) {
    console.warn(`tmux session '${cleanSessionName}' does not exist`);
    return false;
  }

  try {
    await execAsync(`tmux send-keys -t "${cleanSessionName}" "${command}" Enter`);
    return true;
  } catch (error) {
    if (MCP_DEBUG) {
      console.error(`Error sending command to tmux session '${cleanSessionName}':`, error);
    }
    return false;
  }
}

/**
 * Send a prompt to a tmux session after a delay to allow Claude to start up
 */
export async function sendPromptToSession(
  sessionName: string,
  prompt: string,
  delaySeconds: number = 3
): Promise<boolean> {
  if (!await isTmuxAvailable()) {
    return false;
  }

  const cleanSessionName = sanitizeSessionName(sessionName);

  if (!await sessionExists(cleanSessionName)) {
    console.warn(`tmux session '${cleanSessionName}' does not exist`);
    return false;
  }

  try {
    // Wait for Claude to start up
    if (MCP_DEBUG) {
      console.log(`Waiting ${delaySeconds} seconds for Claude to start up in session '${cleanSessionName}'`);
    }
    await new Promise(resolve => setTimeout(resolve, delaySeconds * 1000));

    // First command: Type the prompt text (without Enter)
    if (MCP_DEBUG) {
      console.log(`Typing prompt to session '${cleanSessionName}'`);
    }
    await execAsync(`tmux send-keys -t "${cleanSessionName}" "${prompt}"`);

    // Small delay between typing and pressing Enter
    await new Promise(resolve => setTimeout(resolve, 500));

    // Second command: Send Enter to execute
    if (MCP_DEBUG) {
      console.log(`Sending Enter to session '${cleanSessionName}'`);
    }
    await execAsync(`tmux send-keys -t "${cleanSessionName}" Enter`);

    if (MCP_DEBUG) {
      console.log(`Successfully sent prompt to tmux session '${cleanSessionName}'`);
    }
    return true;
  } catch (error) {
    console.error(`Error sending prompt to tmux session '${cleanSessionName}':`, error);
    return false;
  }
}


/**
 * Send a prompt to a tmux session asynchronously
 */
export function sendPromptAsync(sessionName: string, prompt: string, delaySeconds: number = 3): void {
  setTimeout(() => {
    sendPromptToSession(sessionName, prompt, delaySeconds);
  }, 0);
}

/**
 * Get the last 4 characters of the admin token for session naming
 */
export function getAdminTokenSuffix(adminToken: string): string {
  if (!adminToken || adminToken.length < 4) {
    return '0000'; // Fallback for invalid tokens
  }
  return adminToken.slice(-4).toLowerCase();
}

/**
 * Generate a smart tmux session name in the format: agent-{suffix}
 * where suffix is the last 4 characters of the admin token
 */
export function generateAgentSessionName(agentId: string, adminToken: string): string {
  const suffix = getAdminTokenSuffix(adminToken);
  // Use agent_id prefix + suffix to make it unique per agent but identifiable
  const cleanAgentId = sanitizeSessionName(agentId);
  return `${cleanAgentId}-${suffix}`;
}

/**
 * Parse an agent session name to extract the agent ID
 */
export function parseAgentSessionName(sessionName: string, adminToken: string): string | null {
  const suffix = getAdminTokenSuffix(adminToken);

  // Check if session name ends with the admin token suffix
  if (!sessionName.endsWith(`-${suffix}`)) {
    return null;
  }

  // Extract agent ID by removing the suffix
  const agentId = sessionName.slice(0, -(`-${suffix}`.length));

  // Basic validation - agent ID should not be empty
  if (!agentId) {
    return null;
  }

  return agentId;
}

/**
 * Discover active agents by scanning tmux sessions for our naming pattern
 */
export async function discoverActiveAgentsFromTmux(adminToken: string): Promise<Array<{
  agentId: string;
  sessionName: string;
  sessionCreated?: string;
  sessionAttached: boolean;
  sessionWindows: number;
  discoveredFromTmux: boolean;
}>> {
  const discoveredAgents = [];

  try {
    const sessions = await listTmuxSessions();
    const suffix = getAdminTokenSuffix(adminToken);

    for (const session of sessions) {
      const sessionName = session.name;

      // Check if this session matches our agent pattern
      const agentId = parseAgentSessionName(sessionName, adminToken);

      if (agentId) {
        discoveredAgents.push({
          agentId,
          sessionName,
          sessionCreated: session.created,
          sessionAttached: session.attached,
          sessionWindows: session.windows,
          discoveredFromTmux: true
        });
        
        if (MCP_DEBUG) {
          console.log(`Discovered agent '${agentId}' in tmux session '${sessionName}'`);
        }
      }
    }

    if (MCP_DEBUG) {
      console.log(`Discovered ${discoveredAgents.length} agents from tmux sessions with suffix '${suffix}'`);
    }
  } catch (error) {
    console.error('Error discovering agents from tmux:', error);
  }

  return discoveredAgents;
}

/**
 * Clean up tmux sessions that don't correspond to active agents
 */
export async function cleanupAgentSessions(activeAgentIds: string[]): Promise<number> {
  if (!await isTmuxAvailable()) {
    return 0;
  }

  const sessions = await listTmuxSessions();
  let cleanedCount = 0;

  // Clean up sessions that start with 'agent_' but aren't in activeAgentIds
  for (const session of sessions) {
    const sessionName = session.name;

    // Check if this looks like an agent session
    if (sessionName.startsWith('agent_') || activeAgentIds.some(agentId => sessionName === sanitizeSessionName(agentId))) {
      // Extract potential agent ID
      const potentialAgentId = sessionName.replace('agent_', '');
      const cleanAgentIds = activeAgentIds.map(aid => sanitizeSessionName(aid));

      if (!cleanAgentIds.includes(sessionName) && !activeAgentIds.includes(potentialAgentId)) {
        if (MCP_DEBUG) {
          console.log(`Cleaning up orphaned agent session: ${sessionName}`);
        }
        if (await killTmuxSession(sessionName)) {
          cleanedCount++;
        }
      }
    }
  }

  return cleanedCount;
}

console.log('✅ Tmux utilities loaded');