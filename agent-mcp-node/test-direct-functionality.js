#!/usr/bin/env node

/**
 * CRITICAL TEST: Direct Database Testing of Parent Task Functionality
 * Tests the actual database and core functions directly
 */

import Database from 'better-sqlite3';
import path from 'path';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Database path
const DB_PATH = path.join(__dirname, '.agent', 'mcp_state.db');

console.log('🔍 CRITICAL DIRECT DATABASE TESTING: Parent Task Functionality');
console.log('═══════════════════════════════════════════════════════════════');

class DirectDatabaseTester {
  constructor() {
    this.testResults = { passed: 0, failed: 0, errors: [] };
    this.db = null;
  }

  logTest(testName, success, message = '') {
    const status = success ? '✅ PASS' : '❌ FAIL';
    console.log(`${status}: ${testName}`);
    if (message) console.log(`    ${message}`);
    
    if (success) {
      this.testResults.passed++;
    } else {
      this.testResults.failed++;
      this.testResults.errors.push(`${testName}: ${message}`);
    }
  }

  async initDatabase() {
    try {
      this.db = new Database(DB_PATH);
      this.logTest('Database Connection', true, 'Connected to MCP database');
      return true;
    } catch (error) {
      this.logTest('Database Connection', false, `Failed to connect: ${error.message}`);
      return false;
    }
  }

  async testDatabaseSchema() {
    try {
      // Check if tasks table has parent_task column
      const schema = this.db.prepare(`
        SELECT sql FROM sqlite_master 
        WHERE type='table' AND name='tasks'
      `).get();

      if (schema && schema.sql.includes('parent_task')) {
        this.logTest('Database Schema', true, 'Tasks table has parent_task column');
        return true;
      } else {
        this.logTest('Database Schema', false, 'Tasks table missing parent_task column');
        return false;
      }
    } catch (error) {
      this.logTest('Database Schema', false, error.message);
      return false;
    }
  }

  async testTaskCreationWithParent() {
    try {
      const timestamp = new Date().toISOString();
      const parentTaskId = `critical_test_parent_${Date.now()}`;
      const childTaskId = `critical_test_child_${Date.now()}`;

      // Create parent task
      const insertParent = this.db.prepare(`
        INSERT INTO tasks (
          task_id, title, description, assigned_to, created_by, 
          status, priority, created_at, updated_at, parent_task, 
          child_tasks, depends_on_tasks, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `);

      insertParent.run(
        parentTaskId,
        'Critical Test Parent Task',
        'Parent task for testing hierarchical functionality',
        null, // not assigned
        'admin',
        'pending',
        'high',
        timestamp,
        timestamp,
        null, // no parent
        '[]', // no children yet
        '[]', // no dependencies
        '[]'  // no notes
      );

      // Create child task with parent reference
      const insertChild = this.db.prepare(`
        INSERT INTO tasks (
          task_id, title, description, assigned_to, created_by, 
          status, priority, created_at, updated_at, parent_task, 
          child_tasks, depends_on_tasks, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      `);

      insertChild.run(
        childTaskId,
        'Critical Test Child Task',
        'Child task to test parent relationship',
        null,
        'admin',
        'pending',
        'medium',
        timestamp,
        timestamp,
        parentTaskId, // THIS IS THE KEY TEST - parent reference
        '[]',
        '[]',
        '[]'
      );

      // Update parent's child_tasks array
      const updateParent = this.db.prepare(`
        UPDATE tasks SET child_tasks = ?, updated_at = ? 
        WHERE task_id = ?
      `);

      updateParent.run(JSON.stringify([childTaskId]), timestamp, parentTaskId);

      this.logTest('Task Creation with Parent', true, `Created parent: ${parentTaskId}, child: ${childTaskId}`);
      this.testParentTaskId = parentTaskId;
      this.testChildTaskId = childTaskId;
      return true;

    } catch (error) {
      this.logTest('Task Creation with Parent', false, error.message);
      return false;
    }
  }

