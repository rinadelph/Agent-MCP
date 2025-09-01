// Runtime configuration management for Agent-MCP
// Allows hot-reloading of tool configuration without server restart

import { ToolCategories, loadToolConfig, saveToolConfig, getConfigMode } from './toolConfig.js';
import { toolRegistry } from '../tools/registry.js';
import { TUIColors, MCP_DEBUG } from './config.js';

export class RuntimeConfigManager {
  private currentConfig: ToolCategories;
  private loadedModules: Set<string> = new Set();

  constructor(initialConfig?: ToolCategories) {
    this.currentConfig = initialConfig || loadToolConfig();
  }

  getCurrentConfig(): ToolCategories {
    return { ...this.currentConfig };
  }

  async updateConfiguration(newConfig: ToolCategories): Promise<{success: boolean, changes: string[], errors: string[]}> {
    const changes: string[] = [];
    const errors: string[] = [];

    try {
      // Compare configurations to see what changed
      const configChanges = this.getConfigurationChanges(this.currentConfig, newConfig);
      
      if (configChanges.length === 0) {
        return { success: true, changes: ['No changes detected'], errors: [] };
      }

      // Apply changes
      for (const change of configChanges) {
        try {
          if (change.action === 'enable') {
            await this.enableCategory(change.category);
            changes.push(`✅ Enabled ${change.category}`);
          } else if (change.action === 'disable') {
            await this.disableCategory(change.category);
            changes.push(`❌ Disabled ${change.category}`);
          }
        } catch (error) {
          const errorMsg = `Failed to ${change.action} ${change.category}: ${error instanceof Error ? error.message : error}`;
          errors.push(errorMsg);
        }
      }

      // Update current configuration
      this.currentConfig = { ...newConfig };

      // Save to file
      const currentMode = getConfigMode(newConfig);
      saveToolConfig(newConfig, currentMode || undefined);
      changes.push('💾 Configuration saved');

      return { success: errors.length === 0, changes, errors };

    } catch (error) {
      errors.push(`Configuration update failed: ${error instanceof Error ? error.message : error}`);
      return { success: false, changes, errors };
    }
  }

  private async enableCategory(category: keyof ToolCategories): Promise<void> {
    if (category === 'basic') return; // Basic is always enabled

    const moduleMap: Record<keyof ToolCategories, string> = {
      basic: '../../tools/basic.js',
      rag: '../../tools/rag.js',
      memory: '../../tools/project_context.js',
      agentManagement: '../../tools/agent.js',
      taskManagement: '../../tools/tasks/index.js',
      fileManagement: '../../tools/file_management.js',
      agentCommunication: '../../tools/agentCommunication.js',
      sessionState: '../../tools/sessionState.js',
      assistanceRequest: '../../tools/assistanceRequest.js',
      backgroundAgents: '../../tools/backgroundAgents.js'
    };

    const modulePath = moduleMap[category];
    if (!modulePath) {
      throw new Error(`Unknown category: ${category}`);
    }

    // Load the module if not already loaded
    if (!this.loadedModules.has(modulePath)) {
      try {
        await import(modulePath);
        this.loadedModules.add(modulePath);
        if (MCP_DEBUG) {
          console.log(`🔄 Hot-loaded module: ${modulePath}`);
        }
      } catch (error) {
        throw new Error(`Failed to load module ${modulePath}: ${error instanceof Error ? error.message : error}`);
      }
    }
  }

  private async disableCategory(category: keyof ToolCategories): Promise<void> {
    if (category === 'basic') return; // Basic cannot be disabled

    // Note: We can't actually "unload" modules in Node.js easily
    // But we can mark them as disabled and the tool registry can filter them
    // This is a limitation of the current architecture
    
    if (MCP_DEBUG) {
      console.log(`⚠️  Category ${category} marked as disabled (tools remain loaded but inactive)`);
    }
  }

  private getConfigurationChanges(oldConfig: ToolCategories, newConfig: ToolCategories): Array<{action: 'enable' | 'disable', category: keyof ToolCategories}> {
    const changes: Array<{action: 'enable' | 'disable', category: keyof ToolCategories}> = [];

    for (const [category, enabled] of Object.entries(newConfig) as Array<[keyof ToolCategories, boolean]>) {
      const oldEnabled = oldConfig[category];
      
      if (oldEnabled !== enabled) {
        changes.push({
          action: enabled ? 'enable' : 'disable',
          category
        });
      }
    }

    return changes;
  }

  getToolCount(): number {
    const toolCounts = {
      basic: 1,
      rag: 2,
      memory: 6,
      agentManagement: 7,
      taskManagement: 6,
      fileManagement: 2,
      agentCommunication: 3,
      sessionState: 4,
      assistanceRequest: 1
    };

    return Object.entries(this.currentConfig)
      .filter(([_, enabled]) => enabled)
      .reduce((total, [category, _]) => {
        return total + (toolCounts[category as keyof typeof toolCounts] || 0);
      }, 0);
  }

  getActiveCategories(): string[] {
    return Object.entries(this.currentConfig)
      .filter(([_, enabled]) => enabled)
      .map(([category, _]) => category);
  }

  getInactiveCategories(): string[] {
    return Object.entries(this.currentConfig)
      .filter(([_, enabled]) => !enabled)
      .map(([category, _]) => category);
  }

  async reloadConfiguration(): Promise<void> {
    this.currentConfig = loadToolConfig();
  }
}

// Global runtime config manager instance
let runtimeConfigManager: RuntimeConfigManager | null = null;

export function getRuntimeConfigManager(): RuntimeConfigManager {
  if (!runtimeConfigManager) {
    runtimeConfigManager = new RuntimeConfigManager();
  }
  return runtimeConfigManager;
}

export function initializeRuntimeConfigManager(initialConfig: ToolCategories): void {
  runtimeConfigManager = new RuntimeConfigManager(initialConfig);
}