// Task tools index for Agent-MCP Node.js
// Imports all task tool modules to register them with the MCP server

// Import core utilities (no tools, just shared functions)
import './core.js';

// Import and register task creation tools
import './creation.js';

// Import and register task management tools  
import './management.js';

// Import and register task operations tools
import './operations.js';

console.log('✅ All task tools loaded and registered successfully');

// Export the core utilities for other modules to use
export * from './core.js';