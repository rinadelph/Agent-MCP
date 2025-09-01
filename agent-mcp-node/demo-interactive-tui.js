#!/usr/bin/env node

/**
 * Demo script for the Interactive TUI functionality
 * Shows how to use the new toggleable configuration features
 */

import { TUIColors } from './src/core/config.js';

console.clear();
console.log(`${TUIColors.HEADER}╔══════════════════════════════════════════════════════════════╗${TUIColors.ENDC}`);
console.log(`${TUIColors.HEADER}║                                                              ║${TUIColors.ENDC}`);
console.log(`${TUIColors.HEADER}║    🎛️  Agent-MCP Interactive TUI Demo & Usage Guide         ║${TUIColors.ENDC}`);
console.log(`${TUIColors.HEADER}║                                                              ║${TUIColors.ENDC}`);
console.log(`${TUIColors.HEADER}╚══════════════════════════════════════════════════════════════╝${TUIColors.ENDC}`);
console.log('');

console.log(`${TUIColors.OKGREEN}✨ NEW FEATURES IMPLEMENTED:${TUIColors.ENDC}`);
console.log('');

console.log(`${TUIColors.OKCYAN}📱 1. Interactive TUI (Real-time Configuration)${TUIColors.ENDC}`);
console.log('   • Toggle tool categories while server is running');
console.log('   • Switch between predefined modes instantly');
console.log('   • View detailed tool information');
console.log('   • Hot-reload configuration without restart');
console.log('');

console.log(`${TUIColors.OKCYAN}🔧 2. Runtime Configuration Management${TUIColors.ENDC}`);
console.log('   • HTTP API endpoints for configuration');
console.log('   • Dynamic tool loading/unloading');
console.log('   • Configuration persistence');
console.log('   • Validation and error handling');
console.log('');

console.log(`${TUIColors.OKCYAN}🎯 3. Enhanced CLI Options${TUIColors.ENDC}`);
console.log('   • --interactive for persistent TUI');
console.log('   • --config-mode for one-time setup');
console.log('   • Standalone TUI launcher script');
console.log('   • Environment variable overrides');
console.log('');

console.log(`${TUIColors.BOLD}🚀 HOW TO USE:${TUIColors.ENDC}`);
console.log('');

console.log(`${TUIColors.WARNING}Option 1: Start server with Interactive TUI${TUIColors.ENDC}`);
console.log(`${TUIColors.DIM}   npm run server --interactive${TUIColors.ENDC}`);
console.log('   • Server starts and TUI launches automatically');
console.log('   • Modify configuration while server runs');
console.log('   • Changes apply immediately');
console.log('');

console.log(`${TUIColors.WARNING}Option 2: Use Standalone TUI Launcher${TUIColors.ENDC}`);
console.log(`${TUIColors.DIM}   # Terminal 1: Start server${TUIColors.ENDC}`);
console.log(`${TUIColors.DIM}   npm run server --no-tui${TUIColors.ENDC}`);
console.log('');
console.log(`${TUIColors.DIM}   # Terminal 2: Launch TUI${TUIColors.ENDC}`);
console.log(`${TUIColors.DIM}   ./agent-mcp-tui.js${TUIColors.ENDC}`);
console.log('');

console.log(`${TUIColors.WARNING}Option 3: HTTP API Configuration${TUIColors.ENDC}`);
console.log(`${TUIColors.DIM}   # Get current configuration${TUIColors.ENDC}`);
console.log(`${TUIColors.DIM}   curl http://localhost:3001/config${TUIColors.ENDC}`);
console.log('');
console.log(`${TUIColors.DIM}   # Update configuration${TUIColors.ENDC}`);
console.log(`${TUIColors.DIM}   curl -X POST -H "Content-Type: application/json" \\${TUIColors.ENDC}`);
console.log(`${TUIColors.DIM}        -d '{"basic":true,"rag":true,"memory":true,...}' \\${TUIColors.ENDC}`);
console.log(`${TUIColors.DIM}        http://localhost:3001/config${TUIColors.ENDC}`);
console.log('');

console.log(`${TUIColors.BOLD}🎛️  TUI FEATURES:${TUIColors.ENDC}`);
console.log('');

console.log(`${TUIColors.OKGREEN}✅ Main Menu Options:${TUIColors.ENDC}`);
console.log('   🎯 Switch to Predefined Mode - Quick mode switching');
console.log('   🔧 Toggle Individual Categories - Granular control');  
console.log('   🛠️  View/Toggle Specific Tools - See all available tools');
console.log('   📊 View Configuration Details - Detailed status and warnings');
console.log('   💾 Save & Apply Configuration - Persist and activate changes');
console.log('   🔄 Reset to Default - Restore full mode');
console.log('');

console.log(`${TUIColors.OKGREEN}✅ Real-time Information:${TUIColors.ENDC}`);
console.log('   • Current mode and enabled categories');
console.log('   • Estimated tool count and memory usage');
console.log('   • Server status (running/stopped)');
console.log('   • Configuration warnings and validation');
console.log('');

console.log(`${TUIColors.BOLD}📊 AVAILABLE MODES:${TUIColors.ENDC}`);
console.log('');

const modes = [
  { name: 'Full', tools: '33', desc: 'All tools - complete agent orchestration' },
  { name: 'Memory+RAG', tools: '15', desc: 'Knowledge assistance without agent management' },
  { name: 'Minimal', tools: '1', desc: 'Just health checks - fastest startup' },
  { name: 'Development', tools: '18-20', desc: 'Solo development with context' }
];

modes.forEach(mode => {
  console.log(`   ${TUIColors.OKCYAN}${mode.name.padEnd(12)}${TUIColors.ENDC} ${TUIColors.OKGREEN}${mode.tools.padEnd(6)} tools${TUIColors.ENDC} - ${mode.desc}`);
});

console.log('');
console.log(`${TUIColors.BOLD}🔍 EXAMPLE WORKFLOW:${TUIColors.ENDC}`);
console.log('');

console.log(`${TUIColors.DIM}1. Start with full mode:${TUIColors.ENDC}`);
console.log(`   npm run server --mode full`);
console.log('');

console.log(`${TUIColors.DIM}2. Launch interactive TUI:${TUIColors.ENDC}`);
console.log(`   ./agent-mcp-tui.js`);
console.log('');

console.log(`${TUIColors.DIM}3. In TUI, switch to Memory+RAG mode:${TUIColors.ENDC}`);
console.log('   • Choose "Switch to Predefined Mode"');
console.log('   • Select "Memory + RAG Mode"');
console.log('   • Apply changes');
console.log('');

console.log(`${TUIColors.DIM}4. Server automatically reconfigures:${TUIColors.ENDC}`);
console.log('   • Tools reduced from 33 to 15');
console.log('   • Agent management disabled');
console.log('   • RAG and memory features active');
console.log('');

console.log(`${TUIColors.OKGREEN}🎉 Ready to try the Interactive TUI!${TUIColors.ENDC}`);
console.log(`${TUIColors.DIM}Start with: npm run server --interactive${TUIColors.ENDC}`);
console.log('');