import { buildAgentPrompt } from './build/utils/promptTemplates.js';

console.log('🔍 TESTING PROMPT INCONSISTENCY');
console.log('=' .repeat(60));

const testAgentId = 'test-agent';
const testToken = 'test-token-123';
const adminToken = 'admin-token-456';

// What the template system produces (CORRECT)
const templatePrompt = buildAgentPrompt(testAgentId, testToken, adminToken, 'worker_with_rag');

// What the hardcoded production code uses (WRONG - from line 343)
const hardcodedPrompt = `This is your agent token: ${testToken} Ask the project RAG agent at least 5-7 questions to understand what you need to do. I want you to critically think when asking a question, then criticize yourself before asking that question. How you criticize yourself is by proposing an idea, criticizing it, and based on that criticism you pull through with that idea. It's better to add too much context versus too little. Add all these context entries to the agent mcp. ACT AUTO --worker --memory`;

console.log('\n📋 TEMPLATE SYSTEM OUTPUT (what should be used):');
console.log('-'.repeat(40));
console.log(templatePrompt);

console.log('\n🚨 HARDCODED PRODUCTION OUTPUT (what is actually used):');
console.log('-'.repeat(40));
console.log(hardcodedPrompt);

console.log('\n🔍 COMPARISON:');
console.log(`Template length: ${templatePrompt?.length || 0} characters`);
console.log(`Hardcoded length: ${hardcodedPrompt.length} characters`);
console.log(`Are they identical? ${templatePrompt === hardcodedPrompt ? '✅ YES' : '❌ NO'}`);

if (templatePrompt !== hardcodedPrompt) {
  console.log('\n🚨 CRITICAL FAILURE: Production code does not use template system!');
  console.log('This proves the 1:1 implementation is broken.');
} else {
  console.log('\n✅ Prompts match - implementation is correct');
}

console.log('\n' + '=' .repeat(60));