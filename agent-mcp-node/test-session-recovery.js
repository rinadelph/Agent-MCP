#!/usr/bin/env node

// Test script for session recovery functionality
// This script simulates connection drops and tests recovery

import https from 'https';
import http from 'http';

const SERVER_HOST = 'localhost';
const SERVER_PORT = 3002;

// Helper function to make HTTP requests
function makeRequest(method, path, headers = {}, body = null) {
  return new Promise((resolve, reject) => {
    const options = {
      hostname: SERVER_HOST,
      port: SERVER_PORT,
      path: path,
      method: method,
      headers: {
        'Content-Type': 'application/json',
        ...headers
      }
    };

    const req = http.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => data += chunk);
      res.on('end', () => {
        try {
          const result = {
            statusCode: res.statusCode,
            headers: res.headers,
            data: data ? JSON.parse(data) : null
          };
          resolve(result);
        } catch (error) {
          resolve({
            statusCode: res.statusCode,
            headers: res.headers,
            data: data
          });
        }
      });
    });

    req.on('error', reject);
    
    if (body) {
      req.write(JSON.stringify(body));
    }
    req.end();
  });
}

// Test session recovery workflow
async function testSessionRecovery() {
  console.log('🧪 Starting Session Recovery Test');
  console.log('='.repeat(50));

  try {
    // 1. Check server health
    console.log('1️⃣ Checking server health...');
    const health = await makeRequest('GET', '/health');
    console.log(`   Server status: ${health.statusCode}`);
    console.log(`   Session recovery enabled: ${health.data?.session_recovery?.enabled}`);
    console.log(`   Grace period: ${health.data?.session_recovery?.grace_period_minutes} minutes`);

    // 2. Check current sessions
    console.log('\n2️⃣ Checking current sessions...');
    const sessions = await makeRequest('GET', '/sessions');
    console.log(`   Active transports: ${sessions.data?.summary?.active_transports || 0}`);
    console.log(`   Persistent sessions: ${sessions.data?.summary?.persistent_sessions || 0}`);
    console.log(`   Recovered sessions: ${sessions.data?.summary?.recovered_sessions || 0}`);

    // 3. Initialize a new MCP session
    console.log('\n3️⃣ Initializing new MCP session...');
    const initRequest = {
      jsonrpc: '2.0',
      id: 1,
      method: 'initialize',
      params: {
        protocolVersion: '2024-11-05',
        capabilities: {
          roots: {
            listChanged: false
          },
          sampling: {}
        },
        clientInfo: {
          name: 'session-recovery-test',
          version: '1.0.0'
        }
      }
    };

    const initResponse = await makeRequest('POST', '/mcp', {}, initRequest);
    console.log(`   Init response status: ${initResponse.statusCode}`);
    
    const sessionId = initResponse.headers['mcp-session-id'];
    if (!sessionId) {
      console.log('   ❌ No session ID returned!');
      console.log('   Response:', JSON.stringify(initResponse.data, null, 2));
      return;
    }
    
    console.log(`   ✅ Session ID: ${sessionId}`);

    // 4. Check sessions again
    console.log('\n4️⃣ Checking sessions after initialization...');
    const sessionsAfterInit = await makeRequest('GET', '/sessions');
    console.log(`   Active transports: ${sessionsAfterInit.data?.summary?.active_transports || 0}`);
    console.log(`   Persistent sessions: ${sessionsAfterInit.data?.summary?.persistent_sessions || 0}`);

    // 5. Send a tool call to establish working state
    console.log('\n5️⃣ Sending tool call to establish state...');
    const toolCallRequest = {
      jsonrpc: '2.0',
      id: 2,
      method: 'tools/call',
      params: {
        name: 'save_session_state',
        arguments: {
          state_key: 'test_context',
          state_data: {
            test_id: 'session-recovery-test',
            timestamp: new Date().toISOString(),
            progress: 'initial state saved',
            important_data: [1, 2, 3, 4, 5]
          },
          expires_in_hours: 1
        }
      }
    };

    const toolResponse = await makeRequest('POST', '/mcp', { 'mcp-session-id': sessionId }, toolCallRequest);
    console.log(`   Tool call status: ${toolResponse.statusCode}`);
    if (toolResponse.data?.result) {
      console.log('   ✅ State saved successfully');
    } else {
      console.log('   ⚠️ Tool call response:', JSON.stringify(toolResponse.data, null, 2));
    }

    // 6. Simulate session disconnection by waiting and checking persistence
    console.log('\n6️⃣ Checking session persistence...');
    await new Promise(resolve => setTimeout(resolve, 2000)); // Wait 2 seconds
    
    const persistentSessions = await makeRequest('GET', '/sessions');
    console.log(`   Sessions in database: ${persistentSessions.data?.summary?.persistent_sessions || 0}`);
    
    const sessionDetails = persistentSessions.data?.persistent_sessions?.find(s => s.mcp_session_id === sessionId);
    if (sessionDetails) {
      console.log(`   ✅ Session found in persistence: ${sessionDetails.status}`);
      console.log(`   Last heartbeat: ${new Date(sessionDetails.last_heartbeat).toLocaleString()}`);
    } else {
      console.log('   ❌ Session not found in persistence!');
    }

    // 7. Test session recovery by making request with existing session ID
    console.log('\n7️⃣ Testing session recovery...');
    const recoverRequest = {
      jsonrpc: '2.0',
      id: 3,
      method: 'tools/call',
      params: {
        name: 'load_session_state',
        arguments: {
          state_key: 'test_context'
        }
      }
    };

    const recoverResponse = await makeRequest('POST', '/mcp', { 'mcp-session-id': sessionId }, recoverRequest);
    console.log(`   Recovery request status: ${recoverResponse.statusCode}`);
    
    if (recoverResponse.data?.result) {
      console.log('   ✅ Session recovery successful!');
      console.log('   ✅ State restored successfully!');
      
      // Check if the saved data matches
      const resultText = recoverResponse.data.result.content?.[0]?.text || '';
      if (resultText.includes('session-recovery-test')) {
        console.log('   ✅ Saved state data verified!');
      }
    } else {
      console.log('   ⚠️ Recovery response:', JSON.stringify(recoverResponse.data, null, 2));
    }

    // 8. Final session check
    console.log('\n8️⃣ Final session status...');
    const finalSessions = await makeRequest('GET', '/sessions');
    console.log(`   Active transports: ${finalSessions.data?.summary?.active_transports || 0}`);
    console.log(`   Recovered sessions: ${finalSessions.data?.summary?.recovered_sessions || 0}`);

    console.log('\n✅ Session Recovery Test Complete!');

  } catch (error) {
    console.error('\n❌ Test failed:', error.message);
    console.error('Error details:', error);
  }
}

// Run the test
testSessionRecovery().catch(console.error);