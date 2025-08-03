#!/usr/bin/env node

/**
 * Comprehensive test for agent launching with full logging
 */

import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

async function logTmuxPane(sessionName, step) {
  try {
    const { stdout } = await execAsync(`tmux capture-pane -t "${sessionName}" -p`);
    console.log(`\n=== TMUX PANE CONTENT (${step}) ===`);
    console.log(stdout);
    console.log(`=== END TMUX PANE (${step}) ===\n`);
  } catch (error) {
    console.log(`❌ Failed to capture tmux pane for ${sessionName}: ${error.message}`);
  }
}

async function testSessionMonitoring(sessionName) {
  console.log(`\n👀 Monitoring session: ${sessionName}`);
  
  // Check current state
  await logTmuxPane(sessionName, 'CURRENT STATE');
  
  // Check every 2 seconds for 10 seconds to see if prompt appears
  for (let i = 1; i <= 5; i++) {
    await new Promise(resolve => setTimeout(resolve, 2000));
    await logTmuxPane(sessionName, `AFTER ${i * 2}s`);
  }
  
  // Test manual prompt delivery
  console.log('\n🎯 Testing manual prompt delivery...');
  const testPrompt = `This is your agent token: testtoken123 Ask the project RAG agent at least 5-7 questions to understand what you need to do. I want you to critically think when asking a question, then criticize yourself before asking that question. How you criticize yourself is by proposing an idea, criticizing it, and based on that criticism you pull through with that idea. It's better to add too much context versus too little. Add all these context entries to the agent mcp. ACT AUTO --worker --memory`;
  
  console.log('📝 Sending manual test prompt...');
  await execAsync(`tmux send-keys -t "${sessionName}" "${testPrompt}"`);
  console.log('⏱️ Waiting 0.5 seconds...');
  await new Promise(resolve => setTimeout(resolve, 500));
  await execAsync(`tmux send-keys -t "${sessionName}" Enter`);
  console.log('✅ Manual prompt sent');
  
  // Monitor response
  for (let i = 1; i <= 3; i++) {
    await new Promise(resolve => setTimeout(resolve, 3000));
    await logTmuxPane(sessionName, `MANUAL PROMPT +${i * 3}s`);
  }
}

async function testAgentLaunch() {
  console.log('🚀 Starting comprehensive agent launch test...');
  
  try {
    console.log('\n📋 Listing all tmux sessions...');
    const { stdout } = await execAsync('tmux list-sessions');
    console.log('Available sessions:');
    console.log(stdout);
    
    // Find any agent session
    const lines = stdout.split('\n').filter(line => line.trim());
    const agentSession = lines.find(line => line.includes('agent') && line.includes('148f'));
    
    if (agentSession) {
      const sessionName = agentSession.split(':')[0];
      console.log(`🎯 Found agent session: ${sessionName}`);
      await testSessionMonitoring(sessionName);
    } else {
      console.log('❌ No agent sessions found with pattern "agent" and "148f"');
      console.log('Available sessions:');
      lines.forEach(line => console.log(`  - ${line}`));
      
      // Try to find any session with 'agent' in the name
      const anyAgentSession = lines.find(line => line.toLowerCase().includes('agent'));
      if (anyAgentSession) {
        const sessionName = anyAgentSession.split(':')[0];
        console.log(`🔍 Found any agent session: ${sessionName}`);
        await testSessionMonitoring(sessionName);
      } else {
        console.log('❌ No agent sessions found at all');
      }
    }
    
    console.log('\n🎉 Test completed!');
    
  } catch (error) {
    console.error('❌ Test failed:', error);
  }
}

// Run the test
testAgentLaunch().catch(console.error);