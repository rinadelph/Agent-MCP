// Database schema initialization for Agent-MCP Node.js
// Ported from Python schema.py with full table definitions

import { getDbConnection, isVssLoadable } from './connection.js';
import { EMBEDDING_DIMENSION, MCP_DEBUG } from '../core/config.js';

/**
 * Check if the current embedding table dimension matches configured dimension
 */
function checkEmbeddingDimensionCompatibility(): boolean {
  const db = getDbConnection();
  
  try {
    // Check if rag_embeddings table exists
    const tableInfo = db.prepare(`
      SELECT sql FROM sqlite_master 
      WHERE type IN ('table', 'virtual') AND name='rag_embeddings'
    `).get() as { sql: string } | undefined;
    
    if (!tableInfo) {
      // Table doesn't exist, so it's compatible
      if (MCP_DEBUG) {
        console.log(`rag_embeddings table doesn't exist - will create with dimension ${EMBEDDING_DIMENSION}`);
      }
      return true;
    }
    
    // Extract dimension from CREATE TABLE statement
    const dimensionMatch = tableInfo.sql.match(/FLOAT\[(\d+)\]/);
    
    if (dimensionMatch) {
      const currentDim = parseInt(dimensionMatch[1] || '0');
      if (MCP_DEBUG) {
        console.log(`Current embedding dimension: ${currentDim}, Required: ${EMBEDDING_DIMENSION}`);
      }
      
      if (currentDim !== EMBEDDING_DIMENSION) {
        console.warn("⚠️  Embedding dimension mismatch detected!");
        console.warn(`   Current table: ${currentDim} dimensions`);
        console.warn(`   Config expects: ${EMBEDDING_DIMENSION} dimensions`);
        console.warn(`   Will trigger migration from ${currentDim}D to ${EMBEDDING_DIMENSION}D`);
        return false;
      } else {
        if (MCP_DEBUG) {
          console.log(`✅ Embedding dimensions match (${currentDim}D) - no migration needed`);
        }
        return true;
      }
    } else {
      console.warn("⚠️  Could not parse dimension from table schema:", tableInfo.sql);
      console.warn("Assuming incompatible and will recreate table for safety");
      return false;
    }
  } catch (error) {
    console.error("Error checking embedding dimension compatibility:", error);
    return false;
  }
}

/**
 * Handle embedding dimension changes by recreating the embeddings table
 */
function handleEmbeddingDimensionChange(): void {
  const db = getDbConnection();
  
  console.log("=".repeat(60));
  console.log("🔄 STARTING EMBEDDING DIMENSION MIGRATION");
  console.log("=".repeat(60));
  
  const transaction = db.transaction(() => {
    try {
      // Get stats before migration
      let oldEmbeddingCount = 0;
      let chunkCount = 0;
      
      try {
        const embeddingResult = db.prepare('SELECT COUNT(*) as count FROM rag_embeddings').get() as { count: number };
        oldEmbeddingCount = embeddingResult.count;
        
        const chunkResult = db.prepare('SELECT COUNT(*) as count FROM rag_chunks').get() as { count: number };
        chunkCount = chunkResult.count;
        
        console.log("📊 Migration stats:");
        console.log(`   • Existing embeddings: ${oldEmbeddingCount}`);
        console.log(`   • Text chunks: ${chunkCount}`);
      } catch (error) {
        console.log("Could not get pre-migration stats:", error);
      }
      
      console.log("🗑️  Removing old embeddings and vector table...");
      
      // Delete all embeddings first (safer than DROP)
      db.prepare('DELETE FROM rag_embeddings').run();
      console.log("Deleted all existing embeddings");
      
      // Drop the old virtual table
      db.prepare('DROP TABLE IF EXISTS rag_embeddings').run();
      console.log("Dropped old rag_embeddings table");
      
      // Clear all stored hashes to force re-indexing
      const hashResult = db.prepare("DELETE FROM rag_meta WHERE meta_key LIKE 'hash_%'").run();
      console.log(`Cleared ${hashResult.changes} stored file hashes`);
      
      // Reset last indexed timestamps
      const timestampResult = db.prepare(`
        UPDATE rag_meta 
        SET meta_value = '1970-01-01T00:00:00Z' 
        WHERE meta_key LIKE 'last_indexed_%'
      `).run();
      console.log(`Reset ${timestampResult.changes} indexing timestamps`);
      
      console.log("✅ Migration preparation completed successfully");
      console.log("📝 Next steps:");
      console.log(`   • New vector table will be created with ${EMBEDDING_DIMENSION} dimensions`);
      console.log(`   • RAG indexer will automatically re-process all ${chunkCount} chunks`);
      console.log("   • This may take a few minutes and will use OpenAI API tokens");
      console.log("=".repeat(60));
      
    } catch (error) {
      console.error("❌ Error during migration:", error);
      throw new Error(`Embedding dimension migration failed: ${error}`);
    }
  });
  
  transaction();
}

