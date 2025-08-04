import { buildAgentPrompt, PROMPT_TEMPLATES } from './build/utils/promptTemplates.js';

console.log('🧪 TESTING TEMPLATE DRIFT SCENARIO');
console.log('=' .repeat(60));

// Simulate what happens if someone updates the template
const originalTemplate = PROMPT_TEMPLATES.worker_with_rag;
console.log('\n📋 CURRENT TEMPLATE:');
console.log(originalTemplate);

// The hardcoded version in production (line 343)
const hardcodedInProduction = `This is your agent token: {agent_token} Ask the project RAG agent at least 5-7 questions to understand what you need to do. I want you to critically think when asking a question, then criticize yourself before asking that question. How you criticize yourself is by proposing an idea, criticizing it, and based on that criticism you pull through with that idea. It's better to add too much context versus too little. Add all these context entries to the agent mcp. ACT AUTO --worker --memory`;

console.log('\n🏭 HARDCODED IN PRODUCTION:');
console.log(hardcodedInProduction);

console.log('\n🔍 ANALYSIS:');
console.log(`Templates match exactly: ${originalTemplate === hardcodedInProduction ? '✅ YES' : '❌ NO'}`);

console.log('\n🚨 CRITICAL DESIGN ISSUES:');
console.log('1. ❌ Code duplication - same prompt in two places');
console.log('2. ❌ Template changes won\'t affect production (src/tools/agent.ts:343)');
console.log('3. ❌ Inconsistent architecture - some functions use templates, others hardcode');
console.log('4. ❌ Maintenance nightmare - must update two places for changes');

console.log('\n📋 PROOF OF DESIGN FLAW:');
console.log('If worker_with_rag template is updated:');
console.log('- ✅ buildAgentPrompt() will use new template');
console.log('- ❌ create_agent() will still use old hardcoded string');
console.log('- ❌ Agents get inconsistent prompts');

console.log('\n' + '=' .repeat(60));