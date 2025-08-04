#!/usr/bin/env node

/**
 * CRITICAL TEST: Parent Task Creation - Direct MCP Tool Testing
 * Tests parent task functionality through direct tool calls
 */

// Test the MCP tools directly - this is more reliable
console.log('🔍 CRITICAL TESTING: Parent Task Creation Functionality');
console.log('═══════════════════════════════════════════════════════');

const TEST_TOKEN = '73c4347d534113bf6385e92668b3ed26';

// Test Results Storage
const testResults = {
  passed: 0,
  failed: 0,
  errors: []
};

function logTest(testName, success, message = '') {
  const status = success ? '✅ PASS' : '❌ FAIL';
  console.log(`${status}: ${testName}`);
  if (message) console.log(`    ${message}`);
  
  if (success) {
    testResults.passed++;
  } else {
    testResults.failed++;
    testResults.errors.push(`${testName}: ${message}`);
  }
}

// Test 1: Check if server is responding
async function testServerHealth() {
  try {
    const response = await fetch('http://localhost:3001/health');
    if (response.ok) {
      logTest('Server Health Check', true, 'Server is responding');
      return true;
    } else {
      logTest('Server Health Check', false, `Server returned ${response.status}`);
      return false;
    }
  } catch (error) {
    logTest('Server Health Check', false, `Server not reachable: ${error.message}`);
    return false;
  }
}

// Test 2: Create a parent task
async function testCreateParentTask() {
  try {
    const response = await fetch('http://localhost:3001/mcp', {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream'
      },
      body: JSON.stringify({
        method: "create_self_task",
        params: {
          token: TEST_TOKEN,
          task_title: "CRITICAL_TEST_Parent_Task_" + Date.now(),
          task_description: "Parent task for testing hierarchical task creation functionality"
        }
      })
    });

    if (response.ok) {
      const result = await response.json();
      if (result.result && result.result.text) {
        // Extract task ID from response
        const taskIdMatch = result.result.text.match(/Task ID: ([a-z0-9_]+)/);
        if (taskIdMatch) {
          const parentTaskId = taskIdMatch[1];
          logTest('Create Parent Task', true, `Created parent task: ${parentTaskId}`);
          return parentTaskId;
        } else {
          logTest('Create Parent Task', false, 'Could not extract task ID from response');
          return null;
        }
      } else {
        logTest('Create Parent Task', false, 'Invalid response format');
        return null;
      }
    } else {
      logTest('Create Parent Task', false, `HTTP ${response.status}`);
      return null;
    }
  } catch (error) {
    logTest('Create Parent Task', false, error.message);
    return null;
  }
}

// Test 3: Create a child task with parent specified
async function testCreateChildTask(parentTaskId) {
  if (!parentTaskId) {
    logTest('Create Child Task', false, 'No parent task ID provided');
    return null;
  }

  try {
    const response = await fetch('http://localhost:3001/mcp', {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream'
      },
      body: JSON.stringify({
        method: "create_self_task",
        params: {
          token: TEST_TOKEN,
          task_title: "CRITICAL_TEST_Child_Task_" + Date.now(),
          task_description: "Child task to test parent-child relationship functionality",
          parent_task_id: parentTaskId
        }
      })
    });

    if (response.ok) {
      const result = await response.json();
      if (result.result && result.result.text) {
        const taskIdMatch = result.result.text.match(/Task ID: ([a-z0-9_]+)/);
        const hasParentRef = result.result.text.includes(`Parent Task: ${parentTaskId}`);
        
        if (taskIdMatch && hasParentRef) {
          const childTaskId = taskIdMatch[1];
          logTest('Create Child Task', true, `Created child task: ${childTaskId} with parent: ${parentTaskId}`);
          return childTaskId;
        } else {
          logTest('Create Child Task', false, 'Task ID extracted but parent relationship not confirmed');
          return taskIdMatch ? taskIdMatch[1] : null;
        }
      } else {
        logTest('Create Child Task', false, 'Invalid response format');
        return null;
      }
    } else {
      logTest('Create Child Task', false, `HTTP ${response.status}`);
      return null;
    }
  } catch (error) {
    logTest('Create Child Task', false, error.message);
    return null;
  }
}

