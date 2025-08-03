// Database type definitions for Agent-MCP Node.js
// Ported from Python schema.py

export interface Agent {
  token: string;           // PRIMARY KEY
  agent_id: string;        // UNIQUE NOT NULL
  capabilities: string;    // JSON List
  created_at: string;      // ISO timestamp
  status: AgentStatus;     // 'created', 'active', 'terminated'
  current_task?: string;   // Task ID
  working_directory: string;
  color?: string;          // For dashboard visualization
  terminated_at?: string;  // ISO timestamp
  updated_at: string;      // ISO timestamp
}

export type AgentStatus = 'created' | 'active' | 'terminated';

export interface Task {
  task_id: string;         // PRIMARY KEY
  title: string;
  description?: string;
  assigned_to?: string;    // Agent ID or null
  created_by: string;      // Agent ID or 'admin'
  status: TaskStatus;
  priority: TaskPriority;
  created_at: string;      // ISO timestamp
  updated_at: string;      // ISO timestamp
  parent_task?: string;    // Task ID or null
  child_tasks: string;     // JSON List of child Task IDs
  depends_on_tasks: string; // JSON List of Task IDs this depends on
  notes: string;           // JSON List of note objects
}

export type TaskStatus = 'pending' | 'in_progress' | 'completed' | 'cancelled' | 'failed';
export type TaskPriority = 'low' | 'medium' | 'high';

export interface TaskNote {
  timestamp: string;
  author: string;
  content: string;
}

export interface AgentAction {
  action_id?: number;      // AUTOINCREMENT PRIMARY KEY
  agent_id: string;        // Can be agent_id or 'admin'
  action_type: string;     // 'assigned_task', 'started_work', 'completed_task', etc.
  task_id?: string;        // Optional link to task
  timestamp: string;       // ISO timestamp
  details?: string;        // Optional JSON blob for extra info
}

export interface ProjectContext {
  context_key: string;     // PRIMARY KEY
  value: string;           // JSON string
  last_updated: string;    // ISO timestamp
  updated_by: string;      // Agent ID or 'admin' or 'server_startup'
  description?: string;
}

export interface FileMetadata {
  filepath: string;        // PRIMARY KEY - normalized, absolute path
  metadata: string;        // JSON object
  last_updated: string;    // ISO timestamp
  updated_by: string;      // Agent ID or 'admin'
  content_hash?: string;   // SHA256 hash for change detection
}

export interface RagChunk {
  chunk_id?: number;       // AUTOINCREMENT PRIMARY KEY (matches rowid for vec0)
  source_type: string;     // 'markdown', 'context', 'filemeta', 'codefile', 'code', 'code_summary'
  source_ref: string;      // Filepath, context_key, or other reference
  chunk_text: string;
  indexed_at: string;      // ISO timestamp
  metadata?: string;       // JSON object with chunk-specific metadata
}

export interface RagMeta {
  meta_key: string;        // PRIMARY KEY
  meta_value: string;
}

export interface AgentMessage {
  message_id: string;      // PRIMARY KEY
  sender_id: string;
  recipient_id: string;
  message_content: string;
  message_type: string;    // DEFAULT 'text'
  priority: string;        // DEFAULT 'normal'
  timestamp: string;       // ISO timestamp
  delivered: boolean;      // DEFAULT false
  read: boolean;           // DEFAULT false
}

export interface ClaudeCodeSession {
  session_id: string;      // PRIMARY KEY
  pid: number;
  parent_pid: number;
  first_detected: string;  // ISO timestamp
  last_activity: string;   // ISO timestamp
  working_directory?: string;
  agent_id?: string;       // Links to agents.agent_id
  status: string;          // DEFAULT 'detected' - 'detected', 'registered', 'active', 'inactive'
  git_commits?: string;    // JSON array of commit hashes
  metadata?: string;       // Additional session metadata
}

export interface RagEmbedding {
  // Virtual table using vec0 - rowid matches rag_chunks.chunk_id
  rowid: number;           // Links to rag_chunks.chunk_id
  embedding: Float32Array; // FLOAT[{DIMENSION}] embedding vector
}

// Database configuration
export interface DatabaseConfig {
  dbPath: string;
  enableWAL: boolean;
  timeout: number;
  embeddingDimension: number;
  maxConnections?: number;
}

// Search and query interfaces
export interface SearchResult {
  chunk_id: number;
  source_type: string;
  source_ref: string;
  chunk_text: string;
  distance: number;
  metadata?: any;
}

export interface VectorSearchOptions {
  limit?: number;
  threshold?: number;
  source_types?: string[];
}

// Database operation results
export interface DatabaseResult<T = any> {
  success: boolean;
  data?: T;
  error?: string;
}

export interface BatchResult {
  inserted: number;
  updated: number;
  errors: string[];
}