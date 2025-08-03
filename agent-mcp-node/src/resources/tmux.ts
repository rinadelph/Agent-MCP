// MCP Resources for Tmux Sessions
// Provides tmux session data as MCP resources for @ mentions

import { execSync } from 'child_process';
import { MCP_DEBUG } from '../core/config.js';

// Resource interfaces
export interface TmuxResource {
  uri: string;
  name: string;
  description: string;
  mimeType: string;
}

export interface TmuxResourceContent {
  uri: string;
  mimeType: string;
  text: string;
}

interface TmuxSession {
  name: string;
  windows: number;
  attached: boolean;
  created: string;
  lastActivity: string;
  size: string;
}

interface TmuxPane {
  sessionName: string;
  windowIndex: number;
  paneIndex: number;
  command: string;
  size: string;
  active: boolean;
  title: string;
}

/**
 * Get all tmux sessions
 */
function getTmuxSessions(): TmuxSession[] {
  try {
    // Get tmux sessions with format: name:windows:attached:created:activity:size
    const output = execSync('tmux list-sessions -F "#{session_name}:#{session_windows}:#{session_attached}:#{session_created}:#{session_activity}:#{session_width}x#{session_height}"', 
      { encoding: 'utf8', timeout: 5000 }).trim();
    
    if (!output) return [];
    
    return output.split('\n').map(line => {
      const [name, windows, attached, created, activity, size] = line.split(':');
      return {
        name: name!,
        windows: parseInt(windows!),
        attached: attached === '1',
        created: new Date(parseInt(created!) * 1000).toLocaleString(),
        lastActivity: new Date(parseInt(activity!) * 1000).toLocaleString(),
        size: size!
      };
    });
  } catch (error) {
    if (MCP_DEBUG) {
      console.error('Error getting tmux sessions:', error);
    }
    return [];
  }
}

/**
 * Get tmux session content/logs
 */
function getTmuxSessionContent(sessionName: string): string | null {
  try {
    // Get session info
    const sessionInfo = execSync(`tmux display-message -t "${sessionName}" -p "#{session_name}:#{session_windows}:#{session_attached}:#{session_created}:#{session_activity}:#{session_width}x#{session_height}"`, 
      { encoding: 'utf8', timeout: 3000 }).trim();
    
    const [name, windows, attached, created, activity, size] = sessionInfo.split(':');
    
    // Get window list
    const windowsOutput = execSync(`tmux list-windows -t "${sessionName}" -F "#{window_index}: #{window_name} (#{window_panes} panes) #{?window_active,[ACTIVE],}"`, 
      { encoding: 'utf8', timeout: 3000 }).trim();
    
    // Get recent pane content (last 50 lines)
    let paneContent = '';
    try {
      paneContent = execSync(`tmux capture-pane -t "${sessionName}" -p -S -50`, 
        { encoding: 'utf8', timeout: 3000 });
    } catch {
      paneContent = 'Unable to capture pane content';
    }
    
    // Get pane list
    let panesList = '';
    try {
      panesList = execSync(`tmux list-panes -t "${sessionName}" -F "Pane #{pane_index}: #{pane_current_command} (#{pane_width}x#{pane_height}) #{?pane_active,[ACTIVE],}"`, 
        { encoding: 'utf8', timeout: 3000 }).trim();
    } catch {
      panesList = 'Unable to list panes';
    }
    
    return JSON.stringify({
      "🖥️  Session": sessionName,
      "📊 Status": attached === '1' ? '🟢 attached' : '🔴 detached',
      "📏 Size": size,
      "🪟 Windows": parseInt(windows!),
      "🕒 Created": new Date(parseInt(created!) * 1000).toLocaleString(),
      "⏰ Last Activity": new Date(parseInt(activity!) * 1000).toLocaleString(),
      "─────────────────": "─────────────────",
      "🔧 COMMANDS": "─────────────────",
      "Attach": `tmux attach-session -t "${sessionName}"`,
      "Kill Session": `tmux kill-session -t "${sessionName}"`,
      "New Window": `tmux new-window -t "${sessionName}"`,
      "List Windows": `tmux list-windows -t "${sessionName}"`,
      "Capture Logs": `tmux capture-pane -t "${sessionName}" -p`,
      "─────────────────1": "─────────────────", 
      "🪟 WINDOWS": windowsOutput || 'No windows found',
      "─────────────────2": "─────────────────",
      "📄 PANES": panesList || 'No panes found',
      "─────────────────3": "─────────────────",
      "📝 RECENT OUTPUT (last 50 lines)": paneContent || 'No output captured'
    }, null, 2);
    
  } catch (error) {
    if (MCP_DEBUG) {
      console.error(`Error getting tmux session content for ${sessionName}:`, error);
    }
    return null;
  }
}

/**
 * Get all tmux panes for all sessions
 */
function getAllTmuxPanes(): TmuxPane[] {
  try {
    // Get all panes across all sessions
    const output = execSync('tmux list-panes -a -F "#{session_name}:#{window_index}:#{pane_index}:#{pane_current_command}:#{pane_width}x#{pane_height}:#{?pane_active,1,0}:#{pane_title}"', 
      { encoding: 'utf8', timeout: 5000 }).trim();
    
    if (!output) return [];
    
    return output.split('\n').map(line => {
      const [sessionName, windowIndex, paneIndex, command, size, active, title] = line.split(':');
      return {
        sessionName: sessionName!,
        windowIndex: parseInt(windowIndex!),
        paneIndex: parseInt(paneIndex!),
        command: command!,
        size: size!,
        active: active === '1',
        title: title || `${sessionName}:${windowIndex}.${paneIndex}`
      };
    });
  } catch (error) {
    if (MCP_DEBUG) {
      console.error('Error getting tmux panes:', error);
    }
    return [];
  }
}

