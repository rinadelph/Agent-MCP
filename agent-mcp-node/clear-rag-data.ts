#!/usr/bin/env tsx
// Clear all RAG data and force complete re-indexing

import { getDbConnection } from './src/db/connection.js';
import { runIndexingCycle } from './src/features/rag/indexing.js';
import { getVectorSearchStats } from './src/features/rag/vectorSearch.js';
import { initializeOpenAIClient } from './src/external/openai_service.js';

async function clearAllRagDataAndReindex() {
  console.log('🗑️ Clearing ALL RAG data and re-indexing...');
  
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
  
  // Clear ALL RAG data
  console.log('🗑️ Clearing all RAG chunks, embeddings, and metadata...');
  const db = getDbConnection();
  
  try {
    const clearTransaction = db.transaction(() => {
      // Clear all chunks
      const clearChunks = db.prepare('DELETE FROM rag_chunks');
      const chunksResult = clearChunks.run();
      console.log(`✅ Cleared ${chunksResult.changes} chunks`);
      
      // Clear all embeddings
      const clearEmbeddings = db.prepare('DELETE FROM rag_embeddings');
      const embeddingsResult = clearEmbeddings.run();
      console.log(`✅ Cleared ${embeddingsResult.changes} embeddings`);
      
      // Clear all metadata including hashes
      const clearMeta = db.prepare('DELETE FROM rag_meta');
      const metaResult = clearMeta.run();
      console.log(`✅ Cleared ${metaResult.changes} metadata entries`);
      
      // Reset with fresh timestamps
      const resetTimestamp = '1970-01-01T00:00:00Z';
      const metaEntries = [
        'last_indexed_markdown',
        'last_indexed_code', 
        'last_indexed_context',
        'last_indexed_tasks',
        'last_indexed_filemeta'
      ];
      
      for (const key of metaEntries) {
        db.prepare(`
          INSERT INTO rag_meta (meta_key, meta_value)
          VALUES (?, ?)
        `).run(key, resetTimestamp);
      }
      
      console.log(`✅ Reset ${metaEntries.length} fresh indexing timestamps`);
    });
    
    clearTransaction();
    
    // Verify clearing worked
    const afterClearStats = getVectorSearchStats();
    console.log('📊 After Clear:');
    console.log(`  - Chunks: ${afterClearStats.chunkCount}`);
    console.log(`  - Embeddings: ${afterClearStats.embeddingCount}`);
    
    // Now run indexing cycle which should definitely pick up everything
    console.log('');
    console.log('📚 Running fresh indexing cycle...');
    await runIndexingCycle();
    
    // Get final stats
    const finalStats = getVectorSearchStats();
    console.log('');
    console.log('📊 Final Status:');
    console.log(`  - Chunks: ${finalStats.chunkCount}`);
    console.log(`  - Embeddings: ${finalStats.embeddingCount}`);
    console.log(`  - Coverage: ${finalStats.chunkCount > 0 ? ((finalStats.embeddingCount / finalStats.chunkCount) * 100).toFixed(1) : 0}%`);
    
    if (finalStats.embeddingCount > 0) {
      console.log('');
      console.log(`✅ Complete fresh indexing successful!`);
      console.log(`📈 Indexed ${finalStats.embeddingCount} embeddings`);
      console.log(`📝 Total content indexed: ${finalStats.chunkCount} chunks`);
    } else {
      console.log('');
      console.log('❌ No content was indexed - there may be an issue');
    }
    
  } catch (error) {
    console.error('❌ Clear and re-indexing failed:', error);
    process.exit(1);
  }
}

clearAllRagDataAndReindex().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});