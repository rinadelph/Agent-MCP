// Pre-launch TUI for Agent-MCP configuration
// Runs BEFORE server starts, asks for settings, then launches server with those settings

import { ToolCategories } from '../core/toolConfig.js';
import { TUIColors } from '../core/config.js';
import { launchPracticalConfigurationTUI } from './practical.js';

export async function launchPreConfigurationTUI(): Promise<{
  toolConfig: ToolCategories;
  serverPort: number;
}> {
  // Use the practical TUI - no animations, focus on functionality
  const result = await launchPracticalConfigurationTUI();
  
  console.log(`${TUIColors.OKGREEN}🚀 Starting Agent-MCP server with your configuration...${TUIColors.ENDC}`);
  if (result.configName) {
    console.log(`${TUIColors.OKBLUE}📋 Using configuration: ${result.configName}${TUIColors.ENDC}`);
  }
  console.log(`${TUIColors.OKBLUE}🌐 Server will start on port: ${result.serverPort}${TUIColors.ENDC}`);
  console.log();
  
  return {
    toolConfig: result.toolConfig,
    serverPort: result.serverPort
  };
}