/**
 * Initialize all database tables
 */
export function initDatabase(): void {
  console.log("🗄️  Initializing database schema...");
  
  const db = getDbConnection();
  const vssAvailable = isVssLoadable();
  
  if (!vssAvailable) {
    console.warn("⚠️  sqlite-vec extension not available. RAG virtual table will not be created.");
  }
  
  const transaction = db.transaction(() => {
    // Agents Table
    db.exec(`
      CREATE TABLE IF NOT EXISTS agents (
        token TEXT PRIMARY KEY,
        agent_id TEXT UNIQUE NOT NULL,
        capabilities TEXT, -- JSON List
        created_at TEXT NOT NULL,
        status TEXT NOT NULL, -- 'created', 'active', 'terminated'
        current_task TEXT,    -- Task ID
        working_directory TEXT NOT NULL,
        color TEXT,           -- For terminal visualization
        terminated_at TEXT,   -- Timestamp of termination
        updated_at TEXT       -- Timestamp of last update
      )
    `);
    
    // Tasks Table
    db.exec(`
      CREATE TABLE IF NOT EXISTS tasks (
        task_id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        description TEXT,
        assigned_to TEXT,     -- Agent ID or NULL
        created_by TEXT NOT NULL, -- Agent ID or 'admin'
        status TEXT NOT NULL,     -- 'pending', 'in_progress', 'completed', 'cancelled', 'failed'
        priority TEXT NOT NULL,   -- 'low', 'medium', 'high'
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        parent_task TEXT,         -- Task ID of parent task or NULL
        child_tasks TEXT,         -- JSON List of child Task IDs
        depends_on_tasks TEXT,    -- JSON List of Task IDs this task depends on
        notes TEXT                -- JSON List of note objects
      )
    `);
    
    // Agent Actions Table
    db.exec(`
      CREATE TABLE IF NOT EXISTS agent_actions (
        action_id INTEGER PRIMARY KEY AUTOINCREMENT,
        agent_id TEXT NOT NULL, -- Can be agent_id or 'admin'
        action_type TEXT NOT NULL, -- 'assigned_task', 'started_work', 'completed_task', etc.
        task_id TEXT,          -- Optional: Link action to a specific task_id
        timestamp TEXT NOT NULL,
        details TEXT           -- Optional JSON blob for extra info
      )
    `);
    
    // Admin Configuration Table
    db.exec(`
      CREATE TABLE IF NOT EXISTS admin_config (
        config_key TEXT PRIMARY KEY,
        config_value TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        description TEXT
      )
    `);
    
    // Indexes for agent_actions
    db.exec(`
      CREATE INDEX IF NOT EXISTS idx_agent_actions_agent_id_timestamp 
      ON agent_actions (agent_id, timestamp DESC)
    `);
    db.exec(`
      CREATE INDEX IF NOT EXISTS idx_agent_actions_task_id_timestamp 
      ON agent_actions (task_id, timestamp DESC)
    `);
    
    // Project Context Table
    db.exec(`
      CREATE TABLE IF NOT EXISTS project_context (
        context_key TEXT PRIMARY KEY,
        value TEXT NOT NULL,         -- Stored as JSON string
        last_updated TEXT NOT NULL,
        updated_by TEXT NOT NULL,    -- Agent ID or 'admin' or 'server_startup'
        description TEXT
      )
    `);
    
    // File Metadata Table
    db.exec(`
      CREATE TABLE IF NOT EXISTS file_metadata (
        filepath TEXT PRIMARY KEY,   -- Normalized, absolute path
        metadata TEXT NOT NULL,      -- JSON object
        last_updated TEXT NOT NULL,
        updated_by TEXT NOT NULL,    -- Agent ID or 'admin'
        content_hash TEXT            -- SHA256 hash for change detection
      )
    `);
    
    // RAG Chunks Table
    db.exec(`
      CREATE TABLE IF NOT EXISTS rag_chunks (
        chunk_id INTEGER PRIMARY KEY AUTOINCREMENT, -- Matches rowid for vec0 table
        source_type TEXT NOT NULL, -- 'markdown', 'context', 'filemeta', 'codefile', etc.
        source_ref TEXT NOT NULL,  -- Filepath, context_key, or other reference
        chunk_text TEXT NOT NULL,
        indexed_at TEXT NOT NULL,
        metadata TEXT -- JSON object with chunk-specific metadata
      )
    `);
    
    // Index for rag_chunks
    db.exec(`
      CREATE INDEX IF NOT EXISTS idx_rag_chunks_source_type_ref 
      ON rag_chunks (source_type, source_ref)
    `);
    
    // RAG Meta Table
    db.exec(`
      CREATE TABLE IF NOT EXISTS rag_meta (
        meta_key TEXT PRIMARY KEY, 
        meta_value TEXT
      )
    `);
    
    // Initialize default timestamps
    const defaultMetaEntries = [
      ['last_indexed_markdown', '1970-01-01T00:00:00Z'],
      ['last_indexed_code', '1970-01-01T00:00:00Z'],
      ['last_indexed_context', '1970-01-01T00:00:00Z'],
      ['last_indexed_filemeta', '1970-01-01T00:00:00Z'],
      ['last_indexed_tasks', '1970-01-01T00:00:00Z'],
    ];
    
    const insertMeta = db.prepare('INSERT OR IGNORE INTO rag_meta (meta_key, meta_value) VALUES (?, ?)');
    for (const [key, value] of defaultMetaEntries) {
      insertMeta.run(key, value);
    }
    
    // Agent Messages Table
    db.exec(`
      CREATE TABLE IF NOT EXISTS agent_messages (
        message_id TEXT PRIMARY KEY,
        sender_id TEXT NOT NULL,
        recipient_id TEXT NOT NULL,
        message_content TEXT NOT NULL,
        message_type TEXT NOT NULL DEFAULT 'text',
        priority TEXT NOT NULL DEFAULT 'normal',
        timestamp TEXT NOT NULL,
        delivered BOOLEAN NOT NULL DEFAULT 0,
        read BOOLEAN NOT NULL DEFAULT 0
      )
    `);
    
    // Indexes for agent_messages
    db.exec(`
      CREATE INDEX IF NOT EXISTS idx_agent_messages_recipient_timestamp 
      ON agent_messages (recipient_id, timestamp DESC)
    `);
    db.exec(`
      CREATE INDEX IF NOT EXISTS idx_agent_messages_sender_timestamp 
      ON agent_messages (sender_id, timestamp DESC)
    `);
    db.exec(`
      CREATE INDEX IF NOT EXISTS idx_agent_messages_unread 
      ON agent_messages (recipient_id, read, timestamp DESC)
    `);
    
    // Claude Code Sessions Table
    db.exec(`
      CREATE TABLE IF NOT EXISTS claude_code_sessions (
        session_id TEXT PRIMARY KEY,
        pid INTEGER NOT NULL,
        parent_pid INTEGER NOT NULL,
        first_detected TEXT NOT NULL,
        last_activity TEXT NOT NULL,
        working_directory TEXT,
        agent_id TEXT,              -- Links to agents.agent_id
        status TEXT DEFAULT 'detected',  -- 'detected', 'registered', 'active', 'inactive'
        git_commits TEXT,           -- JSON array of commit hashes
        metadata TEXT               -- Additional session metadata
      )
    `);
    
    // Indexes for claude_code_sessions
    db.exec(`
      CREATE INDEX IF NOT EXISTS idx_claude_sessions_pid 
      ON claude_code_sessions (pid, parent_pid)
    `);
    db.exec(`
      CREATE INDEX IF NOT EXISTS idx_claude_sessions_activity 
      ON claude_code_sessions (last_activity DESC)
    `);
    db.exec(`
      CREATE INDEX IF NOT EXISTS idx_claude_sessions_agent 
      ON claude_code_sessions (agent_id)
    `);
    
    // File Status Table for multi-agent coordination
    db.exec(`
      CREATE TABLE IF NOT EXISTS file_status (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filepath TEXT NOT NULL,     -- Normalized, absolute path
        status TEXT NOT NULL,       -- 'in_use', 'released'
        agent_id TEXT NOT NULL,     -- Agent ID who locked/released the file
        locked_at TEXT NOT NULL,    -- Timestamp when file was locked
        released_at TEXT,           -- Timestamp when file was released
        notes TEXT,                 -- Optional notes about the work
        FOREIGN KEY (agent_id) REFERENCES agents(agent_id)
      )
    `);
    
    // Indexes for file_status
    db.exec(`
      CREATE INDEX IF NOT EXISTS idx_file_status_filepath 
      ON file_status (filepath, status)
    `);
    db.exec(`
      CREATE INDEX IF NOT EXISTS idx_file_status_agent 
      ON file_status (agent_id, locked_at DESC)
    `);
    db.exec(`
      CREATE INDEX IF NOT EXISTS idx_file_status_active 
      ON file_status (status, locked_at DESC)
    `);
    
    // MCP Session Persistence Table for connection recovery
    db.exec(`
      CREATE TABLE IF NOT EXISTS mcp_session_persistence (
        mcp_session_id TEXT PRIMARY KEY,
        transport_state TEXT NOT NULL,     -- JSON serialized transport state
        agent_context TEXT,                -- JSON serialized agent context
        conversation_state TEXT,           -- JSON serialized conversation history
        created_at TEXT NOT NULL,
        last_heartbeat TEXT NOT NULL,
        disconnected_at TEXT,              -- When connection dropped
        recovery_attempts INTEGER DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'active', -- 'active', 'disconnected', 'recovered', 'expired'
        grace_period_expires TEXT,         -- When recovery window closes
        working_directory TEXT,
        metadata TEXT                      -- Additional recovery metadata
      )
    `);
    
    // Indexes for mcp_session_persistence
    db.exec(`
      CREATE INDEX IF NOT EXISTS idx_mcp_sessions_status_heartbeat 
      ON mcp_session_persistence (status, last_heartbeat DESC)
    `);
    db.exec(`
      CREATE INDEX IF NOT EXISTS idx_mcp_sessions_recovery 
      ON mcp_session_persistence (status, grace_period_expires)
    `);
    
    // Agent Session State Table for preserving long-running context
    db.exec(`
      CREATE TABLE IF NOT EXISTS agent_session_state (
        agent_id TEXT,
        mcp_session_id TEXT,
        state_key TEXT,
        state_value TEXT NOT NULL,         -- JSON serialized state data
        last_updated TEXT NOT NULL,
        expires_at TEXT,                   -- Optional expiration
        PRIMARY KEY (agent_id, mcp_session_id, state_key),
        FOREIGN KEY (mcp_session_id) REFERENCES mcp_session_persistence(mcp_session_id)
      )
    `);
    
    // Indexes for agent_session_state
    db.exec(`
      CREATE INDEX IF NOT EXISTS idx_agent_session_state_session 
      ON agent_session_state (mcp_session_id, last_updated DESC)
    `);
    db.exec(`
      CREATE INDEX IF NOT EXISTS idx_agent_session_state_expiry 
      ON agent_session_state (expires_at)
    `);
    
    console.log("✅ Core tables created successfully");
    
    // RAG Embeddings Virtual Table (using sqlite-vec)
    if (vssAvailable) {
      // Check dimension compatibility
      if (!checkEmbeddingDimensionCompatibility()) {
        console.warn("🔄 Embedding dimension changed, recreating vector table...");
        handleEmbeddingDimensionChange();
      }
      
      try {
        // Validate embedding dimension
        if (!Number.isInteger(EMBEDDING_DIMENSION) || EMBEDDING_DIMENSION <= 0) {
          throw new Error(`Invalid EMBEDDING_DIMENSION: ${EMBEDDING_DIMENSION}`);
        }
        
        // Create vec0 virtual table
        db.exec(`
          CREATE VIRTUAL TABLE IF NOT EXISTS rag_embeddings USING vec0(
            embedding FLOAT[${EMBEDDING_DIMENSION}] 
          )
        `);
        
        console.log(`✅ Vector table 'rag_embeddings' created (vec0 with dimension ${EMBEDDING_DIMENSION})`);
      } catch (error) {
        console.error("❌ Failed to create vector table 'rag_embeddings':", error);
        console.error("RAG search functionality will be impaired.");
      }
    } else {
      console.warn("⚠️  Skipping RAG virtual table creation (sqlite-vec not available)");
    }
  });
  
  try {
    transaction();
    console.log("✅ Database schema initialized successfully");
  } catch (error) {
    console.error("❌ Database schema initialization failed:", error);
    throw new Error(`Failed to initialize database schema: ${error}`);
  }
}

/**
 * Get database statistics
 */
export function getDatabaseStats(): Record<string, number> {
  const db = getDbConnection();
  
  const stats: Record<string, number> = {};
  
  const tables = [
    'agents', 'tasks', 'agent_actions', 'admin_config', 'project_context', 
    'file_metadata', 'rag_chunks', 'rag_meta', 'agent_messages', 
    'claude_code_sessions', 'file_status', 'mcp_session_persistence', 'agent_session_state'
  ];
  
  for (const table of tables) {
    try {
      const result = db.prepare(`SELECT COUNT(*) as count FROM ${table}`).get() as { count: number };
      stats[table] = result.count;
    } catch (error) {
      stats[table] = -1; // Table doesn't exist or error
    }
  }
  
  // Try to get vector table stats if available
  if (isVssLoadable()) {
    try {
      const result = db.prepare('SELECT COUNT(*) as count FROM rag_embeddings').get() as { count: number };
      stats.rag_embeddings = result.count;
    } catch (error) {
      stats.rag_embeddings = -1;
    }
  }
  
  return stats;
}