  async testParentChildRelationshipQuery() {
    try {
      if (!this.testParentTaskId || !this.testChildTaskId) {
        this.logTest('Parent-Child Query', false, 'No test tasks available');
        return false;
      }

      // Query child task and verify parent reference
      const childTask = this.db.prepare(`
        SELECT task_id, title, parent_task FROM tasks 
        WHERE task_id = ?
      `).get(this.testChildTaskId);

      if (childTask && childTask.parent_task === this.testParentTaskId) {
        this.logTest('Parent-Child Query', true, `Child correctly references parent: ${this.testParentTaskId}`);
      } else {
        this.logTest('Parent-Child Query', false, `Parent reference mismatch: expected ${this.testParentTaskId}, got ${childTask?.parent_task}`);
        return false;
      }

      // Query parent task and verify child in array
      const parentTask = this.db.prepare(`
        SELECT task_id, title, child_tasks FROM tasks 
        WHERE task_id = ?
      `).get(this.testParentTaskId);

      if (parentTask) {
        const childTasks = JSON.parse(parentTask.child_tasks || '[]');
        if (childTasks.includes(this.testChildTaskId)) {
          this.logTest('Child Tasks Array', true, `Parent correctly lists child: ${this.testChildTaskId}`);
          return true;
        } else {
          this.logTest('Child Tasks Array', false, `Child not found in parent's child_tasks array`);
          return false;
        }
      } else {
        this.logTest('Parent-Child Query', false, 'Parent task not found');
        return false;
      }

    } catch (error) {
      this.logTest('Parent-Child Query', false, error.message);
      return false;
    }
  }

  async testParentFiltering() {
    try {
      if (!this.testParentTaskId) {
        this.logTest('Parent Filtering', false, 'No test parent task available');
        return false;
      }

      // Test filtering by parent task
      const childrenQuery = this.db.prepare(`
        SELECT task_id, title, parent_task FROM tasks 
        WHERE parent_task = ?
      `);

      const children = childrenQuery.all(this.testParentTaskId);

      if (children.length > 0 && children.some(child => child.task_id === this.testChildTaskId)) {
        this.logTest('Parent Filtering', true, `Found ${children.length} child task(s) for parent`);
        return true;
      } else {
        this.logTest('Parent Filtering', false, `No children found for parent ${this.testParentTaskId}`);
        return false;
      }

    } catch (error) {
      this.logTest('Parent Filtering', false, error.message);
      return false;
    }
  }

  async testHierarchicalTaskQuery() {
    try {
      // Test complex hierarchical query
      const hierarchyQuery = this.db.prepare(`
        WITH RECURSIVE task_hierarchy AS (
          -- Base case: root tasks (no parent)
          SELECT task_id, title, parent_task, 0 as level
          FROM tasks 
          WHERE parent_task IS NULL
          
          UNION ALL
          
          -- Recursive case: children of previous level
          SELECT t.task_id, t.title, t.parent_task, th.level + 1
          FROM tasks t
          INNER JOIN task_hierarchy th ON t.parent_task = th.task_id
        )
        SELECT task_id, title, parent_task, level 
        FROM task_hierarchy 
        ORDER BY level, task_id
      `);

      const hierarchy = hierarchyQuery.all();

      if (hierarchy.length > 0) {
        const hasTestTasks = hierarchy.some(task => 
          task.task_id === this.testParentTaskId || task.task_id === this.testChildTaskId
        );
        
        this.logTest('Hierarchical Query', true, `Found ${hierarchy.length} tasks in hierarchy, includes our test tasks: ${hasTestTasks}`);
        return true;
      } else {
        this.logTest('Hierarchical Query', false, 'No hierarchical structure found');
        return false;
      }

    } catch (error) {
      this.logTest('Hierarchical Query', false, error.message);
      return false;
    }
  }

