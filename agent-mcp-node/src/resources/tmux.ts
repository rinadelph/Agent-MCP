// MCP Resources for Tmux Sessions
// Provides tmux session data as MCP resources for @ mentions

import { execSync } from 'child_process';
import { MCP_DEBUG } from '../core/config.js';
import { createColoredResource, ColoredResource } from '../core/resourceColors.js';

// Use the enhanced colored resource interface
export interface TmuxResource extends ColoredResource {}

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
  lastActivity: string; // Unix timestamp as string
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
        lastActivity: activity!,
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
      "\x1b[96m🖥️  Session\x1b[0m (cyan)": sessionName,
      "\x1b[92m📊 Status\x1b[0m (green)": attached === '1' ? '🟢 attached' : '🔴 detached',
      "\x1b[93m📏 Size\x1b[0m (yellow)": size,
      "\x1b[94m🪟 Windows\x1b[0m (blue)": parseInt(windows!),
      "\x1b[95m🕒 Created\x1b[0m (magenta)": new Date(parseInt(created!) * 1000).toLocaleString(),
      "\x1b[91m⏰ Last Activity\x1b[0m (red)": new Date(parseInt(activity!) * 1000).toLocaleString(),
      "─────────────────": "─────────────────",
      "\x1b[97m🔧 COMMANDS\x1b[0m (white)": "─────────────────",
      "Attach": `tmux attach-session -t "${sessionName}"`,
      "Kill Session": `tmux kill-session -t "${sessionName}"`,
      "New Window": `tmux new-window -t "${sessionName}"`,
      "List Windows": `tmux list-windows -t "${sessionName}"`,
      "Capture Logs": `tmux capture-pane -t "${sessionName}" -p`,
      "─────────────────1": "─────────────────", 
      "\x1b[94m🪟 WINDOWS\x1b[0m (blue)": windowsOutput || 'No windows found',
      "─────────────────2": "─────────────────",
      "\x1b[95m📄 PANES\x1b[0m (magenta)": panesList || 'No panes found',
      "─────────────────3": "─────────────────",
      "\x1b[92m📝 RECENT OUTPUT (last 50 lines)\x1b[0m (green)": paneContent || 'No output captured'
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
      "\x1b[96m🖼️  Pane\x1b[0m (cyan)": `${sessionName}:${windowIndex}.${paneIndex}`,
      "\x1b[93m📋 Title\x1b[0m (yellow)": `\x1b[96m${title || `${sessionName}:${windowIndex}.${paneIndex}`}\x1b[0m (cyan)`,
      "\x1b[91m⚡ Command\x1b[0m (red)": command,
      "\x1b[95m🆔 PID\x1b[0m (magenta)": pid,
      "\x1b[94m📏 Size\x1b[0m (blue)": size,
      "\x1b[92m📊 Status\x1b[0m (green)": active === '1' ? '🟢 active' : '⚪ inactive',
      "─────────────────": "─────────────────",
      "\x1b[97m🔧 COMMANDS\x1b[0m (white)": "─────────────────",
      "Attach to Session": `tmux attach-session -t "${sessionName}"`,
      "Select Pane": `tmux select-pane -t "${target}"`,
      "Kill Pane": `tmux kill-pane -t "${target}"`,
      "Split Horizontal": `tmux split-window -t "${target}" -h`,
      "Split Vertical": `tmux split-window -t "${target}" -v`,
      "Capture Full": `tmux capture-pane -t "${target}" -p`,
      "Send Keys": `tmux send-keys -t "${target}" "your-command" Enter`,
      "─────────────────1": "─────────────────",
      "\x1b[92m📝 PANE OUTPUT (last 100 lines)\x1b[0m (green)": paneContent || 'No output captured'
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
    
    // Add session resources with what's running in them
    sessions.forEach(session => {
      const isAttached = session.attached;
      const color = isAttached ? 'green' : 'gray';
      
      // Color based on activity and attachment
      const ansiCode = isAttached ? '\x1b[1;92m' : '\x1b[1;37m'; // Bold bright green for attached, white for detached
      
      // Get the main command running in this session
      const sessionPanes = panes.filter(p => p.sessionName === session.name);
      const commands = [...new Set(sessionPanes.map(p => p.command))]; // Unique commands
      const mainCommand = commands.length > 0 ? commands.slice(0, 2).join(', ') : 'shell';
      
      // Calculate activity status
      const lastActivity = new Date(parseInt(session.lastActivity) * 1000);
      const minutesAgo = Math.floor((Date.now() - lastActivity.getTime()) / 60000);
      const activityStr = minutesAgo < 1 ? 'active' : 
                          minutesAgo < 5 ? `${minutesAgo}m` : 
                          minutesAgo < 60 ? `idle ${minutesAgo}m` : 
                          `idle ${Math.floor(minutesAgo / 60)}h`;
      
      // Compact description with what's running
      const description = isAttached ? 
        `${ansiCode}🟢 ${mainCommand} • ${session.windows}w • ${activityStr}\x1b[0m` :
        `${ansiCode}⚪ ${mainCommand} • ${session.windows}w • ${activityStr}\x1b[0m`;
      
      resources.push({
        uri: `tmux://${session.name}`,
        name: `${ansiCode}@${session.name}\x1b[0m`,
        description,
        mimeType: 'application/json',
        annotations: {
          color,
          type: 'tmux-session',
          status: isAttached ? 'attached' : 'detached',
          priority: isAttached ? 'high' : 'normal',
          category: 'terminal'
        }
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