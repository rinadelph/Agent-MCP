#!/usr/bin/env node

const { spawn } = require('child_process');
const net = require('net');

// Use a fixed port that's unlikely to conflict
const DASHBOARD_PORT = 3847; // Uncommon port for Agent-MCP dashboard

// Check if a port is available
function isPortAvailable(port) {
  return new Promise((resolve) => {
    const server = net.createServer();
    
    server.listen(port, () => {
      server.close(() => {
        resolve(true);
      });
    });
    
    server.on('error', () => {
      resolve(false);
    });
  });
}

// AGENT MCP ASCII art banner variants with gradient colors
const BANNER_VARIANTS = {
  FULL: `
\x1b[38;2;255;182;255m █████╗  ██████╗ ███████╗███╗   ██╗████████╗    ███╗   ███╗ ██████╗██████╗ \x1b[0m
\x1b[38;2;218;163;255m██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝    ████╗ ████║██╔════╝██╔══██╗\x1b[0m
\x1b[38;2;182;144;255m███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║       ██╔████╔██║██║     ██████╔╝\x1b[0m
\x1b[38;2;163;163;255m██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║       ██║╚██╔╝██║██║     ██╔═══╝ \x1b[0m
\x1b[38;2;144;182;255m██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║       ██║ ╚═╝ ██║╚██████╗██║     \x1b[0m
\x1b[38;2;144;255;255m╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝       ╚═╝     ╚═╝ ╚═════╝╚═╝     \x1b[0m
`,
  SPLIT: `
\x1b[38;2;255;182;255m █████╗  ██████╗ ███████╗███╗   ██╗████████╗\x1b[0m
\x1b[38;2;218;163;255m██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝\x1b[0m
\x1b[38;2;182;144;255m███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   \x1b[0m
\x1b[38;2;163;163;255m██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   \x1b[0m
\x1b[38;2;144;182;255m██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   \x1b[0m
\x1b[38;2;144;255;255m╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   \x1b[0m

\x1b[38;2;255;182;255m███╗   ███╗ ██████╗██████╗ \x1b[0m
\x1b[38;2;218;163;255m████╗ ████║██╔════╝██╔══██╗\x1b[0m
\x1b[38;2;182;144;255m██╔████╔██║██║     ██████╔╝\x1b[0m
\x1b[38;2;163;163;255m██║╚██╔╝██║██║     ██╔═══╝ \x1b[0m
\x1b[38;2;144;182;255m██║ ╚═╝ ██║╚██████╗██║     \x1b[0m
\x1b[38;2;144;255;255m╚═╝     ╚═╝ ╚═════╝╚═╝     \x1b[0m
`,
  TEXT: `
\x1b[38;2;255;182;255m╭─────────────╮\x1b[0m
\x1b[38;2;218;163;255m│ AGENT  MCP  │\x1b[0m
\x1b[38;2;144;255;255m╰─────────────╯\x1b[0m
`
};

// Intelligent banner selection based on terminal width
function getResponsiveBanner() {
  const terminalWidth = process.stdout.columns || 80;
  
  if (terminalWidth >= 80) {
    return BANNER_VARIANTS.FULL;
  } else if (terminalWidth >= 50) {
    return BANNER_VARIANTS.SPLIT;
  } else {
    return BANNER_VARIANTS.TEXT;
  }
}

async function startDev() {
  try {
    console.log(getResponsiveBanner());
    console.log('🚀 Starting Agent-MCP Dashboard...\n');
    
    // Check if our preferred port is available
    const portAvailable = await isPortAvailable(DASHBOARD_PORT);
    
    if (portAvailable) {
      console.log(`📡 Dashboard starting on port: ${DASHBOARD_PORT}`);
      console.log(`🌐 Dashboard URL: http://localhost:${DASHBOARD_PORT}\n`);
      console.log('💡 Tip: Bookmark this URL for easy access\n');
    } else {
      console.log(`⚠️  Port ${DASHBOARD_PORT} is in use, Next.js will find another port\n`);
    }
    
    // Start Next.js with the fixed port
    const args = ['dev', '--turbopack', '--port', DASHBOARD_PORT.toString(), '--hostname', '0.0.0.0'];
    
    const nextProcess = spawn('npx', ['next', ...args], {
      stdio: 'inherit',
      cwd: process.cwd(),
      env: process.env,
      shell: true
    });
    
    // Handle process termination
    process.on('SIGINT', () => {
      console.log('\n👋 Shutting down dashboard...');
      nextProcess.kill('SIGINT');
    });
    
    process.on('SIGTERM', () => {
      nextProcess.kill('SIGTERM');
    });
    
    // Exit with the same code as the Next.js process
    nextProcess.on('exit', (code) => {
      process.exit(code);
    });
    
  } catch (error) {
    console.error('❌ Error starting dashboard:', error);
    process.exit(1);
  }
}

// Run the script
startDev();