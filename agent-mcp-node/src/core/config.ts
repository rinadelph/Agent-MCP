// Core configuration for Agent-MCP Node.js
// Ported from Python config.py

import dotenv from 'dotenv';
// Ensure environment variables are loaded
dotenv.config();

import { join } from 'path';
import { existsSync, mkdirSync } from 'fs';

// Version information
export const VERSION = "4.0";
export const GITHUB_REPO = "rinadelph/Agent-MCP";
export const AUTHOR = "Luis Alejandro Rincon";
export const GITHUB_URL = "https://github.com/rinadelph";

// Database configuration
export const DB_FILE_NAME = "mcp_state.db";

// Multi-Provider Embedding Configuration
// Extensible architecture - users can implement their own providers

// Primary embedding provider selection
export const EMBEDDING_PROVIDER = process.env.EMBEDDING_PROVIDER || 'openai';
export const EMBEDDING_MODEL_NAME = process.env.EMBEDDING_MODEL || 'text-embedding-3-large';
export const EMBEDDING_DIMENSIONS = parseInt(process.env.EMBEDDING_DIMENSIONS || '1536');
export const EMBEDDING_MAX_BATCH = parseInt(process.env.EMBEDDING_MAX_BATCH || '100');

// Fallback chain for provider failures (comma-separated list)
export const EMBEDDING_PROVIDERS = process.env.EMBEDDING_PROVIDERS?.split(',').map(p => p.trim()) || 
  [EMBEDDING_PROVIDER]; // Default to single provider if no chain specified

// Auto-detect local models
export const LOCAL_MODEL_AUTO_DETECT = process.env.LOCAL_MODEL_AUTO_DETECT === 'true';

// Provider-specific configuration (users can extend this)
export const PROVIDER_CONFIG = {
  // OpenAI
  OPENAI_API_KEY: process.env.OPENAI_API_KEY,
  OPENAI_BASE_URL: process.env.OPENAI_BASE_URL,
  OPENAI_MODEL: process.env.OPENAI_MODEL || 'text-embedding-3-large',
  
  // Ollama 
  OLLAMA_BASE_URL: process.env.OLLAMA_URL || process.env.OLLAMA_BASE_URL || 'http://localhost:11434',
  OLLAMA_MODEL: process.env.OLLAMA_MODEL || 'nomic-embed-text',
  
  // Gemini
  GEMINI_API_KEY: process.env.GEMINI_API_KEY,
  GEMINI_BASE_URL: process.env.GEMINI_BASE_URL || 'https://generativelanguage.googleapis.com',
  GEMINI_MODEL: process.env.GEMINI_MODEL || 'text-embedding-004',
  
  // HuggingFace
  HUGGINGFACE_API_KEY: process.env.HUGGINGFACE_API_KEY || process.env.HF_TOKEN,
  HUGGINGFACE_MODEL: process.env.HF_MODEL || 'sentence-transformers/all-MiniLM-L6-v2',
  HUGGINGFACE_USE_LOCAL: process.env.HF_USE_LOCAL === 'true',
  
  // Local Server (OpenAI-compatible)
  LOCAL_EMBEDDING_URL: process.env.LOCAL_EMBEDDING_URL || 'http://localhost:4127',
  LOCAL_EMBEDDING_MODEL: process.env.LOCAL_EMBEDDING_MODEL || 'qwen2.5:0.5b',
  
  // Generic provider config
  PROVIDER_BASE_URL: process.env.PROVIDER_BASE_URL,
  PROVIDER_API_KEY: process.env.PROVIDER_API_KEY,
  PROVIDER_TIMEOUT: parseInt(process.env.PROVIDER_TIMEOUT || '30000'),
} as const;

// Provider-specific model dimensions mapping
export const PROVIDER_MODEL_DIMENSIONS: Record<string, Record<string, number>> = {
  openai: {
    'text-embedding-3-small': 1536,
    'text-embedding-3-large': 1536, // Can be 3072 but we use 1536 for simplicity
    'text-embedding-ada-002': 1536,
  },
  ollama: {
    'nomic-embed-text': 768,
    'all-minilm': 384,
    'mxbai-embed-large': 1024,
    'snowflake-arctic-embed': 1024,
  },
  gemini: {
    'text-embedding-004': 768,
  },
  huggingface: {
    'sentence-transformers/all-MiniLM-L6-v2': 384,
    'sentence-transformers/all-mpnet-base-v2': 768,
    'Xenova/all-MiniLM-L6-v2': 384,
    'Xenova/all-mpnet-base-v2': 768,
  },
  localserver: {
    'qwen2.5:0.5b': 896,
    'qwen2.5:1.5b': 896,
    'qwen2.5:3b': 2048,
  },
};

// Legacy support for existing configurations
export const ADVANCED_EMBEDDINGS = process.env.ADVANCED_EMBEDDINGS === 'true';

// Legacy compatibility exports (for existing code)
export const SIMPLE_EMBEDDING_MODEL = "text-embedding-3-large";
export const SIMPLE_EMBEDDING_DIMENSION = 1536;
export const ADVANCED_EMBEDDING_MODEL = "text-embedding-3-large";
export const ADVANCED_EMBEDDING_DIMENSION = 3072;
export const EMBEDDING_MODEL = EMBEDDING_MODEL_NAME;
export const EMBEDDING_DIMENSION = EMBEDDING_DIMENSIONS;

export const CHAT_MODEL = "gpt-4.1-2025-04-14"; // GPT-4.1 with 1M context window
export const TASK_ANALYSIS_MODEL = "gpt-4.1-2025-04-14";
export const MAX_EMBEDDING_BATCH_SIZE = 100;
export const MAX_CONTEXT_TOKENS = 1000000; // GPT-4.1 1 million token context window
export const TASK_ANALYSIS_MAX_TOKENS = 1000000;

