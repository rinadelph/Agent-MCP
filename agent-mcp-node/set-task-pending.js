#!/usr/bin/env node

/**
 * Set task_6037dc070973 back to pending due to critical test failures
 */

import Database from 'better-sqlite3';

const DB_PATH = './.agent/mcp_state.db';
const TASK_ID = 'task_6037dc070973';

console.log('🔄 Setting task status back to pending due to critical test failures...');

try {
    const db = new Database(DB_PATH);
    
    // Check if task exists
    const task = db.prepare('SELECT * FROM tasks WHERE task_id = ?').get(TASK_ID);
    if (!task) {
        console.log(`❌ Task ${TASK_ID} not found`);
        process.exit(1);
    }
    
    console.log(`📋 Current status: ${task.status}`);
    
    // Update task status to pending
    const timestamp = new Date().toISOString();
    const updateResult = db.prepare(`
        UPDATE tasks 
        SET status = ?, updated_at = ? 
        WHERE task_id = ?
    `).run('pending', timestamp, TASK_ID);
    
    if (updateResult.changes > 0) {
        console.log(`✅ Task ${TASK_ID} status changed to PENDING`);
        console.log(`📅 Updated at: ${timestamp}`);
        
        // Add a note about the test failure
        const notesQuery = db.prepare('SELECT notes FROM tasks WHERE task_id = ?').get(TASK_ID);
        const currentNotes = JSON.parse(notesQuery.notes || '[]');
        
        currentNotes.push({
            content: 'CRITICAL TEST FAILURE: Direct agent assignment validation revealed multiple agents violating core requirements. Implementation needs fixes before completion.',
            timestamp: timestamp,
            agent_id: 'test-070973'
        });
        
        db.prepare('UPDATE tasks SET notes = ? WHERE task_id = ?').run(JSON.stringify(currentNotes), TASK_ID);
        console.log('📝 Added failure note to task');
        
    } else {
        console.log(`❌ Failed to update task status`);
        process.exit(1);
    }
    
    db.close();
    console.log('✅ Task status update completed');
    
} catch (error) {
    console.error('❌ Error updating task status:', error);
    process.exit(1);
}