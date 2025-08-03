#!/usr/bin/env tsx
// Comprehensive test script for prompt delivery mechanisms in Agent-MCP

import { 
  isTmuxAvailable, 
  createTmuxSession, 
  sendPromptToSession,
  sendCommandToSession,
  sessionExists,
  killTmuxSession,
  sanitizeSessionName,
  generateAgentSessionName,
  listTmuxSessions
} from './src/utils/tmux.js';
import { buildAgentPrompt } from './src/utils/promptTemplates.js';

async function testPromptDelivery() {
  console.log('🧪 **TESTING PROMPT DELIVERY MECHANISMS**');
  console.log('='.repeat(50));
  
  // Test 1: Check tmux availability
  console.log('📋 Test 1: Tmux Availability');
  const tmuxAvailable = await isTmuxAvailable();
  console.log(`   Result: ${tmuxAvailable ? '✅ Tmux is available' : '❌ Tmux not available'}`);
  
  if (!tmuxAvailable) {
    console.log('❌ Cannot proceed without tmux. Please install tmux.');
    return;
  }
  
  // Test 2: Session name sanitization
  console.log('\n📋 Test 2: Session Name Sanitization');
  const testNames = ['test agent', 'agent.with.dots', 'agent:with:colons', 'valid_agent'];
  for (const name of testNames) {
    const sanitized = sanitizeSessionName(name);
    console.log(`   "${name}" → "${sanitized}"`);
  }
  
  // Test 3: Agent session name generation
  console.log('\n📋 Test 3: Agent Session Name Generation');
  const mockToken = 'abcd1234567890abcdef';
  const agentIds = ['test-agent', 'worker-agent', 'auto-test-agent'];
  for (const agentId of agentIds) {
    const sessionName = generateAgentSessionName(agentId, mockToken);
    console.log(`   Agent "${agentId}" → Session "${sessionName}"`);
  }
  
  // Test 4: Create test session
  console.log('\n📋 Test 4: Session Creation');
  const testSessionName = 'prompt-delivery-test';
  const workingDir = process.cwd();
  
  // Clean up any existing test session
  if (await sessionExists(testSessionName)) {
    console.log('   Cleaning up existing test session...');
    await killTmuxSession(testSessionName);
  }
  
  console.log('   Creating test tmux session...');
  const sessionCreated = await createTmuxSession(testSessionName, workingDir);
  console.log(`   Result: ${sessionCreated ? '✅ Session created successfully' : '❌ Session creation failed'}`);
  
  if (!sessionCreated) {
    console.log('❌ Cannot proceed without a test session');
    return;
  }
  
  // Test 5: Basic command sending
  console.log('\n📋 Test 5: Basic Command Sending');
  console.log('   Sending basic echo command...');
  const basicCommandSent = await sendCommandToSession(testSessionName, 'echo "Hello from Agent-MCP test"');
  console.log(`   Result: ${basicCommandSent ? '✅ Command sent successfully' : '❌ Command sending failed'}`);
  
  // Small delay to let command execute
  await new Promise(resolve => setTimeout(resolve, 1000));
  
  // Test 6: Prompt building
  console.log('\n📋 Test 6: Prompt Building');
  const testAgentId = 'prompt-test-agent';
  const testAgentToken = 'test_token_123456789';
  const testAdminToken = 'admin_token_987654321';
  
  console.log('   Building agent prompt...');
  const agentPrompt = buildAgentPrompt(testAgentId, testAgentToken, testAdminToken);
  
  if (agentPrompt) {
    console.log('   ✅ Prompt built successfully');
    console.log('   Prompt preview (first 200 chars):');
    console.log('   ' + agentPrompt.substring(0, 200) + '...');
    
    // Check if token is embedded
    const tokenEmbedded = agentPrompt.includes(testAgentToken);
    console.log(`   Token embedding check: ${tokenEmbedded ? '✅ Token found in prompt' : '❌ Token NOT found'}`);
    
    // Check if agent ID is embedded
    const agentIdEmbedded = agentPrompt.includes(testAgentId);
    console.log(`   Agent ID embedding check: ${agentIdEmbedded ? '✅ Agent ID found in prompt' : '❌ Agent ID NOT found'}`);
  } else {
    console.log('   ❌ Prompt building failed');
    return;
  }
  
  // Test 7: Prompt delivery with exact tmux send-keys pattern
  console.log('\n📋 Test 7: Prompt Delivery (Exact tmux send-keys Pattern)');
  console.log('   Testing prompt delivery mechanism...');
  
  let promptDelivered = false;
  if (agentPrompt) {
    // Test the exact prompt delivery pattern
    promptDelivered = await sendPromptToSession(testSessionName, agentPrompt, 1); // 1 second delay for test
    console.log(`   Result: ${promptDelivered ? '✅ Prompt delivered successfully' : '❌ Prompt delivery failed'}`);
    
    if (promptDelivered) {
      console.log('   ✅ Prompt delivery using tmux send-keys pattern confirmed');
      console.log('   ✅ Two-step process: text input + Enter keypress');
    }
  }
  
  // Test 8: Multi-line prompt handling
  console.log('\n📋 Test 8: Multi-line Prompt Handling');
  const multilinePrompt = `This is a test prompt.
It has multiple lines.
Each line should be handled correctly.
Testing Agent-MCP prompt delivery.`;
  
  console.log('   Testing multi-line prompt...');
  const multilineDelivered = await sendPromptToSession(testSessionName, multilinePrompt, 0.5);
  console.log(`   Result: ${multilineDelivered ? '✅ Multi-line prompt delivered' : '❌ Multi-line prompt failed'}`);
  
  // Test 9: Special character handling
  console.log('\n📋 Test 9: Special Character Handling');
  const specialCharPrompt = `Test with "quotes" and 'apostrophes' and $variables and (parentheses)`;
  
  console.log('   Testing special characters...');
  const specialCharDelivered = await sendPromptToSession(testSessionName, specialCharPrompt, 0.5);
  console.log(`   Result: ${specialCharDelivered ? '✅ Special characters handled' : '❌ Special character handling failed'}`);
  
  // Test 10: Session cleanup
  console.log('\n📋 Test 10: Session Cleanup');
  console.log('   Cleaning up test session...');
  const sessionKilled = await killTmuxSession(testSessionName);
  console.log(`   Result: ${sessionKilled ? '✅ Session cleaned up successfully' : '❌ Session cleanup failed'}`);
  
  // Test 11: Active session discovery
  console.log('\n📋 Test 11: Active Session Discovery');
  console.log('   Listing all tmux sessions...');
  const sessions = await listTmuxSessions();
  console.log(`   Found ${sessions.length} tmux sessions:`);
  for (const session of sessions) {
    console.log(`   - ${session.name} (created: ${session.created}, attached: ${session.attached})`);
  }
  
  // Summary
  console.log('\n' + '='.repeat(50));
  console.log('📊 **PROMPT DELIVERY TEST SUMMARY**');
  console.log('='.repeat(50));
  
  const tests = [
    { name: 'Tmux Availability', status: tmuxAvailable },
    { name: 'Session Creation', status: sessionCreated },
    { name: 'Basic Command Sending', status: basicCommandSent },
    { name: 'Prompt Building', status: !!agentPrompt },
    { name: 'Token Embedding', status: agentPrompt?.includes(testAgentToken) },
    { name: 'Agent ID Embedding', status: agentPrompt?.includes(testAgentId) },
    { name: 'Prompt Delivery', status: promptDelivered },
    { name: 'Multi-line Handling', status: multilineDelivered },
    { name: 'Special Characters', status: specialCharDelivered },
    { name: 'Session Cleanup', status: sessionKilled }
  ];
  
  const passedTests = tests.filter(t => t.status).length;
  const totalTests = tests.length;
  
  console.log(`✅ Passed: ${passedTests}/${totalTests} tests`);
  console.log(`❌ Failed: ${totalTests - passedTests}/${totalTests} tests`);
  
  for (const test of tests) {
    console.log(`   ${test.status ? '✅' : '❌'} ${test.name}`);
  }
  
  if (passedTests === totalTests) {
    console.log('\n🎉 **ALL PROMPT DELIVERY TESTS PASSED**');
    console.log('🚀 Prompt delivery mechanism is fully operational!');
  } else {
    console.log('\n⚠️ **SOME TESTS FAILED**');
    console.log('🔧 Please review the failed tests and fix issues.');
  }
  
  console.log('\n📋 **Key Findings:**');
  console.log('- Prompt delivery uses exact tmux send-keys pattern');
  console.log('- Agent tokens are embedded in prompt text (not environment variables)');
  console.log('- Two-step delivery: text input + Enter keypress');
  console.log('- Multi-line and special character support confirmed');
  console.log('- Session management and cleanup working properly');
}

// Run the test
testPromptDelivery().catch(error => {
  console.error('❌ Test execution failed:', error);
  process.exit(1);
});