// Port availability checker for Agent-MCP
// Checks if ports are available before starting server

import { createServer } from 'net';

export async function isPortAvailable(port: number): Promise<boolean> {
  return new Promise((resolve) => {
    const server = createServer();
    
    server.listen(port, () => {
      server.once('close', () => {
        resolve(true);
      });
      server.close();
    });
    
    server.on('error', () => {
      resolve(false);
    });
  });
}

export async function findAvailablePort(startPort: number = 3001, maxPort: number = 3100): Promise<number> {
  for (let port = startPort; port <= maxPort; port++) {
    if (await isPortAvailable(port)) {
      return port;
    }
  }
  throw new Error(`No available ports found between ${startPort} and ${maxPort}`);
}

export async function getPortStatus(ports: number[]): Promise<{ port: number; available: boolean; }[]> {
  const results = await Promise.all(
    ports.map(async (port) => ({
      port,
      available: await isPortAvailable(port)
    }))
  );
  
  return results;
}

export function getPortRecommendations(): number[] {
  return [3001, 3002, 3003, 8000, 8001, 8080, 8081, 9000, 9001, 5000];
}