// Environment variables
export const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
export const MCP_DEBUG = process.env.MCP_DEBUG === 'true' || process.env.NODE_ENV === 'development';

// TUI Colors for colorful console output (matching Python version)
export const TUIColors = {
  HEADER: '\x1b[95m',    // Light Magenta
  OKBLUE: '\x1b[94m',    // Light Blue 
  OKCYAN: '\x1b[96m',    // Light Cyan
  OKGREEN: '\x1b[92m',   // Light Green
  WARNING: '\x1b[93m',   // Yellow
  FAIL: '\x1b[91m',      // Red
  ENDC: '\x1b[0m',       // Reset to default
  BOLD: '\x1b[1m',
  UNDERLINE: '\x1b[4m',
  DIM: '\x1b[2m'
} as const;

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
let configuredProjectDir: string | null = null;

export function setProjectDir(dir: string) {
  configuredProjectDir = dir;
}

export function getProjectDir(): string {
  // Use configured project directory if set, otherwise use current working directory
  return configuredProjectDir || process.cwd();
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

// Provider configuration validation
export function validateProviderConfig(): { valid: boolean; errors: string[] } {
  const errors: string[] = [];
  
  // Check if at least one provider is configured
  const hasOpenAI = !!PROVIDER_CONFIG.OPENAI_API_KEY;
  const hasOllama = LOCAL_MODEL_AUTO_DETECT || !!PROVIDER_CONFIG.OLLAMA_BASE_URL;
  const hasGemini = !!PROVIDER_CONFIG.GEMINI_API_KEY;
  const hasHuggingFace = !!PROVIDER_CONFIG.HUGGINGFACE_API_KEY || PROVIDER_CONFIG.HUGGINGFACE_USE_LOCAL;
  
  if (!hasOpenAI && !hasOllama && !hasGemini && !hasHuggingFace) {
    errors.push('No embedding provider configured. Set at least one: OPENAI_API_KEY, OLLAMA_BASE_URL, GEMINI_API_KEY, or HF_TOKEN');
  }
  
  // Validate provider-specific requirements
  if (EMBEDDING_PROVIDER === 'openai' && !PROVIDER_CONFIG.OPENAI_API_KEY) {
    errors.push('OpenAI provider selected but OPENAI_API_KEY not set');
  }
  
  if (EMBEDDING_PROVIDER === 'gemini' && !PROVIDER_CONFIG.GEMINI_API_KEY) {
    errors.push('Gemini provider selected but GEMINI_API_KEY not set');
  }
  
  if (EMBEDDING_PROVIDER === 'huggingface' && !PROVIDER_CONFIG.HUGGINGFACE_USE_LOCAL && !PROVIDER_CONFIG.HUGGINGFACE_API_KEY) {
    errors.push('HuggingFace provider selected but neither HF_TOKEN nor HF_USE_LOCAL=true is set');
  }
  
  // Check dimension consistency
  const selectedProvider = EMBEDDING_PROVIDER as keyof typeof PROVIDER_MODEL_DIMENSIONS;
  const modelDimensions = PROVIDER_MODEL_DIMENSIONS[selectedProvider];
  if (modelDimensions) {
    const modelName = PROVIDER_CONFIG[`${selectedProvider.toUpperCase()}_MODEL` as keyof typeof PROVIDER_CONFIG] || EMBEDDING_MODEL_NAME;
    const expectedDimensions = modelDimensions[modelName as string];
    if (expectedDimensions && expectedDimensions !== EMBEDDING_DIMENSIONS && EMBEDDING_DIMENSIONS !== 1536) {
      errors.push(`Model ${modelName} expects ${expectedDimensions} dimensions, but EMBEDDING_DIMENSIONS is set to ${EMBEDDING_DIMENSIONS}`);
    }
  }
  
  return {
    valid: errors.length === 0,
    errors
  };
}

// Validate on startup if not in test mode
if (!process.env.NODE_ENV?.includes('test')) {
  const validation = validateProviderConfig();
  if (!validation.valid) {
    console.error("⚠️  Embedding provider configuration issues:");
    validation.errors.forEach(error => console.error(`   - ${error}`));
    if (EMBEDDING_PROVIDER === 'openai' && !PROVIDER_CONFIG.OPENAI_API_KEY) {
      console.error("\n💡 To use OpenAI embeddings, set OPENAI_API_KEY in your .env file");
      console.error("💡 Or switch to a local provider: EMBEDDING_PROVIDER=ollama");
    }
  }
}

// Log configuration loading
if (MCP_DEBUG) {
  console.log("🔧 Agent-MCP Node.js configuration loaded");
  console.log(`📁 Project Directory: ${getProjectDir()}`);
  console.log(`🗄️  Database Path: ${getDbPath()}`);
  console.log(`🤖 Embedding Provider: ${EMBEDDING_PROVIDER}`);
  console.log(`🤖 Embedding Model: ${EMBEDDING_MODEL_NAME} (${EMBEDDING_DIMENSIONS}D)`);
  console.log(`💬 Chat Model: ${CHAT_MODEL}`);
  if (EMBEDDING_PROVIDERS.length > 1) {
    console.log(`🔄 Provider Fallback Chain: ${EMBEDDING_PROVIDERS.join(' → ')}`);
  }
  if (LOCAL_MODEL_AUTO_DETECT) {
    console.log(`🔍 Local Model Auto-Detection: Enabled`);
  }
}