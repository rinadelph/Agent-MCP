// Extended configuration system for Agent-MCP
// Manages embedding providers, CLI agents, and advanced settings

import { join } from 'path';
import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'fs';
import { getAgentDir } from './config.js';
import { ToolCategories } from './toolConfig.js';

export interface ExtendedConfig {
  toolCategories: ToolCategories;
  embeddingProvider: string;
  cliAgents: string[];
  serverPort: number;
  projectDirectory?: string;
  configName?: string;
  advancedSettings: {
    embeddingModel?: string;
    embeddingDimensions?: number;
    maxBatchSize?: number;
    cliAgentTimeout?: number;
    defaultCLI?: string;
  };
  lastUpdated: string;
}

export interface NamedConfig {
  name: string;
  description: string;
  config: ExtendedConfig;
  createdAt: string;
  lastUsed?: string;
}

export const DEFAULT_EXTENDED_CONFIG: ExtendedConfig = {
  toolCategories: {
    basic: true,
    rag: true,
    memory: true,
    agentManagement: false,
    taskManagement: false,
    fileManagement: false,
    agentCommunication: false,
    sessionState: false,
    assistanceRequest: false,
    backgroundAgents: true,
  },
  embeddingProvider: 'openai',
  cliAgents: ['claude', 'gemini'],
  serverPort: 3001,
  projectDirectory: process.cwd(),
  advancedSettings: {
    embeddingModel: 'text-embedding-3-large',
    embeddingDimensions: 1536,
    maxBatchSize: 100,
    cliAgentTimeout: 30000,
    defaultCLI: 'claude'
  },
  lastUpdated: new Date().toISOString()
};

const EXTENDED_CONFIG_FILE = 'extended-config.json';
const NAMED_CONFIGS_FILE = 'named-configs.json';

// Import MANAGED_ENV_VARS for validation function
import { MANAGED_ENV_VARS } from './envManager.js';

function getExtendedConfigPath(): string {
  return join(getAgentDir(), EXTENDED_CONFIG_FILE);
}

export function loadExtendedConfig(): ExtendedConfig {
  const configPath = getExtendedConfigPath();
  
  if (!existsSync(configPath)) {
    return { ...DEFAULT_EXTENDED_CONFIG };
  }

  try {
    const configData = readFileSync(configPath, 'utf-8');
    const config = JSON.parse(configData) as ExtendedConfig;
    
    // Merge with defaults to handle new fields
    return {
      ...DEFAULT_EXTENDED_CONFIG,
      ...config,
      advancedSettings: {
        ...DEFAULT_EXTENDED_CONFIG.advancedSettings,
        ...config.advancedSettings
      }
    };
  } catch (error) {
    console.warn(`Warning: Could not load extended config, using defaults. Error: ${error}`);
    return { ...DEFAULT_EXTENDED_CONFIG };
  }
}

export function saveExtendedConfig(config: ExtendedConfig): void {
  try {
    const configPath = getExtendedConfigPath();
    const configDir = getAgentDir();
    
    // Create directory if it doesn't exist
    if (!existsSync(configDir)) {
      mkdirSync(configDir, { recursive: true });
    }
    
    // Update timestamp
    config.lastUpdated = new Date().toISOString();
    
    writeFileSync(configPath, JSON.stringify(config, null, 2));
  } catch (error) {
    console.error(`Error saving extended configuration: ${error}`);
    throw error;
  }
}

export function updateEmbeddingProvider(provider: string): void {
  const config = loadExtendedConfig();
  config.embeddingProvider = provider;
  saveExtendedConfig(config);
  
  // Also update the environment variable for immediate effect
  process.env.EMBEDDING_PROVIDER = provider;
}

export function updateCLIAgents(agents: string[]): void {
  const config = loadExtendedConfig();
  config.cliAgents = agents;
  saveExtendedConfig(config);
}

export function getEmbeddingProvider(): string {
  const config = loadExtendedConfig();
  return config.embeddingProvider;
}

export function getCLIAgents(): string[] {
  const config = loadExtendedConfig();
  return config.cliAgents;
}

export function getDefaultCLI(): string {
  const config = loadExtendedConfig();
  return config.advancedSettings.defaultCLI || 'claude';
}

