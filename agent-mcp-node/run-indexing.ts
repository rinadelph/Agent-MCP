#!/usr/bin/env tsx
// Script to run RAG indexing cycle for Agent-MCP Node.js
// This will index all project documentation and code for RAG queries

import { runIndexingCycle } from './src/features/rag/indexing.js';
import { getVectorSearchStats } from './src/features/rag/vectorSearch.js';
import { initializeOpenAIClient } from './src/external/openai_service.js';

async function main() {
  console.log('🚀 Starting Agent-MCP RAG Indexing...');
  
  // Initialize OpenAI client
  const client = initializeOpenAIClient();
  if (!client) {
    console.error('❌ Failed to initialize OpenAI client. Please check OPENAI_API_KEY environment variable.');
    process.exit(1);
  }
  
  // Get initial stats
  const initialStats = getVectorSearchStats();
  console.log('📊 Initial RAG Status:');
  console.log(`  - Chunks: ${initialStats.chunkCount}`);
  console.log(`  - Embeddings: ${initialStats.embeddingCount}`);
  console.log(`  - Coverage: ${initialStats.chunkCount > 0 ? ((initialStats.embeddingCount / initialStats.chunkCount) * 100).toFixed(1) : 0}%`);
  console.log('');
  
  // Run indexing cycle
  try {
    await runIndexingCycle();
    
    // Get final stats
    const finalStats = getVectorSearchStats();
    console.log('');
    console.log('📊 Final RAG Status:');
    console.log(`  - Chunks: ${finalStats.chunkCount}`);
    console.log(`  - Embeddings: ${finalStats.embeddingCount}`);
    console.log(`  - Coverage: ${finalStats.chunkCount > 0 ? ((finalStats.embeddingCount / finalStats.chunkCount) * 100).toFixed(1) : 0}%`);
    
    if (finalStats.embeddingCount > initialStats.embeddingCount) {
      console.log('');
      console.log('✅ RAG indexing completed successfully!');
      console.log(`📈 Added ${finalStats.embeddingCount - initialStats.embeddingCount} new embeddings`);
    } else {
      console.log('');
      console.log('ℹ️ No new content to index (RAG is up to date)');
    }
    
  } catch (error) {
    console.error('❌ RAG indexing failed:', error);
    process.exit(1);
  }
}

main().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});