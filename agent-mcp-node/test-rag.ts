// Test script for RAG functionality
import dotenv from 'dotenv';
dotenv.config();

import { initDatabase } from './src/db/schema.js';
import { initializeOpenAIClient } from './src/external/openai_service.js';
import { queryRagSystem } from './src/features/rag/query.js';
import { runIndexingCycle } from './src/features/rag/indexing.js';

async function testRagSystem() {
  console.log('🧪 Testing RAG System...');
  
  // Initialize database
  console.log('📊 Initializing database...');
  initDatabase();
  
  // Initialize OpenAI client
  console.log('🤖 Initializing OpenAI client...');
  const client = initializeOpenAIClient();
  if (!client) {
    console.error('❌ OpenAI client initialization failed. Check your API key.');
    return;
  }
  
  // Run indexing cycle to ensure there's some data
  console.log('📚 Running indexing cycle...');
  await runIndexingCycle();
  
  // Test a simple query
  console.log('🔍 Testing RAG query...');
  const testQuery = 'What is Agent-MCP and how does it work?';
  console.log(`Query: "${testQuery}"`);
  
  try {
    const result = await queryRagSystem(testQuery);
    console.log('\n✅ RAG Query Result:');
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
    console.log(result);
    console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━');
  } catch (error) {
    console.error('❌ RAG query failed:', error);
  }
  
  console.log('\n🧪 RAG testing completed!');
}

// Run the test
testRagSystem().catch(console.error);