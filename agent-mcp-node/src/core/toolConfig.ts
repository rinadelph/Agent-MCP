// Tool configuration system for Agent-MCP Node.js
// Manages which tool categories are enabled/disabled

import { join } from 'path';
import { existsSync, readFileSync, writeFileSync } from 'fs';
import { getAgentDir, ensureAgentDir } from './config.js';

// Tool category definitions
export interface ToolCategories {
  basic: boolean;           // Health checks, system status (always enabled)
  rag: boolean;            // RAG/vector search functionality
  memory: boolean;         // Memory and project context
  agentManagement: boolean; // Agent creation/termination/management
  taskManagement: boolean;  // Task creation, assignment, operations
  fileManagement: boolean;  // File operations
  agentCommunication: boolean; // Inter-agent messaging
  sessionState: boolean;   // Session persistence and recovery
  assistanceRequest: boolean; // Intelligent assistance requests
  backgroundAgents: boolean; // Background/standalone agents without task hierarchy
}

// Predefined modes
export interface ConfigMode {
  name: string;
  description: string;
  categories: ToolCategories;
}

export const PREDEFINED_MODES: Record<string, ConfigMode> = {
  full: {
    name: 'Full Mode',
    description: 'All tools enabled - complete agent orchestration platform',
    categories: {
      basic: true,
      rag: true,
      memory: true,
      agentManagement: true,
      taskManagement: true,
      fileManagement: true,
      agentCommunication: true,
      sessionState: true,
      assistanceRequest: true,
      backgroundAgents: true,
    }
  },
  memoryRag: {
    name: 'Memory + RAG Mode',
    description: 'Lightweight mode with just memory, RAG, and basic functionality',
    categories: {
      basic: true,
      rag: true,
      memory: true,
      agentManagement: false,
      taskManagement: false,
      fileManagement: true, // Keep for RAG content access
      agentCommunication: false,
      sessionState: true, // Keep for persistence
      assistanceRequest: false,
      backgroundAgents: false,
    }
  },
  minimal: {
    name: 'Minimal Mode',
    description: 'Only essential tools - health checks and basic functionality',
    categories: {
      basic: true,
      rag: false,
      memory: false,
      agentManagement: false,
      taskManagement: false,
      fileManagement: false,
      agentCommunication: false,
      sessionState: false,
      assistanceRequest: false,
      backgroundAgents: false,
    }
  },
  development: {
    name: 'Development Mode',
    description: 'Tools useful for development - RAG, memory, files, no agent orchestration',
    categories: {
      basic: true,
      rag: true,
      memory: true,
      agentManagement: false,
      taskManagement: false,
      fileManagement: true,
      agentCommunication: false,
      sessionState: true,
      assistanceRequest: true,
      backgroundAgents: false,
    }
  },
  background: {
    name: 'Background Agents Mode',
    description: 'Background agents with memory and RAG - no hierarchical task management',
    categories: {
      basic: true,
      rag: true,
      memory: true,
      agentManagement: false,
      taskManagement: false,
      fileManagement: true,
      agentCommunication: true,
      sessionState: true,
      assistanceRequest: true,
      backgroundAgents: true,
    }
  }
};

// Default configuration
export const DEFAULT_CONFIG: ToolCategories = PREDEFINED_MODES.full?.categories || {
  basic: true,
  rag: true,
  memory: true,
  agentManagement: true,
  taskManagement: true,
  fileManagement: true,
  agentCommunication: true,
  sessionState: true,
  assistanceRequest: true,
  backgroundAgents: true,
};

// Configuration file management
const CONFIG_FILE_NAME = 'tool-config.json';

export function getConfigPath(): string {
  return join(getAgentDir(), CONFIG_FILE_NAME);
}

export interface ToolConfigFile {
  version: string;
  mode?: string;
  categories: ToolCategories;
  lastModified: string;
}

export function loadToolConfig(): ToolCategories {
  const configPath = getConfigPath();
  
  if (!existsSync(configPath)) {
    return DEFAULT_CONFIG;
  }
  
  try {
    const configData = readFileSync(configPath, 'utf-8');
    const config: ToolConfigFile = JSON.parse(configData);
    
    // Ensure basic tools are always enabled
    config.categories.basic = true;
    
    return config.categories;
  } catch (error) {
    console.warn(`⚠️  Failed to load tool config: ${error instanceof Error ? error.message : error}`);
    console.warn('   Using default configuration');
    return DEFAULT_CONFIG;
  }
}

