#!/usr/bin/env node

/**
 * CRITICAL TEST: Parent Task Creation Functionality
 * Tests the actual implementation of task creation with parent task specified
 */

import { spawn } from 'child_process';
import fs from 'fs';
import path from 'path';

// Test configuration
const TEST_TOKEN = '73c4347d534113bf6385e92668b3ed26';
const SERVER_PORT = 3333;
const SERVER_URL = `http://localhost:${SERVER_PORT}`;

class ParentTaskCreationTester {
  constructor() {
    this.testResults = [];
    this.serverProcess = null;
  }

  log(message, type = 'INFO') {
    const timestamp = new Date().toISOString();
    const logMessage = `[${timestamp}] [${type}] ${message}`;
    console.log(logMessage);
    this.testResults.push({ timestamp, type, message });
  }

  async startServer() {
    return new Promise((resolve, reject) => {
      this.log('Starting Agent-MCP server...');
      
      this.serverProcess = spawn('npm', ['start'], {
        cwd: '/home/alejandro/VPS/Agent-MCP/agent-mcp-node',
        stdio: ['pipe', 'pipe', 'pipe']
      });

      let serverOutput = '';
      
      this.serverProcess.stdout.on('data', (data) => {
        serverOutput += data.toString();
        if (serverOutput.includes('Server listening on')) {
          this.log('Server started successfully');
          setTimeout(resolve, 2000); // Give server time to fully initialize
        }
      });

      this.serverProcess.stderr.on('data', (data) => {
        const error = data.toString();
        if (error.includes('EADDRINUSE')) {
          this.log('Server already running, continuing with tests');
          resolve();
        } else {
          this.log(`Server stderr: ${error}`, 'WARN');
        }
      });

      setTimeout(() => {
        reject(new Error('Server failed to start within timeout'));
      }, 30000);
    });
  }

  async makeRequest(endpoint, method = 'POST', body = null) {
    const fetch = (await import('node-fetch')).default;
    
    const options = {
      method,
      headers: {
        'Content-Type': 'application/json',
      }
    };

    if (body) {
      options.body = JSON.stringify(body);
    }

    try {
      const response = await fetch(`${SERVER_URL}${endpoint}`, options);
      const result = await response.json();
      return { status: response.status, data: result };
    } catch (error) {
      this.log(`Request failed: ${error.message}`, 'ERROR');
      return { status: 500, error: error.message };
    }
  }

  async testCreateParentTask() {
    this.log('=== TEST 1: Create Parent Task ===');
    
    const parentTaskData = {
      method: "create_self_task",
      params: {
        token: TEST_TOKEN,
        task_title: "CRITICAL_TEST_Parent_Task",
        task_description: "This is a parent task created for testing parent-child task relationships"
      }
    };

    const result = await this.makeRequest('/mcp', 'POST', parentTaskData);
    
    if (result.status === 200 && result.data.result) {
      this.log('✅ Parent task created successfully');
      // Extract task ID from the response
      const taskIdMatch = result.data.result.text.match(/Task ID: ([a-z0-9_]+)/);
      if (taskIdMatch) {
        this.parentTaskId = taskIdMatch[1];
        this.log(`Parent Task ID: ${this.parentTaskId}`);
        return true;
      } else {
        this.log('❌ Could not extract parent task ID from response', 'ERROR');
        return false;
      }
    } else {
      this.log(`❌ Failed to create parent task: ${JSON.stringify(result)}`, 'ERROR');
      return false;
    }
  }

  async testCreateChildTask() {
    this.log('=== TEST 2: Create Child Task with Parent ===');
    
    if (!this.parentTaskId) {
      this.log('❌ No parent task ID available for child task creation', 'ERROR');
      return false;
    }

    const childTaskData = {
      method: "create_self_task",
      params: {
        token: TEST_TOKEN,
        task_title: "CRITICAL_TEST_Child_Task",
        task_description: "This is a child task that should be linked to the parent task",
        parent_task_id: this.parentTaskId
      }
    };

    const result = await this.makeRequest('/mcp', 'POST', childTaskData);
    
    if (result.status === 200 && result.data.result) {
      this.log('✅ Child task created successfully');
      // Extract child task ID
      const taskIdMatch = result.data.result.text.match(/Task ID: ([a-z0-9_]+)/);
      if (taskIdMatch) {
        this.childTaskId = taskIdMatch[1];
        this.log(`Child Task ID: ${this.childTaskId}`);
        
        // Verify parent relationship is mentioned in response
        if (result.data.result.text.includes(`Parent Task: ${this.parentTaskId}`)) {
          this.log('✅ Parent relationship correctly established in response');
          return true;
        } else {
          this.log('❌ Parent relationship not mentioned in response', 'ERROR');
          return false;
        }
      } else {
        this.log('❌ Could not extract child task ID from response', 'ERROR');
        return false;
      }
    } else {
      this.log(`❌ Failed to create child task: ${JSON.stringify(result)}`, 'ERROR');
      return false;
    }
  }

