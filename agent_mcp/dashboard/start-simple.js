#!/usr/bin/env node

const { spawn } = require('child_process');
const path = require('path');

console.log('🚀 Starting Next.js Dashboard (Simple Mode)...\n');
console.log('📡 Dashboard will start on: http://localhost:3000\n');

// Set environment to skip problematic checks
process.env.SKIP_ENV_VALIDATION = 'true';
process.env.NODE_ENV = 'development';

// Start Next.js directly without Turbopack
const nextProcess = spawn('npx', ['next', 'dev', '--port', '3000'], {
  stdio: 'inherit',
  cwd: process.cwd(),
  env: {
    ...process.env,
    NODE_OPTIONS: '--max-old-space-size=4096'
  }
});

// Handle process termination
process.on('SIGINT', () => {
  console.log('\n👋 Shutting down dashboard...');
  nextProcess.kill('SIGINT');
  process.exit(0);
});

process.on('SIGTERM', () => {
  nextProcess.kill('SIGTERM');
  process.exit(0);
});

nextProcess.on('error', (error) => {
  console.error('❌ Failed to start:', error);
  process.exit(1);
});

nextProcess.on('exit', (code) => {
  if (code !== 0) {
    console.error(`❌ Next.js exited with code ${code}`);
  }
  process.exit(code);
});