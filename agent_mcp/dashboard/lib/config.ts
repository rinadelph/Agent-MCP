// Configuration for the dashboard
export const config = {
  // Default server configuration
  defaultServer: {
    host: process.env.NEXT_PUBLIC_DEFAULT_SERVER_HOST || 'localhost',
    port: parseInt(process.env.NEXT_PUBLIC_DEFAULT_SERVER_PORT || '8080'),
    name: process.env.NEXT_PUBLIC_DEFAULT_SERVER_NAME || 'Local Development'
  },
  
  // Auto-detection configuration
  autoDetect: {
    enabled: process.env.NEXT_PUBLIC_AUTO_CONNECT !== 'false',
    // Try a wide range of ports commonly used for development
    ports: (process.env.NEXT_PUBLIC_AUTO_DETECT_PORTS || '8080,8081,8082,8083,8084,8085,8086,8087,8088,8089,8090,8091,8092,8093,8094,8095,3000,3001,3002,3003,4000,4001,5000,5001')
      .split(',')
      .map(p => parseInt(p.trim()))
      .filter(p => !isNaN(p))
  },
  
  // API configuration
  api: {
    timeout: 5000, // 5 seconds timeout for API calls
    retryCount: 3,
    retryDelay: 1000 // 1 second between retries
  }
}

// Helper to get all possible server configurations for auto-detection
export function getAutoDetectServers(): Array<{ host: string; port: number }> {
  return config.autoDetect.ports.map(port => ({
    host: config.defaultServer.host,
    port
  }))
}