/**
 * Get tmux pane content/logs
 */
function getTmuxPaneContent(sessionName: string, windowIndex: number, paneIndex: number): string | null {
  try {
    const target = `${sessionName}:${windowIndex}.${paneIndex}`;
    
    // Get pane info
    const paneInfo = execSync(`tmux display-message -t "${target}" -p "#{session_name}:#{window_index}:#{pane_index}:#{pane_current_command}:#{pane_width}x#{pane_height}:#{?pane_active,1,0}:#{pane_title}:#{pane_pid}"`, 
      { encoding: 'utf8', timeout: 3000 }).trim();
    
    const [name, wIndex, pIndex, command, size, active, title, pid] = paneInfo.split(':');
    
    // Get pane content (last 100 lines)
    let paneContent = '';
    try {
      paneContent = execSync(`tmux capture-pane -t "${target}" -p -S -100`, 
        { encoding: 'utf8', timeout: 5000 });
    } catch {
      paneContent = 'Unable to capture pane content';
    }
    
    return JSON.stringify({
      "🖼️  Pane": `${sessionName}:${windowIndex}.${paneIndex}`,
      "📋 Title": title || `${sessionName}:${windowIndex}.${paneIndex}`,
      "⚡ Command": command,
      "🆔 PID": pid,
      "📏 Size": size,
      "📊 Status": active === '1' ? '🟢 active' : '⚪ inactive',
      "─────────────────": "─────────────────",
      "🔧 COMMANDS": "─────────────────",
      "Attach to Session": `tmux attach-session -t "${sessionName}"`,
      "Select Pane": `tmux select-pane -t "${target}"`,
      "Kill Pane": `tmux kill-pane -t "${target}"`,
      "Split Horizontal": `tmux split-window -t "${target}" -h`,
      "Split Vertical": `tmux split-window -t "${target}" -v`,
      "Capture Full": `tmux capture-pane -t "${target}" -p`,
      "Send Keys": `tmux send-keys -t "${target}" "your-command" Enter`,
      "─────────────────1": "─────────────────",
      "📝 PANE OUTPUT (last 100 lines)": paneContent || 'No output captured'
    }, null, 2);
    
  } catch (error) {
    if (MCP_DEBUG) {
      console.error(`Error getting tmux pane content for ${sessionName}:${windowIndex}.${paneIndex}:`, error);
    }
    return null;
  }
}

/**
 * Get all tmux sessions and panes as resources
 */
export async function getTmuxResources(): Promise<TmuxResource[]> {
  try {
    const sessions = getTmuxSessions();
    const panes = getAllTmuxPanes();
    const resources: TmuxResource[] = [];
    
    // Add session resources
    sessions.forEach(session => {
      let statusDescription = '';
      
      if (session.attached) {
        statusDescription = `🟢 attached (${session.windows} windows)`;
      } else {
        statusDescription = `🔴 detached (${session.windows} windows)`;
      }
      
      resources.push({
        uri: `tmux://session/${session.name}`,
        name: `@${session.name}`,
        description: statusDescription,
        mimeType: 'application/json'
      });
    });
    
    // Add pane resources
    panes.forEach(pane => {
      const paneTarget = `${pane.sessionName}:${pane.windowIndex}.${pane.paneIndex}`;
      let statusDescription = '';
      
      if (pane.active) {
        statusDescription = `🟢 ${pane.command} (active)`;
      } else {
        statusDescription = `⚪ ${pane.command}`;
      }
      
      resources.push({
        uri: `tmux://pane/${paneTarget}`,
        name: `@${paneTarget}`,
        description: statusDescription,
        mimeType: 'application/json'
      });
    });
    
    return resources;
  } catch (error) {
    console.error('Error fetching tmux resources:', error);
    return [];
  }
}

/**
 * Get detailed tmux session or pane information as resource content
 */
export async function getTmuxResourceContent(identifier: string): Promise<TmuxResourceContent | null> {
  try {
    // Check if it's a pane identifier (contains dots) or session
    if (identifier.includes(':') && identifier.includes('.')) {
      // It's a pane: session:window.pane
      const parts = identifier.split(':');
      const sessionName = parts[0]!;
      const windowPane = parts[1]!.split('.');
      const windowIndex = parseInt(windowPane[0]!);
      const paneIndex = parseInt(windowPane[1]!);
      
      const content = getTmuxPaneContent(sessionName, windowIndex, paneIndex);
      
      if (!content) {
        return null;
      }
      
      return {
        uri: `tmux://pane/${identifier}`,
        mimeType: 'application/json',
        text: content
      };
    } else {
      // It's a session
      const content = getTmuxSessionContent(identifier);
      
      if (!content) {
        return null;
      }
      
      return {
        uri: `tmux://session/${identifier}`,
        mimeType: 'application/json',
        text: content
      };
    }
  } catch (error) {
    console.error(`Error fetching tmux content for ${identifier}:`, error);
    return null;
  }
}

if (MCP_DEBUG) {
  console.log('✅ Tmux resources module loaded');
}