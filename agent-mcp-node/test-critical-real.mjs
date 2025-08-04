import { getDbConnection } from './src/db/connection.js';

console.log('🔍 Testing REAL Agent Implementation...');

const db = getDbConnection();

// Check recent agents
const agents = db.prepare('SELECT agent_id, status, created_at FROM agents ORDER BY created_at DESC LIMIT 5').all();
console.log('\n📊 Recent agents:');
console.log(JSON.stringify(agents, null, 2));

// Check for any completed tasks
const tasks = db.prepare('SELECT task_id, title, status, assigned_to FROM tasks WHERE task_id = ? OR title LIKE ?').all('task_7ca515959191', '%prompt%');
console.log('\n📋 Prompt-related tasks:');
console.log(JSON.stringify(tasks, null, 2));

console.log('\n✅ Database queries completed');