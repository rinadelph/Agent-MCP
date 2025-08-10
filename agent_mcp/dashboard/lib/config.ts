// Configuration for the dashboard
export const config = {
  // Dashboard configuration
  dashboard: {
    port: 3847, // Fixed port for the dashboard
    url: 'http://localhost:3847'
  },
  
  // Default server configuration
  defaultServer: {
    host: process.env.NEXT_PUBLIC_DEFAULT_SERVER_HOST || 'localhost',
    port: parseInt(process.env.NEXT_PUBLIC_DEFAULT_SERVER_PORT || '8080'),
    name: process.env.NEXT_PUBLIC_DEFAULT_SERVER_NAME || 'Local Development'
  },
  
  // Auto-detection configuration
  autoDetect: {
    enabled: process.env.NEXT_PUBLIC_AUTO_CONNECT !== 'false',
    // Try common MCP server ports, but exclude dashboard port
    ports: (process.env.NEXT_PUBLIC_AUTO_DETECT_PORTS || '8080,8081,8082,8083,8084,8085,8086,8087,8088,8089,8090,8091,8092,8093,8094,8095,8000,8001,8002,8003,8004,8005,9000,9001,9002,9003')
      .split(',')
      .map(p => parseInt(p.trim()))
      .filter(p => !isNaN(p) && p !== 3847) // Exclude dashboard port
  },
  
  // API configuration with enhanced CORS support
  api: {
    timeout: 10000, // 10 seconds timeout for API calls
    retryCount: 3,
    retryDelay: 1000, // 1 second between retries
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    },
    cors: {
      mode: 'cors' as RequestMode,
      credentials: 'include' as RequestCredentials
    }
  }
}

// Helper to get all possible server configurations for auto-detection
export function getAutoDetectServers(): Array<{ host: string; port: number }> {
  return config.autoDetect.ports.map(port => ({
    host: config.defaultServer.host,
    port
  }))
}