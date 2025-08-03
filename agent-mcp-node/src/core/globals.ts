// Global state management for Agent-MCP Node.js
// Ported from Python core/globals.py

/**
 * Centralized mutable global state for the MCP server
 * This replaces the Python globals module with TypeScript equivalents
 */

// Agent data interface
interface AgentData {
  agent_id: string;
  capabilities: string[];
  status: 'created' | 'active' | 'terminated' | 'failed';
  current_task?: string;
  working_directory: string;
  color: string;
  created_at: string;
  updated_at: string;
}

// File lock info interface
interface FileLockInfo {
  agent_id: string;
  timestamp: string;
  status: 'locked' | 'unlocked';
  operation?: string;
}

// Task data interface (for in-memory cache)
interface TaskData {
  task_id: string;
  title: string;
  description: string;
  assigned_to?: string;
  created_by: string;
  status: string;
  priority: string;
  created_at: string;
  updated_at: string;
  parent_task?: string;
  child_tasks: string[];
  depends_on_tasks: string[];
  notes: any[];
}

// Audit log entry interface
interface AuditLogEntry {
  timestamp: string;
  agent_id: string;
  action: string;
  details: any;
}

/**
 * Global state container
 * Maintains all server-wide state that needs to persist across requests
 */
export const globalState = {
  // --- Core Server State ---
  
  /**
   * Client connections tracking
   * Maps client ID to connection data
   */
  connections: new Map<string, any>(),
  
  /**
   * Active agents registry
   * Maps agent token to agent data
   */
  activeAgents: new Map<string, AgentData>(),
  
  /**
   * Runtime admin token
   * Generated during server startup or loaded from environment
   */
  adminToken: null as string | null,
  
  /**
   * Tasks in-memory cache
   * Maps task ID to task data for quick access
   */
  tasks: new Map<string, TaskData>(),
  
  // --- File and Directory State ---
  
  /**
   * File locking state
   * Maps file path to lock information
   */
  fileMap: new Map<string, FileLockInfo>(),
  
  /**
   * Agent working directories
   * Maps agent ID to absolute working directory path
   */
  agentWorkingDirs: new Map<string, string>(),
  
  // --- Tmux Session Management ---
  
  /**
   * Active tmux sessions
   * Maps agent ID to tmux session name
   */
  agentTmuxSessions: new Map<string, string>(),
  
  // --- Auditing and Agent Management ---
  
  /**
   * In-memory audit log for current session
   * Persistent log should be stored in files/database
   */
  auditLog: [] as AuditLogEntry[],
  
  /**
   * Agent profile counter for cycling Cursor profiles
   */
  agentProfileCounter: 20,
  
  /**
   * Agent color index for cycling through available colors
   */
  agentColorIndex: 0,
  
  // --- Server Lifecycle ---
  
  /**
   * Server running flag
   * Controls main server loop and background tasks
   */
  serverRunning: true,
  
  /**
   * Server start time for uptime calculations
   */
  serverStartTime: new Date().toISOString(),
  
  // --- External Service Clients ---
  
  /**
   * OpenAI client instance placeholder
   * Will be initialized by external service modules
   */
  openaiClientInstance: null as any,
  
  // --- Database/VSS State ---
  
  /**
   * VSS load test status
   * Tracks if sqlite-vec extension loadability has been tested
   */
  vssLoadTested: false,
  
  /**
   * VSS load success status
   * Indicates if sqlite-vec extension was successfully loaded
   */
  vssLoadSuccessful: false,
  
  // --- Background Task Handles ---
  
  /**
   * RAG indexing background task handle
   * Used for cancellation and lifecycle management
   */
  ragIndexTaskHandle: null as any,
  
  /**
   * Claude Code session monitoring task handle
   */
  claudeSessionTaskHandle: null as any,
  
  // --- Statistics and Monitoring ---
  
  /**
   * Request statistics
   */
  stats: {
    totalRequests: 0,
    totalToolCalls: 0,
    totalErrors: 0,
    startTime: Date.now()
  }
};

/**
 * Helper functions for global state management
 */

/**
 * Reset global state (useful for testing)
 */
export function resetGlobalState(): void {
  globalState.connections.clear();
  globalState.activeAgents.clear();
  globalState.tasks.clear();
  globalState.fileMap.clear();
  globalState.agentWorkingDirs.clear();
  globalState.agentTmuxSessions.clear();
  globalState.auditLog.length = 0;
  globalState.agentProfileCounter = 20;
  globalState.agentColorIndex = 0;
  globalState.serverRunning = true;
  globalState.stats.totalRequests = 0;
  globalState.stats.totalToolCalls = 0;
  globalState.stats.totalErrors = 0;
  globalState.stats.startTime = Date.now();
}

/**
 * Get server statistics
 */
export function getServerStats() {
  const uptime = Date.now() - globalState.stats.startTime;
  
  return {
    uptime,
    uptimeHours: Math.floor(uptime / (1000 * 60 * 60)),
    uptimeMinutes: Math.floor((uptime % (1000 * 60 * 60)) / (1000 * 60)),
    totalRequests: globalState.stats.totalRequests,
    totalToolCalls: globalState.stats.totalToolCalls,
    totalErrors: globalState.stats.totalErrors,
    activeAgents: globalState.activeAgents.size,
    activeTasks: globalState.tasks.size,
    lockedFiles: globalState.fileMap.size,
    tmuxSessions: globalState.agentTmuxSessions.size,
    auditEntries: globalState.auditLog.length
  };
}

/**
 * Increment request counter
 */
export function incrementRequestCount(): void {
  globalState.stats.totalRequests++;
}

/**
 * Increment tool call counter
 */
export function incrementToolCallCount(): void {
  globalState.stats.totalToolCalls++;
}

/**
 * Increment error counter
 */
export function incrementErrorCount(): void {
  globalState.stats.totalErrors++;
}

/**
 * Add entry to audit log
 */
export function addAuditLogEntry(agentId: string, action: string, details: any = {}): void {
  globalState.auditLog.push({
    timestamp: new Date().toISOString(),
    agent_id: agentId,
    action,
    details
  });
  
  // Keep audit log size reasonable (last 1000 entries)
  if (globalState.auditLog.length > 1000) {
    globalState.auditLog.splice(0, globalState.auditLog.length - 1000);
  }
}

/**
 * Get recent audit log entries
 */
export function getAuditLog(limit: number = 50, agentId?: string, action?: string): AuditLogEntry[] {
  let filtered = globalState.auditLog;
  
  if (agentId) {
    filtered = filtered.filter(entry => entry.agent_id === agentId);
  }
  
  if (action) {
    filtered = filtered.filter(entry => entry.action === action);
  }
  
  return filtered.slice(-limit);
}

/**
 * Update task cache
 */
export function updateTaskCache(taskId: string, taskData: TaskData): void {
  globalState.tasks.set(taskId, taskData);
}

/**
 * Remove task from cache
 */
export function removeTaskFromCache(taskId: string): void {
  globalState.tasks.delete(taskId);
}

/**
 * Get task from cache
 */
export function getTaskFromCache(taskId: string): TaskData | undefined {
  return globalState.tasks.get(taskId);
}

console.log('✅ Global state management loaded');