// Health check tool for Agent-MCP Node.js
// Minimal tool for system health monitoring

import { z } from 'zod';
import { registerTool } from './registry.js';
import { getDatabaseStats } from '../db/schema.js';
import { testDatabaseConnection } from '../db/connection.js';
import { VERSION } from '../core/config.js';

// Single health check tool
registerTool(
  'health',
  'Get the current health status of the Agent-MCP system including database and server status',
  z.object({}),
  async (args, context) => {
    try {
      const connectionTest = testDatabaseConnection();
      const stats = getDatabaseStats();
      
      const healthStatus = {
        status: connectionTest.success ? 'healthy' : 'unhealthy',
        database: {
          connected: connectionTest.success,
          vectorSupport: connectionTest.vecSupported,
          error: connectionTest.error
        },
        tables: stats,
        server: {
          version: VERSION,
          uptime: Math.floor(process.uptime()),
          memory: Math.round(process.memoryUsage().heapUsed / 1024 / 1024)
        }
      };
      
      const uptimeHours = Math.floor(healthStatus.server.uptime / 3600);
      const uptimeMinutes = Math.floor((healthStatus.server.uptime % 3600) / 60);
      
      return {
        content: [{
          type: 'text' as const,
          text: `🏥 **Agent-MCP Health Status**

**System Status:** ${healthStatus.status === 'healthy' ? '🟢 Healthy' : '🔴 Unhealthy'}

**Database:**
- Connected: ${healthStatus.database.connected ? '✅ Yes' : '❌ No'}
- Vector Search: ${healthStatus.database.vectorSupport ? '✅ Available' : '⚠️ Disabled'}
- Total Records: ${Object.values(healthStatus.tables).reduce((a, b) => (a + (b > 0 ? b : 0)), 0)}

**Server:**
- Version: ${healthStatus.server.version}
- Uptime: ${uptimeHours}h ${uptimeMinutes}m
- Memory: ${healthStatus.server.memory}MB

**Active Tables:**
${Object.entries(healthStatus.tables)
  .filter(([_, count]) => count > 0)
  .map(([table, count]) => `- ${table}: ${count}`)
  .join('\n') || '- No active records'}

${healthStatus.status === 'healthy' ? '✅ All systems operational' : '⚠️ System issues detected'}`
        }]
      };
    } catch (error) {
      return {
        content: [{
          type: 'text' as const,
          text: `❌ Health check failed: ${error instanceof Error ? error.message : String(error)}`
        }],
        isError: true
      };
    }
  }
);

console.log('✅ Health tool registered successfully');