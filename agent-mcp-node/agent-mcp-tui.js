#!/usr/bin/env node

/**
 * Agent-MCP Standalone TUI
 * 
 * This script can be run independently to configure Agent-MCP
 * while the server is running or to modify saved configuration.
 * 
 * Usage:
 *   node agent-mcp-tui.js                    # Configure local server
 *   node agent-mcp-tui.js http://host:port   # Configure remote server
 */

import { execSync } from 'child_process';
import { TUIColors } from './src/core/config.js';

const serverUrl = process.argv[2] || 'http://localhost:3001';

console.log(`${TUIColors.HEADER}╔════════════════════════════════════════════════════════════╗${TUIColors.ENDC}`);
console.log(`${TUIColors.HEADER}║                                                            ║${TUIColors.ENDC}`);
console.log(`${TUIColors.HEADER}║           🎛️  Agent-MCP Configuration TUI                 ║${TUIColors.ENDC}`);
console.log(`${TUIColors.HEADER}║                                                            ║${TUIColors.ENDC}`);
console.log(`${TUIColors.HEADER}║    Real-time configuration management for Agent-MCP       ║${TUIColors.ENDC}`);
console.log(`${TUIColors.HEADER}║                                                            ║${TUIColors.ENDC}`);
console.log(`${TUIColors.HEADER}╚════════════════════════════════════════════════════════════╝${TUIColors.ENDC}`);
console.log('');

console.log(`${TUIColors.OKCYAN}🎯 Target Server: ${serverUrl}${TUIColors.ENDC}`);
console.log(`${TUIColors.DIM}Starting interactive configuration...${TUIColors.ENDC}\n`);

try {
  // Use tsx to run the TypeScript TUI launcher
  execSync(`npx tsx src/tui/launcher.ts "${serverUrl}"`, { 
    stdio: 'inherit', 
    cwd: process.cwd() 
  });
} catch (error) {
  console.error(`${TUIColors.FAIL}❌ Failed to launch TUI: ${error.message}${TUIColors.ENDC}`);
  process.exit(1);
}