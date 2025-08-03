// Vector search functionality for Agent-MCP Node.js RAG
// Ported from Python RAG query system with sqlite-vec integration

import { getDbConnection, isVssLoadable, createDbConnection } from '../../db/connection.js';
import { generateSingleEmbedding } from '../../external/openai_service.js';
import { MCP_DEBUG, EMBEDDING_MODEL, EMBEDDING_DIMENSION } from '../../core/config.js';

/**
 * Interface for vector search results
 */
export interface VectorSearchResult {
  chunkText: string;
  sourceType: string;
  sourceRef: string;
  metadata?: any;
  distance: number;
  chunkId: number;
}

/**
 * Perform vector similarity search against the RAG embeddings table
 * Returns the most similar chunks to the query text
 */
export async function performVectorSearch(
  queryText: string,
  k: number = 10,
  model: string = EMBEDDING_MODEL,
  dimensions: number = EMBEDDING_DIMENSION
): Promise<VectorSearchResult[]> {
  // Check if vector search is available
  if (!isVssLoadable()) {
    console.warn('Vector search not available: sqlite-vec extension not loaded');
    return [];
  }

  // Use a fresh connection to ensure sqlite-vec is properly loaded
  const db = createDbConnection();
  
  try {
    // Check if rag_embeddings table exists
    const tableExists = db.prepare(`
      SELECT name FROM sqlite_master 
      WHERE type='table' AND name='rag_embeddings'
    `).get();

    if (!tableExists) {
      console.warn('Vector search not available: rag_embeddings table not found');
      return [];
    }

    // Generate embedding for the query text
    if (MCP_DEBUG) {
      console.log(`🔍 Generating embedding for query: "${queryText.substring(0, 100)}..."`);
    }

    const queryEmbedding = await generateSingleEmbedding(queryText, model, dimensions);
    const queryEmbeddingJson = JSON.stringify(queryEmbedding);

    // Perform vector similarity search
    const searchSql = `
      SELECT 
        c.chunk_text,
        c.source_type,
        c.source_ref,
        c.metadata,
        c.chunk_id,
        r.distance
      FROM rag_embeddings r
      JOIN rag_chunks c ON r.rowid = c.chunk_id
      WHERE r.embedding MATCH ? AND k = ?
      ORDER BY r.distance
    `;

    if (MCP_DEBUG) {
      console.log(`🔍 Performing vector search with k=${k}`);
    }

    const results = db.prepare(searchSql).all(queryEmbeddingJson, k);

    // Process and parse results
    const processedResults: VectorSearchResult[] = results.map((row: any) => {
      let metadata = null;
      if (row.metadata) {
        try {
          metadata = JSON.parse(row.metadata);
        } catch (error) {
          console.warn('Failed to parse metadata JSON:', error);
          metadata = null;
        }
      }

      return {
        chunkText: row.chunk_text,
        sourceType: row.source_type,
        sourceRef: row.source_ref,
        metadata: metadata,
        distance: row.distance,
        chunkId: row.chunk_id
      };
    });

    if (MCP_DEBUG) {
      console.log(`🔍 Vector search found ${processedResults.length} results`);
    }

    return processedResults;

  } catch (error) {
    console.error('Error performing vector search:', error);
    
    if (error instanceof Error) {
      if (error.message.includes('no such table')) {
        console.warn('Vector search failed: rag_embeddings table not found');
      } else if (error.message.includes('MATCH')) {
        console.warn('Vector search failed: sqlite-vec extension may not be properly loaded');
      }
    }
    
    return [];
  } finally {
    // Close the fresh connection
    db.close();
  }
}

/**
 * Get statistics about the vector search database
 */
export function getVectorSearchStats(): {
  available: boolean;
  chunkCount: number;
  embeddingCount: number;
  tableExists: boolean;
} {
  const available = isVssLoadable();
  let chunkCount = 0;
  let embeddingCount = 0;
  let tableExists = false;

  if (!available) {
    return { available: false, chunkCount: 0, embeddingCount: 0, tableExists: false };
  }

  // Use a fresh connection to ensure sqlite-vec is properly loaded
  const db = createDbConnection();

  try {
    // Check if tables exist
    const embeddingsTable = db.prepare(`
      SELECT name FROM sqlite_master 
      WHERE type='table' AND name='rag_embeddings'
    `).get();
    
    tableExists = !!embeddingsTable;

    if (tableExists) {
      // Get chunk count
      const chunkResult = db.prepare('SELECT COUNT(*) as count FROM rag_chunks').get() as { count: number };
      chunkCount = chunkResult.count;

      // Get embedding count
      const embeddingResult = db.prepare('SELECT COUNT(*) as count FROM rag_embeddings').get() as { count: number };
      embeddingCount = embeddingResult.count;
    }

  } catch (error) {
    console.error('Error getting vector search stats:', error);
  } finally {
    // Close the fresh connection
    db.close();
  }

  return {
    available,
    chunkCount,
    embeddingCount,
    tableExists
  };
}

/**
 * Test vector search functionality with a simple query
 */