// Environment variable mapping for embedding providers
export function getEmbeddingProviderEnvVars(provider: string): Record<string, string | undefined> {
  const envVars: Record<string, string | undefined> = {};
  
  switch (provider) {
    case 'openai':
      envVars.OPENAI_API_KEY = process.env.OPENAI_API_KEY;
      envVars.EMBEDDING_PROVIDER = 'openai';
      break;
    case 'ollama':
      envVars.EMBEDDING_PROVIDER = 'ollama';
      envVars.OLLAMA_HOST = process.env.OLLAMA_HOST || 'http://localhost:11434';
      break;
    case 'huggingface':
      envVars.HUGGINGFACE_API_KEY = process.env.HUGGINGFACE_API_KEY;
      envVars.EMBEDDING_PROVIDER = 'huggingface';
      break;
    case 'gemini':
      envVars.GEMINI_API_KEY = process.env.GEMINI_API_KEY;
      envVars.EMBEDDING_PROVIDER = 'gemini';
      break;
    case 'localserver':
      envVars.EMBEDDING_PROVIDER = 'localserver';
      envVars.LOCAL_SERVER_URL = process.env.LOCAL_SERVER_URL || 'http://localhost:8080';
      break;
  }
  
  return envVars;
}

// Check if embedding provider configuration is valid
export function validateEmbeddingProviderConfig(provider: string): { valid: boolean; errors: string[] } {
  const errors: string[] = [];
  const envVars = getEmbeddingProviderEnvVars(provider);
  
  switch (provider) {
    case 'openai':
      if (!envVars.OPENAI_API_KEY) {
        errors.push('OpenAI API key not set. Add OPENAI_API_KEY to your .env file');
      }
      break;
    case 'huggingface':
      if (!envVars.HUGGINGFACE_API_KEY) {
        errors.push('HuggingFace API key not set. Add HUGGINGFACE_API_KEY to your .env file');
      }
      break;
    case 'gemini':
      if (!envVars.GEMINI_API_KEY) {
        errors.push('Gemini API key not set. Add GEMINI_API_KEY to your .env file');
      }
      break;
    case 'ollama':
    case 'localserver':
      // These don't require API keys, but we could check if services are running
      break;
    default:
      errors.push(`Unknown embedding provider: ${provider}`);
  }
  
  return {
    valid: errors.length === 0,
    errors
  };
}

// Named configuration management functions
function getNamedConfigsPath(): string {
  return join(getAgentDir(), NAMED_CONFIGS_FILE);
}

export function loadNamedConfigs(): NamedConfig[] {
  const configPath = getNamedConfigsPath();
  
  if (!existsSync(configPath)) {
    return [];
  }

  try {
    const configData = readFileSync(configPath, 'utf-8');
    return JSON.parse(configData) as NamedConfig[];
  } catch (error) {
    console.warn(`Warning: Could not load named configs, returning empty list. Error: ${error}`);
    return [];
  }
}

export function saveNamedConfigs(configs: NamedConfig[]): void {
  try {
    const configPath = getNamedConfigsPath();
    const configDir = getAgentDir();
    
    if (!existsSync(configDir)) {
      mkdirSync(configDir, { recursive: true });
    }
    
    writeFileSync(configPath, JSON.stringify(configs, null, 2));
  } catch (error) {
    console.error(`Error saving named configurations: ${error}`);
    throw error;
  }
}

export function saveNamedConfig(name: string, description: string, config: ExtendedConfig): void {
  const configs = loadNamedConfigs();
  
  // Remove existing config with same name
  const filteredConfigs = configs.filter(c => c.name !== name);
  
  // Add new config
  const namedConfig: NamedConfig = {
    name,
    description,
    config: {
      ...config,
      configName: name,
      lastUpdated: new Date().toISOString()
    },
    createdAt: new Date().toISOString(),
    lastUsed: new Date().toISOString()
  };
  
  filteredConfigs.push(namedConfig);
  saveNamedConfigs(filteredConfigs);
}

export function loadNamedConfig(name: string): NamedConfig | null {
  const configs = loadNamedConfigs();
  const config = configs.find(c => c.name === name);
  
  if (config) {
    // Update last used timestamp
    config.lastUsed = new Date().toISOString();
    saveNamedConfigs(configs);
  }
  
  return config || null;
}

export function deleteNamedConfig(name: string): boolean {
  const configs = loadNamedConfigs();
  const filteredConfigs = configs.filter(c => c.name !== name);
  
  if (filteredConfigs.length === configs.length) {
    return false; // Config not found
  }
  
  saveNamedConfigs(filteredConfigs);
  return true;
}

export function isEnvVariableRequired(key: string, embeddingProvider?: string): boolean {
  const envVar = MANAGED_ENV_VARS.find(v => v.key === key);
  if (!envVar) return false;
  
  // Dynamic requirements based on selected embedding provider
  if (embeddingProvider) {
    switch (key) {
      case 'OPENAI_API_KEY':
        return embeddingProvider === 'openai';
      case 'HUGGINGFACE_API_KEY':
        return embeddingProvider === 'huggingface';
      case 'GEMINI_API_KEY':
        return embeddingProvider === 'gemini';
    }
  }
  
  return envVar.required;
}