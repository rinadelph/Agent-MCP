// Core configuration for Agent-MCP Node.js
// Ported from Python config.py

import dotenv from 'dotenv';
// Ensure environment variables are loaded
dotenv.config();

import { join } from 'path';
import { existsSync, mkdirSync } from 'fs';

// Version information
export const VERSION = "1.0.0";
export const GITHUB_REPO = "rinadelph/Agent-MCP";
export const AUTHOR = "Luis Alejandro Rincon";
export const GITHUB_URL = "https://github.com/rinadelph";

// Database configuration
export const DB_FILE_NAME = "mcp_state.db";

// OpenAI Model Configuration
export const ADVANCED_EMBEDDINGS = process.env.ADVANCED_EMBEDDINGS === 'true';

// Embedding models and dimensions (matching Python config)
export const SIMPLE_EMBEDDING_MODEL = "text-embedding-3-large";
export const SIMPLE_EMBEDDING_DIMENSION = 1536;
export const ADVANCED_EMBEDDING_MODEL = "text-embedding-3-large";
export const ADVANCED_EMBEDDING_DIMENSION = 3072;

// Dynamic configuration based on mode
export const EMBEDDING_MODEL = ADVANCED_EMBEDDINGS ? ADVANCED_EMBEDDING_MODEL : SIMPLE_EMBEDDING_MODEL;
export const EMBEDDING_DIMENSION = ADVANCED_EMBEDDINGS ? ADVANCED_EMBEDDING_DIMENSION : SIMPLE_EMBEDDING_DIMENSION;

export const CHAT_MODEL = "gpt-4.1-2025-04-14"; // GPT-4.1 with 1M context window
export const TASK_ANALYSIS_MODEL = "gpt-4.1-2025-04-14";
export const MAX_EMBEDDING_BATCH_SIZE = 100;
export const MAX_CONTEXT_TOKENS = 1000000; // GPT-4.1 1 million token context window
export const TASK_ANALYSIS_MAX_TOKENS = 1000000;

// Environment variables
export const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
export const MCP_DEBUG = process.env.MCP_DEBUG === 'true';

// Task placement configuration
export const ENABLE_TASK_PLACEMENT_RAG = process.env.ENABLE_TASK_PLACEMENT_RAG !== 'false';
export const TASK_DUPLICATION_THRESHOLD = parseFloat(process.env.TASK_DUPLICATION_THRESHOLD || '0.8');
export const ALLOW_RAG_OVERRIDE = process.env.ALLOW_RAG_OVERRIDE !== 'false';
export const TASK_PLACEMENT_RAG_TIMEOUT = parseInt(process.env.TASK_PLACEMENT_RAG_TIMEOUT || '5');

// Auto-indexing control
export const DISABLE_AUTO_INDEXING = process.env.DISABLE_AUTO_INDEXING === 'true';

// Agent colors for dashboard visualization
export const AGENT_COLORS = [
  "#FF5733", "#33FF57", "#3357FF", "#FF33A1", "#A133FF", "#33FFA1",
  "#FFBD33", "#33FFBD", "#BD33FF", "#FF3333", "#33FF33", "#3333FF",
  "#FF8C00", "#00CED1", "#9400D3", "#FF1493", "#7FFF00", "#1E90FF"
];

// Directory helpers
export function getProjectDir(): string {
  return process.cwd(); // Use current working directory
}

export function getAgentDir(): string {
  const agentDir = join(getProjectDir(), '.agent');
  if (!existsSync(agentDir)) {
    mkdirSync(agentDir, { recursive: true });
  }
  return agentDir;
}

export function getDbPath(): string {
  return join(getAgentDir(), DB_FILE_NAME);
}

// Validate critical environment variables
if (!OPENAI_API_KEY && !process.env.NODE_ENV?.includes('test')) {
  console.error("CRITICAL: OPENAI_API_KEY not found in environment variables.");
  console.error("Please set it in your .env file or environment.");
}

// Log configuration loading
if (MCP_DEBUG) {
  console.log("🔧 Agent-MCP Node.js configuration loaded");
  console.log(`📁 Project Directory: ${getProjectDir()}`);
  console.log(`🗄️  Database Path: ${getDbPath()}`);
  console.log(`🤖 Embedding Model: ${EMBEDDING_MODEL} (${EMBEDDING_DIMENSION}D)`);
  console.log(`💬 Chat Model: ${CHAT_MODEL}`);
}