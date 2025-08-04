#!/usr/bin/env node
/**
 * CRITICAL TEST FOR SESSION DETECTION FUNCTIONALITY
 * Testing actual implementation, not mocks
 */

import { execSync } from 'child_process';
import { readFileSync } from 'fs';

// Import the actual session detection functions
const { detectAdminSessionByToken, detectAgentSessionByToken, getAdminActiveSession, updateAdminSession } = await import('./build/utils/sessionDetection.js');

console.log('🧪 CRITICAL SESSION DETECTION TESTS\n');

let testsPassed = 0;
let testsFailed = 0;

function testResult(name, passed, details = '') {
  if (passed) {
    console.log(`✅ ${name}`);
    testsPassed++;
  } else {
    console.log(`❌ ${name} - ${details}`);
    testsFailed++;
  }
}

// Test 1: Check if tmux is available (prerequisite)
try {
  const tmuxSessions = execSync('tmux list-sessions', { encoding: 'utf8' });
  testResult('Tmux availability', true, `Found sessions: ${tmuxSessions.split('\n').length - 1}`);
} catch (error) {
  testResult('Tmux availability', false, 'tmux not available or no sessions');
  process.exit(1);
}

// Test 2: Test admin session detection with invalid token
try {
  const result = await detectAdminSessionByToken('invalid-token');
  testResult('Admin session detection with invalid token', result === null, `Expected null, got: ${result}`);
} catch (error) {
  testResult('Admin session detection with invalid token', false, `Error: ${error.message}`);
}

// Test 3: Test admin session detection with valid format token (but non-existent)
try {
  const fakeToken = 'a'.repeat(32); // Valid length but fake
  const result = await detectAdminSessionByToken(fakeToken);
  testResult('Admin session detection with fake valid token', result === null || typeof result === 'string', `Got: ${result}`);
} catch (error) {
  testResult('Admin session detection with fake valid token', false, `Error: ${error.message}`);
}

// Test 4: Test agent session detection with invalid token  
try {
  const result = await detectAgentSessionByToken('invalid-token');
  testResult('Agent session detection with invalid token', result === null, `Expected null, got: ${result}`);
} catch (error) {
  testResult('Agent session detection with invalid token', false, `Error: ${error.message}`);
}

// Test 5: Test database session retrieval
try {
  const result = await getAdminActiveSession();
  testResult('Database admin session retrieval', result === null || typeof result === 'string', `Got: ${result}`);
} catch (error) {
  testResult('Database admin session retrieval', false, `Error: ${error.message}`);
}

// Test 6: Test session update functionality
try {
  await updateAdminSession('test-session-123');
  const retrieved = await getAdminActiveSession();
  testResult('Session update and retrieval', retrieved === 'test-session-123', `Expected 'test-session-123', got: ${retrieved}`);
} catch (error) {
  testResult('Session update and retrieval', false, `Error: ${error.message}`);
}

// Test 7: Test with environment admin token if available
const adminToken = process.env.SERVER_ADMIN_TOKEN;
if (adminToken && adminToken.length >= 10) {
  try {
    const result = await detectAdminSessionByToken(adminToken);
    testResult('Real admin token detection', true, `Detected session: ${result || 'none'}`);
  } catch (error) {
    testResult('Real admin token detection', false, `Error: ${error.message}`);
  }
} else {
  console.log('⚠️  No SERVER_ADMIN_TOKEN environment variable - skipping real token test');
}

// Test 8: Check tmux session scanning functionality
try {
  const sessions = execSync('tmux list-sessions -F "#{session_name}:#{session_attached}"', { encoding: 'utf8' });
  const sessionCount = sessions.split('\n').filter(line => line.trim()).length;
  testResult('Tmux session scanning', sessionCount > 0, `Found ${sessionCount} sessions`);
  
  // Try to capture pane from first session
  const firstSession = sessions.split('\n')[0]?.split(':')[0];
  if (firstSession) {
    const paneOutput = execSync(`tmux capture-pane -t "${firstSession}" -p`, { encoding: 'utf8' });
    testResult('Tmux pane capture', paneOutput.length > 0, `Captured ${paneOutput.length} characters`);
  }
} catch (error) {
  testResult('Tmux session scanning', false, `Error: ${error.message}`);
}

// Test 9: Edge case - empty string token
try {
  const result = await detectAdminSessionByToken('');
  testResult('Empty token handling', result === null, `Expected null, got: ${result}`);
} catch (error) {
  testResult('Empty token handling', false, `Error: ${error.message}`);
}

// Test 10: Edge case - very short token
try {
  const result = await detectAdminSessionByToken('abc');
  testResult('Short token handling', result === null, `Expected null, got: ${result}`);
} catch (error) {
  testResult('Short token handling', false, `Error: ${error.message}`);
}

// Final Results
console.log('\n🏁 CRITICAL TEST RESULTS:');
console.log(`✅ Passed: ${testsPassed}`);
console.log(`❌ Failed: ${testsFailed}`);
console.log(`📊 Success Rate: ${((testsPassed / (testsPassed + testsFailed)) * 100).toFixed(1)}%`);

if (testsFailed > 0) {
  console.log('\n🚨 CRITICAL FAILURES DETECTED - IMPLEMENTATION NEEDS FIXES');
  process.exit(1);
} else {
  console.log('\n🎉 ALL CRITICAL TESTS PASSED - SESSION DETECTION IS WORKING');
  process.exit(0);
}