  async testViewTasksWithParentFilter() {
    this.log('=== TEST 3: View Tasks with Parent Filter ===');
    
    if (!this.parentTaskId) {
      this.log('❌ No parent task ID available for filtering test', 'ERROR');
      return false;
    }

    const viewTasksData = {
      method: "view_tasks",
      params: {
        token: TEST_TOKEN,
        filter_parent_task: this.parentTaskId,
        display_mode: "detailed"
      }
    };

    const result = await this.makeRequest('/mcp', 'POST', viewTasksData);
    
    if (result.status === 200 && result.data.result) {
      this.log('✅ Successfully filtered tasks by parent');
      
      // Check if the child task appears in the filtered results
      if (this.childTaskId && result.data.result.text.includes(this.childTaskId)) {
        this.log('✅ Child task appears in parent filter results');
        return true;
      } else {
        this.log('❌ Child task does not appear in parent filter results', 'ERROR');
        return false;
      }
    } else {
      this.log(`❌ Failed to filter tasks by parent: ${JSON.stringify(result)}`, 'ERROR');
      return false;
    }
  }

  async testDatabaseIntegrity() {
    this.log('=== TEST 4: Database Integrity Check ===');
    
    // This would require direct database access, which we'll simulate by checking
    // if the view_tasks with detailed mode shows proper parent-child relationships
    
    const viewAllTasksData = {
      method: "view_tasks",
      params: {
        token: TEST_TOKEN,
        display_mode: "with_dependencies",
        include_completed: true,
        limit: 100
      }
    };

    const result = await this.makeRequest('/mcp', 'POST', viewAllTasksData);
    
    if (result.status === 200 && result.data.result) {
      this.log('✅ Successfully retrieved tasks with dependencies');
      
      // Check if both parent and child tasks exist and their relationship is visible
      const responseText = result.data.result.text;
      const hasParentTask = this.parentTaskId && responseText.includes(this.parentTaskId);
      const hasChildTask = this.childTaskId && responseText.includes(this.childTaskId);
      
      if (hasParentTask && hasChildTask) {
        this.log('✅ Both parent and child tasks exist in database');
        return true;
      } else {
        this.log(`❌ Missing tasks in database - Parent: ${hasParentTask}, Child: ${hasChildTask}`, 'ERROR');
        return false;
      }
    } else {
      this.log(`❌ Failed to check database integrity: ${JSON.stringify(result)}`, 'ERROR');
      return false;
    }
  }

  async testInvalidParentTask() {
    this.log('=== TEST 5: Invalid Parent Task Handling ===');
    
    const invalidParentTaskData = {
      method: "create_self_task",
      params: {
        token: TEST_TOKEN,
        task_title: "CRITICAL_TEST_Invalid_Parent",
        task_description: "This task tries to use an invalid parent task ID",
        parent_task_id: "invalid_task_id_12345"
      }
    };

    const result = await this.makeRequest('/mcp', 'POST', invalidParentTaskData);
    
    // Should fail gracefully or warn about invalid parent
    if (result.status !== 200 || (result.data.result && result.data.result.text.includes('error'))) {
      this.log('✅ System properly handles invalid parent task ID');
      return true;
    } else {
      this.log('❌ System did not properly validate parent task ID', 'ERROR');
      return false;
    }
  }

  async cleanup() {
    this.log('=== CLEANUP: Removing Test Tasks ===');
    
    // Try to delete test tasks (may not be available depending on implementation)
    const tasksToDelete = [this.childTaskId, this.parentTaskId].filter(id => id);
    
    for (const taskId of tasksToDelete) {
      try {
        // Note: This assumes delete functionality exists
        const deleteData = {
          method: "delete_task",
          params: {
            token: TEST_TOKEN,
            task_id: taskId,
            confirmation_phrase: "DELETE TASKS",
            reason: "Cleanup after critical testing"
          }
        };
        
        await this.makeRequest('/mcp', 'POST', deleteData);
        this.log(`Attempted to delete task: ${taskId}`);
      } catch (error) {
        this.log(`Could not delete task ${taskId}: ${error.message}`, 'WARN');
      }
    }
  }

  async runAllTests() {
    try {
      await this.startServer();
      
      const tests = [
        () => this.testCreateParentTask(),
        () => this.testCreateChildTask(),
        () => this.testViewTasksWithParentFilter(),
        () => this.testDatabaseIntegrity(),
        () => this.testInvalidParentTask()
      ];

      let passedTests = 0;
      let totalTests = tests.length;

      for (const test of tests) {
        try {
          const passed = await test();
          if (passed) passedTests++;
        } catch (error) {
          this.log(`Test failed with exception: ${error.message}`, 'ERROR');
        }
      }

      await this.cleanup();

      this.log('=== FINAL RESULTS ===');
      this.log(`Tests Passed: ${passedTests}/${totalTests}`);
      
      if (passedTests === totalTests) {
        this.log('🎉 ALL TESTS PASSED - Parent task functionality is working correctly!');
        return true;
      } else {
        this.log(`❌ ${totalTests - passedTests} TESTS FAILED - Parent task functionality has issues!`, 'ERROR');
        return false;
      }

    } catch (error) {
      this.log(`Critical test failure: ${error.message}`, 'ERROR');
      return false;
    } finally {
      if (this.serverProcess) {
        this.serverProcess.kill();
      }
    }
  }
}

// Run the tests
const tester = new ParentTaskCreationTester();
tester.runAllTests().then(success => {
  process.exit(success ? 0 : 1);
}).catch(error => {
  console.error('Test runner failed:', error);
  process.exit(1);
});

export default ParentTaskCreationTester;