  async testDataIntegrity() {
    try {
      // Check for orphaned child tasks (child references non-existent parent)
      const orphanCheck = this.db.prepare(`
        SELECT c.task_id, c.title, c.parent_task
        FROM tasks c
        LEFT JOIN tasks p ON c.parent_task = p.task_id
        WHERE c.parent_task IS NOT NULL AND p.task_id IS NULL
      `);

      const orphans = orphanCheck.all();

      // Check for inconsistent parent-child relationships
      const inconsistencyCheck = this.db.prepare(`
        SELECT p.task_id as parent_id, p.title as parent_title, p.child_tasks
        FROM tasks p
        WHERE p.child_tasks != '[]' AND p.child_tasks IS NOT NULL
      `);

      const parentsWithChildren = inconsistencyCheck.all();
      let inconsistencies = 0;

      for (const parent of parentsWithChildren) {
        const childIds = JSON.parse(parent.child_tasks || '[]');
        for (const childId of childIds) {
          const childCheck = this.db.prepare(`
            SELECT task_id FROM tasks WHERE task_id = ? AND parent_task = ?
          `).get(childId, parent.parent_id);
          
          if (!childCheck) {
            inconsistencies++;
          }
        }
      }

      const hasIssues = orphans.length > 0 || inconsistencies > 0;
      this.logTest('Data Integrity', !hasIssues, 
        `Orphans: ${orphans.length}, Inconsistencies: ${inconsistencies}`);
      
      return !hasIssues;

    } catch (error) {
      this.logTest('Data Integrity', false, error.message);
      return false;
    }
  }

  async cleanup() {
    try {
      if (this.testParentTaskId) {
        this.db.prepare('DELETE FROM tasks WHERE task_id = ?').run(this.testParentTaskId);
      }
      if (this.testChildTaskId) {
        this.db.prepare('DELETE FROM tasks WHERE task_id = ?').run(this.testChildTaskId);
      }
      console.log('\n🧹 Cleanup: Removed test tasks');
    } catch (error) {
      console.log(`⚠️ Cleanup failed: ${error.message}`);
    }
  }

  async runAllTests() {
    console.log('\n🚀 Starting Direct Database Tests...\n');

    try {
      // Initialize database connection
      if (!await this.initDatabase()) {
        return false;
      }

      const tests = [
        () => this.testDatabaseSchema(),
        () => this.testTaskCreationWithParent(),
        () => this.testParentChildRelationshipQuery(),
        () => this.testParentFiltering(),
        () => this.testHierarchicalTaskQuery(),
        () => this.testDataIntegrity()
      ];

      for (const test of tests) {
        try {
          await test();
        } catch (error) {
          console.log(`💥 Test failed with exception: ${error.message}`);
          this.testResults.failed++;
        }
      }

      await this.cleanup();

      // Results Summary
      console.log('\n═══════════════════════════════════════════════════════');
      console.log('📊 CRITICAL DATABASE TEST RESULTS');
      console.log('═══════════════════════════════════════════════════════');
      console.log(`✅ Tests Passed: ${this.testResults.passed}`);
      console.log(`❌ Tests Failed: ${this.testResults.failed}`);
      console.log(`📈 Success Rate: ${((this.testResults.passed / (this.testResults.passed + this.testResults.failed)) * 100).toFixed(1)}%`);

      if (this.testResults.failed > 0) {
        console.log('\n🔍 FAILURE DETAILS:');
        this.testResults.errors.forEach(error => console.log(`   • ${error}`));
      }

      const allTestsPassed = this.testResults.failed === 0;
      
      if (allTestsPassed) {
        console.log('\n🎉 ALL DATABASE TESTS PASSED!');
        console.log('✅ Parent task functionality at database level is working correctly');
      } else {
        console.log('\n⚠️  CRITICAL DATABASE ISSUES DETECTED!');
        console.log('❌ Parent task functionality has database-level problems');
      }

      return allTestsPassed;

    } finally {
      if (this.db) {
        this.db.close();
      }
    }
  }
}

// Run the tests
const tester = new DirectDatabaseTester();
tester.runAllTests().then(success => {
  process.exit(success ? 0 : 1);
}).catch(error => {
  console.error('💥 Database test execution failed:', error);
  process.exit(1);
});