// Database connection management for Agent-MCP Node.js
// Ported from Python connection.py with sqlite-vec support

import Database from 'better-sqlite3';
import * as sqliteVec from 'sqlite-vec';
import { existsSync, mkdirSync } from 'fs';
import { dirname } from 'path';
import { getDbPath, MCP_DEBUG, ensureAgentDir } from '../core/config.js';
import type { DatabaseConfig } from '../types/database.js';

// Global state for VSS loadability (matching Python implementation)
let vssLoadTested = false;
let vssLoadSuccessful = false;

/**
 * Check if sqlite-vec extension can be loaded
 * This performs a test load on a temporary in-memory database
 */
export function checkVssLoadability(): boolean {
  if (vssLoadTested) {
    return vssLoadSuccessful;
  }

  if (MCP_DEBUG) {
    console.log("🧪 Testing sqlite-vec extension loadability...");
  }

  let testDb: Database.Database | null = null;
  try {
    // Test with in-memory database
    testDb = new Database(':memory:');
    sqliteVec.load(testDb);
    
    // Try to create a simple vec0 table to verify it works
    testDb.exec('CREATE VIRTUAL TABLE test_vec USING vec0(embedding FLOAT[4])');
    testDb.exec('DROP TABLE test_vec');
    
    vssLoadSuccessful = true;
    if (MCP_DEBUG) {
      console.log("✅ sqlite-vec extension loaded successfully");
    }
  } catch (error) {
    vssLoadSuccessful = false;
    console.error("❌ Failed to load sqlite-vec extension:", error instanceof Error ? error.message : error);
    console.error("⚠️  RAG functionality will be disabled. Ensure sqlite-vec is properly installed.");
  } finally {
    if (testDb) {
      testDb.close();
    }
  }

  vssLoadTested = true;
  return vssLoadSuccessful;
}

/**
 * Returns whether sqlite-vec extension is available
 */
export function isVssLoadable(): boolean {
  if (!vssLoadTested) {
    console.warn("isVssLoadable() called before loadability check. Running check now...");
    checkVssLoadability();
  }
  return vssLoadSuccessful;
}

/**
 * Create a new database connection with proper configuration
 */
export function createDbConnection(config?: Partial<DatabaseConfig>): Database.Database {
  const dbPath = config?.dbPath || getDbPath();
  
  // Ensure .agent directory exists if using default path
  if (!config?.dbPath) {
    ensureAgentDir();
  } else {
    // For custom paths, ensure the directory exists
    const dbDir = dirname(dbPath);
    if (!existsSync(dbDir)) {
      try {
        mkdirSync(dbDir, { recursive: true });
      } catch (error) {
        throw new Error(`Failed to create database directory: ${error}`);
      }
    }
  }

  let db: Database.Database;
  try {
    // Create database connection with optimized settings
    db = new Database(dbPath, {
      timeout: config?.timeout || 10000,
      verbose: MCP_DEBUG ? console.log : undefined,
    });

    // Configure SQLite for optimal performance and concurrency
    db.pragma('journal_mode = WAL'); // Enable WAL mode for better concurrency
    db.pragma('foreign_keys = ON');  // Enable foreign key constraints
    db.pragma('synchronous = NORMAL'); // Balance between safety and performance
    db.pragma('cache_size = 10000');   // Increase cache size for better performance
    db.pragma('temp_store = MEMORY');  // Store temporary tables in memory

    // Try to load sqlite-vec extension
    try {
      sqliteVec.load(db);
      vssLoadSuccessful = true;
      vssLoadTested = true;
      if (MCP_DEBUG) {
        console.log("✅ sqlite-vec loaded for database connection");
      }
    } catch (error) {
      vssLoadSuccessful = false;
      vssLoadTested = true;
      if (MCP_DEBUG) {
        console.log("ℹ️  sqlite-vec not loaded (extension not available):", error instanceof Error ? error.message : error);
      }
    }

  } catch (error) {
    throw new Error(`Failed to create database connection: ${error}`);
  }

  return db;
}

/**
 * Get a read-only database connection
 */
export function getDbConnectionRead(): Database.Database {
  return createDbConnection({ timeout: 5000 });
}

/**
 * Get the main database connection (singleton pattern)
 */
let mainDbConnection: Database.Database | null = null;

export function getDbConnection(): Database.Database {
  if (!mainDbConnection) {
    mainDbConnection = createDbConnection();
    
    // Handle graceful shutdown
    process.on('SIGINT', () => {
      if (mainDbConnection) {
        console.log("🔒 Closing database connection...");
        mainDbConnection.close();
        mainDbConnection = null;
      }
    });
    
    process.on('SIGTERM', () => {
      if (mainDbConnection) {
        console.log("🔒 Closing database connection...");
        mainDbConnection.close();
        mainDbConnection = null;
      }
    });
  }
  
  return mainDbConnection;
}

/**
 * Close the main database connection
 */
export function closeDbConnection(): void {
  if (mainDbConnection) {
    mainDbConnection.close();
    mainDbConnection = null;
  }
}

/**
 * Test database connectivity and sqlite-vec functionality
 */
export function testDatabaseConnection(): { success: boolean; error?: string; vecSupported: boolean } {
  try {
    const db = createDbConnection();
    
    // Test basic connectivity
    const result = db.prepare('SELECT 1 as test').get() as { test: number };
    if (result.test !== 1) {
      throw new Error("Basic database query failed");
    }
    
    // Test sqlite-vec if available
    let vecSupported = false;
    if (isVssLoadable()) {
      try {
        const vecVersion = db.prepare('SELECT vec_version() as version').get() as { version: string };
        vecSupported = !!vecVersion.version;
        if (MCP_DEBUG) {
          console.log(`📊 sqlite-vec version: ${vecVersion.version}`);
        }
      } catch (error) {
        if (MCP_DEBUG) {
          console.log("⚠️  sqlite-vec test failed:", error);
        }
      }
    }
    
    db.close();
    return { success: true, vecSupported };
  } catch (error) {
    return { 
      success: false, 
      error: error instanceof Error ? error.message : String(error),
      vecSupported: false 
    };
  }
}