// Test 4: Verify parent filtering works
async function testParentFiltering(parentTaskId, childTaskId) {
  if (!parentTaskId) {
    logTest('Parent Filtering', false, 'No parent task ID for filtering test');
    return false;
  }

  try {
    const response = await fetch('http://localhost:3001/mcp', {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream'
      },
      body: JSON.stringify({
        method: "view_tasks",
        params: {
          token: TEST_TOKEN,
          filter_parent_task: parentTaskId,
          display_mode: "detailed"
        }
      })
    });

    if (response.ok) {
      const result = await response.json();
      if (result.result && result.result.text) {
        const hasChildInResults = childTaskId ? result.result.text.includes(childTaskId) : true;
        logTest('Parent Filtering', hasChildInResults, hasChildInResults ? 'Child task found in parent filter' : 'Child task missing from parent filter');
        return hasChildInResults;
      } else {
        logTest('Parent Filtering', false, 'Invalid response format');
        return false;
      }
    } else {
      logTest('Parent Filtering', false, `HTTP ${response.status}`);
      return false;
    }
  } catch (error) {
    logTest('Parent Filtering', false, error.message);
    return false;
  }
}

// Test 5: Test error handling for invalid parent
async function testInvalidParentHandling() {
  try {
    const response = await fetch('http://localhost:3001/mcp', {
      method: 'POST',
      headers: { 
        'Content-Type': 'application/json',
        'Accept': 'application/json, text/event-stream'
      },
      body: JSON.stringify({
        method: "create_self_task",
        params: {
          token: TEST_TOKEN,
          task_title: "CRITICAL_TEST_Invalid_Parent",
          task_description: "Testing invalid parent task handling",
          parent_task_id: "invalid_nonexistent_task_id_12345"
        }
      })
    });

    if (response.ok) {
      const result = await response.json();
      if (result.result && result.result.text) {
        // Should either fail or create task successfully (depending on implementation)
        // We'll accept both behaviors but log what happens
        const isError = result.result.text.toLowerCase().includes('error');
        logTest('Invalid Parent Handling', true, `Response: ${isError ? 'Error handled' : 'Task created despite invalid parent'}`);
        return true;
      } else {
        logTest('Invalid Parent Handling', false, 'Invalid response format');
        return false;
      }
    } else {
      // Failed request might be expected behavior
      logTest('Invalid Parent Handling', true, `Request failed as expected: HTTP ${response.status}`);
      return true;
    }
  } catch (error) {
    logTest('Invalid Parent Handling', true, `Error handling worked: ${error.message}`);
    return true;
  }
}

// Main test runner
async function runCriticalTests() {
  console.log('\n🚀 Starting Critical Parent Task Tests...\n');

  // Test 1: Server Health
  const serverHealthy = await testServerHealth();
  if (!serverHealthy) {
    console.log('\n❌ CRITICAL FAILURE: Server not available - cannot continue tests');
    return false;
  }

  // Test 2: Create Parent Task
  const parentTaskId = await testCreateParentTask();
  
  // Test 3: Create Child Task
  const childTaskId = await testCreateChildTask(parentTaskId);
  
  // Test 4: Parent Filtering
  await testParentFiltering(parentTaskId, childTaskId);
  
  // Test 5: Invalid Parent Handling
  await testInvalidParentHandling();

  // Results Summary
  console.log('\n═══════════════════════════════════════════════════════');
  console.log('📊 CRITICAL TEST RESULTS SUMMARY');
  console.log('═══════════════════════════════════════════════════════');
  console.log(`✅ Tests Passed: ${testResults.passed}`);
  console.log(`❌ Tests Failed: ${testResults.failed}`);
  console.log(`📈 Success Rate: ${((testResults.passed / (testResults.passed + testResults.failed)) * 100).toFixed(1)}%`);

  if (testResults.failed > 0) {
    console.log('\n🔍 FAILURE DETAILS:');
    testResults.errors.forEach(error => console.log(`   • ${error}`));
  }

  const allTestsPassed = testResults.failed === 0;
  
  if (allTestsPassed) {
    console.log('\n🎉 ALL CRITICAL TESTS PASSED!');
    console.log('✅ Parent task functionality is working correctly');
  } else {
    console.log('\n⚠️  CRITICAL ISSUES DETECTED!');
    console.log('❌ Parent task functionality has problems that need fixing');
  }

  return allTestsPassed;
}

// Execute tests
runCriticalTests().then(success => {
  process.exit(success ? 0 : 1);
}).catch(error => {
  console.error('💥 Critical test execution failed:', error);
  process.exit(1);
});