export function saveToolConfig(categories: ToolCategories, mode?: string): void {
  // Ensure directory exists before saving
  ensureAgentDir();
  const configPath = getConfigPath();
  
  // Ensure basic tools are always enabled
  categories.basic = true;
  
  const config: ToolConfigFile = {
    version: '1.0',
    mode,
    categories,
    lastModified: new Date().toISOString()
  };
  
  try {
    writeFileSync(configPath, JSON.stringify(config, null, 2));
  } catch (error) {
    console.error(`❌ Failed to save tool config: ${error instanceof Error ? error.message : error}`);
    throw error;
  }
}

export function getConfigMode(categories: ToolCategories): string | null {
  // Check if current config matches any predefined mode
  for (const [modeKey, mode] of Object.entries(PREDEFINED_MODES)) {
    const match = Object.entries(mode.categories).every(
      ([key, value]) => categories[key as keyof ToolCategories] === value
    );
    if (match) {
      return modeKey;
    }
  }
  return null; // Custom configuration
}

export function validateToolConfig(categories: ToolCategories): { valid: boolean; warnings: string[] } {
  const warnings: string[] = [];
  
  // Basic tools are always required
  if (!categories.basic) {
    categories.basic = true;
    warnings.push('Basic tools are required and have been enabled');
  }
  
  // RAG requires memory for context storage
  if (categories.rag && !categories.memory) {
    warnings.push('RAG functionality works best with memory/context tools enabled');
  }
  
  // Agent management requires task management
  if (categories.agentManagement && !categories.taskManagement) {
    warnings.push('Agent management typically requires task management for agent coordination');
  }
  
  // Agent communication requires agent management
  if (categories.agentCommunication && !categories.agentManagement) {
    warnings.push('Agent communication requires agent management to be enabled');
  }
  
  return {
    valid: true,
    warnings
  };
}

export function getEnabledCategories(categories: ToolCategories): string[] {
  return Object.entries(categories)
    .filter(([_, enabled]) => enabled)
    .map(([category, _]) => category);
}

export function getDisabledCategories(categories: ToolCategories): string[] {
  return Object.entries(categories)
    .filter(([_, enabled]) => !enabled)
    .map(([category, _]) => category);
}

export function getCategoryDescription(category: keyof ToolCategories): string {
  const descriptions: Record<keyof ToolCategories, string> = {
    basic: 'Health checks, system status, and core functionality',
    rag: 'Vector search, knowledge base queries, and retrieval augmented generation',
    memory: 'Project context storage and persistent memory management', 
    agentManagement: 'Agent creation, termination, and lifecycle management',
    taskManagement: 'Task creation, assignment, and operational workflows',
    fileManagement: 'File operations and content access for RAG indexing',
    agentCommunication: 'Inter-agent messaging and collaboration protocols',
    sessionState: 'Session persistence, recovery, and state management',
    assistanceRequest: 'Intelligent assistance routing and request handling',
    backgroundAgents: 'Standalone background agents without hierarchical task constraints'
  };
  
  return descriptions[category] || 'No description available';
}

// Environment variable overrides
export function applyEnvironmentOverrides(categories: ToolCategories): ToolCategories {
  const overrides: Partial<ToolCategories> = {};
  
  // Check for environment variable overrides
  if (process.env.AGENT_MCP_ENABLE_RAG !== undefined) {
    overrides.rag = process.env.AGENT_MCP_ENABLE_RAG === 'true';
  }
  if (process.env.AGENT_MCP_ENABLE_MEMORY !== undefined) {
    overrides.memory = process.env.AGENT_MCP_ENABLE_MEMORY === 'true';
  }
  if (process.env.AGENT_MCP_ENABLE_AGENTS !== undefined) {
    overrides.agentManagement = process.env.AGENT_MCP_ENABLE_AGENTS === 'true';
  }
  if (process.env.AGENT_MCP_ENABLE_TASKS !== undefined) {
    overrides.taskManagement = process.env.AGENT_MCP_ENABLE_TASKS === 'true';
  }
  if (process.env.AGENT_MCP_ENABLE_FILES !== undefined) {
    overrides.fileManagement = process.env.AGENT_MCP_ENABLE_FILES === 'true';
  }
  if (process.env.AGENT_MCP_ENABLE_COMM !== undefined) {
    overrides.agentCommunication = process.env.AGENT_MCP_ENABLE_COMM === 'true';
  }
  if (process.env.AGENT_MCP_ENABLE_SESSION !== undefined) {
    overrides.sessionState = process.env.AGENT_MCP_ENABLE_SESSION === 'true';
  }
  if (process.env.AGENT_MCP_ENABLE_ASSIST !== undefined) {
    overrides.assistanceRequest = process.env.AGENT_MCP_ENABLE_ASSIST === 'true';
  }
  
  return { ...categories, ...overrides };
}

console.log('✅ Tool configuration system loaded');