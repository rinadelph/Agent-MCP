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

export async function getPortRecommendations(): Promise<number[]> {
  const commonRanges = [
    // Common development ports
    { start: 3000, end: 3010 },
    { start: 8000, end: 8010 },
    { start: 9000, end: 9010 },
    { start: 5000, end: 5010 },
    { start: 4000, end: 4010 }
  ];
  
  const availablePorts: number[] = [];
  
  for (const range of commonRanges) {
    for (let port = range.start; port <= range.end; port++) {
      if (await isPortAvailable(port)) {
        availablePorts.push(port);
        if (availablePorts.length >= 10) { // Limit to first 10 available
          return availablePorts;
        }
      }
    }
  }
  
  return availablePorts;
}