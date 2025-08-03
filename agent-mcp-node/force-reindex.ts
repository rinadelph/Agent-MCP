#!/usr/bin/env tsx
// Force complete re-indexing of all project content

import { getDbConnection } from './src/db/connection.js';
import { runIndexingCycle } from './src/features/rag/indexing.js';
import { getVectorSearchStats } from './src/features/rag/vectorSearch.js';
import { initializeOpenAIClient } from './src/external/openai_service.js';

async function forceCompleteReindex() {
  console.log('🔄 Force Complete RAG Re-indexing...');
  
  // Initialize OpenAI client
  const client = initializeOpenAIClient();
  if (!client) {
    console.error('❌ Failed to initialize OpenAI client');
    process.exit(1);
  }
  
  // Get initial stats
  const initialStats = getVectorSearchStats();
  console.log('📊 Initial Status:');
  console.log(`  - Chunks: ${initialStats.chunkCount}`);
  console.log(`  - Embeddings: ${initialStats.embeddingCount}`);
  
  // Reset all indexing timestamps to force complete re-index
  console.log('🔄 Resetting indexing timestamps...');
  const db = getDbConnection();
  
  try {
    const resetTransaction = db.transaction(() => {
      // Reset all last_indexed timestamps to epoch
      const resetTimestamp = '1970-01-01T00:00:00Z';
      
      const updates = [
        'last_indexed_markdown',
        'last_indexed_code', 
        'last_indexed_context',
        'last_indexed_tasks',
        'last_indexed_filemeta'
      ];
      
      for (const key of updates) {
        db.prepare(`
          INSERT OR REPLACE INTO rag_meta (meta_key, meta_value)
          VALUES (?, ?)
        `).run(key, resetTimestamp);
      }
      
      console.log(`✅ Reset ${updates.length} indexing timestamps`);
    });
    
    resetTransaction();
    
    // Now run indexing cycle which should pick up everything
    console.log('📚 Running complete indexing cycle...');
    await runIndexingCycle();
    
    // Get final stats
    const finalStats = getVectorSearchStats();
    console.log('');
    console.log('📊 Final Status:');
    console.log(`  - Chunks: ${finalStats.chunkCount}`);
    console.log(`  - Embeddings: ${finalStats.embeddingCount}`);
    console.log(`  - Coverage: ${finalStats.chunkCount > 0 ? ((finalStats.embeddingCount / finalStats.chunkCount) * 100).toFixed(1) : 0}%`);
    
    const newEmbeddings = finalStats.embeddingCount - initialStats.embeddingCount;
    if (newEmbeddings > 0) {
      console.log('');
      console.log(`✅ Complete re-indexing successful!`);
      console.log(`📈 Added ${newEmbeddings} new embeddings`);
      console.log(`📝 Total content now indexed: ${finalStats.chunkCount} chunks`);
    } else {
      console.log('');
      console.log('ℹ️ No additional content was indexed');
    }
    
  } catch (error) {
    console.error('❌ Force re-indexing failed:', error);
    process.exit(1);
  }
}

forceCompleteReindex().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});