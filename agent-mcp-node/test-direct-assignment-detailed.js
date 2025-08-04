#!/usr/bin/env node

/**
 * DETAILED TEST: Direct Agent Assignment Critical Bug Investigation
 */

import Database from 'better-sqlite3';

const DB_PATH = './.agent/mcp_state.db';

console.log('🔍 DETAILED INVESTIGATION: Direct Agent Assignment Bug');
console.log('=====================================================');

const db = new Database(DB_PATH);

// Get all agents and their task assignments
console.log('\n📊 AGENT TASK ASSIGNMENT ANALYSIS:');
const agents = db.prepare('SELECT * FROM agents ORDER BY created_at DESC').all();
for (const agent of agents) {
    const tasks = db.prepare('SELECT task_id, title, status FROM tasks WHERE assigned_to = ?').all(agent.agent_id);
    console.log(`\n🤖 Agent: ${agent.agent_id}`);
    console.log(`   Status: ${agent.status}`);
    console.log(`   Created: ${agent.created_at}`);
    console.log(`   Current Task: ${agent.current_task || 'NONE'}`);
    console.log(`   Assigned Tasks: ${tasks.length}`);
    
    if (tasks.length === 0) {
        console.log('   ❌ VIOLATION: Agent has no assigned tasks!');
        
        // Check if this agent should have tasks based on creation pattern
        const agentActions = db.prepare('SELECT * FROM agent_actions WHERE agent_id = ? ORDER BY timestamp DESC').all(agent.agent_id);
        console.log(`   Agent Actions: ${agentActions.length}`);
        
        if (agentActions.length > 0) {
            console.log('   Recent Actions:');
            agentActions.slice(0, 3).forEach(action => {
                console.log(`     - ${action.action_type} at ${action.timestamp}`);
            });
        }
    } else {
        console.log('   ✅ VALID: Agent has assigned tasks');
        tasks.forEach(task => {
            console.log(`     - ${task.task_id}: ${task.title} (${task.status})`);
        });
    }
}

// Check for orphaned tasks (no assigned agent)
console.log('\n📋 ORPHANED TASKS ANALYSIS:');
const orphanedTasks = db.prepare('SELECT * FROM tasks WHERE assigned_to IS NULL AND status != ? ORDER BY created_at DESC').all('completed');
console.log(`Found ${orphanedTasks.length} orphaned tasks`);

if (orphanedTasks.length > 0) {
    orphanedTasks.forEach(task => {
        console.log(`❓ Orphaned: ${task.task_id} - ${task.title} (${task.status})`);
    });
}

// Check task assignment integrity
console.log('\n🔗 TASK ASSIGNMENT INTEGRITY CHECK:');
const allTasks = db.prepare('SELECT * FROM tasks').all();
let integrityViolations = 0;

for (const task of allTasks) {
    if (task.assigned_to) {
        const agent = db.prepare('SELECT agent_id FROM agents WHERE agent_id = ?').get(task.assigned_to);
        if (!agent) {
            console.log(`❌ INTEGRITY VIOLATION: Task ${task.task_id} assigned to non-existent agent ${task.assigned_to}`);
            integrityViolations++;
        }
    }
}

console.log(`Integrity violations found: ${integrityViolations}`);

// Test the smart parent suggestion algorithm on real data
console.log('\n🧠 SMART PARENT SUGGESTION ALGORITHM TEST:');
const testTask = allTasks[0];
if (testTask) {
    console.log(`Testing suggestions for: "${testTask.title}"`);
    
    // Get candidate parent tasks
    const candidates = db.prepare(`
        SELECT task_id, title, description, status, priority, updated_at
        FROM tasks 
        WHERE status IN ('pending', 'in_progress') AND task_id != ?
        ORDER BY 
            CASE WHEN status = 'in_progress' THEN 1 ELSE 2 END,
            CASE priority WHEN 'high' THEN 3 WHEN 'medium' THEN 2 ELSE 1 END DESC,
            updated_at DESC
        LIMIT 5
    `).all(testTask.task_id);
    
    console.log(`Found ${candidates.length} candidate parent tasks:`);
    
    // Calculate similarity scores
    function calculateSimilarity(text1, text2) {
        const words1 = new Set((text1 || '').toLowerCase().split(/\s+/).filter(w => w.length > 2));
        const words2 = new Set((text2 || '').toLowerCase().split(/\s+/).filter(w => w.length > 2));
        
        if (words1.size === 0 || words2.size === 0) return 0;
        
        const intersection = new Set([...words1].filter(w => words2.has(w)));
        const union = new Set([...words1, ...words2]);
        
        return intersection.size / union.size;
    }
    
    const suggestions = [];
    for (const candidate of candidates) {
        const titleSim = calculateSimilarity(testTask.description || '', candidate.title || '');
        const descSim = calculateSimilarity(testTask.description || '', candidate.description || '');
        const combinedScore = (titleSim * 0.6) + (descSim * 0.4);
        
        // Boost score for in-progress tasks
        let finalScore = combinedScore;
        if (candidate.status === 'in_progress') {
            finalScore *= 1.2;
        }
        
        if (finalScore > 0.05) { // Lower threshold for testing
            suggestions.push({
                task_id: candidate.task_id,
                title: candidate.title,
                status: candidate.status,
                priority: candidate.priority,
                similarity_score: Math.round(finalScore * 1000) / 1000,
                reason: `Similar content (${Math.round(finalScore * 100)}% match)`
            });
        }
    }
    
    suggestions.sort((a, b) => b.similarity_score - a.similarity_score);
    
    if (suggestions.length > 0) {
        console.log('💡 Smart suggestions generated:');
        suggestions.slice(0, 3).forEach((suggestion, i) => {
            console.log(`   ${i + 1}. ${suggestion.task_id}: ${suggestion.title}`);
            console.log(`      Status: ${suggestion.status} | Priority: ${suggestion.priority} | ${suggestion.reason}`);
        });
    } else {
        console.log('❌ No smart suggestions generated (algorithm may need tuning)');
    }
}

db.close();

console.log('\n🎯 CRITICAL FINDINGS SUMMARY:');
console.log('============================');

const violatingAgents = agents.filter(agent => {
    const tasks = db.prepare('SELECT COUNT(*) as count FROM tasks WHERE assigned_to = ?').get(agent.agent_id);
    return tasks.count === 0 && agent.status !== 'terminated';
});

if (violatingAgents.length > 0) {
    console.log(`❌ CRITICAL BUG CONFIRMED: ${violatingAgents.length} agents violate direct assignment principle`);
    console.log('   These agents exist without assigned tasks, violating system requirements');
    
    // This is the critical bug that must be reported
    process.exit(1);
} else {
    console.log('✅ All active agents have assigned tasks - direct assignment principle upheld');
    process.exit(0);
}