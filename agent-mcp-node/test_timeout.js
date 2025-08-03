#!/usr/bin/env node

/**
 * Test setTimeout callback execution
 */

import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

console.log('🧪 Testing setTimeout callback execution...');

const testSessionName = 'auto-test-agent-148f';
const testPrompt = 'TEST PROMPT DELIVERY';

console.log(`📍 Starting setTimeout with 2 second delay...`);

setTimeout(async () => {
  console.log('🎯 INSIDE TIMEOUT CALLBACK!');
  
  try {
    console.log('📝 Step 1: Typing test message...');
    await execAsync(`tmux send-keys -t "${testSessionName}" "${testPrompt}"`);
    console.log('✅ Successfully typed message');
    
    console.log('⏱️ Step 2: Waiting 0.5 seconds...');
    await new Promise(resolve => setTimeout(resolve, 500));
    
    console.log('↩️ Step 3: Sending Enter...');
    await execAsync(`tmux send-keys -t "${testSessionName}" Enter`);
    console.log('✅ Successfully sent Enter');
    
  } catch (error) {
    console.error('❌ Error in timeout callback:', error);
  }
  
  console.log('🏁 Timeout callback completed');
}, 2000);

console.log('⏳ Waiting for timeout to execute...');

// Keep the process alive
setTimeout(() => {
  console.log('🔚 Test finished');
  process.exit(0);
}, 5000);