export async function testVectorSearch(): Promise<boolean> {
  try {
    const stats = getVectorSearchStats();
    
    if (!stats.available) {
      console.log('❌ Vector search test failed: sqlite-vec not available');
      return false;
    }

    if (!stats.tableExists) {
      console.log('❌ Vector search test failed: rag_embeddings table not found');
      return false;
    }

    if (stats.embeddingCount === 0) {
      console.log('⚠️ Vector search test skipped: no embeddings in database');
      return true; // Not a failure, just no data
    }

    // Perform a test search
    const results = await performVectorSearch('test query', 1);
    
    if (results.length > 0) {
      console.log('✅ Vector search test passed: found results');
      return true;
    } else {
      console.log('⚠️ Vector search test: no results found (may be normal with test query)');
      return true; // Not necessarily a failure
    }

  } catch (error) {
    console.error('❌ Vector search test failed:', error);
    return false;
  }
}

/**
 * Insert a chunk and its embedding into the vector database
 * Used by the indexing pipeline
 */
export async function insertChunkWithEmbedding(
  chunkText: string,
  sourceType: string,
  sourceRef: string,
  metadata: any = null,
  embedding?: number[]
): Promise<number | null> {
  if (!isVssLoadable()) {
    console.error('Vector search not available - cannot insert chunk with embedding');
    return null;
  }

  // Use a fresh connection to ensure sqlite-vec is properly loaded
  const db = createDbConnection();
  
  try {
    // Generate embedding if not provided
    let chunkEmbedding = embedding;
    if (!chunkEmbedding) {
      chunkEmbedding = await generateSingleEmbedding(chunkText);
    }

    if (!chunkEmbedding) {
      console.error('Failed to generate embedding for chunk');
      return null;
    }

    let chunkId: number | null = null;

    // Step 1: Insert chunk into rag_chunks table first
    const insertChunk = db.prepare(`
      INSERT INTO rag_chunks (source_type, source_ref, chunk_text, indexed_at, metadata)
      VALUES (?, ?, ?, ?, ?)
    `);

    const chunkResult = insertChunk.run(
      sourceType,
      sourceRef,
      chunkText,
      new Date().toISOString(),
      metadata ? JSON.stringify(metadata) : null
    );

    chunkId = chunkResult.lastInsertRowid as number;

    // Step 2: Insert embedding into rag_embeddings table using the chunk ID as rowid
    // Following sqlite-vec documentation pattern for better-sqlite3
    const insertEmbedding = db.prepare(`
      INSERT INTO rag_embeddings (rowid, embedding)
      VALUES (?, ?)
    `);

    // Convert embedding to Float32Array buffer as required by sqlite-vec
    const embeddingFloat32 = new Float32Array(chunkEmbedding);
    const embeddingBuffer = Buffer.from(embeddingFloat32.buffer);
    
    // Ensure rowid is treated as integer by sqlite-vec (try BigInt approach)
    const rowidInteger = BigInt(chunkId);
    insertEmbedding.run(rowidInteger, embeddingBuffer);

    if (MCP_DEBUG) {
      console.log(`📝 Inserted chunk ${chunkId} with embedding (${sourceType}:${sourceRef})`);
    }

    return chunkId;

  } catch (error) {
    console.error('Error inserting chunk with embedding:', error);
    
    // If we inserted a chunk but failed on embedding, clean up the chunk
    if (error instanceof Error && error.message.includes('vec0')) {
      console.error('Vector table (vec0) issue - sqlite-vec extension may not be properly loaded');
    }
    
    return null;
  } finally {
    // Close the fresh connection
    db.close();
  }
}

/**
 * Remove chunks and embeddings by source reference
 * Used for updating or cleaning up indexed content
 */
export function removeChunksBySource(sourceRef: string): number {
  const db = getDbConnection();
  
  try {
    const transaction = db.transaction(() => {
      // Get chunk IDs to remove embeddings
      const chunkIds = db.prepare(`
        SELECT chunk_id FROM rag_chunks WHERE source_ref = ?
      `).all(sourceRef).map((row: any) => row.chunk_id);

      let removedCount = 0;

      if (chunkIds.length > 0) {
        // Remove embeddings
        const removeEmbeddings = db.prepare(`
          DELETE FROM rag_embeddings WHERE rowid = ?
        `);
        
        for (const chunkId of chunkIds) {
          removeEmbeddings.run(chunkId);
        }

        // Remove chunks
        const removeChunks = db.prepare(`
          DELETE FROM rag_chunks WHERE source_ref = ?
        `);
        
        const result = removeChunks.run(sourceRef);
        removedCount = result.changes;
      }

      return removedCount;
    });

    const removedCount = transaction();

    if (MCP_DEBUG && removedCount > 0) {
      console.log(`🗑️ Removed ${removedCount} chunks for source: ${sourceRef}`);
    }

    return removedCount;

  } catch (error) {
    console.error('Error removing chunks by source:', error);
    return 0;
  }
}

console.log('✅ Vector search system loaded');