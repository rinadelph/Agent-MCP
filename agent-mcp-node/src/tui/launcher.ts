#!/usr/bin/env node

// TUI Launcher - Can be run independently to configure a running Agent-MCP server
// This allows dynamic configuration without stopping the server

import { launchInteractiveTUI } from './interactive.js';
import { getRuntimeConfigManager } from '../core/runtimeConfig.js';
import { ToolCategories } from '../core/toolConfig.js';
import { TUIColors } from '../core/config.js';

class TUILauncher {
  private serverUrl: string;
  private runtimeManager = getRuntimeConfigManager();

  constructor(serverUrl: string = 'http://localhost:3001') {
    this.serverUrl = serverUrl;
  }

  async launch(): Promise<void> {
    console.log(`${TUIColors.HEADER}🚀 Agent-MCP TUI Launcher${TUIColors.ENDC}`);
    console.log(`${TUIColors.DIM}Connecting to: ${this.serverUrl}${TUIColors.ENDC}\n`);

    // Check if server is running
    const serverRunning = await this.checkServerStatus();
    
    if (!serverRunning) {
      console.log(`${TUIColors.WARNING}⚠️  Server not detected at ${this.serverUrl}${TUIColors.ENDC}`);
      console.log(`${TUIColors.DIM}You can still modify the configuration for next server start.${TUIColors.ENDC}\n`);
    }

    // Launch interactive TUI
    await launchInteractiveTUI({
      serverRunning,
      onConfigChange: async (config: ToolCategories) => {
        if (serverRunning) {
          await this.applyConfigurationToRunningServer(config);
        }
      }
    });
  }

  private async checkServerStatus(): Promise<boolean> {
    try {
      // Create AbortController for timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 5000);
      
      const response = await fetch(`${this.serverUrl}/health`, {
        method: 'GET',
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      return response.ok;
    } catch (error) {
      return false;
    }
  }

  private async applyConfigurationToRunningServer(config: ToolCategories): Promise<void> {
    try {
      console.log(`${TUIColors.OKCYAN}🔄 Applying configuration to running server...${TUIColors.ENDC}`);
      
      const result = await this.runtimeManager.updateConfiguration(config);
      
      if (result.success) {
        console.log(`${TUIColors.OKGREEN}✅ Configuration applied successfully:${TUIColors.ENDC}`);
        result.changes.forEach(change => console.log(`   ${change}`));
      } else {
        console.log(`${TUIColors.WARNING}⚠️  Configuration applied with errors:${TUIColors.ENDC}`);
        result.changes.forEach(change => console.log(`   ${change}`));
        result.errors.forEach(error => console.log(`   ${TUIColors.FAIL}❌ ${error}${TUIColors.ENDC}`));
      }

      if (result.changes.length > 0) {
        console.log(`${TUIColors.DIM}💡 Some changes may require a server restart to take full effect${TUIColors.ENDC}`);
      }

    } catch (error) {
      console.log(`${TUIColors.FAIL}❌ Failed to apply configuration: ${error instanceof Error ? error.message : error}${TUIColors.ENDC}`);
    }
  }
}

// CLI interface
if (import.meta.url === `file://${process.argv[1]}`) {
  const serverUrl = process.argv[2] || 'http://localhost:3001';
  const launcher = new TUILauncher(serverUrl);
  launcher.launch().catch(error => {
    console.error(`${TUIColors.FAIL}❌ TUI Launcher failed: ${error instanceof Error ? error.message : error}${TUIColors.ENDC}`);
    process.exit(1);
  });
}

export { TUILauncher };